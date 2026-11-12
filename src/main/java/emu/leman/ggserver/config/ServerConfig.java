package emu.leman.ggserver.config;

import java.nio.file.*;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Immutable startup settings; relative paths resolve from the configuration file, never cwd. */
public final class ServerConfig {
    public final Path root;
    public final String host, publicBase, cdnUrl, adminPassword, secretKey, certificatePassword;
    public final int port, httpPort;
    public final boolean https, http, verbose;
    public final Path certificate;
    public final String databaseBackend, mongoUri, mongoDatabase;
    public final int sessionTimeoutSeconds, sessionCleanupSeconds, maxSessions;
    public final boolean sessionRequired;
    public final String logLevel;
    public final boolean logFile;
    private final Map<String,Path> folders;

    private ServerConfig(Path base, Map<String,Object> values, Map<String,String> environment) {
        root=resolve(base,text(values,"root","."));
        host=text(values,"host","127.0.0.1");
        if(host.isBlank()) throw new IllegalArgumentException("host must not be blank");
        https=flag(values,"https",false); http=flag(values,"http",false);
        port=number(values,"port",https && http ? 443 : 8080);
        httpPort=number(values,"httpPort",8080);
        if(port<0 || port>65535 || httpPort<0 || httpPort>65535) throw new IllegalArgumentException("Ports must be between 0 and 65535");
        if(https && http && port!=0 && port==httpPort) throw new IllegalArgumentException("HTTPS and HTTP ports must differ");
        verbose=environment.containsKey("GG_VERBOSE")?environment.get("GG_VERBOSE").equals("1"):flag(values,"verbose",true);
        Map<String,Object> logging=section(values,"logging");
        logLevel=env(environment,"GG_LOG_LEVEL",text(logging,"level","INFO")).toUpperCase(Locale.ROOT);
        if(!Set.of("TRACE","DEBUG","INFO","WARN","ERROR","OFF").contains(logLevel)) throw new IllegalArgumentException("Invalid logging.level");
        logFile=flag(logging,"file",true);
        publicBase=env(environment,"GG_PUBLIC_BASE",env(environment,"GG_PUBLIC_HOST",text(values,"publicBase","")));
        cdnUrl=env(environment,"GG_CDN_URL",text(values,"cdnUrl",""));
        adminPassword=env(environment,"GG_ADMIN_PASSWORD",text(values,"adminPassword",""));
        secretKey=env(environment,"GG_SECRET_KEY",text(values,"secretKey",""));
        certificatePassword=env(environment,"GG_CERT_PASSWORD",text(values,"certificatePassword","changeit"));
        String cert=text(values,"certificate",""); certificate=cert.isBlank()?null:resolve(base,cert);
        Map<String,Object> database=section(values,"database"), sessions=section(values,"sessions");
        databaseBackend=text(database,"backend","sqlite").toLowerCase(Locale.ROOT);
        if(!Set.of("sqlite","mongo","mongodb").contains(databaseBackend)) throw new IllegalArgumentException("database.backend must be sqlite or mongo");
        mongoUri=env(environment,"GG_MONGO_URI",text(database,"uri","mongodb://127.0.0.1:27017"));
        mongoDatabase=env(environment,"GG_MONGO_DATABASE",text(database,"name","ggserver"));
        if(mongoUri.isBlank() || mongoDatabase.isBlank() || mongoDatabase.matches(".*[ /\\\\.\"$].*")) throw new IllegalArgumentException("Invalid MongoDB URI/database name");
        sessionTimeoutSeconds=positive(sessions,"timeoutSeconds",86400);
        sessionCleanupSeconds=positive(sessions,"cleanupSeconds",60);
        maxSessions=positive(sessions,"maxSessions",10000);
        sessionRequired=flag(sessions,"required",false);
        Map<String,Object> configured=map(values.get("folders"));
        if(values.containsKey("folders") && !(values.get("folders") instanceof Map)) throw new IllegalArgumentException("folders must be an object");
        Map<String,Path> paths=new LinkedHashMap<>();
        for(String name:List.of("data","cdn","gamedata","schema","static","captures","apk","logs")) {
            String fallback=switch(name) {case "cdn" -> "cdn_files";case "apk" -> "out";default -> name;};
            String path=text(configured,name,fallback);
            if(path.isBlank()) throw new IllegalArgumentException("folders."+name+" must not be blank");
            paths.put(name,resolve(root,path));
        }
        folders=Map.copyOf(paths);
    }
    public Path folder(String name) { Path path=folders.get(name); if(path==null) throw new IllegalArgumentException("Unknown folder: "+name); return path; }
    public Path database() { return folder("data").resolve("database.db"); }
    public Path resource(String relative) {
        int slash=relative.indexOf('/');
        if(slash>0) { String prefix=relative.substring(0,slash); if(prefix.equals("cdn_files")) prefix="cdn"; if(folders.containsKey(prefix)) return folder(prefix).resolve(relative.substring(slash+1)); }
        return root.resolve(relative);
    }
    public static ServerConfig defaults(Path root) { return new ServerConfig(root.toAbsolutePath().normalize(),obj(),System.getenv()); }
    public static ServerConfig load(Path file) { return load(file,Map.of(),System.getenv()); }
    public static ServerConfig load(Path file,Map<String,Object> overrides,Map<String,String> env) {
        Object parsed=read(file);
        if(!(parsed instanceof Map)) throw new IllegalArgumentException("Server config must be a JSON object: "+file);
        Map<String,Object> values=new LinkedHashMap<>(map(parsed)); values.putAll(overrides);
        return new ServerConfig(file.toAbsolutePath().normalize().getParent(),values,env);
    }
    public static ServerConfig defaults(Path root,Map<String,Object> overrides) { return new ServerConfig(root.toAbsolutePath().normalize(),overrides,System.getenv()); }
    private static Path resolve(Path base,String value) { return base.resolve(value).toAbsolutePath().normalize(); }
    private static Map<String,Object> section(Map<String,Object> values,String key) {
        if(values.containsKey(key) && !(values.get(key) instanceof Map)) throw new IllegalArgumentException(key+" must be an object");
        return map(values.get(key));
    }
    private static int positive(Map<String,Object> values,String key,int fallback) {
        int value=number(values,key,fallback);
        if(value<=0) throw new IllegalArgumentException(key+" must be positive");
        return value;
    }
    private static String text(Map<String,Object> values,String key,String fallback) {
        if(!values.containsKey(key)) return fallback;
        if(!(values.get(key) instanceof String s)) throw new IllegalArgumentException(key+" must be a string");
        return s;
    }
    private static boolean flag(Map<String,Object> values,String key,boolean fallback) {
        if(!values.containsKey(key)) return fallback;
        if(!(values.get(key) instanceof Boolean b)) throw new IllegalArgumentException(key+" must be a boolean");
        return b;
    }
    private static int number(Map<String,Object> values,String key,int fallback) {
        if(!values.containsKey(key)) return fallback;
        if(!(values.get(key) instanceof Number n) || n.doubleValue()!=n.intValue()) throw new IllegalArgumentException(key+" must be an integer");
        return n.intValue();
    }
    private static String env(Map<String,String> env,String key,String fallback) { String v=env.get(key); return v==null||v.isEmpty()?fallback:v; }
}

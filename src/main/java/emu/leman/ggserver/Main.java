package emu.leman.ggserver;

import emu.leman.ggserver.game.GameContext;
import emu.leman.ggserver.server.*;
import java.nio.file.*;
import java.util.concurrent.CountDownLatch;
import javax.net.ssl.SSLContext;
import emu.leman.ggserver.config.ServerConfig;
import java.util.*;
import emu.leman.ggserver.util.Logging;
import org.slf4j.LoggerFactory;

/** Java-only standalone entry point with configuration-file resource paths. */
public final class Main {
    private Main() {}
    public static void main(String[] args) throws Exception {
        Path defaultRoot=defaultRoot(),configFile=null;
        Map<String,Object> overrides=new LinkedHashMap<>();
        for(int i=0;i<args.length;i++) switch(args[i]) {
            case "--config" -> configFile=Path.of(value(args,++i,"--config"));
            case "--host" -> overrides.put("host",value(args,++i,"--host"));
            case "--port" -> overrides.put("port",Integer.parseInt(value(args,++i,"--port")));
            case "--root" -> overrides.put("root",Path.of(value(args,++i,"--root")).toAbsolutePath().normalize().toString());
            case "--cert" -> overrides.put("certificate",Path.of(value(args,++i,"--cert")).toAbsolutePath().normalize().toString());
            case "--https" -> overrides.put("https",true);
            case "--http" -> overrides.put("http",true);
            case "--help","-h" -> { System.out.println("Usage: java -jar ggserver.jar\nLoads resources/server-config.json automatically. Configure host, port, HTTPS and folders there.\nOptional: --config FILE. Legacy --host/--port/--root/--cert/--https/--http override file values.\nRelative paths resolve from the config directory (folders from root). Environment secrets/URLs override file values.");return; }
            default -> throw new IllegalArgumentException("Unknown option: "+args[i]);
        }
        if(configFile==null) {
            String configured=System.getenv("GG_CONFIG");
            if(configured!=null&&!configured.isBlank()) configFile=Path.of(configured);
            else if(Files.isRegularFile(defaultRoot.resolve("server-config.json"))) configFile=defaultRoot.resolve("server-config.json");
        }
        ServerConfig config=configFile==null?ServerConfig.defaults(defaultRoot,overrides):ServerConfig.load(configFile,overrides,System.getenv());
        Logging.configure(config);
        var log=LoggerFactory.getLogger(Main.class);
        log.info("Starting GGServer {}",Optional.ofNullable(Main.class.getPackage().getImplementationVersion()).orElse("dev"));
        Services services=new Services(config);
        log.info("Database ready: {}",config.databaseBackend);
        new GameContext(services).registerModules();
        log.info("Registered {} game handlers",services.registry.commands().size());
        GameServer server=new GameServer(services);
        Runtime.getRuntime().addShutdownHook(new Thread(()->{ log.info("Stopping GGServer");server.close();services.close();log.info("GGServer stopped"); },"ggserver-shutdown"));
        SSLContext tls=config.https?Tls.load(config.certificate==null?Tls.ensureCertificate(config.folder("data"),config.certificatePassword):config.certificate,config.certificatePassword):null;
        var bound=server.start(config.host,config.port,tls);
        log.info("Listening {}://{}:{}",config.https?"https":"http",config.host,bound.getAddress().getPort());
        log.debug("Resources: {} | Config: {}",config.root,configFile);
        if(config.https && config.http) { var plain=server.start(config.host,config.httpPort,null);log.info("Listening http://{}:{}",config.host,plain.getAddress().getPort()); }
        new CountDownLatch(1).await();
    }
    private static String value(String[] args,int i,String option) { if(i>=args.length) throw new IllegalArgumentException("Missing value for "+option);return args[i]; }
    public static Path defaultRoot() {
        String configured=System.getenv("GG_ROOT");if(configured!=null && !configured.isBlank()) return runtimeRoot(Path.of(configured));
        Path cwd=Path.of("").toAbsolutePath().normalize();
        if(hasResources(runtimeRoot(cwd))) return runtimeRoot(cwd);
        Path project=runtimeRoot(cwd.resolve("GGServerJava"));
        if(hasResources(project)) return project;
        try {
            Path location=Path.of(Main.class.getProtectionDomain().getCodeSource().getLocation().toURI());
            for(Path p=Files.isDirectory(location)?location:location.getParent();p!=null;p=p.getParent())
                if(hasResources(runtimeRoot(p))) return runtimeRoot(p);
        } catch(Exception ignored) { }
        return cwd;
    }
    /** Prefer the consolidated layout, while accepting an explicit legacy runtime root. */
    public static Path runtimeRoot(Path base) {
        base=base.toAbsolutePath().normalize();
        Path resources=base.resolve("resources");
        return hasResources(resources)?resources:base;
    }
    private static boolean hasResources(Path path) {
        return Files.isRegularFile(path.resolve("server-config.json")) || Files.isRegularFile(path.resolve("schema/schema.json"));
    }
}

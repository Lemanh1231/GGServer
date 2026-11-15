package emu.leman.ggserver.server;

import com.sun.net.httpserver.*;
import emu.leman.ggserver.Services;
import emu.leman.ggserver.server.admin.AdminServer;
import emu.leman.ggserver.game.account.AuthApi;
import emu.leman.ggserver.net.codec.Codec;
import emu.leman.ggserver.net.Result;
import emu.leman.ggserver.net.GamePacket;
import java.io.*;
import java.net.*;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import javax.net.ssl.SSLContext;
import static emu.leman.ggserver.util.Json.*;
import static emu.leman.ggserver.util.Logging.safe;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Single-port game RPC, NeonAPI, CDN, downloads and delegated admin transport. */
public final class GameServer implements HttpHandler,AutoCloseable {
    private static final Logger log=LoggerFactory.getLogger(GameServer.class);
    private final Services services;
    private final Codec codec;
    private final Dispatch dispatch;
    private final AuthApi auth;
    private final AdminServer admin;
    private final AtomicLong sequence=new AtomicLong();
    private final Object[] accountLocks=new Object[1024];
    private final List<HttpServer> servers=new ArrayList<>();
    private final ExecutorService executor=Executors.newVirtualThreadPerTaskExecutor();
    private final String publicBase;
    private final String cdnUrl;
    private final boolean verbose;
    private static final Set<String> BOOTSTRAP=emu.leman.ggserver.net.CmdId.BOOTSTRAP;
    public GameServer(Services services) {
        this.services=services;codec=new Codec(services.config);dispatch=new Dispatch(codec);auth=new AuthApi(services);admin=new AdminServer(services);
        publicBase=services.config.publicBase;cdnUrl=services.config.cdnUrl;verbose=services.config.verbose;
        Arrays.setAll(accountLocks,i->new Object());
    }
    private static String env(String key,String fallback) { String v=System.getenv(key);return v==null || v.isEmpty()?fallback:v; }
    public HttpServer start(String host,int port,SSLContext tls) throws IOException {
        HttpServer server;
        if(tls==null) server=HttpServer.create(new InetSocketAddress(host,port),128);
        else { HttpsServer secure=HttpsServer.create(new InetSocketAddress(host,port),128);secure.setHttpsConfigurator(new HttpsConfigurator(tls));server=secure; }
        server.createContext("/",this);server.setExecutor(executor);server.start();servers.add(server);return server;
    }
    @Override public void close() { for(HttpServer server:servers) server.stop(1); executor.close(); }
    private static String header(HttpExchange e,String name) { return Optional.ofNullable(e.getRequestHeaders().getFirst(name)).orElse("").trim(); }
    public static String clientIp(HttpExchange e) {
        for(String name:List.of("CF-Connecting-IP","X-Forwarded-For","X-Real-IP")) { String v=header(e,name);if(!v.isEmpty()) return v.split(",",2)[0].trim(); }
        return e.getRemoteAddress()==null?"127.0.0.1":e.getRemoteAddress().getAddress().getHostAddress();
    }
    private static String hostOnly(String host) {
        if(host.startsWith("[")) { int end=host.indexOf(']');return end>0?host.substring(1,end):host; }
        return host.split(":",2)[0].trim().toLowerCase(Locale.ROOT);
    }
    public static String requestDomain(HttpExchange e) {
        String host=hostOnly(header(e,"Host")); if(host.startsWith("www.")) host=host.substring(4);
        if(host.isEmpty() || Set.of("127.0.0.1","localhost","::1").contains(host)) {
            String active=header(e,"X-GG-Active-Domain").toLowerCase(Locale.ROOT);
            if(active.contains("://")) active=active.substring(active.indexOf("://")+3);
            active=hostOnly(active.split("/",2)[0]); if(active.startsWith("www.")) active=active.substring(4);
            if(!active.isEmpty()) return active;
        }
        return host.isEmpty()?"local":host;
    }
    public String baseUrl(HttpExchange e) {
        String local=header(e,"X-GG-Local-Proxy").replaceAll("/+$","");
        if(local.startsWith("http://127.0.0.1:")) try { int port=Integer.parseInt(local.substring(17));if(port>=1024 && port<=65535) return local; } catch(Exception ignored) { }
        String raw=header(e,"Host"),host=hostOnly(raw),forwarded=header(e,"X-Forwarded-Proto").split(",",2)[0].trim().toLowerCase(Locale.ROOT);
        if(!host.isEmpty() && !host.matches("[0-9.]+") && !Set.of("localhost","::1").contains(host)) {
            String scheme=!forwarded.isEmpty()?forwarded:e instanceof HttpsExchange || host.contains(".")?"https":"http";
            return scheme+"://"+raw;
        }
        if(!publicBase.isEmpty()) return publicBase.contains("://")?publicBase:"http://"+publicBase;
        return (!forwarded.isEmpty()?forwarded:e instanceof HttpsExchange?"https":"http")+"://"+(raw.isEmpty()?"localhost":raw);
    }
    @Override public void handle(HttpExchange e) throws IOException {
        try {
            String method=e.getRequestMethod(),path=e.getRequestURI().getPath();
            if(!Set.of("GET","HEAD","POST","OPTIONS").contains(method)) { send(e,"",method.equals("CONNECT")?400:501);return; }
            if(method.equals("OPTIONS")) {
                e.getResponseHeaders().set("Access-Control-Allow-Methods","GET, POST, OPTIONS, HEAD");e.getResponseHeaders().set("Access-Control-Allow-Headers","*");send(e,"",200);return;
            }
            if(path.equals("/") || path.equals("/health")) { send(e,"GG emulator OK",200);return; }
            if(path.startsWith("/admin") && admin.handle(e)) return;
            if(method.equals("GET") || method.equals("HEAD")) { get(e,path); return; }
            if(method.equals("POST")) { post(e,path); return; }
            send(e,"",method.equals("CONNECT")?400:501);
        } catch(Exception ex) {
            log.error("HTTP {} {} failed",safe(e.getRequestMethod()),safe(e.getRequestURI().getPath()),ex);
            capture(e,"ERROR",obj("path",e.getRequestURI().toString(),"error",ex.toString()),false);
            try { send(e,"",500); } catch(IOException ignored) { e.close(); }
        }
    }
    private void send(HttpExchange e,String body,int status) throws IOException { HttpSupport.send(e,body,status,"text/plain; charset=utf-8"); }
    private boolean authPath(String path,boolean post) {
        return path.startsWith("/api/") || path.startsWith("/accounts/") || path.startsWith("/app/") ||
                (post?(path.startsWith("/referrer/") || path.startsWith("/gcm/")):path.startsWith("/eula/"));
    }
    private void get(HttpExchange e,String path) throws IOException {
        if(Set.of("/download","/download/","/tai-game","/tai-game/").contains(path)) { HttpSupport.send(e,Download.getDownloadHtml(),200,"text/html; charset=utf-8");return; }
        if(authPath(path,false)) { AuthApi.Response response=auth.handle(path,obj());if(response!=null) { HttpSupport.send(e,response.body(),200,response.contentType());return; } }
        String filename=null;
        if(Set.of("/download/apk","/download/"+Download.APK_FILENAME,"/"+Download.APK_FILENAME,"/apk").contains(path)) filename=Download.APK_FILENAME;
        else if(path.startsWith("/download/") || path.endsWith(".apk")) { String last=lastName(path);if(last.endsWith(".apk")) filename=last; }
        if(filename!=null) {
            Path file=services.config.folder("apk").resolve(filename);
            if(!Files.isRegularFile(file) && services.root.getParent()!=null) {
                Path legacy=services.root.getParent().resolve("out").resolve(filename);
                if(Files.isRegularFile(legacy)) file=legacy;
            }
            HttpSupport.sendFile(e,file,filename,"application/vnd.android.package-archive");return;
        }
        if(path.startsWith("/AssetBundles/")) {
            Path file=services.config.folder("cdn").resolve(lastName(path)).normalize();
            if(file.startsWith(services.config.folder("cdn")) && Files.isRegularFile(file)) { HttpSupport.sendFile(e,file,null,"application/octet-stream");return; }
        }
        HttpSupport.send(e,new byte[0],404,"application/octet-stream");
    }
    private static String lastName(String path) { int slash=path.lastIndexOf('/');String name=path.substring(slash+1);return name.equals(".") || name.equals("..")?"":name; }
    private void post(HttpExchange e,String path) throws Exception {
        Map<String,Object> form=Multipart.parse(header(e,"Content-Type"),HttpSupport.readBody(e));
        String ip=clientIp(e),domain=requestDomain(e);
        if(path.equals("/api/accounts/v3/global/game-session")) {
            // Adapter issues a normal server session; protected RPC validation is unchanged.
            var result=GameSessionLogin.login(services,codec,form,ip,this::lockFor);
            capture(e,"auth_game_session",obj("path",path,"result_code",result.response().get("result_code"),"identity_check",result.reason()),false);
            HttpSupport.send(e,bytes(result.response()),200,"application/json; charset=utf-8");return;
        }
        if(authPath(path,true)) {
            // Account creation in NeonAPI must share the serialization discipline with RPCs.
            String device=str(form.get("device_cd"));
            synchronized(lockFor(device)) {
                AuthApi.Response response=auth.handle(path,form,ip);
                if(response!=null) {
                    if(!device.isEmpty()) services.state.updateUserIp(device,ip,domain);
                    Map<String,Object> summary=obj();form.forEach((k,v)->summary.put(k,k.toLowerCase(Locale.ROOT).contains("token")?"<redacted>":str(v).substring(0,Math.min(120,str(v).length()))));
                    capture(e,"auth"+path.replace('/','_'),obj("path",path,"form",summary),!device.isEmpty() && services.state.isUserBanned(device));
                    HttpSupport.send(e,response.body(),200,response.contentType());return;
                }
            }
        }
        String call=str(form.get("call")),command=dispatch.resolveCommand(form);
        Dispatch.Message message=Dispatch.findMessageField(form);Map<String,Object> request=null;
        if(message.body()!=null) try { request=codec.decodeRequest(message.body(),command).named(); } catch(Exception ex) { request=obj("_decode_error",ex.toString()); }
        Map<String,Object> payload=map(request==null?null:request.get("data"));
        String uuid=str(first(payload.get("device_uuid"),payload.get("uuid")));
        String identity=str(first(payload.get("device_uuid"),payload.get("uuid"),payload.get("u_seq")));
        // HandlerRegistry owns the canonical-account lock for the full handler operation.
        rpc(e,path,form,call,command,request,uuid,identity,ip,domain);
    }
    private Object lockFor(String identity) {
        String canonical=identity;
        if(!identity.isEmpty()) {
            var user=services.state.getUser(identity);
            if(user!=null && !user.isEmpty()) canonical=str(first(user.get("uuid"),map(user.get("userdata")).get("u_seq"),identity));
        }
        return accountLocks[(canonical.hashCode()&Integer.MAX_VALUE)%accountLocks.length];
    }
    private void rpc(HttpExchange e,String path,Map<String,Object> form,String call,String command,Map<String,Object> request,
                     String uuid,String identity,String ip,String domain) throws Exception {
        long started=System.nanoTime();
        String category=Arrays.stream(path.split("/")).filter(s->!s.isEmpty()).findFirst().orElse("");
        Map<String,Object> summary=obj();form.forEach((k,v)->summary.put(k,k.toLowerCase(Locale.ROOT).contains("token")?"<redacted>":v instanceof String s && s.length()<120?s:"<"+(v instanceof byte[] b?b.length:str(v).length())+">"));
        Map<String,Object> cap=obj("path",path,"call",call.isEmpty()?null:call,"command",command,"category",category,"form_fields",summary,"request_decoded",request);
        boolean banned=!identity.isEmpty() && services.state.isUserBanned(identity);
        if(command==null) { if(call.isEmpty() && form.isEmpty()) send(e,"GG emulator OK",200);else { log.warn("Unresolved RPC: {}",safe(path));capture(e,"UNRESOLVED",cap,banned);send(e,"",200); }return; }
        String simple=str(codec.schemaFor(command).get("name")),base=baseUrl(e);
        if(verbose) log.debug("RECV: {} | {}",simple,safe(ip));
        Map<String,Object> ctx=obj("game_url",base,"cdn_url",cdnUrl.isEmpty()?base:cdnUrl,"uuid",uuid.isEmpty()?null:uuid,"client_ip",ip,"domain",domain);
        String authorization=header(e,"Authorization");
        String token=str(first(form.get("access_token"),form.get("session_token"),authorization.startsWith("Bearer ")?authorization.substring(7):null));
        SessionAccess.Decision session=SessionAccess.validate(services,token,request,BOOTSTRAP.contains(command));
        boolean invalidMessage=(request!=null && request.containsKey("_decode_error"))
                || (!BOOTSTRAP.contains(command) && (request==null || !(request.get("data") instanceof Map)));
        if(session.error()!=null) cap.put("session_diagnostics",SessionAccess.diagnostics(token,header(e,"Content-Type")));
        if(session.uuid()!=null) ctx.put("uuid",session.uuid());
        if(session.error()==null && !invalidMessage && !BOOTSTRAP.contains(command)) {
            String account=session.uuid()==null?identity:session.uuid();
            if(!account.isEmpty()) services.state.updateUserIp(account,ip,domain);
            banned=!account.isEmpty() && services.state.isUserBanned(account);
        }
        Result result;
        if(session.error()!=null) result=Result.error(401,session.error());
        else if(invalidMessage)
            result=Result.error(400,"Missing or invalid RPC message");
        else if(banned && !BOOTSTRAP.contains(command)) {
            result=Result.error(900,"Tài khoản của bạn đã bị KHÓA (BAN) bởi Quản trị viên!\nVui lòng liên hệ Admin để được hỗ trợ.");
            cap.put("blocked",true);cap.put("error",result.error());
        } else {
            GamePacket packet=new GamePacket(simple,request==null?obj():request,ctx);
            result=services.registry.handle(packet.command(),packet.request(),packet.context());
        }
        Map<String,Object> error=result.error();
        if(!banned && error!=null && lng(error.get("code"))!=0 && truth(error.get("errmsg")) && !identity.isEmpty()) {
            var user=services.state.getUser(identity);Object seq=map(user==null?null:user.get("userdata")).get("u_seq");
            if(truth(seq) && !str(error.get("errmsg")).contains(str(seq))) { error=new LinkedHashMap<>(error);error.put("errmsg",error.get("errmsg")+"\n[UID Database: "+seq+"]"); }
        }
        Dispatch.Envelope envelope=dispatch.buildReturn(command,result.data(),simple,category,error);
        if(envelope.dto()==null) { log.warn("No response DTO: {}",simple);cap.put("error","no Return DTO");capture(e,"NORETURN",cap,banned);send(e,"",banned?403:200);return; }
        String encoded=codec.encodeResponse(envelope.dto(),envelope.data());
        cap.put("response_dto",envelope.dto());cap.put("response",envelope.data());capture(e,Boolean.TRUE.equals(cap.get("blocked"))?"BLOCKED_"+simple:simple,cap,banned);
        long code=error==null?0:lng(error.get("code"));
        if(code!=0) log.warn("SEND: {} | code={} | {} B | {} ms",simple,code,encoded.length(),TimeUnit.NANOSECONDS.toMillis(System.nanoTime()-started));
        else if(verbose) log.info("SEND: {} | {} B | {} ms",simple,encoded.length(),TimeUnit.NANOSECONDS.toMillis(System.nanoTime()-started));
        send(e,encoded,200);
    }
    private void capture(HttpExchange e,String tag,Map<String,Object> data,boolean banned) {
        try {
            Map<String,Object> merged=obj("timestamp",emu.leman.ggserver.util.GameTime.timestamp(),
                    "domain",requestDomain(e),"host_header",header(e,"Host"),"active_domain_header",first(header(e,"X-GG-Active-Domain"),null),
                    "via_failover_apk",!header(e,"X-GG-Local-Proxy").isEmpty(),"client_ip",clientIp(e));merged.putAll(data);
            String safeTag=tag.replaceAll("[^a-zA-Z0-9_.-]","_");
            Path dir=services.config.folder("captures");if(banned) dir=dir.resolve("banned");Files.createDirectories(dir);
            Path file=dir.resolve(String.format("%d_%04d_%s.json",Instant.now().getEpochSecond(),sequence.incrementAndGet(),safeTag));
            Files.writeString(file,emu.leman.ggserver.util.Json.MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(merged),StandardOpenOption.CREATE_NEW);
        } catch(Exception ignored) { }
    }
}

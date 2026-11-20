package emu.leman.ggserver.server;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.codec.Codec;
import emu.leman.ggserver.net.Result;
import java.io.*;
import java.net.*;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.zip.GZIPOutputStream;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class TransportTest {
    @TempDir Path root;
    Services services;GameServer server;String base;Codec codec;
    final HttpClient client=HttpClient.newHttpClient();
    @BeforeEach void start() throws Exception {
        root=Files.createDirectories(root.resolve("server"));
        for(String folder:List.of("schema","gamedata","static","cdn_files")) {
            Path source=Path.of("resources",folder);try(var paths=Files.walk(source)) {
                for(Path file:paths.toList()) { Path target=root.resolve(source.relativize(file).toString().isEmpty()?folder:folder+"/"+source.relativize(file));
                    if(Files.isDirectory(file)) Files.createDirectories(target);else Files.copy(file,target); }
            }
        }
        services=new Services(root);codec=new Codec(root);
        services.registry.register("getServerTime",(req,ctx)->Result.ok(Dispatch.nowTimes()));
        services.registry.register("userLoad",(req,ctx)->Result.ok(obj()));
        services.registry.register("Request",(req,ctx)->Result.ok(obj("game_url",ctx.get("game_url"),"cdn_url",ctx.get("cdn_url"))));
        server=new GameServer(services);base="http://127.0.0.1:"+server.start("127.0.0.1",0,null).getAddress().getPort();
    }
    @AfterEach void stop() { if(server!=null) server.close();if(services!=null) services.close(); }
    HttpResponse<byte[]> request(String path,String method,byte[] body,Map<String,String> headers) throws Exception {
        var builder=HttpRequest.newBuilder(URI.create(base+path)).method(method,HttpRequest.BodyPublishers.ofByteArray(body));headers.forEach(builder::header);
        return client.send(builder.build(),HttpResponse.BodyHandlers.ofByteArray());
    }
    @Test void healthCorsHeadAndCdn() throws Exception {
        var health=request("/health","GET",new byte[0],Map.of());assertEquals("GG emulator OK",new String(health.body(),StandardCharsets.UTF_8));
        var options=request("/anything","OPTIONS",new byte[0],Map.of());assertEquals("*",options.headers().firstValue("Access-Control-Allow-Origin").orElseThrow());
        String path="/AssetBundles/Android/Android";var get=request(path,"GET",new byte[0],Map.of());var head=request(path,"HEAD",new byte[0],Map.of());
        assertEquals(200,get.statusCode());assertEquals(200,head.statusCode());assertEquals(0,head.body().length);
        assertEquals(String.valueOf(get.body().length),head.headers().firstValue("Content-Length").orElseThrow());
        assertArrayEquals(Files.readAllBytes(root.resolve("cdn_files/Android")),get.body());
        assertEquals(404,request("/AssetBundles/../schema.json","GET",new byte[0],Map.of()).statusCode());
    }
    @Test void browserHealthIsHtmlAndMonitoringRemainsText() throws Exception {
        var response=request("/health","GET",new byte[0],Map.of("Accept","text/html"));
        assertEquals(200,response.statusCode());
        assertTrue(response.headers().firstValue("Content-Type").orElseThrow().startsWith("text/html"));
        assertTrue(new String(response.body(),StandardCharsets.UTF_8).contains("Máy chủ đang phản hồi"));
        assertEquals("Accept",response.headers().firstValue("Vary").orElseThrow());
        var head=request("/health","HEAD",new byte[0],Map.of("Accept","text/html"));
        assertEquals(200,head.statusCode());assertEquals(0,head.body().length);
        assertEquals("GG emulator OK",new String(request("/health","GET",new byte[0],Map.of()).body(),StandardCharsets.UTF_8));
    }
    @Test void gzipPostAndCapture() throws Exception {
        String payload=codec.encodeResponse("main.getServerTime",obj("call","getServerTime","data",obj()));
        byte[] body=("call=getServerTime&tapsonic_data="+URLEncoder.encode(payload,StandardCharsets.UTF_8)).getBytes(StandardCharsets.UTF_8);
        var zipped=new ByteArrayOutputStream();try(var gzip=new GZIPOutputStream(zipped)) { gzip.write(body); }
        var response=request("/main/getServerTime/en/","POST",zipped.toByteArray(),Map.of("Content-Type","application/x-www-form-urlencoded","Content-Encoding","gzip","X-Forwarded-For","203.0.113.5, 10.0.0.1","X-GG-Active-Domain","https://www.game.example/path"));
        assertEquals(200,response.statusCode());var decoded=codec.decodeRequest(new String(response.body(),StandardCharsets.UTF_8),"main.getServerTimeReturn").named();
        assertEquals(0,lng(map(decoded.get("error")).get("code")));assertTrue(lng(map(decoded.get("server_time")).get("time"))>0);
        try(var captures=Files.list(root.resolve("captures"))) { var capture=map(read(captures.filter(Files::isRegularFile).findFirst().orElseThrow()));assertEquals("203.0.113.5",capture.get("client_ip"));assertEquals("game.example",capture.get("domain")); }
    }
    @Test void bootstrapWithoutMessageDoesNotDecodeRoutingOrCredentialsAsBody() throws Exception {
        var message=Dispatch.findMessageField(obj("call","getServerTime","access_token","opaque-old-sdk-token","session_token","expired-session-token"));
        assertNull(message.body());
        String body="call=getServerTime&access_token=opaque-old-sdk-token";
        var response=request("/main/getServerTime/en/","POST",body.getBytes(StandardCharsets.UTF_8),Map.of("Content-Type","application/x-www-form-urlencoded"));
        var decoded=codec.decodeRequest(new String(response.body(),StandardCharsets.UTF_8),"main.getServerTimeReturn").named();
        assertEquals(0,integer(map(decoded.get("error")).get("code")));
        assertTrue(lng(map(decoded.get("data")).get("time"))>0);
        String nativeMessage=codec.encodeResponse("main.getServerTime",obj("data",obj()));
        assertEquals(nativeMessage,Dispatch.findMessageField(obj("call","getServerTime","legacy_message",nativeMessage)).body());
    }
    @Test void bannedAccountGetsNativeEnvelopeAndBootstrapStillWorks() throws Exception {
        services.state.createUser("banned-test","banned-device","");assertTrue(services.state.banUser("banned-test",true));
        var dispatch=new Dispatch(codec);String command=dispatch.resolveCommand(obj("call","userLoad"));
        String payload=codec.encodeResponse(command,obj("call","userLoad","data",obj("uuid","banned-test")));
        var response=request("/main/userLoad/en/","POST",("call=userLoad&tapsonic_data="+URLEncoder.encode(payload,StandardCharsets.UTF_8)).getBytes(StandardCharsets.UTF_8),Map.of());
        assertEquals(200,response.statusCode());var env=codec.decodeRequest(new String(response.body(),StandardCharsets.UTF_8),dispatch.returnDtoFor(command)).named();
        assertEquals(900,lng(map(env.get("error")).get("code")));assertFalse(env.containsKey("data"));
        String bootstrap=codec.encodeResponse("main.Request",obj("call","Request","data",obj()));
        var init=request("/main/Request/en/","POST",("call=Request&tapsonic_data="+URLEncoder.encode(bootstrap,StandardCharsets.UTF_8)).getBytes(StandardCharsets.UTF_8),Map.of("X-GG-Local-Proxy","http://127.0.0.1:4567/"));
        var initEnv=codec.decodeRequest(new String(init.body(),StandardCharsets.UTF_8),"main.initReturn").named();
        assertEquals(0,lng(map(initEnv.get("error")).get("code")));assertEquals("http://127.0.0.1:4567",map(initEnv.get("data")).get("game_url"));
    }
    @Test void neonLoginAndDownloadAliases() throws Exception {
        var response=request("/api/accounts/v3/global/login","POST","device_cd=neon-device&app_id=123".getBytes(StandardCharsets.UTF_8),Map.of("Content-Type","application/x-www-form-urlencoded"));
        var json=map(parse(new String(response.body(),StandardCharsets.UTF_8)));assertEquals("000",json.get("result_code"));
        assertTrue(str(map(json.get("value")).get("access_token")).contains("|123|neon-device|KR|"));
        assertEquals(200,request("/tai-game","GET",new byte[0],Map.of()).statusCode());
        Files.createDirectories(root.resolve("out"));Files.write(root.resolve("out/"+Download.APK_FILENAME),new byte[]{1,2,3});
        var apk=request("/apk","HEAD",new byte[0],Map.of());assertEquals("3",apk.headers().firstValue("Content-Length").orElseThrow());assertEquals(0,apk.body().length);
    }
    @Test void opaqueProviderCredentialGetsNormalGuestSessionButCannotClaimOtherAliases() throws Exception {
        String device="0123456789abcdef0123456789abcdef";
        services.state.createUser(device,device,"");
        services.state.createUser("victim","fedcba9876543210fedcba9876543210","");
        services.registry.register("userLogin",(req,ctx)->Result.ok(obj("user",map(services.state.getUser(device).get("userdata")))));
        var dispatch=new Dispatch(codec);String command="user.userLogin";
        String payload=codec.encodeResponse(command,obj("call","userLogin","data",obj("uuid",device,"device_uuid",device,"u_seq",0)));
        String body="call=userLogin&access_token=opaque-provider-credential&tapsonic_data="+URLEncoder.encode(payload,StandardCharsets.UTF_8);
        var headers=Map.of("Content-Type","application/x-www-form-urlencoded");
        var exchange=request("/api/accounts/v3/global/game-session","POST",body.getBytes(StandardCharsets.UTF_8),headers);
        var result=map(parse(new String(exchange.body(),StandardCharsets.UTF_8)));
        assertEquals("000",result.get("result_code"));
        String token=str(map(result.get("value")).get("access_token"));
        assertNotNull(services.sessions.find(token));
        String loginBody=body.replace("access_token=opaque-provider-credential","access_token="+URLEncoder.encode(token,StandardCharsets.UTF_8));
        var response=request("/user/userLogin/vi/","POST",loginBody.getBytes(StandardCharsets.UTF_8),headers);
        var env=codec.decodeRequest(new String(response.body(),StandardCharsets.UTF_8),dispatch.returnDtoFor(command)).named();
        assertEquals(0,lng(map(env.get("error")).get("code")));
        assertTrue(lng(map(map(env.get("data")).get("user")).get("u_seq"))>0);
        for(var data:List.of(obj("uuid","victim","device_uuid",device),obj("uuid",device,"device_uuid",device,"u_seq",999999),
                obj("uuid",device,"device_uuid",device,"u_id","victim"),obj("uuid",device,"device_uuid","bad-device"))) {
            String bad=codec.encodeResponse(command,obj("call","userLogin","data",data));
            var rejected=request("/api/accounts/v3/global/game-session","POST",("call=userLogin&tapsonic_data="+URLEncoder.encode(bad,StandardCharsets.UTF_8)).getBytes(StandardCharsets.UTF_8),headers);
            var json=map(parse(new String(rejected.body(),StandardCharsets.UTF_8)));
            assertEquals("401",json.get("result_code"));assertNull(json.get("value"));
        }
        var rejected=request("/user/userLogin/vi/","POST",body.getBytes(StandardCharsets.UTF_8),headers);
        assertEquals(401,lng(map(codec.decodeRequest(new String(rejected.body(),StandardCharsets.UTF_8),dispatch.returnDtoFor(command)).named().get("error")).get("code")));
        services.state.banUser(device);
        int sessions=services.sessions.sessionCount();
        var banned=request("/api/accounts/v3/global/game-session","POST",body.getBytes(StandardCharsets.UTF_8),headers);
        assertEquals("401",map(parse(new String(banned.body(),StandardCharsets.UTF_8))).get("result_code"));
        assertEquals(sessions,services.sessions.sessionCount());
        var malformed=request("/api/accounts/v3/global/game-session","POST","call=userLogin&tapsonic_data=not-a-valid-message".getBytes(StandardCharsets.UTF_8),headers);
        assertEquals("401",map(parse(new String(malformed.body(),StandardCharsets.UTF_8))).get("result_code"));
        try(var files=Files.list(root.resolve("captures"))) {
            for(Path file:files.toList()) assertFalse(Files.readString(file).contains(token));
        }
    }
    @Test void gameSessionPreservesMigratedIdentityAndRejectsCanonicalAliasAsDevice() throws Exception {
        String canonical="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",device="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
        var user=services.state.createUser(canonical,device,"");
        long seq=lng(map(user.get("userdata")).get("u_seq"));
        String command="user.userLogin";
        for(String sentDevice:List.of(device,canonical)) {
            String payload=codec.encodeResponse(command,obj("call","userLogin","data",
                    obj("uuid",canonical,"device_uuid",sentDevice,"u_seq",seq,"u_id",str(seq))));
            var response=request("/api/accounts/v3/global/game-session","POST",
                    ("call=userLogin&tapsonic_data="+URLEncoder.encode(payload,StandardCharsets.UTF_8)).getBytes(StandardCharsets.UTF_8),
                    Map.of("Content-Type","application/x-www-form-urlencoded"));
            var result=map(parse(new String(response.body(),StandardCharsets.UTF_8)));
            assertEquals(sentDevice.equals(device)?"000":"401",result.get("result_code"));
            if(sentDevice.equals(device)) assertEquals(seq,lng(map(map(result.get("value")).get("member")).get("member_id")));
        }
        assertEquals(canonical,services.state.getUser(device).get("uuid"));
        assertEquals(seq,lng(map(services.state.getUser(device).get("userdata")).get("u_seq")));
    }
    @Test void patchedProviderPlaceholderIsNormalizedOnlyAfterDeviceVerification() throws Exception {
        String canonical="cccccccccccccccccccccccccccccccc",device="dddddddddddddddddddddddddddddddd";
        var user=services.state.createUser(canonical,device,"");
        long seq=lng(map(user.get("userdata")).get("u_seq"));
        String command="user.userLogin";
        String message=codec.encodeResponse(command,obj("call","userLogin","data",
                obj("uuid","452465183","device_uuid",device,"u_seq",0,"u_id","")));
        String body="call=userLogin&access_token=opaque-provider&tapsonic_data="+URLEncoder.encode(message,StandardCharsets.UTF_8);
        var headers=Map.of("Content-Type","application/x-www-form-urlencoded");
        var exchange=request("/api/accounts/v3/global/game-session","POST",body.getBytes(StandardCharsets.UTF_8),headers);
        var result=map(parse(new String(exchange.body(),StandardCharsets.UTF_8)));
        assertEquals("000",result.get("result_code"));
        var value=map(result.get("value"));String token=str(value.get("access_token"));
        assertEquals(seq,lng(map(value.get("member")).get("member_id")));
        String normalized=str(value.get("normalized_message"));
        var payload=map(codec.decodeRequest(normalized,command).named().get("data"));
        assertEquals(canonical,payload.get("uuid"));assertEquals(device,payload.get("device_uuid"));
        assertEquals(0,lng(payload.get("u_seq")));assertEquals("",payload.get("u_id"));
        services.registry.register("userLogin",(req,ctx)->Result.ok(obj("user",map(services.state.getUser(device).get("userdata")))));
        for(boolean corrected:List.of(false,true)) {
            String rpc="call=userLogin&access_token="+URLEncoder.encode(token,StandardCharsets.UTF_8)+"&tapsonic_data="
                    +URLEncoder.encode(corrected?normalized:message,StandardCharsets.UTF_8);
            var response=request("/user/userLogin/vi/","POST",rpc.getBytes(StandardCharsets.UTF_8),headers);
            var env=codec.decodeRequest(new String(response.body(),StandardCharsets.UTF_8),new Dispatch(codec).returnDtoFor(command)).named();
            assertEquals(0,lng(map(env.get("error")).get("code")));
        }
        assertNull(services.state.getUser("452465183"));
        for(var bad:List.of(obj("uuid","452465183","device_uuid",device,"u_seq",999999),
                obj("uuid","452465183","device_uuid",device,"u_id","another-player"),
                obj("uuid","452465183","device_uuid",canonical),obj("uuid","452465183","device_uuid","bad"))) {
            int count=services.sessions.sessionCount();
            String encoded=codec.encodeResponse(command,obj("call","userLogin","data",bad));
            var response=request("/api/accounts/v3/global/game-session","POST",
                    ("call=userLogin&tapsonic_data="+URLEncoder.encode(encoded,StandardCharsets.UTF_8)).getBytes(StandardCharsets.UTF_8),headers);
            assertEquals("401",map(parse(new String(response.body(),StandardCharsets.UTF_8))).get("result_code"));
            assertEquals(count,services.sessions.sessionCount());
        }
        try(var files=Files.list(root.resolve("captures"))) {
            for(Path file:files.toList()) assertFalse(Files.readString(file).contains(token));
        }
    }
    @Test void rpcRejectsSessionAccountMismatchAndDoesNotInvokeHandler() throws Exception {
        services.state.createUser("token-user","token-device","");
        services.state.createUser("victim","victim-device","");
        String token=services.sessions.create("token-user","token-device","127.0.0.1").token();
        var dispatch=new Dispatch(codec);String command=dispatch.resolveCommand(obj("call","userLoad"));
        for(String identity:List.of("token-user","victim")) {
            String payload=codec.encodeResponse(command,obj("call","userLoad","data",obj("uuid",identity)));
            String body="call=userLoad&access_token="+URLEncoder.encode(token,StandardCharsets.UTF_8)+"&tapsonic_data="+URLEncoder.encode(payload,StandardCharsets.UTF_8);
            var response=request("/main/userLoad/en/","POST",body.getBytes(StandardCharsets.UTF_8),Map.of());
            var envelope=codec.decodeRequest(new String(response.body(),StandardCharsets.UTF_8),dispatch.returnDtoFor(command)).named();
            assertEquals(identity.equals("token-user")?0:401,lng(map(envelope.get("error")).get("code")));
        }
        try(var files=Files.list(root.resolve("captures"))) {
            for(Path file:files.toList()) assertFalse(Files.readString(file).contains(token));
        }
    }
    @Test void multipartUnityAndUrlencodedDuplicateSemantics() {
        String body="--unity\r\nContent-Disposition: form-data; name=\"call\"\r\n\r\nRequest\r\n--unity\r\nContent-Disposition: form-data; name=\"tapsonic_data\"\r\n\r\nabc+def==\r\n--unity--\r\n";
        var form=Multipart.parse("multipart/form-data; boundary=\"unity\"",body.getBytes(StandardCharsets.UTF_8));
        assertEquals("Request",form.get("call"));assertEquals("abc+def==",form.get("tapsonic_data"));
        assertEquals("a+b",Multipart.parse("","x=a%2Bb&x=second&empty=".getBytes(StandardCharsets.UTF_8)).get("x"));
        assertEquals("",Multipart.parse(null,"x=".getBytes(StandardCharsets.UTF_8)).get("x"));
    }
    @Test void downloadsFallBackToSiblingOutAndPreferLocalOut() throws Exception {
        Path sibling=Files.createDirectories(root.getParent().resolve("out")).resolve("fallback.apk");Files.write(sibling,new byte[]{4,5});
        assertArrayEquals(new byte[]{4,5},request("/download/fallback.apk","GET",new byte[0],Map.of()).body());
        Files.createDirectories(root.resolve("out"));Files.write(root.resolve("out/fallback.apk"),new byte[]{6});
        assertArrayEquals(new byte[]{6},request("/download/fallback.apk","GET",new byte[0],Map.of()).body());
    }
    @Test void selfSignedTlsUsesJavaKeytoolWithoutPythonOrOpenSsl() throws Exception {
        Path certificate=Tls.ensureCertificate(root);assertTrue(Files.isRegularFile(certificate));
        assertNotNull(Tls.load(certificate));assertEquals(certificate,Tls.ensureCertificate(root));
    }
}

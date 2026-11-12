package emu.leman.ggserver.server;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.config.ServerConfig;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class SessionAccessTest {
    @TempDir Path root;
    @Test void diagnosticsRetainOnlyStructureNeverCredentials() {
        String token="member|private-app|private-device|KR|secret|123";
        var diagnostics=SessionAccess.diagnostics(token,"multipart/form-data; boundary=private-boundary");
        assertEquals(obj("present",true,"length",token.length(),"pipeFields",6,
                "urlEncodedPipes",false,"form","multipart"),diagnostics);
        assertFalse(diagnostics.toString().contains("secret"));
        assertFalse(diagnostics.toString().contains("private"));
        assertEquals(true,SessionAccess.diagnostics("member%7Capp%7Cdevice","application/x-www-form-urlencoded").get("urlEncodedPipes"));
        assertEquals(false,SessionAccess.diagnostics(null,null).get("present"));
        assertEquals(0,SessionAccess.diagnostics(null,null).get("pipeFields"));
    }
    @Test void tokenBindsAllAliasesAndRevokingOneLoginDoesNotRevokeAnother() {
        try(Services services=new Services(root)) {
            var player=services.state.createUser("account","device");
            services.state.createUser("other","other-device");
            var first=services.sessions.create("account","device","127.0.0.1");
            var second=services.sessions.create("account","device","127.0.0.2");
            var request=obj("data",obj("device_uuid","device","u_seq",map(player.get("userdata")).get("u_seq")));
            assertNull(SessionAccess.validate(services,first.token(),request,false).error());
            assertEquals("account",SessionAccess.validate(services,second.token(),obj(),false).uuid());
            assertNotNull(SessionAccess.validate(services,first.token(),obj("data",obj("device_uuid","device","uuid","other")),false).error());
            assertNotNull(SessionAccess.validate(services,first.token(),obj("data",obj("u_seq",999999)),false).error());
            services.sessions.invalidate(first.token());
            assertNotNull(SessionAccess.validate(services,first.token(),request,false).error());
            assertNull(SessionAccess.validate(services,second.token(),request,false).error());
            assertNull(SessionAccess.validate(services,"",request,false).error());
            assertNotNull(SessionAccess.validate(services,"forged",request,false).error());
            assertNull(SessionAccess.validate(services,"cached-python-token",request,true).error());
            assertNull(SessionAccess.validate(services,"cached-python-token",request,true).uuid());
            assertNotNull(SessionAccess.validate(services,"cached-python-token",request,false).error());
        }
    }
    @Test void strictModeRequiresTokensExceptDuringBootstrap() {
        try(Services services=new Services(ServerConfig.defaults(root,obj("sessions",obj("required",true))))) {
            assertNotNull(SessionAccess.validate(services,"",obj(),false).error());
            assertNull(SessionAccess.validate(services,"",obj(),true).error());
        }
    }
    @Test void providerPlaceholderRequiresIssuedSessionExactDeviceAndMatchingOtherAliases() {
        try(Services services=new Services(ServerConfig.defaults(root,obj("sessions",obj("required",true))))) {
            String device="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",otherDevice="ffffffffffffffffffffffffffffffff";
            var user=services.state.createUser("canonical",device);
            var other=services.state.createUser("victim",otherDevice);
            long seq=lng(map(user.get("userdata")).get("u_seq"));
            long otherSeq=lng(map(other.get("userdata")).get("u_seq"));
            String token=services.sessions.create("canonical",device,"").token();
            var good=obj("data",obj("uuid","452465183","device_uuid",device,"u_seq",seq,"u_id",str(seq)));
            assertNull(SessionAccess.validate(services,token,good,false).error());
            assertEquals("canonical",map(good.get("data")).get("uuid"));
            for(var data:java.util.List.of(obj("uuid","452465183"),
                    obj("uuid","452465183","device_uuid",otherDevice),
                    obj("uuid","452465183","device_uuid",device,"u_seq",otherSeq),
                    obj("uuid","452465183","device_uuid",device,"u_id",str(otherSeq)),
                    obj("uuid","victim","device_uuid",device))) {
                var before=new java.util.LinkedHashMap<>(data);
                assertNotNull(SessionAccess.validate(services,token,obj("data",data),false).error());
                assertEquals(before,data);
            }
            for(String badToken:java.util.List.of("","forged")) {
                var data=obj("uuid","452465183","device_uuid",device);
                assertNotNull(SessionAccess.validate(services,badToken,obj("data",data),false).error());
                assertEquals("452465183",data.get("uuid"));
            }
            assertNull(services.state.getUser("452465183"));
        }
    }
    @Test void concurrentSessionsCannotClaimTheSameMailRewardTwice() throws Exception {
        try(Services services=new Services(root)) {
            new emu.leman.ggserver.game.GameContext(services).registerModules();
            services.state.createUser("account","device");
            var stored=services.state.getUser("account");
            stored.put("welcome_post_sent",true);
            stored.put("posts",new java.util.ArrayList<>());
            services.state.saveUser(stored);
            var post=new emu.leman.ggserver.game.social.SocialPosts(services).sendPost("account","test","test",java.util.List.of(obj("i_RewardType",1,"i_RewardId",1,"d_RewardQuantity",123)),1,false);
            long before=lng(map(services.state.getUser("account").get("userdata")).get("u_cp"));
            var a=services.sessions.create("account","device","");
            var b=services.sessions.create("account","device","");
            var gate=new java.util.concurrent.CountDownLatch(1);
            try(var executor=java.util.concurrent.Executors.newVirtualThreadPerTaskExecutor()) {
                var futures=new java.util.ArrayList<java.util.concurrent.Future<?>>();
                for(int i=0;i<20;i++) {
                    String token=i%2==0?a.token():b.token();
                    String alias=i%2==0?"account":"device";
                    futures.add(executor.submit(()->{
                        gate.await();
                        var request=obj("data",obj("uuid",alias,"idx",post.get("idx"),"type",0));
                        var access=SessionAccess.validate(services,token,request,false);
                        assertNull(access.error());
                        services.registry.handle("providePost",request,obj("uuid",access.uuid()));
                        return null;
                    }));
                }
                gate.countDown();
                for(var future:futures) future.get();
            }
            assertEquals(before+123,lng(map(services.state.getUser("account").get("userdata")).get("u_cp")));
        }
    }
}

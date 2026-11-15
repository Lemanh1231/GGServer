package emu.leman.ggserver.net;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.game.account.AccountModule;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class GamePacketTest {
    @TempDir Path root;

    @Test void legacyEnvelopeAndIdentityNormalizationArePreservedWithoutMutatingInput() {
        Map<String,Object> payload=obj("uuid","account","device_uuid","phone","nickname",null,"unknown",0);
        Map<String,Object> request=obj("data",payload,"extra","envelope");
        GamePacket packet=new GamePacket("updateNickName",request,obj("uuid","fallback","game_url","https://game"));
        assertEquals("phone",packet.identity());
        assertEquals("phone",packet.payload().get("uuid"));
        assertEquals("account",payload.get("uuid"));
        assertTrue(packet.payload().containsKey("nickname"));
        assertNull(packet.payload().get("nickname"));
        assertEquals(0,packet.payload().get("unknown"));
        assertEquals("envelope",packet.request().get("extra"));
        assertEquals("https://game",packet.context().get("game_url"));
        assertThrows(UnsupportedOperationException.class,() -> packet.payload().put("uuid","changed"));
        assertEquals("fallback",new GamePacket("getProfile",obj(),obj("uuid","fallback")).identity());
        assertEquals("account",new GamePacket("getProfile",obj("uuid","account"),obj()).identity());
    }

    @Test void responseConversionDoesNotRewriteSuccessOrErrorFields() {
        for(Result result:new Result[]{Result.ok(obj("nickname",null)),Result.error(900,"message")}) {
            GameResponse response=GameResponse.from(result);
            assertSame(result.data(),response.data());
            assertSame(result.error(),response.error());
            assertEquals(result,response.toResult());
        }
    }

    @Test void profilePacketAdaptersRetainNicknameNullEmptyZeroAndDefaultSemantics() {
        try(Services services=new Services(root)) {
            new AccountModule(services).register();
            services.state.createUser("account","phone","");
            assertEquals("Guitarist",call(services,"updateNickName",obj()).get("nickname"));
            for(Object value:new Object[]{null,"",0,"Player"}) {
                Map<String,Object> response=call(services,"updateNickName",obj("nickname",value));
                assertTrue(response.containsKey("nickname"));
                assertEquals(value,response.get("nickname"));
                assertEquals(value,call(services,"getProfile",obj()).get("u_nick"));
            }
            assertEquals(19,services.registry.commands().size());
        }
    }

    @Test void avatarAndTitleRetainLegacyTruthyPrimaryAndRawAlternateRules() {
        try(Services services=new Services(root)) {
            new AccountModule(services).register();
            services.state.createUser("account","phone","");
            for(String[] keys:new String[][]{{"updateAvatar","u_avatar","avatar"},{"updateUserTitle","u_title","title"}}) {
                String command=keys[0],field=keys[1],alternate=keys[2];
                assertEquals(1,call(services,command,obj()).get(field));
                assertEquals(8,call(services,command,obj(field,8,alternate,4)).get(field));
                assertEquals(4,call(services,command,obj(field,0,alternate,4)).get(field));
                assertEquals(1,call(services,command,obj(field,0)).get(field));
                assertEquals(0,call(services,command,obj(alternate,0)).get(field));
                assertEquals(0,call(services,"getProfile",obj()).get(field));
                assertNull(call(services,command,obj(alternate,null)).get(field));
                assertNull(call(services,"getProfile",obj()).get(field));
                assertEquals("",call(services,command,obj(field,null,alternate,"")).get(field));
                assertEquals("",call(services,"getProfile",obj()).get(field));
            }
        }
    }

    private Map<String,Object> call(Services services,String command,Map<String,Object> payload) {
        Result result=services.registry.handle(command,obj("data",payload),obj("uuid","phone"));
        assertEquals(0,integer(result.error().get("code")));
        return map(result.data());
    }
}

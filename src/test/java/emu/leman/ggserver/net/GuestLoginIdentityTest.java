package emu.leman.ggserver.net;

import de.bwaldvogel.mongo.MongoServer;
import de.bwaldvogel.mongo.backend.memory.MemoryBackend;
import emu.leman.ggserver.Services;
import emu.leman.ggserver.config.ServerConfig;
import emu.leman.ggserver.game.account.AuthApi;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

/** Guest credentials must not be substituted with public repository lookup aliases. */
class GuestLoginIdentityTest {
    @TempDir Path root;
    Services services;
    MongoServer mongo;

    void setup(String backend) {
        var config=ServerConfig.defaults(root);
        if(backend.equals("mongo")) {
            mongo=new MongoServer(new MemoryBackend());var address=mongo.bind();
            config=ServerConfig.defaults(root,obj("database",obj("backend","mongo","name","guest_identity_test",
                    "uri","mongodb://"+address.getHostString()+":"+address.getPort()+"/?serverSelectionTimeoutMS=5000")));
        }
        services=new Services(config);
    }

    @AfterEach void close() {
        try {if(services!=null)services.close();} finally {if(mongo!=null)mongo.shutdownNow();}
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void canonicalSequenceAndUserAliasesCannotIssueSessionsOrMutateAccount(String backend) {
        setup(backend);
        services.state.createUser("guest-account","private-guest-device");
        var stored=services.state.getUser("guest-account");var data=map(stored.get("userdata"));
        String before=stringify(stored);int count=services.sessions.sessionCount();
        var auth=new AuthApi(services);
        for(String alias:List.of("guest-account",str(data.get("u_seq")),str(data.get("u_id")))) {
            var rejected=auth.login(obj("device_cd",alias),"203.0.113.5");
            assertEquals("401",rejected.get("result_code"));assertNull(rejected.get("value"));
            assertEquals(count,services.sessions.sessionCount());
            assertEquals(before,stringify(services.state.getUser("guest-account")));
        }
        var accepted=auth.login(obj("device_cd","private-guest-device"));
        assertEquals("000",accepted.get("result_code"));
        var session=services.sessions.find(str(map(accepted.get("value")).get("access_token")));
        assertEquals("guest-account",session.canonicalUuid());assertEquals("private-guest-device",session.deviceUuid());
        assertEquals(lng(data.get("u_seq")),lng(map(map(accepted.get("value")).get("member")).get("member_id")));
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void newDeviceAndLegacySameCanonicalDeviceContinueToWork(String backend) {
        setup(backend);var auth=new AuthApi(services);
        var first=auth.login(obj("device_cd","new-private-device"));
        assertEquals("000",first.get("result_code"));
        String before=stringify(services.state.getUser("new-private-device"));
        var second=auth.login(obj("device_cd","new-private-device"));
        assertEquals("000",second.get("result_code"));
        assertEquals(before,stringify(services.state.getUser("new-private-device")));
        assertEquals("new-private-device",services.sessions.find(str(map(second.get("value")).get("access_token"))).canonicalUuid());
        assertEquals(2,services.sessions.sessionCount());
    }
}

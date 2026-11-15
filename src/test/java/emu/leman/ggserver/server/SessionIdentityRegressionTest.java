package emu.leman.ggserver.server;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.config.ServerConfig;
import de.bwaldvogel.mongo.MongoServer;
import de.bwaldvogel.mongo.backend.memory.MemoryBackend;
import com.mongodb.client.MongoClients;
import java.nio.file.Path;
import java.sql.DriverManager;
import java.util.List;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

/** Session identity must not depend on inventory reconstruction or cache stale aliases. */
class SessionIdentityRegressionTest {
    @TempDir Path root;

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void allClaimsStayStrictAndRequestsAreUnchangedOnRejection(String backend) throws Exception {
        try(var fixture=new Fixture(backend)) {
            var s=fixture.services;
            var user=s.state.createUser("account",DEVICE);
            var other=s.state.createUser("other",OTHER_DEVICE);
            var ud=map(user.get("userdata"));var od=map(other.get("userdata"));
            String token=s.sessions.create("account",DEVICE,"").token();
            var good=obj("uuid","account","device_uuid",DEVICE,"u_seq",ud.get("u_seq"),"u_id",ud.get("u_id"));
            assertNull(SessionAccess.validate(s,token,obj("data",copy(good)),false).error());
            for(String field:List.of("uuid","device_uuid","u_seq","u_id")) {
                var bad=copy(good);
                bad.put(field,switch(field){case "uuid"->"other";case "device_uuid"->OTHER_DEVICE;default->od.get(field);});
                String before=stringify(bad);
                assertNotNull(SessionAccess.validate(s,token,obj("data",bad),false).error(),field);
                assertEquals(before,stringify(bad));
                bad.put(field,"unknown-alias");
                assertNotNull(SessionAccess.validate(s,token,obj("data",bad),false).error(),field);
            }
            for(String alias:List.of("account",DEVICE,str(ud.get("u_seq")),"guest_"+ud.get("u_seq")))
                assertNull(SessionAccess.validate(s,token,obj("data",obj("uuid",alias)),false).error(),alias);
            // Optional claims remain compatible.
            assertNull(SessionAccess.validate(s,token,obj("data",obj("uuid","0","u_seq",0)),false).error());
            assertNull(SessionAccess.validate(s,token,obj(),false).error());
            s.sessions.invalidate(token);
            assertNotNull(SessionAccess.validate(s,token,obj("data",good),false).error());
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void lightweightLookupMatchesExistingAliasResolutionAndIsReadOnly(String backend) throws Exception {
        try(var fixture=new Fixture(backend)) {
            var s=fixture.services;var user=s.state.createUser("account",DEVICE);s.state.saveUser(user);
            var ud=map(user.get("userdata"));String before=stringify(s.state.exportUser("account"));
            for(String alias:List.of("account",DEVICE,str(ud.get("u_id")),str(ud.get("u_seq")),
                    "guest_"+ud.get("u_seq")," "+ud.get("u_seq")+" ","00"+ud.get("u_seq"),
                    "unknown","0","-1","999999999999999999999999999","guest_bad","")) {
                var full=s.state.getUser(alias);var identity=s.state.getIdentity(alias);
                if(full==null)assertNull(identity,alias);
                else {
                    assertNotNull(identity,alias);
                    assertEquals(str(full.get("uuid")),identity.canonicalUuid(),alias);
                    assertEquals(str(map(full.get("userdata")).get("device_uuid")),identity.deviceUuid(),alias);
                    assertEquals("UserIdentity[redacted]",identity.toString());
                }
            }
            assertNull(s.state.getIdentity(null));
            assertEquals(before,stringify(s.state.exportUser("account")));
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void placeholderRequiresExactDeviceAndRejectsCollisionWithoutMutation(String backend) throws Exception {
        try(var fixture=new Fixture(backend)) {
            var s=fixture.services;var user=s.state.createUser("account",DEVICE);
            var ud=map(user.get("userdata"));String token=s.sessions.create("account",DEVICE,"").token();
            var good=obj("uuid","452465183","device_uuid",DEVICE,"u_seq",ud.get("u_seq"),"u_id",ud.get("u_id"));
            var accepted=copy(good);
            assertNull(SessionAccess.validate(s,token,obj("data",accepted),false).error());
            assertEquals("account",accepted.get("uuid"));
            for(String alias:List.of("account",str(ud.get("u_seq")),"guest_"+ud.get("u_seq"),"missing")) {
                var bad=copy(good);bad.put("device_uuid",alias);
                String before=stringify(bad);
                assertNotNull(SessionAccess.validate(s,token,obj("data",bad),false).error());
                assertEquals(before,stringify(bad));
            }
            var other=s.state.createUser("other",OTHER_DEVICE);
            var bad=copy(good);bad.put("u_id",map(other.get("userdata")).get("u_id"));
            assertNotNull(SessionAccess.validate(s,token,obj("data",bad),false).error());
            assertEquals("452465183",bad.get("uuid"));
            s.state.createUser("452465183","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
            assertNotNull(SessionAccess.validate(s,token,obj("data",good),false).error());
            assertEquals("452465183",good.get("uuid"));
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void aliasReassignmentIsSeenOnTheNextRequest(String backend) throws Exception {
        try(var fixture=new Fixture(backend)) {
            var s=fixture.services;s.state.createUser("account",DEVICE);
            String token=s.sessions.create("account",DEVICE,"").token();
            var request=obj("data",obj("uuid","account","device_uuid",DEVICE));
            assertNull(SessionAccess.validate(s,token,request,false).error());
            assertTrue(s.state.deleteUser("account"));
            s.state.createUser("other",DEVICE);
            assertNotNull(SessionAccess.validate(s,token,request,false).error());
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void validationDoesNotReadFeatureSnapshots(String backend) throws Exception {
        try(var fixture=new Fixture(backend)) {
            var s=fixture.services;var user=s.state.createUser("account",DEVICE);s.state.saveUser(user);
            var ud=map(user.get("userdata"));String token=s.sessions.create("account",DEVICE,"").token();
            // Deliberately break feature storage only in this disposable test DB.
            // A gameplay getUser must still fail closed, but identity has its own boundary.
            if(backend.equals("mongo")) {
                try(var client=MongoClients.create(fixture.uri)) {
                    client.getDatabase("session_identity_test").getCollection("user_profiles").deleteMany(new org.bson.Document());
                }
            } else {
                try(var db=DriverManager.getConnection("jdbc:sqlite:"+root.resolve("data/database.db"));var statement=db.createStatement()) {
                    statement.executeUpdate("UPDATE user_data SET user_contents_json='not-json' WHERE uuid='account'");
                }
            }
            assertThrows(RuntimeException.class,()->s.state.getUser("account"));
            var request=obj("data",obj("uuid","account","device_uuid",DEVICE,"u_seq",ud.get("u_seq"),"u_id",ud.get("u_id")));
            assertNull(SessionAccess.validate(s,token,request,false).error());
            var placeholder=obj("data",obj("uuid","452465183","device_uuid",DEVICE,"u_seq",ud.get("u_seq"),"u_id",ud.get("u_id")));
            assertNull(SessionAccess.validate(s,token,placeholder,false).error());
            assertEquals("account",map(placeholder.get("data")).get("uuid"));
        }
    }

    private static final String DEVICE="eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",OTHER_DEVICE="ffffffffffffffffffffffffffffffff";
    private final class Fixture implements AutoCloseable {
        final MongoServer mongo;
        final String uri;
        final Services services;
        Fixture(String backend) {
            if(backend.equals("mongo")) {
                mongo=new MongoServer(new MemoryBackend());var address=mongo.bind();
                uri="mongodb://"+address.getHostString()+":"+address.getPort()+"/?serverSelectionTimeoutMS=5000";
            } else {mongo=null;uri="mongodb://127.0.0.1:27017";}
            services=new Services(ServerConfig.defaults(root,obj("sessions",obj("required",true),
                    "database",obj("backend",backend,"name","session_identity_test","uri",uri))));
        }
        @Override public void close() {try{services.close();}finally{if(mongo!=null)mongo.shutdownNow();}}
    }
}

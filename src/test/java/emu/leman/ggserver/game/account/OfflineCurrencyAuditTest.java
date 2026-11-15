package emu.leman.ggserver.game.account;

import de.bwaldvogel.mongo.MongoServer;
import de.bwaldvogel.mongo.backend.memory.MemoryBackend;
import emu.leman.ggserver.Services;
import emu.leman.ggserver.config.ServerConfig;
import java.nio.file.Path;
import java.util.*;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

/** Regression coverage for exact, independent, atomic native offline snapshots. */
class OfflineCurrencyAuditTest {
    @TempDir Path root;

    private final class Fixture implements AutoCloseable {
        final MongoServer mongo;
        final ServerConfig config;
        Services services;
        Fixture(String backend) {
            mongo=backend.equals("mongo")?new MongoServer(new MemoryBackend()):null;
            if(mongo==null) config=ServerConfig.defaults(root);
            else {
                var address=mongo.bind();
                config=ServerConfig.defaults(root,obj("database",obj("backend","mongo","name","offline_audit",
                        "uri","mongodb://"+address.getHostString()+":"+address.getPort()+"/?serverSelectionTimeoutMS=5000")));
            }
            open();
            var user=services.state.createUser("audit-account","audit-device","");
            user.put("legacy_unlock_all_migrated",true);user.put("needs_client_reset",false);
            services.state.saveUser(user);
        }
        void open() { services=new Services(config);new AccountModule(services).register(); }
        void reopen() { services.close();open(); }
        Map<String,Object> user() { return services.state.getUser("audit-device"); }
        Map<String,Object> call(String command,Map<String,Object> payload) {
            payload.put("device_uuid","audit-device");
            var result=services.registry.handle(command,obj("data",payload),obj());
            assertEquals(0,integer(result.error().get("code")));
            return map(result.data());
        }
        void save(Object... rows) { call("userSave",obj("user_area_info",List.of(rows))); }
        @Override public void close() { try {services.close();} finally {if(mongo!=null)mongo.shutdownNow();} }
    }
    private static Map<String,Object> area(int number,String gp) { return obj("u_area_num",number,"s_Gp1",gp,"d_Like",0.0); }
    private static String gp(Map<String,Object> user,int number) { return str(map(map(user.get("areas")).get(str(number))).get("s_Gp1")); }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void readPreservesIndependentChapterTwoBalance(String backend) {
        try(var f=new Fixture(backend)) {
            var user=f.user();map(user.get("userdata")).put("u_like",1000.0);
            user.put("areas",obj("1",area(1,"1000"),"2",area(2,"7")));f.services.state.saveUser(user);
            assertEquals("7",gp(f.user(),2));
        }
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void chapterTwoSaveDoesNotRaiseGlobalLikeOrChapterOne(String backend) {
        try(var f=new Fixture(backend)) {
            f.save(area(1,"10"),area(2,"2000"));
            assertEquals(10.0,dbl(map(f.user().get("userdata")).get("u_like")));
            assertEquals("10",gp(f.user(),1));
            f.reopen();assertEquals("10",gp(f.user(),1));assertEquals("2000",gp(f.user(),2));
        }
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void offlineSpendingCanReduceSavedBalance(String backend) {
        try(var f=new Fixture(backend)) {
            f.save(area(1,"1000"));f.save(area(1,"700"));
            assertEquals("700",gp(f.user(),1));
            assertEquals(700.0,dbl(map(f.user().get("userdata")).get("u_like")));
        }
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void fullLoginRetainsExactIntegerDespiteDoubleProjection(String backend) {
        try(var f=new Fixture(backend)) {
            f.save(area(1,"9007199254740995"));
            assertEquals("9007199254740995",gp(f.user(),1));
            f.call("userLogin",obj("u_seq",map(f.user().get("userdata")).get("u_seq")));
            assertEquals("9007199254740995",gp(f.user(),1));
        }
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void userLoadRetainsExactInteger(String backend) {
        try(var f=new Fixture(backend)) {
            f.save(area(1,"9007199254740995"));
            var response=f.call("userLoad",obj("type","ALL"));
            assertEquals("9007199254740995",str(map(map(response.get("area_data")).get("1")).get("s_Gp1")));
        }
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void auditAbsoluteSaveAcceptsLargeIncomeWithoutOfflineClaim(String backend) {
        try(var f=new Fixture(backend)) {
            f.save(area(1,"1000000000000000000000000000000"));
            assertEquals("1000000000000000000000000000000",gp(f.user(),1));
            assertFalse(truth(f.user().get("needs_client_reset")));
            assertFalse(f.user().containsKey("force_server_like"));
            f.reopen();assertEquals("1000000000000000000000000000000",gp(f.user(),1));
        }
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void hibernationLogCannotDoubleGrantAndLegacyPushListIsExplicitlyEmpty(String backend) {
        try(var f=new Fixture(backend)) {
            String before=stringify(f.user());
            assertEquals(0,integer(f.call("hibernationLog",obj("action",1,"time",21600)).get("action")));
            assertEquals(before,stringify(f.user()));
            assertTrue(f.services.registry.commands().contains("getLocalPush"));
            assertEquals(List.of(),f.services.registry.handle("getLocalPush",obj("data",obj()),obj()).data());
        }
    }
    @Test void failedFinalSaveDoesNotWriteCurrencyOrAdminResetFlags() throws Exception {
        try(var f=new Fixture("sqlite")) {
            String before=stringify(f.user());
            try(var db=java.sql.DriverManager.getConnection("jdbc:sqlite:"+root.resolve("data/database.db"));var sql=db.createStatement()) {
                sql.execute("CREATE TRIGGER offline_audit_fail BEFORE UPDATE OF u_cp ON user_data BEGIN SELECT RAISE(ABORT,'audit final save failure'); END");
                assertThrows(IllegalStateException.class,()->f.call("userSave",obj("user_character",List.of(obj("i_id",1,"i_Level",9)),
                        "user_area_info",List.of(area(1,"1234")))));
                var partial=f.user();
                assertEquals(before,stringify(partial));
                assertEquals(0.0,dbl(map(partial.get("userdata")).get("u_like")));
                assertEquals("0",gp(partial,1));
                assertFalse(truth(partial.get("needs_client_reset")));
                assertFalse(partial.containsKey("force_server_like"));
            }
        }
    }
    @Test void failedMongoSnapshotEncodingCannotPublishCurrencyBeforeProgress() {
        try(var f=new Fixture("mongo")) {
            String before=stringify(f.user());
            assertThrows(IllegalArgumentException.class,()->f.call("userSave",obj("user_character",List.of(obj("i_id",1,"i_Level",9,"invalid",new Object())),
                    "user_area_info",List.of(area(1,"1234")))));
            assertEquals(before,stringify(f.user()));
            f.reopen();assertEquals(before,stringify(f.user()));
        }
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void malformedSnapshotIsRejectedBeforeInventoryOrCurrencyWrites(String backend) {
        try(var f=new Fixture(backend)) {
            for(Object gp:List.of("-1","NaN","Infinity","abc123","1QQQ","1e999","")) {
                String before=stringify(f.user());
                var result=f.services.registry.handle("userSave",obj("data",obj("device_uuid","audit-device",
                        "user_character",List.of(obj("i_id",1,"i_Level",999)),"user_area_info",List.of(area(1,str(gp))))),obj());
                assertNotEquals(0,integer(result.error().get("code")),str(gp));
                assertEquals(before,stringify(f.user()));
            }
            for(var rows:List.of(List.of(area(3,"4")),List.of(area(1,"4"),area(1,"5")))) {
                var result=f.services.registry.handle("userSave",obj("data",obj("device_uuid","audit-device","user_area_info",rows)),obj());
                assertNotEquals(0,integer(result.error().get("code")));
            }
        }
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void adminLikeSetAndIncrementProtectExactChapterOneWithoutChangingHeart(String backend) {
        try(var f=new Fixture(backend)) {
            f.save(area(1,"10"),area(2,"7"));
            f.services.state.setLikeCurrency("audit-device","9007199254740995");
            f.services.state.incrementCurrency("audit-device",0,0,1,0);
            f.save(area(1,"999Z"),area(2,"999Z"));
            assertEquals("9007199254740996",gp(f.user(),1));assertEquals("7",gp(f.user(),2));
            var login=f.call("userLogin",obj("u_seq",map(f.user().get("userdata")).get("u_seq")));
            assertTrue(str(map(login.get("user")).get("device_uuid")).startsWith("RESET_"));
            assertEquals("7",gp(f.user(),2));
            f.save(area(2,"6"),area(1,"9007199254740993"));
            assertEquals("9007199254740993",gp(f.user(),1));assertEquals("6",gp(f.user(),2));
            f.reopen();assertEquals("9007199254740993",gp(f.user(),1));assertEquals("6",gp(f.user(),2));
        }
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void partialAreaSaveRetainsBalanceAndZeroSpendIsAccepted(String backend) {
        try(var f=new Fixture(backend)) {
            f.save(area(1,"100"),area(2,"7"));
            f.save(obj("u_area_num",1,"i_SelectedMusicId",1));
            assertEquals("100",gp(f.user(),1));
            f.save(area(2,"0"),area(1,"0"));
            f.reopen();assertEquals("0",gp(f.user(),1));assertEquals("0",gp(f.user(),2));
        }
    }
}

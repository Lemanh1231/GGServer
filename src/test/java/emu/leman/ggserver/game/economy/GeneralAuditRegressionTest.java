package emu.leman.ggserver.game.economy;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.game.account.AccountModule;
import emu.leman.ggserver.net.Result;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
import static emu.leman.ggserver.util.Json.*;

/** Repository smoke regressions; authoritative tree also tests concurrency and Mongo failures. */
class GeneralAuditRegressionTest {
    @TempDir Path root;
    Services s;
    @BeforeEach void setup() throws Exception {
        for(String file:List.of("gamedata/game_data.json","schema/schema.json")) {
            var target=root.resolve(file);Files.createDirectories(target.getParent());Files.copy(Path.of("resources").resolve(file),target);
        }
        write(root.resolve("event_config.json"),emu.leman.ggserver.game.content.EventManager.defaults());
        s=new Services(root);new AccountModule(s).register();new EconomyModule(s).register();
        var u=s.state.createUser("audit-local","audit-device");map(u.get("userdata")).put("u_cp",100000);
        u.put("user_daily_mission",new ArrayList<>(List.of(obj("i_id",2,"i_Level",1,"d_Quantity",0))));s.state.saveUser(u);
    }
    @AfterEach void close(){s.close();}
    Map<String,Object> user(){return s.state.getUser("audit-local");}
    long cp(){return lng(map(user().get("userdata")).get("u_cp"));}
    Result result(String command,Object... fields){return s.registry.handle(command,obj("data",obj(fields)),obj("uuid","audit-local"));}
    Map<String,Object> call(String command,Object... fields){var r=result(command,fields);assertEquals(0,integer(r.error().get("code")));return map(r.data());}
    @Test void missionRequiresThresholdAndAliasesCannotReplay(){
        assertEquals("N",call("setGameReward","type","daily_mission","id",2,"level",1).get("status"));
        assertEquals("Y",call("setGameReward","type","daily_mission","id","02","level",1,"s_quantity","2376").get("status"));
        assertEquals("N",call("setGameReward","type","daily_mission","id",2,"level",1,"s_quantity","2376").get("status"));
        assertEquals("N",call("setGameReward","type","daily_mission","id",2,"level",2).get("status"));assertEquals(100010,cp());
    }
    @Test void invalidPassClaimsHaveNoRewards(){
        for(int type:List.of(0,1,2,-1)) assertTrue(list(call("setPassReward","group",13,"step",1,"type",type).get("reward_data")).isEmpty());
        assertTrue(list(call("setPassReward","group",13,"step",0,"type",0,"i_Version",999).get("reward_data")).isEmpty());
    }
    @Test void maxAndUnknownUnitDoNotCharge(){
        var u=user();u.put("user_unit",new ArrayList<>(List.of(obj("i_id",3,"i_Level",6))));s.state.saveUser(u);
        call("buyContents","type","unit","idx",3);assertEquals(100000,cp());
        assertNotEquals(0,integer(result("buyContents","type","skill","idx",999999).error().get("code")));assertEquals(100000,cp());
    }
    @Test void skillTimersAndPassPointsSurviveStaleSaves(){
        int version=new emu.leman.ggserver.game.account.AuthContent(s).passVersion(13);
        var u=user();u.put("user_skill",new ArrayList<>(List.of(obj("i_id",1,"i_Level",2))));u.put("user_event_point",new ArrayList<>(List.of(obj("s_EventType","Pass","i_DataID",13,"i_Point",2000,"i_Version",version))));s.state.saveUser(u);
        call("userSave","user_skill",List.of(obj("i_id",1,"i_Level",99,"b_Activate",1,"l_ActivateOnTicks",639000000000000000L,"l_ActivateOffTicks",639000001000000000L)),"user_event_point",List.of(obj("s_EventType","Pass","i_DataID",13,"i_Point",0,"i_Version",version)));
        var skill=map(list(user().get("user_skill")).getFirst());assertEquals(2,integer(skill.get("i_Level")));assertTrue(truth(skill.get("b_Activate")));assertEquals(639000001000000000L,lng(skill.get("l_ActivateOffTicks")));
        assertEquals(2000,lng(map(list(user().get("user_event_point")).getFirst()).get("i_Point")));
    }
    @Test void passAdRetryDoesNotGrantTwice(){
        call("paidEventPoint","i_SubscribeID",13,"type",0);
        long once=lng(map(list(user().get("user_event_point")).getFirst()).get("i_Point"));
        assertNotEquals(0,integer(result("paidEventPoint","i_SubscribeID",13,"type",0).error().get("code")));
        assertEquals(once,lng(map(list(user().get("user_event_point")).getFirst()).get("i_Point")));
    }
    @Test void failedPurchaseDoesNotDeduct() throws Exception {
        try(var db=java.sql.DriverManager.getConnection("jdbc:sqlite:"+root.resolve("data/database.db"));var sql=db.createStatement()) {
            sql.execute("CREATE TRIGGER audit_purchase_fail BEFORE INSERT ON user_inventory BEGIN SELECT RAISE(ABORT,'audit failure'); END");
            assertThrows(IllegalStateException.class,()->call("buyContents","type","skill","idx",1));
            assertEquals(100000,cp());assertTrue(list(user().get("user_skill")).isEmpty());
        }
    }
}

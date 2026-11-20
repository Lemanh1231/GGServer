package emu.leman.ggserver.game.economy;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.game.account.AccountModule;
import emu.leman.ggserver.game.content.*;
import emu.leman.ggserver.net.Result;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
import static emu.leman.ggserver.util.Json.*;

/** Real catalog, synthetic account, isolated SQLite. No production requests. */
class EventSurpriseRegressionTest {
    @TempDir Path root;
    Services s;
    @BeforeEach void setup() throws Exception {
        for(String file:List.of("gamedata/game_data.json","gamedata/tour_drop_weights.json","schema/schema.json","gamedata/getEventRewardList.b64")) {
            var target=root.resolve(file);Files.createDirectories(target.getParent());Files.copy(Path.of("resources").resolve(file),target);
        }
        write(root.resolve("event_config.json"),EventManager.defaults());s=new Services(root);register();
        var u=s.state.createUser("event-regression","synthetic-device");
        u.put("user_music",new ArrayList<>(List.of(obj("i_id",201,"i_Level",1,"b_EncoreBonusAppear",1,"i_EncoreBonusFollowerId",201))));
        u.put("user_follower",new ArrayList<>(List.of(obj("i_id",201,"i_Level",1),obj("i_id",1,"i_Level",1))));s.state.saveUser(u);
    }
    void register(){new AccountModule(s).register();new ContentModule(s).register();new EconomyModule(s).register();}
    @AfterEach void close(){s.close();}
    Map<String,Object> user(){return s.state.getUser("event-regression");}
    Result result(String cmd,Object... args){return s.registry.handle(cmd,obj("data",obj(args)),obj("uuid","event-regression"));}
    void ok(String cmd,Object... args){var r=result(cmd,args);assertEquals(0,integer(r.error().get("code")),r.error().toString());}
    void reject(String cmd,Object... args){String before=stringify(user());assertNotEquals(0,integer(result(cmd,args).error().get("code")));assertEquals(before,stringify(user()));}
    Object nativeSong(int appear,int follower){return obj("i_id",201,"i_Level",1,"i_BonusLevel",0,"b_EncoreBonusAppear",appear,"i_EncoreBonusFollowerId",follower);}
    @Test void nativeEncoreCanRepeatOnlyAfterCooldownAndSurvivesRestart(){
        ok("getMusicReward","i_ids",List.of(201));ok("userSave","user_music",List.of(nativeSong(1,201)));reject("getMusicReward","i_ids",List.of(201));
        s.close();s=new Services(root);register();reject("getMusicReward","i_ids",List.of(201));
        var u=user();map(map(u.get("encore_state")).get("201")).put("claimed_at",System.currentTimeMillis()/1000-75601);s.state.saveUser(u);
        ok("userSave","user_music",List.of(nativeSong(1,201)));ok("getMusicReward","i_ids",List.of(201));reject("getMusicReward","i_ids",List.of(201));
    }
    @Test void staleNoGiftSaveCannotDeletePendingEncore(){ok("userSave","user_music",List.of(nativeSong(0,0)));ok("getMusicReward","i_ids",List.of(201));}
    @Test void chapterTwoMoaGiftAfterInactiveLegacyZeroReceipt(){
        var u=user();u.put("user_music",new ArrayList<>(List.of(nativeSong(0,0))));
        list(u.get("user_follower")).add(obj("i_id",202,"i_Level",1001));
        u.put("encore_claims",obj("201",0));s.state.saveUser(u);
        ok("userLogin");
        ok("userSave","type","music","user_music",List.of(nativeSong(1,202)));
        ok("getMusicReward","i_ids",List.of(201));
        assertTrue(list(user().get("user_follower_profile")).stream().anyMatch(v->integer(map(v).get("i_id"))==5));
        ok("userSave","type","music","user_music",List.of(nativeSong(1,202)));
        reject("getMusicReward","i_ids",List.of(201));
    }
    @Test void crossAreaFollowerCannotReceiveEncore(){var u=user();map(list(u.get("user_music")).getFirst()).put("i_EncoreBonusFollowerId",1);s.state.saveUser(u);reject("getMusicReward","i_ids",List.of(201));}
    @Test void responseIncludesGrantedProfileBonus(){var u=user();u.put("user_follower_profile",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1,"d_Exp",0,"i_AddCandy",3))));s.state.saveUser(u);
        double before=dbl(map(user().get("userdata")).get("u_candy"));var response=result("getMusicReward","i_ids",List.of(201));assertEquals(0,integer(response.error().get("code")));
        assertEquals(13,integer(map(response.data()).get("total_reward_value")));assertEquals(before+13,dbl(map(user().get("userdata")).get("u_candy")));
    }
    @Test void selectionRequiresEnabledEventAndStrictCatalogId(){reject("setSelectReward","i_id",2);s.events.setAttendanceEventEnabled(202111,true);reject("setSelectReward","i_id",999999);reject("setSelectReward","i_id",2.5);ok("setSelectReward","i_id",2);}
    @Test void selectionAttendanceOnlyDaysAdvanceWithoutGrantsAndCannotRepeat(){
        s.events.setAttendanceEventEnabled(202111,true);
        for(int day=1;day<=6;day++) {
            var u=user();
            if(day>1)map(map(u.get("attendance")).get("202111")).put("ymd",0);
            s.state.saveUser(u);
            var before=copy(user());before.remove("attendance");
            ok("setEventReward","event_idx",202111);
            assertEquals(day,integer(map(map(user().get("attendance")).get("202111")).get("day")));
            var after=copy(user());after.remove("attendance");assertEquals(stringify(before),stringify(after));
            String claimed=stringify(user());ok("setEventReward","event_idx",202111);assertEquals(claimed,stringify(user()));
        }
        var u=user();map(map(u.get("attendance")).get("202111")).put("ymd",0);s.state.saveUser(u);
        reject("setEventReward","event_idx",202111);
        ok("setSelectReward","i_id",2);
        ok("setEventReward","event_idx",202111);
        assertEquals(7,integer(map(map(user().get("attendance")).get("202111")).get("day")));
        String claimed=stringify(user());ok("setEventReward","event_idx",202111);assertEquals(claimed,stringify(user()));
    }
    @Test void missingBoardCannotGenerateFallbackReward(){write(root.resolve("gamedata/getEventRewardList.json"),obj());reject("setEventReward","event_idx",3);}
    @Test void corruptAndMissingConfigCannotEnableEvents() throws Exception {Files.writeString(root.resolve("event_config.json"),"{broken");assertFalse(s.events.isMeowfestEnabled());assertFalse(s.events.isStarPassEnabled());Files.delete(root.resolve("event_config.json"));assertTrue(s.events.activeEvents().isEmpty());}
}

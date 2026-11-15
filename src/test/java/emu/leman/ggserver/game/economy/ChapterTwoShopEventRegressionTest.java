package emu.leman.ggserver.game.economy;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.game.account.AccountModule;
import emu.leman.ggserver.game.content.ContentModule;
import emu.leman.ggserver.game.content.AcquisitionRules;
import emu.leman.ggserver.net.Result;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
import static emu.leman.ggserver.util.Json.*;

/** Real catalog, synthetic account, SQLite only; no production requests. */
class ChapterTwoShopEventRegressionTest {
    @TempDir Path root;
    Services s;
    @BeforeEach void setup() throws Exception {
        for(String f:List.of("gamedata/game_data.json","schema/schema.json","gamedata/tour_drop_weights.json","gamedata/getEventRewardList.b64","gamedata/getVarietyStore.b64")) {
            var target=root.resolve(f);Files.createDirectories(target.getParent());Files.copy(Path.of("resources").resolve(f),target);
        }
        s=new Services(root);new AccountModule(s).register();new EconomyModule(s).register();new ContentModule(s).register();
        var u=s.state.createUser("regression","synthetic-device");map(u.get("userdata")).put("u_cp",100000);map(u.get("userdata")).put("u_candy",1000000.0);s.state.saveUser(u);
    }
    @AfterEach void close(){s.close();}
    Map<String,Object> user(){return s.state.getUser("regression");}
    Result result(String cmd,Object... args){return s.registry.handle(cmd,obj("data",obj(args)),obj("uuid","regression"));}
    void ok(String cmd,Object... args){assertEquals(0,integer(result(cmd,args).error().get("code")));}
    void rejected(String cmd,Object... args){String before=stringify(user());assertNotEquals(0,integer(result(cmd,args).error().get("code")));assertEquals(before,stringify(user()));}
    @Test void shopRejectsUnknownDisabledAndCooldownRequests(){
        rejected("buyShop","idx",1501);s.events.setStarPass(false,null,null);s.events.setPassGoodsSaleEnabled(false);
        rejected("buyShop","idx",1013);rejected("buyShop","idx",3012);ok("buyShop","idx",3);rejected("buyShop","idx",3);
        ok("buyShop","idx",31);ok("buyShop","idx",31);
    }
    @Test void varietyAndLegacyEndpointDoNotChargeUnknownOrUnsupportedPurchases(){
        rejected("buyVarietyStore","idx",999999);rejected("buyItem","idx",1);
        double before=dbl(map(user().get("userdata")).get("u_candy"));ok("buyVarietyStore","idx",4);
        assertEquals(before-50,dbl(map(user().get("userdata")).get("u_candy")));assertEquals(1,AcquisitionRules.level(user(),"user_prop",4));
    }
    @Test void musicValidatesCatalogBoundsButPreservesSameSnapshotOfflineAcquisition(){
        ok("userSave","user_music",List.of(obj("i_id",999999,"i_Level",1),obj("i_id",202,"i_Level",Integer.MAX_VALUE)));
        assertEquals(0,AcquisitionRules.level(user(),"user_music",999999));assertEquals(0,AcquisitionRules.level(user(),"user_music",202));
        ok("userSave","user_follower",List.of(obj("i_id",12,"i_Level",15),obj("i_id",202,"i_Level",1)),"user_area_info",List.of(obj("u_area_num",1,"i_UserFanGrade",4)),"user_music",List.of(obj("i_id",202,"i_Level",4)));
        assertEquals(4,AcquisitionRules.level(user(),"user_music",202));rejected("buyMusic","idx",202);rejected("buyAvatar","idx",204);
    }
    @Test void meowfestRejectsSkippedConditionsAndDoesNotManufactureLoginRewards(){
        rejected("getSamSeckReward","i_id",3);rejected("getSamSeckReward","i_id",1);
        var u=user();map(u.get("userdata")).put("u_samseck_step",3);new AccountModule(s).userContents(u);
        assertEquals(0,AcquisitionRules.level(u,"user_guitar",10));assertEquals(0,AcquisitionRules.level(u,"costumes",13));assertEquals(0,AcquisitionRules.level(u,"user_unit",1));
    }
    @Test void encoreDoesNotCreditDisabledHistoricalPass(){
        s.events.setStarPass(false,null,null);var u=user();u.put("user_event_point",new ArrayList<>(List.of(obj("s_EventType","Pass","i_DataID",13,"i_Version",1,"i_Point",800))));
        u.put("user_music",new ArrayList<>(List.of(obj("i_id",201,"i_Level",1,"b_EncoreBonusAppear",1,"i_EncoreBonusFollowerId",201,"l_EncoreBonusActivateTime",100))));u.put("user_follower",new ArrayList<>(List.of(obj("i_id",201,"i_Level",1))));s.state.saveUser(u);
        ok("getMusicReward","i_ids",List.of(201));assertEquals(800,integer(map(list(user().get("user_event_point")).getFirst()).get("i_Point")));
    }
    @Test void rankingNeverFabricatesBots(){
        s.events.setEventRankingEnabled(true);rejected("getEventMain");rejected("getEventRank");
    }
    @Test void malformedShopConfigurationAndIdsCannotChargeOrGrant(){
        var game=map(read(root.resolve("gamedata/game_data.json")));
        for(Object raw:list(game.get("12")))if(integer(map(raw).get("1"))==31)map(raw).put("34","bad");
        write(root.resolve("gamedata/game_data.json"),game);rejected("buyShop","idx",31);rejected("buyShop","idx",31.5);rejected("getSamSeckReward","i_id",1.5);
    }
}

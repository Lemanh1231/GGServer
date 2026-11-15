package emu.leman.ggserver.game.social;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.game.account.AccountModule;
import emu.leman.ggserver.game.content.ContentModule;
import emu.leman.ggserver.game.economy.EconomyModule;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
import static emu.leman.ggserver.util.Json.*;

/** Phase-one regressions; remaining audit-prefixed cases characterize deferred chat/save defects. */
class FollowerAuditReproductionTest {
    @TempDir Path root;
    Services s;
    @BeforeEach void setup() throws Exception {
        Path resources=Path.of(System.getProperty("follower.audit.resources",
                "resources"));
        for(String file:List.of("gamedata/game_data.json","gamedata/tour_drop_weights.json","schema/schema.json")) {
            Path target=root.resolve(file); Files.createDirectories(target.getParent());
            Files.copy(resources.resolve(file),target);
        }
        s=new Services(root);
        new SocialModule(s).register(); new AccountModule(s).register();
        new EconomyModule(s).register(); new ContentModule(s).register();
        Map<String,Object> u=s.state.createUser("audit","audit-device");
        u.put("user_follower",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1,"i_BonusLevel",0))));
        u.put("user_follower_profile",new ArrayList<>(List.of(SocialFollowers.newProfile(1))));
        u.put("user_follower_giftitem",new ArrayList<>(List.of(obj("i_id",1,"i_Value",4),obj("i_id",2,"i_Value",3))));
        u.put("user_messenger",new ArrayList<>()); u.put("user_follower_quest",new ArrayList<>());
        s.state.saveUser(u);
    }
    @AfterEach void close() { if(s!=null) s.close(); }
    Map<String,Object> user() { return s.state.getUser("audit"); }
    Object call(String name,Map<String,Object> p) {
        var result=s.registry.handle(name,obj("data",p),obj("uuid","audit"));
        assertEquals(0,integer(result.error().get("code"))); return result.data();
    }
    void reject(String name,Map<String,Object> p) {
        String before=stringify(user());
        var result=s.registry.handle(name,obj("data",p),obj("uuid","audit"));
        assertNotEquals(0,integer(result.error().get("code")));
        assertEquals(before,stringify(user()),"Rejected requests must not persist mutations");
    }
    Map<String,Object> row(String key,String idKey,int id) {
        return SocialFollowers.find(list(user().get(key)),idKey,id);
    }
    @Test void invalidGiftDoesNotCreateFollowerOrProfile() {
        assertNull(row("user_follower","i_id",15));
        reject("setFollowerProfileGift",obj("profile_id",15,"gift_id",999999,"use_gitf_value",1));
        assertNull(row("user_follower","i_id",15));
        assertNull(row("user_follower_profile","i_id",15));
        assertNull(row("user_follower_giftitem","i_id",999999));
    }
    @Test void unknownProfileCannotUseFallbackExp() {
        reject("setFollowerProfileGift",obj("profile_id",999999,"gift_id",1,"use_gitf_value",1));
        assertNull(row("user_follower","i_id",999999));
    }
    @Test void giftMustBeListedForProfile() {
        // profile 1 permits gifts 1,3; gift 2 is not in table28.s_GiftItemID.
        reject("setFollowerProfileGift",obj("profile_id",1,"gift_id",2,"use_gitf_value",1));
        assertEquals(3,lng(row("user_follower_giftitem","i_id",2).get("i_Value")));
        assertEquals(0,lng(row("user_follower_profile","i_id",1).get("d_Exp")));
    }
    @Test void excessiveGiftQuantityIsRejectedAtomically() {
        reject("setFollowerProfileGift",obj("profile_id",1,"gift_id",1,"use_gitf_value",999));
        assertEquals(4,lng(row("user_follower_giftitem","i_id",1).get("i_Value")));
        assertEquals(0,lng(row("user_follower_profile","i_id",1).get("d_Exp")));
    }
    @Test void unownedProfileCannotClaimLevelOneReward() {
        long before=lng(map(user().get("userdata")).get("u_cp"));
        reject("setUserFollowerProfileReward",obj("i_id",15,"s_level","1"));
        assertEquals(before,lng(map(user().get("userdata")).get("u_cp")));
        assertNull(row("user_follower_profile","i_id",15));
        assertNull(row("user_follower","i_id",15));
    }
    @Test void questRequiresUnlockAndCompletedCondition() {
        double before=dbl(map(user().get("userdata")).get("u_like"));
        Map<String,Object> result=map(call("setUserFollowerQuest",obj("i_CurrentID",1,"i_SubID",1,"d_ConditionValue",0)));
        assertEquals(0,dbl(result.get("d_ConditionValue1")));
        assertEquals(0,integer(result.get("i_RewardReceived1")));
        assertTrue(list(result.get("reward_data")).isEmpty());
        assertEquals(before,dbl(map(user().get("userdata")).get("u_like")));
        Map<String,Object> u=user();map(list(u.get("user_follower")).getFirst()).put("i_Level",250);s.state.saveUser(u);
        result=map(call("setUserFollowerQuest",obj("i_CurrentID",1,"i_SubID",1,"d_ConditionValue",4)));
        assertTrue(list(result.get("reward_data")).isEmpty());
        result=map(call("setUserFollowerQuest",obj("i_CurrentID",1,"i_SubID",1,"d_ConditionValue",5)));
        assertEquals(1,integer(result.get("i_RewardReceived1")));assertFalse(list(result.get("reward_data")).isEmpty());
        result=map(call("setUserFollowerQuest",obj("i_CurrentID",1,"i_SubID",1,"d_ConditionValue",5)));
        assertTrue(list(result.get("reward_data")).isEmpty());
    }
    @Test void questCannotJumpToFutureConfiguredId() {
        Map<String,Object> result=map(call("setUserFollowerQuest",obj("i_CurrentID",20,"i_SubID",1,"d_ConditionValue",0)));
        assertEquals(1,integer(result.get("i_CurrentID")));
        assertTrue(list(result.get("reward_data")).isEmpty());
    }
    @Test void staleMessengerSaveCannotRewindProgress() {
        Map<String,Object> u=user(); u.put("user_messenger",new ArrayList<>(List.of(obj(
                "i_MessengerChatRoomId",1,"s_UnlockGroupList","1,3","i_LastConfirmIndex",20,"l_UpdateTimeTicks",200)))); s.state.saveUser(u);
        call("userSave",obj("user_messenger",List.of(obj("i_MessengerChatRoomId",1,
                "s_UnlockGroupList","1","i_LastConfirmIndex",2,"l_UpdateTimeTicks",100))));
        Map<String,Object> room=row("user_messenger","i_MessengerChatRoomId",1);
        assertEquals("1,3",room.get("s_UnlockGroupList")); assertEquals(20,integer(room.get("i_LastConfirmIndex")));
    }
    @Test void messengerRejectsUnknownRoomAndGroup() {
        call("userSave",obj("user_messenger",List.of(obj("i_MessengerChatRoomId",999999,
                "s_UnlockGroupList","999999","i_LastConfirmIndex",Integer.MAX_VALUE))));
        assertNull(row("user_messenger","i_MessengerChatRoomId",999999));
    }
    @Test void messengerNormalizationDoesNotInventReadHistory() {
        Map<String,Object> u=user();
        list(u.get("user_follower")).add(obj("i_id",4,"i_Level",1)); s.state.saveUser(u);
        call("userSave",obj());
        assertNull(row("user_messenger","i_MessengerChatRoomId",1));
        // Native Init treats every element except the last as completed, not pending unlocks.
    }
    @Test void auditClientSaveAcceptsFollowerBeyondCatalogMaxWithoutPayment() {
        long before=lng(map(user().get("userdata")).get("u_cp"));
        call("userSave",obj("user_follower",List.of(obj("i_id",15,"i_Level",Integer.MAX_VALUE,"i_BonusLevel",Integer.MAX_VALUE))));
        assertEquals(Integer.MAX_VALUE,integer(row("user_follower","i_id",15).get("i_Level")));
        assertEquals(before,lng(map(user().get("userdata")).get("u_cp")));
    }
    @Test void profileAdCannotCreateUnownedFollower() {
        reject("setAdReward",obj("i_id",1,"param1",15));
        assertNull(row("user_follower","i_id",15));
    }
    @Test void encoreCannotRewardMissingSongOrReplay() {
        Map<String,Object> u=user(); u.put("user_music",new ArrayList<>()); s.state.saveUser(u);
        double before=dbl(map(user().get("userdata")).get("u_candy"));
        reject("getMusicReward",obj("i_ids",List.of(999999),"i_levels",List.of(1)));
        u=user();u.put("user_music",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1,"b_EncoreBonusAppear",1,"i_EncoreBonusFollowerId",1))));s.state.saveUser(u);
        reject("getMusicReward",obj("i_ids",List.of(1,1)));
        reject("getMusicReward",obj("i_ids",List.of(1,999999)));
        call("getMusicReward",obj("i_ids",List.of(1),"i_levels",List.of(999999)));
        double once=dbl(map(user().get("userdata")).get("u_candy"));assertTrue(once>before);
        reject("getMusicReward",obj("i_ids",List.of(1)));
        assertEquals(once,dbl(map(user().get("userdata")).get("u_candy")));
        assertEquals(lng(s.gameData.row(11,1).get("7")),lng(row("user_follower_profile","i_id",1).get("d_Exp")));
    }
    @Test void validAliasGiftAndRewardRemainCumulativeAndIdempotentAcrossRestart() {
        call("setFollowerProfileGift",obj("profile_id",201,"gift_id",1,"use_gitf_value",4));
        assertEquals(80,lng(row("user_follower_profile","i_id",1).get("d_Exp")));
        assertEquals(1,integer(row("user_follower","i_id",1).get("i_Level")));
        long before=lng(map(user().get("userdata")).get("u_cp"));
        call("setUserFollowerProfileReward",obj("i_id",201,"s_level","1,1"));
        long once=lng(map(user().get("userdata")).get("u_cp")); assertTrue(once>before);
        s.close(); s=new Services(root); new SocialModule(s).register();
        call("setUserFollowerProfileReward",obj("i_id",1,"s_level","1"));
        assertEquals(once,lng(map(user().get("userdata")).get("u_cp")));
        assertEquals(80,lng(row("user_follower_profile","i_id",1).get("d_Exp")));
    }
    void prepareEncore(long activation) {
        Map<String,Object> u=user();u.put("user_music",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1,
                "b_EncoreBonusAppear",1,"i_EncoreBonusFollowerId",1,"l_EncoreBonusActivateTime",activation))));s.state.saveUser(u);
    }
    @Test void encoreClaimMarkerSurvivesStaleClientSaveAndRestart() {
        prepareEncore(100);call("getMusicReward",obj("i_ids",List.of(1)));
        call("userSave",obj("user_music",List.of(obj("i_id",1,"i_Level",1,"b_EncoreBonusAppear",1,
                "i_EncoreBonusFollowerId",1,"l_EncoreBonusActivateTime",100))));
        s.close();s=new Services(root);new ContentModule(s).register();
        reject("getMusicReward",obj("i_ids",List.of(1)));
        prepareEncore(101);reject("getMusicReward",obj("i_ids",List.of(1)));
        assertEquals(50,lng(row("user_follower_profile","i_id",1).get("d_Exp")));
    }
    @Test void concurrentEncoreClaimsGrantOnce() throws Exception {
        prepareEncore(100);
        try(ExecutorService pool=Executors.newFixedThreadPool(8)) {
            List<Callable<Integer>> tasks=new ArrayList<>();
            for(int i=0;i<16;i++) tasks.add(()->integer(s.registry.handle("getMusicReward",obj("data",obj("i_ids",List.of(1))),obj("uuid","audit")).error().get("code")));
            int success=0;for(Future<Integer> result:pool.invokeAll(tasks)) if(result.get()==0) success++;
            assertEquals(1,success);
        }
        assertEquals(50,lng(row("user_follower_profile","i_id",1).get("d_Exp")));
    }
    @Test void failedEncoreSaveRollsBackCurrencyExpAndClaimTogether() throws Exception {
        prepareEncore(100);String before=stringify(user());
        try(var db=java.sql.DriverManager.getConnection("jdbc:sqlite:"+root.resolve("data/database.db"));var sql=db.createStatement()) {
            sql.execute("CREATE TRIGGER encore_fail BEFORE UPDATE OF u_candy ON user_data BEGIN SELECT RAISE(ABORT,'audit'); END");
            assertThrows(IllegalStateException.class,()->call("getMusicReward",obj("i_ids",List.of(1))));
            assertEquals(before,stringify(user()));
            sql.execute("DROP TRIGGER encore_fail");
        }
        call("getMusicReward",obj("i_ids",List.of(1)));
        assertEquals(50,lng(row("user_follower_profile","i_id",1).get("d_Exp")));
    }
    @Test void invalidGiftQuantitiesAndInactiveDefinitionsDoNotMutate() {
        reject("setFollowerProfileGift",obj());
        for(Object count:List.of(0,-1,"1.5","2147483648"))
            reject("setFollowerProfileGift",obj("profile_id",1,"gift_id",1,"use_gitf_value",count));
        s.gameData.row(30,1).put("18",0);
        reject("setFollowerProfileGift",obj("profile_id",1,"gift_id",1,"use_gitf_value",1));
    }
    @Test void profileAdAliasAndCooldownDoNotCreateFollowerOrExtraExp() {
        call("setAdReward",obj("i_id",1,"param1",201));
        long exp=lng(row("user_follower_profile","i_id",1).get("d_Exp"));assertTrue(exp>0);
        call("setAdReward",obj("i_id",1,"param1",201));
        assertEquals(exp,lng(row("user_follower_profile","i_id",1).get("d_Exp")));
        assertNull(row("user_follower","i_id",201));
    }
    @Test void milestoneUsesAllRowsInRewardGroupAndCumulativeExpNotClaimedLevel() {
        Map<String,Object> u=user();rowFrom(u,"user_follower_profile",1).put("i_Level",20);s.state.saveUser(u);
        assertTrue(list(call("setUserFollowerProfileReward",obj("i_id",1,"s_level","20"))).isEmpty());
        Map<String,Object> milestone=s.gameData.table(31).stream().filter(r->integer(r.get("2"))==1&&integer(r.get("3"))==1).findFirst().orElseThrow();
        int group=integer(milestone.get("5"));
        list(s.gameData.data().get("13")).add(obj("1",99999999,"2",group,"3",11,"4",1,"5",2));
        List<Object> result=list(call("setUserFollowerProfileReward",obj("i_id",1,"s_level","1")));
        assertEquals(2,list(map(result.getFirst()).get("reward_data")).size());
        assertEquals(6,lng(row("user_follower_giftitem","i_id",1).get("i_Value")));
    }
    static Map<String,Object> rowFrom(Map<String,Object> u,String key,int id) {
        return SocialFollowers.find(list(u.get(key)),"i_id",id);
    }
    @Test void questRejectsNonfiniteProgressAndInfiniteReadDoesNotSkip() {
        Map<String,Object> u=user();rowFrom(u,"user_follower",1).put("i_Level",250);s.state.saveUser(u);
        for(double value:new double[]{Double.NaN,Double.POSITIVE_INFINITY,-1}) {
            Map<String,Object> result=map(call("setUserFollowerQuest",obj("i_CurrentID",1,"i_SubID",1,"d_ConditionValue",value)));
            assertTrue(list(result.get("reward_data")).isEmpty());
        }
        u=user();u.put("user_follower_quest",new ArrayList<>(List.of(SocialFollowers.newQuest(42,41,0))));s.state.saveUser(u);
        Map<String,Object> result=map(call("setFollowerQuestInfinite",obj()));
        assertEquals(42,integer(map(result.get("user_follower_quest")).get("i_CurrentID")));
    }
    @Test void mongoEncoreAndGiftClaimsSurviveReopenWithoutReplay() throws Exception {
        s.close();s=null;
        var mongo=new de.bwaldvogel.mongo.MongoServer(new de.bwaldvogel.mongo.backend.memory.MemoryBackend());
        var address=mongo.bind();
        var config=emu.leman.ggserver.config.ServerConfig.defaults(root,obj("database",obj("backend","mongo","name","follower_test",
                "uri","mongodb://"+address.getHostString()+":"+address.getPort()+"/?serverSelectionTimeoutMS=5000")));
        try {
            s=new Services(config);new SocialModule(s).register();new ContentModule(s).register();
            Map<String,Object> u=s.state.createUser("audit","audit-device");
            u.put("user_follower",new ArrayList<>(List.of(obj("i_id",1,"i_Level",250))));
            u.put("user_follower_profile",new ArrayList<>(List.of(SocialFollowers.newProfile(1))));
            u.put("user_follower_giftitem",new ArrayList<>(List.of(obj("i_id",1,"i_Value",4))));s.state.saveUser(u);
            call("setFollowerProfileGift",obj("profile_id",201,"gift_id",1,"use_gitf_value",4));
            call("setUserFollowerProfileReward",obj("i_id",201,"s_level","1"));
            prepareEncore(100);call("getMusicReward",obj("i_ids",List.of(1)));
            long cp=lng(map(user().get("userdata")).get("u_cp"));
            s.close();s=new Services(config);new SocialModule(s).register();new ContentModule(s).register();
            reject("getMusicReward",obj("i_ids",List.of(1)));
            call("setUserFollowerProfileReward",obj("i_id",1,"s_level","1"));
            assertEquals(cp,lng(map(user().get("userdata")).get("u_cp")));
            assertEquals(130,lng(row("user_follower_profile","i_id",1).get("d_Exp")));
            assertEquals(0,lng(row("user_follower_giftitem","i_id",1).get("i_Value")));
        } finally {if(s!=null){s.close();s=null;}mongo.shutdownNow();}
    }
    @Test void failedGiftSaveDoesNotConsumeInventoryOrPersistExp() throws Exception {
        String before=stringify(user());
        try(var db=java.sql.DriverManager.getConnection("jdbc:sqlite:"+root.resolve("data/database.db"));var sql=db.createStatement()) {
            sql.execute("CREATE TRIGGER gift_fail BEFORE UPDATE OF u_cp ON user_data BEGIN SELECT RAISE(ABORT,'audit'); END");
            assertThrows(IllegalStateException.class,()->call("setFollowerProfileGift",obj("profile_id",1,"gift_id",1,"use_gitf_value",1)));
            assertEquals(before,stringify(user()));sql.execute("DROP TRIGGER gift_fail");
        }
        call("setFollowerProfileGift",obj("profile_id",1,"gift_id",1,"use_gitf_value",1));
        assertEquals(3,lng(row("user_follower_giftitem","i_id",1).get("i_Value")));
        assertEquals(20,lng(row("user_follower_profile","i_id",1).get("d_Exp")));
    }
    @Test void concurrentAliasMilestoneAndQuestClaimsPayOnce() throws Exception {
        Map<String,Object> u=user();rowFrom(u,"user_follower",1).put("i_Level",250);s.state.saveUser(u);
        long before=lng(map(user().get("userdata")).get("u_cp"));
        double like=dbl(map(user().get("userdata")).get("u_like"));
        try(ExecutorService pool=Executors.newFixedThreadPool(8)) {
            List<Callable<Object>> jobs=new ArrayList<>();
            for(int i=0;i<16;i++) {
                int id=i%2==0?1:201;
                jobs.add(()->call("setUserFollowerProfileReward",obj("i_id",id,"s_level","1")));
                jobs.add(()->call("setUserFollowerQuest",obj("i_CurrentID",1,"i_SubID",1,"d_ConditionValue",5)));
            }
            for(var result:pool.invokeAll(jobs))result.get();
        }
        assertEquals(before+5,lng(map(user().get("userdata")).get("u_cp")));
        assertEquals(like+3000,dbl(map(user().get("userdata")).get("u_like")));
    }
    @Test void unavailableMilestoneDoesNotCreateMissingProfileOrLowerHistoricalFields() {
        Map<String,Object> u=user();u.put("user_follower_profile",new ArrayList<>());s.state.saveUser(u);
        String before=stringify(user());
        assertTrue(list(call("setUserFollowerProfileReward",obj("i_id",1,"s_level","20"))).isEmpty());
        assertEquals(before,stringify(user()));
        u=user();u.put("user_follower_profile",new ArrayList<>(List.of(obj("i_id",1,"i_Level",20,"d_Exp",0,"i_AddCandy",100))));s.state.saveUser(u);
        call("setUserFollowerProfileReward",obj("i_id",1,"s_level","1"));
        assertEquals(20,integer(row("user_follower_profile","i_id",1).get("i_Level")));
        assertEquals(100,integer(row("user_follower_profile","i_id",1).get("i_AddCandy")));
    }
    @Test void giftCannotMintMissingInventoryAndInactiveOwnerCannotUseSharedProfile() {
        Map<String,Object> u=user();u.put("user_follower_giftitem",new ArrayList<>());s.state.saveUser(u);
        reject("setFollowerProfileGift",obj("profile_id",1,"gift_id",1,"use_gitf_value",1));
        s.gameData.row(5,1).put("44",0);
        reject("setAdReward",obj("i_id",1,"param1",201));
        reject("setUserFollowerProfileReward",obj("i_id",1,"s_level","1"));
    }
}

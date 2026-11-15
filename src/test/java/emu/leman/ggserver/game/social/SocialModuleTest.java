package emu.leman.ggserver.game.social;

import emu.leman.ggserver.Services;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
import static emu.leman.ggserver.util.Json.*;
import static emu.leman.ggserver.game.social.SocialFollowers.*;

class SocialModuleTest {
    @TempDir Path root;
    Services services;
    SocialModule social;
    @BeforeEach void setup() {
        write(root.resolve("gamedata/game_data.json"),obj(
            "5",List.of(obj("1",1,"47",1),obj("1",201,"47",1),obj("1",204,"47",204)),
            "2",List.of(obj("1",204)),"3",List.of(obj("1",204)),"4",List.of(obj("1",204)),
            "7",List.of(obj("1",204)),"20",List.of(obj("1",204)),
            "28",List.of(obj("1",1,"14",1,"15","1")),
            "30",List.of(obj("1",1,"2",1,"3",50)),
            "31",List.of(obj("1",1,"2",1,"3",1,"4",0,"5",0,"6","","7",0),obj("1",2,"2",1,"3",2,"4",50,"5",600,"6","","7",2),obj("1",3,"2",1,"3",3,"4",150,"5",601,"6","story","7",3)),
            "13",List.of(obj("1",500,"2",600,"3",1,"4",1,"5",10),obj("1",501,"2",601,"3",11,"4",1,"5",2)),
            "26",List.of(obj("1",1,"29",1,"4","ADViewCount","5",3,"7","TapCount","8",100,"13",600,"14",600,"15",600),obj("1",2,"29",1,"13",600),obj("1",902,"29",2,"2",1,"3",1),obj("1",903,"29",2,"2",2,"3",100))));
        services=new Services(root); social=new SocialModule(services); social.register(); services.state.createUser("a","device-a");
    }
    @AfterEach void close() { services.close(); }
    Object command(String name,Map<String,Object> p) { return services.registry.handle(name,p,obj("uuid","a")).data(); }
    Map<String,Object> user() { return services.state.getUser("a"); }
    void save(Map<String,Object> user) { services.state.saveUser(user); }
    @Test void registersEveryPythonCommand() {
        assertTrue(services.registry.commands().containsAll(List.of("setFollowerProfileGift","setUserFollowerProfileReward","setFollowerQuestInfinite","setUserFollowerQuest","getPostTime","getPost","providePost","readPost","deletePost")));
    }
    @Test void giftsUseCumulativeExpAndNeverStageLevel() {
        Map<String,Object> user=user(); user.put("user_follower",new ArrayList<>(List.of(obj("i_id",1,"i_Level",2000)))); user.put("user_follower_giftitem",new ArrayList<>(List.of(obj("i_id",1,"i_Value",4)))); save(user);
        Map<String,Object> result=map(command("setFollowerProfileGift",obj("profile_id",1,"gift_id",1,"use_gitf_value",3)));
        assertEquals(3,integer(map(result.get("user_follower_profile")).get("i_Level")));
        assertEquals(150,lng(map(result.get("user_follower_profile")).get("d_Exp")));
        assertEquals(5,lng(map(result.get("user_follower_profile")).get("i_AddCandy")));
        assertEquals(2000,integer(find(rows(user(),"user_follower"),"i_id",1).get("i_Level")));
        command("setFollowerProfileGift",obj("profile_id",1,"gift_id",1,"use_gitf_value",999));
        assertEquals(1,lng(find(rows(user(),"user_follower_giftitem"),"i_id",1).get("i_Value")));
        command("setFollowerProfileGift",obj("use_gitf_value",-1));
        assertEquals(1,lng(find(rows(user(),"user_follower_giftitem"),"i_id",1).get("i_Value")));
    }
    @Test void rewardClaimsAliasAndDuplicatesAreIdempotent() {
        Map<String,Object> user=user(); user.put("user_follower",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1))));user.put("user_follower_profile",new ArrayList<>(List.of(obj("i_id",1,"i_Level",2,"d_Exp",50)))); save(user);
        long before=lng(map(user.get("userdata")).get("u_cp"));
        List<Object> first=list(command("setUserFollowerProfileReward",obj("i_id",201,"s_level","2,2,3")));
        assertEquals(2,first.size()); assertEquals(1,list(map(first.getFirst()).get("reward_data")).size()); assertTrue(list(map(first.getLast()).get("reward_data")).isEmpty());
        command("setUserFollowerProfileReward",obj("i_id",1,"s_level","2"));
        assertEquals(before+10,lng(map(user().get("userdata")).get("u_cp")));
    }
    @Test void messengerPreservesHistoryWithoutInventingCompletedGroupsFromFollowerOwnership() {
        Map<String,Object> user=obj("user_follower",new ArrayList<>(List.of(obj("i_id",1,"i_Level",10),obj("i_id",4,"i_Level",1))),"user_messenger",new ArrayList<>(List.of(room(1,"1,75"))));
        syncMessenger(user); Map<String,Object> joy=find(rows(user,"user_messenger"),"i_MessengerChatRoomId",1);
        assertEquals("1,75",joy.get("s_UnlockGroupList"));
        rows(user,"user_follower").add(obj("i_id",201,"i_Level",700)); rows(user,"user_follower").add(obj("i_id",202,"i_Level",1));
        syncMessenger(user); assertNull(find(rows(user,"user_messenger"),"i_MessengerChatRoomId",16));
        joy.put("s_UnlockGroupList","1,111,130,136"); syncMessenger(user); assertTrue(str(joy.get("s_UnlockGroupList")).endsWith(",136"));
        mergeMessenger(user,List.of(obj("i_MessengerChatRoomId",1,"i_LastConfirmIndex",8)));
        assertNull(find(rows(user,"user_messenger"),"i_MessengerChatRoomId",17)); assertEquals(8,integer(joy.get("i_LastConfirmIndex")));
    }
    @Test void messengerRejectsStaleHistoryButAllowsNewGroupIndexResetAndNativeSentinel() {
        var user=obj("user_messenger",new ArrayList<>(List.of(room(1,"1,4"))));
        var joy=map(rows(user,"user_messenger").getFirst()); joy.put("i_LastConfirmIndex",12);
        mergeMessenger(user,List.of(obj("i_MessengerChatRoomId",1,"s_UnlockGroupList","1","i_LastConfirmIndex",50)));
        assertEquals("1,4",joy.get("s_UnlockGroupList")); assertEquals(12,lng(joy.get("i_LastConfirmIndex")));
        mergeMessenger(user,List.of(obj("i_MessengerChatRoomId",1,"s_UnlockGroupList","1,4","i_LastConfirmIndex",2)));
        assertEquals(12,lng(joy.get("i_LastConfirmIndex")));
        mergeMessenger(user,List.of(obj("i_MessengerChatRoomId",1,"s_UnlockGroupList","1,4,7","i_LastConfirmIndex",-1)));
        assertEquals("1,4,7",joy.get("s_UnlockGroupList")); syncMessenger(user); assertEquals(-1,lng(joy.get("i_LastConfirmIndex")));
        mergeMessenger(user,List.of(obj("i_MessengerChatRoomId",1,"s_UnlockGroupList","1,7,4","i_LastConfirmIndex",99)));
        assertEquals("1,4,7",joy.get("s_UnlockGroupList"));
    }
    @Test void messengerRejectsMalformedHistoryAndOutOfRangeNativeFields() {
        var user=obj("user_messenger",new ArrayList<>());
        for(Object text:List.of("1,bad,4","1,,4","1,4,999999999999999999999","1,1","1,2","",42)) {
            mergeMessenger(user,List.of(obj("i_MessengerChatRoomId",1,"s_UnlockGroupList",text,"i_LastConfirmIndex",0)));
            assertTrue(rows(user,"user_messenger").isEmpty());
        }
        for(Object index:List.of(-2,2147483648L,0.5,Double.NaN)) {
            mergeMessenger(user,List.of(obj("i_MessengerChatRoomId",1,"s_UnlockGroupList","1","i_LastConfirmIndex",index)));
            assertTrue(rows(user,"user_messenger").isEmpty());
        }
        mergeMessenger(user,List.of(obj("i_MessengerChatRoomId",1,"i_LastConfirmIndex",0)));
        assertTrue(rows(user,"user_messenger").isEmpty());
        mergeMessenger(user,List.of(obj("i_MessengerChatRoomId",1,"s_UnlockGroupList","1","i_LastConfirmIndex",-1,"l_UpdateTimeTicks",200)));
        mergeMessenger(user,List.of(obj("i_MessengerChatRoomId",1,"s_UnlockGroupList","1,4","i_LastConfirmIndex",0,"l_UpdateTimeTicks",100)));
        var joy=map(rows(user,"user_messenger").getFirst());
        assertEquals("1,4",joy.get("s_UnlockGroupList")); assertEquals(200,lng(joy.get("l_UpdateTimeTicks")));
    }
    @Test void questNormalizesMergesAdsOnlyAndRejectsDelayedClaimReplay() {
        Map<String,Object> user=user(); user.put("user_follower_quest",new ArrayList<>()); social.followers.normalizeQuest(user);
        Map<String,Object> quest=map(rows(user,"user_follower_quest").getFirst()); assertEquals(3,dbl(quest.get("d_ConditionValue1"))); assertEquals(0,dbl(quest.get("d_ConditionValue2")));
        social.followers.mergeQuest(user,List.of(obj("i_CurrentID",1,"d_ConditionValue2",100))); save(user);
        long before=lng(map(user.get("userdata")).get("u_cp"));
        for(int sub=1;sub<=3;sub++) command("setUserFollowerQuest",obj("i_CurrentID",1,"i_SubID",sub));
        Map<String,Object> replay=map(command("setUserFollowerQuest",obj("i_CurrentID",1,"i_SubID",3)));
        assertEquals(2,integer(replay.get("i_CurrentID"))); assertTrue(list(replay.get("reward_data")).isEmpty());
        assertEquals(before+30,lng(map(user().get("userdata")).get("u_cp")));
    }
    @Test void infiniteQuestsUseOwnedFollowerEligibility() {
        Map<String,Object> user=obj("user_follower",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1))));
        assertArrayEquals(new int[]{902,1},social.followers.nextQuest(user,42));
        assertArrayEquals(new int[]{902,1},social.followers.nextQuest(user,902));
    }
    @Test void clientCannotResynchronizeToFutureQuest() {
        Map<String,Object> result=map(command("setUserFollowerQuest",obj("i_CurrentID",2,"i_SubID",1)));
        assertEquals(1,integer(result.get("i_CurrentID")));
        assertEquals(0,list(result.get("reward_data")).size());
        result=map(command("setUserFollowerQuest",obj("i_CurrentID",2,"i_SubID",1,"d_ConditionValue",25)));
        assertTrue(list(result.get("reward_data")).isEmpty());
        assertEquals(3,dbl(result.get("d_ConditionValue1")));
    }
    @Test void inconsistentWelcomeFlagRetainsPythonInsertionBehavior() {
        Map<String,Object> user=user(); user.put("welcome_post_sent",false); user.put("deleted_post_indices",new ArrayList<>(List.of(1))); save(user);
        List<Object> posts=list(map(command("getPost",obj())).get("post_list"));
        assertEquals(1,posts.size()); assertEquals(1,lng(map(posts.getFirst()).get("idx")));
        // The next read purges the newly inserted welcome because Python retains the tombstone.
        assertTrue(list(map(command("getPost",obj())).get("post_list")).isEmpty());
    }
    @Test void welcomeClaimReadDeleteAndRestartStayIdempotent() {
        List<Object> posts=list(map(command("getPost",obj())).get("post_list")); assertEquals(1,posts.size());
        long before=lng(map(user().get("userdata")).get("u_cp"));
        command("readPost",obj("idx",1)); assertEquals(2,list(command("providePost",obj("idx",1))).size());
        assertTrue(list(command("providePost",obj("idx",1))).isEmpty()); assertEquals(before+1000,lng(map(user().get("userdata")).get("u_cp")));
        command("deletePost",obj("type",1)); assertTrue(list(map(command("getPost",obj())).get("post_list")).isEmpty());
        services.close(); services=new Services(root); social=new SocialModule(services); social.register();
        assertTrue(list(map(command("getPost",obj())).get("post_list")).isEmpty());
    }
    @Test void broadcastsRespectAccountAgeExpiryAndDeletion() {
        long now=System.currentTimeMillis()/1000; Map<String,Object> user=user(); user.put("created_at",now-100); user.put("welcome_post_sent",true); save(user);
        write(root.resolve("broadcast_posts.json"),List.of(mail(101,now-200,now+100,false),mail(102,now-200,now+100,true),mail(103,now-50,now-1,true),mail(104,now-50,now+100,false)));
        List<Object> posts=list(map(command("getPost",obj())).get("post_list")); assertEquals(List.of(102L,104L),posts.stream().map(v->lng(map(v).get("idx"))).toList());
        command("providePost",obj("idx",104)); command("deletePost",obj("idx",104)); assertEquals(1,list(map(command("getPost",obj())).get("post_list")).size());
        command("deletePost",obj("type",1)); assertEquals(1,list(map(command("getPost",obj())).get("post_list")).size()); // unclaimed reward retained
    }
    @Test void sendUsesGlobalTombstonesAndPersistedSequenceAndAlreadyGrantedMarker() {
        Map<String,Object> user=user(); user.put("deleted_post_indices",new ArrayList<>(List.of(800))); save(user);
        Map<String,Object> post=social.posts.sendPost("a","Title","Memo",List.of(obj("i_RewardType",1,"i_RewardId",1,"d_RewardQuantity",100,"already_granted",true)),1,false);
        assertEquals(801,lng(post.get("idx"))); long before=lng(map(user().get("userdata")).get("u_cp"));
        assertEquals(1,list(command("providePost",obj("idx",801))).size()); assertEquals(before,lng(map(user().get("userdata")).get("u_cp")));
        Map<String,Object> broadcast=social.posts.sendPost(null,"Global","",List.of(),1,true); assertEquals(802,lng(broadcast.get("idx")));
        assertTrue(list(read(root.resolve("broadcast_posts.json"))).size()>0);
    }
    @Test void concurrentClaimsGrantExactlyOnce() throws Exception {
        command("getPost",obj()); long before=lng(map(user().get("userdata")).get("u_cp"));
        try(ExecutorService pool=Executors.newFixedThreadPool(8)) {
            List<Callable<Object>> calls=new ArrayList<>(); for(int i=0;i<20;i++) calls.add(()->command("providePost",obj("idx",1)));
            int rewards=0; for(Future<Object> result:pool.invokeAll(calls)) rewards+=list(result.get()).size(); assertEquals(2,rewards);
        }
        assertEquals(before+1000,lng(map(user().get("userdata")).get("u_cp")));
    }
    @Test void mailboxSupportsAllInventoryGrantsAndExactLikeGp() {
        Map<String,Object> user=user(); user.put("welcome_post_sent",true); user.put("areas",obj("1",obj("s_Gp1","100000000000000000000000000000000000000","d_Like",1e38)));
        map(user.get("userdata")).put("u_like",1e38); save(user);
        List<Object> items=new ArrayList<>();
        for(int type:new int[]{2,3,4,5,7,9}) items.add(obj("i_RewardType",type,"i_RewardId",204,"d_RewardQuantity",type==7?2:1));
        items.add(obj("i_RewardType",1,"i_RewardId",3,"d_RewardQuantity",10));
        Map<String,Object> post=social.posts.sendPost("a","Items","",items,1,false);
        command("providePost",obj("idx",post.get("idx"))); user=user();
        for(String key:List.of("user_music","costumes","user_prop","user_follower","user_unit","user_guitar")) assertNotNull(find(rows(user,key),"i_id",204),key);
        assertNull(find(rows(user,"user_messenger"),"i_MessengerChatRoomId",204)); // Native unlocks only after group 118 is completed.
        assertEquals("100000000000000000000000000000000000010",str(map(map(user.get("areas")).get("1")).get("s_Gp1")));
        command("providePost",obj("idx",post.get("idx"))); assertEquals(2,integer(find(rows(user(),"user_unit"),"i_id",204).get("i_Level")));
    }
    @Test void failedSaveRollsBackGrantsAndClaimMarkerTogether() throws Exception {
        command("getPost",obj()); long before=lng(map(user().get("userdata")).get("u_cp"));
        try(java.sql.Connection db=java.sql.DriverManager.getConnection("jdbc:sqlite:"+root.resolve("data/database.db")); java.sql.Statement sql=db.createStatement()) {
            sql.execute("CREATE TRIGGER social_fail BEFORE UPDATE OF u_cp ON user_data BEGIN SELECT RAISE(ABORT,'test failure'); END");
            assertThrows(IllegalStateException.class,()->command("providePost",obj("idx",1)));
            assertEquals(before,lng(map(user().get("userdata")).get("u_cp")));
            assertEquals(1,integer(map(rows(user(),"posts").getFirst()).get("have_reward")));
            sql.execute("DROP TRIGGER social_fail");
        }
        assertEquals(2,list(command("providePost",obj("idx",1))).size());
        assertEquals(before+1000,lng(map(user().get("userdata")).get("u_cp")));
    }
    @Test void fractionalLikeBuffAndTicketRewardsRetainSemantics() {
        Map<String,Object> user=user(); map(user.get("userdata")).put("u_like",0.25);
        SocialRewards.grant(user,1,3,0.5,false,true); assertEquals(0.75,dbl(map(user.get("userdata")).get("u_like")));
        SocialRewards.grant(user,6,2,100,false,true); long end=lng(find(rows(user,"user_buff"),"i_id",2).get("i_EndTime"));
        SocialRewards.grant(user,6,2,100,false,true); assertEquals(end+100,lng(find(rows(user,"user_buff"),"i_id",2).get("i_EndTime")));
        SocialRewards.grant(user,10,8,1,false,true); SocialRewards.grant(user,10,8,1,false,true); assertEquals(1,rows(user,"user_ticketcollection").size());
        SocialRewards.grant(user,11,4,3,false,false); assertEquals(3,lng(find(rows(user,"user_follower_giftitem"),"i_id",4).get("i_Value")));
    }
    @Test void ordinarySocialCurrencyRewardsDoNotCreateAnAdminReset() {
        // Fresh accounts intentionally require an initial reset. Isolate whether these grants add one.
        Map<String,Object> existing=user(); existing.put("needs_client_reset",false); save(existing);
        assertFalse(truth(user().get("needs_client_reset")),"fixture must start without a pending reset");
        for(boolean mailbox:new boolean[]{false,true}) for(boolean quest:new boolean[]{false,true}) {
            if(mailbox&&quest) continue;
            for(int id:new int[]{1,2,8,11}) {
                Map<String,Object> snapshot=obj("uuid","a","userdata",obj("u_cp",0,"u_candy",0.0,"u_like",0.0,"u_fans",0));
                SocialRewards.grant(snapshot,1,id,10,mailbox,quest);
                assertFalse(truth(snapshot.get("needs_client_reset")),"id="+id+", mailbox="+mailbox+", quest="+quest);
            }
        }
        for(boolean quest:new boolean[]{false,true}) {
            Map<String,Object> snapshot=obj("uuid","a","userdata",obj("u_like",0.0));
            SocialRewards.grant(snapshot,1,3,10,false,quest);
            assertFalse(truth(snapshot.get("needs_client_reset")));
        }
        command("providePost",obj("idx",1));
        assertFalse(truth(user().get("needs_client_reset")),"welcome CP/candy must not request RESET_device");
        command("setUserFollowerQuest",obj("i_CurrentID",1,"i_SubID",1));
        assertFalse(truth(user().get("needs_client_reset")),"quest CP must not request RESET_device");
    }
    @Test void mailboxLikeResetUsesIntegerDeltaAndPreservesPendingAdminReset() {
        Map<String,Object> existing=user(); existing.put("needs_client_reset",false); save(existing);
        assertFalse(truth(user().get("needs_client_reset")),"fixture must start without a pending reset");
        Map<String,Object> post=social.posts.sendPost("a","fraction","",List.of(obj("i_RewardType",1,"i_RewardId",3,"d_RewardQuantity",0.5)),1,false);
        command("providePost",obj("idx",post.get("idx")));
        assertFalse(truth(user().get("needs_client_reset")));
        post=social.posts.sendPost("a","aggregate","",List.of(obj("i_RewardType",1,"i_RewardId",3,"d_RewardQuantity",0.5),obj("i_RewardType",1,"i_RewardId",4,"d_RewardQuantity",0.5)),1,false);
        command("providePost",obj("idx",post.get("idx")));
        assertTrue(truth(user().get("needs_client_reset")));
        services.state.setLikeCurrency("a","100A"); Map<String,Object> snapshot=user();
        assertTrue(truth(snapshot.get("needs_client_reset")));
        Object forced=snapshot.get("force_server_like");
        SocialRewards.grant(snapshot,1,1,100,true,false);
        SocialRewards.grant(snapshot,1,2,10,false,true);
        save(snapshot); snapshot=user();
        assertTrue(truth(snapshot.get("needs_client_reset")));
        assertEquals(forced,snapshot.get("force_server_like"));
    }
    private Map<String,Object> mail(int id,long created,long expiry,boolean future) { return obj("idx",id,"create_time",created,"del_time",expiry,"applies_to_new_users",future,"have_reward",1,"status",0,"flg",0,"item_list",List.of()); }
}

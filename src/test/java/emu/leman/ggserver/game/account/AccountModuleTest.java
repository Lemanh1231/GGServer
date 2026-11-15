package emu.leman.ggserver.game.account;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.Result;
import java.nio.file.Path;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
import static emu.leman.ggserver.util.Json.*;
import static emu.leman.ggserver.game.account.AuthContent.*;

class AccountModuleTest {
    @TempDir Path root;
    private Map<String,Object> call(Services s,String command,Map<String,Object> payload) {
        Result result=s.registry.handle(command,obj("data",payload),obj("uuid","fallback","client_ip","203.0.113.8","domain","game.test"));
        assertEquals(0,integer(result.error().get("code"))); return map(result.data());
    }
    @Test void registersEveryCommandAndKeepsSystemRevisionFixed() {
        try(Services s=new Services(root)) {
            new AccountModule(s).register();
            assertEquals(Set.of("userJoin","userLogin","userSave","userLoad","lastSaveTime","setTutorialNew","setSubscribe","setReviewPopup","updateNickName","updateAvatar","updateUserTitle","getProfile","Request","getServerTime","getUpdateTime","defaultSettingList","hibernationLog","getLocalPush","completeLog"),s.registry.commands());
            assertEquals(1700000000,lng(call(s,"getUpdateTime",obj()).get("upd_time")));
            assertEquals(27,list(call(s,"defaultSettingList",obj()).get("setting_list")).size());
            long datetime=lng(call(s,"getServerTime",obj()).get("datetime")); assertTrue(datetime>20200000000000L);
        }
    }
    @Test void identityResetAndLegacyMigrationsAreIdempotent() {
        try(Services s=new Services(root)) {
            AccountModule handlers=new AccountModule(s); handlers.register();
            Map<String,Object> joined=call(s,"userJoin",obj("uuid","account","device_uuid","phone")); long seq=lng(joined.get("u_seq"));
            Map<String,Object> user=s.state.getUser("phone"), ud=map(user.get("userdata"));
            ud.putAll(obj("u_free_cp",1000000,"u_cp",1000000,"u_candy",100000.0)); user.remove("legacy_unlock_all_migrated");
            user.put("costumes",new ArrayList<>(List.of(item(1),item(99)))); s.state.saveUser(user);
            Map<String,Object> login=call(s,"userLogin",obj("uuid","changed-account","device_uuid","phone","u_seq",seq+10));
            assertEquals(seq,lng(map(login.get("user")).get("u_seq"))); assertEquals("RESET_phone",map(login.get("user")).get("device_uuid"));
            assertEquals(0,lng(map(login.get("user")).get("u_cp"))); assertEquals(0.0,dbl(map(login.get("user")).get("u_candy")));
            List<Object> costumes=list(map(login.get("user_contents")).get("user_costume")); assertEquals(Set.of(1,201),ids(costumes));
            user=s.state.getUser("phone"); map(user.get("userdata")).put("u_cp",100); rows(user,"costumes").add(item(99)); s.state.saveUser(user);
            login=call(s,"userLogin",obj("uuid","another-account","device_uuid","phone","u_seq",seq));
            assertEquals("phone",map(login.get("user")).get("device_uuid")); assertEquals(100,lng(map(login.get("user")).get("u_cp")));
            assertTrue(ids(list(map(login.get("user_contents")).get("user_costume"))).contains(99));
            assertEquals("phone",call(s,"lastSaveTime",obj("device_uuid","phone")).get("device_uuid"));
        }
    }
    @Test void joinThenLoginMatchesPythonEmptySqlInventoriesRatherThanReseedingStarters() {
        try(Services s=new Services(root)) {
            AccountModule handlers=new AccountModule(s); handlers.register();
            long seq=lng(call(s,"userJoin",obj("device_uuid","phone")).get("u_seq"));
            Map<String,Object> contents=map(call(s,"userLogin",obj("device_uuid","phone","u_seq",seq)).get("user_contents"));
            assertEquals(Set.of(201),ids(list(contents.get("user_costume"))));
            assertEquals(Set.of(201),ids(list(contents.get("user_guitar"))));
            assertEquals(Set.of(201),ids(list(contents.get("user_music"))));
            assertTrue(list(contents.get("user_follower")).isEmpty());
            assertTrue(list(contents.get("user_follower_giftitem")).isEmpty());
            assertEquals(0,integer(map(list(contents.get("user_costume")).getFirst()).get("i_BonusLevel")));
        }
    }
    @Test void savePreservesServerGrantsAndCompactRecordFields() {
        try(Services s=new Services(root)) {
            AccountModule handlers=new AccountModule(s); handlers.register(); Map<String,Object> u=s.state.createUser("phone","phone","");
            u.put("legacy_unlock_all_migrated",true); u.put("needs_client_reset",false); u.put("costumes",new ArrayList<>(List.of(obj("i_id",1,"i_Level",8,"i_BonusLevel",4),item(77))));
            u.put("achievements",new ArrayList<>(List.of(obj("i_id",1,"i_Level",5,"d_Quantity",10))));
            u.put("user_follower_quest",new ArrayList<>(List.of(obj("i_id",1,"i_CurrentID",2,"i_RewardReceived1",1,"d_ConditionValue1",20))));
            u.put("pending_grants",obj("cp",21,"candy",2.5,"cookies",3)); s.state.saveUser(u);
            call(s,"userSave",obj("device_uuid","phone","user_costume",List.of(obj("i_id",1,"i_Level",2,"i_BonusLevel",1)),"user_achievement",List.of(obj("i_id",1,"d_Quantity",42)),"user_follower_quest",List.of(obj("i_CurrentID",2,"d_ConditionValue1",5)),"user_chthird_stage",List.of(obj("i_id",3)),"user_area_info",List.of(obj("u_area_num",1,"s_Gp1","1A"))));
            u=s.state.getUser("phone"); Map<String,Object> costume=map(list(u.get("costumes")).stream().filter(raw->integer(map(raw).get("i_id"))==1).findFirst().orElseThrow());
            assertEquals(8,integer(costume.get("i_Level"))); assertEquals(4,integer(costume.get("i_BonusLevel"))); assertTrue(ids(list(u.get("costumes"))).contains(77));
            Map<String,Object> achievement=map(list(u.get("achievements")).getFirst()); assertEquals(5,integer(achievement.get("i_Level"))); assertEquals(42,lng(achievement.get("d_Quantity")));
            Map<String,Object> quest=map(list(u.get("user_follower_quest")).getFirst()); assertEquals(1,integer(quest.get("i_id"))); assertEquals(1,integer(quest.get("i_RewardReceived1"))); assertEquals(20,dbl(quest.get("d_ConditionValue1")));
            assertEquals(u.get("user_chthird_stage"),u.get("user_ch_third_stage")); assertFalse(u.containsKey("pending_grants"));
            assertEquals(21,lng(map(u.get("userdata")).get("u_cp"))); assertEquals(2.5,dbl(map(u.get("userdata")).get("u_candy"))); assertEquals(1000,dbl(map(u.get("userdata")).get("u_like")));
        }
    }
    @Test void normalizersRetainDailyAndPaidPassSemantics() {
        write(root.resolve("event_config.json"),emu.leman.ggserver.game.content.EventManager.defaults());
        List<Object> missionsFixture=new ArrayList<>();String[] types={"DailyAttendanceCount","TapCount","ExtraTouchCount","SkillUseCount","PlayTimePerSecond","CompleteDailyMissionCount"};int[] targets={1,2000,30,5,1800,5};
        for(int i=0;i<6;i++) missionsFixture.add(obj("1",i+1,"27",types[i],"28",targets[i],"44",1));
        write(root.resolve("gamedata/game_data.json"),obj("10",missionsFixture,"17",List.of(obj("1",13,"11",2021)),"18",List.of(obj("2",13,"3",1,"4",100),obj("2",13,"3",2,"4",500))));
        try(Services s=new Services(root)) {
            AuthContent content=new AuthContent(s); Map<String,Object> u=obj("daily_mission_date",19000101,"claimed_daily_rewards",obj("1",true));
            List<Object> missions=content.dailyMissions(u,null); assertEquals(1,lng(map(missions.getFirst()).get("d_Quantity"))); assertEquals(0,lng(map(missions.getLast()).get("d_Quantity"))); assertTrue(map(u.get("claimed_daily_rewards")).isEmpty());
            missions=content.dailyMissions(u,List.of(obj("i_id",2,"d_Quantity",2000),obj("i_id",3,"i_Level",2))); assertEquals(3,lng(map(missions.getLast()).get("d_Quantity")));
            u.put("user_event_point",new ArrayList<>(List.of(obj("s_EventType","Pass","i_DataID",13,"i_Point",250,"i_ADViewTime",2),obj("s_EventType","Pass","i_DataID",13,"i_Point",50,"i_ADViewTime",8),obj("s_EventType","Other","i_Point",3))));
            List<Object> points=content.eventPoints(u); assertEquals(2,points.size()); Map<String,Object> pass=map(points.getLast()); assertEquals(250,lng(pass.get("i_Point"))); assertEquals(8,lng(pass.get("i_ADViewTime"))); assertEquals(1,integer(pass.get("i_Step")));
            u.put("user_subscribe_list",new ArrayList<>(List.of(obj("i_SubscribeID",13,"i_isActive",0,"i_EndTime",123)))); assertTrue(content.subscriptions(u).isEmpty());
            u.put("user_shop",new ArrayList<>(List.of(obj("i_id",2013,"i_Count",1)))); assertEquals(1,content.subscriptions(u).size()); assertEquals(Set.of(13,1013),ids(content.tickets(u)));
            u.put("user_shop",new ArrayList<>(List.of(obj("i_id",2013,"i_Count",1),obj("i_id",1012,"i_Count",1)))); content.subscriptions(u); assertEquals(Set.of(12,13,1013),ids(content.tickets(u)));
            s.events.setStarPass(false,null,null); assertEquals(1,content.eventPoints(u).size()); assertEquals(1,content.subscriptions(u).size());
        }
    }
    @Test void chapterTwoAchievementsAreSeededAndProgressSurvivesSaveAndReopen() {
        List<Object> definitions=new ArrayList<>();
        for(int id=201;id<=207;id++) definitions.add(obj("1",id,"52",1));
        definitions.add(obj("1",208,"52",0));
        write(root.resolve("gamedata/game_data.json"),obj("9",definitions));
        try(Services s=new Services(root)) {
            new AccountModule(s).register();
            var u=s.state.createUser("phone","phone","");
            u.put("achievements",new ArrayList<>(List.of(obj("i_id",201,"i_Level",3,"d_Quantity",42),obj("i_id",999,"i_Level",2,"d_Quantity",10))));
            s.state.saveUser(u);
            call(s,"userSave",obj("device_uuid","phone","user_achievement",List.of(obj("i_id",201,"i_Level",1,"d_Quantity",5),obj("i_id",202,"d_Quantity",19))));
            var saved=list(s.state.getUser("phone").get("achievements"));
            assertTrue(ids(saved).containsAll(Set.of(201,202,203,204,205,206,207,999)));
            assertFalse(ids(saved).contains(208));
            var first=map(saved.stream().filter(v->integer(map(v).get("i_id"))==201).findFirst().orElseThrow());
            assertEquals(3,integer(first.get("i_Level"))); assertEquals(42,dbl(first.get("d_Quantity")));
        }
        try(Services s=new Services(root)) {
            var achievements=new AuthContent(s).achievements(s.state.getUser("phone"),null);
            assertTrue(ids(achievements).containsAll(Set.of(201,202,203,204,205,206,207,999)));
            assertEquals(19,dbl(map(achievements.stream().filter(v->integer(map(v).get("i_id"))==202).findFirst().orElseThrow()).get("d_Quantity")));
        }
    }
    @Test void messengerProgressSurvivesAuthSaveAndActualReopenWithoutSyntheticChapterTwoHistory() {
        try(Services s=new Services(root)) {
            new AccountModule(s).register();
            var user=s.state.createUser("chat-phone","chat-phone","");
            user.put("user_messenger",new ArrayList<>(List.of(obj("i_MessengerChatRoomId",1,"s_UnlockGroupList","1,4","i_LastConfirmIndex",12,"l_UpdateTimeTicks",200))));
            user.put("user_follower",new ArrayList<>(List.of(obj("i_id",201,"i_Level",700),obj("i_id",204,"i_Level",1))));
            s.state.saveUser(user);
            call(s,"userSave",obj("device_uuid","chat-phone","user_messenger",List.of(obj("i_MessengerChatRoomId",1,"s_UnlockGroupList","1","i_LastConfirmIndex",2))));
            assertEquals(1,list(s.state.getUser("chat-phone").get("user_messenger")).size());
        }
        try(Services s=new Services(root)) {
            var rooms=list(s.state.getUser("chat-phone").get("user_messenger"));
            assertEquals(1,rooms.size()); assertEquals("1,4",map(rooms.getFirst()).get("s_UnlockGroupList"));
            assertEquals(12,lng(map(rooms.getFirst()).get("i_LastConfirmIndex")));
        }
    }
    @Test void profileTutorialAndAccountEndpointsPersist() {
        try(Services s=new Services(root)) {
            new AccountModule(s).register(); AuthApi api=new AuthApi(s);
            Map<String,Object> first=map(api.login(obj("device_cd","phone","app_id","9")).get("value")); long seq=lng(map(first.get("member")).get("member_id"));
            call(s,"updateNickName",obj("device_uuid","phone","nickname","Player")); call(s,"updateAvatar",obj("device_uuid","phone","avatar",8)); call(s,"updateUserTitle",obj("device_uuid","phone","title",4));
            Map<String,Object> profile=call(s,"getProfile",obj("device_uuid","phone")); assertEquals("Player",profile.get("u_nick")); assertEquals(8,integer(profile.get("u_avatar"))); assertEquals(4,integer(profile.get("u_title")));
            Map<String,Object> tutorials=call(s,"setTutorialNew",obj("device_uuid","phone","i_ids",List.of(8,"9","bad",8,-1))); assertEquals(9,list(tutorials.get("tutorial")).size());
            Map<String,Object> second=map(api.login(obj("device_cd","phone","app_id","9")).get("value")); assertEquals(seq,lng(map(second.get("member")).get("member_id"))); assertEquals("Player",map(second.get("member")).get("nickname"));
            assertTrue(str(second.get("access_token")).startsWith(seq+"|9|phone|KR|")); assertNotNull(api.handle("/api/accounts/v3/global/login?x=1",obj("device_cd","phone"))); assertNull(api.handle("/unmatched",obj()));
            assertEquals("text/html; charset=utf-8",api.handle("/api/eula/latest",obj()).contentType());
            call(s,"setReviewPopup",obj("device_uuid","phone")); assertEquals("Y",map(s.state.getUser("phone").get("userdata")).get("u_review_popup"));
        }
    }
    @Test void forcedLikeResetCannotBeUndoneByStaleClientSave() {
        try(Services s=new Services(root)) {
            AccountModule handlers=new AccountModule(s); handlers.register(); Map<String,Object> u=s.state.createUser("phone","phone","");
            u.put("legacy_unlock_all_migrated",true); u.put("needs_client_reset",false); u.put("force_server_like",true);
            map(u.get("userdata")).put("u_like",10.0); s.state.saveUser(u);
            call(s,"userSave",obj("device_uuid","phone","user_area_info",List.of(obj("u_area_num",1,"s_Gp1","999Z"))));
            u=s.state.getUser("phone"); assertEquals(10.0,dbl(map(u.get("userdata")).get("u_like"))); assertEquals("10",map(map(u.get("areas")).get("1")).get("s_Gp1"));
            long seq=lng(map(u.get("userdata")).get("u_seq"));
            Map<String,Object> login=call(s,"userLogin",obj("device_uuid","phone","u_seq",seq));
            assertEquals("10",map(map(login.get("area_data")).get("1")).get("s_Gp1")); assertFalse(s.state.getUser("phone").containsKey("force_server_like"));
            call(s,"userSave",obj("device_uuid","phone","user_area_info",List.of(obj("u_area_num",1,"s_Gp1","2A"))));
            assertEquals(2000.0,dbl(map(s.state.getUser("phone").get("userdata")).get("u_like")));
        }
    }
    @Test void normalizesBuffsGatesSamseckAndFollowerProfiles() {
        write(root.resolve("gamedata/game_data.json"),obj("8",List.of(obj("1",1,"2",1,"37",100),obj("1",2,"2",1,"37",300),obj("1",3,"2",1,"37",500),obj("1",4,"2",1,"37",1)),
                "5",List.of(obj("1",1,"47",1)),"31",List.of(obj("2",1,"3",1,"4",0,"7",0),obj("2",1,"3",2,"4",50,"6","story","7",2),obj("2",1,"3",3,"4",150,"7",3))));
        try(Services s=new Services(root)) {
            AuthContent content=new AuthContent(s); Map<String,Object> u=obj("userdata",obj("u_samseck_step",99),"characters",new ArrayList<>(List.of(obj("i_id",1,"i_Level",300))),
                "user_follower",new ArrayList<>(List.of(obj("i_id",1,"i_Level",2000))),"user_follower_profile",new ArrayList<>(List.of(obj("i_id",1,"i_Level",19,"d_Exp",60))),
                "user_follower_profile_reward",new ArrayList<>(List.of(obj("i_id",1,"i_RewardLevel",19))),"user_skill",new ArrayList<>(List.of(obj("i_id",3,"i_Level",9))),
                "user_buff",new ArrayList<>(List.of(obj("i_id",1,"i_EndTime",now()-1),obj("i_id",2,"i_ExpiredTime",now()+100))));
            Map<String,Object> result=content.contents(u);
            assertEquals(Set.of(1,2,3,4),ids(list(result.get("user_skill")))); assertEquals(Set.of(2,4),ids(list(result.get("user_buff"))));
            assertEquals(9,integer(map(list(result.get("user_skill")).getFirst()).get("i_Level"))); // earned upgrade is never revoked
            assertEquals(Set.of(1,2),ids(list(result.get("user_character")))); assertTrue(ids(list(result.get("user_costume"))).containsAll(Set.of(1,201))); assertTrue(ids(list(result.get("user_guitar"))).containsAll(Set.of(1,201)));
            assertFalse(ids(list(result.get("user_costume"))).contains(13));assertFalse(ids(list(result.get("user_guitar"))).contains(10));
            assertEquals(99,integer(map(u.get("userdata")).get("u_samseck_step"))); assertTrue(list(u.get("user_unit")).isEmpty());
            content.contents(u); assertTrue(list(u.get("user_unit")).isEmpty());
            Map<String,Object> p=map(list(u.get("user_follower_profile")).getFirst()); assertEquals(2,integer(p.get("i_Level"))); assertEquals(60,lng(p.get("d_Exp"))); assertEquals(2,integer(p.get("i_AddCandy")));
            assertEquals(2000,integer(map(list(u.get("user_follower")).getFirst()).get("i_Level"))); assertEquals(1,list(u.get("user_follower_profile_reward")).size());
            assertEquals(2,integer(map(list(u.get("user_follower_profile_reward")).getFirst()).get("i_RewardLevel")));
        }
    }
    @Test void resetIsConsumedOnlyByFullLoginAndNeverSynthesizedByLoadOrSave() {
        try(Services s=new Services(root)) {
            new AccountModule(s).register();
            long seq=lng(call(s,"userJoin",obj("device_uuid","phone")).get("u_seq"));
            Map<String,Object> request=obj("device_uuid","phone","u_seq",seq);
            assertEquals("RESET_phone",map(call(s,"userLogin",request).get("user")).get("device_uuid"));
            call(s,"userLoad",obj("device_uuid","phone","type","ALL"));
            call(s,"userSave",obj("device_uuid","phone"));
            assertFalse(truth(s.state.getUser("phone").get("needs_client_reset")));
            assertEquals("phone",map(call(s,"userLogin",request).get("user")).get("device_uuid"));
            Map<String,Object> user=s.state.getUser("phone"); user.put("needs_client_reset",true); s.state.saveUser(user);
            call(s,"userLoad",obj("device_uuid","phone","type","ALL"));
            call(s,"userSave",obj("device_uuid","phone"));
            assertTrue(truth(s.state.getUser("phone").get("needs_client_reset")));
            call(s,"userLogin",obj("device_uuid","phone","u_seq",0));
            assertTrue(truth(s.state.getUser("phone").get("needs_client_reset")));
            assertEquals("RESET_phone",map(call(s,"userLogin",request).get("user")).get("device_uuid"));
            assertFalse(truth(s.state.getUser("phone").get("needs_client_reset")));
            assertEquals("phone",map(call(s,"userLogin",request).get("user")).get("device_uuid"));
        }
    }
    private static Set<Integer> ids(List<Object> values) { Set<Integer> result=new HashSet<>(); values.forEach(raw->result.add(integer(map(raw).get("i_id")))); return result; }
}

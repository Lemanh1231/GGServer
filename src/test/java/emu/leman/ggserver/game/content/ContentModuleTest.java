package emu.leman.ggserver.game.content;

import emu.leman.ggserver.net.Result;

import emu.leman.ggserver.Services;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static emu.leman.ggserver.util.Json.*;

class ContentModuleTest {
    @TempDir Path root;
    Services s;
    @BeforeEach void setup() throws Exception {
        Files.createDirectories(root.resolve("schema"));Files.copy(Path.of("resources/schema/schema.json"),root.resolve("schema/schema.json"));
        write(root.resolve("gamedata/game_data.json"),obj(
            "17",List.of(obj("1",1,"12",8),obj("1",2,"12",9)),
            "24",List.of(obj("1",1)),"38",List.of(obj("1",1),obj("1",2)),
            "11",List.of(obj("1",1,"6",10,"7",50)),
            "18",List.of(obj("1",1,"2",13,"3",1,"4",10)),
            "31",List.of(obj("1",1,"2",1,"3",1,"4",0,"7",0),obj("1",2,"2",1,"3",2,"4",50,"7",2),obj("1",3,"2",100000,"3",1,"4",0,"7",0),obj("1",4,"2",100000,"3",2,"4",100,"7",0)),
            "33",List.of(obj("1",1001,"2",1,"3",1,"5",90,"6",135,"7",180,"8","1","33",1,"34","Normal","37","100"),obj("1",1002,"2",1,"3",2,"5",90,"6",135,"7",180,"8","1","33",1,"34","Normal","37","100"),obj("1",1010,"2",1,"3",10,"34","Story")),
            "34",List.of(obj("1",1,"2",1,"3",50,"4",100,"5",550)),
            "35",List.of(obj("1",1,"3",10,"4",3,"5",11,"6",6,"7",12,"8",9)),
            "36",List.of(obj("1",100,"2",11,"3",4,"4",2,"5",100)),
            "13",List.of(obj("1",1,"2",10,"3",11,"4",4,"5",5),obj("1",2,"2",10,"3",9,"4",2,"5",1)),
            "26",List.of(obj("1",1,"4","ADViewCount","5",5))));
        s=new Services(root);new ContentModule(s).register();s.state.createUser("u","d");
    }
    @AfterEach void close() {if(s!=null)s.close();}
    Result call(String command,Object... fields) {Map<String,Object> p=obj(fields);p.put("uuid","u");return s.registry.handle(command,obj("data",p),obj());}
    Map<String,Object> data(Result result) {return map(result.data());}
    Map<String,Object> user() {return s.state.getUser("u");}
    @Test void eventTogglesFilterContentWithoutMutatingBaseTables() {
        s.events.setStarPass(true,2,false);ContentModule handlers=new ContentModule(s);Map<String,Object> data=handlers.filteredGameData(8);
        assertEquals(1,list(data.get("event_list")).size());Map<String,Object> event=map(list(data.get("event_list")).getFirst());assertEquals("0001-01-01 00:00:00",event.get("start_date"));assertEquals("9999-12-31 23:59:00",event.get("end_date"));
        List<Object> passes=list(data.get("SubscribeList"));assertEquals(9,integer(map(passes.getFirst()).get("i_RepeatMonth")));assertEquals(8,integer(map(passes.get(1)).get("i_RepeatMonth")));assertEquals(1,integer(map(passes.get(1)).get("b_IsActive")));
        assertEquals(0.0,dbl(map(list(data.get("followerquest")).getFirst()).get("d_Condition1_1")));
        s.events.setMeowfestEnabled(false);assertTrue(list(handlers.filteredGameData().get("samseckevent")).isEmpty());assertFalse(list(s.gameData.namedData().get("samseckevent")).isEmpty());
    }
    @Test void meowfestRewardsAreGrantedExactlyOnce() {
        call("getSamSeckReward","i_id",1);call("getSamSeckReward","i_id",2);call("getSamSeckReward","i_id",3);call("getSamSeckReward","i_id",3);
        assertEquals(3,integer(map(user().get("userdata")).get("u_samseck_step")));
        assertEquals(1,ContentModule.rows(user(),"user_guitar").stream().filter(r->integer(r.get("i_id"))==10).count());
        assertEquals(1,integer(ContentModule.find(ContentModule.rows(user(),"user_unit"),1).get("i_Level")));
        s.events.setMeowfestEnabled(false);assertEquals(1,integer(call("getSamSeckReward","i_id",1).error().get("code")));
    }
    @Test void freshUserStagesStayEmptyUntilExplicitChapterQuery() {
        assertTrue(list(user().get("user_chthird_stage")).isEmpty());
        Map<String,Object> result=data(call("getChThird"));List<Object> stages=list(result.get("user_ch_third_stage"));
        assertEquals(3,stages.size());assertEquals(3,integer(map(stages.getFirst()).get("i_Star")));assertEquals(0,integer(map(stages.getLast()).get("i_Star")));
    }
    @Test void tutorialScoreDropsAndStarChestArePersistedAndIdempotent() {
        Map<String,Object> result=data(call("chThirdStage","i_id",1001,"music_id",1,"profile_ids","1"));assertEquals(3,integer(result.get("star")));assertEquals(180,integer(result.get("total_score")));assertEquals(65,integer(map(result.get("user_ap")).get("i_Ap")));assertEquals(2,integer(ContentModule.find(ContentModule.rows(user(),"user_follower_giftitem"),4).get("i_Value")));
        Map<String,Object> chest=data(call("getChThirdStarReward","i_id",1,"reward_num",1));assertEquals(2,list(chest.get("reward_data")).size());assertEquals(7,integer(ContentModule.find(ContentModule.rows(user(),"user_follower_giftitem"),4).get("i_Value")));assertFalse(ContentModule.rows(user(),"user_ticketcollection").isEmpty());
        assertTrue(list(data(call("setChThirdChapterReward","i_id",1,"reward_num",1)).get("reward_data")).isEmpty());
        assertTrue(list(data(call("getChThirdStarReward","i_id",1,"reward_num",2)).get("reward_data")).isEmpty());
    }
    @Test void scoreUsesPythonRoundingAndBestStarsNeverDecrease() {
        Map<String,Object> result=data(call("chThirdStage","i_id",1002,"music_id",1,"profile_ids","1"));assertEquals(28,integer(result.get("music_score")));assertEquals(20,integer(map(list(result.get("user_follower_profile_score")).getFirst()).get("bonus_score")));assertEquals(158,integer(result.get("total_score")));assertEquals(2,integer(result.get("star")));
        result=data(call("chThirdStage","i_id",1002,"music_id",0,"profile_ids",""));assertEquals(0,integer(result.get("star")));assertEquals(2,integer(map(result.get("user_ch_third_stage")).get("i_Star")));
    }
    @Test void storyIsFreeStreamingCostsPerRunAndInsufficientApIsRejected() {
        Map<String,Object> user=user();user.put("user_ap",obj("i_Ap",10,"i_FullApTime",Instant.now().getEpochSecond()+60*300,"i_MaxAp",70));s.state.saveUser(user);
        assertEquals(10,integer(map(data(call("chThirdStage","i_id",1010)).get("user_ap")).get("i_Ap")));
        Map<String,Object> streamed=data(call("chThirdStreamStage","i_id",1001,"count",2));assertEquals(0,integer(map(streamed.get("user_ap")).get("i_Ap")));assertEquals(2,map(streamed.get("reward_data")).size());assertEquals(1,integer(call("chThirdStage","i_id",1001).error().get("code")));
    }
    @Test void offlineApRegeneratesAndCapsAtSeventy() {
        Map<String,Object> user=obj("user_ap",obj("i_Ap",0,"i_FullApTime",Instant.now().getEpochSecond()+15*300,"i_MaxAp",70));assertEquals(55,integer(ContentChapter.ap(user).get("i_Ap")));
        map(user.get("user_ap")).put("i_FullApTime",Instant.now().getEpochSecond()-1);assertEquals(70,integer(ContentChapter.ap(user).get("i_Ap")));assertEquals(0,lng(ContentChapter.ap(user).get("i_FullApTime")));
    }
    @Test void streamingSamplesOneCandidatePerRewardGroupPerRun() {
        s.gameData.data().put("36",List.of(obj("1",100,"2",11,"3",4,"4",2,"5",1),obj("1",100,"2",11,"3",5,"4",2,"5",100)));
        int before=ContentModule.rows(user(),"user_follower_giftitem").stream().mapToInt(r->integer(r.get("i_Value"))).sum();
        Map<String,Object> result=data(call("chThirdStreamStage","i_id",1001,"count",3));
        Map<String,Object> rewards=map(result.get("reward_data"));assertEquals(3,rewards.size());
        for(Object run:rewards.values())assertEquals(1,list(run).size());
        int total=ContentModule.rows(user(),"user_follower_giftitem").stream().mapToInt(r->integer(r.get("i_Value"))).sum();assertEquals(6,total-before);
    }
    @Test void chapterPropChestGrantsOwnedContentOnce() {
        Map<String,Object> user=user();user.remove("user_prop");
        user.put("user_ch_third_stage",new ArrayList<>(List.of(obj("i_id",1001,"i_ChapterId",1,"i_Star",3))));
        user.put("user_chthird_stage",user.get("user_ch_third_stage"));s.state.saveUser(user);
        s.gameData.data().put("13",List.of(obj("1",1,"2",10,"3",4,"4",3,"5",1)));
        Map<String,Object> response=data(call("getChThirdStarReward","i_id",1,"reward_num",1));
        assertEquals(1,list(response.get("reward_data")).size());
        List<Map<String,Object>> props=ContentModule.rows(user(),"user_prop");
        assertEquals(List.of(3),props.stream().map(r->integer(r.get("i_id"))).toList());
        assertTrue(list(data(call("getChThirdStarReward","i_id",1,"reward_num",1)).get("reward_data")).isEmpty());
    }
    @Test void encoreGrantsCandyProfileExpAndPassPoints() {
        Map<String,Object> user=user();user.put("user_follower_profile",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1,"d_Exp",0,"i_AddCandy",3))));user.put("user_event_point",new ArrayList<>(List.of(obj("s_EventType","Pass","i_DataID",13,"i_Point",0,"i_Step",0))));s.state.saveUser(user);
        Map<String,Object> result=data(call("getMusicReward","i_ids",List.of(1),"i_levels",List.of(1)));assertEquals(10,integer(result.get("total_reward_value")));assertEquals(13,dbl(map(user().get("userdata")).get("u_candy")));
        Map<String,Object> profile=ContentModule.find(ContentModule.rows(user(),"user_follower_profile"),1);assertEquals(50,lng(profile.get("d_Exp")));assertEquals(2,integer(profile.get("i_Level")));assertEquals(2,integer(profile.get("i_AddCandy")));
        assertEquals(10,integer(ContentModule.rows(user(),"user_event_point").getFirst().get("i_Point")));assertEquals(1,integer(ContentModule.rows(user(),"user_event_point").getFirst().get("i_Step")));
    }
    @Test void eventRankingUsesFutureWindowAndToggle() {
        Map<String,Object> main=data(call("getEventMain"));assertEquals(4102444800L,lng(main.get("end_time")));assertEquals(5,list(call("getEventRank").data()).size());s.events.setEventRankingEnabled(false);assertEquals(1,integer(call("getEventMain").error().get("code")));
    }
}

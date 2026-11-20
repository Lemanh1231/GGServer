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
        Files.createDirectories(root.resolve("gamedata"));write(root.resolve("gamedata/tour_drop_weights.json"),List.of(obj("i_id",1,"i_Percent",100),obj("i_id",2,"i_Percent",100)));
        write(root.resolve("gamedata/game_data.json"),obj(
            "17",List.of(obj("1",1,"12",8,"3","Pass","7",1),obj("1",2,"12",9,"3","Pass","7",1)),
            "24",List.of(obj("1",1,"14","CharacterLevel","15",200),obj("1",2,"14","TotalMusicCount","15",3),obj("1",3,"14","HaveMate","15",1)),"38",List.of(obj("1",1),obj("1",2)),
            "11",List.of(obj("1",1,"6",10,"7",50)),
            "18",List.of(obj("1",1,"2",1,"3",1,"4",10)),
            "31",List.of(obj("1",1,"2",1,"3",1,"4",0,"7",0),obj("1",2,"2",1,"3",2,"4",50,"7",2),obj("1",3,"2",100000,"3",1,"4",0,"7",0),obj("1",4,"2",100000,"3",2,"4",100,"7",0)),
            "2",List.of(obj("1",1,"49",1),obj("1",211,"45","Package","47",2,"48",19,"49",1),obj("1",216,"45","Package","49",1)),"5",List.of(obj("1",1,"47",1,"44",1),obj("1",5,"47",5,"44",1)),
            "28",List.of(obj("1",1,"14",1)),
            "33",List.of(obj("1",1001,"2",1,"3",1,"5",90,"6",135,"7",180,"8","1","33",1,"34","Normal","36",1,"37","100"),obj("1",1002,"2",1,"3",2,"5",90,"6",135,"7",180,"8","1","33",1,"34","Normal","37","100"),obj("1",1010,"2",1,"3",3,"34","Story")),
            "34",List.of(obj("1",1,"2",1,"3",50,"4",100,"5",550)),
            "35",List.of(obj("1",1,"3",10,"4",3,"5",11,"6",6,"7",12,"8",9)),
            "36",List.of(obj("1",100,"2",11,"3",4,"4",2,"5",1,"6",1)),
            "13",List.of(obj("1",1,"2",10,"3",11,"4",4,"5",5),obj("1",2,"2",10,"3",9,"4",2,"5",1)),
            "26",List.of(obj("1",1,"4","ADViewCount","5",5))));
        write(root.resolve("event_config.json"),EventManager.defaults());
        s=new Services(root);new ContentModule(s).register();s.state.createUser("u","d");
        var u=user();ContentModule.rows(u,"user_follower").add(obj("i_id",5,"i_Level",1));s.state.saveUser(u);
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
    @Test void onlyJingleBellAcquisitionIsDisabledWithoutRemovingSongOrChangingCatalog() {
        var music=list(new ContentModule(s).filteredGameData().get("music"));
        var jingle=map(music.stream().filter(v->integer(map(v).get("i_id"))==211).findFirst().orElseThrow());
        assertEquals("NotForSale",jingle.get("s_GoodsType")); assertEquals(1,integer(jingle.get("b_IsActive")));
        assertEquals(19,integer(jingle.get("i_AcquisitionId")));
        assertEquals("Package",map(music.stream().filter(v->integer(map(v).get("i_id"))==216).findFirst().orElseThrow()).get("s_GoodsType"));
        assertEquals("Package",s.gameData.row(2,211).get("45"));
    }
    @Test void meowfestRewardsAreGrantedExactlyOnce() {
        var u=user();u.put("characters",new ArrayList<>(List.of(obj("i_id",1,"i_Level",200))));u.put("user_music",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1),obj("i_id",211,"i_Level",1),obj("i_id",216,"i_Level",1))));u.put("user_unit",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1))));s.state.saveUser(u);
        double candy=dbl(map(user().get("userdata")).get("u_candy"));
        call("getSamSeckReward","i_id",1);call("getSamSeckReward","i_id",2);call("getSamSeckReward","i_id",3);call("getSamSeckReward","i_id",3);
        assertEquals(3,integer(map(user().get("userdata")).get("u_samseck_step")));
        assertEquals(1,ContentModule.rows(user(),"user_guitar").stream().filter(r->integer(r.get("i_id"))==10).count());
        assertEquals(1,integer(ContentModule.find(ContentModule.rows(user(),"user_unit"),1).get("i_Level")));
        assertEquals(candy+333.0,dbl(map(user().get("userdata")).get("u_candy")));
        s.events.setMeowfestEnabled(false);assertEquals(1,integer(call("getSamSeckReward","i_id",1).error().get("code")));
    }
    @Test void freshUserStagesStayEmptyUntilExplicitChapterQuery() {
        assertTrue(list(user().get("user_chthird_stage")).isEmpty());
        Map<String,Object> result=data(call("getChThird"));List<Object> stages=list(result.get("user_ch_third_stage"));
        assertTrue(stages.isEmpty());assertTrue(ContentModule.rows(user(),"user_ch_third_stage").isEmpty());
    }
    @Test void tutorialScoreDropsAndStarChestArePersistedAndIdempotent() {
        Map<String,Object> result=data(call("chThirdStage","i_id",1001,"music_id",1,"profile_ids","1"));assertEquals(3,integer(result.get("star")));assertEquals(207,integer(result.get("total_score")));assertEquals(65,integer(map(result.get("user_ap")).get("i_Ap")));assertEquals(2,integer(ContentModule.find(ContentModule.rows(user(),"user_follower_giftitem"),4).get("i_Value")));
        Map<String,Object> chest=data(call("getChThirdStarReward","i_id",1,"reward_num",1));assertEquals(2,list(chest.get("reward_data")).size());assertEquals(7,integer(ContentModule.find(ContentModule.rows(user(),"user_follower_giftitem"),4).get("i_Value")));assertFalse(ContentModule.rows(user(),"user_ticketcollection").isEmpty());
        assertTrue(list(data(call("setChThirdChapterReward","i_id",1,"reward_num",1)).get("reward_data")).isEmpty());
        assertTrue(list(data(call("getChThirdStarReward","i_id",1,"reward_num",2)).get("reward_data")).isEmpty());
    }
    @Test void scoreUsesNativeTruncationAndBestStarsNeverDecrease() {
        call("chThirdStage","i_id",1001,"music_id",1,"profile_ids","1");
        Map<String,Object> result=data(call("chThirdStage","i_id",1002,"music_id",1,"profile_ids","1"));assertEquals(27,integer(result.get("music_score")));assertEquals(20,integer(map(list(result.get("user_follower_profile_score")).getFirst()).get("bonus_score")));assertEquals(197,integer(result.get("total_score")));assertEquals(3,integer(result.get("star")));
        var config=s.gameData.row(33,1002);config.put("5",1000);config.put("6",2000);config.put("7",3000);
        result=data(call("chThirdStage","i_id",1002,"music_id",1,"profile_ids","1"));assertEquals(0,integer(result.get("star")));assertEquals(3,integer(map(result.get("user_ch_third_stage")).get("i_Star")));
    }
    @Test void storyIsFreeStreamingCostsPerRunAndInsufficientApIsRejected() {
        call("chThirdStage","i_id",1001,"music_id",1,"profile_ids","1");call("chThirdStage","i_id",1002,"music_id",1,"profile_ids","1");
        Map<String,Object> user=user();user.put("user_ap",obj("i_Ap",10,"i_FullApTime",Instant.now().getEpochSecond()+60*300,"i_MaxAp",70));s.state.saveUser(user);
        assertEquals(10,integer(map(data(call("chThirdStage","i_id",1010)).get("user_ap")).get("i_Ap")));
        Map<String,Object> streamed=data(call("chThirdStreamStage","i_id",1001,"count",2));assertEquals(0,integer(map(streamed.get("user_ap")).get("i_Ap")));assertEquals(2,map(streamed.get("reward_data")).size());assertEquals(1,integer(call("chThirdStage","i_id",1001).error().get("code")));
    }
    @Test void offlineApRegeneratesAndCapsAtSeventy() {
        Map<String,Object> user=obj("user_ap",obj("i_Ap",0,"i_FullApTime",Instant.now().getEpochSecond()+15*300,"i_MaxAp",70));assertEquals(55,integer(ContentChapter.ap(user).get("i_Ap")));
        map(user.get("user_ap")).put("i_FullApTime",Instant.now().getEpochSecond()-1);assertEquals(70,integer(ContentChapter.ap(user).get("i_Ap")));assertEquals(0,lng(ContentChapter.ap(user).get("i_FullApTime")));
    }
    @Test void streamingSamplesOneCandidatePerRewardGroupPerRun() {
        call("chThirdStage","i_id",1001,"music_id",1,"profile_ids","1");
        s.gameData.data().put("36",List.of(obj("1",100,"2",11,"3",4,"4",2,"5",1,"6",1),obj("1",100,"2",11,"3",5,"4",2,"5",1,"6",2)));
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
    @Test void chapterLevelGateRejectsPlaySweepAndChestWithoutChangingPlayerData() {
        s.gameData.data().put("35",List.of(obj("1",1,"2",1),obj("1",2,"2",10)));
        s.gameData.data().put("33",List.of(obj("1",2002,"2",2,"3",2,"34","Normal")));
        Map<String,Object> u=user();ContentModule.find(ContentModule.rows(u,"user_follower_profile"),100000).put("i_Level",5);
        u.put("user_ch_third_stage",new ArrayList<>(List.of(obj("i_id",2002,"i_ChapterId",2,"i_Star",3))));
        u.put("user_chthird_stage",u.get("user_ch_third_stage"));s.state.saveUser(u);String before=stringify(user());
        assertEquals(1,integer(call("chThirdStage","i_id",2002).error().get("code")));
        assertEquals(1,integer(call("chThirdStreamStage","i_id",2002,"count",1).error().get("code")));
        assertEquals(1,integer(call("getChThirdStarReward","i_id",2,"reward_num",1).error().get("code")));
        assertEquals(before,stringify(user()));
        u=user();ContentModule.find(ContentModule.rows(u,"user_follower_profile"),100000).put("i_Level",10);s.state.saveUser(u);
        assertEquals(0,integer(call("chThirdStreamStage","i_id",2002,"count",1).error().get("code")));
    }
    @Test void scoreUsesTourGirlProfileNotIdleCharacterLevel() {
        s.gameData.data().put("34",List.of(obj("1",1,"2",1,"3",50,"4",100,"5",550),obj("1",2,"2",50,"3",800,"4",1600,"5",1000)));
        Map<String,Object> u=user();map(list(u.get("characters")).getFirst()).put("i_Level",8923);s.state.saveUser(u);
        assertEquals(50,integer(data(call("chThirdStage","i_id",1001,"music_id",1,"profile_ids","1")).get("character_score")));
    }
    @Test void sweepRequiresEarnedThreeStarsAndValidStage() {
        call("getChThird");
        assertEquals(1,integer(call("chThirdStreamStage","i_id",1001,"count",1).error().get("code")));
        assertEquals(1,integer(call("chThirdStage","i_id",999999).error().get("code")));
        call("chThirdStage","i_id",1001,"music_id",1,"profile_ids","1");
        assertEquals(1,integer(call("chThirdStreamStage","i_id",1001,"count",6).error().get("code")));
        assertEquals(0,integer(call("chThirdStreamStage","i_id",1001,"count",1).error().get("code")));
    }
    @Test void purchasedCookieOverflowSurvivesChapterReadAndSpend() {
        Map<String,Object> u=user();u.put("user_ap",obj("i_Ap",95,"i_FullApTime",0,"i_MaxAp",70));s.state.saveUser(u);
        assertEquals(95,integer(map(data(call("getChThird")).get("user_ap")).get("i_Ap")));
        Map<String,Object> ap=map(data(call("chThirdStage","i_id",1001,"music_id",1,"profile_ids","1")).get("user_ap"));
        assertEquals(90,integer(ap.get("i_Ap")));assertEquals(0,lng(ap.get("i_FullApTime")));
    }
    @Test void encoreGrantsCandyProfileExpAndPassPoints() {
        s.events.setStarPass(true,1,false);
        var prepared=user();prepared.put("user_music",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1,"b_EncoreBonusAppear",1,"i_EncoreBonusFollowerId",1))));ContentModule.rows(prepared,"user_follower").add(obj("i_id",1,"i_Level",1));s.state.saveUser(prepared);
        Map<String,Object> user=user();user.put("user_follower_profile",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1,"d_Exp",0,"i_AddCandy",3))));user.put("user_event_point",new ArrayList<>(List.of(obj("s_EventType","Pass","i_DataID",13,"i_Point",0,"i_Step",0))));s.state.saveUser(user);
        Map<String,Object> result=data(call("getMusicReward","i_ids",List.of(1),"i_levels",List.of(1)));assertEquals(13,integer(result.get("total_reward_value")));assertEquals(13,dbl(map(user().get("userdata")).get("u_candy")));
        Map<String,Object> profile=ContentModule.find(ContentModule.rows(user(),"user_follower_profile"),1);assertEquals(50,lng(profile.get("d_Exp")));assertEquals(2,integer(profile.get("i_Level")));assertEquals(2,integer(profile.get("i_AddCandy")));
        assertEquals(10,integer(ContentModule.rows(user(),"user_event_point").getFirst().get("i_Point")));assertEquals(1,integer(ContentModule.rows(user(),"user_event_point").getFirst().get("i_Step")));
    }
    @Test void eventRankingNeverReturnsFabricatedRanksEvenWhenEnabled() {
        s.events.setEventRankingEnabled(true);assertEquals(1,integer(call("getEventMain").error().get("code")));assertEquals(1,integer(call("getEventRank").error().get("code")));assertTrue(list(call("getEventRank").data()).isEmpty());s.events.setEventRankingEnabled(false);assertEquals(1,integer(call("getEventMain").error().get("code")));
    }
}

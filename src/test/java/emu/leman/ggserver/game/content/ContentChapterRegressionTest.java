package emu.leman.ggserver.game.content;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.Result;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.*;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class ContentChapterRegressionTest {
    @TempDir Path root;
    Services s;
    Clock clock=Clock.fixed(Instant.ofEpochSecond(1900000000),ZoneOffset.UTC);
    @BeforeEach void setup() throws Exception {
        try(var paths=Files.walk(Path.of("resources/gamedata/catalog"))) {
            for(var from:paths.toList()) {
                var to=root.resolve("gamedata/catalog").resolve(Path.of("resources/gamedata/catalog").relativize(from));
                if(Files.isDirectory(from))Files.createDirectories(to);else Files.copy(from,to);
            }
        }
        Files.createDirectories(root.resolve("schema"));Files.copy(Path.of("resources/schema/schema.json"),root.resolve("schema/schema.json"));
        Files.copy(Path.of("resources/gamedata/tour_drop_weights.json"),root.resolve("gamedata/tour_drop_weights.json"));
        open();s.state.createUser("u","d");
        var u=user();u.put("user_follower",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1),obj("i_id",2,"i_Level",1),obj("i_id",5,"i_Level",1))));
        u.put("user_music",new ArrayList<>(List.of(music(1),music(2),music(3))));
        u.put("user_follower_profile",new ArrayList<>(List.of(obj("i_id",100000,"i_Level",5,"d_Exp",2700),obj("i_id",1,"i_Level",1,"d_Exp",0),obj("i_id",2,"i_Level",1,"d_Exp",0))));
        u.put("user_ch_third_stage",new ArrayList<>(List.of(obj("i_id",1001,"i_ChapterId",1,"i_StageIndex",1,"i_Star",3))));
        u.put("user_chthird_stage",u.get("user_ch_third_stage"));s.state.saveUser(u);
    }
    void open() {if(!Files.exists(root.resolve("event_config.json")))write(root.resolve("event_config.json"),EventManager.defaults());s=new Services(root);new ContentChapter(s,clock).register();}
    @AfterEach void close() {if(s!=null)s.close();}
    Map<String,Object> music(int id) {return obj("i_id",id,"i_Level",1,"i_ChThirdActiveTime",0);}
    Map<String,Object> user() {return s.state.getUser("u");}
    Result result(String cmd,Object... fields) {var p=obj(fields);p.put("uuid","u");return s.registry.handle(cmd,obj("data",p),obj());}
    Map<String,Object> call(String cmd,Object... fields) {var r=result(cmd,fields);assertEquals(0,integer(r.error().get("code")),str(r.error()));return map(r.data());}
    void unlock1004() {call("chThirdStage","i_id",1002);call("chThirdStage","i_id",1003);}
    void girl(int level,long exp) {var u=user();var p=ContentModule.find(ContentModule.rows(u,"user_follower_profile"),100000);p.put("i_Level",level);p.put("d_Exp",exp);s.state.saveUser(u);}
    void unchangedRejection(String cmd,Object... fields) {String before=stringify(user());assertEquals(1,integer(result(cmd,fields).error().get("code")));assertEquals(before,stringify(user()));}
    @Test void correctedTotalsMatchNativeAuditAndComponentsAddUp() {
        unlock1004();
        for(int music:new int[]{3,2,1}) {
            girl(5,2700);
            var r=call("chThirdStage","i_id",1004,"music_id",music,"profile_ids","1");
            assertEquals(music==2?275:255,integer(r.get("total_score")));
            assertEquals(music==2?2:1,integer(r.get("star")));
            assertEquals(music==2?20:0,integer(r.get("bonus_music_score")));
            assertEquals(integer(r.get("total_score")),integer(r.get("character_score"))+integer(r.get("music_score"))+integer(r.get("follower_profile_score"))+integer(r.get("bonus_score")));
        }
    }
    @Test void firstStageDoesNotFabricateThreeStars() {
        girl(1,0);
        var r=call("chThirdStage","i_id",1001,"music_id",3,"profile_ids","2");
        assertEquals(177,integer(r.get("total_score")));assertEquals(27,integer(r.get("music_score")));assertEquals(2,integer(r.get("star")));
        assertEquals(3,integer(map(r.get("user_ch_third_stage")).get("i_Star")),"historical best is retained");
    }
    @Test void fractionalBonusUsesCombinedTruncationAndReconcilesResponse() {
        girl(2,100);
        var r=call("chThirdStage","i_id",1001,"music_id",1,"profile_ids","2");
        assertEquals(34,integer(r.get("music_score")));assertEquals(12,integer(r.get("bonus_music_score")));assertEquals(208,integer(r.get("total_score")));
    }
    @Test void invalidTeamsNeverSpendOrReward() {
        for(String team:new String[]{"1,1","100000","1,2,5,6","999999","1,invalid","1,","-1",""})
            unchangedRejection("chThirdStage","i_id",1001,"music_id",1,"profile_ids",team);
        unchangedRejection("chThirdStage","i_id",1001,"music_id",999999,"profile_ids","1");
        unchangedRejection("chThirdStage","i_id",1001,"music_id",0,"profile_ids","1");
        var u=user();ContentModule.rows(u,"user_follower_profile").add(obj("i_id",3,"i_Level",1));s.state.saveUser(u);
        unchangedRejection("chThirdStage","i_id",1001,"music_id",1,"profile_ids","3");
    }
    @Test void validThreeUniqueOwnedFollowersAreAccepted() {
        var u=user();ContentModule.rows(u,"user_follower_profile").add(obj("i_id",5,"i_Level",1));s.state.saveUser(u);
        assertEquals(300,integer(call("chThirdStage","i_id",1001,"music_id",1,"profile_ids","1,2,5").get("follower_profile_score")));
    }
    @Test void unownedAndInactiveMusicAreRejectedWithoutSpending() {
        unchangedRejection("chThirdStage","i_id",1001,"music_id",4,"profile_ids","1");
        s.gameData.row(2,1).put("49",0);unchangedRejection("chThirdStage","i_id",1001,"music_id",1,"profile_ids","1");
    }
    @Test void existingFutureMusicAvailabilityIsEnforcedAtBoundary() {
        var u=user();ContentModule.find(ContentModule.rows(u,"user_music"),1).put("i_ChThirdActiveTime",clock.instant().getEpochSecond()+1);s.state.saveUser(u);
        unchangedRejection("chThirdStage","i_id",1001,"music_id",1,"profile_ids","1");
        clock=Clock.offset(clock,Duration.ofSeconds(1));s.close();open();call("chThirdStage","i_id",1001,"music_id",1,"profile_ids","1");
    }
    @Test void placeholdersAreNotCompletionButStayStored() {
        var u=user();var progress=new ArrayList<Map<String,Object>>();
        for(var c:s.gameData.table(33))progress.add(obj("i_id",integer(c.get("1")),"i_ChapterId",integer(c.get("2")),"i_StageIndex",integer(c.get("3")),"i_Star",0));
        u.put("user_ch_third_stage",progress);u.put("user_chthird_stage",progress);s.state.saveUser(u);
        assertTrue(list(call("getChThird").get("user_ch_third_stage")).isEmpty());assertEquals(41,ContentModule.rows(user(),"user_ch_third_stage").size());
        unchangedRejection("chThirdStage","i_id",1002);unchangedRejection("chThirdStage","i_id",1004,"music_id",1,"profile_ids","1");
        girl(10,18700);unchangedRejection("chThirdStage","i_id",2001);
    }
    @Test void sequenceUnlocksStoryOnceAndSurvivesReopen() {
        unchangedRejection("chThirdStage","i_id",1003);
        long before=lng(ContentModule.find(ContentModule.rows(user(),"user_follower_profile"),100000).get("d_Exp"));
        call("chThirdStage","i_id",1002);s.close();open();
        call("chThirdStage","i_id",1002);call("chThirdStage","i_id",1002);
        assertEquals(before+100,lng(ContentModule.find(ContentModule.rows(user(),"user_follower_profile"),100000).get("d_Exp")));
        assertEquals(70,integer(map(user().get("user_ap")).get("i_Ap")));call("chThirdStage","i_id",1003);
        assertEquals(List.of(1001,1002,1003),list(call("getChThird").get("user_ch_third_stage")).stream().map(r->integer(map(r).get("i_id"))).toList());
    }
    @Test void concurrentStoryRequestsAwardOnce() throws Exception {
        long before=lng(ContentModule.find(ContentModule.rows(user(),"user_follower_profile"),100000).get("d_Exp"));
        try(var pool=Executors.newFixedThreadPool(8)) {
            List<Callable<Integer>> jobs=new ArrayList<>();for(int i=0;i<8;i++)jobs.add(()->integer(result("chThirdStage","i_id",1002).error().get("code")));
            for(var f:pool.invokeAll(jobs))assertEquals(0,f.get());
        }
        assertEquals(before+100,lng(ContentModule.find(ContentModule.rows(user(),"user_follower_profile"),100000).get("d_Exp")));
    }
    @Test void historicalLaterStarsInferEarlierCompletionWithoutAwardingReplayExp() {
        var u=user();ContentModule.rows(u,"user_ch_third_stage").add(obj("i_id",1019,"i_ChapterId",1,"i_StageIndex",19,"i_Star",3));s.state.saveUser(u);
        var before=ContentModule.find(ContentModule.rows(user(),"user_follower_profile"),100000).get("d_Exp");
        call("chThirdStage","i_id",1002);assertEquals(before,ContentModule.find(ContentModule.rows(user(),"user_follower_profile"),100000).get("d_Exp"));
        girl(10,18700);unchangedRejection("chThirdStage","i_id",2001);call("chThirdStage","i_id",1020);call("chThirdStage","i_id",2001);
    }
    @Test void unlockAndActiveGatesApplyBeforeRewards() {
        var u=user();ContentModule.rows(u,"user_follower").removeIf(r->integer(r.get("i_id"))==5);s.state.saveUser(u);
        unchangedRejection("chThirdStage","i_id",1002);unchangedRejection("getChThird");
    }
    @Test void disabledStagesAndChaptersRejectEvenHistoricalProgress() {
        s.gameData.row(33,1001).put("33",0);unchangedRejection("chThirdStage","i_id",1001,"music_id",1,"profile_ids","1");unchangedRejection("chThirdStreamStage","i_id",1001,"count",1);
        s.gameData.row(35,1).put("21",0);unchangedRejection("getChThirdStarReward","i_id",1,"reward_num",1);
    }
    @Test void apSpendingPreservesPartialTimeAndOverflowBoundaries() {
        long now=clock.instant().getEpochSecond(),full=now+60*300-194;
        var u=obj("user_ap",obj("i_Ap",10,"i_FullApTime",full));var ap=ContentChapter.ap(u,now);
        assertTrue(ContentChapter.spend(ap,5,now));assertEquals(full+1500,lng(ap.get("i_FullApTime")));
        assertEquals(6,integer(ContentChapter.ap(u,now+106).get("i_Ap")));
        for(int initial:new int[]{95,75}) {
            ap=obj("i_Ap",initial,"i_FullApTime",0);assertTrue(ContentChapter.spend(ap,5,now));assertEquals(0,lng(ap.get("i_FullApTime")));
        }
        ap=obj("i_Ap",70,"i_FullApTime",0);assertTrue(ContentChapter.spend(ap,5,now));assertEquals(now+1500,lng(ap.get("i_FullApTime")));
        ap=obj("i_Ap",72,"i_FullApTime",0);assertTrue(ContentChapter.spend(ap,5,now));assertEquals(now+900,lng(ap.get("i_FullApTime")));
    }
    @Test void dropWeightsExactlyPartitionOriginalProbabilityRanges() {
        Map<Integer,Integer> weights=new HashMap<>();for(Object o:list(read(root.resolve("gamedata/tour_drop_weights.json")))) {var r=map(o);weights.put(integer(r.get("i_id")),integer(r.get("i_Percent")));}
        var candidates=s.gameData.table(36).stream().filter(r->integer(r.get("1"))==301010).toList();int[] counts=new int[5];
        for(int pick=0;pick<100;pick++)counts[integer(ContentChapter.choose(candidates,weights,pick).get("4"))]++;
        assertArrayEquals(new int[]{0,10,20,50,20},counts);assertEquals(120,weights.size());
        assertThrows(IllegalArgumentException.class,()->ContentChapter.choose(candidates,weights,100));
    }
    @Test void missingWeightsFailClosedInsteadOfSilentlyUsingActiveFlags() throws Exception {
        s.close();s=null;Files.delete(root.resolve("gamedata/tour_drop_weights.json"));
        try(var services=new Services(root)) {assertThrows(IllegalArgumentException.class,()->new ContentChapter(services));}
    }
    @Test void storyClearMarkerPersistsThroughMongoPublishedSections() {
        var mongo=new de.bwaldvogel.mongo.MongoServer(new de.bwaldvogel.mongo.backend.memory.MemoryBackend());
        var address=mongo.bind();
        try {
            var config=emu.leman.ggserver.config.ServerConfig.defaults(root,obj("database",obj("backend","mongo","name","tour_test","uri","mongodb://"+address.getHostString()+":"+address.getPort()+"/?serverSelectionTimeoutMS=5000")));
            try(var services=new Services(config)) {
                var u=services.state.createUser("mongo-tour","mongo-device");
                u.put("user_ch_third_stage",new ArrayList<>(List.of(obj("i_id",1002,"i_ChapterId",1,"i_StageIndex",2,"i_Star",0,"b_Clear",true))));
                services.state.saveUser(u);
            }
            try(var services=new Services(config)) {
                var u=services.state.getUser("mongo-tour");assertTrue(truth(ContentModule.rows(u,"user_ch_third_stage").getFirst().get("b_Clear")));
                assertEquals(List.of(1001,1002),ContentChapter.wireProgress(services.gameData,u).stream().map(r->integer(r.get("i_id"))).toList());
            }
        } finally {mongo.shutdownNow();}
    }
}

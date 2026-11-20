package emu.leman.ggserver.game.content;

import de.bwaldvogel.mongo.MongoServer;
import de.bwaldvogel.mongo.backend.memory.MemoryBackend;
import emu.leman.ggserver.Services;
import emu.leman.ggserver.config.ServerConfig;
import emu.leman.ggserver.game.account.AccountModule;
import emu.leman.ggserver.net.Result;
import java.nio.file.*;
import java.sql.DriverManager;
import java.util.*;
import java.util.concurrent.*;
import java.util.stream.Stream;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.*;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

/** Native-format saves, real catalog, synthetic accounts. Never uses live configuration. */
class ChapterEncoreRegressionTest {
    static final String ID="chapter-encore-regression";
    @TempDir Path root;
    Services s;
    ServerConfig config;
    MongoServer mongo;
    int music;

    static Stream<Arguments> chapters() {
        return Stream.of(Arguments.of(1,"sqlite"),Arguments.of(2,"sqlite"),
                Arguments.of(1,"mongo"),Arguments.of(2,"mongo"));
    }
    void setup(int chapter,String backend) throws Exception {
        music=chapter==1?1:201;
        for(String file:List.of("gamedata/game_data.json","gamedata/tour_drop_weights.json","schema/schema.json")) {
            Path target=root.resolve(file);Files.createDirectories(target.getParent());Files.copy(Path.of("resources").resolve(file),target);
        }
        write(root.resolve("event_config.json"),EventManager.defaults());
        if(backend.equals("mongo")) {
            mongo=new MongoServer(new MemoryBackend());var address=mongo.bind();
            config=ServerConfig.defaults(root,obj("database",obj("backend","mongo","name","encore_test",
                    "uri","mongodb://"+address.getHostString()+":"+address.getPort()+"/?serverSelectionTimeoutMS=5000")));
        } else config=ServerConfig.defaults(root);
        reopen();
        var u=s.state.createUser(ID,"synthetic-device");
        u.put("user_music",new ArrayList<>(List.of(song(1,music))));
        u.put("user_follower",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1),obj("i_id",201,"i_Level",1))));
        // CH1 follower1 and CH2 follower201 intentionally share profile1 in the real catalog.
        u.put("user_follower_profile",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1,"d_Exp",0,"i_AddCandy",3))));
        s.state.saveUser(u);
    }
    void reopen() {
        if(s!=null)s.close();s=new Services(config);
        new AccountModule(s).register();new ContentModule(s).register();
    }
    @AfterEach void close() {try {if(s!=null)s.close();} finally {if(mongo!=null)mongo.shutdownNow();}}
    Map<String,Object> user() {return s.state.getUser(ID);}
    Map<String,Object> song(int appear,int follower) {
        return obj("i_id",music,"i_Level",1,"i_BonusLevel",0,"b_EncoreBonusAppear",appear,"i_EncoreBonusFollowerId",follower);
    }
    Result call(String command,Object... args) {return s.registry.handle(command,obj("data",obj(args)),obj("uuid",ID));}
    Map<String,Object> claim() {
        var r=call("getMusicReward","i_ids",List.of(music));assertEquals(0,integer(r.error().get("code")),r.error().toString());return map(r.data());
    }
    void reject(Object ids) {
        String before=stringify(user());assertNotEquals(0,integer(call("getMusicReward","i_ids",ids).error().get("code")));
        assertEquals(before,stringify(user()),"Rejected claims must not mutate any account section");
    }
    void save(Object... songs) {assertEquals(0,integer(call("userSave","user_music",List.of(songs)).error().get("code")));}
    void backdate(long secondsAgo) {
        var u=user();map(map(u.get("encore_state")).get(str(music))).put("claimed_at",System.currentTimeMillis()/1000-secondsAgo);s.state.saveUser(u);
    }

    @ParameterizedTest @MethodSource("chapters")
    void nativeCycleRepeatsAfterCooldownAndSurvivesReopen(int chapter,String backend) throws Exception {
        setup(chapter,backend);claim();reject(List.of(music));save(song(1,music));reopen();reject(List.of(music));
        backdate(75601);save(song(1,music));reopen();claim();reject(List.of(music));
        assertEquals(100,lng(map(list(user().get("user_follower_profile")).getFirst()).get("d_Exp")));
    }
    @ParameterizedTest @MethodSource("chapters")
    void pendingGiftSurvivesStaleMissingAndForgedFields(int chapter,String backend) throws Exception {
        setup(chapter,backend);
        var stale=song(0,0);stale.put("l_EncoreBonusActivateTime",Long.MAX_VALUE);save(stale);
        save(obj("i_id",music,"i_Level",1,"i_BonusLevel",0));save();reopen();
        assertEquals(13,integer(claim().get("total_reward_value")));reject(List.of(music));
    }
    @ParameterizedTest @MethodSource("chapters")
    void crossAreaAndUnownedExactFollowerCannotClaim(int chapter,String backend) throws Exception {
        setup(chapter,backend);var u=user();
        map(list(u.get("user_music")).getFirst()).put("i_EncoreBonusFollowerId",chapter==1?201:1);s.state.saveUser(u);reject(List.of(music));
        u=user();map(list(u.get("user_music")).getFirst()).put("i_EncoreBonusFollowerId",music);
        list(u.get("user_follower")).removeIf(v->integer(map(v).get("i_id"))==music);s.state.saveUser(u);
        reject(List.of(music)); // Owning a different follower with the same profile is insufficient.
    }
    @ParameterizedTest @MethodSource("chapters")
    void appearanceValidatesAreaOwnershipAndIgnoresClientTimestamp(int chapter,String backend) throws Exception {
        setup(chapter,backend);claim();backdate(75601);
        save(song(1,chapter==1?201:1));reject(List.of(music));
        var next=song(1,music);next.put("l_EncoreBonusActivateTime",Long.MAX_VALUE);save(next);
        long activation=lng(map(list(user().get("user_music")).getFirst()).get("l_EncoreBonusActivateTime"));
        assertTrue(Math.abs(activation-System.currentTimeMillis()/1000)<5);claim();
        save(next);reject(List.of(music));
    }
    @ParameterizedTest @MethodSource("chapters")
    void cooldownUsesCatalogAtFourLevelsAndExactBoundary(int chapter,String backend) throws Exception {
        setup(chapter,backend);
        for(int level:List.of(1,10,25,50)) {
            // Exercise merge with a fixed server time, without sleeping or altering the machine clock.
            var u=user();var previous=song(0,0);previous.put("i_Level",level);
            long claimed=1_000_000,wait=EncoreRules.cooldown(s.gameData,level);
            u.put("encore_state",obj(str(music),obj("pending",0,"claimed_at",claimed)));
            var incoming=new LinkedHashMap<>(previous);
            EncoreRules.mergeAppearance(s.gameData,u,previous,incoming,1,music,claimed+wait-1);
            assertEquals(0,integer(incoming.get("b_EncoreBonusAppear")));
            EncoreRules.mergeAppearance(s.gameData,u,previous,incoming,1,music,claimed-1);
            assertEquals(0,integer(incoming.get("b_EncoreBonusAppear")));
            EncoreRules.mergeAppearance(s.gameData,u,previous,incoming,1,music,claimed+wait);
            assertEquals(1,integer(incoming.get("b_EncoreBonusAppear")));
            assertEquals(claimed+wait,lng(EncoreRules.state(u,music).get("issued_at")));
        }
    }
    @ParameterizedTest @MethodSource("chapters")
    void inactiveZeroReceiptAllowsNewRollButNeverReplay(int chapter,String backend) throws Exception {
        setup(chapter,backend);var u=user();
        var row=map(list(u.get("user_music")).getFirst());
        row.put("b_EncoreBonusAppear",0);row.put("i_EncoreBonusFollowerId",0);row.put("l_EncoreBonusActivateTime",0);
        u.put("encore_claims",obj(str(music),0));
        new emu.leman.ggserver.game.account.AuthContent(s).contents(u);
        assertEquals(1,integer(EncoreRules.state(u,music).get("legacy_placeholder")));
        s.state.saveUser(u);reopen();reject(List.of(music));
        save(song(1,music));claim();reopen();save(song(1,music));reject(List.of(music));
    }
    @ParameterizedTest @MethodSource("chapters")
    void inactiveRealReceiptStartsMigrationAtLoadNotAtNextRoll(int chapter,String backend) throws Exception {
        setup(chapter,backend);var u=user();var row=map(list(u.get("user_music")).getFirst());
        row.put("b_EncoreBonusAppear",0);u.put("encore_claims",obj(str(music),123));
        EncoreRules.normalizeAppearance(u,row,1000);
        assertEquals(1000,lng(EncoreRules.state(u,music).get("claimed_at")));
        EncoreRules.normalizeAppearance(u,row,2000);
        assertEquals(1000,lng(EncoreRules.state(u,music).get("claimed_at")));
        var incoming=song(1,music);
        EncoreRules.mergeAppearance(s.gameData,u,row,incoming,1,music,2000);
        assertEquals(0,integer(incoming.get("b_EncoreBonusAppear")));
        assertEquals(1000,lng(EncoreRules.state(u,music).get("claimed_at")));
    }
    @ParameterizedTest @MethodSource("chapters")
    void legacyReceiptMigratesWithoutTrustingItsTimeUnits(int chapter,String backend) throws Exception {
        setup(chapter,backend);var u=user();u.put("encore_claims",obj(str(music),Long.MAX_VALUE));s.state.saveUser(u);
        reject(List.of(music));save(song(1,music));reopen();reject(List.of(music));
        assertEquals(Long.MAX_VALUE,lng(map(user().get("encore_claims")).get(str(music))));
        long claimed=lng(EncoreRules.state(user(),music).get("claimed_at"));
        assertTrue(Math.abs(claimed-System.currentTimeMillis()/1000)<5);
        backdate(75601);save(song(1,music));claim();reject(List.of(music));
    }
    @ParameterizedTest @MethodSource("chapters")
    void legacyZeroReceiptIsHiddenOnLoadAndRecoversAfterCooldown(int chapter,String backend) throws Exception {
        setup(chapter,backend);var u=user();u.put("encore_claims",obj(str(music),0));s.state.saveUser(u);
        double balance=dbl(map(u.get("userdata")).get("u_candy"));
        var contents=new emu.leman.ggserver.game.account.AuthContent(s).contents(u);
        var projected=list(contents.get("user_music")).stream().map(v->map(v))
                .filter(v->integer(v.get("i_id"))==music).findFirst().orElseThrow();
        assertEquals(0,integer(projected.get("b_EncoreBonusAppear")));
        assertEquals(0,integer(projected.get("i_EncoreBonusFollowerId")));
        long claimed=lng(EncoreRules.state(u,music).get("claimed_at"));
        assertTrue(Math.abs(claimed-System.currentTimeMillis()/1000)<5);
        s.state.saveUser(u);reopen();reject(List.of(music));
        save(song(1,music));save(obj("i_id",music,"i_Level",1));reopen();
        assertEquals(claimed,lng(EncoreRules.state(user(),music).get("claimed_at")),"Stale saves must not restart cooldown");
        assertEquals(0,integer(map(list(user().get("user_music")).getFirst()).get("b_EncoreBonusAppear")));
        assertEquals(0,lng(map(user().get("encore_claims")).get(str(music))));
        assertEquals(balance,dbl(map(user().get("userdata")).get("u_candy")));
        backdate(75601);save(song(1,music));claim();save(song(1,music));reject(List.of(music));
    }
    @ParameterizedTest @MethodSource("chapters")
    void consumedLifecycleHidesStaleFlagButPendingGiftSurvivesProjection(int chapter,String backend) throws Exception {
        setup(chapter,backend);var u=user();
        u.put("encore_state",obj(str(music),obj("pending",1,"issued_at",100)));
        var song=map(list(u.get("user_music")).getFirst());
        EncoreRules.normalizeAppearance(u,song,200);
        assertEquals(1,integer(song.get("b_EncoreBonusAppear")));
        u.put("encore_state",obj(str(music),obj("pending",0,"claimed_at",150)));
        EncoreRules.normalizeAppearance(u,song,200);
        assertEquals(0,integer(song.get("b_EncoreBonusAppear")));
        assertEquals(150,lng(song.get("l_EncoreBonusActivateTime")));
        EncoreRules.normalizeAppearance(u,song,300);
        assertEquals(150,lng(EncoreRules.state(u,music).get("claimed_at")));
    }
    @ParameterizedTest @MethodSource("chapters")
    void saveReconcilesLegacyGiftEvenWhenAppearanceIsOmitted(int chapter,String backend) throws Exception {
        setup(chapter,backend);var u=user();u.put("encore_claims",obj(str(music),0));s.state.saveUser(u);
        save(obj("i_id",music,"i_Level",1));reopen();
        assertEquals(0,integer(map(list(user().get("user_music")).getFirst()).get("b_EncoreBonusAppear")));
        assertEquals(0,integer(EncoreRules.state(user(),music).get("pending")));
        assertTrue(lng(EncoreRules.state(user(),music).get("claimed_at"))>0);reject(List.of(music));
    }
    @ParameterizedTest @MethodSource("chapters")
    void invalidBatchNeverPartiallyGrantsAndValidBatchIncludesProfileBonus(int chapter,String backend) throws Exception {
        setup(chapter,backend);
        for(Object ids:List.of(List.of(),List.of(music,music),List.of(music,999999),List.of(music,1.5)))reject(ids);
        var u=user();var second=song(1,music);second.put("i_id",music+1);list(u.get("user_music")).add(second);s.state.saveUser(u);
        double before=dbl(map(user().get("userdata")).get("u_candy"));
        var result=call("getMusicReward","i_ids",List.of(music,music+1));assertEquals(0,integer(result.error().get("code")));
        assertEquals(26,integer(map(result.data()).get("total_reward_value")));
        assertEquals(List.of(13,13),list(map(result.data()).get("reward_value")));
        assertEquals(before+26,dbl(map(user().get("userdata")).get("u_candy")));reject(List.of(music,music+1));
    }
    @ParameterizedTest @MethodSource("chapters")
    void concurrentClaimsPayOnce(int chapter,String backend) throws Exception {
        setup(chapter,backend);double before=dbl(map(user().get("userdata")).get("u_candy"));
        try(var pool=Executors.newFixedThreadPool(8)) {
            List<Callable<Integer>> tasks=new ArrayList<>();
            for(int i=0;i<16;i++)tasks.add(()->integer(call("getMusicReward","i_ids",List.of(music)).error().get("code")));
            int successes=0;for(var future:pool.invokeAll(tasks))if(future.get()==0)successes++;
            assertEquals(1,successes);
        }
        assertEquals(before+13,dbl(map(user().get("userdata")).get("u_candy")));reopen();reject(List.of(music));
    }
    @ParameterizedTest @ValueSource(ints={1,2})
    void failedSaveRollsBackEntireClaimAndAllowsRetry(int chapter) throws Exception {
        setup(chapter,"sqlite");s.events.setStarPass(true,3,false);String before=stringify(user());
        try(var db=DriverManager.getConnection("jdbc:sqlite:"+root.resolve("data/database.db"));var sql=db.createStatement()) {
            sql.execute("CREATE TRIGGER encore_fail BEFORE UPDATE OF u_candy ON user_data BEGIN SELECT RAISE(ABORT,'test'); END");
            assertThrows(IllegalStateException.class,this::claim);assertEquals(before,stringify(user()));
            sql.execute("DROP TRIGGER encore_fail");
        }
        claim();reopen();reject(List.of(music));
    }
    @ParameterizedTest @MethodSource("chapters")
    void malformedSavedFollowerIdCannotAliasAValidFollower(int chapter,String backend) throws Exception {
        setup(chapter,backend);
        for(Object invalid:List.of(music+0.5,4_294_967_296L+music,"not-an-id")) {
            var u=user();map(list(u.get("user_music")).getFirst()).put("i_EncoreBonusFollowerId",invalid);
            s.state.saveUser(u);reject(List.of(music));
        }
    }
    @ParameterizedTest @MethodSource("chapters")
    void malformedSavedLevelCannotWrapIntoARewardRow(int chapter,String backend) throws Exception {
        setup(chapter,backend);
        // Both repositories canonicalize inventory levels to long on save; test values
        // that remain invalid after that round trip rather than an already-truncated float.
        for(Object invalid:List.of(4_294_967_297L,0,-1,"not-a-level")) {
            var u=user();map(list(u.get("user_music")).getFirst()).put("i_Level",invalid);
            s.state.saveUser(u);reject(List.of(music));
        }
    }
    @ParameterizedTest @MethodSource("chapters")
    void responseWithoutProfileBonusMatchesBalance(int chapter,String backend) throws Exception {
        setup(chapter,backend);var u=user();map(list(u.get("user_follower_profile")).getFirst()).put("i_AddCandy",0);s.state.saveUser(u);
        double before=dbl(map(user().get("userdata")).get("u_candy"));var result=claim();
        assertEquals(10,integer(result.get("total_reward_value")));assertEquals(List.of(10),list(result.get("reward_value")));
        assertEquals(before+10,dbl(map(user().get("userdata")).get("u_candy")));
    }
}

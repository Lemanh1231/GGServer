package emu.leman.ggserver.game.economy;

import de.bwaldvogel.mongo.MongoServer;
import de.bwaldvogel.mongo.backend.memory.MemoryBackend;
import emu.leman.ggserver.Services;
import emu.leman.ggserver.config.ServerConfig;
import emu.leman.ggserver.game.content.EventManager;
import emu.leman.ggserver.game.content.ContentModule;
import emu.leman.ggserver.net.Result;
import java.nio.file.*;
import java.sql.DriverManager;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

/** Real catalog, isolated stores; no live accounts, purchases, or configuration. */
class StarPassPurchaseRegressionTest {
    @TempDir Path root;
    Services s;
    ServerConfig config;
    MongoServer mongo;

    void setup(String backend) throws Exception {
        Files.createDirectories(root.resolve("gamedata"));
        Files.copy(Path.of("resources/gamedata/game_data.json"),root.resolve("gamedata/game_data.json"));
        Files.createDirectories(root.resolve("schema"));
        Files.copy(Path.of("resources/schema/schema.json"),root.resolve("schema/schema.json"));
        write(root.resolve("event_config.json"),EventManager.defaults());
        config=ServerConfig.defaults(root);
        if(backend.equals("mongo")) {
            mongo=new MongoServer(new MemoryBackend());var address=mongo.bind();
            config=ServerConfig.defaults(root,obj("database",obj("backend","mongo","name","purchase_test",
                    "uri","mongodb://"+address.getHostString()+":"+address.getPort()+"/?serverSelectionTimeoutMS=5000")));
        }
        reopen();s.events.setStarPass(true,3,true);
        var u=s.state.createUser("purchase-test","synthetic-device");
        map(u.get("userdata")).put("u_cp",1000);s.state.saveUser(u);
    }
    void reopen() {if(s!=null)s.close();s=new Services(config);new EconomyModule(s).register();}
    @AfterEach void close() {try {if(s!=null)s.close();} finally {if(mongo!=null)mongo.shutdownNow();}}
    Map<String,Object> user() {return s.state.getUser("purchase-test");}
    long cp() {return lng(map(user().get("userdata")).get("u_cp"));}
    Result call(String cmd,Object... args) {return s.registry.handle(cmd,obj("data",obj(args)),obj("uuid","purchase-test"));}
    void ok(Result r) {assertEquals(0,integer(r.error().get("code")),r.error().toString());}
    void rejectedUnchanged(Object id) {
        String before=stringify(user());assertNotEquals(0,integer(call("buyShop","idx",id).error().get("code")));
        assertEquals(before,stringify(user()));
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void merchandiseAliasesChargeOnceGrantEntitlementAndSurviveReopen(String backend) throws Exception {
        setup(backend);String before=stringify(user());ok(call("buyCheck","idx",2003));
        assertEquals(before,stringify(user()),"Preflight must not persist normalization");
        var response=call("buyShop","idx",2003);ok(response);assertEquals(950,cp());
        assertFalse(list(map(response.data()).get("reward_data")).isEmpty());
        for(int id:List.of(3,1003)) {
            assertEquals(1,list(user().get("user_subscribe_list")).stream().filter(r->integer(map(r).get("i_SubscribeID"))==id).count());
            assertEquals(1,list(user().get("user_ticketcollection")).stream().filter(r->integer(map(r).get("i_id"))==id).count());
        }
        for(int id:List.of(2003,3003)) {
            assertEquals(1,list(user().get("user_shop")).stream().filter(r->integer(map(r).get("i_id"))==id&&lng(map(r).get("i_TotalCount"))==1).count());
        }
        reopen();rejectedUnchanged(2003);rejectedUnchanged(3003);rejectedUnchanged(1003);
        assertEquals(1,integer(map(call("checkBuyShop","shop_id",3003).data()).get("is_owner")));
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void starCardChargesCatalogPriceAndPreservesPassProgress(String backend) throws Exception {
        setup(backend);var u=user();
        var progress=List.of(obj("s_EventType","Pass","i_DataID",3,"i_Point",123,"i_Step",2,"i_Version",6));
        u.put("user_event_point",progress);s.state.saveUser(u);
        var result=call("buyShop","idx",1003);ok(result);
        assertEquals(1550,cp()); // Catalog price 50 CP, immediate reward 600 CP.
        assertTrue(list(map(result.data()).get("reward_data")).stream().anyMatch(r->integer(map(r).get("reward_type"))==1
                &&integer(map(r).get("reward_id"))==1&&lng(map(r).get("reward_value"))==600));
        assertEquals(stringify(progress),stringify(user().get("user_event_point")));rejectedUnchanged(1003);
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void insufficientFundsDisabledEventsAndMalformedIdsDoNotMutate(String backend) throws Exception {
        setup(backend);var u=user();map(u.get("userdata")).put("u_cp",49);s.state.saveUser(u);
        rejectedUnchanged(2003);rejectedUnchanged(1003);rejectedUnchanged("2003.0");rejectedUnchanged(999999);
        map(u.get("userdata")).put("u_cp",1000);s.state.saveUser(u);
        var cfg=s.events.snapshot();map(cfg.get("pass_goods_sale")).put("enabled",false);s.events.saveConfig(cfg);
        rejectedUnchanged(2003);rejectedUnchanged(3003);
        assertNotEquals(0,integer(call("buyCheck","idx",3003).error().get("code")));
        s.events.setStarPass(true,3,false);rejectedUnchanged(1003);
        s.events.setStarPass(true,3,true);ok(call("buyShop","idx",1003)); // toggles refresh immediately
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void concurrentAliasesGrantAndDeductOnlyOnce(String backend) throws Exception {
        setup(backend);
        var user=user();var data=map(user.get("userdata"));
        var aliases=List.of("purchase-test","synthetic-device",str(data.get("u_seq")),str(data.get("u_id")));
        for(String alias:aliases)assertEquals("purchase-test",s.state.canonicalIdentity(alias));
        assertEquals("unknown-alias",s.state.canonicalIdentity("unknown-alias"));
        try(var pool=Executors.newVirtualThreadPerTaskExecutor()) {
            var work=new ArrayList<Callable<Result>>();
            for(int i=0;i<12;i++) {
                int id=i%2==0?2003:3003;String alias=aliases.get(i%aliases.size());
                work.add(()->s.registry.handle("buyShop",obj("data",obj("idx",id)),obj("uuid",alias)));
            }
            int successes=0;for(var future:pool.invokeAll(work))if(integer(future.get().error().get("code"))==0)successes++;
            assertEquals(1,successes);
        }
        assertEquals(950,cp());rejectedUnchanged(2003);rejectedUnchanged(3003);
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void saleClosureAfterPreflightBlocksBothAliasesAndRefreshesClientProjection(String backend) throws Exception {
        setup(backend);ok(call("buyCheck","idx",3003));
        var content=new ContentModule(s);
        var open=content.filteredGameData();
        for(Object raw:list(open.get("shop"))) {
            var row=map(raw);int id=integer(row.get("i_id"));
            if(id==2003||id==3003) {
                assertEquals(50,lng(row.get("i_SellValue")));
                for(String key:List.of("s_StorePrice_AOS","s_StorePrice_IOS","s_Kor_StorePrice_AOS","s_Kor_StorePrice_IOS"))
                    assertEquals("50",row.get(key));
            }
        }
        // Projection is detached; immutable public catalog remains the original.
        assertEquals(120,lng(s.gameData.row(12,2003).get("34")));
        s.events.setPassGoodsSaleEnabled(false);
        for(int season=1;season<=13;season++)for(int offset:List.of(2000,3000)) {
            int id=offset+season;
            assertNotEquals(0,integer(call("buyCheck","idx",id).error().get("code")));
            assertEquals(1,integer(map(call("checkBuyShop","shop_id",id).data()).get("is_owner")));
            rejectedUnchanged(id);
        }
        var closed=list(content.filteredGameData().get("shop"));
        assertEquals(26,closed.stream().map(emu.leman.ggserver.util.Json::map)
                .filter(r->StarPassShopRules.merchandise(integer(r.get("i_id")))&&integer(r.get("b_IsActive"))==0).count());
        s.events.setPassGoodsSaleEnabled(true);
        assertEquals(26,list(content.filteredGameData().get("shop")).stream().map(emu.leman.ggserver.util.Json::map)
                .filter(r->StarPassShopRules.merchandise(integer(r.get("i_id")))&&integer(r.get("b_IsActive"))==1).count());
        ok(call("buyShop","idx",3003));assertEquals(950,cp());
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void corruptOrMissingSaleConfigFailsClosedWithoutAccountChanges(String backend) throws Exception {
        setup(backend);
        Files.writeString(root.resolve("event_config.json"),"{broken");
        rejectedUnchanged(2003);rejectedUnchanged(3003);
        write(root.resolve("event_config.json"),obj("pass_goods_sale",obj("enabled","true")));
        rejectedUnchanged(3003);
        Files.delete(root.resolve("event_config.json"));rejectedUnchanged(3003);
    }
    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void malformedRewardDefinitionRollsBackDetachedDeduction(String backend) throws Exception {
        setup(backend);
        var catalog=map(read(root.resolve("gamedata/game_data.json")));
        for(Object raw:list(catalog.get("13")))if(integer(map(raw).get("2"))==7036000)map(raw).put("5","1.5");
        write(root.resolve("gamedata/game_data.json"),catalog);reopen();rejectedUnchanged(2003);
    }
    @Test void failedSqliteBatchRollsBackPaymentInventoriesAndReceipts() throws Exception {
        setup("sqlite");String before=stringify(user());
        try(var db=DriverManager.getConnection("jdbc:sqlite:"+config.database());var statement=db.createStatement()) {
            statement.execute("CREATE TRIGGER fail_purchase BEFORE INSERT ON user_inventory WHEN NEW.item_type='shop' BEGIN SELECT RAISE(ABORT,'synthetic save failure'); END");
            assertThrows(IllegalStateException.class,()->call("buyShop","idx",2003));
            assertEquals(before,stringify(user()));
            statement.execute("DROP TRIGGER fail_purchase");
        }
        ok(call("buyShop","idx",2003));assertEquals(950,cp());reopen();rejectedUnchanged(3003);
    }
}

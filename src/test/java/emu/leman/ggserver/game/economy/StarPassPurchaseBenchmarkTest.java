package emu.leman.ggserver.game.economy;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.config.ServerConfig;
import emu.leman.ggserver.game.content.EventManager;
import de.bwaldvogel.mongo.MongoServer;
import de.bwaldvogel.mongo.backend.memory.MemoryBackend;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

/** Repeatable synthetic characterization, not a network SLA or a timing assertion. */
class StarPassPurchaseBenchmarkTest {
    @TempDir Path root;

    @ParameterizedTest @CsvSource({"sqlite,2003","sqlite,1003","mongo,2003","mongo,1003"})
    void purchaseWithRealCatalogAndPopulatedInventory(String backend,int product) throws Exception {
        Files.createDirectories(root.resolve("gamedata"));
        Files.copy(Path.of("resources/gamedata/game_data.json"),root.resolve("gamedata/game_data.json"));
        write(root.resolve("event_config.json"),EventManager.defaults());
        MongoServer mongo=null;
        var config=ServerConfig.defaults(root);
        if(backend.equals("mongo")) {
            mongo=new MongoServer(new MemoryBackend());var address=mongo.bind();
            config=ServerConfig.defaults(root,obj("database",obj("backend","mongo","name","benchmark_only",
                    "uri","mongodb://"+address.getHostString()+":"+address.getPort()+"/?serverSelectionTimeoutMS=5000")));
        }
        try(var s=new Services(config)) {
            s.events.setStarPass(true,3,true);
            var base=s.state.createUser("benchmark-only","synthetic-device");
            map(base.get("userdata")).put("u_cp",10000);
            var catalog=map(read(root.resolve("gamedata/game_data.json")));
            for(var entry:Map.of("user_music",2,"costumes",3,"user_prop",4,"user_guitar",20,"user_follower",5).entrySet()) {
                var inventory=new ArrayList<Object>();
                for(Object raw:list(catalog.get(str(entry.getValue())))) {
                    int id=integer(map(raw).get("1"));
                    if(id>0)inventory.add(obj("i_id",id,"i_Level",10,"i_BonusLevel",1));
                }
                base.put(entry.getKey(),inventory);
            }
            var shop=new ArrayList<Object>();
            for(Object raw:list(catalog.get("12"))) {
                int id=integer(map(raw).get("1"));
                if(id<1000||id>3020)shop.add(obj("i_id",id,"i_Count",0,"i_TotalCount",0,"i_Level",1));
            }
            base.put("user_shop",shop);
            new EconomyModule(s).register();
            var samples=new LinkedHashMap<String,List<Long>>();
            for(String phase:List.of("load","save","buyCheck","buyShop","checkBuyShop","workflow"))samples.put(phase,new ArrayList<>());
            for(int i=0;i<120;i++) {
                s.state.saveUser(base);
                long start=System.nanoTime();var loaded=s.state.getUser("benchmark-only");
                record(samples,"load",start,i);
                start=System.nanoTime();s.state.saveUser(loaded);record(samples,"save",start,i);
                long workflow=System.nanoTime();
                for(String cmd:List.of("buyCheck","buyShop","checkBuyShop")) {
                    start=System.nanoTime();
                    var result=s.registry.handle(cmd,obj("data",obj(cmd.equals("checkBuyShop")?"shop_id":"idx",product)),obj("uuid","benchmark-only"));
                    record(samples,cmd,start,i);assertEquals(0,integer(result.error().get("code")));
                    if(cmd.equals("checkBuyShop"))assertEquals(1,integer(map(result.data()).get("is_owner")));
                }
                record(samples,"workflow",workflow,i);
            }
            samples.forEach((phase,times)-> {
                Collections.sort(times);
                System.out.printf(Locale.ROOT,"STAR_PASS_BENCH %s product=%d %s n=%d p50_ms=%.3f p95_ms=%.3f%n",backend,product,phase,times.size(),times.get(times.size()/2)/1e6,times.get((times.size()*95-1)/100)/1e6);
            });
            System.out.println("STAR_PASS_BENCH inventory_rows="+List.of("user_music","costumes","user_prop","user_guitar","user_follower").stream().mapToInt(k->list(base.get(k)).size()).sum());
        } finally {if(mongo!=null)mongo.shutdownNow();}
    }
    private static void record(Map<String,List<Long>> samples,String phase,long start,int iteration) {
        if(iteration>=40)samples.get(phase).add(System.nanoTime()-start);
    }
}

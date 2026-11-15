package emu.leman.ggserver.server;

import de.bwaldvogel.mongo.MongoServer;
import de.bwaldvogel.mongo.backend.memory.MemoryBackend;
import emu.leman.ggserver.Services;
import emu.leman.ggserver.config.ServerConfig;
import emu.leman.ggserver.game.GameContext;
import emu.leman.ggserver.net.codec.Codec;
import java.nio.file.*;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

/** Inventory and regressions for confirmed audit findings.
 * All accounts/storage are disposable. Requests and responses use the native schema codec. */
class RpcLogicAuditTest {
    @TempDir Path root;

    @Test void inventoryEveryWireCommandWithoutExecutingGameplay() throws Exception {
        try(var f=new Fixture("sqlite",false)) {
            var owners=new TreeMap<String,String>();
            f.game.commands().forEach((owner,names)->names.forEach(name->owners.put(name,owner)));
            var rows=new ArrayList<Object>();
            for(var entry:f.codec.schema.entrySet()) {
                var spec=map(entry.getValue());var fields=list(spec.get("fields"));
                var names=new HashSet<String>();fields.forEach(v->names.add(str(map(v).get("name"))));
                if(!names.containsAll(List.of("call","data"))||str(spec.get("name")).endsWith("Return"))continue;
                String wire=entry.getKey(),simple=str(spec.get("name")),ret=f.dispatch.returnDtoFor(wire);
                assertNotNull(ret,wire);
                String requestDto=fields.stream().map(v->map(v)).filter(v->"data".equals(v.get("name")))
                        .map(v->str(v.get("struct"))).findFirst().orElse("");
                var empty=f.dispatch.buildReturn(wire,obj(),simple,str(spec.get("ns")),null);
                f.codec.decodeRequest(f.codec.encodeResponse(empty.dto(),empty.data()),empty.dto());
                rows.add(obj("wire",wire,"simple",simple,"owner",owners.getOrDefault(simple,"legacy-fallback"),
                        "requestDto",requestDto,"returnDto",ret,"returnDataDto",f.dispatch.retdataDtoFor(wire),
                        "bootstrap",emu.leman.ggserver.net.CmdId.BOOTSTRAP.contains(wire)));
            }
            assertEquals(134,rows.size());assertEquals(129,rows.stream().map(v->map(v).get("simple")).distinct().count());
            String output=System.getProperty("rpc.audit.inventory");
            if(output!=null)write(Path.of(output),rows);
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void profileReturnsRequestedTarget(String backend) throws Exception {
        try(var f=new Fixture(backend,false)) {
            var target=f.s.state.createUser("target","bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb");
            map(target.get("userdata")).put("u_nick","Target profile");f.s.state.saveUser(target);
            var response=f.call("user.getProfile",obj("get_u_seq",map(target.get("userdata")).get("u_seq")));
            assertEquals("Target profile",map(response.get("data")).get("u_nick"));
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void disabledCookieAdCannotGrantAp(String backend) throws Exception {
        try(var f=new Fixture(backend,true)) {
            assertEquals(0,integer(f.s.gameData.row(32,2).get("20")));
            int before=f.ap();var response=f.call("user.setAdReward",obj("i_id",2));
            assertNotEquals(0,integer(map(response.get("error")).get("code")));
            assertTrue(list(map(response.get("data")).get("reward_data")).isEmpty());
            assertEquals(before,f.ap());
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void cookieAdRetryRespectsCatalogCooldown(String backend) throws Exception {
        try(var f=new Fixture(backend,false)) {
            var definition=f.s.gameData.row(32,2);
            assertEquals("COOLTIME",definition.get("5"));assertEquals(300,integer(definition.get("6")));
            int before=f.ap();
            var first=map(f.call("user.setAdReward",obj("i_id",2)).get("data"));
            var second=map(f.call("user.setAdReward",obj("i_id",2)).get("data"));
            long a=lng(map(first.get("user_ad_list")).get("i_LastViewTime"));
            long b=lng(map(second.get("user_ad_list")).get("i_LastViewTime"));
            assertEquals(a,b);assertTrue(list(second.get("reward_data")).isEmpty());
            assertEquals(before+25,f.ap());
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void nativeDailySaveCannotLowerClaimedTierDespiteDirectMapSuspicion(String backend) throws Exception {
        try(var f=new Fixture(backend,false)) {
            var claimed=map(f.call("user.setGameReward",obj("type","daily_mission","id",2,"level",1,"s_quantity","2000")).get("data"));
            assertEquals("Y",claimed.get("status"));
            f.call("user.userSave",obj("user_daily_mission",List.of(obj("i_id",2,"i_Level",1,"d_Quantity",0))));
            var mission=list(f.s.state.getUser("requester").get("user_daily_mission")).stream().map(v->map(v))
                    .filter(v->integer(v.get("i_id"))==2).findFirst().orElseThrow();
            assertEquals(2,integer(mission.get("i_Level")));
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void confirmedFindingsAreReachableOverHttpWithRequiredSession(String backend) throws Exception {
        try(var f=new Fixture(backend,false);var server=new GameServer(f.s)) {
            assertTrue(f.s.config.sessionRequired);
            var target=f.s.state.createUser("http-target","cccccccccccccccccccccccccccccccc");
            map(target.get("userdata")).put("u_nick","HTTP target");f.s.state.saveUser(target);
            String base="http://127.0.0.1:"+server.start("127.0.0.1",0,null).getAddress().getPort();
            String token=f.s.sessions.create("requester","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","").token();
            var client=HttpClient.newHttpClient();
            var profile=f.http(client,base,token,"user.getProfile",obj("get_u_seq",map(target.get("userdata")).get("u_seq")));
            assertEquals("HTTP target",map(profile.get("data")).get("u_nick"));
            int before=f.ap();
            f.http(client,base,token,"user.setAdReward",obj("i_id",2));
            var retry=f.http(client,base,token,"user.setAdReward",obj("i_id",2));
            assertTrue(list(map(retry.get("data")).get("reward_data")).isEmpty());assertEquals(before+25,f.ap());
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void disabledCookieAdRejectedOverAuthenticatedHttp(String backend) throws Exception {
        try(var f=new Fixture(backend,true);var server=new GameServer(f.s)) {
            String base="http://127.0.0.1:"+server.start("127.0.0.1",0,null).getAddress().getPort();
            String token=f.s.sessions.create("requester","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","").token();
            int before=f.ap();
            var response=f.http(HttpClient.newHttpClient(),base,token,"user.setAdReward",obj("i_id",2));
            assertNotEquals(0,integer(map(response.get("error")).get("code")));
            assertTrue(list(map(response.get("data")).get("reward_data")).isEmpty());assertEquals(before,f.ap());
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void malformedProfileUpdateCannotMutateOverHttp(String backend) throws Exception {
        try(var f=new Fixture(backend,false);var server=new GameServer(f.s)) {
            String base="http://127.0.0.1:"+server.start("127.0.0.1",0,null).getAddress().getPort();
            String token=f.s.sessions.create("requester","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","").token();
            var client=HttpClient.newHttpClient();
            String missingData=f.codec.encodeResponse("user.updateNickName",obj("call","user.updateNickName"));
            for(String extra:List.of("", "&tapsonic_data=not-a-valid-native-message",
                    "&tapsonic_data="+URLEncoder.encode(missingData,StandardCharsets.UTF_8))) {
                var user=f.s.state.getUser("requester");map(user.get("userdata")).put("u_nick","Requester profile");f.s.state.saveUser(user);
                String body="call=user.updateNickName&access_token="+URLEncoder.encode(token,StandardCharsets.UTF_8)+extra;
                var response=client.send(HttpRequest.newBuilder(URI.create(base+"/user/updateNickName/vi/"))
                        .header("Content-Type","application/x-www-form-urlencoded").POST(HttpRequest.BodyPublishers.ofString(body)).build(),HttpResponse.BodyHandlers.ofString());
                assertEquals(200,response.statusCode());
                var envelope=f.codec.decodeRequest(response.body(),"user.updateNickNameReturn").named();
                assertEquals(400,integer(map(envelope.get("error")).get("code")));
                assertEquals("Requester profile",map(f.s.state.getUser("requester").get("userdata")).get("u_nick"));
            }
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void reciprocalProfileReadsDoNotDeadlockOrExposePrivateFields(String backend) throws Exception {
        try(var f=new Fixture(backend,false);var executor=java.util.concurrent.Executors.newVirtualThreadPerTaskExecutor()) {
            var target=f.s.state.createUser("target","bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb");
            map(target.get("userdata")).put("u_nick","Target");f.s.state.saveUser(target);
            String a=str(map(f.s.state.getUser("requester").get("userdata")).get("u_seq"));
            String b=str(map(target.get("userdata")).get("u_seq"));
            var work=new ArrayList<java.util.concurrent.Callable<emu.leman.ggserver.net.Result>>();
            for(int i=0;i<10;i++) {
                work.add(()->f.s.registry.handle("getProfile",obj("data",obj("uuid","requester","get_u_seq",b)),obj()));
                work.add(()->f.s.registry.handle("getProfile",obj("data",obj("uuid","target","get_u_seq",a)),obj()));
            }
            var results=executor.invokeAll(work,20,java.util.concurrent.TimeUnit.SECONDS);
            for(int i=0;i<results.size();i++) {
                assertFalse(results.get(i).isCancelled(),"Cross-account read must not nest account locks");
                var result=results.get(i).get();assertEquals(i%2==0?"Target":"Requester profile",map(result.data()).get("u_nick"));
                assertFalse(map(result.data()).containsKey("device_uuid"));assertFalse(map(result.data()).containsKey("u_cp"));
            }
            var missing=f.call("user.getProfile",obj("get_u_seq",999999999));
            assertNotEquals(0,integer(map(missing.get("error")).get("code")));
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void catalogSkillAndUnitGatesRejectWithoutChargingAndAllowExactBoundary(String backend) throws Exception {
        try(var f=new Fixture(backend,false)) {
            var user=f.s.state.getUser("requester");
            user.put("user_skill",new ArrayList<>());user.put("user_unit",new ArrayList<>());
            map(user.get("userdata")).put("u_cp",10000);
            user.put("characters",new ArrayList<>(List.of(obj("i_id",1,"i_Level",99),obj("i_id",2,"i_Level",99))));
            f.s.state.saveUser(user);
            for(var spec:List.of(obj("type","skill","id",1,"level",100,"area",1),
                    obj("type","skill","id",21,"level",100,"area",2),obj("type","unit","id",2,"level",300,"area",1))) {
                user=f.s.state.getUser("requester");
                for(var raw:list(user.get("characters"))) if(integer(map(raw).get("i_id"))==integer(spec.get("area")))
                    map(raw).put("i_Level",integer(spec.get("level"))-1);
                f.s.state.saveUser(user);
                long before=lng(map(user.get("userdata")).get("u_cp"));
                var rejected=f.call("store.buyContents",obj("type",spec.get("type"),"idx",spec.get("id")));
                assertNotEquals(0,integer(map(rejected.get("error")).get("code")));
                assertEquals(before,lng(map(f.s.state.getUser("requester").get("userdata")).get("u_cp")));
                user=f.s.state.getUser("requester");
                for(var raw:list(user.get("characters"))) if(integer(map(raw).get("i_id"))==integer(spec.get("area")))
                    map(raw).put("i_Level",spec.get("level"));
                f.s.state.saveUser(user);
                var accepted=f.call("store.buyContents",obj("type",spec.get("type"),"idx",spec.get("id")));
                assertEquals(0,integer(map(accepted.get("error")).get("code")));
                String key="user_"+spec.get("type");
                assertEquals(spec.get("type").equals("skill")?2:1,integer(map(map(accepted.get("data")).get(key)).get("i_Level")));
                assertTrue(lng(map(f.s.state.getUser("requester").get("userdata")).get("u_cp"))<before);
            }
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void skillProjectionUsesCatalogAndPreservesEarnedProgress(String backend) throws Exception {
        try(var f=new Fixture(backend,false)) {
            var user=f.s.state.getUser("requester");
            user.put("user_skill",new ArrayList<>());
            user.put("characters",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1),obj("i_id",2,"i_Level",1))));
            var content=new emu.leman.ggserver.game.account.AuthContent(f.s);
            content.contents(user);
            assertEquals(Set.of(4,24),list(user.get("user_skill")).stream().map(v->integer(map(v).get("i_id"))).collect(java.util.stream.Collectors.toSet()));
            list(user.get("user_skill")).add(obj("i_id",3,"i_Level",9,"b_Activate",1,"l_ActivateOffTicks",12345));
            content.contents(user);
            var earned=list(user.get("user_skill")).stream().map(v->map(v)).filter(v->integer(v.get("i_id"))==3).findFirst().orElseThrow();
            assertEquals(9,integer(earned.get("i_Level")));assertEquals(12345,lng(earned.get("l_ActivateOffTicks")));
            f.s.state.saveUser(user);
            assertEquals(3,list(f.s.state.getUser("requester").get("user_skill")).size());
        }
    }

    @ParameterizedTest @ValueSource(strings={"sqlite","mongo"})
    void concurrentAdRetriesGrantOnlyOnce(String backend) throws Exception {
        try(var f=new Fixture(backend,false);var executor=java.util.concurrent.Executors.newVirtualThreadPerTaskExecutor()) {
            int before=f.ap();
            var work=new ArrayList<java.util.concurrent.Callable<Map<String,Object>>>();
            for(int i=0;i<8;i++) work.add(()->f.call("user.setAdReward",obj("i_id",2)));
            int grants=0;
            for(var result:executor.invokeAll(work)) if(!list(map(result.get().get("data")).get("reward_data")).isEmpty()) grants++;
            assertEquals(1,grants);assertEquals(before+25,f.ap());
            var persisted=map(map(f.s.state.getUser("requester").get("ad_rewards")).get("2"));
            assertEquals(1,integer(persisted.get("i_Count")));assertEquals(1,integer(persisted.get("i_TotalCount")));
        }
    }

    private final class Fixture implements AutoCloseable {
        final MongoServer mongo;
        final Services s;
        final GameContext game;
        final Codec codec;
        final Dispatch dispatch;
        Fixture(String backend,boolean disabled) throws Exception {
            for(String name:List.of("schema/schema.json","gamedata/game_data.json","gamedata/tour_drop_weights.json")) {
                var target=root.resolve(name);Files.createDirectories(target.getParent());
                Files.copy(Path.of("resources").resolve(name),target);
            }
            if(disabled) {
                var catalog=map(read(root.resolve("gamedata/game_data.json")));
                list(catalog.get("32")).stream().map(v->map(v)).filter(v->integer(v.get("1"))==2).forEach(v->v.put("20",0));
                write(root.resolve("gamedata/game_data.json"),catalog);
            }
            String uri="mongodb://127.0.0.1:27017";
            if(backend.equals("mongo")) {mongo=new MongoServer(new MemoryBackend());var address=mongo.bind();uri="mongodb://"+address.getHostString()+":"+address.getPort();}
            else mongo=null;
            s=new Services(ServerConfig.defaults(root,obj("sessions",obj("required",true),"database",obj("backend",backend,"uri",uri,"name","rpc_logic_audit"))));
            game=new GameContext(s).registerModules();codec=new Codec(root);dispatch=new Dispatch(codec);
            var user=s.state.createUser("requester","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa");
            map(user.get("userdata")).put("u_nick","Requester profile");s.state.saveUser(user);
        }
        int ap() {return integer(map(s.state.getUser("requester").get("user_ap")).get("i_Ap"));}
        Map<String,Object> call(String wire,Map<String,Object> data) throws Exception {
            assertFalse(codec.schemaFor(wire).isEmpty(),"Unknown wire RPC: "+wire);
            data.put("uuid","requester");
            var request=codec.decodeRequest(codec.encodeResponse(wire,obj("call",wire,"data",data)),wire).named();
            var result=s.registry.handle(str(codec.schemaFor(wire).get("name")),request,obj("uuid","requester"));
            var envelope=dispatch.buildReturn(wire,result.data(),str(codec.schemaFor(wire).get("name")),str(codec.schemaFor(wire).get("ns")),result.error());
            return codec.decodeRequest(codec.encodeResponse(envelope.dto(),envelope.data()),envelope.dto()).named();
        }
        Map<String,Object> http(HttpClient client,String base,String token,String wire,Map<String,Object> data) throws Exception {
            data.put("uuid","requester");
            String message=codec.encodeResponse(wire,obj("call",wire,"data",data));
            String body="call="+wire+"&access_token="+URLEncoder.encode(token,StandardCharsets.UTF_8)
                    +"&tapsonic_data="+URLEncoder.encode(message,StandardCharsets.UTF_8);
            var response=client.send(HttpRequest.newBuilder(URI.create(base+"/"+wire.replace('.','/')+"/vi/"))
                    .header("Content-Type","application/x-www-form-urlencoded").POST(HttpRequest.BodyPublishers.ofString(body)).build(),HttpResponse.BodyHandlers.ofString());
            assertEquals(200,response.statusCode());
            var decoded=codec.decodeRequest(response.body(),dispatch.returnDtoFor(wire)).named();
            return decoded;
        }
        @Override public void close() {try{s.close();}finally{if(mongo!=null)mongo.shutdownNow();}}
    }
}

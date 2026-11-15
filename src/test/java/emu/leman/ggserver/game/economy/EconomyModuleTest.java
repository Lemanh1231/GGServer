package emu.leman.ggserver.game.economy;

import emu.leman.ggserver.net.Result;

import emu.leman.ggserver.Services;
import java.nio.file.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
import static emu.leman.ggserver.util.Json.*;

class EconomyModuleTest {
    @TempDir Path root;
    Services s;
    final TestClock clock = new TestClock();
    static class TestClock extends Clock {
        Instant time=Instant.now();
        public ZoneId getZone() { return ZoneId.systemDefault(); }
        public Clock withZone(ZoneId zone) { return Clock.fixed(time,zone); }
        public Instant instant() { return time; }
        void advance(long seconds) { time=time.plusSeconds(seconds); }
    }

    @BeforeEach void setup() throws Exception {
        Files.createDirectories(root.resolve("gamedata"));
        write(root.resolve("gamedata/game_data.json"),obj(
                "12",List.of(obj("1",3,"31",200010,"33",0,"36",4,"37",900),
                        obj("1",10012,"31",600,"33",0,"36",5,"37",1),
                        obj("1",2003,"31",700,"33",1,"34",100,"36",1,"37",1),
                        obj("1",1001,"31",900,"33",1,"34",30)),
                "13",List.of(obj("2",200010,"3",1,"4",1,"5",10),obj("2",200020,"3",1,"4",1,"5",20),
                        obj("2",600,"3",6,"4",2,"5",60),obj("2",700,"3",3,"4",99,"5",1),
                        obj("2",800,"3",1,"4",1,"5",25),obj("2",801,"3",11,"4",3,"5",2),
                        obj("2",900,"3",10,"4",1,"5",1),obj("2",10010,"3",3,"4",42,"5",1),obj("2",10130,"3",1,"4",1,"5",500)),
                "3",List.of(obj("1",99)),"6",List.of(obj("1",2)),
                "37",List.of(obj("1",200010,"2",1,"3",0,"4",200010),obj("1",200010,"2",2,"3",5,"4",200020)),
                "18",List.of(obj("2",1,"3",1,"4",10,"5",800,"6",801)),
                "17",List.of(obj("1",1,"11",2020,"7",1,"3","Pass")),
                "19",List.of(obj("1",1,"4",5,"5",50,"8",10)),
                "10",List.of(obj("1",1,"29","CP","28",1,"42",7)),
                "9",List.of(obj("1",1,"28","CP","41",11,"55",1,"56","1")),
                "2",List.of(obj("1",50,"45","CP","39",0,"46",12),obj("1",51,"45","USD","39",20),obj("1",52,"45","CP","39",-1)),
                "5",List.of(obj("1",1,"47",1)),
                "28",List.of(obj("1",1,"14",1,"15","1")),
                "32",List.of(obj("1",1,"2",1)),
                "31",List.of(obj("2",1,"3",1,"4",0,"7",0),obj("2",1,"3",2,"4",50,"7",3),obj("2",1,"3",3,"4",150,"7",4))));
        write(root.resolve("gamedata/getEventRewardList.json"),obj("data",obj(
                "1",obj("group_idx",1,"reward_list",List.of(
                        obj("reward_num",1,"reward_type",1,"reward_id",1,"reward_value",100,"reward_flg","Y","get_date",20240101),
                        obj("reward_num",2,"reward_type",1,"reward_id",2,"reward_value",10,"reward_flg","Y","get_date",20240102))),
                "2",obj("group_idx",2,"reward_list",List.of(obj("reward_num",1,"reward_type",13,"reward_id",10,"reward_value",1,"reward_flg","Y"))))));
        write(root.resolve("event_config.json"),emu.leman.ggserver.game.content.EventManager.defaults());
        s = new Services(root);
        Map<String,Object> user = s.state.createUser("canonical","device");
        map(user.get("userdata")).put("u_cp",1000);
        map(user.get("userdata")).put("u_candy",1000.0);
        s.state.saveUser(user);
        new EconomyModule(s,clock).register();
        s.events.setStarPass(true,1,true);
    }
    @AfterEach void close() { if (s != null) s.close(); }
    Result result(String command, Object... fields) {
        Map<String,Object> p = obj(fields); p.put("device_uuid","device"); p.put("uuid","wrong");
        return s.registry.handle(command,obj("data",p),obj());
    }
    Map<String,Object> call(String command, Object... fields) { return map(result(command,fields).data()); }
    Map<String,Object> user() { return s.state.getUser("canonical"); }
    long cp() { return lng(map(user().get("userdata")).get("u_cp")); }

    @Test void registersEverySourceCommand() {
        assertEquals(18,s.registry.commands().size());
    }

    @Test void freeShopUsesCurrentAdLevelAndNeverHitsCountWall() {
        assertEquals(10,lng(map(list(call("buyShop","idx",3).get("reward_data")).getFirst()).get("reward_value")));
        assertEquals(1,integer(result("buyShop","idx",3).error().get("code")));clock.advance(899);
        assertEquals(1,integer(result("buyShop","idx",3).error().get("code")));clock.advance(1);
        assertEquals(20,lng(map(list(call("buyShop","idx",3).get("reward_data")).getFirst()).get("reward_value")));
        for (int i=0;i<6;i++) {clock.advance(900);assertEquals(0,integer(result("buyShop","idx",3).error().get("code")));}
        Map<String,Object> shop = list(user().get("user_shop")).stream().map(emu.leman.ggserver.util.Json::map).filter(r -> integer(r.get("i_id"))==3).findFirst().orElseThrow();
        assertEquals(0,integer(shop.get("i_Count"))); assertEquals(8,lng(shop.get("i_TotalCount")));
        assertEquals(1150,cp());
    }

    @Test void dailyShopLimitAndBuffExtension() {
        call("buyShop","idx",10012);
        assertEquals(1,integer(result("buyShop","idx",10012).error().get("code")));
        Map<String,Object> u = user();
        map(list(u.get("user_shop")).getFirst()).put("i_PurchaseTime",Instant.now().minusSeconds(172800).getEpochSecond());
        long end = lng(map(list(u.get("user_buff")).getFirst()).get("i_EndTime"));
        s.state.saveUser(u);
        call("buyShop","idx",10012);
        assertEquals(end+60,lng(map(list(user().get("user_buff")).getFirst()).get("i_EndTime")));
    }

    @Test void starMerchandiseDiscountAliasesAndEntitlement() {
        call("buyShop","idx",2003);
        assertEquals(950,cp());
        assertEquals(1,integer(call("checkBuyShop","shop_id",3003).get("is_owner")));
        assertEquals(1,integer(result("buyShop","idx",1003).error().get("code")));
        assertTrue(list(user().get("user_ticketcollection")).stream().anyMatch(t -> integer(map(t).get("i_id"))==1003));
    }

    @Test void inventoryPurchaseIsIdempotentAndRejectsRealMoneyAndNegativePrices() {
        call("buyMusic","idx",50); call("buyMusic","idx",50);
        call("buyMusic","idx",51); call("buyMusic","idx",52); call("buyMusic","idx",999);
        assertEquals(1000,cp()); // Sort-order 12 is not a price; explicit CP price is zero.
        assertEquals(1,list(user().get("user_music")).stream().filter(m -> integer(map(m).get("i_id"))==50).count());
    }

    @Test void attendanceSeparatesLoginFromBoardClaimAndWrapsNextDay() {
        assertEquals("Y",call("setAttendance","type","add").get("status"));
        assertEquals(1000,cp());
        Map<String,Object> fresh = map(call("getEventRewardList").get("1"));
        assertEquals(0,integer(map(list(fresh.get("reward_list")).getFirst()).get("get_date")));
        assertFalse(call("getEventRewardList").containsKey("2"));
        assertEquals("Y",call("setEventReward","event_idx",1).get("status"));
        assertEquals("N",call("setEventReward","event_idx",1).get("status"));
        assertEquals(1100,cp());
        Map<String,Object> u = user(); map(map(u.get("attendance")).get("1")).put("day",2); map(map(u.get("attendance")).get("1")).put("ymd",20000101); s.state.saveUser(u);
        assertEquals(0,integer(map(list(map(call("getEventRewardList").get("1")).get("reward_list")).getFirst()).get("get_date")));
        call("setEventReward","event_idx",1); assertEquals(1200,cp());
    }

    @Test void selectedSetFallsBackToCompensationOnlyWhenAllOwned() {
        var game=map(read(root.resolve("gamedata/game_data.json")));game.put("39",List.of(obj("1",1,"2",10,"3",10010,"4",10130,"5",1)));list(game.get("3")).add(obj("1",42));write(root.resolve("gamedata/game_data.json"),game);
        s.events.setAttendanceEventEnabled(2,true);
        Map<String,Object> u = user(); u.put("costumes",new ArrayList<>(List.of(obj("i_id",42,"i_Level",1))));u.put("user_select_reward",new ArrayList<>(List.of(obj("i_GroupId",10,"i_RewardGroupId",10010,"i_AltRewardGroupId",10130)))); s.state.saveUser(u);
        Map<String,Object> response = call("setEventReward","event_idx",2);
        assertEquals(500,lng(map(list(response.get("reward_data")).getFirst()).get("reward_value")));
        assertEquals(1500,cp());
    }

    @Test void passPaidTrackRequiresEntitlementAndRetriesDoNotDuplicateGifts() {
        s.events.setStarPass(true,1,false);
        var u=user();u.put("user_event_point",new ArrayList<>(List.of(obj("s_EventType","Pass","i_DataID",1,"i_Point",10,"i_Version",java.time.Year.now().getValue()-2020))));s.state.saveUser(u);
        assertTrue(list(call("setPassReward","group",1,"step",1,"type",1).get("reward_data")).isEmpty());
        s.events.setStarPass(true,1,true);call("buyShop","idx",1001);s.events.setStarPass(true,1,false);
        call("setPassReward","group",1,"step",1,"type",1);
        assertTrue(list(call("setPassReward","group",1,"step",1,"type",1).get("reward_data")).isEmpty());
        Map<String,Object> gift = list(user().get("user_follower_giftitem")).stream()
                .map(emu.leman.ggserver.util.Json::map).filter(row -> integer(row.get("i_id")) == 3)
                .findFirst().orElseThrow();
        assertEquals(2,lng(gift.get("i_Value")));
        call("setPassReward","group",1,"step",1,"type",0);
        assertEquals(995,cp());
    }

    @Test void missionAndAchievementClaimsAreIdempotentIncludingConcurrentRetries() throws Exception {
        var u=user();u.put("user_daily_mission",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1,"d_Quantity",1))));u.put("achievements",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1,"d_Quantity",1))));s.state.saveUser(u);
        try (ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor()) {
            List<Callable<Object>> work = new ArrayList<>();
            for (int i=0;i<8;i++) work.add(() -> call("setGameReward","type","daily_mission","id",1,"level",1));
            for (Future<Object> future : executor.invokeAll(work)) future.get();
        }
        assertEquals(1007,cp());
        call("setGameReward","type","achievement","id",1,"level",1);
        assertEquals("N",call("setGameReward","type","achievement","id",1,"level",1).get("status"));
        assertEquals(1018,cp());
        assertEquals(20,lng(map(list(user().get("user_event_point")).getFirst()).get("i_Point")));
    }

    @Test void adsHaveSeparateLimitsAndProfileExpDoesNotChangeStageLevel() {
        Map<String,Object> response = call("setAdReward","i_id",1,"param1",1);
        assertEquals(100,lng(map(list(response.get("reward_data")).getFirst()).get("reward_value")));
        assertEquals(2,integer(map(response.get("user_follower_profile")).get("i_Level")));
        assertTrue(list(call("setAdReward","i_id",1,"param1",1).get("reward_data")).isEmpty());
        for (int i=0;i<5;i++) assertEquals(1,list(call("setAdReward","i_id",2).get("reward_data")).size());
        assertTrue(list(call("setAdReward","i_id",2).get("reward_data")).isEmpty());
        assertEquals(1,integer(map(list(user().get("user_follower")).getFirst()).get("i_Level")));
    }

    @Test void paidPointsDeduplicateExistingRowsAndChargeOnlyOncePerRequest() {
        Map<String,Object> u = user(); u.put("user_event_point",new ArrayList<>(List.of(
                obj("s_EventType","Pass","i_DataID",1,"i_Point",30),obj("s_EventType","Pass","i_DataID",1,"i_Point",40)))); s.state.saveUser(u);
        Map<String,Object> response = call("paidEventPoint","i_SubscribeID",1,"type",1);
        assertEquals(90,lng(response.get("i_Point"))); assertEquals(995,cp());
        assertEquals(1,list(user().get("user_event_point")).size());
    }

    @Test void capturedAttendanceBoardDecodesWithoutPython() {
        Path existing = Path.of("resources/gamedata/getEventRewardList.b64");
        Assumptions.assumeTrue(Files.isRegularFile(existing));
        EconomyData real = new EconomyData(Path.of("resources").toAbsolutePath());
        assertTrue(real.boards().containsKey("1"));
        assertEquals(7,list(map(real.boards().get("1")).get("reward_list")).size());
    }
}

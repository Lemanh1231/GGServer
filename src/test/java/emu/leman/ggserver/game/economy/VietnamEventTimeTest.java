package emu.leman.ggserver.game.economy;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.game.account.AccountModule;
import emu.leman.ggserver.game.content.EventManager;
import emu.leman.ggserver.game.content.ContentModule;
import emu.leman.ggserver.util.GameTime;
import emu.leman.ggserver.net.Result;
import java.nio.file.*;
import java.time.*;
import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

/** Real seven-day boards, synthetic SQLite, UTC test clock, explicit Vietnam resets. */
class VietnamEventTimeTest {
    @TempDir Path root;
    Services s;
    static class TestClock extends Clock {
        Instant time=Instant.parse("2026-11-15T16:59:59Z");
        public ZoneId getZone() {return ZoneOffset.UTC;}
        public Clock withZone(ZoneId zone) {return Clock.fixed(time,zone);}
        public Instant instant() {return time;}
    }
    final TestClock clock=new TestClock();
    @BeforeEach void setup() throws Exception {
        for(String file:List.of("gamedata/game_data.json","gamedata/getEventRewardList.b64","schema/schema.json")) {
            Path target=root.resolve(file);Files.createDirectories(target.getParent());Files.copy(Path.of("resources").resolve(file),target);
        }
        write(root.resolve("event_config.json"),EventManager.defaults());reopen();s.state.createUser("time-test","synthetic-device");
    }
    void reopen() {if(s!=null)s.close();s=new Services(root);new EconomyModule(s,clock).register();}
    @AfterEach void close() {if(s!=null)s.close();}
    Result call(String command,Object... args) {return s.registry.handle(command,obj("data",obj(args)),obj("uuid","time-test"));}
    Map<String,Object> user() {return s.state.getUser("time-test");}
    Map<String,Object> receipt(int event) {return map(map(user().get("attendance")).get(str(event)));}
    void claim(int event,String status) {
        var result=call("setEventReward","event_idx",event);assertEquals(0,integer(result.error().get("code")));assertEquals(status,map(result.data()).get("status"));
    }
    @ParameterizedTest @ValueSource(ints={1,3})
    void sevenDaysResetAtVietnamMidnightNotUtcOrTokyo(int event) {
        claim(event,"Y");claim(event,"N");assertEquals(20261115,integer(receipt(event).get("ymd")));
        // 00:00 UTC+9 is 22:00 VN: no new daily reward yet.
        clock.time=Instant.parse("2026-11-15T15:00:00Z");claim(event,"N");
        clock.time=Instant.parse("2026-11-15T17:00:00Z");claim(event,"Y");assertEquals(20261116,integer(receipt(event).get("ymd")));
        // UTC midnight remains the same Vietnam day.
        clock.time=Instant.parse("2026-11-16T00:00:00Z");claim(event,"N");
        for(int day=3;day<=7;day++) {
            clock.time=Instant.parse("2026-11-15T17:00:00Z").plusSeconds((day-2)*86400L);
            claim(event,"Y");claim(event,"N");assertEquals(day,integer(receipt(event).get("day")));
        }
        reopen();claim(event,"N"); // No policy change to existing seven-day wrap in this timezone fix.
    }
    @ParameterizedTest @ValueSource(ints={1,3})
    void futureReceiptCannotBeReclaimedOrRewrittenAfterClockRollback(int event) {
        clock.time=Instant.parse("2026-11-16T17:00:00Z");claim(event,"Y");
        String before=stringify(user());clock.time=Instant.parse("2026-11-15T16:59:59Z");
        claim(event,"N");assertEquals(before,stringify(user()));reopen();claim(event,"N");
        if(event==1) {
            assertEquals("N",map(call("setAttendance","type","add").data()).get("status"));assertEquals(before,stringify(user()));
        }
        clock.time=Instant.parse("2026-11-17T17:00:00Z");claim(event,"Y");assertEquals(2,integer(receipt(event).get("day")));
    }
    @Test void legacyFutureAttendanceDateBlocksAddAndClaimWithoutErasingIt() {
        var u=user();map(u.get("userdata")).put("attendance_date",20261130);s.state.saveUser(u);String before=stringify(user());
        claim(1,"N");assertEquals("N",map(call("setAttendance","type","add").data()).get("status"));
        assertEquals(before,stringify(user()));
    }
    @Test void dailyShopUsesVietnamDateEvenWithUtcClock() {
        var u=user();map(u.get("userdata")).put("u_cp",100000);s.state.saveUser(u);
        assertEquals(0,integer(call("buyShop","idx",10012).error().get("code")));
        assertNotEquals(0,integer(call("buyShop","idx",10012).error().get("code")));
        clock.time=Instant.parse("2026-11-15T17:00:00Z");
        assertEquals(0,integer(call("buyShop","idx",10012).error().get("code")));
        clock.time=Instant.parse("2026-11-16T00:00:00Z");
        assertNotEquals(0,integer(call("buyShop","idx",10012).error().get("code")));
    }
    @Test void loginAttendanceResetsAtVietnamMidnight() {
        assertEquals("Y",map(call("setAttendance","type","add").data()).get("status"));
        assertEquals(20261115,integer(map(user().get("userdata")).get("attendance_date")));
        clock.time=Instant.parse("2026-11-15T17:00:00Z");
        assertEquals("Y",map(call("setAttendance","type","add").data()).get("status"));
        assertEquals(20261116,integer(map(user().get("userdata")).get("attendance_date")));
        clock.time=Instant.parse("2026-11-16T00:00:00Z");
        assertEquals("Y",map(call("setAttendance","type","check").data()).get("status"));
        assertEquals(20261116,integer(map(user().get("userdata")).get("attendance_date")));
    }
    @Test void eventMetadataAndPassMonthUseVietnamCalendar() {
        s.events.setEventRankingEnabled(true);assertEquals(7,integer(s.events.getEventModeData().get("utc")));
        s.events.setStarPass(true,3,false);
        var pass=list(new ContentModule(s).filteredGameData().get("SubscribeList")).stream().map(emu.leman.ggserver.util.Json::map)
                .filter(r->integer(r.get("i_id"))==3).findFirst().orElseThrow();
        assertEquals(GameTime.today().getMonthValue(),integer(pass.get("i_RepeatMonth")));
    }
}

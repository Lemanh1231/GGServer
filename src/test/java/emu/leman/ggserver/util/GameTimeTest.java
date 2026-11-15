package emu.leman.ggserver.util;

import emu.leman.ggserver.game.account.AccountModule;
import emu.leman.ggserver.game.account.AuthContent;
import emu.leman.ggserver.server.Dispatch;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class GameTimeTest {
    @ParameterizedTest @ValueSource(strings={"UTC","Asia/Tokyo","America/Los_Angeles"})
    void vietnamCalendarDoesNotDependOnJvmZone(String hostZone) {
        var original=TimeZone.getDefault();
        try {
            TimeZone.setDefault(TimeZone.getTimeZone(hostZone));
            var before=Clock.fixed(Instant.parse("2026-12-31T16:59:59Z"),ZoneId.of(hostZone));
            var after=Clock.fixed(Instant.parse("2026-12-31T17:00:00Z"),ZoneId.of(hostZone));
            assertEquals(20261231,GameTime.day(before));assertEquals(20270101,GameTime.day(after));
            assertEquals(20261231235959L,lng(GameTime.serverTime(before.instant()).get("datetime")));
            assertEquals(20270101000000L,lng(GameTime.serverTime(after.instant()).get("datetime")));
            assertEquals(after.instant().getEpochSecond(),lng(GameTime.serverTime(after.instant()).get("time")));
            assertEquals(LocalDateTime.of(2027,1,1,0,0),GameTime.localNow(after));
            assertEquals(GameTime.today(),LocalDate.parse(str(AuthContent.today()),DateTimeFormatter.BASIC_ISO_DATE));
            for(var response:List.of(AccountModule.serverTime(),Dispatch.nowTimes())) {
                long epoch=lng(response.get("time"));
                long expected=Long.parseLong(DateTimeFormatter.ofPattern("yyyyMMddHHmmss").withZone(GameTime.ZONE).format(Instant.ofEpochSecond(epoch)));
                assertEquals(expected,lng(response.get("datetime")));
            }
        } finally {TimeZone.setDefault(original);}
    }
}

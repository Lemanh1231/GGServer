package emu.leman.ggserver.util;

import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.Map;
import static emu.leman.ggserver.util.Json.obj;

/** Gameplay calendar is always Vietnam time, independent of the host/JVM zone.
 * Epoch seconds and duration-based cooldowns remain timezone-independent. */
public final class GameTime {
    public static final ZoneId ZONE=ZoneId.of("Asia/Ho_Chi_Minh");
    private static final DateTimeFormatter WIRE=DateTimeFormatter.ofPattern("yyyyMMddHHmmss").withZone(ZONE);
    private GameTime() {}
    public static LocalDate today() { return LocalDate.now(ZONE); }
    public static LocalDate today(Clock clock) { return date(clock.instant().getEpochSecond()); }
    public static LocalDate date(long seconds) { return Instant.ofEpochSecond(seconds).atZone(ZONE).toLocalDate(); }
    public static int day(Clock clock) { return Integer.parseInt(today(clock).format(DateTimeFormatter.BASIC_ISO_DATE)); }
    public static LocalDateTime localNow() { return LocalDateTime.now(ZONE); }
    public static LocalDateTime localNow(Clock clock) { return LocalDateTime.ofInstant(clock.instant(),ZONE); }
    public static String timestamp() { return localNow().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")); }
    public static Map<String,Object> serverTime() { return serverTime(Instant.now()); }
    public static Map<String,Object> serverTime(Instant instant) {
        return obj("time",instant.getEpochSecond(),"datetime",Long.parseLong(WIRE.format(instant)));
    }
}

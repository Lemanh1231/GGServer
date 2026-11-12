package emu.leman.ggserver.game.content;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.concurrent.atomic.AtomicInteger;
import static org.junit.jupiter.api.Assertions.*;
import static emu.leman.ggserver.util.Json.*;

class EventManagerTest {
    @TempDir Path root;
    @Test void defaultsLegacyNormalizationAndHotReload() {
        EventManager events=new EventManager(root);
        assertTrue(events.isAttendanceEventEnabled(1));assertFalse(events.isAttendanceEventEnabled(2));assertFalse(events.isAttendanceEventEnabled(999));assertEquals(13,events.activeStarPassSeason());
        write(root.resolve("event_config.json"),obj("events",obj("1",obj("enabled",false),"2",obj("enabled",true)),"paid_star_card",obj("enabled",true),"star_pass",obj("active_season",99),"weather_festival",obj("snow_enabled",true,"cherry_blossom_enabled",true)));
        assertFalse(events.isAttendanceEventEnabled(1));assertTrue(events.isAttendanceEventEnabled(2));assertEquals(13,events.activeStarPassSeason());
        assertTrue(events.isWeatherSnowEnabled());assertFalse(events.isWeatherCherryBlossomEnabled());
        events.save(obj("paid_star_card",obj("enabled",true)));
        assertTrue(events.isPaidStarCardEnabled());
        assertEquals("active",map(map(events.snapshot().get("events")).get("1")).get("state"));
    }
    @Test void mutationsAreAtomicNormalizedAndNotificationIsOptional() {
        EventManager events=new EventManager(root);AtomicInteger notices=new AtomicInteger();events.notificationSink(cfg->notices.incrementAndGet());
        events.setStarPass(false,3,true);assertFalse(events.isStarPassEnabled());assertEquals(3,events.activeStarPassSeason());assertTrue(events.isPaidStarCardEnabled());
        events.setWeatherFestival(false,true);assertFalse(events.isWeatherSnowEnabled());assertTrue(events.isWeatherCherryBlossomEnabled());
        events.setWeatherFestival(null,false);assertFalse(events.isWeatherCherryBlossomEnabled());
        events.setMeowfestEnabled(false);assertFalse(events.isMeowfestEnabled());
        events.save(events.snapshot(),true);assertEquals(1,notices.get());
        assertTrue(Files.exists(root.resolve("event_config.json")));
    }
    @Test void corruptConfigurationFallsBackToDefaults() throws Exception {
        Files.writeString(root.resolve("event_config.json"),"{broken");EventManager events=new EventManager(root);assertTrue(events.isMeowfestEnabled());assertEquals(2,events.activeEvents().size());
    }
}

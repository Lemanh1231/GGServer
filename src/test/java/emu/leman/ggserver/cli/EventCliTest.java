package emu.leman.ggserver.cli;

import emu.leman.ggserver.game.content.EventManager;
import emu.leman.ggserver.util.Json;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.io.*;
import java.nio.file.*;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class EventCliTest {
    @TempDir Path root;
    private int run(String... args) {
        return EventCli.run(args, Map.of("GG_ROOT", root.toString(), "GG_NO_ADB", "1"),
            new PrintStream(new ByteArrayOutputStream()), new PrintStream(new ByteArrayOutputStream()));
    }
    private Map<String,Object> cfg() { return map(Json.read(root.resolve("event_config.json"))); }

    @Test void allAndWeatherAndLegacyMirrors() {
        assertEquals(0, run("enable", "all"));
        assertTrue(truth(map(cfg().get("star_pass")).get("paid_card_enabled")));
        assertTrue(truth(map(cfg().get("paid_star_card")).get("enabled")));
        assertEquals("snow", map(cfg().get("weather_festival")).get("mode"));
        assertEquals(0, run("on", "hoaanhdao"));
        assertFalse(truth(map(cfg().get("weather_festival")).get("snow_enabled")));
        assertEquals("cherry", map(cfg().get("weather_festival")).get("mode"));
        assertEquals(0, run("off", "tuyet"));
        assertEquals("cherry", map(cfg().get("weather_festival")).get("mode"));
        assertEquals(0, run("disable", "all"));
        assertEquals("none", map(cfg().get("weather_festival")).get("mode"));
        for (Object item : map(cfg().get("attendance_events")).values()) assertFalse(truth(map(item).get("enabled")));
        assertEquals("ended", map(map(cfg().get("events")).get("1")).get("state"));
    }

    @Test void aliasesAndSeasons() {
        for (String target : List.of("1", "2", "3", "202110", "202111", "pass", "starpass", "star_pass", "gold", "paid_gold", "starpass_gold",
            "sale", "goodssale", "pass_sale", "meow", "meowfest", "cat", "samseck", "ch3", "tour", "chapter3", "snow", "tuyet",
            "cherry", "cherryblossom", "hoaanhdao", "fanart", "costume", "rank", "ranking", "duatop")) {
            assertEquals(0, run("start", target), target);
            assertEquals(0, run("stop", target), target);
        }
        for (int season = 1; season <= 13; season++) {
            assertEquals(0, run("setseason", String.valueOf(season)));
            assertEquals(season, integer(map(cfg().get("star_pass")).get("active_season")));
        }
        assertEquals(0, run("gold", "bật"));
        assertTrue(truth(map(cfg().get("paid_star_card")).get("enabled")));
        assertEquals(0, run("gold", "tắt"));
        assertFalse(truth(map(cfg().get("paid_star_card")).get("enabled")));
    }

    @Test void invalidInputAndMalformedJsonAreNotOverwritten() throws Exception {
        assertEquals(1, run("season", "14"));
        assertEquals(1, run("enable", "missing"));
        assertEquals(1, run("gold", "perhaps"));
        assertFalse(Files.exists(root.resolve("event_config.json")));
        Path path = root.resolve("event_config.json");
        Files.writeString(path, "{broken");
        assertEquals(1, run("enable", "all"));
        assertEquals("{broken", Files.readString(path));
    }

    @Test void preservesUnknownFieldsAndListIsReadOnly() throws Exception {
        Map<String,Object> cfg = EventManager.defaults();
        cfg.put("extension", obj("custom", "retained"));
        map(cfg.get("star_pass")).put("custom", 123);
        Json.write(root.resolve("event_config.json"), cfg);
        byte[] before = Files.readAllBytes(root.resolve("event_config.json"));
        assertEquals(0, run("ls"));
        assertArrayEquals(before, Files.readAllBytes(root.resolve("event_config.json")));
        assertEquals(0, run("season", "4"));
        assertEquals("retained", map(cfg().get("extension")).get("custom"));
        assertEquals(123, map(cfg().get("star_pass")).get("custom"));
    }

    @Test void refusesPythonRoot() throws Exception {
        Files.createDirectories(root.resolve("server"));
        Files.writeString(root.resolve("server/state.py"), "# original emulator");
        assertEquals(1, run("enable", "all"));
        assertFalse(Files.exists(root.resolve("event_config.json")));
    }
}

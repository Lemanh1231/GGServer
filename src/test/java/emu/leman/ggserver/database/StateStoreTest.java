package emu.leman.ggserver.database;

import emu.leman.ggserver.game.economy.Currency;

import emu.leman.ggserver.util.Json;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.sql.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import static org.junit.jupiter.api.Assertions.*;

class StateStoreTest {
    @TempDir Path root;
    private static final String UUID = "0123456789abcdef0123456789abcdef";
    private static final String DEVICE = "fedcba9876543210fedcba9876543210";
    private Connection connection() throws SQLException { return DriverManager.getConnection("jdbc:sqlite:" + root.resolve("data/database.db")); }
    private static Map<String,Object> ud(Map<String,Object> user) { return Json.map(user.get("userdata")); }

    @Test void defaultsStableDeviceAliasesBansAttendanceAndIp() throws Exception {
        try (StateStore store = new StateStore(root)) {
            Map<String,Object> user = store.createUser(UUID, DEVICE, "203.0.113.1");
            assertEquals(100001, Json.lng(ud(user).get("u_seq")));
            assertEquals(0, Json.lng(ud(user).get("u_cp")));
            assertEquals(70, Json.lng(Json.map(user.get("user_ap")).get("i_Ap")));
            assertEquals(2, Json.list(user.get("costumes")).size());
            assertEquals(141, Json.lng(Json.map(Json.list(user.get("user_follower_giftitem")).getFirst()).get("i_Value")));
            assertEquals(UUID, store.createUser("fresh-install", DEVICE).get("uuid"));
            for (String alias : List.of(UUID, DEVICE, "100001", "guest_100001")) {
                assertEquals(UUID, store.getUser(alias).get("uuid"));
                assertTrue(store.banUser(alias, true));
                assertTrue(store.isUserBanned(alias));
                assertTrue(store.banUser(alias, false));
            }
            store.updateAttendance("guest_100001", 7, 20261111);
            store.updateUserIp(DEVICE, "127.0.0.1", "LOCALHOST");
            store.updateUserIp("guest_100001", "", " Game.Example ");
            assertEquals("203.0.113.1", store.getUser(UUID).get("ip"));
            assertEquals(7, Json.integer(ud(store.getUser(UUID)).get("attendance_count")));
            try (Connection conn = connection(); Statement s = conn.createStatement(); ResultSet rs = s.executeQuery("SELECT last_domain FROM user_data")) {
                assertTrue(rs.next()); assertEquals("game.example", rs.getString(1));
            }
            assertTrue(store.banUser(null, true, 100001L));
            assertTrue(store.isUserBanned(DEVICE));
        }
    }

    @Test void savesSnapshotWithoutMutatingInventoryOrResponseAndPersistsExtras() throws Exception {
        try (StateStore store = new StateStore(root)) {
            Map<String,Object> user = store.createUser(UUID, DEVICE);
            Map<String,Object> item = Json.obj("i_id", 201, "i_Level", 9, "i_ActiveTime", 88,
                    "i_BonusLevel", 2, "b_EncoreBonusAppear", 1, "custom", Json.obj("nested", 3));
            user.put("user_music", new ArrayList<>(List.of(item)));
            ud(user).put("u_cp", 123);
            ud(user).put("u_candy", 12.25);
            String before = Json.stringify(user);
            store.saveUser(user);
            assertEquals(before, Json.stringify(user));
            assertEquals(9, Json.integer(item.get("i_Level")));
            Map<String,Object> loaded = store.getUser(UUID);
            assertEquals(1, Json.list(loaded.get("user_music")).size());
            Map<String,Object> reloaded = Json.map(Json.list(loaded.get("user_music")).getFirst());
            assertEquals(88, Json.integer(reloaded.get("i_ActiveTime")));
            assertEquals(3, Json.integer(Json.map(reloaded.get("custom")).get("nested")));
            assertEquals(123, Json.lng(ud(loaded).get("u_cp")));
            try (Connection conn = connection(); Statement s = conn.createStatement(); ResultSet rs = s.executeQuery("SELECT user_contents_json FROM user_data")) {
                assertTrue(rs.next());
                Map<String,Object> stored = Json.map(Json.parse(rs.getString(1)));
                assertFalse(stored.containsKey("user_music"));
                assertFalse(ud(stored).containsKey("u_cp"));
            }
            loaded.put("user_music", new ArrayList<>());
            store.saveUser(loaded);
            assertTrue(Json.list(store.getUser(UUID).get("user_music")).isEmpty());
        }
    }

    @Test void exactLikesSurviveSetReadIncrementAndReopen() {
        String exact = "123456789012345678901234567890123456789";
        try (StateStore store = new StateStore(root)) {
            store.createUser(UUID, DEVICE);
            store.setLikeCurrency(DEVICE, exact);
            assertAreaGp(store.getUser(UUID), exact);
            store.incrementCurrency("guest_100001", 5, 1.25, "1", 2);
            assertAreaGp(store.getUser(UUID), "123456789012345678901234567890123456790");
            assertEquals(5, Json.lng(ud(store.getUser(UUID)).get("u_cp")));
            store.setLikeCurrency(UUID, 0);
            assertAreaGp(store.getUser(UUID), "0");
            store.setLikeCurrency(UUID, "1e999");
            assertAreaGp(store.getUser(UUID), Currency.MAX_DECIMAL.toBigInteger().toString());
        }
        try (StateStore store = new StateStore(root)) {
            assertAreaGp(store.getUser(UUID), Currency.MAX_DECIMAL.toBigInteger().toString());
        }
    }
    private static void assertAreaGp(Map<String,Object> user, String expected) {
        assertEquals(expected, Json.map(Json.map(user.get("areas")).get("1")).get("s_Gp1"));
        assertTrue(Double.isFinite(Json.dbl(ud(user).get("u_like"))));
    }

    @Test void booleanForcedLikeUsesSqlBalanceAndRemainsAFlagAfterIncrement() {
        try (StateStore store = new StateStore(root)) {
            Map<String,Object> user = store.createUser(UUID, DEVICE);
            user.put("force_server_like", true);
            ud(user).put("u_like", 10.0);
            for (Object area : Json.map(user.get("areas")).values()) Json.map(area).put("s_Gp1", "9999");
            store.saveUser(user);
            assertAreaGp(store.getUser(UUID), "10");
            assertEquals(true, store.getUser(UUID).get("force_server_like"));
            store.incrementCurrency(UUID, 0, 0, "5", 0);
            assertAreaGp(store.getUser(UUID), "15");
            assertEquals(true, store.getUser(UUID).get("force_server_like"));
            // A numeric or non-GP legacy marker is also a flag, not an exact balance.
            for (Object flag : List.of(1, "true")) {
                user = store.getUser(UUID);
                user.put("force_server_like", flag);
                store.saveUser(user);
                assertAreaGp(store.getUser(UUID), "15");
            }
        }
        try (StateStore store = new StateStore(root)) {
            assertAreaGp(store.getUser(UUID), "15");
        }
    }

    @Test void atomicSpendingAcrossConnectionsNeverOverdraws() throws Exception {
        try (StateStore first = new StateStore(root); StateStore second = new StateStore(root)) {
            first.createUser(UUID, DEVICE);
            first.setCurrency(UUID, 100, 10.5);
            AtomicInteger successes = new AtomicInteger();
            try (ExecutorService executor = Executors.newFixedThreadPool(12)) {
                List<Future<?>> jobs = new ArrayList<>();
                for (int i = 0; i < 250; i++) {
                    StateStore store = i % 2 == 0 ? first : second;
                    jobs.add(executor.submit(() -> { if (store.spendCurrency(DEVICE, "cp", 1)) successes.incrementAndGet(); }));
                }
                for (Future<?> job : jobs) job.get();
            }
            assertEquals(100, successes.get());
            assertEquals(0, Json.lng(ud(first.getUser(UUID)).get("u_cp")));
            assertTrue(second.spendCurrency("guest_100001", "candy", 10.25));
            assertFalse(second.spendCurrency(UUID, "candy", 1));
            assertFalse(second.spendCurrency(UUID, "candy", -1));
            assertFalse(second.spendCurrency(UUID, "candy", Double.NaN));
            assertFalse(second.spendCurrency(UUID, "cp", Double.POSITIVE_INFINITY));
            assertEquals(0.25, Json.dbl(ud(first.getUser(UUID)).get("u_candy")));
            first.setCurrency(UUID, 9007199254740994L, 0);
            assertTrue(second.spendCurrency(UUID, "cp", 9007199254740993L));
            assertEquals(1L, Json.lng(ud(first.getUser(UUID)).get("u_cp")));
        }
    }

    @Test void migratesPythonSchemaAndLegacyJsonInventory() throws Exception {
        Files.createDirectories(root.resolve("data"));
        try (Connection conn = connection(); Statement s = conn.createStatement()) {
            s.execute("CREATE TABLE user_data (uuid TEXT PRIMARY KEY,device_uuid TEXT,u_id TEXT,u_seq INTEGER,u_cp INTEGER DEFAULT 0,u_candy REAL DEFAULT 0,u_like REAL DEFAULT 0,u_fans INTEGER DEFAULT 0,attendance_count INTEGER DEFAULT 0,user_contents_json TEXT)");
            try (PreparedStatement p = conn.prepareStatement("INSERT INTO user_data(uuid,device_uuid,u_id,u_seq,user_contents_json) VALUES(?,?,?,?,?)")) {
                p.setString(1, "42"); p.setString(2, DEVICE); p.setString(3, "guest_100008"); p.setLong(4, 100008);
                p.setString(5, Json.stringify(Json.obj("userdata", Json.obj("u_create_time", "20260101"),
                        "costumes", List.of(Json.obj("i_id", 201, "i_Level", 3)))));
                p.executeUpdate();
            }
        }
        Json.write(root.resolve("data/user_legacy.json"), Json.obj("uuid", UUID,
                "userdata", Json.obj("uuid", UUID, "device_uuid", "legacy-device", "u_seq", 100009,
                        "u_id", "guest_100009", "u_cp", 25, "u_candy", 1.5),
                "user_music", List.of(Json.obj("i_id", 1, "i_Level", 4))));
        try (StateStore store = new StateStore(root)) {
            assertEquals("42", store.getUser(DEVICE).get("uuid"));
            assertEquals(3, Json.integer(Json.map(Json.list(store.getUser(DEVICE).get("costumes")).getFirst()).get("i_Level")));
            store.incrementCurrency(DEVICE, 5, 0, 0, 0);
            assertEquals(5, Json.lng(ud(store.getUser("42")).get("u_cp")));
            assertEquals(25, Json.lng(ud(store.getUser(UUID)).get("u_cp")));
            assertEquals(4, Json.integer(Json.map(Json.list(store.getUser(UUID).get("user_music")).getFirst()).get("i_Level")));
            assertTrue(Files.exists(root.resolve("data/user_legacy.json.migrated")));
            assertFalse(Files.exists(root.resolve("data/user_legacy.json")));
        }
    }

    @Test void deletionCleanupAndApMatchPythonBehavior() throws Exception {
        try (StateStore store = new StateStore(root)) {
            Map<String,Object> user = store.createUser(UUID, DEVICE);
            store.createUser("test-user", "test-device");
            assertEquals(1, store.cleanupTestUsers());
            assertNotNull(store.getUser(UUID));
            user.put("user_ap", 5);
            assertEquals(75, Json.integer(StateStore.addAp(user, 5).get("i_Ap")));
            assertEquals(0, Json.integer(Json.map(user.get("user_ap")).get("i_FullApTime")));
            assertTrue(store.deleteUser(null, 100001L));
            assertNull(store.getUser(UUID));
            try (Connection conn = connection(); Statement s = conn.createStatement(); ResultSet rs = s.executeQuery("SELECT COUNT(*) FROM user_inventory")) {
                assertTrue(rs.next()); assertEquals(0, rs.getInt(1));
            }
        }
    }

    @Test void failedSaveRollsBackInventoryAndStageHelperReadsRootGameData() {
        try (StateStore store = new StateStore(root)) {
            Map<String,Object> user = store.createUser(UUID, DEVICE);
            user.put("costumes", List.of(Json.obj("i_id", 999, "unserializable", new Object())));
            assertThrows(IllegalArgumentException.class, () -> store.saveUser(user));
            assertEquals(2, Json.list(store.getUser(UUID).get("costumes")).size());
            assertEquals(41, store.allChThirdStages().size());
            Json.write(root.resolve("gamedata/game_data.json"), Json.obj("33", List.of(
                    Json.obj("1", 3001, "2", 3, "3", 1, "34", "Normal"),
                    Json.obj("1", 3002, "2", 3, "3", 2, "34", "Boss"))));
            assertEquals(2, store.allChThirdStages().size());
            assertEquals(3, Json.integer(store.allChThirdStages().getFirst().get("i_Star")));
            assertTrue(Json.list(user.get("user_ch_third_stage")).isEmpty());
        }
    }
}

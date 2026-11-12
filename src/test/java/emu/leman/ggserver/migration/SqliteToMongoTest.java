package emu.leman.ggserver.migration;

import emu.leman.ggserver.config.ServerConfig;
import emu.leman.ggserver.database.StateStore;
import emu.leman.ggserver.util.Json;
import de.bwaldvogel.mongo.MongoServer;
import de.bwaldvogel.mongo.backend.memory.MemoryBackend;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.net.InetSocketAddress;
import java.sql.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;
import static org.junit.jupiter.api.Assertions.*;

class SqliteToMongoTest {
    @TempDir Path root;

    private static final class MemoryTarget implements SqliteToMongo.Target {
        final List<Map<String,Object>> existing = new ArrayList<>();
        final List<Map<String,Object>> imported = new ArrayList<>();
        int failAt = -1;
        boolean closed;
        public List<Map<String,Object>> rows() { return existing; }
        public void insert(Map<String,Object> user) {
            if (imported.size() == failAt) throw new IllegalStateException("Injected import failure");
            imported.add(Json.copy(user));
        }
        public void close() { closed = true; }
    }

    private Path source() throws Exception {
        Path source = root.resolve("original emulator/data/database.db");
        Files.createDirectories(source.getParent());
        try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + source); Statement s = db.createStatement()) {
            s.execute("""
                CREATE TABLE user_data (uuid TEXT PRIMARY KEY, device_uuid TEXT, u_id TEXT, u_seq INTEGER,
                  u_cp INTEGER, u_candy REAL, u_like REAL, u_fans INTEGER, attendance_count INTEGER,
                  attendance_date INTEGER, user_contents_json TEXT, is_banned INTEGER, ip TEXT, last_domain TEXT)
                """);
            s.execute("""
                CREATE TABLE user_inventory (uuid TEXT, item_type TEXT, item_id INTEGER, level INTEGER,
                  active_time INTEGER, bonus_level INTEGER, value INTEGER, extra_json TEXT,
                  PRIMARY KEY(uuid, item_type, item_id))
                """);
        }
        return source;
    }

    private static void account(Connection db, String uuid, String device, long sequence) throws Exception {
        Map<String,Object> snapshot = Json.obj("uuid", "stale-json-uuid", "created_at", 1600000123,
                "userdata", Json.obj("u_cp", 1, "u_seq", 1, "u_create_time", "20200913"),
                "user_unit", List.of(Json.obj("i_id", 777, "i_Level", 1)),
                "costumes", List.of(Json.obj("i_id", 1, "i_Level", 2, "starter_extra", true)),
                "user_follower_giftitem", List.of(Json.obj("i_id", 2, "i_Value", 141)),
                "custom", Json.obj("nested", List.of("retained")), "force_server_like", "123456789012345678901234567890");
        try (PreparedStatement s = db.prepareStatement("INSERT INTO user_data VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)")) {
            Object[] values = {uuid, device, "guest_" + sequence, sequence, 987654321, 123.25, 456.75, 321,
                    12, 20261111, Json.stringify(snapshot), 1, "203.0.113.8", "Game.Example"};
            for (int i = 0; i < values.length; i++) s.setObject(i + 1, values[i]);
            s.executeUpdate();
        }
    }

    private static void inventory(Connection db, String uuid, String extra) throws Exception {
        try (PreparedStatement s = db.prepareStatement("INSERT INTO user_inventory VALUES (?, 'unit', 201, 9, 88, 2, 0, ?)")) {
            s.setString(1, uuid); s.setString(2, extra); s.executeUpdate();
        }
    }

    private static Map<String,byte[]> bytes(Path source) throws Exception {
        Map<String,byte[]> result = new LinkedHashMap<>();
        for (String suffix : List.of("", "-wal", "-shm", "-journal")) {
            Path file = Path.of(source + suffix);
            if (Files.exists(file)) result.put(suffix, Files.readAllBytes(file));
        }
        return result;
    }

    private static void unchanged(Map<String,byte[]> before, Path source) throws Exception {
        Map<String,byte[]> after = bytes(source);
        assertEquals(before.keySet(), after.keySet(), "Must not create or remove original SQLite sidecars");
        for (String key : before.keySet()) assertArrayEquals(before.get(key), after.get(key), "Changed source " + key);
    }

    @Test void dryRunValidatesWithoutImportingOrChangingSource() throws Exception {
        Path source = source();
        try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + source)) {
            account(db, "player-a", "device-a", 200007);
            inventory(db, "player-a", "{\"custom\":{\"nested\":3}}");
        }
        Map<String,byte[]> before = bytes(source);
        MemoryTarget target = new MemoryTarget();
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        Map<String,Object> report = SqliteToMongo.migrate(source, false, false, () -> target, new PrintStream(output));
        assertEquals("validated", report.get("status"));
        assertEquals(1, report.get("sourceAccounts"));
        assertEquals(1, report.get("inventoryRows"));
        assertEquals(1, report.get("eligible"));
        assertEquals(0, report.get("imported"));
        assertEquals(true, report.get("sourceUnchanged"));
        assertEquals(report.get("sourceSha256Before"), report.get("sourceSha256After"));
        assertTrue(Json.map(report.get("sourceSha256Before")).get("database.db").toString().matches("[a-f0-9]{64}"));
        assertTrue(target.imported.isEmpty());
        assertTrue(target.closed);
        assertEquals("validated", Json.map(Json.parse(output.toString(StandardCharsets.UTF_8))).get("status"));
        unchanged(before, source);
    }

    @Test void reconstructsAuthoritativeSqlMetadataAndSeparatedInventoriesWithoutLosingJsonOnlyStarters() throws Exception {
        Path source = source();
        try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + source)) {
            account(db, "player-a", "device-a", 200007);
            inventory(db, "player-a", "{\"custom\":{\"nested\":3},\"b_EncoreBonusAppear\":1}");
        }
        MemoryTarget target = new MemoryTarget();
        Map<String,Object> report = SqliteToMongo.migrate(source, true, false, () -> target, System.out);
        assertEquals("complete", report.get("status"));
        Map<String,Object> user = target.imported.getFirst(), ud = Json.map(user.get("userdata"));
        assertEquals("player-a", user.get("uuid"));
        assertEquals("player-a", ud.get("uuid"));
        assertEquals("device-a", ud.get("device_uuid"));
        assertEquals("guest_200007", ud.get("u_id"));
        assertEquals(200007, Json.lng(ud.get("u_seq")));
        assertEquals(987654321, Json.lng(ud.get("u_cp")));
        assertEquals(123.25, Json.dbl(ud.get("u_candy")));
        assertEquals(456.75, Json.dbl(ud.get("u_like")));
        assertEquals(321, Json.lng(ud.get("u_fans")));
        assertEquals(12, Json.lng(ud.get("attendance_count")));
        assertEquals(20261111, Json.lng(ud.get("attendance_date")));
        assertEquals(true, user.get("is_banned"));
        assertEquals("203.0.113.8", user.get("ip"));
        assertEquals("Game.Example", user.get("last_domain"));
        assertEquals(1600000123, Json.lng(user.get("created_at")));
        assertEquals("123456789012345678901234567890", user.get("force_server_like"));
        assertEquals(List.of("retained"), Json.map(user.get("custom")).get("nested"));
        List<Object> units = Json.list(user.get("user_unit"));
        assertEquals(1, units.size());
        Map<String,Object> item = Json.map(units.getFirst());
        assertEquals(201, Json.lng(item.get("i_id")));
        assertEquals(9, Json.lng(item.get("i_Level")));
        assertEquals(88, Json.lng(item.get("i_ActiveTime")));
        assertEquals(2, Json.lng(item.get("i_BonusLevel")));
        assertEquals(3, Json.integer(Json.map(item.get("custom")).get("nested")));
        assertTrue(Json.truth(Json.map(Json.list(user.get("costumes")).getFirst()).get("starter_extra")));
        assertEquals(141, Json.lng(Json.map(Json.list(user.get("user_follower_giftitem")).getFirst()).get("i_Value")));
    }

    @Test void lateCollisionFailsBeforeAnyWritesAndSkipExistingIsExplicit() throws Exception {
        Path source = source();
        try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + source)) {
            account(db, "a-new", "device-a", 200001);
            account(db, "z-collision", "device-z", 200002);
        }
        MemoryTarget target = new MemoryTarget();
        target.existing.add(Json.obj("uuid", "different-uuid", "device_uuid", "device-z", "u_id", "other", "u_seq", 300003));
        assertThrows(IllegalStateException.class, () -> SqliteToMongo.migrate(source, true, false, () -> target, System.out));
        assertTrue(target.imported.isEmpty());
        Map<String,Object> report = SqliteToMongo.migrate(source, true, true, () -> target, System.out);
        assertEquals(1, report.get("skipped"));
        assertEquals(1, report.get("imported"));
        assertEquals("a-new", target.imported.getFirst().get("uuid"));
        assertEquals("different-uuid", target.existing.getFirst().get("uuid"));
    }

    @Test void detectsSequenceAndCrossFieldAliasCollisions() throws Exception {
        Path source = source();
        try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + source)) {
            account(db, "player-a", "device-a", 200001);
        }
        for (Map<String,Object> row : List.of(Json.obj("uuid", "x", "u_seq", 200001),
                Json.obj("uuid", "device-a"), Json.obj("uuid", "200001"), Json.obj("uuid", "guest_200001"))) {
            MemoryTarget target = new MemoryTarget(); target.existing.add(row);
            assertThrows(IllegalStateException.class, () -> SqliteToMongo.migrate(source, true, false, () -> target, System.out));
            assertTrue(target.imported.isEmpty());
        }
    }

    @Test void rejectsMalformedLateAccountBeforeOpeningTarget() throws Exception {
        Path source = source();
        try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + source); Statement s = db.createStatement()) {
            account(db, "a-valid", "device-a", 200001);
            account(db, "z-invalid", "device-z", 200002);
            s.executeUpdate("UPDATE user_data SET user_contents_json='[]' WHERE uuid='z-invalid'");
        }
        AtomicBoolean opened = new AtomicBoolean();
        assertThrows(IllegalArgumentException.class, () -> SqliteToMongo.migrate(source, true, false,
                () -> { opened.set(true); return new MemoryTarget(); }, System.out));
        assertFalse(opened.get());
    }

    @Test void rejectsSourceIdentityCollisionsBeforeOpeningTarget() throws Exception {
        Path source = source();
        try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + source)) {
            account(db, "player-a", "shared-device", 200001);
            account(db, "player-b", "shared-device", 200002);
        }
        AtomicBoolean opened = new AtomicBoolean();
        assertThrows(IllegalArgumentException.class, () -> SqliteToMongo.migrate(source, true, false,
                () -> { opened.set(true); return new MemoryTarget(); }, System.out));
        assertFalse(opened.get());
    }

    @Test void rejectsCorruptExtraJsonAndUnknownOrOrphanInventoryBeforeWrites() throws Exception {
        for (String mode : List.of("malformed", "unknown", "orphan")) {
            Path source = source();
            try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + source); Statement s = db.createStatement()) {
                account(db, "player-a", "device-a", 200001);
                inventory(db, mode.equals("orphan") ? "missing" : "player-a", mode.equals("malformed") ? "broken" : "{}");
                if (mode.equals("unknown")) s.executeUpdate("UPDATE user_inventory SET item_type='unsupported'");
            }
            MemoryTarget target = new MemoryTarget();
            assertThrows(IllegalArgumentException.class, () -> SqliteToMongo.migrate(source, true, false, () -> target, System.out));
            assertTrue(target.imported.isEmpty());
            // Each iteration only replaces this test's own fixture.
            Files.delete(source);
        }
    }

    @Test void reportsPartialImportAndDoesNotClaimSuccessAfterTargetFailure() throws Exception {
        Path source = source();
        try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + source)) {
            account(db, "player-a", "device-a", 200001);
            account(db, "player-b", "device-b", 200002);
        }
        MemoryTarget target = new MemoryTarget(); target.failAt = 1;
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        assertThrows(IllegalStateException.class, () -> SqliteToMongo.migrate(source, true, false, () -> target, new PrintStream(output)));
        Map<String,Object> report = Json.map(Json.parse(output.toString(StandardCharsets.UTF_8)));
        assertEquals("partial", report.get("status"));
        assertEquals(1, Json.integer(report.get("imported")));
        assertEquals(true, report.get("sourceUnchanged"));
        assertTrue(target.closed);
    }

    @Test void abortsIfSourceChangesDuringPreflight() throws Exception {
        Path source = source();
        try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + source)) {
            account(db, "player-a", "device-a", 200001);
        }
        MemoryTarget target = new MemoryTarget();
        ByteArrayOutputStream output = new ByteArrayOutputStream();
        assertThrows(IllegalStateException.class, () -> SqliteToMongo.migrate(source, true, false, () -> {
            try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + source); Statement s = db.createStatement()) {
                s.executeUpdate("UPDATE user_data SET u_cp=777");
            } catch (SQLException e) { throw new IllegalStateException(e); }
            return target;
        }, new PrintStream(output)));
        assertTrue(target.imported.isEmpty());
        Map<String,Object> report = Json.map(Json.parse(output.toString(StandardCharsets.UTF_8)));
        assertEquals("failed", report.get("status"));
        assertEquals(false, report.get("sourceUnchanged"));
    }

    @Test void readsCommittedWalWithoutTouchingOriginalDatabaseOrSidecars() throws Exception {
        Path source = source();
        try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + source); Statement s = db.createStatement()) {
            s.execute("PRAGMA journal_mode=WAL");
            s.execute("PRAGMA wal_autocheckpoint=0");
            account(db, "wal-player", "wal-device", 500009);
            assertTrue(Files.size(Path.of(source + "-wal")) > 0);
            Map<String,byte[]> before = bytes(source);
            MemoryTarget target = new MemoryTarget();
            SqliteToMongo.migrate(source, true, false, () -> target, System.out);
            assertEquals("wal-player", target.imported.getFirst().get("uuid"));
            unchanged(before, source);
        }
    }

    @Test void requiresExplicitMongoBackendAndRejectsUnsafeCliOptions() throws Exception {
        Path source = source();
        assertThrows(IllegalArgumentException.class, () -> SqliteToMongo.migrate(ServerConfig.defaults(root), source, true, false, System.out));
        assertThrows(IllegalArgumentException.class, () -> SqliteToMongo.main(new String[]{"--apply", "--dry-run"}));
        assertThrows(IllegalArgumentException.class, () -> SqliteToMongo.main(new String[]{"--replace"}));
        assertThrows(IllegalArgumentException.class, () -> SqliteToMongo.main(new String[]{"--source"}));
        assertThrows(IllegalArgumentException.class, () -> SqliteToMongo.main(new String[]{"--config", "--apply"}));
    }

    @Test void embeddedMongoRoundTripKeepsSourceAndConfiguredDataFolderAndAdvancesSequence() throws Exception {
        Path source = source();
        try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + source)) {
            account(db, "player-a", "device-a", 800007);
            inventory(db, "player-a", "{\"custom\":{\"nested\":3}}");
            account(db, "player-b", "device-b", 800008);
        }
        Map<String,byte[]> before = bytes(source);
        MongoServer server = new MongoServer(new MemoryBackend());
        try {
            InetSocketAddress address = server.bind();
            Path configFile = root.resolve("configuration/server-config.json");
            Json.write(configFile, Json.obj("root", "../java-root", "folders", Json.obj("data", "configured-data"),
                    "database", Json.obj("backend", "mongo", "name", "migration_accounts",
                            "uri", "mongodb://" + address.getHostString() + ":" + address.getPort() + "/?serverSelectionTimeoutMS=5000")));
            ServerConfig config = ServerConfig.load(configFile, Map.of(), Map.of());
            Map<String,Object> dry = SqliteToMongo.migrate(config, source, false, false, System.out);
            assertEquals("validated", dry.get("status"));
            try (StateStore target = new StateStore(config)) { assertTrue(target.listUserRows().isEmpty()); }
            assertEquals(2, SqliteToMongo.migrate(config, source, true, false, System.out).get("imported"));
            try (StateStore target = new StateStore(config)) {
                Map<String,Object> user = target.exportUser("device-a"), ud = Json.map(user.get("userdata"));
                assertEquals("player-a", user.get("uuid"));
                assertEquals("guest_800007", ud.get("u_id"));
                assertEquals(800007, Json.lng(ud.get("u_seq")));
                assertEquals(987654321, Json.lng(ud.get("u_cp")));
                assertEquals(123.25, Json.dbl(ud.get("u_candy")));
                assertEquals(456.75, Json.dbl(ud.get("u_like")));
                assertEquals(true, user.get("is_banned"));
                assertEquals("203.0.113.8", user.get("ip"));
                assertEquals("Game.Example", user.get("last_domain"));
                assertEquals(1600000123, Json.lng(user.get("created_at")));
                Map<String,Object> item = Json.map(Json.list(user.get("user_unit")).getFirst());
                assertEquals(201, Json.lng(item.get("i_id")));
                assertEquals(9, Json.lng(item.get("i_Level")));
                assertEquals(3, Json.lng(Json.map(item.get("custom")).get("nested")));
                assertTrue(Json.truth(Json.map(Json.list(user.get("costumes")).getFirst()).get("starter_extra")));
                assertEquals(141, Json.lng(Json.map(Json.list(user.get("user_follower_giftitem")).getFirst()).get("i_Value")));
                assertTrue(Json.lng(Json.map(target.createUser("next-player", "next-device").get("userdata")).get("u_seq")) > 800008);
            }
            assertThrows(IllegalStateException.class, () -> SqliteToMongo.migrate(config, source, true, false, System.out));
            Map<String,Object> skipped = SqliteToMongo.migrate(config, source, true, true, System.out);
            assertEquals(2, skipped.get("skipped"));
            assertEquals(0, skipped.get("imported"));
            assertFalse(Files.exists(config.database()), "Mongo migration must not initialize configured SQLite data");
            unchanged(before, source);
        } finally { server.shutdownNow(); }
    }

    @Test void embeddedMongoConcurrentCanonicalCollisionCannotOverwriteExistingAccount() throws Exception {
        Path source = source();
        try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + source)) {
            account(db, "player-a", "source-device", 800007);
        }
        MongoServer server = new MongoServer(new MemoryBackend());
        try {
            InetSocketAddress address = server.bind();
            ServerConfig config = ServerConfig.defaults(root, Json.obj("database", Json.obj("backend", "mongo",
                    "name", "migration_race", "uri", "mongodb://" + address.getHostString() + ":" + address.getPort())));
            try (StateStore target = new StateStore(config)) {
                SqliteToMongo.Target racingTarget = new SqliteToMongo.Target() {
                    public List<Map<String,Object>> rows() {
                        List<Map<String,Object>> snapshot = target.listUserRows();
                        // Simulate another writer after the destination's preflight snapshot.
                        target.createUser("player-a", "concurrent-device", "198.51.100.7");
                        target.setCurrency("player-a", 17, 18.25);
                        return snapshot;
                    }
                    public void insert(Map<String,Object> user) { target.importUser(user); }
                    public void close() { }
                };
                assertThrows(RuntimeException.class, () -> SqliteToMongo.migrate(source, true, false, () -> racingTarget, System.out));
                Map<String,Object> existing = target.exportUser("player-a");
                assertEquals("concurrent-device", Json.map(existing.get("userdata")).get("device_uuid"));
                assertEquals(17, Json.lng(Json.map(existing.get("userdata")).get("u_cp")));
                assertEquals("198.51.100.7", existing.get("ip"));
                assertEquals(1, target.listUserRows().size());
            }
        } finally { server.shutdownNow(); }
    }
}

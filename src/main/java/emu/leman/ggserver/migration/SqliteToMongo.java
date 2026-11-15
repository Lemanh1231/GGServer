package emu.leman.ggserver.migration;

import emu.leman.ggserver.config.ServerConfig;
import emu.leman.ggserver.database.StateStore;
import emu.leman.ggserver.util.Json;
import java.io.*;
import java.math.BigDecimal;
import java.nio.file.*;
import java.security.*;
import java.sql.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;

/** Explicit, insert-only migration. The original SQLite files are never opened by SQLite. */
public final class SqliteToMongo {
    private static final Map<String,String> INVENTORIES = new LinkedHashMap<>();
    private static final List<String> IDENTITIES = List.of("uuid", "device_uuid", "u_id", "u_seq");
    private static final List<String> CURRENCIES = List.of("u_cp", "u_candy", "u_like", "u_fans", "attendance_count", "attendance_date");
    static {
        INVENTORIES.put("unit", "user_unit"); INVENTORIES.put("skill", "user_skill");
        INVENTORIES.put("music", "user_music"); INVENTORIES.put("guitar", "user_guitar");
        INVENTORIES.put("costume", "costumes"); INVENTORIES.put("prop", "user_prop");
        INVENTORIES.put("follower", "user_follower"); INVENTORIES.put("gift", "user_follower_giftitem");
        INVENTORIES.put("shop", "user_shop");
    }
    private SqliteToMongo() {}

    public static void main(String[] args) throws Exception {
        Options options = Options.parse(args);
        if (options.help) {
            System.out.println("SqliteToMongo --config resources/server-config.json --source ../emulator/data/database.db "
                    + "[--dry-run | --apply] [--skip-existing]\n"
                    + "Defaults to dry-run. Config must explicitly select database.backend=mongo.\n"
                    + "Stop source and destination servers first. Never replaces or deletes accounts or SQLite files.");
            return;
        }
        ServerConfig config = ServerConfig.load(options.config, Map.of(), System.getenv());
        migrate(config, options.source, options.apply, options.skipExisting, System.out);
    }

    public static Map<String,Object> migrate(ServerConfig config, Path source, boolean apply,
                                              boolean skipExisting, PrintStream output) throws Exception {
        if (!Set.of("mongo", "mongodb").contains(config.databaseBackend))
            throw new IllegalArgumentException("Migration target must explicitly select database.backend=mongo");
        return migrate(source, apply, skipExisting, () -> new StoreTarget(new StateStore(config)), output);
    }

    /** Separate boundary also permits failure-injection tests without a live MongoDB server. */
    interface Target extends AutoCloseable {
        List<Map<String,Object>> rows();
        void insert(Map<String,Object> user);
        @Override void close();
    }
    @FunctionalInterface interface OpenTarget { Target open(); }
    private record StoreTarget(StateStore store) implements Target {
        public List<Map<String,Object>> rows() { return store.listUserRows(); }
        public void insert(Map<String,Object> user) { store.importUser(user); }
        public void close() { store.close(); }
    }

    static Map<String,Object> migrate(Path source, boolean apply, boolean skipExisting,
                                      OpenTarget opener, PrintStream output) throws Exception {
        source = source.toAbsolutePath().normalize().toRealPath();
        Map<String,Object> report = Json.obj("status", "failed", "mode", apply ? "apply" : "dry-run",
                "source", source.toString(), "sourceAccounts", 0, "inventoryRows", 0,
                "eligible", 0, "skipped", 0, "imported", 0, "sourceUnchanged", false);
        Map<String,String> before = null;
        Exception failure = null;
        try {
            before = fingerprint(source);
            report.put("sourceSha256Before", before);
            Snapshot snapshot = readSnapshot(source, before);
            report.put("sourceAccounts", snapshot.users.size());
            report.put("inventoryRows", snapshot.inventoryRows);
            validateIdentities(snapshot.users);
            try (Target target = opener.open()) {
                Set<String> occupied = identities(target.rows());
                List<Map<String,Object>> eligible = new ArrayList<>();
                List<String> collisions = new ArrayList<>();
                for (Map<String,Object> user : snapshot.users) {
                    if (identityKeys(user).stream().anyMatch(occupied::contains)) {
                        collisions.add(Json.str(user.get("uuid")));
                    } else eligible.add(user);
                }
                report.put("eligible", eligible.size());
                report.put("collisions", collisions);
                report.put("skipped", skipExisting ? collisions.size() : 0);
                if (!collisions.isEmpty() && !skipExisting)
                    throw new IllegalStateException("Existing account collisions; nothing imported. Use --skip-existing to skip: "
                            + String.join(", ", collisions));
                requireUnchanged(source, before);
                if (apply) {
                    for (Map<String,Object> user : eligible) {
                        target.insert(user); // Atomic insert-only import; never save/upsert an existing account.
                        report.put("imported", ((Number)report.get("imported")).intValue() + 1);
                    }
                }
                report.put("status", apply ? "complete" : "validated");
            }
        } catch (Exception e) {
            failure = e;
            report.put("status", ((Number)report.get("imported")).intValue() == 0 ? "failed" : "partial");
            report.put("error", e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage());
        } finally {
            if (before != null) {
                try {
                    Map<String,String> after = fingerprint(source);
                    report.put("sourceSha256After", after);
                    report.put("sourceUnchanged", before.equals(after));
                    if (!before.equals(after)) throw new IllegalStateException("Source changed during migration; stop all writers and retry");
                } catch (Exception e) {
                    report.put("status", ((Number)report.get("imported")).intValue() == 0 ? "failed" : "partial");
                    report.put("error", e.getMessage());
                    if (failure == null) failure = e; else failure.addSuppressed(e);
                }
            }
            output.println(Json.stringify(report));
        }
        if (failure != null) throw failure;
        return report;
    }

    private record Snapshot(List<Map<String,Object>> users, int inventoryRows) {}

    private static Snapshot readSnapshot(Path source, Map<String,String> before) throws Exception {
        Path directory = Files.createTempDirectory("gg-mongo-migration-");
        Path copy = directory.resolve("database.db");
        try {
            // WAL is part of the committed database. Do not use immutable=1, which ignores WAL.
            for (String suffix : List.of("", "-wal", "-journal")) {
                Path original = Path.of(source + suffix);
                if (Files.exists(original)) Files.copy(original, Path.of(copy + suffix));
            }
            requireUnchanged(source, before);
            try (Connection db = DriverManager.getConnection("jdbc:sqlite:" + copy.toUri() + "?mode=ro");
                 Statement statement = db.createStatement()) {
                statement.execute("PRAGMA query_only=ON");
                statement.execute("BEGIN");
                try (ResultSet check = statement.executeQuery("PRAGMA integrity_check")) {
                    if (!check.next() || !"ok".equalsIgnoreCase(check.getString(1)) || check.next())
                        throw new SQLException("Source SQLite integrity_check failed");
                }
                Map<String,Map<String,Object>> users = new LinkedHashMap<>();
                try (ResultSet rs = statement.executeQuery("SELECT * FROM user_data ORDER BY uuid")) {
                    Set<String> columns = columns(rs);
                    for (String required : List.of("uuid", "device_uuid", "u_id", "u_seq", "user_contents_json",
                            "u_cp", "u_candy", "u_like", "u_fans", "attendance_count"))
                        if (!columns.contains(required)) throw new SQLException("Source user_data missing column: " + required);
                    while (rs.next()) {
                        Map<String,Object> row = row(rs);
                        Map<String,Object> user = reconstruct(row);
                        String uuid = Json.str(user.get("uuid"));
                        if (users.putIfAbsent(uuid, user) != null) throw new IllegalArgumentException("Duplicate source UUID: " + uuid);
                    }
                }
                Map<String,Set<String>> separated = new HashMap<>();
                int count = 0;
                try (ResultSet rs = statement.executeQuery("SELECT * FROM user_inventory ORDER BY uuid, item_type, item_id")) {
                    Set<String> columns = columns(rs);
                    for (String required : List.of("uuid", "item_type", "item_id", "level", "active_time", "bonus_level", "value", "extra_json"))
                        if (!columns.contains(required)) throw new SQLException("Source user_inventory missing column: " + required);
                    while (rs.next()) {
                        Map<String,Object> row = row(rs);
                        String uuid = Json.str(row.get("uuid")), type = Json.str(row.get("item_type"));
                        Map<String,Object> user = users.get(uuid);
                        if (user == null) throw new IllegalArgumentException("Orphan inventory row for " + uuid);
                        String key = INVENTORIES.get(type);
                        if (key == null) throw new IllegalArgumentException("Unsupported inventory type: " + type);
                        if (separated.computeIfAbsent(uuid, ignored -> new HashSet<>()).add(key)) user.put(key, new ArrayList<>());
                        Map<String,Object> item = Json.obj("i_id", integer(row.get("item_id"), "item_id"));
                        if (!type.equals("gift")) item.put("i_Level", integer(row.get("level"), "level"));
                        long active = integer(row.get("active_time"), "active_time");
                        long bonus = integer(row.get("bonus_level"), "bonus_level");
                        if (active != 0) item.put("i_ActiveTime", active);
                        if (bonus != 0) item.put("i_BonusLevel", bonus);
                        if (type.equals("gift")) item.put("i_Value", integer(row.get("value"), "value"));
                        Object extra = row.get("extra_json");
                        if (extra != null && !extra.toString().isBlank()) item.putAll(object(Json.parse(extra.toString()), "extra_json"));
                        Json.list(user.get(key)).add(item);
                        count++;
                    }
                }
                for (Map<String,Object> user : users.values()) validateInventories(user);
                return new Snapshot(new ArrayList<>(users.values()), count);
            }
        } finally {
            // Only remove our own temporary snapshot, never any source path.
            for (String suffix : List.of("-shm", "-wal", "-journal", "")) Files.deleteIfExists(Path.of(copy + suffix));
            Files.deleteIfExists(directory);
        }
    }

    private static Map<String,Object> reconstruct(Map<String,Object> row) {
        Object raw = row.get("user_contents_json");
        if (!(raw instanceof String text) || text.isBlank()) throw new IllegalArgumentException("Missing user_contents_json for " + row.get("uuid"));
        Map<String,Object> user = object(Json.parse(text), "user_contents_json");
        Map<String,Object> ud;
        if (!user.containsKey("userdata")) { ud = new LinkedHashMap<>(); user.put("userdata", ud); }
        else ud = object(user.get("userdata"), "userdata");
        String uuid = Json.str(row.get("uuid"));
        if (uuid.isBlank()) throw new IllegalArgumentException("Empty source UUID");
        user.put("uuid", uuid);
        for (String key : IDENTITIES) ud.put(key, row.get(key));
        for (String key : List.of("device_uuid", "u_id"))
            if (!(ud.get(key) instanceof String value) || value.isBlank())
                throw new IllegalArgumentException("Missing source " + key + " for " + uuid + "; refusing to generate a replacement identity");
        long sequence = integer(ud.get("u_seq"), "u_seq");
        if (sequence <= 0 || sequence == Long.MAX_VALUE) throw new IllegalArgumentException("Invalid source u_seq for " + uuid);
        ud.put("u_seq", sequence);
        for (String key : CURRENCIES) {
            Object value = row.containsKey(key) ? row.get(key) : ud.get(key);
            if (value != null) finite(value, key);
            ud.put(key, value == null ? 0 : value);
        }
        for (String key : List.of("u_cp", "u_fans", "attendance_count", "attendance_date")) {
            long value = integer(ud.get(key), key);
            if ((key.equals("attendance_count") || key.equals("attendance_date")) && value != (int)value)
                throw new IllegalArgumentException("Source " + key + " exceeds supported integer range for " + uuid);
        }
        Object ip = row.containsKey("ip") ? row.get("ip") : Json.first(user.get("ip"), ud.get("ip"), "");
        user.put("ip", ip == null ? "" : ip); ud.put("ip", ip == null ? "" : ip);
        Object domain = row.containsKey("last_domain") ? row.get("last_domain") : user.getOrDefault("last_domain", "");
        user.put("last_domain", domain == null ? "" : domain);
        ud.put("last_domain", domain == null ? "" : domain);
        if (row.containsKey("is_banned")) user.put("is_banned", Json.truth(row.get("is_banned")));
        if (row.get("created_at") != null) user.put("created_at", row.get("created_at"));
        if (!user.containsKey("created_at")) {
            // No wall-clock fallback: repeated dry runs must describe the same source data.
            Object created = user.get("last_save_time");
            try {
                created = LocalDate.parse(Json.str(ud.get("u_create_time")), DateTimeFormatter.BASIC_ISO_DATE)
                        .atStartOfDay(emu.leman.ggserver.util.GameTime.ZONE).toEpochSecond();
            } catch (RuntimeException ignored) { }
            if (created != null) user.put("created_at", created);
        }
        return user;
    }

    private static void validateInventories(Map<String,Object> user) {
        for (String key : INVENTORIES.values()) {
            if (!user.containsKey(key)) user.put(key, new ArrayList<>());
            if (!(user.get(key) instanceof List<?> items)) throw new IllegalArgumentException(key + " must be an array");
            Set<Long> ids = new HashSet<>();
            for (Object entry : items) {
                Map<String,Object> item = object(entry, key + " item");
                long id = integer(item.get("i_id"), key + ".i_id");
                if (!ids.add(id)) throw new IllegalArgumentException("Duplicate item ID in " + key + ": " + id);
                for (String field : List.of("i_Level", "i_ActiveTime", "i_BonusLevel", "i_Value"))
                    if (item.containsKey(field)) integer(item.get(field), key + "." + field);
            }
        }
    }

    private static long integer(Object value, String field) {
        try { return new BigDecimal(String.valueOf(value)).longValueExact(); }
        catch (RuntimeException e) { throw new IllegalArgumentException("Invalid integer " + field + ": " + value, e); }
    }
    private static void finite(Object value, String field) {
        try {
            BigDecimal n = new BigDecimal(value.toString());
            if (!Double.isFinite(n.doubleValue())) throw new NumberFormatException();
        } catch (RuntimeException e) { throw new IllegalArgumentException("Invalid currency " + field + ": " + value, e); }
    }
    private static Map<String,Object> object(Object value, String field) {
        if (!(value instanceof Map<?,?>)) throw new IllegalArgumentException(field + " must be a JSON object");
        return Json.map(value);
    }
    private static Set<String> columns(ResultSet rs) throws SQLException {
        Set<String> columns = new HashSet<>();
        for (int i = 1; i <= rs.getMetaData().getColumnCount(); i++) columns.add(rs.getMetaData().getColumnLabel(i));
        return columns;
    }
    private static Map<String,Object> row(ResultSet rs) throws SQLException {
        Map<String,Object> row = new LinkedHashMap<>();
        for (int i = 1; i <= rs.getMetaData().getColumnCount(); i++) row.put(rs.getMetaData().getColumnLabel(i), rs.getObject(i));
        return row;
    }

    private static void validateIdentities(List<Map<String,Object>> users) {
        Set<String> seen = new HashSet<>();
        for (Map<String,Object> user : users) {
            Set<String> keys = identityKeys(user);
            if (keys.stream().anyMatch(seen::contains)) throw new IllegalArgumentException("Source account identity collision: " + user.get("uuid"));
            seen.addAll(keys);
        }
    }
    private static Set<String> identities(List<Map<String,Object>> rows) {
        Set<String> result = new HashSet<>();
        for (Map<String,Object> row : rows) result.addAll(identityKeys(row));
        return result;
    }
    private static Set<String> identityKeys(Map<String,Object> user) {
        Map<String,Object> fields = user.get("userdata") instanceof Map<?,?> ? Json.map(user.get("userdata")) : user;
        Set<String> keys = new HashSet<>();
        for (String key : IDENTITIES) {
            Object value = key.equals("uuid") && user.containsKey(key) ? user.get(key) : fields.get(key);
            if (value == null || value.toString().isBlank()) continue;
            // UUID, device UUID and display ID share the StateStore identifier lookup namespace.
            keys.add(key.equals("u_seq") ? "sequence:" + integer(value, "u_seq") : "identifier:" + value);
            if (!key.equals("u_seq")) {
                String text = value.toString();
                if (text.startsWith("guest_")) text = text.substring(6);
                if (text.matches("[0-9]+")) keys.add("sequence:" + integer(text, "identifier"));
            }
        }
        return keys;
    }

    private static Map<String,String> fingerprint(Path source) throws IOException, NoSuchAlgorithmException {
        if (!Files.isRegularFile(source)) throw new IOException("Missing source database: " + source);
        Map<String,String> hashes = new LinkedHashMap<>();
        for (String suffix : List.of("", "-wal", "-shm", "-journal")) {
            Path file = Path.of(source + suffix);
            if (!Files.exists(file)) continue;
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream input = Files.newInputStream(file)) {
                byte[] buffer = new byte[65536];
                int n;
                while ((n = input.read(buffer)) != -1) digest.update(buffer, 0, n);
            }
            hashes.put(file.getFileName().toString(), HexFormat.of().formatHex(digest.digest()));
        }
        return hashes;
    }
    private static void requireUnchanged(Path source, Map<String,String> before) throws Exception {
        if (!before.equals(fingerprint(source))) throw new IllegalStateException("Source changed during migration; stop all writers and retry");
    }

    private record Options(Path config, Path source, boolean apply, boolean skipExisting, boolean help) {
        static Options parse(String[] args) {
            Path config = emu.leman.ggserver.Main.defaultRoot().resolve("server-config.json"), source = Path.of("../emulator/data/database.db");
            boolean apply = false, dryRun = false, skip = false, help = false;
            for (int i = 0; i < args.length; i++) {
                switch (args[i]) {
                    case "--config", "--source" -> {
                        String option = args[i];
                        if (++i >= args.length || args[i].startsWith("--")) throw new IllegalArgumentException("Missing value for " + option);
                        if (option.equals("--config")) config = Path.of(args[i]); else source = Path.of(args[i]);
                    }
                    case "--apply" -> apply = true;
                    case "--dry-run" -> dryRun = true;
                    case "--skip-existing" -> skip = true;
                    case "--help", "-h" -> help = true;
                    default -> throw new IllegalArgumentException("Unknown option: " + args[i]);
                }
            }
            if (apply && dryRun) throw new IllegalArgumentException("Choose either --apply or --dry-run, not both");
            return new Options(config, source, apply, skip, help);
        }
    }
}

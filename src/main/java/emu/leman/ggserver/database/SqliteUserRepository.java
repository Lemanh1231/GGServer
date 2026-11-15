package emu.leman.ggserver.database;

import emu.leman.ggserver.game.economy.Currency;
import emu.leman.ggserver.util.Json;
import java.io.IOException;
import java.math.BigInteger;
import java.nio.file.*;
import java.sql.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.ReentrantLock;

/** Python-compatible SQLite user store. All compound operations are single, serialized transactions. */
public final class SqliteUserRepository implements UserRepository {
    private static final Map<Path,ReentrantLock> LOCKS = new ConcurrentHashMap<>();
    private static final Map<String,String> INVENTORIES = new LinkedHashMap<>();
    private static final Set<String> CURRENCIES = Set.of("u_cp", "u_candy", "u_like", "u_fans", "attendance_count", "attendance_date");
    private static final Set<String> ITEM_COLUMNS = Set.of("i_id", "i_Level", "i_ActiveTime", "i_BonusLevel", "i_Value");
    private static final Set<String> LOCAL_IPS = Set.of("127.0.0.1", "localhost", "::1");
    static {
        INVENTORIES.put("user_unit", "unit"); INVENTORIES.put("user_skill", "skill");
        INVENTORIES.put("user_music", "music"); INVENTORIES.put("user_guitar", "guitar");
        INVENTORIES.put("costumes", "costume"); INVENTORIES.put("user_prop", "prop");
        INVENTORIES.put("user_follower", "follower"); INVENTORIES.put("user_follower_giftitem", "gift");
        INVENTORIES.put("user_shop", "shop");
    }

    private final Connection db;
    private final ReentrantLock lock;
    private final Path root;
    private final emu.leman.ggserver.config.ServerConfig config;
    private boolean closed;

    public SqliteUserRepository(Path root) { this(emu.leman.ggserver.config.ServerConfig.defaults(root)); }
    public SqliteUserRepository(emu.leman.ggserver.config.ServerConfig config) {
        this.config=config;
        this.root = config.root;
        Path database = config.database();
        lock = LOCKS.computeIfAbsent(database, ignored -> new ReentrantLock(true));
        lock.lock();
        Connection opened = null;
        try {
            Files.createDirectories(database.getParent());
            opened = DriverManager.getConnection("jdbc:sqlite:" + database);
            db = opened;
            execute("PRAGMA busy_timeout=10000");
            execute("PRAGMA journal_mode=WAL");
            execute("PRAGMA synchronous=NORMAL");
            initialize(database.getParent());
        } catch (SQLException | IOException | RuntimeException e) {
            if (opened != null) try { opened.close(); } catch (SQLException suppressed) { e.addSuppressed(suppressed); }
            throw new IllegalStateException("Cannot open state database " + database, e);
        } finally {
            lock.unlock();
        }
    }

    @FunctionalInterface private interface Work<T> { T run() throws SQLException; }
    private <T> T transaction(Work<T> work) {
        lock.lock();
        try {
            if (closed) throw new IllegalStateException("StateStore is closed");
            execute("BEGIN IMMEDIATE");
            try {
                T result = work.run();
                execute("COMMIT");
                return result;
            } catch (SQLException | RuntimeException | Error e) {
                try { execute("ROLLBACK"); } catch (SQLException suppressed) { e.addSuppressed(suppressed); }
                throw e;
            }
        } catch (SQLException e) {
            throw new IllegalStateException("State database operation failed", e);
        } finally {
            lock.unlock();
        }
    }

    private void execute(String sql) throws SQLException {
        try (Statement statement = db.createStatement()) { statement.execute(sql); }
    }
    private int update(String sql, Object... parameters) throws SQLException {
        try (PreparedStatement statement = prepare(sql, parameters)) { return statement.executeUpdate(); }
    }
    private PreparedStatement prepare(String sql, Object... parameters) throws SQLException {
        PreparedStatement statement = db.prepareStatement(sql);
        for (int i = 0; i < parameters.length; i++) statement.setObject(i + 1, parameters[i]);
        return statement;
    }
    private Map<String,Object> row(String sql, Object... parameters) throws SQLException {
        try (PreparedStatement statement = prepare(sql, parameters); ResultSet rs = statement.executeQuery()) {
            if (!rs.next()) return null;
            return readRow(rs);
        }
    }
    private static Map<String,Object> readRow(ResultSet rs) throws SQLException {
        Map<String,Object> result = new LinkedHashMap<>();
        for (int i = 1; i <= rs.getMetaData().getColumnCount(); i++) result.put(rs.getMetaData().getColumnLabel(i), rs.getObject(i));
        return result;
    }

    private void initialize(Path dataDirectory) throws SQLException, IOException {
        transaction(() -> {
            execute("""
                CREATE TABLE IF NOT EXISTS user_data (
                    uuid TEXT PRIMARY KEY, device_uuid TEXT, u_id TEXT, u_seq INTEGER,
                    u_cp INTEGER DEFAULT 0, u_candy REAL DEFAULT 0.0, u_like REAL DEFAULT 0.0,
                    u_fans INTEGER DEFAULT 0, attendance_count INTEGER DEFAULT 0,
                    attendance_date INTEGER DEFAULT 0, user_contents_json TEXT,
                    is_banned INTEGER DEFAULT 0, ip TEXT DEFAULT '', last_domain TEXT DEFAULT '')
                """);
            execute("""
                CREATE TABLE IF NOT EXISTS user_inventory (
                    uuid TEXT, item_type TEXT, item_id INTEGER, level INTEGER DEFAULT 1,
                    active_time INTEGER DEFAULT 0, bonus_level INTEGER DEFAULT 0,
                    value INTEGER DEFAULT 0, extra_json TEXT,
                    PRIMARY KEY(uuid, item_type, item_id),
                    FOREIGN KEY(uuid) REFERENCES user_data(uuid) ON DELETE CASCADE)
                """);
            Set<String> columns = new HashSet<>();
            try (Statement statement = db.createStatement(); ResultSet rs = statement.executeQuery("PRAGMA table_info(user_data)")) {
                while (rs.next()) columns.add(rs.getString("name"));
            }
            for (String[] column : new String[][]{{"is_banned", "INTEGER DEFAULT 0"}, {"ip", "TEXT DEFAULT ''"},
                    {"last_domain", "TEXT DEFAULT ''"}, {"attendance_date", "INTEGER DEFAULT 0"}}) {
                if (!columns.contains(column[0])) execute("ALTER TABLE user_data ADD COLUMN " + column[0] + " " + column[1]);
            }
            return null;
        });
        try (DirectoryStream<Path> files = Files.newDirectoryStream(dataDirectory, "user_*.json")) {
            for (Path path : files) {
                try {
                    Map<String,Object> user = Json.map(Json.read(path));
                    Map<String,Object> ud = Json.map(user.get("userdata"));
                    String uuid = Json.str(Json.first(user.get("uuid"), ud.get("uuid")));
                    if (uuid.isEmpty()) continue;
                    transaction(() -> {
                        int inserted = update("""
                            INSERT OR IGNORE INTO user_data
                            (uuid,device_uuid,u_id,u_seq,u_cp,u_candy,u_like,u_fans,attendance_count,attendance_date,user_contents_json)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)
                            """, uuid, ud.get("device_uuid"), ud.get("u_id"), ud.get("u_seq"),
                            Json.lng(ud.getOrDefault("u_cp", 1000000)), Json.dbl(ud.getOrDefault("u_candy", 100000.0)),
                            Currency.parse(ud.get("u_like")).floating(), Json.lng(ud.get("u_fans")),
                            Json.integer(ud.get("attendance_count")), Json.integer(ud.get("attendance_date")), storedJson(user));
                        if (inserted != 0) writeInventories(uuid, user);
                        return null;
                    });
                    Files.move(path, path.resolveSibling(path.getFileName() + ".migrated"), StandardCopyOption.REPLACE_EXISTING);
                } catch (RuntimeException | IOException e) {
                    org.slf4j.LoggerFactory.getLogger(SqliteUserRepository.class).warn("Migration failed for {}", path.getFileName(), e);
                }
            }
        }
    }

    private String resolve(String identifier) throws SQLException {
        if (identifier == null || identifier.isEmpty()) return null;
        Map<String,Object> found = row("SELECT uuid FROM user_data WHERE uuid = ?", identifier);
        if (found == null) {
            String sequence = identifier.strip();
            if (sequence.startsWith("guest_")) sequence = sequence.substring(6);
            long seq = -1;
            try { if (sequence.matches("[0-9]+")) seq = Long.parseLong(sequence); } catch (NumberFormatException ignored) {}
            found = row("SELECT uuid FROM user_data WHERE device_uuid = ? OR u_id = ? OR u_seq = ?", identifier, identifier, seq);
        }
        return found == null ? null : Json.str(found.get("uuid"));
    }

    public Map<String,Object> getUser(String identifier) {
        if (identifier == null || identifier.isEmpty()) return null;
        return transaction(() -> getUserInternal(identifier));
    }
    @Override public String canonicalIdentity(String identifier) {
        if(identifier==null||identifier.isEmpty())return identifier;
        String canonical=transaction(()->resolve(identifier));
        return canonical==null?identifier:canonical;
    }
    @Override public List<Map<String,Object>> listUserRows() {
        return transaction(() -> {
            List<Map<String,Object>> rows = new ArrayList<>();
            try (Statement statement = db.createStatement(); ResultSet rs = statement.executeQuery("SELECT * FROM user_data ORDER BY u_seq")) {
                while (rs.next()) rows.add(readRow(rs));
            }
            return rows;
        });
    }
    @Override public Map<String,Object> exportUser(String identifier) {
        return transaction(() -> {
            String uuid = resolve(identifier);
            if (uuid == null) return null;
            Map<String,Object> row = row("SELECT * FROM user_data WHERE uuid=?", uuid);
            Map<String,Object> user = reconstruct(row);
            user.put("last_domain", Json.str(row.get("last_domain")));
            return user;
        });
    }
    @Override public void importUser(Map<String,Object> user) {
        Objects.requireNonNull(user, "user");
        Map<String,Object> ud = Json.map(user.get("userdata"));
        String uuid = Json.str(Json.first(user.get("uuid"), ud.get("uuid")));
        if (uuid.isBlank()) throw new IllegalArgumentException("Imported user must have a canonical uuid");
        transaction(() -> {
            String device = Json.str(Json.first(ud.get("device_uuid"), uuid));
            long sequence = Json.lng(ud.get("u_seq"));
            if (sequence <= 0) sequence = Math.max(100000, Json.lng(row("SELECT MAX(u_seq) AS m FROM user_data").get("m"))) + 1;
            String uid = Json.str(Json.first(ud.get("u_id"), "guest_" + sequence));
            Map<String,Object> collision = row("SELECT uuid FROM user_data WHERE uuid IN (?,?,?) OR device_uuid IN (?,?,?) OR u_id IN (?,?,?) OR u_seq=?",
                    uuid, device, uid, uuid, device, uid, uuid, device, uid, sequence);
            if (collision != null) throw new IllegalArgumentException("Imported user aliases belong to another account");
            update("""
                INSERT INTO user_data(uuid,device_uuid,u_id,u_seq,u_cp,u_candy,u_like,u_fans,attendance_count,attendance_date,user_contents_json,is_banned,ip,last_domain)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, uuid, device, uid, sequence, Json.lng(ud.get("u_cp")), Json.dbl(ud.get("u_candy")),
                    Currency.parse(ud.get("u_like")).floating(), Json.lng(ud.get("u_fans")),
                    Json.integer(ud.get("attendance_count")), Json.integer(ud.get("attendance_date")), storedJson(user),
                    Json.truth(user.get("is_banned")) ? 1 : 0, Json.str(Json.first(user.get("ip"), ud.get("ip"), "")), Json.str(user.get("last_domain")));
            writeInventories(uuid, user);
            return null;
        });
    }
    private Map<String,Object> getUserInternal(String identifier) throws SQLException {
        String uuid = resolve(identifier);
        return uuid == null ? null : reconstruct(row("SELECT * FROM user_data WHERE uuid = ?", uuid));
    }

    private Map<String,Object> reconstruct(Map<String,Object> row) throws SQLException {
        Map<String,Object> data = Json.map(Json.parse(Json.str(row.get("user_contents_json"))));
        // Old Python create_user kept starter inventory in JSON until the first save.
        // Use that legacy snapshot only for types that have never been separated.
        Map<String,String> types = new HashMap<>();
        for (var entry : INVENTORIES.entrySet()) types.put(entry.getValue(), entry.getKey());
        Map<String,List<Object>> inventory = new LinkedHashMap<>();
        for (String key : INVENTORIES.keySet()) inventory.put(key, new ArrayList<>());
        Set<String> present = new HashSet<>();
        try (PreparedStatement statement = prepare("SELECT * FROM user_inventory WHERE uuid = ?", row.get("uuid")); ResultSet rs = statement.executeQuery()) {
            while (rs.next()) {
                String key = types.get(rs.getString("item_type"));
                if (key == null) continue;
                present.add(key);
                Map<String,Object> item = Json.obj("i_id", rs.getLong("item_id"));
                if (!"gift".equals(rs.getString("item_type"))) item.put("i_Level", rs.getLong("level"));
                if (rs.getLong("active_time") != 0) item.put("i_ActiveTime", rs.getLong("active_time"));
                if (rs.getLong("bonus_level") != 0) item.put("i_BonusLevel", rs.getLong("bonus_level"));
                if ("gift".equals(rs.getString("item_type"))) item.put("i_Value", rs.getLong("value"));
                String extra = rs.getString("extra_json");
                if (extra != null && !extra.isEmpty()) try { item.putAll(Json.map(Json.parse(extra))); } catch (IllegalArgumentException ignored) {}
                inventory.get(key).add(item);
            }
        }
        for (String key : INVENTORIES.keySet()) {
            if (present.contains(key) || !(data.get(key) instanceof List<?>)) data.put(key, inventory.get(key));
        }
        Map<String,Object> ud = ensureMap(data, "userdata");
        data.put("uuid", row.get("uuid"));
        ud.put("u_join_type", 1);
        for (String key : List.of("uuid", "device_uuid", "u_id", "u_seq")) ud.put(key, row.get(key));
        for (String key : CURRENCIES) ud.put(key, row.get(key) == null ? 0 : row.get(key));
        String ip = Json.str(Json.first(row.get("ip"), ud.get("ip"), ""));
        ud.put("ip", ip); data.put("ip", ip);
        data.put("is_banned", Json.truth(row.get("is_banned")));
        if (!data.containsKey("created_at")) {
            long created = Json.lng(Json.first(data.get("last_save_time"), Instant.now().getEpochSecond()));
            try { created = LocalDate.parse(Json.str(ud.get("u_create_time")), DateTimeFormatter.BASIC_ISO_DATE).atStartOfDay(emu.leman.ggserver.util.GameTime.ZONE).toEpochSecond(); }
            catch (RuntimeException ignored) {}
            data.put("created_at", created);
        }
        ensureAreas(data);
        emu.leman.ggserver.game.economy.AreaCurrency.normalize(data);
        return data;
    }

    public Map<String,Object> createUser(String uuid, String deviceUuid) { return createUser(uuid, deviceUuid, ""); }
    public Map<String,Object> createUser(String uuid, String deviceUuid, String ip) {
        String canonical = uuid;
        String device = deviceUuid;
        if (canonical == null || canonical.isEmpty()) canonical = device;
        if (canonical == null || canonical.isEmpty()) canonical = "gen_" + UUID.randomUUID().toString().replace("-", "").substring(0, 16);
        if (device == null || device.isEmpty()) device = canonical;
        final String id = canonical, dev = device;
        return transaction(() -> {
            Map<String,Object> existing = getUserInternal(dev);
            if (existing == null) existing = getUserInternal(id);
            if (existing != null) {
                if (ip != null && !ip.isEmpty() && !Json.truth(existing.get("ip"))) updateIpInternal(Json.str(existing.get("uuid")), ip, null);
                return getUserInternal(Json.str(existing.get("uuid")));
            }
            Map<String,Object> maximum = row("SELECT MAX(u_seq) AS m FROM user_data");
            long seq = maximum.get("m") == null ? 100001 : Json.lng(maximum.get("m")) + 1;
            Map<String,Object> user = defaultUser(seq, id, dev, ip == null ? "" : ip);
            update("""
                INSERT INTO user_data (uuid,device_uuid,u_id,u_seq,u_cp,u_candy,u_like,u_fans,
                    attendance_count,attendance_date,user_contents_json,ip)
                VALUES (?,?,?,?,0,0.0,0.0,0,0,0,?,?)
                """, id, dev, "guest_" + seq, seq, storedJson(user), ip == null ? "" : ip);
            writeInventories(id, user);
            return reconstruct(row("SELECT * FROM user_data WHERE uuid = ?", id));
        });
    }

    public void saveUser(Map<String,Object> user) {
        if (user == null) return;
        Map<String,Object> ud = Json.map(user.get("userdata"));
        String identifier = Json.str(Json.first(user.get("uuid"), ud.get("uuid")));
        if (identifier.isEmpty()) return;
        transaction(() -> {
            String uuid = resolve(identifier);
            if (uuid == null) return null;
            writeInventories(uuid, user);
            String ip = Json.str(Json.first(user.get("ip"), ud.get("ip"), "")).strip();
            boolean setIp = !ip.isEmpty() && !LOCAL_IPS.contains(ip);
            String sql = "UPDATE user_data SET user_contents_json=?,u_cp=?,u_candy=?,u_like=?,u_fans=?,attendance_count=?,attendance_date=?"
                    + (setIp ? ",ip=?" : "") + " WHERE uuid=?";
            List<Object> values = new ArrayList<>(List.of(storedJson(user), Json.lng(ud.get("u_cp")), Json.dbl(ud.get("u_candy")),
                    Currency.parse(ud.get("u_like")).floating(), Json.lng(ud.get("u_fans")),
                    Json.integer(ud.get("attendance_count")), Json.integer(ud.get("attendance_date"))));
            if (setIp) values.add(ip);
            values.add(uuid);
            update(sql, values.toArray());
            return null;
        });
    }

    private static String storedJson(Map<String,Object> user) {
        Map<String,Object> stored = new LinkedHashMap<>(user);
        Map<String,Object> ud = new LinkedHashMap<>(Json.map(user.get("userdata")));
        CURRENCIES.forEach(ud::remove);
        stored.put("userdata", ud);
        INVENTORIES.keySet().forEach(stored::remove);
        return Json.stringify(stored);
    }

    private void writeInventories(String uuid, Map<String,Object> user) throws SQLException {
        // Keep the same enclosing transaction and replacement semantics, but
        // prepare once per save instead of compiling SQL for every inventory row.
        try(var delete=db.prepareStatement("DELETE FROM user_inventory WHERE uuid=? AND item_type=?");
                var insert=db.prepareStatement("""
                INSERT INTO user_inventory (uuid,item_type,item_id,level,active_time,bonus_level,value,extra_json)
                VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(uuid,item_type,item_id) DO UPDATE SET
                level=excluded.level,active_time=excluded.active_time,bonus_level=excluded.bonus_level,
                value=excluded.value,extra_json=excluded.extra_json
                """)) {
            for (var entry : INVENTORIES.entrySet()) {
                if (!user.containsKey(entry.getKey())) continue;
                delete.setString(1,uuid);delete.setString(2,entry.getValue());delete.executeUpdate();
                for (Object raw : Json.list(user.get(entry.getKey()))) {
                    Map<String,Object> item = Json.map(raw);
                    Map<String,Object> extra = new LinkedHashMap<>(item);
                    ITEM_COLUMNS.forEach(extra::remove);
                    insert.setString(1,uuid);insert.setString(2,entry.getValue());
                    insert.setLong(3,Json.lng(item.get("i_id")));insert.setLong(4,Json.lng(item.getOrDefault("i_Level",1)));
                    insert.setLong(5,Json.lng(item.get("i_ActiveTime")));insert.setLong(6,Json.lng(item.get("i_BonusLevel")));
                    insert.setLong(7,Json.lng(item.get("i_Value")));insert.setString(8,extra.isEmpty()?null:Json.stringify(extra));
                    insert.addBatch();
                }
                insert.executeBatch();insert.clearBatch();
            }
        }
    }

    public void updateUserIp(String identifier, String ip) { updateUserIp(identifier, ip, null); }
    public void updateUserIp(String identifier, String ip, String domain) {
        transaction(() -> { updateIpInternal(identifier, ip, domain); return null; });
    }
    private void updateIpInternal(String identifier, String ip, String domain) throws SQLException {
        String uuid = resolve(identifier);
        if (uuid == null) return;
        String address = ip == null ? "" : ip.strip();
        String host = domain == null ? "" : domain.strip().toLowerCase(Locale.ROOT);
        boolean local = host.isEmpty() || LOCAL_IPS.contains(host) || host.equals("local");
        Map<String,Object> old = row("SELECT ip,last_domain FROM user_data WHERE uuid=?", uuid);
        String newIp = Json.str(old.get("ip"));
        if (!address.isEmpty() && (!LOCAL_IPS.contains(address) || newIp.isEmpty())) newIp = address;
        update("UPDATE user_data SET ip=?,last_domain=? WHERE uuid=?", newIp, local ? Json.str(old.get("last_domain")) : host, uuid);
    }

    public void incrementCurrency(String identifier, long cp, double candy, Object like, long fans) {
        transaction(() -> {
            String uuid = resolve(identifier);
            if (uuid == null) return null;
            Currency.Parsed delta = Currency.parse(like);
            Map<String,Object> row = row("SELECT u_like,user_contents_json FROM user_data WHERE uuid=?", uuid);
            Map<String,Object> data = parseContents(row);
            ensureMap(data,"userdata").put("u_like",row.get("u_like"));
            emu.leman.ggserver.game.economy.AreaCurrency.addLike(data,like);
            double newLike=Json.dbl(ensureMap(data,"userdata").get("u_like"));
            if (delta.integer().signum() != 0 || cp != 0 || candy != 0) data.put("needs_client_reset", true);
            update("UPDATE user_data SET user_contents_json=?,u_like=?,u_cp=u_cp+?,u_candy=u_candy+?,u_fans=u_fans+? WHERE uuid=?",
                    Json.stringify(data),newLike,cp,candy,fans,uuid);
            return null;
        });
    }

    public void setLikeCurrency(String identifier, Object amount) {
        transaction(() -> {
            String uuid = resolve(identifier);
            if (uuid == null) return null;
            Currency.Parsed parsed = Currency.parse(amount);
            Map<String,Object> data = parseContents(row("SELECT user_contents_json FROM user_data WHERE uuid=?", uuid));
            emu.leman.ggserver.game.economy.AreaCurrency.setLike(data,amount);
            update("UPDATE user_data SET u_like=?,user_contents_json=? WHERE uuid=?", parsed.floating(), Json.stringify(data), uuid);
            return null;
        });
    }

    public boolean banUser(String identifier, boolean banned) { return banUser(identifier, banned, null); }
    public boolean banUser(String identifier) { return banUser(identifier, true, null); }
    public boolean banUser(String identifier, boolean banned, Long seq) {
        return transaction(() -> {
            String uuid = "null".equals(identifier) ? null : resolve(identifier);
            if (uuid != null) return update("UPDATE user_data SET is_banned=? WHERE uuid=?", banned ? 1 : 0, uuid) != 0;
            if (seq != null && seq != 0) { update("UPDATE user_data SET is_banned=? WHERE u_seq=?", banned ? 1 : 0, seq); return true; }
            return false;
        });
    }
    public boolean isUserBanned(String identifier) {
        return transaction(() -> {
            String uuid = resolve(identifier);
            Map<String,Object> found = uuid == null ? null : row("SELECT is_banned FROM user_data WHERE uuid=?", uuid);
            return found != null && Json.truth(found.get("is_banned"));
        });
    }

    public boolean deleteUser(String identifier) { return deleteUser(identifier, null); }
    public boolean deleteUser(String identifier, Long seq) {
        return transaction(() -> {
            String uuid = "null".equals(identifier) ? null : resolve(identifier);
            if (uuid == null && seq != null && seq != 0) {
                Map<String,Object> found = row("SELECT uuid FROM user_data WHERE u_seq=?", seq);
                if (found != null && found.get("uuid") != null) uuid = Json.str(found.get("uuid"));
            }
            if (uuid != null) {
                update("DELETE FROM user_inventory WHERE uuid=?", uuid);
                update("DELETE FROM user_data WHERE uuid=?", uuid);
                return true;
            }
            if (seq != null && seq != 0) { update("DELETE FROM user_data WHERE u_seq=?", seq); return true; }
            return false;
        });
    }

    public static boolean isRealDeviceUuid(Object value) {
        return value instanceof String text && text.strip().matches("(?i)[0-9a-f]{32}");
    }
    public static boolean isTestUser(String uuid, String deviceUuid) {
        if (uuid == null || uuid.isEmpty() || deviceUuid == null || deviceUuid.isEmpty()) return true;
        for (String text : List.of(uuid.toLowerCase(Locale.ROOT), deviceUuid.toLowerCase(Locale.ROOT))) {
            if (text.contains("test") || text.contains("verify")) return true;
            for (String prefix : List.of("test", "t1-", "t2-", "t3-", "t4-", "t5-", "t6-", "t7-", "t8-", "t9-",
                    "emu-", "att-", "dm-", "verify-", "cat-", "music-", "ad-", "gift-", "fix-")) {
                if (text.startsWith(prefix)) return true;
            }
        }
        return !isRealDeviceUuid(uuid);
    }
    public int cleanupTestUsers() {
        return transaction(() -> {
            List<Map<String,Object>> users = new ArrayList<>();
            try (Statement statement = db.createStatement(); ResultSet rs = statement.executeQuery("SELECT rowid,uuid,device_uuid FROM user_data")) {
                while (rs.next()) users.add(readRow(rs));
            }
            int deleted = 0;
            for (Map<String,Object> user : users) if (isTestUser(Json.str(user.get("uuid")), Json.str(user.get("device_uuid")))) {
                update("DELETE FROM user_inventory WHERE uuid=?", user.get("uuid"));
                update("DELETE FROM user_data WHERE rowid=?", user.get("rowid"));
                deleted++;
            }
            return deleted;
        });
    }

    public boolean spendCurrency(String identifier, String currency, double amount) {
        if (!Double.isFinite(amount)) return false;
        double spend = "cp".equals(currency) ? (double)(long)amount : amount;
        if (spend < 0) return false;
        if (spend == 0) return true;
        String column = "cp".equals(currency) ? "u_cp" : "u_candy";
        return transaction(() -> {
            String uuid = resolve(identifier);
            if (uuid == null) return false;
            Object value = "cp".equals(currency) ? (Object)(long)spend : spend;
            return update("UPDATE user_data SET " + column + "=" + column + "-? WHERE uuid=? AND " + column + ">=?", value, uuid, value) == 1;
        });
    }
    /** Integer overload avoids losing CP precision above the double exact-integer range. */
    public boolean spendCurrency(String identifier, String currency, long amount) {
        if (!"cp".equals(currency)) return spendCurrency(identifier, currency, (double)amount);
        if (amount < 0) return false;
        if (amount == 0) return true;
        return transaction(() -> {
            String uuid = resolve(identifier);
            return uuid != null && update("UPDATE user_data SET u_cp=u_cp-? WHERE uuid=? AND u_cp>=?", amount, uuid, amount) == 1;
        });
    }
    public void setCurrency(String identifier, long cp, double candy) {
        transaction(() -> {
            String uuid = resolve(identifier);
            if (uuid != null) update("UPDATE user_data SET u_cp=?,u_candy=? WHERE uuid=?", cp, candy, uuid);
            return null;
        });
    }
    public void updateAttendance(String identifier, int count, int date) {
        transaction(() -> {
            String uuid = resolve(identifier);
            if (uuid != null) update("UPDATE user_data SET attendance_count=?,attendance_date=? WHERE uuid=?", count, date, uuid);
            return null;
        });
    }

    public static Map<String,Object> addAp(Map<String,Object> user, int amount) {
        if (user == null || user.isEmpty()) return new LinkedHashMap<>();
        if (!(user.get("user_ap") instanceof Map<?,?>)) user.put("user_ap", defaultAp());
        Map<String,Object> ap = Json.map(user.get("user_ap"));
        long current = Json.lng(Json.first(ap.get("i_Ap"), 70));
        long maximum = Json.lng(Json.first(ap.get("i_MaxAp"), 70));
        ap.put("i_Ap", current + amount);
        if (current + amount >= maximum) ap.put("i_FullApTime", 0);
        return ap;
    }

    private static Map<String,Object> ensureMap(Map<String,Object> parent, String key) {
        if (!(parent.get(key) instanceof Map<?,?>)) parent.put(key, new LinkedHashMap<String,Object>());
        return Json.map(parent.get(key));
    }
    private static String exactForcedLike(Map<String,Object> data) {
        Object value = data.get("force_server_like");
        return value instanceof String text && text.matches("[0-9]+") ? text : null;
    }
    private static Map<String,Object> ensureAreas(Map<String,Object> data) {
        if (!(data.get("areas") instanceof Map<?,?>)) data.put("areas", defaultAreas());
        return Json.map(data.get("areas"));
    }
    private static Map<String,Object> parseContents(Map<String,Object> row) {
        try { return Json.map(Json.parse(Json.str(row.get("user_contents_json")))); }
        catch (IllegalArgumentException e) { return new LinkedHashMap<>(); }
    }
    private static Map<String,Object> defaultAp() { return Json.obj("i_Ap", 70, "i_FullApTime", 0, "i_MaxAp", 70); }
    /** Stage definitions helper; fresh users intentionally start with no stage progress. */
    public List<Map<String,Object>> allChThirdStages() {
        return allChThirdStages(config);
    }
    public static List<Map<String,Object>> allChThirdStages(emu.leman.ggserver.config.ServerConfig config) {
        try {
            Map<String,Object> gameData = Json.map(Json.read(config.resource("gamedata/game_data.json")));
            List<Map<String,Object>> stages = new ArrayList<>();
            for (Object value : Json.list(gameData.get("33"))) {
                Map<String,Object> row = Json.map(value);
                int id = Json.integer(row.get("1"));
                if (id > 0) stages.add(Json.obj("i_id", id, "i_ChapterId", Json.integer(row.get("2")),
                        "i_StageIndex", Json.integer(row.get("3")), "i_Star", "Normal".equals(Json.str(row.get("34"))) ? 3 : 0));
            }
            return stages;
        } catch (RuntimeException e) {
            Set<Integer> normal = Set.of(1001, 1004, 1006, 1008, 1010, 1011, 1013, 1015, 1017, 1019,
                    2002, 2004, 2007, 2009, 2010, 2012, 2014, 2016, 2018, 2020);
            List<Map<String,Object>> stages = new ArrayList<>();
            for (int chapter = 1; chapter <= 2; chapter++) {
                for (int index = 1; index <= (chapter == 1 ? 20 : 21); index++) {
                    int id = chapter * 1000 + index;
                    stages.add(Json.obj("i_id", id, "i_ChapterId", chapter, "i_StageIndex", index,
                            "i_Star", normal.contains(id) ? 3 : 0));
                }
            }
            return stages;
        }
    }
    private static Map<String,Object> defaultAreas() {
        Map<String,Object> result = new LinkedHashMap<>();
        for (int i = 1; i <= 2; i++) {
            int selected = i == 1 ? 1 : 201;
            result.put(Integer.toString(i), Json.obj("u_area_num", i, "d_Candy", 0.0, "d_Like", 0.0,
                    "i_UserFanCount", 0, "i_UserFanGrade", 1, "i_SelectedCostumeId", selected,
                    "i_SelectedMusicId", selected, "i_SelectedGuitarId", selected,
                    "s_TutorialList", "", "s_Gp1", "", "s_Gp2", ""));
        }
        return result;
    }
    private static List<Object> equipment(int... ids) {
        List<Object> items = new ArrayList<>();
        for (int id : ids) items.add(Json.obj("i_id", id, "i_Level", 1, "i_BonusLevel", 0));
        return items;
    }
    public static Map<String,Object> defaultUser(long sequence, String uuid, String deviceUuid, String ip) {
        String guest = "guest_" + sequence;
        LocalDateTime now = emu.leman.ggserver.util.GameTime.localNow();
        String timestamp = now.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
        Map<String,Object> ud = Json.obj("u_seq", sequence, "u_id", guest, "uuid", uuid, "u_name", guest,
                "u_nick", "Guitarist", "u_fans_grade", 1, "u_selected_costume_id", 1, "u_selected_music_id", 1,
                "u_retain_continuous_tap", 0, "u_join_type", 1, "u_last_login", timestamp,
                "u_last_communication", timestamp, "u_save_date", timestamp,
                "u_create_time", now.format(DateTimeFormatter.BASIC_ISO_DATE), "u_tutorial_step", 0,
                "u_review_popup", "N", "device_uuid", deviceUuid, "u_samseck_step", 0,
                "u_free_cp", 0, "u_charge_cp", 0, "u_fans", 0, "u_like", 0.0, "u_ap", 70, "u_cp", 0);
        List<Object> achievements = new ArrayList<>();
        for (int i = 1; i <= 10; i++) achievements.add(Json.obj("i_id", i, "i_Level", 1, "d_Quantity", 1.0, "s_Quantity", ""));
        List<Object> music = equipment(1, 201);
        for (Object item : music) Json.map(item).putAll(Json.obj("b_EncoreBonusAppear", 0, "l_EncoreBonusActivateTime", 0,
                "i_EncoreBonusFollowerId", 0, "i_ChThirdActiveTime", 0));
        long epoch = Instant.now().getEpochSecond();
        List<Object> stages = new ArrayList<>();
        return Json.obj("uuid", uuid, "ip", ip, "created_at", epoch, "posts", new ArrayList<>(),
                "welcome_post_sent", false, "deleted_post_indices", new ArrayList<>(), "userdata", ud,
                "needs_client_reset", true, "last_save_time", epoch, "areas", defaultAreas(),
                "achievements", achievements, "characters", equipment(1, 2), "costumes", equipment(1, 201),
                "user_music", music, "user_guitar", equipment(1, 201), "user_follower", equipment(1),
                "user_follower_profile", new ArrayList<>(List.of(
                        Json.obj("i_id", 1, "i_Level", 1, "d_Exp", 0, "i_AddCandy", 0),
                        Json.obj("i_id", 100000, "i_Level", 1, "d_Exp", 0, "i_AddCandy", 0))),
                "user_follower_profile_reward", new ArrayList<>(),
                "user_follower_giftitem", new ArrayList<>(List.of(Json.obj("i_id", 1, "i_Value", 141))),
                "user_ch_third_stage", stages, "user_chthird_stage", stages, "user_ap", defaultAp(),
                "user_messenger", new ArrayList<>(List.of(Json.obj("i_MessengerChatRoomId", 1, "i_LastConfirmIndex", 0,
                        "s_UnlockGroupList", "1", "l_UpdateTimeTicks", 0))), "legacy_unlock_all_migrated", true);
    }

    @Override public void close() {
        lock.lock();
        try {
            if (!closed) { db.close(); closed = true; }
        } catch (SQLException e) {
            throw new IllegalStateException("Cannot close state database", e);
        } finally {
            lock.unlock();
        }
    }
}

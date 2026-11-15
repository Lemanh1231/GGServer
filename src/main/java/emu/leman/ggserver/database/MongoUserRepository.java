package emu.leman.ggserver.database;

import com.mongodb.ErrorCategory;
import com.mongodb.MongoWriteException;
import com.mongodb.client.*;
import com.mongodb.client.model.*;
import emu.leman.ggserver.config.ServerConfig;
import emu.leman.ggserver.game.economy.Currency;
import emu.leman.ggserver.util.Json;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.*;
import java.util.function.Consumer;
import org.bson.Document;
import org.bson.conversions.Bson;
import static com.mongodb.client.model.Filters.*;
import static com.mongodb.client.model.Updates.*;

/**
 * Native MongoDB account storage. Identity/balances live in users; feature rows live in
 * separate collections. Immutable sections are staged then atomically published with CAS.
 * No replica-set transaction dependency, read-side migration, or SQLite access.
 */
public final class MongoUserRepository implements UserRepository {
    private static final List<String> CURRENCIES = List.of("u_cp", "u_candy", "u_like", "u_fans", "attendance_count", "attendance_date");
    private static final List<String> INVENTORIES = List.of("user_unit", "user_skill", "user_music", "user_guitar", "costumes",
            "user_prop", "user_follower", "user_follower_giftitem", "user_shop");
    private static final Set<String> LOCAL_IPS = Set.of("127.0.0.1", "localhost", "::1");
    private final ServerConfig config;
    private final MongoClient client;
    private final MongoCollection<Document> users;
    private final MongoCollection<Document> counters;
    private final MongoUserSections sections;
    private volatile boolean closed;

    public MongoUserRepository(ServerConfig config) {
        this.config = config;
        client = MongoClients.create(config.mongoUri);
        try {
            MongoDatabase database = client.getDatabase(config.mongoDatabase);
            users = database.getCollection("users");
            counters = database.getCollection("counters");
            sections = new MongoUserSections(database);
            // Never drop/rebuild indexes: an incompatible existing database must fail visibly.
            for (String field : List.of("device_uuid", "u_id", "u_seq"))
                users.createIndex(Indexes.ascending(field), new IndexOptions().unique(true));
            // A multikey uniqueness constraint prevents cross-field aliases racing (UUID versus device/id/sequence).
            users.createIndex(Indexes.ascending("aliases"), new IndexOptions().unique(true).sparse(true));
            Document last = users.find().sort(Sorts.descending("u_seq")).first();
            advanceCounter(last == null ? 100000 : Math.max(100000, Json.lng(last.get("u_seq"))));
        } catch (RuntimeException | Error failure) {
            client.close();
            throw failure;
        }
    }

    private void checkOpen() { if (closed) throw new IllegalStateException("StateStore is closed"); }
    private void advanceCounter(long sequence) {
        try { counters.updateOne(eq("_id", "user_sequence"), max("value", sequence), new UpdateOptions().upsert(true)); }
        catch (MongoWriteException e) {
            if (e.getError().getCategory() != ErrorCategory.DUPLICATE_KEY) throw e;
            counters.updateOne(eq("_id", "user_sequence"), max("value", sequence));
        }
    }
    private long nextSequence() {
        Document counter = counters.findOneAndUpdate(eq("_id", "user_sequence"), inc("value", 1L),
                new FindOneAndUpdateOptions().returnDocument(ReturnDocument.AFTER));
        return Json.lng(Objects.requireNonNull(counter).get("value"));
    }
    private Document find(String identifier) {
        checkOpen();
        if (identifier == null || identifier.isEmpty()) return null;
        Document found = users.find(eq("_id", identifier)).first();
        if (found != null) return found;
        String sequence = identifier.strip();
        if (sequence.startsWith("guest_")) sequence = sequence.substring(6);
        long seq = -1;
        try { if (sequence.matches("[0-9]+")) seq = Long.parseLong(sequence); } catch (NumberFormatException ignored) {}
        return users.find(or(eq("device_uuid", identifier), eq("u_id", identifier), eq("u_seq", seq))).first();
    }
    @Override public String canonicalIdentity(String identifier) {
        var document=find(identifier);
        return document==null?identifier:document.getString("_id");
    }
    private Map<String,Object> contents(Document document) {
        return sections.read(document);
    }
    private static Map<String,Object> ensureMap(Map<String,Object> parent, String key) {
        if (!(parent.get(key) instanceof Map<?,?>)) parent.put(key, new LinkedHashMap<String,Object>());
        return Json.map(parent.get(key));
    }
    private static String forcedExact(Map<String,Object> data) {
        Object value = data.get("force_server_like");
        return value instanceof String text && text.matches("[0-9]+") ? text : null;
    }
    /** BSON cannot encode arbitrary-precision integers; preserve those as exact decimal strings. */
    private static Object bsonValue(Object value) {
        if (value instanceof BigInteger || value instanceof BigDecimal) return value.toString();
        if (value instanceof Map<?,?> map) {
            Document document = new Document();
            map.forEach((key, entry) -> document.put(String.valueOf(key), bsonValue(entry)));
            return document;
        }
        if (value instanceof List<?> list) return list.stream().map(MongoUserRepository::bsonValue).toList();
        return value;
    }
    private static Document nativeContents(Map<String,Object> user) {
        Map<String,Object> copy = Json.copy(user); // Validate serializability before any write; don't mutate callers.
        Map<String,Object> ud = ensureMap(copy, "userdata");
        CURRENCIES.forEach(ud::remove);
        copy.remove("last_domain");
        return (Document)bsonValue(copy);
    }
    private Map<String,Object> reconstruct(Document document) {
        if (document == null) return null;
        Map<String,Object> user = contents(document);
        Map<String,Object> ud = ensureMap(user, "userdata");
        user.put("uuid", document.get("_id"));
        ud.put("uuid", document.get("_id"));
        for (String key : List.of("device_uuid", "u_id", "u_seq")) ud.put(key, document.get(key));
        ud.put("u_join_type", 1);
        for (String key : CURRENCIES) ud.put(key, document.getOrDefault(key, 0));
        String ip = Json.str(document.get("ip"));
        user.put("ip", ip); ud.put("ip", ip);
        user.put("is_banned", Json.truth(document.get("is_banned")));
        for (String inventory : INVENTORIES) user.putIfAbsent(inventory, new ArrayList<>());
        normalizeSavedInventories(user);
        emu.leman.ggserver.game.economy.AreaCurrency.normalize(user);
        return user;
    }
    private static Document account(Map<String,Object> user, String uuid, String device, String uid, long sequence) {
        Map<String,Object> ud = Json.map(user.get("userdata"));
        Document document = new Document("_id", uuid).append("device_uuid", device).append("u_id", uid).append("u_seq", sequence)
                .append("revision", 0L).append("contents", nativeContents(user));
        document.put("aliases", new ArrayList<>(new LinkedHashSet<>(List.of(uuid, device, uid, Long.toString(sequence), "guest_" + sequence))));
        copyCurrencies(document, ud);
        document.put("ip", Json.str(Json.first(user.get("ip"), ud.get("ip"), "")));
        document.put("last_domain", Json.str(user.get("last_domain")));
        document.put("is_banned", Json.truth(user.get("is_banned")));
        return document;
    }
    private static void copyCurrencies(Document document, Map<String,Object> ud) {
        document.put("u_cp", Json.lng(ud.get("u_cp")));
        document.put("u_candy", Json.dbl(ud.get("u_candy")));
        document.put("u_like", Currency.parse(ud.get("u_like")).floating());
        document.put("u_fans", Json.lng(ud.get("u_fans")));
        document.put("attendance_count", Json.integer(ud.get("attendance_count")));
        document.put("attendance_date", Json.integer(ud.get("attendance_date")));
    }
    private static Bson revisionFilter(Document document) {
        return and(eq("_id", document.get("_id")), eq("revision", document.get("revision")));
    }
    private boolean mutate(String identifier, Consumer<Document> mutation) {
        Document document = find(identifier);
        while (document != null) {
            Bson filter = revisionFilter(document);
            String uuid = document.getString("_id");
            long revision = Json.lng(document.get("revision"));
            mutation.accept(document);
            document.put("revision", revision + 1);
            Document staged=stageContents(document);
            // On an ambiguous network failure retain staged rows: the publication may have succeeded.
            if (users.replaceOne(filter, document).getMatchedCount() == 1) return true;
            if(staged!=null) sections.discard(uuid,staged);
            document = users.find(eq("_id", uuid)).first();
        }
        return false;
    }

    private Document stageContents(Document document) {
        if(!document.containsKey("contents")) return null;
        Document manifest=sections.stage(document.getString("_id"),(Document)document.get("contents"));
        document.remove("contents");document.put("sections",manifest);document.put("storage_version",2);
        return manifest;
    }

    /** Explicit per-account, revision-checked conversion. Never invoked just by reading. */
    public boolean splitLegacyUser(String identifier) {
        Document document=find(identifier);
        if(document==null || document.containsKey("sections")) return false;
        return mutate(identifier,current -> {});
    }

    @Override public Map<String,Object> getUser(String identifier) { return reconstruct(find(identifier)); }
    @Override public Map<String,Object> createUser(String uuid, String deviceUuid, String ip) {
        checkOpen();
        String canonical = uuid;
        if (canonical == null || canonical.isEmpty()) canonical = deviceUuid;
        if (canonical == null || canonical.isEmpty()) canonical = "gen_" + UUID.randomUUID().toString().replace("-", "").substring(0, 16);
        String device = deviceUuid == null || deviceUuid.isEmpty() ? canonical : deviceUuid;
        while (true) {
            Document existing = find(device);
            if (existing == null) existing = find(canonical);
            if (existing != null) {
                String id = existing.getString("_id");
                if (ip != null && !ip.isEmpty() && Json.str(existing.get("ip")).isEmpty()) updateUserIp(id, ip, null);
                return getUser(id);
            }
            long sequence = nextSequence();
            Map<String,Object> user = SqliteUserRepository.defaultUser(sequence, canonical, device, ip == null ? "" : ip);
            Document document = account(user, canonical, device, "guest_" + sequence, sequence);
            Document staged=stageContents(document);
            try { users.insertOne(document); return reconstruct(document); }
            catch (MongoWriteException e) {
                if (e.getError().getCategory() != ErrorCategory.DUPLICATE_KEY) throw e;
                sections.discard(canonical,staged);
            }
            // The unique device/canonical/sequence indexes choose the winner across processes.
        }
    }
    @Override public void saveUser(Map<String,Object> user) {
        if (user == null) return;
        Map<String,Object> snapshot = Json.copy(user);
        normalizeSavedInventories(snapshot);
        Map<String,Object> ud = Json.map(snapshot.get("userdata"));
        String identifier = Json.str(Json.first(snapshot.get("uuid"), ud.get("uuid")));
        if (identifier.isEmpty()) return;
        mutate(identifier, document -> {
            Map<String,Object> merged = contents(document);
            Map<String,Object> saved = new LinkedHashMap<>(snapshot);
            // SQLite keeps inventory types omitted by a partial save, but clears explicitly empty types.
            for (String inventory : INVENTORIES) if (!snapshot.containsKey(inventory) && merged.containsKey(inventory))
                saved.put(inventory, merged.get(inventory));
            document.put("contents", nativeContents(saved));
            copyCurrencies(document, ud);
            String ip = Json.str(Json.first(snapshot.get("ip"), ud.get("ip"), "")).strip();
            if (!ip.isEmpty() && !LOCAL_IPS.contains(ip)) document.put("ip", ip);
        });
    }
    /** Match the legacy SQL inventory round trip, including omitted zero-valued optional fields. */
    private static void normalizeSavedInventories(Map<String,Object> snapshot) {
        for(String inventory:INVENTORIES) {
            if(!snapshot.containsKey(inventory)) continue;
            boolean gift=inventory.equals("user_follower_giftitem");
            // SQL reads traverse the (uuid,item_type,item_id) primary key, not purchase order.
            Map<Long,Object> items=new TreeMap<>();
            for(Object raw:Json.list(snapshot.get(inventory))) {
                Map<String,Object> item=new LinkedHashMap<>(Json.map(raw));
                long id=Json.lng(item.get("i_id"));item.put("i_id",id);
                if(gift) { item.remove("i_Level");item.put("i_Value",Json.lng(item.get("i_Value"))); }
                else { item.put("i_Level",Json.lng(item.getOrDefault("i_Level",1)));item.remove("i_Value"); }
                for(String optional:List.of("i_ActiveTime","i_BonusLevel")) {
                    long value=Json.lng(item.get(optional));
                    if(value==0) item.remove(optional);else item.put(optional,value);
                }
                items.put(id,item);
            }
            snapshot.put(inventory,new ArrayList<>(items.values()));
        }
    }
    @Override public void updateUserIp(String identifier, String ip, String domain) {
        mutate(identifier, document -> {
            String address = ip == null ? "" : ip.strip();
            String host = domain == null ? "" : domain.strip().toLowerCase(Locale.ROOT);
            if (!address.isEmpty() && (!LOCAL_IPS.contains(address) || Json.str(document.get("ip")).isEmpty())) document.put("ip", address);
            if (!host.isEmpty() && !LOCAL_IPS.contains(host) && !host.equals("local")) document.put("last_domain", host);
        });
    }
    @Override public void incrementCurrency(String identifier, long cp, double candy, Object like, long fans) {
        Currency.Parsed delta = Currency.parse(like);
        mutate(identifier, document -> {
            document.put("u_cp", Json.lng(document.get("u_cp")) + cp);
            document.put("u_candy", Json.dbl(document.get("u_candy")) + candy);
            document.put("u_fans", Json.lng(document.get("u_fans")) + fans);
            Map<String,Object> data = contents(document);
            ensureMap(data,"userdata").put("u_like",document.get("u_like"));
            emu.leman.ggserver.game.economy.AreaCurrency.addLike(data,like);
            document.put("u_like",Json.dbl(ensureMap(data,"userdata").get("u_like")));
            if (delta.integer().signum() != 0 || cp != 0 || candy != 0) data.put("needs_client_reset", true);
            document.put("contents", nativeContents(data));
        });
    }
    @Override public void setLikeCurrency(String identifier, Object amount) {
        Currency.Parsed parsed = Currency.parse(amount);
        mutate(identifier, document -> {
            document.put("u_like", parsed.floating());
            Map<String,Object> data = contents(document);
            emu.leman.ggserver.game.economy.AreaCurrency.setLike(data,amount);
            document.put("contents", nativeContents(data));
        });
    }
    @Override public boolean spendCurrency(String identifier, String currency, double amount) {
        if (!Double.isFinite(amount)) return false;
        if ("cp".equals(currency)) return spendCurrency(identifier, currency, (long)amount);
        if (amount < 0) return false;
        if (amount == 0) return true;
        return spend(identifier, "u_candy", amount);
    }
    @Override public boolean spendCurrency(String identifier, String currency, long amount) {
        if (!"cp".equals(currency)) return spendCurrency(identifier, currency, (double)amount);
        if (amount < 0) return false;
        if (amount == 0) return true;
        return spend(identifier, "u_cp", amount);
    }
    private boolean spend(String identifier, String field, Number amount) {
        Document document = find(identifier);
        if (document == null) return false;
        Number negative;
        if (amount instanceof Long) negative = -amount.longValue();
        else negative = -amount.doubleValue();
        return users.updateOne(and(eq("_id", document.get("_id")), gte(field, amount)),
                combine(inc(field, negative), inc("revision", 1L))).getModifiedCount() == 1;
    }
    @Override public void setCurrency(String identifier, long cp, double candy) {
        mutate(identifier, document -> { document.put("u_cp", cp); document.put("u_candy", candy); });
    }
    @Override public void updateAttendance(String identifier, int count, int date) {
        mutate(identifier, document -> { document.put("attendance_count", count); document.put("attendance_date", date); });
    }
    @Override public boolean banUser(String identifier, boolean banned, Long sequence) {
        Document document = "null".equals(identifier) ? null : find(identifier);
        if (document != null) return mutate(document.getString("_id"), current -> current.put("is_banned", banned));
        if (sequence != null && sequence != 0) {
            users.updateOne(eq("u_seq", sequence), combine(set("is_banned", banned), inc("revision", 1L)));
            return true;
        }
        return false;
    }
    @Override public boolean isUserBanned(String identifier) {
        Document document = find(identifier);
        return document != null && Json.truth(document.get("is_banned"));
    }
    @Override public boolean deleteUser(String identifier, Long sequence) {
        Document document = "null".equals(identifier) ? null : find(identifier);
        if (document == null && sequence != null && sequence != 0) document = users.find(eq("u_seq", sequence)).first();
        if (document != null) {
            if(users.deleteOne(revisionFilter(document)).getDeletedCount()!=1) return deleteUser(identifier,sequence);
            sections.deletePublishedHistory(document.getString("_id"),document);return true;
        }
        return sequence != null && sequence != 0;
    }
    @Override public int cleanupTestUsers() {
        checkOpen();
        int deleted = 0;
        for (Document document : users.find()) if (SqliteUserRepository.isTestUser(document.getString("_id"), document.getString("device_uuid"))) {
            if(users.deleteOne(revisionFilter(document)).getDeletedCount()==1) {
                sections.deletePublishedHistory(document.getString("_id"),document);deleted++;
            }
        }
        return deleted;
    }
    @Override public List<Map<String,Object>> listUserRows() {
        checkOpen();
        List<Map<String,Object>> rows = new ArrayList<>();
        for (Document document : users.find().sort(Sorts.ascending("u_seq"))) {
            Map<String,Object> row = Json.obj("uuid", document.get("_id"));
            for (String key : List.of("device_uuid", "u_id", "u_seq", "ip", "last_domain")) row.put(key, document.get(key));
            CURRENCIES.forEach(key -> row.put(key, document.get(key)));
            row.put("is_banned", Json.truth(document.get("is_banned")) ? 1 : 0);
            Map<String,Object> data = contents(document);
            INVENTORIES.forEach(data::remove);
            row.put("user_contents_json", Json.stringify(data));
            rows.add(row);
        }
        return rows;
    }
    @Override public Map<String,Object> exportUser(String identifier) {
        Document document = find(identifier);
        if (document == null) return null;
        Map<String,Object> user = reconstruct(document);
        user.put("last_domain", Json.str(document.get("last_domain")));
        return user;
    }
    @Override public void importUser(Map<String,Object> user) {
        checkOpen();
        Objects.requireNonNull(user, "user");
        Map<String,Object> snapshot = Json.copy(user);
        Map<String,Object> ud = Json.map(snapshot.get("userdata"));
        String uuid = Json.str(Json.first(snapshot.get("uuid"), ud.get("uuid")));
        if (uuid.isBlank()) throw new IllegalArgumentException("Imported user must have a canonical uuid");
        String device = Json.str(Json.first(ud.get("device_uuid"), uuid));
        long sequence = Json.lng(ud.get("u_seq"));
        if (sequence <= 0) sequence = nextSequence();
        String uid = Json.str(Json.first(ud.get("u_id"), "guest_" + sequence));
        Document replacement = account(snapshot, uuid, device, uid, sequence);
        if (users.find(or(in("_id", uuid, device, uid), in("device_uuid", uuid, device, uid), in("u_id", uuid, device, uid), eq("u_seq", sequence))).first() != null)
            throw new IllegalArgumentException("Imported user aliases belong to an existing account");
        advanceCounter(sequence);
        Document staged=stageContents(replacement);
        try {
            users.insertOne(replacement);
        } catch (MongoWriteException e) {
            if (e.getError().getCategory() != ErrorCategory.DUPLICATE_KEY) throw e;
            sections.discard(uuid,staged);
            throw new IllegalArgumentException("Imported user aliases belong to another account (or simultaneous import)", e);
        }
    }
    @Override public List<Map<String,Object>> allChThirdStages() { return SqliteUserRepository.allChThirdStages(config); }
    @Override public void close() { if (!closed) { closed = true; client.close(); } }
}

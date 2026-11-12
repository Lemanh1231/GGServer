package emu.leman.ggserver.database;

import com.mongodb.client.MongoClients;
import de.bwaldvogel.mongo.MongoServer;
import de.bwaldvogel.mongo.backend.memory.MemoryBackend;
import emu.leman.ggserver.config.ServerConfig;
import emu.leman.ggserver.game.economy.Currency;
import emu.leman.ggserver.util.Json;
import java.math.BigInteger;
import java.net.InetSocketAddress;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import org.bson.Document;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

/** Uses a real Mongo wire-protocol server, not mocked driver calls. */
class MongoUserRepositoryTest {
    @TempDir Path root;
    private MongoServer server;
    private ServerConfig config;
    private static final String UUID = "0123456789abcdef0123456789abcdef";
    private static final String DEVICE = "fedcba9876543210fedcba9876543210";
    private static Map<String,Object> ud(Map<String,Object> user) { return Json.map(user.get("userdata")); }

    @BeforeEach void start() {
        server = new MongoServer(new MemoryBackend());
        InetSocketAddress address = server.bind();
        config = ServerConfig.defaults(root, Json.obj("database", Json.obj("backend", "mongo", "name", "test_accounts",
                "uri", "mongodb://" + address.getHostString() + ":" + address.getPort() + "/?serverSelectionTimeoutMS=5000")));
    }
    @AfterEach void stop() { server.shutdownNow(); }

    @Test void aliasesMetadataInventoryAndReopenWithoutTouchingSqlite() {
        try (StateStore store = new StateStore(config)) {
            Map<String,Object> user = store.createUser(UUID, DEVICE, "203.0.113.7");
            assertEquals(100001, Json.lng(ud(user).get("u_seq")));
            assertEquals(70, Json.lng(Json.map(user.get("user_ap")).get("i_Ap")));
            assertEquals(2, Json.list(user.get("costumes")).size());
            assertEquals(UUID, store.createUser("another-install", DEVICE).get("uuid"));
            for (String alias : List.of(UUID, DEVICE, "100001", "guest_100001")) {
                assertEquals(UUID, store.getUser(alias).get("uuid"));
                assertTrue(store.banUser(alias));
                assertTrue(store.isUserBanned(alias));
            }
            store.updateUserIp(DEVICE, "127.0.0.1", "LOCALHOST");
            store.updateUserIp(DEVICE, "", " Game.Example ");
            store.updateAttendance(DEVICE, 9, 20261111);
            user = store.getUser(UUID);
            user.put("user_music", List.of(Json.obj("i_id", 201, "i_Level", 9, "custom", Json.obj("nested", 7))));
            ud(user).put("u_cp", 9007199254740994L);
            String before = Json.stringify(user);
            store.saveUser(user);
            assertEquals(before, Json.stringify(user));
            Map<String,Object> row = store.listUserRows().getFirst();
            assertEquals("game.example", row.get("last_domain"));
            assertEquals(1, row.get("is_banned"));
            assertFalse(Json.map(Json.parse(Json.str(row.get("user_contents_json")))).containsKey("user_music"));
        }
        try (StateStore store = new StateStore(config)) {
            Map<String,Object> user = store.getUser(DEVICE);
            assertEquals(9007199254740994L, Json.lng(ud(user).get("u_cp")));
            assertEquals(9, Json.integer(ud(user).get("attendance_count")));
            assertEquals("203.0.113.7", user.get("ip"));
            assertTrue(store.isUserBanned(DEVICE));
            assertEquals(7, Json.integer(Json.map(Json.map(Json.list(user.get("user_music")).getFirst()).get("custom")).get("nested")));
            user.put("user_music", new ArrayList<>());
            store.saveUser(user);
            assertTrue(Json.list(store.getUser(UUID).get("user_music")).isEmpty());
        }
        assertFalse(Files.exists(root.resolve("data/database.db")));
    }

    @Test void savedInventoriesMatchLegacySqliteOptionalFieldNormalization() {
        try(StateStore mongo=new StateStore(config);StateStore sqlite=new StateStore(root.resolve("legacy"))) {
            for(StateStore store:List.of(mongo,sqlite)) {
                var user=store.createUser(UUID,DEVICE);
                user.put("costumes",List.of(Json.obj("i_id",1,"i_BonusLevel",0,"i_ActiveTime",0,"i_Value",7,"custom",true)));
                user.put("user_follower_giftitem",List.of(Json.obj("i_id",2,"i_Level",5,"i_BonusLevel",0)));
                store.saveUser(user);
            }
            for(String inventory:List.of("costumes","user_follower_giftitem"))
                assertEquals(Json.parse(Json.stringify(sqlite.getUser(UUID).get(inventory))),Json.parse(Json.stringify(mongo.getUser(UUID).get(inventory))));
        }
    }

    @Test void purchasedAndRewardedInventoriesUseNumericIdOrderAfterReload() {
        List<String> inventories=List.of("costumes","user_music","user_guitar","user_shop","user_follower_giftitem");
        try(StateStore mongo=new StateStore(config);StateStore sqlite=new StateStore(root.resolve("legacy"))) {
            for(StateStore store:List.of(mongo,sqlite)) {
                var user=store.createUser(UUID,DEVICE);
                for(String inventory:inventories) user.put(inventory,List.of(
                        Json.obj("i_id",201,"i_Level",1,"i_Value",1),
                        Json.obj("i_id",1003,"i_Level",1,"i_Value",2),
                        Json.obj("i_id",13,"i_Level",1,"i_Value",3),
                        Json.obj("i_id",2,"i_Level",1,"i_Value",4),
                        Json.obj("i_id",13,"i_Level",2,"i_Value",5)));
                store.saveUser(user);
            }
            for(String inventory:inventories) {
                var actual=Json.list(mongo.getUser(DEVICE).get(inventory));
                assertEquals(List.of(2L,13L,201L,1003L),actual.stream().map(row->Json.lng(Json.map(row).get("i_id"))).toList());
                assertEquals(Json.parse(Json.stringify(sqlite.getUser(UUID).get(inventory))),Json.parse(Json.stringify(actual)));
            }
        }
        try(StateStore reopened=new StateStore(config)) {
            assertEquals(2L,Json.lng(Json.map(Json.list(reopened.getUser(UUID).get("user_shop")).getFirst()).get("i_id")));
        }
    }

    @Test void existingUnsortedMongoDocumentsAreNormalizedWithoutReadSideWrites() {
        try(StateStore store=new StateStore(config);var client=MongoClients.create(config.mongoUri)) {
            store.createUser(UUID,DEVICE);
            var collection=client.getDatabase(config.mongoDatabase).getCollection("users");
            var filter=new Document("_id",UUID);
            // Explicitly seed the pre-split format; ordinary reads must not migrate it.
            collection.updateOne(filter,new Document("$set",new Document("contents",Document.parse(Json.stringify(store.exportUser(UUID)))))
                    .append("$unset",new Document("sections","").append("storage_version","")));
            collection.updateOne(filter,new Document("$set",new Document("contents.user_guitar",List.of(
                    new Document("i_id",201).append("i_Level",1),new Document("i_id",10).append("i_Level",1)))));
            Document before=collection.find(filter).first();
            assertEquals(List.of(10L,201L),Json.list(store.getUser(UUID).get("user_guitar")).stream().map(row->Json.lng(Json.map(row).get("i_id"))).toList());
            assertEquals(before,collection.find(filter).first());
        }
    }

    @Test void featureRowsAreSeparatedAndExplicitMigrationPreservesFullAccount() {
        try(var repository=new MongoUserRepository(config);var client=MongoClients.create(config.mongoUri)) {
            var user=repository.createUser(UUID,DEVICE,"203.0.113.8");
            user.put("custom_feature",Json.obj("nested",List.of(1,2,3)));
            repository.saveUser(user);
            var db=client.getDatabase(config.mongoDatabase);
            var account=db.getCollection("users").find(new Document("_id",UUID)).first();
            assertFalse(account.containsKey("contents"));
            assertEquals(2,account.getInteger("storage_version"));
            for(String field:List.of("userdata","user_music","costumes","areas","posts","custom_feature"))
                assertTrue(Json.map(account.get("sections")).containsKey(field));
            assertTrue(db.getCollection("user_music").countDocuments(new Document("uuid",UUID))>=2);
            assertTrue(db.getCollection("user_profiles").countDocuments(new Document("uuid",UUID))>0);
            var before=repository.exportUser(UUID);
            // Simulate the exact old one-document schema, retaining original aliases/balances.
            account.remove("sections");account.remove("storage_version");
            account.put("contents",Document.parse(Json.stringify(before)));
            db.getCollection("users").replaceOne(new Document("_id",UUID),account);
            assertEquals(Json.stringify(before),Json.stringify(repository.exportUser(UUID)));
            assertEquals(account,db.getCollection("users").find(new Document("_id",UUID)).first());
            assertTrue(repository.splitLegacyUser(DEVICE));
            assertFalse(repository.splitLegacyUser(UUID));
            assertEquals(Json.stringify(before),Json.stringify(repository.exportUser(UUID)));
            assertFalse(db.getCollection("users").find(new Document("_id",UUID)).first().containsKey("contents"));
        }
    }

    @Test void unpublishedSectionsStayInvisibleAndMissingPublishedDataFailsClosed() {
        try(var repository=new MongoUserRepository(config);var client=MongoClients.create(config.mongoUri)) {
            repository.createUser(UUID,DEVICE,"");
            var db=client.getDatabase(config.mongoDatabase);
            var storage=new MongoUserSections(db);
            var before=repository.exportUser(UUID);
            var manifest=storage.stage(UUID,new Document("user_music",List.of(new Document("i_id",999))));
            assertEquals(Json.stringify(before),Json.stringify(repository.exportUser(UUID)));
            storage.discard(UUID,manifest);
            assertEquals(Json.stringify(before),Json.stringify(repository.exportUser(UUID)));
            var account=db.getCollection("users").find(new Document("_id",UUID)).first();
            var ref=Json.map(Json.map(account.get("sections")).get("user_music"));
            db.getCollection("user_music").deleteMany(new Document("uuid",UUID).append("snapshot",ref.get("snapshot")));
            assertThrows(IllegalStateException.class,()->repository.exportUser(UUID));
        }
    }

    @Test void migrationCliIsReadOnlyByDefaultBacksUpAndIsIdempotent() throws Exception {
        Path settings=root.resolve("split-config.json");
        Json.write(settings,Json.obj("database",Json.obj("backend","mongo","name",config.mongoDatabase,"uri",config.mongoUri)));
        String[] dry={"--config",settings.toString(),"--dry-run"};
        assertThrows(IllegalStateException.class,()->emu.leman.ggserver.migration.SplitMongoUsers.main(dry));
        try(var repository=new MongoUserRepository(config);var client=MongoClients.create(config.mongoUri)) {
            repository.createUser(UUID,DEVICE,"");
            var users=client.getDatabase(config.mongoDatabase).getCollection("users");
            var account=users.find(new Document("_id",UUID)).first();
            account.put("contents",Document.parse(Json.stringify(repository.exportUser(UUID))));
            account.remove("sections");account.remove("storage_version");
            users.replaceOne(new Document("_id",UUID),account);
            var before=repository.exportUser(UUID);
            emu.leman.ggserver.migration.SplitMongoUsers.main(dry);
            assertEquals(account,users.find(new Document("_id",UUID)).first());
            assertThrows(IllegalArgumentException.class,()->emu.leman.ggserver.migration.SplitMongoUsers.main(new String[]{"--config",settings.toString(),"--apply"}));
            Path backup=root.resolve("backup");
            String[] apply={"--config",settings.toString(),"--apply","--writers-stopped","--backup",backup.toString()};
            emu.leman.ggserver.migration.SplitMongoUsers.main(apply);
            assertEquals(account,Document.parse(Files.readAllLines(backup.resolve("users.bson.jsonl")).getFirst()));
            assertEquals(Json.stringify(before),Json.stringify(repository.exportUser(UUID)));
            assertFalse(users.find(new Document("_id",UUID)).first().containsKey("contents"));
            assertThrows(FileAlreadyExistsException.class,()->emu.leman.ggserver.migration.SplitMongoUsers.main(apply));
            emu.leman.ggserver.migration.SplitMongoUsers.main(new String[]{"--config",settings.toString(),"--apply","--writers-stopped","--backup",root.resolve("backup2").toString()});
            assertEquals(0,Json.integer(Json.map(Json.read(root.resolve("backup2/report.json"))).get("migrated")));
        }
    }

    @Test void concurrentCreationHasStableDeviceAndUniqueDurableSequences() throws Exception {
        try (StateStore first = new StateStore(config); StateStore second = new StateStore(config);
             ExecutorService executor = Executors.newFixedThreadPool(8)) {
            List<Future<String>> repeated = new ArrayList<>();
            for (int i = 0; i < 32; i++) {
                int index = i;
                repeated.add(executor.submit(() -> Json.str((index % 2 == 0 ? first : second).createUser("install-" + index, DEVICE).get("uuid"))));
            }
            Set<String> canonical = new HashSet<>();
            for (Future<String> result : repeated) canonical.add(result.get());
            assertEquals(1, canonical.size());
            List<Future<Long>> unique = new ArrayList<>();
            for (int i = 0; i < 32; i++) {
                int index = i;
                unique.add(executor.submit(() -> Json.lng(ud((index % 2 == 0 ? first : second).createUser("account-" + index, "device-" + index)).get("u_seq"))));
            }
            Set<Long> sequences = new HashSet<>();
            for (Future<Long> result : unique) assertTrue(sequences.add(result.get()));
            assertEquals(33, first.listUserRows().size());
        }
        try (StateStore store = new StateStore(config)) {
            long max = store.listUserRows().stream().mapToLong(row -> Json.lng(row.get("u_seq"))).max().orElseThrow();
            assertTrue(Json.lng(ud(store.createUser("next", "next-device")).get("u_seq")) > max);
        }
    }

    @Test void atomicSpendingAndCompoundIncrementsAcrossClientsNeverLoseUpdates() throws Exception {
        try (StateStore first = new StateStore(config); StateStore second = new StateStore(config);
             ExecutorService executor = Executors.newFixedThreadPool(8)) {
            first.createUser(UUID, DEVICE);
            first.setCurrency(UUID, 50, 10.5);
            AtomicInteger successes = new AtomicInteger();
            List<Future<?>> jobs = new ArrayList<>();
            for (int i = 0; i < 100; i++) {
                StateStore store = i % 2 == 0 ? first : second;
                jobs.add(executor.submit(() -> { if (store.spendCurrency(DEVICE, "cp", 1L)) successes.incrementAndGet(); }));
            }
            for (Future<?> job : jobs) job.get();
            assertEquals(50, successes.get());
            assertEquals(0, Json.lng(ud(first.getUser(UUID)).get("u_cp")));
            assertTrue(second.spendCurrency(DEVICE, "candy", 10.25));
            assertFalse(first.spendCurrency(UUID, "candy", 1));
            assertFalse(first.spendCurrency(UUID, "candy", Double.NaN));
            first.setCurrency(UUID, 9007199254740994L, 0);
            assertTrue(second.spendCurrency(UUID, "cp", 9007199254740993L));
            assertEquals(1, Json.lng(ud(first.getUser(UUID)).get("u_cp")));
            String exact = "123456789012345678901234567890123456789";
            first.setLikeCurrency(UUID, exact);
            jobs.clear();
            for (int i = 0; i < 40; i++) {
                StateStore store = i % 2 == 0 ? first : second;
                jobs.add(executor.submit(() -> store.incrementCurrency(DEVICE, 1, 0.5, "1", 1)));
            }
            for (Future<?> job : jobs) job.get();
            Map<String,Object> user = first.getUser(UUID);
            assertEquals(41, Json.lng(ud(user).get("u_cp")));
            assertEquals(20, Json.dbl(ud(user).get("u_candy")));
            assertGp(user, new BigInteger(exact).add(BigInteger.valueOf(40)).toString());
        }
    }

    @Test void explicitImportExportRoundTripsBothBackendsAndRejectsCollisionsAtomically() {
        try (StateStore sqlite = new StateStore(root); StateStore mongo = new StateStore(config)) {
            sqlite.createUser(UUID, DEVICE, "203.0.113.8");
            sqlite.setCurrency(UUID, 123, 1.25);
            sqlite.setLikeCurrency(UUID, "987654321098765432109876543210");
            sqlite.updateAttendance(UUID, 17, 20261111);
            sqlite.banUser(UUID);
            sqlite.updateUserIp(UUID, "", "example.org");
            Map<String,Object> exported = sqlite.exportUser(DEVICE);
            mongo.importUser(exported);
            Map<String,Object> copied = mongo.exportUser(UUID);
            assertEquals(Json.parse(Json.stringify(exported)), Json.parse(Json.stringify(copied)));
            assertEquals("example.org", copied.get("last_domain"));
            assertTrue(mongo.isUserBanned(DEVICE));
            Map<String,Object> changed = mongo.getUser(UUID);
            changed.put("custom_big_integer", new BigInteger("1234567890123456789012345678901234567890"));
            mongo.saveUser(changed);
            assertEquals("1234567890123456789012345678901234567890", mongo.getUser(UUID).get("custom_big_integer"));
            assertThrows(IllegalArgumentException.class, () -> sqlite.importUser(mongo.exportUser(UUID)));
            assertGp(sqlite.getUser(UUID), "987654321098765432109876543210");
            Map<String,Object> collision = Json.copy(exported);
            collision.put("uuid", "another-canonical");
            assertThrows(IllegalArgumentException.class, () -> mongo.importUser(collision));
            assertEquals(1, mongo.listUserRows().size());
            assertEquals(UUID, mongo.getUser(DEVICE).get("uuid"));
            assertThrows(IllegalArgumentException.class, () -> sqlite.importUser(collision));
            assertEquals(1, sqlite.listUserRows().size());
        }
    }

    @Test void exactHugeLikesLegacyFlagsFailedSaveCleanupAndDelete() {
        try (StateStore store = new StateStore(config)) {
            Map<String,Object> user = store.createUser(UUID, DEVICE);
            user.put("force_server_like", true);
            ud(user).put("u_like", 10.0);
            for (Object area : Json.map(user.get("areas")).values()) Json.map(area).put("s_Gp1", "9999");
            store.saveUser(user);
            assertGp(store.getUser(UUID), "10");
            store.incrementCurrency(UUID, 0, 0, "5", 0);
            assertGp(store.getUser(UUID), "15");
            assertEquals(true, store.getUser(UUID).get("force_server_like"));
            store.setLikeCurrency(UUID, "1e999");
            assertGp(store.getUser(UUID), Currency.MAX_DECIMAL.toBigInteger().toString());
            store.setLikeCurrency(UUID, 0);
            assertGp(store.getUser(UUID), "0");
            user = store.getUser(UUID);
            user.put("costumes", List.of(Json.obj("i_id", 999, "invalid", new Object())));
            Map<String,Object> invalid = user;
            assertThrows(IllegalArgumentException.class, () -> store.saveUser(invalid));
            assertEquals(2, Json.list(store.getUser(UUID).get("costumes")).size());
            store.createUser("test-user", "test-device");
            assertEquals(1, store.cleanupTestUsers());
            assertTrue(store.deleteUser(null, 100001L));
            assertNull(store.getUser(DEVICE));
            assertTrue(store.listUserRows().isEmpty());
            try (var client = MongoClients.create(config.mongoUri)) {
                Document document = client.getDatabase(config.mongoDatabase).getCollection("counters").find().first();
                assertNotNull(document);
            }
        }
    }
    private static void assertGp(Map<String,Object> user, String expected) {
        for (Object value : Json.map(user.get("areas")).values()) assertEquals(expected, Json.map(value).get("s_Gp1"));
        assertTrue(Double.isFinite(Json.dbl(ud(user).get("u_like"))));
    }
}

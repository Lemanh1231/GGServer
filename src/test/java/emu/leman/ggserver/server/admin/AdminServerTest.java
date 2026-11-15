package emu.leman.ggserver.server.admin;

import com.sun.net.httpserver.HttpServer;
import emu.leman.ggserver.Services;
import java.net.*;
import java.net.http.*;
import java.nio.file.*;
import java.time.Duration;
import java.util.*;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
import static emu.leman.ggserver.util.Json.*;

class AdminServerTest {
    @TempDir Path root;
    Services services;
    HttpServer server;
    URI base;
    String token;
    final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
    @BeforeEach void setup() throws Exception {
        write(root.resolve("gamedata/game_data.json"),obj("20",List.of(obj("1",10,"37",1))));
        write(root.resolve("event_config.json"),emu.leman.ggserver.game.content.EventManager.defaults());
        services = new Services(root);
        token = new AdminAuth(root).createToken(3600);
        var admin = new AdminServer(services);
        server = HttpServer.create(new InetSocketAddress(InetAddress.getLoopbackAddress(), 0), 0);
        server.createContext("/", exchange -> {
            if (!admin.handle(exchange)) { exchange.sendResponseHeaders(418, -1); exchange.close(); }
        });
        server.start();
        base = URI.create("http://localhost:" + server.getAddress().getPort());
    }
    @AfterEach void close() { server.stop(0); services.close(); }
    HttpResponse<String> call(String path, String method, Object body, boolean authenticated) throws Exception {
        var request = HttpRequest.newBuilder(base.resolve(path)).timeout(Duration.ofSeconds(10));
        if (authenticated) request.header("Authorization", "Bearer " + token);
        request.method(method, body == null ? HttpRequest.BodyPublishers.noBody() : HttpRequest.BodyPublishers.ofString(stringify(body)));
        return client.send(request.build(), HttpResponse.BodyHandlers.ofString());
    }
    Map<String,Object> json(HttpResponse<String> response) { return map(parse(response.body())); }
    @Test void routingAndSecurity() throws Exception {
        assertEquals(418, call("/administrator", "GET", null, false).statusCode());
        var login = call("/admin", "GET", null, false);
        assertEquals(200, login.statusCode());
        assertTrue(login.body().contains("/admin/api/login"));
        assertEquals(401, call("/admin/api/users", "GET", null, false).statusCode());
        assertEquals(401, call("/admin/api/login", "POST", obj("password", "definitely-not-the-password"), false).statusCode());
        assertEquals(404, call("/admin/api/not-implemented", "GET", null, true).statusCode());
        assertEquals(404, call("/admin/api/not-implemented", "POST", obj(), true).statusCode());
        assertEquals(405, call("/admin/api/users", "DELETE", null, true).statusCode());
        var dashboard = call("/admin", "GET", null, true);
        assertTrue(dashboard.body().contains("attendance_events_custom"));
        assertTrue(dashboard.body().contains("Tiếng Việt"));
        var cookie = HttpRequest.newBuilder(base.resolve("/admin/api/events")).header("Cookie", "unrelated=1; gg_admin_token=" + token).GET().build();
        assertEquals(200, client.send(cookie, HttpResponse.BodyHandlers.ofString()).statusCode());
        var logout = call("/admin/api/logout", "POST", obj(), false);
        assertTrue(logout.headers().firstValue("Set-Cookie").orElseThrow().contains("Max-Age=0"));
    }
    @Test void signedTokensAndPasswordCompatibility() throws Exception {
        var auth = new AdminAuth(root, "password", "shared-secret");
        String signed = auth.createToken(60);
        assertTrue(auth.verifyToken(signed));
        assertTrue(auth.verifyToken("password"));
        assertFalse(auth.verifyToken(signed + "0"));
        assertFalse(auth.verifyToken(auth.createToken(-1)));
        assertFalse(auth.verifyToken("not.a.valid.token"));
        assertTrue(new AdminAuth(root, "password", "shared-secret").verifyToken(signed));
        assertFalse(new AdminAuth(root, "password", "other-secret").verifyToken(signed));
        Path otherRoot = root.resolve("generated-key");
        String generated = new AdminAuth(otherRoot, "password", null).createToken(60);
        assertTrue(new AdminAuth(otherRoot, "password", null).verifyToken(generated));
    }
    @Test void settingsCurrenciesInventoryBansAndDeletes() throws Exception {
        var user = services.state.createUser("admin-test-user", "admin-test-device");
        long oldCp = lng(map(user.get("userdata")).get("u_cp"));
        var response = call("/admin/api/user/event_settings", "POST", obj("uuid", "admin-test-user", "is_gold", true,
                "star_point", 12000, "unlock_ch2", true, "add_cp", 125, "add_candy", 2.5, "set_like", "1.5A",
                "attendance_day", 7, "attendance_mode", "complete", "send_mail", true), true);
        assertEquals(200, response.statusCode(), response.body());
        user = services.state.getUser("admin-test-user");
        assertEquals(oldCp + 125, lng(map(user.get("userdata")).get("u_cp")));
        assertEquals(1500, dbl(map(user.get("userdata")).get("u_like")));
        assertEquals(7, integer(map(map(user.get("attendance")).get("1")).get("day")));
        assertTrue(truth(user.get("needs_client_reset")));
        assertTrue(list(user.get("user_ticketcollection")).stream().anyMatch(v -> integer(map(v).get("i_id")) == 1013));
        assertEquals(1, list(user.get("posts")).size());
        assertTrue(list(map(list(user.get("posts")).getFirst()).get("item_list")).stream().allMatch(i -> truth(map(i).get("already_granted"))));
        var users = call("/admin/api/users", "GET", null, true);
        assertEquals(200, users.statusCode(), users.body());
        assertTrue(truth(map(list(json(users).get("users")).getFirst()).get("ch2_unlocked")));
        long seq = lng(map(user.get("userdata")).get("u_seq"));
        assertEquals(200, call("/admin/api/user/ban", "POST", obj("u_seq", seq), true).statusCode());
        assertTrue(services.state.isUserBanned("admin-test-user"));
        assertEquals(200, call("/admin/api/user/ban", "POST", obj("uuid", "admin-test-user", "banned", false), true).statusCode());
        assertFalse(services.state.isUserBanned("admin-test-user"));
        assertEquals(200, call("/admin/api/user/delete", "POST", obj("u_seq", seq), true).statusCode());
        assertNull(services.state.getUser("admin-test-user"));
        assertEquals(400, call("/admin/api/user/delete", "POST", obj("uuid", "missing"), true).statusCode());
    }
    @Test void eventSaveAndMailBroadcasts() throws Exception {
        services.state.createUser("first", "device-first");
        services.state.createUser("second", "device-second");
        var cfg = services.events.snapshot();
        map(cfg.get("star_pass")).put("active_season", 5);
        cfg.put("notify_in_game", true);
        assertEquals(200, call("/admin/api/events", "POST", cfg, true).statusCode());
        assertEquals(5, services.events.activeStarPassSeason());
        assertEquals(1, list(services.state.getUser("first").get("posts")).size());
        var response = call("/admin/api/send_post", "POST", obj("uuid", "all", "title", "Gift", "memo", "A gift", "cp", 10, "candy", 1.5, "cookies", 2), true);
        assertEquals(200, response.statusCode(), response.body());
        var post = map(json(response).get("post"));
        assertEquals(3, list(post.get("item_list")).size());
        assertEquals("Gift", post.get("title_en"));
        assertEquals(2, list(services.state.getUser("first").get("posts")).size());
        assertEquals(2, list(services.state.getUser("second").get("posts")).size());
        long id = lng(post.get("idx"));
        response = call("/admin/api/send_post", "POST", obj("uuid", "first", "title", "Personal"), true);
        assertTrue(lng(map(json(response).get("post")).get("idx")) > id);
        assertEquals(3, list(services.state.getUser("first").get("posts")).size());
        assertEquals(2, list(services.state.getUser("second").get("posts")).size());
        assertEquals(400, call("/admin/api/send_post", "POST", obj("uuid", "absent"), true).statusCode());
    }
    @Test void cleanupIsExplicitAndAuthenticated() throws Exception {
        services.state.createUser("test-cleanup-user", "test-cleanup-device");
        new AdminServer(services);
        assertNotNull(services.state.getUser("test-cleanup-user"));
        assertEquals(401, call("/admin/api/users/cleanup_tests", "POST", obj(), false).statusCode());
        assertNotNull(services.state.getUser("test-cleanup-user"));
        var cleanup = call("/admin/api/users/cleanup_tests", "POST", obj(), true);
        assertEquals(200, cleanup.statusCode(), cleanup.body());
        assertNull(services.state.getUser("test-cleanup-user"));
    }
    @Test void explicitCliItemsArePreservedAndValidated() throws Exception {
        services.state.createUser("cli-recipient", "cli-device");
        var items = List.of(obj("i_RewardType", 1, "i_RewardId", 3, "d_RewardQuantity", 1234.5),
                obj("i_RewardType", 9, "i_RewardId", 10, "d_RewardQuantity", 1.0));
        var response = call("/admin/api/send_post", "POST", obj("uuid", "cli-recipient", "title", "CLI gift", "memo", "Gift", "items", items), true);
        assertEquals(200, response.statusCode(), response.body());
        var sent = map(json(response).get("post"));
        assertEquals(items, list(sent.get("item_list")));
        assertEquals(2, list(map(list(services.state.getUser("cli-recipient").get("posts")).getFirst()).get("item_list")).size());
        assertEquals(400, call("/admin/api/send_post", "POST", obj("uuid", "cli-recipient", "items", List.of(obj("i_RewardType", 99, "i_RewardId", 1, "d_RewardQuantity", 1))), true).statusCode());
        assertEquals(1, list(services.state.getUser("cli-recipient").get("posts")).size());
    }
    @Test void capturedAttendanceRewardsGrantInventoryAndCompleteBoard() throws Exception {
        Files.createDirectories(root.resolve("gamedata"));
        Files.createDirectories(root.resolve("schema"));
        Files.copy(Path.of("resources/gamedata/getEventRewardList.b64"), root.resolve("gamedata/getEventRewardList.b64"));
        Files.copy(Path.of("resources/schema/schema.json"), root.resolve("schema/schema.json"));
        var before = services.state.createUser("reward-recipient", "reward-device");
        long cp = lng(map(before.get("userdata")).get("u_cp"));
        var response = call("/admin/api/user/event_settings", "POST", obj("uuid", "reward-recipient", "grant_7d_rewards", true), true);
        assertEquals(200, response.statusCode(), response.body());
        var after = services.state.getUser("reward-recipient");
        assertEquals(7, integer(map(map(after.get("attendance")).get("1")).get("day")));
        assertTrue(lng(map(after.get("userdata")).get("u_cp")) > cp);
        assertFalse(list(after.get("costumes")).isEmpty());
    }
    @Test void broadcastWaitsForAccountMutationAndPreservesBothChanges() throws Exception {
        services.state.createUser("concurrent-user", "concurrent-device");
        var entered = new java.util.concurrent.CountDownLatch(1);
        var release = new java.util.concurrent.CountDownLatch(1);
        var broadcastStarted = new java.util.concurrent.CountDownLatch(1);
        try (var executor = java.util.concurrent.Executors.newFixedThreadPool(2)) {
            var account = executor.submit(() -> services.registry.withAccountLock("concurrent-user", () -> {
                var user = services.state.getUser("concurrent-user");
                entered.countDown();
                try { assertTrue(release.await(5, java.util.concurrent.TimeUnit.SECONDS)); }
                catch (InterruptedException e) { throw new RuntimeException(e); }
                map(user.get("userdata")).put("u_nick", "Concurrent update");
                services.state.saveUser(user);
                return null;
            }));
            assertTrue(entered.await(5, java.util.concurrent.TimeUnit.SECONDS));
            var broadcast = executor.submit(() -> {
                broadcastStarted.countDown();
                return new AdminPosts(services).send(null, "Concurrent broadcast", "memo", new ArrayList<>());
            });
            try {
                assertTrue(broadcastStarted.await(5, java.util.concurrent.TimeUnit.SECONDS));
                assertThrows(java.util.concurrent.TimeoutException.class,
                        () -> broadcast.get(100, java.util.concurrent.TimeUnit.MILLISECONDS),
                        "Broadcast must not finish while an account operation owns the shared registry gate");
            }
            finally { release.countDown(); }
            account.get(5, java.util.concurrent.TimeUnit.SECONDS);
            broadcast.get(5, java.util.concurrent.TimeUnit.SECONDS);
        }
        var user = services.state.getUser("concurrent-user");
        assertEquals("Concurrent update", map(user.get("userdata")).get("u_nick"));
        assertEquals(1, list(user.get("posts")).size());
    }
    @Test void customAttendanceAndMissingRewardDataAreNotSilentSuccess() throws Exception {
        services.state.createUser("attendance-user", "attendance-device");
        var request = obj("uuid", "attendance-user", "attendance_events_custom", obj("1", obj("modified", true, "target_day", 4, "unlock_today", true)));
        assertEquals(200, call("/admin/api/user/event_settings", "POST", request, true).statusCode());
        assertEquals(3, integer(map(map(services.state.getUser("attendance-user").get("attendance")).get("1")).get("day")));
        request.put("grant_7d_rewards", true); request.remove("attendance_events_custom");
        assertEquals(400, call("/admin/api/user/event_settings", "POST", request, true).statusCode());
        assertEquals(3, integer(map(map(services.state.getUser("attendance-user").get("attendance")).get("1")).get("day")));
    }
}

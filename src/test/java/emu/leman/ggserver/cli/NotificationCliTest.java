package emu.leman.ggserver.cli;

import com.sun.net.httpserver.HttpServer;
import emu.leman.ggserver.util.Json;
import org.junit.jupiter.api.Test;
import java.io.*;
import java.net.InetSocketAddress;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class NotificationCliTest {
    private final ByteArrayOutputStream output = new ByteArrayOutputStream();
    private final ByteArrayOutputStream errors = new ByteArrayOutputStream();
    private int run(Map<String,String> env, String... args) {
        return NotificationCli.run(args, env, new PrintStream(output), new PrintStream(errors));
    }

    @Test void sendsEveryRewardThroughLiveServerWithAuthentication() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        AtomicReference<Map<String,Object>> received = new AtomicReference<>();
        AtomicReference<String> authorization = new AtomicReference<>();
        server.createContext("/admin/api/send_post", exchange -> {
            received.set(map(Json.parse(new String(exchange.getRequestBody().readAllBytes(), java.nio.charset.StandardCharsets.UTF_8))));
            authorization.set(exchange.getRequestHeaders().getFirst("Authorization"));
            byte[] response = Json.bytes(obj("success", true, "post", obj("idx", 101, "item_list", received.get().get("items"))));
            exchange.sendResponseHeaders(200, response.length);
            exchange.getResponseBody().write(response);
            exchange.close();
        });
        server.start();
        try {
            Map<String,String> env = Map.of("GG_ADMIN_URL", "http://127.0.0.1:" + server.getAddress().getPort(), "GG_ADMIN_PASSWORD", "test-secret", "GG_NO_ADB", "1");
            assertEquals(0, run(env, "--uuid", "player", "--title", "Tiêu đề", "--memo", "Text", "--cp", "12", "--candy", "1.5", "--like", "2.5",
                "--cookies", "3", "--guitar", "4", "--costume", "5", "--music", "6"), errors.toString());
            assertEquals("Bearer test-secret", authorization.get());
            assertEquals("player", received.get().get("uuid"));
            assertEquals("Tiêu đề", received.get().get("title"));
            List<Object> items = list(received.get().get("items"));
            assertEquals(7, items.size());
            int[] types = {1, 1, 1, 1, 9, 3, 2}, ids = {1, 2, 3, 11, 4, 5, 6};
            double[] quantities = {12, 1.5, 2.5, 3, 1, 1, 1};
            for (int i = 0; i < items.size(); i++) {
                assertEquals(types[i], integer(map(items.get(i)).get("i_RewardType")));
                assertEquals(ids[i], integer(map(items.get(i)).get("i_RewardId")));
                assertEquals(quantities[i], dbl(map(items.get(i)).get("d_RewardQuantity")));
            }
            assertTrue(output.toString().contains("#101"));
            assertEquals(0, EventCli.run(new String[]{"sendmail", "Title", "Memo", "5", "6.5", "7"}, env, new PrintStream(output), new PrintStream(errors)));
            assertEquals("all", received.get().get("uuid"));
            assertEquals(3, list(received.get().get("items")).size());
        } finally { server.stop(0); }
    }

    @Test void errorsDoNotClaimDelivery() throws Exception {
        assertEquals(1, run(Map.of(), "--candy", "NaN"));
        assertEquals(1, run(Map.of(), "--candy", "Infinity"));
        assertEquals(1, run(Map.of(), "--cp", "-1"));
        assertEquals(1, run(Map.of(), "--cp", "1.5"));
        assertEquals(1, run(Map.of(), "--guitar", "999999999999"));
        assertEquals(1, run(Map.of(), "--unknown", "value"));
        assertEquals(1, run(Map.of(), "--memo"));
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/admin/api/send_post", exchange -> {
            byte[] body = Json.bytes(obj("success", false, "error", "Unknown user"));
            exchange.sendResponseHeaders(400, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        server.start();
        try {
            assertEquals(1, run(Map.of("GG_ADMIN_URL", "http://127.0.0.1:" + server.getAddress().getPort(), "GG_NO_ADB", "1"), "--uuid", "missing"));
            assertTrue(errors.toString().contains("Unknown user"));
            assertFalse(output.toString().contains("SUCCESS"));
        } finally { server.stop(0); }
    }

    @Test void helpAndOriginalAndroidActivity() {
        assertEquals(0, run(Map.of(), "--help"));
        assertEquals("com.neowiz.game.guitargirl/com.google.firebase.MessagingUnityPlayerActivity", CliSupport.GAME_ACTIVITY);
    }

    @Test void doesNotSilentlyAcceptDroppedRewards() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/admin/api/send_post", exchange -> {
            byte[] body = Json.bytes(obj("success", true, "post", obj("idx", 123, "item_list", List.of())));
            exchange.sendResponseHeaders(200, body.length);
            exchange.getResponseBody().write(body);
            exchange.close();
        });
        server.start();
        try {
            assertEquals(1, run(Map.of("GG_ADMIN_URL", "http://127.0.0.1:" + server.getAddress().getPort(), "GG_NO_ADB", "1"), "--cp", "10"));
            assertTrue(errors.toString().contains("did not preserve requested rewards"));
            assertFalse(output.toString().contains("SUCCESS"));
        } finally { server.stop(0); }
    }
}

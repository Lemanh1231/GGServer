package emu.leman.ggserver.cli;

import emu.leman.ggserver.util.Json;
import java.io.PrintStream;
import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.util.*;

/** Sends through the running server, preserving its cache consistency and live SSE delivery. */
public final class NotificationCli {
    private NotificationCli() {}
    public static void main(String[] args) {
        System.exit(run(args, System.getenv(), System.out, System.err));
    }

    public static int run(String[] args, Map<String,String> env, PrintStream out, PrintStream err) {
        try {
            Map<String,String> options = parse(args);
            if (options.containsKey("help")) { help(out); return 0; }
            List<Object> items = new ArrayList<>();
            reward(items, 1, 1, CliSupport.quantity(options.getOrDefault("cp", "0"), true));
            reward(items, 1, 2, CliSupport.quantity(options.getOrDefault("candy", "0"), false));
            reward(items, 1, 3, CliSupport.quantity(options.getOrDefault("like", "0"), false));
            reward(items, 1, 11, CliSupport.quantity(options.getOrDefault("cookie", "0"), true));
            for (String name : List.of("guitar", "costume", "music")) {
                double id = CliSupport.quantity(options.getOrDefault(name, "0"), true);
                if (id > Integer.MAX_VALUE) throw new IllegalArgumentException("Item ID out of range: " + name);
                if (id > 0) reward(items, name.equals("guitar") ? 9 : name.equals("costume") ? 3 : 2, (int)id, 1);
            }
            String target = options.getOrDefault("uuid", "all");
            Map<String,Object> request = Json.obj("uuid", target,
                "title", options.getOrDefault("title", "Thông báo từ Ban Quản Trị"),
                "memo", options.getOrDefault("memo", "Cảm ơn bạn đã đồng hành cùng Guitar Girl!"), "items", items);
            Map<String,Object> post = send(request, options.get("server"), env);
            out.println("[SUCCESS] Sent notification #" + post.get("idx") + " to " + target);
            out.println("Title: " + request.get("title"));
            out.println("Memo:  " + request.get("memo"));
            out.println("Attached rewards: " + items.size());
            for (Object item : items) out.println("  " + Json.stringify(item));
            CliSupport.softResume(env, out);
            return 0;
        } catch (Exception e) { return CliSupport.error(err, e); }
    }

    static Map<String,Object> send(Map<String,Object> request, String server, Map<String,String> env) throws Exception {
        String base = server != null ? server : CliSupport.adminUrl(env);
        URI uri = URI.create(base.replaceAll("/+$", "") + "/admin/api/send_post");
        if (!("http".equals(uri.getScheme()) || "https".equals(uri.getScheme())) || uri.getHost() == null || uri.getUserInfo() != null)
            throw new IllegalArgumentException("Invalid server URL");
        HttpRequest httpRequest = HttpRequest.newBuilder(uri).timeout(Duration.ofSeconds(20))
            .header("Content-Type", "application/json; charset=utf-8")
            .header("Authorization", "Bearer " + env.getOrDefault("GG_ADMIN_PASSWORD", "admin123"))
            .POST(HttpRequest.BodyPublishers.ofByteArray(Json.bytes(request))).build();
        HttpResponse<String> response;
        try (HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build()) {
            response = client.send(httpRequest, HttpResponse.BodyHandlers.ofString());
        } catch (java.io.IOException e) {
            throw new IllegalStateException("Cannot reach running Java server at " + base + "; start it with ./serverctl.sh start. No mail was written offline.", e);
        }
        Map<String,Object> body;
        try { body = Json.map(Json.parse(response.body())); }
        catch (Exception e) { throw new IllegalStateException("Server returned HTTP " + response.statusCode() + " (not JSON)"); }
        if (response.statusCode() / 100 != 2 || Boolean.FALSE.equals(body.get("success")))
            throw new IllegalStateException("Server HTTP " + response.statusCode() + ": " + Json.str(body.getOrDefault("error", "Notification rejected")));
        Map<String,Object> post = Json.map(body.getOrDefault("post", body));
        if (!post.containsKey("idx")) throw new IllegalStateException("Server response did not contain a post ID");
        if (!Json.list(request.get("items")).isEmpty() && !Json.MAPPER.valueToTree(request.get("items")).equals(Json.MAPPER.valueToTree(post.get("item_list"))))
            throw new IllegalStateException("Server created post #" + post.get("idx") + " but did not preserve requested rewards. Check server support for items; do not retry blindly.");
        return post;
    }

    static void reward(List<Object> items, int type, int id, double quantity) {
        if (quantity > 0) items.add(Json.obj("i_RewardType", type, "i_RewardId", id, "d_RewardQuantity", quantity));
    }

    private static Map<String,String> parse(String[] args) {
        Set<String> allowed = Set.of("uuid", "title", "memo", "cp", "candy", "like", "cookie", "guitar", "costume", "music", "server");
        Map<String,String> options = new LinkedHashMap<>();
        for (int i = 0; i < args.length; i++) {
            String arg = args[i];
            if (List.of("-h", "--help", "help").contains(arg)) { options.put("help", ""); continue; }
            if (!arg.startsWith("--")) throw new IllegalArgumentException("Unexpected argument: " + arg);
            String[] pair = arg.substring(2).split("=", 2);
            String name = pair[0].equals("cookies") ? "cookie" : pair[0];
            if (!allowed.contains(name)) throw new IllegalArgumentException("Unknown option: " + arg);
            String value;
            if (pair.length == 2) value = pair[1];
            else if (++i < args.length && !args[i].startsWith("--")) value = args[i];
            else throw new IllegalArgumentException("Missing value: " + arg);
            options.put(name, value);
        }
        return options;
    }

    private static void help(PrintStream out) {
        out.println("Usage: ./send-notification.sh [--uuid all|UUID] [--title TEXT] [--memo TEXT]");
        out.println("  [--cp N] [--candy N] [--like N] [--cookie N] [--guitar ID] [--costume ID] [--music ID]");
        out.println("  [--server URL] (default GG_ADMIN_URL or http://127.0.0.1:$PORT)");
        out.println("Requires the running Java server; authentication: GG_ADMIN_PASSWORD. Set GG_NO_ADB=1 to skip optional ADB resume.");
    }
}

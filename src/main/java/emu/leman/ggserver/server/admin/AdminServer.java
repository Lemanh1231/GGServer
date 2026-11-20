package emu.leman.ggserver.server.admin;

import com.sun.net.httpserver.HttpExchange;
import emu.leman.ggserver.Services;
import emu.leman.ggserver.game.economy.Currency;
import emu.leman.ggserver.database.StateStore;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Native management HTTP boundary. Unrelated paths are never consumed. */
public final class AdminServer {
    private static final long TOKEN_TTL = 2592000;
    private final Services services;
    private final AdminAuth auth;
    private final AdminData data;
    private final AdminPosts posts;
    private final AdminSettings settings;
    public AdminServer(Services services) {
        this.services = services;
        auth = new AdminAuth(services.config);
        data = new AdminData(services);
        posts = new AdminPosts(services);
        settings = new AdminSettings(services, data, posts);
    }
    public boolean handle(HttpExchange exchange) throws IOException {
        String path = exchange.getRequestURI().getPath(), method = exchange.getRequestMethod();
        if (!path.equals("/admin") && !path.startsWith("/admin/")) return false;
        try {
            if (method.equals("OPTIONS")) {
                exchange.getResponseHeaders().set("Access-Control-Allow-Methods", "GET, POST, OPTIONS, HEAD");
                exchange.getResponseHeaders().set("Access-Control-Allow-Headers", "*");
                respond(exchange, 200, obj());
                return true;
            }
            if ((method.equals("GET") || method.equals("HEAD")) && (path.equals("/admin") || path.equals("/admin/"))) {
                send(exchange, 200, "text/html; charset=utf-8", html(auth.authenticated(exchange.getRequestHeaders()) ? "dashboard.html" : "login.html"));
                return true;
            }
            if (method.equals("POST") && path.equals("/admin/api/login")) {
                Map<String,Object> request = request(exchange);
                if (!auth.checkPassword(str(request.get("password")).strip())) {
                    respond(exchange, 401, obj("success", false, "error", "Mật khẩu quản trị không chính xác!"));
                } else {
                    String token = auth.createToken(TOKEN_TTL);
                    exchange.getResponseHeaders().add("Set-Cookie", "gg_admin_token=" + token + "; Path=/; Max-Age=" + TOKEN_TTL + "; HttpOnly; SameSite=Lax");
                    respond(exchange, 200, obj("success", true, "token", token, "message", "Đăng nhập thành công!"));
                }
                return true;
            }
            if (method.equals("POST") && (path.equals("/admin/api/logout") || path.equals("/admin/logout"))) {
                exchange.getResponseHeaders().add("Set-Cookie", "gg_admin_token=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0; HttpOnly; SameSite=Lax");
                respond(exchange, 200, obj("success", true, "message", "Đã đăng xuất thành công!"));
                return true;
            }
            if (!auth.authenticated(exchange.getRequestHeaders())) {
                respond(exchange, 401, obj("success", false, "error", "Unauthorized. Vui lòng đăng nhập lại!"));
                return true;
            }
            if (method.equals("GET") || method.equals("HEAD")) {
                switch (path) {
                    case "/admin/api/events" -> respond(exchange, 200, obj("success", true, "config", services.events.snapshot(), "seasons", seasons()));
                    case "/admin/api/users" -> respond(exchange, 200, obj("success", true, "users", users(), "active_season", services.events.activeStarPassSeason()));
                    case "/admin/api/status" -> respond(exchange, 200, status());
                    default -> respond(exchange, 404, obj("success", false, "error", "Unknown admin route: " + path));
                }
            } else if (method.equals("POST")) {
                {
                    Map<String,Object> response;
                    switch (path) {
                        case "/admin/api/events" -> {
                            Map<String,Object> req = request(exchange);
                            Map<String,Object> config = services.events.save(req, false);
                            if (truth(req.getOrDefault("notify_in_game", true))) notifyEvents(config);
                            response = obj("success", true, "config", config, "message", "Cập nhật sự kiện thành công!");
                        }
                        case "/admin/api/send_post" -> {
                            Map<String,Object> req = request(exchange);
                            String target = str(first(req.get("uuid"), req.get("target"), "")).strip();
                            if (List.of("", "null", "None", "all").contains(target)) target = null;
                            List<Object> items = new ArrayList<>();
                            if (req.containsKey("items")) {
                                if (!(req.get("items") instanceof List<?>)) throw new IllegalArgumentException("items must be a JSON array");
                                if (list(req.get("items")).size() > 100) throw new IllegalArgumentException("At most 100 reward items are allowed");
                                for (Object raw : list(req.get("items"))) {
                                    if (!(raw instanceof Map)) throw new IllegalArgumentException("Each reward item must be an object");
                                    var item = map(raw);
                                    int type = Math.toIntExact(AdminSettings.whole(item.get("i_RewardType")));
                                    int id = Math.toIntExact(AdminSettings.whole(item.get("i_RewardId")));
                                    double quantity = number(item.get("d_RewardQuantity"));
                                    if (!List.of(1, 2, 3, 4, 5, 7, 9, 11).contains(type) || id <= 0 || quantity <= 0)
                                        throw new IllegalArgumentException("Unsupported reward type/ID or nonpositive quantity");
                                    if (type == 1 && !List.of(1, 2, 3, 4, 8, 11).contains(id))
                                        throw new IllegalArgumentException("Unsupported goods reward ID: " + id);
                                    // Type 11 means goods in mailbox rewards (the existing native protocol).
                                    if (type == 11 && !List.of(1, 2, 3, 4, 8, 11).contains(id))
                                        throw new IllegalArgumentException("Unsupported mailbox goods reward ID: " + id);
                                    var validated = obj("i_RewardType", type, "i_RewardId", id, "d_RewardQuantity", quantity);
                                    if (truth(item.get("already_granted"))) validated.put("already_granted", true);
                                    items.add(validated);
                                }
                            }
                            addReward(items, 1, AdminSettings.whole(req.get("cp")), false);
                            addReward(items, 2, number(req.get("candy")), false);
                            addReward(items, 11, AdminSettings.whole(req.get("cookies")), false);
                            if(number(req.get("cp"))<0||number(req.get("candy"))<0||number(req.get("cookies"))<0)
                                throw new IllegalArgumentException("Mail rewards cannot be negative");
                            items=emu.leman.ggserver.game.social.MailboxRewards.validate(services.gameData,items,false);
                            var post = posts.send(target, first(req.get("title"), "Thông báo Quản trị"), first(req.get("memo"), "Quản trị viên đã gửi thông báo đến bạn."), items,false,str(req.get("request_id")));
                            response = obj("success", true, "message", "Đã gửi thư và quà thành công vào game!", "post", post);
                        }
                        case "/admin/api/user/ban" -> {
                            var req = request(exchange);
                            boolean banned = truth(req.getOrDefault("banned", true));
                            String uuid = canonical(data.resolve(req));
                            if (!services.registry.withAccountLock(uuid, () -> services.state.banUser(uuid, banned, null))) throw new IllegalArgumentException("Không tìm thấy người chơi!");
                            response = obj("success", true, "is_banned", banned, "message", banned ? "Đã KHÓA (BAN) tài khoản thành công!" : "Đã MỞ KHÓA tài khoản thành công!");
                        }
                        case "/admin/api/user/delete" -> {
                            var req = request(exchange);
                            String uuid = canonical(data.resolve(req));
                            if (!services.registry.withAccountLock(uuid, () -> services.state.deleteUser(uuid, null))) throw new IllegalArgumentException("Không tìm thấy người chơi để xóa!");
                            response = obj("success", true, "message", "Đã xóa toàn bộ dữ liệu tài khoản thành công! Khi vào lại game sẽ là tài khoản mới tinh.");
                        }
                        case "/admin/api/users/cleanup_tests" -> {
                            int count = 0;
                            for (var row : data.rows()) {
                                String uuid = str(row.get("uuid"));
                                if (StateStore.isTestUser(uuid, str(row.get("device_uuid")))
                                        && services.registry.withAccountLock(uuid, () -> services.state.deleteUser(uuid, null))) count++;
                            }
                            response = obj("success", true, "count", count, "message", "Đã dọn dẹp thành công " + count + " tài khoản test tự động!");
                        }
                        case "/admin/api/user/event_settings" -> {
                            var req = request(exchange);
                            String uuid = canonical(data.resolve(req));
                            req.put("uuid", uuid);
                            response = services.registry.withAccountLock(uuid, () -> settings.update(req));
                        }
                        default -> {
                            respond(exchange, 404, obj("success", false, "error", "Unknown admin route: " + path));
                            return true;
                        }
                    }
                    respond(exchange, 200, response);
                }
            } else {
                exchange.getResponseHeaders().set("Allow", "GET, HEAD, POST, OPTIONS");
                respond(exchange, 405, obj("success", false, "error", "Method not allowed"));
            }
        } catch (IllegalArgumentException e) {
            respond(exchange, 400, obj("success", false, "error", str(e.getMessage())));
        } catch (RuntimeException e) {
            org.slf4j.LoggerFactory.getLogger(AdminServer.class).error("Admin request failed: {}", emu.leman.ggserver.util.Logging.safe(path), e);
            respond(exchange, 500, obj("success", false, "error", str(e.getMessage())));
        }
        return true;
    }
    private Map<String,Object> status() throws IOException {
        List<String> lines=new ArrayList<>();
        List<Long> offsets=new ArrayList<>();String generation="";
        Path file=services.config.folder("logs").resolve("latest.log");
        if(Files.isRegularFile(file)) {
            var attributes=Files.readAttributes(file,java.nio.file.attribute.BasicFileAttributes.class);
            generation=str(attributes.fileKey())+":"+attributes.creationTime().toMillis();
            // Bounded tail; expose operational summaries only, never payloads/stack traces.
            try(var input=new RandomAccessFile(file.toFile(),"r")) {
                long start=Math.max(0,input.length()-65536);input.seek(start);
                if(start>0)input.readLine();
                String line;
                while((line=input.readLine())!=null) {
                    if(line.matches("(?:\\[[0-9 :\\-]+\\] )?\\[(INFO|WARN)\\] (SEND: [A-Za-z0-9_.]+ \\| (?:code=[0-9]+ \\| )?[0-9]+ B \\| [0-9]+ ms|Starting GGServer [0-9.]+|Database ready: (mongo|sqlite)|Registered [0-9]+ game handlers|Resources ready: [0-9]+ tables / [0-9]+ rows)")) {
                        lines.add(line);offsets.add(input.getFilePointer());
                        if(lines.size()>80){lines.removeFirst();offsets.removeFirst();}
                    }
                }
            }
        }
        Runtime runtime=Runtime.getRuntime();
        return obj("success",true,"status",obj("uptime_seconds",java.lang.management.ManagementFactory.getRuntimeMXBean().getUptime()/1000,
                "heap_used",runtime.totalMemory()-runtime.freeMemory(),"heap_max",runtime.maxMemory(),
                "database",services.config.databaseBackend,"log_available",Files.isRegularFile(file)),"logs",lines,"log_offsets",offsets,"log_generation",generation);
    }
    private String canonical(String identifier) {
        var user = services.state.getUser(identifier);
        if (user == null) throw new IllegalArgumentException("Không tìm thấy người chơi!");
        return str(user.get("uuid"));
    }
    private void notifyEvents(Map<String,Object> cfg) {
        int season = integer(map(cfg.get("star_pass")).get("active_season"));
        posts.send(null, obj("vi", "Cập nhật Sự kiện Trực tiếp", "en", "Live Event Update"),
                obj("vi", "Sự kiện máy chủ đã được đồng bộ! Star Pass: Mùa " + season + ". Chúc bạn chơi game vui vẻ!",
                        "en", "Server event has been synchronized! Star Pass: Season " + season + ". Have a relaxing and wonderful time!"), new ArrayList<>());
    }
    private List<Object> users() {
        int season = services.events.activeStarPassSeason();
        List<Object> out = new ArrayList<>();
        for (var row : data.rows()) {
            String uuid = str(row.get("uuid"));
            var user = services.state.getUser(uuid);
            if (user == null) continue;
            var ud = map(user.get("userdata"));
            var attendance = map(user.get("attendance"));
            var att1 = map(attendance.get("1"));
            var att3 = map(attendance.get("3"));
            var pass = list(user.get("user_event_point")).stream().map(emu.leman.ggserver.util.Json::map)
                    .filter(p -> "Pass".equals(p.get("s_EventType")) && integer(p.get("i_DataID")) == season).findFirst().orElseGet(LinkedHashMap::new);
            boolean gold = list(user.get("user_ticketcollection")).stream().map(emu.leman.ggserver.util.Json::map).anyMatch(t -> seasonId(t.get("i_id"), season))
                    || list(user.get("user_subscribe_list")).stream().map(emu.leman.ggserver.util.Json::map).anyMatch(s -> seasonId(s.get("i_SubscribeID"), season) && integer(s.get("i_isActive")) == 1);
            boolean ch2 = integer(map(map(user.get("areas")).get("1")).get("i_UserFanGrade")) >= 4
                    && list(user.get("user_follower")).stream().map(emu.leman.ggserver.util.Json::map).anyMatch(f -> integer(f.get("i_id")) == 12 && integer(f.get("i_Level")) >= 15);
            double like = dbl(row.get("u_like"));
            out.add(obj("uuid", uuid, "device_uuid", row.get("device_uuid"), "u_seq", row.get("u_seq"), "u_id", row.get("u_id"),
                    "ip", first(row.get("ip"), ud.get("ip"), ""), "last_domain", first(row.get("last_domain"), ""),
                    "u_nick", first(ud.get("u_nick"), row.get("u_id"), "Player " + row.get("u_seq")),
                    "u_last_login", first(ud.get("u_last_login"), ud.get("u_last_communication"), "Chưa có"),
                    "u_cp", row.get("u_cp"), "u_candy", row.get("u_candy"), "u_like", like, "u_like_formatted", Currency.format(like),
                    "attendance_count", first(row.get("attendance_count"), ud.get("attendance_count"), 0),
                    "attendance_day", att1.getOrDefault("day", 0), "attendance_ymd", att1.getOrDefault("ymd", 0),
                    "ch2_attendance_day", att3.getOrDefault("day", 0), "ch2_attendance_ymd", att3.getOrDefault("ymd", 0),
                    "attendance_map", attendance, "ch2_unlocked", ch2, "is_gold", gold,"event_overrides",map(user.get("event_overrides")),
                    "star_point", pass.getOrDefault("i_Point", 0), "star_step", pass.getOrDefault("i_Step", 0),
                    "is_banned", truth(row.get("is_banned")), "is_test", StateStore.isTestUser(uuid, str(row.get("device_uuid")))));
        }
        return out;
    }
    static boolean seasonId(Object id, int season) { return integer(id) == season || integer(id) == season + 1000; }
    static double number(Object value) {
        if (value == null || str(value).isBlank()) return 0;
        double result;
        try { result = Double.parseDouble(str(value)); } catch (NumberFormatException e) { throw new IllegalArgumentException("Invalid numeric value: " + value); }
        if (!Double.isFinite(result)) throw new IllegalArgumentException("Numeric value must be finite");
        return result;
    }
    static void addReward(List<Object> items, int id, double amount, boolean alreadyGranted) {
        if (amount == 0 || !alreadyGranted && amount < 0) return;
        var reward = obj("i_RewardType", 1, "i_RewardId", id, "d_RewardQuantity", amount);
        if (alreadyGranted) reward.put("already_granted", true);
        items.add(reward);
    }
    private static Map<String,Object> request(HttpExchange exchange) throws IOException {
        byte[] body = exchange.getRequestBody().readNBytes(1048577);
        if (body.length > 1048576) throw new IllegalArgumentException("Admin request body too large");
        Object parsed = parse(new String(body, StandardCharsets.UTF_8));
        if (!(parsed instanceof Map)) throw new IllegalArgumentException("Expected a JSON object");
        return map(parsed);
    }
    private static byte[] html(String name) throws IOException {
        try (InputStream input = AdminServer.class.getResourceAsStream(name)) {
            if (input != null) return input.readAllBytes();
        }
        // Source-tree development fallback. Production distributions package these as resources.
        for (Path base : List.of(Path.of("src/main/java/emu/leman/ggserver/admin"), Path.of("GGServerJava/src/main/java/emu/leman/ggserver/admin"))) {
            if (Files.isRegularFile(base.resolve(name))) return Files.readAllBytes(base.resolve(name));
        }
        throw new IOException("Missing packaged admin UI resource " + name);
    }
    private static void respond(HttpExchange exchange, int status, Object value) throws IOException { send(exchange, status, "application/json; charset=utf-8", bytes(value)); }
    private static void send(HttpExchange exchange, int status, String contentType, byte[] body) throws IOException {
        exchange.getResponseHeaders().set("Content-Type", contentType);
        exchange.getResponseHeaders().set("Cache-Control", "no-store");
        exchange.getResponseHeaders().set("X-Content-Type-Options", "nosniff");
        if (exchange.getRequestMethod().equals("HEAD")) {
            exchange.getResponseHeaders().set("Content-Length", String.valueOf(body.length));
            exchange.sendResponseHeaders(status, -1);
        } else {
            exchange.sendResponseHeaders(status, body.length);
            exchange.getResponseBody().write(body);
        }
        exchange.close();
    }
    private static List<Object> seasons() {
        String[] en = {"Lemon Flavored Vacation", "Make a wish to the moon", "Sweet Halloween Party", "Sweet Idol Photoshoot!", "Twinkling Dreamy Christmas", "Snow Festival", "Maid in Valentine", "Cherry Blossom Date", "Pleasant Spring Message", "Sunny Evening Picnic", "Dreaming Pastel Memories", "Shining Summer", "Riding a Romantic Ferris Wheel"};
        String[] vi = {"Vị chanh Kỳ nghỉ", "Một điều ước gửi đến mặt trăng", "Ngọt ngào Bữa tiệc Halloween", "Buổi chụp ảnh đặc biệt! Thần tượng ngọt ngào", "Lấp lánh Giáng Sinh mộng mơ", "Lễ hội tuyết", "Thiếu nữ ngày Tình nhân", "Hẹn hò mùa hoa anh đào", "Thông điệp mùa xuân dễ thương", "Picnic Tối Đầy Nắng", "Ký Ức Màu Phấn Mơ Mộng", "Mùa Hè Lấp Lánh", "Cưỡi một vòng đu quay lãng mạn"};
        List<Object> out = new ArrayList<>();
        for (int i = 0; i < en.length; i++) out.add(obj("id", i + 1, "name", vi[i] + " (" + en[i] + ")", "name_vi", vi[i], "name_en", en[i], "year", 2020 + (i + 7) / 12, "month", (i + 7) % 12 + 1));
        return out;
    }
}

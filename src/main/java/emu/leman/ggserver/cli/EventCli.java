package emu.leman.ggserver.cli;

import emu.leman.ggserver.game.content.EventManager;
import emu.leman.ggserver.util.Json;
import java.io.PrintStream;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.util.*;
import java.util.function.Consumer;
import static emu.leman.ggserver.util.Json.*;

/** Native eventctl; only event_config.json under GG_ROOT is changed. */
public final class EventCli {
    private static final String[] SEASONS = {
        "Vị chanh Kỳ nghỉ / Lemon Flavored Vacation", "Một điều ước gửi đến mặt trăng / Make a wish to the moon",
        "Ngọt ngào Bữa tiệc Halloween / Sweet Halloween Party", "Buổi chụp ảnh đặc biệt! Thần tượng ngọt ngào / Sweet Idol Photoshoot!",
        "Lấp lánh Giáng Sinh mộng mơ / Twinkling Dreamy Christmas", "Lễ hội tuyết / Snow Festival",
        "Thiếu nữ ngày Tình nhân / Maid in Valentine", "Hẹn hò mùa hoa anh đào / Cherry Blossom Date",
        "Thông điệp mùa xuân dễ thương / Pleasant Spring Message", "Picnic Tối Đầy Nắng / Sunny Evening Picnic",
        "Ký Ức Màu Phấn Mơ Mộng / Dreaming Pastel Memories", "Mùa Hè Lấp Lánh / Shining Summer",
        "Cưỡi một vòng đu quay lãng mạn / Riding a Romantic Ferris Wheel"
    };
    private EventCli() {}
    public static void main(String[] args) { System.exit(run(args, System.getenv(), System.out, System.err)); }

    public static int run(String[] args, Map<String,String> env, PrintStream out, PrintStream err) {
        try {
            if (args.length == 0 || Set.of("help", "--help", "-h").contains(args[0])) { help(out); return 0; }
            String cmd = args[0].toLowerCase(Locale.ROOT);
            if (Set.of("sendmail", "mail", "post").contains(cmd)) return mail(args, env, out, err);
            Path root = CliSupport.root(env);
            CliSupport.checkRoot(root);
            if (Set.of("list", "status", "ls").contains(cmd)) {
                if (args.length != 1) throw new IllegalArgumentException("Usage: eventctl.sh list");
                list(load(root), out);
                return 0;
            }
            if (args.length != 2) throw new IllegalArgumentException("Expected a command and target; see eventctl.sh --help");
            String target = args[1].toLowerCase(Locale.ROOT);
            switch (cmd) {
                case "enable", "on", "start" -> edit(root, cfg -> toggle(cfg, target, true));
                case "disable", "off", "stop" -> edit(root, cfg -> toggle(cfg, target, false));
                case "season", "setseason" -> {
                    int season;
                    try { season = Integer.parseInt(target); } catch (NumberFormatException e) { throw new IllegalArgumentException("Season must be 1 through 13"); }
                    if (season < 1 || season > 13) throw new IllegalArgumentException("Season must be 1 through 13");
                    edit(root, cfg -> map(cfg.get("star_pass")).put("active_season", season));
                    out.println("Star Pass season " + season + ": " + SEASONS[season - 1]);
                }
                case "gold" -> {
                    boolean enabled;
                    if (Set.of("on", "true", "1", "enable", "bat", "bật").contains(target)) enabled = true;
                    else if (Set.of("off", "false", "0", "disable", "tat", "tắt").contains(target)) enabled = false;
                    else throw new IllegalArgumentException("Gold state must be on or off");
                    edit(root, cfg -> map(cfg.get("star_pass")).put("paid_card_enabled", enabled));
                }
                default -> throw new IllegalArgumentException("Unknown command: " + cmd);
            }
            out.println("Updated " + root.resolve("event_config.json") + " (hot reload; no restart required).");
            return 0;
        } catch (Exception e) { return CliSupport.error(err, e); }
    }

    private static int mail(String[] args, Map<String,String> env, PrintStream out, PrintStream err) {
        if (args.length < 3 || args.length > 6) throw new IllegalArgumentException("Usage: eventctl.sh sendmail TITLE MEMO [cp] [candy] [cookies]");
        List<String> options = new ArrayList<>(List.of("--title", args[1], "--memo", args[2]));
        String[] names = {"--cp", "--candy", "--cookie"};
        for (int i = 3; i < args.length; i++) { options.add(names[i-3]); options.add(args[i]); }
        return NotificationCli.run(options.toArray(String[]::new), env, out, err);
    }

    private static Map<String,Object> load(Path root) {
        Path path = root.resolve("event_config.json");
        if (!Files.exists(path)) return EventManager.normalize(EventManager.defaults());
        Object raw = Json.read(path);
        if (!(raw instanceof Map)) throw new IllegalArgumentException("event_config.json must contain an object; refusing to overwrite it");
        // Preserve unknown extension fields while filling legacy/default sections for the editor.
        Map<String,Object> result = copy(map(raw));
        merge(result, EventManager.normalize(raw));
        return result;
    }

    private static void merge(Map<String,Object> target, Map<String,Object> normalized) {
        normalized.forEach((key, value) -> {
            if (value instanceof Map && target.get(key) instanceof Map) merge(map(target.get(key)), map(value));
            else target.put(key, copy(value));
        });
    }

    private static synchronized void edit(Path root, Consumer<Map<String,Object>> operation) throws Exception {
        Path lockPath = root.resolve(".eventctl.lock");
        try (FileChannel channel = FileChannel.open(lockPath, StandardOpenOption.CREATE, StandardOpenOption.WRITE);
             var ignored = channel.lock()) {
            Map<String,Object> cfg = load(root);
            operation.accept(cfg);
            merge(cfg, EventManager.normalize(cfg)); // synchronize legacy mirrors, keep extension fields
            Json.write(root.resolve("event_config.json"), cfg);
        }
    }

    private static void toggle(Map<String,Object> cfg, String target, boolean enabled) {
        Map<String,Object> attendance = map(cfg.get("attendance_events"));
        if (attendance.containsKey(target)) { map(attendance.get(target)).put("enabled", enabled); return; }
        switch (target) {
            case "pass", "starpass", "star_pass" -> map(cfg.get("star_pass")).put("enabled", enabled);
            case "gold", "paid_gold", "starpass_gold" -> map(cfg.get("star_pass")).put("paid_card_enabled", enabled);
            case "sale", "goodssale", "pass_sale" -> map(cfg.get("pass_goods_sale")).put("enabled", enabled);
            case "meow", "meowfest", "cat", "samseck" -> map(cfg.get("meowfest")).put("enabled", enabled);
            case "ch3", "tour", "chapter3" -> map(cfg.get("chapter3_tour")).put("enabled", enabled);
            case "snow", "tuyet" -> weather(cfg, true, enabled);
            case "cherry", "cherryblossom", "hoaanhdao" -> weather(cfg, false, enabled);
            case "fanart", "costume" -> map(cfg.get("fan_art_costume")).put("enabled", enabled);
            case "rank", "ranking", "duatop" -> map(cfg.get("event_ranking")).put("enabled", enabled);
            case "all" -> {
                attendance.values().forEach(value -> map(value).put("enabled", enabled));
                for (String section : List.of("star_pass", "pass_goods_sale", "meowfest", "chapter3_tour", "fan_art_costume", "event_ranking"))
                    map(cfg.get(section)).put("enabled", enabled);
                map(cfg.get("star_pass")).put("paid_card_enabled", enabled);
                weather(cfg, false, false);
                weather(cfg, true, enabled);
            }
            default -> throw new IllegalArgumentException("Unknown event: " + target);
        }
    }

    private static void weather(Map<String,Object> cfg, boolean snow, boolean enabled) {
        Map<String,Object> wf = map(cfg.get("weather_festival"));
        wf.put(snow ? "snow_enabled" : "cherry_blossom_enabled", enabled);
        if (enabled) wf.put(snow ? "cherry_blossom_enabled" : "snow_enabled", false);
        wf.put("mode", truth(wf.get("snow_enabled")) ? "snow" : truth(wf.get("cherry_blossom_enabled")) ? "cherry" : "none");
    }

    private static void list(Map<String,Object> cfg, PrintStream out) {
        out.println("=== GUITAR GIRL SERVER - EVENTS / SỰ KIỆN ===");
        map(cfg.get("attendance_events")).forEach((id, value) -> {
            Map<String,Object> item = map(value);
            out.println("Attendance " + id + ": " + status(item.get("enabled")) + " " + str(item.get("name")) + " - " + str(item.get("description")));
        });
        Map<String,Object> sp = map(cfg.get("star_pass"));
        int season = integer(sp.get("active_season"));
        out.println("Star Pass: " + status(sp.get("enabled")) + "; season " + season + " - " + SEASONS[season-1]);
        out.println("Paid Gold: " + status(sp.get("paid_card_enabled")));
        for (String section : List.of("pass_goods_sale", "meowfest", "chapter3_tour", "fan_art_costume", "event_ranking")) {
            Map<String,Object> item = map(cfg.get(section));
            out.println(section + ": " + status(item.get("enabled")) + " " + str(item.get("name")) + " - " + str(item.get("description")));
        }
        Map<String,Object> wf = map(cfg.get("weather_festival"));
        out.println("Snow: " + status(wf.get("snow_enabled")) + "; Cherry blossom: " + status(wf.get("cherry_blossom_enabled")));
    }
    private static String status(Object value) { return truth(value) ? "[ON / BẬT]" : "[OFF / TẮT]"; }
    private static void help(PrintStream out) {
        out.println("Usage: ./eventctl.sh list|status|ls");
        out.println("  enable|on|start TARGET / disable|off|stop TARGET");
        out.println("  Targets: 1, 2, 3, 202110, 202111, pass, gold, sale, meowfest, ch3, snow, cherry, fanart, rank, all");
        out.println("  Aliases: starpass, star_pass; paid_gold, starpass_gold; goodssale, pass_sale; meow, cat, samseck;");
        out.println("           tour, chapter3; tuyet; cherryblossom, hoaanhdao; costume; ranking, duatop");
        out.println("  season|setseason 1..13 / gold on|off");
        out.println("  sendmail|mail|post TITLE MEMO [cp] [candy] [cookies]");
        out.println("GG_ROOT selects the Java data directory. Config edits hot reload; sending mail requires the live Java server.");
    }
}

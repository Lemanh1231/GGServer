package emu.leman.ggserver.server.admin;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.codec.Codec;
import emu.leman.ggserver.game.economy.Currency;
import emu.leman.ggserver.database.StateStore;
import java.io.IOException;
import java.nio.file.Files;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Per-player management, retaining the game's existing inventory and attendance wire fields. */
final class AdminSettings {
    private final Services services;
    private final AdminData data;
    private final AdminPosts posts;
    AdminSettings(Services services, AdminData data, AdminPosts posts) { this.services = services; this.data = data; this.posts = posts; }
    Map<String,Object> update(Map<String,Object> req) {
        var user = services.state.getUser(data.resolve(req));
        if (user == null || user.isEmpty()) throw new IllegalArgumentException("Không tìm thấy người chơi!");
        String uuid = str(user.get("uuid"));
        Map<String,Object> ud = child(user, "userdata");
        long cp = whole(req.get("add_cp"));
        double candy = AdminServer.number(req.get("add_candy"));
        Object setLike = req.get("set_like"), addLike = req.get("add_like");
        int season = services.events.activeStarPassSeason();
        boolean passEnabled = services.events.isStarPassEnabled();

        if (passEnabled && req.containsKey("is_gold")) gold(user, season, truth(req.get("is_gold")));
        if (passEnabled && present(req.get("star_point"))) {
            long point = Math.max(0, whole(req.get("star_point")));
            int step = 0;
            for (var r : services.gameData.table(18)) if (integer(r.get("2")) == season && point >= lng(r.get("4"))) step = Math.max(step, integer(r.get("3")));
            int year = integer(services.gameData.row(17, season).getOrDefault("11", season <= 5 ? 2020 : 2021));
            var entry = find(listAt(user, "user_event_point"), "i_DataID", season);
            if (entry == null || !"Pass".equals(entry.get("s_EventType"))) {
                entry = obj("s_EventType", "Pass", "i_DataID", season, "i_ADViewTime", 0);
                listAt(user, "user_event_point").add(entry);
            }
            entry.put("i_Point", point); entry.put("i_Step", step); entry.put("i_Version", LocalDate.now().getYear() - year);
        }
        attendance(user, req);
        if (req.containsKey("unlock_ch2")) chapter2(user, truth(req.get("unlock_ch2")));

        List<Object> mailItems = new ArrayList<>();
        boolean reset = false, sendMail = truth(req.get("send_mail"));
        if (present(setLike)) {
            var parsed = Currency.parse(setLike);
            emu.leman.ggserver.game.economy.AreaCurrency.setLike(user,setLike);
            reset = true;
        } else if (present(addLike)) {
            var parsed = Currency.parse(addLike);
            if (parsed.integer().signum() != 0) {
                emu.leman.ggserver.game.economy.AreaCurrency.addLike(user,addLike);
                if (sendMail) AdminServer.addReward(mailItems, 3, parsed.floating(), true);
                reset = true;
            }
        }
        if (cp != 0 || candy != 0) {
            ud.put("u_cp", Math.addExact(lng(ud.get("u_cp")), cp));
            double result = dbl(ud.get("u_candy")) + candy;
            if (!Double.isFinite(result)) throw new IllegalArgumentException("Candy balance overflow");
            ud.put("u_candy", result);
            if (sendMail) { AdminServer.addReward(mailItems, 1, cp, true); AdminServer.addReward(mailItems, 2, candy, true); }
            reset = true;
        }
        if (reset) user.put("needs_client_reset", true);
        // Save once, after validating the complete settings payload. SQL balances and inventory are
        // committed by StateStore together, rather than incrementing then saving a stale snapshot.
        services.state.saveUser(user);
        if (req.containsKey("is_banned")) services.state.banUser(uuid, truth(req.get("is_banned")), null);
        if (sendMail) posts.send(uuid, first(req.get("mail_title"), "Cập nhật Quà tặng từ Quản trị viên"),
                first(req.get("mail_memo"), "Quản trị viên đã gửi quà tặng/quyền lợi vào tài khoản của bạn. Chúc bạn chơi game vui vẻ!"), mailItems);
        return obj("success", true, "message", "Đã cập nhật sự kiện cho người chơi thành công!");
    }
    private static void gold(Map<String,Object> user, int season, boolean enabled) {
        var shop = listAt(user, "user_shop"); var subs = listAt(user, "user_subscribe_list"); var tickets = listAt(user, "user_ticketcollection");
        if (enabled) {
            var sh = find(shop, "i_id", 1000 + season);
            if (sh == null) shop.add(obj("i_id", 1000 + season, "i_Count", 1, "i_TotalCount", 1));
            else { sh.put("i_Count", Math.max(1, integer(sh.get("i_Count")))); sh.put("i_TotalCount", Math.max(1, integer(sh.get("i_TotalCount")))); }
            var sub = subs.stream().map(emu.leman.ggserver.util.Json::map).filter(s -> AdminServer.seasonId(s.get("i_SubscribeID"), season)).findFirst().orElse(null);
            if (sub == null) { sub = obj("i_SubscribeID", season); subs.add(sub); }
            sub.put("i_isActive", 1); sub.put("i_ActiveTime", Integer.MAX_VALUE);
            if (find(tickets, "i_id", season) == null) tickets.add(obj("i_id", season));
            if (find(tickets, "i_id", 1000 + season) == null) tickets.add(obj("i_id", 1000 + season));
        } else {
            shop.removeIf(o -> List.of(season, 1000 + season, 2000 + season, 3000 + season).contains(integer(map(o).get("i_id"))));
            subs.removeIf(o -> AdminServer.seasonId(map(o).get("i_SubscribeID"), season));
            tickets.removeIf(o -> AdminServer.seasonId(map(o).get("i_id"), season));
        }
    }
    private void attendance(Map<String,Object> user, Map<String,Object> req) {
        var custom = map(req.get("attendance_events_custom"));
        boolean customized = custom.values().stream().anyMatch(v -> truth(map(v).get("modified")));
        if (customized) {
            for (var entry : custom.entrySet()) {
                var cfg = map(entry.getValue()); String event = entry.getKey();
                if (!truth(cfg.get("modified")) || !services.events.isAttendanceEventEnabled(event)) continue;
                int max = List.of("2", "202110").contains(event) ? 14 : 7;
                progress(user, event, cfg.get("target_day"), truth(cfg.getOrDefault("unlock_today", true)), str(cfg.getOrDefault("mode", "claim_day")), max, truth(cfg.get("grant_all")));
            }
        } else {
            progress(user, "1", req.getOrDefault("attendance_day", req.get("attendance_count")), truth(req.getOrDefault("attendance_unlock_today", true)), str(req.getOrDefault("attendance_mode", "claim_day")), 7, truth(req.get("grant_7d_rewards")));
            progress(user, "3", req.get("ch2_attendance_day"), truth(req.getOrDefault("ch2_attendance_unlock_today", true)), str(req.getOrDefault("ch2_attendance_mode", "claim_day")), 7, truth(req.get("grant_ch2_rewards")));
        }
    }
    private void progress(Map<String,Object> user, String event, Object target, boolean unlock, String mode, int max, boolean grant) {
        if (!present(target) && !grant) return;
        var state = child(child(user, "attendance"), event);
        int today = Integer.parseInt(LocalDate.now().format(DateTimeFormatter.BASIC_ISO_DATE));
        int day = present(target) ? Math.toIntExact(whole(target)) : 0;
        int claimed = day <= 0 ? 0 : day >= max && mode.equals("complete") ? max : Math.min(day, max) - 1;
        int date = day <= 0 ? 0 : day >= max && mode.equals("complete") || !unlock ? today : 0;
        if (grant) {
            List<Object> rewards = eventRewards(event);
            if (rewards.isEmpty()) throw new IllegalArgumentException("Attendance reward data unavailable for event " + event + "; no progress or rewards saved");
            for (Object reward : rewards) {
                int n = integer(map(reward).get("reward_num"));
                if (n >= 1 && n <= max) giveReward(user, map(reward));
            }
            claimed = max; date = today;
        }
        state.put("day", claimed); state.put("ymd", date);
        if (event.equals("1")) {
            child(user, "userdata").put("attendance_count", grant || mode.equals("complete") && claimed == max ? claimed : day <= 0 ? 0 : claimed + 1);
            child(user, "userdata").put("attendance_date", date);
        }
    }
    private List<Object> eventRewards(String event) {
        try {
            var decoded = new Codec(services.config).decodeRequest(Files.readString(services.config.resource("gamedata/getEventRewardList.b64")), "main.getEventRewardListReturn").named();
            // Thrift map keys are i32, whereas JSON attendance keys are strings.
            Map<?,?> events = map(decoded.get("data"));
            for (var entry : events.entrySet()) {
                if (String.valueOf(entry.getKey()).equals(event)) return list(map(entry.getValue()).get("reward_list"));
            }
            return List.of();
        } catch (IOException | RuntimeException e) { throw new IllegalArgumentException("Cannot decode attendance rewards: " + e.getMessage(), e); }
    }
    private void giveReward(Map<String,Object> user, Map<String,Object> reward) {
        int type = integer(reward.get("reward_type")), id = integer(reward.get("reward_id"));
        double amount = AdminServer.number(reward.get("reward_value"));
        var ud = child(user, "userdata");
        if (type == 1) {
            switch (id) {
                case 1 -> ud.put("u_cp", Math.addExact(lng(ud.get("u_cp")), (long)amount));
                case 2 -> ud.put("u_candy", dbl(ud.get("u_candy")) + amount);
                case 3, 4 -> emu.leman.ggserver.game.economy.AreaCurrency.addLike(user,amount);
                case 8 -> ud.put("u_fans", Math.addExact(lng(ud.get("u_fans")), (long)amount));
                case 11 -> StateStore.addAp(user, (int)amount);
                default -> throw new IllegalArgumentException("Unsupported attendance goods reward ID " + id);
            }
            return;
        }
        String key = switch (type) {
            case 2 -> "user_music"; case 3 -> "costumes"; case 4 -> "user_prop"; case 5 -> "user_follower";
            case 7 -> "user_unit"; case 9 -> "user_guitar"; case 11 -> "user_follower_giftitem";
            default -> throw new IllegalArgumentException("Unsupported attendance reward type " + type);
        };
        var inventory = listAt(user, key); var item = find(inventory, "i_id", id);
        if (type == 11) {
            if (item == null) inventory.add(obj("i_id", id, "i_Value", (long)amount));
            else item.put("i_Value", lng(item.get("i_Value")) + (long)amount);
        } else if (type == 7) {
            int add = Math.max(1, (int)amount);
            if (item == null) inventory.add(obj("i_id", id, "i_Level", Math.min(20, add)));
            else item.put("i_Level", Math.min(20, integer(item.getOrDefault("i_Level", 1)) + add));
        } else if (item == null) {
            item = obj("i_id", id, "i_Level", 1, "i_BonusLevel", 0);
            if (type == 2) item.putAll(obj("b_EncoreBonusAppear", 0, "l_EncoreBonusActivateTime", 0, "i_EncoreBonusFollowerId", 0, "i_ChThirdActiveTime", 0));
            inventory.add(item);
        }
    }
    private static void chapter2(Map<String,Object> user, boolean unlock) {
        var area = child(child(user, "areas"), "1");
        area.putIfAbsent("i_Area", 1);
        area.put("i_UserFanGrade", unlock ? Math.max(4, integer(area.get("i_UserFanGrade"))) : 1);
        if (unlock) area.put("i_UserFanCount", Math.max(1000000, lng(area.get("i_UserFanCount"))));
        var followers = listAt(user, "user_follower");
        var follower = find(followers, "i_id", 12);
        if (follower == null && unlock) {
            follower = obj("i_id", 12, "i_Level", 15, "i_ActiveTime", 0, "i_BonusLevel", 0);
            followers.add(follower);
        } else if (follower != null) follower.put("i_Level", unlock ? Math.max(15, integer(follower.get("i_Level"))) : 1);
    }
    static Map<String,Object> child(Map<String,Object> parent, String key) {
        if (!(parent.get(key) instanceof Map)) parent.put(key, obj());
        return map(parent.get(key));
    }
    static List<Object> listAt(Map<String,Object> parent, String key) {
        if (!(parent.get(key) instanceof List)) parent.put(key, new ArrayList<>());
        return list(parent.get(key));
    }
    private static Map<String,Object> find(List<Object> list, String key, int id) {
        return list.stream().map(emu.leman.ggserver.util.Json::map).filter(i -> integer(i.get(key)) == id).findFirst().orElse(null);
    }
    private static boolean present(Object value) { return value != null && !str(value).isBlank(); }
    static long whole(Object value) {
        if (!present(value)) return 0;
        try { return new java.math.BigDecimal(str(value)).longValueExact(); }
        catch (NumberFormatException | ArithmeticException e) { throw new IllegalArgumentException("Invalid integer value: " + value); }
    }
}

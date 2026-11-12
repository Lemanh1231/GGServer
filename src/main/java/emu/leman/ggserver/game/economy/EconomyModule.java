package emu.leman.ggserver.game.economy;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.CmdId;
import emu.leman.ggserver.database.StateStore;
import emu.leman.ggserver.game.social.SocialFollowers;
import emu.leman.ggserver.net.CommandHandler;
import emu.leman.ggserver.net.HandlerRegistry;
import emu.leman.ggserver.net.Result;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;
import static emu.leman.ggserver.game.economy.EconomyData.reward;

/** Native shop/reward commands. Wire names deliberately match the original client. */
public final class EconomyModule implements emu.leman.ggserver.game.GameModule {
    private static final Map<Integer,Integer> AD_GROUPS = Map.of(3, 200010, 2, 210010, 18, 220010);
    private final Services s;
    private final EconomyData data;

    public EconomyModule(Services services) { s = services; data = new EconomyData(s.config); }

    @Override public String id() { return "economy"; }
    @Override public void register() {
        bind(CmdId.BUY_VARIETY_STORE, this::buyVariety);
        bind(CmdId.BUY_CHECK, this::buyCheck);
        bind(CmdId.CHECK_BUY_SHOP, this::checkBuyShop);
        bind(CmdId.BUY_SHOP, this::buyShop);
        bind(CmdId.BUY_MUSIC, (p,c) -> buyInventory(p,c,true));
        bind(CmdId.BUY_AVATAR, (p,c) -> buyInventory(p,c,false));
        bind(CmdId.BUY_ITEM, this::buyItem);
        bind(CmdId.BUY_CONTENTS, this::buyContents);
        bind(CmdId.SET_ATTENDANCE, this::attendance);
        bind(CmdId.GET_EVENT_REWARD_LIST, this::eventBoards);
        bind(CmdId.SET_EVENT_REWARD, this::eventReward);
        bind(CmdId.SET_SELECT_REWARD, this::selectReward);
        bind(CmdId.SET_GAME_REWARD, this::gameReward);
        bind(CmdId.UPDATE_ACHIEVEMENT, (p,c) -> Result.ok(obj("achievement", first(p.get("achievement"), p.get("u_achievement"), 0))));
        bind(CmdId.SET_PASS_REWARD, this::passReward);
        bind(CmdId.SET_AD_REWARD, this::adReward);
        bind(CmdId.AD_VIEW_LOG, (p,c) -> Result.ok(obj("status", "Y")));
        bind(CmdId.PAID_EVENT_POINT, this::paidEventPoint);
    }

    private void bind(String name, CommandHandler handler) {
        s.registry.register(name, (request, context) -> {
            // The read/check/write sequence must be serialized as well as individual state calls.
            synchronized (s.state) {
                return handler.handle(HandlerRegistry.payload(request), context == null ? obj() : context);
            }
        });
    }

    private Map<String,Object> user(Map<String,Object> p, Map<String,Object> context) {
        Object id = first(p.get("device_uuid"), p.get("uuid"), context.get("uuid"), p.get("u_seq"), p.get("u_id"), "");
        return s.state.getUser(str(id));
    }
    private static String uuid(Map<String,Object> user) { return str(first(user.get("uuid"), map(user.get("userdata")).get("uuid"), "")); }
    private static Map<String,Object> ud(Map<String,Object> user) { return user == null ? obj() : child(user, "userdata"); }
    private static Map<String,Object> child(Map<String,Object> parent, String key) {
        if (!(parent.get(key) instanceof Map)) parent.put(key, obj());
        return map(parent.get(key));
    }
    private static List<Object> items(Map<String,Object> user, String key) {
        if (!(user.get(key) instanceof List)) user.put(key, new ArrayList<>());
        return list(user.get(key));
    }
    private static Map<String,Object> find(List<Object> list, String key, int id) {
        for (Object value : list) if (value instanceof Map && integer(map(value).get(key)) == id) return map(value);
        return null;
    }
    private static Map<String,Object> find(List<Object> list, int id) { return find(list, "i_id", id); }
    private static int number(Map<String,Object> row, String key, int fallback) { return integer(first(row.get(key), fallback)); }
    private static long now() { return Instant.now().getEpochSecond(); }
    private static int today() { return Integer.parseInt(LocalDate.now().format(DateTimeFormatter.BASIC_ISO_DATE)); }
    private static LocalDate date(long seconds) { return Instant.ofEpochSecond(seconds).atZone(ZoneId.systemDefault()).toLocalDate(); }
    private static void add(Map<String,Object> map, String key, long amount) { map.put(key, lng(map.get(key)) + amount); }

    private boolean deduct(Map<String,Object> user, String currency, Long price) {
        if (user == null || currency == null || currency.isEmpty() || price == null || price < 0) return false;
        if (price == 0) return true;
        String key = switch (currency.toUpperCase(Locale.ROOT)) {
            case "CP", "CHOCOLATE", "SOCOLA" -> "cp";
            case "GP", "CANDY" -> "candy";
            default -> "";
        };
        if (key.isEmpty() || !s.state.spendCurrency(uuid(user), key, price.doubleValue())) return false;
        Map<String,Object> ud = ud(user);
        if (key.equals("cp")) add(ud, "u_cp", -price);
        else ud.put("u_candy", dbl(ud.get("u_candy")) - price);
        return true;
    }

    private record Price(String currency, Long amount) {}
    private Price price(int table, int id, String currencyColumn, String priceColumn) {
        Map<String,Object> row = data.row(table, id);
        if (row.isEmpty()) return new Price(null, null);
        long amount = lng(row.get(priceColumn));
        if (table == 2 && amount == 0 && lng(row.get("46")) > 0) amount = lng(row.get("46"));
        return amount < 0 ? new Price(null, null) : new Price(str(row.get(currencyColumn)), amount);
    }

    private static Map<String,Object> music(int id) {
        return obj("i_id", id, "i_Level", 1, "i_BonusLevel", 0, "b_EncoreBonusAppear", 0,
                "l_EncoreBonusActivateTime", 0, "i_EncoreBonusFollowerId", 0, "i_ChThirdActiveTime", 0);
    }

    /** Shop type 11 historically means goods; reward type 11 means a follower gift. */
    void grant(Map<String,Object> user, Map<String,Object> reward, boolean shop) {
        if (user == null) return;
        int type = integer(reward.get("reward_type")), id = integer(reward.get("reward_id"));
        long value = lng(reward.get("reward_value"));
        Map<String,Object> ud = ud(user);
        if (type == 1 || (shop && type == 11)) {
            long cp = 0, fans = 0;
            double candy = 0;
            Object like = 0;
            switch (id) {
                case 1 -> { cp = value; add(ud, "u_cp", cp); }
                case 2 -> { candy = dbl(reward.get("reward_value")); ud.put("u_candy", dbl(ud.get("u_candy")) + candy); }
                case 3, 4 -> {
                    like = reward.get("reward_value");
                    // Preserve large integral balances rather than narrowing to a double.
                    ud.put("u_like", Currency.parse(Currency.parse(ud.get("u_like")).integer().add(Currency.parse(like).integer())).floating());
                }
                case 8 -> { fans = value; add(ud, "u_fans", fans); }
                case 11 -> StateStore.addAp(user, (int)value);
                default -> { }
            }
            if (cp != 0 || candy != 0 || dbl(like) != 0 || fans != 0)
                s.state.incrementCurrency(uuid(user), cp, candy, like, fans);
            return;
        }
        if (type == 11) {
            List<Object> gifts = items(user, "user_follower_giftitem");
            Map<String,Object> gift = find(gifts, id);
            if (gift == null) gifts.add(obj("i_id", id, "i_Value", value));
            else add(gift, "i_Value", value);
        } else if (type == 7 && !shop) {
            List<Object> units = items(user, "user_unit");
            Map<String,Object> unit = find(units, id);
            int levels = Math.max(1, (int)value);
            if (unit == null) units.add(obj("i_id", id, "i_Level", Math.min(20, levels)));
            else unit.put("i_Level", Math.min(20, number(unit, "i_Level", 1) + levels));
        } else if (type == 6 && shop) {
            List<Object> buffs = items(user, "user_buff");
            Map<String,Object> buff = find(buffs, id);
            if (buff == null) { buff = obj("i_id", id, "i_Level", 1); buffs.add(buff); }
            long end = lng(buff.getOrDefault("i_EndTime", buff.get("i_ExpiredTime")));
            buff.put("i_Level", Math.max(1, number(buff, "i_Level", 1)));
            buff.put("i_ActiveTime", now());
            buff.put("i_EndTime", Math.max(now(), end) + value);
            buff.remove("i_BuffTime"); buff.remove("i_ExpiredTime");
        } else if (type == 10 && shop) {
            subscribe(user, id, id > 1000 ? id % 1000 : id);
        } else {
            String key = switch (type) {
                case 2 -> "user_music";
                case 3 -> "costumes";
                case 4 -> "user_prop";
                case 5 -> shop ? "" : "user_follower";
                case 9 -> "user_guitar";
                default -> "";
            };
            if (key.isEmpty()) return;
            if (!shop && type == 4 && !user.containsKey(key)) user.put(key, new ArrayList<>(List.of(obj("i_id",1,"i_Level",1),obj("i_id",2,"i_Level",1))));
            List<Object> inventory = items(user, key);
            Map<String,Object> owned = find(inventory, id);
            if (owned == null) {
                inventory.add(type == 2 ? music(id) : type == 4 ? obj("i_id", id, "i_Level", 1) : obj("i_id", id, "i_Level", 1, "i_BonusLevel", 0));
                if (type == 5) SocialFollowers.syncMessenger(user);
            } else if (shop && type == 4) add(owned, "i_Level", 1);
        }
    }

    private static void subscribe(Map<String,Object> user, int... ids) {
        Set<Integer> all = new LinkedHashSet<>();
        for (int id : ids) { all.add(id); all.add(1000 + (id > 1000 ? id % 1000 : id)); }
        for (int id : all) {
            if (find(items(user,"user_subscribe_list"), "i_SubscribeID", id) == null)
                items(user,"user_subscribe_list").add(obj("i_SubscribeID",id,"i_ActiveTime",now(),"i_isActive",1));
            if (find(items(user,"user_ticketcollection"),id) == null) items(user,"user_ticketcollection").add(obj("i_id",id));
        }
    }

    List<Object> normaliseShop(Map<String,Object> user) {
        Map<Integer,Map<String,Object>> byId = new LinkedHashMap<>();
        long now = now();
        for (Object raw : items(user,"user_shop")) {
            if (!(raw instanceof Map)) continue;
            Map<String,Object> item = map(raw);
            int id = integer(item.get("i_id"));
            if (id <= 0) continue;
            int count = integer(item.get("i_Count"));
            long time = Math.min(now, lng(item.get("i_PurchaseTime")));
            Map<String,Object> normalized = obj("i_id",id,"i_Level",Math.max(1,number(item,"i_Level",1)),
                    "i_Count",count,"i_TotalCount",Math.max(count,lng(item.get("i_TotalCount"))),
                    "i_PurchaseTime",time,"upd_day",lng(first(item.get("upd_day"),time)));
            Map<String,Object> previous = byId.putIfAbsent(id,normalized);
            if (previous != null) for (String key : List.of("i_Count","i_TotalCount","i_PurchaseTime","upd_day","i_Level"))
                previous.put(key,Math.max(lng(previous.get(key)),lng(normalized.get(key))));
        }
        for (Map.Entry<Integer,Map<String,Object>> pair : byId.entrySet()) {
            int id = pair.getKey(), condition = integer(data.row(12,id).get("36"));
            Map<String,Object> item = pair.getValue();
            if (condition == 4 || AD_GROUPS.containsKey(id)) item.put("i_Count",0);
            else if (condition == 5 || id == 10012) {
                long time = lng(item.get("i_PurchaseTime"));
                if (time <= 0 || !date(time).equals(LocalDate.now())) { item.put("i_Count",0); item.put("i_PurchaseTime",0); }
            }
        }
        List<Object> result = new ArrayList<>(byId.values());
        user.put("user_shop", result);
        return result;
    }

    private int[] adLevel(int group, long exp) {
        int level = 1, reward = group;
        List<Map<String,Object>> levels = data.rows(37).stream().filter(r -> integer(r.get("1")) == group)
                .sorted(Comparator.comparingInt(r -> number(r,"2",1))).toList();
        for (Map<String,Object> row : levels) {
            if (exp < lng(row.get("3"))) break;
            level = number(row,"2",1); reward = number(row,"4",group);
        }
        return new int[]{level,reward};
    }

    List<Object> normaliseAdLevels(Map<String,Object> user) {
        List<Object> shop = normaliseShop(user);
        Object raw = user.get("user_ad_level");
        List<Object> existing = raw instanceof Map ? List.of(raw) : list(raw);
        List<Object> result = new ArrayList<>();
        for (int group : List.of(200010,210010,220010)) {
            int shopId = AD_GROUPS.entrySet().stream().filter(e -> e.getValue() == group).findFirst().orElseThrow().getKey();
            Map<String,Object> item = find(shop,shopId), old = find(existing,group);
            long history = item == null ? 0 : lng(item.get("i_TotalCount"))*5;
            long exp = old == null ? 0 : lng(old.get("i_EXP"));
            if (exp == 1 && history == 0) exp = 0;
            exp = Math.max(exp,history);
            int level = adLevel(group,exp)[0];
            result.add(obj("i_id",group,"i_Level",level,"i_EXP",exp));
            if (item != null) item.put("i_Level",level);
        }
        user.put("user_ad_level",result);
        return result;
    }

    private String eligibility(Map<String,Object> user, int id) {
        if (user == null) return "User not found";
        List<Object> shop = normaliseShop(user);
        int season = id % 1000;
        if (id >= 1000 && id < 2000) {
            for (Object value : items(user,"user_subscribe_list")) {
                Map<String,Object> sub = map(value);
                int sid = integer(sub.get("i_SubscribeID"));
                if ((sid == season || sid == 1000+season) && integer(sub.getOrDefault("i_isActive",1)) == 1)
                    return "Bạn đã sở hữu Thẻ Sao mùa này rồi!";
            }
            if (find(items(user,"user_ticketcollection"),season) != null) return "Bạn đã sở hữu Thẻ Sao mùa này rồi!";
        }
        if (id >= 2000 && id <= 3020) for (Object value : shop) {
            Map<String,Object> item = map(value);
            int sid = integer(item.get("i_id"));
            if ((sid == 2000+season || sid == 3000+season) && lng(item.getOrDefault("i_Count",item.get("i_TotalCount"))) > 0)
                return "Bạn đã sở hữu gói vật phẩm này rồi!";
        }
        Map<String,Object> row = data.row(12,id), item = find(shop,id);
        int condition = integer(row.get("36")), max = integer(row.get("37"));
        if (item != null && max > 0 && lng(item.get("i_Count")) >= max) {
            if (condition == 1 || condition == 2) return "Vật phẩm đã đạt giới hạn mua tối đa!";
            if (condition == 5 && lng(item.get("i_PurchaseTime")) > 0 && date(lng(item.get("i_PurchaseTime"))).equals(LocalDate.now()))
                return "Vật phẩm đã đạt giới hạn mua trong ngày!";
        }
        return "";
    }

    private Result buyCheck(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c);
        if (user != null && p.get("idx") != null) {
            String error;
            try { error = eligibility(user,Integer.parseInt(str(p.get("idx")))); }
            catch (NumberFormatException e) { error = "Invalid item ID"; }
            if (!error.isEmpty()) return new Result(obj("result","fail"),obj("code",1,"errmsg",error));
        }
        return Result.ok(obj("result","ok"));
    }

    private Result checkBuyShop(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c);
        int id = integer(p.get("shop_id"));
        return Result.ok(obj("is_owner",id != 0 && user != null && !eligibility(user,id).isEmpty() ? 1 : 0));
    }

    private Result buyShop(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c);
        if (user == null) return Result.error(1,"User not found");
        int id = integer(p.getOrDefault("idx",1));
        String error = eligibility(user,id);
        if (!error.isEmpty()) return Result.error(1,error);
        Map<String,Object> row = data.row(12,id);
        int sellType = row.isEmpty() ? 1 : integer(row.get("33"));
        long price = lng(row.get("34"));
        if (id == 2003 || id == 3003) price = 50;
        boolean pass = id >= 1000 && id <= 3020;
        if ((pass || sellType == 1) && !deduct(user,"CP",price))
            return Result.error(1,pass ? "Không đủ Socola!" : "Not enough CP");
        int group = integer(row.get("31"));
        Map<String,Object> updated = null;
        List<Object> levels = normaliseAdLevels(user);
        if (AD_GROUPS.containsKey(id)) {
            int adGroup = AD_GROUPS.get(id);
            updated = find(levels,adGroup);
            long exp = lng(updated.get("i_EXP"));
            group = adLevel(adGroup,exp)[1];
            updated.put("i_EXP",exp+5); updated.put("i_Level",adLevel(adGroup,exp+5)[0]);
        }
        List<Object> rewards = data.rewards(group);
        for (Object rew : rewards) grant(user,map(rew),true);
        int season = id % 1000;
        if (pass && season >= 1 && season <= 13) {
            subscribe(user,season,1000+season);
            if (rewards.stream().noneMatch(r -> integer(map(r).get("reward_type")) == 10)) rewards.add(reward(10,1000+season,1));
        }
        List<Object> shop = normaliseShop(user);
        Set<Integer> record = new LinkedHashSet<>(List.of(id));
        if (id >= 2000 && id <= 3020) { record.add(2000+season); record.add(3000+season); }
        for (int recordId : record) {
            Map<String,Object> item = find(shop,recordId);
            boolean free = integer(row.get("36")) == 4 || AD_GROUPS.containsKey(recordId);
            if (item == null) { item = obj("i_id",recordId,"i_Level",1,"i_Count",0,"i_TotalCount",0); shop.add(item); }
            item.put("i_Count",free ? 0 : lng(item.get("i_Count"))+1);
            add(item,"i_TotalCount",1); item.put("i_PurchaseTime",now()); item.put("upd_day",now());
            if (updated != null && recordId == id) item.put("i_Level",updated.get("i_Level"));
        }
        normaliseTickets(user);
        s.state.saveUser(user);
        Map<String,Object> result = obj("u_cp",ud(user).getOrDefault("u_cp",0),"u_candy",dbl(ud(user).get("u_candy")),"reward_data",rewards);
        if (updated != null) result.put("user_ad_level",updated);
        return Result.ok(result);
    }

    private static int varietyCost(int id) {
        return switch (id) { case 1 -> 10; case 2,3 -> 30; case 4,5,6,11 -> 50; case 7,8,9,12 -> 100;
            case 10,13,14,15 -> 150; case 16,17,18,19 -> 200; default -> 50; };
    }
    private Result buyVariety(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c);
        int id = number(p,"idx",1), type = id == 11 || id == 12 ? 1 : 4;
        int rewardId = id == 11 ? 4 : id == 12 ? 1 : id >= 13 && id <= 19 ? id-2 : id;
        long value = id == 11 ? 3000 : id == 12 ? 10 : 1;
        boolean paid = deduct(user,"GP",(long)varietyCost(id));
        if (paid) {
            List<Object> shop = items(user,"user_candy_shop");
            Map<String,Object> item = find(shop,id);
            if (item == null) { item = obj("i_id",id,"i_CurrentBuyCount",0,"i_TotalBuyCount",0); shop.add(item); }
            item.put("i_CurrentBuyCount",integer(item.get("upd_day")) == today() ? lng(item.get("i_CurrentBuyCount"))+1 : 1);
            add(item,"i_TotalBuyCount",1); item.put("l_LastBuyTick",now()); item.put("upd_day",today());
            grant(user,reward(type,rewardId,value),true);
            s.state.saveUser(user);
        }
        return Result.ok(obj("u_cp",ud(user).getOrDefault("u_cp",0),"u_candy",dbl(ud(user).get("u_candy")),
                "reward_type",type,"reward_id",rewardId,"reward_value",value,"status",paid ? "Y" : "N"));
    }

    private Result buyInventory(Map<String,Object> p, Map<String,Object> c, boolean music) {
        Map<String,Object> user = user(p,c);
        int id = number(p,"idx",1);
        Price price = music ? price(2,id,"45","39") : price(3,id,"29","30");
        boolean paid = user != null && find(items(user,music ? "user_music" : "costumes"),id) == null && deduct(user,price.currency,price.amount);
        if (paid) { grant(user,reward(music ? 2 : 3,id,1),true); s.state.saveUser(user); }
        Map<String,Object> result = obj("u_gold",ud(user).getOrDefault("u_candy",0),"u_cp",ud(user).getOrDefault("u_cp",0),"u_mp",0);
        if (music) result.put("music",paid ? obj(str(id),obj("music_idx",id,"score1",0,"score2",0,"score3",0)) : obj());
        else result.put("avatar_idx",p.getOrDefault("idx",1));
        return Result.ok(result);
    }

    private Result buyItem(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c);
        if (deduct(user,"GP",(long)varietyCost(integer(p.getOrDefault("idx",1))))) s.state.saveUser(user);
        return Result.ok(obj("idx",p.getOrDefault("idx",1),"u_gold",ud(user).getOrDefault("u_candy",0),
                "u_cp",ud(user).getOrDefault("u_cp",0),"u_mp",0,"u_credit",0));
    }

    private Price upgradePrice(int table, int id, int level) {
        Map<String,Object> row = data.row(table,id);
        if (row.isEmpty()) return new Price("CP",100L);
        if (table == 7) return new Price(str(row.getOrDefault("28","CP")),lng(row.getOrDefault("29",200)) + Math.max(0,level)*(long)dbl(row.get("30")));
        return new Price(str(row.getOrDefault("29","CP")),lng(row.getOrDefault("30",100)) + (Math.max(1,level)-1)*(long)dbl(first(row.get("31"),10)));
    }

    private Result buyContents(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c), result = obj();
        if (user == null) return Result.ok(result);
        String type = str(p.get("type"));
        int id = number(p,"idx",1);
        String key = switch (type) { case "unit" -> "user_unit"; case "skill" -> "user_skill"; case "guitar" -> "user_guitar"; case "costume" -> "costumes"; default -> ""; };
        if (!key.isEmpty()) {
            List<Object> list = items(user,key);
            Map<String,Object> item = find(list,id);
            int level = item == null ? (type.equals("unit") ? 0 : 1) : integer(item.get("i_Level"));
            if (type.equals("unit") || type.equals("skill")) {
                int max = type.equals("unit") ? 20 : number(data.row(8,id),"28",20);
                if (type.equals("skill") && level >= max) result.put(key,item);
                else {
                    Price price = upgradePrice(type.equals("unit") ? 7 : 8,id,level);
                    if (deduct(user,price.currency,price.amount)) {
                        if (item == null) { item = obj("i_id",id,"i_Level",type.equals("unit") ? 1 : 2); if (type.equals("skill")) item.put("i_ActiveTime",0); list.add(item); }
                        else item.put("i_Level",Math.min(max,level+1));
                        result.put(key,item);
                    }
                }
            } else {
                Price price = type.equals("guitar") ? price(20,id,"30","31") : price(3,id,"29","30");
                if (item == null && deduct(user,price.currency,price.amount)) list.add(obj("i_id",id,"i_Level",1,"i_BonusLevel",0));
            }
        }
        s.state.saveUser(user);
        result.put("u_cp",ud(user).getOrDefault("u_cp",0)); result.put("u_candy",dbl(ud(user).get("u_candy")));
        return Result.ok(result);
    }

    private static void normaliseTickets(Map<String,Object> user) {
        Set<Integer> owned = new TreeSet<>();
        for (Object value : items(user,"user_shop")) {
            Map<String,Object> row = map(value);
            int id = integer(row.get("i_id")), season = id % 1000;
            if (lng(row.getOrDefault("i_Count",row.get("i_TotalCount"))) <= 0 || season < 1 || season > 13) continue;
            if (id >= 1001 && id <= 1013) owned.add(season);
            else if (id >= 2001 && id <= 3013) { owned.add(season); owned.add(1000+season); }
        }
        for (Object value : items(user,"user_subscribe_list")) {
            Map<String,Object> row = map(value);
            int id = integer(row.get("i_SubscribeID"));
            if (integer(row.get("i_isActive")) != 1) continue;
            if (id >= 1 && id <= 13) owned.add(id);
            else if (id >= 1001 && id <= 1013) { owned.add(id); owned.add(id%1000); }
        }
        user.put("user_ticketcollection",new ArrayList<>(owned.stream().map(id -> obj("i_id",id)).toList()));
    }

    private static Map<String,Object> attendanceState(Map<String,Object> user, String event) {
        Map<String,Object> attendance = child(user,"attendance");
        if (!(attendance.get(event) instanceof Map)) attendance.put(event,obj("day",0,"ymd",0));
        return map(attendance.get(event));
    }
    private List<Object> boardRewards(String event) { return list(map(data.boards().get(event)).get("reward_list")); }
    private int maxDay(String event) { int count = boardRewards(event).size(); return count == 0 ? 7 : count; }
    private static int claimDay(Map<String,Object> state, int max) {
        if (integer(state.get("ymd")) == today()) return number(state,"day",1);
        int day = integer(state.get("day"))+1;
        return day > max ? 1 : day;
    }
    private static Map<String,Object> eventResponse(Map<String,Object> ud, Map<String,Object> reward, String status, List<Object> expanded) {
        Map<String,Object> rew = reward == null ? obj() : reward;
        return obj("u_cp",ud.getOrDefault("u_cp",0),"u_candy",ud.getOrDefault("u_candy",0.0),
                "u_like",ud.getOrDefault("u_like",0.0),"u_fans",ud.getOrDefault("u_fans",0),
                "reward_type",rew.getOrDefault("reward_type",0),"reward_id",rew.getOrDefault("reward_id",0),
                "reward_value",rew.getOrDefault("reward_value",0),"status",status,
                "reward_data",expanded != null ? expanded : reward == null ? new ArrayList<>() : new ArrayList<>(List.of(reward)));
    }

    private Result attendance(Map<String,Object> p, Map<String,Object> c) {
        if (!s.events.isAttendanceEventEnabled(1)) return Result.ok(obj("status","N","attendance_count",0,"attendance_date",0,"max_coutinuous_attendance_count",0));
        Map<String,Object> user = user(p,c);
        boolean added = false, claimed = false;
        int current = 1;
        if (user != null) {
            Map<String,Object> ud = ud(user), state = attendanceState(user,"1");
            if (str(p.getOrDefault("type","check")).equals("add") && integer(ud.get("attendance_date")) != today()) {
                int count = integer(ud.get("attendance_count"))+1;
                ud.put("attendance_count",count); ud.put("attendance_date",today());
                ud.put("max_coutinuous_attendance_count",Math.max(integer(ud.get("max_coutinuous_attendance_count")),count));
                s.state.updateAttendance(uuid(user),count,today()); s.state.saveUser(user); added = true;
            }
            claimed = integer(state.get("ymd")) == today();
            current = claimed ? integer(state.getOrDefault("day",1)) : claimDay(state,maxDay("1"));
        }
        Map<String,Object> result = obj("status",added || !claimed ? "Y" : "N","attendance_count",current,
                "attendance_date",claimed || added ? today() : 0,"max_coutinuous_attendance_count",current);
        if (user != null && added) {
            SocialFollowers followers = new SocialFollowers(s);
            List<Object> quests = followers.normalizeQuest(user);
            if (!quests.isEmpty()) {
                Map<String,Object> quest = map(quests.getFirst());
                int id = number(quest,"i_CurrentID",1);
                if (integer(quest.get("i_isInfinity")) == 1 || id >= 900) {
                    quest.put("i_id",1); quest.put("i_CurrentID",followers.nextQuest(user,id)[0]);
                    for (int k = 1; k <= 3; k++) { quest.put("d_ConditionValue"+k,0.0); quest.put("i_RewardReceived"+k,0); }
                    quest.put("i_isInfinity",1); s.state.saveUser(user); result.put("user_follower_quest",new LinkedHashMap<>(quest));
                }
            }
        }
        return Result.ok(result);
    }

    private Result eventBoards(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c), result = obj();
        for (Map.Entry<String,Object> entry : data.boards().entrySet()) {
            String event = entry.getKey();
            if (!s.events.isAttendanceEventEnabled(event)) continue;
            Map<String,Object> board = map(entry.getValue()), state = user == null ? obj() : attendanceState(user,event);
            List<Object> rewards = list(board.get("reward_list")), overlaid = new ArrayList<>();
            int claimed = integer(state.get("day")), ymd = integer(state.get("ymd"));
            if (claimed >= (rewards.isEmpty() ? 7 : rewards.size()) && ymd != today()) { claimed = 0; ymd = 0; }
            for (Object raw : rewards) {
                Map<String,Object> reward = new LinkedHashMap<>(map(raw));
                if (claimed != 0 && integer(reward.get("reward_num")) <= claimed) {
                    reward.put("reward_flg","N"); reward.put("get_date",ymd == 0 ? reward.getOrDefault("get_date",0) : ymd);
                } else reward.put("get_date",0);
                overlaid.add(reward);
            }
            result.put(event,obj("reward_list",overlaid,"group_idx",board.getOrDefault("group_idx",0)));
        }
        return Result.ok(result);
    }

    private Map<String,Object> dayReward(String event, int day) {
        for (Object raw : boardRewards(event)) {
            Map<String,Object> row = map(raw);
            if (integer(row.get("reward_num")) == day) return reward(integer(row.get("reward_type")),integer(row.get("reward_id")),row.get("reward_value"));
        }
        return reward(1,1,100);
    }

    private Result eventReward(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c);
        String event = str(p.getOrDefault("event_idx",1));
        if (!s.events.isAttendanceEventEnabled(event)) return Result.ok(eventResponse(obj(),null,"N",null));
        if (user == null) return Result.ok(eventResponse(obj(),dayReward(event,1),"Y",null));
        Map<String,Object> ud = ud(user), state = attendanceState(user,event);
        if (integer(state.get("ymd")) == today()) return Result.ok(eventResponse(ud,null,"N",null));
        int day = claimDay(state,maxDay(event));
        Map<String,Object> rew = dayReward(event,day);
        List<Object> expanded = null;
        if (integer(rew.get("reward_type")) == 13) {
            Map<String,Object> selected = find(items(user,"user_select_reward"),"i_GroupId",number(rew,"reward_id",10));
            if (selected == null) selected = obj();
            List<Object> primary = data.rewards(number(selected,"i_RewardGroupId",10010));
            List<Object> alternate = data.rewards(number(selected,"i_AltRewardGroupId",10130));
            if (alternate.isEmpty()) alternate.add(reward(1,1,500));
            boolean owned = !primary.isEmpty() && primary.stream().allMatch(r -> {
                int type = integer(map(r).get("reward_type")), id = integer(map(r).get("reward_id"));
                return type == 3 && find(items(user,"costumes"),id) != null || type == 9 && find(items(user,"user_guitar"),id) != null;
            });
            expanded = owned ? alternate : primary;
            for (Object r : expanded) grant(user,map(r),false);
        } else grant(user,rew,false);
        state.put("day",day); state.put("ymd",today());
        if (event.equals("1")) { ud.put("attendance_count",day); ud.put("attendance_date",today()); s.state.updateAttendance(uuid(user),day,today()); }
        s.state.saveUser(user);
        return Result.ok(eventResponse(ud,rew,"Y",expanded));
    }

    private Result selectReward(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c), row = data.row(39,number(p,"i_id",1));
        if (row.isEmpty()) row = data.row(39,1);
        Map<String,Object> selected = obj("i_GroupId",number(row,"2",10),"i_RewardGroupId",number(row,"3",10010),"i_AltRewardGroupId",number(row,"4",10130));
        long seq = lng(p.get("u_seq"));
        List<Object> selectedList = new ArrayList<>(List.of(selected));
        if (user != null) {
            seq = lng(first(ud(user).get("u_seq"),seq));
            selectedList = items(user,"user_select_reward");
            int group = integer(selected.get("i_GroupId"));
            selectedList.removeIf(r -> integer(map(r).get("i_GroupId")) == group);
            selectedList.add(selected); s.state.saveUser(user);
        }
        return Result.ok(obj("u_seq",seq,"user_select_reward_list",selectedList));
    }

    private void missionCompleted(List<Object> missions) {
        new emu.leman.ggserver.game.account.DailyMissionRules(s.gameData).complete(missions);
    }

    private void initialiseMissions(Map<String,Object> user) {
        List<Object> missions = items(user,"user_daily_mission");
        if (user.containsKey("daily_mission_date") && integer(user.get("daily_mission_date")) != today()) {
            missions.clear(); user.put("claimed_daily_rewards",obj());
        }
        var rules=new emu.leman.ggserver.game.account.DailyMissionRules(s.gameData);
        for (var definition:rules.definitions()) {
            int id=integer(definition.get("i_id"));
            if(find(missions,id)==null) missions.add(obj("i_id",id,"i_Level",1,"d_Quantity",rules.attendance(definition)?1:0,"upd_date",""));
        }
        user.put("daily_mission_date",today()); missionCompleted(missions);
    }

    private static Result gameResponse(String type, int id, int level, String rewardType, long value, String status) {
        return Result.ok(obj("type",type,"id",id,"level",level,"reward_type",rewardType,"reward_value",value,"status",status,"user_follower_profile",obj()));
    }

    private Result gameReward(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c);
        String type = str(p.getOrDefault("type","daily_mission")), itemId = str(p.getOrDefault("id",1));
        int id = integer(itemId), level = Math.max(1,integer(p.getOrDefault("level",1)));
        boolean daily = type.equals("daily_mission");
        if (!daily && !type.equals("achievement")) return gameResponse(type,id,level,"None",0,"N");
        Map<String,Object> row = s.gameData.serverRows(daily ? "daily_mission" : "achievement").stream()
                .filter(r->integer(r.get("i_id"))==id).findFirst().orElseGet(LinkedHashMap::new);
        if(row.isEmpty() || integer(row.get("b_IsActive"))==0) return gameResponse(type,id,level,"None",0,"N");
        String rewardType = str(row.getOrDefault("s_RewardType","CP")).strip();
        if (rewardType.isEmpty()) rewardType = "CP";
        long value = lng(row.getOrDefault("i_Reward_"+(daily?1:level),0));
        if (user != null) {
            Map<String,Object> claims;
            if (daily) {
                if (!truth(user.get("user_daily_mission"))) initialiseMissions(user);
                Map<String,Object> days = child(user,"claimed_daily_rewards");
                String date = str(today());
                days.keySet().removeIf(k -> !k.equals(date)); claims = child(days,date);
            } else claims = child(user,"claimed_achievement_rewards");
            List<Object> progress = items(user,daily ? "user_daily_mission" : "achievements");
            Map<String,Object> item = find(progress,id);
            String claim = itemId+":"+level;
            if (claims.containsKey(claim)) return gameResponse(type,id,Math.max(item == null ? level : number(item,"i_Level",level),level+1),"0",0,"N");
            claims.put(claim,now());
            if (rewardType.equalsIgnoreCase("CP") && value > 0) grant(user,reward(1,1,value),false);
            if (item != null) item.put("i_Level",Math.max(number(item,"i_Level",1),level+1));
            else if (!daily) progress.add(obj("i_id",id,"i_Level",level+1,"d_Quantity",0.0,"s_Quantity",""));
            if (daily) missionCompleted(progress);
            if (!user.containsKey("user_event_point")) user.put("user_event_point",new ArrayList<>(List.of(obj("s_EventType","Pass","i_DataID",13,"i_Point",0,"i_Step",0,"i_ADViewTime",0,"i_Version",13))));
            for (Object raw : items(user,"user_event_point")) {
                Map<String,Object> ep = map(raw);
                if (str(ep.get("s_EventType")).equals("Pass")) {
                    add(ep,"i_Point",10); ep.put("i_Step",stepForPoints(number(ep,"i_DataID",13),lng(ep.get("i_Point")))); break;
                }
            }
            s.state.saveUser(user);
        }
        return gameResponse(type,itemId.matches("[0-9]+") ? id : 1,level+1,rewardType,value,"Y");
    }

    private Result passReward(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c);
        int group = integer(p.get("group")), step = integer(p.get("step")), type = integer(p.get("type"));
        Object version = p.getOrDefault("i_Version",5);
        Map<String,Object> claim = obj("i_SubscribeID",group,"i_Type",type,"i_Step",step,"i_UpdateTime",now(),"i_Version",version);
        List<Object> rewards = new ArrayList<>();
        for (Map<String,Object> row : data.rows(18)) if (integer(row.get("2")) == group && integer(row.get("3")) == step)
            rewards = data.rewards(integer(row.get(type != 0 ? "6" : "5")));
        if (user != null) {
            boolean paid = s.events.isPaidStarCardEnabled() && s.events.isStarPassEnabled();
            for (Object raw : items(user,"user_subscribe_list")) {
                Map<String,Object> sub = map(raw);
                int id = integer(sub.get("i_SubscribeID"));
                if ((id == group || id == 1000+group) && truth(sub.get("i_isActive"))) paid = true;
            }
            if (type == 1 && !paid) rewards.clear();
            else {
                List<Object> claims = items(user,"user_subscribe_pass_reward");
                Map<String,Object> existing = null;
                for (Object raw : claims) {
                    Map<String,Object> old = map(raw);
                    if (integer(old.get("i_SubscribeID")) == group && integer(old.get("i_Type")) == type && integer(old.get("i_Step")) == step
                            && str(old.getOrDefault("i_Version",version)).equals(str(version))) { existing = old; break; }
                }
                if (existing != null) { claim = existing; rewards.clear(); }
                else { for (Object rew : rewards) grant(user,map(rew),false); claims.add(claim); s.state.saveUser(user); }
            }
        }
        return Result.ok(obj("subscribe_pass_reward",claim,"reward_data",rewards));
    }

    private int stepForPoints(int group, long points) {
        int step = 0;
        List<Map<String,Object>> rows = data.rows(18).stream().filter(r -> integer(r.get("2")) == group)
                .sorted(Comparator.comparingInt(r -> integer(r.get("3")))).toList();
        for (Map<String,Object> row : rows) if (points >= lng(row.get("4"))) step = integer(row.get("3"));
        return step;
    }

    private int passVersion(int group) {
        Map<String,Object> row = data.row(17,group);
        return Year.now().getValue() - (row.isEmpty() ? group <= 5 ? 2020 : 2021 : number(row,"11",2020));
    }

    private Result paidEventPoint(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c);
        if (user == null) return Result.error(1,"User not found");
        int group = number(p,"i_SubscribeID",13), version = integer(p.get("i_Version")), type = integer(p.get("type"));
        if (version <= 0) version = passVersion(group);
        Map<String,Object> cfg = obj();
        for (Map<String,Object> row : data.rows(19)) if (integer(row.get("1")) == group || integer(row.get("2")) == group) { cfg = row; break; }
        int points = type == 1 ? number(cfg,"5",5000) : number(cfg,"8",2000);
        if (type == 1 && !deduct(user,"CP",(long)number(cfg,"4",50)))
            return new Result(obj("u_cp",ud(user).getOrDefault("u_cp",0),"u_candy",dbl(ud(user).get("u_candy"))),obj("code",1,"errmsg","Not enough CP"));
        List<Object> events = items(user,"user_event_point");
        long base = 0, ad = 0;
        List<Object> others = new ArrayList<>();
        for (Object raw : events) {
            Map<String,Object> ep = map(raw);
            if (str(ep.get("s_EventType")).equals("Pass") && integer(ep.get("i_DataID")) == group) {
                base = Math.max(base,lng(ep.get("i_Point"))); ad = Math.max(ad,lng(ep.get("i_ADViewTime")));
            } else others.add(raw);
        }
        long total = base+points;
        others.add(obj("s_EventType","Pass","i_DataID",group,"i_Point",total,"i_Step",stepForPoints(group,total),"i_ADViewTime",type == 0 ? now() : ad,"i_Version",version));
        user.put("user_event_point",others); s.state.saveUser(user);
        return Result.ok(obj("u_cp",ud(user).getOrDefault("u_cp",0),"u_candy",dbl(ud(user).get("u_candy")),"i_SubscribeID",group,"i_Point",total,"i_Version",version));
    }

    private Result adReward(Map<String,Object> p, Map<String,Object> c) {
        final int id, rawProfile;
        try { id = Integer.parseInt(str(p.getOrDefault("i_id",0))); rawProfile = Integer.parseInt(str(p.getOrDefault("param1",0))); }
        catch (NumberFormatException e) { return Result.ok(obj()); }
        Map<String,Object> user = user(p,c);
        if (user == null || id != 2 && !(id == 1 && rawProfile > 0))
            return Result.ok(obj("i_id",id,"user_ad_list",obj("i_id",id,"i_Count",0,"i_TotalCount",0,"i_LastViewTime",0),"reward_data",new ArrayList<>()));
        Map<String,Object> slots = child(user,"ad_rewards");
        String key = str(id);
        if (!(slots.get(key) instanceof Map)) slots.put(key,obj("i_id",id,"i_Count",0,"i_TotalCount",0,"i_LastViewTime",0,"upd_day",today()));
        Map<String,Object> slot = map(slots.get(key));
        if (integer(slot.get("upd_day")) != today()) { slot.put("i_Count",0); slot.put("upd_day",today()); }
        List<Object> rewards = new ArrayList<>();
        Map<String,Object> profile = null;
        SocialFollowers followers = new SocialFollowers(s);
        int profileId = rawProfile;
        if (id == 1) {
            profileId = followers.profileId(data.game(),rawProfile);
            List<Object> profiles = items(user,"user_follower_profile");
            profile = SocialFollowers.find(profiles,"i_id",profileId,rawProfile);
            if (profile == null) { profile = SocialFollowers.newProfile(profileId); profiles.add(profile); }
            List<Object> owned = items(user,"user_follower");
            if (SocialFollowers.find(owned,"i_id",profileId,rawProfile) == null && rawProfile != 100000)
                owned.add(obj("i_id",rawProfile,"i_Level",1,"i_BonusLevel",0));
        }
        long last = lng(slot.get("i_LastViewTime"));
        boolean allowed = integer(slot.get("i_Count")) < 5 && (id == 2 || last == 0 || now()-last >= 600);
        if (allowed) {
            if (id == 2) { StateStore.addAp(user,25); rewards.add(reward(1,11,25)); }
            else {
                Map<Integer,Map<String,Object>> levels = followers.levels(data.game(),profileId,rawProfile,1);
                int level = Math.max(1,number(profile,"i_Level",1));
                long current = lng(levels.getOrDefault(level,obj()).get("4")), next = lng(levels.getOrDefault(level+1,obj()).get("4"));
                long gain = next > current ? Math.max(100,Math.min(300,(long)((next-current)*0.1))) : 100;
                SocialFollowers.applyProfileExp(profile,levels,gain); followers.syncProfiles(user);
                rewards.add(reward(0,0,gain));
            }
            add(slot,"i_Count",1); add(slot,"i_TotalCount",1); slot.put("i_LastViewTime",now()); s.state.saveUser(user);
        }
        Map<String,Object> result = obj("i_id",id,"user_ad_list",obj("i_id",id,"i_Count",integer(slot.get("i_Count")),
                "i_TotalCount",integer(slot.get("i_TotalCount")),"i_LastViewTime",lng(slot.get("i_LastViewTime"))),"reward_data",rewards);
        if (profile != null) result.put("user_follower_profile",profile);
        return Result.ok(result);
    }
}

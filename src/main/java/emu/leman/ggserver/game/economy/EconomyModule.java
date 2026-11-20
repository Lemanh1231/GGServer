package emu.leman.ggserver.game.economy;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.CmdId;
import emu.leman.ggserver.database.StateStore;
import emu.leman.ggserver.game.social.SocialFollowers;
import emu.leman.ggserver.game.social.FollowerAccess;
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
    private final Clock clock;

    public EconomyModule(Services services) { this(services,Clock.system(emu.leman.ggserver.util.GameTime.ZONE)); }
    EconomyModule(Services services,Clock clock) { s = services; data = new EconomyData(s.config); this.clock = clock; }

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
    private long now() { return clock.instant().getEpochSecond(); }
    private int today() { return emu.leman.ggserver.util.GameTime.day(clock); }
    private static LocalDate date(long seconds) { return emu.leman.ggserver.util.GameTime.date(seconds); }
    private static void add(Map<String,Object> map, String key, long amount) { map.put(key, lng(map.get(key)) + amount); }

    private boolean deduct(Map<String,Object> user, String currency, Long price) {
        if (user == null || currency == null || currency.isEmpty() || price == null || price < 0) return false;
        if (price == 0) return true;
        String key = switch (currency.toUpperCase(Locale.ROOT)) {
            case "CP", "CHOCOLATE", "SOCOLA" -> "cp";
            case "GP", "CANDY" -> "candy";
            default -> "";
        };
        if (key.isEmpty()) return false;
        Map<String,Object> ud = ud(user);
        // Mutate the detached snapshot only: payment and inventory commit together in saveUser.
        if(key.equals("cp") ? lng(ud.get("u_cp"))<price : !Double.isFinite(dbl(ud.get("u_candy")))||dbl(ud.get("u_candy"))<price) return false;
        if (key.equals("cp")) add(ud, "u_cp", -price);
        else ud.put("u_candy", dbl(ud.get("u_candy")) - price);
        return true;
    }

    private record Price(String currency, Long amount) {}
    private Price price(int table, int id, String currencyColumn, String priceColumn) {
        Map<String,Object> row = data.row(table, id);
        if (row.isEmpty()) return new Price(null, null);
        long amount = lng(row.get(priceColumn));
        // CH2 GP acquisition is a local LevelUpMusic purchase using native MusicCost.
        // This legacy RPC has no verified dynamic price; never charge sort-order or grant free.
        if (table == 2 && integer(row.get("50"))==2 && "GP".equals(row.get("45")) && amount==0) return new Price(null,null);
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
                    AreaCurrency.addLike(user,like);
                }
                case 8 -> { fans = value; add(ud, "u_fans", fans); }
                case 11 -> StateStore.addAp(user, (int)value);
                default -> { }
            }
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
        } else if (type == 6) {
            List<Object> buffs = items(user, "user_buff");
            Map<String,Object> buff = find(buffs, id);
            if (buff == null) { buff = obj("i_id", id, "i_Level", 1); buffs.add(buff); }
            long end = lng(buff.getOrDefault("i_EndTime", buff.get("i_ExpiredTime")));
            buff.put("i_Level", Math.max(1, number(buff, "i_Level", 1)));
            buff.put("i_ActiveTime", now());
            buff.put("i_EndTime", Math.addExact(Math.max(now(), end), value));
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

    private void subscribe(Map<String,Object> user, int... ids) {
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
                if (time <= 0 || !date(time).equals(emu.leman.ggserver.util.GameTime.today(clock))) { item.put("i_Count",0); item.put("i_PurchaseTime",0); }
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
        return normaliseAdLevels(user,normaliseShop(user));
    }

    private List<Object> normaliseAdLevels(Map<String,Object> user,List<Object> shop) {
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
        Map<String,Object> product=data.row(12,id);
        if(product.isEmpty()||integer(product.getOrDefault("35",1))!=1)return "Product is unavailable";
        int method=strictInt(product.get("33"));
        if(method!=0&&method!=1)return "Unsupported payment method";
        if(strictLong(product.getOrDefault("34",0))<0)return "Invalid product price";
        if(integer(product.get("57"))==1&&!inSaleWindow(product))return "Product is outside its sale window";
        if(id>=1001&&id<=1013) {
            // A single fresh snapshot per check; do not cache operator event toggles.
            var pass=map(s.events.snapshot().get("star_pass"));
            if(!truth(pass.get("enabled"))||!truth(pass.get("paid_card_enabled"))||id%1000!=integer(pass.get("active_season")))return "Star card is unavailable";
        }
        if(StarPassShopRules.merchandise(id)&&!StarPassShopRules.saleOpen(s.events.snapshot()))return "Pass goods sale is closed";
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
        Map<String,Object> item = find(shop,id);
        int condition = integer(product.get("36")), max = integer(product.get("37"));
        if(id!=31&&condition==4&&item!=null&&lng(item.get("i_TotalCount"))>0&&now()-lng(item.get("i_PurchaseTime"))<Math.max(0,max))return "Please wait before claiming again";
        if (item != null && max > 0 && lng(item.get("i_Count")) >= max) {
            if (condition == 1 || condition == 2) return "Vật phẩm đã đạt giới hạn mua tối đa!";
            if (condition == 5 && lng(item.get("i_PurchaseTime")) > 0 && date(lng(item.get("i_PurchaseTime"))).equals(emu.leman.ggserver.util.GameTime.today(clock)))
                return "Vật phẩm đã đạt giới hạn mua trong ngày!";
        }
        return "";
    }

    private boolean inSaleWindow(Map<String,Object> row) {
        try {
            var format=DateTimeFormatter.ofPattern("uuuu-MM-dd HH:mm:ss").withResolverStyle(java.time.format.ResolverStyle.STRICT);
            var start=LocalDateTime.parse(str(row.get("59")),format);var end=LocalDateTime.parse(str(row.get("60")),format);var current=emu.leman.ggserver.util.GameTime.localNow(clock);
            return !end.isBefore(start)&&!current.isBefore(start)&&current.isBefore(end);
        } catch(java.time.format.DateTimeParseException e) {return false;}
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
        int id = strictInt(p.getOrDefault("idx",1));
        String error = eligibility(user,id);
        if (!error.isEmpty()) return Result.error(1,error);
        Map<String,Object> row = data.row(12,id);
        int sellType = row.isEmpty() ? 1 : integer(row.get("33"));
        long price = StarPassShopRules.effectivePrice(id,lng(row.get("34")));
        boolean pass = id >= 1000 && id <= 3020;
        if ((pass || sellType == 1) && !deduct(user,"CP",price))
            return Result.error(1,pass ? "Không đủ Socola!" : "Not enough CP");
        int group = integer(row.get("31"));
        Map<String,Object> updated = null;
        // eligibility already normalized this detached shop snapshot. Reuse it for
        // ad history and receipts instead of rebuilding/scanning it three times.
        List<Object> shop = items(user,"user_shop");
        List<Object> levels = normaliseAdLevels(user,shop);
        if (AD_GROUPS.containsKey(id)) {
            int adGroup = AD_GROUPS.get(id);
            updated = find(levels,adGroup);
            long exp = lng(updated.get("i_EXP"));
            group = adLevel(adGroup,exp)[1];
            updated.put("i_EXP",exp+5); updated.put("i_Level",adLevel(adGroup,exp+5)[0]);
        }
        List<Object> rewards = data.rewards(group);
        for(var definition:data.groupedRows(13,"2",group)) if(strictInt(definition.get("3"))<=0||strictInt(definition.get("4"))<=0||strictLong(definition.get("5"))<=0)return Result.error(1,"Invalid shop rewards");
        if(rewards.isEmpty()||rewards.stream().anyMatch(r->!validShopReward(map(r))))return Result.error(1,"Invalid shop rewards");
        for (Object rew : rewards) grant(user,map(rew),true);
        int season = id % 1000;
        if (pass && season >= 1 && season <= 13) {
            subscribe(user,season,1000+season);
            if (rewards.stream().noneMatch(r -> integer(map(r).get("reward_type")) == 10)) rewards.add(reward(10,1000+season,1));
        }
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

    private boolean validShopReward(Map<String,Object> reward) {
        int type=integer(reward.get("reward_type")),id=integer(reward.get("reward_id"));
        if(lng(reward.get("reward_value"))<=0)return false;
        if(type==1||type==11)return Set.of(1,2,3,4,8,11).contains(id);
        int table=switch(type){case 2->2;case 3->3;case 4->4;case 6->6;case 9->20;case 10->17;default->0;};
        return table!=0&&!data.row(table,type==10&&id>1000?id%1000:id).isEmpty();
    }
    private Result buyVariety(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c);
        int id = strictInt(p.get("idx"));
        var definition=find(list(s.gameData.varietyStore()),id);
        if(user==null||definition==null)return Result.error(1,"Invalid Variety item");
        int type=strictInt(definition.get("i_RewardType")),rewardId=strictInt(definition.get("i_RewardId"));long value=strictLong(definition.get("i_RewardQuantity")),cost=strictLong(definition.get("i_Cost"));
        if(cost<0||!validShopReward(reward(type,rewardId,value)))return Result.error(1,"Invalid Variety reward or price");
        boolean paid = deduct(user,"GP",cost);
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
        int id = strictInt(p.getOrDefault("idx",1));
        if(!emu.leman.ggserver.game.content.AcquisitionRules.allowed(s.gameData,user,music?2:3,id))return Result.error(1,"Content acquisition requirements are not met");
        Price price = music ? price(2,id,"45","39") : price(3,id,"29","30");
        if(price.amount==null)return Result.error(1,"Use the native offline music purchase path");
        boolean paid = user != null && find(items(user,music ? "user_music" : "costumes"),id) == null && deduct(user,price.currency,price.amount);
        if (paid) { grant(user,reward(music ? 2 : 3,id,1),true); s.state.saveUser(user); }
        Map<String,Object> result = obj("u_gold",ud(user).getOrDefault("u_candy",0),"u_cp",ud(user).getOrDefault("u_cp",0),"u_mp",0);
        if (music) result.put("music",paid ? obj(str(id),obj("music_idx",id,"score1",0,"score2",0,"score3",0)) : obj());
        else result.put("avatar_idx",p.getOrDefault("idx",1));
        return Result.ok(result);
    }

    private Result buyItem(Map<String,Object> p, Map<String,Object> c) {
        // No verified grant/callback contract for this unused legacy endpoint.
        return Result.error(1,"Legacy item purchase is unsupported; use Variety Store");
    }

    private Price upgradePrice(int table, int id, int level) {
        Map<String,Object> row = data.row(table,id);
        if (row.isEmpty()) return new Price(null,null);
        if (table == 7) return new Price(str(row.getOrDefault("28","CP")),lng(row.getOrDefault("29",200)) + Math.max(0,level)*(long)dbl(row.get("30")));
        return new Price(str(row.getOrDefault("29","CP")),lng(row.getOrDefault("30",100)) + (Math.max(1,level)-1)*(long)dbl(first(row.get("31"),10)));
    }

    private Result buyContents(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c), result = obj();
        if (user == null) return Result.ok(result);
        String type = str(p.get("type"));
        int id = strictInt(p.getOrDefault("idx",1));
        String key = switch (type) { case "unit" -> "user_unit"; case "skill" -> "user_skill"; case "guitar" -> "user_guitar"; case "costume" -> "costumes"; default -> ""; };
        int table=switch(type){case "unit"->7;case "skill"->8;case "guitar"->20;case "costume"->3;default->0;};
        var definition=data.row(table,id);
        if(key.isEmpty()||definition.isEmpty()) return Result.error(1,"Invalid content ID or type");
        if (!key.isEmpty()) {
            List<Object> list = items(user,key);
            Map<String,Object> item = find(list,id);
            if ((type.equals("unit") || type.equals("skill")) && item==null
                    && !emu.leman.ggserver.game.content.UpgradeAccess.unlocked(s.gameData,user,table,id))
                return Result.error(1,"Content unlock requirements are not met");
            int level = item == null ? (type.equals("unit") ? 0 : 1) : integer(item.get("i_Level"));
            if (type.equals("unit") || type.equals("skill")) {
                int max = type.equals("unit") ? number(definition,"27",20) : number(definition,"28",20);
                if (level >= max) result.put(key,item);
                else {
                    Price price = upgradePrice(type.equals("unit") ? 7 : 8,id,level);
                    if (deduct(user,price.currency,price.amount)) {
                        if (item == null) { item = obj("i_id",id,"i_Level",type.equals("unit") ? 1 : 2); if (type.equals("skill")) item.put("i_ActiveTime",0); list.add(item); }
                        else item.put("i_Level",Math.min(max,level+1));
                        result.put(key,item);
                    }
                }
            } else {
                if(item==null&&!emu.leman.ggserver.game.content.AcquisitionRules.allowed(s.gameData,user,table,id))return Result.error(1,"Content acquisition requirements are not met");
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
    private int claimDay(Map<String,Object> state, int max) {
        if (integer(state.get("ymd")) >= today()) return number(state,"day",1);
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
            if (str(p.getOrDefault("type","check")).equals("add") && integer(ud.get("attendance_date")) < today()
                    && integer(state.get("ymd")) < today()) {
                int count = integer(ud.get("attendance_count"))+1;
                ud.put("attendance_count",count); ud.put("attendance_date",today());
                ud.put("max_coutinuous_attendance_count",Math.max(integer(ud.get("max_coutinuous_attendance_count")),count));
                s.state.saveUser(user); added = true;
            }
            claimed = integer(state.get("ymd")) >= today() || integer(ud.get("attendance_date")) > today();
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
            if (claimed >= (rewards.isEmpty() ? 7 : rewards.size()) && ymd < today()) { claimed = 0; ymd = 0; }
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
            if (strictInt(row.get("reward_num")) == day) return reward(strictInt(row.get("reward_type")),strictInt(row.get("reward_id")),row.get("reward_value"));
        }
        return null;
    }

    private boolean validEventReward(Map<String,Object> reward) {
        int type=strictInt(reward.get("reward_type")),id=strictInt(reward.get("reward_id"));
        long value=strictLong(reward.get("reward_value"));
        if(value<=0||value>Integer.MAX_VALUE||id<=0)return false;
        if(type==1)return Set.of(1,2,3,4,8,11).contains(id);
        int table=switch(type){case 2->2;case 3->3;case 4->4;case 7->7;case 9->20;case 11->30;default->0;};
        return table!=0&&!data.row(table,id).isEmpty();
    }
    private List<Object> eventGroup(int group) {
        List<Object> rewards=new ArrayList<>();
        for(var row:data.rows(13))if(strictInt(row.get("2"))==group) {
            var reward=reward(strictInt(row.get("3")),strictInt(row.get("4")),row.get("5"));
            if(!validEventReward(reward))return List.of();rewards.add(reward);
        }
        return rewards;
    }

    private Result eventReward(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c);
        String event = str(p.getOrDefault("event_idx",1));
        if (!s.events.isAttendanceEventEnabled(event)) return Result.ok(eventResponse(obj(),null,"N",null));
        if (user == null) return Result.error(1,"Account not found");
        if (boardRewards(event).isEmpty()) return Result.error(1,"Attendance board is unavailable");
        Map<String,Object> ud = ud(user), state = attendanceState(user,event);
        if (integer(state.get("ymd")) >= today()
                || event.equals("1") && integer(ud.get("attendance_date")) > today())
            return Result.ok(eventResponse(ud,null,"N",null));
        int day = claimDay(state,maxDay(event));
        Map<String,Object> rew = dayReward(event,day);
        if(rew==null)return Result.error(1,"Attendance reward is unavailable");
        boolean attendanceOnly = strictInt(rew.get("reward_type"))==0
                && strictInt(rew.get("reward_id"))==0 && strictLong(rew.get("reward_value"))==0
                && data.rows(38).stream().anyMatch(row->event.equals(str(row.get("1")))
                    && "DailyReward_Select_NewUser".equals(row.get("2")));
        if(!attendanceOnly&&integer(rew.get("reward_type"))!=13&&!validEventReward(rew))return Result.error(1,"Invalid attendance reward");
        List<Object> expanded = null;
        if (integer(rew.get("reward_type")) == 13) {
            if(strictInt(rew.get("reward_id"))<=0||strictLong(rew.get("reward_value"))<=0)return Result.error(1,"Invalid selection reward");
            Map<String,Object> selected = find(items(user,"user_select_reward"),"i_GroupId",number(rew,"reward_id",10));
            if (selected == null) return Result.error(1,"Choose an event reward first");
            boolean validSelection=data.rows(39).stream().anyMatch(r->strictInt(r.get("5"))==1
                    && strictInt(r.get("2"))>0 && strictInt(r.get("2"))==strictInt(selected.get("i_GroupId"))
                    && strictInt(r.get("3"))>0 && strictInt(r.get("3"))==strictInt(selected.get("i_RewardGroupId"))
                    && strictInt(r.get("4"))>0 && strictInt(r.get("4"))==strictInt(selected.get("i_AltRewardGroupId")));
            if(!validSelection)return Result.error(1,"Invalid event selection");
            List<Object> primary = eventGroup(integer(selected.get("i_RewardGroupId")));
            List<Object> alternate = eventGroup(integer(selected.get("i_AltRewardGroupId")));
            if(primary.isEmpty()||alternate.isEmpty())return Result.error(1,"Event reward group is unavailable");
            boolean owned = !primary.isEmpty() && primary.stream().allMatch(r -> {
                int type = integer(map(r).get("reward_type")), id = integer(map(r).get("reward_id"));
                return type == 3 && find(items(user,"costumes"),id) != null || type == 9 && find(items(user,"user_guitar"),id) != null;
            });
            expanded = owned ? alternate : primary;
            for (Object r : expanded) grant(user,map(r),false);
        } else if(!attendanceOnly) grant(user,rew,false);
        state.put("day",day); state.put("ymd",today());
        if (event.equals("1")) { ud.put("attendance_count",day); ud.put("attendance_date",today()); }
        s.state.saveUser(user);
        return Result.ok(eventResponse(ud,rew,"Y",expanded));
    }

    private Result selectReward(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c);
        if(user==null)return Result.error(1,"Account not found");
        final int id;
        try {id=Integer.parseInt(str(p.get("i_id")));}catch(NumberFormatException e){return Result.error(1,"Invalid selection ID");}
        Map<String,Object> row = data.rows(39).stream().filter(r->strictInt(r.get("1"))==id).findFirst().orElse(obj());
        if(row.isEmpty()||strictInt(row.get("5"))!=1||strictInt(row.get("2"))<=0)return Result.error(1,"Event selection is unavailable");
        boolean enabled=data.rows(38).stream().anyMatch(r->"DailyReward_Select_NewUser".equals(r.get("2"))
                && strictInt(r.get("5"))==1 && s.events.isAttendanceEventEnabled(r.get("1"))
                && boardRewards(str(r.get("1"))).stream().anyMatch(v->strictInt(map(v).get("reward_type"))==13
                    && strictInt(map(v).get("reward_id"))==strictInt(row.get("2"))));
        if(!enabled)return Result.error(1,"Selection event is disabled");
        if(eventGroup(strictInt(row.get("3"))).isEmpty()||eventGroup(strictInt(row.get("4"))).isEmpty())return Result.error(1,"Event reward group is unavailable");
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
        int id = strictInt(itemId), level = strictInt(p.getOrDefault("level",1));
        boolean daily = type.equals("daily_mission");
        if (!daily && !type.equals("achievement")) return gameResponse(type,id,level,"None",0,"N");
        Map<String,Object> row = s.gameData.serverRows(daily ? "daily_mission" : "achievement").stream()
                .filter(r->integer(r.get("i_id"))==id).findFirst().orElseGet(LinkedHashMap::new);
        if(user==null || row.isEmpty() || integer(row.get("b_IsActive"))==0 || level<1
                || level>(daily?1:integer(row.get("i_MaxLevel")))) return gameResponse(type,id,level,"None",0,"N");
        String rewardType = str(row.getOrDefault("s_RewardType","CP")).strip();
        if (rewardType.isEmpty()) rewardType = "CP";
        long value = lng(row.getOrDefault("i_Reward_"+(daily?1:level),0));
        if (user != null) {
            Map<String,Object> claims;
            if (daily) {
                initialiseMissions(user);
                Map<String,Object> days = child(user,"claimed_daily_rewards");
                String date = str(today());
                days.keySet().removeIf(k -> !k.equals(date)); claims = child(days,date);
            } else claims = child(user,"claimed_achievement_rewards");
            List<Object> progress = items(user,daily ? "user_daily_mission" : "achievements");
            Map<String,Object> item = find(progress,id);
            String claim = id+":"+level;
            // Honor historical textual aliases too; never erase old receipts to migrate keys.
            boolean claimed=claims.keySet().stream().anyMatch(k->{String[] parts=k.split(":",-1);return parts.length==2&&strictInt(parts[0])==id&&strictInt(parts[1])==level;});
            if (claimed) return gameResponse(type,id,Math.max(item == null ? level : number(item,"i_Level",level),level+1),"0",0,"N");
            // Native claims carry the current offline counter before the next userSave.
            // This protocol is client-authoritative for counters, not for tiers/receipts/rewards.
            String reported=str(p.get("s_quantity"));
            if(item!=null && number(item,"i_Level",1)==level && reported.length()<=320 && reported.matches("[0-9]+(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?(?:[A-Za-z]+)?")) {
                var q=Currency.parse(reported);
                if(daily) item.put("d_Quantity",Math.max(dbl(item.get("d_Quantity")),q.floating()));
                else if(q.integer().compareTo(Currency.parse(first(truth(item.get("s_Quantity"))?item.get("s_Quantity"):null,item.get("d_Quantity"))).integer())>0) {
                    item.put("s_Quantity",q.gp());item.put("d_Quantity",q.floating());
                }
            }
            Object goal=row.get((daily?"d_Condition_":"s_Condition_")+level);
            if(item==null || number(item,"i_Level",1)!=level || goal==null || !reached(item,goal,daily))
                return gameResponse(type,id,level,"None",0,"N");
            claims.put(claim,now());
            if (rewardType.equalsIgnoreCase("CP") && value > 0) grant(user,reward(1,1,value),false);
            if (item != null) item.put("i_Level",Math.max(number(item,"i_Level",1),level+1));
            else if (!daily) progress.add(obj("i_id",id,"i_Level",level+1,"d_Quantity",0.0,"s_Quantity",""));
            if (daily) missionCompleted(progress);
            new emu.leman.ggserver.game.account.AuthContent(s).awardPassPoints(user,10);
            s.state.saveUser(user);
        }
        return gameResponse(type,itemId.matches("[0-9]+") ? id : 1,level+1,rewardType,value,"Y");
    }

    private static int strictInt(Object value) {
        try {return Integer.parseInt(str(value));} catch(NumberFormatException e) {return Integer.MIN_VALUE;}
    }
    private static long strictLong(Object value) {
        try {return Long.parseLong(str(value));} catch(NumberFormatException e) {return Long.MIN_VALUE;}
    }
    private static boolean reached(Map<String,Object> item,Object goal,boolean daily) {
        if(daily) {double quantity=dbl(item.get("d_Quantity")),target=dbl(goal);return Double.isFinite(quantity)&&Double.isFinite(target)&&target>0&&quantity>=target;}
        var target=Currency.parse(goal).integer();
        var quantity=Currency.parse(first(truth(item.get("s_Quantity"))?item.get("s_Quantity"):null,item.get("d_Quantity"))).integer();
        return target.signum()>0&&quantity.compareTo(target)>=0;
    }

    private Result passReward(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c);
        int group = strictInt(p.get("group")), step = strictInt(p.get("step")), type = strictInt(p.get("type"));
        int version = passVersion(group);
        Map<String,Object> claim = obj("i_SubscribeID",group,"i_Type",type,"i_Step",step,"i_UpdateTime",now(),"i_Version",version);
        List<Object> rewards = new ArrayList<>();
        if(user==null || !validPass(group,p) || (type!=0&&type!=1) || step<0)
            return Result.ok(obj("subscribe_pass_reward",obj(),"reward_data",rewards));
        new emu.leman.ggserver.game.account.AuthContent(s).eventPoints(user);
        long points=0;
        for(Object raw:items(user,"user_event_point")) {var ep=map(raw);if("Pass".equals(ep.get("s_EventType"))&&integer(ep.get("i_DataID"))==group&&integer(ep.get("i_Version"))==version) points=Math.max(points,lng(ep.get("i_Point")));}
        for (Map<String,Object> row : data.rows(18)) if (integer(row.get("2")) == group && integer(row.get("3")) == step)
            if(points>=lng(row.get("4"))) rewards = data.rewards(integer(row.get(type != 0 ? "6" : "5")));
        if(rewards.isEmpty()) return Result.ok(obj("subscribe_pass_reward",obj(),"reward_data",rewards));
        // A denied claim must not look like a persisted receipt to the native UI.
        if(type==1 && !paidPass(user,group))
            return Result.ok(obj("subscribe_pass_reward",obj(),"reward_data",List.of()));
        List<Object> claims = items(user,"user_subscribe_pass_reward");
        Map<String,Object> existing = null;
        for (Object raw : claims) {
            Map<String,Object> old = map(raw);
            if (integer(old.get("i_SubscribeID")) == group && integer(old.get("i_Type")) == type && integer(old.get("i_Step")) == step
                    && strictInt(old.getOrDefault("i_Version",version))==version) { existing = old; break; }
        }
        if (existing != null) { claim = existing; rewards.clear(); }
        else {
            for (Object rew : rewards) grant(user,map(rew),false);
            claims.add(claim);
            s.state.saveUser(user); // Buffs/currencies/inventory and receipt publish together.
        }
        return Result.ok(obj("subscribe_pass_reward",claim,"reward_data",rewards));
    }

    private boolean paidPass(Map<String,Object> user,int group) {
        if(s.events.isPaidStarCardEnabled() && s.events.isStarPassEnabled()) return true;
        for(Object raw:items(user,"user_subscribe_list")) {
            var sub=map(raw);int id=integer(sub.get("i_SubscribeID"));
            if((id==group || id==1000+group) && truth(sub.get("i_isActive"))) return true;
        }
        // Login projects subscriptions from durable purchases. Claims must also work
        // before that projection (e.g. imported accounts), without granting free Gold.
        for(Object raw:items(user,"user_shop")) {
            var item=map(raw);int id=integer(item.get("i_id"));
            if((id==1000+group || id==2000+group || id==3000+group)
                    && lng(item.getOrDefault("i_Count",item.get("i_TotalCount")))>0) {
                return true;
            }
        }
        return false;
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
        return Year.now(clock).getValue() - (row.isEmpty() ? group <= 5 ? 2020 : 2021 : number(row,"11",2020));
    }

    private boolean validPass(int group,Map<String,Object> p) {
        var season=data.row(17,group);
        return s.events.isStarPassEnabled() && group==s.events.activeStarPassSeason() && !season.isEmpty() && "Pass".equals(season.get("3")) && integer(season.get("7"))==1
                && (!p.containsKey("i_Version") || strictInt(p.get("i_Version"))==passVersion(group));
    }

    private Result paidEventPoint(Map<String,Object> p, Map<String,Object> c) {
        Map<String,Object> user = user(p,c);
        if (user == null) return Result.error(1,"User not found");
        int group = strictInt(p.getOrDefault("i_SubscribeID",s.events.activeStarPassSeason())), version = passVersion(group), type = strictInt(p.get("type"));
        if(!validPass(group,p)||(type!=0&&type!=1)) return Result.error(1,"Invalid Pass parameters");
        Map<String,Object> cfg = obj();
        for (Map<String,Object> row : data.rows(19)) if (integer(row.get("1")) == group || integer(row.get("2")) == group) { cfg = row; break; }
        if(cfg.isEmpty()) return Result.error(1,"Missing Pass rule");
        int points = type == 1 ? number(cfg,"5",0) : number(cfg,"8",0);
        if(points<=0) return Result.error(1,"Invalid Pass points");
        new emu.leman.ggserver.game.account.AuthContent(s).eventPoints(user);
        List<Object> events = items(user,"user_event_point");
        long base = 0, ad = 0;
        List<Object> others = new ArrayList<>();
        for (Object raw : events) {
            Map<String,Object> ep = map(raw);
            if (str(ep.get("s_EventType")).equals("Pass") && integer(ep.get("i_DataID")) == group && integer(ep.get("i_Version"))==version) {
                base = Math.max(base,lng(ep.get("i_Point"))); ad = Math.max(ad,lng(ep.get("i_ADViewTime")));
            } else others.add(raw);
        }
        if(type==0 && ad>0 && now()-ad<number(cfg,"9",600)) return Result.error(1,"Pass advertisement is cooling down");
        if(type==1&&!deduct(user,"CP",cfg.containsKey("4")?lng(cfg.get("4")):null)) return Result.error(1,"Not enough CP");
        long total = Math.addExact(base,points);
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
        var definition=s.gameData.row(32,id);
        if(definition.isEmpty() || integer(definition.get("20"))!=1)
            return Result.error(1,"Advertisement is not available");
        int limit=adCondition(definition,"DAY_LIMIT"), cooldown=adCondition(definition,"COOLTIME");
        if(limit<=0 || cooldown<0) return Result.error(1,"Invalid advertisement configuration");
        if(id==1 && !FollowerAccess.ownedProfile(s.gameData,user,rawProfile))
            return Result.error(1,"Profile ad is not available");
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
            profileId = FollowerAccess.profileId(s.gameData,rawProfile);
            profile = FollowerAccess.profile(s.gameData,user,rawProfile);
            if(followers.levels(s.gameData.data(),profileId).isEmpty()) return Result.error(1,"Invalid profile configuration");
        }
        long last = lng(slot.get("i_LastViewTime"));
        boolean allowed = integer(slot.get("i_Count")) < limit && (last == 0 || now()-last >= cooldown);
        if (allowed) {
            if (id == 2) { StateStore.addAp(user,25); rewards.add(reward(1,11,25)); }
            else {
                if(profile==null) {profile=SocialFollowers.newProfile(profileId);items(user,"user_follower_profile").add(profile);}
                Map<Integer,Map<String,Object>> levels = followers.levels(s.gameData.data(),profileId);
                int level = Math.max(1,number(profile,"i_Level",1));
                long current = lng(levels.getOrDefault(level,obj()).get("4")), next = lng(levels.getOrDefault(level+1,obj()).get("4"));
                long gain = next > current ? Math.max(100,Math.min(300,(long)((next-current)*0.1))) : 100;
                SocialFollowers.applyProfileExp(profile,levels,gain);
                rewards.add(reward(0,0,gain));
            }
            add(slot,"i_Count",1); add(slot,"i_TotalCount",1); slot.put("i_LastViewTime",now()); s.state.saveUser(user);
        }
        Map<String,Object> result = obj("i_id",id,"user_ad_list",obj("i_id",id,"i_Count",integer(slot.get("i_Count")),
                "i_TotalCount",integer(slot.get("i_TotalCount")),"i_LastViewTime",lng(slot.get("i_LastViewTime"))),"reward_data",rewards);
        if (profile != null) result.put("user_follower_profile",profile);
        return Result.ok(result);
    }

    private static int adCondition(Map<String,Object> definition,String condition) {
        for(int col:new int[]{3,5}) if(condition.equals(str(definition.get(str(col))))) {
            try { return Integer.parseInt(str(definition.get(str(col+1)))); }
            catch(NumberFormatException ignored) { return -1; }
        }
        return -1;
    }
}

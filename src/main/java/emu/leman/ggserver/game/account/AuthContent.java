package emu.leman.ggserver.game.account;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.util.GameTime;
import java.nio.file.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Login/load normalization shared with authentication and other command handlers. */
public final class AuthContent {
    private final Services s;
    public AuthContent(Services services) { s = services; }
    /** Python create_user returns starter lists, but only stores them in JSON.
     * Its next get_user replaces SQL-backed lists with empty inventory rows.
     * Keep that observable distinction until StateStore provides the same API.
     */
    public static Map<String,Object> createUser(Services s,String id,String device,String ip) {
        Map<String,Object> existing = truth(device) ? s.state.getUser(device) : null;
        if (existing == null && truth(id)) existing = s.state.getUser(id);
        Map<String,Object> user = s.state.createUser(id,device,ip);
        if (existing != null) return user;
        // StateStore reconstructs SQL inventories, omitting zero bonus fields;
        // create_user itself returns its original, un-reconstructed starters.
        for (String key : List.of("costumes","user_music","user_guitar","user_follower")) {
            for (Object raw : rows(user,key)) map(raw).putIfAbsent("i_BonusLevel",0);
        }
        Map<String,Object> persisted = new LinkedHashMap<>(user);
        for (String key : List.of("user_unit","user_skill","user_music","user_guitar","costumes","user_prop","user_follower","user_follower_giftitem","user_shop")) {
            persisted.put(key,new ArrayList<>());
        }
        s.state.saveUser(persisted);
        return user;
    }
    public static long now() { return Instant.now().getEpochSecond(); }
    public static int today() { return Integer.parseInt(GameTime.today().format(DateTimeFormatter.BASIC_ISO_DATE)); }
    public static String timestamp() { return GameTime.timestamp(); }
    public static List<Object> rows(Map<String,Object> user,String key) {
        if (!(user.get(key) instanceof List)) user.put(key,new ArrayList<>());
        return list(user.get(key));
    }
    public static Map<String,Object> object(Map<String,Object> user,String key) {
        if (!(user.get(key) instanceof Map)) user.put(key,obj());
        return map(user.get(key));
    }
    public static Map<String,Object> item(int id) { return obj("i_id",id,"i_Level",1,"i_BonusLevel",0); }
    public static Map<String,Object> music(int id) {
        Map<String,Object> row = item(id);
        row.putAll(obj("b_EncoreBonusAppear",0,"l_EncoreBonusActivateTime",0,"i_EncoreBonusFollowerId",0,"i_ChThirdActiveTime",0));
        return row;
    }
    private static List<Object> defaults(Map<String,Object> user,String key,Object... values) {
        if (!user.containsKey(key)) user.put(key,new ArrayList<>(Arrays.asList(values)));
        return rows(user,key);
    }
    public List<Object> table(String id) {
        return new ArrayList<>(s.gameData.table(id));
    }
    public Map<String,Object> config() {
        return s.events.snapshot();
    }
    public boolean enabled(String section,String field,boolean fallback) {
        Map<String,Object> part = map(config().get(section));
        return part.containsKey(field) ? truth(part.get(field)) : fallback;
    }
    public boolean starPassEnabled() { return s.events.isStarPassEnabled(); }
    public boolean paidStarCardEnabled() {
        return s.events.isPaidStarCardEnabled();
    }
    public int activeSeason() {
        return s.events.activeStarPassSeason();
    }
    public int passVersion(int season) {
        int year = season <= 5 ? 2020 : 2021;
        for (Object raw : table("17")) { Map<String,Object> row = map(raw); if (integer(row.get("1")) == season) { year = integer(first(row.get("11"),2020)); break; } }
        return GameTime.today().getYear()-year;
    }
    public int passStep(int season,long points) {
        int step = 0;
        for (Object raw : table("18")) { Map<String,Object> row = map(raw); if (integer(row.get("2")) == season && points >= lng(row.get("4"))) step = Math.max(step,integer(row.get("3"))); }
        return step;
    }

    public static List<Object> safeMergeItems(Object existing,Object incoming) {
        if (!(existing instanceof List)) return incoming instanceof List ? copy(list(incoming)) : new ArrayList<>();
        if (!(incoming instanceof List)) return list(existing);
        Map<Integer,Map<String,Object>> merged = new LinkedHashMap<>();
        for (Object raw : list(existing)) { Map<String,Object> row = map(raw); if (row.containsKey("i_id")) merged.put(integer(row.get("i_id")),new LinkedHashMap<>(row)); }
        for (Object raw : list(incoming)) {
            Map<String,Object> row = map(raw);
            if (!row.containsKey("i_id")) continue;
            int id = integer(row.get("i_id"));
            if (!merged.containsKey(id)) { merged.put(id,new LinkedHashMap<>(row)); continue; }
            Map<String,Object> prev = merged.get(id);
            int level = integer(first(prev.get("i_Level"),1)), bonus = integer(prev.get("i_BonusLevel"));
            boolean hasLevel = prev.containsKey("i_Level") || row.containsKey("i_Level"), hasBonus = prev.containsKey("i_BonusLevel") || row.containsKey("i_BonusLevel");
            prev.putAll(row);
            if (hasLevel) prev.put("i_Level",Math.max(level,integer(first(row.get("i_Level"),1))));
            if (hasBonus) prev.put("i_BonusLevel",Math.max(bonus,integer(row.get("i_BonusLevel"))));
        }
        return new ArrayList<>(merged.values());
    }
    private static Map<Integer,Map<String,Object>> index(Object value,String key) {
        Map<Integer,Map<String,Object>> result = new LinkedHashMap<>();
        for (Object raw : list(value)) { Map<String,Object> row = map(raw); int id = integer(row.get(key)); if (id != 0) result.put(id,row); }
        return result;
    }
    /** Offline music purchases/levels remain client-managed, within known catalog bounds.
     * Preserve historical rows unchanged; only new acquisitions must satisfy current gates. */
    public void mergeMusic(Map<String,Object> user,Object incoming) {
        var existing=index(user.get("user_music"),"i_id");
        List<Object> accepted=new ArrayList<>();
        for(Object raw:list(incoming)) {
            var row=new LinkedHashMap<>(map(raw));long id=nonnegativeLong(row.get("i_id")),level=nonnegativeLong(row.get("i_Level"));
            if(id<=0||id>Integer.MAX_VALUE)continue;
            var definition=s.gameData.row(2,(int)id);
            if(definition.isEmpty()||level<1||level>integer(definition.getOrDefault("28",50)))continue;
            if(row.containsKey("i_BonusLevel")&&(nonnegativeLong(row.get("i_BonusLevel"))<0||nonnegativeLong(row.get("i_BonusLevel"))>Integer.MAX_VALUE))continue;
            accepted.add(row);
        }
        // Resolve new prerequisite songs from the same snapshot, independent of DTO ordering.
        boolean changed;
        do {
            changed=false;
            for(var iterator=accepted.iterator();iterator.hasNext();) {var row=map(iterator.next());int id=integer(row.get("i_id"));
                if(!existing.containsKey(id)&&!emu.leman.ggserver.game.content.AcquisitionRules.allowed(s.gameData,user,2,id))continue;
                Object appear=row.get("b_EncoreBonusAppear"),follower=row.get("i_EncoreBonusFollowerId");
                emu.leman.ggserver.game.content.EncoreRules.mergeAppearance(s.gameData,user,existing.get(id),row,appear,follower,now());
                user.put("user_music",safeMergeItems(user.get("user_music"),List.of(row)));existing.put(id,row);iterator.remove();changed=true;
            }
        } while(changed&&!accepted.isEmpty());
    }

    /** Server-produced points target only the enabled current season/version. */
    public void awardPassPoints(Map<String,Object> user,long amount) {
        if(amount<=0||!starPassEnabled())return;
        int season=activeSeason();var definition=s.gameData.row(17,season);
        if(definition.isEmpty()||integer(definition.getOrDefault("7",1))!=1||!"Pass".equals(definition.get("3")))return;
        eventPoints(user);
        for(Object raw:rows(user,"user_event_point")) {var row=map(raw);
            if("Pass".equals(row.get("s_EventType"))&&integer(row.get("i_DataID"))==season&&integer(row.get("i_Version"))==passVersion(season)) {
                long total=Math.addExact(lng(row.get("i_Point")),amount);row.put("i_Point",total);row.put("i_Step",passStep(season,total));return;
            }
        }
    }
    public List<Object> achievements(Map<String,Object> user,Object incoming) {
        Map<Integer,Map<String,Object>> old = index(user.get("achievements"),"i_id"), sent = index(incoming == null ? user.get("achievements") : incoming,"i_id");
        List<Object> result = new ArrayList<>();
        Set<Integer> ids=new LinkedHashSet<>();
        for(int i=1;i<=10;i++) ids.add(i); // Backward-compatible baseline when a fixture has no catalog.
        for(var definition:s.gameData.table(9)) if(integer(definition.getOrDefault("52",1))==1) ids.add(integer(definition.get("1")));
        ids.addAll(old.keySet()); // Never discard a historical achievement merely because config changed.
        ids.remove(0);
        for (int i:ids) {
            Map<String,Object> prev = old.getOrDefault(i,obj()), upd = sent.getOrDefault(i,obj());
            int previousLevel = integer(first(prev.get("i_Level"),1));
            if(upd.containsKey("i_Level")&&integer(upd.get("i_Level"))<previousLevel) upd=obj(); // Stale tier must not replace current-tier counters.
            int level = Math.max(previousLevel, upd.get("i_Level") == null ? previousLevel : integer(first(upd.get("i_Level"),1)));
            result.add(obj("i_id",i,"i_Level",level,"d_Quantity",upd.getOrDefault("d_Quantity",prev.getOrDefault("d_Quantity",0)),"s_Quantity",upd.getOrDefault("s_Quantity",prev.getOrDefault("s_Quantity",""))));
        }
        user.put("achievements",result); return result;
    }
    public List<Object> dailyMissions(Map<String,Object> user,Object incoming) {
        int today = today();
        boolean reset = incoming == null && user.containsKey("daily_mission_date") && integer(user.get("daily_mission_date")) != today;
        if (reset) { user.put("claimed_daily_rewards",obj()); user.put("daily_mission_date",today); }
        Map<Integer,Map<String,Object>> old = reset ? Map.of() : index(user.get("user_daily_mission"),"i_id");
        Map<Integer,Map<String,Object>> sent = index(incoming == null ? (reset ? List.of() : user.get("user_daily_mission")) : incoming,"i_id");
        List<Object> result = new ArrayList<>();var rules=new DailyMissionRules(s.gameData);
        for (var definition:rules.definitions()) {
            int i=integer(definition.get("i_id"));
            Map<String,Object> prev = old.getOrDefault(i,obj()), upd = sent.getOrDefault(i,obj());
            int level = Math.max(1,integer(upd.getOrDefault("i_Level",prev.getOrDefault("i_Level",1))));
            long qty = Math.max(rules.attendance(definition) ? 1 : 0,lng(upd.getOrDefault("d_Quantity",prev.getOrDefault("d_Quantity",0))));
            result.add(obj("i_id",i,"i_Level",level,"d_Quantity",qty,"upd_date",upd.getOrDefault("upd_date",prev.getOrDefault("upd_date",""))));
        }
        if(!reset) rules.complete(result);
        user.put("user_daily_mission",result); user.putIfAbsent("daily_mission_date",today); return result;
    }
    public List<Object> activeBuffs(Map<String,Object> user) {
        List<Object> result = new ArrayList<>(); long now = now(); boolean premium = false;
        for (Object raw : rows(user,"user_buff")) {
            Map<String,Object> row = map(raw); long end = lng(row.getOrDefault("i_EndTime",row.get("i_ExpiredTime")));
            if (end <= now) continue;
            int id = integer(row.get("i_id")); premium |= id == 4;
            result.add(obj("i_id",id,"i_Level",Math.max(1,integer(row.getOrDefault("i_Level",1))),"i_ActiveTime",lng(first(row.get("i_ActiveTime"),now)),"i_EndTime",end));
        }
        if (!premium) result.add(obj("i_id",4,"i_Level",1,"i_ActiveTime",now,"i_EndTime",2147483647));
        user.put("user_buff",result); return result;
    }
    public List<Object> eventPoints(Map<String,Object> user) {
        List<Object> result = new ArrayList<>(); Map<String,Map<String,Object>> passes = new LinkedHashMap<>();
        for (Object raw : rows(user,"user_event_point")) {
            Map<String,Object> row = map(raw);
            if (!"Pass".equals(row.get("s_EventType"))) { result.add(row); continue; }
            int id=integer(row.get("i_DataID")),version=integer(row.getOrDefault("i_Version",passVersion(id)));
            if(id<=0) continue;
            var best=passes.computeIfAbsent(id+":"+version,k->obj("s_EventType","Pass","i_DataID",id,"i_Version",version,"i_Point",0,"i_ADViewTime",0));
            best.put("i_Point",Math.max(lng(best.get("i_Point")),lng(row.get("i_Point"))));
            best.put("i_ADViewTime",Math.max(lng(best.get("i_ADViewTime")),lng(row.get("i_ADViewTime"))));
            best.put("i_Step",passStep(id,lng(best.get("i_Point"))));
        }
        if (starPassEnabled()) {
            int active = activeSeason(); var best = passes.remove(active+":"+passVersion(active));
            result.add(best == null ? pass(active,new long[]{0,0}) : best);
        }
        result.addAll(passes.values());
        user.put("user_event_point",result);
        // Disabled events are hidden, not destroyed in the saved snapshot.
        return result.stream().filter(raw->{var row=map(raw);return !"Pass".equals(row.get("s_EventType"))
                || starPassEnabled()&&integer(row.get("i_Version"))==passVersion(integer(row.get("i_DataID")));}).toList();
    }
    /** Monotonic absolute counters retain offline gains without letting stale saves undo grants.
     * Old-season versions remain historical; a client cannot relabel them as this year's points. */
    public void mergeEventPoints(Map<String,Object> user,Object incoming) {
        eventPoints(user);
        List<Object> stored=rows(user,"user_event_point");
        for(Object raw:list(incoming)) {
            var row=map(raw);int id=integer(row.get("i_DataID"));
            if(!"Pass".equals(row.get("s_EventType")) || s.gameData.row(17,id).isEmpty()
                    || integer(row.get("i_Version"))!=passVersion(id)) continue;
            long points=nonnegativeLong(row.get("i_Point"));if(points<0) continue;
            Map<String,Object> found=null;
            for(Object old:stored) {var prev=map(old);if("Pass".equals(prev.get("s_EventType"))&&integer(prev.get("i_DataID"))==id&&integer(prev.get("i_Version"))==passVersion(id)) {found=prev;break;}}
            if(found==null) {found=pass(id,new long[]{0,0});stored.add(found);}
            found.put("i_Point",Math.max(points,lng(found.get("i_Point"))));
            // Ad times are server-owned; accepting a future client time can lock out real ads.
        }
        eventPoints(user);
    }
    private static long nonnegativeLong(Object value) {
        try {long n=Long.parseLong(str(value));return n<0?-1:n;}catch(NumberFormatException e){return -1;}
    }
    /** Native save rows intentionally omit level. Never infer ownership/levels from timers. */
    public void mergeSkills(Map<String,Object> user,Object incoming) {
        Map<Integer,Map<String,Object>> owned=index(user.get("user_skill"),"i_id");
        for(Object raw:list(incoming)) {
            var row=map(raw);int id=integer(row.get("i_id"));var prev=owned.get(id);
            if(prev==null || s.gameData.row(8,id).isEmpty()) continue;
            long on=nonnegativeLong(row.get("l_ActivateOnTicks")),off=nonnegativeLong(row.get("l_ActivateOffTicks"));
            String flag=str(row.get("b_Activate"));
            boolean active=flag.equals("1")||flag.equals("true");
            if(!Set.of("0","1","false","true").contains(flag)||on<0||off<on||off>3155378975999999999L||active&&on==0) continue;
            long oldOn=lng(prev.get("l_ActivateOnTicks")),oldOff=lng(prev.get("l_ActivateOffTicks"));
            if(on<oldOn||on==oldOn&&off<oldOff) continue;
            if(on==oldOn && off==oldOff && !truth(prev.get("b_Activate"))) active=false;
            prev.put("b_Activate",active);prev.put("l_ActivateOnTicks",on);prev.put("l_ActivateOffTicks",off);
        }
    }
    private Map<String,Object> pass(int season,long[] values) { return obj("s_EventType","Pass","i_DataID",season,"i_Point",values[0],"i_Step",passStep(season,values[0]),"i_ADViewTime",values[1],"i_Version",passVersion(season)); }
    private Set<Integer> purchases(Map<String,Object> user) {
        Set<Integer> ids = new HashSet<>();
        for (Object raw : rows(user,"user_shop")) { Map<String,Object> row = map(raw); if (lng(row.getOrDefault("i_Count",row.get("i_TotalCount")))>0) ids.add(integer(row.get("i_id"))); }
        return ids;
    }
    private static boolean bought(Set<Integer> ids,int season) { return ids.contains(1000+season)||ids.contains(2000+season)||ids.contains(3000+season); }
    public List<Object> subscriptions(Map<String,Object> user) {
        Set<Integer> bought = purchases(user), seen = new HashSet<>(); List<Object> result = new ArrayList<>();
        boolean enabled = starPassEnabled(), paid = paidStarCardEnabled(); int active = activeSeason();
        for (Object raw : rows(user,"user_subscribe_list")) {
            Map<String,Object> row = map(raw); if (row.containsKey("i_EndTime")) row.put("i_ActiveTime",lng(row.remove("i_EndTime"))); row.putIfAbsent("i_ActiveTime",0);
            int id = integer(row.get("i_SubscribeID")), season = id>1000 ? id%1000 : id;
            boolean valid = !enabled ? season!=0 && bought(bought,season) : season==active ? paid || bought(bought,active) : bought(bought,season);
            if (!valid || (enabled && !seen.add(id))) continue;
            row.put("i_isActive",1);
            if (enabled && season==active && !truth(row.get("i_ActiveTime"))) row.put("i_ActiveTime",paid ? 2147483647L : now());
            result.add(row);
        }
        if (enabled && (paid || bought(bought,active)) && !seen.contains(active) && !seen.contains(1000+active)) result.add(obj("i_SubscribeID",active,"i_isActive",1,"i_ActiveTime",paid ? 2147483647L : now()));
        user.put("user_subscribe_list",result); return result;
    }
    public List<Object> tickets(Map<String,Object> user) {
        Set<Integer> ids = new TreeSet<>();
        for (int id : purchases(user)) { int season = id%1000; if (season<1 || season>13) continue; if (id>=1001 && id<=1013) ids.add(season); else if (id>=2001 && id<=3013) { ids.add(season); ids.add(1000+season); } }
        for (Object raw : rows(user,"user_subscribe_list")) { Map<String,Object> row = map(raw); if (integer(row.get("i_isActive"))!=1) continue; int id=integer(row.get("i_SubscribeID")); if (id>=1&&id<=13) ids.add(id); else if (id>=1001&&id<=1013) { ids.add(id); ids.add(id%1000); } }
        List<Object> result = new ArrayList<>(); ids.forEach(id->result.add(obj("i_id",id))); user.put("user_ticketcollection",result); return result;
    }
    public List<Object> adList(Map<String,Object> user) {
        Map<String,Object> ads = object(user,"ad_rewards"), oldFp = map(user.get("follower_profile_ad_rewards")), oldAp = map(user.get("chapter_ap_ad_rewards"));
        if (!ads.containsKey("1") && !oldFp.isEmpty()) ads.put("1",oldFp.getOrDefault("1",oldFp.values().iterator().next()));
        if (!ads.containsKey("2") && oldAp.containsKey("2")) ads.put("2",oldAp.get("2"));
        List<Object> result = new ArrayList<>();
        for (int id=1;id<=2;id++) {
            Map<String,Object> ad = map(ads.computeIfAbsent(str(id),k->obj("i_Count",0,"i_TotalCount",0,"i_LastViewTime",0,"upd_day",today())));
            if (integer(ad.get("upd_day")) != today()) { ad.put("i_Count",0); ad.put("upd_day",today()); }
            result.add(obj("i_id",id,"i_Count",lng(ad.get("i_Count")),"i_TotalCount",lng(ad.get("i_TotalCount")),"i_LastViewTime",lng(ad.get("i_LastViewTime"))));
        }
        return result;
    }
    public List<Object> shop(Map<String,Object> user) {
        Map<Integer,Map<String,Object>> defs=index(table("12"),"1"), items=new LinkedHashMap<>(); long now=now();
        for (Object raw:rows(user,"user_shop")) {
            Map<String,Object> row=map(raw); int id=integer(row.get("i_id")); if(id<=0) continue;
            long count=lng(row.get("i_Count")), time=Math.min(now,lng(row.get("i_PurchaseTime")));
            Map<String,Object> next=obj("i_id",id,"i_Level",Math.max(1,integer(row.getOrDefault("i_Level",1))),"i_Count",count,"i_TotalCount",Math.max(count,lng(row.get("i_TotalCount"))),"i_PurchaseTime",time,"upd_day",lng(first(row.get("upd_day"),time)));
            Map<String,Object> prev=items.get(id);
            if(prev==null) items.put(id,next); else for(String key:List.of("i_Level","i_Count","i_TotalCount","i_PurchaseTime","upd_day")) prev.put(key,Math.max(lng(prev.get(key)),lng(next.get(key))));
        }
        for(var entry:items.entrySet()) {
            int id=entry.getKey(), cond=integer(defs.getOrDefault(id,obj()).get("36")); Map<String,Object> row=entry.getValue();
            if(cond==4||Set.of(2,3,18).contains(id)) row.put("i_Count",0);
            else if(cond==5||id==10012) { long time=lng(row.get("i_PurchaseTime")); if(time<=0||!GameTime.date(time).equals(GameTime.today())) { row.put("i_Count",0); row.put("i_PurchaseTime",0); } }
        }
        List<Object> result=new ArrayList<>(items.values()); user.put("user_shop",result); return result;
    }
    public List<Object> adLevels(Map<String,Object> user) {
        List<Object> shop=shop(user), result=new ArrayList<>(); Object raw=user.get("user_ad_level");
        Map<Integer,Map<String,Object>> old=index(raw instanceof Map ? List.of(raw):raw,"i_id"); int[][] groups={{200010,3},{210010,2},{220010,18}};
        for(int[] group:groups) {
            int id=group[0]; long history=0;
            for(Object value:shop) if(integer(map(value).get("i_id"))==group[1]) history=lng(map(value).get("i_TotalCount"))*5;
            long exp=lng(old.getOrDefault(id,obj()).get("i_EXP")); if(exp==1&&history==0) exp=0; exp=Math.max(exp,history); int level=1;
            for(Object value:table("37")) { Map<String,Object> row=map(value); if(integer(row.get("1"))==id&&exp>=lng(row.get("3"))) level=Math.max(level,integer(row.get("2"))); }
            result.add(obj("i_id",id,"i_Level",level,"i_EXP",exp));
            for(Object value:shop) if(integer(map(value).get("i_id"))==group[1]) map(value).put("i_Level",level);
        }
        user.put("user_ad_level",result); return result;
    }

    private static void ensure(List<Object> items,int id,Map<String,Object> value) { if(items.stream().noneMatch(raw->integer(map(raw).get("i_id"))==id)) items.add(value); }
    public Map<String,Object> contents(Map<String,Object> user) {
        List<Object> skills=rows(user,"user_skill"); Map<Integer,Map<String,Object>> charsById=index(user.get("characters"),"i_id");
        int[][] gates={{1,1,100},{2,1,300},{3,1,500},{4,1,10},{21,2,100},{22,2,300},{23,2,500},{24,2,10}};
        Set<Integer> unlocked=new LinkedHashSet<>();
        for(int[] gate:gates) if(integer(charsById.getOrDefault(gate[1],obj()).get("i_Level"))>=gate[2]) unlocked.add(gate[0]);
        skills.removeIf(raw->!unlocked.contains(integer(map(raw).get("i_id"))));
        unlocked.forEach(id->ensure(skills,id,obj("i_id",id,"i_Level",1,"b_Activate",0,"l_ActivateOnTicks",0,"l_ActivateOffTicks",0)));
        List<Object> props=rows(user,"user_prop"); if(props.isEmpty()) { props.add(obj("i_id",1,"i_Level",1)); props.add(obj("i_id",2,"i_Level",1)); }
        AuthFollowerSupport followers=new AuthFollowerSupport(this); followers.sync(user);
        // Projection must not manufacture event receipts or grant skipped historical rewards.
        Object stages=first(user.get("user_ch_third_stage"),user.get("user_chthird_stage"),new ArrayList<>()); user.put("user_ch_third_stage",stages); user.put("user_chthird_stage",stages);
        List<Object> chars=defaults(user,"characters",item(1)); ensure(chars,2,item(2));
        List<Object> costumes=defaults(user,"costumes",item(1)); ensure(costumes,201,item(201));
        List<Object> guitars=defaults(user,"user_guitar",item(1)); ensure(guitars,201,item(201));
        List<Object> music=defaults(user,"user_music",music(1)); ensure(music,201,music(201));
        shop(user); List<Object> adLevels=adLevels(user);
        Map<String,Object> result=obj("user_achievement",achievements(user,null),"user_buff",activeBuffs(user),"user_candy_shop",rows(user,"user_candy_shop"),
            "user_character",chars,"user_costume",costumes,"user_daily_mission",dailyMissions(user,null),"user_follower",defaults(user,"user_follower",item(1)),
            "user_music",music,"user_prop",props,"user_unit",rows(user,"user_unit"),"user_skill",skills,"user_shop",rows(user,"user_shop"),
            "user_messenger",followers.messenger(user),"user_guitar",guitars,"user_event_point",eventPoints(user),"user_subscribe_list",subscriptions(user),
            "user_subscribe_pass_reward",rows(user,"user_subscribe_pass_reward"),"user_ticketcollection",tickets(user),"user_follower_profile_reward",rows(user,"user_follower_profile_reward"),
            "user_follower_profile",rows(user,"user_follower_profile"),"user_follower_giftitem",defaults(user,"user_follower_giftitem",obj("i_id",1,"i_Value",141)),
            "user_follower_quest",rows(user,"user_follower_quest"),"user_chthird_stage",emu.leman.ggserver.game.content.ContentChapter.wireProgress(s.gameData,user),"user_ad_level",adLevels,"user_ad_list",adList(user),"user_select_reward",rows(user,"user_select_reward"));
        if(!user.containsKey("user_tutorial")) { List<Object> tutorials=new ArrayList<>(); for(int i=1;i<=7;i++) tutorials.add(obj("i_id",i)); user.put("user_tutorial",tutorials); }
        result.put("user_tutorial",rows(user,"user_tutorial")); return result;
    }
}

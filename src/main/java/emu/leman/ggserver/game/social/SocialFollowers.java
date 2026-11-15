package emu.leman.ggserver.game.social;

import emu.leman.ggserver.Services;
import java.util.*;
import java.util.stream.Collectors;
import static emu.leman.ggserver.util.Json.*;

/** Follower intimacy, messenger ordering and quest normalization. Stage and intimacy levels are independent. */
public final class SocialFollowers {
    private final Services services;
    public SocialFollowers(Services services) { this.services = services; }
    Map<String,Object> data() {
        return services.gameData.data();
    }
    static List<Object> rows(Map<String,Object> user, String key) {
        if (!(user.get(key) instanceof List)) user.put(key, new ArrayList<>());
        return list(user.get(key));
    }
    public static Map<String,Object> find(List<Object> rows, String key, int... ids) {
        for (Object value : rows) {
            if (!(value instanceof Map)) continue;
            Map<String,Object> row = map(value);
            for (int id : ids) if (integer(row.get(key)) == id) return row;
        }
        return null;
    }
    static Map<Integer,Map<String,Object>> index(Map<String,Object> data, String table) {
        Map<Integer,Map<String,Object>> result = new TreeMap<>();
        for (Object value : list(data.get(table))) {
            Map<String,Object> row = map(value); result.put(integer(row.get("1")), row);
        }
        return result;
    }
    public int profileId(Map<String,Object> data, int id) {
        Map<String,Object> row = index(data,"5").get(id);
        return row == null ? id : integer(first(row.get("47"), id));
    }
    public Map<Integer,Map<String,Object>> levels(Map<String,Object> data, int... ids) {
        for (int id : ids) {
            Map<Integer,Map<String,Object>> result = new TreeMap<>();
            for (Object value : list(data.get("31"))) {
                Map<String,Object> row = map(value);
                if (integer(row.get("2")) == id) result.put(integer(row.get("3")), row);
            }
            if (!result.isEmpty()) return result;
        }
        return new TreeMap<>();
    }
    public static void applyProfileExp(Map<String,Object> profile, Map<Integer,Map<String,Object>> levels, long gain) {
        if (profile == null || levels.isEmpty()) return;
        int maxLevel = Collections.max(levels.keySet()), reached = 1;
        long current = Math.max(0, lng(profile.get("d_Exp")));
        long total = Math.min(lng(levels.get(maxLevel).get("4")), current > Long.MAX_VALUE - Math.max(0,gain) ? Long.MAX_VALUE : current + Math.max(0,gain));
        for (int level : new TreeSet<>(levels.keySet())) {
            if (total >= lng(levels.get(level).get("4"))) reached = level; else break;
        }
        long candy = 0;
        for (int level : levels.keySet()) if (level <= reached) candy += Math.max(0,lng(levels.get(level).get("7")));
        profile.put("i_Level",Math.min(maxLevel,reached)); profile.put("d_Exp",total); profile.put("i_AddCandy",candy);
    }
    public static Map<String,Object> newProfile(int id) { return obj("i_id",id,"i_Level",1,"d_Exp",0,"i_AddCandy",0); }
    public List<Object> syncProfiles(Map<String,Object> user) {
        if (user == null || user.isEmpty()) return new ArrayList<>();
        Map<String,Object> data = data();
        List<Object> profiles = rows(user,"user_follower_profile");
        for (Object value : rows(user,"user_follower")) {
            int id = integer(map(value).get("i_id")); if (id == 0) continue;
            int pid = profileId(data,id);
            if (find(profiles,"i_id",pid) == null) profiles.add(newProfile(pid));
        }
        if (find(profiles,"i_id",100000) == null) profiles.add(newProfile(100000));
        Map<Integer,Map<String,Object>> byId = new LinkedHashMap<>();
        for (Object value : profiles) { Map<String,Object> profile=map(value); int id=integer(profile.get("i_id")); byId.put(id,profile); applyProfileExp(profile,levels(data,id,1),0); }
        List<Object> valid = new ArrayList<>(); Set<String> seen = new HashSet<>();
        for (Object value : rows(user,"user_follower_profile_reward")) {
            Map<String,Object> claim=map(value); int id=integer(claim.get("i_id")), level=integer(claim.get("i_RewardLevel"));
            if (byId.containsKey(id) && level <= integer(byId.get(id).get("i_Level")) && seen.add(id+":"+level)) valid.add(claim);
        }
        byId.forEach((id,profile) -> levels(data,id,1).forEach((level,row) -> {
            if (level <= integer(profile.get("i_Level")) && truth(row.get("6")) && seen.add(id+":"+level)) valid.add(obj("i_id",id,"i_RewardLevel",level));
        }));
        user.put("user_follower_profile_reward",valid); syncMessenger(user); return valid;
    }

    static List<Integer> groups(Object value) {
        List<Integer> result = new ArrayList<>();
        for(String part : str(value).split(",")) if(part.strip().matches("[0-9]+")) {
            try { result.add(Integer.parseInt(part.strip())); } catch(NumberFormatException ignored) { }
        }
        return result;
    }
    static Map<String,Object> room(int id,String groups) { return obj("i_MessengerChatRoomId",id,"i_LastConfirmIndex",0,"s_UnlockGroupList",groups,"l_UpdateTimeTicks",0); }
    public static List<Object> syncMessenger(Map<String,Object> user) {
        if(user==null || user.isEmpty()) return new ArrayList<>();
        // Native builds pending groups from Messenger.db and checks levels/prop/completed prerequisites.
        // Every saved group except the last is treated as completed: never synthesize history from ownership.
        // Preserve historical rows (including the native -1 index sentinel); no automatic account repair/reset.
        return rows(user,"user_messenger");
    }
    private static String join(List<Integer> groups) { return groups.stream().map(String::valueOf).collect(Collectors.joining(",")); }
    public static void mergeMessenger(Map<String,Object> user,Object incoming) {
        if(!(incoming instanceof List)) return;
        List<Object> rooms=rows(user,"user_messenger");
        for(Object value:list(incoming)) {
            if(!(value instanceof Map)) continue; Map<String,Object> inc=map(value), existing=find(rooms,"i_MessengerChatRoomId",integer(inc.get("i_MessengerChatRoomId")));
            if(!MessengerCatalog.valid(inc,groups(inc.get("s_UnlockGroupList")))) continue;
            if(existing==null) { if(!groups(inc.get("s_UnlockGroupList")).isEmpty()) rooms.add(copy(inc)); continue; }
            List<Integer> old=groups(existing.get("s_UnlockGroupList"));
            List<Integer> sent=inc.containsKey("s_UnlockGroupList")?groups(inc.get("s_UnlockGroupList")):old;
            // Accept append-only progress, not a stale shorter or divergent history. Do not sort group IDs.
            if(sent.size()<old.size()||!sent.subList(0,old.size()).equals(old)) continue;
            boolean advanced=sent.size()>old.size();
            if(inc.containsKey("s_UnlockGroupList")) existing.put("s_UnlockGroupList",join(sent));
            if(inc.containsKey("i_LastConfirmIndex")) existing.put("i_LastConfirmIndex",advanced?Math.max(-1,lng(inc.get("i_LastConfirmIndex"))):Math.max(lng(existing.getOrDefault("i_LastConfirmIndex",-1)),lng(inc.get("i_LastConfirmIndex"))));
            if(inc.containsKey("l_UpdateTimeTicks")) existing.put("l_UpdateTimeTicks",Math.max(lng(existing.get("l_UpdateTimeTicks")),lng(inc.get("l_UpdateTimeTicks"))));
        }
    }

    public int[] nextQuest(Map<String,Object> user,int current) { return nextQuest(user,current,index(data(),"26")); }
    private int[] nextQuest(Map<String,Object> user,int current,Map<Integer,Map<String,Object>> defs) {
        List<Integer> normal=new ArrayList<>(), infinite=new ArrayList<>(), eligible=new ArrayList<>();
        defs.forEach((id,row)->{ int type=integer(first(row.get("29"),1)); if(type==1) normal.add(id); if(type==2) infinite.add(id); });
        for(int id:normal) if(id>current) return new int[]{id,0};
        Map<Integer,Integer> owned=new HashMap<>();
        for(Object value:list(user.get("user_follower"))) { Map<String,Object> f=map(value); owned.merge(integer(f.get("i_id")),integer(first(f.get("i_Level"),1)),Math::max); }
        for(int id:infinite) { Map<String,Object> row=defs.get(id); if(owned.getOrDefault(integer(first(row.get("2"),1)),0)>=integer(first(row.get("3"),1))) eligible.add(id); }
        if(eligible.isEmpty()) eligible=infinite.isEmpty()?List.of(902):infinite;
        for(int id:eligible) if(id>current) return new int[]{id,1};
        return new int[]{eligible.getFirst(),1};
    }
    static Map<String,Object> newQuest(int current,int completed,int infinite) {
        Map<String,Object> quest=obj("i_id",1,"i_CurrentID",current,"i_CompleteID",completed,"i_isInfinity",infinite);
        resetQuest(quest); return quest;
    }
    static void resetQuest(Map<String,Object> quest) { for(int i=1;i<=3;i++) { quest.put("d_ConditionValue"+i,0.0); quest.put("i_RewardReceived"+i,0); } }
    public void autocompleteAds(Map<String,Object> quest) { autocompleteAds(quest,index(data(),"26")); }
    private void autocompleteAds(Map<String,Object> quest,Map<Integer,Map<String,Object>> defs) {
        Map<String,Object> row=defs.getOrDefault(integer(first(quest.get("i_CurrentID"),1)),obj());
        for(int i=1;i<=3;i++) if("ADViewCount".equals(str(row.get(str(1+i*3))))) {
            String key="d_ConditionValue"+i; quest.put(key,Math.max(dbl(quest.get(key)),dbl(first(row.get(str(2+i*3)),1.0))));
        }
    }
    public List<Object> normalizeQuest(Map<String,Object> user) {
        if(user==null||user.isEmpty()) return new ArrayList<>();
        List<Map<String,Object>> valid=list(user.get("user_follower_quest")).stream().filter(v->v instanceof Map).map(v->map(v)).toList();
        int current=valid.stream().mapToInt(q->integer(first(q.get("i_CurrentID"),1))).max().orElse(1);
        int completed=valid.stream().mapToInt(q->integer(q.get("i_CompleteID"))).max().orElse(0);
        Map<String,Object> quest=newQuest(current,completed,current>=900?1:0);
        for(Map<String,Object> q:valid) if(integer(first(q.get("i_CurrentID"),1))==current) for(int i=1;i<=3;i++) {
            String condition="d_ConditionValue"+i, reward="i_RewardReceived"+i;
            quest.put(condition,Math.max(dbl(quest.get(condition)),dbl(q.get(condition))));
            if(integer(q.get(reward))==1) quest.put(reward,1);
        }
        if(allReceived(quest)) { int[] next=nextQuest(user,current); quest=newQuest(next[0],Math.max(completed,current),next[1]); }
        autocompleteAds(quest); List<Object> result=new ArrayList<>(List.of(quest)); user.put("user_follower_quest",result); return result;
    }
    static boolean allReceived(Map<String,Object> quest) { return integer(quest.get("i_RewardReceived1"))==1&&integer(quest.get("i_RewardReceived2"))==1&&integer(quest.get("i_RewardReceived3"))==1; }
    public List<Object> mergeQuest(Map<String,Object> user,Object incoming) {
        List<Object> quests=normalizeQuest(user); if(quests.isEmpty()||!(incoming instanceof List)) return quests;
        Map<String,Object> quest=map(quests.getFirst());
        for(Object value:list(incoming)) { Map<String,Object> inc=map(value); if(integer(inc.get("i_CurrentID"))==integer(quest.get("i_CurrentID"))) for(int i=1;i<=3;i++) { String key="d_ConditionValue"+i; quest.put(key,Math.max(dbl(quest.get(key)),dbl(inc.get(key)))); } }
        autocompleteAds(quest); return quests;
    }
}

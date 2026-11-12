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
        try { return map(read(services.config.resource("gamedata/game_data.json"))); }
        catch (RuntimeException e) { return obj(); }
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

    private static final Map<Integer,int[]> ROUTES = new LinkedHashMap<>();
    static {
        int[] groups={1,2,6,9,13,18,20,51,62,54,74,80,88,90,91};
        for(int i=0;i<groups.length;i++) ROUTES.put(i+1,new int[]{i+1,groups[i]});
        ROUTES.put(201,new int[]{1,111}); ROUTES.put(202,new int[]{5,110});
        int[] ch2={114,127,138,178,181,186};
        for(int i=0;i<ch2.length;i++) ROUTES.put(203+i,new int[]{203+i,ch2[i]});
    }
    static List<Integer> groups(Object value) {
        List<Integer> result = new ArrayList<>();
        for(String part : str(value).split(",")) if(part.strip().matches("[0-9]+")) {
            try { result.add(Integer.parseInt(part.strip())); } catch(NumberFormatException ignored) { }
        }
        return result;
    }
    public static String mergeGroups(Object existing, Collection<Integer> required, Integer target) {
        List<Integer> original=groups(existing); Integer proceeding=target;
        if (target == null || (!original.isEmpty() && original.subList(0,original.size()-1).contains(target))) proceeding=original.isEmpty()?null:original.getLast();
        List<Integer> merged=new ArrayList<>(new LinkedHashSet<>(original));
        for(int group:required) if(!merged.contains(group)) merged.add(group);
        if(proceeding!=null) { merged.remove(proceeding); merged.add(proceeding); }
        return merged.isEmpty()?String.valueOf(target==null||target==0?1:target):merged.stream().map(String::valueOf).collect(Collectors.joining(","));
    }
    static Map<String,Object> room(int id,String groups) { return obj("i_MessengerChatRoomId",id,"i_LastConfirmIndex",0,"s_UnlockGroupList",groups,"l_UpdateTimeTicks",0); }
    static void ensureRoom(List<Object> rooms,Map<Integer,Map<String,Object>> byId,int id,List<Integer> required,Integer target) {
        Map<String,Object> room=byId.get(id);
        if(room==null) { room=room(id,""); rooms.add(room); byId.put(id,room); }
        room.put("s_UnlockGroupList",mergeGroups(room.get("s_UnlockGroupList"),required,target));
        if(integer(room.getOrDefault("i_LastConfirmIndex",-1))<0) room.put("i_LastConfirmIndex",0);
    }
    public static List<Object> syncMessenger(Map<String,Object> user) {
        if(user==null || user.isEmpty()) return new ArrayList<>();
        List<Object> rooms=rows(user,"user_messenger"); Map<Integer,Map<String,Object>> byId=new LinkedHashMap<>();
        for(Object value:rooms) { Map<String,Object> room=map(value); byId.put(integer(room.get("i_MessengerChatRoomId")),room); }
        Map<Integer,Integer> followers=new LinkedHashMap<>();
        for(Object value:rows(user,"user_follower")) { Map<String,Object> f=map(value); followers.put(integer(f.get("i_id")),integer(f.get("i_Level"))); }
        boolean ch2=followers.keySet().stream().anyMatch(id->id>=201&&id<=208);
        if(!byId.containsKey(1)) { Map<String,Object> room=room(1,"1"); rooms.add(room); byId.put(1,room); }
        int[][] corrupt={{1,75,1250,1},{2,77,1100,2},{3,44,650,6},{5,55,625,13},{6,43,250,18},{7,58,375,20},{16,79,1150,76}};
        if(!ch2) for(int[] repair:corrupt) {
            Map<String,Object> room=byId.get(repair[0]); if(room==null) continue;
            List<Integer> gs=groups(room.get("s_UnlockGroupList"));
            if(!gs.isEmpty()&&gs.getLast()==repair[1]&&followers.getOrDefault(repair[0]==16?1:repair[0],0)<repair[2]) {
                room.put("s_UnlockGroupList",str(repair[3])); room.put("i_LastConfirmIndex",0); room.put("l_UpdateTimeTicks",0);
            }
        }
        int[][] yanked={{1,111,130,136},{2,2,8,22,61,125,131,141,143,145,148},{5,157,164,167},{6,18,63,129,133,163,168},{12,109,137},{16,172,119,120},{17,174,176,177}};
        for(int[] repair:yanked) {
            Map<String,Object> room=byId.get(repair[0]); if(room==null) continue; List<Integer> gs=groups(room.get("s_UnlockGroupList"));
            if(gs.size()>1&&gs.getLast()==repair[1]) {
                Set<Integer> later=new HashSet<>(); for(int i=2;i<repair.length;i++) later.add(repair[i]);
                for(int i=0;i<gs.size()-1;i++) if(later.contains(gs.get(i))) { gs.removeLast(); gs.add(i,repair[1]); room.put("s_UnlockGroupList",join(gs)); break; }
            }
        }
        for(int fid:followers.keySet()) {
            if(fid==1||fid==201||fid==202||!ROUTES.containsKey(fid)) continue;
            int[] route=ROUTES.get(fid); Map<String,Object> room=byId.get(route[0]);
            if(room==null) { room=room(route[0],str(route[1])); rooms.add(room); byId.put(route[0],room); }
            else if(!truth(room.get("s_UnlockGroupList"))) room.put("s_UnlockGroupList",str(route[1]));
        }
        List<Integer> req=new ArrayList<>();
        if(followers.containsKey(4)) req.addAll(List.of(4,7));
        if(followers.containsKey(5)) req.addAll(List.of(10,12));
        if(any(followers,6,7)) req.addAll(List.of(15,16));
        if(followers.containsKey(8)||followers.getOrDefault(7,0)>=75) req.addAll(List.of(24,30,32,33,35,36,41,45,47));
        if(any(followers,9,10,11)||followers.getOrDefault(7,0)>=375) req.addAll(List.of(56,57));
        if(any(followers,11,12,13,14,15)) req.add(75);
        int proceeding=lastGroup(byId.get(1),1); if(proceeding==75&&followers.getOrDefault(1,0)<1250) proceeding=1;
        ensureRoom(rooms,byId,1,req,proceeding);
        if(byId.containsKey(7)&&(any(followers,9,10,11)||followers.getOrDefault(7,0)>=375||followers.getOrDefault(3,0)>=850)) {
            proceeding=lastGroup(byId.get(7),20); if(proceeding==58&&followers.getOrDefault(7,0)<375) proceeding=20;
            ensureRoom(rooms,byId,7,List.of(53,58),proceeding);
        }
        if(followers.containsKey(12)) ensureRoom(rooms,byId,16,List.of(76,78,79),81);
        else if(followers.getOrDefault(1,0)>=1250&&!byId.containsKey(16)) ensureRoom(rooms,byId,16,List.of(),76);
        if(ch2) {
            ensureRoom(rooms,byId,12,List.of(80,86,87,103),109);
            if(byId.containsKey(6)) ensureRoom(rooms,byId,6,List.of(18,26,43,106,113),null);
            if(byId.containsKey(2)) ensureRoom(rooms,byId,2,List.of(2,5,11,77,116),null);
            ensureRoom(rooms,byId,16,List.of(76,78,79,81,82,104,105,108,115,118,128,132,135,171),172);
            if(any(followers,204,205,206,207,208)||followers.getOrDefault(201,0)>=650) ensureRoom(rooms,byId,17,List.of(139,140,142,144,146,149,151,152,153,154,155,162,173),174);
            if(followers.containsKey(201)) ensureRoom(rooms,byId,1,List.of(1,75,156),111);
            if(followers.containsKey(202)) ensureRoom(rooms,byId,5,List.of(13,14,21,25,28,40,46,55,110),157);
        }
        byId.forEach((id,room)->{
            if(integer(room.getOrDefault("i_LastConfirmIndex",-1))<0) room.put("i_LastConfirmIndex",0);
            if(!truth(room.get("s_UnlockGroupList"))) room.put("s_UnlockGroupList",str(id==16?76:id==17?139:ROUTES.getOrDefault(id,new int[]{0,1})[1]));
        });
        return rooms;
    }
    private static boolean any(Map<Integer,?> map,int... ids) { for(int id:ids) if(map.containsKey(id)) return true; return false; }
    private static int lastGroup(Map<String,Object> room,int fallback) { List<Integer> gs=groups(room.get("s_UnlockGroupList")); return gs.isEmpty()?fallback:gs.getLast(); }
    private static String join(List<Integer> groups) { return groups.stream().map(String::valueOf).collect(Collectors.joining(",")); }
    public static void mergeMessenger(Map<String,Object> user,Object incoming) {
        if(!(incoming instanceof List)) return;
        List<Object> rooms=rows(user,"user_messenger");
        for(Object value:list(incoming)) {
            if(!(value instanceof Map)) continue; Map<String,Object> inc=map(value), existing=find(rooms,"i_MessengerChatRoomId",integer(inc.get("i_MessengerChatRoomId")));
            if(existing==null) rooms.add(copy(inc)); else existing.putAll(inc);
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

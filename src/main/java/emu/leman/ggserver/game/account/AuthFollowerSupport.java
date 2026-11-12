package emu.leman.ggserver.game.account;

import java.util.*;
import java.util.stream.Collectors;
import static emu.leman.ggserver.util.Json.*;
import static emu.leman.ggserver.game.account.AuthContent.*;

/** The follower normalization invoked by auth, without owning follower commands. */
public final class AuthFollowerSupport {
    private final AuthContent content;
    public AuthFollowerSupport(AuthContent content) { this.content=content; }
    private static Map<Integer,Map<String,Object>> index(Object value,String key) {
        Map<Integer,Map<String,Object>> result=new LinkedHashMap<>();
        for(Object raw:list(value)) result.put(integer(map(raw).get(key)),map(raw)); return result;
    }
    public void sync(Map<String,Object> user) {
        List<Object> profiles=rows(user,"user_follower_profile"); Map<Integer,Map<String,Object>> byId=index(profiles,"i_id"), definitions=index(content.table("5"),"1");
        for(Object raw:rows(user,"user_follower")) {
            int fid=integer(map(raw).get("i_id")); if(fid==0) continue;
            int pid=integer(first(definitions.getOrDefault(fid,obj()).get("47"),fid));
            if(!byId.containsKey(pid)) { Map<String,Object> p=profile(pid); profiles.add(p); byId.put(pid,p); }
        }
        if(!byId.containsKey(100000)) { Map<String,Object> p=profile(100000); profiles.add(p); byId.put(100000,p); }
        Map<Integer,TreeMap<Integer,Map<String,Object>>> levels=new HashMap<>();
        for(Object raw:content.table("31")) { Map<String,Object> row=map(raw); levels.computeIfAbsent(integer(row.get("2")),k->new TreeMap<>()).put(integer(row.get("3")),row); }
        for(var entry:byId.entrySet()) {
            TreeMap<Integer,Map<String,Object>> data=levels.getOrDefault(entry.getKey(),levels.getOrDefault(1,new TreeMap<>())); if(data.isEmpty()) continue;
            Map<String,Object> p=entry.getValue(); long exp=Math.min(Math.max(0,lng(p.get("d_Exp"))),lng(data.lastEntry().getValue().get("4"))); int level=1,candy=0;
            for(var row:data.entrySet()) { if(exp>=lng(row.getValue().get("4"))) level=row.getKey(); else break; }
            for(var row:data.entrySet()) if(row.getKey()<=level&&integer(row.getValue().get("7"))>0) candy+=integer(row.getValue().get("7"));
            p.put("i_Level",level); p.put("d_Exp",exp); p.put("i_AddCandy",candy);
        }
        List<Object> claims=new ArrayList<>(); Set<String> seen=new HashSet<>();
        for(Object raw:rows(user,"user_follower_profile_reward")) {
            Map<String,Object> row=map(raw); int id=integer(row.get("i_id")),level=integer(row.get("i_RewardLevel"));
            if(byId.containsKey(id)&&level<=integer(first(byId.get(id).get("i_Level"),1))&&seen.add(id+":"+level)) claims.add(row);
        }
        for(var entry:byId.entrySet()) {
            int id=entry.getKey(),level=integer(first(entry.getValue().get("i_Level"),1));
            for(var row:levels.getOrDefault(id,levels.getOrDefault(1,new TreeMap<>())).entrySet()) if(row.getKey()<=level&&truth(row.getValue().get("6"))&&seen.add(id+":"+row.getKey())) claims.add(obj("i_id",id,"i_RewardLevel",row.getKey()));
        }
        user.put("user_follower_profile_reward",claims); messenger(user); quest(user);
    }
    private static Map<String,Object> profile(int id) { return obj("i_id",id,"i_Level",1,"d_Exp",0,"i_AddCandy",0); }
    private static final Map<Integer,Integer> GROUPS=Map.ofEntries(Map.entry(1,1),Map.entry(2,2),Map.entry(3,6),Map.entry(4,9),Map.entry(5,13),Map.entry(6,18),Map.entry(7,20),Map.entry(8,51),Map.entry(9,62),Map.entry(10,54),Map.entry(11,74),Map.entry(12,80),Map.entry(13,88),Map.entry(14,90),Map.entry(15,91),Map.entry(203,114),Map.entry(204,127),Map.entry(205,138),Map.entry(206,178),Map.entry(207,181),Map.entry(208,186));
    private static List<Integer> groups(Object text) {
        List<Integer> result=new ArrayList<>(); for(String part:str(text).split(",")) if(part.strip().matches("\\d+")) result.add(integer(part.strip())); return result;
    }
    public static String mergeGroups(Object original,List<Integer> required,Integer proceeding) {
        List<Integer> old=groups(original); Integer last;
        if(proceeding!=null) last=!old.isEmpty()&&old.subList(0,old.size()-1).contains(proceeding)?old.getLast():proceeding;
        else last=old.isEmpty()?null:old.getLast();
        List<Integer> result=new ArrayList<>(new LinkedHashSet<>(old)); for(int group:required) if(!result.contains(group)) result.add(group);
        if(last!=null) { result.remove(last); result.add(last); }
        return result.isEmpty()?str(proceeding==null?1:proceeding):result.stream().map(String::valueOf).collect(Collectors.joining(","));
    }
    private static Map<String,Object> room(int id,String groups) { return obj("i_MessengerChatRoomId",id,"i_LastConfirmIndex",0,"s_UnlockGroupList",groups,"l_UpdateTimeTicks",0); }
    private static void route(List<Object> rooms,Map<Integer,Map<String,Object>> byId,int id,List<Integer> required,Integer proceeding) {
        Map<String,Object> row=byId.get(id);
        if(row==null) { row=room(id,mergeGroups("",required,proceeding)); rooms.add(row); byId.put(id,row); }
        else row.put("s_UnlockGroupList",mergeGroups(row.get("s_UnlockGroupList"),required,proceeding));
        if(integer(row.getOrDefault("i_LastConfirmIndex",-1))<0) row.put("i_LastConfirmIndex",0);
    }
    private static boolean has(Map<Integer,Integer> levels,int... ids) { for(int id:ids) if(levels.containsKey(id)) return true; return false; }
    private static int last(Map<String,Object> room,int fallback) { List<Integer> values=groups(room.get("s_UnlockGroupList")); return values.isEmpty()?fallback:values.getLast(); }
    public List<Object> messenger(Map<String,Object> user) {
        List<Object> rooms=rows(user,"user_messenger"); Map<Integer,Map<String,Object>> byId=index(rooms,"i_MessengerChatRoomId"); Map<Integer,Integer> levels=new LinkedHashMap<>();
        for(Object raw:rows(user,"user_follower")) levels.put(integer(map(raw).get("i_id")),integer(map(raw).get("i_Level")));
        boolean ch2=has(levels,201,202,203,204,205,206,207,208);
        if(!byId.containsKey(1)) { Map<String,Object> row=room(1,"1"); rooms.add(row); byId.put(1,row); }
        int[][] corrupt={{1,75,1250,1},{2,77,1100,2},{3,44,650,6},{5,55,625,13},{6,43,250,18},{7,58,375,20},{16,79,1150,76}};
        if(!ch2) for(int[] heal:corrupt) if(byId.containsKey(heal[0])&&last(byId.get(heal[0]),-1)==heal[1]&&levels.getOrDefault(heal[0]==16?1:heal[0],0)<heal[2]) byId.get(heal[0]).putAll(obj("s_UnlockGroupList",str(heal[3]),"i_LastConfirmIndex",0,"l_UpdateTimeTicks",0));
        int[][] yanked={{1,111,130,136},{2,2,8,22,61,125,131,141,143,145,148},{5,157,164,167},{6,18,63,129,133,163,168},{12,109,137},{16,172,119,120},{17,174,176,177}};
        for(int[] heal:yanked) if(byId.containsKey(heal[0])) {
            Map<String,Object> row=byId.get(heal[0]); List<Integer> values=groups(row.get("s_UnlockGroupList")); Set<Integer> later=new HashSet<>(); for(int i=2;i<heal.length;i++) later.add(heal[i]);
            if(values.size()>1&&values.getLast()==heal[1]&&values.subList(0,values.size()-1).stream().anyMatch(later::contains)) {
                values.removeLast(); int at=0; while(!later.contains(values.get(at))) at++; values.add(at,heal[1]); row.put("s_UnlockGroupList",values.stream().map(String::valueOf).collect(Collectors.joining(",")));
            }
        }
        for(int fid:levels.keySet()) if(fid!=1&&GROUPS.containsKey(fid)&&!byId.containsKey(fid)) { Map<String,Object> row=room(fid,str(GROUPS.get(fid))); rooms.add(row); byId.put(fid,row); }
        List<Integer> req=new ArrayList<>();
        if(has(levels,4)) req.addAll(List.of(4,7)); if(has(levels,5)) req.addAll(List.of(10,12)); if(has(levels,6,7)) req.addAll(List.of(15,16));
        if(has(levels,8)||levels.getOrDefault(7,0)>=75) req.addAll(List.of(24,30,32,33,35,36,41,45,47));
        if(has(levels,9,10,11)||levels.getOrDefault(7,0)>=375) req.addAll(List.of(56,57)); if(has(levels,11,12,13,14,15)) req.add(75);
        int proc=last(byId.get(1),1); if(proc==75&&levels.getOrDefault(1,0)<1250) proc=1; route(rooms,byId,1,req,proc);
        if(byId.containsKey(7)&&(has(levels,9,10,11)||levels.getOrDefault(7,0)>=375||levels.getOrDefault(3,0)>=850)) { proc=last(byId.get(7),20); if(proc==58&&levels.getOrDefault(7,0)<375) proc=20; route(rooms,byId,7,List.of(53,58),proc); }
        if(has(levels,12)) route(rooms,byId,16,List.of(76,78,79),81); else if(levels.getOrDefault(1,0)>=1250&&!byId.containsKey(16)) route(rooms,byId,16,List.of(),76);
        if(ch2) {
            route(rooms,byId,12,List.of(80,86,87,103),109);
            if(byId.containsKey(6)) route(rooms,byId,6,List.of(18,26,43,106,113),null);
            if(byId.containsKey(2)) route(rooms,byId,2,List.of(2,5,11,77,116),null);
            route(rooms,byId,16,List.of(76,78,79,81,82,104,105,108,115,118,128,132,135,171),172);
            if(has(levels,204,205,206,207,208)||levels.getOrDefault(201,0)>=650) route(rooms,byId,17,List.of(139,140,142,144,146,149,151,152,153,154,155,162,173),174);
            if(has(levels,201)) route(rooms,byId,1,List.of(1,75,156),111);
            if(has(levels,202)) route(rooms,byId,5,List.of(13,14,21,25,28,40,46,55,110),157);
        }
        for(var entry:byId.entrySet()) {
            Map<String,Object> row=entry.getValue(); int id=entry.getKey(); if(integer(row.getOrDefault("i_LastConfirmIndex",-1))<0) row.put("i_LastConfirmIndex",0);
            if(!truth(row.get("s_UnlockGroupList"))) row.put("s_UnlockGroupList",str(id==16?76:id==17?139:GROUPS.getOrDefault(id,1)));
        }
        return rooms;
    }
    public void mergeMessenger(Map<String,Object> user,Object incoming) {
        List<Object> rooms=rows(user,"user_messenger"); Map<Integer,Map<String,Object>> byId=index(rooms,"i_MessengerChatRoomId");
        for(Object raw:list(incoming)) { Map<String,Object> row=map(raw); int id=integer(row.get("i_MessengerChatRoomId")); if(byId.containsKey(id)) byId.get(id).putAll(row); else { rooms.add(row); byId.put(id,row); } }
    }
    private int nextQuest(Map<String,Object> user,int current) {
        TreeMap<Integer,Map<String,Object>> normal=new TreeMap<>(),infinite=new TreeMap<>();
        for(Object raw:content.table("26")) { Map<String,Object> row=map(raw); (integer(first(row.get("29"),1))==2?infinite:normal).put(integer(row.get("1")),row); }
        if(normal.higherKey(current)!=null) return normal.higherKey(current);
        Map<Integer,Map<String,Object>> followers=index(user.get("user_follower"),"i_id"); List<Integer> eligible=new ArrayList<>();
        infinite.forEach((id,row)->{ if(integer(followers.getOrDefault(integer(first(row.get("2"),1)),obj()).get("i_Level"))>=integer(first(row.get("3"),1))) eligible.add(id); });
        if(eligible.isEmpty()) eligible.addAll(infinite.keySet()); if(eligible.isEmpty()) eligible.add(902);
        for(int id:eligible) if(id>current) return id; return eligible.getFirst();
    }
    private void adQuest(Map<String,Object> row) {
        Map<String,Object> definition=index(content.table("26"),"1").getOrDefault(integer(first(row.get("i_CurrentID"),1)),obj());
        for(int i=1;i<=3;i++) if("ADViewCount".equals(definition.get(str(1+3*i)))) row.put("d_ConditionValue"+i,Math.max(dbl(row.get("d_ConditionValue"+i)),dbl(first(definition.get(str(2+3*i)),1.0))));
    }
    public List<Object> quest(Map<String,Object> user) {
        List<Object> raw=rows(user,"user_follower_quest"); int current=1,complete=0;
        for(Object value:raw) { Map<String,Object> row=map(value); current=Math.max(current,integer(first(row.get("i_CurrentID"),1))); complete=Math.max(complete,integer(row.get("i_CompleteID"))); }
        Map<String,Object> result=obj("i_id",1,"i_CurrentID",current,"i_CompleteID",complete,"i_isInfinity",current>=900?1:0);
        for(int i=1;i<=3;i++) {
            double count=0; int reward=0;
            for(Object value:raw) { Map<String,Object> row=map(value); if(integer(first(row.get("i_CurrentID"),1))==current) { count=Math.max(count,dbl(row.get("d_ConditionValue"+i))); if(integer(row.get("i_RewardReceived"+i))==1) reward=1; } }
            result.put("d_ConditionValue"+i,count); result.put("i_RewardReceived"+i,reward);
        }
        if(integer(result.get("i_RewardReceived1"))==1&&integer(result.get("i_RewardReceived2"))==1&&integer(result.get("i_RewardReceived3"))==1) {
            result.put("i_CompleteID",Math.max(complete,current)); int next=nextQuest(user,current); result.put("i_CurrentID",next); result.put("i_isInfinity",next>=900?1:0);
            for(int i=1;i<=3;i++) { result.put("d_ConditionValue"+i,0.0); result.put("i_RewardReceived"+i,0); }
        }
        adQuest(result); List<Object> list=new ArrayList<>(List.of(result)); user.put("user_follower_quest",list); return list;
    }
    public void mergeQuest(Map<String,Object> user,Object incoming) {
        Map<String,Object> result=map(quest(user).getFirst());
        for(Object value:list(incoming)) { Map<String,Object> row=map(value); if(integer(row.get("i_CurrentID"))==integer(result.get("i_CurrentID"))) for(int i=1;i<=3;i++) result.put("d_ConditionValue"+i,Math.max(dbl(result.get("d_ConditionValue"+i)),dbl(row.get("d_ConditionValue"+i)))); }
        adQuest(result);
    }
}

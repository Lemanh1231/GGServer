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
    public List<Object> messenger(Map<String,Object> user) {
        return emu.leman.ggserver.game.social.SocialFollowers.syncMessenger(user);
    }
    public void mergeMessenger(Map<String,Object> user,Object incoming) {
        emu.leman.ggserver.game.social.SocialFollowers.mergeMessenger(user,incoming);
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

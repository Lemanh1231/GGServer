package emu.leman.ggserver.game.social;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.CmdId;
import emu.leman.ggserver.net.HandlerRegistry;
import emu.leman.ggserver.net.Result;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;
import static emu.leman.ggserver.game.social.SocialFollowers.*;

/** Native follower and mailbox commands. All social read/modify/write operations share the state monitor. */
public final class SocialModule implements emu.leman.ggserver.game.GameModule {
    private final Services services;
    public final SocialFollowers followers;
    public final SocialPosts posts;
    public SocialModule(Services services) { this.services=services; followers=new SocialFollowers(services); posts=new SocialPosts(services); }
    @Override public String id() { return "social"; }
    @Override public void register() {
        register(CmdId.SET_FOLLOWER_PROFILE_GIFT,this::gift);
        register(CmdId.SET_USER_FOLLOWER_PROFILE_REWARD,this::profileReward);
        register(CmdId.SET_FOLLOWER_QUEST_INFINITE,this::infinite);
        register(CmdId.SET_USER_FOLLOWER_QUEST,this::quest);
        register(CmdId.GET_POST_TIME,(p,u)->obj("time",posts.getUserPosts(u).stream().mapToLong(v->lng(map(v).get("create_time"))).max().orElse(0)));
        register(CmdId.GET_POST,(p,u)->obj("server_time",System.currentTimeMillis()/1000,"post_list",posts.getUserPosts(u)));
        register(CmdId.PROVIDE_POST,(p,u)->posts.claim(u,lng(p.get("idx")),integer(p.get("type"))));
        register(CmdId.READ_POST,(p,u)->posts.read(u,lng(p.get("idx"))));
        register(CmdId.DELETE_POST,(p,u)->posts.delete(u,lng(p.get("idx")),integer(p.get("type"))));
    }
    @FunctionalInterface private interface Operation { Object apply(Map<String,Object> payload,Map<String,Object> user); }
    private void register(String name,Operation operation) {
        services.registry.register(name,(request,context)->{
            synchronized(services.state) {
                Map<String,Object> payload=HandlerRegistry.payload(request);
                String uuid=str(first(payload.get("uuid"),context.get("uuid")));
                Map<String,Object> stored=services.state.getUser(uuid);
                Map<String,Object> user=stored==null||stored.isEmpty()?null:copy(stored);
                return Result.ok(operation.apply(payload,user));
            }
        });
    }
    private Object gift(Map<String,Object> p,Map<String,Object> user) {
        if(user==null) return obj();
        int raw,id,count;
        try { raw=Integer.parseInt(str(p.getOrDefault("profile_id",1))); id=Integer.parseInt(str(p.getOrDefault("gift_id",1))); count=Integer.parseInt(str(p.getOrDefault("use_gitf_value",1))); }
        catch(RuntimeException e) { return obj(); }
        if(count<=0) return obj();
        Map<String,Object> data=followers.data(); int pid=followers.profileId(data,raw);
        Map<String,Object> gift=index(data,"30").get(id);
        List<Object> owned=rows(user,"user_follower");
        if(raw!=100000&&find(owned,"i_id",pid,raw)==null) owned.add(obj("i_id",raw,"i_Level",1,"i_BonusLevel",0));
        List<Object> profiles=rows(user,"user_follower_profile"); Map<String,Object> profile=find(profiles,"i_id",pid,raw);
        if(profile==null) { profile=newProfile(pid); profiles.add(profile); }
        if(!user.containsKey("user_follower_giftitem")) user.put("user_follower_giftitem",new ArrayList<>(List.of(obj("i_id",1,"i_Value",141))));
        List<Object> inventory=rows(user,"user_follower_giftitem"); Map<String,Object> item=find(inventory,"i_id",id);
        if(item==null) { item=obj("i_id",id,"i_Value",0); inventory.add(item); }
        long current=Math.max(0,lng(item.get("i_Value"))), used=gift==null?0:Math.min(current,count);
        item.put("i_Value",current-used);
        applyProfileExp(profile,followers.levels(data,pid,raw,1),gift==null?0:lng(gift.get("3"))*used);
        followers.syncProfiles(user); services.state.saveUser(user);
        return obj("i_gift_type",gift==null||current<=0?integer(first(gift==null?null:gift.get("2"),1)):integer(gift.get("2")),"user_follower_giftitem",item,"user_follower_profile",profile);
    }
    private Object profileReward(Map<String,Object> p,Map<String,Object> user) {
        List<Object> result=new ArrayList<>(); if(user==null) return result;
        int raw; try { raw=Integer.parseInt(str(p.get("i_id"))); } catch(RuntimeException e) { return result; }
        List<Integer> requested=groups(p.get("s_level")); if(requested.isEmpty()) return result;
        Map<String,Object> data=followers.data(); int pid=followers.profileId(data,raw);
        List<Object> claims=rows(user,"user_follower_profile_reward"), profiles=rows(user,"user_follower_profile");
        Map<String,Object> profile=find(profiles,"i_id",pid,raw);
        if(profile==null) { profile=newProfile(raw); profiles.add(profile); }
        int current=Math.max(1,integer(profile.get("i_Level")));
        Map<Integer,Map<String,Object>> rewards=index(data,"13");
        for(int level:requested) {
            if(level<1) continue;
            boolean claimed=false;
            for(Object value:claims) { Map<String,Object> claim=map(value); int id=integer(claim.get("i_id")); if((id==pid||id==raw)&&integer(claim.get("i_RewardLevel"))==level) { claimed=true; break; } }
            List<Object> granted=new ArrayList<>();
            if(!claimed) {
                Map<String,Object> milestone=null;
                for(int candidate:new int[]{pid,raw}) {
                    for(Object value:list(data.get("31"))) {
                        Map<String,Object> row=map(value);
                        if(integer(row.get("2"))==candidate&&integer(row.get("3"))==level) { milestone=row; break; }
                    }
                    if(milestone!=null) break;
                }
                if(milestone==null||current<level) continue;
                Map<String,Object> reward=rewards.get(integer(first(milestone.get("5"),-1)));
                if(reward!=null) {
                    int type=integer(reward.get("3")), id=integer(reward.get("4")); long value=lng(reward.get("5"));
                    if(type!=0&&value!=0) { SocialRewards.grant(user,type,id,value,false,false); granted.add(obj("reward_type",type,"reward_id",id,"reward_value",(double)value)); }
                }
                claims.add(obj("i_id",raw,"i_RewardLevel",level));
                if(pid!=raw) claims.add(obj("i_id",pid,"i_RewardLevel",level));
            }
            result.add(obj("i_id",raw,"i_level",level,"reward_data",granted,"user_follower_profile",profile));
        }
        services.state.saveUser(user); return result;
    }
    private Object infinite(Map<String,Object> p,Map<String,Object> user) {
        Map<String,Object> quest;
        if(user==null) quest=newQuest(902,42,1);
        else {
            quest=map(followers.normalizeQuest(user).getFirst()); int current=integer(first(quest.get("i_CurrentID"),1));
            if(current>=42) {
                int[] next=followers.nextQuest(user,Math.max(current,42)); quest.put("i_id",1); quest.put("i_CurrentID",next[0]); quest.put("i_isInfinity",1); resetQuest(quest);
                followers.autocompleteAds(quest); services.state.saveUser(user);
            }
        }
        followers.autocompleteAds(quest);
        return obj("u_seq",user==null?100001:map(user.get("userdata")).getOrDefault("u_seq",100001),"user_follower_quest",quest);
    }
    private Object quest(Map<String,Object> p,Map<String,Object> user) {
        int current=integer(first(p.get("i_CurrentID"),p.get("CurrentID"),p.get("current_id"),1));
        int sub=integer(first(p.get("i_SubID"),p.get("SubID"),p.get("sub_id"),1));
        double condition=dbl(first(p.get("d_ConditionValue"),p.get("ConditionValue"),p.get("condition_value"),0.0));
        List<Object> rewardData=new ArrayList<>(); Map<String,Object> defs=followers.data();
        Map<String,Object> quest=user==null?newQuest(current,0,current>=900?1:0):map(followers.normalizeQuest(user).getFirst());
        int active=integer(quest.get("i_CurrentID"));
        // Preserve Python's client-ID resynchronization except for proven completed normal-quest replays.
        // Infinite IDs rotate, so i_CompleteID cannot safely classify an infinite quest as a replay.
        boolean completedReplay=user!=null&&active!=current&&current>0&&current<900&&current<=integer(quest.get("i_CompleteID"));
        if(user!=null&&active!=current&&!completedReplay&&index(defs,"26").containsKey(current)) {
            quest.put("i_CurrentID",current); quest.put("i_isInfinity",current>=900?1:0);
        }
        boolean valid=sub>=1&&sub<=3&&!completedReplay;
        if(valid&&integer(quest.get("i_RewardReceived"+sub))!=1) {
            Map<String,Object> definition=index(defs,"26").getOrDefault(current,obj());
            int group=integer(definition.get(str(12+sub)));
            for(Object value:list(defs.get("13"))) {
                Map<String,Object> reward=map(value); if(group==0||integer(reward.getOrDefault("2",reward.get("1")))!=group) continue;
                int type=integer(reward.get("3")),id=integer(reward.get("4")); double amount=dbl(reward.get("5"));
                if(user!=null) SocialRewards.grant(user,type,id,amount,false,true);
                rewardData.add(obj("reward_type",type,"reward_id",id,"reward_value",amount));
            }
            quest.put("i_RewardReceived"+sub,1);
        }
        if(valid) quest.put("d_ConditionValue"+sub,Math.max(dbl(quest.get("d_ConditionValue"+sub)),condition));
        int nextFlag=0;
        if(user!=null&&allReceived(quest)) {
            int[] next=followers.nextQuest(user,current); quest.put("i_CurrentID",next[0]); quest.put("i_CompleteID",Math.max(integer(quest.get("i_CompleteID")),current)); quest.put("i_isInfinity",next[1]); resetQuest(quest); nextFlag=1;
        }
        if(user!=null) followers.autocompleteAds(quest);
        if(user!=null) services.state.saveUser(user);
        Map<String,Object> result=obj("i_CurrentID",quest.get("i_CurrentID"),"i_CompleteID",quest.get("i_CompleteID"),"next_flg",nextFlag,"reward_data",rewardData);
        for(int i=1;i<=3;i++) { result.put("d_ConditionValue"+i,quest.get("d_ConditionValue"+i)); result.put("i_RewardReceived"+i,quest.get("i_RewardReceived"+i)); }
        return result;
    }
}

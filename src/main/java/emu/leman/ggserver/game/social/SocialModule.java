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
        register(CmdId.GET_POST_TIME,(p,u)->obj("time",posts.getUserPosts(u).stream().mapToLong(v->SocialPosts.notificationTime(map(v))).max().orElse(0)));
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
                Object response=operation.apply(payload,user);
                return response instanceof Result result?result:Result.ok(response);
            }
        });
    }
    private Object gift(Map<String,Object> p,Map<String,Object> user) {
        if(user==null) return Result.error(1,"Account not found");
        int raw,id,count;
        try { raw=Integer.parseInt(str(p.get("profile_id"))); id=Integer.parseInt(str(p.get("gift_id"))); count=Integer.parseInt(str(p.get("use_gitf_value"))); }
        catch(RuntimeException e) { return Result.error(1,"Invalid gift parameters"); }
        if(count<=0) return Result.error(1,"Invalid gift quantity");
        Map<String,Object> data=followers.data(); int pid=followers.profileId(data,raw);
        Map<String,Object> gift=index(data,"30").get(id);
        if(!FollowerAccess.ownedProfile(services.gameData,user,raw) || gift==null
                || !FollowerAccess.active(gift,"18") || integer(gift.get("2"))!=1
                || !FollowerAccess.giftAllowed(services.gameData,raw,id)) return Result.error(1,"Gift or profile is not available");
        Map<Integer,Map<String,Object>> levels=followers.levels(data,pid);
        if(levels.isEmpty() || lng(gift.get("3"))<=0) return Result.error(1,"Invalid profile gift configuration");
        Map<String,Object> item=find(list(user.get("user_follower_giftitem")),"i_id",id);
        if(item==null || lng(item.get("i_Value"))<count) return Result.error(1,"Not enough gifts");
        final long gain;
        try { gain=Math.multiplyExact(lng(gift.get("3")),(long)count); }
        catch(ArithmeticException e) { return Result.error(1,"Invalid gift quantity"); }
        List<Object> profiles=rows(user,"user_follower_profile"); Map<String,Object> profile=find(profiles,"i_id",pid,raw);
        if(profile==null) { profile=newProfile(pid); profiles.add(profile); }
        item.put("i_Value",lng(item.get("i_Value"))-count);
        applyProfileExp(profile,levels,gain);
        services.state.saveUser(user);
        return obj("i_gift_type",integer(gift.get("2")),"user_follower_giftitem",item,"user_follower_profile",profile);
    }
    private Object profileReward(Map<String,Object> p,Map<String,Object> user) {
        List<Object> result=new ArrayList<>(); if(user==null) return result;
        int raw; try { raw=Integer.parseInt(str(p.get("i_id"))); } catch(RuntimeException e) { return result; }
        List<Integer> requested=groups(p.get("s_level")); if(requested.isEmpty()) return result;
        Map<String,Object> data=followers.data(); int pid=followers.profileId(data,raw);
        if(!FollowerAccess.ownedProfile(services.gameData,user,raw)) return Result.error(1,"Profile is not owned");
        Map<Integer,Map<String,Object>> levels=followers.levels(data,pid);
        if(levels.isEmpty()) return Result.error(1,"Invalid profile configuration");
        List<Object> claims=rows(user,"user_follower_profile_reward"), profiles=rows(user,"user_follower_profile");
        Map<String,Object> profile=find(profiles,"i_id",pid,raw);
        if(profile==null) { profile=newProfile(pid); profiles.add(profile); }
        Map<String,Object> calculated=copy(profile);
        applyProfileExp(calculated,levels,0);
        int current=Math.max(1,integer(calculated.get("i_Level")));
        boolean changed=false;
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
                if(milestone==null||!FollowerAccess.active(milestone,"9")||current<level) continue;
                int group=integer(first(milestone.get("5"),-1));
                for(Object rewardRow:list(data.get("13"))) {
                    Map<String,Object> reward=map(rewardRow);
                    if(group<=0 || integer(reward.get("2"))!=group) continue;
                    int type=integer(reward.get("3")), id=integer(reward.get("4")); long value=lng(reward.get("5"));
                    if(type!=0&&value!=0) { SocialRewards.grant(user,type,id,value,false,false); granted.add(obj("reward_type",type,"reward_id",id,"reward_value",(double)value)); }
                }
                claims.add(obj("i_id",raw,"i_RewardLevel",level));
                if(pid!=raw) claims.add(obj("i_id",pid,"i_RewardLevel",level));
                changed=true;
            }
            result.add(obj("i_id",raw,"i_level",level,"reward_data",granted,"user_follower_profile",profile));
        }
        if(changed) services.state.saveUser(user); return result;
    }
    private Object infinite(Map<String,Object> p,Map<String,Object> user) {
        Map<String,Object> quest;
        if(user==null) quest=newQuest(902,42,1);
        else {
            // Normalization advances a fully claimed quest. This read must not skip/reset an active one.
            quest=map(followers.normalizeQuest(user).getFirst());
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
        Map<String,Object> definition=index(defs,"26").getOrDefault(current,obj());
        boolean valid=user!=null && active==current && sub>=1 && sub<=3
                && Double.isFinite(condition) && condition>=0
                && FollowerAccess.questUnlocked(services.gameData,user,definition);
        if(valid) {
            double target=dbl(definition.get(str(2+3*sub)));
            double stored=dbl(quest.get("d_ConditionValue"+sub));
            if(!Double.isFinite(target) || target<0 || !Double.isFinite(stored)) valid=false;
            else {
                // Offline counters are client-reported; enforce unlock/sequence/threshold, not proof of play.
                double progress=Math.min(target,Math.max(stored,condition));
                quest.put("d_ConditionValue"+sub,progress);
                valid=progress>=target;
            }
        }
        if(valid&&integer(quest.get("i_RewardReceived"+sub))!=1) {
            int group=integer(definition.get(str(12+sub)));
            for(Object value:list(defs.get("13"))) {
                Map<String,Object> reward=map(value); if(group==0||integer(reward.getOrDefault("2",reward.get("1")))!=group) continue;
                int type=integer(reward.get("3")),id=integer(reward.get("4")); double amount=dbl(reward.get("5"));
                if(user!=null) SocialRewards.grant(user,type,id,amount,false,true);
                rewardData.add(obj("reward_type",type,"reward_id",id,"reward_value",amount));
            }
            quest.put("i_RewardReceived"+sub,1);
        }
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

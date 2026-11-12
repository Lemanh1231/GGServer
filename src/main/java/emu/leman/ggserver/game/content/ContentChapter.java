package emu.leman.ggserver.game.content;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.CmdId;
import emu.leman.ggserver.database.StateStore;
import emu.leman.ggserver.game.social.SocialFollowers;
import emu.leman.ggserver.net.HandlerRegistry;
import emu.leman.ggserver.net.Result;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;
import static emu.leman.ggserver.util.Json.*;
import static emu.leman.ggserver.game.content.ContentModule.*;

/** Chapter-three AP, score calculation, weighted drops and one-shot star chests. */
final class ContentChapter {
    private final Services s;
    ContentChapter(Services services) {s=services;}
    void register() {
        s.registry.register(CmdId.GET_CH_THIRD,this::get);
        s.registry.register(CmdId.CH_THIRD_STAGE,this::stage);
        s.registry.register(CmdId.CH_THIRD_STREAM_STAGE,this::stream);
        s.registry.register(CmdId.GET_CH_THIRD_STAR_REWARD,this::chest);
        s.registry.register(CmdId.SET_CH_THIRD_CHAPTER_REWARD,this::chest);
    }
    static Map<String,Object> ap(Map<String,Object> user) {
        long now=Instant.now().getEpochSecond();Map<String,Object> ap=map(user.computeIfAbsent("user_ap",k->obj("i_Ap",70,"i_FullApTime",0,"i_MaxAp",70)));
        int current=Math.max(0,Math.min(70,integer(ap.getOrDefault("i_Ap",70))));long full=lng(ap.get("i_FullApTime"));
        if(current<70&&full!=0)current=(int)Math.max(0,70-Math.max(0,(full-now+299)/300));
        if(current>=70){current=70;full=0;}else if(full==0)full=now+(70-current)*300L;
        ap.put("i_Ap",current);ap.put("i_FullApTime",full);ap.put("i_MaxAp",70);return ap;
    }
    private boolean spend(Map<String,Object> ap,long cost) {int current=integer(ap.get("i_Ap"));if(current<cost)return false;ap.put("i_Ap",current-cost);ap.put("i_FullApTime",Instant.now().getEpochSecond()+(70-current+cost)*300L);return true;}
    private List<Map<String,Object>> stages(Map<String,Object> user) {Object value=first(user.get("user_ch_third_stage"),user.get("user_chthird_stage"),new ArrayList<>());user.put("user_ch_third_stage",value);user.put("user_chthird_stage",value);return rows(user,"user_ch_third_stage");}
    private Result get(Map<String,Object> req,Map<String,Object> ctx) {
        if(!s.events.isChapter3TourEnabled())return failure(obj(),"Chapter 3 Tour is closed");Map<String,Object> user=user(s,HandlerRegistry.payload(req),ctx);if(user==null)return Result.ok(obj());
        Map<String,Object> ap=ap(user);List<Map<String,Object>> stages=stages(user);
        if(stages.isEmpty())for(Map<String,Object> row:s.gameData.table(33))if(integer(row.get("1"))>0)stages.add(obj("i_id",integer(row.get("1")),"i_ChapterId",integer(row.get("2")),"i_StageIndex",integer(row.get("3")),"i_Star","Normal".equals(row.get("34"))?3:0));
        List<Map<String,Object>> claims=rows(user,"user_ch_third_chapter_reward");s.state.saveUser(user);return Result.ok(obj("u_seq",map(user.get("userdata")).get("u_seq"),"user_ap",ap,"user_ch_third_stage",stages,"user_ch_third_chapter_reward",claims));
    }
    private Result stage(Map<String,Object> req,Map<String,Object> ctx) {
        if(!s.events.isChapter3TourEnabled())return failure(obj("clear",0),"Chapter 3 Tour is closed");
        Map<String,Object> p=HandlerRegistry.payload(req),user=user(s,p,ctx);if(user==null)return Result.ok(obj());
        int id=integer(p.get("i_id"));Map<String,Object> config=s.gameData.row(33,id),ap=ap(user);boolean story="Story".equals(config.get("34"));
        if(!story&&!spend(ap,5))return failure(obj("clear",0,"user_ap",ap),"Not enough Cookie");
        List<Map<String,Object>> stages=stages(user);Map<String,Object> stage=find(stages,id);
        if(stage==null){stage=obj("i_id",id,"i_ChapterId",id/1000,"i_StageIndex",id%1000,"i_Star",0);stages.add(stage);}
        Map<String,Object> girl=ContentProfiles.profile(user,100000);
        if(story) {
            ContentProfiles.exp(s.gameData,girl,id>=2000?200:100);s.state.saveUser(user);
            return Result.ok(obj("star",0,"character_score",0,"music_score",0,"follower_profile_score",0,"bonus_score",0,"total_score",0,"clear",1,"user_ap",ap,"user_ch_third_stage",stage,"user_music",null,"reward_data",List.of(),"bonus_follower_profile_ids",List.of(),"user_follower_profile",girl,"user_follower_profile_score",List.of()));
        }
        Map<Integer,Map<String,Object>> scores=new HashMap<>();for(Map<String,Object> row:s.gameData.table(34))scores.put(integer(row.get("2")),row);int maxLevel=scores.keySet().stream().mapToInt(Integer::intValue).max().orElse(50);
        int characterLevel=rows(user,"characters").stream().mapToInt(r->integer(r.get("i_Level"))).max().orElse(1),charScore=integer(first(score(scores,characterLevel,maxLevel).get("3"),50));
        int musicId=integer(p.get("music_id"));Map<String,Object> music=find(rows(user,"user_music"),musicId);int musicLevel=music==null?1:integer(first(music.get("i_Level"),1));
        double multiplier=integer(first(score(scores,musicLevel,maxLevel).get("5"),550))/1000.0,bonus=musicId>0&&musicId==integer(config.get("33"))?.2:0;
        int charMusic=round(charScore*(multiplier+bonus)),musicScore=round(charScore*multiplier),bonusMusic=round(charScore*bonus),followerScore=0,bonusFollowers=0;
        List<Object> profileScores=new ArrayList<>(),bonusIds=new ArrayList<>();List<Integer> recommended=ids(config.get("8"));
        for(int pid:ids(p.get("profile_ids"))) {
            Map<String,Object> profile=find(rows(user,"user_follower_profile"),pid);int level=profile==null?1:integer(profile.get("i_Level"));int base=integer(first(score(scores,level,maxLevel).get("4"),100)),extra=recommended.contains(pid)?round(base*.2):0;
            if(recommended.contains(pid)){bonusIds.add(pid);bonusFollowers+=extra;}profileScores.add(obj("i_id",pid,"score",base,"bonus_score",extra));followerScore+=base;
        }
        int one=integer(first(config.get("5"),1)),two=integer(first(config.get("6"),one)),three=integer(first(config.get("7"),two)),total=charMusic+followerScore+bonusFollowers;
        int star=total>=three?3:total>=two?2:total>=one?1:0;if(id==1001){star=3;total=Math.max(total,three>0?three:180);}int clear=star>0?1:0;
        stage.put("i_Star",Math.max(star,integer(stage.get("i_Star"))));List<Map<String,Object>> rewards=clear>0?drops(config):List.of();gifts(user,rewards);
        if(clear>0)ContentProfiles.exp(s.gameData,girl,id>=2000?200:100);s.state.saveUser(user);
        return Result.ok(obj("star",star,"character_score",charScore,"music_score",musicScore,"follower_profile_score",followerScore,"bonus_score",bonusMusic+bonusFollowers,"total_score",total,"clear",clear,"user_ap",ap,"user_ch_third_stage",stage,"user_music",music,"reward_data",rewards,"bonus_follower_profile_ids",bonusIds,"user_follower_profile",girl,"bonus_music_score",bonusMusic,"user_follower_profile_score",profileScores));
    }
    private static Map<String,Object> score(Map<Integer,Map<String,Object>> scores,int level,int maximum) {return scores.getOrDefault(Math.min(Math.max(1,level),maximum),obj());}
    private static int round(double value) {return (int)Math.rint(value);}
    private static List<Integer> ids(Object value) {List<Integer> out=new ArrayList<>();for(String token:str(value).split(","))try{out.add(Integer.parseInt(token.trim()));}catch(NumberFormatException ignored){}return out;}
    private List<Map<String,Object>> drops(Map<String,Object> stage) {
        List<Map<String,Object>> out=new ArrayList<>();
        for(int group:ids(stage.get("37"))) {
            List<Map<String,Object>> candidates=s.gameData.table(36).stream().filter(r->integer(r.get("1"))==group).toList();double total=candidates.stream().mapToDouble(r->dbl(first(r.get("5"),1))).sum();if(candidates.isEmpty()||total<=0)continue;
            double pick=ThreadLocalRandom.current().nextDouble(total);Map<String,Object> chosen=candidates.getLast();for(Map<String,Object> candidate:candidates){pick-=dbl(first(candidate.get("5"),1));if(pick<0){chosen=candidate;break;}}
            int amount=integer(chosen.get("4"));if(amount>0)out.add(obj("reward_type",integer(first(chosen.get("2"),11)),"reward_id",integer(chosen.get("3")),"reward_value",amount));
        }
        return out;
    }
    private static void gifts(Map<String,Object> user,List<Map<String,Object>> rewards) {for(Map<String,Object> reward:rewards)if(integer(reward.get("reward_type"))==11&&integer(reward.get("reward_id"))>0){int id=integer(reward.get("reward_id"));Map<String,Object> gift=find(rows(user,"user_follower_giftitem"),id);if(gift==null){gift=obj("i_id",id,"i_Value",0);rows(user,"user_follower_giftitem").add(gift);}gift.put("i_Value",integer(gift.get("i_Value"))+integer(reward.get("reward_value")));}}
    private Result stream(Map<String,Object> req,Map<String,Object> ctx) {
        Map<String,Object> p=HandlerRegistry.payload(req),user=user(s,p,ctx);if(user==null)return Result.ok(obj());int id=integer(p.get("i_id")),count=Math.max(1,integer(first(p.get("count"),1)));Map<String,Object> ap=ap(user);
        if(!spend(ap,count*5L))return failure(obj("clear",0,"user_ap",ap),"Not enough Cookie");
        Map<String,Object> rewardData=obj(),config=s.gameData.row(33,id);for(int i=1;i<=count;i++){List<Map<String,Object>> rewards=drops(config);rewardData.put(String.valueOf(i),rewards);gifts(user,rewards);}
        Map<String,Object> girl=ContentProfiles.profile(user,100000);ContentProfiles.exp(s.gameData,girl,(id>=2000?200L:100L)*count);s.state.saveUser(user);return Result.ok(obj("i_id",id,"user_ap",ap,"user_follower_profile",girl,"reward_data",rewardData));
    }
    private Result chest(Map<String,Object> req,Map<String,Object> ctx) {
        Map<String,Object> p=HandlerRegistry.payload(req),user=user(s,p,ctx);if(user==null)return Result.ok(obj());int chapter=integer(p.get("i_id")),number=integer(p.get("reward_num"));Map<String,Object> ap=ap(user),config=s.gameData.row(35,chapter);
        boolean valid=!config.isEmpty()&&number>=1&&number<=3;int group=valid?integer(config.get(String.valueOf(3+(number-1)*2))):0,required=valid?integer(config.get(String.valueOf(4+(number-1)*2))):0;
        int earned=stages(user).stream().filter(r->integer(r.get("i_ChapterId"))==chapter).mapToInt(r->integer(r.get("i_Star"))).sum();List<Map<String,Object>> claims=rows(user,"user_ch_third_chapter_reward");Map<String,Object> claim=find(claims,chapter);if(claim==null){claim=obj("i_id",chapter,"i_ReceivedReward1",0,"i_ReceivedReward2",0,"i_ReceivedReward3",0);claims.add(claim);}
        String field="i_ReceivedReward"+number;List<Map<String,Object>> rewards=new ArrayList<>();
        if(valid&&earned>=required&&integer(claim.get(field))==0){claim.put(field,1);for(Map<String,Object> row:s.gameData.table(13))if(integer(row.get("2"))==group)rewards.add(obj("reward_type",integer(row.get("3")),"reward_id",integer(row.get("4")),"reward_value",dbl(row.get("5"))));grant(user,rewards);}
        s.state.saveUser(user);return Result.ok(obj("i_id",chapter,"reward_num",number,"user_ap",ap,"reward_data",rewards));
    }
    private void grant(Map<String,Object> user,List<Map<String,Object>> rewards) {
        gifts(user,rewards);Map<String,Object> ud=map(user.get("userdata"));
        for(Map<String,Object> reward:rewards) {
            int type=integer(reward.get("reward_type")),id=integer(reward.get("reward_id"));double amount=dbl(reward.get("reward_value"));
            if(type==1) {
                if(id==11)StateStore.addAp(user,(int)amount);
                String field=switch(id){case 1->"u_cp";case 2->"u_candy";case 3,4->"u_like";case 8->"u_fans";default->"";};
                if(!field.isEmpty()){ud.put(field,dbl(ud.get(field))+amount);s.state.incrementCurrency(str(user.get("uuid")),id==1?(long)amount:0,id==2?amount:0,id==3||id==4?amount:0,id==8?(long)amount:0);}
            } else if(type==9) {if(find(rows(user,"user_ticketcollection"),id)==null)rows(user,"user_ticketcollection").add(obj("i_id",id));}
            else if(type==2) {if(find(rows(user,"user_music"),id)==null)rows(user,"user_music").add(obj("i_id",id,"i_Level",1,"i_BonusLevel",0,"b_EncoreBonusAppear",0,"l_EncoreBonusActivateTime",0,"i_EncoreBonusFollowerId",0,"i_ChThirdActiveTime",0));}
            else if(type==3)owned(user,"costumes",id,true);
            else if(type==4)owned(user,"user_prop",id,false);
            else if(type==5){owned(user,"user_follower",id,true);SocialFollowers.syncMessenger(user);}
            else if(type==7){Map<String,Object> unit=find(rows(user,"user_unit"),id);int add=Math.max(1,(int)amount);if(unit==null)rows(user,"user_unit").add(obj("i_id",id,"i_Level",Math.min(20,add)));else unit.put("i_Level",Math.min(20,integer(first(unit.get("i_Level"),1))+add));}
        }
    }
}

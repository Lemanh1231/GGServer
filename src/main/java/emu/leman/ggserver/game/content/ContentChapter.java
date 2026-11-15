package emu.leman.ggserver.game.content;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.CmdId;
import emu.leman.ggserver.database.StateStore;
import emu.leman.ggserver.game.social.SocialFollowers;
import emu.leman.ggserver.net.HandlerRegistry;
import emu.leman.ggserver.net.Result;
import java.time.Instant;
import java.time.Clock;
import java.nio.file.Files;
import java.util.*;
import java.util.concurrent.ThreadLocalRandom;
import static emu.leman.ggserver.util.Json.*;
import static emu.leman.ggserver.game.content.ContentModule.*;

/** Chapter-three AP, score calculation, weighted drops and one-shot star chests. */
public final class ContentChapter {
    private final Services s;
    private final Clock clock;
    private final Map<Integer,Integer> dropWeights=new HashMap<>();
    ContentChapter(Services services) {this(services,Clock.systemUTC());}
    ContentChapter(Services services,Clock clock) {
        s=services;this.clock=clock;
        var weights=s.config.resource("gamedata/tour_drop_weights.json");
        if(Files.exists(weights)) for(Object value:list(read(weights))) {
            var row=map(value);int id=integer(row.get("i_id")),weight=integer(row.get("i_Percent"));
            if(id<=0||weight<0||dropWeights.putIfAbsent(id,weight)!=null)throw new IllegalArgumentException("Invalid Tour drop weight: "+id);
        }
        for(var row:s.gameData.table(36)) if(active(row,"5")&&!dropWeights.containsKey(integer(row.get("6"))))
            throw new IllegalArgumentException("Missing Tour drop weight: "+row.get("6"));
    }
    void register() {
        s.registry.register(CmdId.GET_CH_THIRD,this::get);
        s.registry.register(CmdId.CH_THIRD_STAGE,this::stage);
        s.registry.register(CmdId.CH_THIRD_STREAM_STAGE,this::stream);
        s.registry.register(CmdId.GET_CH_THIRD_STAR_REWARD,this::chest);
        s.registry.register(CmdId.SET_CH_THIRD_CHAPTER_REWARD,this::chest);
    }
    static Map<String,Object> ap(Map<String,Object> user) {
        return ap(user,Instant.now().getEpochSecond());
    }
    static Map<String,Object> ap(Map<String,Object> user,long now) {
        Map<String,Object> ap=map(user.computeIfAbsent("user_ap",k->obj("i_Ap",70,"i_FullApTime",0,"i_MaxAp",70)));
        int current=Math.max(0,integer(ap.getOrDefault("i_Ap",70)));long full=lng(ap.get("i_FullApTime"));
        if(current<70&&full!=0)current=(int)Math.max(0,70-Math.max(0,(full-now+299)/300));
        if(current>=70){full=0;}else if(full==0)full=now+(70-current)*300L;
        ap.put("i_Ap",current);ap.put("i_FullApTime",full);ap.put("i_MaxAp",70);return ap;
    }
    static boolean spend(Map<String,Object> ap,long cost,long now) {
        int current=integer(ap.get("i_Ap"));if(cost<0||current<cost)return false;
        long remaining=current-cost,full=lng(ap.get("i_FullApTime"));
        // A future full-time already includes the partial interval in progress.
        ap.put("i_Ap",remaining);ap.put("i_FullApTime",remaining>=70?0:current<70&&full>now?full+cost*300L:now+(70-remaining)*300L);
        return true;
    }
    private long now() {return clock.instant().getEpochSecond();}
    private static boolean active(Map<String,Object> config,String field) {return integer(config.getOrDefault(field,1))==1;}
    private List<Map<String,Object>> stages(Map<String,Object> user) {Object value=first(user.get("user_ch_third_stage"),user.get("user_chthird_stage"),new ArrayList<>());user.put("user_ch_third_stage",value);user.put("user_chthird_stage",value);return rows(user,"user_ch_third_stage");}
    private boolean chapterAvailable(Map<String,Object> user,int chapter) {
        Map<String,Object> config=s.gameData.row(35,chapter);
        Map<String,Object> girl=find(rows(user,"user_follower_profile"),100000);
        int level=girl==null?1:integer(girl.get("i_Level"));
        if(config.isEmpty()||!active(config,"21")||level<Math.max(1,integer(config.get("2")))||!tourUnlocked(user))return false;
        if(chapter==1)return true;
        List<Map<String,Object>> previous=s.gameData.table(33).stream().filter(r->integer(r.get("2"))==chapter-1&&active(r,"33")).toList();
        // Preserve existing progress: a later earned result is proof the player reached this chapter.
        if(previous.isEmpty()||hasChapterProgress(user,chapter))return true;
        return previous.stream().allMatch(r->cleared(user,r));
    }
    private boolean tourUnlocked(Map<String,Object> user) {
        Map<String,Object> follower=find(rows(user,"user_follower"),5);
        return follower!=null&&integer(follower.getOrDefault("i_Level",1))>=1;
    }
    private boolean hasChapterProgress(Map<String,Object> user,int chapter) {
        return stages(user).stream().anyMatch(r->integer(r.get("i_ChapterId"))==chapter&&(integer(r.get("i_Star"))>0||truth(r.get("b_Clear"))));
    }
    private boolean cleared(Map<String,Object> user,Map<String,Object> config) {
        int chapter=integer(config.get("2")),index=integer(config.get("3"));
        // Never trust the mere presence of the legacy zero-star placeholders.
        return stages(user).stream().anyMatch(r->integer(r.get("i_ChapterId"))==chapter&&integer(r.getOrDefault("i_StageIndex",integer(r.get("i_id"))%1000))>=index
                &&(integer(r.get("i_Star"))>0||truth(r.get("b_Clear"))));
    }
    public static List<Map<String,Object>> wireProgress(emu.leman.ggserver.game.GameData data,Map<String,Object> user) {
        List<Map<String,Object>> saved=rows(user,user.containsKey("user_ch_third_stage")?"user_ch_third_stage":"user_chthird_stage"),out=new ArrayList<>();
        for(var config:data.table(33))if(active(config,"33")) {
            int chapter=integer(config.get("2")),index=integer(config.get("3"));
            boolean clear=saved.stream().anyMatch(r->integer(r.get("i_ChapterId"))==chapter&&integer(r.getOrDefault("i_StageIndex",integer(r.get("i_id"))%1000))>=index&&(integer(r.get("i_Star"))>0||truth(r.get("b_Clear"))));
            if(clear) {var row=find(saved,integer(config.get("1")));out.add(obj("i_id",integer(config.get("1")),"i_ChapterId",chapter,"i_StageIndex",index,"i_Star",row==null?0:integer(row.get("i_Star"))));}
        }
        return out;
    }
    private boolean stageAvailable(Map<String,Object> user,Map<String,Object> config) {
        if(config.isEmpty()||!active(config,"33")||!chapterAvailable(user,integer(config.get("2"))))return false;
        int chapter=integer(config.get("2")),index=integer(config.get("3"));
        if(index==1||cleared(user,config))return true;
        return s.gameData.table(33).stream().filter(r->integer(r.get("2"))==chapter&&integer(r.get("3"))==index-1&&active(r,"33"))
                .anyMatch(r->cleared(user,r));
    }
    private Result get(Map<String,Object> req,Map<String,Object> ctx) {
        if(!s.events.isChapter3TourEnabled())return failure(obj(),"Chapter 3 Tour is closed");Map<String,Object> user=user(s,HandlerRegistry.payload(req),ctx);if(user==null)return Result.ok(obj());
        if(!tourUnlocked(user))return failure(obj(),"Tour is locked");
        Map<String,Object> ap=ap(user,now());List<Map<String,Object>> progress=wireProgress(s.gameData,user);
        // Native uses presence/count as completion. Keep legacy placeholders in storage, not on the wire.
        List<Map<String,Object>> claims=rows(user,"user_ch_third_chapter_reward");s.state.saveUser(user);return Result.ok(obj("u_seq",map(user.get("userdata")).get("u_seq"),"user_ap",ap,"user_ch_third_stage",progress,"user_ch_third_chapter_reward",claims));
    }
    private Result stage(Map<String,Object> req,Map<String,Object> ctx) {
        if(!s.events.isChapter3TourEnabled())return failure(obj("clear",0),"Chapter 3 Tour is closed");
        Map<String,Object> p=HandlerRegistry.payload(req),user=user(s,p,ctx);if(user==null)return Result.ok(obj());
        int id=integer(p.get("i_id"));Map<String,Object> config=s.gameData.row(33,id);
        if(!stageAvailable(user,config))return failure(obj("clear",0),"Chapter or preceding stage is locked");
        boolean story="Story".equals(config.get("34")),wasCleared=cleared(user,config);
        if(!story&&!"Normal".equals(config.get("34")))return failure(obj("clear",0),"Invalid stage type");
        int musicId=integer(p.get("music_id"));Map<String,Object> music=find(rows(user,"user_music"),musicId);
        List<Integer> selected=team(p.get("profile_ids"));
        if(!story&&(musicId<=0||music==null||s.gameData.row(2,musicId).isEmpty()||!active(s.gameData.row(2,musicId),"49")
                ||integer(music.getOrDefault("i_Level",1))<1||lng(music.get("i_ChThirdActiveTime"))>now()||!validTeam(user,selected)))
            return failure(obj("clear",0),"Invalid, unowned or unavailable Tour team");
        Map<String,Object> ap=ap(user,now());
        if(!story&&!spend(ap,5,now()))return failure(obj("clear",0,"user_ap",ap),"Not enough Cookie");
        List<Map<String,Object>> stages=stages(user);Map<String,Object> stage=find(stages,id);
        if(stage==null){stage=obj("i_id",id,"i_ChapterId",integer(config.get("2")),"i_StageIndex",integer(config.get("3")),"i_Star",0);stages.add(stage);}
        Map<String,Object> girl=ContentProfiles.profile(user,100000);
        if(story) {
            if(!wasCleared)ContentProfiles.exp(s.gameData,girl,id>=2000?200:100);
            stage.put("b_Clear",true);s.state.saveUser(user);
            return Result.ok(obj("star",0,"character_score",0,"music_score",0,"follower_profile_score",0,"bonus_score",0,"total_score",0,"clear",1,"user_ap",ap,"user_ch_third_stage",stage,"user_music",null,"reward_data",List.of(),"bonus_follower_profile_ids",List.of(),"user_follower_profile",girl,"user_follower_profile_score",List.of()));
        }
        Map<Integer,Map<String,Object>> scores=new HashMap<>();for(Map<String,Object> row:s.gameData.table(34))scores.put(integer(row.get("2")),row);int maxLevel=scores.keySet().stream().mapToInt(Integer::intValue).max().orElse(50);
        int characterLevel=Math.max(1,integer(girl.get("i_Level"))),charScore=integer(first(score(scores,characterLevel,maxLevel).get("3"),50));
        int musicLevel=integer(first(music.get("i_Level"),1));
        float multiplier=integer(first(score(scores,musicLevel,maxLevel).get("5"),550))/1000.0f,bonus=musicId==integer(config.get("36"))?.2f:0;
        int charMusic=(int)(charScore*(multiplier+bonus)),musicScore=(int)(charScore*multiplier),bonusMusic=charMusic-musicScore,followerScore=0,bonusFollowers=0;
        List<Object> profileScores=new ArrayList<>(),bonusIds=new ArrayList<>();List<Integer> recommended=ids(config.get("8"));
        for(int pid:selected) {
            Map<String,Object> profile=find(rows(user,"user_follower_profile"),pid);int level=profile==null?1:integer(profile.get("i_Level"));int base=integer(first(score(scores,level,maxLevel).get("4"),100)),extra=recommended.contains(pid)?round(base*.2):0;
            if(recommended.contains(pid)){bonusIds.add(pid);bonusFollowers+=extra;}profileScores.add(obj("i_id",pid,"score",base,"bonus_score",extra));followerScore+=base;
        }
        int one=integer(first(config.get("5"),1)),two=integer(first(config.get("6"),one)),three=integer(first(config.get("7"),two)),total=charScore+charMusic+followerScore+bonusFollowers;
        int star=total>=three?3:total>=two?2:total>=one?1:0;int clear=star>0?1:0;
        if(clear>0)stage.put("b_Clear",true);
        stage.put("i_Star",Math.max(star,integer(stage.get("i_Star"))));List<Map<String,Object>> rewards=clear>0?drops(config):List.of();gifts(user,rewards);
        if(clear>0)ContentProfiles.exp(s.gameData,girl,id>=2000?200:100);s.state.saveUser(user);
        return Result.ok(obj("star",star,"character_score",charScore,"music_score",musicScore,"follower_profile_score",followerScore,"bonus_score",bonusMusic+bonusFollowers,"total_score",total,"clear",clear,"user_ap",ap,"user_ch_third_stage",stage,"user_music",music,"reward_data",rewards,"bonus_follower_profile_ids",bonusIds,"user_follower_profile",girl,"bonus_music_score",bonusMusic,"user_follower_profile_score",profileScores));
    }
    private static Map<String,Object> score(Map<Integer,Map<String,Object>> scores,int level,int maximum) {return scores.getOrDefault(Math.min(Math.max(1,level),maximum),obj());}
    private static int round(double value) {return (int)Math.rint(value);}
    private static List<Integer> team(Object value) {
        String text=str(value);if(text.isBlank()||text.length()>64)return List.of();
        List<Integer> out=new ArrayList<>();
        for(String token:text.split(",",-1))try {int id=Integer.parseInt(token.trim());if(id<=0||out.contains(id))return List.of();out.add(id);}catch(NumberFormatException ignored){return List.of();}
        return out;
    }
    private boolean validTeam(Map<String,Object> user,List<Integer> selected) {
        if(selected.isEmpty()||selected.size()>3)return false;
        for(int pid:selected) {
            var profile=find(rows(user,"user_follower_profile"),pid);
            if(pid==100000||profile==null||integer(profile.get("i_Level"))<1)return false;
            boolean owned=rows(user,"user_follower").stream().anyMatch(f->{
                int id=integer(f.get("i_id"));var config=s.gameData.row(5,id);
                return !config.isEmpty()&&active(config,"44")&&integer(f.getOrDefault("i_Level",1))>=1&&integer(config.getOrDefault("47",id))==pid;
            });
            if(!owned)return false;
        }
        return true;
    }
    private static List<Integer> ids(Object value) {List<Integer> out=new ArrayList<>();for(String token:str(value).split(","))try{out.add(Integer.parseInt(token.trim()));}catch(NumberFormatException ignored){}return out;}
    private List<Map<String,Object>> drops(Map<String,Object> stage) {
        List<Map<String,Object>> out=new ArrayList<>();
        for(int group:ids(stage.get("37"))) {
            List<Map<String,Object>> candidates=s.gameData.table(36).stream().filter(r->integer(r.get("1"))==group&&active(r,"5")).toList();long total=candidates.stream().mapToLong(this::weight).sum();if(candidates.isEmpty()||total<=0)continue;
            Map<String,Object> chosen=choose(candidates,dropWeights,ThreadLocalRandom.current().nextLong(total));
            int amount=integer(chosen.get("4"));if(amount>0)out.add(obj("reward_type",integer(first(chosen.get("2"),11)),"reward_id",integer(chosen.get("3")),"reward_value",amount));
        }
        return out;
    }
    private int weight(Map<String,Object> row) {return dropWeights.getOrDefault(integer(row.get("6")),0);}
    static Map<String,Object> choose(List<Map<String,Object>> candidates,Map<Integer,Integer> weights,long pick) {
        if(pick<0)throw new IllegalArgumentException("Negative drop pick");
        for(var candidate:candidates) {pick-=weights.getOrDefault(integer(candidate.get("6")),0);if(pick<0)return candidate;}
        throw new IllegalArgumentException("Drop pick exceeds weights");
    }
    private static void gifts(Map<String,Object> user,List<Map<String,Object>> rewards) {for(Map<String,Object> reward:rewards)if(integer(reward.get("reward_type"))==11&&integer(reward.get("reward_id"))>0){int id=integer(reward.get("reward_id"));Map<String,Object> gift=find(rows(user,"user_follower_giftitem"),id);if(gift==null){gift=obj("i_id",id,"i_Value",0);rows(user,"user_follower_giftitem").add(gift);}gift.put("i_Value",integer(gift.get("i_Value"))+integer(reward.get("reward_value")));}}
    private Result stream(Map<String,Object> req,Map<String,Object> ctx) {
        if(!s.events.isChapter3TourEnabled())return failure(obj(),"Chapter 3 Tour is closed");
        Map<String,Object> p=HandlerRegistry.payload(req),user=user(s,p,ctx);if(user==null)return Result.ok(obj());int id=integer(p.get("i_id")),count=integer(first(p.get("count"),1));
        Map<String,Object> config=s.gameData.row(33,id),stage=find(stages(user),id);
        if(!stageAvailable(user,config)||!"Normal".equals(config.get("34"))||stage==null||integer(stage.get("i_Star"))<3)
            return failure(obj(),"Chapter is locked or stage has not earned three stars");
        if(count<1||count>5)return failure(obj(),"Invalid sweep count");
        Map<String,Object> ap=ap(user,now());
        if(!spend(ap,count*5L,now()))return failure(obj("clear",0,"user_ap",ap),"Not enough Cookie");
        Map<String,Object> rewardData=obj();for(int i=1;i<=count;i++){List<Map<String,Object>> rewards=drops(config);rewardData.put(String.valueOf(i),rewards);gifts(user,rewards);}
        Map<String,Object> girl=ContentProfiles.profile(user,100000);ContentProfiles.exp(s.gameData,girl,(id>=2000?200L:100L)*count);s.state.saveUser(user);return Result.ok(obj("i_id",id,"user_ap",ap,"user_follower_profile",girl,"reward_data",rewardData));
    }
    private Result chest(Map<String,Object> req,Map<String,Object> ctx) {
        if(!s.events.isChapter3TourEnabled())return failure(obj(),"Chapter 3 Tour is closed");
        Map<String,Object> p=HandlerRegistry.payload(req),user=user(s,p,ctx);if(user==null)return Result.ok(obj());int chapter=integer(p.get("i_id")),number=integer(p.get("reward_num"));Map<String,Object> config=s.gameData.row(35,chapter);
        if(!chapterAvailable(user,chapter))return failure(obj(),"Chapter is locked");
        Map<String,Object> ap=ap(user,now());
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
                if(field.equals("u_like")) emu.leman.ggserver.game.economy.AreaCurrency.addLike(user,amount);
                else if(!field.isEmpty())ud.put(field,dbl(ud.get(field))+amount);
            } else if(type==9) {if(find(rows(user,"user_ticketcollection"),id)==null)rows(user,"user_ticketcollection").add(obj("i_id",id));}
            else if(type==2) {if(find(rows(user,"user_music"),id)==null)rows(user,"user_music").add(obj("i_id",id,"i_Level",1,"i_BonusLevel",0,"b_EncoreBonusAppear",0,"l_EncoreBonusActivateTime",0,"i_EncoreBonusFollowerId",0,"i_ChThirdActiveTime",0));}
            else if(type==3)owned(user,"costumes",id,true);
            else if(type==4)owned(user,"user_prop",id,false);
            else if(type==5){owned(user,"user_follower",id,true);SocialFollowers.syncMessenger(user);}
            else if(type==7){Map<String,Object> unit=find(rows(user,"user_unit"),id);int add=Math.max(1,(int)amount);if(unit==null)rows(user,"user_unit").add(obj("i_id",id,"i_Level",Math.min(20,add)));else unit.put("i_Level",Math.min(20,integer(first(unit.get("i_Level"),1))+add));}
        }
    }
}

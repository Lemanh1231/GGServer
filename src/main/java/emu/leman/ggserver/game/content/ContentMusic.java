package emu.leman.ggserver.game.content;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.CmdId;
import emu.leman.ggserver.game.social.FollowerAccess;
import emu.leman.ggserver.net.HandlerRegistry;
import emu.leman.ggserver.net.Result;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;
import static emu.leman.ggserver.game.content.ContentModule.*;

final class ContentMusic {
    private final Services s;
    ContentMusic(Services services) {s=services;}
    void register() {
        s.registry.register(CmdId.PLAY_MUSIC,(req,ctx)->Result.ok(obj("code",0,"album_idx",1,"music_idx",HandlerRegistry.payload(req).getOrDefault("music_idx",1),"score1",1000,"score2",1000,"score3",1000,"grade1",1,"grade2",1,"grade3",1,"u_cp",0,"u_candy",0.0,"u_like",0.0,"u_fans",0)));
        s.registry.register(CmdId.MUSIC_POINT_REVIEW,(req,ctx)->Result.ok(first(HandlerRegistry.payload(req).get("review_point"),new ArrayList<>())));
        s.registry.register(CmdId.GET_MUSIC_REWARD,(req,ctx)->{
            synchronized(s.state) { return reward(req,ctx); }
        });
    }
    private Result reward(Map<String,Object> req,Map<String,Object> ctx) {
        Map<String,Object> p=HandlerRegistry.payload(req),stored=user(s,p,ctx);
        if(stored==null) return Result.error(1,"Account not found");
        Map<String,Object> user=copy(stored);
        List<Integer> ids=new ArrayList<>();
        for(Object value:list(p.get("i_ids"))) {
            final int id;
            try {id=Integer.parseInt(str(value));} catch(NumberFormatException e) {return Result.error(1,"Invalid music ID");}
            if(id<=0 || ids.contains(id)) return Result.error(1,"Invalid or duplicate music ID");
            ids.add(id);
        }
        if(ids.isEmpty()) return Result.error(1,"No Encore selected");
        List<Integer> candies=new ArrayList<>();Map<Integer,Long> gains=new LinkedHashMap<>();long granted=0;
        long now=java.time.Instant.now().getEpochSecond();
        Map<String,Object> claims=map(user.get("encore_claims"));
        List<Map<String,Object>> music=user==null?List.of():rows(user,"user_music");
        for(int index=0;index<ids.size();index++) {
            Map<String,Object> song=find(music,ids.get(index));
            if(song==null || !FollowerAccess.active(s.gameData.row(2,ids.get(index)),"49")
                    || integer(song.get("b_EncoreBonusAppear"))!=1) return Result.error(1,"Encore is not available");
            var lifecycle=EncoreRules.state(user,ids.get(index));
            if(!lifecycle.isEmpty()?integer(lifecycle.get("pending"))!=1:EncoreRules.legacyClaimed(user,song)) return Result.error(1,"Encore was already claimed");
            // Historical/imported state is not necessarily validated by the current save path.
            // Do not truncate fractional IDs/levels or wrap a long into a valid catalog ID.
            final int level,rawFollower;
            try {
                level=Integer.parseInt(str(song.get("i_Level")));
                rawFollower=Integer.parseInt(str(song.get("i_EncoreBonusFollowerId")));
            } catch(NumberFormatException e) {return Result.error(1,"Invalid Encore configuration");}
            Map<String,Object> config=s.gameData.row(11,level);
            if(config.isEmpty() || !EncoreRules.eligible(s.gameData,user,ids.get(index),rawFollower)) return Result.error(1,"Invalid Encore configuration");
            final int candy,exp;
            try {candy=Integer.parseInt(str(config.get("6")));exp=Integer.parseInt(str(config.get("7")));}
            catch(NumberFormatException e) {return Result.error(1,"Invalid Encore reward");}
            if(candy<0 || exp<0) return Result.error(1,"Invalid Encore reward");
            int follower=FollowerAccess.profileId(s.gameData,rawFollower);gains.merge(follower,(long)exp,Long::sum);
            if(s.gameData.table(31).stream().noneMatch(row->integer(row.get("2"))==follower)) return Result.error(1,"Invalid Encore profile configuration");
            Map<String,Object> profile=find(rows(user,"user_follower_profile"),follower);
            long amount=(long)candy+(profile==null?0:Math.max(0,integer(profile.get("i_AddCandy"))));
            if(amount>Integer.MAX_VALUE || granted+amount>Integer.MAX_VALUE)return Result.error(1,"Encore reward exceeds client range");
            candies.add((int)amount);granted+=amount;
        }
        List<Map<String,Object>> profiles=new ArrayList<>(List.of(obj("i_id",1,"i_Level",1,"d_Exp",0,"i_AddCandy",0)));
        if(user!=null) {
            // One repository save commits currencies, EXP, pass points and consumed bonuses together.
            Map<String,Object> ud=map(user.get("userdata"));ud.put("u_candy",dbl(ud.get("u_candy"))+granted);
            if(!user.containsKey("encore_claims")) {claims=obj();user.put("encore_claims",claims);}
            for(int id:ids) {Map<String,Object> song=find(music,id);if(song!=null){claims.put(str(id),lng(song.get("l_EncoreBonusActivateTime")));EncoreRules.consumed(user,song,now);song.put("l_EncoreBonusActivateTime",now);song.put("b_EncoreBonusAppear",0);song.put("i_EncoreBonusFollowerId",0);}}
            new emu.leman.ggserver.game.account.AuthContent(s).awardPassPoints(user,10L*ids.size());
            gains.forEach((id,gain)->ContentProfiles.exp(s.gameData,ContentProfiles.profile(user,id),gain));
            profiles=rows(user,"user_follower_profile");s.state.saveUser(user);
        }
        return Result.ok(obj("total_reward_value",candies.stream().mapToInt(Integer::intValue).sum(),"reward_music_id",ids,"reward_value",candies,"user_follower_profile",profiles,"error_data",obj()));
    }
}

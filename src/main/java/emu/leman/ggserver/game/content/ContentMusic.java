package emu.leman.ggserver.game.content;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.CmdId;
import emu.leman.ggserver.game.social.SocialFollowers;
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
        s.registry.register(CmdId.GET_MUSIC_REWARD,this::reward);
    }
    private Result reward(Map<String,Object> req,Map<String,Object> ctx) {
        Map<String,Object> p=HandlerRegistry.payload(req),user=user(s,p,ctx);List<Integer> ids=list(p.get("i_ids")).stream().map(v->integer(v)).filter(v->v>0).toList();if(ids.isEmpty())ids=List.of(1);
        List<Object> levels=list(p.get("i_levels"));List<Integer> candies=new ArrayList<>();Map<Integer,Long> gains=new LinkedHashMap<>();long granted=0;
        List<Map<String,Object>> music=user==null?List.of():rows(user,"user_music");
        for(int index=0;index<ids.size();index++) {
            Map<String,Object> song=find(music,ids.get(index));int level=index<levels.size()&&integer(levels.get(index))>0?integer(levels.get(index)):song==null?1:integer(first(song.get("i_Level"),1));
            Map<String,Object> config=s.gameData.row(11,level);if(config.isEmpty())config=s.gameData.row(11,1);
            int candy=integer(first(config.get("6"),10)),exp=integer(first(config.get("7"),50));candies.add(candy);
            int follower=song==null?1:integer(first(song.get("i_EncoreBonusFollowerId"),1));if(follower<=0)follower=1;gains.merge(follower,(long)exp,Long::sum);
            Map<String,Object> profile=user==null?null:find(rows(user,"user_follower_profile"),follower);granted+=candy+(profile==null?0:Math.max(0,integer(profile.get("i_AddCandy"))));
        }
        List<Map<String,Object>> profiles=new ArrayList<>(List.of(obj("i_id",1,"i_Level",1,"d_Exp",0,"i_AddCandy",0)));
        if(user!=null) {
            s.state.incrementCurrency(uuid(p,ctx),0,(double)granted,0.0,0);
            Map<String,Object> ud=map(user.get("userdata"));ud.put("u_candy",dbl(ud.get("u_candy"))+granted);
            for(int id:ids) {Map<String,Object> song=find(music,id);if(song!=null){song.put("b_EncoreBonusAppear",0);song.put("i_EncoreBonusFollowerId",0);}}
            if(!user.containsKey("user_event_point"))user.put("user_event_point",new ArrayList<>(List.of(obj("s_EventType","Pass","i_DataID",13,"i_Point",0,"i_Step",0,"i_ADViewTime",0,"i_Version",13))));
            for(Map<String,Object> point:rows(user,"user_event_point"))if("Pass".equals(point.get("s_EventType"))) {
                int total=integer(point.get("i_Point"))+10*ids.size(),season=integer(first(point.get("i_DataID"),13)),step=0;point.put("i_Point",total);
                for(Map<String,Object> row:s.gameData.table(18))if(integer(row.get("2"))==season&&total>=integer(row.get("4")))step=Math.max(step,integer(row.get("3")));point.put("i_Step",step);break;
            }
            gains.forEach((id,gain)->ContentProfiles.exp(s.gameData,ContentProfiles.profile(user,id),gain));
            new SocialFollowers(s).syncProfiles(user);profiles=rows(user,"user_follower_profile");s.state.saveUser(user);
        }
        return Result.ok(obj("total_reward_value",candies.stream().mapToInt(Integer::intValue).sum(),"reward_music_id",ids,"reward_value",candies,"user_follower_profile",profiles,"error_data",obj()));
    }
}

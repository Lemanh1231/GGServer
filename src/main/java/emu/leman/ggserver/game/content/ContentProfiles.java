package emu.leman.ggserver.game.content;

import emu.leman.ggserver.game.GameData;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;
import static emu.leman.ggserver.game.content.ContentModule.*;

/** The cumulative profile EXP rules shared by tour and encore rewards. */
final class ContentProfiles {
    private ContentProfiles() {}
    static Map<String,Object> profile(Map<String,Object> user,int id) {
        List<Map<String,Object>> profiles=rows(user,"user_follower_profile");Map<String,Object> found=find(profiles,id);
        if(found==null) {found=obj("i_id",id,"i_Level",1,"d_Exp",0,"i_AddCandy",0);profiles.add(found);}return found;
    }
    static void exp(GameData data,Map<String,Object> profile,long gain) {exp(data,profile,gain,false);}
    static void exp(GameData data,Map<String,Object> profile,long gain,boolean fallback) {
        int id=integer(profile.get("i_id"));List<Map<String,Object>> levels=data.table(31).stream().filter(r->integer(r.get("2"))==id).sorted(Comparator.comparingInt(r->integer(r.get("3")))).toList();
        if(levels.isEmpty()&&fallback)levels=data.table(31).stream().filter(r->integer(r.get("2"))==1).sorted(Comparator.comparingInt(r->integer(r.get("3")))).toList();
        if(levels.isEmpty())return;
        long total=Math.min(Math.max(0,lng(profile.get("d_Exp")))+Math.max(0,gain),lng(levels.getLast().get("4")));
        int reached=1,candy=0;for(Map<String,Object> row:levels) {if(total<lng(row.get("4")))break;reached=integer(row.get("3"));candy+=Math.max(0,integer(row.get("7")));}
        profile.put("i_Level",reached);profile.put("d_Exp",total);profile.put("i_AddCandy",candy);
    }
}

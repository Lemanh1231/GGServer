package emu.leman.ggserver.game.content;

import emu.leman.ggserver.game.GameData;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Acquisition only: never revoke historical ownership or restrict owned-item upgrades. */
public final class AcquisitionRules {
    private AcquisitionRules() {}
    public static int level(Map<String,Object> user,String field,int id) {
        for(Object raw:list(user.get(field))) {var row=map(raw);if(integer(row.get("i_id"))==id)return integer(row.getOrDefault("i_Level",1));}
        return 0;
    }
    public static boolean allowed(GameData data,Map<String,Object> user,int table,int id) {
        var row=data.row(table,id);if(row.isEmpty()||user==null)return false;
        String active=table==2?"49":table==3?"48":"37", goods=table==2?"45":table==3?"29":"30";
        if(integer(row.getOrDefault(active,1))!=1||!Set.of("GP","CP","Candy").contains(str(row.get(goods)))||table==2&&id==211)return false;
        int area=integer(row.getOrDefault(table==2?"50":table==3?"49":"2",1));
        if(area==2&&id!=201&&(integer(map(map(user.get("areas")).get("1")).get("i_UserFanGrade"))<=3||level(user,"user_follower",12)<15))return false;
        int character=area==2?2:1,required=integer(row.get(table==20?"32":"38"));
        if(Math.max(1,level(user,"characters",character))<required)return false;
        if(table==20)return true;
        for(int col:table==2?new int[]{40,41}:new int[]{39,40}) {int follower=integer(row.get(str(col)));if(follower>0&&level(user,"user_follower",follower)<=0)return false;}
        String inventory=table==2?"user_music":"user_prop";
        for(int col:table==2?new int[]{42,43}:new int[]{41,42}) {int item=integer(row.get(str(col)));if(item>0&&level(user,inventory,item)<=0)return false;}
        int count=integer(row.get(table==2?"44":"43"));
        long owned=list(user.get(inventory)).stream().map(emu.leman.ggserver.util.Json::map).filter(r->level(user,inventory,integer(r.get("i_id")))>0).map(r->integer(r.get("i_id"))).distinct().count();
        return owned>=count;
    }
}

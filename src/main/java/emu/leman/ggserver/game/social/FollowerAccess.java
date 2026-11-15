package emu.leman.ggserver.game.social;

import emu.leman.ggserver.game.GameData;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Catalog/ownership checks shared by gift, milestone, ad and Encore commands. No mutations. */
public final class FollowerAccess {
    private FollowerAccess() {}
    public static boolean active(Map<String,Object> row,String field) {
        return !row.isEmpty() && integer(row.getOrDefault(field,1))==1;
    }
    public static int profileId(GameData data,int raw) {
        Map<String,Object> follower=data.row(5,raw);
        return follower.isEmpty()?raw:integer(follower.getOrDefault("47",raw));
    }
    public static boolean ownedProfile(GameData data,Map<String,Object> user,int raw) {
        if(user==null || raw<=0) return false;
        Map<String,Object> follower=data.row(5,raw);
        if(!follower.isEmpty()&&!active(follower,"44")) return false;
        int pid=profileId(data,raw);
        if(!active(data.row(28,pid),"14")) return false;
        if(pid==100000) return raw==100000;
        for(Object value:list(user.get("user_follower"))) {
            Map<String,Object> owned=map(value); int id=integer(owned.get("i_id"));
            Map<String,Object> definition=data.row(5,id);
            if(integer(owned.get("i_Level"))>0 && active(definition,"44") && profileId(data,id)==pid) return true;
        }
        return false;
    }
    public static Map<String,Object> profile(GameData data,Map<String,Object> user,int raw) {
        int pid=profileId(data,raw);
        for(Object value:list(user.get("user_follower_profile"))) {
            Map<String,Object> profile=map(value);
            if(integer(profile.get("i_id"))==pid) return profile;
        }
        return null;
    }
    public static boolean giftAllowed(GameData data,int raw,int gift) {
        String allowed=str(data.row(28,profileId(data,raw)).get("15"));
        for(String token:allowed.split(",")) if(token.strip().equals(Integer.toString(gift))) return true;
        return false;
    }
    public static boolean questUnlocked(GameData data,Map<String,Object> user,Map<String,Object> quest) {
        if(user==null || !active(quest,"28")) return false;
        int id=integer(quest.get("2")),required=integer(quest.getOrDefault("3",1));
        if(id<=0) return true;
        if(!active(data.row(5,id),"44")) return false;
        for(Object value:list(user.get("user_follower"))) {
            Map<String,Object> follower=map(value);
            if(integer(follower.get("i_id"))==id && integer(follower.get("i_Level"))>=Math.max(1,required)) return true;
        }
        return false;
    }
}

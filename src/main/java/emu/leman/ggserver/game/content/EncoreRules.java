package emu.leman.ggserver.game.content;

import emu.leman.ggserver.game.GameData;
import emu.leman.ggserver.game.social.FollowerAccess;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Native saves carry only appear/follower, not an activation timestamp or operation ID.
 * Server-owned lifecycle metadata bounds replays without trusting invented client times.
 * An identical offline snapshot after cooldown cannot be distinguished from a new roll. */
public final class EncoreRules {
    private EncoreRules() {}
    public static boolean eligible(GameData data,Map<String,Object> user,int music,int follower) {
        var song=data.row(2,music);var definition=data.row(5,follower);
        return FollowerAccess.active(song,"49") && FollowerAccess.active(definition,"44")
                && integer(song.get("50"))==integer(definition.get("45"))
                && list(user.get("user_follower")).stream().anyMatch(v->integer(map(v).get("i_id"))==follower && integer(map(v).get("i_Level"))>0)
                && FollowerAccess.ownedProfile(data,user,follower);
    }
    public static long cooldown(GameData data,int level) {
        try {long seconds=Long.parseLong(str(data.row(11,level).get("4")));return seconds>0?seconds:-1;}
        catch(NumberFormatException e) {return -1;}
    }
    private static Map<String,Object> states(Map<String,Object> user) {
        if(!(user.get("encore_state") instanceof Map))user.put("encore_state",obj());
        return map(user.get("encore_state"));
    }
    public static Map<String,Object> state(Map<String,Object> user,int id) {
        return map(map(user.get("encore_state")).get(str(id)));
    }
    public static boolean legacyClaimed(Map<String,Object> user,Map<String,Object> song) {
        Object receipt=map(user.get("encore_claims")).get(str(song.get("i_id")));
        return receipt!=null && lng(song.get("l_EncoreBonusActivateTime"))<=lng(receipt);
    }
    /** Reconcile stale display flags without granting rewards or deleting replay receipts. */
    public static void normalizeAppearance(Map<String,Object> user,Map<String,Object> song,long now) {
        int music=integer(song.get("i_id"));
        // A zero receipt on an inactive, never-activated song is an imported placeholder,
        // not evidence of a successful claim. Persist the distinction before a new roll.
        if(integer(song.get("b_EncoreBonusAppear"))!=1 && state(user,music).isEmpty()
                && map(user.get("encore_claims")).containsKey(str(music))) {
            boolean placeholder=lng(map(user.get("encore_claims")).get(str(music)))==0
                    && lng(song.get("l_EncoreBonusActivateTime"))==0;
            states(user).put(str(music),placeholder?obj("pending",0,"legacy_placeholder",1)
                    :obj("pending",0,"claimed_at",now,"legacy_migrated",1));
        }
        if(integer(song.get("b_EncoreBonusAppear"))!=1)return;
        int id=integer(song.get("i_id"));var state=state(user,id);
        if(state.isEmpty()) {
            if(!legacyClaimed(user,song))return;
            // Legacy receipt units are unknown: begin one conservative cooldown now.
            states(user).put(str(id),obj("pending",0,"claimed_at",now));
        } else if(integer(state.get("pending"))==1)return;
        song.put("b_EncoreBonusAppear",0);song.put("i_EncoreBonusFollowerId",0);
        song.put("l_EncoreBonusActivateTime",lng(state(user,id).get("claimed_at")));
    }
    /** Only server claim clears pending. A no-bonus/stale save must not delete a gift. */
    private static void preserve(Map<String,Object> previous,Map<String,Object> incoming) {
        for(String field:List.of("b_EncoreBonusAppear","i_EncoreBonusFollowerId","l_EncoreBonusActivateTime"))incoming.remove(field);
        if(previous!=null)for(String field:List.of("b_EncoreBonusAppear","i_EncoreBonusFollowerId","l_EncoreBonusActivateTime"))
            if(previous.containsKey(field))incoming.put(field,previous.get(field));
    }
    public static void mergeAppearance(GameData data,Map<String,Object> user,Map<String,Object> previous,Map<String,Object> incoming,Object appear,Object follower,long now) {
        if(previous!=null)normalizeAppearance(user,previous,now);
        preserve(previous,incoming);
        int id=integer(incoming.get("i_id"));var state=state(user,id);
        if(previous!=null && integer(previous.get("b_EncoreBonusAppear"))==1
                && (integer(state.get("pending"))==1 || state.isEmpty()&&!legacyClaimed(user,previous)))return;
        // Native omitted fields are not a new appearance. Reject fractional/unknown IDs.
        int raw;
        try {if(!"1".equals(str(appear)))return;raw=Integer.parseInt(str(follower));}
        catch(NumberFormatException e) {return;}
        if(!eligible(data,user,id,raw))return;
        int level=Math.max(integer(incoming.get("i_Level")),previous==null?0:integer(previous.get("i_Level")));
        long wait=cooldown(data,level);
        if(wait<0)return;
        if(state.isEmpty() && map(user.get("encore_claims")).containsKey(str(id))) {
            // Old receipts have unknown units/claim time. Preserve them; establish a
            // conservative cooldown on first observation, never treat them as Unix time.
            states(user).put(str(id),obj("pending",0,"claimed_at",now));return;
        }
        if(state.containsKey("claimed_at") && (now<lng(state.get("claimed_at")) || now-lng(state.get("claimed_at"))<wait))return;
        var next=new LinkedHashMap<>(state);next.put("pending",1);next.put("issued_at",now);states(user).put(str(id),next);
        incoming.put("b_EncoreBonusAppear",1);incoming.put("i_EncoreBonusFollowerId",raw);
        incoming.put("l_EncoreBonusActivateTime",now);
    }
    public static void consumed(Map<String,Object> user,Map<String,Object> song,long now) {
        int id=integer(song.get("i_id"));var next=new LinkedHashMap<>(state(user,id));
        next.put("pending",0);next.put("claimed_at",now);states(user).put(str(id),next);
    }
}

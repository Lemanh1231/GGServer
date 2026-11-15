package emu.leman.ggserver.game.player;

import java.util.List;
import java.util.Map;
import static emu.leman.ggserver.util.Json.*;

/** Profile business operations shared by packet handlers and other in-process features. */
public final class ProfileManager extends PlayerManager {
    public ProfileManager(Player player) { super(player); }

    public void setNickname(Object value) { set("u_nick",value); }
    public void setAvatar(Object value) { set("u_avatar",value); }
    public void setTitle(Object value) { set("u_title",value); }

    private void set(String field, Object value) {
        // In particular, an explicit null nickname is not replaced by its default.
        player().update(snapshot -> {
            if(!(snapshot.get("userdata") instanceof Map)) snapshot.put("userdata",obj());
            map(snapshot.get("userdata")).put(field,value);
        });
    }

    public Map<String,Object> profile() {
        return player().read(ProfileManager::project);
    }

    /** Only public fields from one persisted snapshot; never exposes account/session data. */
    static Map<String,Object> project(Map<String,Object> snapshot) {
        Map<String,Object> ud=snapshot==null ? obj() : map(snapshot.get("userdata"));
        Map<String,Object> result=obj("u_avatar",ud.getOrDefault("u_avatar",1),"u_id",ud.getOrDefault("u_id",""),"u_nick",ud.getOrDefault("u_nick","Guitarist"),"u_country",ud.getOrDefault("u_country","KR"),"u_title",ud.getOrDefault("u_title",1));
        for(String key:List.of("allper","allcom","gold","silver","bronze","single_cnt","multi_cnt","master_cnt","single_score","multi_score")) result.put(key,0);
        return result;
    }
}

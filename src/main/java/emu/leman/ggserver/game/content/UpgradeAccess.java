package emu.leman.ggserver.game.content;

import emu.leman.ggserver.game.GameData;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Catalog gates shared by skill visibility and first skill/unit acquisition. */
public final class UpgradeAccess {
    private UpgradeAccess() {}

    public static boolean unlocked(GameData data,Map<String,Object> user,int table,int id) {
        var row=data.row(table,id);
        if(user==null || row.isEmpty() || table!=7 && table!=8) return false;
        boolean skill=table==8;
        if(!skill && integer(row.getOrDefault("43",1))!=1) return false;
        int area=integer(row.getOrDefault(skill?"2":"42",1));
        if(area!=1 && area!=2) return false;
        if(AcquisitionRules.level(user,"characters",area)<integer(row.get(skill?"37":"33"))) return false;
        int first=skill?39:35;
        String[] inventories={skill?"user_skill":"user_unit","user_follower","user_prop"};
        for(int kind=0;kind<inventories.length;kind++) for(int n=0;n<2;n++) {
            int required=integer(row.get(str(first+kind*2+n)));
            if(required>0 && AcquisitionRules.level(user,inventories[kind],required)<=0) return false;
        }
        long props=list(user.get("user_prop")).stream().map(emu.leman.ggserver.util.Json::map)
                .filter(r->integer(r.getOrDefault("i_Level",1))>0).map(r->integer(r.get("i_id"))).distinct().count();
        return props>=integer(row.get(skill?"45":"41"));
    }
}

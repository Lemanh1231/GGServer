package emu.leman.ggserver.game.account;

import emu.leman.ggserver.game.GameData;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Daily mission IDs, conditions and aggregates are owned by the dumped catalog. */
public final class DailyMissionRules {
    private final GameData data;
    public DailyMissionRules(GameData data) { this.data=data; }
    public List<Map<String,Object>> definitions() {
        return data.serverRows("daily_mission").stream().filter(r->integer(r.get("b_IsActive"))!=0).toList();
    }
    public boolean attendance(Map<String,Object> definition) {
        return "DailyAttendanceCount".equals(definition.get("s_DailyMissionConditionType"));
    }
    public boolean aggregate(Map<String,Object> definition) {
        return "CompleteDailyMissionCount".equals(definition.get("s_DailyMissionConditionType"));
    }
    public void complete(List<Object> missions) {
        Map<Integer,Map<String,Object>> progress=new HashMap<>();
        for(Object raw:missions) progress.put(integer(map(raw).get("i_id")),map(raw));
        long completed=definitions().stream().filter(d->!aggregate(d)).filter(d->{
            var item=progress.get(integer(d.get("i_id")));
            return item!=null && (integer(item.getOrDefault("i_Level",1))>=2 || dbl(item.get("d_Quantity"))>=dbl(d.get("d_Condition_1")));
        }).count();
        for(var definition:definitions()) if(aggregate(definition)) {
            var item=progress.get(integer(definition.get("i_id")));
            if(item!=null) item.put("d_Quantity",Math.max(lng(item.get("d_Quantity")),completed));
        }
    }
}

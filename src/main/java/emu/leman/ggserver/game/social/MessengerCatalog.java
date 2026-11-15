package emu.leman.ggserver.game.social;

import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Group ownership from published v8.0.0 table_db.ab / Messenger.db (i_Group 1..192).
 * Only validates incoming saves; native remains responsible for unlock requirements and dialogue timing. */
final class MessengerCatalog {
    private static final int[] ROOMS={
        1,2,1,1,2,3,1,2,4,1,2,1,5,5,1,1,5,6,1,7,5,2,7,1,5,6,1,5,7,1,3,1,
        1,7,1,1,7,7,7,5,1,7,6,3,1,5,1,1,3,4,8,5,7,10,5,1,1,7,1,1,2,9,6,3,
        10,10,10,10,5,5,1,9,7,11,1,16,2,16,16,12,16,16,11,11,11,12,12,13,13,14,15,15,6,9,1,5,
        4,3,7,10,2,1,12,16,16,6,10,16,12,5,1,10,6,203,16,2,10,16,16,16,13,14,11,15,2,10,204,16,
        6,204,2,16,6,204,16,203,10,205,17,17,2,17,2,17,2,17,15,2,17,7,17,17,17,17,17,1,5,205,1,204,
        6,17,6,5,205,205,5,6,204,5,16,16,17,17,3,17,17,206,206,206,207,1,207,207,1,208,208,208,208,208,208,10
    };
    static boolean valid(Map<String,Object> row,List<Integer> groups) {
        if(!whole(row.get("i_MessengerChatRoomId"),1,Integer.MAX_VALUE)) return false;
        int room=integer(row.get("i_MessengerChatRoomId"));
        if(!((room>=1&&room<=17)||(room>=203&&room<=208))) return false;
        if(row.containsKey("s_UnlockGroupList")) {
            Object raw=row.get("s_UnlockGroupList");
            if(!(raw instanceof String text)||!text.matches("\\s*[0-9]+\\s*(,\\s*[0-9]+\\s*)*")||groups.size()!=text.split(",",-1).length) return false;
        }
        if(row.containsKey("i_LastConfirmIndex")&&!whole(row.get("i_LastConfirmIndex"),-1,Integer.MAX_VALUE)) return false;
        if(row.containsKey("l_UpdateTimeTicks")&&!whole(row.get("l_UpdateTimeTicks"),0,3155378975999999999L)) return false;
        if(groups.size()!=new HashSet<>(groups).size()) return false;
        return groups.stream().allMatch(id->id>0&&id<=ROOMS.length&&ROOMS[id-1]==room);
    }
    private static boolean whole(Object value,long min,long max) {
        if(!(value instanceof Number number)) return false;
        try {
            long n=new java.math.BigDecimal(number.toString()).longValueExact();
            return n>=min&&n<=max;
        } catch(NumberFormatException|ArithmeticException e) { return false; }
    }
}

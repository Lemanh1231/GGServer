package emu.leman.ggserver.game.content;

import emu.leman.ggserver.game.GameData;
import java.nio.file.Path;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class UpgradeAccessTest {
    @TempDir Path root;

    @Test void everyPrerequisiteAndDistinctPropCountIsRequiredForSkillsAndUnits() {
        for(int table:new int[]{7,8}) {
            int first=table==8?39:35;
            var row=obj("1",1,table==8?"2":"42",2,table==8?"37":"33",100,
                    str(first),10,str(first+1),11,str(first+2),20,str(first+3),21,
                    str(first+4),30,str(first+5),31,str(first+6),3);
            if(table==7) row.put("43",1);
            write(root.resolve("gamedata/game_data.json"),obj(str(table),List.of(row)));
            var data=new GameData(root);
            var user=obj("characters",List.of(obj("i_id",1,"i_Level",9999),obj("i_id",2,"i_Level",99)));
            String own=table==8?"user_skill":"user_unit";
            user.put(own,List.of(obj("i_id",10,"i_Level",1),obj("i_id",11,"i_Level",1)));
            user.put("user_follower",List.of(obj("i_id",20,"i_Level",1),obj("i_id",21,"i_Level",1)));
            user.put("user_prop",List.of(obj("i_id",30,"i_Level",1),obj("i_id",31,"i_Level",1),obj("i_id",32,"i_Level",1)));
            assertFalse(UpgradeAccess.unlocked(data,user,table,1),"Wrong chapter level must not satisfy gate");
            user.put("characters",List.of(obj("i_id",2,"i_Level",100)));
            assertTrue(UpgradeAccess.unlocked(data,user,table,1));
            for(String inventory:List.of(own,"user_follower","user_prop")) {
                Object saved=user.get(inventory);
                user.put(inventory,List.of());assertFalse(UpgradeAccess.unlocked(data,user,table,1));
                user.put(inventory,saved);
            }
            user.put("user_prop",List.of(obj("i_id",30,"i_Level",1),obj("i_id",31,"i_Level",1),obj("i_id",31,"i_Level",1)));
            assertFalse(UpgradeAccess.unlocked(data,user,table,1),"Duplicate prop must not satisfy count");
        }
    }

    @Test void missingInactiveOrUnsupportedCatalogCannotUnlock() {
        write(root.resolve("gamedata/game_data.json"),obj("7",List.of(obj("1",1,"42",1,"43",0,"33",1))));
        var data=new GameData(root);var user=obj("characters",List.of(obj("i_id",1,"i_Level",1000)));
        assertFalse(UpgradeAccess.unlocked(data,user,7,1));
        assertFalse(UpgradeAccess.unlocked(data,user,7,999));
        assertFalse(UpgradeAccess.unlocked(data,user,20,1));
        assertFalse(UpgradeAccess.unlocked(data,null,7,1));
    }
}

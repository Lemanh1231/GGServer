package emu.leman.ggserver.game;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import static org.junit.jupiter.api.Assertions.*;
import static emu.leman.ggserver.util.Json.*;

class GameDataTest {
    @TempDir Path root;
    @Test void numericAndNamedTablesAreAccessible() throws Exception {
        Files.createDirectories(root.resolve("schema"));
        Files.copy(Path.of("resources/schema/schema.json"),root.resolve("schema/schema.json"));
        write(root.resolve("gamedata/game_data.json"),obj("2",List.of(obj("1",7,"2","Song"))));
        GameData data=new GameData(root);
        assertEquals(7,integer(data.row(2,7).get("1")));
        assertEquals(data.table(2),data.table("music"));
        assertTrue(data.row("music",999).isEmpty());
        assertEquals(7,integer(map(list(data.namedData().get("music")).getFirst()).get("i_id")));
        Map<String,Object> response=data.namedData();list(response.get("music")).clear();
        assertEquals(1,list(data.namedData().get("music")).size());
    }
    @Test void originalCapturesAreReadNatively() {
        GameData data=new GameData(Path.of("resources"));
        assertEquals(39,data.data().size());
        assertFalse(list(data.namedData().get("music")).isEmpty());
        assertFalse(list(data.namedData().get("samseckevent")).isEmpty());
        assertFalse(list(data.varietyStore()).isEmpty());
    }
    @Test void schemaFreeAchievementRewardsKeepNoncontiguousFieldNumbers() {
        write(root.resolve("gamedata/game_data.json"),obj("9",List.of(obj("1",1,"28","CP","51",99,"52",1,
                "53",11,"54",12,"76",13,"83",20))));
        var row=new GameData(root).serverRows("achievement").getFirst();
        assertEquals(11,lng(row.get("i_Reward_11")));
        assertEquals(12,lng(row.get("i_Reward_12")));
        assertEquals(13,lng(row.get("i_Reward_13")));
        assertEquals(20,lng(row.get("i_Reward_20")));
    }
    @Test void dailyMissionCompletionFollowsEditedCatalogNotFixedIdsOrTargets() throws Exception {
        Path source=Path.of("resources");
        for(String folder:List.of("schema","gamedata/catalog")) {
            try(var paths=Files.walk(source.resolve(folder))) {
                for(Path file:paths.toList()) {
                    Path target=root.resolve(source.relativize(file));
                    if(Files.isDirectory(file)) Files.createDirectories(target);else Files.copy(file,target);
                }
            }
        }
        Path missions=root.resolve("gamedata/catalog/tables/quests/daily_missions.json");
        var rows=list(read(missions));
        for(Object raw:rows) {
            var row=map(raw);
            if(integer(row.get("i_id"))==2) row.put("d_Condition_1",4);
            if(integer(row.get("i_id"))==6) row.put("i_id",60);
            if(integer(row.get("i_id"))==3) row.put("b_IsActive",0);
        }
        write(missions,rows);
        var manifest=map(read(root.resolve("gamedata/catalog/manifest.json")));
        for(Object raw:list(manifest.get("tables"))) if("daily_mission".equals(map(raw).get("name"))) map(raw).remove("clientFile");
        write(root.resolve("gamedata/catalog/manifest.json"),manifest);
        var rules=new emu.leman.ggserver.game.account.DailyMissionRules(new GameData(root));
        assertEquals(5,rules.definitions().size());
        List<Object> progress=new ArrayList<>(List.of(obj("i_id",2,"i_Level",1,"d_Quantity",4),
                obj("i_id",3,"i_Level",2,"d_Quantity",100),obj("i_id",60,"i_Level",1,"d_Quantity",0)));
        rules.complete(progress);
        assertEquals(1,lng(map(progress.getLast()).get("d_Quantity")));
        var returned=new GameData(root).serverRows("daily_mission");returned.clear();
        assertEquals(6,new GameData(root).serverRows("daily_mission").size());
    }
}

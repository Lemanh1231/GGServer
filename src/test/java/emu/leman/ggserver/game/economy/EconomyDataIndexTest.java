package emu.leman.ggserver.game.economy;

import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class EconomyDataIndexTest {
    @TempDir Path root;
    @Test void indexesPreserveFirstIdAndAllOrderedGroupDefinitions() throws Exception {
        Files.createDirectories(root.resolve("gamedata"));
        write(root.resolve("gamedata/game_data.json"),obj("13",List.of(
                obj("1",1,"2",7,"3",1,"4",1,"5",10),
                obj("1",1,"2",7,"3",1,"4",2,"5",20),
                obj("1",2,"2",8,"3",1,"4",1,"5",30))));
        var data=new EconomyData(root);
        assertEquals(10,lng(data.row(13,1).get("5")));
        assertEquals(2,data.groupedRows(13,"2",7).size());
        assertEquals(20,lng(map(data.rewards(7).get(1)).get("reward_value")));
        assertTrue(data.row(13,999).isEmpty());assertTrue(data.rows(999).isEmpty());
        assertTrue(data.rewards(999).isEmpty());
    }
    @Test void rewardResponsesCannotPolluteCachedCatalog() throws Exception {
        Files.createDirectories(root.resolve("gamedata"));
        write(root.resolve("gamedata/game_data.json"),obj("13",List.of(obj("2",7,"3",1,"4",1,"5",10))));
        var data=new EconomyData(root);var first=data.rewards(7);
        map(first.getFirst()).put("reward_value",999);first.add(EconomyData.reward(10,1003,1));
        var second=data.rewards(7);assertEquals(1,second.size());
        assertEquals(10,lng(map(second.getFirst()).get("reward_value")));
    }
}

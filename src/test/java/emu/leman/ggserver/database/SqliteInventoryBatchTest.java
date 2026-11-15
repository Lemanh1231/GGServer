package emu.leman.ggserver.database;

import java.nio.file.Path;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class SqliteInventoryBatchTest {
    @TempDir Path root;
    @Test void batchRetainsReplacementPartialSaveAndLastDuplicateSemantics() {
        try(var store=new StateStore(root)) {
            var user=store.createUser("batch-only","synthetic-device");
            user.put("user_music",List.of(obj("i_id",201,"i_Level",2,"custom","old"),
                    obj("i_id",201,"i_Level",7,"custom","last"),obj("i_id",202,"i_Level",3)));
            user.put("user_shop",List.of(obj("i_id",2003,"i_Count",1)));
            store.saveUser(user);
            var loaded=store.getUser("batch-only");var songs=list(loaded.get("user_music"));
            assertEquals(2,songs.size());
            var song=songs.stream().map(emu.leman.ggserver.util.Json::map).filter(r->integer(r.get("i_id"))==201).findFirst().orElseThrow();
            assertEquals(7,integer(song.get("i_Level")));assertEquals("last",song.get("custom"));
            // Omitted sections are retained; an explicitly empty section is deleted.
            store.saveUser(obj("uuid","batch-only","userdata",loaded.get("userdata"),"user_music",List.of()));
            assertTrue(list(store.getUser("batch-only").get("user_music")).isEmpty());
            assertEquals(1,list(store.getUser("batch-only").get("user_shop")).size());
        }
        try(var store=new StateStore(root)) {
            assertTrue(list(store.getUser("batch-only").get("user_music")).isEmpty());
            assertEquals(1,list(store.getUser("batch-only").get("user_shop")).size());
        }
    }
}

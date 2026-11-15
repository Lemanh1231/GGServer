package emu.leman.ggserver.data;

import emu.leman.ggserver.game.GameData;
import emu.leman.ggserver.config.ServerConfig;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class ResourceLoaderTest {
    @TempDir Path root;
    private final Map<String,Object> schema=map(read(Path.of("resources/schema/schema.json")));

    @Test void shippedCatalogPreservesAllLegacyGameplayAndClientValues() throws Exception {
        var catalog=ResourceLoader.load(Path.of("resources/gamedata/catalog"),schema);
        assertEquals(39,catalog.tables().size());
        var legacy=map(read(Path.of("resources/gamedata/game_data.json")));
        // The CH2 cookie product (shop 31) intentionally added one row. Verify
        // every table against the independent numeric source, not a stale total.
        for(var field:list(map(schema.get("main.getGameDataListRetDataInfo")).get("fields"))) {
            var spec=map(field);String id=str(spec.get("id")),name=str(spec.get("name"));
            assertEquals(list(legacy.get(id)).size(),catalog.tables().get(name).size(),"Row count: "+name);
        }
        assertEquals(legacy.values().stream().mapToInt(value->list(value).size()).sum(),
                catalog.tables().values().stream().mapToInt(DataTable::size).sum());
        assertEquals(legacy,catalog.numeric());
        Files.createDirectories(root.resolve("schema"));Files.createDirectories(root.resolve("gamedata"));
        Files.copy(Path.of("resources/schema/schema.json"),root.resolve("schema/schema.json"));
        Files.copy(Path.of("resources/gamedata/game_data.json"),root.resolve("gamedata/game_data.json"));
        var numericClient=new GameData(root).namedData();
        Files.copy(Path.of("resources/gamedata/getGameDataList.b64"),root.resolve("gamedata/getGameDataList.b64"));
        var captured=new GameData(root).namedData();
        // The immutable wire capture predates three intentional CH2/UI fixes.
        // Assert both ends explicitly; all other captured values must match exactly.
        var label=list(captured.get("SystemString")).stream().map(emu.leman.ggserver.util.Json::map)
                .filter(row->integer(row.get("i_StringID"))==1330029).findFirst().orElseThrow();
        assertEquals("Nhận",label.get("s_VI"));label.put("s_VI","Đã nhận");
        var ad=list(captured.get("ad_list")).stream().map(emu.leman.ggserver.util.Json::map)
                .filter(row->integer(row.get("i_id"))==2).findFirst().orElseThrow();
        assertEquals("0",ad.get("s_ConditionValue2"));ad.put("s_ConditionValue2","300");
        assertTrue(list(captured.get("shop")).stream().noneMatch(row->integer(map(row).get("i_id"))==31));
        var cookie=list(numericClient.get("shop")).stream().map(emu.leman.ggserver.util.Json::map)
                .filter(row->integer(row.get("i_id"))==31).findFirst().orElseThrow();
        list(captured.get("shop")).addFirst(cookie);
        assertEquals(captured,catalog.client());
    }

    @Test void shippedCookiePurchaseRemainsAnExplicitServerAndClientProduct() {
        var catalog=ResourceLoader.load(Path.of("resources/gamedata/catalog"),schema);
        var product=catalog.tables().get("shop").find(31).orElseThrow();
        assertEquals(1021,integer(product.get("i_RewardGroup")));
        assertEquals(1,integer(product.get("i_SellType")));
        assertEquals(100,lng(product.get("i_SellValue")));
        assertEquals(1,integer(product.get("b_IsActive")));
        assertEquals(0,integer(product.get("i_Condition")));
        var client=list(catalog.client().get("shop")).stream().map(emu.leman.ggserver.util.Json::map)
                .filter(row->integer(row.get("i_id"))==31).toList();
        assertEquals(1,client.size());
        assertEquals(100,lng(client.getFirst().get("i_SellValue")));
        assertEquals(1021,integer(client.getFirst().get("i_RewardGroup")));
    }

    @Test void declaredTotalAndPerTableCountsCannotHideAddedOrMissingRows() throws Exception {
        Path catalog=fixture();var manifest=map(read(catalog.resolve("manifest.json")));
        manifest.put("rowCount",integer(manifest.get("rowCount"))-1);write(catalog.resolve("manifest.json"),manifest);
        assertThrows(IllegalArgumentException.class,()->ResourceLoader.load(catalog,schema));
        manifest.put("rowCount",integer(manifest.get("rowCount"))+1);
        var table=map(list(manifest.get("tables")).getFirst());table.put("rowCount",integer(table.get("rowCount"))+1);
        write(catalog.resolve("manifest.json"),manifest);
        assertThrows(IllegalArgumentException.class,()->ResourceLoader.load(catalog,schema));
    }

    @Test void explicitPrimaryKeysRetainGroupRowsAndCompositeIds() {
        var catalog=ResourceLoader.load(Path.of("resources/gamedata/catalog"),schema);
        var fans=catalog.tables().get("Fan");
        assertEquals(6,fans.matching("i_Area",1L).size());
        assertTrue(fans.find(1,1).isPresent());
        assertThrows(IllegalArgumentException.class,()->fans.find(1));
        var rewards=catalog.tables().get("percent");
        assertEquals(4,rewards.matching("i_GroupID",301010).size());
        var skill=catalog.tables().get("skill").find(1L).orElseThrow();
        skill.put("s_Name_EN","modified caller");
        assertNotEquals("modified caller",catalog.tables().get("skill").find(1).orElseThrow().get("s_Name_EN"));
    }

    @Test void normalGameDataStartupPrefersCatalogOverLegacyJsonAndCapture() {
        var data=new GameData(ServerConfig.defaults(Path.of("resources")));
        assertEquals(8,data.resource("skill").size());
        assertEquals(68,data.resource("followerquest").size());
        assertEquals(data.table(8),data.table("skill"));
        assertThrows(IllegalArgumentException.class,()->data.resource("invented"));
    }

    private Path fixture() throws Exception {
        Path catalog=root.resolve("catalog");
        try(var paths=Files.walk(Path.of("resources/gamedata/catalog"))) {
            for(Path path:paths.toList()) {
                Path target=catalog.resolve(Path.of("resources/gamedata/catalog").relativize(path));
                if(Files.isDirectory(path)) Files.createDirectories(target);else Files.copy(path,target);
            }
        }
        return catalog;
    }
    @Test void malformedExistingCatalogFailsClosedInsteadOfSilentlyUsingOldData() throws Exception {
        Path catalog=fixture();var manifest=map(read(catalog.resolve("manifest.json")));
        list(manifest.get("tables")).removeLast();write(catalog.resolve("manifest.json"),manifest);
        assertThrows(IllegalArgumentException.class,()->ResourceLoader.load(catalog,schema));
    }
    @Test void invalidFieldTypesAndDuplicateKeysAreRejected() throws Exception {
        Path catalog=fixture();Path file=catalog.resolve("tables/skills/skills.json");
        var rows=list(read(file));map(rows.getFirst()).put("i_id","not-an-id");write(file,rows);
        assertThrows(IllegalArgumentException.class,()->ResourceLoader.load(catalog,schema));
        rows=list(read(Path.of("resources/gamedata/catalog/tables/skills/skills.json")));
        rows.set(1,copy(rows.getFirst()));write(file,rows);
        assertThrows(IllegalArgumentException.class,()->ResourceLoader.load(catalog,schema));
    }
    @Test void manifestCannotReadOutsideResourceDirectory() throws Exception {
        Path catalog=fixture();var manifest=map(read(catalog.resolve("manifest.json")));
        map(list(manifest.get("tables")).getFirst()).put("file","../outside.json");
        write(catalog.resolve("manifest.json"),manifest);
        assertThrows(IllegalArgumentException.class,()->ResourceLoader.load(catalog,schema));
    }
    @Test void presentCatalogWithMissingManifestCannotFallBackToLegacy() throws Exception {
        Files.createDirectories(root.resolve("gamedata/catalog"));
        write(root.resolve("gamedata/game_data.json"),obj("8",List.of(obj("1",999))));
        assertThrows(IllegalStateException.class,()->new GameData(root));
    }
    @Test void clientVariantCannotReplaceRowIdsWithoutExplicitServerChange() throws Exception {
        Path catalog=fixture();Path file=catalog.resolve("client/shops/products.json");
        var rows=list(read(file));map(rows.getFirst()).put("i_id",999999);write(file,rows);
        assertThrows(IllegalArgumentException.class,()->ResourceLoader.load(catalog,schema));
    }
}

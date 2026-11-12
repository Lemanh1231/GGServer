package emu.leman.ggserver.game;


import java.nio.file.*;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Native, schema-driven access to the numeric game tables and their wire names. */
public final class GameData {
    private final emu.leman.ggserver.config.ServerConfig config;
    private final Map<String,Object> data;
    private final Map<String,Object> schema;
    private final Map<String,String> tableIds = new LinkedHashMap<>();
    private final Map<String,Object> named;
    private final Map<String,emu.leman.ggserver.data.DataTable> resources;

    public GameData(Path root) { this(emu.leman.ggserver.config.ServerConfig.defaults(root)); }
    public GameData(emu.leman.ggserver.config.ServerConfig config) {
        this.config = config;
        Path game = config.resource("gamedata/game_data.json");
        Path schemas = config.resource("schema/schema.json");
        schema = Files.exists(schemas) ? map(read(schemas)) : obj();
        Path catalog=config.resource("gamedata/catalog");
        if(Files.exists(catalog)) {
            var loaded=emu.leman.ggserver.data.ResourceLoader.load(catalog,schema);
            data=loaded.numeric();named=loaded.client();resources=loaded.tables();
            for(Object entry:list(map(schema.get("main.getGameDataListRetDataInfo")).get("fields"))) {
                var field=map(entry);tableIds.put(str(field.get("name")),str(field.get("id")));
            }
            return;
        }
        resources=Map.of();
        data = Files.exists(game) ? map(read(game)) : obj();
        named = obj();
        for (Object entry : list(map(schema.get("main.getGameDataListRetDataInfo")).get("fields"))) {
            Map<String,Object> field = map(entry);
            String id = str(field.get("id")), name = str(field.get("name"));
            tableIds.put(name, id);
            List<Map<String,Object>> rows = new ArrayList<>();
            for (Map<String,Object> row : table(id)) rows.add(convertRow(row, str(map(field.get("elem")).get("struct"))));
            named.put(name, rows);
        }
        Path capture = config.resource("gamedata/getGameDataList.b64");
        if(Files.exists(capture)) {
            Map<String,Object> envelope=ContentCapture.read(capture,schema,"main.getGameDataListReturn");
            Map<String,Object> captured=map(map(envelope.get("data")).get("ret"));
            if(!captured.isEmpty()) { named.clear(); named.putAll(captured); }
        }
    }

    public Map<String,Object> data() { return data; }
    public Map<String,Object> namedData() { return copy(named); }
    /** Authoritative server rows with schema names (not the captured client variant). */
    public List<Map<String,Object>> serverRows(String name) {
        var resource=resources.get(name);
        if(resource!=null) return resource.rows();
        String id=tableIds.getOrDefault(name,switch(name) { case "daily_mission" -> "10";case "achievement" -> "9";default -> name; }),dto="";
        for(Object raw:list(map(schema.get("main.getGameDataListRetDataInfo")).get("fields"))) {
            var field=map(raw);if(str(field.get("id")).equals(id)) dto=str(map(field.get("elem")).get("struct"));
        }
        List<Map<String,Object>> rows=new ArrayList<>();
        for(var row:table(id)) {
            if(!dto.isEmpty()) rows.add(convertRow(row,dto));
            else if(name.equals("daily_mission") || name.equals("achievement")) {
                // Minimal numeric fixtures/legacy roots may omit the schema file.
                Map<String,Object> converted=obj("i_id",row.get("1"),"s_RewardType",row.get(name.equals("daily_mission")?"29":"28"),
                        "b_IsActive",row.getOrDefault(name.equals("daily_mission")?"44":"52",1));
                if(name.equals("daily_mission")) converted.putAll(obj("s_DailyMissionConditionType",row.get("27"),"d_Condition_1",row.get("28"),"i_Reward_1",row.get("42")));
                else for(int level=1;level<=20;level++) { String key=str(level<=10?40+level:level<=12?42+level:63+level);if(row.containsKey(key)) converted.put("i_Reward_"+level,row.get(key)); }
                rows.add(converted);
            } else rows.add(copy(row));
        }
        return rows;
    }
    /** Explicit named resource access for new features; legacy numeric handlers remain compatible. */
    public emu.leman.ggserver.data.DataTable resource(String name) {
        var table=resources.get(name);
        if(table==null) throw new IllegalArgumentException("No catalog resource: "+name);
        return table;
    }
    @SuppressWarnings("unchecked") public List<Map<String,Object>> table(String table) {
        Object rows = data.get(tableIds.getOrDefault(table, table));
        return rows instanceof List<?> ? (List<Map<String,Object>>)rows : List.of();
    }
    public List<Map<String,Object>> table(int table) { return table(String.valueOf(table)); }
    public Map<String,Object> row(String table, int id) {
        return table(table).stream().filter(r -> integer(first(r.get("1"),r.get("i_id"),r.get("idx"))) == id).findFirst().orElseGet(LinkedHashMap::new);
    }
    public Map<String,Object> row(int table, int id) { return row(String.valueOf(table),id); }
    private Map<String,Object> convertRow(Map<String,Object> row, String struct) {
        Map<String,Object> converted = obj();
        for(Object entry : list(map(schema.get(struct)).get("fields"))) {
            Map<String,Object> field = map(entry);
            String id = str(field.get("id"));
            if(row.containsKey(id)) converted.put(str(field.get("name")), row.get(id));
        }
        return converted;
    }

    /** The captured store contains records outside the numeric game-data tables. */
    public Object varietyStore() {
        Path json = config.resource("gamedata/variety_store.json");
        if(Files.exists(json)) return read(json);
        Path captured = config.resource("gamedata/getVarietyStore.b64");
        if(!Files.exists(captured)) return new ArrayList<>();
        return ContentCapture.read(captured, schema, "store.getVarietyStoreReturn").getOrDefault("data", new ArrayList<>());
    }
}

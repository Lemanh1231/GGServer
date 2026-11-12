package emu.leman.ggserver.database;

import com.mongodb.client.*;
import com.mongodb.client.model.*;
import emu.leman.ggserver.util.Json;
import java.util.*;
import org.bson.Document;
import static com.mongodb.client.model.Filters.*;

/** Immutable feature rows, published by the revision-checked users document.
 * Readers never see a half-written save, including on standalone MongoDB.
 * Published snapshots are retained: removing old versions requires offline GC.
 */
final class MongoUserSections {
    static final Map<String,String> COLLECTIONS;
    static {
        Map<String,String> names=new LinkedHashMap<>();
        names.put("userdata","user_profiles");
        names.put("costumes","user_costumes");
        for(String field:List.of("areas","posts","achievements","characters")) names.put(field,"user_"+field);
        for(String field:List.of("user_unit","user_skill","user_music","user_guitar","user_prop",
                "user_follower","user_follower_giftitem","user_shop","user_ap","user_follower_profile",
                "user_follower_profile_reward","user_follower_quest","user_messenger","user_ch_third_stage",
                "user_chthird_stage","user_ad_level","user_ticketcollection","user_event_point",
                "user_daily_mission","user_buff","user_subscribe_list","user_tutorial")) names.put(field,field);
        COLLECTIONS=Collections.unmodifiableMap(names);
    }
    private final MongoDatabase database;
    private final Set<String> indexed=new HashSet<>();
    MongoUserSections(MongoDatabase database) { this.database=database; }

    private synchronized MongoCollection<Document> collection(String name,boolean index) {
        var collection=database.getCollection(name);
        if(index && indexed.add(name)) {
            try {
                collection.createIndex(Indexes.compoundIndex(Indexes.ascending("uuid"),Indexes.ascending("snapshot"),
                        Indexes.ascending("field"),Indexes.ascending("position")),new IndexOptions().unique(true));
            } catch(RuntimeException ex) { indexed.remove(name);throw ex; }
        }
        return collection;
    }

    /** Stage first; no user points at these rows until its atomic publication succeeds. */
    Document stage(String uuid,Document contents) {
        String snapshot=UUID.randomUUID().toString();
        Document manifest=new Document();
        try {
            for(var entry:contents.entrySet()) {
                String field=entry.getKey(),name=COLLECTIONS.getOrDefault(field,"user_state");
                Object value=entry.getValue();
                String kind=value instanceof List<?>?"list":value instanceof Map<?,?>?"map":"scalar";
                List<Document> rows=new ArrayList<>();
                if(value instanceof List<?> list) {
                    for(int i=0;i<list.size();i++) rows.add(row(uuid,snapshot,field,i,list.get(i)));
                } else if(value instanceof Map<?,?> map) {
                    int i=0;
                    for(var item:map.entrySet()) rows.add(row(uuid,snapshot,field,i++,item.getValue()).append("key",item.getKey()));
                } else rows.add(row(uuid,snapshot,field,0,value));
                manifest.put(field,new Document("collection",name).append("snapshot",snapshot).append("kind",kind).append("count",rows.size()));
                var target=collection(name,true);
                if(!rows.isEmpty()) target.insertMany(rows);
            }
            return manifest;
        } catch(RuntimeException|Error ex) {
            try { discard(uuid,manifest); } catch(RuntimeException cleanup) { ex.addSuppressed(cleanup); }
            throw ex;
        }
    }
    private static Document row(String uuid,String snapshot,String field,int position,Object value) {
        return new Document("uuid",uuid).append("snapshot",snapshot).append("field",field)
                .append("position",position).append("data",value);
    }
    Map<String,Object> read(Document account) {
        if(!account.containsKey("sections")) return Json.copy(Json.map(account.get("contents")));
        Map<String,Object> result=new LinkedHashMap<>();
        for(var entry:Json.map(account.get("sections")).entrySet()) {
            String field=entry.getKey();Map<String,Object> ref=Json.map(entry.getValue());
            String name=Json.str(ref.get("collection"));
            if(!name.equals(COLLECTIONS.getOrDefault(field,"user_state"))) throw new IllegalStateException("Invalid user section collection");
            var rows=collection(name,false).find(and(eq("uuid",account.get("_id")),eq("snapshot",ref.get("snapshot")),eq("field",field)))
                    .sort(Sorts.ascending("position")).into(new ArrayList<>());
            if(rows.size()!=Json.integer(ref.get("count"))) throw new IllegalStateException("Incomplete Mongo user section: "+field);
            Object value;
            switch(Json.str(ref.get("kind"))) {
                case "list" -> { List<Object> list=new ArrayList<>();rows.forEach(row->list.add(row.get("data")));value=list; }
                case "map" -> { Map<String,Object> map=new LinkedHashMap<>();rows.forEach(row->map.put(row.getString("key"),row.get("data")));value=map; }
                case "scalar" -> { if(rows.size()!=1) throw new IllegalStateException("Invalid scalar section");value=rows.getFirst().get("data"); }
                default -> throw new IllegalStateException("Unknown Mongo section kind");
            }
            result.put(field,value);
        }
        return Json.copy(result);
    }
    /** Only unpublished snapshots owned by this attempt may be discarded. */
    void discard(String uuid,Document manifest) {
        Set<String> visited=new HashSet<>();
        for(Object raw:manifest.values()) {
            Map<String,Object> ref=Json.map(raw);String name=Json.str(ref.get("collection")),snapshot=Json.str(ref.get("snapshot"));
            if(visited.add(name+":"+snapshot)) collection(name,false).deleteMany(and(eq("uuid",uuid),eq("snapshot",snapshot)));
        }
    }
    /** Called only after removing the account publication; recreation uses different snapshot IDs. */
    void deletePublishedHistory(String uuid,Document account) {
        // Delete exactly the published snapshot, not every UUID row: a concurrent recreation is safe.
        if(account.get("sections") instanceof Document manifest) discard(uuid,manifest);
    }
}

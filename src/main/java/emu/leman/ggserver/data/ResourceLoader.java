package emu.leman.ggserver.data;

import java.math.BigDecimal;
import java.nio.file.*;
import java.util.*;
import org.slf4j.LoggerFactory;
import static emu.leman.ggserver.util.Json.*;

/** Explicit manifest-driven loading, like Nebula resources without reflection or guessed fields. */
public final class ResourceLoader {
    public record Catalog(Map<String,Object> numeric,Map<String,Object> client,Map<String,DataTable> tables) {}
    private ResourceLoader() {}

    public static Catalog load(Path directory,Map<String,Object> schema) {
        Map<String,Object> manifest=object(read(directory.resolve("manifest.json")),"manifest");
        if(integer(manifest.get("formatVersion"))!=1) throw new IllegalArgumentException("Unsupported game catalog version");
        Map<String,Object> numeric=obj(),client=obj();
        Map<String,DataTable> tables=new LinkedHashMap<>();
        Map<String,Map<String,Object>> expected=new LinkedHashMap<>();
        for(Object raw:list(map(schema.get("main.getGameDataListRetDataInfo")).get("fields"))) {
            Map<String,Object> field=map(raw);expected.put(str(field.get("id")),field);
        }
        int total=0;
        if(!(manifest.get("tables") instanceof List<?> definitions)) throw new IllegalArgumentException("Catalog tables must be an array");
        for(Object raw:definitions) {
            Map<String,Object> definition=object(raw,"table definition");
            String id=str(definition.get("id")),name=str(definition.get("name")),dto=str(definition.get("struct"));
            Map<String,Object> field=expected.get(id);
            if(field==null || !name.equals(str(field.get("name"))) || !dto.equals(str(map(field.get("elem")).get("struct"))))
                throw new IllegalArgumentException("Catalog/schema mismatch: "+name+" ("+id+")");
            List<Object> fields=list(map(schema.get(dto)).get("fields"));
            if(!stringify(fields).equals(stringify(definition.get("fields"))))
                throw new IllegalArgumentException("Catalog field schema drift: "+name);
            List<Map<String,Object>> rows=rows(directory,str(definition.get("file")),fields);
            if(rows.size()!=integer(definition.get("rowCount"))) throw new IllegalArgumentException("Catalog row count mismatch: "+name);
            List<String> keys=list(definition.get("keyFields")).stream().map(emu.leman.ggserver.util.Json::str).toList();
            Set<String> names=new HashSet<>();fields.forEach(f->names.add(str(map(f).get("name"))));
            if(keys.isEmpty() || new HashSet<>(keys).size()!=keys.size() || !names.containsAll(keys)) throw new IllegalArgumentException("Invalid key fields: "+name);
            DataTable table=new DataTable(name,keys,rows);
            if(tables.putIfAbsent(name,table)!=null || numeric.containsKey(id)) throw new IllegalArgumentException("Duplicate catalog table: "+name);
            List<Object> wire=new ArrayList<>();
            for(Map<String,Object> row:rows) {
                Map<String,Object> converted=obj();
                for(Object entry:fields) {
                    Map<String,Object> spec=map(entry);String key=str(spec.get("name"));
                    if(row.containsKey(key)) converted.put(str(spec.get("id")),row.get(key));
                }
                wire.add(converted);
            }
            numeric.put(id,wire);
            List<Map<String,Object>> clientRows=definition.containsKey("clientFile")?rows(directory,str(definition.get("clientFile")),fields):rows;
            // Validate client keys too, but preserve its original list order and values.
            DataTable clientTable=new DataTable(name,keys,clientRows);
            if(clientRows.size()!=rows.size()) throw new IllegalArgumentException("Client row count mismatch: "+name);
            for(Map<String,Object> row:rows)
                if(clientTable.find(keys.stream().map(row::get).toArray()).isEmpty()) throw new IllegalArgumentException("Client key mismatch: "+name);
            client.put(name,clientRows);total+=rows.size();
            LoggerFactory.getLogger(ResourceLoader.class).debug("Loaded {}: {} rows",name,rows.size());
        }
        if(!numeric.keySet().equals(expected.keySet()) || tables.size()!=integer(manifest.get("tableCount")) || total!=integer(manifest.get("rowCount")))
            throw new IllegalArgumentException("Incomplete game catalog");
        LoggerFactory.getLogger(ResourceLoader.class).info("Resources ready: {} tables / {} rows",tables.size(),total);
        return new Catalog(numeric,client,Collections.unmodifiableMap(tables));
    }
    private static Map<String,Object> object(Object value,String context) {
        if(!(value instanceof Map<?,?>)) throw new IllegalArgumentException(context+" must be an object");
        return map(value);
    }
    private static List<Map<String,Object>> rows(Path directory,String relative,List<Object> fields) {
        try {
            Path root=directory.toRealPath(),file=root.resolve(relative).normalize();
            if(relative.isBlank() || Path.of(relative).isAbsolute() || !file.startsWith(root) || !file.toRealPath().startsWith(root))
                throw new IllegalArgumentException("Catalog path escapes root: "+relative);
            Object parsed=read(file);
            if(!(parsed instanceof List<?> values)) throw new IllegalArgumentException(relative+" must be an array");
            Map<String,Map<String,Object>> specs=new LinkedHashMap<>();
            fields.forEach(f->specs.put(str(map(f).get("name")),map(f)));
            List<Map<String,Object>> result=new ArrayList<>();
            for(Object value:values) {
                Map<String,Object> row=object(value,relative+" row");
                for(var entry:row.entrySet()) {
                    Map<String,Object> spec=specs.get(entry.getKey());
                    if(spec==null) throw new IllegalArgumentException(relative+": unknown field "+entry.getKey());
                    validate(entry.getValue(),str(spec.get("type")),relative+"."+entry.getKey());
                }
                result.add(row);
            }
            return result;
        } catch(java.io.IOException e) { throw new IllegalArgumentException("Cannot load catalog table "+relative,e); }
    }
    private static void validate(Object value,String type,String field) {
        boolean valid=switch(type) {
            case "STRING" -> value instanceof String;
            case "BOOL" -> value instanceof Boolean;
            case "DOUBLE" -> value instanceof Number n && Double.isFinite(n.doubleValue());
            case "BYTE","I16","I32","I64" -> integral(value,type);
            default -> false; // Extend explicitly if a future schema adds nested table fields.
        };
        if(!valid) throw new IllegalArgumentException("Invalid "+type+" value at "+field);
    }
    private static boolean integral(Object value,String type) {
        if(!(value instanceof Number)) return false;
        try {
            var integer=new BigDecimal(value.toString()).toBigIntegerExact();
            int bits=switch(type) { case "BYTE" -> 8;case "I16" -> 16;case "I32" -> 32;default -> 64; };
            return integer.bitLength()<bits;
        } catch(ArithmeticException e) { return false; }
    }
}

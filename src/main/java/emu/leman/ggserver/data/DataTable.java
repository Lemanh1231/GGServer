package emu.leman.ggserver.data;

import java.math.BigDecimal;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Named resource rows with explicit primary keys (including composite keys). */
public final class DataTable {
    private final String name;
    private final List<String> keyFields;
    private final List<Map<String,Object>> rows;
    private final Map<List<Object>,Map<String,Object>> index=new LinkedHashMap<>();

    DataTable(String name,List<String> keyFields,List<Map<String,Object>> rows) {
        this.name=name;this.keyFields=List.copyOf(keyFields);this.rows=copy(rows);
        for(Map<String,Object> row:this.rows) {
            List<Object> key=keyFields.stream().map(field->{
                if(!row.containsKey(field)) throw new IllegalArgumentException(name+": missing key "+field);
                return keyPart(row.get(field));
            }).toList();
            if(index.putIfAbsent(key,row)!=null) throw new IllegalArgumentException(name+": duplicate key "+key);
        }
    }
    private static Object keyPart(Object value) {
        return value instanceof Number ? new BigDecimal(value.toString()).stripTrailingZeros() : value;
    }
    public String name() { return name; }
    public int size() { return rows.size(); }
    public List<String> keyFields() { return keyFields; }
    public List<Map<String,Object>> rows() { return copy(rows); }
    public Optional<Map<String,Object>> find(Object... key) {
        if(key.length!=keyFields.size()) throw new IllegalArgumentException(name+": expected "+keyFields.size()+" key values");
        Map<String,Object> row=index.get(Arrays.stream(key).map(DataTable::keyPart).toList());
        return row==null?Optional.empty():Optional.of(copy(row));
    }
    /** Group IDs are not necessarily unique; never collapse rewards or level rows. */
    public List<Map<String,Object>> matching(String field,Object value) {
        return copy(rows.stream().filter(row->Objects.equals(keyPart(row.get(field)),keyPart(value))).toList());
    }
}

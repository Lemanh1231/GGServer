package emu.leman.ggserver.util;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.file.*;
import java.util.*;

/** JSON boundary helpers; wire field names intentionally remain unchanged. */
public final class Json {
    public static final ObjectMapper MAPPER = new ObjectMapper();
    private Json() {}
    public static Map<String,Object> obj(Object... pairs) {
        Map<String,Object> result = new LinkedHashMap<>();
        for (int i=0;i<pairs.length;i+=2) result.put(String.valueOf(pairs[i]),pairs[i+1]);
        return result;
    }
    @SuppressWarnings("unchecked") public static Map<String,Object> map(Object value) { return value instanceof Map ? (Map<String,Object>)value : new LinkedHashMap<>(); }
    @SuppressWarnings("unchecked") public static List<Object> list(Object value) { return value instanceof List ? (List<Object>)value : new ArrayList<>(); }
    public static String str(Object v) { return v == null ? "" : String.valueOf(v); }
    public static String str(Map<String,Object> m,String k,String fallback) { return m.get(k)==null ? fallback : str(m.get(k)); }
    public static long lng(Object v) { try { return v instanceof Number n ? n.longValue() : new java.math.BigDecimal(str(v)).longValue(); } catch(Exception e) { return 0; } }
    public static int integer(Object v) { return (int)lng(v); }
    public static double dbl(Object v) { try { return v instanceof Number n ? n.doubleValue() : Double.parseDouble(str(v)); } catch(Exception e) { return 0; } }
    public static boolean truth(Object v) { return v!=null && !Boolean.FALSE.equals(v) && (!(v instanceof Number n)||n.doubleValue()!=0) && (!(v instanceof String s)||!s.isEmpty()) && (!(v instanceof Collection<?> c)||!c.isEmpty()) && (!(v instanceof Map<?,?> m)||!m.isEmpty()); }
    public static Object first(Object... values) { for(Object v:values) if(truth(v)) return v; return values.length==0 ? null : values[values.length-1]; }
    public static Object read(Path path) { try { return MAPPER.readValue(Files.readAllBytes(path),Object.class); } catch(Exception e) { throw new IllegalStateException("Cannot read "+path,e); } }
    public static Object parse(String json) { try { return MAPPER.readValue(json,Object.class); } catch(Exception e) { throw new IllegalArgumentException("Invalid JSON",e); } }
    public static String stringify(Object value) { try { return MAPPER.writeValueAsString(value); } catch(Exception e) { throw new IllegalArgumentException(e); } }
    public static byte[] bytes(Object value) { return stringify(value).getBytes(java.nio.charset.StandardCharsets.UTF_8); }
    public static void write(Path path,Object value) { try { if(path.getParent()!=null) Files.createDirectories(path.getParent()); Path tmp=Files.createTempFile(path.getParent(),".json-",".tmp"); Files.write(tmp,bytes(value)); try { Files.move(tmp,path,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING); } catch(AtomicMoveNotSupportedException e) { Files.move(tmp,path,StandardCopyOption.REPLACE_EXISTING); } } catch(Exception e) { throw new IllegalStateException("Cannot write "+path,e); } }
    @SuppressWarnings("unchecked") public static <T> T copy(T value) { return (T)parse(stringify(value)); }
}

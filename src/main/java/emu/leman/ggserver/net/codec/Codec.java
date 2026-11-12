package emu.leman.ggserver.net.codec;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import org.apache.commons.compress.compressors.bzip2.*;
import static emu.leman.ggserver.util.Json.*;

/** Base64(BZip2(TBinaryProtocol(struct))), compatible with the Unity client. */
public final class Codec {
    public final Map<String,Object> schema;
    public Codec(Path root) { this(map(read(root.resolve("schema/schema.json")))); }
    public Codec(emu.leman.ggserver.config.ServerConfig config) { this(map(read(config.resource("schema/schema.json")))); }
    public Codec(Map<String,Object> schema) { this.schema=schema; }
    public Map<String,Object> schemaFor(String name) { return map(schema.get(name)); }
    public static byte[] decodeBody(String text) throws IOException {
        byte[] compressed;
        try { compressed=Base64.getMimeDecoder().decode(text.trim()); }
        catch(IllegalArgumentException e) { throw new IOException("Invalid base64",e); }
        try(var in=new BZip2CompressorInputStream(new ByteArrayInputStream(compressed),true);
            var out=new ByteArrayOutputStream()) {
            byte[] buffer=new byte[8192]; int n;
            while((n=in.read(buffer))!=-1) { if(out.size()+n>64*1024*1024) throw new IOException("Decoded message too large"); out.write(buffer,0,n); }
            return out.toByteArray();
        }
    }
    public static String encodeBody(byte[] raw) throws IOException {
        var bytes=new ByteArrayOutputStream();
        try(var out=new BZip2CompressorOutputStream(bytes,3)) { out.write(raw); }
        return Base64.getEncoder().encodeToString(bytes.toByteArray());
    }
    public record Decoded(Map<String,Object> named,Map<Integer,Object> ids) {}
    public Decoded decodeRequest(String body,String structName) throws IOException {
        Map<Integer,Object> ids=Thrift.readStruct(decodeBody(body));
        return new Decoded(idsToNames(structName,ids),ids);
    }
    public String encodeResponse(String name,Object data) throws IOException { return encodeBody(Thrift.writeStruct(data,name,schema)); }
    public Map<String,Object> idsToNames(String name,Map<?,?> values) {
        Map<String,Object> spec=schemaFor(name),out=new LinkedHashMap<>(); Map<Integer,Map<String,Object>> byId=new HashMap<>();
        for(Object f0:list(spec.get("fields"))) { var f=map(f0); byId.put(integer(f.get("id")),f); }
        for(var e:values.entrySet()) {
            Map<String,Object> f=byId.get(integer(e.getKey()));
            out.put(f==null?str(e.getKey()):str(f.get("name")),f==null?e.getValue():convert(f,e.getValue()));
        }
        return out;
    }
    private Object convert(Map<String,Object> f,Object v) {
        return switch(str(f.get("type"))) {
            case "STRUCT" -> v instanceof Map<?,?> m?idsToNames(str(f.get("struct")),m):v;
            case "LIST","SET" -> {
                if(!(v instanceof List<?> l)) yield v;
                List<Object> out=new ArrayList<>(); for(Object item:l) out.add(convert(map(f.get("elem")),item)); yield out;
            }
            case "MAP" -> {
                if(!(v instanceof Map<?,?> m)) yield v;
                Map<Object,Object> out=new LinkedHashMap<>(); for(var e:m.entrySet()) out.put(e.getKey(),convert(map(f.get("val")),e.getValue())); yield out;
            }
            default -> v;
        };
    }
}

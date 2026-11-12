package emu.leman.ggserver.game;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import org.apache.commons.compress.compressors.bzip2.BZip2CompressorInputStream;
import static emu.leman.ggserver.util.Json.*;

/** Read-only native Thrift capture reader; no dependency on the network codec lifecycle. */
final class ContentCapture {
    private ContentCapture() {}
    static Map<String,Object> read(Path path, Map<String,Object> schema, String type) {
        try (DataInputStream in = new DataInputStream(new BZip2CompressorInputStream(new ByteArrayInputStream(Base64.getMimeDecoder().decode(Files.readString(path)))))) {
            return struct(in,schema,type);
        } catch(IOException | IllegalArgumentException e) { throw new IllegalStateException("Cannot decode content capture " + path,e); }
    }
    private static Map<String,Object> struct(DataInputStream in, Map<String,Object> schema, String name) throws IOException {
        Map<Integer,Map<String,Object>> fields = new HashMap<>();
        for(Object o : list(map(schema.get(name)).get("fields"))) { Map<String,Object> f=map(o); fields.put(integer(f.get("id")), f); }
        Map<String,Object> out = obj();
        for(int tag; (tag=in.readUnsignedByte())!=0;) {
            int id=in.readShort(); Map<String,Object> spec=fields.getOrDefault(id,obj());
            out.put(str(spec.getOrDefault("name",String.valueOf(id))), value(in,tag,schema,spec));
        }
        return out;
    }
    private static Object value(DataInputStream in, int tag, Map<String,Object> schema, Map<String,Object> spec) throws IOException {
        return switch(tag) {
            case 2 -> in.readByte()!=0;
            case 3 -> (int)in.readByte();
            case 4 -> in.readDouble();
            case 6 -> (int)in.readShort();
            case 8 -> in.readInt();
            case 10 -> in.readLong();
            case 11 -> { int size=size(in); byte[] bytes=in.readNBytes(size); if(bytes.length!=size) throw new EOFException(); yield new String(bytes,StandardCharsets.UTF_8); }
            case 12 -> struct(in,schema,str(spec.get("struct")));
            case 13 -> { int k=in.readUnsignedByte(),v=in.readUnsignedByte(),n=size(in); Map<String,Object> out=obj(); for(int i=0;i<n;i++) out.put(str(value(in,k,schema,map(spec.get("key")))),value(in,v,schema,map(spec.get("val")))); yield out; }
            case 14,15 -> { int t=in.readUnsignedByte(),n=size(in); List<Object> out=new ArrayList<>(); for(int i=0;i<n;i++) out.add(value(in,t,schema,map(spec.get("elem")))); yield out; }
            default -> throw new IOException("Unknown Thrift type " + tag);
        };
    }
    private static int size(DataInputStream in) throws IOException { int n=in.readInt(); if(n<0 || n>32_000_000) throw new IOException("Invalid capture size " + n); return n; }
}

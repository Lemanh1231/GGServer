package emu.leman.ggserver.net.codec;

import java.io.*;
import java.math.BigDecimal;
import java.nio.ByteBuffer;
import java.nio.charset.*;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** The game's bare, non-strict TBinaryProtocol structs (no message envelope). */
public final class Thrift {
    public static final int STOP=0, VOID=1, BOOL=2, BYTE=3, DOUBLE=4, I16=6, I32=8,
            I64=10, STRING=11, STRUCT=12, MAP=13, SET=14, LIST=15;
    public static final Map<String,Integer> TYPES=Map.ofEntries(Map.entry("BOOL",BOOL),Map.entry("BYTE",BYTE),
            Map.entry("DOUBLE",DOUBLE),Map.entry("I16",I16),Map.entry("I32",I32),Map.entry("I64",I64),
            Map.entry("STRING",STRING),Map.entry("STRUCT",STRUCT),Map.entry("MAP",MAP),Map.entry("SET",SET),
            Map.entry("LIST",LIST),Map.entry("VOID",VOID));
    private Thrift() {}
    public static Map<Integer,Object> readStruct(byte[] bytes) throws IOException { return new Reader(bytes).struct(0); }
    public static byte[] writeStruct(Object data,String name,Map<String,Object> schema) throws IOException {
        Writer w=new Writer(schema); w.struct(data,name,0); return w.bytes.toByteArray();
    }
    private static final int MAX_DEPTH=128;
    private static void depth(int d) throws IOException { if(d>MAX_DEPTH) throw new IOException("Thrift nesting limit exceeded"); }

    public static final class Reader {
        private final ByteArrayInputStream bytes;
        private final DataInputStream in;
        public Reader(byte[] b) { bytes=new ByteArrayInputStream(b); in=new DataInputStream(bytes); }
        private int count() throws IOException {
            int n=in.readInt();
            if(n<0 || n>16_777_216) throw new IOException("Invalid Thrift collection length: "+n);
            return n;
        }
        public Map<Integer,Object> struct() throws IOException { return struct(0); }
        private Map<Integer,Object> struct(int d) throws IOException {
            depth(d); Map<Integer,Object> out=new LinkedHashMap<>();
            for(int t;(t=in.readUnsignedByte())!=STOP;) { int id=in.readShort(); out.put(id,value(t,d+1)); }
            return out;
        }
        private Object value(int t,int d) throws IOException {
            depth(d);
            return switch(t) {
                case BOOL -> in.readUnsignedByte()!=0;
                case BYTE -> (int)in.readByte();
                case I16 -> (int)in.readShort();
                case I32 -> in.readInt();
                case I64 -> in.readLong();
                case DOUBLE -> in.readDouble();
                case STRING -> {
                    int n=in.readInt();
                    if(n<0 || n>bytes.available()) throw new EOFException("thrift underrun");
                    byte[] raw=in.readNBytes(n);
                    try { yield StandardCharsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(raw)).toString(); }
                    catch(CharacterCodingException e) { yield raw; }
                }
                case STRUCT -> struct(d+1);
                case LIST,SET -> {
                    int et=in.readUnsignedByte(),n=count(); List<Object> out=new ArrayList<>();
                    for(int i=0;i<n;i++) out.add(value(et,d+1)); yield out;
                }
                case MAP -> {
                    int kt=in.readUnsignedByte(),vt=in.readUnsignedByte(),n=count(); Map<Object,Object> out=new LinkedHashMap<>();
                    for(int i=0;i<n;i++) out.put(value(kt,d+1),value(vt,d+1)); yield out;
                }
                default -> throw new IOException("bad type "+t);
            };
        }
    }

    private static final class Writer {
        final ByteArrayOutputStream bytes=new ByteArrayOutputStream();
        final DataOutputStream out=new DataOutputStream(bytes);
        final Map<String,Object> schema;
        Writer(Map<String,Object> schema) { this.schema=schema; }
        long integer(Object v,long min,long max) {
            try {
                if(v instanceof String s && !s.strip().matches("[+-]?[0-9]+")) return 0;
                BigDecimal n=v instanceof Boolean b ? BigDecimal.valueOf(b?1:0) : new BigDecimal(str(v));
                if(n.compareTo(BigDecimal.valueOf(max))>0) return max;
                if(n.compareTo(BigDecimal.valueOf(min))<0) return min;
                return n.longValue();
            } catch(Exception e) { return 0; }
        }
        int type(Map<String,Object> spec,String fallback) { return TYPES.getOrDefault(str(spec,"type",fallback),STRING); }
        void struct(Object value,String name,int d) throws IOException {
            depth(d);
            if(!(value instanceof Map<?,?> data)) { out.writeByte(STOP); return; }
            Map<String,Object> spec=map(schema.get(name));
            if(spec.isEmpty()) {
                for(var e:data.entrySet()) {
                    int id; try { id=Integer.parseInt(str(e.getKey())); } catch(Exception ex) { continue; }
                    Object v=e.getValue(); int t=guess(v);
                    out.writeByte(t); out.writeShort(id); value(t,v,Map.of(),d+1);
                }
            } else for(Object f0:list(spec.get("fields"))) {
                Map<String,Object> f=map(f0); String field=str(f.get("name")); int id=(int)lng(f.get("id"));
                Object v=data.containsKey(field)?data.get(field):data.get(id);
                if(v==null) continue;
                int t=type(f,"STRING"); out.writeByte(t); out.writeShort(id); value(t,v,f,d+1);
            }
            out.writeByte(STOP);
        }
        int guess(Object v) {
            if(v instanceof Boolean) return BOOL;
            if(v instanceof Float || v instanceof Double || v instanceof BigDecimal) return DOUBLE;
            if(v instanceof Number) return I64;
            if(v instanceof List<?>) return LIST;
            if(v instanceof Map<?,?>) return STRUCT;
            return STRING;
        }
        void value(int t,Object v,Map<String,Object> spec,int d) throws IOException {
            depth(d);
            switch(t) {
                case BOOL -> out.writeByte(truth(v)?1:0);
                case BYTE -> {
                    int x=0;
                    try {
                        if(!(v instanceof String s) || s.strip().matches("[+-]?[0-9]+"))
                            x=(v instanceof Boolean b?BigDecimal.valueOf(b?1:0):new BigDecimal(str(v))).toBigInteger().byteValue();
                    } catch(Exception ignored) { }
                    out.writeByte(x&255);
                }
                case I16 -> out.writeShort((int)integer(v,Short.MIN_VALUE,Short.MAX_VALUE));
                case I32 -> out.writeInt((int)integer(v,Integer.MIN_VALUE,Integer.MAX_VALUE));
                case I64 -> out.writeLong(integer(v,Long.MIN_VALUE,Long.MAX_VALUE));
                case DOUBLE -> { double x=dbl(v); out.writeDouble(Math.max(-Double.MAX_VALUE,Math.min(Double.MAX_VALUE,x))); }
                case STRING -> { byte[] b=v instanceof byte[] b0?b0:str(v).getBytes(StandardCharsets.UTF_8); out.writeInt(b.length); out.write(b); }
                case STRUCT -> struct(v,str(spec.get("struct")),d+1);
                case LIST,SET -> {
                    Map<String,Object> es=map(spec.get("elem")); int et=type(es,"STRING");
                    Collection<?> items=v==null?List.of():v instanceof Collection<?> c?c:
                            v instanceof Map<?,?> m && m.isEmpty()?List.of():Collections.singletonList(v);
                    out.writeByte(et); out.writeInt(items.size()); for(Object item:items) value(et,item,es,d+1);
                }
                case MAP -> {
                    Map<String,Object> ks=map(spec.get("key")),vs=map(spec.get("val"));
                    int kt=type(ks,"I32"),vt=type(vs,"STRING"); Map<?,?> m=v instanceof Map<?,?> m0?m0:Map.of();
                    out.writeByte(kt); out.writeByte(vt); out.writeInt(m.size());
                    for(var e:m.entrySet()) { value(kt,e.getKey(),ks,d+1); value(vt,e.getValue(),vs,d+1); }
                }
                default -> throw new IOException("cant write type "+t);
            }
        }
    }
}

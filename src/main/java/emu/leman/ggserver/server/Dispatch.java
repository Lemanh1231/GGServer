package emu.leman.ggserver.server;

import emu.leman.ggserver.net.codec.Codec;
import emu.leman.ggserver.net.CmdId;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Schema-based command identification and response envelopes. */
public final class Dispatch {
    private final Codec codec;
    private final Map<String,List<String>> simple=new LinkedHashMap<>();
    private final Set<String> commands=new HashSet<>();
    public Dispatch(Codec codec) {
        this.codec=codec;
        for(var e:codec.schema.entrySet()) {
            var spec=map(e.getValue()); String name=str(spec.get("name"));
            simple.computeIfAbsent(name,k->new ArrayList<>()).add(e.getKey());
            Set<String> fields=fieldNames(spec);
            if(fields.contains("call") && fields.contains("data") && !name.endsWith("Return")) commands.add(e.getKey());
        }
    }
    private static Set<String> fieldNames(Map<String,Object> spec) {
        Set<String> names=new HashSet<>(); for(Object f:list(spec.get("fields"))) names.add(str(map(f).get("name"))); return names;
    }
    public String resolveCommand(Map<String,?> fields) {
        Object call=fields.get("call");
        if(call instanceof String s && !s.isEmpty()) { String found=resolveSimple(s); if(found!=null) return found; if(commands.contains(s)) return s; }
        for(Object v:fields.values()) if(v instanceof String s) { String found=resolveSimple(s); if(found!=null) return found; }
        for(Object v:fields.values()) if(v instanceof String s && commands.contains(s)) return s;
        return null;
    }
    private String resolveSimple(String s) { for(String full:simple.getOrDefault(s,List.of())) if(commands.contains(full)) return full; return null; }
    public String returnDtoFor(String command) {
        var spec=codec.schemaFor(command); if(spec.isEmpty()) return null;
        String name=str(spec.get("name")),ns=str(spec.get("ns")),candidate=ns+"."+name+"Return";
        if(codec.schema.containsKey(candidate)) return candidate;
        String special=CmdId.SPECIAL_RETURNS.get(name);
        if(special!=null) { candidate=ns+"."+special; if(codec.schema.containsKey(candidate)) return candidate; return simple.getOrDefault(special,List.of()).stream().findFirst().orElse(null); }
        return null;
    }
    public String retdataDtoFor(String command) {
        for(Object f0:list(codec.schemaFor(returnDtoFor(command)).get("fields"))) { var f=map(f0); if("data".equals(f.get("name"))) return str(f.get("struct")); } return null;
    }
    public record Message(String field,String body) {}
    public static Message findMessageField(Map<String,?> form) {
        for(String field:List.of("tapsonic_data","msg","data")) if(form.get(field) instanceof String s && s.length()>=8) return new Message(field,s);
        Message best=null;
        for(var e:form.entrySet()) {
            if(!(e.getValue() instanceof String s) || s.length()<8) continue;
            byte[] raw; try { raw=Base64.getMimeDecoder().decode(s); } catch(Exception ex) { continue; }
            if(raw.length>=3 && raw[0]=='B' && raw[1]=='Z' && raw[2]=='h') return new Message(e.getKey(),s);
            if(best==null || s.length()>best.body.length()) best=new Message(e.getKey(),s);
        }
        return best==null?new Message(null,null):best;
    }
    public static Map<String,Object> nowTimes() {
        Instant now=Instant.now();
        long dt=Long.parseLong(DateTimeFormatter.ofPattern("yyyyMMddHHmmss").withZone(ZoneOffset.ofHours(9)).format(now));
        return obj("time",now.getEpochSecond(),"datetime",dt);
    }
    public record Envelope(String dto,Map<String,Object> data) {}
    public Envelope buildReturn(String command,Object retData,String call,String category,Map<String,Object> error) {
        String dto=returnDtoFor(command); if(dto==null) return new Envelope(null,null);
        Map<String,Object> spec=codec.schemaFor(dto); Set<String> names=fieldNames(spec);
        if(error==null || error.isEmpty()) error=obj("code",0,"errmsg","");
        Map<String,Object> env=obj();
        if(names.contains("error")) env.put("error",obj("code",error.getOrDefault("code",0),"errmsg",error.getOrDefault("errmsg","")));
        if(names.contains("server_time")) env.put("server_time",nowTimes());
        if(names.contains("mode")) env.put("mode",truth(category)?category:codec.schemaFor(command).get("ns"));
        if(names.contains("call")) env.put("call",truth(call)?call:codec.schemaFor(command).get("name"));
        if(names.contains("data") && lng(error.get("code"))==0) {
            String dtype="STRUCT";
            for(Object f0:list(spec.get("fields"))) { var f=map(f0); if("data".equals(f.get("name"))) dtype=str(f.get("type")); }
            Object value=retData instanceof Map<?,?>?retData:obj();
            if(dtype.equals("LIST") || dtype.equals("SET")) value=retData==null?List.of():retData instanceof Collection<?> c?new ArrayList<>(c):retData instanceof Map<?,?> m && m.isEmpty()?List.of():List.of(retData);
            env.put("data",value);
        }
        if(names.contains("maintenance")) env.put("maintenance",obj());
        return new Envelope(dto,env);
    }
}

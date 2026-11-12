package emu.leman.ggserver.server;

import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.*;

/** Unity WWWForm parser. Multipart duplicate fields use the last value; URL forms use the first. */
public final class Multipart {
    private static final Pattern BOUNDARY=Pattern.compile("boundary=([^;]+)",Pattern.CASE_INSENSITIVE);
    private static final Pattern NAME=Pattern.compile("(?:^|[;\\s])name=\"([^\"]*)\"");
    private Multipart() {}
    public static Map<String,Object> parse(String contentType,byte[] body) {
        String ct=contentType==null?"":contentType.toLowerCase(Locale.ROOT);
        if(ct.contains("multipart/form-data")) {
            Matcher m=BOUNDARY.matcher(contentType); if(!m.find()) return new LinkedHashMap<>();
            String b=m.group(1).trim(); if(b.startsWith("\"") && b.endsWith("\"")) b=b.substring(1,b.length()-1);
            return multipart(body,b);
        }
        if(!ct.isEmpty() && !ct.contains("application/x-www-form-urlencoded")) {
            String raw=new String(body,StandardCharsets.ISO_8859_1); Matcher m=Pattern.compile("^--([^\\r\\n]+)\\r\\n").matcher(raw);
            if(m.find()) return multipart(body,m.group(1));
        }
        return urlencoded(body);
    }
    public static Map<String,Object> urlencoded(byte[] body) {
        Map<String,Object> out=new LinkedHashMap<>();
        for(String part:new String(body,StandardCharsets.UTF_8).split("&")) {
            if(part.isEmpty()) continue; int eq=part.indexOf('=');
            try {
                String name=URLDecoder.decode(eq<0?part:part.substring(0,eq),StandardCharsets.UTF_8);
                String value=URLDecoder.decode(eq<0?"":part.substring(eq+1),StandardCharsets.UTF_8);
                out.putIfAbsent(name,value);
            } catch(IllegalArgumentException ignored) { }
        }
        return out;
    }
    private static Map<String,Object> multipart(byte[] body,String boundary) {
        Map<String,Object> out=new LinkedHashMap<>();
        String raw=new String(body,StandardCharsets.ISO_8859_1);
        for(String part:raw.split(Pattern.quote("--"+boundary),-1)) {
            part=part.replaceAll("^[\\r\\n]+|[\\r\\n]+$","");
            if(part.isEmpty() || part.equals("--")) continue;
            int split=part.indexOf("\r\n\r\n"); if(split<0) continue;
            Matcher m=NAME.matcher(part.substring(0,split)); if(!m.find()) continue;
            String name=new String(m.group(1).getBytes(StandardCharsets.ISO_8859_1),StandardCharsets.UTF_8);
            byte[] value=part.substring(split+4).replaceAll("[\\r\\n]+$","").getBytes(StandardCharsets.ISO_8859_1);
            try { out.put(name,StandardCharsets.UTF_8.newDecoder().decode(java.nio.ByteBuffer.wrap(value)).toString()); }
            catch(java.nio.charset.CharacterCodingException e) { out.put(name,value); }
        }
        return out;
    }
}

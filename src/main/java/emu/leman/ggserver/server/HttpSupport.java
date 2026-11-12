package emu.leman.ggserver.server;

import com.sun.net.httpserver.HttpExchange;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.zip.*;

/** Shared response semantics: CORS and real Content-Length on HEAD as required by Unity CDN. */
public final class HttpSupport {
    private HttpSupport() {}
    public static void send(HttpExchange exchange,String body,int code,String contentType) throws IOException {
        send(exchange,body.getBytes(StandardCharsets.UTF_8),code,contentType);
    }
    public static void send(HttpExchange exchange,byte[] body,int code,String contentType) throws IOException {
        var headers=exchange.getResponseHeaders(); headers.set("Content-Type",contentType); headers.set("Access-Control-Allow-Origin","*");
        headers.set("Content-Length",String.valueOf(body.length));
        if(exchange.getRequestMethod().equals("HEAD") || body.length==0) { exchange.sendResponseHeaders(code,-1); exchange.close(); return; }
        exchange.sendResponseHeaders(code,body.length);
        try(var out=exchange.getResponseBody()) { out.write(body); }
    }
    public static void sendFile(HttpExchange exchange,Path file,String filename,String type) throws IOException {
        if(!Files.isRegularFile(file)) { send(exchange,"File Not Found",404,"text/plain; charset=utf-8"); return; }
        long size=Files.size(file); var headers=exchange.getResponseHeaders();
        headers.set("Content-Type",type); headers.set("Content-Length",String.valueOf(size));
        headers.set("Access-Control-Allow-Origin","*"); headers.set("Accept-Ranges","bytes");
        if(filename!=null) headers.set("Content-Disposition","attachment; filename=\""+filename.replace("\"","")+"\"");
        if(exchange.getRequestMethod().equals("HEAD") || size==0) { exchange.sendResponseHeaders(200,-1); exchange.close(); return; }
        long start=0,end=size-1;int status=200;
        String range=exchange.getRequestHeaders().getFirst("Range");
        // Single byte ranges support interrupted APK downloads. Ignore unsupported
        // units/multiple ranges and If-Range (no validator), serving the full file.
        if(range!=null && range.startsWith("bytes=") && !range.contains(",") && exchange.getRequestHeaders().getFirst("If-Range")==null) {
            try {
                String spec=range.substring(6);
                if(!spec.matches("[0-9]*-[0-9]*") || spec.equals("-")) throw new IllegalArgumentException();
                String[] parts=spec.split("-",-1);
                if(parts[0].isEmpty()) { long suffix=Long.parseLong(parts[1]);if(suffix<=0) throw new IllegalArgumentException();start=Math.max(0,size-suffix); }
                else { start=Long.parseLong(parts[0]);if(!parts[1].isEmpty()) end=Math.min(end,Long.parseLong(parts[1])); }
                if(start>=size || end<start) throw new IllegalArgumentException();
                status=206;headers.set("Content-Range","bytes "+start+"-"+end+"/"+size);
            } catch(IllegalArgumentException ex) {
                headers.set("Content-Range","bytes */"+size);headers.set("Content-Length","0");
                exchange.sendResponseHeaders(416,-1);exchange.close();return;
            }
        }
        long length=end-start+1;headers.set("Content-Length",String.valueOf(length));
        exchange.sendResponseHeaders(status,length);
        try(var in=Files.newInputStream(file);var out=exchange.getResponseBody()) {
            in.skipNBytes(start);byte[] buffer=new byte[64*1024];long remaining=length;
            while(remaining>0) { int count=in.read(buffer,0,(int)Math.min(buffer.length,remaining));if(count<0) break;out.write(buffer,0,count);remaining-=count; }
        }
    }
    public static byte[] readBody(HttpExchange exchange) throws IOException {
        InputStream in=exchange.getRequestBody();
        if("gzip".equalsIgnoreCase(exchange.getRequestHeaders().getFirst("Content-Encoding"))) in=new GZIPInputStream(in);
        try(InputStream input=in;var out=new ByteArrayOutputStream()) {
            byte[] buffer=new byte[8192]; int n;
            while((n=input.read(buffer))!=-1) { if(out.size()+n>64*1024*1024) throw new IOException("Request body too large"); out.write(buffer,0,n); }
            return out.toByteArray();
        }
    }
}

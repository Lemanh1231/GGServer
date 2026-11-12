package com.kotori.guitargirl.network;

import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.regex.*;

/** Refresh cached SDK credentials through the normal login API, never bypass server validation. */
final class SessionTokenBridge {
    private final Map<String,String> sessions = new LinkedHashMap<String,String>();

    synchronized byte[] prepare(String path, Map<String,List<String>> headers, byte[] body,
                                String domain, String release, String localProxy) throws IOException {
        String contentType = "";
        for (Map.Entry<String,List<String>> entry : headers.entrySet()) {
            if (entry.getKey().equalsIgnoreCase("Content-Type") && !entry.getValue().isEmpty()) contentType = entry.getValue().get(0);
        }
        String text = new String(body, StandardCharsets.UTF_8);
        boolean multipart = contentType.toLowerCase(Locale.US).contains("multipart/form-data");
        Matcher field = (multipart
            ? Pattern.compile("(?i)Content-Disposition:[^\\r\\n]*name=\"access_token\"[^\\r\\n]*\\r\\n(?:[^\\r\\n]+\\r\\n)*\\r\\n([^\\r\\n]*)")
            : Pattern.compile("(?:^|&)access_token=([^&]*)")).matcher(text);
        if (!field.find()) return body;
        String oldToken = multipart ? field.group(1) : URLDecoder.decode(field.group(1), "UTF-8");
        String token = sessions.get(oldToken);
        boolean login = path.contains("/userLogin/") || path.contains("/userJoin/");
        if (login) {
            sessions.remove(oldToken);
            token = null;
            String response = null;
            boolean opaque = false;
            String[] parts = oldToken.split("\\|", -1);
            // Cached Python and Java SDK tokens use member|app|device|locale|... .
            // Opaque tokens instead require the server's DTO/device identity checks below.
            if (parts.length >= 5 && !parts[2].isEmpty() && parts[2].length() <= 256) {
                response = refresh(domain, release, localProxy, parts[1], parts[2]);
            } else if (!oldToken.isEmpty()) {
                // The actual device uses an opaque provider credential. Let the native
                // server decode the existing game DTO and perform normal guest SDK login.
                opaque = true;
                response = exchange(domain, release, localProxy,
                    "/api/accounts/v3/global/game-session",contentType,body);
            }
            if(response!=null) {
                token=jsonString(response,"access_token");
                if(token==null) throw new IOException("Session refresh returned no token");
                if(opaque) {
                    String messageField=jsonString(response,"message_field");
                    String normalized=jsonString(response,"normalized_message");
                    if(messageField==null || normalized==null || !Arrays.asList("tapsonic_data","msg","data").contains(messageField))
                        throw new IOException("Session refresh returned no normalized login message");
                    text=replaceField(text,multipart,messageField,normalized);
                    // Re-find offsets: replacing the message may shift the token field.
                    field=field(text,multipart,"access_token");
                    if(!field.find()) throw new IOException("Login token field disappeared");
                }
            }
            if(token!=null) {
                if (sessions.size() >= 32) sessions.clear();
                sessions.put(oldToken, token);
            }
        }
        if (token == null) return body;
        String replacement = multipart ? token : URLEncoder.encode(token, "UTF-8");
        return (text.substring(0, field.start(1)) + replacement + text.substring(field.end(1))).getBytes(StandardCharsets.UTF_8);
    }

    private static Matcher field(String text,boolean multipart,String name) {
        return (multipart
            ? Pattern.compile("(?i)Content-Disposition:[^\\r\\n]*name=\""+Pattern.quote(name)+"\"[^\\r\\n]*\\r\\n(?:[^\\r\\n]+\\r\\n)*\\r\\n([^\\r\\n]*)")
            : Pattern.compile("(?:^|&)"+Pattern.quote(name)+"=([^&]*)")).matcher(text);
    }
    private static String replaceField(String text,boolean multipart,String name,String value)throws IOException {
        Matcher match=field(text,multipart,name);
        if(!match.find()) throw new IOException("Login message field missing");
        String encoded=multipart?value:URLEncoder.encode(value,"UTF-8");
        return text.substring(0,match.start(1))+encoded+text.substring(match.end(1));
    }
    private static String jsonString(String json,String name) {
        Matcher match=Pattern.compile("\""+Pattern.quote(name)+"\"\\s*:\\s*\"([^\"\\\\]*)\"").matcher(json);
        return match.find()?match.group(1):null;
    }

    private String refresh(String domain, String release, String localProxy, String app, String device) throws IOException {
        byte[] form = ("app_id=" + URLEncoder.encode(app,"UTF-8") + "&device_cd=" + URLEncoder.encode(device,"UTF-8")).getBytes(StandardCharsets.UTF_8);
        return exchange(domain,release,localProxy,"/api/accounts/v3/global/login","application/x-www-form-urlencoded",form);
    }

    private String exchange(String domain,String release,String localProxy,String path,String contentType,byte[] form) throws IOException {
        HttpURLConnection connection = (HttpURLConnection)new URL(domain + path).openConnection();
        connection.setConnectTimeout(3500); connection.setReadTimeout(8000);
        connection.setInstanceFollowRedirects(false); connection.setRequestMethod("POST"); connection.setDoOutput(true);
        connection.setRequestProperty("X-GG-Client-Release", release);
        connection.setRequestProperty("X-GG-Local-Proxy", localProxy);
        connection.setRequestProperty("Content-Type", contentType);
        connection.setFixedLengthStreamingMode(form.length);
        try {
            try (OutputStream output = connection.getOutputStream()) { output.write(form); }
            int status=connection.getResponseCode();
            // Authentication denial is not an unavailable domain. Let the unchanged
            // RPC receive normal Java rejection; do not retry on other domains.
            if(status==401 || status==403) return null;
            if(status!=200) throw new IOException("Session refresh HTTP " + status);
            ByteArrayOutputStream bytes = new ByteArrayOutputStream();
            try (InputStream input = connection.getInputStream()) {
                byte[] buffer = new byte[4096]; int count;
                while ((count = input.read(buffer)) != -1) {
                    if (bytes.size() + count > 65536) throw new IOException("Session refresh response too large");
                    bytes.write(buffer,0,count);
                }
            }
            String json = new String(bytes.toByteArray(),StandardCharsets.UTF_8);
            String code=jsonString(json,"result_code");
            if("401".equals(code) || "403".equals(code)) return null;
            if(!"000".equals(code)) throw new IOException("Session refresh invalid result");
            return json;
        } finally { connection.disconnect(); }
    }
}

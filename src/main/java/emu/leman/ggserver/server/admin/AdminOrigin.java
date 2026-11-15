package emu.leman.ggserver.server.admin;

import com.sun.net.httpserver.HttpExchange;
import java.net.URI;
import java.util.Locale;

/** Reject cross-origin admin writes, retaining non-browser Bearer API compatibility. */
final class AdminOrigin {
    private AdminOrigin() {}
    static boolean allowed(HttpExchange exchange,String publicBase) {
        var headers=exchange.getRequestHeaders();
        String site=headers.getFirst("Sec-Fetch-Site");
        if(site!=null && !site.equals("same-origin") && !site.equals("none"))return false;
        String type=headers.getFirst("Content-Type");
        if(type==null || !type.split(";",2)[0].strip().equalsIgnoreCase("application/json"))return false;
        String origin=headers.getFirst("Origin"),referer=headers.getFirst("Referer");
        if(origin==null && referer==null) {
            // Browsers making credentialed JSON POSTs send Origin. No-origin clients must
            // authenticate explicitly; login/logout do not change game/account state.
            String bearer=headers.getFirst("Authorization");
            return site==null && (bearer!=null && bearer.startsWith("Bearer ")
                    || exchange.getRequestURI().getPath().equals("/admin/api/login")
                    || exchange.getRequestURI().getPath().equals("/admin/api/logout")
                    || exchange.getRequestURI().getPath().equals("/admin/logout"));
        }
        try {
            URI source=URI.create(origin==null?referer:origin);
            String host=headers.getFirst("Host");
            if(host==null || host.contains(","))return false;
            // Only accept a scheme from configured publicBase when it names this host.
            String scheme=exchange instanceof com.sun.net.httpserver.HttpsExchange?"https":"http";
            String forwarded=headers.getFirst("X-Forwarded-Proto");
            if("https".equals(forwarded) || "http".equals(forwarded))scheme=forwarded;
            if(!publicBase.isBlank()) {
                URI configured=URI.create(publicBase);
                if(host.equalsIgnoreCase(configured.getRawAuthority()))scheme=configured.getScheme();
            }
            URI target=URI.create(scheme+"://"+host);
            return source.getUserInfo()==null && source.getHost()!=null
                    && source.getScheme().toLowerCase(Locale.ROOT).equals(scheme)
                    && source.getHost().equalsIgnoreCase(target.getHost()) && port(source)==port(target)
                    && (origin==null || source.getRawPath().isEmpty()) && source.getRawQuery()==null && source.getRawFragment()==null;
        } catch(RuntimeException invalid){return false;}
    }
    private static int port(URI uri){return uri.getPort()<0?("https".equalsIgnoreCase(uri.getScheme())?443:80):uri.getPort();}
}

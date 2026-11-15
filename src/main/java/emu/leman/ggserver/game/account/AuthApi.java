package emu.leman.ggserver.game.account;

import emu.leman.ggserver.Services;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Native NeonAPI/PmangPlus endpoints; null means the path is not an auth route. */
public final class AuthApi {
    private final Services s;
    public AuthApi(Services services) { s = services; }
    public record Response(byte[] body, String contentType) {}

    public Response handle(String path, Map<String,Object> form) {
        return handle(path,form,"");
    }

    public Response handle(String path, Map<String,Object> form,String ip) {
        String p = path.split("\\?", 2)[0];
        if (p.startsWith("/api/")) p = p.substring(4);
        if (p.equals("/accounts/v3/global/login")) return json(login(form,ip));
        if (p.startsWith("/eula/")) {
            Path file = s.config.resource("static/eula.html");
            if (!Files.exists(file)) file = s.root.resolve("emulator/static/eula.html");
            try { return new Response(Files.exists(file) ? Files.readAllBytes(file) : "<html>OK</html>".getBytes(StandardCharsets.UTF_8), "text/html; charset=utf-8"); }
            catch (java.io.IOException e) { throw new IllegalStateException("Cannot read EULA", e); }
        }
        if (p.equals("/referrer/save")) return json(simple("OK"));
        if (p.startsWith("/gcm/")) return json(obj("value",obj("unsubscription",List.of(),"subscription",List.of(),"fcmheader","CsYsPQf1UEU:APA91bE1dMmiUqnw5HACZ9GstHG8U_K-5sNxSgWWPbNZBOfP93v2M7PzjATrXetY_vnzRc5aFQAbS2TGpKDniifN5DDcfUlPG4MVWkhSHjUHS_X6ViwpImmU5BteBUZhjBAAAAq1Zi1q"),"result_code","","result_msg",""));
        if (p.equals("/analytics") || p.endsWith("/analytics")) return json(simple(true));
        if (p.contains("geoip")) return json(simple("US"));
        if (p.startsWith("/accounts/") || p.startsWith("/app/") || p.startsWith("/api/")) return json(simple(true));
        return null;
    }

    public Map<String,Object> login(Map<String,Object> form) {
        return login(form,"");
    }

    public Map<String,Object> login(Map<String,Object> form,String ip) {
        long now = System.currentTimeMillis(), memberId = 429071553;
        String appId = str(form,"app_id","0"), device = str(form,"device_cd",""), nick = "Guitarist";
        String canonical = device.isEmpty() ? "neon_"+UUID.randomUUID() : device;
        if (!device.isEmpty()) {
            // Repository lookup also accepts UUID/u_seq/u_id aliases. Those are
            // account selectors, not guest credentials: require the stored device
            // before createUser can update account metadata or a session is issued.
            var existing=s.state.getUser(device);
            if(existing!=null && !device.equals(str(map(existing.get("userdata")).get("device_uuid"))))
                return rejectedGuestIdentity();
            Map<String,Object> user = AuthContent.createUser(s,device,device,ip);
            Map<String,Object> ud = map(user.get("userdata"));
            // Recheck the resolved result, including account-creation races.
            if(!device.equals(str(ud.get("device_uuid"))))return rejectedGuestIdentity();
            canonical = str(first(user.get("uuid"),ud.get("uuid"),device));
            memberId = lng(first(ud.get("u_seq"), memberId));
            nick = str(first(ud.get("u_nick"),nick));
        }
        String token = s.sessions.create(canonical,device,ip,memberId+"|"+appId+"|"+device+"|KR|","|"+now).token();
        Map<String,Object> member = obj("crt_dt",now,"upd_dt",now,"status_cd","OK","member_id",memberId,"nickname",nick,
            "profile_img_url",null,"feeling",null,"adult_auth_yn","N","adult_auth_dt",null,"recent_login_dt",null,
            "recent_app_id",integer(appId),"email",null,"anonymous_yn","N","friend_accept_cd",null,"reg_path",null,
            "recent_app_title","Guitar Girl","last_msg_dt",null,"new_msg_yn",null,"conflict_member_id",0,"reg_ip","127.0.0.1",
            "reg_nation","US","is_guest_login",false,"provider_display_name","PmangPlus","pushgroup",null,"locale",null);
        return simple(obj("access_token",token,"member",member,"force_receipt",null,"conflict_member_id",null,"is_guest_login",false,
            "old_member_id",null,"jailbreak_yn","N","fcm_send_lang","EN","unreg_status","NO","unreg_remain_time",null,"callTime",0));
    }
    private static Map<String,Object> rejectedGuestIdentity() {
        return obj("value",null,"result_code","401","result_msg","Guest identity could not be verified; no session issued");
    }
    private static Map<String,Object> simple(Object value) { return obj("value",value,"result_code","000","result_msg","API_OK"); }
    private static Response json(Object value) { return new Response(bytes(value),"application/json; charset=utf-8"); }
}

package emu.leman.ggserver.server;

import emu.leman.ggserver.Services;
import java.util.Map;
import static emu.leman.ggserver.util.Json.*;

/** Validates every supplied account alias; no client token is ever imported as a session. */
final class SessionAccess {
    record Decision(String uuid,String error) {}
    /** Structural diagnostics only: never retain a token, device/app ID, or token hash. */
    static Map<String,Object> diagnostics(String token,String contentType) {
        String value=token==null?"":token;
        String type=contentType==null?"":contentType.toLowerCase(java.util.Locale.ROOT);
        return obj("present",!value.isBlank(),"length",value.length(),
                "pipeFields",value.isEmpty()?0:value.split("\\|",-1).length,
                "urlEncodedPipes",value.toLowerCase(java.util.Locale.ROOT).contains("%7c"),
                "form",type.contains("multipart/form-data")?"multipart":
                        type.contains("application/x-www-form-urlencoded")?"urlencoded":"other");
    }
    static Decision validate(Services services,String token,Map<String,Object> request,boolean bootstrap) {
        // Public startup tables/routing must work with a cached Python/expired
        // SDK token so the client can reach Neon login and obtain a fresh session.
        // This grants no account identity; protected commands still reject it.
        if(bootstrap) return new Decision(null,null);
        if(token==null || token.isBlank()) return new Decision(null,services.config.sessionRequired&&!bootstrap?"Session token required":null);
        var session=services.sessions.find(token);
        if(session==null) return new Decision(null,"Session expired or invalid; please log in again");
        Map<String,Object> payload=map(request==null?null:request.get("data"));
        // The wire user DTO has no UUID field, so Unity may keep its patched provider
        // placeholder after login. Normalize only with a valid issued session AND the
        // exact stored device belonging to that session. All real aliases stay strict.
        // Resolve fresh identity metadata for every check; gameplay sections are
        // unnecessary here, and cross-request caching could retain reassigned aliases.
        if("452465183".equals(str(payload.get("uuid")))) {
            String device=str(payload.get("device_uuid"));
            var account=services.state.getIdentity(device);
            if(!emu.leman.ggserver.database.StateStore.isRealDeviceUuid(device) || account==null
                    || !device.equals(account.deviceUuid())
                    || !session.canonicalUuid().equals(account.canonicalUuid()))
                return new Decision(null,"Session does not belong to this device");
            var collision=services.state.getIdentity("452465183");
            if(collision!=null && !session.canonicalUuid().equals(collision.canonicalUuid()))
                return new Decision(null,"Provider placeholder conflicts with account identity");
            // Validate the other claims before mutating the decoded request.
            for(String field:new String[]{"u_seq","u_id"}) {
                String alias=str(payload.get(field));
                if(alias.isBlank() || alias.equals("0")) continue;
                var other=services.state.getIdentity(alias);
                if(other==null || !session.canonicalUuid().equals(other.canonicalUuid()))
                    return new Decision(null,"Session does not belong to this account");
            }
            payload.put("uuid",session.canonicalUuid());
        }
        for(String field:new String[]{"uuid","device_uuid","u_seq","u_id"}) {
            String alias=str(payload.get(field));
            if(alias.isBlank() || alias.equals("0")) continue;
            var account=services.state.getIdentity(alias);
            String canonical=account==null?alias:account.canonicalUuid();
            if(!canonical.equals(session.canonicalUuid())) return new Decision(null,"Session does not belong to this account");
        }
        if(!services.sessions.touch(session)) return new Decision(null,"Session expired or invalid; please log in again");
        return new Decision(session.canonicalUuid(),null);
    }
}

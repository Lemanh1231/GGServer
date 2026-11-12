package emu.leman.ggserver.server;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.game.account.AuthApi;
import emu.leman.ggserver.net.codec.Codec;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Guest SDK login adapter for clients whose opaque provider token has no device framing.
 * The old token is never accepted as a session. Device credentials have the same trust
 * model as Neon device_cd login; UUID/UID aliases alone must never select an account.
 */
final class GameSessionLogin {
    // Provider placeholder emitted by this patched APK; never an account credential/alias.
    private static final String PATCHED_PROVIDER_ID="452465183";
    record Outcome(Map<String,Object> response,String reason) {}
    private GameSessionLogin() {}
    static Outcome login(Services services,Codec codec,Map<String,Object> form,String ip,
                                    java.util.function.Function<String,Object> accountLock) {
        try {
            String command=new Dispatch(codec).resolveCommand(form);
            if(!Set.of("user.userLogin","user.userJoin").contains(command==null?"":command)) return rejected("unsupported_command");
            var message=Dispatch.findMessageField(form);
            if(message.body()==null || !Set.of("tapsonic_data","msg","data").contains(message.field())) return rejected("missing_message");
            Map<String,Object> request=codec.decodeRequest(message.body(),command).named();
            Map<String,Object> payload=map(request.get("data"));
            String device=str(payload.get("device_uuid"));
            if(!emu.leman.ggserver.database.StateStore.isRealDeviceUuid(device)) return rejected("invalid_device_format");
            synchronized(accountLock.apply(device)) {
                var user=services.state.getUser(device);
                String canonical=user==null?null:str(user.get("uuid"));
                // A device must be the actual stored device, not just an alias/UID of another account.
                if(user!=null && !device.equals(str(map(user.get("userdata")).get("device_uuid")))) return rejected("device_not_stored_device");
                for(String field:List.of("uuid","u_seq","u_id")) {
                    String alias=str(payload.get(field));
                    if(alias.isBlank() || alias.equals("0")) continue;
                    // Ignore only the exact patched provider placeholder in this guest adapter.
                    // Never persist it as an alias and never relax protected RPC validation.
                    if(field.equals("uuid") && alias.equals(PATCHED_PROVIDER_ID)) {
                        var collision=services.state.getUser(alias);
                        if(collision!=null && !str(collision.get("uuid")).equals(canonical)) return rejected("provider_id_collision");
                        continue;
                    }
                    if(user==null) {
                        if(!field.equals("uuid") || !alias.equals(device)) return rejected("unknown_device_alias_"+field);
                    } else {
                        var other=services.state.getUser(alias);
                        if(other==null || !canonical.equals(str(other.get("uuid")))) return rejected("alias_mismatch_"+field);
                    }
                }
                if(user!=null && truth(user.get("is_banned"))) return rejected("banned");
                // Encode before issuing a session so malformed messages cannot leave sessions behind.
                payload.put("uuid",user==null?device:canonical);
                String normalized=codec.encodeResponse(command,request);
                var response=new AuthApi(services).login(obj("device_cd",device,"app_id","0"),ip);
                map(response.get("value")).putAll(obj("message_field",message.field(),"normalized_message",normalized));
                return new Outcome(response,"verified");
            }
        } catch(java.io.IOException|IllegalArgumentException failure) { return rejected("malformed_message"); }
    }
    private static Outcome rejected(String reason) {
        return new Outcome(obj("value",null,"result_code","401","result_msg","Guest identity could not be verified; no session issued"),reason);
    }
}

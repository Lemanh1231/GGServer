package emu.leman.ggserver.net;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import static emu.leman.ggserver.util.Json.*;

/** A request envelope, not a new wire format. Null values and legacy field names survive. */
public final class GamePacket {
    private final String command;
    private final Map<String,Object> request;
    private final Map<String,Object> payload;
    private final Map<String,Object> context;

    public GamePacket(String command, Map<String,Object> request, Map<String,Object> context) {
        this.command=command;
        this.request=copy(request);
        this.payload=copy(HandlerRegistry.payload(this.request));
        this.context=copy(context);
    }

    private static Map<String,Object> copy(Map<String,Object> values) {
        return Collections.unmodifiableMap(new LinkedHashMap<>(values==null ? Map.of() : values));
    }

    public String command() { return command; }
    public Map<String,Object> request() { return request; }
    public Map<String,Object> payload() { return payload; }
    public Map<String,Object> context() { return context; }

    /** Same identity precedence as the original auth/profile handlers after payload normalization. */
    public String identity() { return str(first(payload.get("uuid"),payload.get("device_uuid"),context.get("uuid"))); }
}

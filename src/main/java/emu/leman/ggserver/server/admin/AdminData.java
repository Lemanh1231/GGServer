package emu.leman.ggserver.server.admin;

import emu.leman.ggserver.Services;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Backend-independent management listings; mutations go through StateStore. */
final class AdminData {
    private final Services services;
    AdminData(Services services) { this.services = services; }
    List<Map<String,Object>> rows() {
        return services.state.listUserRows();
    }
    String resolve(Map<String,Object> request) {
        String uuid = str(request.get("uuid"));
        if (!uuid.isBlank() && !uuid.equals("null")) return uuid;
        long seq = lng(request.get("u_seq"));
        if (seq != 0) for (var row : rows()) if (lng(row.get("u_seq")) == seq) return str(row.get("uuid"));
        throw new IllegalArgumentException("Thiếu mã UUID của người chơi!");
    }
}

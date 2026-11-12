package emu.leman.ggserver.server.admin;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.game.social.SocialPosts;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Management adapter to the shared native mailbox implementation. */
public final class AdminPosts {
    private final Services services;
    private final SocialPosts posts;
    public AdminPosts(Services services) { this.services = services; this.posts = new SocialPosts(services); }
    public Map<String,Object> send(String uuid, Object title, Object memo, List<Object> items) {
        return send(uuid, title, memo, items, false);
    }
    public Map<String,Object> send(String uuid, Object title, Object memo, List<Object> items, boolean appliesToNewUsers) {
        if (uuid == null) {
            // Hold the global gate before SocialPosts reads any recipient snapshots. Account
            // handlers hold the read side of this gate across their complete read/modify/save.
            return services.registry.withExclusiveLock(
                    () -> checked(posts.sendPost(null, title, memo, items, 1, appliesToNewUsers)));
        }
        var user = services.state.getUser(uuid);
        if (user == null) throw new IllegalArgumentException("Không tìm thấy tài khoản người chơi nhận thư!");
        String canonical = str(user.get("uuid"));
        return services.registry.withAccountLock(canonical,
                () -> checked(posts.sendPost(canonical, title, memo, items, 1, appliesToNewUsers)));
    }
    private static Map<String,Object> checked(Map<String,Object> post) {
        if (post == null) throw new IllegalArgumentException("Không tìm thấy tài khoản người chơi nhận thư!");
        return post;
    }
}

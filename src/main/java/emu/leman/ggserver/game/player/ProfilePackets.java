package emu.leman.ggserver.game.player;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.CmdId;
import emu.leman.ggserver.net.GamePacket;
import emu.leman.ggserver.net.NetHandler;
import emu.leman.ggserver.net.Result;
import java.util.List;
import java.util.Map;
import static emu.leman.ggserver.util.Json.*;

/** Thin wire adapters. Persistence and profile projection belong to ProfileManager. */
public final class ProfilePackets {
    private ProfilePackets() {}

    public static List<NetHandler> handlers(Services services) {
        return List.of(new UpdateNickname(services),new UpdateAvatar(services),new UpdateTitle(services),new GetProfile(services));
    }

    private abstract static class ProfileHandler extends NetHandler {
        private final Services services;
        ProfileHandler(String command, Services services) { super(command); this.services=services; }
        final ProfileManager profile(GamePacket packet) { return new Player(services,packet.identity()).profile(); }
    }

    private static final class UpdateNickname extends ProfileHandler {
        UpdateNickname(Services services) { super(CmdId.UPDATE_NICK_NAME,services); }
        @Override public Result handle(GamePacket packet) {
            Object value=packet.payload().getOrDefault("nickname","Guitarist");
            profile(packet).setNickname(value);
            return Result.ok(obj("nickname",value));
        }
    }

    private static final class UpdateAvatar extends ProfileHandler {
        UpdateAvatar(Services services) { super(CmdId.UPDATE_AVATAR,services); }
        @Override public Result handle(GamePacket packet) {
            Map<String,Object> p=packet.payload();
            Object value=first(p.get("u_avatar"),p.getOrDefault("avatar",1));
            profile(packet).setAvatar(value);
            return Result.ok(obj("u_avatar",value));
        }
    }

    private static final class UpdateTitle extends ProfileHandler {
        UpdateTitle(Services services) { super(CmdId.UPDATE_USER_TITLE,services); }
        @Override public Result handle(GamePacket packet) {
            Map<String,Object> p=packet.payload();
            Object value=first(p.get("u_title"),p.getOrDefault("title",1));
            profile(packet).setTitle(value);
            return Result.ok(obj("u_title",value));
        }
    }

    private static final class GetProfile extends ProfileHandler {
        GetProfile(Services services) { super(CmdId.GET_PROFILE,services); }
        @Override public Result handle(GamePacket packet) { return Result.ok(profile(packet).profile()); }
    }
}

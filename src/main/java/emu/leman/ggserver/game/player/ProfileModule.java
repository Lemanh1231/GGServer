package emu.leman.ggserver.game.player;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.game.GameModule;

/** Nested auth feature: deliberately not also installed as a top-level module. */
public final class ProfileModule implements GameModule {
    private final Services services;
    public ProfileModule(Services services) { this.services=services; }
    @Override public String id() { return "player-profile"; }
    @Override public void register() { ProfilePackets.handlers(services).forEach(handler -> handler.register(services.registry)); }
}

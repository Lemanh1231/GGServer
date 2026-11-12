package emu.leman.ggserver.game.player;

import java.util.Objects;

/** Feature managers belong to a player, rather than owning independent cached user data. */
public abstract class PlayerManager {
    private final Player player;
    protected PlayerManager(Player player) { this.player=Objects.requireNonNull(player); }
    public final Player player() { return player; }
}

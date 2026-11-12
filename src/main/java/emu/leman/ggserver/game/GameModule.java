package emu.leman.ggserver.game;

/** A named feature composition root which installs its command handlers. */
public interface GameModule {
    String id();
    void register();
}

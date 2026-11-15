package emu.leman.ggserver;
import java.nio.file.Path;
import emu.leman.ggserver.net.HandlerRegistry;
import emu.leman.ggserver.database.StateStore;
import emu.leman.ggserver.game.GameData;
import emu.leman.ggserver.game.content.EventManager;
import emu.leman.ggserver.config.ServerConfig;
import emu.leman.ggserver.net.SessionManager;
public final class Services implements AutoCloseable {
    public final Path root;
    public final ServerConfig config;
    public final StateStore state;
    public final GameData gameData;
    public final EventManager events;
    public final HandlerRegistry registry;
    public final SessionManager sessions;
    public Services(Path root) { this(ServerConfig.defaults(root)); }
    public Services(ServerConfig config) {
        this.config=config;
        this.root=config.root;
        gameData=new GameData(config);
        state=new StateStore(config);
        events=new EventManager(this.root);
        sessions=new SessionManager(config.sessionTimeoutSeconds,config.sessionCleanupSeconds,config.maxSessions);
        registry=new HandlerRegistry(state::canonicalIdentity);
    }
    @Override public void close() { try { sessions.close(); } finally { state.close(); } }
}

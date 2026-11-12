package emu.leman.ggserver.game.player;

import emu.leman.ggserver.Services;
import java.util.Map;
import java.util.Objects;
import java.util.function.Consumer;
import java.util.function.Function;

/**
 * An account identity with feature managers, never a cached mutable database document.
 * Each operation loads a fresh snapshot under the same account lock as command dispatch.
 */
public final class Player {
    private final Services services;
    private final String identity;
    private final ProfileManager profile;

    public Player(Services services, String identity) {
        this.services=Objects.requireNonNull(services);
        this.identity=identity==null ? "" : identity;
        this.profile=new ProfileManager(this);
    }

    public String identity() { return identity; }
    public ProfileManager profile() { return profile; }

    <T> T read(Function<Map<String,Object>,T> operation) {
        return services.registry.withAccountLock(identity,() -> operation.apply(services.state.getUser(identity)));
    }

    void update(Consumer<Map<String,Object>> operation) {
        services.registry.withAccountLock(identity,() -> {
            Map<String,Object> snapshot=services.state.getUser(identity);
            if(snapshot!=null) {
                operation.accept(snapshot);
                services.state.saveUser(snapshot);
            }
            return null;
        });
    }
}

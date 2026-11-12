package emu.leman.ggserver.game;

import emu.leman.ggserver.game.account.AccountModule;
import emu.leman.ggserver.game.content.ContentModule;
import emu.leman.ggserver.game.economy.EconomyModule;
import emu.leman.ggserver.game.social.SocialModule;
import emu.leman.ggserver.Services;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/** Module lifecycle and actual command ownership inventory for one Services instance. */
public final class GameContext {
    private final Services services;
    private final Map<String,GameModule> modules=new LinkedHashMap<>();
    private final Map<String,Set<String>> commands=new LinkedHashMap<>();

    public GameContext(Services services) {
        this.services=Objects.requireNonNull(services);
        addModule(new AccountModule(services));
        addModule(new EconomyModule(services));
        addModule(new SocialModule(services));
        addModule(new ContentModule(services));
    }

    public Services services() { return services; }

    public synchronized GameContext addModule(GameModule module) {
        Objects.requireNonNull(module);
        String id=Objects.requireNonNull(module.id());
        if(id.isBlank()) throw new IllegalArgumentException("Module id must not be blank");
        if(modules.putIfAbsent(id,module)!=null) throw new IllegalStateException("Duplicate module: "+id);
        return this;
    }

    /** Idempotent per context; registry duplicate checks still reject competing bootstraps. */
    public synchronized GameContext registerModules() {
        for(GameModule module:modules.values()) {
            if(commands.containsKey(module.id())) continue;
            Set<String> before=services.registry.commands();
            module.register();
            Set<String> installed=new LinkedHashSet<>(services.registry.commands());
            installed.removeAll(before);
            commands.put(module.id(),Set.copyOf(installed));
        }
        return this;
    }

    public synchronized Map<String,GameModule> modules() { return Collections.unmodifiableMap(new LinkedHashMap<>(modules)); }
    public synchronized Map<String,Set<String>> commands() { return Collections.unmodifiableMap(new LinkedHashMap<>(commands)); }
}

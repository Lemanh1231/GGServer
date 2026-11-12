package emu.leman.ggserver.migration;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.game.GameContext;
import java.nio.file.Path;
import java.util.TreeSet;
import static emu.leman.ggserver.util.Json.*;

/** Export actual registrations without relying on a source-code regex. Use a disposable --root. */
public final class CommandInventory {
    public static void main(String[] args) {
        if(args.length!=2 || !args[0].equals("--root"))
            throw new IllegalArgumentException("Usage: CommandInventory --root DISPOSABLE_TEST_ROOT");
        // This utility's stdout is a machine-readable JSON contract, not a console log.
        var logger=(ch.qos.logback.classic.Logger)org.slf4j.LoggerFactory.getLogger(emu.leman.ggserver.data.ResourceLoader.class);
        var previous=logger.getLevel();logger.setLevel(ch.qos.logback.classic.Level.WARN);
        try {
            try(Services services=new Services(Path.of(args[1]))) {
                new GameContext(services).registerModules();
                System.out.println(stringify(obj("commands",new TreeSet<>(services.registry.commands()))));
            }
        } finally { logger.setLevel(previous); }
    }
}

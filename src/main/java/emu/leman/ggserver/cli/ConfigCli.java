package emu.leman.ggserver.cli;

import emu.leman.ggserver.config.ServerConfig;
import java.nio.file.Path;

/** Small native configuration reader for lifecycle scripts (no eval or Python dependency). */
public final class ConfigCli {
    private ConfigCli() {}
    public static void main(String[] args) {
        if(args.length!=1) throw new IllegalArgumentException("Usage: ConfigCli CONFIG_FILE");
        ServerConfig config=ServerConfig.load(Path.of(args[0]));
        System.out.println(config.port);
        System.out.println(config.https?"https":"http");
        System.out.println(config.host);
    }
}

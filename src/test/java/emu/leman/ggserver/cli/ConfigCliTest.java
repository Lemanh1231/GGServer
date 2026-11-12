package emu.leman.ggserver.cli;

import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class ConfigCliTest {
    @TempDir Path directory;
    @Test void operationsUseConfiguredRootAndPortUnlessExplicitlyOverridden() {
        Path file=directory.resolve("settings.json");
        write(file,obj("root","runtime","port",9443,"https",true));
        var env=Map.of("GG_CONFIG",file.toString());
        assertEquals(directory.resolve("runtime"),CliSupport.root(env));
        assertEquals("https://127.0.0.1:9443",CliSupport.adminUrl(env));
        assertEquals("https://127.0.0.1:9999",CliSupport.adminUrl(Map.of("GG_CONFIG",file.toString(),"PORT","9999")));
        assertEquals("http://proxy:8080",CliSupport.adminUrl(Map.of("GG_CONFIG",file.toString(),"GG_ADMIN_URL","http://proxy:8080")));
    }
}

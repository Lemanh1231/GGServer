package emu.leman.ggserver.config;

import emu.leman.ggserver.Main;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

class ResourcesLayoutTest {
    @TempDir Path temporary;

    @Test void shippedConfigResolvesAllRuntimeFilesUnderResources() {
        Path root=Path.of("resources").toAbsolutePath().normalize();
        var config=ServerConfig.load(root.resolve("server-config.example.json"),Map.of(),Map.of());
        assertEquals(root,config.root);
        for(String folder:new String[]{"data","cdn","gamedata","schema","static","captures"})
            assertTrue(config.folder(folder).startsWith(root),folder);
        for(String file:new String[]{"schema/schema.json","gamedata/game_data.json","static/eula.html",
                "cdn_files/Android","event_config.json","broadcast_posts.json","post_seq.json"})
            assertTrue(Files.isRegularFile(config.resource(file)),file);
        assertEquals(root.resolve("out"),config.folder("apk"));
        assertEquals(root,Main.runtimeRoot(Path.of(".")));
        assertEquals(root,Main.runtimeRoot(root));
    }

    @Test void explicitLegacyRootsAndConfigSemanticsStillWork() throws Exception {
        assertEquals(temporary,Main.runtimeRoot(temporary));
        Files.writeString(temporary.resolve("server-config.json"),"{\"root\":\".\"}");
        assertEquals(temporary,ServerConfig.load(temporary.resolve("server-config.json")).root);
        Path resources=Files.createDirectory(temporary.resolve("resources"));
        Files.writeString(resources.resolve("server-config.json"),"{\"root\":\".\"}");
        assertEquals(resources,Main.runtimeRoot(temporary));
        assertEquals(temporary,ServerConfig.defaults(temporary).root);
    }
}

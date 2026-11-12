package emu.leman.ggserver.game;

import emu.leman.ggserver.game.account.AccountModule;
import emu.leman.ggserver.game.content.ContentModule;
import emu.leman.ggserver.game.economy.EconomyModule;
import emu.leman.ggserver.game.social.SocialModule;
import emu.leman.ggserver.server.admin.AdminServer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Keep feature code together without regrowing parallel layer-only packages. */
class SourceLayoutTest {
    @Test void baseHasOnlyTheDocumentedFeatureAndResourcePackages() throws Exception {
        Path base=Path.of("src/main/java/emu/leman/ggserver");
        try(var files=Files.walk(base)) {
            Set<String> packages=files.filter(Files::isRegularFile)
                    .filter(path -> path.toString().endsWith(".java"))
                    .map(base::relativize).filter(path -> path.getNameCount()>1)
                    .map(path -> path.getName(0).toString()).collect(Collectors.toSet());
            assertEquals(Set.of("config","database","data","game","net","server","cli","migration","util"),packages);
        }
    }

    @Test void featuresAreRealModulesRatherThanRegistrarWrappers() {
        for(Class<?> feature:List.of(AccountModule.class,EconomyModule.class,SocialModule.class,ContentModule.class)) {
            assertTrue(GameModule.class.isAssignableFrom(feature));
            assertEquals("emu.leman.ggserver.game."+switch(feature.getSimpleName()) {
                case "AccountModule" -> "account";
                case "EconomyModule" -> "economy";
                case "SocialModule" -> "social";
                default -> "content";
            },feature.getPackageName());
        }
    }

    @Test void relocatedAdminTemplatesArePackagedBesideTheController() throws Exception {
        for(String name:List.of("login.html","dashboard.html")) {
            try(var resource=AdminServer.class.getResourceAsStream(name)) {
                assertNotNull(resource,name+" must be available in the built JAR");
                assertTrue(resource.readAllBytes().length>100);
            }
        }
    }
}

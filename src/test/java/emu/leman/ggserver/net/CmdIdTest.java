package emu.leman.ggserver.net;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.game.GameContext;
import emu.leman.ggserver.net.codec.Codec;
import emu.leman.ggserver.server.Dispatch;
import java.lang.reflect.Modifier;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class CmdIdTest {
    @TempDir Path root;

    private Set<String> identifiers() throws Exception {
        Set<String> ids=new HashSet<>();
        for(var field:CmdId.class.getDeclaredFields()) {
            if(field.getType()==String.class && Modifier.isPublic(field.getModifiers()))
                assertTrue(ids.add((String)field.get(null)),"Duplicate command: "+field.getName());
        }
        return ids;
    }

    @Test void coversEverySchemaCommandWithoutInventingExtraIds() throws Exception {
        Codec codec=new Codec(Path.of("resources"));
        Set<String> schemaCommands=new HashSet<>();
        for(var entry:codec.schema.values()) {
            var spec=map(entry);
            Set<String> fields=new HashSet<>();
            for(Object field:list(spec.get("fields"))) fields.add(str(map(field).get("name")));
            String name=str(spec.get("name"));
            if(fields.containsAll(Set.of("call","data"))&&!name.endsWith("Return")) schemaCommands.add(name);
        }
        assertEquals(129,schemaCommands.size());
        assertEquals(schemaCommands,identifiers());
        try(Services services=new Services(root)) {
            new GameContext(services).registerModules();
            assertEquals(61,services.registry.commands().size());
            assertTrue(identifiers().containsAll(services.registry.commands()));
        }
    }

    @Test void specialResponsesAndBootstrapRemainWireCompatible() {
        var dispatch=new Dispatch(new Codec(Path.of("resources")));
        assertEquals("main.initReturn",dispatch.returnDtoFor("main."+CmdId.REQUEST));
        assertEquals("user.userJoinReturn",dispatch.returnDtoFor("user."+CmdId.FACEBOOK_USER_JOIN));
        assertEquals("user.getChThirdStarRewardReturn",dispatch.returnDtoFor("user."+CmdId.SET_CH_THIRD_CHAPTER_REWARD));
        assertEquals(Set.of("main.Request","main.getServerTime","main.getUpdateTime",
                "main.defaultSettingList","main.getGameDataList","store.getVarietyStore"),CmdId.BOOTSTRAP);
    }

    @Test void productionRegistrationsDoNotReintroduceInlineCommandStrings() throws Exception {
        try(var files=Files.walk(Path.of("src/main/java"))) {
            for(Path file:files.filter(p->p.toString().endsWith(".java")).toList()) {
                assertFalse(java.util.regex.Pattern.compile("(?:register|bind|super)\\(\\s*\"")
                        .matcher(Files.readString(file)).find(),file.toString());
            }
        }
    }
}

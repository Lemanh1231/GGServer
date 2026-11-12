package emu.leman.ggserver.config;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.codec.Codec;
import emu.leman.ggserver.server.GameServer;
import java.net.URI;
import java.net.http.*;
import java.nio.file.*;
import java.util.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class ServerConfigTest {
    @TempDir Path temp;
    @Test void relativeFoldersResolveFromConfiguredRoot() {
        Path file=temp.resolve("server-config.json");
        write(file,obj("root","runtime","folders",obj("cdn","../assets/cdn","gamedata","../tables","data","players"),"port",12345));
        ServerConfig config=ServerConfig.load(file,Map.of(),Map.of());
        assertEquals(temp.resolve("runtime"),config.root);
        assertEquals(temp.resolve("assets/cdn"),config.folder("cdn"));
        assertEquals(temp.resolve("tables/game_data.json"),config.resource("gamedata/game_data.json"));
        assertEquals(temp.resolve("runtime/players/database.db"),config.database());
        assertEquals(12345,config.port);
    }
    @Test void validatesTypesPortsAndExplicitMissingFile() {
        Path file=temp.resolve("server-config.json");
        for(Object value:List.of(obj("port",70000),obj("port","8080"),obj("https","false"),obj("folders","bad"),obj("folders",obj("cdn","")),obj("https",true,"http",true,"port",8080))) {
            write(file,value);assertThrows(IllegalArgumentException.class,()->ServerConfig.load(file,Map.of(),Map.of()));
        }
        assertThrows(IllegalStateException.class,()->ServerConfig.load(temp.resolve("missing.json")));
    }
    @Test void supportsOverridesAndEnvironmentSecrets() {
        Path file=temp.resolve("server-config.json");
        write(file,obj("port",8080,"adminPassword","file-secret","publicBase","https://file.example","verbose",true));
        ServerConfig config=ServerConfig.load(file,obj("port",9000),Map.of("GG_ADMIN_PASSWORD","env-secret","GG_VERBOSE","0"));
        assertEquals(9000,config.port);assertEquals("env-secret",config.adminPassword);assertFalse(config.verbose);
        assertEquals("https://file.example",config.publicBase);
    }
    @Test void databaseAndSessionConfigurationAreValidated() {
        Path file=temp.resolve("server-config.json");
        write(file,obj("database",obj("backend","mongo","uri","mongodb://localhost:27017","name","players"),"sessions",obj("timeoutSeconds",30,"cleanupSeconds",5,"maxSessions",20,"required",true)));
        ServerConfig config=ServerConfig.load(file,Map.of(),Map.of("GG_MONGO_URI","mongodb://db:27017"));
        assertEquals("mongo",config.databaseBackend);assertEquals("mongodb://db:27017",config.mongoUri);
        assertEquals("players",config.mongoDatabase);assertEquals(30,config.sessionTimeoutSeconds);
        assertEquals(5,config.sessionCleanupSeconds);assertEquals(20,config.maxSessions);assertTrue(config.sessionRequired);
        assertEquals("sqlite",ServerConfig.defaults(temp).databaseBackend);
        for(Object value:List.of(obj("database",obj("backend","redis")),obj("database","bad"),obj("database",obj("name","bad/name")),obj("sessions",obj("timeoutSeconds",0)),obj("sessions",obj("maxSessions",-1)),obj("sessions",obj("required","true")))) {
            write(file,value);assertThrows(IllegalArgumentException.class,()->ServerConfig.load(file,Map.of(),Map.of()));
        }
    }
    @Test void configuredDirectoriesAreUsedByStorageCodecEconomySocialAndCdn() throws Exception {
        Path file=temp.resolve("server-config.json"),assets=temp.resolve("assets");
        Files.createDirectories(assets);
        for(String name:List.of("schema","gamedata")) {
            Files.createDirectories(assets.resolve(name));
            try(var paths=Files.list(Path.of("resources",name))) {
                for(Path p:paths.filter(Files::isRegularFile).toList()) Files.copy(p,assets.resolve(name).resolve(p.getFileName()));
            }
        }
        Files.createDirectories(assets.resolve("cdn"));Files.writeString(assets.resolve("cdn/Android"),"custom-cdn");
        write(file,obj("root","runtime","port",0,"verbose",false,"folders",obj("schema","../assets/schema","gamedata","../assets/gamedata","cdn","../assets/cdn","data","players","captures","trace")));
        ServerConfig config=ServerConfig.load(file,Map.of(),Map.of());
        try(Services services=new Services(config);GameServer server=new GameServer(services)) {
            assertFalse(services.gameData.table(13).isEmpty());
            assertFalse(new Codec(config).schemaFor("user.userLogin").isEmpty());
            new emu.leman.ggserver.game.economy.EconomyModule(services).register();
            new emu.leman.ggserver.game.social.SocialModule(services).register();
            services.state.createUser("config-test","config-test");
            var sent=new emu.leman.ggserver.game.social.SocialPosts(services).sendPost("config-test","title","memo",List.of(),1,false);
            assertNotNull(sent);assertTrue(Files.isRegularFile(config.database()));
            assertFalse(Files.exists(config.root.resolve("data/database.db")));
            var bound=server.start("127.0.0.1",0,null);
            var response=HttpClient.newHttpClient().send(HttpRequest.newBuilder(URI.create("http://127.0.0.1:"+bound.getAddress().getPort()+"/AssetBundles/Android/Android")).build(),HttpResponse.BodyHandlers.ofString());
            assertEquals(200,response.statusCode());assertEquals("custom-cdn",response.body());
        }
    }
}

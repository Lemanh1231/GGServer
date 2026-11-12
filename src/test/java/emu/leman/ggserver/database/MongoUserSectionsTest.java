package emu.leman.ggserver.database;

import com.mongodb.client.*;
import de.bwaldvogel.mongo.MongoServer;
import de.bwaldvogel.mongo.backend.memory.MemoryBackend;
import java.util.*;
import org.bson.Document;
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

class MongoUserSectionsTest {
    private MongoServer server;
    private MongoClient client;
    private MongoDatabase database;
    @BeforeEach void start() {
        server=new MongoServer(new MemoryBackend());var address=server.bind();
        client=MongoClients.create("mongodb://"+address.getHostString()+":"+address.getPort());
        database=client.getDatabase("sections_test");
    }
    @AfterEach void stop() { client.close();server.shutdownNow(); }

    @Test void historicalReadersRemainConsistentAfterNewPublication() {
        var storage=new MongoUserSections(database);
        var oldData=new Document("user_music",List.of(new Document("i_id",1)))
                .append("areas",new Document("1",new Document("s_Gp1","9007199254740993")))
                .append("unknown_feature",new Document("nested",List.of(1,2,3)))
                .append("empty_list",List.of()).append("empty_map",new Document()).append("nullable",null);
        var oldAccount=new Document("_id","player").append("sections",storage.stage("player",oldData));
        var old=storage.read(oldAccount);
        var newAccount=new Document("_id","player").append("sections",storage.stage("player",new Document("user_music",List.of())));
        assertEquals(List.of(),storage.read(newAccount).get("user_music"));
        assertEquals(old,storage.read(oldAccount));
        assertEquals(oldData.keySet(),old.keySet());
        assertNull(old.get("nullable"));
        storage.discard("player",newAccount.get("sections",Document.class));
        assertEquals(old,storage.read(oldAccount));
    }

    @Test void failedStagingNeverChangesPublishedDataAndCleansItsOwnPartialRows() {
        var storage=new MongoUserSections(database);
        var published=new Document("_id","player").append("sections",storage.stage("player",new Document("user_music",List.of(new Document("i_id",1)))));
        var before=storage.read(published);
        long count=database.getCollection("user_music").countDocuments();
        var invalid=new Document("user_music",List.of(new Document("i_id",999)))
                .append("user_guitar",List.of(new Object()));
        assertThrows(RuntimeException.class,()->storage.stage("player",invalid));
        assertEquals(count,database.getCollection("user_music").countDocuments());
        assertEquals(before,storage.read(published));
    }
}

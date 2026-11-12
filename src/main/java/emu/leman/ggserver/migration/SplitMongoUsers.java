package emu.leman.ggserver.migration;

import com.mongodb.client.*;
import emu.leman.ggserver.config.ServerConfig;
import emu.leman.ggserver.database.MongoUserRepository;
import emu.leman.ggserver.util.Json;
import java.nio.file.*;
import java.nio.file.attribute.PosixFilePermissions;
import java.io.*;
import java.util.*;
import org.bson.Document;
import org.bson.json.*;

/** Explicit stopped-writer migration. Dry run is read-only, apply backs up before publication. */
public final class SplitMongoUsers {
    private SplitMongoUsers() {}
    public static void main(String[] args) throws Exception {
        Map<String,String> options=new LinkedHashMap<>();boolean apply=false,stopped=false;
        for(int i=0;i<args.length;i++) switch(args[i]) {
            case "--apply" -> apply=true;
            case "--dry-run" -> { }
            case "--writers-stopped" -> stopped=true;
            case "--config","--backup" -> { String key=args[i];if(++i>=args.length) throw new IllegalArgumentException("Missing "+key);options.put(key,args[i]); }
            default -> throw new IllegalArgumentException("Usage: SplitMongoUsers --config FILE [--dry-run | --apply --writers-stopped --backup NEW_DIRECTORY]");
        }
        if(!options.containsKey("--config")) throw new IllegalArgumentException("--config is required");
        if(apply && (!stopped || !options.containsKey("--backup"))) throw new IllegalArgumentException("Apply requires --writers-stopped and --backup NEW_DIRECTORY");
        var config=ServerConfig.load(Path.of(options.get("--config")));
        if(!Set.of("mongo","mongodb").contains(config.databaseBackend)) throw new IllegalArgumentException("Config must select MongoDB");
        try(var client=MongoClients.create(config.mongoUri)) {
            var users=client.getDatabase(config.mongoDatabase).getCollection("users");
            var accounts=users.find().into(new ArrayList<>());
            long legacy=accounts.stream().filter(d->!d.containsKey("sections")).count();
            // An empty/wrong target must not look like a successful live migration.
            if(accounts.isEmpty()) throw new IllegalStateException("Target users collection is empty; verify MongoDB target. Nothing changed.");
            if(!apply) {
                System.out.println(Json.stringify(Json.obj("mode","dry-run","accounts",accounts.size(),"legacy",legacy,"alreadySplit",accounts.size()-legacy,"writes",0)));
                return;
            }
            Path backup=Path.of(options.get("--backup")).toAbsolutePath();
            Files.createDirectory(backup,PosixFilePermissions.asFileAttribute(PosixFilePermissions.fromString("rwx------")));
            var settings=JsonWriterSettings.builder().outputMode(JsonMode.EXTENDED).build();
            try(var out=Files.newBufferedWriter(backup.resolve("users.bson.jsonl"),StandardOpenOption.CREATE_NEW)) {
                for(Document account:accounts) { out.write(account.toJson(settings));out.newLine(); }
            }
            // Close the backup before changing any account. No deletes, no collection drops.
            int migrated=0;
            try(var repository=new MongoUserRepository(config)) {
                for(Document account:accounts) {
                    String uuid=account.getString("_id");
                    if(account.containsKey("sections")) continue;
                    var current=users.find(new Document("_id",uuid)).first();
                    if(!account.equals(current)) throw new IllegalStateException("Account changed since backup; stop all writers and retry");
                    String before=Json.stringify(repository.exportUser(uuid));
                    if(repository.splitLegacyUser(uuid)) migrated++;
                    if(!Json.parse(before).equals(Json.parse(Json.stringify(repository.exportUser(uuid)))))
                        throw new IllegalStateException("Post-migration verification failed; backup retained");
                }
            }
            var report=Json.obj("mode","apply","accounts",accounts.size(),"migrated",migrated,"verified",true,"backup",backup.toString());
            Json.write(backup.resolve("report.json"),report);System.out.println(Json.stringify(report));
        }
    }
}

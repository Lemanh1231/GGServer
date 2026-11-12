package emu.leman.ggserver.migration;

import java.nio.file.*;
import java.sql.*;
import java.time.Instant;
import java.util.*;

/** Explicit, consistent SQLite snapshot: never starts or alters the Python server. */
public final class ImportPythonData {
    private ImportPythonData() {}

    public static void main(String[] args) throws Exception {
        Path source = Path.of("../emulator");
        Path target = emu.leman.ggserver.Main.defaultRoot();
        boolean replace = false;
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--source" -> source = Path.of(args[++i]);
                case "--root" -> target = Path.of(args[++i]);
                case "--replace" -> replace = true;
                case "--help", "-h" -> {
                    System.out.println("ImportPythonData --source ../emulator --root resources [--replace]\n"
                            + "Copies data/database.db using SQLite backup; --replace first backs up existing Java data.\n"
                            + "Stop both servers during the final cutover to avoid losing newer player writes.");
                    return;
                }
                default -> throw new IllegalArgumentException("Unknown option: " + args[i]);
            }
        }
        Path imported = snapshot(source, target, replace);
        System.out.println("Imported SQLite snapshot to " + imported);
    }

    public static Path snapshot(Path sourceRoot, Path targetRoot, boolean replace) throws Exception {
        Path source = sourceRoot.toAbsolutePath().normalize().resolve("data/database.db");
        Path target = targetRoot.toAbsolutePath().normalize().resolve("data/database.db");
        if (!Files.isRegularFile(source)) throw new IllegalArgumentException("Missing Python database: " + source);
        if (source.equals(target) || (Files.exists(target) && Files.isSameFile(source, target)))
            throw new IllegalArgumentException("Source and target database must differ");
        if (Files.exists(target) && !replace)
            throw new FileAlreadyExistsException(target + ": use a fresh destination or --replace (creates backup)");
        Files.createDirectories(target.getParent());
        Path temp = target.resolveSibling("import-" + UUID.randomUUID() + ".db");
        try {
            // VACUUM INTO includes committed WAL pages; copying database.db alone does not.
            try (Connection connection = DriverManager.getConnection("jdbc:sqlite:file:" + source + "?mode=ro");
                 Statement statement = connection.createStatement()) {
                statement.execute("PRAGMA busy_timeout=10000");
                statement.execute("VACUUM INTO '" + temp.toString().replace("'", "''") + "'");
            }
            verify(temp);
            if (Files.exists(target)) {
                Path backup = target.resolveSibling("database.backup-" + Instant.now().toEpochMilli() + "-" + UUID.randomUUID() + ".db");
                // Snapshot the old target as well, retaining committed WAL data.
                try (Connection connection = DriverManager.getConnection("jdbc:sqlite:" + target);
                     Statement statement = connection.createStatement()) {
                    statement.execute("PRAGMA busy_timeout=10000");
                    statement.execute("VACUUM INTO '" + backup.toString().replace("'", "''") + "'");
                    try (ResultSet checkpoint = statement.executeQuery("PRAGMA wal_checkpoint(TRUNCATE)")) {
                        if (checkpoint.next() && checkpoint.getInt(1) != 0)
                            throw new IllegalStateException("Target database is busy: stop Java server before importing");
                    }
                }
                System.out.println("Previous Java database backed up to " + backup);
            }
            try {
                Files.move(temp, target, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            } catch (AtomicMoveNotSupportedException exception) {
                Files.move(temp, target, StandardCopyOption.REPLACE_EXISTING);
            }
            return target;
        } finally {
            Files.deleteIfExists(temp);
        }
    }

    private static void verify(Path database) throws SQLException {
        try (Connection connection = DriverManager.getConnection("jdbc:sqlite:file:" + database + "?mode=ro");
             Statement statement = connection.createStatement()) {
            try (ResultSet result = statement.executeQuery("PRAGMA integrity_check")) {
                if (!result.next() || !"ok".equalsIgnoreCase(result.getString(1)))
                    throw new SQLException("SQLite integrity check failed");
            }
            try (ResultSet ignored = statement.executeQuery("SELECT uuid, user_contents_json FROM user_data LIMIT 1")) {
                // Validate expected schema even for an empty source database.
            }
        }
    }
}

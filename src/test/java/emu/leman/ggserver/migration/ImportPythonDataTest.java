package emu.leman.ggserver.migration;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.sql.*;
import static org.junit.jupiter.api.Assertions.*;

class ImportPythonDataTest {
    @TempDir Path temp;

    @Test void importsCommittedWalPagesAndRefusesSilentOverwrite() throws Exception {
        Path source = temp.resolve("python"), target = temp.resolve("java");
        Files.createDirectories(source.resolve("data"));
        try (Connection connection = DriverManager.getConnection("jdbc:sqlite:" + source.resolve("data/database.db"));
             Statement statement = connection.createStatement()) {
            statement.execute("PRAGMA journal_mode=WAL");
            statement.execute("CREATE TABLE user_data(uuid TEXT PRIMARY KEY,user_contents_json TEXT)");
            statement.execute("INSERT INTO user_data VALUES ('original','{}')");
            Path result = ImportPythonData.snapshot(source, target, false);
            try (Connection copy = DriverManager.getConnection("jdbc:sqlite:" + result);
                 ResultSet rows = copy.createStatement().executeQuery("SELECT uuid FROM user_data")) {
                assertTrue(rows.next());
                assertEquals("original", rows.getString(1));
            }
            assertThrows(FileAlreadyExistsException.class, () -> ImportPythonData.snapshot(source, target, false));
            assertThrows(IllegalArgumentException.class, () -> ImportPythonData.snapshot(source, source, true));
            ImportPythonData.snapshot(source,target,true);
            try (var files = Files.list(target.resolve("data"))) {
                assertTrue(files.anyMatch(p -> p.getFileName().toString().startsWith("database.backup-")));
            }
        }
    }
}

package emu.leman.ggserver.util;

import ch.qos.logback.classic.*;
import ch.qos.logback.core.rolling.RollingFileAppender;
import ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy;
import emu.leman.ggserver.config.ServerConfig;
import org.junit.jupiter.api.*;
import org.junit.jupiter.api.io.TempDir;
import org.slf4j.LoggerFactory;
import java.nio.file.*;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;

class LoggingTest {
    @TempDir Path root;

    @Test void compactFileLogsRotateAndDoNotDuplicateOnReconfiguration() throws Exception {
        Logger logger=((LoggerContext)LoggerFactory.getILoggerFactory()).getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME);
        Level old=logger.getLevel();
        try {
            ServerConfig config=ServerConfig.defaults(root,Json.obj("logging",Json.obj("level","DEBUG")));
            Logging.configure(config);Logging.configure(config);
            var appender=(RollingFileAppender<?>)logger.getAppender("FILE");
            assertTrue(appender.isStarted());
            assertInstanceOf(SizeAndTimeBasedRollingPolicy.class,appender.getRollingPolicy());
            assertEquals(14,((SizeAndTimeBasedRollingPolicy<?>)appender.getRollingPolicy()).getMaxHistory());
            LoggerFactory.getLogger(LoggingTest.class).info("SEND: userLoad | 100 B | 2 ms");
            Logging.configure(ServerConfig.defaults(root,Json.obj("logging",Json.obj("file",false))));
            assertNull(logger.getAppender("FILE"));
            String text=Files.readString(root.resolve("logs/latest.log"));
            assertEquals(1,text.lines().filter(line->line.contains("SEND: userLoad")).count());
            assertTrue(text.matches("(?s)\\[\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2}] \\[INFO] SEND: userLoad.*"));
        } finally {
            var appender=logger.getAppender("FILE");
            if(appender!=null) { logger.detachAppender(appender);appender.stop(); }
            logger.setLevel(old);
        }
    }

    @Test void settingsValidateLevelsAndResolveLogFolderFromRoot() throws Exception {
        Path file=root.resolve("config.json");
        Json.write(file,Json.obj("root","runtime","logging",Json.obj("level","debug"),"folders",Json.obj("logs","trace")));
        var config=ServerConfig.load(file,Map.of(),Map.of("GG_LOG_LEVEL","WARN"));
        assertEquals("WARN",config.logLevel);
        assertEquals(root.resolve("runtime/trace"),config.folder("logs"));
        Json.write(file,Json.obj("logging",Json.obj("level","INVALID")));
        assertThrows(IllegalArgumentException.class,()->ServerConfig.load(file,Map.of(),Map.of()));
    }

    @Test void untrustedLogFieldsStayOnOneBoundedLine() {
        assertEquals("/rpc_FAKE_info_",Logging.safe("/rpc\nFAKE\rinfo\u001b"));
        assertEquals(160,Logging.safe("x".repeat(200)).length());
    }
}

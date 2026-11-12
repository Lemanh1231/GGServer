package emu.leman.ggserver.util;

import ch.qos.logback.classic.*;
import ch.qos.logback.classic.encoder.PatternLayoutEncoder;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.rolling.*;
import ch.qos.logback.core.util.FileSize;
import emu.leman.ggserver.config.ServerConfig;
import org.slf4j.LoggerFactory;

/** Nebula-style console with bounded, compressed file history under the runtime root. */
public final class Logging {
    private Logging() {}
    public static void configure(ServerConfig config) {
        LoggerContext context=(LoggerContext)LoggerFactory.getILoggerFactory();
        Logger root=context.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME);
        root.setLevel(Level.valueOf(config.logLevel));
        var previous=root.getAppender("FILE");
        if(previous!=null) { root.detachAppender(previous);previous.stop(); }
        if(!config.logFile) return;
        var encoder=new PatternLayoutEncoder();
        encoder.setContext(context);encoder.setPattern("[%d{yyyy-MM-dd HH:mm:ss}] [%level] %msg%n");encoder.start();
        var file=new RollingFileAppender<ILoggingEvent>();
        file.setContext(context);file.setName("FILE");file.setFile(config.folder("logs").resolve("latest.log").toString());file.setEncoder(encoder);
        var policy=new SizeAndTimeBasedRollingPolicy<ILoggingEvent>();
        policy.setContext(context);policy.setParent(file);
        policy.setFileNamePattern(config.folder("logs").resolve("server.%d{yyyy-MM-dd}.%i.log.gz").toString());
        policy.setMaxFileSize(FileSize.valueOf("10MB"));policy.setMaxHistory(14);policy.setTotalSizeCap(FileSize.valueOf("256MB"));
        policy.start();file.setRollingPolicy(policy);file.start();
        if(!file.isStarted()) throw new IllegalStateException("Cannot open log file in "+config.folder("logs"));
        root.addAppender(file);
    }
    /** Prevent untrusted paths/forwarded headers from injecting lines or terminal escapes. */
    public static String safe(String value) {
        if(value==null) return "-";
        String clean=value.replaceAll("[\\p{Cntrl}\\p{Zl}\\p{Zp}]","_");
        return clean.substring(0,Math.min(160,clean.length()));
    }
}

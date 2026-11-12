package emu.leman.ggserver.cli;

import java.io.PrintStream;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.TimeUnit;

final class CliSupport {
    static final String GAME_ACTIVITY = "com.neowiz.game.guitargirl/com.google.firebase.MessagingUnityPlayerActivity";
    private CliSupport() {}

    static Path root(Map<String,String> env) {
        Path root=runtimeRoot(env);
        Path config=Path.of(env.getOrDefault("GG_CONFIG",root.resolve("server-config.json").toString()));
        return java.nio.file.Files.isRegularFile(config)?emu.leman.ggserver.config.ServerConfig.load(config,Map.of(),env).root:root;
    }

    static String adminUrl(Map<String,String> env) {
        if(env.containsKey("GG_ADMIN_URL")) return env.get("GG_ADMIN_URL");
        Path root=runtimeRoot(env);
        Path file=Path.of(env.getOrDefault("GG_CONFIG",root.resolve("server-config.json").toString()));
        if(java.nio.file.Files.isRegularFile(file)) {
            var config=emu.leman.ggserver.config.ServerConfig.load(file,Map.of(),env);
            return (config.https?"https":"http")+"://127.0.0.1:"+env.getOrDefault("PORT",Integer.toString(config.port));
        }
        return "http://127.0.0.1:"+env.getOrDefault("PORT","8080");
    }

    static void checkRoot(Path root) throws java.io.IOException {
        Path real = root.toRealPath();
        // Never accidentally operate on the original Python emulator's data.
        if (java.nio.file.Files.exists(real.resolve("server/state.py")))
            throw new IllegalArgumentException("Refusing to use the Python emulator directory as GG_ROOT: " + real);
    }

    private static Path runtimeRoot(Map<String,String> env) {
        return env.containsKey("GG_ROOT") ? emu.leman.ggserver.Main.runtimeRoot(Path.of(env.get("GG_ROOT")))
                : emu.leman.ggserver.Main.defaultRoot();
    }

    static int error(PrintStream err, Exception e) {
        err.println("ERROR: " + e.getMessage());
        return 1;
    }

    static void softResume(Map<String,String> env, PrintStream out) {
        if ("1".equals(env.get("GG_NO_ADB"))) return;
        try {
            Process devices = new ProcessBuilder("adb", "devices").redirectError(ProcessBuilder.Redirect.DISCARD).start();
            if (!devices.waitFor(2, TimeUnit.SECONDS)) { devices.destroyForcibly(); return; }
            String text = new String(devices.getInputStream().readAllBytes(), java.nio.charset.StandardCharsets.UTF_8);
            if (!text.contains("\tdevice")) return;
            Process resume = new ProcessBuilder("adb", "shell", "am", "start", "-n", GAME_ACTIVITY)
                .redirectOutput(ProcessBuilder.Redirect.DISCARD).redirectError(ProcessBuilder.Redirect.DISCARD).start();
            if (!resume.waitFor(3, TimeUnit.SECONDS)) { resume.destroyForcibly(); return; }
            if (resume.exitValue() == 0) out.println("ADB soft-sync requested (game activity resumed without restarting).");
        } catch (Exception ignored) { /* ADB is optional; mail delivery has already succeeded. */ }
    }

    static double quantity(String value, boolean integer) {
        try {
            double number = integer ? Long.parseLong(value) : Double.parseDouble(value);
            if (!Double.isFinite(number) || number < 0) throw new NumberFormatException();
            return number;
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("Invalid non-negative " + (integer ? "integer" : "number") + ": " + value);
        }
    }
}

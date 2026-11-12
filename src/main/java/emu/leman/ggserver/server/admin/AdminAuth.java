package emu.leman.ggserver.server.admin;

import com.sun.net.httpserver.Headers;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.security.*;
import java.time.Instant;
import java.util.HexFormat;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/** Python-compatible administrator tokens. No game-account credentials are accepted here. */
public final class AdminAuth {
    private final Path secretFile;
    private final String password;
    private byte[] secret;
    public AdminAuth(Path root) {
        this(root, System.getenv().getOrDefault("GG_ADMIN_PASSWORD", "admin123"), System.getenv("GG_SECRET_KEY"));
    }
    public AdminAuth(emu.leman.ggserver.config.ServerConfig config) {
        this.secretFile=config.folder("data").resolve("admin_secret.key");
        this.password=config.adminPassword.isEmpty()?"admin123":config.adminPassword;
        if(!config.secretKey.isEmpty()) this.secret=config.secretKey.getBytes(StandardCharsets.UTF_8);
    }
    AdminAuth(Path root, String password, String secret) {
        this.secretFile = root.resolve("data/admin_secret.key");
        this.password = password;
        if (secret != null && !secret.isEmpty()) this.secret = secret.getBytes(StandardCharsets.UTF_8);
    }
    public boolean checkPassword(String supplied) {
        return MessageDigest.isEqual(password.getBytes(StandardCharsets.UTF_8), supplied.getBytes(StandardCharsets.UTF_8));
    }
    private synchronized byte[] secret() throws IOException {
        if (secret != null) return secret;
        Files.createDirectories(secretFile.getParent());
        if (Files.isRegularFile(secretFile)) {
            byte[] stored = Files.readAllBytes(secretFile);
            // Python's bytes.strip(), not Unicode/String.strip(), on the binary key.
            byte[] trimmed = trim(stored);
            if (trimmed.length > 0) return secret = trimmed;
        }
        byte[] generated = new byte[32];
        SecureRandom random = new SecureRandom();
        do { random.nextBytes(generated); } while (whitespace(generated[0]) || whitespace(generated[generated.length - 1]));
        try { Files.write(secretFile, generated, StandardOpenOption.CREATE_NEW); }
        catch (FileAlreadyExistsException e) {
            byte[] stored = Files.readAllBytes(secretFile);
            byte[] trimmed = trim(stored);
            if (trimmed.length > 0) return secret = trimmed;
            Files.write(secretFile, generated);
        }
        return secret = generated;
    }
    private static boolean whitespace(byte b) { return b == 32 || b >= 9 && b <= 13; }
    private static byte[] trim(byte[] stored) {
        int a = 0, b = stored.length;
        while (a < b && whitespace(stored[a])) a++;
        while (b > a && whitespace(stored[b - 1])) b--;
        return java.util.Arrays.copyOfRange(stored, a, b);
    }
    private String signature(long expires) throws IOException {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret(), "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(("admin:" + expires).getBytes(StandardCharsets.UTF_8)));
        } catch (GeneralSecurityException e) { throw new IOException("Cannot sign admin token", e); }
    }
    public String createToken(long ttlSeconds) throws IOException {
        long expires = Instant.now().getEpochSecond() + ttlSeconds;
        return expires + "." + signature(expires);
    }
    public boolean verifyToken(String token) {
        if (token == null) return false;
        token = token.strip();
        if (checkPassword(token)) return true; // Existing API clients send the password as Bearer.
        int dot = token.indexOf('.');
        if (dot < 1) return false;
        try {
            long expires = Long.parseLong(token.substring(0, dot));
            return Instant.now().getEpochSecond() < expires && MessageDigest.isEqual(
                    signature(expires).getBytes(StandardCharsets.US_ASCII),
                    token.substring(dot + 1).getBytes(StandardCharsets.US_ASCII));
        } catch (IOException | NumberFormatException e) { return false; }
    }
    public boolean authenticated(Headers headers) {
        String bearer = headers.getFirst("Authorization");
        if (bearer != null && bearer.startsWith("Bearer ") && verifyToken(bearer.substring(7))) return true;
        for (String cookies : headers.getOrDefault("Cookie", java.util.List.of())) {
            for (String cookie : cookies.split(";")) {
                String item = cookie.strip();
                if (item.startsWith("gg_admin_token=") && verifyToken(item.substring(15))) return true;
            }
        }
        return false;
    }
}

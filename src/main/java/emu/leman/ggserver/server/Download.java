package emu.leman.ggserver.server;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;

/** React download page bundled at build time; APK routes remain server-owned. */
public final class Download {
    public static final String APK_FILENAME="Guitar_Girl_v8.0.0_NoGooglePlay.apk";
    private Download() {}
    public static String getDownloadHtml() {
        try(var input=Download.class.getResourceAsStream("download.html")) {
            if(input==null)throw new IllegalStateException("Missing download UI; run npm ci && npm run build in web-admin");
            return new String(input.readAllBytes(),StandardCharsets.UTF_8);
        } catch(IOException e) {throw new UncheckedIOException(e);}
    }
}

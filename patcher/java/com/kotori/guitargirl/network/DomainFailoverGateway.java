package com.kotori.guitargirl.network;

import java.io.BufferedInputStream;
import java.io.ByteArrayOutputStream;
import java.io.EOFException;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * In-Process Local Loopback HTTP->HTTPS Multi-Domain Active-Passive Failover Gateway.
 *
 * Behavior:
 * - Binds strictly to 127.0.0.1:28765 inside the APK process.
 * - Sticky Primary (Active-Passive): Uses ONLY 1 active domain as long as it responds cleanly.
 *   The other 3 domains receive ZERO connections and ZERO DNS queries during normal operation.
 * - Automatic Failover: If the current domain fails (DNS block, TCP timeout, TLS error, HTTP 5xx/408/429),
 *   transparently switches to the next domain, replays the exact request, and persists the new active domain.
 */
public final class DomainFailoverGateway {

    public static final int DEFAULT_PORT = 28765;

    public static final String[] DEFAULT_DOMAINS = new String[] {
        "https://kotori.click",
        "https://kotorin.click",
        "https://kotorin.dev",
        "https://kotorin.me"
    };

    private static final int CONNECT_TIMEOUT_MS = 3500;
    private static final int READ_TIMEOUT_RPC_MS = 8000;
    private static final int READ_TIMEOUT_CDN_MS = 30000;
    private static final int MAX_BUFFER_RESPONSE_BYTES = 2 * 1024 * 1024; // 2 MB

    private static final Set<String> HOP_BY_HOP_REQ = new HashSet<String>(Arrays.asList(
        "host", "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
        "te", "trailer", "transfer-encoding", "upgrade", "expect", "content-length"
    ));

    private static final Set<String> HOP_BY_HOP_RESP = new HashSet<String>(Arrays.asList(
        "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
        "te", "trailer", "transfer-encoding", "upgrade", "content-length"
    ));

    public interface StateStore {
        int loadActiveIndex();
        void saveActiveIndex(int index);
        void logInfo(String msg);
        void logWarn(String msg);
    }

    private static final Object START_LOCK = new Object();
    private static volatile DomainFailoverGateway sInstance;

    private final int port;
    private final String[] domains;
    private final StateStore store;
    private final AtomicInteger activeIndex;
    private final AtomicInteger totalFailovers = new AtomicInteger(0);
    private ServerSocket serverSocket;
    private ExecutorService workerPool;
    private volatile boolean running;

    public DomainFailoverGateway(int port, String[] domains, StateStore store) {
        this.port = port;
        this.domains = (domains != null && domains.length > 0) ? domains.clone() : DEFAULT_DOMAINS.clone();
        this.store = store;
        int initial = 0;
        if (store != null) {
            try {
                initial = store.loadActiveIndex();
            } catch (Throwable ignored) {
            }
        }
        if (initial < 0 || initial >= this.domains.length) {
            initial = 0;
        }
        this.activeIndex = new AtomicInteger(initial);
    }

    public static DomainFailoverGateway ensureStarted(StateStore store) {
        if (sInstance != null && sInstance.running) {
            return sInstance;
        }
        synchronized (START_LOCK) {
            if (sInstance != null && sInstance.running) {
                return sInstance;
            }
            DomainFailoverGateway gw = new DomainFailoverGateway(DEFAULT_PORT, DEFAULT_DOMAINS, store);
            try {
                gw.start();
                sInstance = gw;
            } catch (IOException e) {
                if (store != null) {
                    store.logWarn("Failed to bind loopback failover gateway on 127.0.0.1:" + DEFAULT_PORT + ": " + e);
                }
            }
            return sInstance;
        }
    }

    public void start() throws IOException {
        if (running) {
            return;
        }
        ServerSocket ss = new ServerSocket();
        ss.setReuseAddress(true);
        ss.bind(new InetSocketAddress("127.0.0.1", port), 128);
        this.serverSocket = ss;
        this.running = true;

        this.workerPool = Executors.newCachedThreadPool(new ThreadFactory() {
            private final AtomicInteger seq = new AtomicInteger(1);
            @Override
            public Thread newThread(Runnable r) {
                Thread t = new Thread(r, "GG-Failover-Worker-" + seq.getAndIncrement());
                t.setDaemon(true);
                return t;
            }
        });

        Thread acceptor = new Thread(new Runnable() {
            @Override
            public void run() {
                acceptLoop();
            }
        }, "GG-Failover-Acceptor");
        acceptor.setDaemon(true);
        acceptor.start();

        if (store != null) {
            store.logInfo("Started on http://127.0.0.1:" + port
                + " | Active domain [" + activeIndex.get() + "]: " + domains[activeIndex.get()]);
        }
    }

    public void stop() {
        running = false;
        if (serverSocket != null) {
            try {
                serverSocket.close();
            } catch (IOException ignored) {
            }
        }
        if (workerPool != null) {
            workerPool.shutdownNow();
        }
    }

    public int getActiveIndex() {
        return activeIndex.get();
    }

    public String getActiveDomain() {
        return domains[activeIndex.get()];
    }

    public int getTotalFailovers() {
        return totalFailovers.get();
    }

    private void acceptLoop() {
        while (running) {
            try {
                final Socket client = serverSocket.accept();
                client.setTcpNoDelay(true);
                client.setSoTimeout(30000);
                workerPool.execute(new Runnable() {
                    @Override
                    public void run() {
                        handleClient(client);
                    }
                });
            } catch (IOException e) {
                if (running && store != null) {
                    store.logWarn("Acceptor error: " + e);
                }
            }
        }
    }

    private void handleClient(Socket client) {
        try {
            InputStream rawIn = new BufferedInputStream(client.getInputStream(), 8192);
            OutputStream out = client.getOutputStream();

            String requestLine = readAsciiLine(rawIn);
            if (requestLine == null || requestLine.isEmpty()) {
                return;
            }
            String[] parts = requestLine.split(" ");
            if (parts.length < 2) {
                writeSimpleError(out, 400, "Bad Request");
                return;
            }
            String method = parts[0].trim().toUpperCase(Locale.US);
            String rawTarget = parts[1].trim();
            String pathAndQuery = normalizeTarget(rawTarget);

            Map<String, List<String>> reqHeaders = new LinkedHashMap<String, List<String>>();
            int contentLength = -1;
            boolean isChunked = false;
            boolean expectContinue = false;

            while (true) {
                String line = readAsciiLine(rawIn);
                if (line == null || line.isEmpty()) {
                    break;
                }
                int colon = line.indexOf(':');
                if (colon <= 0) {
                    continue;
                }
                String hName = line.substring(0, colon).trim();
                String hVal = line.substring(colon + 1).trim();
                String lower = hName.toLowerCase(Locale.US);

                if ("content-length".equals(lower)) {
                    try {
                        contentLength = Integer.parseInt(hVal);
                    } catch (NumberFormatException ignored) {
                    }
                } else if ("transfer-encoding".equals(lower) && hVal.toLowerCase(Locale.US).contains("chunked")) {
                    isChunked = true;
                } else if ("expect".equals(lower) && hVal.toLowerCase(Locale.US).contains("100-continue")) {
                    expectContinue = true;
                }

                if (!HOP_BY_HOP_REQ.contains(lower)) {
                    List<String> vals = reqHeaders.get(hName);
                    if (vals == null) {
                        vals = new ArrayList<String>(1);
                        reqHeaders.put(hName, vals);
                    }
                    vals.add(hVal);
                }
            }

            if (expectContinue) {
                out.write("HTTP/1.1 100 Continue\r\n\r\n".getBytes(StandardCharsets.US_ASCII));
                out.flush();
            }

            byte[] reqBody;
            if (isChunked) {
                reqBody = readChunkedBody(rawIn);
            } else if (contentLength > 0) {
                reqBody = readExactBytes(rawIn, contentLength);
            } else {
                reqBody = new byte[0];
            }

            forwardWithFailover(method, pathAndQuery, reqHeaders, reqBody, out);
        } catch (Throwable t) {
            if (store != null) {
                store.logWarn("Local proxy request error: " + t);
            }
        } finally {
            try {
                client.close();
            } catch (IOException ignored) {
            }
        }
    }

    private void forwardWithFailover(
            String method,
            String pathAndQuery,
            Map<String, List<String>> reqHeaders,
            byte[] reqBody,
            OutputStream clientOut) throws IOException {

        final int startIdx = activeIndex.get();
        final int n = domains.length;
        final boolean isCdnAsset = pathAndQuery.startsWith("/AssetBundles/") || pathAndQuery.endsWith(".apk");
        final int readTimeout = isCdnAsset ? READ_TIMEOUT_CDN_MS : READ_TIMEOUT_RPC_MS;
        final String localProxyUrl = "http://127.0.0.1:" + port;

        Throwable lastError = null;
        int lastFailStatus = 502;

        for (int attempt = 0; attempt < n; attempt++) {
            final int idx = (startIdx + attempt) % n;
            final String baseDomain = domains[idx];
            final String fullUrl = baseDomain + pathAndQuery;

            HttpURLConnection conn = null;
            try {
                conn = (HttpURLConnection) new URL(fullUrl).openConnection();
                conn.setInstanceFollowRedirects(false);
                conn.setConnectTimeout(CONNECT_TIMEOUT_MS);
                conn.setReadTimeout(readTimeout);
                conn.setUseCaches(false);
                conn.setRequestMethod(method);

                for (Map.Entry<String, List<String>> entry : reqHeaders.entrySet()) {
                    String k = entry.getKey();
                    for (String v : entry.getValue()) {
                        conn.addRequestProperty(k, v);
                    }
                }
                conn.setRequestProperty("X-GG-Local-Proxy", localProxyUrl);
                conn.setRequestProperty("X-GG-Active-Domain", baseDomain);
                conn.setRequestProperty("Accept-Encoding", "identity");

                if (reqBody.length > 0 || "POST".equals(method) || "PUT".equals(method)) {
                    conn.setDoOutput(true);
                    conn.setFixedLengthStreamingMode(reqBody.length);
                    OutputStream upOut = conn.getOutputStream();
                    if (reqBody.length > 0) {
                        upOut.write(reqBody);
                    }
                    upOut.flush();
                    upOut.close();
                }

                int status = conn.getResponseCode();
                if (shouldFailoverOnStatus(status)) {
                    lastFailStatus = status;
                    consumeQuietly(conn);
                    if (store != null) {
                        store.logWarn("Domain [" + idx + "] " + baseDomain + " returned HTTP " + status
                            + " -> failing over to next domain");
                    }
                    continue;
                }

                InputStream upIn = null;
                try {
                    upIn = (status >= 400) ? conn.getErrorStream() : conn.getInputStream();
                } catch (IOException ioe) {
                    upIn = conn.getErrorStream();
                }

                long upLen = -1L;
                String clHdr = conn.getHeaderField("Content-Length");
                if (clHdr != null) {
                    try {
                        upLen = Long.parseLong(clHdr.trim());
                    } catch (NumberFormatException ignored) {
                    }
                }
                boolean streamDirect = isCdnAsset;

                byte[] bufferedResp = null;
                if (!"HEAD".equals(method) && !streamDirect) {
                    // Buffer full RPC/API response before committing to client so mid-transfer drops also failover cleanly
                    bufferedResp = readBoundedStream(upIn, 16 * 1024 * 1024);
                }

                // Upstream domain succeeded! Lock onto this domain if we failed over.
                if (attempt > 0) {
                    activeIndex.set(idx);
                    totalFailovers.incrementAndGet();
                    if (store != null) {
                        try {
                            store.saveActiveIndex(idx);
                        } catch (Throwable ignored) {
                        }
                        store.logInfo("Failover succeeded -> locked onto domain [" + idx + "]: " + baseDomain);
                    }
                }

                String statusMsg = conn.getResponseMessage();
                if (statusMsg == null || statusMsg.isEmpty()) {
                    statusMsg = "OK";
                }

                StringBuilder respHdr = new StringBuilder(256);
                respHdr.append("HTTP/1.1 ").append(status).append(' ').append(statusMsg).append("\r\n");

                for (Map.Entry<String, List<String>> e : conn.getHeaderFields().entrySet()) {
                    String hk = e.getKey();
                    if (hk == null) {
                        continue;
                    }
                    if (HOP_BY_HOP_RESP.contains(hk.toLowerCase(Locale.US))) {
                        continue;
                    }
                    for (String hv : e.getValue()) {
                        if (hv != null) {
                            respHdr.append(hk).append(": ").append(hv).append("\r\n");
                        }
                    }
                }

                if ("HEAD".equals(method)) {
                    if (upLen >= 0) {
                        respHdr.append("Content-Length: ").append(upLen).append("\r\n");
                    }
                    respHdr.append("Connection: close\r\n\r\n");
                    clientOut.write(respHdr.toString().getBytes(StandardCharsets.US_ASCII));
                    clientOut.flush();
                    return;
                }

                if (!streamDirect && bufferedResp != null) {
                    respHdr.append("Content-Length: ").append(bufferedResp.length).append("\r\n");
                    respHdr.append("Connection: close\r\n\r\n");
                    clientOut.write(respHdr.toString().getBytes(StandardCharsets.US_ASCII));
                    if (bufferedResp.length > 0) {
                        clientOut.write(bufferedResp);
                    }
                    clientOut.flush();
                    return;
                }

                // Large CDN stream mode
                if (upLen >= 0) {
                    respHdr.append("Content-Length: ").append(upLen).append("\r\n");
                }
                respHdr.append("Connection: close\r\n\r\n");
                clientOut.write(respHdr.toString().getBytes(StandardCharsets.US_ASCII));
                if (upIn != null) {
                    byte[] buf = new byte[32768];
                    int r;
                    while ((r = upIn.read(buf)) != -1) {
                        clientOut.write(buf, 0, r);
                    }
                }
                clientOut.flush();
                return;

            } catch (IOException ioe) {
                lastError = ioe;
                if (store != null) {
                    store.logWarn("Domain [" + idx + "] " + baseDomain + " failed ("
                        + ioe.getClass().getSimpleName() + ": " + ioe.getMessage() + ") -> trying next domain");
                }
                if (conn != null) {
                    conn.disconnect();
                }
            }
        }

        // All 4 domains failed
        String errText = "All 4 domains unreachable"
            + (lastError != null ? (": " + lastError.getMessage()) : (" (HTTP " + lastFailStatus + ")"));
        writeSimpleError(clientOut, lastFailStatus, errText);
    }

    private static boolean shouldFailoverOnStatus(int status) {
        // Trigger failover on server/gateway/Cloudflare origin errors, request timeout, or rate-limit
        return status >= 500 || status == 408 || status == 429;
    }

    private static String normalizeTarget(String rawTarget) {
        if (rawTarget.startsWith("http://") || rawTarget.startsWith("https://")) {
            int schemeEnd = rawTarget.indexOf("://");
            int pathSlash = rawTarget.indexOf('/', schemeEnd + 3);
            return (pathSlash >= 0) ? rawTarget.substring(pathSlash) : "/";
        }
        return rawTarget.startsWith("/") ? rawTarget : ("/" + rawTarget);
    }

    private static String readAsciiLine(InputStream in) throws IOException {
        ByteArrayOutputStream baos = new ByteArrayOutputStream(128);
        int b;
        boolean gotAny = false;
        while ((b = in.read()) != -1) {
            gotAny = true;
            if (b == '\n') {
                break;
            }
            if (b != '\r') {
                baos.write(b);
            }
            if (baos.size() > 16384) {
                throw new IOException("Header line too long");
            }
        }
        if (!gotAny && baos.size() == 0) {
            return null;
        }
        return new String(baos.toByteArray(), StandardCharsets.ISO_8859_1);
    }

    private static byte[] readExactBytes(InputStream in, int len) throws IOException {
        byte[] data = new byte[len];
        int off = 0;
        while (off < len) {
            int r = in.read(data, off, len - off);
            if (r == -1) {
                throw new EOFException("Premature EOF reading request body");
            }
            off += r;
        }
        return data;
    }

    private static byte[] readChunkedBody(InputStream in) throws IOException {
        ByteArrayOutputStream out = new ByteArrayOutputStream(1024);
        while (true) {
            String sizeLine = readAsciiLine(in);
            if (sizeLine == null) {
                break;
            }
            int semi = sizeLine.indexOf(';');
            if (semi >= 0) {
                sizeLine = sizeLine.substring(0, semi);
            }
            sizeLine = sizeLine.trim();
            if (sizeLine.isEmpty()) {
                continue;
            }
            int chunkSize = Integer.parseInt(sizeLine, 16);
            if (chunkSize == 0) {
                // Consume trailing headers + CRLF
                while (true) {
                    String tr = readAsciiLine(in);
                    if (tr == null || tr.isEmpty()) {
                        break;
                    }
                }
                break;
            }
            byte[] chunk = readExactBytes(in, chunkSize);
            out.write(chunk);
            readAsciiLine(in); // trailing CRLF after chunk bytes
        }
        return out.toByteArray();
    }

    private static byte[] readBoundedStream(InputStream in, int maxBytes) throws IOException {
        if (in == null) {
            return new byte[0];
        }
        ByteArrayOutputStream out = new ByteArrayOutputStream(4096);
        byte[] buf = new byte[8192];
        int r;
        while ((r = in.read(buf)) != -1) {
            if (out.size() + r > maxBytes) {
                return null;
            }
            out.write(buf, 0, r);
        }
        return out.toByteArray();
    }

    private static void consumeQuietly(HttpURLConnection conn) {
        if (conn == null) {
            return;
        }
        InputStream es = null;
        try {
            es = conn.getErrorStream();
            if (es != null) {
                byte[] buf = new byte[1024];
                while (es.read(buf) != -1) {
                    // drain
                }
            }
        } catch (Throwable ignored) {
        } finally {
            if (es != null) {
                try {
                    es.close();
                } catch (IOException ignored) {
                }
            }
            conn.disconnect();
        }
    }

    private static void writeSimpleError(OutputStream out, int code, String message) throws IOException {
        byte[] body = message.getBytes(StandardCharsets.UTF_8);
        String hdr = "HTTP/1.1 " + code + " Gateway Error\r\n"
            + "Content-Type: text/plain; charset=utf-8\r\n"
            + "Content-Length: " + body.length + "\r\n"
            + "Connection: close\r\n\r\n";
        out.write(hdr.getBytes(StandardCharsets.US_ASCII));
        out.write(body);
        out.flush();
    }
}

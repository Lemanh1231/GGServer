package emu.leman.ggserver.net;

import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/** Token-keyed, bounded sessions. Logging in never replaces another login for the same account. */
public final class SessionManager implements AutoCloseable {
    private final Map<String,Session> sessions=new HashMap<>();
    private final SecureRandom random=new SecureRandom();
    private final Clock clock;
    private final Duration timeout;
    private final int maxSessions;
    private final ScheduledExecutorService cleanup;
    private boolean closed;

    public SessionManager(int timeoutSeconds,int cleanupSeconds,int maxSessions) {
        this(timeoutSeconds,cleanupSeconds,maxSessions,Clock.systemUTC());
    }

    /** Clock injection keeps expiry tests deterministic; all durations and the capacity must be positive. */
    public SessionManager(int timeoutSeconds,int cleanupSeconds,int maxSessions,Clock clock) {
        if(timeoutSeconds<=0 || cleanupSeconds<=0 || maxSessions<=0)
            throw new IllegalArgumentException("Session timeout, cleanup interval and capacity must be positive");
        this.clock=Objects.requireNonNull(clock,"clock");
        timeout=Duration.ofSeconds(timeoutSeconds);
        this.maxSessions=maxSessions;
        cleanup=Executors.newSingleThreadScheduledExecutor(task -> {
            Thread thread=new Thread(task,"ggserver-session-cleanup");
            thread.setDaemon(true);
            return thread;
        });
        cleanup.scheduleWithFixedDelay(this::cleanupExpired,cleanupSeconds,cleanupSeconds,TimeUnit.SECONDS);
    }

    public Session create(String canonicalUuid,String deviceUuid,String ip) {
        return create(canonicalUuid,deviceUuid,ip,"","");
    }

    /**
     * Adds server-selected legacy wire framing around fresh 256-bit randomness. The complete wire token
     * is registered; this never imports a client-supplied token or derives identity from its contents.
     */
    public synchronized Session create(String canonicalUuid,String deviceUuid,String ip,String prefix,String suffix) {
        if(closed) throw new IllegalStateException("Session manager is closed");
        if(canonicalUuid==null || canonicalUuid.isBlank()) throw new IllegalArgumentException("Canonical UUID is required");
        Objects.requireNonNull(prefix,"prefix");
        Objects.requireNonNull(suffix,"suffix");
        if(sessions.size()>=maxSessions) cleanupExpired();
        if(sessions.size()>=maxSessions) throw new IllegalStateException("Session capacity reached");
        String token;
        do {
            byte[] entropy=new byte[32];
            random.nextBytes(entropy);
            token=prefix+Base64.getUrlEncoder().withoutPadding().encodeToString(entropy)+suffix;
        } while(sessions.containsKey(token));
        Session session=new Session(token,canonicalUuid,deviceUuid==null?"":deviceUuid,ip==null?"":ip,clock.instant());
        sessions.put(token,session);
        return session;
    }

    /** Looks up a live token without extending its idle timeout. Blank/unknown/expired tokens return null. */
    public synchronized Session find(String token) {
        return find(token,clock.instant());
    }

    private Session find(String token,Instant now) {
        if(token==null || token.isEmpty()) return null;
        Session session=sessions.get(token);
        if(session!=null && expired(session,now)) {
            sessions.remove(token);
            return null;
        }
        return session;
    }

    /** Extend activity only after validating the request's identity. Expired sessions cannot be revived. */
    public synchronized boolean touch(String token) {
        Instant now=clock.instant();
        Session session=find(token,now);
        if(session==null) return false;
        session.touch(now);
        return true;
    }

    public synchronized boolean touch(Session session) {
        return session!=null && find(session.token())==session && touch(session.token());
    }

    public synchronized boolean invalidate(String token) { return sessions.remove(token)!=null; }

    /** Returns the number of live sessions, not accounts. */
    public synchronized int sessionCount() { cleanupExpired();return sessions.size(); }

    public synchronized int cleanupExpired() {
        Instant now=clock.instant();
        int before=sessions.size();
        sessions.values().removeIf(session -> expired(session,now));
        return before-sessions.size();
    }

    private boolean expired(Session session,Instant now) {
        return !now.isBefore(session.lastActiveAt().plus(timeout));
    }

    /** Services owns this lifecycle; stopping cleanup also revokes all remaining tokens. */
    @Override public synchronized void close() {
        if(closed) return;
        closed=true;
        cleanup.shutdownNow();
        sessions.clear();
    }
}

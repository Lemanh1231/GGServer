package emu.leman.ggserver.net;

import java.time.Instant;

/** A login's identity and activity only; mutable account state is always loaded from StateStore. */
public final class Session {
    private final String token;
    private final String canonicalUuid;
    private final String deviceUuid;
    private final String ip;
    private final Instant createdAt;
    private volatile Instant lastActiveAt;

    Session(String token,String canonicalUuid,String deviceUuid,String ip,Instant now) {
        this.token=token;
        this.canonicalUuid=canonicalUuid;
        this.deviceUuid=deviceUuid;
        this.ip=ip;
        createdAt=now;
        lastActiveAt=now;
    }

    public String token() { return token; }
    public String canonicalUuid() { return canonicalUuid; }
    public String deviceUuid() { return deviceUuid; }
    public String ip() { return ip; }
    public Instant createdAt() { return createdAt; }
    public Instant lastActiveAt() { return lastActiveAt; }

    // Called only while holding the owning manager's monitor. Clock rollback must not shorten activity.
    void touch(Instant now) { if(now.isAfter(lastActiveAt)) lastActiveAt=now; }

    /** Deliberately excludes the bearer token from logs. */
    @Override public String toString() { return "Session[canonicalUuid="+canonicalUuid+", createdAt="+createdAt+"]"; }
}

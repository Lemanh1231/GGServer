package emu.leman.ggserver.database;

/** Sensitive detached identity metadata only; no inventory and no cross-request caching. */
public record UserIdentity(String canonicalUuid,String deviceUuid) {
    @Override public String toString() { return "UserIdentity[redacted]"; }
}

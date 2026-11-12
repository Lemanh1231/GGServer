package emu.leman.ggserver.net;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HashSet;
import java.util.concurrent.Callable;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class SessionManagerTest {
    private static final class MutableClock extends Clock {
        private final AtomicReference<Instant> now=new AtomicReference<>(Instant.parse("2026-01-01T00:00:00Z"));
        @Override public ZoneId getZone() { return ZoneOffset.UTC; }
        @Override public Clock withZone(ZoneId zone) { return this; }
        @Override public Instant instant() { return now.get(); }
        void advance(long seconds) { now.updateAndGet(value -> value.plusSeconds(seconds)); }
    }

    @Test void sameAccountHasIndependentTokensAndConnectionDetails() {
        MutableClock clock=new MutableClock();
        try(SessionManager sessions=new SessionManager(60,3600,10,clock)) {
            Session phone=sessions.create("account","phone","203.0.113.1");
            Session tablet=sessions.create("account","tablet","203.0.113.2");
            assertNotEquals(phone.token(),tablet.token());
            assertEquals(32,Base64.getUrlDecoder().decode(phone.token()).length);
            assertEquals("account",phone.canonicalUuid());
            assertEquals("phone",phone.deviceUuid());
            assertEquals("203.0.113.2",tablet.ip());
            assertEquals(clock.instant(),phone.createdAt());
            assertEquals(clock.instant(),phone.lastActiveAt());
            assertSame(phone,sessions.find(phone.token()));
            assertSame(tablet,sessions.find(tablet.token()));
            assertEquals(2,sessions.sessionCount());
            assertTrue(sessions.invalidate(phone.token()));
            assertNull(sessions.find(phone.token()));
            assertSame(tablet,sessions.find(tablet.token()));
            assertFalse(phone.toString().contains(phone.token()));
        }
    }

    @Test void touchAndExpiryAffectOnlyOneLoginAndCannotReviveExpiredTokens() {
        MutableClock clock=new MutableClock();
        try(SessionManager sessions=new SessionManager(10,3600,10,clock)) {
            Session idle=sessions.create("account","phone","");
            Session active=sessions.create("account","tablet","");
            clock.advance(6);
            assertTrue(sessions.touch(active));
            assertEquals(clock.instant(),active.lastActiveAt());
            clock.advance(4);
            assertNull(sessions.find(idle.token())); // Exact timeout boundary expires.
            assertFalse(sessions.touch(idle));
            assertSame(active,sessions.find(active.token()));
            assertEquals(1,sessions.sessionCount());
            clock.advance(6);
            assertFalse(sessions.touch(active.token()));
            assertEquals(0,sessions.sessionCount());
        }
    }

    @Test void lookupDoesNotRefreshActivityAndCleanupIsClockControlled() {
        MutableClock clock=new MutableClock();
        try(SessionManager sessions=new SessionManager(10,3600,2,clock)) {
            Session first=sessions.create("account","phone","");
            clock.advance(9);
            assertNotNull(sessions.find(first.token()));
            assertEquals(first.createdAt(),first.lastActiveAt());
            clock.advance(1);
            assertEquals(1,sessions.cleanupExpired());
            assertNull(sessions.find(first.token()));
        }
    }

    @Test void capacityRejectsWithoutEvictionAndReclaimsExpiredSlots() {
        MutableClock clock=new MutableClock();
        try(SessionManager sessions=new SessionManager(10,3600,1,clock)) {
            Session original=sessions.create("account","phone","");
            assertThrows(IllegalStateException.class,()->sessions.create("account","tablet",""));
            assertSame(original,sessions.find(original.token()));
            clock.advance(10);
            Session replacement=sessions.create("account","tablet","");
            assertNull(sessions.find(original.token()));
            assertSame(replacement,sessions.find(replacement.token()));
            assertEquals(1,sessions.sessionCount());
        }
    }

    @Test void concurrentSameAccountLoginsAreUniqueAndCannotExceedCapacity() throws Exception {
        try(SessionManager sessions=new SessionManager(60,3600,64);
            var executor=Executors.newVirtualThreadPerTaskExecutor()) {
            var tasks=new ArrayList<Callable<Session>>();
            for(int i=0;i<256;i++) tasks.add(()-> {
                try { return sessions.create("account","phone",""); }
                catch(IllegalStateException full) { return null; }
            });
            var tokens=new HashSet<String>();
            for(var future:executor.invokeAll(tasks)) {
                Session session=future.get();
                if(session!=null) assertTrue(tokens.add(session.token()));
            }
            assertEquals(64,tokens.size());
            assertEquals(64,sessions.sessionCount());
        }
    }

    @Test void unknownAndClientSuppliedTokensAreNeverRegistered() {
        try(SessionManager sessions=new SessionManager(60,3600,10)) {
            assertNull(sessions.find(null));
            assertNull(sessions.find(""));
            assertNull(sessions.find("client-chosen-token"));
            assertFalse(sessions.touch("client-chosen-token"));
            assertFalse(sessions.invalidate("client-chosen-token"));
            assertEquals(0,sessions.sessionCount());
            Session framed=sessions.create("account","phone","","100001|123|phone|KR|","|42");
            assertTrue(framed.token().startsWith("100001|123|phone|KR|"));
            assertTrue(framed.token().endsWith("|42"));
            assertSame(framed,sessions.find(framed.token()));
        }
    }

    @Test void cleanupThreadIsDaemonAndCloseRevokesSessionsAndStopsCreation() {
        SessionManager sessions=new SessionManager(60,3600,10);
        Session session=sessions.create("account","phone","");
        assertTrue(Thread.getAllStackTraces().keySet().stream()
                .anyMatch(thread -> thread.getName().equals("ggserver-session-cleanup") && thread.isDaemon()));
        assertTimeoutPreemptively(Duration.ofSeconds(2),sessions::close);
        sessions.close();
        assertNull(sessions.find(session.token()));
        assertFalse(sessions.touch(session));
        assertEquals(0,sessions.sessionCount());
        assertThrows(IllegalStateException.class,()->sessions.create("account","phone",""));
    }

    @Test void invalidConfigurationAndMissingIdentityFailEarly() {
        assertThrows(IllegalArgumentException.class,()->new SessionManager(0,1,1));
        assertThrows(IllegalArgumentException.class,()->new SessionManager(1,0,1));
        assertThrows(IllegalArgumentException.class,()->new SessionManager(1,1,0));
        try(SessionManager sessions=new SessionManager(60,3600,10)) {
            assertThrows(IllegalArgumentException.class,()->sessions.create(" ","phone",""));
            Session session=sessions.create("account",null,null);
            assertEquals("",session.deviceUuid());
            assertEquals("",session.ip());
        }
    }
}

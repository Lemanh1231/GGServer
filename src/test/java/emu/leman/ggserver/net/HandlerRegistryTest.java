package emu.leman.ggserver.net;

import org.junit.jupiter.api.Test;
import java.util.*;
import java.util.concurrent.*;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class HandlerRegistryTest {
    @Test void stableDeviceIdentityTakesPrecedence() {
        Map<String,Object> request=obj("data",obj("uuid","client-session","device_uuid","stable"));
        assertEquals("stable",HandlerRegistry.payload(request).get("uuid"));
        assertEquals("client-session",map(request.get("data")).get("uuid"));
    }
    @Test void completeMutationsAreSerializedAcrossAliases() throws Exception {
        HandlerRegistry registry=new HandlerRegistry(ignored -> "canonical-account");
        int[] balance={0};
        registry.register("increment",(request,context) -> {
            int current=balance[0];
            Thread.yield();
            balance[0]=current+1;
            return Result.ok(obj());
        });
        try(var executor=Executors.newVirtualThreadPerTaskExecutor()) {
            List<Future<?>> tasks=new ArrayList<>();
            for(int i=0;i<1000;i++) {
                final int alias=i;
                tasks.add(executor.submit(() -> registry.handle("increment",obj("uuid","alias-"+alias),obj())));
            }
            for(var task:tasks) task.get();
        }
        assertEquals(1000,balance[0]);
        assertThrows(IllegalStateException.class,() -> registry.register("increment",(r,c) -> Result.ok(obj())));
    }
    @Test void broadcastsExcludeAccountWritersAndCannotUpgradeReadLock() throws Exception {
        HandlerRegistry registry=new HandlerRegistry();
        CountDownLatch entered=new CountDownLatch(1), release=new CountDownLatch(1);
        try(var executor=Executors.newVirtualThreadPerTaskExecutor()) {
            Future<?> account=executor.submit(() -> registry.withAccountLock("user",() -> {
                entered.countDown();
                try { assertTrue(release.await(5,TimeUnit.SECONDS)); } catch(InterruptedException e) { throw new RuntimeException(e); }
                return null;
            }));
            assertTrue(entered.await(5,TimeUnit.SECONDS));
            Future<?> broadcast=executor.submit(() -> registry.withExclusiveLock(() -> null));
            try { assertThrows(TimeoutException.class,() -> broadcast.get(100,TimeUnit.MILLISECONDS)); }
            finally { release.countDown(); }
            account.get(5,TimeUnit.SECONDS);
            broadcast.get(5,TimeUnit.SECONDS);
        }
        assertThrows(IllegalStateException.class,() -> registry.withAccountLock("user",() -> registry.withExclusiveLock(() -> null)));
    }
}

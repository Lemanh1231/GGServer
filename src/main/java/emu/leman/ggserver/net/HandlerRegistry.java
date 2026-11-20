package emu.leman.ggserver.net;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.locks.ReentrantLock;
import java.util.concurrent.locks.ReentrantReadWriteLock;
import java.util.function.Function;
import java.util.function.Supplier;
import static emu.leman.ggserver.util.Json.*;
public final class HandlerRegistry {
    private final Map<String,CommandHandler> handlers = new ConcurrentHashMap<>();
    private final ReentrantLock[] accountLocks = new ReentrantLock[1024];
    private final ReentrantReadWriteLock operations = new ReentrantReadWriteLock(true);
    private final Function<String,String> canonicalIdentity;
    private java.util.function.BiFunction<String,Supplier<Result>,Result> accountScope=(id,operation)->operation.get();
    public void accountScope(java.util.function.BiFunction<String,Supplier<Result>,Result> scope) {accountScope=Objects.requireNonNull(scope);}
    public HandlerRegistry() { this(Function.identity()); }
    public HandlerRegistry(Function<String,String> canonicalIdentity) {
        this.canonicalIdentity=canonicalIdentity;
        Arrays.setAll(accountLocks,i -> new ReentrantLock());
    }
    public void register(String name,CommandHandler handler) { if(handlers.putIfAbsent(name,handler)!=null) throw new IllegalStateException("Duplicate command: "+name); }
    public Result handle(String name,Map<String,Object> request,Map<String,Object> context) {
        CommandHandler handler=handlers.get(name);
        if(handler==null) return Result.ok(obj()); // Matches Python's unimplemented-command fallback.
        Map<String,Object> data=payload(request);
        String identity=str(first(data.get("uuid"),context.get("uuid"),data.get("u_seq"),""));
        return withAccountLock(identity,() -> accountScope.apply(identity,() -> handler.handle(request,context)));
    }
    public <T> T withAccountLock(String identity,Supplier<T> operation) {
        operations.readLock().lock();
        try {
            String canonical=identity==null || identity.isEmpty() ? "" : canonicalIdentity.apply(identity);
            ReentrantLock lock=accountLocks[(Objects.hashCode(canonical)&Integer.MAX_VALUE)%accountLocks.length];
            // Guard the complete read-modify-save sequence, not only individual SQL updates.
            // Fixed stripes bound memory even when clients submit arbitrary UUIDs.
            lock.lock();
            try { return operation.get(); } finally { lock.unlock(); }
        } finally { operations.readLock().unlock(); }
    }
    /** For broadcasts spanning many account snapshots. Acquire before loading any users. */
    public <T> T withExclusiveLock(Supplier<T> operation) {
        if(operations.getReadHoldCount()>0 && !operations.isWriteLockedByCurrentThread())
            throw new IllegalStateException("Cannot upgrade an account operation into a global operation");
        operations.writeLock().lock();
        try { return operation.get(); } finally { operations.writeLock().unlock(); }
    }
    public Set<String> commands() { return Set.copyOf(handlers.keySet()); }
    public static Map<String,Object> payload(Map<String,Object> request) { Map<String,Object> p=new LinkedHashMap<>(request.get("data") instanceof Map ? map(request.get("data")) : request); if(truth(p.get("device_uuid"))) p.put("uuid",p.get("device_uuid")); return p; }
}

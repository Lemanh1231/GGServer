package emu.leman.ggserver.database;

import emu.leman.ggserver.config.ServerConfig;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

/** Stable game-facing API; storage selection is explicit and never migrates or deletes another backend. */
public final class StateStore implements AutoCloseable {
    private final UserRepository repository;

    /** Legacy callers and fixtures continue to use SQLite. */
    public StateStore(Path root) { this(new SqliteUserRepository(ServerConfig.defaults(root))); }
    public StateStore(ServerConfig config) {
        this(switch (config.databaseBackend) {
            case "sqlite" -> new SqliteUserRepository(config);
            case "mongo", "mongodb" -> new MongoUserRepository(config);
            default -> throw new IllegalArgumentException("Unsupported database backend: " + config.databaseBackend);
        });
    }
    public StateStore(UserRepository repository) { this.repository = java.util.Objects.requireNonNull(repository); }
    public Map<String,Object> getUser(String identifier) { return repository.getUser(identifier); }
    public UserIdentity getIdentity(String identifier) { return repository.getIdentity(identifier); }
    public String canonicalIdentity(String identifier) { return repository.canonicalIdentity(identifier); }
    public Map<String,Object> createUser(String uuid, String deviceUuid) { return createUser(uuid, deviceUuid, ""); }
    public Map<String,Object> createUser(String uuid, String deviceUuid, String ip) { return repository.createUser(uuid, deviceUuid, ip); }
    public void saveUser(Map<String,Object> user) { repository.saveUser(user); }
    public void updateUserIp(String identifier, String ip) { updateUserIp(identifier, ip, null); }
    public void updateUserIp(String identifier, String ip, String domain) { repository.updateUserIp(identifier, ip, domain); }
    public void incrementCurrency(String identifier, long cp, double candy, Object like, long fans) { repository.incrementCurrency(identifier, cp, candy, like, fans); }
    public void setLikeCurrency(String identifier, Object amount) { repository.setLikeCurrency(identifier, amount); }
    public boolean banUser(String identifier) { return banUser(identifier, true, null); }
    public boolean banUser(String identifier, boolean banned) { return banUser(identifier, banned, null); }
    public boolean banUser(String identifier, boolean banned, Long sequence) { return repository.banUser(identifier, banned, sequence); }
    public boolean isUserBanned(String identifier) { return repository.isUserBanned(identifier); }
    public boolean deleteUser(String identifier) { return deleteUser(identifier, null); }
    public boolean deleteUser(String identifier, Long sequence) { return repository.deleteUser(identifier, sequence); }
    public int cleanupTestUsers() { return repository.cleanupTestUsers(); }
    public boolean spendCurrency(String identifier, String currency, double amount) { return repository.spendCurrency(identifier, currency, amount); }
    public boolean spendCurrency(String identifier, String currency, long amount) { return repository.spendCurrency(identifier, currency, amount); }
    public void setCurrency(String identifier, long cp, double candy) { repository.setCurrency(identifier, cp, candy); }
    public void updateAttendance(String identifier, int count, int date) { repository.updateAttendance(identifier, count, date); }
    public List<Map<String,Object>> allChThirdStages() { return repository.allChThirdStages(); }
    public List<Map<String,Object>> listUserRows() { return repository.listUserRows(); }
    public Map<String,Object> exportUser(String identifier) { return repository.exportUser(identifier); }
    public void importUser(Map<String,Object> user) { repository.importUser(user); }
    public static boolean isRealDeviceUuid(Object value) { return SqliteUserRepository.isRealDeviceUuid(value); }
    public static boolean isTestUser(String uuid, String deviceUuid) { return SqliteUserRepository.isTestUser(uuid, deviceUuid); }
    public static Map<String,Object> addAp(Map<String,Object> user, int amount) { return SqliteUserRepository.addAp(user, amount); }
    @Override public void close() { repository.close(); }
}

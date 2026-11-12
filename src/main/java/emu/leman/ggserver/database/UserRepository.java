package emu.leman.ggserver.database;

import java.util.List;
import java.util.Map;

/** Storage boundary. Returned account maps are detached snapshots, never live database objects. */
public interface UserRepository extends AutoCloseable {
    Map<String,Object> getUser(String identifier);
    Map<String,Object> createUser(String uuid, String deviceUuid, String ip);
    void saveUser(Map<String,Object> user);
    void updateUserIp(String identifier, String ip, String domain);
    void incrementCurrency(String identifier, long cp, double candy, Object like, long fans);
    void setLikeCurrency(String identifier, Object amount);
    boolean banUser(String identifier, boolean banned, Long sequence);
    boolean isUserBanned(String identifier);
    boolean deleteUser(String identifier, Long sequence);
    int cleanupTestUsers();
    boolean spendCurrency(String identifier, String currency, double amount);
    boolean spendCurrency(String identifier, String currency, long amount);
    void setCurrency(String identifier, long cp, double candy);
    void updateAttendance(String identifier, int count, int date);
    List<Map<String,Object>> allChThirdStages();
    /** Compatibility rows matching the legacy user_data SQL column names and JSON snapshot. */
    List<Map<String,Object>> listUserRows();
    /** Lossless, backend-neutral account snapshot, including ban, IP and last-domain metadata. */
    Map<String,Object> exportUser(String identifier);
    /** Explicit atomic insert. Canonical UUID and aliases are preserved; any existing account collision fails. */
    void importUser(Map<String,Object> user);
    @Override void close();
}

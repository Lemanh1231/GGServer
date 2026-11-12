package emu.leman.ggserver.net;
import java.util.Map;
@FunctionalInterface public interface CommandHandler { Result handle(Map<String,Object> request, Map<String,Object> context); }

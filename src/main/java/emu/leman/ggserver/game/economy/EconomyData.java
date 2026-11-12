package emu.leman.ggserver.game.economy;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import org.apache.commons.compress.compressors.bzip2.BZip2CompressorInputStream;
import static emu.leman.ggserver.util.Json.*;

/** Local, read-only table access, including the captured attendance board's native wire format. */
final class EconomyData {
    final Path root;
    private final emu.leman.ggserver.config.ServerConfig config;
    private Map<String,Object> game;
    private Map<String,Object> boards;

    EconomyData(Path root) { this(emu.leman.ggserver.config.ServerConfig.defaults(root)); }
    EconomyData(emu.leman.ggserver.config.ServerConfig config) { this.config=config; this.root=config.root; }

    Path locate(String relative) {
        return config.resource(relative);
    }

    synchronized Map<String,Object> game() {
        if (game == null) {
            Path path = locate("gamedata/game_data.json");
            game = Files.isRegularFile(path) ? map(read(path)) : obj();
        }
        return game;
    }

    List<Map<String,Object>> rows(int table) {
        List<Map<String,Object>> result = new ArrayList<>();
        for (Object row : list(game().get(String.valueOf(table)))) if (row instanceof Map) result.add(map(row));
        return result;
    }

    Map<String,Object> row(int table, int id) {
        for (Map<String,Object> row : rows(table)) if (integer(row.get("1")) == id) return row;
        return obj();
    }

    List<Object> rewards(int group) {
        List<Object> result = new ArrayList<>();
        for (Map<String,Object> row : rows(13)) if (integer(row.get("2")) == group)
            result.add(reward(integer(row.get("3")), integer(row.get("4")), lng(row.get("5"))));
        return result;
    }

    static Map<String,Object> reward(int type, int id, Object value) {
        return obj("reward_type", type, "reward_id", id, "reward_value", value);
    }

    synchronized Map<String,Object> boards() {
        if (boards == null) {
            Path json = locate("gamedata/getEventRewardList.json");
            if (Files.isRegularFile(json)) {
                Map<String,Object> decoded = map(read(json));
                boards = map(decoded.getOrDefault("data", decoded));
            } else {
                Path capture = locate("gamedata/getEventRewardList.b64");
                if (!Files.isRegularFile(capture)) boards = obj();
                else try {
                    Map<String,Object> schema = map(read(locate("schema/schema.json")));
                    byte[] compressed = Base64.getMimeDecoder().decode(Files.readString(capture).strip());
                    try (DataInputStream in = new DataInputStream(new BZip2CompressorInputStream(new ByteArrayInputStream(compressed)))) {
                        boards = map(map(readStruct(in, "main.getEventRewardListReturn", schema)).get("data"));
                    }
                } catch (IOException | IllegalArgumentException e) {
                    throw new IllegalStateException("Cannot decode attendance board " + capture, e);
                }
            }
        }
        return boards;
    }

    // Minimal schema-driven Thrift binary reader. Unknown fields are consumed, not guessed.
    private static Object readStruct(DataInputStream in, String name, Map<String,Object> schema) throws IOException {
        Map<String,Object> result = obj();
        Map<Integer,Map<String,Object>> fields = new HashMap<>();
        for (Object f : list(map(schema.get(name)).get("fields"))) fields.put(integer(map(f).get("id")), map(f));
        for (int type; (type = in.readUnsignedByte()) != 0;) {
            int id = in.readShort();
            Map<String,Object> field = fields.getOrDefault(id, obj());
            result.put(str(field.getOrDefault("name", String.valueOf(id))), readValue(in, type, field, schema));
        }
        return result;
    }

    private static int size(DataInputStream in) throws IOException {
        int size = in.readInt();
        if (size < 0 || size > 16_000_000) throw new IOException("Invalid Thrift length: " + size);
        return size;
    }

    private static Object readValue(DataInputStream in, int type, Map<String,Object> spec, Map<String,Object> schema) throws IOException {
        return switch (type) {
            case 2 -> in.readBoolean();
            case 3 -> in.readByte();
            case 4 -> in.readDouble();
            case 6 -> in.readShort();
            case 8 -> in.readInt();
            case 10 -> in.readLong();
            case 11 -> {
                byte[] bytes = new byte[size(in)];
                in.readFully(bytes);
                yield new String(bytes, StandardCharsets.UTF_8);
            }
            case 12 -> readStruct(in, str(spec.get("struct")), schema);
            case 13 -> {
                int keyType = in.readUnsignedByte(), valueType = in.readUnsignedByte(), count = size(in);
                Map<String,Object> result = obj();
                for (int i = 0; i < count; i++) {
                    Object key = readValue(in, keyType, map(spec.get("key")), schema);
                    result.put(str(key), readValue(in, valueType, map(spec.get("val")), schema));
                }
                yield result;
            }
            case 14, 15 -> {
                int itemType = in.readUnsignedByte(), count = size(in);
                List<Object> result = new ArrayList<>();
                for (int i = 0; i < count; i++) result.add(readValue(in, itemType, map(spec.get("elem")), schema));
                yield result;
            }
            default -> throw new IOException("Unsupported Thrift type: " + type);
        };
    }
}

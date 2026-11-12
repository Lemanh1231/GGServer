package emu.leman.ggserver.game.content;

import java.nio.file.*;
import java.util.*;
import java.util.function.Consumer;
import static emu.leman.ggserver.util.Json.*;

/** Every query reloads configuration, so operator edits take effect without a restart. */
public final class EventManager {
    public static final List<Map<String,Object>> STAR_PASS_SEASONS = seasons();
    private static List<Map<String,Object>> seasons() {
        String[] vi={"Vị chanh Kỳ nghỉ","Một điều ước gửi đến mặt trăng","Ngọt ngào Bữa tiệc Halloween","Buổi chụp ảnh đặc biệt! Thần tượng ngọt ngào","Lấp lánh Giáng Sinh mộng mơ","Lễ hội tuyết","Thiếu nữ ngày Tình nhân","Hẹn hò mùa hoa anh đào","Thông điệp mùa xuân dễ thương","Picnic Tối Đầy Nắng","Ký Ức Màu Phấn Mơ Mộng","Mùa Hè Lấp Lánh","Cưỡi một vòng đu quay lãng mạn"};
        String[] en={"Lemon Flavored Vacation","Make a wish to the moon","Sweet Halloween Party","Sweet Idol Photoshoot!","Twinkling Dreamy Christmas","Snow Festival","Maid in Valentine","Cherry Blossom Date","Pleasant Spring Message","Sunny Evening Picnic","Dreaming Pastel Memories","Shining Summer","Riding a Romantic Ferris Wheel"};
        List<Map<String,Object>> seasons=new ArrayList<>();
        for(int i=0;i<13;i++)seasons.add(Collections.unmodifiableMap(obj("id",i+1,"name",vi[i]+" ("+en[i]+")","name_vi",vi[i],"name_en",en[i],"year",i<5?2020:2021,"month",i<5?i+8:i-4)));
        return Collections.unmodifiableList(seasons);
    }
    private final Path configPath;
    private Consumer<Map<String,Object>> notificationSink;
    public EventManager(Path root) { configPath=root.resolve("event_config.json"); }
    public Path configPath() { return configPath; }
    public static Map<String,Object> defaults() {
        Map<String,Object> attendance=obj();
        String[] ids={"1","2","3","202110","202111"};
        String[] names={"Điểm danh 7 ngày tân thủ","Điểm danh kỷ niệm 1 năm","Tiệm bánh Hạnh phúc (CH2)","Điểm danh Halloween (10/2021)","Chọn quà tân thủ (11/2021)"};
        String[] descriptions={"Nhận CP, Kẹo, Trang phục Váy đầm hoa tuyết và Nhạc Bông hoa chưa được đặt tên","Sự kiện 1st Anniversary mừng sinh nhật game (14 ngày: Guitar Đêm tím, Trang phục Ký ức vĩnh cửu)","Điểm danh hằng ngày Cửa hàng tiện lợi Chapter 2 (7 ngày Bánh gừng, Kẹo, Năng lượng Cookie AP)","Sự kiện đăng nhập lễ hội Halloween 14 ngày (Guitar Hoa hạnh nhân, Trang phục Cô gái hồng)","Sự kiện chọn quà đăng nhập tân thủ 7 ngày"};
        for(int i=0;i<ids.length;i++) attendance.put(ids[i],obj("name",names[i],"description",descriptions[i],"enabled",i==0||i==2));
        Map<String,Object> cfg=obj("attendance_events",attendance,
            "star_pass",obj("name","Thẻ Sao / Star Pass","description","Vé mùa Star Pass với chuỗi nhiệm vụ và phần thưởng độc quyền 13 mùa giải","enabled",true,"active_season",13,"paid_card_enabled",false),
            "weather_festival",obj("name","Lễ hội Hiệu ứng Thời tiết Mùa","description","Hiệu ứng tuyết rơi mùa đông (Snow Festival) hoặc cánh hoa anh đào rơi mùa xuân (Cherry Blossom Date)","snow_enabled",true,"cherry_blossom_enabled",false));
        String[] sections={"pass_goods_sale","meowfest","chapter3_tour","fan_art_costume","event_ranking"};
        String[] labels={"Cửa hàng Giảm giá Star Pass (Pass Goods Sale)","Sự kiện Nuôi Mèo Meowfest (SamSeck)","Tour Chapter 3 (Sunshine High School)","Trang phục Thiết kế Fan Art","Đua Top Xếp Hạng Sự Kiện (Event Ranking)"};
        String[] sectionDescriptions={"Mở biểu tượng nút Sale trên sảnh chính để mua lại toàn bộ Trang phục & Guitar của 13 mùa Star Pass đã qua","Mở khóa 3 mốc nuôi mèo Tam Thể nhận Cây cào móng (Guitar 10), Quần yếm (Costume 13), Bé mèo Navi (Unit 1)","Biểu diễn sân khấu trường trung học Sunshine 20 màn với Năng lượng Cookie / AP","Kích hoạt bộ trang phục nghệ thuật do cộng đồng người hâm mộ sáng tạo","Bảng xếp hạng đua top điểm sự kiện trực tiếp với danh sách Top 100 cao thủ"};
        for(int i=0;i<sections.length;i++) cfg.put(sections[i],obj("name",labels[i],"description",sectionDescriptions[i],"enabled",true));
        return cfg;
    }
    public static Map<String,Object> normalize(Object value) {
        Map<String,Object> raw=map(value),cfg=defaults();
        Map<String,Object> att=map(raw.get(raw.get("attendance_events") instanceof Map ? "attendance_events":"events"));
        for(var entry:map(cfg.get("attendance_events")).entrySet()) {
            Map<String,Object> def=map(entry.getValue());
            if(att.get(entry.getKey()) instanceof Map) {
                Map<String,Object> item=map(att.get(entry.getKey()));
                def.put("enabled",truth(item.getOrDefault("enabled",def.get("enabled"))));
                for(String key:List.of("name","description")) if(item.containsKey(key)) def.put(key,item.get(key));
            }
        }
        Map<String,Object> sp=map(cfg.get("star_pass"));
        if(raw.get("star_pass") instanceof Map) {
            Map<String,Object> item=map(raw.get("star_pass"));
            sp.put("enabled",truth(item.getOrDefault("enabled",true)));
            int season=integer(item.getOrDefault("active_season",13));
            if(season>=1&&season<=13) sp.put("active_season",season);
            sp.put("paid_card_enabled",truth(item.get("paid_card_enabled")));
        } else if(raw.get("paid_star_card") instanceof Map) sp.put("paid_card_enabled",truth(map(raw.get("paid_star_card")).get("enabled")));
        for(String section:List.of("pass_goods_sale","meowfest","chapter3_tour","fan_art_costume","event_ranking")) {
            if(raw.get(section) instanceof Map) map(cfg.get(section)).put("enabled",truth(map(raw.get(section)).getOrDefault("enabled",true)));
        }
        if(raw.get("weather_festival") instanceof Map) {
            Map<String,Object> item=map(raw.get("weather_festival")),wf=map(cfg.get("weather_festival"));
            boolean snow=truth(item.get("snow_enabled")),cherry=truth(item.get("cherry_blossom_enabled"));
            String mode=str(item.get("mode"));
            switch(mode) { case "snow" -> {snow=true;cherry=false;} case "cherry" -> {snow=false;cherry=true;} case "none" -> {snow=false;cherry=false;} default -> { if(snow&&cherry) cherry=false; mode=snow?"snow":cherry?"cherry":"none"; } }
            wf.put("snow_enabled",snow); wf.put("cherry_blossom_enabled",cherry); wf.put("mode",mode);
        }
        Map<String,Object> legacy=obj();
        map(cfg.get("attendance_events")).forEach((key,val)-> {Map<String,Object> item=map(val);legacy.put(key,obj("name",item.get("name"),"enabled",item.get("enabled"),"state",truth(item.get("enabled"))?"active":"ended"));});
        cfg.put("events",legacy); cfg.put("paid_star_card",obj("name","Thẻ Sao Gold trả tiền","enabled",sp.get("paid_card_enabled"),"price",0));
        return cfg;
    }
    public Map<String,Object> snapshot() { try { return normalize(read(configPath)); } catch(Exception e) { return normalize(defaults()); } }
    public Map<String,Object> activeEvents() { Map<String,Object> out=obj(); map(snapshot().get("attendance_events")).forEach((k,v)->{if(truth(map(v).get("enabled"))) out.put(k,v);}); return out; }
    public Map<String,Object> getActiveAttendanceEvents() { return activeEvents(); }
    public Map<String,Object> saveConfig(Map<String,Object> cfg) { return save(cfg); }
    public int getStarPassSeason() { return activeStarPassSeason(); }
    public Map<String,Object> getSettingsOverrides() {
        Map<String,Object> cfg=snapshot();
        return obj("weather_snow",String.valueOf(truth(map(cfg.get("weather_festival")).get("snow_enabled"))),
            "weather_cherry_blossom",String.valueOf(truth(map(cfg.get("weather_festival")).get("cherry_blossom_enabled"))),
            "active_fan_art_costume",String.valueOf(truth(map(cfg.get("fan_art_costume")).get("enabled"))),
            "pass_goods_sale_start_time","2020-01-01 00:00",
            "pass_goods_sale_end_time",truth(map(cfg.get("pass_goods_sale")).get("enabled"))?"2999-12-31 23:59":"2020-01-01 00:00");
    }
    /** User-independent event-main fields. A disabled event yields an empty map. */
    public Map<String,Object> getEventModeData() {
        if(!isEventRankingEnabled())return obj();
        return obj("idx",1,"title","Guitar Girl Live Festival","img1","","img2","","movie","","utc",9,"banner","","desc_cn","吉他少女现场庆典活动","desc_en","Guitar Girl Live Festival Event","desc_jp","ギターガールライブフェスティバル","server_time",java.time.Instant.now().getEpochSecond(),"start_time",1600000000L,"end_time",4102444800L);
    }
    /** Event-ranking rewards (not attendance rewards). */
    public Map<String,Object> getEventRewardList() {
        if(!isEventRankingEnabled())return obj();
        return obj("event_idx",1,"reward_list",List.of(obj("gain_point",100,"reward_type",1,"reward_value",500),obj("gain_point",500,"reward_type",1,"reward_value",1000),obj("gain_point",1000,"reward_type",1,"reward_value",2000)),"rank_reward_list",List.of(
            obj("title","Top 1-10","desc_cn","第1-10名奖励","desc_en","Rank 1-10 Reward","desc_jp","1-10位報酬","reward_type",1,"reward_value",5000),
            obj("title","Top 11-50","desc_cn","第11-50名奖励","desc_en","Rank 11-50 Reward","desc_jp","11-50位報酬","reward_type",1,"reward_value",2500),
            obj("title","Top 51-100","desc_cn","第51-100名奖励","desc_en","Rank 51-100 Reward","desc_jp","51-100位報酬","reward_type",1,"reward_value",1000)));
    }
    public synchronized Map<String,Object> save(Map<String,Object> cfg) { return save(cfg,false); }
    public synchronized Map<String,Object> save(Map<String,Object> cfg, boolean notifyInGame) { Map<String,Object> normalized=normalize(cfg);write(configPath,normalized);if(notifyInGame&&notificationSink!=null) notificationSink.accept(copy(normalized));return normalized; }
    /** Allows the post service to supply the optional live-update announcement. */
    public void notificationSink(Consumer<Map<String,Object>> sink) { notificationSink=sink; }
    private boolean enabled(String section,String key) { return truth(map(snapshot().get(section)).get(key)); }
    public boolean isAttendanceEventEnabled(Object id) { return truth(map(map(snapshot().get("attendance_events")).get(str(id))).get("enabled")); }
    public boolean isStarPassEnabled() { return enabled("star_pass","enabled"); }
    public int activeStarPassSeason() { return integer(map(snapshot().get("star_pass")).get("active_season")); }
    public int getActiveStarPassSeason() { return activeStarPassSeason(); }
    public boolean isPaidStarCardEnabled() { return enabled("star_pass","paid_card_enabled"); }
    public boolean isPassGoodsSaleEnabled() { return enabled("pass_goods_sale","enabled"); }
    public boolean isMeowfestEnabled() { return enabled("meowfest","enabled"); }
    public boolean isChapter3TourEnabled() { return enabled("chapter3_tour","enabled"); }
    public boolean isWeatherSnowEnabled() { return enabled("weather_festival","snow_enabled"); }
    public boolean isWeatherCherryBlossomEnabled() { return enabled("weather_festival","cherry_blossom_enabled"); }
    public boolean isFanArtCostumeEnabled() { return enabled("fan_art_costume","enabled"); }
    public boolean isEventRankingEnabled() { return enabled("event_ranking","enabled"); }
    public Map<String,Object> setAttendanceEventEnabled(Object id,boolean enabled) { Map<String,Object> cfg=snapshot(),item=map(map(cfg.get("attendance_events")).get(str(id)));if(item.isEmpty()) return cfg;item.put("enabled",enabled);return save(cfg); }
    public Map<String,Object> setStarPass(Boolean enabled,Integer season,Boolean paidGold) { Map<String,Object> cfg=snapshot(),sp=map(cfg.get("star_pass"));if(enabled!=null)sp.put("enabled",enabled);if(season!=null&&season>=1&&season<=13)sp.put("active_season",season);if(paidGold!=null)sp.put("paid_card_enabled",paidGold);return save(cfg); }
    public Map<String,Object> setEnabled(String section,boolean enabled) { Map<String,Object> cfg=snapshot();if(map(cfg.get(section)).containsKey("enabled"))map(cfg.get(section)).put("enabled",enabled);return save(cfg); }
    public Map<String,Object> setMeowfestEnabled(boolean value) {return setEnabled("meowfest",value);}
    public Map<String,Object> setPassGoodsSaleEnabled(boolean value) {return setEnabled("pass_goods_sale",value);}
    public Map<String,Object> setChapter3TourEnabled(boolean value) {return setEnabled("chapter3_tour",value);}
    public Map<String,Object> setFanArtCostumeEnabled(boolean value) {return setEnabled("fan_art_costume",value);}
    public Map<String,Object> setEventRankingEnabled(boolean value) {return setEnabled("event_ranking",value);}
    public Map<String,Object> setWeatherFestival(Boolean snow,Boolean cherry) {
        Map<String,Object> cfg=snapshot(),wf=map(cfg.get("weather_festival"));
        boolean s=truth(wf.get("snow_enabled")),c=truth(wf.get("cherry_blossom_enabled"));
        if(Boolean.TRUE.equals(snow)) {s=true;c=false;} else if(Boolean.TRUE.equals(cherry)) {s=false;c=true;} else {if(snow!=null)s=snow;if(cherry!=null)c=cherry;}
        wf.put("snow_enabled",s);wf.put("cherry_blossom_enabled",c);wf.put("mode",s?"snow":c?"cherry":"none");return save(cfg);
    }
}

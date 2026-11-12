package emu.leman.ggserver.game.account;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.CmdId;
import emu.leman.ggserver.game.player.ProfileModule;
import emu.leman.ggserver.game.economy.Currency;
import emu.leman.ggserver.database.StateStore;
import emu.leman.ggserver.net.HandlerRegistry;
import emu.leman.ggserver.net.Result;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;
import static emu.leman.ggserver.game.account.AuthContent.*;

/** Auth, profile and system commands, preserving the client wire schema. */
public final class AccountModule implements emu.leman.ggserver.game.GameModule {
    private final Services s;
    public final AuthContent content;
    public AccountModule(Services services) { s=services; content=new AuthContent(s); }
    @Override public String id() { return "auth"; }
    @Override public void register() {
        s.registry.register(CmdId.USER_JOIN,(r,c)->join(HandlerRegistry.payload(r),c));
        s.registry.register(CmdId.USER_LOGIN,(r,c)->login(HandlerRegistry.payload(r),c));
        s.registry.register(CmdId.USER_SAVE,(r,c)->save(HandlerRegistry.payload(r),c));
        s.registry.register(CmdId.USER_LOAD,(r,c)->load(HandlerRegistry.payload(r),c));
        s.registry.register(CmdId.LAST_SAVE_TIME,(r,c)->lastSave(HandlerRegistry.payload(r),c));
        s.registry.register(CmdId.SET_TUTORIAL_NEW,(r,c)->tutorial(HandlerRegistry.payload(r),c));
        s.registry.register(CmdId.SET_SUBSCRIBE,(r,c)->subscribe(HandlerRegistry.payload(r),c));
        s.registry.register(CmdId.SET_REVIEW_POPUP,(r,c)->{ Map<String,Object> u=user(HandlerRegistry.payload(r),c); if(u!=null) { object(u,"userdata").put("u_review_popup","Y"); s.state.saveUser(u); } return Result.ok(obj("status","Y")); });
        new ProfileModule(s).register();
        s.registry.register(CmdId.REQUEST,(r,c)->Result.ok(obj("idx",253,"game_url",c.get("game_url"),"cdn_url",c.get("cdn_url"))));
        s.registry.register(CmdId.GET_SERVER_TIME,(r,c)->Result.ok(serverTime()));
        s.registry.register(CmdId.GET_UPDATE_TIME,(r,c)->Result.ok(obj("upd_time",1700000000)));
        s.registry.register(CmdId.DEFAULT_SETTING_LIST,(r,c)->Result.ok(defaultSettings()));
        s.registry.register(CmdId.HIBERNATION_LOG,(r,c)->Result.ok(obj("action",0)));
        s.registry.register(CmdId.COMPLETE_LOG,(r,c)->Result.ok(obj("status","1")));
    }
    private String identity(Map<String,Object> p,Map<String,Object> c) { return str(first(p.get("uuid"),p.get("device_uuid"),c.get("uuid"))); }
    private Map<String,Object> user(Map<String,Object> p,Map<String,Object> c) { return s.state.getUser(identity(p,c)); }
    private Result join(Map<String,Object> p,Map<String,Object> c) {
        Map<String,Object> ud=map(AuthContent.createUser(s,identity(p,c),str(p.get("device_uuid")),"").get("userdata"));
        return Result.ok(obj("u_seq",ud.get("u_seq"),"u_id",ud.get("u_id")));
    }
    public void migrateLegacy(Map<String,Object> user) {
        Map<String,Object> ud=object(user,"userdata");
        if(lng(ud.get("u_free_cp"))==1_000_000) {
            ud.putAll(obj("u_free_cp",0,"u_cp",0,"u_candy",0.0));
            s.state.setCurrency(str(user.get("uuid")),0,0.0); s.state.saveUser(user);
        }
        if(!truth(user.get("legacy_unlock_all_migrated"))) {
            user.put("costumes",new ArrayList<>(List.of(item(1)))); user.put("user_music",new ArrayList<>(List.of(music(1))));
            user.put("user_guitar",new ArrayList<>(List.of(item(1)))); user.put("legacy_unlock_all_migrated",true); s.state.saveUser(user);
        }
    }
    private Result login(Map<String,Object> p,Map<String,Object> c) {
        synchronized(s.state) {
            String id=identity(p,c); Map<String,Object> u=s.state.getUser(id);
            if(u==null&&truth(p.get("device_uuid"))) u=s.state.getUser(str(p.get("device_uuid")));
            if(u!=null&&truth(u.get("is_banned"))) return Result.error(900,"Tài khoản của bạn đã bị KHÓA (BAN) bởi Quản trị viên!\nVui lòng liên hệ Admin để được hỗ trợ.");
            String ip=str(c.get("client_ip"));
            if(u==null) u=AuthContent.createUser(s,id,str(p.get("device_uuid")),ip);
            else if(!ip.isEmpty()) { s.state.updateUserIp(str(u.get("uuid")),ip,str(c.get("domain"))); u.put("ip",ip); object(u,"userdata").put("ip",ip); }
            Map<String,Object> ud=object(u,"userdata");
            if(lng(p.get("u_seq"))==0) {
                Map<String,Object> resp=obj("u_seq",ud.get("u_seq"),"u_id",str(first(ud.get("u_seq"),ud.get("u_id"))));
                if(truth(p.get("uuid"))) resp.put("uuid",p.get("uuid")); return Result.ok(obj("user",resp));
            }
            migrateLegacy(u); Map<String,Object> contents=userContents(u); Map<String,Object> areas=areas(u);
            Currency.Parsed like=Currency.parse(ud.get("u_like"));
            for(Object value:areas.values()) {
                Map<String,Object> area=map(value); Currency.Parsed previous=Currency.parse(first(area.get("s_Gp1"),"0"));
                Currency.Parsed target=truth(u.get("force_server_like"))||like.integer().compareTo(previous.integer())>0 ? like:previous;
                area.put("d_Like",target.floating()); area.put("s_Gp1",target.gp());
            }
            u.remove("force_server_like");
            if(!str(ud.get("u_create_time")).matches("-?\\d+")) ud.put("u_create_time",str(today()));
            boolean reset=truth(u.get("needs_client_reset"))||lng(p.get("u_seq"))!=lng(ud.get("u_seq")); String now=timestamp();
            ud.put("u_last_login",now); ud.put("u_last_communication",now);
            Map<String,Object> response=new LinkedHashMap<>(ud); response.put("u_id",str(first(ud.get("u_seq"),ud.get("u_id"))));
            if(truth(p.get("uuid"))) response.put("uuid",p.get("uuid"));
            if(reset) {
                response.put("device_uuid","RESET_"+str(first(ud.get("device_uuid"),p.get("device_uuid"),id)));
                u.put("needs_client_reset",false); u.put("last_save_time",now()); ud.put("u_save_date",now); response.put("u_save_date",now);
            }
            s.state.saveUser(u); return Result.ok(obj("user",response,"area_data",areas,"user_contents",contents));
        }
    }
    public Map<String,Object> userContents(Map<String,Object> user) { return content.contents(user); }
    public Map<String,Object> userLoadData(Map<String,Object> user) {
        Map<String,Object> contents=userContents(user), areas=areas(user), ud=object(user,"userdata"); Currency.Parsed like=Currency.parse(ud.get("u_like"));
        for(Object value:areas.values()) {
            Map<String,Object> area=map(value);
            if(like.floating()>dbl(area.get("d_Like"))) area.put("d_Like",like.floating());
            if(like.integer().compareTo(Currency.parse(first(area.get("s_Gp1"),"0")).integer())>0) area.put("s_Gp1",like.gp());
        }
        Map<String,Object> response=new LinkedHashMap<>(ud); response.put("u_id",str(first(ud.get("u_seq"),ud.get("u_id")))); response.put("u_last_communication",timestamp());
        return obj("user",response,"area_data",areas,"user_contents",contents);
    }
    public static Map<String,Object> defaultAreas() {
        Map<String,Object> areas=obj();
        for(int i=1;i<=2;i++) { int selected=i==1?1:201; areas.put(str(i),obj("u_area_num",i,"d_Candy",0.0,"d_Like",0.0,"i_UserFanCount",0,"i_UserFanGrade",1,"i_SelectedCostumeId",selected,"i_SelectedMusicId",selected,"i_SelectedGuitarId",selected,"s_TutorialList","","s_Gp1","","s_Gp2","")); }
        return areas;
    }
    private static Map<String,Object> areas(Map<String,Object> user) { if(!truth(user.get("areas"))) user.put("areas",defaultAreas()); return map(user.get("areas")); }
    private Result load(Map<String,Object> p,Map<String,Object> c) {
        Map<String,Object> u=user(p,c); if(u==null) return Result.ok(obj()); String type=str(p.get("type"));
        if(type.equals("shop")) { Object shop=content.shop(u); s.state.saveUser(u); return Result.ok(obj("user_contents",obj("user_shop",shop))); }
        if(type.equals("buff")) return Result.ok(obj("user_contents",obj("user_buff",content.activeBuffs(u))));
        return Result.ok(type.isEmpty()||type.equals("ALL") ? userLoadData(u):obj());
    }
    private Result save(Map<String,Object> p,Map<String,Object> c) {
        synchronized(s.state) {
            Map<String,Object> u=user(p,c); if(u==null) return Result.ok(obj("status","Y"));
            Map<String,Object> ud=object(u,"userdata"); String time=timestamp(); u.put("last_save_time",now()); ud.put("u_save_date",time); ud.put("u_last_communication",time);
            if(p.containsKey("user_achievement")) content.achievements(u,p.get("user_achievement"));
            String[][] merges={{"user_character","characters"},{"user_costume","costumes"},{"user_music","user_music"},{"user_guitar","user_guitar"},{"user_follower","user_follower"},{"user_prop","user_prop"}};
            for(String[] keys:merges) if(p.containsKey(keys[0])) u.put(keys[1],safeMergeItems(u.get(keys[1]),p.get(keys[0])));
            AuthFollowerSupport follower=new AuthFollowerSupport(content);
            if(p.containsKey("user_follower")) follower.sync(u);
            if(p.containsKey("user_messenger")) follower.mergeMessenger(u,p.get("user_messenger")); follower.messenger(u);
            for(String key:List.of("user_ticketcollection","user_candy_shop")) if(p.containsKey(key)) u.put(key,p.get(key));
            if(p.containsKey("user_event_point")) { u.put("user_event_point",p.get("user_event_point")); content.eventPoints(u); }
            if(p.containsKey("user_daily_mission")) content.dailyMissions(u,p.get("user_daily_mission"));
            if(p.containsKey("user_follower_quest")) follower.mergeQuest(u,p.get("user_follower_quest"));
            for(String key:List.of("user_chthird_stage","user_ch_third_stage")) if(p.containsKey(key)) { u.put("user_chthird_stage",p.get(key)); u.put("user_ch_third_stage",p.get(key)); }
            Map<String,Object> pending=map(u.remove("pending_grants"));
            if(pending.containsKey("cp")) ud.put("u_cp",lng(ud.get("u_cp"))+lng(pending.get("cp")));
            if(pending.containsKey("candy")) ud.put("u_candy",dbl(ud.get("u_candy"))+dbl(pending.get("candy")));
            if(pending.containsKey("cookies")) StateStore.addAp(u,integer(pending.get("cookies")));
            for(Object raw:list(p.get("user_info"))) { Map<String,Object> info=map(raw); for(String key:List.of("u_selected_costume_id","u_selected_music_id")) if(truth(info.get(key))) ud.put(key,info.get(key)); }
            for(Object raw:list(p.get("user_area_info"))) {
                Map<String,Object> incoming=map(raw); Object n=incoming.get("u_area_num"); if(n==null) continue;
                Map<String,Object> stored=map(object(u,"areas").computeIfAbsent(str(n),k->obj())); stored.putAll(incoming);
                Currency.Parsed server=Currency.parse(ud.get("u_like")), client=Currency.parse(incoming.get("s_Gp1"));
                boolean useServer=truth(u.get("needs_client_reset"))||truth(u.get("force_server_like"))||server.integer().compareTo(client.integer())>0;
                Currency.Parsed target=useServer?server:client; stored.put("s_Gp1",target.gp()); stored.put("d_Like",target.floating());
                if(!useServer) { ud.put("u_like",target.floating()); s.state.setLikeCurrency(str(u.get("uuid")),target.floating()); }
            }
            s.state.saveUser(u); return Result.ok(obj("status","Y"));
        }
    }
    private Result lastSave(Map<String,Object> p,Map<String,Object> c) {
        Map<String,Object> u=user(p,c); Object device=p.getOrDefault("device_uuid",""); long last=now();
        if(u!=null) { device=first(map(u.get("userdata")).get("device_uuid"),device); last=lng(first(u.get("last_save_time"),last)); }
        return Result.ok(obj("last_save_time",last,"device_uuid",device));
    }
    private Result tutorial(Map<String,Object> p,Map<String,Object> c) {
        Map<String,Object> u=user(p,c); if(u==null) return Result.ok(obj());
        if(!u.containsKey("user_tutorial")) { List<Object> initial=new ArrayList<>(); for(int i=1;i<=7;i++) initial.add(obj("i_id",i)); u.put("user_tutorial",initial); }
        List<Object> tutorials=rows(u,"user_tutorial"); Set<Integer> known=new HashSet<>(); tutorials.forEach(raw->known.add(integer(map(raw).get("i_id"))));
        for(Object raw:list(p.get("i_ids"))) { int id=integer(raw); if(id>0&&known.add(id)) tutorials.add(obj("i_id",id)); }
        s.state.saveUser(u); return Result.ok(obj("u_seq",map(u.get("userdata")).get("u_seq"),"tutorial",tutorials));
    }
    private Result subscribe(Map<String,Object> p,Map<String,Object> c) {
        String id=str(first(p.get("device_uuid"),p.get("uuid"),c.get("uuid"),str(p.getOrDefault("u_seq","")),str(p.getOrDefault("u_id",""))));
        Map<String,Object> u=s.state.getUser(id); return Result.ok(obj("u_seq",p.getOrDefault("u_seq",0),"user_subscribe_list",u==null?List.of():content.subscriptions(u)));
    }
    public static Map<String,Object> serverTime() { return obj("time",now(),"datetime",Long.parseLong(LocalDateTime.now(ZoneOffset.ofHours(9)).format(DateTimeFormatter.ofPattern("yyyyMMddHHmmss")))); }
    public Map<String,Object> defaultSettings() {
        Map<String,Object> weather=map(content.config().get("weather_festival")); String mode=str(weather.get("mode"));
        boolean snow=mode.equals("snow")||mode.isEmpty()&&content.enabled("weather_festival","snow_enabled",true), cherry=mode.equals("cherry")||mode.isEmpty()&&!snow&&content.enabled("weather_festival","cherry_blossom_enabled",false);
        String[][] values={{"shop_call_wait","2"},{"ad_cancel_delay","0"},{"force_menu_restric","true"},{"max_bundle_texutre_loading","1"},{"weather_snow",str(snow)},{"check_time_cheat","false"},{"ap_max","70"},{"ap_time","300"},{"ap_use","5"},{"character_exp","45"},{"ap_shop_id","31"},{"ap_ad_list_id","2"},{"ch_third_unlock_follower_id","5"},{"ch_third_unlock_follower_level","1"},{"ad_follower_profile_exp_persent","0.1"},{"follower_profile_bonus_percent","1"},{"spine_load_max_count","0"},{"log_flag","true"},{"weather_cherry_blossom",str(cherry)},{"active_goods_ticket_buff","true"},{"active_fan_art_costume",str(content.enabled("fan_art_costume","enabled",true))},{"pass_goods_sale_start_time","2020-01-01 00:00"},{"pass_goods_sale_end_time",content.enabled("pass_goods_sale","enabled",true)?"2999-12-31 23:59":"2020-01-01 00:00"},{"attendacne_buff_value","0.01"},{"attendacne_buff_limit_day","10000"},{"log_flag_unfinished_purchase","true"},{"jp_laws_flag","true"}};
        List<Object> settings=new ArrayList<>(); for(String[] value:values) settings.add(obj("setting_key",value[0],"setting_value",value[1]));
        return obj("status","Y","setting_list",settings);
    }
}

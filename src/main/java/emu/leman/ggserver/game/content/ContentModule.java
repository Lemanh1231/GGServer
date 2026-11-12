package emu.leman.ggserver.game.content;

import emu.leman.ggserver.Services;
import emu.leman.ggserver.net.CmdId;
import emu.leman.ggserver.net.HandlerRegistry;
import emu.leman.ggserver.net.Result;
import java.time.LocalDate;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Static content, live events, chapter-three gameplay and music encore commands. */
public final class ContentModule implements emu.leman.ggserver.game.GameModule {
    private final Services s;
    public ContentModule(Services services) { s=services; }
    @Override public String id() { return "content"; }
    @Override public void register() {
        s.registry.register(CmdId.GET_GAME_DATA_LIST,(req,ctx)->Result.ok(obj("ret",filteredGameData())));
        s.registry.register(CmdId.GET_VARIETY_STORE,(req,ctx)->Result.ok(s.gameData.varietyStore()));
        s.registry.register(CmdId.GET_SAM_SECK_LIST,(req,ctx)->Result.ok(obj("event_type","","rewardList",s.events.isMeowfestEnabled()?List.of(
            obj("i_id",1,"i_RewardType",9,"i_RewardId",10,"d_RewardQuantity",1.0),
            obj("i_id",2,"i_RewardType",3,"i_RewardId",13,"d_RewardQuantity",1.0),
            obj("i_id",3,"i_RewardType",7,"i_RewardId",1,"d_RewardQuantity",1.0)):List.of())));
        s.registry.register(CmdId.GET_SAM_SECK_REWARD,this::samseckReward);
        s.registry.register(CmdId.GET_EVENT_MAIN,this::eventMain);
        s.registry.register(CmdId.GET_EVENT_RANK,this::eventRank);
        s.registry.register(CmdId.EVENT_REWARD_LIST,(req,ctx)->eventRewardList());
        new ContentChapter(s).register();
        new ContentMusic(s).register();
    }

    public Map<String,Object> filteredGameData() { return filteredGameData(LocalDate.now().getMonthValue()); }
    public Map<String,Object> filteredGameData(int currentMonth) {
        Map<String,Object> ret=s.gameData.namedData(),cfg=s.events.snapshot();
        if(!truth(map(cfg.get("meowfest")).get("enabled"))) ret.put("samseckevent",new ArrayList<>());
        List<Object> attendance=new ArrayList<>();
        for(Object value:list(ret.get("event_list"))) {
            Map<String,Object> event=map(value);
            if(!truth(map(map(cfg.get("attendance_events")).get(str(event.get("idx")))).get("enabled"))) continue;
            event.put("b_IsActive",1);event.put("start_date","0001-01-01 00:00:00");event.put("end_date","9999-12-31 23:59:00");attendance.add(event);
        }
        ret.put("event_list",attendance);
        Map<String,Object> sp=map(cfg.get("star_pass"));boolean enabled=truth(sp.get("enabled"));int season=integer(sp.get("active_season")),originalMonth=currentMonth;
        for(Object value:list(ret.get("SubscribeList"))) {Map<String,Object> sub=map(value);if(integer(sub.get("i_id"))==season) {originalMonth=integer(first(sub.get("i_RepeatMonth"),currentMonth));break;}}
        for(Object value:list(ret.get("SubscribeList"))) {
            Map<String,Object> sub=map(value);int id=integer(sub.get("i_id")),month=integer(first(sub.get("i_RepeatMonth"),1));
            sub.put("b_IsActive",enabled&&id==season?1:0);sub.put("i_TimeLimit",1);
            sub.put("i_RepeatMonth",enabled&&id==season?currentMonth:enabled&&month==currentMonth&&id!=season?originalMonth:month);
            sub.putIfAbsent("i_StartYear",id<=5?2020:2021);sub.putIfAbsent("i_MonthGroupIndex",0);
        }
        for(Object value:list(ret.get("followerquest"))) {Map<String,Object> quest=map(value);for(int i=1;i<=3;i++)if("ADViewCount".equals(quest.get("s_ConditionType"+i)))quest.put("d_Condition"+i+"_1",0.0);}
        return ret;
    }

    private Result samseckReward(Map<String,Object> req,Map<String,Object> ctx) {
        if(!s.events.isMeowfestEnabled()) return failure(obj("step",0),"Meowfest event is closed");
        Map<String,Object> p=HandlerRegistry.payload(req),user=user(s,p,ctx);int id=integer(p.get("i_id"));
        if(user==null) return Result.ok(obj("step",Math.max(0,Math.min(3,id))));
        Map<String,Object> ud=map(user.get("userdata"));int current=Math.min(3,integer(ud.get("u_samseck_step"))),step=id>=1&&id<=3?Math.max(current,id):current;ud.put("u_samseck_step",step);
        List<Object> claimed=values(user,"claimed_samseck");
        if(id>=1&&id<=3&&claimed.stream().noneMatch(v->integer(v)==id)) {
            claimed.add(id);
            if(id==1) { if(!user.containsKey("user_guitar")) user.put("user_guitar",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1,"i_BonusLevel",0))));owned(user,"user_guitar",10,true); }
            if(id==2) { if(!user.containsKey("costumes")) user.put("costumes",new ArrayList<>(List.of(obj("i_id",1,"i_Level",1,"i_BonusLevel",0))));owned(user,"costumes",13,true); }
            if(id==3) {Map<String,Object> unit=find(rows(user,"user_unit"),1);if(unit==null)rows(user,"user_unit").add(obj("i_id",1,"i_Level",1));else unit.put("i_Level",Math.min(20,integer(first(unit.get("i_Level"),1))+1));}
        }
        s.state.saveUser(user);return Result.ok(obj("step",step));
    }
    private Result eventMain(Map<String,Object> req,Map<String,Object> ctx) {
        if(!s.events.isEventRankingEnabled()) return failure(obj(),"Event ranking is inactive");
        Map<String,Object> user=user(s,HandlerRegistry.payload(req),ctx);long score=user==null?0:score(user);
        Map<String,Object> data=s.events.getEventModeData();data.put("my_score",score);data.put("my_rank",1);return Result.ok(data);
    }
    private Result eventRank(Map<String,Object> req,Map<String,Object> ctx) {
        if(!s.events.isEventRankingEnabled()) return failure(List.of(),"Event ranking is inactive");
        Map<String,Object> p=HandlerRegistry.payload(req),user=user(s,p,ctx);String uuid=uuid(p,ctx),nick=user==null?"Guitarist":str(first(map(user.get("userdata")).get("u_nick"),"Guitarist"));long score=user==null?1000:score(user);
        List<Object> ranks=new ArrayList<>();String[] names={nick,"Mimi","Aoi","Yuna","Hana"},countries={"VN","KR","JP","US","TW"};long[] minimum={0,100,50,30,10};
        for(int i=0;i<5;i++) ranks.add(obj("u_seq",i+1,"u_nick",names[i],"u_id",i==0?(uuid.isEmpty()?"user1":uuid):"bot_"+(i+1),"u_avatar",i+1,"u_country",countries[i],"u_title",1,"rank",i+1,"score",i==0?score:Math.max(minimum[i],(long)(score*(1.0-i*.1)))));
        return Result.ok(ranks);
    }
    private Result eventRewardList() {
        if(!s.events.isEventRankingEnabled()) return failure(obj(),"Event ranking is inactive");
        return Result.ok(s.events.getEventRewardList());
    }
    private long score(Map<String,Object> user) {Map<String,Object> ud=map(user.get("userdata"));return lng(first(ud.get("u_event_point"),ud.get("u_fans"),1000));}
    static Result failure(Object data,String message) {return new Result(data,obj("code",1,"errmsg",message));}
    static String uuid(Map<String,Object> p,Map<String,Object> ctx) {return str(first(p.get("uuid"),ctx.get("uuid")));}
    static Map<String,Object> user(Services s,Map<String,Object> p,Map<String,Object> ctx) {String id=uuid(p,ctx);return id.isEmpty()?null:s.state.getUser(id);}
    static List<Object> values(Map<String,Object> user,String key) {return list(user.computeIfAbsent(key,k->new ArrayList<>()));}
    @SuppressWarnings("unchecked") static List<Map<String,Object>> rows(Map<String,Object> user,String key) {return (List<Map<String,Object>>)(List<?>)values(user,key);}
    static Map<String,Object> find(List<Map<String,Object>> rows,int id) {return rows.stream().filter(r->integer(r.get("i_id"))==id).findFirst().orElse(null);}
    static void owned(Map<String,Object> user,String key,int id,boolean bonus) {List<Map<String,Object>> list=rows(user,key);if(find(list,id)==null){Map<String,Object> row=obj("i_id",id,"i_Level",1);if(bonus)row.put("i_BonusLevel",0);list.add(row);}}
}

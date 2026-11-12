package emu.leman.ggserver.game.social;

import emu.leman.ggserver.game.economy.Currency;
import emu.leman.ggserver.database.StateStore;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;
import static emu.leman.ggserver.game.social.SocialFollowers.*;

/** Mutates a detached user snapshot; the caller persists grants and claim flags together. */
final class SocialRewards {
    private SocialRewards() {}
    static void grant(Map<String,Object> user,int type,int id,double quantity,boolean mailbox,boolean quest) {
        Map<String,Object> ud=map(user.computeIfAbsent("userdata",k->obj()));
        if(type==1 || (mailbox&&type==11)) {
            switch(id) {
                case 1 -> ud.put("u_cp",lng(ud.get("u_cp"))+(long)quantity);
                case 2 -> ud.put("u_candy",dbl(ud.get("u_candy"))+quantity);
                case 3,4 -> {
                    Object current=first(user.get("force_server_like"),ud.get("u_like"),0);
                    java.math.BigInteger total=Currency.parse(current).integer().add(Currency.parse(quantity).integer());
                    Currency.Parsed parsed=Currency.parse(total);
                    double floating=Math.min(Currency.MAX_FLOAT,Currency.parse(current).floating()+quantity);
                    ud.put("u_like",floating);
                    if(truth(user.get("force_server_like"))) user.put("force_server_like",parsed.gp());
                    Map<String,Object> areas=map(user.get("areas"));
                    for(Object value:areas.values()) if(value instanceof Map) {
                        Map<String,Object> area=map(value);
                        Currency.Parsed exact=Currency.parse(Currency.parse(first(area.get("s_Gp1"),current)).integer().add(Currency.parse(quantity).integer()));
                        area.put("d_Like",floating); area.put("s_Gp1",exact.gp());
                    }
                }
                case 8 -> ud.put("u_fans",lng(ud.get("u_fans"))+(long)quantity);
                case 11 -> StateStore.addAp(user,(int)quantity);
                default -> { }
            }
            // Reset signaling is caller-specific. SocialPosts handles its aggregate Like delta;
            // quest/profile helpers do not introduce a persisted reset. Keep pending admin flags.
            return;
        }
        if(quest && type!=6 && type!=10) return;
        if(type==11) {
            List<Object> gifts=rows(user,"user_follower_giftitem"); Map<String,Object> gift=find(gifts,"i_id",id);
            if(gift==null) gifts.add(obj("i_id",id,"i_Value",(long)quantity));
            else gift.put("i_Value",lng(gift.get("i_Value"))+(long)quantity);
        } else if(type==6 && quest) {
            List<Object> buffs=rows(user,"user_buff"); Map<String,Object> buff=find(buffs,"i_id",id);
            long now=System.currentTimeMillis()/1000, duration=(long)quantity;
            if(buff==null) buffs.add(obj("i_id",id,"i_Level",1,"i_ActiveTime",now,"i_EndTime",now+duration));
            else {
                long end=lng(buff.getOrDefault("i_EndTime",buff.get("i_ExpiredTime")));
                buff.put("i_Level",Math.max(1,integer(buff.get("i_Level")))); buff.put("i_ActiveTime",now); buff.put("i_EndTime",Math.max(now,end)+duration);
                buff.remove("i_BuffTime"); buff.remove("i_ExpiredTime");
            }
        } else if(type==10 && quest) {
            List<Object> tickets=rows(user,"user_ticketcollection"); if(find(tickets,"i_id",id)==null) tickets.add(obj("i_id",id));
        } else if(type==7) {
            List<Object> units=rows(user,"user_unit"); Map<String,Object> unit=find(units,"i_id",id);
            int add=Math.max(1,(int)quantity);
            if(unit==null) units.add(obj("i_id",id,"i_Level",Math.min(20,add)));
            else unit.put("i_Level",Math.min(20,integer(first(unit.get("i_Level"),1))+add));
        } else {
            String key=switch(type) { case 2->"user_music"; case 3->"costumes"; case 4->"user_prop"; case 5->"user_follower"; case 9->"user_guitar"; default->null; };
            if(key==null) return;
            if(type==4&&!mailbox&&!user.containsKey(key)) user.put(key,new ArrayList<>(List.of(obj("i_id",1,"i_Level",1),obj("i_id",2,"i_Level",1))));
            List<Object> items=rows(user,key); if(find(items,"i_id",id)!=null) return;
            Map<String,Object> item=obj("i_id",id,"i_Level",1);
            if(type!=4) item.put("i_BonusLevel",0);
            if(type==2) item.putAll(obj("b_EncoreBonusAppear",0,"l_EncoreBonusActivateTime",0,"i_EncoreBonusFollowerId",0,"i_ChThirdActiveTime",0));
            items.add(item); if(type==5) syncMessenger(user);
        }
    }
}

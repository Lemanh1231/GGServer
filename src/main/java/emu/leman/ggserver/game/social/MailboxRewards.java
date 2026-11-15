package emu.leman.ggserver.game.social;

import emu.leman.ggserver.game.GameData;
import java.math.BigDecimal;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Mailbox-only boundary checks; other native reward contexts deliberately keep their own semantics. */
public final class MailboxRewards {
    private MailboxRewards() {}
    public static List<Object> validate(GameData data,List<?> items,boolean trustedReceipt) {
        if(items==null) return new ArrayList<>();
        if(items.size()>100) throw new IllegalArgumentException("At most 100 reward items are allowed");
        List<Object> result=new ArrayList<>();
        for(Object raw:items) {
            if(!(raw instanceof Map)) throw new IllegalArgumentException("Each reward item must be an object");
            var item=map(raw);
            int type=wholeId(item.get("i_RewardType")),id=wholeId(item.get("i_RewardId"));
            double quantity;
            try { quantity=Double.parseDouble(str(item.get("d_RewardQuantity"))); }
            catch(RuntimeException e) { throw new IllegalArgumentException("Invalid mailbox reward quantity"); }
            boolean receipt=truth(item.get("already_granted"));
            if(receipt&&!trustedReceipt) throw new IllegalArgumentException("already_granted is reserved for internal receipts");
            if(!Double.isFinite(quantity)||quantity==0||(!receipt&&quantity<0)) throw new IllegalArgumentException("Reward quantity must be finite and positive");
            if(type==1||type==11) {
                if(!Set.of(1,2,3,4,8,11).contains(id)) throw new IllegalArgumentException("Unsupported mailbox goods reward ID");
                if(!receipt&&(id==1||id==8||id==11)) {
                    // JSON/native double quantities must remain exact before conversion to integer balances.
                    double max=id==11?Integer.MAX_VALUE:9_007_199_254_740_991d;
                    if(quantity!=Math.rint(quantity)||quantity>max) throw new IllegalArgumentException("Whole reward quantity exceeds supported range");
                }
            } else {
                int table=switch(type) {case 2->2;case 3->3;case 4->4;case 5->5;case 7->7;case 9->20;default->0;};
                if(table==0) throw new IllegalArgumentException("Unsupported mailbox reward type");
                var row=data.row(table,id);
                String active=switch(type) {case 2->"49";case 3->"48";case 4->"29";case 5->"44";case 7->"43";default->"37";};
                if(!FollowerAccess.active(row,active)) throw new IllegalArgumentException("Unknown or inactive mailbox catalog item");
                if(quantity!=Math.rint(quantity)||quantity<1||(type==7?quantity>20:quantity!=1))
                    throw new IllegalArgumentException("Unique rewards require quantity 1; unit levels require 1..20");
            }
            var normalized=obj("i_RewardType",type,"i_RewardId",id,"d_RewardQuantity",quantity);
            if(receipt) normalized.put("already_granted",true);
            result.add(normalized);
        }
        return result;
    }
    private static int wholeId(Object value) {
        try { int id=new BigDecimal(str(value)).intValueExact(); if(id>0)return id; }
        catch(RuntimeException ignored) { }
        throw new IllegalArgumentException("Reward type and ID must be positive integers");
    }
    /** Check aggregate destination capacity immediately before mutating the detached claim snapshot. */
    static void grant(Map<String,Object> user,Map<String,Object> item) {
        if(truth(item.get("already_granted"))) return;
        int type=integer(item.get("i_RewardType")),id=integer(item.get("i_RewardId")); double quantity=dbl(item.get("d_RewardQuantity"));
        if(type==1||type==11) {
            var ud=map(user.get("userdata"));
            try {
                if(id==1||id==8) Math.addExact(lng(ud.get(id==1?"u_cp":"u_fans")),(long)quantity);
                if(id==11) {
                    long current=lng(map(user.get("user_ap")).getOrDefault("i_Ap",70));
                    if(current<0||Math.addExact(current,(long)quantity)>Integer.MAX_VALUE) throw new ArithmeticException();
                }
                if(id==2&&!Double.isFinite(dbl(ud.get("u_candy"))+quantity)) throw new ArithmeticException();
            } catch(ArithmeticException e) { throw new IllegalArgumentException("Mailbox reward exceeds destination balance capacity"); }
        }
        SocialRewards.grant(user,type,id,quantity,true,false);
    }
}

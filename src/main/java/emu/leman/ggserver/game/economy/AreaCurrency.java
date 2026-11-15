package emu.leman.ggserver.game.economy;

import java.math.BigDecimal;
import java.util.*;
import static emu.leman.ggserver.util.Json.*;

/** Per-area GP1 wallets. u_like is only a legacy CH1 projection, never a merge watermark. */
public final class AreaCurrency {
    private AreaCurrency() {}
    private static Object forcedAmount(Map<String,Object> user) {
        Object forced=user.get("force_server_like");
        return forced instanceof String text&&text.matches("[0-9]+")?text:map(user.get("userdata")).get("u_like");
    }

    public static Map<String,Object> area(Map<String,Object> user,int number) {
        var areas=map(user.computeIfAbsent("areas",k->obj()));
        return map(areas.computeIfAbsent(str(number),k->obj("u_area_num",number)));
    }
    public static Currency.Parsed balance(Map<String,Object> user,int number) {
        var area=area(user,number);
        Object exact=area.get("s_Gp1");
        if(exact!=null&&!str(exact).isBlank()) return Currency.parse(exact);
        Object fallback=area.get("d_Like");
        // Old accounts without a GP string retain their legacy CH1 balance only.
        if(number==1) fallback=first(map(user.get("userdata")).get("u_like"),fallback,0);
        return Currency.parse(fallback);
    }
    public static void put(Map<String,Object> user,int number,Currency.Parsed amount) {
        var area=area(user,number);
        area.put("s_Gp1",amount.gp());area.put("d_Like",amount.floating());
        if(number==1) map(user.computeIfAbsent("userdata",k->obj())).put("u_like",amount.floating());
    }
    public static void normalize(Map<String,Object> user) {
        for(int number=1;number<=2;number++) {
            Currency.Parsed amount=balance(user,number);
            if(number==1&&truth(user.get("force_server_like"))) {
                amount=Currency.parse(forcedAmount(user));
            }
            var area=area(user,number);
            area.put("s_Gp1",amount.gp());area.put("d_Like",amount.floating());
        }
    }
    public static void setLike(Map<String,Object> user,Object amount) {
        var parsed=Currency.parse(amount);put(user,1,parsed);
        user.put("force_server_like",parsed.gp());user.put("needs_client_reset",true);
    }
    public static void addLike(Map<String,Object> user,Object delta) {
        var before=balance(user,1);var add=Currency.parse(delta);
        Object forced=user.get("force_server_like");
        if(truth(forced)) before=Currency.parse(forcedAmount(user));
        var total=Currency.parse(before.integer().add(add.integer()));
        // Keep historical sub-unit projections for rewards; native GP remains integral.
        var legacy=Currency.parse(map(user.get("userdata")).get("u_like"));
        double floating=Math.min(Currency.MAX_FLOAT,(legacy.integer().equals(before.integer())?legacy.floating():before.floating())+add.floating());
        put(user,1,new Currency.Parsed(total.integer(),floating,total.gp(),total.formatted()));
        if(forced instanceof String text&&text.matches("[0-9]+")) user.put("force_server_like",total.gp());
    }
    /** Validate before any snapshot merges; permissive Currency.parse is not an input validator. */
    public static void validateSave(Object rows) {
        if(rows==null) return;
        if(!(rows instanceof List<?> values)) throw new IllegalArgumentException("Invalid area snapshot");
        Set<Integer> seen=new HashSet<>();
        for(Object raw:values) {
            if(!(raw instanceof Map<?,?>)) throw new IllegalArgumentException("Invalid area snapshot");
            var incoming=map(raw);String n=str(incoming.get("u_area_num"));
            if(!n.equals("1")&&!n.equals("2")) throw new IllegalArgumentException("Invalid area number");
            if(!seen.add(Integer.parseInt(n))) throw new IllegalArgumentException("Duplicate area number");
            if(incoming.containsKey("s_Gp1")) {
                String gp=str(incoming.get("s_Gp1")).strip();
                if(gp.length()>512||!gp.matches("[0-9]+(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?[a-zA-Z]*"))
                    throw new IllegalArgumentException("Invalid GP1 balance");
                // Suffix shorthand is retained for legacy clients/tools, but must be recognized.
                var match=java.util.regex.Pattern.compile("^([0-9]+(?:\\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)([a-zA-Z]*)$").matcher(gp);
                if(!match.matches()) throw new IllegalArgumentException("Invalid GP1 balance");
                BigDecimal exact;
                try { exact=new BigDecimal(match.group(1)).scaleByPowerOfTen(Currency.unitStrToExp(match.group(2))); }
                catch(RuntimeException invalid) { throw new IllegalArgumentException("Invalid GP1 balance"); }
                if(exact.compareTo(Currency.MAX_DECIMAL)>0) throw new IllegalArgumentException("GP1 balance exceeds client range");
            }
            if(incoming.containsKey("d_Like")) {
                double value;
                try {value=Double.parseDouble(str(incoming.get("d_Like")));}
                catch(RuntimeException invalid) {throw new IllegalArgumentException("Invalid Like projection");}
                if(!Double.isFinite(value)||value<0||value>Currency.MAX_FLOAT) throw new IllegalArgumentException("Invalid Like projection");
            }
        }
    }
}

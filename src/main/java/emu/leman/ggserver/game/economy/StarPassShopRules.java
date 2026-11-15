package emu.leman.ggserver.game.economy;

import java.util.Map;
import static emu.leman.ggserver.util.Json.*;

/** Shared manual Sale policy for client projections and authoritative purchases. */
public final class StarPassShopRules {
    private StarPassShopRules() {}

    public static boolean merchandise(int id) {
        return id>=2001&&id<=2013 || id>=3001&&id<=3013;
    }

    public static boolean saleOpen(Map<String,Object> events) {
        return Boolean.TRUE.equals(map(events.get("pass_goods_sale")).get("enabled"));
    }

    /** Preserve the existing season-three promotion, including its normal alias. */
    public static long effectivePrice(int id,long catalogPrice) {
        return id==2003||id==3003 ? 50 : catalogPrice;
    }

    public static void project(Map<String,Object> product,Map<String,Object> events) {
        int id=integer(product.get("i_id"));
        if(!merchandise(id))return;
        if(!saleOpen(events))product.put("b_IsActive",0);
        if(id==2003||id==3003) {
            product.put("i_SellValue",effectivePrice(id,lng(product.get("i_SellValue"))));
            // These schema fields are prices, not titles or discount descriptions.
            for(String key:java.util.List.of("s_StorePrice_AOS","s_StorePrice_IOS",
                    "s_Kor_StorePrice_AOS","s_Kor_StorePrice_IOS")) {
                if(product.containsKey(key))product.put(key,"50");
            }
        }
    }
}

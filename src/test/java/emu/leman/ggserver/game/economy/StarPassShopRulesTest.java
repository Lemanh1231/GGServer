package emu.leman.ggserver.game.economy;

import java.util.*;
import org.junit.jupiter.api.Test;
import static emu.leman.ggserver.util.Json.*;
import static org.junit.jupiter.api.Assertions.*;

class StarPassShopRulesTest {
    @Test void onlyKnownMerchandiseAliasesAreSaleProducts() {
        for(int season=1;season<=13;season++) {
            assertTrue(StarPassShopRules.merchandise(2000+season));
            assertTrue(StarPassShopRules.merchandise(3000+season));
        }
        for(int id:List.of(3,1003,2000,2014,2500,3000,3014,10012))assertFalse(StarPassShopRules.merchandise(id));
    }
    @Test void absentAndNonBooleanSaleFlagsAreClosed() {
        assertFalse(StarPassShopRules.saleOpen(obj()));
        for(Object enabled:List.of(false,"true",1))assertFalse(StarPassShopRules.saleOpen(obj("pass_goods_sale",obj("enabled",enabled))));
        assertTrue(StarPassShopRules.saleOpen(obj("pass_goods_sale",obj("enabled",true))));
    }
    @Test void projectionDoesNotRewriteOtherProductsOrOverrideCatalogDeactivation() {
        var open=obj("pass_goods_sale",obj("enabled",true));
        var ordinary=obj("i_id",3,"i_SellValue",123,"b_IsActive",1,"s_StorePrice_AOS","123");
        String before=stringify(ordinary);StarPassShopRules.project(ordinary,obj());assertEquals(before,stringify(ordinary));
        var otherSeason=obj("i_id",3001,"i_SellValue",80,"b_IsActive",0,"s_StorePrice_AOS","80");
        before=stringify(otherSeason);StarPassShopRules.project(otherSeason,open);assertEquals(before,stringify(otherSeason));
        assertEquals(80,StarPassShopRules.effectivePrice(3001,80));
        assertEquals(50,StarPassShopRules.effectivePrice(2003,120));
        assertEquals(50,StarPassShopRules.effectivePrice(3003,50));
    }
    @Test void titleDescriptionAndSaleScheduleAreNotPriceFields() {
        var product=obj("i_id",2003,"i_SellValue",120,"b_IsActive",1,
                "s_StorePrice_AOS","120","s_Description_VI","120 notes",
                "s_Title_EN","Season 3","s_StartTime","2020-01-01 00:00:00",
                "s_EndTime","2999-12-31 23:59:00");
        StarPassShopRules.project(product,obj("pass_goods_sale",obj("enabled",true)));
        assertEquals(50,lng(product.get("i_SellValue")));assertEquals("50",product.get("s_StorePrice_AOS"));
        assertEquals("120 notes",product.get("s_Description_VI"));assertEquals("Season 3",product.get("s_Title_EN"));
        assertEquals("2020-01-01 00:00:00",product.get("s_StartTime"));
        assertEquals("2999-12-31 23:59:00",product.get("s_EndTime"));
    }
}

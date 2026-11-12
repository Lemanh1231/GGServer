package emu.leman.ggserver.game.economy;

import org.junit.jupiter.api.Test;
import java.math.BigDecimal;
import java.math.BigInteger;
import static org.junit.jupiter.api.Assertions.*;

class CurrencyTest {
    @Test void usesGameUnitsRatherThanMetricAbbreviations() {
        assertEquals("42877000000000000000000", Currency.parse("42.877G").gp());
        assertEquals("42.877G", Currency.format("42.877G"));
        assertEquals(new BigInteger("10500"), Currency.parse("10.5A").integer());
        assertEquals(39, Currency.unitStrToExp("m"));
        assertEquals("AA", Currency.getUnitName(26));
        assertEquals("CW", Currency.getUnitName(100));
        assertEquals("CW", Currency.getUnitName(999));
        assertEquals(101, Currency.UNITS.size());
    }

    @Test void preservesPrecisionClampsAndHandlesMalformedValues() {
        String exact = "123456789012345678901234567890123456789";
        assertEquals(exact, Currency.parse(exact).gp());
        assertEquals(exact, Currency.parse(new BigDecimal(exact)).gp());
        assertEquals("1.234D", Currency.format("1234567890123"));
        assertEquals("1.23A", Currency.format(1234, 2));
        assertEquals("123", Currency.parse("123.99").gp());
        assertEquals("999.999CW", Currency.parse("1e999").formatted());
        assertEquals(Currency.MAX_DECIMAL.toBigInteger(), Currency.parse("1e999").integer());
        assertTrue(Double.isFinite(Currency.parse("1e999").floating()));
        for (Object value : new Object[]{"-1", "no currency", "100ZZ", Double.NaN, Double.POSITIVE_INFINITY}) {
            assertEquals("0", Currency.parse(value).gp());
        }
        assertEquals("0", Currency.parse(null).gp());
        assertEquals("1234", Currency.parse("$1,234").gp());
    }
}

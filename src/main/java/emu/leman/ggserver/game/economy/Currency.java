package emu.leman.ggserver.game.economy;

import java.math.BigDecimal;
import java.math.BigInteger;
import java.util.*;
import java.util.regex.*;

/** Exact game short-scale conversion. SQL/wire doubles and GP integer strings stay separate. */
public final class Currency {
    public static final int MAX_UNITS_COUNT = 101;
    public static final int MAX_SAFE_DIGITS = 306;
    public static final double MAX_FLOAT = 9.99999e305;
    public static final BigDecimal MAX_DECIMAL = new BigDecimal("9.99999e305");
    public static final List<String> UNITS;
    public static final List<String> GAME_UNITS;
    public static final Map<String,Integer> UNIT_TO_EXP;
    private static final Pattern NUMBER = Pattern.compile("^([+-]?\\d+(?:\\.\\d+)?(?:[eE][+-]?\\d+)?)\\s*([a-zA-Z]*)$");
    private static final Parsed ZERO = new Parsed(BigInteger.ZERO, 0.0, "0", "0");

    static {
        List<String> units = new ArrayList<>();
        for (char c = 'A'; c <= 'Z'; c++) units.add(String.valueOf(c));
        for (char a = 'A'; a <= 'Z' && units.size() < MAX_UNITS_COUNT; a++) {
            for (char b = 'A'; b <= 'Z' && units.size() < MAX_UNITS_COUNT; b++) units.add("" + a + b);
        }
        UNITS = List.copyOf(units);
        GAME_UNITS = UNITS;
        Map<String,Integer> exponents = new LinkedHashMap<>();
        for (int i = 0; i < units.size(); i++) {
            exponents.put(units.get(i), 3 * (i + 1));
            exponents.put(units.get(i).toLowerCase(Locale.ROOT), 3 * (i + 1));
        }
        UNIT_TO_EXP = Collections.unmodifiableMap(exponents);
    }

    private Currency() {}

    public record Parsed(BigInteger integer, double floating, String gp, String formatted) {}

    public static String getUnitName(int index) {
        return index < 0 ? "" : UNITS.get(Math.min(index, UNITS.size() - 1));
    }

    public static int unitStrToExp(String unit) {
        if (unit == null || unit.isEmpty()) return 0;
        Integer exponent = UNIT_TO_EXP.get(unit.strip().toUpperCase(Locale.ROOT));
        if (exponent == null) throw new IllegalArgumentException("Unknown game currency unit: " + unit);
        return exponent;
    }

    public static Parsed parse(Object value) {
        if (value == null) return ZERO;
        String text = value.toString().strip();
        if (text.isEmpty() || text.equals("0")) return ZERO;
        try {
            Matcher match = NUMBER.matcher(text);
            BigDecimal decimal;
            if (match.matches()) {
                decimal = new BigDecimal(match.group(1)).scaleByPowerOfTen(unitStrToExp(match.group(2)));
            } else {
                String digits = text.replaceAll("[^\\d.]", "");
                decimal = digits.isEmpty() ? BigDecimal.ZERO : new BigDecimal(digits);
            }
            decimal = decimal.max(BigDecimal.ZERO).min(MAX_DECIMAL);
            BigInteger integer = decimal.toBigInteger();
            String gp = integer.toString();
            return new Parsed(integer, Math.min(MAX_FLOAT, decimal.doubleValue()), gp, formatInteger(gp, 3));
        } catch (IllegalArgumentException | ArithmeticException e) {
            return ZERO;
        }
    }

    public static Parsed parseCurrency(Object value) { return parse(value); }
    public static String format(Object value) { return format(value, 3); }
    public static String format(Object value, int decimals) {
        if (decimals < 0) throw new IllegalArgumentException("Negative decimals");
        return formatInteger(parse(value).gp(), decimals);
    }
    public static String formatCurrency(Object value) { return format(value); }
    public static String formatCurrency(Object value, int decimals) { return format(value, decimals); }

    private static String formatInteger(String gp, int decimals) {
        if (gp.length() <= 3) return gp;
        int integerLength = (gp.length() - 1) % 3 + 1;
        String fraction = gp.substring(integerLength, Math.min(gp.length(), integerLength + decimals));
        fraction += "0".repeat(decimals - fraction.length());
        return gp.substring(0, integerLength) + "." + fraction + getUnitName((gp.length() - 1) / 3 - 1);
    }
}

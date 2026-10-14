"""Guitar Girl currency converter & big-number safety module.

Dumps from IL2CPP (ShortScaleString & GgGameCoreMainManagerSGT):
  Single letter:
    A = 10^3 (Thousand)
    B = 10^6 (Million)
    C = 10^9 (Billion)
    D = 10^12 (Trillion)
    E = 10^15 (Quadrillion)
    F = 10^18 (Quintillion)  [near uint64 max = 1.84467e19]
    G = 10^21 (Sextillion)   [exceeds uint64]
    H = 10^24 (Septillion)
    I = 10^27 (Octillion)
    J = 10^30 (Nonillion)
    K = 10^33 (Decillion)
    ...
    Z = 10^78
  Double letter:
    AA = 10^81
    AB = 10^84
    ...
    ZZ = 10^2109 (702 units total in ShortScaleString)

Safety limits:
  1. Client C# BigInteger: unlimited digits, but ShortScaleString has 702 units up to ZZ (10^2109).
     If unit_index >= 702, ShortScaleString throws IndexOutOfRangeException.
  2. Client Thrift & ObscuredDouble: d_Like and u_like are IEEE 754 float64 (double).
     double.MaxValue = 1.7976931348623157e+308 (~10^308, unit CX/CY).
     Values > 1.79e308 overflow to Infinity in double.
  3. Python sqlite3: binding Python int > 2^63-1 to SQL parameter crashes with:
     OverflowError: Python int too large to convert to SQLite INTEGER.
     Must always bind float or TEXT! For u_like (REAL), bind float(val).
  4. Thrift protocol:
     s_Gp1, s_Gp2: STRING (exact integer string).
     d_Like: DOUBLE (IEEE 754 float, <= 1.79e308).
     u_like: DOUBLE (IEEE 754 float, <= 1.79e308).
"""
import re
import sys
from decimal import Decimal, InvalidOperation

# Max IEEE 754 float64
MAX_FLOAT = 1.7976931348623157e308
MAX_DECIMAL = Decimal('1.7976931348623157e308')

# Build the 702 units matching ShortScaleString
UNITS = []
for i in range(26):
    UNITS.append(chr(ord('A') + i))
for i in range(26):
    for j in range(26):
        UNITS.append(chr(ord('A') + i) + chr(ord('A') + j))

GAME_UNITS = UNITS

# Unit to power-of-10 exponent lookup
# Follows the game's native alphabet scale:
# A=10^3, B=10^6, C=10^9, D=10^12, E=10^15, F=10^18, G=10^21, H=10^24 ...
UNIT_TO_EXP = {}
for idx, u in enumerate(UNITS):
    exp = 3 * (idx + 1)
    UNIT_TO_EXP[u] = exp
    UNIT_TO_EXP[u.lower()] = exp


def get_unit_name(idx):
    """Return unit name for 0-indexed unit (0 -> 'A', 6 -> 'G', 7 -> 'H', 26 -> 'AA', 701 -> 'ZZ')."""
    if 0 <= idx < len(UNITS):
        return UNITS[idx]
    if idx < 0:
        return ''
    return UNITS[-1]


def unit_str_to_exp(u):
    """Convert a unit string (e.g. 'A', 'G', 'H', 'AA', 'ZZ', 'k', 'm') to power of 10."""
    if not u:
        return 0
    u_clean = u.strip()
    if u_clean in UNIT_TO_EXP:
        return UNIT_TO_EXP[u_clean]
    u_upper = u_clean.upper()
    if u_upper in UNIT_TO_EXP:
        return UNIT_TO_EXP[u_upper]
    raise ValueError(f"Unknown game currency unit: {u}")


def parse_currency(val):
    """Parse any currency representation into safe primitives.

    Supports:
      - Integers / floats / Decimals: 1000, 42877000000000000000000, 1e24
      - String with game units: '42.877G', '100H', '10.5A', '1.25AA', '100ZZ'
      - Standard metric shortcuts: '10k', '5m', '2b', '1t'

    Returns:
      (int_val, float_val, gp_str, formatted)
      - int_val: Python int (exact arbitrary precision integer)
      - float_val: Python float (IEEE 754 safe, clamped to MAX_FLOAT)
      - gp_str: Decimal string for s_Gp1 / s_Gp2 in Thrift
      - formatted: Game UI string, e.g. '42.877G'
    """
    if val is None:
        return 0, 0.0, '0', '0'

    if isinstance(val, (int, float, Decimal)):
        val_str = str(val).strip()
    else:
        val_str = str(val).strip()

    if not val_str or val_str == '0':
        return 0, 0.0, '0', '0'

    # Match number + optional unit suffix
    m = re.match(r'^([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([a-zA-Z]*)$', val_str)
    if not m:
        # Fallback: strip any non-digit/dot characters
        digits = re.sub(r'[^\d.]', '', val_str)
        try:
            dec = Decimal(digits) if digits else Decimal(0)
        except InvalidOperation:
            return 0, 0.0, '0', '0'
    else:
        num_str = m.group(1)
        unit_str = m.group(2)
        try:
            exp = unit_str_to_exp(unit_str) if unit_str else 0
            dec = Decimal(num_str) * (Decimal(10) ** exp)
        except (ValueError, InvalidOperation):
            return 0, 0.0, '0', '0'

    # Clamp bounds
    if dec < 0:
        dec = Decimal(0)
    if dec > MAX_DECIMAL:
        dec = MAX_DECIMAL

    int_val = int(dec)
    try:
        float_val = float(dec)
    except OverflowError:
        float_val = MAX_FLOAT

    if float_val > MAX_FLOAT:
        float_val = MAX_FLOAT

    gp_str = str(int_val)

    # Format into game unit string matching ShortScaleString.parseBigInteger
    if len(gp_str) <= 3:
        formatted = gp_str
    else:
        digits = len(gp_str)
        unit_idx = (digits - 1) // 3
        unit_name = get_unit_name(unit_idx - 1)
        int_len = ((digits - 1) % 3) + 1
        int_part = gp_str[:int_len]
        dec_part = gp_str[int_len:int_len + 3].ljust(3, '0')
        formatted = f"{int_part}.{dec_part}{unit_name}"

    return int_val, float_val, gp_str, formatted


def format_currency(val, decimals=3):
    """Format any currency value to game string representation (e.g. 42.877G, 100.000H).

    Matches client ShortScaleString.parseBigInteger exactly:
      s = val.ToString();
      len = s.Length;
      unit_index = (len - 1) / 3;
      int_len = ((len - 1) % 3) + 1;
      format: '{0}.{1}{2}' (int_part, dec_part, unit_str)
    """
    if val is None:
        return '0'
    try:
        if isinstance(val, (int, float, Decimal)):
            s = str(int(val))
        else:
            s_val = str(val).strip()
            if not s_val:
                return '0'
            # If scientific notation or unit string, parse first
            if any(c in s_val for c in ('e', 'E', '.')) or re.search(r'[a-zA-Z]', s_val):
                _, _, s, _ = parse_currency(s_val)
            else:
                s = str(int(s_val))
    except Exception:
        return '0'

    if len(s) <= 3:
        return s

    digits = len(s)
    unit_idx = (digits - 1) // 3
    if unit_idx < 1:
        return s

    unit_name = get_unit_name(unit_idx - 1)
    int_len = ((digits - 1) % 3) + 1
    int_part = s[:int_len]
    dec_part = s[int_len:int_len + decimals].ljust(decimals, '0')
    return f"{int_part}.{dec_part}{unit_name}"

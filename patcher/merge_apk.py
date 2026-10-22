#!/usr/bin/env python3
"""Merge the 3 Guitar Girl split APKs into ONE universal APK installable with `adb install`.

Why this exists
---------------
The app ships as an Android App Bundle split set:
  - com.neowiz.game.guitargirl.apk  : base (manifest, dex, resources.arsc, res/)
  - config.arm64_v8a.apk            : ABI split, carries lib/arm64-v8a/*.so
  - base_assets.apk                 : install-time asset-pack, carries assets/ (Unity data + il2cpp metadata)

The base manifest declares  android:requiredSplitTypes="base__abi"  so the package
manager refuses a lone base APK with INSTALL_FAILED_MISSING_SPLIT. We therefore:

  1. Surgically EMPTY that attribute inside the *binary* AndroidManifest.xml (AXML) — no
     resource recompilation (apktool/aapt choke on the new 0x0101064e attribute), so
     resources.arsc / dex stay byte-identical.
  2. Build one zip = base entries (minus old signatures) with the patched manifest, plus
     lib/* from the abi split, plus assets/* from the asset-pack (carrying the already
     URL-patched global-metadata.dat).

Sign the result with one key (uber-apk-signer, done by patch_apk.py) and `adb install` it.

AXML reference: a START_ELEMENT chunk lists 20-byte attributes; an attribute's android
resource id is resourceMap[nameIndex]. We match by id (0x0101064e requiredSplitTypes,
0x0101064f splitTypes) instead of by fragile string names.
"""
import struct, zipfile, os

# Android resource ids (stable across builds; the names in the string pool are not).
ID_REQUIRED_SPLIT_TYPES = 0x0101064e
ID_SPLIT_TYPES          = 0x0101064f

# AXML chunk types
RES_STRING_POOL      = 0x0001
RES_XML_RESOURCE_MAP = 0x0180
RES_XML_START_ELEMENT = 0x0102

UTF8_FLAG = 1 << 8

# ARM64 binary patches for lib/arm64-v8a/libil2cpp.so:
# Disables offline restrictions and PmangPlus account requirements for:
# 1) Push notifications toggles in Settings (m_goNotifications_Online_KR)
# 2) CP (Chocolate) free/paid breakdown in Settings (m_goGoods_Online)
# 3) Star Pass Goods Shop (UI 19) & Detail Popup (UI 20) live slot interaction & refresh
LIBIL2CPP_PATCHES = [
    # (offset, expected_original_bytes, patched_replacement_bytes, description)
    (0x1E13D04, b'\xe0\x08\x00\x37', b'\x1f\x20\x03\xd5', 'SetupNotifications: isOffline tbnz -> NOP'),
    (0x1E13D1C, b'\x21\x08\x00\x54', b'\x1f\x20\x03\xd5', 'SetupNotifications: authType b.ne -> NOP'),
    (0x1E137D0, b'\x80\x01\x00\x37', b'\x1f\x20\x03\xd5', 'ClickDay: isOffline tbnz -> NOP'),
    (0x1E137E8, b'\xc1\x00\x00\x54', b'\x1f\x20\x03\xd5', 'ClickDay: authType b.ne -> NOP'),
    (0x1E18774, b'\x80\x01\x00\x37', b'\x1f\x20\x03\xd5', 'ClickNight: isOffline tbnz -> NOP'),
    (0x1E1878C, b'\xc1\x00\x00\x54', b'\x1f\x20\x03\xd5', 'ClickNight: authType b.ne -> NOP'),
    (0x1E1526C, b'\x80\x01\x00\x37', b'\x1f\x20\x03\xd5', 'ClickGO: isOffline tbnz -> NOP'),
    (0x1E15284, b'\xc1\x00\x00\x54', b'\x1f\x20\x03\xd5', 'ClickGO: authType b.ne -> NOP'),
    (0x1ED4904, b'\x00\x01\x00\x36', b'\x08\x00\x00\x14', 'SetGoods: isOffline tbz -> b #0x1ed8924'),
    (0x1ED493C, b'\xe1\x17\x9f\x1a', b'\x21\x00\x80\x52', 'SetGoods: cset w1, eq -> mov w1, #1'),
    (0x1ED4950, b'\xa1\x00\x00\x54', b'\x1f\x20\x03\xd5', 'SetGoods: authType b.ne -> NOP'),

    # 3a) Replace GgUIIngamePassGoodsShop.뀁뀈뀎뀌뀊뀊뀃뀏뀅뀌뀅 (208 bytes) with:
    #     - Live Slot click handler (0x20D7FE0..0x20D804C): opens Popup 20 if unsubscribed, refreshes if subscribed
    #     - Post-purchase auto-refresh hook (0x20D8050..0x20D8094): refreshes Live Slot when Detail closes
    #     - 6 NOPs padding (0x20D8098..0x20D80AC)
    (
        0x20D3FE0,
        bytes.fromhex(
            'fe0f1ff8210100b4283c40f9e80000b40811423968000034fe0741f804000014'
            'fe0741f8c0035fd6a6ade497fe0f1ef8f44f01a9730e01f0f4f60090688a5839'
            '942e43f928010037e0f60090002c43f9fdace497c0f600b0006c46f9faace497'
            '28008052688a1839800240f908e440b94800003548ade497c0e88452e1031faa'
            '046ef097f30300aae0e88452e1031faa006ef097f40300aae0031faaf4170394'
            '600100b4c8f600b0e10313aae20314aa086d46f9f44f41a9e3031faae5031faa'
            '040140f9fe0742f83e9bef177dade497'
        ),
        bytes.fromhex(
            # Live slot click handler (112 bytes)
            'fe0f1ef8f44f01a9e10200b4f40301aa803e40f9e00000b4e1031faada46f497'
            '80000034e00314aa752bfc970e000014933a40f9930100b4e0031faa0c180394'
            '200100b48102805222008052e3031faa3699ef97800000b4e10313aae2031faa'
            '8a1a0394f44f41a9fe0742f8c0035fd6'
            # Post-purchase auto-refresh hook (72 bytes)
            'e0031faafe170394e00000b4610280526998ef97800000b4002c40f9400000b4'
            '5b2bfc97685e40f9c80000b4002140f9011540f9020d40f9fe4fc1a840001fd6'
            'fe4fc1a8c0035fd6'
            # 6 NOPs padding (24 bytes)
            '1f2003d51f2003d51f2003d51f2003d51f2003d51f2003d5'
        ),
        'PassGoodsShop: Live Slot click handler + Detail closed auto-refresh hook',
    ),
    # 3b) Detail Popup OnClosed hook call: jump to 0x20D8050
    (
        0x2199E64,
        b'\x68\x5e\x40\xf9',
        b'\x7b\xe8\xfc\x17',
        'PassGoodsDetail: OnClosed hook -> b #0x20d8050',
    ),
    # 3c) Detail Popup active item pricing getter fix: ldr x0, [x19, #0x28]
    (
        0x226230C,
        b'\x60\x12\x40\xf9',
        b'\x60\x16\x40\xf9',
        'PassGoodsDetail: use m_cItem_Active (0x28) instead of m_cItem (0x20)',
    ),
]


def patch_libil2cpp_so(so_bytes):
    """Patch libil2cpp.so to bypass offline restrictions on notifications and goods (CP).
    Returns (new_bytes, patched_count). Byte length is strictly preserved."""
    buf = bytearray(so_bytes)
    patched = 0
    for offset, old, new, desc in LIBIL2CPP_PATCHES:
        if offset + len(old) <= len(buf):
            chunk = buf[offset:offset + len(old)]
            if chunk == old:
                buf[offset:offset + len(new)] = new
                patched += 1
    return bytes(buf), patched



def _read_string_pool(data, off):
    """Return (list_of_strings,) for the string pool chunk at `off`."""
    _type, header_size, size = struct.unpack_from('<HHI', data, off)
    string_count, style_count, flags, strings_start, styles_start = struct.unpack_from('<IIIII', data, off + 8)
    utf8 = bool(flags & UTF8_FLAG)
    offsets = [struct.unpack_from('<I', data, off + 28 + i * 4)[0] for i in range(string_count)]
    base = off + strings_start
    out = []
    for o in offsets:
        p = base + o
        if utf8:
            # two length fields (chars, then bytes); high-bit means 2-byte length
            n = data[p]; p += 1
            if n & 0x80:
                n = ((n & 0x7f) << 8) | data[p]; p += 1   # char length (unused)
            m = data[p]; p += 1
            if m & 0x80:
                m = ((m & 0x7f) << 8) | data[p]; p += 1   # byte length
            out.append(data[p:p + m].decode('utf-8', 'replace'))
        else:
            n = struct.unpack_from('<H', data, p)[0]; p += 2
            if n & 0x8000:
                n = ((n & 0x7fff) << 16) | struct.unpack_from('<H', data, p)[0]; p += 2
            out.append(data[p:p + n * 2].decode('utf-16-le', 'replace'))
    return out


def _read_resource_map(data, off):
    _type, header_size, size = struct.unpack_from('<HHI', data, off)
    count = (size - 8) // 4
    return [struct.unpack_from('<I', data, off + 8 + i * 4)[0] for i in range(count)]


def patch_manifest_axml(data):
    """Empty android:requiredSplitTypes and disable PlayGamesInitProvider (android:enabled="false")
    in a binary AndroidManifest.xml. Returns (new_bytes, changed_count). Same length as input (in-place edits)."""
    buf = bytearray(data)
    # file header: type(2) headerSize(2) size(4); chunks follow at offset 8
    resmap = []
    strings = []
    empty_raw = empty_data = None   # string-pool index of "" (reused from splitTypes="")
    # First pass over top-level chunks to grab string pool + resource map.
    p = 8
    end = len(buf)
    chunks = []
    while p + 8 <= end:
        ctype, hsize, csize = struct.unpack_from('<HHI', buf, p)
        if csize < 8:
            break
        chunks.append((ctype, p, csize))
        if ctype == RES_STRING_POOL:
            strings = _read_string_pool(buf, p)
        elif ctype == RES_XML_RESOURCE_MAP:
            resmap = _read_resource_map(buf, p)
        p += csize

    def attr_id(name_idx):
        return resmap[name_idx] if name_idx < len(resmap) else 0

    # Pass 1: find the empty-string indices from any splitTypes="" attribute.
    for ctype, coff, csize in chunks:
        if ctype != RES_XML_START_ELEMENT:
            continue
        attr_start = coff + 16 + struct.unpack_from('<H', buf, coff + 24)[0]
        attr_size  = struct.unpack_from('<H', buf, coff + 26)[0]
        attr_count = struct.unpack_from('<H', buf, coff + 28)[0]
        for i in range(attr_count):
            ab = attr_start + i * attr_size
            if attr_id(struct.unpack_from('<I', buf, ab + 4)[0]) == ID_SPLIT_TYPES:
                empty_raw  = struct.unpack_from('<I', buf, ab + 8)[0]    # rawValue index ("")
                empty_data = struct.unpack_from('<I', buf, ab + 16)[0]   # typed string data ("")
                break
        if empty_data is not None:
            break

    # Pass 2: repoint requiredSplitTypes to the empty string.
    changed = 0
    for ctype, coff, csize in chunks:
        if ctype != RES_XML_START_ELEMENT:
            continue
        attr_start = coff + 16 + struct.unpack_from('<H', buf, coff + 24)[0]
        attr_size  = struct.unpack_from('<H', buf, coff + 26)[0]
        attr_count = struct.unpack_from('<H', buf, coff + 28)[0]
        for i in range(attr_count):
            ab = attr_start + i * attr_size
            if attr_id(struct.unpack_from('<I', buf, ab + 4)[0]) != ID_REQUIRED_SPLIT_TYPES:
                continue
            if empty_data is None:
                raise SystemExit("requiredSplitTypes present but no empty string to point it at")
            struct.pack_into('<I', buf, ab + 8, empty_raw)             # rawValue -> ""
            struct.pack_into('<BBI', buf, ab + 15, 0x03, 0, empty_data)  # dataType=STRING, data -> ""
            changed += 1

    # Pass 3: disable Google Play Games v2 PlayGamesInitProvider (android:enabled="false")
    # This completely disables auto sign-in popup on startup without needing to dismiss Google Play.
    ID_ENABLED = 0x0101000e
    ID_INIT_ORDER = 0x0101001a
    enabled_name_idx = resmap.index(ID_ENABLED) if ID_ENABLED in resmap else None

    if enabled_name_idx is not None and strings:
        for ctype, coff, csize in chunks:
            if ctype != RES_XML_START_ELEMENT:
                continue
            tag_idx = struct.unpack_from('<I', buf, coff + 20)[0]
            tag_name = strings[tag_idx] if tag_idx < len(strings) else ''
            if tag_name != 'provider':
                continue
            attr_start = coff + 16 + struct.unpack_from('<H', buf, coff + 24)[0]
            attr_size  = struct.unpack_from('<H', buf, coff + 26)[0]
            attr_count = struct.unpack_from('<H', buf, coff + 28)[0]
            is_playgames = False
            init_order_offset = None
            for i in range(attr_count):
                ab = attr_start + i * attr_size
                name_idx = struct.unpack_from('<I', buf, ab + 4)[0]
                raw_idx = struct.unpack_from('<I', buf, ab + 8)[0]
                raw_str = strings[raw_idx] if (raw_idx < len(strings) and raw_idx != 0xffffffff) else ''
                dtype = buf[ab + 15]
                data_val = struct.unpack_from('<I', buf, ab + 16)[0]
                data_str = strings[data_val] if (dtype == 0x03 and data_val < len(strings)) else ''
                res_id = attr_id(name_idx)
                if 'PlayGamesInitProvider' in raw_str or 'PlayGamesInitProvider' in data_str:
                    is_playgames = True
                if res_id == ID_INIT_ORDER:
                    init_order_offset = ab
            if is_playgames and init_order_offset is not None:
                # Replace initOrder attribute with android:enabled="false"
                # name_idx -> enabled_name_idx
                struct.pack_into('<I', buf, init_order_offset + 4, enabled_name_idx)
                # raw_idx -> 0xffffffff
                struct.pack_into('<I', buf, init_order_offset + 8, 0xffffffff)
                # typed value: size(2)=8, res0(1)=0, dataType(1)=0x12 (boolean), data(4)=0 (false)
                struct.pack_into('<HBB I', buf, init_order_offset + 12, 8, 0, 0x12, 0)
                changed += 1

    # Pass 4: Empty com.google.android.gms.games.APP_ID
    app_id_idx = strings.index('com.google.android.gms.games.APP_ID') if 'com.google.android.gms.games.APP_ID' in strings else None
    if app_id_idx is not None and empty_data is not None:
        for ctype, coff, csize in chunks:
            if ctype != RES_XML_START_ELEMENT: continue
            tag_idx = struct.unpack_from('<I', buf, coff + 20)[0]
            tag_name = strings[tag_idx] if tag_idx < len(strings) else ''
            if tag_name != 'meta-data': continue
            attr_start = coff + 16 + struct.unpack_from('<H', buf, coff + 24)[0]
            attr_size  = struct.unpack_from('<H', buf, coff + 26)[0]
            attr_count = struct.unpack_from('<H', buf, coff + 28)[0]
            for i in range(attr_count):
                ab = attr_start + i * attr_size
                name_idx = struct.unpack_from('<I', buf, ab + 4)[0]
                res_id = attr_id(name_idx)
                dtype = buf[ab + 15]
                data_val = struct.unpack_from('<I', buf, ab + 16)[0]
                if res_id == 0x01010003 and dtype == 0x03 and data_val == app_id_idx:
                    struct.pack_into('<I', buf, ab + 8, empty_raw)
                    struct.pack_into('<I', buf, ab + 16, empty_data)
                    changed += 1

    # Pass 5: Redirect GooglePlayAuth activity to GamePlayLogin
    game_login_idx = strings.index('com.pmangplus.ui.activity.login.GamePlayLogin') if 'com.pmangplus.ui.activity.login.GamePlayLogin' in strings else None
    if game_login_idx is not None:
        for ctype, coff, csize in chunks:
            if ctype != RES_XML_START_ELEMENT: continue
            tag_idx = struct.unpack_from('<I', buf, coff + 20)[0]
            tag_name = strings[tag_idx] if tag_idx < len(strings) else ''
            if tag_name != 'activity': continue
            attr_start = coff + 16 + struct.unpack_from('<H', buf, coff + 24)[0]
            attr_size  = struct.unpack_from('<H', buf, coff + 26)[0]
            attr_count = struct.unpack_from('<H', buf, coff + 28)[0]
            for i in range(attr_count):
                ab = attr_start + i * attr_size
                name_idx = struct.unpack_from('<I', buf, ab + 4)[0]
                res_id = attr_id(name_idx)
                dtype = buf[ab + 15]
                data_val = struct.unpack_from('<I', buf, ab + 16)[0]
                if res_id == 0x01010003 and dtype == 0x03:
                    act_name = strings[data_val] if data_val < len(strings) else ''
                    if act_name == 'com.pmangplus.ui.activity.firebase.GooglePlayAuth':
                        struct.pack_into('<I', buf, ab + 8, game_login_idx)
                        struct.pack_into('<I', buf, ab + 16, game_login_idx)
                        changed += 1

    return bytes(buf), changed


def merge(apk_dir, out_apk, base='com.neowiz.game.guitargirl.apk',
          abi='config.arm64_v8a.apk', assets='base_assets.apk', verbose=True):
    """Write a single universal APK to out_apk from the 3 splits in apk_dir."""
    base_p   = os.path.join(apk_dir, base)
    abi_p    = os.path.join(apk_dir, abi)
    assets_p = os.path.join(apk_dir, assets)

    with zipfile.ZipFile(base_p) as z:
        manifest = z.read('AndroidManifest.xml')
    patched, n = patch_manifest_axml(manifest)
    if n == 0 and verbose:
        print("  [merge] note: requiredSplitTypes not found (already standalone?)")
    elif verbose:
        print(f"  [merge] emptied android:requiredSplitTypes in {n} place(s)")

    seen = set()
    with zipfile.ZipFile(out_apk, 'w') as zo:
        def copy_entry(zi, src):
            if zi.filename in seen:
                return
            seen.add(zi.filename)
            zo.writestr(zi, src.read(zi.filename), compress_type=zi.compress_type)

        # 1) base: everything except old signatures and the manifest (we inject the patched one)
        with zipfile.ZipFile(base_p) as zb:
            for zi in zb.infolist():
                nm = zi.filename
                if nm == 'AndroidManifest.xml' or nm.startswith('META-INF/'):
                    continue
                copy_entry(zi, zb)
            mi = zipfile.ZipInfo('AndroidManifest.xml')
            mi.compress_type = zipfile.ZIP_STORED
            zo.writestr(mi, patched)
            seen.add('AndroidManifest.xml')

        # 2) abi split: native libs
        nlibs = 0
        with zipfile.ZipFile(abi_p) as za:
            for zi in za.infolist():
                if zi.filename.startswith('lib/'):
                    if zi.filename in seen:
                        continue
                    seen.add(zi.filename)
                    data = za.read(zi.filename)
                    if zi.filename.endswith('libil2cpp.so'):
                        data, n_patched = patch_libil2cpp_so(data)
                        if verbose and n_patched > 0:
                            print(f"  [merge] patched libil2cpp.so at {n_patched} location(s)")
                    zo.writestr(zi, data, compress_type=zi.compress_type)
                    nlibs += 1

        # 3) asset-pack: assets (carries the URL-patched global-metadata.dat)
        nassets = 0
        with zipfile.ZipFile(assets_p) as zs:
            for zi in zs.infolist():
                if zi.filename.startswith('assets/'):
                    copy_entry(zi, zs); nassets += 1

    if verbose:
        print(f"  [merge] wrote {out_apk}: +{nlibs} lib, +{nassets} asset entries")
    return out_apk


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description="Merge 3 Guitar Girl split APKs into one universal APK.")
    ap.add_argument('apk_dir', help="dir containing the 3 split apks (base_assets.apk already URL-patched)")
    ap.add_argument('-o', '--out', required=True)
    a = ap.parse_args()
    merge(a.apk_dir, a.out)

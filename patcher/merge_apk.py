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
    """Empty android:requiredSplitTypes in a binary AndroidManifest.xml so the APK installs
    standalone. Returns (new_bytes, changed_count). Same length as input (in-place edits)."""
    buf = bytearray(data)
    # file header: type(2) headerSize(2) size(4); chunks follow at offset 8
    resmap = []
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
        if ctype == RES_XML_RESOURCE_MAP:
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
                    copy_entry(zi, za); nlibs += 1

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

#!/usr/bin/env python3
"""Build redirected + re-signed split APKs for Guitar Girl.

1. Patch the server-URL string literals inside base_assets.apk's global-metadata.dat
   (STORED entry, same size -> overwritten in place + CRC fixed; no 364MB rebuild).
2. Re-sign ALL splits with one fresh key (uber-apk-signer; v1+v2+v3) so BlueStacks accepts them.
3. Print the adb install-multiple command.

Usage:
  python3 patch_apk.py --apk-dir <orig apk dir> --target http://192.168.1.50:8080 --out <out dir>
"""
import argparse, os, shutil, struct, subprocess, sys, tempfile, zipfile, binascii
import patch_metadata

META_ENTRY = "assets/bin/Data/Managed/Metadata/global-metadata.dat"
SPLITS = ["com.neowiz.game.guitargirl.apk", "config.arm64_v8a.apk", "base_assets.apk"]
HERE = os.path.dirname(os.path.abspath(__file__))
JAR = os.path.join(HERE, "uber-apk-signer.jar")


def find_local_entry(apk_path, name):
    """Return (data_offset, comp_size, local_header_offset) for a STORED zip entry."""
    with zipfile.ZipFile(apk_path) as z:
        zi = z.getinfo(name)
        if zi.compress_type != zipfile.ZIP_STORED:
            raise SystemExit(f"{name} is not STORED (method={zi.compress_type}); in-place patch unsupported.")
        lho = zi.header_offset
        comp_size = zi.compress_size
    with open(apk_path, 'rb') as f:
        f.seek(lho)
        sig = f.read(4)
        assert sig == b'PK\x03\x04', "bad local header"
        f.seek(lho + 26)
        namelen, extralen = struct.unpack('<HH', f.read(4))
        data_off = lho + 30 + namelen + extralen
    return data_off, comp_size, lho


def overwrite_stored_entry(apk_path, name, new_bytes):
    """Overwrite a STORED entry's bytes in place (same length) and fix CRC in local + central dir."""
    data_off, comp_size, lho = find_local_entry(apk_path, name)
    if len(new_bytes) != comp_size:
        raise SystemExit(f"size mismatch: new {len(new_bytes)} != stored {comp_size}")
    new_crc = binascii.crc32(new_bytes) & 0xffffffff
    with open(apk_path, 'r+b') as f:
        f.seek(data_off)
        f.write(new_bytes)
        # local header CRC @ lho+14
        f.seek(lho + 14)
        f.write(struct.pack('<I', new_crc))
    # central directory CRC: scan EOCD -> central dir, find this name
    _fix_central_crc(apk_path, name, new_crc)


def _fix_central_crc(apk_path, name, new_crc):
    name_b = name.encode()
    with open(apk_path, 'r+b') as f:
        f.seek(0, 2); size = f.tell()
        # find EOCD (scan last 64KB+22)
        tail = min(size, 65557)
        f.seek(size - tail); blob = f.read(tail)
        i = blob.rfind(b'PK\x05\x06')
        if i < 0:
            raise SystemExit("EOCD not found")
        cd_off = struct.unpack('<I', blob[i+16:i+20])[0]
        cd_size = struct.unpack('<I', blob[i+12:i+16])[0]
        f.seek(cd_off); cd = f.read(cd_size)
        p = 0
        while p < len(cd) - 4 and cd[p:p+4] == b'PK\x01\x02':
            nlen, elen, clen = struct.unpack('<HHH', cd[p+28:p+34])
            ename = cd[p+46:p+46+nlen]
            if ename == name_b:
                f.seek(cd_off + p + 16)
                f.write(struct.pack('<I', new_crc))
                return
            p += 46 + nlen + elen + clen
    raise SystemExit("central dir entry not found for " + name)


def replace_entry_grow(apk_path, name, new_bytes):
    """Replace a zip entry whose size changed, via the `zip` CLI (STORED, preserves others)."""
    td = tempfile.mkdtemp()
    try:
        fp = os.path.join(td, name)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        with open(fp, 'wb') as f:
            f.write(new_bytes)
        subprocess.run(['zip', '-0', '-X', '-q', os.path.abspath(apk_path), name], cwd=td, check=True)
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apk-dir', required=True, help="dir with the 3 split apks")
    ap.add_argument('--target', required=True, help="local base url e.g. http://192.168.1.50:8080")
    ap.add_argument('--out', required=True)
    ap.add_argument('--ks', default=os.path.join(HERE, 'gg.keystore'))
    ap.add_argument('--no-sign', action='store_true')
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    # 1) extract + patch metadata
    base_in = os.path.join(a.apk_dir, 'base_assets.apk')
    base_out = os.path.join(a.out, 'base_assets.apk')
    print(f"[1/3] copying base_assets.apk -> {base_out}")
    shutil.copy2(base_in, base_out)
    with zipfile.ZipFile(base_in) as z:
        meta = z.read(META_ENTRY)
    print(f"[1/3] patching metadata URLs -> {a.target}")
    patched, rep = patch_metadata.patch(meta, a.target)
    if not rep:
        raise SystemExit("no URLs patched; aborting")
    for url, new, mode, ol, nl in rep:
        print(f"        [{mode:7}] {url} -> {new}")
    if len(patched) == len(meta):
        print(f"[1/3] size unchanged -> overwriting STORED entry in place (CRC fixed)")
        overwrite_stored_entry(base_out, META_ENTRY, bytes(patched))
    else:
        print(f"[1/3] size changed ({len(meta)} -> {len(patched)}) -> rebuilding zip entry")
        replace_entry_grow(base_out, META_ENTRY, bytes(patched))

    # copy the other splits
    for s in SPLITS:
        if s == 'base_assets.apk':
            continue
        shutil.copy2(os.path.join(a.apk_dir, s), os.path.join(a.out, s))
    print(f"[2/3] copied {len(SPLITS)} splits to {a.out}")

    if a.no_sign:
        print("--no-sign: skipping signing. Sign all 3 with ONE key then adb install-multiple.")
        return

    # 2) keystore
    if not os.path.exists(a.ks):
        print(f"[3/3] creating keystore {a.ks}")
        subprocess.run(['keytool', '-genkeypair', '-v', '-keystore', a.ks, '-alias', 'gg',
                        '-keyalg', 'RSA', '-keysize', '2048', '-validity', '10000',
                        '-storepass', 'android', '-keypass', 'android', '-dname', 'CN=gg'], check=True)

    # 3) sign all splits with uber-apk-signer (zipalign + v1/v2/v3)
    apks = [os.path.join(a.out, s) for s in SPLITS]
    print("[3/3] signing all splits with one key (uber-apk-signer)")
    cmd = ['java', '-jar', JAR, '--apks', *apks, '--ks', a.ks, '--ksAlias', 'gg',
           '--ksPass', 'android', '--ksKeyPass', 'android', '--overwrite', '--allowResign']
    subprocess.run(cmd, check=True)

    print("\nDONE. Install on BlueStacks (uninstall original first):")
    print("  adb uninstall com.neowiz.game.guitargirl")
    print("  adb install-multiple \\\n    " + " \\\n    ".join(apks))


if __name__ == '__main__':
    main()

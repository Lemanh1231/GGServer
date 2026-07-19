#!/usr/bin/env python3
"""Patch IL2CPP global-metadata.dat server-URL string literals to a custom base URL.

String literals are length-prefixed: a stringLiteral table of (u32 length, u32 dataIndex) entries
pointing into the stringLiteralData heap.

- If the replacement fits (<= original length) it is overwritten IN PLACE (file size unchanged).
- If it is LONGER (e.g. an external https domain), the new bytes are APPENDED to the end of the
  stringLiteralData heap; the file grows, so every metadata section that lies after the heap has its
  header offset bumped and the heap's size is increased. The literal's table entry is repointed to
  the appended bytes. This lifts the length limit entirely (any scheme/host/length works).

Only the 31 header (offset,size) pairs are absolute; everything else uses indices or heap-relative
offsets, so shifting sections + fixing the header keeps the metadata structurally valid.
"""
import struct, re

# Full URL literals the client uses; the scheme+host[:port] is swapped to the target, path preserved.
TARGET_URLS = [
    "https://game.gtgl.pmang.cloud",
    "https://game.gtgl-dev2.pmang.cloud",
    "https://game.gtgl-dq.pmang.cloud",
    "https://game.gtgl-review.pmang.cloud",
    "https://dl.gtgl.pmang.cloud",
    "https://dl.gtgl-dev.pmang.cloud",
    "https://dl.gtgl-dq.pmang.cloud",
    "https://dl.gtgl-review.pmang.cloud",
    "https://global.neonapi.com/api",
    "https://qa-global.neonapi.com/api",
    "https://www.neonapi.com/api",
    "https://qa-www.neonapi.com/api",
]

_HOST_RE = re.compile(r'^(https?://)([^/]+)(.*)$')
_N_HEADER_PAIRS = 31   # IL2CPP v31 header: magic+version + 31*(offset,size) = 0x100 bytes


def _split(url):
    m = _HOST_RE.match(url)
    return (m.group(1), m.group(2), m.group(3)) if m else (None, None, None)


def _header(data):
    magic, ver = struct.unpack_from('<Ii', data, 0)
    assert magic == 0xFAB11BAF, "not global-metadata.dat (magic %08x)" % magic
    sl_off, sl_sz, sld_off, sld_sz = struct.unpack_from('<IIII', data, 8)
    return ver, sl_off, sl_sz, sld_off, sld_sz


def patch(data, target_base, verbose=True):
    """target_base: 'https://host[:port]' or 'http://ip:port'. Returns (patched bytearray, report)."""
    ver, sl_off, sl_sz, sld_off, sld_sz = _header(data)
    buf = bytearray(data)
    target_base = target_base.rstrip('/')
    n = sl_sz // 8
    entries = [(i,) + struct.unpack_from('<II', data, sl_off + i * 8) for i in range(n)]  # (i, length, dataIndex)

    inplace, appends, report = [], [], []
    for url in TARGET_URLS:
        _, _, path = _split(url)
        repl = (target_base + (path or '')).encode('ascii')
        ub = url.encode('ascii')
        hit = next(((i, ln, di) for (i, ln, di) in entries
                    if ln == len(ub) and bytes(data[sld_off + di: sld_off + di + ln]) == ub), None)
        if not hit:
            continue
        i, length, di = hit
        if len(repl) <= length:
            inplace.append((i, sld_off + di, repl, length))
        else:
            appends.append((i, repl, sld_off + di, length))   # also zero the old bytes
        report.append((url, repl.decode(), 'inplace' if len(repl) <= length else 'append', length, len(repl)))

    # in-place overwrites (no size change)
    for (i, ad, repl, length) in inplace:
        buf[ad: ad + len(repl)] = repl
        for z in range(ad + len(repl), ad + length):
            buf[z] = 0
        struct.pack_into('<I', buf, sl_off + i * 8, len(repl))

    # appended (longer) literals -> grow stringLiteralData heap
    if appends:
        insertion = sld_off + sld_sz                 # current end of heap = start of next section
        blob = bytearray()
        for (i, repl, old_ad, old_len) in appends:
            for z in range(old_ad, old_ad + old_len):   # erase orphaned original bytes
                buf[z] = 0
            new_di = sld_sz + len(blob)               # dataIndex relative to sld_off
            struct.pack_into('<II', buf, sl_off + i * 8, len(repl), new_di)
            blob += repl
        delta = len(blob)
        buf = buf[:insertion] + blob + buf[insertion:]
        # bump every section offset that is at/after the insertion point
        for idx in range(_N_HEADER_PAIRS):
            poff = 8 + idx * 8
            off = struct.unpack_from('<I', buf, poff)[0]
            if off >= insertion:
                struct.pack_into('<I', buf, poff, off + delta)
        # grow the stringLiteralData size field (pair index 1 -> size at byte 8+1*8+4 = 20)
        struct.pack_into('<I', buf, 8 + 1 * 8 + 4, sld_sz + delta)

    return buf, report


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description="Patch GG metadata server URLs to a custom base URL.")
    ap.add_argument('metadata')
    ap.add_argument('target', help="base URL, e.g. https://gg.example.com  or  http://192.168.1.50:8080")
    ap.add_argument('-o', '--out', required=True)
    a = ap.parse_args()
    buf, rep = patch(open(a.metadata, 'rb').read(), a.target)
    open(a.out, 'wb').write(buf)
    print(f"patched {len(rep)} URL literal(s):")
    for url, new, mode, ol, nl in rep:
        print(f"  [{mode:7}] {url:58} -> {new}  ({ol}->{nl})")
    print(f"wrote {a.out}  (size {len(open(a.metadata,'rb').read())} -> {len(buf)})")
    if not rep:
        print("WARNING: no target URLs found.")

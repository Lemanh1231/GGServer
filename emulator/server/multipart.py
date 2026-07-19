"""Minimal multipart/form-data + urlencoded parser for Unity WWWForm POST bodies."""
import re
from urllib.parse import parse_qs


def parse(content_type, body):
    """Return dict {field_name: value(str)}. Values decoded utf-8 (errors ignored)."""
    if not content_type:
        return _urlencoded(body)
    ct = content_type.lower()
    if 'multipart/form-data' in ct:
        m = re.search(r'boundary=([^;]+)', content_type)
        if not m:
            return {}
        boundary = m.group(1).strip().strip('"')
        return _multipart(body, boundary.encode())
    if 'application/x-www-form-urlencoded' in ct:
        return _urlencoded(body)
    # unknown: try multipart sniff then urlencoded
    if body[:2] == b'--':
        bm = re.match(rb'--([^\r\n]+)\r\n', body)
        if bm:
            return _multipart(body, bm.group(1))
    return _urlencoded(body)


def _urlencoded(body):
    try:
        q = parse_qs(body.decode('utf-8', 'ignore'), keep_blank_values=True)
    except Exception:
        return {}
    return {k: v[0] for k, v in q.items()}


def _multipart(body, boundary):
    out = {}
    delim = b'--' + boundary
    parts = body.split(delim)
    for part in parts:
        part = part.strip(b'\r\n')
        if not part or part == b'--':
            continue
        if b'\r\n\r\n' not in part:
            continue
        head, _, data = part.partition(b'\r\n\r\n')
        hm = re.search(rb'name="([^"]*)"', head)
        if not hm:
            continue
        name = hm.group(1).decode('utf-8', 'ignore')
        out[name] = data.rstrip(b'\r\n')
    # decode text values
    res = {}
    for k, v in out.items():
        if isinstance(v, (bytes, bytearray)):
            try:
                res[k] = v.decode('utf-8')
            except UnicodeDecodeError:
                res[k] = v
        else:
            res[k] = v
    return res

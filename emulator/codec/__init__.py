"""Full wire codec for Guitar Girl:  body = Base64( BZip2( ThriftBinary(struct) ) ).

Confirmed from libil2cpp.so disassembly of NetworkManagerSGT.Serialize/Deserialize:
  Serialize:   struct.Write(TBinaryProtocol) -> bytes -> BZip2.Compress(blockSize=3) -> ToBase64String
  Deserialize: [optional prefix strip] -> FromBase64String -> BZip2InputStream -> TBinaryProtocol.Read
"""
import os, json, bz2, base64
from . import thrift

_SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'schema', 'schema.json')
SCHEMA = json.load(open(_SCHEMA_PATH, encoding='utf-8'))
thrift.load_schema(SCHEMA)


# ---------- low level transform ----------
def decode_body(b64_text):
    """base64 text -> raw thrift bytes (after bunzip2)."""
    if isinstance(b64_text, str):
        b64_text = b64_text.strip()
    comp = base64.b64decode(b64_text)
    raw = bz2.decompress(comp)
    return raw

def encode_body(thrift_bytes):
    """raw thrift bytes -> base64( bzip2(bytes) ).  blockSize 3 matches the client."""
    comp = bz2.compress(thrift_bytes, 3)
    return base64.b64encode(comp).decode('ascii')


# ---------- struct <-> dict ----------
def _ids_to_names(struct_name, idmap):
    """Recursively convert {field_id: value} -> {name: value} using schema."""
    spec = SCHEMA.get(struct_name)
    if not spec:
        return idmap
    byid = {f['id']: f for f in spec['fields']}
    out = {}
    for fid, val in idmap.items():
        f = byid.get(fid)
        if not f:
            out[fid] = val; continue
        out[f['name']] = _convert_val(f, val)
    return out

def _convert_val(f, val):
    t = f['type']
    if t == 'STRUCT' and isinstance(val, dict):
        return _ids_to_names(f.get('struct'), val)
    if t == 'LIST' and isinstance(val, list):
        es = f.get('elem') or {}
        if es.get('type') == 'STRUCT':
            return [_ids_to_names(es.get('struct'), x) if isinstance(x, dict) else x for x in val]
        return val
    if t == 'MAP' and isinstance(val, dict):
        vs = f.get('val') or {}
        if vs.get('type') == 'STRUCT':
            return {k:(_ids_to_names(vs.get('struct'), x) if isinstance(x, dict) else x) for k,x in val.items()}
        return val
    return val


def decode_request(b64_text, struct_name=None):
    """Decode a request body. Returns (named_dict_or_idmap, raw_idmap)."""
    raw = decode_body(b64_text)
    idmap = thrift.read_struct(raw)
    named = _ids_to_names(struct_name, idmap) if struct_name else idmap
    return named, idmap

def encode_response(struct_name, data):
    """data: dict keyed by field name (or id). Returns base64 body string."""
    tb = thrift.write_struct(data, struct_name)
    return encode_body(tb)


def schema_for(name):
    return SCHEMA.get(name)

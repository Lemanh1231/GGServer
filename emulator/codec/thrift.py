"""Apache Thrift TBinaryProtocol (non-strict) reader/writer in pure Python.

The game serializes a single Thrift struct (no message envelope) via TBinaryProtocol,
then BZip2-compresses, then Base64-encodes. This module implements just TBinaryProtocol.

Reading is fully self-describing (no schema needed) -> returns {field_id: value}.
Writing is schema-driven -> takes a dict and a schema field list.
"""
import struct

# Thrift type ids
STOP=0; VOID=1; BOOL=2; BYTE=3; DOUBLE=4; I16=6; I32=8; I64=10
STRING=11; STRUCT=12; MAP=13; SET=14; LIST=15
NAME2ID={'BOOL':BOOL,'BYTE':BYTE,'DOUBLE':DOUBLE,'I16':I16,'I32':I32,'I64':I64,
         'STRING':STRING,'STRUCT':STRUCT,'MAP':MAP,'SET':SET,'LIST':LIST,'VOID':VOID}
ID2NAME={v:k for k,v in NAME2ID.items()}


class Reader:
    def __init__(self, buf):
        self.b=buf; self.p=0
    def _r(self,n):
        v=self.b[self.p:self.p+n]; self.p+=n
        if len(v)!=n: raise EOFError("thrift underrun")
        return v
    def byte(self): return self._r(1)[0]
    def sbyte(self):
        v=self.byte(); return v-256 if v>=128 else v
    def i16(self): return struct.unpack('>h', self._r(2))[0]
    def i32(self): return struct.unpack('>i', self._r(4))[0]
    def i64(self): return struct.unpack('>q', self._r(8))[0]
    def dbl(self): return struct.unpack('>d', self._r(8))[0]
    def string(self):
        n=self.i32()
        raw=self._r(n) if n>0 else b''
        try: return raw.decode('utf-8')
        except UnicodeDecodeError: return raw  # binary
    def bool(self): return self.byte()!=0

    def value(self, t):
        if t==BOOL: return self.bool()
        if t==BYTE: return self.sbyte()
        if t==DOUBLE: return self.dbl()
        if t==I16: return self.i16()
        if t==I32: return self.i32()
        if t==I64: return self.i64()
        if t==STRING: return self.string()
        if t==STRUCT: return self.struct()
        if t==LIST or t==SET:
            et=self.byte(); n=self.i32()
            return [self.value(et) for _ in range(n)]
        if t==MAP:
            kt=self.byte(); vt=self.byte(); n=self.i32()
            return {self.value(kt): self.value(vt) for _ in range(n)}
        raise ValueError("bad type %d"%t)

    def struct(self):
        """Read a struct -> {field_id: value}. Self-describing."""
        out={}
        while True:
            t=self.byte()
            if t==STOP: break
            fid=self.i16()
            out[fid]=self.value(t)
        return out


def _safe_int(v, default=0):
    if v is None: return default
    try: return int(v)
    except (ValueError, TypeError, OverflowError): return default

def _safe_float(v, default=0.0):
    if v is None: return default
    try:
        fv = float(v)
        if fv > 1.7976931348623157e308: return 1.7976931348623157e308
        if fv < -1.7976931348623157e308: return -1.7976931348623157e308
        return fv
    except (ValueError, TypeError, OverflowError): return default


class Writer:
    def __init__(self): self.o=bytearray()
    def byte(self,v): self.o.append(_safe_int(v) & 0xff)
    def i16(self,v):
        iv = _safe_int(v)
        if iv > 32767: iv = 32767
        elif iv < -32768: iv = -32768
        self.o+=struct.pack('>h', iv)
    def i32(self,v):
        iv = _safe_int(v)
        if iv > 2147483647: iv = 2147483647
        elif iv < -2147483648: iv = -2147483648
        self.o+=struct.pack('>i', iv)
    def i64(self,v):
        iv = _safe_int(v)
        if iv > 9223372036854775807: iv = 9223372036854775807
        elif iv < -9223372036854775808: iv = -9223372036854775808
        self.o+=struct.pack('>q', iv)
    def dbl(self,v): self.o+=struct.pack('>d', _safe_float(v))
    def string(self,v):
        if v is None:
            raw = b''
        elif isinstance(v, (bytes, bytearray)):
            raw = bytes(v)
        elif isinstance(v, str):
            raw = v.encode('utf-8')
        else:
            raw = str(v).encode('utf-8')
        self.i32(len(raw)); self.o+=raw
    def field_begin(self,t,fid): self.byte(t); self.i16(fid)
    def field_stop(self): self.byte(STOP)

    def value(self, t, v, fieldspec=None):
        if t==BOOL: self.byte(1 if v else 0)
        elif t==BYTE: self.byte(_safe_int(v) & 0xff)
        elif t==DOUBLE: self.dbl(_safe_float(v))
        elif t==I16: self.i16(_safe_int(v))
        elif t==I32: self.i32(_safe_int(v))
        elif t==I64: self.i64(_safe_int(v))
        elif t==STRING: self.string(v)
        elif t==STRUCT:
            sub=(fieldspec or {}).get('struct')
            self.struct(v if isinstance(v, dict) else {}, sub)
        elif t in (LIST,SET):
            es=(fieldspec or {}).get('elem') or {'type':'STRING'}
            et=NAME2ID.get(es.get('type', 'STRING'), STRING)
            if v is None:
                items = []
            elif isinstance(v, (list, tuple, set)):
                items = list(v)
            elif isinstance(v, dict):
                items = [v] if v else []
            else:
                items = [v]
            self.byte(et); self.i32(len(items))
            for it in items: self.value(et, it, es)
        elif t==MAP:
            ks=(fieldspec or {}).get('key') or {'type':'I32'}
            vs=(fieldspec or {}).get('val') or {'type':'STRING'}
            kt=NAME2ID.get(ks.get('type', 'I32'), I32)
            vt=NAME2ID.get(vs.get('type', 'STRING'), STRING)
            if not isinstance(v, dict): v = {}
            self.byte(kt); self.byte(vt); self.i32(len(v))
            for k,val in v.items():
                self.value(kt, k, ks); self.value(vt, val, vs)
        else:
            raise ValueError("cant write type %d"%t)

    def struct(self, data, struct_name=None):
        """data: dict keyed by field NAME or id. schema looked up via SCHEMA registry."""
        if not isinstance(data, dict):
            self.field_stop()
            return
        spec = SCHEMA.get(struct_name) if struct_name else None
        if spec is None:
            # no schema: data must be {id:(typename,value)} or already-id dict of plain values -> can't infer types
            # Expect caller to provide schema; fall back to writing by guessing from python type.
            for fid, val in data.items():
                try: ifid = int(fid)
                except (ValueError, TypeError): continue
                t=_guess_type(val); self.field_begin(t, ifid); self.value(t, val)
            self.field_stop(); return
        for f in spec['fields']:
            name=f['name']; fid=f['id']; t=NAME2ID.get(f['type'], STRING)
            if name in data: val=data[name]
            elif fid in data: val=data[fid]
            else: continue  # field not set -> omit (Thrift optional)
            if val is None: continue
            self.field_begin(t, fid)
            self.value(t, val, f)
        self.field_stop()


def _guess_type(v):
    if isinstance(v,bool): return BOOL
    if isinstance(v,int): return I64
    if isinstance(v,float): return DOUBLE
    if isinstance(v,str) or isinstance(v,(bytes,bytearray)): return STRING
    if isinstance(v,list): return LIST
    if isinstance(v,dict): return STRUCT
    return STRING


# ---- schema registry (loaded by codec.__init__) ----
SCHEMA={}

def load_schema(d): SCHEMA.clear(); SCHEMA.update(d)

def read_struct(buf):
    return Reader(buf).struct()

def write_struct(data, struct_name):
    w=Writer(); w.struct(data, struct_name); return bytes(w.o)

"""Command identification + generic response-envelope construction."""
import base64, time, datetime
import codec

SCHEMA = codec.SCHEMA

# simple-name -> [full names]
_BY_SIMPLE = {}
for _full, _v in SCHEMA.items():
    _BY_SIMPLE.setdefault(_v['name'], []).append(_full)

# commands = request envelopes (have 'call' and 'data', not a *Return)
def _is_request_env(v):
    fns = {f['name'] for f in v['fields']}
    return 'call' in fns and 'data' in fns and not v['name'].endswith('Return')

COMMANDS = {full: v for full, v in SCHEMA.items() if _is_request_env(v)}

# special command -> Return DTO mapping (where it's not <cmd>Return)
_SPECIAL_RETURN = {
    'Request': 'initReturn',
    'facebookUserJoin': 'userJoinReturn',
}

def return_dto_for(cmd_full):
    """Resolve the response-envelope DTO full name for a request command."""
    v = SCHEMA.get(cmd_full)
    if not v:
        return None
    ns, name = v['ns'], v['name']
    cand = f"{ns}.{name}Return"
    if cand in SCHEMA:
        return cand
    sp = _SPECIAL_RETURN.get(name)
    if sp:
        full = f"{ns}.{sp}"
        if full in SCHEMA:
            return full
        # search any namespace
        for c in _BY_SIMPLE.get(sp, []):
            return c
    # fallback: a DTO named <base>Return where base derives from req payload
    return None

def retdata_dto_for(cmd_full):
    """The RetDataInfo struct that goes in the Return.data field (authoritative from schema)."""
    rdto = return_dto_for(cmd_full)
    if not rdto:
        return None
    for f in SCHEMA[rdto]['fields']:
        if f['name'] == 'data':
            return f.get('struct')
    return None


def resolve_command(form_fields, idmap=None):
    """Identify the request command full-name. The client sends a plaintext form field
    `call` = command name (confirmed from the reference proxy). Fall back to any field
    value matching a known request-envelope name."""
    # 1) the dedicated `call` form field (authoritative)
    call = form_fields.get('call')
    if isinstance(call, str) and call:
        for full in _BY_SIMPLE.get(call, []):
            if full in COMMANDS:
                return full
        if call in COMMANDS:
            return call
    # 2) any form field value that exactly matches a known request-envelope simple name
    for k, val in form_fields.items():
        if isinstance(val, str) and val in _BY_SIMPLE:
            for full in _BY_SIMPLE[val]:
                if full in COMMANDS:
                    return full
    # 3) fully-qualified value
    for k, val in form_fields.items():
        if isinstance(val, str) and val in COMMANDS:
            return val
    return None


# The client carries the encoded message in the `tapsonic_data` form field
# ("TapSonic" = the original Neowiz title). Confirmed from the reference proxy.
MESSAGE_FIELDS = ('tapsonic_data', 'msg', 'data')

def find_message_field(form_fields):
    """Return (field_name, b64_text) for the field carrying base64(BZip2(...))."""
    # 1) known field names first
    for name in MESSAGE_FIELDS:
        v = form_fields.get(name)
        if isinstance(v, str) and len(v) >= 8:
            return name, v
    # 2) auto-detect: any base64 value that decodes to bzip2 (BZh magic)
    best = None
    for k, val in form_fields.items():
        if not isinstance(val, str) or len(val) < 8:
            continue
        try:
            dec = base64.b64decode(val, validate=False)
        except Exception:
            continue
        if dec[:3] == b'BZh':   # bzip2 magic
            return k, val
        if best is None or len(val) > len(best[1]):
            best = (k, val)
    return best if best else (None, None)


# ---------- response envelope ----------
def now_times():
    t = int(time.time())
    dt = int(datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S'))
    return t, dt

def success_error():
    return {'code': 0, 'errmsg': ''}

def empty_maintenance():
    return {'code': 0}

def build_return(cmd_full, ret_data, *, call=None, category='', error=None):
    """Construct the Return-envelope dict (BaseGameResponse layout), matching the reference:
      1 error, 2 server_time(timestamp), 3 mode(=category), 4 call, 5 data(omit on error), 6 maintenance({}).
    `error` is a {code,errmsg} dict; on non-zero code, `data` is omitted."""
    rdto = return_dto_for(cmd_full)
    if not rdto:
        return None, None
    spec = SCHEMA[rdto]
    names = {f['name'] for f in spec['fields']}
    error = error or {'code': 0, 'errmsg': ''}
    t, dt = now_times()
    env = {}
    if 'error' in names:       env['error'] = {'code': error.get('code', 0), 'errmsg': error.get('errmsg', '')}
    if 'server_time' in names: env['server_time'] = {'time': t, 'datetime': dt}
    if 'mode' in names:        env['mode'] = category or SCHEMA[cmd_full]['ns']
    if 'call' in names:        env['call'] = call or SCHEMA[cmd_full]['name']
    if 'data' in names and error.get('code', 0) == 0:
        env['data'] = ret_data if ret_data is not None else {}
    if 'maintenance' in names: env['maintenance'] = {}      # empty struct = no maintenance
    return rdto, env

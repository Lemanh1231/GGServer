"""Guitar Girl emulator HTTP(S) server (single port).

Routes:
  POST /{category}/{call}/en/   game Thrift RPC (call form field selects handler)
  POST /api/...                 NeonAPI/PmangPlus auth (JSON)
  GET  /AssetBundles/...        CDN asset bundles
Wire: request `tapsonic_data` = base64(BZip2(Thrift(envelope))); response = same transform.

Every request is logged to captures/ for analysis.
"""
import os, sys, json, time, traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import codec
from server import multipart, dispatch, handlers, state, auth

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAP_DIR = os.path.join(BASE, 'captures')
GAMEDATA_DIR = os.path.join(BASE, 'gamedata')
CDN_DIR = os.path.join(BASE, 'cdn_files')
os.makedirs(CAP_DIR, exist_ok=True)

CONFIG = {
    # Full base URL advertised to the client in init's game_url/cdn_url. Set this to the SAME value
    # you patched into the APK (e.g. https://gg.example.com). Required when running HTTP behind a
    # TLS-terminating proxy/tunnel (so init returns https://..., not the local http scheme).
    'public_base': os.environ.get('GG_PUBLIC_BASE', '') or os.environ.get('GG_PUBLIC_HOST', ''),
    'cdn_url': os.environ.get('GG_CDN_URL', ''),
    'verbose': os.environ.get('GG_VERBOSE', '1') == '1',
}

# precompiled static responses (verbatim base64 bodies)
STATIC_RESPONSES = {}
# NOTE: getEventRewardList is intentionally NOT static -- it is built per-user by
# handlers/reward.py so the attendance board reflects which days the player already claimed
# (otherwise the daily/7-day popup re-opens every login and claims never "stick").
for _name in ('getGameDataList', 'getVarietyStore', 'getPostTime'):
    _f = os.path.join(GAMEDATA_DIR, _name + '.b64')
    if os.path.exists(_f):
        STATIC_RESPONSES[_name] = open(_f).read().strip()

# CDN path -> file (the 4 fixed paths the client requests)
CDN_MAP = {
    '/AssetBundles/Android/Android.manifest': 'Android.manifest',
    '/AssetBundles/Android/Android': 'Android',
    '/AssetBundles/Android/table/table_bundlesize.ab.manifest': 'table_bundlesize.ab.manifest',
    '/AssetBundles/Android/table/table_bundlesize.ab': 'table_bundlesize.ab',
}

_seq = 0
def _capture(tag, data):
    global _seq
    _seq += 1
    try:
        json.dump(data, open(os.path.join(CAP_DIR, f"{int(time.time())}_{_seq:04d}_{tag}.json"), 'w',
                  encoding='utf-8'), indent=1, ensure_ascii=False, default=str)
    except Exception:
        pass


class _HTTPSMarker: pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def log_message(self, fmt, *a):
        if CONFIG['verbose']:
            sys.stderr.write("[gg] " + (fmt % a) + "\n")

    def _send(self, body, code=200, ctype='text/plain; charset=utf-8'):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        # HEAD must carry the same headers (incl. Content-Length) but no body.
        if self.command == 'HEAD':
            return
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def _base_url(self):
        # 1) explicit public base (recommended for external/HTTPS-proxy setups)
        pb = CONFIG['public_base']
        if pb:
            return pb if '://' in pb else ('http://' + pb)
        # 2) derive from request: honor proxy's X-Forwarded-Proto, else local socket scheme
        host = self.headers.get('Host', 'localhost')
        scheme = self.headers.get('X-Forwarded-Proto') or \
                 ('https' if isinstance(self.server, _HTTPSMarker) else 'http')
        return f"{scheme}://{host}"

    # ---------------- GET (CDN / health) ----------------
    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path in ('/', '/health'):
            self._send('GG emulator OK')
            return
        fname = CDN_MAP.get(path)
        if not fname and path.startswith('/AssetBundles/'):
            fname = os.path.basename(path)   # tolerant fallback
        if fname:
            fpath = os.path.join(CDN_DIR, fname)
            if os.path.exists(fpath):
                self.log_message("CDN %s", path)
                self._send(open(fpath, 'rb').read(), 200, 'application/octet-stream')
                return
        self._send(b'', 404, 'application/octet-stream')

    # HEAD: the client validates CDN downloads with a HEAD request (GgUtil.IsValidDownloadFile);
    # without this BaseHTTPRequestHandler answers 501 -> client reports ERROR_90005 ("network error").
    # _send() suppresses the body for HEAD while keeping status + Content-Length headers identical.
    do_HEAD = do_GET

    # ---------------- POST (game RPC / auth) ----------------
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0) or 0)
            body = self.rfile.read(length) if length else b''
            ctype = self.headers.get('Content-Type', '')
            path = self.path.split('?', 1)[0]
            form = multipart.parse(ctype, body)

            # --- NeonAPI / PmangPlus auth (JSON) ---
            if path.startswith('/api/'):
                res = auth.handle(path, form)
                if res is not None:
                    data, ct = res
                    _capture('auth' + path.replace('/', '_'),
                             {'path': path, 'form': {k: str(v)[:120] for k, v in form.items()}})
                    self.log_message("AUTH %s", path)
                    self._send(data, 200, ct)
                    return

            # --- game Thrift RPC ---
            call = form.get('call')
            base_url = self._base_url()
            cdn_url = CONFIG['cdn_url'] or base_url

            # category from /{category}/{call}/en/
            parts = [p for p in path.split('/') if p]
            category = parts[0] if parts else ''

            # static precompiled responses (verbatim)
            if call in STATIC_RESPONSES:
                self.log_message("%s -> static (%d B)", call, len(STATIC_RESPONSES[call]))
                _capture(call, {'path': path, 'call': call, 'static': True})
                self._send(STATIC_RESPONSES[call])
                return

            cmd_full = dispatch.resolve_command(form)
            msg_field, b64 = dispatch.find_message_field(form)
            req_named = None
            if b64:
                try:
                    req_named, _ = codec.decode_request(b64, cmd_full)
                except Exception as e:
                    req_named = {'_decode_error': str(e)}

            cap = {'path': path, 'call': call, 'command': cmd_full, 'category': category,
                   'form_fields': {k: (v if isinstance(v, str) and len(v) < 120 else f"<{len(v)}>")
                                   for k, v in form.items()},
                   'request_decoded': req_named}

            if not cmd_full:
                _capture('UNRESOLVED', cap)
                self.log_message("UNRESOLVED call=%s fields=%s", call, list(form.keys()))
                self._send('')
                return

            uuid = None
            if isinstance(req_named, dict):
                d = req_named.get('data') or {}
                if isinstance(d, dict):
                    uuid = d.get('uuid') or d.get('device_uuid')
            ctx = {'game_url': base_url, 'cdn_url': cdn_url, 'uuid': uuid}

            simple = codec.SCHEMA[cmd_full]['name']
            ret_data, error = handlers.handle(simple, req_named, ctx)
            rdto, env = dispatch.build_return(cmd_full, ret_data, call=simple,
                                              category=category, error=error)
            if not rdto:
                cap['error'] = 'no Return DTO'
                _capture('NORETURN', cap)
                self._send('')
                return

            out_b64 = codec.encode_response(rdto, env)
            cap['response_dto'] = rdto
            cap['response'] = env
            _capture(simple, cap)
            self.log_message("%s -> %s (%d B)", simple, rdto, len(out_b64))
            self._send(out_b64)

        except Exception as e:
            traceback.print_exc()
            _capture('ERROR', {'path': self.path, 'error': str(e), 'tb': traceback.format_exc()})
            self._send('', 500)


def make_server(host, port, certfile=None):
    httpd = ThreadingHTTPServer((host, port), Handler)
    if certfile:
        import ssl
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile)
        httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
        httpd.__class__ = type('HTTPSServer', (ThreadingHTTPServer, _HTTPSMarker), {})
    return httpd

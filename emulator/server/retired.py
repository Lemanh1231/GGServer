"""Legacy endpoint: protocol errors only. Never import auth, handlers or player state."""
import json
import copy
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import codec
from server import dispatch, multipart

DOWNLOAD_URL = 'https://kotori.click/download'
MESSAGE = ('Đã ngắt kết nối: máy chủ Python cũ đã ngừng phục vụ.\n'
           'Vui lòng tải phiên bản mới tại website:\n' + DOWNLOAD_URL + '\n'
           'Không gỡ game hoặc xóa dữ liệu trước khi lưu thông tin tài khoản.')
ERROR_CODE = 900
MAX_BODY = 2 * 1024 * 1024
BASE = Path(__file__).resolve().parents[1]
BOOTSTRAP = {'main.Request', 'main.getServerTime', 'main.getUpdateTime',
             'main.defaultSettingList', 'main.getGameDataList', 'store.getVarietyStore'}
_TABLES = {}


def bootstrap_data(command, base_url):
    """Same pre-ban allowlist as app.py; no user handlers or database access."""
    if command == 'main.Request':
        return {'idx': 253, 'game_url': base_url, 'cdn_url': base_url}
    if command == 'main.getServerTime':
        timestamp, date = dispatch.now_times()
        return {'time': timestamp, 'datetime': date}
    if command == 'main.getUpdateTime':
        return {'upd_time': 1700000000}
    if command == 'main.defaultSettingList':
        settings = [('shop_call_wait', '2'), ('ad_cancel_delay', '0'), ('force_menu_restric', 'true'),
                    ('max_bundle_texutre_loading', '1'), ('weather_snow', 'false'), ('check_time_cheat', 'false'),
                    ('ap_max', '70'), ('ap_time', '300'), ('ap_use', '5'), ('character_exp', '45'),
                    ('ap_shop_id', '31'), ('ap_ad_list_id', '2'), ('ch_third_unlock_follower_id', '5'),
                    ('ch_third_unlock_follower_level', '1'), ('ad_follower_profile_exp_persent', '0.1'),
                    ('follower_profile_bonus_percent', '1'), ('spine_load_max_count', '0'), ('log_flag', 'true'),
                    ('weather_cherry_blossom', 'false'), ('active_goods_ticket_buff', 'true'),
                    ('active_fan_art_costume', 'false'), ('pass_goods_sale_start_time', '2020-01-01 00:00'),
                    ('pass_goods_sale_end_time', '2020-01-01 00:00'), ('attendacne_buff_value', '0.01'),
                    ('attendacne_buff_limit_day', '10000'), ('log_flag_unfinished_purchase', 'true'), ('jp_laws_flag', 'true')]
        return {'status': 'Y', 'setting_list': [{'setting_key': k, 'setting_value': v} for k, v in settings]}
    if command not in _TABLES:
        name = command.split('.')[-1]
        decoded, _ = codec.decode_request((BASE / 'gamedata' / (name + '.b64')).read_text().strip(),
                                          dispatch.return_dto_for(command))
        _TABLES[command] = decoded['data']
    return copy.deepcopy(_TABLES[command])


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def send(self, body, status=200, content_type='text/plain; charset=utf-8', location=None):
        body = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'close')
        if location:
            self.send_header('Location', location)
        self.end_headers()
        self.close_connection = True
        if self.command != 'HEAD':
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/health':
            self.send(json.dumps({'mode': 'retired', 'gameplay': False, 'download_url': DOWNLOAD_URL}),
                      content_type='application/json; charset=utf-8')
        elif path in ('/download', '/download/', '/download/apk', '/tai-game', '/apk'):
            self.send(MESSAGE, 302, location=DOWNLOAD_URL)
        elif path.startswith('/AssetBundles/'):
            # Read-only UI assets needed before the native ban dialog can appear.
            file = BASE / 'cdn_files' / Path(path).name
            if file.is_file():
                self.send(file.read_bytes(), content_type='application/octet-stream')
            else:
                self.send(MESSAGE, 404)
        elif self.sdk_response(path, {}):
            return
        else:
            self.send(MESSAGE, 410)

    do_HEAD = do_GET

    def sdk_response(self, path, form):
        normalized = path[4:] if path.startswith('/api/') else path
        if not normalized.startswith(('/accounts/', '/app/', '/gcm/', '/referrer/', '/analytics', '/eula/')) and 'geoip' not in normalized:
            return False
        if normalized == '/accounts/v3/global/login':
            # SDK-only, nonpersistent identity to reach the game login error UI.
            # This token is NOT registered anywhere and cannot open a game session.
            now = int(time.time() * 1000)
            member = {'member_id': 429071553, 'nickname': 'Update required', 'status_cd': 'OK',
                      'crt_dt': now, 'upd_dt': now, 'anonymous_yn': 'N', 'adult_auth_yn': 'N',
                      'is_guest_login': False, 'provider_display_name': 'PmangPlus', 'conflict_member_id': 0}
            value = {'access_token': f"429071553|{form.get('app_id', '0')}|{form.get('device_cd', '')}|KR|618de92ee950717f49afcd82d359bc92b2c34a7f|{now}",
                     'member': member, 'is_guest_login': False, 'jailbreak_yn': 'N', 'fcm_send_lang': 'EN',
                     'unreg_status': 'NO', 'callTime': 0}
        elif normalized.startswith('/eula/'):
            self.send('<html><body>Legacy service retired. ' + DOWNLOAD_URL + '</body></html>', content_type='text/html; charset=utf-8')
            return True
        elif normalized.startswith('/gcm/'):
            value = {'unsubscription': [], 'subscription': [], 'fcmheader': ''}
        else:
            value = 'US' if 'geoip' in normalized else True
        self.send(json.dumps({'value': value, 'result_code': '000', 'result_msg': 'API_OK'}),
                  content_type='application/json; charset=utf-8')
        return True

    def do_POST(self):
        if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Encoding'):
            self.send(MESSAGE, 400)
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 0 or length > MAX_BODY:
                raise ValueError()
        except ValueError:
            self.send(MESSAGE, 413)
            return
        self.connection.settimeout(10)
        try:
            body = self.rfile.read(length)
        except (OSError, TimeoutError):
            self.send(MESSAGE, 408)
            return
        path = urlsplit(self.path).path
        form = multipart.parse(self.headers.get('Content-Type', ''), body)
        if self.sdk_response(path, form):
            return
        if path.startswith(('/api/', '/accounts/', '/app/', '/gcm/', '/referrer/')):
            # Never issue credentials, create accounts or forward to the old auth.
            self.send(json.dumps({'success': False, 'error': {'code': ERROR_CODE, 'errmsg': MESSAGE},
                                  'message': MESSAGE, 'download_url': DOWNLOAD_URL}, ensure_ascii=False),
                      410, 'application/json; charset=utf-8')
            return
        command = dispatch.resolve_command(form)
        if command is None:
            # Some legacy clients identify the command only in the URL.
            for part in reversed(path.strip('/').split('/')):
                command = dispatch.resolve_command({'call': part})
                if command:
                    break
        if command:
            data = None
            error = {'code': ERROR_CODE, 'errmsg': MESSAGE}
            if command in BOOTSTRAP:
                # Both supported APK generations contain a loopback gateway.
                # Recover cached direct-domain routing: the gateway, not the
                # shared domain URL, carries the old/new release distinction.
                base_url = 'http://127.0.0.1:28765'
                local = self.headers.get('X-GG-Local-Proxy', '').rstrip('/')
                if local.startswith('http://127.0.0.1:') and local[17:].isdigit() and 1024 <= int(local[17:]) <= 65535:
                    base_url = local
                data = bootstrap_data(command, base_url)
                error = {'code': 0, 'errmsg': ''}
            self.log_message('%s %s', 'BOOTSTRAP' if command in BOOTSTRAP else 'UPDATE_REQUIRED', command)
            category = next((part for part in path.split('/') if part), '')
            dto, envelope = dispatch.build_return(command, data, category=category, error=error)
            if dto:
                # HTTP 200 lets the game decode/display the nonzero Thrift error;
                # 5xx would only trigger failover/retries and hide the message.
                self.send(codec.encode_response(dto, envelope))
                return
        self.send(MESSAGE, 410)


def make_server(host, port, cert=None):
    server = ThreadingHTTPServer((host, port), Handler)
    server.daemon_threads = True
    if cert:
        import ssl
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    return server

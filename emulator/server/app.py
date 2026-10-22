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
from server import multipart, dispatch, handlers, state, auth, event_manager, admin, download, currency

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE)
CAP_DIR = os.path.join(BASE, 'captures')
BANNED_CAP_DIR = os.path.join(CAP_DIR, 'banned')
GAMEDATA_DIR = os.path.join(BASE, 'gamedata')
CDN_DIR = os.path.join(BASE, 'cdn_files')
OUT_DIR = os.path.join(PROJECT_ROOT, 'out')
APK_FILENAME = 'Guitar_Girl_v8.0.0_NoGooglePlay.apk'
APK_PATH = os.path.join(OUT_DIR, APK_FILENAME)
os.makedirs(CAP_DIR, exist_ok=True)
os.makedirs(BANNED_CAP_DIR, exist_ok=True)

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
# NOTE: getPostTime, getEventRewardList, and getGameDataList are intentionally NOT static --
# getPostTime is handled dynamically by handlers/post.py so the client checks
# for new mailbox rewards and triggers red dot notifications on unread mail.
# getGameDataList is handled dynamically by handlers/gamedata.py to sync live event toggles (Meowfest, etc.).
for _name in ('getVarietyStore',):
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
def _capture(tag, data, is_banned=False):
    global _seq
    _seq += 1
    target_dir = BANNED_CAP_DIR if is_banned else CAP_DIR
    try:
        fname = os.path.join(target_dir, f"{int(time.time())}_{_seq:04d}_{tag}.json")
        with open(fname, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=1, ensure_ascii=False, default=str)
    except Exception:
        pass


class _HTTPSMarker: pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_CONNECT(self):
        try:
            self.send_response(400)
            self.end_headers()
        except Exception:
            pass

    def log_error(self, fmt, *a):
        msg = fmt % a
        # Suppress scanner noise (unsupported method, bad request syntax, etc.)
        if any(k in msg for k in ('Unsupported method', 'code 501', 'code 400', 'code 404')):
            return
        if CONFIG['verbose']:
            now_str = time.strftime('%d/%m/%y %H:%M:%S')
            sys.stderr.write(f"[{now_str}] {msg}\n")

    def log_request(self, code='-', size='-'):
        # Do not log health checks, admin UI/API polling, or scanner 404s/errors
        path = getattr(self, 'path', '')
        if path in ('/health', '/') or path.startswith('/admin') or str(code) in ('404', '400', '501'):
            return
        super().log_request(code, size)

    def log_message(self, fmt, *a):
        msg = fmt % a
        # Suppress health checks, root pings, admin polling, and scanner probes from log output
        if any(k in msg for k in ('/health', '"GET / HTTP', '"GET /admin', '"GET /favicon',
                                  'CONNECT ', '/SDK/', ' 404 -', ' 501 -', ' 400 -')):
            return
        if CONFIG['verbose']:
            now_str = time.strftime('%d/%m/%y %H:%M:%S')
            sys.stderr.write(f"[{now_str}] {msg}\n")

    def _get_client_ip(self):
        for hdr in ('CF-Connecting-IP', 'X-Forwarded-For', 'X-Real-IP'):
            val = self.headers.get(hdr)
            if val:
                return val.split(',')[0].strip()
        if self.client_address and len(self.client_address) > 0:
            return str(self.client_address[0]).strip()
        return '127.0.0.1'

    def _send(self, body, code=200, ctype='text/plain; charset=utf-8', headers=None):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        if headers:
            if isinstance(headers, dict):
                for k, v in headers.items():
                    self.send_header(k, str(v))
            elif isinstance(headers, (list, tuple)):
                for item in headers:
                    if isinstance(item, (tuple, list)) and len(item) == 2:
                        self.send_header(str(item[0]), str(item[1]))
        self.end_headers()
        # HEAD must carry the same headers (incl. Content-Length) but no body.
        if self.command == 'HEAD':
            return
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def _send_file(self, fpath, filename=None, ctype='application/vnd.android.package-archive'):
        if not os.path.isfile(fpath):
            self._send(b'File Not Found', 404)
            return
        size = os.path.getsize(fpath)
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(size))
        if filename:
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        if self.command == 'HEAD':
            return
        try:
            with open(fpath, 'rb') as f:
                while True:
                    chunk = f.read(256 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
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

    # ---------------- GET (CDN / health / admin / download) ----------------
    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path in ('/', '/health'):
            self._send('GG emulator OK')
            return
        if path in ('/download', '/download/', '/tai-game', '/tai-game/'):
            html = download.get_download_html()
            self._send(html, 200, 'text/html; charset=utf-8')
            return
        if path.startswith('/api/') or path.startswith('/eula/') or path.startswith('/accounts/') or path.startswith('/app/'):
            res = auth.handle(path, {})
            if res is not None:
                data, ct = res
                self._send(data, 200, ct)
                return
        if path in ('/download/apk', '/download/' + APK_FILENAME, '/' + APK_FILENAME, '/apk'):
            self.log_message("DOWNLOAD APK requested: %s", APK_PATH)
            self._send_file(APK_PATH, filename=APK_FILENAME)
            return
        if path.startswith('/download/') or path.endswith('.apk'):
            req_file = os.path.basename(path)
            candidate = os.path.join(OUT_DIR, req_file)
            if os.path.isfile(candidate) and req_file.endswith('.apk'):
                self.log_message("DOWNLOAD specific APK requested: %s", candidate)
                self._send_file(candidate, filename=req_file)
                return
        if path in ('/admin', '/admin/'):
            if not admin.is_admin_authenticated(self.headers):
                html = admin.get_login_html()
                self._send(html, 200, 'text/html; charset=utf-8')
                return
            html = admin.get_admin_html()
            self._send(html, 200, 'text/html; charset=utf-8')
            return
        if path.startswith('/admin/api/'):
            if not admin.is_admin_authenticated(self.headers):
                self._send(json.dumps({'success': False, 'error': 'Unauthorized. Vui lòng đăng nhập lại!'}), 401, 'application/json; charset=utf-8')
                return
        if path == '/admin/api/events':
            cfg = event_manager.load_event_config()
            resp = {
                'success': True,
                'config': cfg,
                'seasons': event_manager.STAR_PASS_SEASONS
            }
            self._send(json.dumps(resp, ensure_ascii=False), 200, 'application/json; charset=utf-8')
            return
        if path == '/admin/api/users':
            active_season = event_manager.get_active_star_pass_season()
            users_list = []
            conn = state.get_db()
            rows = conn.execute('SELECT uuid, device_uuid, u_id, u_seq, u_cp, u_candy, u_like, attendance_count, is_banned, ip, user_contents_json FROM user_data ORDER BY u_seq ASC').fetchall()
            f12_rows = conn.execute("SELECT uuid, level FROM user_inventory WHERE item_type = 'follower' AND item_id = 12").fetchall()
            f12_map = {fr['uuid']: int(fr['level'] or 0) for fr in f12_rows}
            conn.close()
            for r in rows:
                try:
                    data = json.loads(r['user_contents_json'] or '{}')
                except Exception:
                    data = {}
                ud = data.get('userdata', {})
                tickets = data.get('user_ticketcollection', []) or []
                subs = data.get('user_subscribe_list', []) or []
                evp = data.get('user_event_point', []) or []

                has_ticket = any(int(t.get('i_id', 0) or 0) in (active_season, 1000 + active_season) for t in tickets)
                has_active_sub = any(int(s.get('i_SubscribeID', 0) or 0) in (active_season, 1000 + active_season) and int(s.get('i_isActive', 0) or 0) == 1 for s in subs)
                is_gold = has_ticket or has_active_sub

                pass_entry = next((e for e in evp if e.get('s_EventType') == 'Pass' and int(e.get('i_DataID', 0) or 0) == active_season), {})
                cur_point = int(pass_entry.get('i_Point', 0) or 0)
                cur_step = int(pass_entry.get('i_Step', 0) or 0)

                att_info_1 = data.get('attendance', {}).get('1', {})
                att_1_day = att_info_1.get('day', 0)
                att_1_ymd = att_info_1.get('ymd', 0)

                att_info_3 = data.get('attendance', {}).get('3', {})
                att_3_day = att_info_3.get('day', 0)
                att_3_ymd = att_info_3.get('ymd', 0)

                areas = data.get('areas', {}) or {}
                a1 = areas.get('1') or areas.get(1) or {}
                a1_grade = int(a1.get('i_UserFanGrade', 1) or 1)
                followers = data.get('user_follower', []) or []
                f12_level = f12_map.get(r['uuid']) or next((int(f.get('i_Level', 0) or 0) for f in followers if int(f.get('i_id', 0) or 0) == 12), 0)
                ch2_unlocked = bool(a1_grade >= 4 and f12_level >= 15)
                is_test = state.is_test_user(r['uuid'], r['device_uuid'])

                users_list.append({
                    'uuid': r['uuid'],
                    'device_uuid': r['device_uuid'],
                    'u_seq': r['u_seq'],
                    'u_id': r['u_id'],
                    'ip': r['ip'] if ('ip' in r.keys() and r['ip']) else (ud.get('ip') or ''),
                    'u_nick': ud.get('u_nick') or r['u_id'] or f"Player {r['u_seq']}",
                    'u_last_login': ud.get('u_last_login') or ud.get('u_last_communication') or 'Chưa có',
                    'u_cp': r['u_cp'],
                    'u_candy': r['u_candy'],
                    'u_like': float(r['u_like'] or 0.0),
                    'u_like_formatted': currency.format_currency(r['u_like'] or 0.0),
                    'attendance_count': r['attendance_count'] or ud.get('attendance_count', 0),
                    'attendance_day': att_1_day,
                    'attendance_ymd': att_1_ymd,
                    'ch2_attendance_day': att_3_day,
                    'ch2_attendance_ymd': att_3_ymd,
                    'attendance_map': data.get('attendance', {}) or {},
                    'ch2_unlocked': ch2_unlocked,
                    'is_gold': is_gold,
                    'star_point': cur_point,
                    'star_step': cur_step,
                    'is_banned': bool(r['is_banned'] if 'is_banned' in r.keys() else 0),
                    'is_test': is_test,
                })
            resp = {'success': True, 'users': users_list, 'active_season': active_season}
            self._send(json.dumps(resp, ensure_ascii=False), 200, 'application/json; charset=utf-8')
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

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, HEAD')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Content-Length', '0')
        self.end_headers()

    # ---------------- POST (game RPC / auth) ----------------
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0) or 0)
            body = self.rfile.read(length) if length else b''
            ctype = self.headers.get('Content-Type', '')
            path = self.path.split('?', 1)[0]

            if path in ('/', '/health'):
                self._send('GG emulator OK')
                return

            # --- Admin Authentication APIs ---
            if path == '/admin/api/login':
                try:
                    data = json.loads(body.decode('utf-8'))
                    password = str(data.get('password', '')).strip()
                    if password == admin.ADMIN_PASSWORD:
                        token = admin.create_admin_token()
                        cookie_val = f"gg_admin_token={token}; Path=/; Max-Age=2592000; HttpOnly; SameSite=Lax"
                        resp = {'success': True, 'token': token, 'message': 'Đăng nhập thành công!'}
                        self._send(json.dumps(resp, ensure_ascii=False), 200, 'application/json; charset=utf-8', headers=[('Set-Cookie', cookie_val)])
                    else:
                        resp = {'success': False, 'error': 'Mật khẩu quản trị không chính xác!'}
                        self._send(json.dumps(resp, ensure_ascii=False), 401, 'application/json; charset=utf-8')
                except Exception as e:
                    resp = {'success': False, 'error': str(e)}
                    self._send(json.dumps(resp, ensure_ascii=False), 400, 'application/json; charset=utf-8')
                return

            if path in ('/admin/api/logout', '/admin/logout'):
                cookie_val = "gg_admin_token=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Max-Age=0; HttpOnly; SameSite=Lax"
                resp = {'success': True, 'message': 'Đã đăng xuất thành công!'}
                self._send(json.dumps(resp, ensure_ascii=False), 200, 'application/json; charset=utf-8', headers=[('Set-Cookie', cookie_val)])
                return

            # Protect all other /admin/api/ endpoints
            if path.startswith('/admin/api/'):
                if not admin.is_admin_authenticated(self.headers):
                    self._send(json.dumps({'success': False, 'error': 'Unauthorized. Vui lòng đăng nhập lại!'}), 401, 'application/json; charset=utf-8')
                    return

            # --- Admin Event Manager API ---
            if path == '/admin/api/events':
                try:
                    data = json.loads(body.decode('utf-8'))
                    notify = bool(data.get('notify_in_game', True))
                    updated = event_manager.save_event_config(data, notify_in_game=notify)
                    resp = {'success': True, 'config': updated, 'message': 'Cập nhật sự kiện thành công!'}
                    self._send(json.dumps(resp, ensure_ascii=False), 200, 'application/json; charset=utf-8')
                except Exception as e:
                    resp = {'success': False, 'error': str(e)}
                    self._send(json.dumps(resp, ensure_ascii=False), 400, 'application/json; charset=utf-8')
                return

            if path == '/admin/api/send_post':
                try:
                    data = json.loads(body.decode('utf-8'))
                    title = data.get('title') or 'Thông báo Quản trị'
                    memo = data.get('memo') or 'Quản trị viên đã gửi thông báo đến bạn.'
                    target_uuid = data.get('uuid') or None
                    items = []
                    cp = int(data.get('cp', 0) or 0)
                    if cp > 0:
                        items.append({'i_RewardType': 1, 'i_RewardId': 1, 'd_RewardQuantity': float(cp)})
                    candy = float(data.get('candy', 0) or 0)
                    if candy > 0:
                        items.append({'i_RewardType': 1, 'i_RewardId': 2, 'd_RewardQuantity': float(candy)})
                    cookies = int(data.get('cookies', 0) or 0)
                    if cookies > 0:
                        items.append({'i_RewardType': 1, 'i_RewardId': 11, 'd_RewardQuantity': float(cookies)})

                    from server.handlers import post
                    p = post.send_post(uuid=target_uuid, title=title, memo=memo, items=items)
                    resp = {'success': True, 'message': 'Đã gửi thư và quà thành công vào game!', 'post': p}
                    self._send(json.dumps(resp, ensure_ascii=False), 200, 'application/json; charset=utf-8')
                except Exception as e:
                    resp = {'success': False, 'error': str(e)}
                    self._send(json.dumps(resp, ensure_ascii=False), 400, 'application/json; charset=utf-8')
                return

            if path == '/admin/api/user/ban':
                try:
                    data = json.loads(body.decode('utf-8'))
                    target_uuid = data.get('uuid')
                    u_seq = data.get('u_seq')
                    banned = bool(data.get('banned', True))
                    ok = state.ban_user(target_uuid, banned=banned, u_seq=u_seq)
                    if not ok:
                        raise ValueError('Không tìm thấy người chơi!')
                    msg = 'Đã KHÓA (BAN) tài khoản thành công!' if banned else 'Đã MỞ KHÓA tài khoản thành công!'
                    resp = {'success': True, 'message': msg, 'is_banned': banned}
                    self._send(json.dumps(resp, ensure_ascii=False), 200, 'application/json; charset=utf-8')
                except Exception as e:
                    resp = {'success': False, 'error': str(e)}
                    self._send(json.dumps(resp, ensure_ascii=False), 400, 'application/json; charset=utf-8')
                return

            if path == '/admin/api/user/delete':
                try:
                    data = json.loads(body.decode('utf-8'))
                    target_uuid = data.get('uuid')
                    u_seq = data.get('u_seq')
                    ok = state.delete_user(target_uuid, u_seq=u_seq)
                    if not ok:
                        raise ValueError('Không tìm thấy người chơi để xóa!')
                    resp = {'success': True, 'message': 'Đã xóa toàn bộ dữ liệu tài khoản thành công! Khi vào lại game sẽ là tài khoản mới tinh.'}
                    self._send(json.dumps(resp, ensure_ascii=False), 200, 'application/json; charset=utf-8')
                except Exception as e:
                    resp = {'success': False, 'error': str(e)}
                    self._send(json.dumps(resp, ensure_ascii=False), 400, 'application/json; charset=utf-8')
                return

            if path == '/admin/api/users/cleanup_tests':
                try:
                    count = state.cleanup_test_users()
                    resp = {'success': True, 'count': count, 'message': f'Đã dọn dẹp thành công {count} tài khoản test tự động!'}
                    self._send(json.dumps(resp, ensure_ascii=False), 200, 'application/json; charset=utf-8')
                except Exception as e:
                    resp = {'success': False, 'error': str(e)}
                    self._send(json.dumps(resp, ensure_ascii=False), 400, 'application/json; charset=utf-8')
                return

            if path == '/admin/api/user/event_settings':
                try:
                    data = json.loads(body.decode('utf-8'))
                    target_uuid = data.get('uuid')
                    u_seq = data.get('u_seq')
                    if (not target_uuid or target_uuid == 'null') and u_seq:
                        conn = state.get_db()
                        row = conn.execute('SELECT uuid FROM user_data WHERE u_seq = ?', (int(u_seq),)).fetchone()
                        conn.close()
                        if row and row['uuid']:
                            target_uuid = row['uuid']
                    if not target_uuid:
                        raise ValueError('Thiếu mã UUID của người chơi!')

                    user = state.get_user(target_uuid)
                    if not user:
                        raise ValueError(f'Không tìm thấy người chơi với ID {target_uuid}!')

                    active_season = event_manager.get_active_star_pass_season()
                    sp_enabled = event_manager.is_star_pass_enabled()

                    # 1. Update Gold Pass for this individual user (ONLY if Star Pass is enabled globally)
                    if sp_enabled and 'is_gold' in data:
                        is_gold = bool(data['is_gold'])
                        shop_items = user.setdefault('user_shop', [])
                        subs = user.setdefault('user_subscribe_list', [])
                        tickets = user.setdefault('user_ticketcollection', [])

                        target_shop_id = 1000 + active_season
                        sub_ids = (active_season, 1000 + active_season)

                        if is_gold:
                            # Add to user_shop to mark as legitimately owned
                            sh = next((item for item in shop_items if int(item.get('i_id', 0) or 0) == target_shop_id), None)
                            if not sh:
                                shop_items.append({'i_id': target_shop_id, 'i_Count': 1, 'i_TotalCount': 1})
                            else:
                                sh['i_Count'] = max(int(sh.get('i_Count', 0) or 0), 1)
                                sh['i_TotalCount'] = max(int(sh.get('i_TotalCount', 0) or 0), 1)

                            # Ensure active subscription
                            sub = next((s for s in subs if int(s.get('i_SubscribeID', 0) or 0) in sub_ids), None)
                            if not sub:
                                subs.append({
                                    'i_SubscribeID': active_season,
                                    'i_isActive': 1,
                                    'i_ActiveTime': 2147483647
                                })
                            else:
                                sub['i_isActive'] = 1
                                sub['i_ActiveTime'] = 2147483647

                            # Ensure tickets in ticketcollection
                            t_ids = {int(t.get('i_id', 0) or 0) for t in tickets}
                            if active_season not in t_ids:
                                tickets.append({'i_id': active_season})
                            if target_shop_id not in t_ids:
                                tickets.append({'i_id': target_shop_id})
                        else:
                            # Revoke Gold Pass for this season
                            user['user_shop'] = [item for item in shop_items if int(item.get('i_id', 0) or 0) not in (active_season, 1000 + active_season, 2000 + active_season, 3000 + active_season)]
                            user['user_subscribe_list'] = [s for s in subs if int(s.get('i_SubscribeID', 0) or 0) not in sub_ids]
                            user['user_ticketcollection'] = [t for t in tickets if int(t.get('i_id', 0) or 0) not in (active_season, target_shop_id)]

                    # 2. Update Star Pass Points (ONLY if Star Pass is enabled globally)
                    if sp_enabled and 'star_point' in data and data['star_point'] is not None:
                        new_point = max(0, int(data['star_point']))
                        from server.handlers.reward import _get_step_for_points, _get_pass_version
                        new_step = _get_step_for_points(active_season, new_point)
                        pass_version = _get_pass_version(active_season)

                        evp_list = user.setdefault('user_event_point', [])
                        pass_entry = next((e for e in evp_list if e.get('s_EventType') == 'Pass' and int(e.get('i_DataID', 0) or 0) == active_season), None)
                        if pass_entry:
                            pass_entry['i_Point'] = new_point
                            pass_entry['i_Step'] = new_step
                            pass_entry['i_Version'] = pass_version
                        else:
                            evp_list.append({
                                's_EventType': 'Pass',
                                'i_DataID': active_season,
                                'i_Point': new_point,
                                'i_Step': new_step,
                                'i_ADViewTime': 0,
                                'i_Version': pass_version,
                            })

                    # 3. Update attendance count & board progress
                    att_dict = user.setdefault('attendance', {})
                    today_ymd = int(time.strftime('%Y%m%d', time.localtime()))
                    ud = user.setdefault('userdata', {})

                    custom_atts = data.get('attendance_events_custom')
                    if isinstance(custom_atts, dict) and any(bool(v.get('modified')) for v in custom_atts.values() if isinstance(v, dict)):
                        from server.handlers.reward import _give_reward, _get_event_rewards
                        all_rewards = _get_event_rewards()
                        for eidx, ev_cfg in custom_atts.items():
                            if not isinstance(ev_cfg, dict) or not ev_cfg.get('modified'):
                                continue
                            e_str = str(eidx)
                            if not event_manager.is_attendance_event_enabled(e_str):
                                continue  # Do not modify or seed attendance for globally disabled events
                            att_entry = att_dict.setdefault(e_str, {'day': 0, 'ymd': 0})
                            max_days = 14 if e_str in ('2', '202110') else 7
                            t_day = ev_cfg.get('target_day')
                            mode = ev_cfg.get('mode', 'claim_day')
                            unl = bool(ev_cfg.get('unlock_today', True))

                            if ev_cfg.get('grant_all'):
                                e_rews = all_rewards.get(e_str, {})
                                for d_num in range(1, max_days + 1):
                                    rew = e_rews.get(str(d_num))
                                    if rew:
                                        _give_reward(user, rew)
                                att_entry['day'] = max_days
                                att_entry['ymd'] = today_ymd
                            elif t_day is not None and str(t_day).strip() != '':
                                d_val = int(t_day)
                                if d_val >= max_days:
                                    if mode == 'complete':
                                        att_entry['day'] = max_days
                                        att_entry['ymd'] = today_ymd
                                    else:
                                        att_entry['day'] = max_days - 1
                                        att_entry['ymd'] = 0 if unl else today_ymd
                                elif d_val <= 0:
                                    att_entry['day'] = 0
                                    att_entry['ymd'] = 0
                                else:
                                    att_entry['day'] = d_val - 1
                                    att_entry['ymd'] = 0 if unl else today_ymd

                            if e_str == '1':
                                ud['attendance_count'] = att_entry['day'] if mode == 'complete' else (att_entry['day'] + 1)
                                ud['attendance_date'] = att_entry['ymd']
                                conn = state.get_db()
                                conn.execute('UPDATE user_data SET attendance_count = ?, attendance_date = ? WHERE uuid = ?',
                                             (ud['attendance_count'], ud['attendance_date'], user['uuid']))
                                conn.commit()
                                conn.close()
                    else:
                        # Fallback for individual Event 1 & 3 fields
                        att_1 = att_dict.setdefault('1', {'day': 0, 'ymd': 0})
                        unlock_today = bool(data.get('attendance_unlock_today', True))
                        att_mode = data.get('attendance_mode', 'claim_day')

                        target_att = data.get('attendance_day')
                        if target_att is None:
                            target_att = data.get('attendance_count')

                        if target_att is not None and str(target_att).strip() != '':
                            target_day = int(target_att)
                            if target_day >= 7:
                                if att_mode == 'complete':
                                    att_1['day'] = 7
                                    att_1['ymd'] = today_ymd
                                    ud['attendance_count'] = 7
                                    ud['attendance_date'] = today_ymd
                                else:
                                    att_1['day'] = 6
                                    att_1['ymd'] = 0 if unlock_today else today_ymd
                                    ud['attendance_count'] = 7
                                    ud['attendance_date'] = 0 if unlock_today else today_ymd
                            elif target_day <= 0:
                                att_1['day'] = 0
                                att_1['ymd'] = 0
                                ud['attendance_count'] = 0
                                ud['attendance_date'] = 0
                            else:
                                att_1['day'] = target_day - 1
                                att_1['ymd'] = 0 if unlock_today else today_ymd
                                ud['attendance_count'] = target_day
                                ud['attendance_date'] = 0 if unlock_today else today_ymd

                            conn = state.get_db()
                            conn.execute('UPDATE user_data SET attendance_count = ?, attendance_date = ? WHERE uuid = ?',
                                         (ud['attendance_count'], ud['attendance_date'], user['uuid']))
                            conn.commit()
                            conn.close()

                        if data.get('grant_7d_rewards'):
                            from server.handlers.reward import _give_reward, _get_event_rewards
                            rewards = _get_event_rewards().get('1', {})
                            for d_num in range(1, 8):
                                rew = rewards.get(str(d_num))
                                if rew:
                                    _give_reward(user, rew)
                            att_1['day'] = 7
                            att_1['ymd'] = today_ymd
                            ud['attendance_count'] = 7
                            ud['attendance_date'] = today_ymd
                            conn = state.get_db()
                            conn.execute('UPDATE user_data SET attendance_count = 7, attendance_date = ? WHERE uuid = ?',
                                         (today_ymd, user['uuid']))
                            conn.commit()
                            conn.close()

                        # Event 3: Cửa Hàng Tiện Lợi Hạnh Phúc (Chapter 2)
                        att_3 = att_dict.setdefault('3', {'day': 0, 'ymd': 0})
                        ch2_target_att = data.get('ch2_attendance_day')
                        ch2_unlock_today = bool(data.get('ch2_attendance_unlock_today', True))
                        ch2_att_mode = data.get('ch2_attendance_mode', 'claim_day')

                        if ch2_target_att is not None and str(ch2_target_att).strip() != '':
                            ch2_day = int(ch2_target_att)
                            if ch2_day >= 7:
                                if ch2_att_mode == 'complete':
                                    att_3['day'] = 7
                                    att_3['ymd'] = today_ymd
                                else:
                                    att_3['day'] = 6
                                    att_3['ymd'] = 0 if ch2_unlock_today else today_ymd
                            elif ch2_day <= 0:
                                att_3['day'] = 0
                                att_3['ymd'] = 0
                            else:
                                att_3['day'] = ch2_day - 1
                                att_3['ymd'] = 0 if ch2_unlock_today else today_ymd

                        if data.get('grant_ch2_rewards'):
                            from server.handlers.reward import _give_reward, _get_event_rewards
                            rewards_3 = _get_event_rewards().get('3', {})
                            for d_num in range(1, 8):
                                rew = rewards_3.get(str(d_num))
                                if rew:
                                    _give_reward(user, rew)
                            att_3['day'] = 7
                            att_3['ymd'] = today_ymd

                    # 3.5 Chapter 2 Unlock (Test Mode / Danger)
                    if 'unlock_ch2' in data:
                        unlock_ch2 = bool(data['unlock_ch2'])
                        areas = user.setdefault('areas', state._default_areas())
                        area1 = areas.get('1') or areas.get(1)
                        if not isinstance(area1, dict):
                            area1 = {'i_Area': 1, 'i_UserFanGrade': 1, 'i_UserFanCount': 0}
                        areas['1'] = area1
                        if 1 in areas:
                            areas[1] = area1
                        followers = user.setdefault('user_follower', [])
                        f12 = next((f for f in followers if int(f.get('i_id', 0) or 0) == 12), None)
                        if unlock_ch2:
                            area1['i_UserFanGrade'] = max(int(area1.get('i_UserFanGrade', 1) or 1), 4)
                            area1['i_UserFanCount'] = max(int(area1.get('i_UserFanCount', 0) or 0), 1000000)
                            if f12:
                                f12['i_Level'] = max(int(f12.get('i_Level', 1) or 1), 15)
                            else:
                                followers.append({
                                    'i_id': 12,
                                    'i_Level': 15,
                                    'i_ActiveTime': 0,
                                    'i_BonusLevel': 0,
                                })
                        else:
                            area1['i_UserFanGrade'] = 1
                            if f12:
                                f12['i_Level'] = 1

                    # 4. Currencies (CP, Candy, Tim/Like)
                    if 'is_banned' in data:
                        state.ban_user(user['uuid'], banned=bool(data['is_banned']))

                    add_cp = int(data.get('add_cp', 0) or 0)
                    add_candy = float(data.get('add_candy', 0) or 0)
                    set_like = data.get('set_like')
                    add_like = data.get('add_like')
                    from server import currency

                    mail_items = []
                    needs_reset = False

                    if set_like is not None and str(set_like).strip() != '':
                        s_int, s_like, s_str, s_fmt = currency.parse_currency(set_like)
                        state.set_like_currency(user['uuid'], s_str)
                        user.setdefault('userdata', {})['u_like'] = s_like
                        user['force_server_like'] = s_str
                        areas = user.setdefault('areas', state._default_areas())
                        for a in areas.values():
                            if isinstance(a, dict):
                                a['d_Like'] = s_like
                                a['s_Gp1'] = s_str
                        needs_reset = True
                        add_like = 0
                    elif add_like is not None and str(add_like).strip() not in ('', '0'):
                        a_int, a_like, a_str, a_fmt = currency.parse_currency(add_like)
                        if a_int != 0:
                            state.increment_currency(user['uuid'], like=a_str)
                            cur_l = min(currency.MAX_FLOAT, float(user.get('userdata', {}).get('u_like', 0.0) or 0.0) + a_like)
                            user.setdefault('userdata', {})['u_like'] = cur_l
                            areas = user.setdefault('areas', state._default_areas())
                            for a in areas.values():
                                if isinstance(a, dict):
                                    old_int, _, _, _ = currency.parse_currency(a.get('s_Gp1') or '0')
                                    new_int = min(currency.MAX_DECIMAL, currency.Decimal(old_int) + currency.Decimal(a_int))
                                    _, af, astr, _ = currency.parse_currency(new_int)
                                    a['d_Like'] = af
                                    a['s_Gp1'] = astr
                            needs_reset = True
                            if data.get('send_mail'):
                                mail_items.append({
                                    'i_RewardType': 1,
                                    'i_RewardId': 3,
                                    'd_RewardQuantity': float(a_like),
                                    'already_granted': True
                                })

                    if add_cp != 0 or add_candy != 0:
                        state.increment_currency(user['uuid'], cp=add_cp, candy=add_candy)
                        if add_cp != 0:
                            user.setdefault('userdata', {})['u_cp'] = int(user.get('userdata', {}).get('u_cp', 0) or 0) + add_cp
                            if data.get('send_mail'):
                                mail_items.append({
                                    'i_RewardType': 1,
                                    'i_RewardId': 1,
                                    'd_RewardQuantity': float(add_cp),
                                    'already_granted': True
                                })
                        if add_candy != 0:
                            user.setdefault('userdata', {})['u_candy'] = float(user.get('userdata', {}).get('u_candy', 0.0) or 0.0) + add_candy
                            if data.get('send_mail'):
                                mail_items.append({
                                    'i_RewardType': 1,
                                    'i_RewardId': 2,
                                    'd_RewardQuantity': float(add_candy),
                                    'already_granted': True
                                })
                        needs_reset = True

                    if needs_reset:
                        user['needs_client_reset'] = True

                    # Save user with updated areas and attendance
                    state.save_user(user)

                    # 5. Direct Mail notification
                    if data.get('send_mail'):
                        title = data.get('mail_title') or 'Cập nhật Quà tặng từ Quản trị viên'
                        memo = data.get('mail_memo') or 'Quản trị viên đã gửi quà tặng/quyền lợi vào tài khoản của bạn. Chúc bạn chơi game vui vẻ!'
                        from server.handlers import post
                        post.send_post(uuid=user['uuid'], title=title, memo=memo, items=mail_items)

                    resp = {'success': True, 'message': 'Đã cập nhật sự kiện cho người chơi thành công!'}
                    self._send(json.dumps(resp, ensure_ascii=False), 200, 'application/json; charset=utf-8')
                except Exception as e:
                    resp = {'success': False, 'error': str(e)}
                    self._send(json.dumps(resp, ensure_ascii=False), 400, 'application/json; charset=utf-8')
                return

            form = multipart.parse(ctype, body)
            client_ip = self._get_client_ip()

            # --- NeonAPI / PmangPlus auth (JSON) ---
            if path.startswith('/api/') or path.startswith('/accounts/') or path.startswith('/referrer/') or path.startswith('/gcm/') or path.startswith('/app/'):
                res = auth.handle(path, form)
                if res is not None:
                    data, ct = res
                    device_cd = form.get('device_cd', '')
                    if device_cd:
                        state.update_user_ip(device_cd, client_ip)
                    is_banned = state.is_user_banned(device_cd) if device_cd else False
                    _capture('auth' + path.replace('/', '_'),
                             {'path': path, 'form': {k: str(v)[:120] for k, v in form.items()}},
                             is_banned=is_banned)
                    self.log_message("[%s] AUTH %s (banned=%s)", client_ip, path, is_banned)
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
                self.log_message("[%s] %s -> static (%d B)", client_ip, call, len(STATIC_RESPONSES[call]))
                _capture(call, {'path': path, 'call': call, 'static': True})
                self._send(STATIC_RESPONSES[call])
                return

            # dynamic event-aware gamedata response with caching
            if call == 'getGameDataList':
                from server.handlers import gamedata
                out_b64 = gamedata.get_game_data_list_b64(category=category)
                self.log_message("[%s] %s -> dynamic (meowfest=%s, %d B)",
                                 client_ip, call, event_manager.is_meowfest_enabled(), len(out_b64))
                _capture(call, {'path': path, 'call': call, 'dynamic': True,
                                'meowfest': event_manager.is_meowfest_enabled()})
                self._send(out_b64)
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

            uuid = None
            if isinstance(req_named, dict):
                d = req_named.get('data') or {}
                if isinstance(d, dict):
                    uuid = d.get('device_uuid') or d.get('uuid')

            # Identify if this device/user is banned
            is_banned = False
            u_ident = uuid
            if not u_ident and isinstance(req_named, dict):
                d = req_named.get('data') or {}
                if isinstance(d, dict):
                    for k in ('device_uuid', 'uuid', 'u_seq'):
                        val = d.get(k)
                        if val:
                            u_ident = str(val)
                            break
            if u_ident:
                state.update_user_ip(u_ident, client_ip)
            elif uuid:
                state.update_user_ip(uuid, client_ip)

            if u_ident and state.is_user_banned(u_ident):
                is_banned = True

            if not cmd_full:
                if not call and not form:
                    self._send('GG emulator OK')
                    return
                _capture('UNRESOLVED', cap, is_banned=is_banned)
                self.log_message("[%s] UNRESOLVED call=%s fields=%s", client_ip, call, list(form.keys()))
                self._send('')
                return

            ctx = {'game_url': base_url, 'cdn_url': cdn_url, 'uuid': uuid, 'client_ip': client_ip}

            # Banned player check
            # DO NOT block bootstrap/system handshake commands (Request, getServerTime, getUpdateTime,
            # defaultSettingList, getGameDataList, store.getVarietyStore) so the Unity client can initialize
            # its UI properly and display the native Ban dialog instead of falling back to "No network connection".
            if cmd_full not in ('main.Request', 'main.getServerTime', 'main.getUpdateTime',
                                'main.defaultSettingList', 'main.getGameDataList', 'store.getVarietyStore'):
                if is_banned:
                    self.log_message("[%s] BANNED USER BLOCKED: %s (cmd=%s)", client_ip, u_ident, cmd_full)
                    error = {
                        'code': 900,
                        'errmsg': 'Tài khoản của bạn đã bị KHÓA (BAN) bởi Quản trị viên!\nVui lòng liên hệ Admin để được hỗ trợ.'
                    }
                    simple = codec.SCHEMA[cmd_full]['name']
                    rdto, env = dispatch.build_return(cmd_full, None, call=simple, category=category, error=error)
                    cap['response_dto'] = rdto
                    cap['response'] = env
                    cap['error'] = error
                    cap['blocked'] = True
                    _capture('BLOCKED_' + simple, cap, is_banned=True)
                    if rdto:
                        out_b64 = codec.encode_response(rdto, env)
                        self._send(out_b64)
                    else:
                        self._send('', 403)
                    return

            simple = codec.SCHEMA[cmd_full]['name']
            ret_data, error = handlers.handle(simple, req_named, ctx)
            rdto, env = dispatch.build_return(cmd_full, ret_data, call=simple,
                                              category=category, error=error)
            if not rdto:
                cap['error'] = 'no Return DTO'
                _capture('NORETURN', cap, is_banned=is_banned)
                self._send('')
                return

            out_b64 = codec.encode_response(rdto, env)
            cap['response_dto'] = rdto
            cap['response'] = env
            _capture(simple, cap, is_banned=is_banned)
            self.log_message("[%s] %s -> %s (%d B)", client_ip, simple, rdto, len(out_b64))
            self._send(out_b64)

        except Exception as e:
            traceback.print_exc()
            _capture('ERROR', {'path': self.path, 'error': str(e), 'tb': traceback.format_exc()},
                     is_banned=is_banned if 'is_banned' in locals() else False)
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

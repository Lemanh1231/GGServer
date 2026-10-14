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
from server import multipart, dispatch, handlers, state, auth, event_manager, admin

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
        if path in ('/admin', '/admin/'):
            html = admin.get_admin_html()
            self._send(html, 200, 'text/html; charset=utf-8')
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
            rows = conn.execute('SELECT uuid, device_uuid, u_id, u_seq, u_cp, u_candy, u_like, attendance_count, is_banned, user_contents_json FROM user_data ORDER BY u_seq ASC').fetchall()
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

                is_test = bool(
                    str(r['uuid']).startswith(('test_', 'emu-test-', 'att-test-', 'dm-test-', 'verify-'))
                    or str(r['device_uuid']).startswith(('test_', 'emu-test-', 'att-test-', 'dm-test-', 'verify-'))
                )

                users_list.append({
                    'uuid': r['uuid'],
                    'device_uuid': r['device_uuid'],
                    'u_seq': r['u_seq'],
                    'u_id': r['u_id'],
                    'u_nick': ud.get('u_nick') or r['u_id'] or f"Player {r['u_seq']}",
                    'u_last_login': ud.get('u_last_login') or ud.get('u_last_communication') or 'Chưa có',
                    'u_cp': r['u_cp'],
                    'u_candy': r['u_candy'],
                    'u_like': float(r['u_like'] or 0.0),
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
                    banned = bool(data.get('banned', True))
                    ok = state.ban_user(target_uuid, banned=banned)
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
                    ok = state.delete_user(target_uuid)
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
                    if not target_uuid:
                        raise ValueError('Thiếu mã UUID của người chơi!')

                    user = state.get_user(target_uuid)
                    if not user:
                        raise ValueError(f'Không tìm thấy người chơi với ID {target_uuid}!')

                    active_season = event_manager.get_active_star_pass_season()

                    # 1. Update Gold Pass for this individual user
                    if 'is_gold' in data:
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
                            for s in subs:
                                if int(s.get('i_SubscribeID', 0) or 0) in sub_ids:
                                    s['i_isActive'] = 0
                                    s['i_ActiveTime'] = 0
                            user['user_ticketcollection'] = [t for t in tickets if int(t.get('i_id', 0) or 0) not in (active_season, target_shop_id)]

                    # 2. Update Star Pass Points
                    if 'star_point' in data and data['star_point'] is not None:
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
                    add_like = float(data.get('add_like', 0) or 0)
                    set_like = data.get('set_like')

                    if set_like is not None and str(set_like).strip() != '':
                        state.set_like_currency(user['uuid'], set_like)
                        try:
                            s_str = str(set_like).strip()
                            s_int = int(float(s_str)) if ('.' in s_str or 'e' in s_str.lower()) else int(s_str)
                        except Exception:
                            s_int = 0
                        s_like = float(s_int)
                        user.setdefault('userdata', {})['u_like'] = s_like
                        for a in user.setdefault('areas', state._default_areas()).values():
                            a['d_Like'] = s_like
                            a['s_Gp1'] = str(s_int)
                        add_like = 0
                    elif add_like != 0:
                        state.increment_currency(user['uuid'], like=add_like)
                        cur_l = float(user.get('userdata', {}).get('u_like', 0.0) or 0.0) + add_like
                        user.setdefault('userdata', {})['u_like'] = cur_l
                        add_int = int(add_like)
                        for a in user.setdefault('areas', state._default_areas()).values():
                            a['d_Like'] = float(a.get('d_Like', 0.0) or 0.0) + add_like
                            try:
                                old_gp = int(a.get('s_Gp1') or '0')
                            except Exception:
                                old_gp = 0
                            a['s_Gp1'] = str(max(0, old_gp + add_int))

                    if add_cp != 0 or add_candy != 0:
                        state.increment_currency(user['uuid'], cp=add_cp, candy=add_candy)

                    # Save user with updated areas and attendance
                    state.save_user(user)

                    # 5. Direct Mail notification
                    if data.get('send_mail'):
                        title = data.get('mail_title') or 'Cập nhật Sự kiện Cá nhân'
                        memo = data.get('mail_memo') or 'Quản trị viên đã cập nhật quyền lợi sự kiện cho tài khoản của bạn.'
                        from server.handlers import post
                        post.send_post(uuid=user['uuid'], title=title, memo=memo, items=[])

                    resp = {'success': True, 'message': 'Đã cập nhật sự kiện cho người chơi thành công!'}
                    self._send(json.dumps(resp, ensure_ascii=False), 200, 'application/json; charset=utf-8')
                except Exception as e:
                    resp = {'success': False, 'error': str(e)}
                    self._send(json.dumps(resp, ensure_ascii=False), 400, 'application/json; charset=utf-8')
                return

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

            # dynamic event-aware gamedata response with caching
            if call == 'getGameDataList':
                from server.handlers import gamedata
                out_b64 = gamedata.get_game_data_list_b64(category=category)
                self.log_message("%s -> dynamic (meowfest=%s, %d B)",
                                 call, event_manager.is_meowfest_enabled(), len(out_b64))
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

            if not cmd_full:
                if not call and not form:
                    self._send('GG emulator OK')
                    return
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

            # Banned player check
            # DO NOT block bootstrap/system handshake commands (Request, getServerTime, getUpdateTime,
            # defaultSettingList, getGameDataList, getVarietyStore) so the Unity client can initialize
            # its UI properly and display the native Ban dialog instead of falling back to "No network connection".
            if cmd_full not in ('main.Request', 'main.getServerTime', 'main.getUpdateTime',
                                'main.defaultSettingList', 'main.getGameDataList', 'store.getVarietyStore'):
                u_check = None
                if uuid:
                    u_check = state.get_user(uuid)
                if not u_check and isinstance(req_named, dict):
                    d = req_named.get('data') or {}
                    if isinstance(d, dict):
                        for k in ('device_uuid', 'uuid', 'u_seq'):
                            val = d.get(k)
                            if val:
                                u_check = state.get_user(str(val))
                                if u_check:
                                    break
                if u_check and u_check.get('is_banned'):
                    self.log_message("BANNED USER BLOCKED: %s (cmd=%s)", u_check.get('uuid'), cmd_full)
                    error = {
                        'code': 900,
                        'errmsg': 'Tài khoản của bạn đã bị KHÓA (BAN) bởi Quản trị viên!\nVui lòng liên hệ Admin để được hỗ trợ.'
                    }
                    simple = codec.SCHEMA[cmd_full]['name']
                    rdto, env = dispatch.build_return(cmd_full, None, call=simple, category=category, error=error)
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

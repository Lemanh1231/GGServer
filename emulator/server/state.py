"""Persistent user store (SQLite), keyed by uuid.

Mirrors the reference repo's architectural split of JSON vs Currencies to ensure Atomic Updates and prevent Race Conditions.
"""
import sqlite3, json, os, threading, time

_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(_DIR, exist_ok=True)
_DB_PATH = os.path.join(_DIR, 'database.db')
_LOCK = threading.RLock()

def get_db():
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def _resolve_uuid(conn, ident):
    """Return the canonical `uuid` column for an identifier, matching get_user's lookup order.
    The client sends its device_uuid in the `uuid` field, but a row's uuid column may be a numeric
    account id -- so updates keyed strictly on `uuid` would silently miss. Resolve it the same way
    reads do (uuid -> device_uuid/u_id/u_seq -> single-row fallback)."""
    if not ident:
        ident = ''
    row = conn.execute('SELECT uuid FROM user_data WHERE uuid = ?', (ident,)).fetchone()
    if not row:
        row = conn.execute('SELECT uuid FROM user_data WHERE device_uuid = ? OR u_id = ? OR u_seq = ?',
                           (ident, ident, ident if str(ident).isdigit() else -1)).fetchone()
    return row['uuid'] if row else None

def init_db():
    with _LOCK:
        conn = get_db()
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS user_inventory (
                uuid TEXT,
                item_type TEXT,
                item_id INTEGER,
                level INTEGER DEFAULT 1,
                active_time INTEGER DEFAULT 0,
                bonus_level INTEGER DEFAULT 0,
                value INTEGER DEFAULT 0,
                extra_json TEXT,
                PRIMARY KEY(uuid, item_type, item_id),
                FOREIGN KEY(uuid) REFERENCES user_data(uuid) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS user_data (
                uuid TEXT PRIMARY KEY,
                device_uuid TEXT,
                u_id TEXT,
                u_seq INTEGER,
                u_cp INTEGER DEFAULT 0,
                u_candy REAL DEFAULT 0.0,
                u_like REAL DEFAULT 0.0,
                u_fans INTEGER DEFAULT 0,
                attendance_count INTEGER DEFAULT 0,
                attendance_date INTEGER DEFAULT 0,
                user_contents_json TEXT,
                is_banned INTEGER DEFAULT 0,
                ip TEXT DEFAULT ''
            )
        ''')
        # Automatic Migration
        try:
            conn.execute('ALTER TABLE user_data ADD COLUMN is_banned INTEGER DEFAULT 0')
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute('ALTER TABLE user_data ADD COLUMN ip TEXT DEFAULT ""')
            conn.commit()
        except Exception:
            pass

        for f in os.listdir(_DIR):
            if f.startswith('user_') and f.endswith('.json'):
                try:
                    p = os.path.join(_DIR, f)
                    with open(p, 'r', encoding='utf-8') as file:
                        d = json.load(file)
                        ud = d.get('userdata', {})
                        uuid = d.get('uuid') or ud.get('uuid')
                        if uuid:
                            u_cp = int(ud.get('u_cp', 1000000))
                            u_candy = float(ud.get('u_candy', 100000.0))
                            u_like = float(ud.get('u_like', 0.0))
                            u_fans = int(ud.get('u_fans', 0))
                            att_count = int(ud.get('attendance_count', 0))
                            att_date = int(ud.get('attendance_date', 0))
                            
                            ud.pop('u_cp', None)
                            ud.pop('u_candy', None)
                            ud.pop('u_like', None)
                            ud.pop('u_fans', None)
                            ud.pop('attendance_count', None)
                            ud.pop('attendance_date', None)
                            
                            conn.execute('''
                                INSERT OR IGNORE INTO user_data 
                                (uuid, device_uuid, u_id, u_seq, u_cp, u_candy, u_like, u_fans, attendance_count, attendance_date, user_contents_json)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (uuid, ud.get('device_uuid'), ud.get('u_id'), ud.get('u_seq'), 
                                  u_cp, u_candy, u_like, u_fans, att_count, att_date, json.dumps(d, ensure_ascii=False)))
                    os.rename(p, p + '.migrated')
                except Exception as e:
                    print(f"Migration error for {f}: {e}")
        conn.commit()
        conn.close()

init_db()

def _now_str():
    return time.strftime('%Y-%m-%d %H:%M:%S')

def _next_seq():
    with _LOCK:
        conn = get_db()
        row = conn.execute('SELECT MAX(u_seq) as m FROM user_data').fetchone()
        n = 100001
        if row and row['m']:
            n = row['m'] + 1
        conn.close()
        return n

def _default_userdata(u_seq, u_id, uuid, device_uuid):
    return {
        'u_seq': u_seq, 'u_id': u_id, 'uuid': uuid, 'u_name': u_id, 'u_nick': 'Guitarist',
        'u_fans_grade': 1, 'u_selected_costume_id': 1, 'u_selected_music_id': 1, 
        'u_retain_continuous_tap': 0, 'u_join_type': 1, 'u_last_login': _now_str(), 
        'u_last_communication': _now_str(), 'u_save_date': _now_str(), 
        'u_create_time': time.strftime('%Y%m%d'), 'u_tutorial_step': 0,
        'u_review_popup': 'N', 'device_uuid': device_uuid, 'u_samseck_step': 0,
        'u_free_cp': 0, 'u_charge_cp': 0,
        'u_fans': 0, 'u_like': 0.0,
    }

def _all_ch_third_stages():
    """Return all Chapter 1 and Chapter 2 stages (for stage definitions lookup)."""
    gd_path = os.path.join(os.path.dirname(__file__), '..', 'gamedata', 'game_data.json')
    try:
        with open(gd_path, 'r', encoding='utf-8') as f:
            gd = json.load(f)
        stages = []
        for r in gd.get('33', []):
            s_id = int(r.get('1', 0) or 0)
            chap = int(r.get('2', 0) or 0)
            idx = int(r.get('3', 0) or 0)
            stype = str(r.get('34', ''))
            star = 3 if stype == 'Normal' else 0
            if s_id > 0:
                stages.append({'i_id': s_id, 'i_ChapterId': chap, 'i_StageIndex': idx, 'i_Star': star})
        return stages
    except Exception:
        res = []
        for i in range(1001, 1021):
            res.append({'i_id': i, 'i_ChapterId': 1, 'i_StageIndex': i - 1000, 'i_Star': 3 if i in (1001, 1004, 1006, 1008, 1010, 1011, 1013, 1015, 1017, 1019) else 0})
        for i in range(2001, 2022):
            res.append({'i_id': i, 'i_ChapterId': 2, 'i_StageIndex': i - 2000, 'i_Star': 3 if i in (2002, 2004, 2007, 2009, 2010, 2012, 2014, 2016, 2018, 2020) else 0})
        return res

def _default_areas():
    return {
        1: {'u_area_num': 1, 'd_Candy': 0.0, 'd_Like': 0.0, 'i_UserFanCount': 0,
            'i_UserFanGrade': 1, 'i_SelectedCostumeId': 1, 'i_SelectedMusicId': 1,
            'i_SelectedGuitarId': 1, 's_TutorialList': '', 's_Gp1': '', 's_Gp2': ''},
        2: {'u_area_num': 2, 'd_Candy': 0.0, 'd_Like': 0.0, 'i_UserFanCount': 0,
            'i_UserFanGrade': 1, 'i_SelectedCostumeId': 201, 'i_SelectedMusicId': 201,
            'i_SelectedGuitarId': 201, 's_TutorialList': '', 's_Gp1': '', 's_Gp2': ''}
    }

def _reconstruct_user(row):
    data = json.loads(row['user_contents_json'])
    
    conn = get_db()
    items = conn.execute('SELECT * FROM user_inventory WHERE uuid = ?', (row['uuid'],)).fetchall()
    conn.close()
    
    key_map = {
        'unit': 'user_unit',
        'skill': 'user_skill',
        'music': 'user_music',
        'guitar': 'user_guitar',
        'costume': 'costumes',
        'prop': 'user_prop',
        'follower': 'user_follower',
        'gift': 'user_follower_giftitem',
        'shop': 'user_shop'
    }
    
    for item in items:
        jkey = key_map.get(item['item_type'])
        if not jkey: continue
        lst = data.setdefault(jkey, [])
        d = {'i_id': item['item_id']}
        if item['item_type'] != 'gift':
            d['i_Level'] = item['level']
        if item['active_time']: d['i_ActiveTime'] = item['active_time']
        if item['bonus_level']: d['i_BonusLevel'] = item['bonus_level']
        if item['item_type'] == 'gift': d['i_Value'] = item['value']
        
        if item['extra_json']:
            try: d.update(json.loads(item['extra_json']))
            except: pass
        lst.append(d)
    ud = data.setdefault('userdata', {})
    ud['u_join_type'] = 1
    ud['uuid'] = row['uuid']
    ud['device_uuid'] = row['device_uuid']
    ud['u_id'] = row['u_id']
    ud['u_seq'] = row['u_seq']
    ud['u_cp'] = row['u_cp']
    ud['u_candy'] = row['u_candy']
    ud['u_like'] = row['u_like']
    ud['u_fans'] = row['u_fans']
    ud['attendance_count'] = row['attendance_count']
    user_ip = row['ip'] if ('ip' in row.keys() and row['ip']) else (ud.get('ip') or '')
    ud['ip'] = user_ip
    data['ip'] = user_ip
    data['is_banned'] = bool(row['is_banned'] if 'is_banned' in row.keys() else 0)
    if 'created_at' not in data:
        uct = ud.get('u_create_time')
        if uct and len(str(uct)) == 8:
            try:
                data['created_at'] = int(time.mktime(time.strptime(str(uct), '%Y%m%d')))
            except Exception:
                data['created_at'] = data.get('last_save_time') or int(time.time())
        else:
            data['created_at'] = data.get('last_save_time') or int(time.time())


    # Sync like currency to active areas so client in-game HUD displays the hearts safely
    from server import currency
    cur_like = float(row['u_like'] or 0.0)
    cur_like_int, cur_like_f, cur_like_str, _ = currency.parse_currency(cur_like)
    ud['u_like'] = cur_like_f
    areas = data.setdefault('areas', _default_areas())
    for aid, ainfo in areas.items():
        if isinstance(ainfo, dict):
            old_gp1 = ainfo.get('s_Gp1') or '0'
            old_int, _, _, _ = currency.parse_currency(old_gp1)
            target_int = cur_like_int if data.get('force_server_like') else max(cur_like_int, old_int)
            _, tf, tstr, _ = currency.parse_currency(target_int)
            ainfo['d_Like'] = tf
            ainfo['s_Gp1'] = tstr

    return data

def get_user(uuid):
    with _LOCK:
        if not uuid: return None
        conn = get_db()
        row = conn.execute('SELECT * FROM user_data WHERE uuid = ?', (uuid,)).fetchone()
        if not row:
            row = conn.execute('SELECT * FROM user_data WHERE device_uuid = ? OR u_id = ? OR u_seq = ?', 
                               (uuid, uuid, uuid if str(uuid).isdigit() else -1)).fetchone()

        if row:
            user = _reconstruct_user(row)
            conn.close()
            return user
            
        conn.close()
        return None

def create_user(uuid, device_uuid, ip=''):
    with _LOCK:
        if not uuid and not device_uuid:
            import uuid as uuidlib
            uuid = f"gen_{uuidlib.uuid4().hex[:16]}"
            device_uuid = uuid
        elif not uuid:
            uuid = device_uuid
        elif not device_uuid:
            device_uuid = uuid

        # The app creates a fresh local UUID after Clear data, while its
        # device UUID remains stable.  Prefer that stable identifier so a
        # clear cannot create a second account and re-grant starter rewards.
        existing = get_user(device_uuid) if device_uuid else None
        if not existing:
            existing = get_user(uuid)
        if existing:
            if ip and not existing.get('ip'):
                update_user_ip(existing.get('uuid'), ip)
            return existing
        
        seq = _next_seq()
        u_id = f'guest_{seq}'
        starter_stage = []
        now_ts = int(time.time())
        user = {
            'uuid': uuid,
            'ip': ip or '',
            'created_at': now_ts,
            'posts': [],
            'welcome_post_sent': False,
            'deleted_post_indices': [],
            'userdata': _default_userdata(seq, u_id, uuid, device_uuid),
            'needs_client_reset': True,
            'last_save_time': now_ts,
            'areas': _default_areas(),
            'achievements': [{'i_id': i, 'i_Level': 1, 'd_Quantity': 1.0, 's_Quantity': ''} for i in range(1, 11)],
            'characters': [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}, {'i_id': 2, 'i_Level': 1, 'i_BonusLevel': 0}],
            'costumes': [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}, {'i_id': 201, 'i_Level': 1, 'i_BonusLevel': 0}],
            'user_music': [
                {'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0,
                 'b_EncoreBonusAppear': 0, 'l_EncoreBonusActivateTime': 0,
                 'i_EncoreBonusFollowerId': 0, 'i_ChThirdActiveTime': 0},
                {'i_id': 201, 'i_Level': 1, 'i_BonusLevel': 0,
                 'b_EncoreBonusAppear': 0, 'l_EncoreBonusActivateTime': 0,
                 'i_EncoreBonusFollowerId': 0, 'i_ChThirdActiveTime': 0},
            ],
            'user_guitar': [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}, {'i_id': 201, 'i_Level': 1, 'i_BonusLevel': 0}],
            'user_follower': [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}],
            'user_follower_profile': [
                {'i_id': 1, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0},
                {'i_id': 100000, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0},
            ],
            'user_follower_profile_reward': [],
            'user_follower_giftitem': [{'i_id': 1, 'i_Value': 141}],
            'user_ch_third_stage': starter_stage,
            'user_chthird_stage': starter_stage,
            'user_ap': {'i_Ap': 70, 'i_FullApTime': 0, 'i_MaxAp': 70},
            'user_messenger': [
                {
                    'i_MessengerChatRoomId': 1,
                    'i_LastConfirmIndex': 0,
                    's_UnlockGroupList': '1',
                    'l_UpdateTimeTicks': 0,
                }
            ],
            'legacy_unlock_all_migrated': True,
        }
        user['userdata']['u_ap'] = 70
        user['userdata']['u_cp'] = 0
        user['userdata']['u_fans'] = 0
        user['userdata']['u_like'] = 0.0
        
        u_cp = 0
        u_candy = 0.0
        u_like = 0.0
        u_fans = 0
        att_count = 0
        att_date = 0
        
        conn = get_db()
        conn.execute('''
            INSERT INTO user_data 
            (uuid, device_uuid, u_id, u_seq, u_cp, u_candy, u_like, u_fans, attendance_count, attendance_date, user_contents_json, ip)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (uuid, device_uuid, u_id, seq, u_cp, u_candy, u_like, u_fans, att_count, att_date, json.dumps(user, ensure_ascii=False), ip or ''))
        conn.commit()
        conn.close()
        
        ud = user['userdata']
        ud['ip'] = ip or ''
        ud['u_cp'] = u_cp
        ud['u_candy'] = u_candy
        ud['u_like'] = u_like
        ud['u_fans'] = u_fans
        ud['attendance_count'] = att_count
        ud['attendance_date'] = att_date
        return user

def save_user(user):
    with _LOCK:
        uuid = user.get('uuid')
        if not uuid: return
        ud = user.get('userdata', {})

        # Keep the caller's object intact.  Handlers often place one of these
        # inventory objects in the response before calling save_user(); popping
        # fields from it here encoded an empty response, so upgrades looked as
        # though they had failed on the client.
        stored = dict(user)
        stored_ud = dict(ud)
        for key in ('u_cp', 'u_candy', 'u_like', 'u_fans',
                    'attendance_count', 'attendance_date'):
            stored_ud.pop(key, None)
        stored['userdata'] = stored_ud
        
        conn = get_db()
        
        key_map = {
            'user_unit': 'unit',
            'user_skill': 'skill',
            'user_music': 'music',
            'user_guitar': 'guitar',
            'costumes': 'costume',
            'user_prop': 'prop',
            'user_follower': 'follower',
            'user_follower_giftitem': 'gift',
            'user_shop': 'shop'
        }
        
        for jkey, itype in key_map.items():
            # Store inventory separately without mutating the in-memory lists.
            if jkey not in stored:
                continue
            lst = stored.pop(jkey)
            # save_user receives a full inventory snapshot.  Without removing
            # rows omitted from that snapshot, old unlock-all entries survive
            # forever in SQLite and are merged back on the next login.
            conn.execute('DELETE FROM user_inventory WHERE uuid = ? AND item_type = ?',
                         (uuid, itype))
            for item in lst:
                item_id = item.get('i_id', 0)
                level = item.get('i_Level', 1)
                active_time = item.get('i_ActiveTime', 0)
                bonus_level = item.get('i_BonusLevel', 0)
                value = item.get('i_Value', 0)
                extra = {k: v for k, v in item.items()
                         if k not in ('i_id', 'i_Level', 'i_ActiveTime',
                                      'i_BonusLevel', 'i_Value')}
                extra_json = json.dumps(extra) if extra else None
                
                conn.execute('''
                    INSERT INTO user_inventory
                    (uuid, item_type, item_id, level, active_time, bonus_level, value, extra_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(uuid, item_type, item_id) DO UPDATE SET
                    level=excluded.level, active_time=excluded.active_time, 
                    bonus_level=excluded.bonus_level, value=excluded.value, extra_json=excluded.extra_json
                ''', (uuid, itype, item_id, level, active_time, bonus_level, value, extra_json))
        
        from server import currency
        u_like_val = min(currency.MAX_FLOAT, float(ud.get('u_like', 0.0) or 0.0))
        u_cp_val = int(ud.get('u_cp', 0) or 0)
        u_candy_val = float(ud.get('u_candy', 0.0) or 0.0)
        u_fans_val = int(ud.get('u_fans', 0) or 0)
        att_cnt = int(ud.get('attendance_count', 0) or 0)
        att_dt = int(ud.get('attendance_date', 0) or 0)
        u_ip = str(user.get('ip') or ud.get('ip') or '').strip()

        if u_ip and u_ip not in ('127.0.0.1', 'localhost', '::1'):
            conn.execute('''
                UPDATE user_data 
                SET user_contents_json = ?,
                    u_cp = ?,
                    u_candy = ?,
                    u_like = ?,
                    u_fans = ?,
                    attendance_count = ?,
                    attendance_date = ?,
                    ip = ?
                WHERE uuid = ?
            ''', (json.dumps(stored, ensure_ascii=False), u_cp_val, u_candy_val, u_like_val, u_fans_val, att_cnt, att_dt, u_ip, uuid))
        else:
            conn.execute('''
                UPDATE user_data 
                SET user_contents_json = ?,
                    u_cp = ?,
                    u_candy = ?,
                    u_like = ?,
                    u_fans = ?,
                    attendance_count = ?,
                    attendance_date = ?
                WHERE uuid = ?
            ''', (json.dumps(stored, ensure_ascii=False), u_cp_val, u_candy_val, u_like_val, u_fans_val, att_cnt, att_dt, uuid))
        conn.commit()
        conn.close()

def update_user_ip(ident, ip):
    if not ident or not ip:
        return
    ip_str = str(ip).strip()
    if not ip_str:
        return
    with _LOCK:
        try:
            conn = get_db()
            ruuid = _resolve_uuid(conn, ident)
            if ruuid:
                # If ip_str is localhost and user already has a real IP, do not overwrite
                if ip_str in ('127.0.0.1', 'localhost', '::1'):
                    row = conn.execute('SELECT ip FROM user_data WHERE uuid = ?', (ruuid,)).fetchone()
                    if row and row['ip']:
                        conn.close()
                        return
                conn.execute('UPDATE user_data SET ip = ? WHERE uuid = ?', (ip_str, ruuid))
                conn.commit()
            conn.close()
        except Exception:
            pass

def increment_currency(uuid, cp=0, candy=0.0, like=0.0, fans=0):
    with _LOCK:
        conn = get_db()
        ruuid = _resolve_uuid(conn, uuid)
        if ruuid is not None:
            from server import currency
            like_int, like_f, like_str, _ = currency.parse_currency(like)
            conn.execute('''
                UPDATE user_data
                SET u_cp = u_cp + ?, u_candy = u_candy + ?, u_like = MIN(?, u_like + ?), u_fans = u_fans + ?
                WHERE uuid = ?
            ''', (int(cp), float(candy), float(currency.MAX_FLOAT), float(like_f), int(fans), ruuid))
            row = conn.execute('SELECT u_like, user_contents_json FROM user_data WHERE uuid = ?', (ruuid,)).fetchone()
            if row and row['user_contents_json']:
                try:
                    d = json.loads(row['user_contents_json'])
                    new_l = min(currency.MAX_FLOAT, float(row['u_like'] or 0.0))
                    d.setdefault('userdata', {})['u_like'] = new_l
                    if like_int != 0 or cp != 0 or candy != 0:
                        d['needs_client_reset'] = True
                    for a in d.setdefault('areas', {}).values():
                        if isinstance(a, dict):
                            a['d_Like'] = new_l
                            old_iv, _, _, _ = currency.parse_currency(a.get('s_Gp1') or '0')
                            new_iv = min(currency.MAX_DECIMAL, currency.Decimal(old_iv) + currency.Decimal(like_int))
                            _, _, nstr, _ = currency.parse_currency(new_iv)
                            a['s_Gp1'] = nstr
                    conn.execute('UPDATE user_data SET user_contents_json = ?, u_like = ? WHERE uuid = ?', (json.dumps(d, ensure_ascii=False), float(new_l), ruuid))
                except Exception:
                    pass
            conn.commit()
        conn.close()

def set_like_currency(uuid, amount):
    with _LOCK:
        conn = get_db()
        ruuid = _resolve_uuid(conn, uuid)
        if ruuid is not None:
            from server import currency
            int_val, float_val, gp_str, formatted = currency.parse_currency(amount)

            conn.execute('UPDATE user_data SET u_like = ? WHERE uuid = ?', (float(float_val), ruuid))
            row = conn.execute('SELECT user_contents_json FROM user_data WHERE uuid = ?', (ruuid,)).fetchone()
            if row and row['user_contents_json']:
                try:
                    d = json.loads(row['user_contents_json'])
                    d.setdefault('userdata', {})['u_like'] = float_val
                    d['needs_client_reset'] = True
                    d['force_server_like'] = gp_str
                    for a in d.setdefault('areas', {}).values():
                        if isinstance(a, dict):
                            a['d_Like'] = float_val
                            a['s_Gp1'] = gp_str
                    conn.execute('UPDATE user_data SET user_contents_json = ? WHERE uuid = ?', (json.dumps(d, ensure_ascii=False), ruuid))
                except Exception:
                    pass
            conn.commit()
        conn.close()

def ban_user(uuid, banned=True, u_seq=None):
    with _LOCK:
        conn = get_db()
        ruuid = None
        if uuid and uuid != 'null':
            ruuid = _resolve_uuid(conn, uuid)
        if ruuid is not None:
            val = 1 if banned else 0
            conn.execute('UPDATE user_data SET is_banned = ? WHERE uuid = ?', (val, ruuid))
            conn.commit()
            res = True
        elif u_seq:
            try:
                val = 1 if banned else 0
                conn.execute('UPDATE user_data SET is_banned = ? WHERE u_seq = ?', (val, int(u_seq)))
                conn.commit()
                res = True
            except Exception:
                res = False
        else:
            res = False
        conn.close()
        return res

def is_user_banned(ident):
    if not ident:
        return False
    with _LOCK:
        conn = get_db()
        ruuid = _resolve_uuid(conn, ident)
        if ruuid is not None:
            row = conn.execute('SELECT is_banned FROM user_data WHERE uuid = ?', (ruuid,)).fetchone()
            res = bool(row['is_banned']) if row and 'is_banned' in row.keys() else False
        else:
            res = False
        conn.close()
        return res

def is_real_device_uuid(val):
    if not val or not isinstance(val, str):
        return False
    s = val.strip().lower()
    if len(s) != 32:
        return False
    return all(c in '0123456789abcdef' for c in s)

def is_test_user(uuid, device_uuid):
    if not uuid or not device_uuid:
        return True
    u_str = str(uuid).lower()
    d_str = str(device_uuid).lower()
    test_prefixes = (
        'test', 't1-', 't2-', 't3-', 't4-', 't5-', 't6-', 't7-', 't8-', 't9-',
        'emu-', 'att-', 'dm-', 'verify-', 'cat-', 'music-', 'ad-', 'gift-', 'fix-'
    )
    if any(u_str.startswith(p) for p in test_prefixes) or any(d_str.startswith(p) for p in test_prefixes):
        return True
    if any(k in u_str for k in ('test', 'verify')) or any(k in d_str for k in ('test', 'verify')):
        return True
    return not is_real_device_uuid(uuid)

def delete_user(uuid, u_seq=None):
    with _LOCK:
        conn = get_db()
        ruuid = None
        if uuid and uuid != 'null':
            ruuid = _resolve_uuid(conn, uuid)
        if ruuid is None and u_seq:
            try:
                row = conn.execute('SELECT uuid FROM user_data WHERE u_seq = ?', (int(u_seq),)).fetchone()
                if row:
                    ruuid = row['uuid']
                    if ruuid is None:
                        conn.execute('DELETE FROM user_data WHERE u_seq = ?', (int(u_seq),))
                        conn.commit()
                        conn.close()
                        return True
            except Exception:
                pass
        if ruuid is not None:
            conn.execute('DELETE FROM user_inventory WHERE uuid = ?', (ruuid,))
            conn.execute('DELETE FROM user_data WHERE uuid = ?', (ruuid,))
            conn.commit()
            res = True
        elif u_seq:
            try:
                conn.execute('DELETE FROM user_data WHERE u_seq = ?', (int(u_seq),))
                conn.commit()
                res = True
            except Exception:
                res = False
        else:
            res = False
        conn.close()
        return res

def cleanup_test_users():
    """Delete all automatically generated test accounts from database."""
    with _LOCK:
        conn = get_db()
        rows = conn.execute('SELECT rowid, u_seq, uuid, device_uuid FROM user_data').fetchall()
        deleted_count = 0
        for r in rows:
            row_id = r['rowid']
            uuid = r['uuid']
            dev = r['device_uuid']
            if is_test_user(uuid, dev):
                if uuid:
                    conn.execute('DELETE FROM user_inventory WHERE uuid = ?', (uuid,))
                conn.execute('DELETE FROM user_data WHERE rowid = ?', (row_id,))
                deleted_count += 1
        conn.commit()
        conn.close()
        return deleted_count

def spend_currency(uuid, *, currency, amount):
    """Atomically spend a positive amount only when the balance covers it."""
    try:
        amount = int(amount) if currency == 'cp' else float(amount)
    except (TypeError, ValueError):
        return False
    if amount < 0:
        return False
    if amount == 0:
        return True
    column = 'u_cp' if currency == 'cp' else 'u_candy'
    with _LOCK:
        conn = get_db()
        ruuid = _resolve_uuid(conn, uuid)
        if ruuid is None:
            conn.close()
            return False
        cursor = conn.execute(
            f'UPDATE user_data SET {column} = {column} - ? '
            f'WHERE uuid = ? AND {column} >= ?',
            (amount, ruuid, amount),
        )
        conn.commit()
        conn.close()
        return cursor.rowcount == 1


def set_currency(uuid, *, cp, candy):
    """Set the two spendable currencies for a one-time data migration."""
    with _LOCK:
        conn = get_db()
        ruuid = _resolve_uuid(conn, uuid)
        if ruuid is not None:
            conn.execute('''
                UPDATE user_data SET u_cp = ?, u_candy = ? WHERE uuid = ?
            ''', (cp, candy, ruuid))
            conn.commit()
        conn.close()

def update_attendance(uuid, count, date):
    with _LOCK:
        conn = get_db()
        ruuid = _resolve_uuid(conn, uuid)
        if ruuid is not None:
            conn.execute('''
                UPDATE user_data
                SET attendance_count = ?, attendance_date = ?
                WHERE uuid = ?
            ''', (count, date, ruuid))
            conn.commit()
        conn.close()


def add_ap(user, amount):
    """Safely increment player cookie / AP balance while preserving the user_ap dict structure."""
    if not user:
        return {}
    if not isinstance(user.get('user_ap'), dict):
        user['user_ap'] = {'i_Ap': 70, 'i_FullApTime': 0, 'i_MaxAp': 70}
    ap = user['user_ap']
    cur = int(ap.get('i_Ap', 70) or 70)
    max_ap = int(ap.get('i_MaxAp', 70) or 70)
    new_ap = cur + int(amount)
    ap['i_Ap'] = new_ap
    if new_ap >= max_ap:
        ap['i_FullApTime'] = 0
    return ap


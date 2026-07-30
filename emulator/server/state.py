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
                user_contents_json TEXT
            )
        ''')
        # Automatic Migration
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
        'u_retain_continuous_tap': 0, 'u_join_type': 0, 'u_last_login': _now_str(), 
        'u_last_communication': _now_str(), 'u_save_date': _now_str(), 
        'u_create_time': time.strftime('%Y%m%d'), 'u_tutorial_step': 0,
        'u_review_popup': 'N', 'device_uuid': device_uuid, 'u_samseck_step': 0,
        'u_free_cp': 0, 'u_charge_cp': 0,
    }

def _default_areas():
    def area(n):
        return {'u_area_num': n, 'd_Candy': 0.0, 'd_Like': 0.0, 'i_UserFanCount': 0,
                'i_UserFanGrade': 1, 'i_SelectedCostumeId': 1, 'i_SelectedMusicId': 1,
                'i_SelectedGuitarId': 1, 's_TutorialList': '', 's_Gp1': '', 's_Gp2': ''}
    return {1: area(1), 2: area(2)}

def _reconstruct_user(row):
    data = json.loads(row['user_contents_json'])
    
    conn = get_db()
    items = conn.execute('SELECT * FROM user_inventory WHERE uuid = ?', (row['uuid'],)).fetchall()
    conn.close()
    
    key_map = {
        'unit': 'user_unit',
        'skill': 'user_skill',
        'music': 'user_music',
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
    ud['uuid'] = row['uuid']
    ud['device_uuid'] = row['device_uuid']
    ud['u_id'] = row['u_id']
    ud['u_seq'] = row['u_seq']
    ud['u_cp'] = row['u_cp']
    ud['u_candy'] = row['u_candy']
    ud['u_like'] = row['u_like']
    ud['u_fans'] = row['u_fans']
    ud['attendance_count'] = row['attendance_count']
    ud['attendance_date'] = row['attendance_date']
    return data

def get_user(uuid):
    with _LOCK:
        if not uuid: return None
        conn = get_db()
        row = conn.execute('SELECT * FROM user_data WHERE uuid = ?', (uuid,)).fetchone()
        if not row:
            row = conn.execute('SELECT * FROM user_data WHERE device_uuid = ? OR u_id = ? OR u_seq = ?', 
                               (uuid, uuid, uuid if uuid.isdigit() else -1)).fetchone()

        if row:
            user = _reconstruct_user(row)
            conn.close()
            return user
            
        conn.close()
        return None

def create_user(uuid, device_uuid):
    with _LOCK:
        existing = get_user(uuid)
        if existing: return existing
        
        seq = _next_seq()
        u_id = f'guest_{seq}'
        user = {
            'uuid': uuid,
            'userdata': _default_userdata(seq, u_id, uuid, device_uuid),
            'areas': _default_areas(),
            'achievements': [{'i_id': i, 'i_Level': 1, 'd_Quantity': 1.0, 's_Quantity': ''} for i in range(1, 11)],
            'characters': [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}],
            'costumes': [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}],
        }
        
        # A new profile starts empty.  The old seeded values (1,000,000 CP and
        # 100,000 Candy) made every purchase effectively free.
        u_cp = 0
        u_candy = 0.0
        u_like = 0.0
        u_fans = 0
        att_count = 0
        att_date = 0
        
        conn = get_db()
        conn.execute('''
            INSERT INTO user_data 
            (uuid, device_uuid, u_id, u_seq, u_cp, u_candy, u_like, u_fans, attendance_count, attendance_date, user_contents_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (uuid, device_uuid, u_id, seq, u_cp, u_candy, u_like, u_fans, att_count, att_date, json.dumps(user, ensure_ascii=False)))
        conn.commit()
        conn.close()
        
        ud = user['userdata']
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
            'costumes': 'costume',
            'user_prop': 'prop',
            'user_follower': 'follower',
            'user_follower_giftitem': 'gift',
            'user_shop': 'shop'
        }
        
        for jkey, itype in key_map.items():
            # Store inventory separately without mutating the in-memory lists.
            lst = stored.pop(jkey, [])
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
        
        conn.execute('''
            UPDATE user_data 
            SET user_contents_json = ? 
            WHERE uuid = ?
        ''', (json.dumps(stored, ensure_ascii=False), uuid))
        conn.commit()
        conn.close()

def increment_currency(uuid, cp=0, candy=0.0, like=0.0, fans=0):
    with _LOCK:
        conn = get_db()
        ruuid = _resolve_uuid(conn, uuid)
        if ruuid is not None:
            conn.execute('''
                UPDATE user_data
                SET u_cp = u_cp + ?, u_candy = u_candy + ?, u_like = u_like + ?, u_fans = u_fans + ?
                WHERE uuid = ?
            ''', (cp, candy, like, fans, ruuid))
            conn.commit()
        conn.close()


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

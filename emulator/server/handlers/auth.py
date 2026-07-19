import time, os, json
from server import state
from server.handlers.registry import cmd, OK, _payload

# --- "unlock everything" catalogue, loaded once from game_data.json -----------------------------
# game_data.json is a {table_id: [rows]} map; each row's column "1" is the item id.
#   table 3  = costumes (trang phục)   table 20 = guitars (đàn)   table 2 = music discs (đĩa nhạc)
# We expose every catalogued id on login so all costumes/guitars/music show up as owned.
_GAMEDATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'gamedata', 'game_data.json')
_CATALOG = None  # {'costume': [...ids], 'guitar': [...ids], 'music': [...ids]}

def _catalog():
    global _CATALOG
    if _CATALOG is not None:
        return _CATALOG
    cat = {'costume': [], 'guitar': [], 'music': []}
    try:
        with open(_GAMEDATA_PATH, encoding='utf-8') as f:
            gd = json.load(f)
        def ids(table_id):
            seen = []
            for row in gd.get(table_id, []):
                i = row.get('1')
                if isinstance(i, int) and i not in seen:
                    seen.append(i)
            return sorted(seen)
        cat = {'costume': ids('3'), 'guitar': ids('20'), 'music': ids('2')}
    except Exception:
        pass  # fall back to whatever the user already owns
    _CATALOG = cat
    return _CATALOG

def _all_costumes():
    return [{'i_id': i, 'i_Level': 1, 'i_BonusLevel': 0} for i in _catalog()['costume']]

def _all_guitars():
    return [{'i_id': i, 'i_Level': 1, 'i_BonusLevel': 0} for i in _catalog()['guitar']]

def _all_music():
    return [{'i_id': i, 'i_Level': 1, 'i_BonusLevel': 0, 'b_EncoreBonusAppear': 0,
             'l_EncoreBonusActivateTime': 0, 'i_EncoreBonusFollowerId': 0, 'i_ChThirdActiveTime': 0}
            for i in _catalog()['music']]

@cmd('userJoin')
def h_user_join(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or p.get('device_uuid') or ctx.get('uuid')
    device_uuid = p.get('device_uuid', '')
    user = state.create_user(uuid, device_uuid)
    ud = user['userdata']
    return {'u_seq': ud['u_seq'], 'u_id': ud['u_id']}, OK

def _user_contents(user):
    return {
        'user_achievement': user.get('achievements', []),
        'user_candy_shop': [
            {'i_id': 1, 'i_CurrentBuyCount': 1, 'i_TotalBuyCount': 1, 'l_LastBuyTick': 1767022695, 'upd_day': 20251230},
            {'i_id': 2, 'i_CurrentBuyCount': 1, 'i_TotalBuyCount': 1, 'l_LastBuyTick': 1767114498, 'upd_day': 20251231},
        ],
        'user_character': user.get('characters', []),
        # unlock-all: every costume in the catalogue (table 3), not just the ones the user bought
        'user_costume': _all_costumes(),
        'user_daily_mission': user.setdefault('user_daily_mission', [
            {'i_id': 1, 'i_Level': 1, 'd_Quantity': 1, 'upd_date': ''},
            {'i_id': 2, 'i_Level': 1, 'd_Quantity': 0, 'upd_date': ''},
            {'i_id': 3, 'i_Level': 1, 'd_Quantity': 0, 'upd_date': ''},
            {'i_id': 4, 'i_Level': 1, 'd_Quantity': 0, 'upd_date': ''},
            {'i_id': 5, 'i_Level': 1, 'd_Quantity': 0, 'upd_date': ''},
            {'i_id': 6, 'i_Level': 1, 'd_Quantity': 0, 'upd_date': ''},
        ]),
        'user_follower': user.setdefault('user_follower', [
            {'i_id': 1, 'i_Level': 125, 'i_BonusLevel': 5},
            {'i_id': 2, 'i_Level': 48, 'i_BonusLevel': 1},
            {'i_id': 3, 'i_Level': 13, 'i_BonusLevel': 0},
            {'i_id': 4, 'i_Level': 1, 'i_BonusLevel': 0},
        ]),
        # unlock-all: every music disc in the catalogue (table 2)
        'user_music': _all_music(),
        'user_prop': user.setdefault('user_prop', [{'i_id': 1, 'i_Level': 1}, {'i_id': 2, 'i_Level': 1}]),
        'user_unit': user.setdefault('user_unit', [{'i_id': 1, 'i_Level': 1}]),
        'user_skill': user.setdefault('user_skill', [
            {'i_id': 1, 'i_Level': 1, 'b_Activate': 0, 'l_ActivateOnTicks': 0, 'l_ActivateOffTicks': 0},
            {'i_id': 4, 'i_Level': 1, 'b_Activate': 0, 'l_ActivateOnTicks': 0, 'l_ActivateOffTicks': 0},
        ]),
        'user_shop': user.setdefault('user_shop', []),
        'user_messenger': [
            {'i_MessengerChatRoomId': i, 'i_LastConfirmIndex': 9999, 's_UnlockGroupList': ','.join(map(str, range(1, 50))), 'l_UpdateTimeTicks': 639013642974540000} 
            for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 203, 204, 205, 206, 207, 208, 100000]
        ],
        # unlock-all: every guitar in the catalogue (table 20)
        'user_guitar': _all_guitars(),
        # Star Pass: read from persisted user data, default to fresh start
        'user_event_point': user.setdefault('user_event_point', [
            {'s_EventType': 'Pass', 'i_DataID': 5, 'i_Point': 0, 'i_Step': 0, 'i_ADViewTime': 0, 'i_Version': 5},
        ]),
        'user_subscribe_pass_reward': user.setdefault('user_subscribe_pass_reward', []),
        'user_ticketcollection': [{'i_id': i} for i in range(1, 14)],
        'user_follower_profile_reward': [
            {'i_id': f, 'i_RewardLevel': lvl} 
            for f in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 201, 202, 203, 204, 205, 206, 207, 208] 
            for lvl in range(1, 6)
        ],
        'user_follower_profile': user.setdefault('user_follower_profile', [
            {'i_id': 1, 'i_Level': 3, 'd_Exp': 150, 'i_AddCandy': 0},
            {'i_id': 2, 'i_Level': 2, 'd_Exp': 110, 'i_AddCandy': 0},
            {'i_id': 3, 'i_Level': 2, 'd_Exp': 70, 'i_AddCandy': 0},
        ]),
        'user_follower_giftitem': user.setdefault('user_follower_giftitem', [{'i_id': 1, 'i_Value': 141}]),
        'user_tutorial': [{'i_id': i} for i in range(1, 8)],
        'user_ad_level': [{'i_id': 210010, 'i_Level': 1, 'i_EXP': 1}],
    }

@cmd('userLogin')
def h_user_login(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or p.get('device_uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    if not user:
        user = state.create_user(uuid, p.get('device_uuid', ''))
    u_seq_req = p.get('u_seq', 0) or 0
    if u_seq_req != 0:
        area_map = {int(k): v for k, v in user.get('areas', {}).items()}
        ud = user['userdata']
        ct = str(ud.get('u_create_time', ''))
        if not ct.lstrip('-').isdigit():
            ud['u_create_time'] = str(int(time.time()))
        return {
            'user': ud,
            'area_data': area_map,
            'user_contents': _user_contents(user),
        }, OK
    ud = user['userdata']
    return {'user': {'u_seq': ud['u_seq'], 'u_id': ud['u_id']}}, OK

@cmd('userSave')
def h_user_save(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    if user:
        if 'user_achievement' in p: user['achievements'] = p['user_achievement']
        if 'user_character' in p:   user['characters'] = p['user_character']
        if 'user_costume' in p:     user['costumes'] = p['user_costume']
        if 'user_event_point' in p: user['user_event_point'] = p['user_event_point']
        if 'user_daily_mission' in p: user['user_daily_mission'] = p['user_daily_mission']
        for area in (p.get('user_area_info') or []):
            n = area.get('u_area_num')
            if n is not None:
                user.setdefault('areas', {})[str(n)] = area
        state.save_user(user)
    return {'status': 'Y'}, OK

@cmd('userLoad')
def h_user_load(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    if p.get('type') == 'shop' and user:
        return {'user_contents': {'user_shop': user.get('user_shop', [])}}, OK
    return {}, OK

@cmd('setSubscribe')
def h_set_subscribe(req, player, ctx):
    p = _payload(req)
    now = int(time.time())
    subs = [{'i_SubscribeID': i + 1, 'i_ActiveTime': now, 'i_isActive': 1} for i in range(100)]
    return {'u_seq': p.get('u_seq', 0), 'user_subscribe_list': subs}, OK

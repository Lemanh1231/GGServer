"""Handler for main.getGameDataList with dynamic event synchronization.

Controls runtime availability of:
- Meowfest / SamSeck event (samseckevent table):
  * When enabled: serves the 3 milestone conditions (Guitar 10, Costume 13, Unit 1).
  * When disabled: serves an empty list [] so client controller disables and hides
    the lobby 'Sự kiện Meow' side icon.
- Attendance & Login events (event_list table):
  * Synchronizes b_IsActive (0/1) with event_manager.is_attendance_event_enabled(idx).

Provides sub-millisecond cached responses invalidated on event config change.
"""
import copy
import os
import threading
import time
import codec
from server import event_manager, dispatch
from server.handlers.registry import cmd, OK

GAMEDATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'gamedata', 'getGameDataList.b64')

_BASE_RET = None
_BASE_SAMSECK = None
_LOCK = threading.Lock()
_CACHE = {}  # cache_key -> base64_encoded_response


def _load_base():
    global _BASE_RET, _BASE_SAMSECK
    if _BASE_RET is not None:
        return _BASE_RET, _BASE_SAMSECK
    with open(GAMEDATA_PATH, 'r', encoding='utf-8') as f:
        b64 = f.read().strip()
    decoded, _ = codec.decode_request(b64, 'main.getGameDataListReturn')
    _BASE_RET = decoded['data']['ret']
    _BASE_SAMSECK = copy.deepcopy(_BASE_RET.get('samseckevent', []))
    return _BASE_RET, _BASE_SAMSECK


def invalidate_cache():
    with _LOCK:
        _CACHE.clear()


def build_filtered_ret():
    base_ret, base_samseck = _load_base()
    ret = dict(base_ret)

    # 1. Meowfest (SamSeck)
    if event_manager.is_meowfest_enabled():
        ret['samseckevent'] = copy.deepcopy(base_samseck)
    else:
        ret['samseckevent'] = []

    # 2. Attendance event_list
    orig_events = base_ret.get('event_list', [])
    filtered_events = []
    for ev in orig_events:
        ev_copy = dict(ev)
        eidx = str(ev.get('idx', ''))
        is_active = 1 if event_manager.is_attendance_event_enabled(eidx) else 0
        ev_copy['b_IsActive'] = is_active
        if is_active:
            ev_copy['start_date'] = '0001-01-01 00:00:00'
            ev_copy['end_date'] = '9999-12-31 23:59:00'
        else:
            ev_copy['start_date'] = '2020-01-01 00:00:00'
            ev_copy['end_date'] = '2020-01-01 00:00:00'
        filtered_events.append(ev_copy)
    ret['event_list'] = filtered_events

    # 3. Star Pass (SubscribeList)
    sp_enabled = event_manager.is_star_pass_enabled()
    active_season = event_manager.get_active_star_pass_season()
    orig_subscribes = base_ret.get('SubscribeList', [])
    filtered_subscribes = []
    now_t = time.localtime()
    current_month = now_t.tm_mon

    # Original month of the active season
    active_orig_month = current_month
    for sub in orig_subscribes:
        if int(sub.get('i_id', 0) or 0) == active_season:
            active_orig_month = int(sub.get('i_RepeatMonth', current_month) or current_month)
            break

    for sub in orig_subscribes:
        sub_copy = dict(sub)
        sid = int(sub.get('i_id', 0) or 0)
        orig_month = int(sub.get('i_RepeatMonth', 1) or 1)

        if sp_enabled and sid == active_season:
            sub_copy['b_IsActive'] = 1
            sub_copy['i_TimeLimit'] = 1
            sub_copy['i_RepeatMonth'] = current_month
        elif sp_enabled and orig_month == current_month and active_season != sid:
            # Swap month with the active season to prevent month dictionary collisions
            sub_copy['b_IsActive'] = 0
            sub_copy['i_TimeLimit'] = 1
            sub_copy['i_RepeatMonth'] = active_orig_month
        else:
            sub_copy['b_IsActive'] = 0
            sub_copy['i_TimeLimit'] = 1
            sub_copy['i_RepeatMonth'] = orig_month

        # Strictly preserve original start year and month group index
        sub_copy['i_StartYear'] = sub.get('i_StartYear', 2020 if sid <= 5 else 2021)
        sub_copy['i_MonthGroupIndex'] = sub.get('i_MonthGroupIndex', 0)
        filtered_subscribes.append(sub_copy)
    ret['SubscribeList'] = filtered_subscribes

    return ret


def get_game_data_list_b64(category='main'):
    # Cache key includes all event toggle states affecting getGameDataList
    mf_enabled = event_manager.is_meowfest_enabled()
    sp_enabled = event_manager.is_star_pass_enabled()
    active_season = event_manager.get_active_star_pass_season()
    att_states = tuple(event_manager.is_attendance_event_enabled(k) for k in ('1', '2', '3', '202110', '202111'))
    cache_key = (mf_enabled, sp_enabled, active_season, att_states, category)

    with _LOCK:
        if cache_key in _CACHE:
            return _CACHE[cache_key]

    ret = build_filtered_ret()
    rdto, env = dispatch.build_return('main.getGameDataList', {'ret': ret}, call='getGameDataList', category=category)
    out_b64 = codec.encode_response(rdto, env)

    with _LOCK:
        _CACHE[cache_key] = out_b64
    return out_b64


@cmd('getGameDataList')
def h_get_game_data_list(req, player, ctx):
    ret = build_filtered_ret()
    return {'ret': ret}, OK

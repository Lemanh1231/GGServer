import os, time, json
from server import state
from server.handlers.registry import cmd, OK, _payload

EVENT_REWARDS = None
_EVENT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'event_config.json')

def _event_settings():
    """Read operator-controlled event availability on every request.

    This intentionally is not cached: changing `event_config.json` opens or
    closes an event immediately, without modifying player data or restarting
    the server.
    """
    try:
        with open(_EVENT_CONFIG_PATH, encoding='utf-8') as f:
            config = json.load(f)
        return config if isinstance(config, dict) else {}
    except (OSError, ValueError, TypeError):
        return {'events': {'1': {'enabled': True}}}

def _event_config():
    return _event_settings().get('events', {})

def _event_enabled(event_idx):
    event = _event_config().get(str(event_idx), {})
    return bool(event.get('enabled', False))

def _paid_star_card_enabled():
    return bool(_event_settings().get('paid_star_card', {}).get('enabled', False))

# game_data.json is the decoded getGameDataList payload.  These three tables
# describe exactly which Free/Paid reward belongs to each Star Pass group/step.
_PASS_REWARD_DATA = None


def _pass_rewards(group, step, reward_type):
    """Return the actual rewards for a Star Pass claim.

    Table 18 (SubscribePassReward) maps (group, step, type) to a reward group;
    table 13 (reward_group) expands that group to one or more retReward items.
    """
    global _PASS_REWARD_DATA
    if _PASS_REWARD_DATA is None:
        _PASS_REWARD_DATA = ({}, {})
        try:
            path = os.path.join(os.path.dirname(__file__), '..', '..', 'gamedata', 'game_data.json')
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            pass_rows = {
                (int(row.get('2', 0)), int(row.get('3', 0))): row
                for row in data.get('18', [])
            }
            groups = {}
            for row in data.get('13', []):
                groups.setdefault(int(row.get('2', 0)), []).append({
                    'reward_type': int(row.get('3', 0)),
                    'reward_id': int(row.get('4', 0)),
                    'reward_value': int(row.get('5', 0)),
                })
            _PASS_REWARD_DATA = (pass_rows, groups)
        except Exception:
            pass

    pass_rows, groups = _PASS_REWARD_DATA
    row = pass_rows.get((int(group), int(step)))
    if not row:
        return []
    reward_group = int(row.get('6' if int(reward_type) else '5', 0))
    return list(groups.get(reward_group, []))
def _get_event_rewards():
    global EVENT_REWARDS
    if EVENT_REWARDS is not None: return EVENT_REWARDS
    EVENT_REWARDS = {}
    try:
        p = os.path.join(os.path.dirname(__file__), '..', '..', 'gamedata', 'getEventRewardList.b64')
        with open(p) as f: b64 = f.read()
        import codec
        decoded, _ = codec.decode_request(b64, 'main.getEventRewardListReturn')
        for k, v in decoded.get('data', {}).items():
            lst = v.get('reward_list', [])
            EVENT_REWARDS[str(k)] = {}
            for r in lst:
                EVENT_REWARDS[str(k)][str(r.get('reward_num'))] = {
                    'reward_type': r.get('reward_type'),
                    'reward_id': r.get('reward_id'),
                    'reward_value': r.get('reward_value')
                }
    except Exception as e:
        pass
    return EVENT_REWARDS

EVENT_TEMPLATE = None
def _get_event_template():
    """Full decoded getEventRewardList data map: {event_idx: {'reward_list':[...], 'group_idx':N}}.
    Unlike _get_event_rewards() this keeps every field (reward_flg, get_date, icons, ...) so the
    dynamic handler can overlay per-user claim state and re-emit the whole board."""
    global EVENT_TEMPLATE
    if EVENT_TEMPLATE is not None:
        return EVENT_TEMPLATE
    EVENT_TEMPLATE = {}
    try:
        p = os.path.join(os.path.dirname(__file__), '..', '..', 'gamedata', 'getEventRewardList.b64')
        with open(p) as f:
            b64 = f.read()
        import codec
        decoded, _ = codec.decode_request(b64, 'main.getEventRewardListReturn')
        EVENT_TEMPLATE = decoded.get('data', {}) or {}
    except Exception:
        EVENT_TEMPLATE = {}
    return EVENT_TEMPLATE

def _today_ymd():
    return int(time.strftime('%Y%m%d', time.localtime()))

def _att_state(user, event_idx):
    return user.setdefault('attendance', {}).setdefault(str(event_idx), {'day': 0, 'ymd': 0})

def _event_max_day(event_idx):
    return len(_get_event_rewards().get(str(event_idx), {})) or 7

def _claim_day(st, max_day, today):
    if st.get('ymd') == today:
        return st.get('day', 1) or 1
    nxt = st.get('day', 0) + 1
    if nxt > max_day:
        nxt = 1
    return nxt

def _event_resp(ud, rew, status):
    rd = [rew] if rew else []
    return {
        'u_cp': ud.get('u_cp', 0), 'u_candy': ud.get('u_candy', 0.0),
        'u_like': ud.get('u_like', 0.0), 'u_fans': ud.get('u_fans', 0),
        'reward_type': (rew or {}).get('reward_type', 0),
        'reward_id': (rew or {}).get('reward_id', 0),
        'reward_value': (rew or {}).get('reward_value', 0),
        'status': status, 'reward_data': rd,
    }

def _give_reward(user, rew):
    rtype = rew.get('reward_type', 0)
    rid = rew.get('reward_id', 0)
    rval = float(rew.get('reward_value', 0))
    if not user: return
    uuid = user.get('uuid')
    ud = user['userdata']
    if rtype in (1, 11): # Goods / Table 1
        cp = candy = like = fans = 0
        if rtype == 11 or rid == 11: # Cookies / AP
            state.add_ap(user, int(rval))
        elif rid == 1: 
            cp = int(rval)
            ud['u_cp'] = int(ud.get('u_cp', 0) or 0) + cp
        elif rid == 2: 
            candy = rval
            ud['u_candy'] = ud.get('u_candy', 0.0) + candy
        elif rid in (3, 4): 
            like = rval
            ud['u_like'] = ud.get('u_like', 0.0) + like
        elif rid == 8: 
            fans = int(rval)
            ud['u_fans'] = ud.get('u_fans', 0) + fans
        if uuid and (cp or candy or like or fans):
            state.increment_currency(uuid, cp=cp, candy=candy, like=like, fans=fans)
    elif rtype == 2: # Music
        lst = user.setdefault('user_music', [])
        if not any(x.get('i_id') == rid for x in lst):
            lst.append({'i_id': rid, 'i_Level': 1, 'i_BonusLevel': 0, 'b_EncoreBonusAppear': 0, 'l_EncoreBonusActivateTime': 0, 'i_EncoreBonusFollowerId': 0, 'i_ChThirdActiveTime': 0})
    elif rtype == 3: # Costume
        lst = user.setdefault('costumes', [])
        if not any(x.get('i_id') == rid for x in lst): lst.append({'i_id': rid})
    elif rtype == 4: # Prop
        lst = user.setdefault('user_prop', [{'i_id': 1, 'i_Level': 1}, {'i_id': 2, 'i_Level': 1}])
        if not any(x.get('i_id') == rid for x in lst): lst.append({'i_id': rid, 'i_Level': 1})
    elif rtype == 5: # Follower
        lst = user.setdefault('user_follower', [])
        if not any(x.get('i_id') == rid for x in lst):
            lst.append({'i_id': rid, 'i_Level': 1, 'i_BonusLevel': 0})
            from server.handlers.follower import _sync_follower_messenger
            _sync_follower_messenger(user)
    elif rtype == 7: # Unit
        lst = user.setdefault('user_unit', [])
        if not any(x.get('i_id') == rid for x in lst): lst.append({'i_id': rid, 'i_Level': 1})

@cmd('setAttendance')
def h_set_attendance(req, player, ctx):
    """Serve the daily-login event through the client's normal check/add flow.

    The client sends `add` during initial entry sequence to record daily login.
    The actual 7-day attendance board reward is claimed explicitly via setEventReward.
    """
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    rtype = p.get('type', 'check')
    user = state.get_user(uuid)
    today = _today_ymd()
    cur = 0
    added = False
    if not _event_enabled(1):
        return {
            'status': 'N', 'attendance_count': 0, 'attendance_date': 0,
            'max_coutinuous_attendance_count': 0,
        }, OK
    max_day = _event_max_day(1)
    if user:
        ud = user.setdefault('userdata', {})
        st = _att_state(user, 1)
        if rtype == 'add':
            last_date = int(ud.get('attendance_date', 0) or 0)
            if last_date != today:
                att_cnt = int(ud.get('attendance_count', 0) or 0) + 1
                ud['attendance_count'] = att_cnt
                ud['attendance_date'] = today
                max_cnt = max(int(ud.get('max_coutinuous_attendance_count', 0) or 0), att_cnt)
                ud['max_coutinuous_attendance_count'] = max_cnt
                state.update_attendance(user.get('uuid'), att_cnt, today)
                state.save_user(user)
                added = True
        claimed_today = (st.get('ymd') == today)
        cur = st.get('day', 1) if claimed_today else _claim_day(st, max_day, today)
    else:
        claimed_today = False
        cur = 1
    return {
        'status': 'Y' if added else ('N' if (claimed_today or (user and int(user.get('userdata', {}).get('attendance_date', 0) or 0) == today)) else 'Y'),
        'attendance_count': cur,
        'attendance_date': today if (claimed_today or added) else 0,
        'max_coutinuous_attendance_count': cur,
    }, OK

@cmd('getEventRewardList')
def h_get_event_reward_list(req, player, ctx):
    # Built per-user (NOT static) so the attendance board reflects what the player already
    # claimed. The board is sequential: day 1, then day 2 the next calendar day, ... The server
    # records progress in user['attendance'][event_idx] = {'day': last claimed day, 'ymd': last
    # claim date} via setEventReward. We overlay that here:
    #   - days already claimed (reward_num <= day)  -> reward_flg='N' + get_date=<claim date>
    #   - days not yet claimed                      -> left as the template (reward_flg='Y')
    # so the client greys out claimed days and lets the next day be claimed tomorrow.
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    today = _today_ymd()
    template = _get_event_template()
    data = {}
    for eidx, board in template.items():
        if not _event_enabled(eidx):
            continue
        st = _att_state(user, eidx) if user else {'day': 0, 'ymd': 0}
        claimed_day = st.get('day', 0)
        claim_ymd = st.get('ymd', 0)
        rl = []
        for r in board.get('reward_list', []):
            r2 = dict(r)
            if claimed_day and r2.get('reward_num', 0) <= claimed_day:
                r2['reward_flg'] = 'N'                      # already received
                r2['get_date'] = claim_ymd or r2.get('get_date', 0)
            else:
                # The captured template is a retired live-event response and
                # carries its original 2024/2025 get_date values.  They are
                # not this player's history; the client interprets them as
                # already-passed attendance days and paints several seals on
                # a fresh account.  An unclaimed reward has no claim date.
                r2['get_date'] = 0
            rl.append(r2)
        data[eidx] = {'reward_list': rl, 'group_idx': board.get('group_idx', 0)}
    return data, OK

@cmd('setEventReward')
def h_set_event_reward(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    event_idx = str(p.get('event_idx', 1))
    if not _event_enabled(event_idx):
        return _event_resp({}, None, 'N'), OK
    rewards = _get_event_rewards().get(event_idx, {})
    max_day = len(rewards) or 7

    if not user:
        rew = rewards.get('1') or {'reward_type': 1, 'reward_id': 1, 'reward_value': 100}
        return _event_resp({}, rew, 'Y'), OK

    ud = user['userdata']
    st = _att_state(user, event_idx)
    today = _today_ymd()

    if st.get('ymd') == today:
        return _event_resp(ud, None, 'N'), OK

    day = st.get('day', 0) + 1
    if day > max_day:
        day = 1
    rew = rewards.get(str(day)) or {'reward_type': 1, 'reward_id': 1, 'reward_value': 100}

    _give_reward(user, rew)
    st['day'] = day
    st['ymd'] = today
    if event_idx == '1':
        ud['attendance_count'] = day
        ud['attendance_date'] = today
        state.update_attendance(uuid, day, today)
    state.save_user(user)
    return _event_resp(ud, rew, 'Y'), OK

@cmd('setGameReward')
def h_set_game_reward(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    req_type = p.get('type', 'daily_mission')
    item_id = str(p.get('id', 1))
    try:
        level = int(p.get('level', 1))
    except (TypeError, ValueError):
        level = 1
    if level < 1:
        level = 1

    today = str(_today_ymd())
    claim_key = f'{item_id}:{level}'

    reward_type = 'CP'
    rval = 0

    try:
        _gd_path = os.path.join(os.path.dirname(__file__), '..', '..', 'gamedata', 'game_data.json')
        with open(_gd_path, 'r', encoding='utf-8') as f:
            gamedata = json.load(f)

        if req_type == 'daily_mission':
            for row in gamedata.get('10', []):
                if str(row.get('1')) == item_id:
                    reward_type = str(row.get('29', 'CP')).strip() or 'CP'
                    rval = int(row.get('42', 10))
                    break
        elif req_type == 'achievement':
            for row in gamedata.get('9', []):
                if str(row.get('1')) == item_id:
                    reward_type = str(row.get('28', 'CP')).strip() or 'CP'
                    val_key = str(40 + level)
                    rval = int(row.get(val_key, 0))
                    break
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass

    if req_type not in ('daily_mission', 'achievement'):
        return {
            'type': req_type, 'id': int(item_id) if item_id.isdigit() else 0,
            'level': level, 'reward_type': 'None', 'reward_value': 0,
            'status': 'N', 'user_follower_profile': {}
        }, OK

    if user:
        if req_type == 'daily_mission':
            if not user.get('user_daily_mission'):
                from server.handlers.auth import _normalise_daily_missions
                _normalise_daily_missions(user)
            claims = user.setdefault('claimed_daily_rewards', {})
            today_claims = claims.setdefault(today, {})
            for old_day in [day for day in list(claims.keys()) if day != today]:
                del claims[old_day]
            already_claimed = claim_key in today_claims
            current_level = level
            for m in user.get('user_daily_mission', []):
                if str(m.get('i_id')) == item_id:
                    current_level = int(m.get('i_Level', level) or level)
                    break
            if already_claimed:
                return {
                    'type': req_type,
                    'id': int(item_id) if item_id.isdigit() else 1,
                    'level': max(current_level, level + 1),
                    'reward_type': '0',
                    'reward_value': 0,
                    'status': 'N',
                    'user_follower_profile': {},
                }, OK
            today_claims[claim_key] = int(time.time())
            if reward_type.upper() == 'CP' and rval > 0:
                state.increment_currency(uuid, cp=rval)
                user.setdefault('userdata', {})['u_cp'] = user['userdata'].get('u_cp', 0) + rval
            for m in user.setdefault('user_daily_mission', []):
                if str(m.get('i_id')) == item_id:
                    m['i_Level'] = max(int(m.get('i_Level', 1) or 1), level + 1)
                    break
            _DM_TARGETS = {1: 1, 2: 2000, 3: 30, 4: 5, 5: 1800}
            missions = user.setdefault('user_daily_mission', [])
            completed_count = sum(
                1 for m in missions
                if 1 <= int(m.get('i_id', 0) or 0) <= 5 and (
                    m.get('d_Quantity', 0) >= _DM_TARGETS.get(int(m.get('i_id', 0) or 0), 1)
                    or int(m.get('i_Level', 1) or 1) >= 2
                )
            )
            for m in missions:
                if int(m.get('i_id', 0) or 0) == 6:
                    m['d_Quantity'] = max(int(m.get('d_Quantity', 0) or 0), completed_count)
                    break
            next_level = level + 1
        else:
            claims = user.setdefault('claimed_achievement_rewards', {})
            already_claimed = claim_key in claims
            current_level = level
            for a in user.get('achievements', []):
                if str(a.get('i_id')) == item_id:
                    current_level = int(a.get('i_Level', level) or level)
                    break
            if already_claimed:
                return {
                    'type': req_type,
                    'id': int(item_id) if item_id.isdigit() else 1,
                    'level': max(current_level, level + 1),
                    'reward_type': '0',
                    'reward_value': 0,
                    'status': 'N',
                    'user_follower_profile': {},
                }, OK
            claims[claim_key] = int(time.time())
            if reward_type.upper() == 'CP' and rval > 0:
                state.increment_currency(uuid, cp=rval)
                user.setdefault('userdata', {})['u_cp'] = user['userdata'].get('u_cp', 0) + rval
            found = False
            for a in user.setdefault('achievements', []):
                if str(a.get('i_id')) == item_id:
                    a['i_Level'] = max(int(a.get('i_Level', 1) or 1), level + 1)
                    found = True
                    break
            if not found:
                user['achievements'].append({
                    'i_id': int(item_id),
                    'i_Level': level + 1,
                    'd_Quantity': 0.0,
                    's_Quantity': '',
                })
            next_level = level + 1

        # Award Star Pass points
        evp_list = user.setdefault('user_event_point', [
            {'s_EventType': 'Pass', 'i_DataID': 13, 'i_Point': 0, 'i_Step': 0, 'i_ADViewTime': 0, 'i_Version': 13}
        ])
        for ep in evp_list:
            if ep.get('s_EventType') == 'Pass':
                ep['i_Point'] = ep.get('i_Point', 0) + 10
                break

        state.save_user(user)
    else:
        next_level = level + 1

    return {
        'type': req_type,
        'id': int(item_id) if item_id.isdigit() else 1,
        'level': next_level,
        'reward_type': reward_type,
        'reward_value': rval,
        'status': 'Y',
        'user_follower_profile': {},
    }, OK

@cmd('updateAchievement')
def h_update_achievement(req, player, ctx):
    p = _payload(req)
    # the client just wants us to acknowledge the achievement step
    ach = p.get('achievement', 0) or p.get('u_achievement', 0)
    return {'achievement': ach}, OK

@cmd('setPassReward')
def h_set_pass_reward(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    
    group = p.get('group', 0)
    step = p.get('step', 0)
    ptype = p.get('type', 0)
    
    group = int(group)
    step = int(step)
    ptype = int(ptype)
    version = p.get('i_Version', 5)
    now = int(time.time())
    claim = {
        'i_SubscribeID': group,
        'i_Type': ptype,
        'i_Step': step,
        'i_UpdateTime': now,
        'i_Version': version,
    }
    rewards = _pass_rewards(group, step, ptype)

    if user:
        # type 0 is the Free Star Pass track.  type 1 is the paid/gold track
        # and may only be claimed when a real entitlement is present.  The
        # emulator deliberately never creates that entitlement.
        paid_active = any(item.get('i_SubscribeID') in (group, 1000 + group)
                          and item.get('i_isActive') for item
                          in user.get('user_subscribe_list', []))
        if ptype == 1 and not paid_active:
            rewards = []
            return {
                'subscribe_pass_reward': claim,
                'reward_data': rewards,
            }, OK
        lst = user.setdefault('user_subscribe_pass_reward', [])
        existing = next((item for item in lst
                         if item.get('i_SubscribeID') == group
                         and item.get('i_Type') == ptype
                         and item.get('i_Step') == step
                         and item.get('i_Version', version) == version), None)
        if existing:
            # A retry must not duplicate the reward.  Echo the original claim
            # so the client can still reconcile its local state.
            claim = existing
            rewards = []
        else:
            for reward in rewards:
                _give_reward(user, reward)
            lst.append(claim)
            state.save_user(user)

    return {
        'subscribe_pass_reward': claim,
        'reward_data': rewards,
    }, OK

@cmd('setAdReward')
def h_set_ad_reward(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    with state._LOCK:
        user = state.get_user(uuid)
        try:
            i_id = int(p.get('i_id', 0))
            profile_id = int(p.get('param1', 0))
        except (TypeError, ValueError):
            return {}, OK

        # Capture: adViewLog(ad_profile_free_gift), followed by
        # setAdReward(i_id=1, param1=<profile id>). Game table 32 configures
        # this as PROFILE_EXP: 300 hearts/EXP, 10-minute cooldown, 5 per day.
        if i_id == 1 and profile_id > 0 and user:
            from server.handlers.follower import _apply_profile_exp, _follower_data
            profiles_def, gifts_def, level_data, f_to_p, followers_tbl = _follower_data()
            raw_profile_id = profile_id
            profile_id = f_to_p.get(raw_profile_id, raw_profile_id)

            now = int(time.time())
            today = _today_ymd()
            ad_rewards = user.setdefault('ad_rewards', {})
            slot = ad_rewards.setdefault('1', {
                'i_id': 1, 'i_Count': 0, 'i_TotalCount': 0, 'i_LastViewTime': 0, 'upd_day': today,
            })
            if int(slot.get('upd_day', 0) or 0) != today:
                slot['i_Count'] = 0
                slot['upd_day'] = today

            profiles = user.setdefault('user_follower_profile', [])
            profile = next((row for row in profiles
                            if int(row.get('i_id', 0) or 0) in (profile_id, raw_profile_id)), None)
            followers = user.setdefault('user_follower', [])
            follower = next((row for row in followers
                             if int(row.get('i_id', 0) or 0) in (profile_id, raw_profile_id)), None)

            if profile is None:
                profile = {'i_id': profile_id, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0}
                profiles.append(profile)

            if follower is None and raw_profile_id != 100000:
                follower = {'i_id': raw_profile_id, 'i_Level': 1, 'i_BonusLevel': 0}
                followers.append(follower)

            cur_count = int(slot.get('i_Count', 0) or 0)
            last_time = int(slot.get('i_LastViewTime', 0) or 0)
            # Table 32: DAY_LIMIT = 5, COOLTIME = 600s
            allowed = (cur_count < 5 and (last_time == 0 or now - last_time >= 600))

            if allowed:
                p_levels = level_data.get(profile_id) or level_data.get(raw_profile_id) or level_data.get(1, {})
                curr_lvl = max(1, int(profile.get('i_Level', 1) or 1))
                req_curr = int(p_levels.get(curr_lvl, {}).get('4', 0) or 0)
                req_next = int(p_levels.get(curr_lvl + 1, {}).get('4', 0) or 0)
                delta_req = max(0, req_next - req_curr) if req_next > req_curr else 0
                ad_exp = max(100, min(300, int(delta_req * 0.1))) if delta_req > 0 else 100

                _apply_profile_exp(profile, p_levels, ad_exp)
                slot['i_Count'] = cur_count + 1
                slot['i_TotalCount'] = int(slot.get('i_TotalCount', 0) or 0) + 1
                slot['i_LastViewTime'] = now

                from server.handlers.follower import _sync_follower_profiles
                _sync_follower_profiles(user)

                state.save_user(user)
                rew_data = [{'reward_type': 0, 'reward_id': 0, 'reward_value': ad_exp}]
            else:
                rew_data = []

            return {
                'i_id': i_id,
                'user_ad_list': {
                    'i_id': 1,
                    'i_Count': int(slot.get('i_Count', 0) or 0),
                    'i_TotalCount': int(slot.get('i_TotalCount', 0) or 0),
                    'i_LastViewTime': int(slot.get('i_LastViewTime', 0) or 0),
                },
                'user_follower_profile': profile,
                'reward_data': rew_data,
            }, OK

        # Game table 32: ad_ap. It is a separate ad slot from the follower
        # profile ad: five views per day, no cooldown, reward group 1011 =
        # 25 Cookie (Chapter 3 AP).
        if i_id == 2 and user:
            from server.handlers.ch_third import _add_ap
            today = _today_ymd()
            now = int(time.time())
            ad_rewards = user.setdefault('ad_rewards', {})
            slot = ad_rewards.setdefault('2', {
                'i_id': 2, 'i_Count': 0, 'i_TotalCount': 0, 'i_LastViewTime': 0, 'upd_day': today,
            })
            if int(slot.get('upd_day', 0) or 0) != today:
                slot['i_Count'] = 0
                slot['upd_day'] = today

            allowed = int(slot.get('i_Count', 0) or 0) < 5
            if allowed:
                _add_ap(user, 25)
                slot['i_Count'] = int(slot.get('i_Count', 0) or 0) + 1
                slot['i_TotalCount'] = int(slot.get('i_TotalCount', 0) or 0) + 1
                slot['i_LastViewTime'] = now
                state.save_user(user)

            return {
                'i_id': i_id,
                'user_ad_list': {
                    'i_id': 2,
                    'i_Count': int(slot.get('i_Count', 0) or 0),
                    'i_TotalCount': int(slot.get('i_TotalCount', 0) or 0),
                    'i_LastViewTime': int(slot.get('i_LastViewTime', 0) or 0),
                },
                'reward_data': ([{'reward_type': 1, 'reward_id': 11, 'reward_value': 25}]
                                if allowed else []),
            }, OK

        # Preserve a neutral response for ad slots that have not been captured.
        return {
            'i_id': i_id,
            'user_ad_list': {'i_id': i_id, 'i_Count': 0, 'i_TotalCount': 0,
                             'i_LastViewTime': 0},
            'reward_data': [],
        }, OK

@cmd('adViewLog')
def h_ad_view_log(req, player, ctx):
    return {'status': 'Y'}, OK

def _get_pass_point_config(sub_id):
    try:
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'gamedata', 'game_data.json')
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        for r in data.get('19', []):
            if int(r.get('1', 0) or 0) == sub_id or int(r.get('2', 0) or 0) == sub_id:
                return {
                    'cp_cost': int(r.get('4', 50) or 50),
                    'paid_point': int(r.get('5', 5000) or 5000),
                    'ad_point': int(r.get('8', 2000) or 2000),
                    'ad_cooltime': int(r.get('9', 600) or 600)
                }
    except Exception:
        pass
    return {'cp_cost': 50, 'paid_point': 5000, 'ad_point': 2000, 'ad_cooltime': 600}

def _get_step_for_points(sub_id, points):
    try:
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'gamedata', 'game_data.json')
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        goals = [(int(r.get('3', 0)), int(r.get('4', 0))) for r in data.get('18', []) if int(r.get('2', 0)) == sub_id]
        goals.sort(key=lambda x: x[0])
        curr_step = 0
        for step, goal in goals:
            if points >= goal:
                curr_step = step
        return curr_step
    except Exception:
        return 0

@cmd('paidEventPoint')
def h_paid_event_point(req, player, ctx):
    """Star Pass 'Charge Up' – buy event points with CP or watch AD."""
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    if not user:
        return {}, {'code': 1, 'errmsg': 'User not found'}

    sub_id = int(p.get('i_SubscribeID', 13) or 13)
    version = int(p.get('i_Version', 0) or 0)
    ptype = int(p.get('type', 0) or 0)
    cfg = _get_pass_point_config(sub_id)

    ud = user.setdefault('userdata', {})
    if ptype == 1: # Paid with Chocolate (CP)
        cp_cost = cfg['cp_cost']
        points_to_add = cfg['paid_point']
        if int(ud.get('u_cp', 0) or 0) < cp_cost:
            return {'u_cp': ud.get('u_cp', 0), 'u_candy': float(ud.get('u_candy', 0.0))}, {'code': 1, 'errmsg': 'Not enough CP'}
        state.increment_currency(uuid, cp=-cp_cost)
        ud['u_cp'] = int(ud.get('u_cp', 0) or 0) - cp_cost
    else: # Free / AD
        points_to_add = cfg['ad_point']

    evp_list = user.setdefault('user_event_point', [])
    cur_point = 0
    cur_step = 0
    now_ts = int(time.time())
    found = False
    for ep in evp_list:
        if ep.get('s_EventType') == 'Pass' and int(ep.get('i_DataID', 0) or 0) == sub_id:
            ep['i_Point'] = int(ep.get('i_Point', 0) or 0) + points_to_add
            cur_point = ep['i_Point']
            ep['i_Step'] = _get_step_for_points(sub_id, cur_point)
            cur_step = ep['i_Step']
            if ptype == 0:
                ep['i_ADViewTime'] = now_ts
            found = True

    if not found:
        cur_point = points_to_add
        cur_step = _get_step_for_points(sub_id, cur_point)
        evp_list.append({
            's_EventType': 'Pass',
            'i_DataID': sub_id,
            'i_Point': cur_point,
            'i_Step': cur_step,
            'i_ADViewTime': now_ts if ptype == 0 else 0,
            'i_Version': version
        })

    state.save_user(user)
    return {
        'u_cp': ud.get('u_cp', 0),
        'u_candy': float(ud.get('u_candy', 0.0)),
        'i_SubscribeID': sub_id,
        'i_Point': cur_point,
        'i_Version': version
    }, OK

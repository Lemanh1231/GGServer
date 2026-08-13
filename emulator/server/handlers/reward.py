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
    if rtype in (1, 11): # Goods
        cp = candy = like = fans = 0
        if rid == 1: 
            candy = rval
            ud['u_candy'] = ud.get('u_candy', 0.0) + candy
        elif rid == 2: 
            cp = int(rval)
            ud['u_cp'] = ud.get('u_cp', 0) + cp
        elif rid in (3, 4): 
            like = rval
            ud['u_like'] = ud.get('u_like', 0.0) + like
        elif rid == 8: 
            fans = int(rval)
            ud['u_fans'] = ud.get('u_fans', 0) + fans
        if uuid:
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
        if not any(x.get('i_id') == rid for x in lst): lst.append({'i_id': rid, 'i_Level': 1, 'i_BonusLevel': 0})
    elif rtype == 7: # Unit
        lst = user.setdefault('user_unit', [{'i_id': 1, 'i_Level': 1}])
        if not any(x.get('i_id') == rid for x in lst): lst.append({'i_id': rid, 'i_Level': 1})

@cmd('setAttendance')
def h_set_attendance(req, player, ctx):
    """Serve the daily-login event through the client's normal check/add flow.

    `check` controls whether the login-event popup is visible.  The former
    emulator always returned N and auto-claimed the prize while building the
    event list, which hid the event and made its button unusable.  Now a reward
    remains available until the client explicitly sends `add` (or claims it
    from the event board through setEventReward).
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
    if user:
        st = _att_state(user, 1)
        cur = st.get('day', 0)
        if rtype == 'add' and st.get('ymd') != today:
            rewards = _get_event_rewards().get('1', {})
            max_day = len(rewards) or 7
            day = cur + 1
            if day > max_day:
                day = 1
            rew = rewards.get(str(day)) or {
                'reward_type': 1, 'reward_id': 1, 'reward_value': 100,
            }
            _give_reward(user, rew)
            st['day'] = day
            st['ymd'] = today
            cur = day
            ud = user['userdata']
            ud['attendance_count'] = day
            ud['attendance_date'] = today
            state.update_attendance(user.get('uuid'), day, today)
            state.save_user(user)
            added = True
        claimed_today = st.get('ymd') == today
    else:
        claimed_today = False
    return {
        'status': 'Y' if added else ('N' if claimed_today else 'Y'),
        'attendance_count': cur,
        'attendance_date': today if claimed_today else 0,
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
        level = 0

    today = str(_today_ymd())
    claim_key = f'{item_id}:{level}'
    rtype = rid = rval = None
    try:
        _gd_path = os.path.join(os.path.dirname(__file__), '..', '..', 'gamedata', 'game_data.json')
        with open(_gd_path, 'r', encoding='utf-8') as f:
            gamedata = json.load(f)

        if req_type == 'daily_mission':
            for row in gamedata.get('10', []):
                if str(row.get('1')) == item_id:
                    rtype = int(row.get('44', 1))
                    rid = int(row.get('43', 2))
                    rval = int(row.get('42', 10))
                    if rtype == 1 and rid == 0:
                        currency = str(row.get('29', '')).upper()
                        if 'CP' in currency: rid = 2
                        elif 'CHOCO' in currency: rid = 1
                    break
        elif req_type == 'achievement':
            for row in gamedata.get('9', []):
                if str(row.get('1')) == item_id:
                    # Rows with production multipliers are not currency
                    # rewards.  The old handler mistook them for Candy.
                    if str(row.get('28', '')).upper() != 'CP':
                        break
                    val_key = str(40 + level)
                    if level < 1 or val_key not in row:
                        break
                    rtype, rid, rval = 1, 2, int(row[val_key])
                    break
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass

    def denied():
        return {
            'type': req_type, 'id': int(item_id) if item_id.isdigit() else 0,
            'level': level, 'reward_type': '0', 'reward_value': 0,
            'status': 'N', 'user_follower_profile': {}
        }, OK

    if req_type not in ('daily_mission', 'achievement') or None in (rtype, rid, rval):
        return denied()

    if user:
        if req_type == 'daily_mission':
            # Daily rewards reset by calendar date.
            claims = user.setdefault('claimed_daily_rewards', {})
            today_claims = claims.setdefault(today, {})
            if claim_key in today_claims:
                return denied()
            for old_day in [day for day in claims if day != today]:
                del claims[old_day]
            today_claims[claim_key] = int(time.time())
        else:
            # Achievement milestones are permanent claims.
            claims = user.setdefault('claimed_achievement_rewards', {})
            if claim_key in claims:
                return denied()
            claims[claim_key] = int(time.time())

        rew = {'reward_type': rtype, 'reward_id': rid, 'reward_value': rval}
        _give_reward(user, rew)
        state.save_user(user)

    return {
        'type': req_type, 'id': int(item_id) if item_id.isdigit() else 0, 'level': level,
        'reward_type': str(rtype), 'reward_value': rval,
        'status': 'Y', 'user_follower_profile': {}
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
        paid_active = any(item.get('i_SubscribeID') == group
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
    user = state.get_user(uuid)
    try:
        i_id = int(p.get('i_id', 0))
        profile_id = int(p.get('param1', 0))
    except (TypeError, ValueError):
        return {}, OK

    # Capture: adViewLog(ad_profile_free_gift), followed by
    # setAdReward(i_id=1, param1=<profile id>).  Game table 32 configures
    # this as PROFILE_EXP: 300 hearts/EXP, 10-minute cooldown, 5 per day.
    # It is not the generic 50-Candy ad reward this emulator used before.
    if i_id == 1 and profile_id > 0 and user:
        now = int(time.time())
        today = _today_ymd()
        ad_state = user.setdefault('follower_profile_ad_rewards', {})
        slot = ad_state.setdefault(str(profile_id), {
            'i_Count': 0, 'i_TotalCount': 0, 'i_LastViewTick': 0, 'upd_day': today,
        })
        if int(slot.get('upd_day', 0) or 0) != today:
            slot['i_Count'] = 0
            slot['upd_day'] = today

        allowed = (int(slot.get('i_Count', 0) or 0) < 5
                   and now - int(slot.get('i_LastViewTick', 0) or 0) >= 600)
        profile = next((row for row in user.setdefault('user_follower_profile', [
            {'i_id': 1, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0},
        ]) if int(row.get('i_id', 0) or 0) == profile_id), None)
        if not profile:
            return {'i_id': i_id, 'reward_data': []}, OK

        if allowed:
            from server.handlers.follower import _apply_profile_exp, _follower_data
            _, _, level_data = _follower_data()
            _apply_profile_exp(profile, level_data.get(profile_id, {}), 300)
            slot['i_Count'] = int(slot.get('i_Count', 0) or 0) + 1
            slot['i_TotalCount'] = int(slot.get('i_TotalCount', 0) or 0) + 1
            slot['i_LastViewTick'] = now

            followers = user.setdefault('user_follower', [])
            follower = next((row for row in followers
                             if int(row.get('i_id', 0) or 0) == profile_id), None)
            if follower is None:
                follower = {'i_id': profile_id, 'i_Level': 1, 'i_BonusLevel': 0}
                followers.append(follower)
            follower['i_Level'] = int(profile['i_Level'])
            state.save_user(user)

        return {
            'i_id': i_id,
            'user_ad_list': {'i_id': i_id, **slot},
            'user_follower_profile': profile,
            # This is profile EXP rather than a currency/inventory item.
            'reward_data': ([{'reward_type': 0, 'reward_id': 0, 'reward_value': 300}]
                            if allowed else []),
        }, OK

    # Game table 32: ad_ap.  It is a separate ad slot from the follower
    # profile ad: five views per day, no cooldown, reward group 1011 =
    # 25 Cookie (Chapter 3 AP).  The client adds the returned reward locally
    # and will receive the authoritative AP value on its next getChThird.
    if i_id == 2 and user:
        from server.handlers.ch_third import _add_ap
        today = _today_ymd()
        ad_state = user.setdefault('chapter_ap_ad_rewards', {})
        slot = ad_state.setdefault('2', {
            'i_Count': 0, 'i_TotalCount': 0, 'i_LastViewTime': 0, 'upd_day': today,
        })
        if int(slot.get('upd_day', 0) or 0) != today:
            slot['i_Count'] = 0
            slot['upd_day'] = today
        allowed = int(slot.get('i_Count', 0) or 0) < 5
        if allowed:
            _add_ap(user, 25)
            slot['i_Count'] = int(slot.get('i_Count', 0) or 0) + 1
            slot['i_TotalCount'] = int(slot.get('i_TotalCount', 0) or 0) + 1
            slot['i_LastViewTime'] = int(time.time())
            state.save_user(user)
        return {
            'i_id': i_id,
            'user_ad_list': slot,
            'reward_data': ([{'reward_type': 1, 'reward_id': 11, 'reward_value': 25}]
                            if allowed else []),
        }, OK

    # Preserve a neutral response for ad slots that have not been captured.
    return {
        'i_id': i_id,
        'user_ad_list': {'i_id': i_id, 'i_Count': 0, 'i_TotalCount': 0,
                         'i_LastViewTick': 0, 'upd_day': _today_ymd()},
        'reward_data': [],
    }, OK

@cmd('paidEventPoint')
def h_paid_event_point(req, player, ctx):
    """Star Pass 'Charge Up' – buy event points with CP."""
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    sub_id = p.get('i_SubscribeID', 5)
    version = p.get('i_Version', 5)
    # point_price comes from getSubscribePass table; default 10 CP per point batch
    points_to_add = 100

    # Gold Star Card / paid point top-up is deliberately disabled in this
    # offline emulator.  Never deduct a currency or grant points for it.
    if not _paid_star_card_enabled():
        ud = user.get('userdata', {}) if user else {}
        return {
            'u_cp': ud.get('u_cp', 0), 'u_candy': ud.get('u_candy', 0.0),
            'i_SubscribeID': sub_id, 'i_Point': 0, 'i_Version': version,
        }, OK

    if user:
        ud = user['userdata']
        # deduct CP (10 CP per charge)
        cp_cost = 10
        state.increment_currency(uuid, cp=-cp_cost)
        ud['u_cp'] = ud.get('u_cp', 0) - cp_cost
        # add star pass points
        evp_list = user.setdefault('user_event_point', [
            {'s_EventType': 'Pass', 'i_DataID': sub_id, 'i_Point': 0, 'i_Step': 0, 'i_ADViewTime': 0, 'i_Version': version}
        ])
        cur_point = 0
        for ep in evp_list:
            if ep.get('s_EventType') == 'Pass':
                ep['i_Point'] = ep.get('i_Point', 0) + points_to_add
                cur_point = ep['i_Point']
                break
        state.save_user(user)
        return {
            'u_cp': ud.get('u_cp', 0),
            'u_candy': ud.get('u_candy', 0.0),
            'i_SubscribeID': sub_id,
            'i_Point': cur_point,
            'i_Version': version
        }, OK

    return {
        'u_cp': 0, 'u_candy': 0.0,
        'i_SubscribeID': sub_id, 'i_Point': points_to_add, 'i_Version': version
    }, OK

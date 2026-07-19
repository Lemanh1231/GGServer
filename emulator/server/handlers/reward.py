import os, time, json
from server import state
from server.handlers.registry import cmd, OK, _payload

EVENT_REWARDS = None
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
    # The client's entry flow (InGameEntryProcess -> AddAttendanceState ->
    # STM_ConsecutiveAttendance) sends type="check" on login and auto-opens the 7-day login
    # popup whenever that check reports attendance is still AVAILABLE (status "Y"); it then
    # fires type="add" to claim. The popup is gated on `status`, NOT on attendance_date -- so
    # stamping today's date alone never stopped it.
    #
    # We suppress the auto-popup by answering the "check" with status "N" ("nothing to claim
    # today"). The "add" path still reports "Y" in case the client ever calls it directly. The
    # attendance board stays reachable from the event menu (getEventRewardList + setEventReward),
    # which keeps its own per-day claim state.
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    rtype = p.get('type', 'check')
    user = state.get_user(uuid)
    today = _today_ymd()
    cur = 1
    if user:
        st = _att_state(user, 1)
        cur = max(1, st.get('day', 0))   # last claimed day, not the next claimable one
    return {
        'status': 'N' if rtype == 'check' else 'Y',
        'attendance_count': cur,
        'attendance_date': today,     # = today -> any date-based check also treats it as done
        'max_coutinuous_attendance_count': cur,
    }, OK

# event_idx of the daily check-in boards that should auto-claim on login.
# 1 = 출석부 (daily reward), 3 = 상시 출석부 (daily attendance). The others (2 = anniversary,
# 202110/202111 = expired 2021 login events) are left alone.
DAILY_BOARDS = ('1', '3')

def _auto_claim_daily(user, eidx, today):
    """Auto-claim today's reward for a daily attendance board so the client never has a pending
    claim (the popup only has a 'Close' button -- it never fires setEventReward itself, so without
    this the board would re-open every login forever). Advances one day per calendar day, credits
    the reward, and stamps the claim date = today. No-op if already claimed today."""
    if not user:
        return
    st = _att_state(user, eidx)
    if st.get('ymd') == today:
        return  # already claimed today
    rewards = _get_event_rewards().get(str(eidx), {})
    max_day = len(rewards) or 7
    day = st.get('day', 0) + 1
    if day > max_day:
        day = 1
    rew = rewards.get(str(day)) or {'reward_type': 1, 'reward_id': 1, 'reward_value': 100}
    _give_reward(user, rew)
    st['day'] = day
    st['ymd'] = today
    if str(eidx) == '1':
        ud = user['userdata']
        ud['attendance_count'] = day
        ud['attendance_date'] = today
        state.update_attendance(user.get('uuid'), day, today)
    state.save_user(user)

@cmd('getEventRewardList')
def h_get_event_reward_list(req, player, ctx):
    # Built per-user (NOT static) so the attendance board reflects what the player already
    # claimed. The board is sequential: day 1, then day 2 the next calendar day, ... The server
    # records progress in user['attendance'][event_idx] = {'day': last claimed day, 'ymd': last
    # claim date} via setEventReward. We overlay that here:
    #   - days already claimed (reward_num <= day)  -> reward_flg='N' + get_date=<claim date>
    #   - days not yet claimed                      -> left as the template (reward_flg='Y')
    # so the client greys out claimed days, stops auto-opening the popup once today's reward is
    # taken (last claimed day has get_date == today), and lets the next day be claimed tomorrow.
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    today = _today_ymd()
    # auto-claim today's daily-board rewards before rendering, so claimed days show as received
    # (get_date == today) and the client stops re-opening the attendance popup.
    if user:
        for _b in DAILY_BOARDS:
            _auto_claim_daily(user, _b, today)
    template = _get_event_template()
    data = {}
    for eidx, board in template.items():
        st = _att_state(user, eidx) if user else {'day': 0, 'ymd': 0}
        claimed_day = st.get('day', 0)
        claim_ymd = st.get('ymd', 0)
        rl = []
        for r in board.get('reward_list', []):
            r2 = dict(r)
            if claimed_day and r2.get('reward_num', 0) <= claimed_day:
                r2['reward_flg'] = 'N'                      # already received
                r2['get_date'] = claim_ymd or r2.get('get_date', 0)
            rl.append(r2)
        data[eidx] = {'reward_list': rl, 'group_idx': board.get('group_idx', 0)}
    return data, OK

@cmd('setEventReward')
def h_set_event_reward(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    event_idx = str(p.get('event_idx', 1))
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
    level = int(p.get('level', 1))
    
    # --- check if already claimed today ---
    today = str(_today_ymd())
    claim_key = f'{req_type}:{item_id}:{level}'
    if user:
        claimed = user.setdefault('claimed_rewards', {})
        today_claims = claimed.get(today, {})
        if claim_key in today_claims:
            # already claimed today → tell client "nothing to claim"
            return {
                'type': req_type, 'id': int(item_id), 'level': level,
                'reward_type': '0', 'reward_value': 0,
                'status': 'N', 'user_follower_profile': {}
            }, OK
    
    rtype = 1
    rid = 2
    rval = 10
    
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
                    rtype = 1
                    rid = 1
                    val_key = str(40 + level)
                    rval = int(row.get(val_key, 10))
                    break
    except Exception as e:
        pass
        
    if user:
        rew = {'reward_type': rtype, 'reward_id': rid, 'reward_value': rval}
        _give_reward(user, rew)
        # stamp this claim so it can't be repeated today
        claimed = user.setdefault('claimed_rewards', {})
        today_claims = claimed.setdefault(today, {})
        today_claims[claim_key] = int(time.time())
        # prune old days (keep only today)
        for old_day in [d for d in claimed if d != today]:
            del claimed[old_day]
        state.save_user(user)

    return {
        'type': req_type, 'id': int(item_id), 'level': level,
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
    
    # Just a mock reward: 10 Chocolate
    rew = {'reward_type': 1, 'reward_id': 1, 'reward_value': 10}
    if user:
        _give_reward(user, rew)
        lst = user.setdefault('user_subscribe_pass_reward', [])
        # We don't actually manage the full list perfectly, but we can append the progress
        # to prevent the client from requesting it again.
        lst.append({
            'i_SubscribeID': group,
            'i_Type': ptype,
            'i_Step': step,
            'i_UpdateTime': int(time.time()),
            'i_Version': p.get('i_Version', 5)
        })
        state.save_user(user)
        
    return {
        'subscribe_pass_reward': {
            'i_SubscribeID': group,
            'i_Type': ptype,
            'i_Step': step,
            'i_UpdateTime': int(time.time()),
            'i_Version': p.get('i_Version', 5)
        },
        'reward_data': [rew]
    }, OK

@cmd('setAdReward')
def h_set_ad_reward(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    i_id = p.get('i_id', 0)
    
    # Ads typically give Chocolate (1) or Candy (2)
    # Here we mock 50 Chocolate
    rew = {'reward_type': 1, 'reward_id': 1, 'reward_value': 50}
    
    if user:
        _give_reward(user, rew)
        state.save_user(user)
        
    return {
        'i_id': i_id,
        'user_ad_list': {'i_id': i_id, 'i_Count': 1, 'i_TotalCount': 1, 'i_LastViewTick': int(time.time()), 'upd_day': _today_ymd()},
        'reward_data': [rew]
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

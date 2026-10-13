import time
from server import state
from server.handlers.registry import cmd, OK, _payload

def _remove_legacy_paid_subscriptions(user):
    # Keep subscriptions intact so purchased or activated season passes are preserved
    pass


def _remove_legacy_currency_grant(user):
    """Remove the old 1,000,000 CP/100,000 Candy starter grant once.

    u_free_cp was never a real purchase balance in this emulator, so its old
    sentinel value reliably identifies profiles created by the previous seed.
    Keeping the marker at zero makes the migration idempotent and preserves all
    currency earned after the next login.
    """
    ud = user.get('userdata', {})
    if int(ud.get('u_free_cp', 0) or 0) != 1_000_000:
        return
    ud['u_free_cp'] = 0
    ud['u_cp'] = 0
    ud['u_candy'] = 0.0
    state.set_currency(user.get('uuid'), cp=0, candy=0.0)
    state.save_user(user)

def _remove_legacy_unlock_all(user):
    """Replace the former synthetic full catalogue with starter ownership."""
    if user.get('legacy_unlock_all_migrated'):
        return
    user['costumes'] = [
        {'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0},
    ]
    user['user_music'] = [
        {'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0,
         'b_EncoreBonusAppear': 0, 'l_EncoreBonusActivateTime': 0,
         'i_EncoreBonusFollowerId': 0, 'i_ChThirdActiveTime': 0},
    ]
    user['user_guitar'] = [
        {'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0},
    ]
    user['legacy_unlock_all_migrated'] = True
    state.save_user(user)

@cmd('userJoin')
def h_user_join(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or p.get('device_uuid') or ctx.get('uuid')
    device_uuid = p.get('device_uuid', '')
    user = state.create_user(uuid, device_uuid)
    ud = user['userdata']
    return {'u_seq': ud['u_seq'], 'u_id': ud['u_id']}, OK


def _normalise_achievements(user, incoming=None):
    """Keep the server-owned achievement tier when Unity omits it on save.

    The client sends only the counters for most ``userSave`` calls.  Replacing
    the records verbatim used to erase ``i_Level``; a missing tier is decoded
    by the UI as tier 0 and makes almost the entire achievement page vanish.
    """
    old = {int(x.get('i_id', 0) or 0): x
           for x in user.get('achievements', []) if int(x.get('i_id', 0) or 0)}
    sent = {int(x.get('i_id', 0) or 0): x
            for x in (incoming if incoming is not None else user.get('achievements', []))
            if int(x.get('i_id', 0) or 0)}
    result = []
    for item_id in range(1, 11):
        previous = old.get(item_id, {})
        update = sent.get(item_id, {})
        prev_lvl = int(previous.get('i_Level', 1) or 1)
        upd_val = update.get('i_Level')
        upd_lvl = int(upd_val or 1) if upd_val is not None else prev_lvl
        level = max(prev_lvl, upd_lvl)
        result.append({
            'i_id': item_id,
            'i_Level': level,
            'd_Quantity': update.get('d_Quantity', previous.get('d_Quantity', 0)),
            's_Quantity': update.get('s_Quantity', previous.get('s_Quantity', '')),
        })
    user['achievements'] = result
    return result


MISSION_TARGETS = {1: 1, 2: 2000, 3: 30, 4: 5, 5: 1800}


def _normalise_daily_missions(user, incoming=None):
    """Restore fields omitted by the compact daily-mission userSave payload and ensure daily attendance."""
    today = int(time.strftime('%Y%m%d', time.localtime()))
    stored_date = user.get('daily_mission_date')

    # If incoming is None (called during userLogin / startup):
    if incoming is None:
        if stored_date is not None and stored_date != today:
            # New calendar day rollover on login: reset all 6 missions
            user['daily_mission_date'] = today
            user['claimed_daily_rewards'] = {}
            result = [
                {'i_id': 1, 'i_Level': 1, 'd_Quantity': 1, 'upd_date': ''},
                {'i_id': 2, 'i_Level': 1, 'd_Quantity': 0, 'upd_date': ''},
                {'i_id': 3, 'i_Level': 1, 'd_Quantity': 0, 'upd_date': ''},
                {'i_id': 4, 'i_Level': 1, 'd_Quantity': 0, 'upd_date': ''},
                {'i_id': 5, 'i_Level': 1, 'd_Quantity': 0, 'upd_date': ''},
                {'i_id': 6, 'i_Level': 1, 'd_Quantity': 0, 'upd_date': ''},
            ]
            user['user_daily_mission'] = result
            return result
        elif stored_date is None:
            user['daily_mission_date'] = today

    old = {int(x.get('i_id', 0) or 0): x
           for x in user.get('user_daily_mission', []) if int(x.get('i_id', 0) or 0)}
    sent = {int(x.get('i_id', 0) or 0): x
            for x in (incoming if incoming is not None else user.get('user_daily_mission', []))
            if int(x.get('i_id', 0) or 0)}
    result = []
    for item_id in range(1, 7):
        previous = old.get(item_id, {})
        update = sent.get(item_id, {})
        level = update.get('i_Level', previous.get('i_Level', 1))
        try:
            level = max(1, int(level or 1))
        except (TypeError, ValueError):
            level = 1

        qty = update.get('d_Quantity', previous.get('d_Quantity', 0))
        try:
            qty = max(0, int(qty or 0))
        except (TypeError, ValueError):
            qty = 0

        # Mission 1 is Daily Attendance ("Đăng nhập nhiều hơn 1 lần")
        # Since the player is active / logged in today, Mission 1 progress is 1.
        if item_id == 1:
            qty = max(1, qty)

        result.append({
            'i_id': item_id,
            'i_Level': level,
            'd_Quantity': qty,
            'upd_date': update.get('upd_date', previous.get('upd_date', '')),
        })

    # Mission 6 is "Hoàn thành toàn bộ Nhiệm vụ hàng ngày" (Complete all daily missions 1..5)
    # Target is 5. Update progress to match how many of missions 1..5 are completed.
    completed_count = sum(
        1 for m in result[:5]
        if m.get('d_Quantity', 0) >= MISSION_TARGETS.get(m['i_id'], 1) or m.get('i_Level', 1) >= 2
    )
    result[5]['d_Quantity'] = max(result[5].get('d_Quantity', 0), completed_count)

    user['user_daily_mission'] = result
    if 'daily_mission_date' not in user:
        user['daily_mission_date'] = today
    return result


def _active_buffs(user):
    """Return timed buffs which have not expired, using server time only."""
    now = int(time.time())
    buffs = []
    for buff in user.get('user_buff', []):
        try:
            if int(buff.get('i_EndTime', 0) or 0) <= now:
                continue
            buffs.append({
                'i_id': int(buff.get('i_id', 0) or 0),
                'i_Level': max(1, int(buff.get('i_Level', 1) or 1)),
                'i_ActiveTime': int(buff.get('i_ActiveTime', now) or now),
                'i_EndTime': int(buff['i_EndTime']),
            })
        except (TypeError, ValueError):
            continue
    # Always include Buff ID 4: Guitar Girl Premium (Table 6 ID 4: "Removes all in-game Ads")
    # This disables/bypasses all ads in the client globally.
    if not any(b.get('i_id') == 4 for b in buffs):
        buffs.append({
            'i_id': 4,
            'i_Level': 1,
            'i_ActiveTime': now,
            'i_EndTime': 2147483647,
        })
    user['user_buff'] = buffs
    return buffs
def _starter_messenger(user):
    from server.handlers.follower import _sync_follower_messenger
    return _sync_follower_messenger(user)

def _normalise_event_points(user):
    from server import event_manager
    from server.handlers.reward import _get_pass_version, _get_step_for_points
    evp = user.setdefault('user_event_point', [])
    if not event_manager.is_star_pass_enabled():
        evp[:] = [e for e in evp if e.get('s_EventType') != 'Pass']
        return evp

    active_season = event_manager.get_active_star_pass_season()
    target_version = _get_pass_version(active_season)

    passes_by_id = {}
    non_passes = []
    for e in evp:
        if e.get('s_EventType') == 'Pass':
            sid = int(e.get('i_DataID', 0) or 0)
            if sid not in passes_by_id:
                passes_by_id[sid] = []
            passes_by_id[sid].append(e)
        else:
            non_passes.append(e)

    result_passes = []
    if active_season in passes_by_id:
        active_entries = passes_by_id.pop(active_season)
        best_point = max(int(e.get('i_Point', 0) or 0) for e in active_entries)
        best_ad = max(int(e.get('i_ADViewTime', 0) or 0) for e in active_entries)
        result_passes.append({
            's_EventType': 'Pass',
            'i_DataID': active_season,
            'i_Point': best_point,
            'i_Step': _get_step_for_points(active_season, best_point),
            'i_ADViewTime': best_ad,
            'i_Version': target_version,
        })
    else:
        result_passes.append({
            's_EventType': 'Pass',
            'i_DataID': active_season,
            'i_Point': 0,
            'i_Step': 0,
            'i_ADViewTime': 0,
            'i_Version': target_version,
        })

    for sid, entries in passes_by_id.items():
        if sid <= 0:
            continue
        best_point = max(int(e.get('i_Point', 0) or 0) for e in entries)
        best_ad = max(int(e.get('i_ADViewTime', 0) or 0) for e in entries)
        sid_version = _get_pass_version(sid)
        result_passes.append({
            's_EventType': 'Pass',
            'i_DataID': sid,
            'i_Point': best_point,
            'i_Step': _get_step_for_points(sid, best_point),
            'i_ADViewTime': best_ad,
            'i_Version': sid_version,
        })

    evp[:] = non_passes + result_passes
    return evp


def _normalise_subscribe_list(user):
    from server import event_manager
    subs = user.setdefault('user_subscribe_list', [])

    # Migrate any legacy i_EndTime to i_ActiveTime
    for s in subs:
        if 'i_EndTime' in s:
            s['i_ActiveTime'] = int(s.pop('i_EndTime', 0) or 0)
        if 'i_ActiveTime' not in s:
            s['i_ActiveTime'] = 0

    if not event_manager.is_star_pass_enabled():
        for s in subs:
            s['i_isActive'] = 0
        return subs

    active_season = event_manager.get_active_star_pass_season()
    paid_enabled = event_manager.is_paid_star_card_enabled()

    # Check if user legitimately bought active season in shop
    shop_items = user.get('user_shop', []) or []
    bought_ids = {int(sh.get('i_id', 0) or 0) for sh in shop_items if int(sh.get('i_Count', sh.get('i_TotalCount', 0)) or 0) > 0}
    season_bought = (1000 + active_season in bought_ids or 2000 + active_season in bought_ids or 3000 + active_season in bought_ids)

    paid_sub = next((s for s in subs if s.get('i_SubscribeID') in (active_season, 1000 + active_season)), None)
    if paid_enabled or season_bought:
        if not paid_sub:
            subs.append({'i_SubscribeID': active_season, 'i_isActive': 1, 'i_ActiveTime': 2147483647 if paid_enabled else int(time.time())})
        else:
            paid_sub['i_isActive'] = 1
            if paid_sub.get('i_ActiveTime', 0) == 0:
                paid_sub['i_ActiveTime'] = 2147483647 if paid_enabled else int(time.time())
    else:
        if paid_sub:
            paid_sub['i_isActive'] = 0
            paid_sub['i_ActiveTime'] = 0

    for s in subs:
        sid = s.get('i_SubscribeID', 0)
        s_season = sid % 1000 if sid > 1000 else sid
        if s_season != active_season:
            s_bought = (1000 + s_season in bought_ids or 2000 + s_season in bought_ids or 3000 + s_season in bought_ids)
            if not s_bought:
                s['i_isActive'] = 0

    return subs


def _normalise_ticketcollection(user):
    owned_tickets = set()

    # 1. Shop purchases
    for sh in user.get('user_shop', []) or []:
        idx = int(sh.get('i_id', 0) or 0)
        cnt = int(sh.get('i_Count', sh.get('i_TotalCount', 0)) or 0)
        if cnt > 0:
            if 1001 <= idx <= 1013:
                s_num = idx % 1000
                if 1 <= s_num <= 13:
                    owned_tickets.add(s_num)
            elif 2001 <= idx <= 3013:
                s_num = idx % 1000
                if 1 <= s_num <= 13:
                    owned_tickets.add(s_num)
                    owned_tickets.add(1000 + s_num)

    # 2. Active subscriptions (legitimately purchased or admin-granted)
    for s in user.get('user_subscribe_list', []) or []:
        if int(s.get('i_isActive', 0) or 0) == 1:
            pid = int(s.get('i_SubscribeID', 0) or 0)
            if 1 <= pid <= 13:
                owned_tickets.add(pid)
            elif 1001 <= pid <= 1013:
                owned_tickets.add(pid)
                owned_tickets.add(pid % 1000)

    result = [{'i_id': tid} for tid in sorted(owned_tickets)]
    user['user_ticketcollection'] = result
    return result

def _sync_follower_profiles_and_rewards(user):
    """Ensure all owned followers have corresponding profiles with valid cumulative EXP, unlocked information milestones, and chat rooms."""
    from server.handlers.follower import _sync_follower_profiles, _sync_follower_messenger
    _sync_follower_profiles(user)
    _sync_follower_messenger(user)

def _user_contents(user):
    # Do not expose skills before their character-level gates.  The game-data
    # table defines the three Guitar Girl skills at Lv. 100 / 300 / 500; the
    # separate cooldown-reset skill unlocks at Lv. 10.
    skills = user.setdefault('user_skill', [])
    c1_level = max([int(c.get('i_Level', 0) or 0) for c in user.get('characters', []) if int(c.get('i_id', 0) or 0) == 1] or [0])
    c2_level = max([int(c.get('i_Level', 0) or 0) for c in user.get('characters', []) if int(c.get('i_id', 0) or 0) == 2] or [0])
    skill_gates = {
        1: (1, 100),
        2: (1, 300),
        3: (1, 500),
        4: (1, 10),
        21: (2, 100),
        22: (2, 300),
        23: (2, 500),
        24: (2, 10),
    }

    def _is_unlocked(sid):
        char_id, req_lvl = skill_gates.get(sid, (1, 999999))
        lvl = c1_level if char_id == 1 else c2_level
        return lvl >= req_lvl

    skills[:] = [s for s in skills if _is_unlocked(s.get('i_id', 0))]
    for sid, (char_id, req_lvl) in skill_gates.items():
        lvl = c1_level if char_id == 1 else c2_level
        if (lvl >= req_lvl
                and not any(s.get('i_id') == sid for s in skills)):
            skills.append({'i_id': sid, 'i_Level': 1, 'b_Activate': 0,
                           'l_ActivateOnTicks': 0, 'l_ActivateOffTicks': 0})

    props = user.setdefault('user_prop', [])
    if not props:
        props.extend([{'i_id': 1, 'i_Level': 1}, {'i_id': 2, 'i_Level': 1}])

    # Ensure all owned followers have a profile entry and unlocked rewards
    _sync_follower_profiles_and_rewards(user)
    profiles = user.get('user_follower_profile', [])

    # Ensure Meowfest / SamSeck event rewards are granted if claimed in u_samseck_step
    samseck_step = int(user.get('userdata', {}).get('u_samseck_step', 0) or 0)
    if samseck_step & 1:
        guitars = user.setdefault('user_guitar', [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}])
        if not any(int(g.get('i_id', 0) or 0) == 10 for g in guitars):
            guitars.append({'i_id': 10, 'i_Level': 1, 'i_BonusLevel': 0})
    if samseck_step & 2:
        costumes = user.setdefault('costumes', [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}])
        if not any(int(c.get('i_id', 0) or 0) == 13 for c in costumes):
            costumes.append({'i_id': 13, 'i_Level': 1, 'i_BonusLevel': 0})
    if samseck_step & 4:
        units = user.setdefault('user_unit', [])
        if not any(int(u.get('i_id', 0) or 0) == 1 for u in units):
            units.append({'i_id': 1, 'i_Level': 1})

    ch3_stages = user.get('user_ch_third_stage') or user.get('user_chthird_stage') or [{'i_id': 1001, 'i_ChapterId': 1, 'i_StageIndex': 1, 'i_Star': 3}]
    user['user_ch_third_stage'] = ch3_stages
    user['user_chthird_stage'] = ch3_stages

    chars = user.setdefault('characters', [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}])
    if not any(int(c.get('i_id', 0) or 0) == 2 for c in chars):
        chars.append({'i_id': 2, 'i_Level': 1, 'i_BonusLevel': 0})

    costumes = user.setdefault('costumes', [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}])
    if not any(int(c.get('i_id', 0) or 0) == 201 for c in costumes):
        costumes.append({'i_id': 201, 'i_Level': 1, 'i_BonusLevel': 0})

    guitars = user.setdefault('user_guitar', [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}])
    if not any(int(g.get('i_id', 0) or 0) == 201 for g in guitars):
        guitars.append({'i_id': 201, 'i_Level': 1, 'i_BonusLevel': 0})

    user_music = user.setdefault('user_music', [
        {'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0,
         'b_EncoreBonusAppear': 0, 'l_EncoreBonusActivateTime': 0,
         'i_EncoreBonusFollowerId': 0, 'i_ChThirdActiveTime': 0}
    ])
    if not any(int(m.get('i_id', 0) or 0) == 201 for m in user_music):
        user_music.append({
            'i_id': 201, 'i_Level': 1, 'i_BonusLevel': 0,
            'b_EncoreBonusAppear': 0, 'l_EncoreBonusActivateTime': 0,
            'i_EncoreBonusFollowerId': 0, 'i_ChThirdActiveTime': 0
        })

    return {
        'user_achievement': _normalise_achievements(user),
        'user_buff': _active_buffs(user),
        'user_candy_shop': user.setdefault('user_candy_shop', []),
        'user_character': chars,
        'user_costume': costumes,
        'user_daily_mission': _normalise_daily_missions(user),
        'user_follower': user.setdefault('user_follower', [
            {'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0},
        ]),
        'user_music': user_music,
        'user_prop': props,
        'user_unit': user.setdefault('user_unit', []),
        'user_skill': skills,
        'user_shop': user.setdefault('user_shop', []),
        # Chat room 1 (Joy) is unlocked at start with unread notification
        'user_messenger': _starter_messenger(user),
        'user_guitar': guitars,
        # Star Pass: read from persisted user data, default to Season 13
        'user_event_point': _normalise_event_points(user),
        # Star Pass Subscriptions: Season 13 Thẻ Sao Nâng Cấp is active
        'user_subscribe_list': _normalise_subscribe_list(user),
        'user_subscribe_pass_reward': user.setdefault('user_subscribe_pass_reward', []),
        'user_ticketcollection': _normalise_ticketcollection(user),
        'user_follower_profile_reward': user.setdefault('user_follower_profile_reward', []),
        'user_follower_profile': profiles,
        'user_follower_giftitem': user.setdefault('user_follower_giftitem', [{'i_id': 1, 'i_Value': 141}]),
        'user_chthird_stage': ch3_stages,
        'user_tutorial': user.setdefault('user_tutorial', [{'i_id': i} for i in range(1, 8)]),
        'user_ad_level': [{'i_id': 210010, 'i_Level': 1, 'i_EXP': 1}],
        'user_ad_list': _normalise_ad_list(user),
    }

def _normalise_ad_list(user):
    today = int(time.strftime('%Y%m%d', time.localtime()))
    ad_rewards = user.setdefault('ad_rewards', {})

    if '1' not in ad_rewards and 'follower_profile_ad_rewards' in user:
        old_fp = user.get('follower_profile_ad_rewards', {})
        if '1' in old_fp:
            ad_rewards['1'] = old_fp['1']
        elif old_fp:
            ad_rewards['1'] = next(iter(old_fp.values()))
    if '2' not in ad_rewards and 'chapter_ap_ad_rewards' in user:
        old_ap = user.get('chapter_ap_ad_rewards', {})
        if '2' in old_ap:
            ad_rewards['2'] = old_ap['2']

    ad1 = ad_rewards.setdefault('1', {
        'i_id': 1, 'i_Count': 0, 'i_TotalCount': 0, 'i_LastViewTime': 0, 'upd_day': today,
    })
    if int(ad1.get('upd_day', 0) or 0) != today:
        ad1['i_Count'] = 0
        ad1['upd_day'] = today

    ad2 = ad_rewards.setdefault('2', {
        'i_id': 2, 'i_Count': 0, 'i_TotalCount': 0, 'i_LastViewTime': 0, 'upd_day': today,
    })
    if int(ad2.get('upd_day', 0) or 0) != today:
        ad2['i_Count'] = 0
        ad2['upd_day'] = today

    return [
        {
            'i_id': 1,
            'i_Count': int(ad1.get('i_Count', 0) or 0),
            'i_TotalCount': int(ad1.get('i_TotalCount', 0) or 0),
            'i_LastViewTime': int(ad1.get('i_LastViewTime', 0) or 0),
        },
        {
            'i_id': 2,
            'i_Count': int(ad2.get('i_Count', 0) or 0),
            'i_TotalCount': int(ad2.get('i_TotalCount', 0) or 0),
            'i_LastViewTime': int(ad2.get('i_LastViewTime', 0) or 0),
        },
    ]

@cmd('userLogin')
def h_user_login(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or p.get('device_uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    if not user:
        user = state.create_user(uuid, p.get('device_uuid', ''))
    u_seq_req = p.get('u_seq', 0) or 0
    if u_seq_req != 0:
        _remove_legacy_currency_grant(user)
        _remove_legacy_unlock_all(user)
        contents = _user_contents(user)
        areas = user.get('areas') or state._default_areas()
        user['areas'] = areas
        ud = user['userdata']
        cur_like = float(ud.get('u_like', 0.0) or 0.0)
        for aid, ainfo in areas.items():
            if cur_like > float(ainfo.get('d_Like', 0.0) or 0.0):
                ainfo['d_Like'] = cur_like
        area_map = {int(k): v for k, v in areas.items()}
        ct = str(ud.get('u_create_time', ''))
        if not ct.lstrip('-').isdigit():
            ud['u_create_time'] = time.strftime('%Y%m%d')

        needs_reset = user.get('needs_client_reset', False)
        # If client's requested u_seq does not match this server profile's u_seq,
        # the phone has leftover save data from an old/deleted account.
        if u_seq_req != ud.get('u_seq'):
            needs_reset = True

        now_str = time.strftime('%Y-%m-%d %H:%M:%S')
        now_ts = int(time.time())
        ud['u_last_login'] = now_str
        ud['u_last_communication'] = now_str
        ud_resp = dict(ud)
        ud_resp['u_last_login'] = now_str
        ud_resp['u_last_communication'] = now_str
        if p.get('uuid'):
            ud_resp['uuid'] = p.get('uuid')

        if needs_reset:
            # Send mismatched device_uuid on this initial login response to trigger
            # the client's internal purge: GgUtil.ClearRenewalPrefs(), ClearUserTable(),
            # and ClearUserTempPrefbs() in ApiServerSGT.OnRecv(userLogin).
            # This purges leftover PlayerPrefs, local tables, and HibernationStartTimeTicks (enum 0xa5)
            # so the client doesn't calculate massive fake offline rewards from prior sessions.
            dev_id = ud.get('device_uuid') or p.get('device_uuid') or uuid
            ud_resp['device_uuid'] = "RESET_" + str(dev_id)
            user['needs_client_reset'] = False
            user['last_save_time'] = now_ts
            ud['u_save_date'] = now_str
            ud_resp['u_save_date'] = now_str

        state.save_user(user)
        return {
            'user': ud_resp,
            'area_data': area_map,
            'user_contents': contents,
        }, OK
    ud = user['userdata']
    u_resp = {'u_seq': ud['u_seq'], 'u_id': ud['u_id']}
    if p.get('uuid'):
        u_resp['uuid'] = p.get('uuid')
    return {'user': u_resp}, OK

def _safe_merge_items(existing_items, new_items):
    """Merge client items into existing items without losing items granted server-side."""
    if not isinstance(existing_items, list):
        return new_items if isinstance(new_items, list) else []
    if not isinstance(new_items, list):
        return existing_items

    merged_map = {}
    for item in existing_items:
        if isinstance(item, dict) and 'i_id' in item:
            merged_map[int(item['i_id'])] = dict(item)

    for item in new_items:
        if isinstance(item, dict) and 'i_id' in item:
            iid = int(item['i_id'])
            if iid in merged_map:
                merged_map[iid].update(item)
            else:
                merged_map[iid] = dict(item)

    return list(merged_map.values())


@cmd('userSave')
def h_user_save(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    with state._LOCK:
        user = state.get_user(uuid)
        if user:
            now_ts = int(time.time())
            now_s = time.strftime('%Y-%m-%d %H:%M:%S')
            user['last_save_time'] = now_ts
            user['userdata']['u_save_date'] = now_s
            user['userdata']['u_last_communication'] = now_s

            # Two-way safe merging: never lose server-granted items
            if 'user_achievement' in p: _normalise_achievements(user, p['user_achievement'])
            if 'user_character' in p:   user['characters'] = _safe_merge_items(user.get('characters', []), p['user_character'])
            if 'user_costume' in p:     user['costumes'] = _safe_merge_items(user.get('costumes', []), p['user_costume'])
            if 'user_music' in p:       user['user_music'] = _safe_merge_items(user.get('user_music', []), p['user_music'])
            if 'user_guitar' in p:      user['user_guitar'] = _safe_merge_items(user.get('user_guitar', []), p['user_guitar'])
            if 'user_follower' in p:
                user['user_follower'] = p['user_follower']
                _sync_follower_profiles_and_rewards(user)
            if 'user_messenger' in p:
                from server.handlers.follower import _merge_user_messenger
                _merge_user_messenger(user, p['user_messenger'])
            from server.handlers.follower import _sync_follower_messenger
            _sync_follower_messenger(user)
            if 'user_ticketcollection' in p: user['user_ticketcollection'] = p['user_ticketcollection']
            if 'user_event_point' in p:
                user['user_event_point'] = p['user_event_point']
                _normalise_event_points(user)
            if 'user_daily_mission' in p: _normalise_daily_missions(user, p['user_daily_mission'])
            if 'user_prop' in p:        user['user_prop'] = _safe_merge_items(user.get('user_prop', []), p['user_prop'])
            if 'user_candy_shop' in p:  user['user_candy_shop'] = p['user_candy_shop']

            # Apply any pending server-side grants
            pending = user.pop('pending_grants', None)
            if pending and isinstance(pending, dict):
                ud = user.setdefault('userdata', {})
                if 'cp' in pending:
                    ud['u_cp'] = int(ud.get('u_cp', 0) or 0) + int(pending['cp'])
                if 'candy' in pending:
                    ud['u_candy'] = float(ud.get('u_candy', 0.0) or 0.0) + float(pending['candy'])
                if 'cookies' in pending:
                    state.add_ap(user, int(pending['cookies']))

            for ui in (p.get('user_info') or []):
                if ui.get('u_selected_costume_id'):
                    user['userdata']['u_selected_costume_id'] = ui['u_selected_costume_id']
                if ui.get('u_selected_music_id'):
                    user['userdata']['u_selected_music_id'] = ui['u_selected_music_id']
            for area in (p.get('user_area_info') or []):
                n = area.get('u_area_num')
                if n is not None:
                    stored = user.setdefault('areas', {}).setdefault(str(n), {})
                    stored.update(area)
                    srv_like = float(user.get('userdata', {}).get('u_like', 0.0) or 0.0)
                    if srv_like > float(stored.get('d_Like', 0.0) or 0.0):
                        stored['d_Like'] = srv_like
                    else:
                        c_like = float(stored.get('d_Like', 0.0) or 0.0)
                        user.setdefault('userdata', {})['u_like'] = c_like
                        conn = state.get_db()
                        conn.execute('UPDATE user_data SET u_like = ? WHERE uuid = ?', (c_like, user['uuid']))
                        conn.commit()
                        conn.close()
            state.save_user(user)
    return {'status': 'Y'}, OK

@cmd('lastSaveTime')
def h_last_save_time(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    now = int(time.time())
    last_save = now
    device_uuid = p.get('device_uuid', '')
    if user:
        ud = user.get('userdata', {})
        device_uuid = ud.get('device_uuid') or device_uuid
        last_save = int(user.get('last_save_time', now) or now)
    return {'last_save_time': last_save, 'device_uuid': device_uuid}, OK

@cmd('userLoad')
def h_user_load(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    if not user:
        return {}, OK
    load_type = p.get('type')
    if load_type == 'shop':
        return {'user_contents': {'user_shop': user.get('user_shop', [])}}, OK
    elif load_type == 'buff':
        return {'user_contents': {'user_buff': _active_buffs(user)}}, OK
    elif load_type in ('ALL', None, ''):
        contents = _user_contents(user)
        areas = user.get('areas') or state._default_areas()
        user['areas'] = areas
        ud = user.get('userdata', {})
        cur_like = float(ud.get('u_like', 0.0) or 0.0)
        for aid, ainfo in areas.items():
            if cur_like > float(ainfo.get('d_Like', 0.0) or 0.0):
                ainfo['d_Like'] = cur_like
        area_map = {int(k): v for k, v in areas.items()}
        now_str = time.strftime('%Y-%m-%d %H:%M:%S')
        ud_resp = dict(ud)
        ud_resp['u_last_communication'] = now_str
        return {
            'user': ud_resp,
            'area_data': area_map,
            'user_contents': contents,
        }, OK
    return {}, OK

@cmd('setTutorialNew')
def h_set_tutorial_new(req, player, ctx):
    """Persist completed tutorial IDs instead of acknowledging them only."""
    p = _payload(req)
    user = state.get_user(p.get('uuid') or ctx.get('uuid'))
    if not user:
        return {}, OK
    tutorials = user.setdefault('user_tutorial', [{'i_id': i} for i in range(1, 8)])
    known = {int(row.get('i_id', 0) or 0) for row in tutorials}
    for tutorial_id in p.get('i_ids') or []:
        try:
            tutorial_id = int(tutorial_id)
        except (TypeError, ValueError):
            continue
        if tutorial_id > 0 and tutorial_id not in known:
            tutorials.append({'i_id': tutorial_id})
            known.add(tutorial_id)
    state.save_user(user)
    return {'u_seq': user['userdata']['u_seq'], 'tutorial': tutorials}, OK

@cmd('setSubscribe')
def h_set_subscribe(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    subs = _normalise_subscribe_list(user) if user else []
    return {'u_seq': p.get('u_seq', 0), 'user_subscribe_list': subs}, OK

@cmd('setReviewPopup')
def h_set_review_popup(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    if user:
        user.setdefault('userdata', {})['u_review_popup'] = 'Y'
        state.save_user(user)
    return {'status': 'Y'}, OK

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
    user['costumes'] = [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}]
    user['user_music'] = [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0,
                           'b_EncoreBonusAppear': 0, 'l_EncoreBonusActivateTime': 0,
                           'i_EncoreBonusFollowerId': 0, 'i_ChThirdActiveTime': 0}]
    user['user_guitar'] = [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}]
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
    ms = user.get('user_messenger')
    if not ms:
        ms = [{
            'i_MessengerChatRoomId': 1,
            'i_LastConfirmIndex': -1,
            's_UnlockGroupList': '1',
            'l_UpdateTimeTicks': 0,
        }]
        user['user_messenger'] = ms
        return ms
    for r in ms:
        if r.get('i_MessengerChatRoomId') == 1 and not r.get('s_UnlockGroupList'):
            r['s_UnlockGroupList'] = '1'
    return ms

def _normalise_event_points(user):
    evp = user.setdefault('user_event_point', [])
    pass_entry = next((e for e in evp if e.get('s_EventType') == 'Pass'), None)
    if not pass_entry:
        evp.append({'s_EventType': 'Pass', 'i_DataID': 13, 'i_Point': 0, 'i_Step': 0, 'i_ADViewTime': 0, 'i_Version': 13})
    elif pass_entry.get('i_DataID') != 13:
        pass_entry['i_DataID'] = 13
        pass_entry['i_Version'] = 13
    return evp

def _normalise_subscribe_list(user):
    return user.setdefault('user_subscribe_list', [])


def _normalise_ticketcollection(user):
    tickets = user.setdefault('user_ticketcollection', [])
    owned_seasons = set()
    for s in user.get('user_subscribe_list', []):
        pid = int(s.get('i_SubscribeID', 0) or 0)
        s_num = pid % 1000 if pid > 1000 else pid
        if 1 <= s_num <= 13:
            owned_seasons.add(s_num)
    for sh in user.get('user_shop', []):
        idx = int(sh.get('i_id', 0) or 0)
        if 1001 <= idx <= 3013:
            s_num = idx % 1000
            if 1 <= s_num <= 13:
                owned_seasons.add(s_num)
    for t in tickets:
        tid = int(t.get('i_id', 0) or 0)
        if 1 <= tid <= 13:
            owned_seasons.add(tid)
    result = [{'i_id': sid} for sid in sorted(owned_seasons)]
    user['user_ticketcollection'] = result
    return result

def _sync_follower_profiles_and_rewards(user):
    """Ensure all owned followers have corresponding profiles with valid cumulative EXP and unlocked information milestones."""
    from server.handlers.follower import _follower_data, _apply_profile_exp, _sync_follower_unlock_rewards
    _, _, level_data, f_to_p, _ = _follower_data()

    profiles = user.setdefault('user_follower_profile', [])
    existing_profiles = {int(p.get('i_id', 0) or 0): p for p in profiles}

    for f in user.get('user_follower', []):
        fid = int(f.get('i_id', 0) or 0)
        flvl = int(f.get('i_Level', 1) or 1)
        if not fid:
            continue
        pid = f_to_p.get(fid, fid)
        if pid not in existing_profiles:
            p = {
                'i_id': pid,
                'i_Level': flvl,
                'd_Exp': 0,
                'i_AddCandy': 0,
            }
            profiles.append(p)
            existing_profiles[pid] = p
        else:
            p = existing_profiles[pid]
            max_lvl = max(int(p.get('i_Level', 1) or 1), flvl)
            p['i_Level'] = max_lvl
            f['i_Level'] = max_lvl

    # Ensure Guitar Girl profile (100000) exists starting at Level 1
    if 100000 not in existing_profiles:
        p100 = {
            'i_id': 100000,
            'i_Level': 1,
            'd_Exp': 0,
            'i_AddCandy': 0,
        }
        profiles.append(p100)
        existing_profiles[100000] = p100
    else:
        p100 = existing_profiles[100000]
        if int(p100.get('i_Level', 1) or 1) >= 20:
            p100['i_Level'] = 1
            p100['d_Exp'] = 0
            p100['i_AddCandy'] = 0
            user['user_follower_profile_reward'] = [
                r for r in user.get('user_follower_profile_reward', [])
                if int(r.get('i_id', 0) or 0) != 100000
            ]
        else:
            p100['i_Level'] = max(1, int(p100.get('i_Level', 1) or 1))

    # Reconcile and heal cumulative EXP for all follower profiles
    for p in profiles:
        pid = int(p.get('i_id', 0) or 0)
        p_levels = level_data.get(pid) or level_data.get(1, {})
        _apply_profile_exp(p, p_levels, 0)

    # Synchronize unlocked information milestones in user_follower_profile_reward
    _sync_follower_unlock_rewards(user)

def _user_contents(user):
    # Do not expose skills before their character-level gates.  The game-data
    # table defines the three Guitar Girl skills at Lv. 100 / 300 / 500; the
    # separate cooldown-reset skill unlocks at Lv. 10.
    skills = user.setdefault('user_skill', [
        {'i_id': 1, 'i_Level': 1, 'b_Activate': 0,
         'l_ActivateOnTicks': 0, 'l_ActivateOffTicks': 0},
    ])
    character_level = max(
        (int(c.get('i_Level', 0) or 0) for c in user.get('characters', [])),
        default=0,
    )
    skill_unlock_levels = {1: 100, 2: 300, 3: 500, 4: 10}
    skills[:] = [
        skill for skill in skills
        if character_level >= skill_unlock_levels.get(skill.get('i_id'), 0)
    ]
    for skill_id, unlock_level in skill_unlock_levels.items():
        if (character_level >= unlock_level
                and not any(skill.get('i_id') == skill_id for skill in skills)):
            skills.append({'i_id': skill_id, 'i_Level': 1, 'b_Activate': 0,
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

    return {
        'user_achievement': _normalise_achievements(user),
        'user_buff': _active_buffs(user),
        'user_candy_shop': user.setdefault('user_candy_shop', []),
        'user_character': user.get('characters', []),
        'user_costume': user.setdefault('costumes', [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}]),
        'user_daily_mission': _normalise_daily_missions(user),
        'user_follower': user.setdefault('user_follower', [
            {'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0},
        ]),
        'user_music': user.setdefault('user_music', [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0,
                                                       'b_EncoreBonusAppear': 0, 'l_EncoreBonusActivateTime': 0,
                                                       'i_EncoreBonusFollowerId': 0, 'i_ChThirdActiveTime': 0}]),
        'user_prop': props,
        'user_unit': user.setdefault('user_unit', [{'i_id': 1, 'i_Level': 1}]),
        'user_skill': skills,
        'user_shop': user.setdefault('user_shop', []),
        # Chat room 1 (Joy) is unlocked at start with unread notification
        'user_messenger': _starter_messenger(user),
        'user_guitar': user.setdefault('user_guitar', [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}]),
        # Star Pass: read from persisted user data, default to Season 13
        'user_event_point': _normalise_event_points(user),
        # Star Pass Subscriptions: Season 13 Thẻ Sao Nâng Cấp is active
        'user_subscribe_list': _normalise_subscribe_list(user),
        'user_subscribe_pass_reward': user.setdefault('user_subscribe_pass_reward', []),
        'user_ticketcollection': _normalise_ticketcollection(user),
        'user_follower_profile_reward': user.setdefault('user_follower_profile_reward', []),
        'user_follower_profile': profiles,
        'user_follower_giftitem': user.setdefault('user_follower_giftitem', [{'i_id': 1, 'i_Value': 141}]),
        'user_chthird_stage': user.get('user_chthird_stage') or user.setdefault('user_ch_third_stage', [{'i_id': 1001, 'i_ChapterId': 1, 'i_StageIndex': 1, 'i_Star': 3}]),
        'user_tutorial': user.setdefault('user_tutorial', [{'i_id': i} for i in range(1, 8)]),
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
        _remove_legacy_currency_grant(user)
        _remove_legacy_paid_subscriptions(user)
        _remove_legacy_unlock_all(user)
        area_map = {int(k): v for k, v in user.get('areas', {}).items()}
        ud = user['userdata']
        ct = str(ud.get('u_create_time', ''))
        if not ct.lstrip('-').isdigit():
            ud['u_create_time'] = str(int(time.time()))
        contents = _user_contents(user)
        state.save_user(user)
        return {
            'user': ud,
            'area_data': area_map,
            'user_contents': contents,
        }, OK
    ud = user['userdata']
    return {'user': {'u_seq': ud['u_seq'], 'u_id': ud['u_id']}}, OK

@cmd('userSave')
def h_user_save(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    with state._LOCK:
        user = state.get_user(uuid)
        if user:
            if 'user_achievement' in p: _normalise_achievements(user, p['user_achievement'])
            if 'user_character' in p:   user['characters'] = p['user_character']
            if 'user_costume' in p:     user['costumes'] = p['user_costume']
            if 'user_music' in p:       user['user_music'] = p['user_music']
            if 'user_guitar' in p:      user['user_guitar'] = p['user_guitar']
            if 'user_follower' in p:
                user['user_follower'] = p['user_follower']
                _sync_follower_profiles_and_rewards(user)
            if 'user_messenger' in p:   user['user_messenger'] = p['user_messenger']
            if 'user_ticketcollection' in p: user['user_ticketcollection'] = p['user_ticketcollection']
            if 'user_event_point' in p: user['user_event_point'] = p['user_event_point']
            if 'user_daily_mission' in p: _normalise_daily_missions(user, p['user_daily_mission'])
            if 'user_prop' in p:        user['user_prop'] = p['user_prop']
            if 'user_candy_shop' in p:  user['user_candy_shop'] = p['user_candy_shop']
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
    if not user:
        return {}, OK
    load_type = p.get('type')
    if load_type == 'shop':
        return {'user_contents': {'user_shop': user.get('user_shop', [])}}, OK
    elif load_type == 'buff':
        return {'user_contents': {'user_buff': _active_buffs(user)}}, OK
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

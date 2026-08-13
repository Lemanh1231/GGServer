import time
from server import state
from server.handlers.registry import cmd, OK, _payload

def _remove_legacy_paid_subscriptions(user):
    """Remove the former unlock-all Gold Star Card seed from existing saves."""
    if not user.get('user_subscribe_list'):
        return
    user['user_subscribe_list'] = []
    state.save_user(user)


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
        level = update.get('i_Level', previous.get('i_Level', 1))
        try:
            level = max(1, int(level or 1))
        except (TypeError, ValueError):
            level = 1
        result.append({
            'i_id': item_id,
            'i_Level': level,
            'd_Quantity': update.get('d_Quantity', previous.get('d_Quantity', 0)),
            's_Quantity': update.get('s_Quantity', previous.get('s_Quantity', '')),
        })
    user['achievements'] = result
    return result


def _normalise_daily_missions(user, incoming=None):
    """Restore fields omitted by the compact daily-mission userSave payload."""
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
        result.append({
            'i_id': item_id,
            'i_Level': level,
            'd_Quantity': update.get('d_Quantity', previous.get('d_Quantity', 0)),
            'upd_date': update.get('upd_date', previous.get('upd_date', '')),
        })
    user['user_daily_mission'] = result
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
    user['user_buff'] = buffs
    return buffs

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

    return {
        'user_achievement': _normalise_achievements(user),
        'user_buff': _active_buffs(user),
        'user_candy_shop': [
            {'i_id': 1, 'i_CurrentBuyCount': 1, 'i_TotalBuyCount': 1, 'l_LastBuyTick': 1767022695, 'upd_day': 20251230},
            {'i_id': 2, 'i_CurrentBuyCount': 1, 'i_TotalBuyCount': 1, 'l_LastBuyTick': 1767114498, 'upd_day': 20251231},
        ],
        'user_character': user.get('characters', []),
        'user_costume': user.setdefault('costumes', [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}]),
        'user_daily_mission': _normalise_daily_missions(user),
        'user_follower': user.setdefault('user_follower', [
            {'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0},
        ]),
        'user_music': user.setdefault('user_music', [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0,
                                                       'b_EncoreBonusAppear': 0, 'l_EncoreBonusActivateTime': 0,
                                                       'i_EncoreBonusFollowerId': 0, 'i_ChThirdActiveTime': 0}]),
        'user_prop': user.setdefault('user_prop', [{'i_id': 1, 'i_Level': 1}, {'i_id': 2, 'i_Level': 1}]),
        'user_unit': user.setdefault('user_unit', [{'i_id': 1, 'i_Level': 1}]),
        'user_skill': skills,
        'user_shop': user.setdefault('user_shop', []),
        # Chat rooms and album/ticket images are progression rewards.  Do not
        # fabricate them for a new profile.
        'user_messenger': user.setdefault('user_messenger', []),
        'user_guitar': user.setdefault('user_guitar', [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}]),
        # Star Pass: read from persisted user data, default to fresh start
        'user_event_point': user.setdefault('user_event_point', [
            {'s_EventType': 'Pass', 'i_DataID': 5, 'i_Point': 0, 'i_Step': 0, 'i_ADViewTime': 0, 'i_Version': 5},
        ]),
        # Keep this empty: Free Pass rewards are available without a card,
        # while a populated list unlocks the paid/gold Star Pass track.
        # A non-empty list represents the paid/gold Star Card entitlement.
        'user_subscribe_list': user.setdefault('user_subscribe_list', []),
        'user_subscribe_pass_reward': user.setdefault('user_subscribe_pass_reward', []),
        'user_ticketcollection': user.setdefault('user_ticketcollection', []),
        'user_follower_profile_reward': user.setdefault('user_follower_profile_reward', []),
        'user_follower_profile': user.setdefault('user_follower_profile', [
            {'i_id': 1, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0},
        ]),
        'user_follower_giftitem': user.setdefault('user_follower_giftitem', [{'i_id': 1, 'i_Value': 141}]),
        # This is server-owned progress.  In particular tutorial 14 is the
        # Chapter 3 introduction; returning only a fabricated 1..7 list made
        # the client replay it every time the chapter was opened.
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
        # Persist migrations of compact userSave records before the client
        # receives them, otherwise a subsequent login would lose their tiers.
        state.save_user(user)
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
        if 'user_achievement' in p: _normalise_achievements(user, p['user_achievement'])
        if 'user_character' in p:   user['characters'] = p['user_character']
        if 'user_costume' in p:     user['costumes'] = p['user_costume']
        if 'user_music' in p:       user['user_music'] = p['user_music']
        if 'user_guitar' in p:      user['user_guitar'] = p['user_guitar']
        if 'user_follower' in p:    user['user_follower'] = p['user_follower']
        if 'user_messenger' in p:   user['user_messenger'] = p['user_messenger']
        if 'user_ticketcollection' in p: user['user_ticketcollection'] = p['user_ticketcollection']
        if 'user_event_point' in p: user['user_event_point'] = p['user_event_point']
        if 'user_daily_mission' in p: _normalise_daily_missions(user, p['user_daily_mission'])
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
    # Never turn a client-side list of Star Pass ids into a paid entitlement.
    # The Free track is available independently of this response.
    subs = []
    if user:
        user['user_subscribe_list'] = subs
        state.save_user(user)
    return {'u_seq': p.get('u_seq', 0), 'user_subscribe_list': subs}, OK

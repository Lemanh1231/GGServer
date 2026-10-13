import json
import os
from server import state
from server.handlers.registry import cmd, OK, _payload

_GAME_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'gamedata', 'game_data.json')

def _follower_data():
    """Return follower profile, normal gift and level definitions from game data."""
    try:
        with open(_GAME_DATA_PATH, encoding='utf-8') as f:
            data = json.load(f)
        profiles = {int(row['1']): row for row in data.get('28', [])}
        followers = {int(row['1']): row for row in data.get('5', [])}
        gifts = {int(row['1']): row for row in data.get('30', [])}
        levels = {}
        for row in data.get('31', []):
            levels.setdefault(int(row['2']), {})[int(row['3'])] = row
        f_to_p = {int(row['1']): int(row.get('47', row['1']) or row['1']) for row in data.get('5', [])}
        return profiles, gifts, levels, f_to_p, followers
    except (OSError, ValueError, TypeError, json.JSONDecodeError, KeyError):
        return {}, {}, {}, {}, {}

def _apply_profile_exp(profile, level_rows, exp_gain=0):
    """Apply gift/ad/encore EXP to a follower profile using Table 31 (followerprofilelevel).

    Follower profiles in the game client (GgFollowerProfileManagerSGT) use
    cumulative total EXP from Table 31 (getFollowerProfileLevelData):
    - Level 1: 0 EXP
    - Level 2: 50 EXP
    - Level 3: 150 EXP
    - Level 4: 350 EXP
    ...
    - Level 20: 141,890 EXP (283,780 for Guitar Girl 100000)

    On the client UI, current level EXP is displayed as:
      (profile.d_Exp - currentLevel.RequireEXP) / (nextLevel.RequireEXP - currentLevel.RequireEXP)

    profile['d_Exp'] stores CUMULATIVE TOTAL EXP across all levels.
    profile['i_Level'] is determined purely by the highest level in Table 31 whose RequireEXP <= d_Exp.
    profile['i_Level'] CANNOT exceed max level (20).
    Follower stage level (user_follower.i_Level) is an entirely separate system and must NEVER be synced to profile level.
    """
    if not profile or not level_rows:
        return

    cur_exp = max(0, int(profile.get('d_Exp', 0) or 0))
    total_exp = cur_exp + max(0, int(exp_gain or 0))

    max_level = max(level_rows.keys()) if level_rows else 20
    max_req = int(level_rows[max_level].get('4', 0) or 0)
    if total_exp > max_req:
        total_exp = max_req

    reached_level = 1
    for lvl in sorted(level_rows.keys()):
        req = int(level_rows[lvl].get('4', 0) or 0)
        if total_exp >= req:
            reached_level = lvl
        else:
            break

    profile['i_Level'] = min(max_level, reached_level)
    profile['d_Exp'] = total_exp

    total_add_candy = sum(
        int(level_rows[l].get('7', 0) or 0)
        for l in range(1, profile['i_Level'] + 1)
        if int(level_rows.get(l, {}).get('7', -1) or -1) > 0
    )
    profile['i_AddCandy'] = total_add_candy

def _sync_follower_profiles(user, target_profile_id=None):
    """Ensure all owned followers have corresponding profiles in user_follower_profile.
    
    CRITICAL: Follower stage levels (user_follower.i_Level) are upgraded by Likes/Fans
    and go up to 2000+. Follower intimacy profiles (user_follower_profile.i_Level) are
    upgraded by Gifts/EXP and only go up to level 20. They are COMPLETELY INDEPENDENT.
    NEVER copy user_follower.i_Level into profile.i_Level, and NEVER overwrite
    user_follower.i_Level with profile.i_Level.
    """
    if not user:
        return []
    profiles_def, _, level_data, f_to_p, _ = _follower_data()

    profiles = user.setdefault('user_follower_profile', [])
    profile_map = {int(p.get('i_id', 0) or 0): p for p in profiles}

    # Ensure all owned followers from user_follower are reflected in profiles
    for f in user.get('user_follower', []):
        fid = int(f.get('i_id', 0) or 0)
        if not fid:
            continue
        pid = f_to_p.get(fid, fid)
        if pid not in profile_map:
            p = {'i_id': pid, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0}
            profiles.append(p)
            profile_map[pid] = p

    # Ensure Guitar Girl profile (100000) exists
    if 100000 not in profile_map:
        p100 = {'i_id': 100000, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0}
        profiles.append(p100)
        profile_map[100000] = p100

    # Reconcile EXP and levels for all profiles
    for pid, p in profile_map.items():
        p_levels = level_data.get(pid) or level_data.get(1, {})
        _apply_profile_exp(p, p_levels, 0)

    # Sanitize claimed rewards: remove any claim for levels beyond reached profile level
    claims = user.setdefault('user_follower_profile_reward', [])
    valid_claims = []
    seen = set()
    for c in claims:
        cid = int(c.get('i_id', 0) or 0)
        clvl = int(c.get('i_RewardLevel', 0) or 0)
        prof = profile_map.get(cid)
        if prof and clvl <= int(prof.get('i_Level', 1) or 1):
            key = (cid, clvl)
            if key not in seen:
                seen.add(key)
                valid_claims.append(c)

    # Ensure reached story / info milestones (Table 31 col 6 != '') are unlocked
    for pid, p in profile_map.items():
        cur_lvl = int(p.get('i_Level', 1) or 1)
        p_levels = level_data.get(pid) or level_data.get(1, {})
        for lvl in range(1, cur_lvl + 1):
            row = p_levels.get(lvl, {})
            if row.get('6'):
                key = (pid, lvl)
                if key not in seen:
                    seen.add(key)
                    valid_claims.append({'i_id': pid, 'i_RewardLevel': lvl})

    user['user_follower_profile_reward'] = valid_claims
    _sync_follower_messenger(user)
    return valid_claims

_sync_follower_unlock_rewards = _sync_follower_profiles

FOLLOWER_MESSENGER_MAP = {
    1: (1, 1),        # Follower 1 (Classmate Joy) -> Room 1, Group 1
    2: (2, 2),        # Follower 2 (Convenience Store Friend) -> Room 2, Group 2
    3: (3, 6),        # Follower 3 (Homeroom Teacher) -> Room 3, Group 6
    4: (4, 9),        # Follower 4 (Quiet Upperclassman) -> Room 4, Group 9
    5: (5, 13),       # Follower 5 (Neighbor Moa) -> Room 5, Group 13
    6: (6, 18),       # Follower 6 (Friend Elle) -> Room 6, Group 18
    7: (7, 20),       # Follower 7 (Class President Amber) -> Room 7, Group 20
    8: (8, 51),       # Follower 8 (School President) -> Room 8, Group 51
    9: (9, 62),       # Follower 9 (New Employee Sua) -> Room 9, Group 62
    10: (10, 54),     # Follower 10 (Cat Butler) -> Room 10, Group 54
    11: (11, 74),     # Follower 11 (Classmate Jae) -> Room 11, Group 74
    12: (12, 80),     # Follower 12 (Happy Bakery) -> Room 12, Group 80
    13: (13, 88),     # Follower 13 (MN Trainee Nova) -> Room 13, Group 88
    14: (14, 90),     # Follower 14 (Fashionista Yeri) -> Room 14, Group 90
    15: (15, 91),     # Follower 15 (Band Mocha Latte) -> Room 15, Group 91
    201: (1, 1),      # Follower 201 (Joy Ch2) -> Room 1, Group 1
    202: (5, 13),     # Follower 202 (Moa Ch2) -> Room 5, Group 13
    203: (203, 114),  # Follower 203 (Reading Fox) -> Room 203, Group 114
    204: (204, 127),  # Follower 204 (Friend Ruby) -> Room 204, Group 127
    205: (205, 138),  # Follower 205 (Friend Alex) -> Room 205, Group 138
    206: (206, 178),  # Follower 206 (Busking TV) -> Room 206, Group 178
    207: (207, 181),  # Follower 207 (Friend Sora) -> Room 207, Group 181
    208: (208, 186),  # Follower 208 (Jessica) -> Room 208, Group 186
}

def _sync_follower_messenger(user):
    """Ensure all owned followers have corresponding chat rooms in user_messenger."""
    if not user:
        return []
    ms = user.setdefault('user_messenger', [])
    existing_rooms = {int(r.get('i_MessengerChatRoomId', 0) or 0): r for r in ms}

    # Ensure starter follower (Joy - Room 1) exists
    if 1 not in existing_rooms:
        r1 = {
            'i_MessengerChatRoomId': 1,
            'i_LastConfirmIndex': -1,
            's_UnlockGroupList': '1',
            'l_UpdateTimeTicks': 0,
        }
        ms.append(r1)
        existing_rooms[1] = r1

    followers = user.get('user_follower', [])
    f_levels = {}
    for f in followers:
        fid = int(f.get('i_id', 0) or 0)
        flvl = int(f.get('i_Level', 0) or 0)
        f_levels[fid] = flvl
        if fid in FOLLOWER_MESSENGER_MAP:
            room_id, init_group = FOLLOWER_MESSENGER_MAP[fid]
            if room_id not in existing_rooms:
                new_room = {
                    'i_MessengerChatRoomId': room_id,
                    'i_LastConfirmIndex': -1,
                    's_UnlockGroupList': str(init_group),
                    'l_UpdateTimeTicks': 0,
                }
                ms.append(new_room)
                existing_rooms[room_id] = new_room

    # Group chat room 16 (Joy, Moa) unlocks when Follower 1 level >= 1250
    if f_levels.get(1, 0) >= 1250 and 16 not in existing_rooms:
        r16 = {
            'i_MessengerChatRoomId': 16,
            'i_LastConfirmIndex': -1,
            's_UnlockGroupList': '76',
            'l_UpdateTimeTicks': 0,
        }
        ms.append(r16)
        existing_rooms[16] = r16

    # Group chat room 17 (Joy, Moa, Ruby, Alex) unlocks when Follower 201 level >= 650
    if f_levels.get(201, 0) >= 650 and 17 not in existing_rooms:
        r17 = {
            'i_MessengerChatRoomId': 17,
            'i_LastConfirmIndex': -1,
            's_UnlockGroupList': '139',
            'l_UpdateTimeTicks': 0,
        }
        ms.append(r17)
        existing_rooms[17] = r17

    # Ensure each room has a valid s_UnlockGroupList
    for rid, r in existing_rooms.items():
        if not r.get('s_UnlockGroupList'):
            if rid == 16:
                r['s_UnlockGroupList'] = '76'
            elif rid == 17:
                r['s_UnlockGroupList'] = '139'
            elif rid in FOLLOWER_MESSENGER_MAP:
                r['s_UnlockGroupList'] = str(FOLLOWER_MESSENGER_MAP[rid][1])
            else:
                r['s_UnlockGroupList'] = '1'

    user['user_messenger'] = ms
    return ms

def _merge_user_messenger(user, incoming_ms):
    """Safely merge incoming user_messenger without dropping server-known rooms."""
    if incoming_ms is None:
        return
    ms = user.setdefault('user_messenger', [])
    room_map = {int(r.get('i_MessengerChatRoomId', 0) or 0): r for r in ms}
    for inc in incoming_ms:
        rid = int(inc.get('i_MessengerChatRoomId', 0) or 0)
        if rid in room_map:
            room_map[rid].update(inc)
        else:
            ms.append(inc)
            room_map[rid] = inc
    user['user_messenger'] = ms


def _profile_reward_data():
    """Return the configured follower-profile milestones and their rewards."""
    try:
        with open(_GAME_DATA_PATH, encoding='utf-8') as f:
            data = json.load(f)
        milestones = {
            (int(row['2']), int(row['3'])): row
            for row in data.get('31', [])
        }
        rewards = {int(row['1']): row for row in data.get('13', [])}
        return milestones, rewards
    except (OSError, ValueError, TypeError, json.JSONDecodeError, KeyError):
        return {}, {}

def _profile_level_for_reward(user, profile_id):
    """Resolve the level that is allowed to claim a profile milestone."""
    _, _, _, f_to_p, _ = _follower_data()
    profile = next((row for row in user.get('user_follower_profile', [])
                    if int(row.get('i_id', 0) or 0) in (profile_id, f_to_p.get(profile_id))), None)
    if profile:
        return max(1, int(profile.get('i_Level', 1) or 1))
    return 1

@cmd('setFollowerProfileGift')
def h_set_follower_profile_gift(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    
    with state._LOCK:
        user = state.get_user(uuid)
        if not user:
            return {}, OK

        try:
            raw_profile_id = int(p.get('profile_id', 1))
            gift_id = int(p.get('gift_id', 1))
            use_count = int(p.get('use_gitf_value', 1))
        except (TypeError, ValueError):
            return {}, OK

        if use_count <= 0:
            return {}, OK

        profiles_def, gifts_def, level_data, f_to_p, followers_tbl = _follower_data()
        profile_id = f_to_p.get(raw_profile_id, raw_profile_id)
        profile_def = profiles_def.get(profile_id) or profiles_def.get(raw_profile_id)
        gift_def = gifts_def.get(gift_id)
        p_levels = level_data.get(profile_id) or level_data.get(raw_profile_id) or level_data.get(1, {})

        # Ensure follower exists in user_follower (NPC followers only)
        followers = user.setdefault('user_follower', [])
        follower = next((item for item in followers if int(item.get('i_id', 0) or 0) in (profile_id, raw_profile_id)), None)
        if follower is None and raw_profile_id != 100000:
            follower = {'i_id': raw_profile_id, 'i_Level': 1, 'i_BonusLevel': 0}
            followers.append(follower)

        # Ensure profile exists in user_follower_profile (starts at Level 1, 0 EXP)
        profiles = user.setdefault('user_follower_profile', [])
        profile = next((item for item in profiles if int(item.get('i_id', 0) or 0) in (profile_id, raw_profile_id)), None)
        if profile is None:
            profile = {'i_id': profile_id, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0}
            profiles.append(profile)

        # Inventory lookup
        inventory = user.setdefault('user_follower_giftitem', [{'i_id': 1, 'i_Value': 141}])
        gift_item = next((item for item in inventory if int(item.get('i_id', 0) or 0) == gift_id), None)
        if gift_item is None:
            gift_item = {'i_id': gift_id, 'i_Value': 0}
            inventory.append(gift_item)

        cur_val = max(0, int(gift_item.get('i_Value', 0) or 0))
        gift_item['i_Value'] = cur_val

        # If user has no gifts remaining, heal profile and return current count so client UI displays cleanly
        if cur_val <= 0 or not gift_def:
            _apply_profile_exp(profile, p_levels, 0)
            _sync_follower_profiles(user)
            state.save_user(user)
            return {
                'i_gift_type': int((gift_def or {}).get('2', 0) or 1),
                'user_follower_giftitem': gift_item,
                'user_follower_profile': profile,
            }, OK

        # Deduct gifts safely
        actual_use = min(cur_val, use_count)
        gift_item['i_Value'] = cur_val - actual_use
        exp_gain = int(gift_def.get('3', 0) or 0) * actual_use
        _apply_profile_exp(profile, p_levels, exp_gain)

        _sync_follower_profiles(user)

        state.save_user(user)

        return {
            'i_gift_type': int(gift_def.get('2', 0) or 0),
            'user_follower_giftitem': gift_item,
            'user_follower_profile': profile,
        }, OK

@cmd('setUserFollowerProfileReward')
def h_set_user_follower_profile_reward(req, player, ctx):
    """Claim one follower-profile level reward exactly once (supports single level or comma-separated levels)."""
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    
    with state._LOCK:
        user = state.get_user(uuid)
        if not user:
            return [], OK

        try:
            raw_profile_id = int(p.get('i_id'))
        except (TypeError, ValueError):
            return [], OK

        profiles_def, _, _, f_to_p, _ = _follower_data()
        profile_id = f_to_p.get(raw_profile_id, raw_profile_id)

        s_level_str = str(p.get('s_level', ''))
        levels = []
        for part in s_level_str.split(','):
            part = part.strip()
            if part.isdigit():
                levels.append(int(part))

        if not levels:
            return [], OK

        milestones, reward_defs = _profile_reward_data()
        claims = user.setdefault('user_follower_profile_reward', [])
        ret_items = []
        changed = False

        profiles = user.setdefault('user_follower_profile', [])
        profile = next((row for row in profiles
                        if int(row.get('i_id', 0) or 0) in (profile_id, raw_profile_id)), None)
        if not profile:
            profile = {
                'i_id': raw_profile_id,
                'i_Level': 1,
                'd_Exp': 0,
                'i_AddCandy': 0,
            }
            profiles.append(profile)
            changed = True

        curr_lvl = _profile_level_for_reward(user, profile_id)

        for reward_level in levels:
            if reward_level < 1:
                continue
            milestone = milestones.get((profile_id, reward_level)) or milestones.get((raw_profile_id, reward_level))
            already_claimed = any(int(row.get('i_id', 0) or 0) in (profile_id, raw_profile_id)
                                  and int(row.get('i_RewardLevel', 0) or 0) == reward_level
                                  for row in claims)

            if already_claimed:
                ret_items.append({
                    'i_id': raw_profile_id,
                    'i_level': reward_level,
                    'reward_data': [],
                    'user_follower_profile': profile,
                })
                continue

            if not milestone or curr_lvl < reward_level:
                continue

            reward = reward_defs.get(int(milestone.get('5', -1) or -1))
            reward_type = reward_id = reward_value = 0
            if reward:
                reward_type = int(reward.get('3', 0) or 0)
                reward_id = int(reward.get('4', 0) or 0)
                reward_value = int(reward.get('5', 0) or 0)
                if reward_type and reward_value:
                    from server.handlers.reward import _give_reward
                    _give_reward(user, {'reward_type': reward_type,
                                        'reward_id': reward_id,
                                        'reward_value': reward_value})

            claim = {'i_id': raw_profile_id, 'i_RewardLevel': reward_level}
            claims.append(claim)
            if profile_id != raw_profile_id:
                claims.append({'i_id': profile_id, 'i_RewardLevel': reward_level})
            changed = True

            ret_items.append({
                'i_id': raw_profile_id,
                'i_level': reward_level,
                'reward_data': [{
                    'reward_type': reward_type,
                    'reward_id': reward_id,
                    'reward_value': float(reward_value),
                }] if (reward_type and reward_value) else [],
                'user_follower_profile': profile,
            })

        if changed:
            state.save_user(user)

        return ret_items, OK

@cmd('setFollowerQuestInfinite')
def h_set_follower_quest_infinite(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    u_seq = user.get('userdata', {}).get('u_seq', 100001) if user else 100001
    q_id = int(p.get('i_id', 1) or 1)
    
    # Locate or create quest in user_follower_quest
    quests = user.setdefault('user_follower_quest', []) if user else []
    quest = next((q for q in quests if int(q.get('i_id', 0) or 0) == q_id), None)
    if not quest:
        quest = {
            'i_id': q_id,
            'i_CurrentID': q_id,
            'i_CompleteID': 0,
            'd_ConditionValue1': 0.0,
            'd_ConditionValue2': 0.0,
            'd_ConditionValue3': 0.0,
            'i_RewardReceived1': 0,
            'i_RewardReceived2': 0,
            'i_RewardReceived3': 0,
            'i_isInfinity': 1
        }
        quests.append(quest)
    else:
        quest['i_isInfinity'] = 1
    if user:
        state.save_user(user)

    return {
        'u_seq': u_seq,
        'user_follower_quest': quest
    }, OK

@cmd('setUserFollowerQuest')
def h_set_user_follower_quest(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    cur_id = int(p.get('i_CurrentID', 0) or 0)
    sub_id = int(p.get('i_SubID', 1) or 1)
    cond_val = float(p.get('d_ConditionValue', 0.0) or 0.0)
    quest = {
        'i_CurrentID': cur_id,
        'i_CompleteID': 0,
        'd_ConditionValue1': 0.0,
        'd_ConditionValue2': 0.0,
        'd_ConditionValue3': 0.0,
        'i_RewardReceived1': 0,
        'i_RewardReceived2': 0,
        'i_RewardReceived3': 0,
        'next_flg': 0,
        'reward_data': [],
    }
    if user:
        quests = user.setdefault('user_follower_quest', [])
        found_quest = next((q for q in quests if int(q.get('i_CurrentID', 0) or 0) == cur_id), None)
        if not found_quest:
            found_quest = dict(quest)
            quests.append(found_quest)
        if sub_id == 1:
            found_quest['d_ConditionValue1'] = cond_val
        elif sub_id == 2:
            found_quest['d_ConditionValue2'] = cond_val
        elif sub_id == 3:
            found_quest['d_ConditionValue3'] = cond_val
        state.save_user(user)
        quest = found_quest
    return quest, OK

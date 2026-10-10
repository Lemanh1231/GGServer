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

def _apply_profile_exp(profile, level_rows, exp_gain):
    """Apply gift/ad EXP to a follower profile.

    Follower profiles in the game client (GgFollowerProfileManagerSGT) use
    cumulative total EXP from Table 31 (getFollowerProfileLevelData):
    - Level 1: 0 EXP
    - Level 2: 50 EXP
    - Level 3: 150 EXP
    - Level 4: 350 EXP
    ...
    - Level 20: 141,890 EXP

    On the client UI, current level EXP is displayed as:
      (profile.d_Exp - currentLevel.RequireEXP) / (nextLevel.RequireEXP - currentLevel.RequireEXP)

    Therefore:
    1. profile['d_Exp'] stores CUMULATIVE TOTAL EXP across all levels.
    2. Total EXP never has level costs subtracted from it.
    3. If an existing profile has d_Exp < currentLevel.RequireEXP (due to old server bugs
       where d_Exp was reset or stored as within-level delta), we rebase it to
       currentLevel.RequireEXP + d_Exp before applying exp_gain.
    """
    if not profile or not level_rows:
        return

    cur_level = max(1, int(profile.get('i_Level', 1) or 1))
    cur_exp = max(0, int(profile.get('d_Exp', 0) or 0))

    base_req = int(level_rows.get(cur_level, {}).get('4', 0) or 0)
    # Heal legacy within-level EXP
    if cur_exp < base_req:
        cur_exp = base_req + cur_exp

    total_exp = cur_exp + max(0, int(exp_gain or 0))

    # Cap at max level's requirement if exceeded
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

    profile['i_Level'] = reached_level
    profile['d_Exp'] = total_exp

    total_add_candy = sum(
        int(level_rows[l].get('7', 0) or 0)
        for l in range(1, reached_level + 1)
        if int(level_rows.get(l, {}).get('7', -1) or -1) > 0
    )
    profile['i_AddCandy'] = total_add_candy

def _sync_follower_unlock_rewards(user, target_profile_id=None, target_level=None):
    """Ensure user_follower_profile_reward contains all reached
    information unlock milestone levels (Table 31 col 6 != '') for owned followers."""
    if not user:
        return []
    profiles_def, _, level_data, f_to_p, _ = _follower_data()

    claims = user.setdefault('user_follower_profile_reward', [])
    existing_claims = {(int(r.get('i_id', 0) or 0), int(r.get('i_RewardLevel', 0) or 0)) for r in claims}

    profiles = user.setdefault('user_follower_profile', [])
    profile_map = {int(p.get('i_id', 0) or 0): p for p in profiles}

    # Ensure all owned followers from user_follower are reflected in profiles
    for f in user.get('user_follower', []):
        fid = int(f.get('i_id', 0) or 0)
        if not fid:
            continue
        pid = f_to_p.get(fid, fid)
        flvl = int(f.get('i_Level', 1) or 1)
        if pid not in profile_map:
            p = {'i_id': pid, 'i_Level': flvl, 'd_Exp': 0, 'i_AddCandy': 0}
            profiles.append(p)
            profile_map[pid] = p
        else:
            profile_map[pid]['i_Level'] = max(int(profile_map[pid].get('i_Level', 1) or 1), flvl)
            f['i_Level'] = profile_map[pid]['i_Level']

    for pid, p in profile_map.items():
        cur_lvl = int(p.get('i_Level', 1) or 1)
        if target_profile_id is not None and pid == target_profile_id and target_level is not None:
            cur_lvl = max(cur_lvl, target_level)
            p['i_Level'] = cur_lvl

        p_levels = level_data.get(pid) or level_data.get(1, {})

        # Milestone information unlock levels from Table 31 (e.g. Levels 5, 7, 10, 15, 20)
        for lvl in range(1, cur_lvl + 1):
            row = p_levels.get(lvl, {})
            if row.get('6'):  # unlock_info column is non-empty
                if (pid, lvl) not in existing_claims:
                    claims.append({'i_id': pid, 'i_RewardLevel': lvl})
                    existing_claims.add((pid, lvl))

    return claims

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
    follower = next((row for row in user.get('user_follower', [])
                     if int(row.get('i_id', 0) or 0) in (profile_id, f_to_p.get(profile_id))), None)
    if follower:
        return max(1, int(follower.get('i_Level', 1) or 1))
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

        # Ensure profile exists in user_follower_profile
        profiles = user.setdefault('user_follower_profile', [])
        profile = next((item for item in profiles if int(item.get('i_id', 0) or 0) in (profile_id, raw_profile_id)), None)
        if profile is None:
            follower_level = int(follower.get('i_Level', 1) or 1) if follower else 1
            profile = {'i_id': profile_id, 'i_Level': follower_level, 'd_Exp': 0, 'i_AddCandy': 0}
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
            _sync_follower_unlock_rewards(user, profile_id, int(profile['i_Level']))
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

        # Sync follower level
        reached_level = int(profile['i_Level'])
        if follower:
            follower['i_Level'] = reached_level
            for f in followers:
                fid = int(f.get('i_id', 0) or 0)
                if fid in (profile_id, raw_profile_id) or f_to_p.get(fid) == profile_id:
                    f['i_Level'] = reached_level

        _sync_follower_unlock_rewards(user, profile_id, reached_level)

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

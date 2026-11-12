import json
import os
import time
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
    201: (1, 111),    # Follower 201 (Joy Ch2) -> Room 1, Group 111
    202: (5, 110),    # Follower 202 (Moa Ch2) -> Room 5, Group 110
    203: (203, 114),  # Follower 203 (Reading Fox) -> Room 203, Group 114
    204: (204, 127),  # Follower 204 (Friend Ruby) -> Room 204, Group 127
    205: (205, 138),  # Follower 205 (Friend Alex) -> Room 205, Group 138
    206: (206, 178),  # Follower 206 (Busking TV) -> Room 206, Group 178
    207: (207, 181),  # Follower 207 (Friend Sora) -> Room 207, Group 181
    208: (208, 186),  # Follower 208 (Jessica) -> Room 208, Group 186
}

def _merge_groups_seq(existing_str, required_groups, target_proceeding=None):
    orig = [int(x.strip()) for x in str(existing_str or '').split(',') if x.strip().isdigit()]
    if target_proceeding is not None:
        target_proceeding = int(target_proceeding)
        # If target_proceeding was already completed (present in orig[:-1]),
        # preserve the player's newer active proceeding group (orig[-1]).
        if orig and target_proceeding in orig[:-1]:
            final_proc = orig[-1]
        else:
            final_proc = target_proceeding
    else:
        final_proc = orig[-1] if orig else None

    current = []
    for g in orig:
        if g not in current:
            current.append(g)
    for g in required_groups:
        g = int(g)
        if g not in current:
            current.append(g)

    if final_proc is not None:
        if final_proc in current:
            current.remove(final_proc)
        current.append(final_proc)

    return ",".join(str(x) for x in current) if current else str(target_proceeding or 1)

def _sync_follower_messenger(user):
    """Ensure all owned followers have corresponding chat rooms in user_messenger."""
    if not user:
        return []
    ms = user.setdefault('user_messenger', [])
    existing_rooms = {int(r.get('i_MessengerChatRoomId', 0) or 0): r for r in ms}

    followers = user.get('user_follower', [])
    f_levels = {}
    for f in followers:
        fid = int(f.get('i_id', 0) or 0)
        flvl = int(f.get('i_Level', 0) or 0)
        f_levels[fid] = flvl

    # Check if user has entered Chapter 2 (owns any CH2 follower 201..208)
    has_ch2 = any(fid in f_levels for fid in range(201, 209))

    # Ensure starter follower (Joy - Room 1) exists
    if 1 not in existing_rooms:
        r1 = {
            'i_MessengerChatRoomId': 1,
            'i_LastConfirmIndex': 0,
            's_UnlockGroupList': '1',
            'l_UpdateTimeTicks': 0,
        }
        ms.append(r1)
        existing_rooms[1] = r1
    elif existing_rooms[1].get('i_LastConfirmIndex', -1) < 0:
        existing_rooms[1]['i_LastConfirmIndex'] = 0

    # Auto-heal legacy corrupted group sequences generated by previous prerequisite injection bug
    # (which erroneously assigned late-game prerequisite groups as the proceeding group, muting followers).
    CORRUPT_CH1_HEAL = {
        1: (75, 1250, '1'),
        2: (77, 1100, '2'),
        3: (44, 650, '6'),
        5: (55, 625, '13'),
        6: (43, 250, '18'),
        7: (58, 375, '20'),
        16: (79, 1150, '76'),
    }
    for rid, r in list(existing_rooms.items()):
        if rid in CORRUPT_CH1_HEAL and not has_ch2:
            corrupt_last, req_lvl, clean_val = CORRUPT_CH1_HEAL[rid]
            fid = 1 if rid == 16 else rid
            groups = [int(x.strip()) for x in str(r.get('s_UnlockGroupList', '')).split(',') if x.strip().isdigit()]
            if groups and groups[-1] == corrupt_last and f_levels.get(fid, 0) < req_lvl:
                r['s_UnlockGroupList'] = clean_val
                r['i_LastConfirmIndex'] = 0
                r['l_UpdateTimeTicks'] = 0

    # Auto-heal rooms where a completed starter/CH2 group was yanked to the end after later unlocked groups
    YANKED_PROC_HEAL = {
        1: (111, {130, 136}),
        2: (2, {8, 22, 61, 125, 131, 141, 143, 145, 148}),
        5: (157, {164, 167}),
        6: (18, {63, 129, 133, 163, 168}),
        12: (109, {137}),
        16: (172, {119, 120}),
        17: (174, {176, 177}),
    }
    for rid, (yanked_grp, later_grps) in YANKED_PROC_HEAL.items():
        if rid in existing_rooms:
            r = existing_rooms[rid]
            groups = [int(x.strip()) for x in str(r.get('s_UnlockGroupList', '')).split(',') if x.strip().isdigit()]
            if len(groups) > 1 and groups[-1] == yanked_grp and any(g in later_grps for g in groups[:-1]):
                groups.pop()
                first_later_idx = next(i for i, g in enumerate(groups) if g in later_grps)
                groups.insert(first_later_idx, yanked_grp)
                r['s_UnlockGroupList'] = ",".join(str(x) for x in groups)

    # Sync individual follower rooms (CH1: 2..15, CH2: 203..208)
    for fid in f_levels:
        if fid in (1, 201, 202):
            continue  # Handled with special room/group routing below
        if fid in FOLLOWER_MESSENGER_MAP:
            room_id, init_group = FOLLOWER_MESSENGER_MAP[fid]
            if room_id not in existing_rooms:
                new_room = {
                    'i_MessengerChatRoomId': room_id,
                    'i_LastConfirmIndex': 0,
                    's_UnlockGroupList': str(init_group),
                    'l_UpdateTimeTicks': 0,
                }
                ms.append(new_room)
                existing_rooms[room_id] = new_room
            else:
                r = existing_rooms[room_id]
                if r.get('i_LastConfirmIndex', -1) < 0:
                    r['i_LastConfirmIndex'] = 0
                if not r.get('s_UnlockGroupList'):
                    r['s_UnlockGroupList'] = str(init_group)

    # Chapter 1 cross-room prerequisite satisfaction:
    # In GgTableManagerSGT / libil2cpp.so, CheckRequirement checks CompleteProgressGroupList
    # of prerequisite rooms (e.g. Group 9 requires Group 7 in Room 1).
    # We ensure these prerequisite groups are present in Room 1, 7, and 16 BEFORE their own proceeding group,
    # so each follower's initial greeting is active as the proceeding group.
    r1_prereqs = []
    if 4 in f_levels:
        r1_prereqs.extend([4, 7])
    if 5 in f_levels:
        r1_prereqs.extend([10, 12])
    if 6 in f_levels or 7 in f_levels:
        r1_prereqs.extend([15, 16])
    if 8 in f_levels or f_levels.get(7, 0) >= 75:
        r1_prereqs.extend([24, 30, 32, 33, 35, 36, 41, 45, 47])
    if 9 in f_levels or 10 in f_levels or 11 in f_levels or f_levels.get(7, 0) >= 375:
        r1_prereqs.extend([56, 57])
    if any(fid in f_levels for fid in (11, 12, 13, 14, 15)):
        r1_prereqs.extend([75])

    r1 = existing_rooms[1]
    r1_groups = [int(x.strip()) for x in str(r1.get('s_UnlockGroupList', '1')).split(',') if x.strip().isdigit()]
    joy_proceeding = r1_groups[-1] if r1_groups else 1
    if joy_proceeding == 75 and f_levels.get(1, 0) < 1250:
        joy_proceeding = 1
    r1['s_UnlockGroupList'] = _merge_groups_seq(r1.get('s_UnlockGroupList', '1'), r1_prereqs, target_proceeding=joy_proceeding)

    # Room 7: Amber's proceeding group is 20, but groups 53, 58 must be completed for Sua (9), Butler Cat (10), Jae (11), etc.
    if 7 in existing_rooms and (9 in f_levels or 10 in f_levels or 11 in f_levels or f_levels.get(7, 0) >= 375 or f_levels.get(3, 0) >= 850):
        r7 = existing_rooms[7]
        r7_groups = [int(x.strip()) for x in str(r7.get('s_UnlockGroupList', '20')).split(',') if x.strip().isdigit()]
        amber_proc = r7_groups[-1] if r7_groups else 20
        if amber_proc == 58 and f_levels.get(7, 0) < 375:
            amber_proc = 20
        r7['s_UnlockGroupList'] = _merge_groups_seq(r7.get('s_UnlockGroupList', '20'), [53, 58], target_proceeding=amber_proc)

    # Room 16 in Chapter 1: Happy Bakery (12) requires Group 79 in Room 16 completed
    if 12 in f_levels:
        if 16 not in existing_rooms:
            r16 = {
                'i_MessengerChatRoomId': 16,
                'i_LastConfirmIndex': 0,
                's_UnlockGroupList': '76,78,79,81',
                'l_UpdateTimeTicks': 0,
            }
            ms.append(r16)
            existing_rooms[16] = r16
        else:
            r16 = existing_rooms[16]
            r16['s_UnlockGroupList'] = _merge_groups_seq(r16.get('s_UnlockGroupList', '76'), [76, 78, 79], target_proceeding=81)
    elif f_levels.get(1, 0) >= 1250 and 16 not in existing_rooms:
        r16 = {
            'i_MessengerChatRoomId': 16,
            'i_LastConfirmIndex': 0,
            's_UnlockGroupList': '76',
            'l_UpdateTimeTicks': 0,
        }
        ms.append(r16)
        existing_rooms[16] = r16

    # Special handling for Chapter 2
    if has_ch2:
        # Chapter 2 cross-room prerequisite satisfaction:
        # 1. Room 12 (Happy Bakery): Bridge between CH1 and CH2
        # Group 103 (Room 12) is the prerequisite dialogue welcoming player to CH2.
        # Group 109 is required by Group 110 (Moa Room 5).
        r12_reqs = [80, 86, 87, 103]
        r12_proc = 109
        if 12 not in existing_rooms:
            r12 = {
                'i_MessengerChatRoomId': 12,
                'i_LastConfirmIndex': 0,
                's_UnlockGroupList': _merge_groups_seq('', r12_reqs, target_proceeding=r12_proc),
                'l_UpdateTimeTicks': 0,
            }
            ms.append(r12)
            existing_rooms[12] = r12
        else:
            r12 = existing_rooms[12]
            r12['s_UnlockGroupList'] = _merge_groups_seq(r12.get('s_UnlockGroupList', '80'), r12_reqs, target_proceeding=r12_proc)
            if r12.get('i_LastConfirmIndex', -1) < 0:
                r12['i_LastConfirmIndex'] = 0

        # 2. Room 6: Elle's room has groups 106 and 113 needed for CH2
        r6_reqs = [18, 26, 43, 106, 113]
        if 6 in existing_rooms:
            existing_rooms[6]['s_UnlockGroupList'] = _merge_groups_seq(existing_rooms[6].get('s_UnlockGroupList', '18'), r6_reqs, target_proceeding=None)

        # 3. Room 2: Convenience store friend has group 116 needed by group 118
        r2_reqs = [2, 5, 11, 77, 116]
        if 2 in existing_rooms:
            existing_rooms[2]['s_UnlockGroupList'] = _merge_groups_seq(existing_rooms[2].get('s_UnlockGroupList', '2'), r2_reqs, target_proceeding=None)

        # 4. Room 16 (Joy, Moa Group Chat): Story backbone for Chapter 2
        r16_reqs = [76, 78, 79, 81, 82, 104, 105, 108, 115, 118, 128, 132, 135, 171]
        r16_proceeding = 172
        if 16 not in existing_rooms:
            r16 = {
                'i_MessengerChatRoomId': 16,
                'i_LastConfirmIndex': 0,
                's_UnlockGroupList': _merge_groups_seq('', r16_reqs, target_proceeding=r16_proceeding),
                'l_UpdateTimeTicks': 0,
            }
            ms.append(r16)
            existing_rooms[16] = r16
        else:
            r16 = existing_rooms[16]
            r16['s_UnlockGroupList'] = _merge_groups_seq(r16.get('s_UnlockGroupList', '76'), r16_reqs, target_proceeding=r16_proceeding)
            if r16.get('i_LastConfirmIndex', -1) < 0:
                r16['i_LastConfirmIndex'] = 0

        # 5. Room 17 (Joy, Moa, Ruby, Alex Group Chat)
        # 173 is needed for Busking TV (206)
        needs_r17 = any(fid in f_levels for fid in (204, 205, 206, 207, 208)) or f_levels.get(201, 0) >= 650
        if needs_r17:
            r17_reqs = [139, 140, 142, 144, 146, 149, 151, 152, 153, 154, 155, 162, 173]
            r17_proceeding = 174
            if 17 not in existing_rooms:
                r17 = {
                    'i_MessengerChatRoomId': 17,
                    'i_LastConfirmIndex': 0,
                    's_UnlockGroupList': _merge_groups_seq('', r17_reqs, target_proceeding=r17_proceeding),
                    'l_UpdateTimeTicks': 0,
                }
                ms.append(r17)
                existing_rooms[17] = r17
            else:
                r17 = existing_rooms[17]
                r17['s_UnlockGroupList'] = _merge_groups_seq(r17.get('s_UnlockGroupList', '139'), r17_reqs, target_proceeding=r17_proceeding)
                if r17.get('i_LastConfirmIndex', -1) < 0:
                    r17['i_LastConfirmIndex'] = 0

        # 6. Room 1 (Joy in CH2) -> Group 111 (requires 110 completed)
        r1 = existing_rooms.get(1)
        if r1 and 201 in f_levels:
            r1['s_UnlockGroupList'] = _merge_groups_seq(r1.get('s_UnlockGroupList', '1'), [1, 75, 156], target_proceeding=111)

        # 7. Room 5 (Moa in CH2) -> Group 157 (with 110 completed)
        if 202 in f_levels:
            r5_reqs = [13, 14, 21, 25, 28, 40, 46, 55, 110]
            r5_proceeding = 157
            if 5 not in existing_rooms:
                r5 = {
                    'i_MessengerChatRoomId': 5,
                    'i_LastConfirmIndex': 0,
                    's_UnlockGroupList': _merge_groups_seq('', r5_reqs, target_proceeding=r5_proceeding),
                    'l_UpdateTimeTicks': 0,
                }
                ms.append(r5)
                existing_rooms[5] = r5
            else:
                r5 = existing_rooms[5]
                r5['s_UnlockGroupList'] = _merge_groups_seq(r5.get('s_UnlockGroupList', '13'), r5_reqs, target_proceeding=r5_proceeding)

    # Ensure each room has a valid s_UnlockGroupList and non-negative confirm index
    for rid, r in existing_rooms.items():
        if r.get('i_LastConfirmIndex', -1) < 0:
            r['i_LastConfirmIndex'] = 0
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

def _load_follower_quest_tables():
    """Load Table 26 (followerquest) and Table 13 (reward_group)."""
    try:
        with open(_GAME_DATA_PATH, encoding='utf-8') as f:
            data = json.load(f)
        quests = {int(r['1']): r for r in data.get('26', [])}
        rewards = {}
        for r in data.get('13', []):
            rewards.setdefault(int(r.get('2', r['1'])), []).append(r)
        return quests, rewards
    except Exception:
        return {}, {}


def _pick_next_follower_quest_id(user, cur_id, quests_def=None):
    """Return (next_cur_id, is_infinity) after completing all 3 sub-missions of cur_id."""
    if quests_def is None:
        quests_def, _ = _load_follower_quest_tables()
    normal_ids = sorted(qid for qid, r in quests_def.items() if int(r.get('29', 1) or 1) == 1)
    inf_ids = sorted(qid for qid, r in quests_def.items() if int(r.get('29', 1) or 1) == 2)

    if normal_ids and cur_id < max(normal_ids):
        for qid in normal_ids:
            if qid > cur_id:
                return qid, 0

    # All normal quests (1..42) completed -> pick an eligible infinite quest (902..942)
    follower_lvls = {}
    if user:
        for f in user.get('user_follower', []):
            if isinstance(f, dict):
                fid = int(f.get('i_id', 0) or 0)
                flvl = int(f.get('i_Level', 1) or 1)
                follower_lvls[fid] = max(follower_lvls.get(fid, 0), flvl)

    eligible = []
    for qid in inf_ids:
        row = quests_def.get(qid, {})
        req_fid = int(row.get('2', 1) or 1)
        req_lvl = int(row.get('3', 1) or 1)
        if follower_lvls.get(req_fid, 0) >= req_lvl:
            eligible.append(qid)

    if not eligible:
        eligible = inf_ids or [902]

    # Rotate to the next eligible infinite quest after cur_id
    for qid in eligible:
        if qid > cur_id:
            return qid, 1
    return eligible[0], 1


def _apply_ad_quest_autocomplete(entry, quests_def=None):
    """Auto-complete ONLY sub-missions whose condition type is 'ADViewCount' (Watch Ads).

    Since Buff ID 4 (Guitar Girl Premium) disables all ads globally, 'ADViewCount' sub-missions
    cannot be incremented by watching ads and are made immediately claimable.
    All other sub-missions (TapCount, SkillUseCount, GetADChocoCount, GetADLikeCount, etc.)
    remain normal so players complete them through gameplay.
    """
    if not isinstance(entry, dict):
        return entry
    if quests_def is None:
        quests_def, _ = _load_follower_quest_tables()
    cur_id = int(entry.get('i_CurrentID', 1) or 1)
    qrow = quests_def.get(cur_id, {})
    if not qrow:
        return entry
    for k, (type_col, val_col) in ((1, ('4', '5')), (2, ('7', '8')), (3, ('10', '11'))):
        ctype = str(qrow.get(type_col, '') or '')
        if ctype == 'ADViewCount':
            target = float(qrow.get(val_col, 1.0) or 1.0)
            vkey = f'd_ConditionValue{k}'
            entry[vkey] = max(float(entry.get(vkey, 0.0) or 0.0), target)
    return entry


def _normalise_user_follower_quest(user):
    """Ensure user['user_follower_quest'] is a single-element list with i_id=1.

    In libil2cpp.so (UserFollowerQuestTable.GetFollowerQuest at 0x1D422D4,
    UpdateFollowerQuest at 0x1E2B858, OnRecv(setUserFollowerQuest) at 0x1F0A924),
    the client always looks up dictionary key i_id == 1.
    """
    if not user:
        return []
    quests_def, _ = _load_follower_quest_tables()
    raw_list = user.get('user_follower_quest')
    if not isinstance(raw_list, list):
        raw_list = []

    valid_dicts = [q for q in raw_list if isinstance(q, dict)]
    if not valid_dicts:
        entry = {
            'i_id': 1,
            'i_CurrentID': 1,
            'i_CompleteID': 0,
            'd_ConditionValue1': 0.0,
            'd_ConditionValue2': 0.0,
            'd_ConditionValue3': 0.0,
            'i_RewardReceived1': 0,
            'i_RewardReceived2': 0,
            'i_RewardReceived3': 0,
            'i_isInfinity': 0,
        }
        _apply_ad_quest_autocomplete(entry, quests_def)
        user['user_follower_quest'] = [entry]
        return user['user_follower_quest']

    cur_id = max((int(q.get('i_CurrentID', 1) or 1) for q in valid_dicts), default=1)
    comp_id = max((int(q.get('i_CompleteID', 0) or 0) for q in valid_dicts), default=0)
    matching = [q for q in valid_dicts if int(q.get('i_CurrentID', 1) or 1) == cur_id] or valid_dicts

    c1 = max((float(q.get('d_ConditionValue1', 0.0) or 0.0) for q in matching), default=0.0)
    c2 = max((float(q.get('d_ConditionValue2', 0.0) or 0.0) for q in matching), default=0.0)
    c3 = max((float(q.get('d_ConditionValue3', 0.0) or 0.0) for q in matching), default=0.0)
    r1 = 1 if any(int(q.get('i_RewardReceived1', 0) or 0) == 1 for q in matching) else 0
    r2 = 1 if any(int(q.get('i_RewardReceived2', 0) or 0) == 1 for q in matching) else 0
    r3 = 1 if any(int(q.get('i_RewardReceived3', 0) or 0) == 1 for q in matching) else 0

    if r1 == 1 and r2 == 1 and r3 == 1:
        comp_id = max(comp_id, cur_id)
        cur_id, is_inf = _pick_next_follower_quest_id(user, cur_id, quests_def)
        c1 = c2 = c3 = 0.0
        r1 = r2 = r3 = 0
    else:
        is_inf = 1 if cur_id >= 900 else 0

    entry = {
        'i_id': 1,
        'i_CurrentID': int(cur_id),
        'i_CompleteID': int(comp_id),
        'd_ConditionValue1': float(c1),
        'd_ConditionValue2': float(c2),
        'd_ConditionValue3': float(c3),
        'i_RewardReceived1': int(r1),
        'i_RewardReceived2': int(r2),
        'i_RewardReceived3': int(r3),
        'i_isInfinity': int(is_inf),
    }
    _apply_ad_quest_autocomplete(entry, quests_def)
    user['user_follower_quest'] = [entry]
    return user['user_follower_quest']


def _merge_user_follower_quest(user, client_quests):
    """Safely merge saveUserFollowerQuest from userSave without losing i_id=1 or i_RewardReceived1..3.

    saveUserFollowerQuest only contains (i_CurrentID, d_ConditionValue1, d_ConditionValue2, d_ConditionValue3).
    Overwriting user['user_follower_quest'] directly would strip i_id=1 and i_RewardReceived1..3.
    """
    quests = _normalise_user_follower_quest(user)
    if not quests or not isinstance(client_quests, list):
        return quests
    entry = quests[0]
    cur_id = int(entry.get('i_CurrentID', 1) or 1)
    for cq in client_quests:
        if isinstance(cq, dict) and int(cq.get('i_CurrentID', 0) or 0) == cur_id:
            entry['d_ConditionValue1'] = max(
                float(entry.get('d_ConditionValue1', 0.0) or 0.0),
                float(cq.get('d_ConditionValue1', 0.0) or 0.0),
            )
            entry['d_ConditionValue2'] = max(
                float(entry.get('d_ConditionValue2', 0.0) or 0.0),
                float(cq.get('d_ConditionValue2', 0.0) or 0.0),
            )
            entry['d_ConditionValue3'] = max(
                float(entry.get('d_ConditionValue3', 0.0) or 0.0),
                float(cq.get('d_ConditionValue3', 0.0) or 0.0),
            )
    _apply_ad_quest_autocomplete(entry)
    return quests


@cmd('setFollowerQuestInfinite')
def h_set_follower_quest_infinite(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    u_seq = user.get('userdata', {}).get('u_seq', 100001) if user else 100001

    if user:
        quests = _normalise_user_follower_quest(user)
        quest = quests[0]
        cur_id = int(quest.get('i_CurrentID', 1) or 1)
        if cur_id >= 42:
            next_id, _ = _pick_next_follower_quest_id(user, max(cur_id, 42))
            quest['i_id'] = 1
            quest['i_CurrentID'] = next_id
            quest['d_ConditionValue1'] = 0.0
            quest['d_ConditionValue2'] = 0.0
            quest['d_ConditionValue3'] = 0.0
            quest['i_RewardReceived1'] = 0
            quest['i_RewardReceived2'] = 0
            quest['i_RewardReceived3'] = 0
            quest['i_isInfinity'] = 1
            _apply_ad_quest_autocomplete(quest)
            state.save_user(user)
    else:
        quest = {
            'i_id': 1,
            'i_CurrentID': 902,
            'i_CompleteID': 42,
            'd_ConditionValue1': 0.0,
            'd_ConditionValue2': 0.0,
            'd_ConditionValue3': 0.0,
            'i_RewardReceived1': 0,
            'i_RewardReceived2': 0,
            'i_RewardReceived3': 0,
            'i_isInfinity': 1,
        }
        _apply_ad_quest_autocomplete(quest)

    return {
        'u_seq': u_seq,
        'user_follower_quest': quest,
    }, OK


def _grant_follower_quest_reward(user, rtype, rid, rval):
    if not user:
        return
    ud = user.setdefault('userdata', {})
    uuid = user.get('uuid')
    if rtype == 1:  # Consume / Currencies (Table 1)
        cp = 0
        candy = 0.0
        like = 0.0
        fans = 0
        if rid == 1:  # Chocolate / CP
            cp = int(rval)
            ud['u_cp'] = int(ud.get('u_cp', 0) or 0) + cp
        elif rid == 2:  # Candy
            candy = float(rval)
            ud['u_candy'] = float(ud.get('u_candy', 0.0) or 0.0) + candy
        elif rid in (3, 4):  # Likes
            like = float(rval)
            ud['u_like'] = float(ud.get('u_like', 0.0) or 0.0) + like
        elif rid == 8:  # Fans
            fans = int(rval)
            ud['u_fans'] = int(ud.get('u_fans', 0) or 0) + fans
        elif rid == 11:  # Cookie / AP
            state.add_ap(user, int(rval))
        if uuid and (cp or candy or like or fans):
            state.increment_currency(uuid, cp=cp, candy=candy, like=like, fans=fans)
    elif rtype == 6:  # Buff (Table 6, e.g. rid=2 Fever/AutoTap buff for rval seconds)
        now_ts = int(time.time())
        buffs = user.setdefault('user_buff', [])
        b_entry = next((b for b in buffs if int(b.get('i_id', 0) or 0) == int(rid)), None)
        dur = int(rval)
        if b_entry:
            cur_end = int(b_entry.get('i_EndTime', b_entry.get('i_ExpiredTime', 0)) or 0)
            b_entry['i_Level'] = max(1, int(b_entry.get('i_Level', 1) or 1))
            b_entry['i_ActiveTime'] = now_ts
            b_entry['i_EndTime'] = max(now_ts, cur_end) + dur
            b_entry.pop('i_BuffTime', None)
            b_entry.pop('i_ExpiredTime', None)
        else:
            buffs.append({
                'i_id': int(rid),
                'i_Level': 1,
                'i_ActiveTime': now_ts,
                'i_EndTime': now_ts + dur,
            })
    elif rtype == 10:  # Ticket
        tickets = user.setdefault('user_ticketcollection', [])
        if not any(int(t.get('i_id', 0) or 0) == int(rid) for t in tickets):
            tickets.append({'i_id': int(rid)})


@cmd('setUserFollowerQuest')
def h_set_user_follower_quest(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    cur_id = int(p.get('i_CurrentID') or p.get('CurrentID') or p.get('current_id', 0) or 1)
    sub_id = int(p.get('i_SubID') or p.get('SubID') or p.get('sub_id', 1) or 1)
    cond_val = float(p.get('d_ConditionValue') or p.get('ConditionValue') or p.get('condition_value', 0.0) or 0.0)

    quests_def, rewards_def = _load_follower_quest_tables()
    quest_row = quests_def.get(cur_id, {})

    # Determine reward group from Table 26
    rg_key = '13' if sub_id == 1 else ('14' if sub_id == 2 else '15')
    rg_id = int(quest_row.get(rg_key, 0) or 0)

    reward_data = []
    already_claimed = False
    if user:
        quests = _normalise_user_follower_quest(user)
        found_quest = quests[0]
        # Sync cur_id if client is on cur_id
        if int(found_quest.get('i_CurrentID', 1) or 1) != cur_id and cur_id in quests_def:
            found_quest['i_CurrentID'] = cur_id
            found_quest['i_isInfinity'] = 1 if cur_id >= 900 else 0
        rec_key = f'i_RewardReceived{sub_id}'
        if int(found_quest.get(rec_key, 0) or 0) == 1:
            already_claimed = True

    if rg_id and rg_id in rewards_def and not already_claimed:
        for r in rewards_def[rg_id]:
            rtype = int(r.get('3', 0) or 0)
            rid = int(r.get('4', 0) or 0)
            rval = float(r.get('5', 0) or 0)
            if user:
                _grant_follower_quest_reward(user, rtype, rid, rval)
            reward_data.append({
                'reward_type': rtype,
                'reward_id': rid,
                'reward_value': rval,
            })

    if user:
        quests = _normalise_user_follower_quest(user)
        found_quest = quests[0]
        found_quest['i_id'] = 1

        if sub_id == 1:
            found_quest['d_ConditionValue1'] = max(float(found_quest.get('d_ConditionValue1', 0.0) or 0.0), cond_val)
            found_quest['i_RewardReceived1'] = 1
        elif sub_id == 2:
            found_quest['d_ConditionValue2'] = max(float(found_quest.get('d_ConditionValue2', 0.0) or 0.0), cond_val)
            found_quest['i_RewardReceived2'] = 1
        elif sub_id == 3:
            found_quest['d_ConditionValue3'] = max(float(found_quest.get('d_ConditionValue3', 0.0) or 0.0), cond_val)
            found_quest['i_RewardReceived3'] = 1

        r1 = int(found_quest.get('i_RewardReceived1', 0) or 0)
        r2 = int(found_quest.get('i_RewardReceived2', 0) or 0)
        r3 = int(found_quest.get('i_RewardReceived3', 0) or 0)

        if r1 == 1 and r2 == 1 and r3 == 1:
            # All 3 sub-missions completed!
            # In libil2cpp.so (OnRecv at 0x1F0A830 & callback at 0x1E2E598):
            # When next_flg == 1, the client reads the new i_CurrentID and i_CompleteID
            # from the response, resets condition values & reward flags to 0, and loads the next quest.
            comp_id = max(int(found_quest.get('i_CompleteID', 0) or 0), cur_id)
            next_cur_id, is_inf = _pick_next_follower_quest_id(user, cur_id, quests_def)
            found_quest['i_id'] = 1
            found_quest['i_CurrentID'] = int(next_cur_id)
            found_quest['i_CompleteID'] = int(comp_id)
            found_quest['d_ConditionValue1'] = 0.0
            found_quest['d_ConditionValue2'] = 0.0
            found_quest['d_ConditionValue3'] = 0.0
            found_quest['i_RewardReceived1'] = 0
            found_quest['i_RewardReceived2'] = 0
            found_quest['i_RewardReceived3'] = 0
            found_quest['i_isInfinity'] = int(is_inf)
            _apply_ad_quest_autocomplete(found_quest, quests_def)
            r1 = r2 = r3 = 0
            next_flg = 1
        else:
            _apply_ad_quest_autocomplete(found_quest, quests_def)
            next_flg = 0

        state.save_user(user)
        return {
            'i_CurrentID': int(found_quest.get('i_CurrentID', cur_id) or cur_id),
            'i_CompleteID': int(found_quest.get('i_CompleteID', 0) or 0),
            'd_ConditionValue1': float(found_quest.get('d_ConditionValue1', 0.0) or 0.0),
            'd_ConditionValue2': float(found_quest.get('d_ConditionValue2', 0.0) or 0.0),
            'd_ConditionValue3': float(found_quest.get('d_ConditionValue3', 0.0) or 0.0),
            'i_RewardReceived1': r1,
            'i_RewardReceived2': r2,
            'i_RewardReceived3': r3,
            'next_flg': next_flg,
            'reward_data': reward_data,
        }, OK

    return {
        'i_CurrentID': cur_id,
        'i_CompleteID': 0,
        'd_ConditionValue1': cond_val if sub_id == 1 else 0.0,
        'd_ConditionValue2': cond_val if sub_id == 2 else 0.0,
        'd_ConditionValue3': cond_val if sub_id == 3 else 0.0,
        'i_RewardReceived1': 1 if sub_id == 1 else 0,
        'i_RewardReceived2': 1 if sub_id == 2 else 0,
        'i_RewardReceived3': 1 if sub_id == 3 else 0,
        'next_flg': 0,
        'reward_data': reward_data,
    }, OK

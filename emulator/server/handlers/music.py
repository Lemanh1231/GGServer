import json
import os
from server import state
from server.handlers.registry import cmd, OK, _payload

_GAME_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'gamedata', 'game_data.json')

def _load_encore_tables():
    """Load Table 11 (Music Encore Level Data) and Table 31 (Follower Profile Level Data)."""
    try:
        with open(_GAME_DATA_PATH, encoding='utf-8') as f:
            gd = json.load(f)
        # Table 11: key = level (int), value = row dict
        # Col 6 = _i_EncoreBonusGiftAmount (Candy base: 10)
        # Col 7 = _i_EncoreFollowerProfileExp (Follower EXP gain: 50)
        t11 = {int(r['1']): r for r in gd.get('11', [])}
        
        # Table 31: key = profile_id, value = {level: row dict}
        # Col 2 = profile_id, Col 3 = level, Col 4 = d_RequireEXP, Col 7 = i_AddCandy
        t31 = {}
        for r in gd.get('31', []):
            t31.setdefault(int(r['2']), {})[int(r['3'])] = r
        return t11, t31
    except Exception:
        return {}, {}

def _apply_follower_profile_exp(profile, t31_profile_rows, exp_gain):
    """Add encore EXP and update profile level and i_AddCandy based on Table 31."""
    from server.handlers.follower import _apply_profile_exp
    _apply_profile_exp(profile, t31_profile_rows, exp_gain)

@cmd('playMusic')
def h_play_music(req, player, ctx):
    p = _payload(req)
    idx = p.get('music_idx', 1)
    
    # Just return a success code for playing music
    return {
        'code': 0,
        'album_idx': 1,
        'music_idx': idx,
        'score1': 1000,
        'score2': 1000,
        'score3': 1000,
        'grade1': 1,
        'grade2': 1,
        'grade3': 1,
        'u_cp': 0,
        'u_candy': 0.0,
        'u_like': 0.0,
        'u_fans': 0
    }, OK

@cmd('musicPointReview')
def h_music_point_review(req, player, ctx):
    p = _payload(req)
    review_points = p.get('review_point') or []
    return review_points, OK

@cmd('getMusicReward')
def h_get_music_reward(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    
    i_ids = p.get('i_ids') or []
    i_levels = p.get('i_levels') or []
    
    # Client checks total_reward_value >= 1, reward_music_id.Count >= 1,
    # reward_value.Count >= 1, and user_follower_profile.Count > 0.
    # If any check fails, the encore bonus popup is silently dismissed without granting rewards.
    claimed_ids = [int(mid) for mid in i_ids if int(mid) > 0]
    if not claimed_ids:
        claimed_ids = [1]

    t11, t31 = _load_encore_tables()
    
    claimed_base_candy = []
    total_granted_candy = 0
    follower_exp_gains = {}  # follower_id -> total exp gain

    user_music_map = {}
    if user:
        user_music_map = {int(um.get('i_id', 0)): um for um in user.get('user_music', [])}

    for idx, mid in enumerate(claimed_ids):
        # Look up song level (from request or user_music, default 1)
        song_lvl = 1
        if idx < len(i_levels) and int(i_levels[idx]) > 0:
            song_lvl = int(i_levels[idx])
        elif mid in user_music_map:
            song_lvl = int(user_music_map[mid].get('i_Level', 1) or 1)

        t11_row = t11.get(song_lvl, t11.get(1, {}))
        # Col 6 = _i_EncoreBonusGiftAmount (10 Candy)
        base_candy = int(t11_row.get('6', 10) or 10)
        # Col 7 = _i_EncoreFollowerProfileExp (50 EXP)
        follower_exp = int(t11_row.get('7', 50) or 50)

        claimed_base_candy.append(base_candy)

        # Determine follower for this music encore
        follower_id = 1
        if mid in user_music_map:
            fid = int(user_music_map[mid].get('i_EncoreBonusFollowerId', 0) or 0)
            if fid > 0:
                follower_id = fid
        
        # Add follower EXP
        follower_exp_gains[follower_id] = follower_exp_gains.get(follower_id, 0) + follower_exp

        # Check follower bonus candy
        bonus_candy = 0
        if user:
            for fp in user.get('user_follower_profile', []):
                if int(fp.get('i_id', 0)) == follower_id:
                    bonus_candy = max(0, int(fp.get('i_AddCandy', 0) or 0))
                    break

        total_granted_candy += (base_candy + bonus_candy)

    total_base_candy = sum(claimed_base_candy)

    follower_profiles = []
    if user:
        # Award Candy (Encore gifts are Candy, NOT CP)
        state.increment_currency(uuid, candy=float(total_granted_candy))
        user.setdefault('userdata', {})['u_candy'] = user['userdata'].get('u_candy', 0.0) + float(total_granted_candy)
        
        # Reset encore bonus appear state in user_music
        for mid in claimed_ids:
            if mid in user_music_map:
                user_music_map[mid]['b_EncoreBonusAppear'] = 0
                user_music_map[mid]['i_EncoreBonusFollowerId'] = 0

        # Award Star Pass points (10 per song)
        evp_list = user.setdefault('user_event_point', [
            {'s_EventType': 'Pass', 'i_DataID': 13, 'i_Point': 0, 'i_Step': 0, 'i_ADViewTime': 0, 'i_Version': 13}
        ])
        for ep in evp_list:
            if ep.get('s_EventType') == 'Pass':
                ep['i_Point'] = ep.get('i_Point', 0) + 10 * len(claimed_ids)
                from server.handlers.reward import _get_step_for_points
                sub_id = int(ep.get('i_DataID', 13) or 13)
                ep['i_Step'] = _get_step_for_points(sub_id, ep['i_Point'])
                break

        # Apply follower EXP and update profile levels
        follower_profiles = user.setdefault('user_follower_profile', [])
        profile_map = {int(fp.get('i_id', 0)): fp for fp in follower_profiles}
        for fid, exp in follower_exp_gains.items():
            if fid not in profile_map:
                new_fp = {'i_id': fid, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0}
                follower_profiles.append(new_fp)
                profile_map[fid] = new_fp
            _apply_follower_profile_exp(profile_map[fid], t31.get(fid, {}), exp)

        from server.handlers.follower import _sync_follower_profiles
        _sync_follower_profiles(user)

        if not follower_profiles:
            follower_profiles = [{'i_id': 1, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0}]
            user['user_follower_profile'] = follower_profiles
            
        state.save_user(user)
    else:
        follower_profiles = [{'i_id': 1, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0}]

    return {
        'total_reward_value': total_base_candy,
        'reward_music_id': claimed_ids,
        'reward_value': claimed_base_candy,
        'user_follower_profile': follower_profiles,
        'error_data': {},
    }, OK

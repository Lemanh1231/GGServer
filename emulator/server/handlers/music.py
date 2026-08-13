from server import state
from server.handlers.registry import cmd, OK, _payload

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
    # the client sends review points
    return {'status': 'Y'}, OK

@cmd('getMusicReward')
def h_get_music_reward(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    
    i_ids = p.get('i_ids') or []
    i_levels = p.get('i_levels') or []
    # The reward is a one-time prize for reaching the submitted music level.
    # A client can retry this request, so its (music id, level) pair must be
    # idempotent rather than granting another reward on each retry.
    requested = list(zip(i_ids, i_levels))
    claimed_ids = []
    claimed_values = []
    if user:
        claimed = user.setdefault('claimed_music_rewards', {})
        for music_id, level in requested:
            music_id = int(music_id)
            level = int(level)
            if music_id <= 0 or level <= 0:
                continue
            claim_key = f'{music_id}:{level}'
            if claim_key in claimed:
                continue
            claimed[claim_key] = True
            claimed_ids.append(music_id)
            claimed_values.append(500)

        cp = sum(claimed_values)
        if cp:
            state.increment_currency(uuid, cp=cp)
            user['userdata']['u_cp'] = user['userdata'].get('u_cp', 0) + cp
            # Award Star Pass points only for newly claimed music rewards.
            evp_list = user.setdefault('user_event_point', [
                {'s_EventType': 'Pass', 'i_DataID': 5, 'i_Point': 0, 'i_Step': 0, 'i_ADViewTime': 0, 'i_Version': 5}
            ])
            for ep in evp_list:
                if ep.get('s_EventType') == 'Pass':
                    ep['i_Point'] = ep.get('i_Point', 0) + 10 * len(claimed_ids)
                    break
        state.save_user(user)
    else:
        cp = 0
        
    return {
        'total_reward_value': cp,
        'reward_music_id': claimed_ids,
        'reward_value': claimed_values,
        'user_follower_profile': [],
        'error_data': {},
    }, OK

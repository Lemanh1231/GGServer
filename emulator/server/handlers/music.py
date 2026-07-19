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
    
    # Give a small reward for playing music
    cp = 500 * len(i_ids) if i_ids else 500
    if user:
        state.increment_currency(uuid, cp=cp)
        user['userdata']['u_cp'] = user['userdata'].get('u_cp', 0) + cp
        # Award Star Pass points (10 per music played)
        pts_earned = 10 * max(len(i_ids), 1)
        evp_list = user.setdefault('user_event_point', [
            {'s_EventType': 'Pass', 'i_DataID': 5, 'i_Point': 0, 'i_Step': 0, 'i_ADViewTime': 0, 'i_Version': 5}
        ])
        for ep in evp_list:
            if ep.get('s_EventType') == 'Pass':
                ep['i_Point'] = ep.get('i_Point', 0) + pts_earned
                break
        state.save_user(user)
        
    return {
        'total_reward_value': cp,
        'reward_music_id': i_ids,
        'reward_value': [500] * len(i_ids),
        'user_follower_profile': []
    }, OK

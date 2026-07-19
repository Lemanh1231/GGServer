from server import state
from server.handlers.registry import cmd, OK, _payload

@cmd('setFollowerProfileGift')
def h_set_follower_profile_gift(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    
    pid = p.get('profile_id', 1)
    
    if user:
        lst = user.setdefault('user_follower_giftitem', [])
        found = False
        for g in lst:
            if g.get('i_id') == pid:
                g['i_Value'] = g.get('i_Value', 0) + p.get('use_gitf_value', 1)
                found = True
        if not found:
            lst.append({'i_id': pid, 'i_Value': p.get('use_gitf_value', 1)})
        state.save_user(user)
        
    return {'profile_id': pid, 'gift_id': p.get('gift_id', 1), 'status': 'Y'}, OK

@cmd('setFollowerQuestInfinite')
def h_set_follower_quest_infinite(req, player, ctx):
    p = _payload(req)
    return {'status': 'Y'}, OK

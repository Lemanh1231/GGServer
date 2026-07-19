from server import state
from server.handlers.registry import cmd, OK, _payload

@cmd('updateNickName')
def h_update_nickname(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    nickname = p.get('nickname', 'Guitarist')
    if user:
        user['userdata']['u_nick'] = nickname
        state.save_user(user)
    return {'nickname': nickname}, OK

@cmd('updateAvatar')
def h_update_avatar(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    # The client might send 'u_avatar' or just 'avatar' depending on serialization
    avatar = p.get('u_avatar') or p.get('avatar', 1)
    if user:
        user['userdata']['u_avatar'] = avatar
        state.save_user(user)
    return {'u_avatar': avatar}, OK

@cmd('updateUserTitle')
def h_update_user_title(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    title = p.get('u_title') or p.get('title', 1)
    if user:
        user['userdata']['u_title'] = title
        state.save_user(user)
    return {'u_title': title}, OK

@cmd('getProfile')
def h_get_profile(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    ud = user['userdata'] if user else {}
    return {
        'u_avatar': ud.get('u_avatar', 1),
        'u_id': ud.get('u_id', ''),
        'u_nick': ud.get('u_nick', 'Guitarist'),
        'u_country': ud.get('u_country', 'KR'),
        'u_title': ud.get('u_title', 1),
        'allper': 0, 'allcom': 0, 'gold': 0, 'silver': 0, 'bronze': 0,
        'single_cnt': 0, 'multi_cnt': 0, 'master_cnt': 0,
        'single_score': 0, 'multi_score': 0
    }, OK

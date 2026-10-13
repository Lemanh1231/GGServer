"""eventMode.* handlers (SamSeck milestone event).

SamSeck = the 3 milestones in getGameDataList.samseckevent (i_id 1..3), each an
independent condition (Reach Lv.200 / Own 3 Songs / Unlock a Mate).
Table 24 maps milestones to reward IDs 100001, 100002, 100003:
- 1: Guitar 10 (Calico Cat Scratcher / 삼색이 스크래쳐)
- 2: Costume 13 (Calico Cat Overalls / 삼색이 멜빵 바지)
- 3: Unit 1 (Calico Cat Navi / 삼색이)
"""
from server import state, event_manager
from server.handlers.registry import cmd, OK, _payload


@cmd('getSamSeckList')
def h_get_samseck_list(req, player, ctx):
    # getSamSeckListRetDataInfo: { event_type: STRING, rewardList: LIST<rewardListData> }.
    # The client binds each slot by its milestone i_id (1..3) matching getGameDataList.samseckevent.
    if not event_manager.is_meowfest_enabled():
        return {'event_type': '', 'rewardList': []}, OK
    return {
        'event_type': '',
        'rewardList': [
            {'i_id': 1, 'i_RewardType': 9, 'i_RewardId': 10, 'd_RewardQuantity': 1.0},
            {'i_id': 2, 'i_RewardType': 3, 'i_RewardId': 13, 'd_RewardQuantity': 1.0},
            {'i_id': 3, 'i_RewardType': 7, 'i_RewardId': 1, 'd_RewardQuantity': 1.0},
        ],
    }, OK


@cmd('getSamSeckReward')
def h_get_samseck_reward(req, player, ctx):
    # Claim milestone i_id. Claimed milestones are tracked in the single I16 user field
    # u_samseck_step as a BITMASK (bit i_id-1) -- the slots are claimed independently.
    if not event_manager.is_meowfest_enabled():
        return {'step': 0}, {'code': 1, 'errmsg': 'Meowfest event is closed'}
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    i_id = int(p.get('i_id', 0) or 0)
    bit = (1 << (i_id - 1)) if 1 <= i_id <= 15 else 0
    user = state.get_user(uuid) if uuid else None
    if not user:
        return {'step': bit}, OK
    ud = user['userdata']
    step = (int(ud.get('u_samseck_step', 0) or 0) | bit) & 0x7FFF
    ud['u_samseck_step'] = step

    # Grant milestone rewards directly to player inventory
    if i_id == 1:
        # Step 1: Guitar 10 (Calico Cat Scratcher / 삼색이 스크래쳐)
        guitars = user.setdefault('user_guitar', [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}])
        if not any(int(g.get('i_id', 0) or 0) == 10 for g in guitars):
            guitars.append({'i_id': 10, 'i_Level': 1, 'i_BonusLevel': 0})
    elif i_id == 2:
        # Step 2: Costume 13 (Calico Cat Overalls / 삼색이 멜빵 바지)
        costumes = user.setdefault('costumes', [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0}])
        if not any(int(c.get('i_id', 0) or 0) == 13 for c in costumes):
            costumes.append({'i_id': 13, 'i_Level': 1, 'i_BonusLevel': 0})
    elif i_id == 3:
        # Step 3: Unit 1 (Calico Cat Navi / 삼색이)
        units = user.setdefault('user_unit', [])
        unit1 = next((u for u in units if int(u.get('i_id', 0) or 0) == 1), None)
        if not unit1:
            units.append({'i_id': 1, 'i_Level': 1})
        else:
            unit1['i_Level'] = int(unit1.get('i_Level', 1) or 1) + 1

    state.save_user(user)
    return {'step': step}, OK


@cmd('getEventMain')
def h_get_event_main(req, player, ctx):
    if not event_manager.is_event_ranking_enabled():
        return {}, {'code': 1, 'errmsg': 'Event ranking is inactive'}
    import time
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid) if uuid else None
    my_score = 0
    if user:
        ud = user.get('userdata', {})
        my_score = int(ud.get('u_event_point', 0) or ud.get('u_fans', 1000) or 1000)
    now_t = int(time.time())
    return {
        'idx': 1,
        'title': 'Guitar Girl Live Festival',
        'img1': '',
        'img2': '',
        'movie': '',
        'utc': 9,
        'banner': '',
        'desc_cn': '吉他少女现场庆典活动',
        'desc_en': 'Guitar Girl Live Festival Event',
        'desc_jp': 'ギターガールライブフェスティバル',
        'server_time': now_t,
        'start_time': 1600000000,
        'end_time': 4102444800,
        'my_score': my_score,
        'my_rank': 1,
    }, OK


@cmd('getEventRank')
def h_get_event_rank(req, player, ctx):
    if not event_manager.is_event_ranking_enabled():
        return [], {'code': 1, 'errmsg': 'Event ranking is inactive'}
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid) if uuid else None
    my_nick = 'Kotori'
    my_score = 1000
    if user:
        ud = user.get('userdata', {})
        my_nick = ud.get('u_nick', 'Kotori') or 'Kotori'
        my_score = int(ud.get('u_event_point', 0) or ud.get('u_fans', 1000) or 1000)
    ranks = [
        {'u_seq': 1, 'u_nick': my_nick, 'u_id': uuid or 'user1', 'u_avatar': 1, 'u_country': 'VN', 'u_title': 1, 'rank': 1, 'score': my_score},
        {'u_seq': 2, 'u_nick': 'Mimi', 'u_id': 'bot_2', 'u_avatar': 2, 'u_country': 'KR', 'u_title': 1, 'rank': 2, 'score': max(100, int(my_score * 0.9))},
        {'u_seq': 3, 'u_nick': 'Aoi', 'u_id': 'bot_3', 'u_avatar': 3, 'u_country': 'JP', 'u_title': 1, 'rank': 3, 'score': max(50, int(my_score * 0.8))},
        {'u_seq': 4, 'u_nick': 'Yuna', 'u_id': 'bot_4', 'u_avatar': 4, 'u_country': 'US', 'u_title': 1, 'rank': 4, 'score': max(30, int(my_score * 0.7))},
        {'u_seq': 5, 'u_nick': 'Hana', 'u_id': 'bot_5', 'u_avatar': 5, 'u_country': 'TW', 'u_title': 1, 'rank': 5, 'score': max(10, int(my_score * 0.6))},
    ]
    return ranks, OK


@cmd('eventRewardList')
def h_event_reward_list(req, player, ctx):
    if not event_manager.is_event_ranking_enabled():
        return {}, {'code': 1, 'errmsg': 'Event ranking is inactive'}
    return {
        'event_idx': 1,
        'reward_list': [
            {'gain_point': 100, 'reward_type': 1, 'reward_value': 500},
            {'gain_point': 500, 'reward_type': 1, 'reward_value': 1000},
            {'gain_point': 1000, 'reward_type': 1, 'reward_value': 2000},
        ],
        'rank_reward_list': [
            {'title': 'Top 1-10', 'desc_cn': '第1-10名奖励', 'desc_en': 'Rank 1-10 Reward', 'desc_jp': '1-10位報酬', 'reward_type': 1, 'reward_value': 5000},
            {'title': 'Top 11-50', 'desc_cn': '第11-50名奖励', 'desc_en': 'Rank 11-50 Reward', 'desc_jp': '11-50位報酬', 'reward_type': 1, 'reward_value': 2500},
            {'title': 'Top 51-100', 'desc_cn': '第51-100名奖励', 'desc_en': 'Rank 51-100 Reward', 'desc_jp': '51-100位報酬', 'reward_type': 1, 'reward_value': 1000},
        ],
    }, OK


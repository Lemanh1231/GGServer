"""eventMode.* handlers (SamSeck milestone event).

SamSeck = the 3 milestones in getGameDataList.samseckevent (i_id 1..3), each an
independent condition (Reach Lv.200 / Own 3 Songs / Unlock a Mate).
Table 24 maps milestones to reward IDs 100001, 100002, 100003:
- 1: Guitar 10 (Calico Cat Scratcher / 삼색이 스크래쳐)
- 2: Costume 13 (Calico Cat Overalls / 삼색이 멜빵 바지)
- 3: Unit 1 (Calico Cat Navi / 삼색이)
"""
from server import state
from server.handlers.registry import cmd, OK, _payload


@cmd('getSamSeckList')
def h_get_samseck_list(req, player, ctx):
    # getSamSeckListRetDataInfo: { event_type: STRING, rewardList: LIST<rewardListData> }.
    # The client binds each slot by its rewardList entry (i_id 100001..100003).
    return {
        'event_type': '',
        'rewardList': [
            {'i_id': 100001, 'i_RewardType': 5, 'i_RewardId': 10, 'd_RewardQuantity': 1.0},
            {'i_id': 100002, 'i_RewardType': 4, 'i_RewardId': 13, 'd_RewardQuantity': 1.0},
            {'i_id': 100003, 'i_RewardType': 8, 'i_RewardId': 1, 'd_RewardQuantity': 1.0},
        ],
    }, OK


@cmd('getSamSeckReward')
def h_get_samseck_reward(req, player, ctx):
    # Claim milestone i_id. Claimed milestones are tracked in the single I16 user field
    # u_samseck_step as a BITMASK (bit i_id-1) -- the slots are claimed independently.
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
        if not any(int(u.get('i_id', 0) or 0) == 1 for u in units):
            units.append({'i_id': 1, 'i_Level': 1})

    state.save_user(user)
    return {'step': step}, OK

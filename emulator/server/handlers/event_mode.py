"""eventMode.* handlers (SamSeck milestone event).

SamSeck = the 3 milestones in getGameDataList.samseckevent (i_id 1..3), each an
independent condition (Reach Lv.200 / Own 3 Songs / Unlock a Mate). The reference
server never implemented these calls, so there is no canonical response to copy.
"""
from server import state
from server.handlers.registry import cmd, OK, _payload


@cmd('getSamSeckList')
def h_get_samseck_list(req, player, ctx):
    # getSamSeckListRetDataInfo: { event_type: STRING, rewardList: LIST<rewardListData> }.
    # Return an explicit empty list (not the default {}): an absent rewardList deserialises to a
    # *null* List on the client and the event UI iterates it -> NullReferenceException. Claimed
    # state is carried by u_samseck_step (see below), not by this list, so [] is correct.
    return {'event_type': '', 'rewardList': []}, OK


@cmd('getSamSeckReward')
def h_get_samseck_reward(req, player, ctx):
    # Claim milestone i_id. Claimed milestones are tracked in the single I16 user field
    # u_samseck_step as a BITMASK (bit i_id-1) -- the slots are claimed independently, which a
    # count/highest-id can't represent. Must set the bit and return the new mask, else the claim
    # never registers and the client retries. We don't grant the mail reward (i_MailRewardID):
    # this emulator serves no mailbox and has no mail-reward table, so faking it would desync.
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    i_id = int(p.get('i_id', 0) or 0)
    bit = (1 << (i_id - 1)) if 1 <= i_id <= 15 else 0   # guard the shift; stay within I16
    user = state.get_user(uuid) if uuid else None
    if not user:
        return {'step': bit}, OK
    ud = user['userdata']
    step = (int(ud.get('u_samseck_step', 0) or 0) | bit) & 0x7FFF
    ud['u_samseck_step'] = step
    state.save_user(user)
    return {'step': step}, OK

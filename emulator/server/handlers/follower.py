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
        # Table 30 is the gift list shown in the follower UI: its column 3
        # is the heart/profile-EXP earned per gift.  Table 34 looks similar
        # but is a separate progression table (gift 1 = 50), which made a
        # 20-heart gingerbread jump five levels at a time.
        gifts = {int(row['1']): row for row in data.get('30', [])}
        levels = {}
        for row in data.get('27', []):
            levels.setdefault(int(row['2']), {})[int(row['3'])] = row
        return profiles, gifts, levels
    except (OSError, ValueError, TypeError, json.JSONDecodeError, KeyError):
        return {}, {}, {}

def _apply_profile_exp(profile, level_rows, exp_gain):
    """Apply gift EXP, carrying it through each configured profile level."""
    level = max(1, int(profile.get('i_Level', 1) or 1))
    exp = max(0, int(profile.get('d_Exp', 0) or 0)) + exp_gain
    while level in level_rows:
        required = int(level_rows[level].get('4', 0) or 0)
        if required <= 0 or exp < required:
            break
        exp -= required
        level += 1
    profile['i_Level'] = level
    profile['d_Exp'] = exp

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
    if profile_id == 100000:
        # 100000 is the player's common fan-profile track, not NPC profile 1.
        return max(1, int(user.get('userdata', {}).get('u_fans_grade', 1) or 1))
    profile = next((row for row in user.get('user_follower_profile', [])
                    if int(row.get('i_id', 0) or 0) == profile_id), None)
    return int(profile.get('i_Level', 0) or 0) if profile else 0

@cmd('setFollowerProfileGift')
def h_set_follower_profile_gift(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    
    try:
        profile_id = int(p.get('profile_id', 1))
        gift_id = int(p.get('gift_id', 1))
        use_count = int(p.get('use_gitf_value', 1))
    except (TypeError, ValueError):
        return {}, OK
    if not user or use_count <= 0:
        return {}, OK

    profiles, gifts, level_data = _follower_data()
    profile_def = profiles.get(profile_id)
    gift_def = gifts.get(gift_id)
    allowed_gifts = {
        int(value.strip()) for value in str((profile_def or {}).get('15', '')).split(',')
        if value.strip().isdigit()
    }
    if not profile_def or not gift_def or gift_id not in allowed_gifts:
        return {}, OK

    # Profiles and gifts used to be synthesized only in userLogin's response,
    # leaving a newly created SQLite profile with neither list.  Seed them on
    # first use as a backwards-compatible migration for those accounts.
    inventory = user.setdefault('user_follower_giftitem', [{'i_id': 1, 'i_Value': 141}])
    gift_item = next((item for item in inventory if item.get('i_id') == gift_id), None)
    profile = next((item for item in user.setdefault('user_follower_profile', [
                    {'i_id': 1, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0},
                ])
                    if item.get('i_id') == profile_id), None)
    if not gift_item or not profile or int(gift_item.get('i_Value', 0) or 0) < use_count:
        return {}, OK

    # i_Value is the owned quantity.  The old handler added to it and keyed it
    # by profile id, creating infinite gifts without giving follower EXP.
    gift_item['i_Value'] -= use_count
    exp_gain = int(gift_def.get('3', 0) or 0) * use_count
    _apply_profile_exp(profile, level_data.get(profile_id, {}), exp_gain)

    # The follower screen reads the owned follower level (`user_follower`)
    # after it has been opened again, while the gift response updates the
    # profile card.  Keeping only `user_follower_profile` in sync made the
    # card appear to level during the request but return to level 1 after a
    # reload/login.
    followers = user.setdefault('user_follower', [])
    follower = next((item for item in followers if item.get('i_id') == profile_id), None)
    if follower is None:
        follower = {'i_id': profile_id, 'i_Level': 1, 'i_BonusLevel': 0}
        followers.append(follower)
    follower['i_Level'] = int(profile['i_Level'])
    state.save_user(user)

    return {
        'i_gift_type': int(gift_def.get('2', 0) or 0),
        'user_follower_giftitem': gift_item,
        'user_follower_profile': profile,
    }, OK

@cmd('setUserFollowerProfileReward')
def h_set_user_follower_profile_reward(req, player, ctx):
    """Claim one follower-profile level reward exactly once."""
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    try:
        profile_id = int(p.get('i_id'))
        reward_level = int(p.get('s_level'))
    except (TypeError, ValueError):
        return {'status': 'N'}, OK
    if not user or reward_level < 1:
        return {'status': 'N'}, OK

    milestones, reward_defs = _profile_reward_data()
    milestone = milestones.get((profile_id, reward_level))
    claim = {'i_id': profile_id, 'i_RewardLevel': reward_level}
    claims = user.setdefault('user_follower_profile_reward', [])
    already_claimed = any(int(row.get('i_id', 0) or 0) == profile_id
                          and int(row.get('i_RewardLevel', 0) or 0) == reward_level
                          for row in claims)
    if not milestone or already_claimed or _profile_level_for_reward(user, profile_id) < reward_level:
        return {'status': 'N', 'user_follower_profile_reward': claim}, OK

    # Table 31 points to table 13, whose columns 3/4/5 are the same reward
    # type/id/value format used by the common reward helper.
    reward = reward_defs.get(int(milestone.get('5', -1) or -1))
    reward_type = reward_id = reward_value = 0
    if reward:
        reward_type = int(reward.get('3', 0) or 0)
        reward_id = int(reward.get('4', 0) or 0)
        reward_value = int(reward.get('5', 0) or 0)
        if reward_type and reward_value:
            # Local import avoids a module import cycle at handler startup.
            from server.handlers.reward import _give_reward
            _give_reward(user, {'reward_type': reward_type,
                                'reward_id': reward_id,
                                'reward_value': reward_value})

    # This list is the client's authoritative unlocked-information/claimed
    # state.  Persisting it makes the corresponding profile entry open after
    # the follower screen is reloaded and prevents the same prize being paid
    # again on retries.
    claims.append(claim)
    state.save_user(user)
    return {
        'status': 'Y',
        'user_follower_profile_reward': claim,
        'reward_type': reward_type,
        'reward_id': reward_id,
        'reward_value': reward_value,
    }, OK

@cmd('setFollowerQuestInfinite')
def h_set_follower_quest_infinite(req, player, ctx):
    p = _payload(req)
    return {'status': 'Y'}, OK

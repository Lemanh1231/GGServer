"""Chapter 3 story energy (Cookie / AP) handlers."""
import json
import os
import time

from server import state
from server.handlers.registry import cmd, OK, _payload

AP_MAX = 70
AP_USE = 5
AP_REGEN_SECONDS = 300
_GAME_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'gamedata', 'game_data.json')


def _stage_config(stage_id):
    """Read a Chapter 3 stage row from game data."""
    try:
        with open(_GAME_DATA_PATH, encoding='utf-8') as f:
            stages = json.load(f).get('33', [])
        return next((row for row in stages if int(row.get('1', 0)) == stage_id), None)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None


def _stage_rewards(stage):
    """Expand the stage's reward groups into its actual follower-gift drops."""
    if not stage:
        return []
    try:
        group_ids = [int(value.strip()) for value in str(stage.get('37', '')).split(',')
                     if value.strip().isdigit()]
        with open(_GAME_DATA_PATH, encoding='utf-8') as f:
            rows = json.load(f).get('36', [])
        rewards = []
        for group_id in group_ids:
            # Each group is a weighted/random reward list in the original
            # game.  The emulator deterministically selects its first item.
            row = next((row for row in rows if int(row.get('1', 0)) == group_id), None)
            if row:
                rewards.append({
                    'reward_type': int(row.get('2', 11) or 11),
                    'reward_id': int(row.get('3', 0) or 0),
                    'reward_value': int(row.get('4', 0) or 0),
                })
        return rewards
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return []


def _grant_gift_rewards(user, rewards):
    gifts = user.setdefault('user_follower_giftitem', [])
    by_id = {int(row.get('i_id', 0) or 0): row for row in gifts}
    for reward in rewards:
        # Chapter 3's table uses reward type 11 for follower gift items.
        if reward['reward_type'] != 11 or reward['reward_id'] <= 0:
            continue
        gift = by_id.get(reward['reward_id'])
        if gift is None:
            gift = {'i_id': reward['reward_id'], 'i_Value': 0}
            gifts.append(gift)
            by_id[reward['reward_id']] = gift
        gift['i_Value'] = int(gift.get('i_Value', 0) or 0) + reward['reward_value']


def _chapter_reward(chapter_id, reward_num):
    """Return (required stars, rewards) for one chapter-star chest."""
    try:
        with open(_GAME_DATA_PATH, encoding='utf-8') as f:
            rows = json.load(f)
        chapter = next((row for row in rows.get('35', [])
                        if int(row.get('1', 0)) == chapter_id), None)
        if not chapter or reward_num not in (1, 2, 3):
            return None, []
        reward_group = int(chapter.get(str(3 + (reward_num - 1) * 2), 0) or 0)
        required = int(chapter.get(str(4 + (reward_num - 1) * 2), 0) or 0)
        rewards = [
            {'reward_type': int(row.get('3', 0) or 0),
             'reward_id': int(row.get('4', 0) or 0),
             'reward_value': float(row.get('5', 0) or 0)}
            for row in rows.get('13', []) if int(row.get('2', 0)) == reward_group
        ]
        return required, rewards
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None, []


def _grant_chapter_rewards(user, rewards):
    gift_rewards = [reward for reward in rewards if reward['reward_type'] == 11]
    _grant_gift_rewards(user, gift_rewards)
    # Reuse the normal reward implementation for owned content such as
    # costumes.  Type 9 is a collection ticket, represented by its id.
    if any(reward['reward_type'] != 11 for reward in rewards):
        from server.handlers.reward import _give_reward
        for reward in rewards:
            if reward['reward_type'] == 9:
                tickets = user.setdefault('user_ticketcollection', [])
                if not any(int(ticket.get('i_id', 0) or 0) == reward['reward_id']
                           for ticket in tickets):
                    tickets.append({'i_id': reward['reward_id']})
            elif reward['reward_type'] != 11:
                _give_reward(user, reward)


def _user_ap(user):
    """Return the persisted AP after applying elapsed offline regeneration.

    ``i_FullApTime`` is the epoch time at which the bar will become full.
    This lets the server calculate the same result after an app restart
    without trusting a value saved by the client.
    """
    now = int(time.time())
    ap = user.setdefault('user_ap', {
        'i_Ap': AP_MAX,
        'i_FullApTime': 0,
        'i_MaxAp': AP_MAX,
    })
    maximum = AP_MAX
    current = max(0, min(int(ap.get('i_Ap', maximum) or 0), maximum))
    full_at = int(ap.get('i_FullApTime', 0) or 0)

    if current < maximum and full_at:
        missing = max(0, (full_at - now + AP_REGEN_SECONDS - 1) // AP_REGEN_SECONDS)
        current = max(0, maximum - missing)
    if current >= maximum:
        current, full_at = maximum, 0
    elif not full_at:
        full_at = now + (maximum - current) * AP_REGEN_SECONDS

    ap.update({'i_Ap': current, 'i_FullApTime': full_at, 'i_MaxAp': maximum})
    return ap


def _add_ap(user, amount):
    ap = _user_ap(user)
    ap['i_Ap'] = min(AP_MAX, int(ap['i_Ap']) + int(amount))
    ap['i_FullApTime'] = (0 if ap['i_Ap'] >= AP_MAX
                          else int(time.time()) + (AP_MAX - ap['i_Ap']) * AP_REGEN_SECONDS)
    return ap


def _spend_ap(user, amount=AP_USE):
    ap = _user_ap(user)
    if int(ap['i_Ap']) < amount:
        return False, ap
    ap['i_Ap'] -= amount
    ap['i_FullApTime'] = int(time.time()) + (AP_MAX - ap['i_Ap']) * AP_REGEN_SECONDS
    return True, ap


@cmd('getChThird')
def h_get_ch_third(req, player, ctx):
    p = _payload(req)
    user = state.get_user(p.get('uuid') or ctx.get('uuid'))
    if not user:
        return {}, OK
    ap = _user_ap(user)
    state.save_user(user)
    return {
        'u_seq': user['userdata']['u_seq'],
        'user_ap': ap,
        'user_ch_third_stage': user.setdefault('user_ch_third_stage', []),
        'user_ch_third_chapter_reward': user.setdefault('user_ch_third_chapter_reward', []),
    }, OK


@cmd('chThirdStage')
def h_ch_third_stage(req, player, ctx):
    p = _payload(req)
    user = state.get_user(p.get('uuid') or ctx.get('uuid'))
    if not user:
        return {}, OK
    stage_id = int(p.get('i_id', 0) or 0)
    spent, ap = _spend_ap(user)
    if not spent:
        return {'clear': 0, 'user_ap': ap}, {'code': 1, 'errmsg': 'Not enough Cookie'}

    stages = user.setdefault('user_ch_third_stage', [])
    stage = next((x for x in stages if int(x.get('i_id', 0)) == stage_id), None)
    config = _stage_config(stage_id) or {}
    one_star = int(config.get('5', 1) or 1)
    two_star = int(config.get('6', one_star) or one_star)
    three_star = int(config.get('7', two_star) or two_star)

    # Each contributor supplies at most a third of the stage's three-star
    # target.  Consequently an empty slot cannot be disguised as a full score.
    third = three_star / 3.0
    character_level = max((int(row.get('i_Level', 0) or 0)
                           for row in user.get('characters', [])), default=0)
    character_score = round(third * min(1.0, character_level / 100.0))
    selected_profile_ids = []
    for value in str(p.get('profile_ids', '')).split(','):
        try:
            selected_profile_ids.append(int(value.strip()))
        except (TypeError, ValueError):
            continue
    music_id = int(p.get('music_id', 0) or 0)
    selected_music = next((row for row in user.get('user_music', [])
                           if int(row.get('i_id', 0) or 0) == music_id), None)
    music_score = round(third * min(1.0, int((selected_music or {}).get('i_Level', 0) or 0) / 50.0))
    profile_levels = {int(row.get('i_id', 0) or 0): int(row.get('i_Level', 0) or 0)
                      for row in user.get('user_follower_profile', [])}
    profile_ratio = (sum(min(1.0, profile_levels.get(profile_id, 0) / 20.0)
                         for profile_id in selected_profile_ids) / len(selected_profile_ids)
                     if selected_profile_ids else 0.0)
    follower_score = round(third * profile_ratio)
    total_score = character_score + music_score + follower_score
    star = 3 if total_score >= three_star else (2 if total_score >= two_star else (1 if total_score >= one_star else 0))
    clear = 1 if star else 0
    profile_scores = [{'i_id': profile_id,
                       'score': int(follower_score / len(selected_profile_ids)), 'bonus_score': 0}
                      for profile_id in selected_profile_ids]
    # Earlier versions stamped i_Star=3 regardless of the real score.  Clear
    # only those bad cached values once, then retain genuine best results.
    if not user.get('ch_third_score_fix_v1'):
        for saved_stage in stages:
            saved_stage['i_Star'] = 0
        user['ch_third_score_fix_v1'] = True
    if stage is None:
        stage = {'i_id': stage_id, 'i_ChapterId': stage_id // 1000,
                 'i_StageIndex': stage_id % 1000, 'i_Star': star}
        stages.append(stage)
    else:
        stage['i_Star'] = max(star, int(stage.get('i_Star', 0) or 0))
    rewards = _stage_rewards(config) if clear else []
    _grant_gift_rewards(user, rewards)
    state.save_user(user)
    return {
        'star': star, 'character_score': character_score, 'music_score': music_score,
        'follower_profile_score': follower_score, 'bonus_score': 0, 'total_score': total_score,
        'clear': clear, 'user_ap': ap, 'user_ch_third_stage': stage,
        'user_music': selected_music, 'reward_data': rewards, 'bonus_follower_profile_ids': [],
        'user_follower_profile_score': profile_scores,
    }, OK


@cmd('getChThirdStarReward')
def h_get_ch_third_star_reward(req, player, ctx):
    p = _payload(req)
    user = state.get_user(p.get('uuid') or ctx.get('uuid'))
    if not user:
        return {}, OK
    try:
        chapter_id = int(p.get('i_id', 0) or 0)
        reward_num = int(p.get('reward_num', 0) or 0)
    except (TypeError, ValueError):
        return {}, OK
    ap = _user_ap(user)
    required, rewards = _chapter_reward(chapter_id, reward_num)
    earned_stars = sum(int(stage.get('i_Star', 0) or 0)
                       for stage in user.get('user_ch_third_stage', [])
                       if int(stage.get('i_ChapterId', 0) or 0) == chapter_id)
    claims = user.setdefault('user_ch_third_chapter_reward', [])
    claim = next((row for row in claims if int(row.get('i_id', 0) or 0) == chapter_id), None)
    if claim is None:
        claim = {'i_id': chapter_id, 'i_ReceivedReward1': 0,
                 'i_ReceivedReward2': 0, 'i_ReceivedReward3': 0}
        claims.append(claim)
    field = f'i_ReceivedReward{reward_num}'
    allowed = (required is not None and earned_stars >= required
               and not int(claim.get(field, 0) or 0))
    granted = rewards if allowed else []
    if allowed:
        claim[field] = 1
        _grant_chapter_rewards(user, granted)
    state.save_user(user)
    # Return all schema-required fields even when unavailable/already claimed;
    # an empty response leaves the Unity client permanently loading.
    return {
        'i_id': chapter_id, 'reward_num': reward_num,
        'user_ap': ap, 'reward_data': granted,
    }, OK

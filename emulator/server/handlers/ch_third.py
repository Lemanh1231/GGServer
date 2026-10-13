"""Chapter 3 story energy (Cookie / AP) handlers."""
import json
import os
import time

from server import state, event_manager
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


def _score_config():
    """Read Table 34 (chthird_score) from game data."""
    try:
        with open(_GAME_DATA_PATH, encoding='utf-8') as f:
            rows = json.load(f).get('34', [])
        return {int(row.get('2', 0) or 0): row for row in rows}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}


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


def _get_or_create_girl_profile(user):
    profiles = user.setdefault('user_follower_profile', [])
    girl_profile = next((x for x in profiles if int(x.get('i_id', 0) or 0) == 100000), None)
    if girl_profile is None:
        girl_profile = {'i_id': 100000, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0}
        profiles.append(girl_profile)
    return girl_profile


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
    if not event_manager.is_chapter3_tour_enabled():
        return {}, {'code': 1, 'errmsg': 'Chapter 3 Tour is closed'}
    p = _payload(req)
    user = state.get_user(p.get('uuid') or ctx.get('uuid'))
    if not user:
        return {}, OK
    ap = _user_ap(user)
    stages = user.get('user_ch_third_stage') or user.get('user_chthird_stage')
    if not stages:
        stages = [{'i_id': 1001, 'i_ChapterId': 1, 'i_StageIndex': 1, 'i_Star': 3}]
        user['user_ch_third_stage'] = stages
        user['user_chthird_stage'] = stages
    state.save_user(user)
    return {
        'u_seq': user['userdata']['u_seq'],
        'user_ap': ap,
        'user_ch_third_stage': stages,
        'user_ch_third_chapter_reward': user.setdefault('user_ch_third_chapter_reward', []),
    }, OK


@cmd('chThirdStage')
def h_ch_third_stage(req, player, ctx):
    if not event_manager.is_chapter3_tour_enabled():
        return {'clear': 0}, {'code': 1, 'errmsg': 'Chapter 3 Tour is closed'}
    p = _payload(req)
    user = state.get_user(p.get('uuid') or ctx.get('uuid'))
    if not user:
        return {}, OK
    stage_id = int(p.get('i_id', 0) or 0)
    config = _stage_config(stage_id) or {}
    is_story = (config.get('34') == 'Story')

    if not is_story:
        spent, ap = _spend_ap(user)
        if not spent:
            return {'clear': 0, 'user_ap': ap}, {'code': 1, 'errmsg': 'Not enough Cookie'}
    else:
        ap = _user_ap(user)

    stages = user.get('user_ch_third_stage') or user.get('user_chthird_stage')
    if not stages:
        stages = [{'i_id': 1001, 'i_ChapterId': 1, 'i_StageIndex': 1, 'i_Star': 3}]
    user['user_ch_third_stage'] = stages
    user['user_chthird_stage'] = stages
    stage = next((x for x in stages if int(x.get('i_id', 0)) == stage_id), None)

    if is_story:
        if stage is None:
            stage = {'i_id': stage_id, 'i_ChapterId': stage_id // 1000,
                     'i_StageIndex': stage_id % 1000, 'i_Star': 0}
            stages.append(stage)
        girl_profile = _get_or_create_girl_profile(user)
        exp_gain = 200 if stage_id >= 2000 else 100
        from server.handlers.follower import _follower_data, _apply_profile_exp
        _, _, level_data, _, _ = _follower_data()
        gg_levels = level_data.get(100000, {})
        _apply_profile_exp(girl_profile, gg_levels, exp_gain)
        state.save_user(user)
        return {
            'star': 0, 'character_score': 0, 'music_score': 0,
            'follower_profile_score': 0, 'bonus_score': 0, 'total_score': 0,
            'clear': 1, 'user_ap': ap, 'user_ch_third_stage': stage,
            'user_music': None, 'reward_data': [],
            'bonus_follower_profile_ids': [],
            'user_follower_profile': girl_profile,
            'user_follower_profile_score': [],
        }, OK

    one_star = int(config.get('5', 1) or 1)
    two_star = int(config.get('6', one_star) or one_star)
    three_star = int(config.get('7', two_star) or two_star)

    score_table = _score_config()
    max_level = max(score_table.keys()) if score_table else 50

    # Character score from Table 34 column 3
    character_level = max((int(row.get('i_Level', 0) or 0)
                           for row in user.get('characters', [])), default=1)
    char_row = score_table.get(min(max(1, character_level), max_level), {})
    char_score = int(char_row.get('3', 50) or 50)

    selected_profile_ids = []
    for value in str(p.get('profile_ids', '')).split(','):
        try:
            selected_profile_ids.append(int(value.strip()))
        except (TypeError, ValueError):
            continue

    # Music multiplier & bonus from Table 34 column 5
    music_id = int(p.get('music_id', 0) or 0)
    selected_music = next((row for row in user.get('user_music', [])
                           if int(row.get('i_id', 0) or 0) == music_id), None)
    music_level = int((selected_music or {}).get('i_Level', 1) or 1)
    music_row = score_table.get(min(max(1, music_level), max_level), {})
    music_mult = (int(music_row.get('5', 550) or 550)) / 1000.0

    rec_music_id = int(config.get('33', 0) or 0)
    is_bonus_music = (music_id > 0 and music_id == rec_music_id)
    bonus_mult = 0.2 if is_bonus_music else 0.0

    char_music_score = round(char_score * (music_mult + bonus_mult))
    music_score = round(char_score * music_mult)
    bonus_music_score = round(char_score * bonus_mult) if is_bonus_music else 0

    # Follower profiles score & bonus from Table 34 column 4
    profile_levels = {int(row.get('i_id', 0) or 0): int(row.get('i_Level', 0) or 0)
                      for row in user.get('user_follower_profile', [])}
    rec_profile_ids = [int(x.strip()) for x in str(config.get('8', '')).split(',')
                       if x.strip().isdigit()]

    profile_scores = []
    bonus_follower_profile_ids = []
    total_follower_score = 0
    bonus_follower_score = 0

    for pid in selected_profile_ids:
        plv = profile_levels.get(pid, 1)
        fol_row = score_table.get(min(max(1, plv), max_level), {})
        base_fol = int(fol_row.get('4', 100) or 100)
        is_bonus_fol = (pid in rec_profile_ids)
        b_fol = round(base_fol * 0.2) if is_bonus_fol else 0
        if is_bonus_fol:
            bonus_follower_profile_ids.append(pid)
            bonus_follower_score += b_fol
        profile_scores.append({
            'i_id': pid,
            'score': base_fol,
            'bonus_score': b_fol,
        })
        total_follower_score += base_fol

    bonus_score = bonus_music_score + bonus_follower_score
    follower_score = total_follower_score
    total_score = char_music_score + total_follower_score + bonus_follower_score

    # Stage 1-1 (1001) is the Chapter 3 tutorial stage and must always clear with 3 stars!
    is_tutorial = (stage_id == 1001)
    if is_tutorial:
        star = 3
        clear = 1
        total_score = max(total_score, three_star if three_star > 0 else 180)
    else:
        star = 3 if total_score >= three_star else (2 if total_score >= two_star else (1 if total_score >= one_star else 0))
        clear = 1 if star > 0 else 0

    if stage is None:
        stage = {'i_id': stage_id, 'i_ChapterId': stage_id // 1000,
                 'i_StageIndex': stage_id % 1000, 'i_Star': star}
        stages.append(stage)
    else:
        stage['i_Star'] = max(star, int(stage.get('i_Star', 0) or 0))
    rewards = _stage_rewards(config) if clear else []
    _grant_gift_rewards(user, rewards)

    girl_profile = _get_or_create_girl_profile(user)
    if clear:
        exp_gain = 200 if stage_id >= 2000 else 100
        from server.handlers.follower import _follower_data, _apply_profile_exp
        _, _, level_data, _, _ = _follower_data()
        gg_levels = level_data.get(100000, {})
        _apply_profile_exp(girl_profile, gg_levels, exp_gain)

    state.save_user(user)
    return {
        'star': star, 'character_score': char_score, 'music_score': music_score,
        'follower_profile_score': follower_score, 'bonus_score': bonus_score, 'total_score': total_score,
        'clear': clear, 'user_ap': ap, 'user_ch_third_stage': stage,
        'user_music': selected_music, 'reward_data': rewards,
        'bonus_follower_profile_ids': bonus_follower_profile_ids,
        'user_follower_profile': girl_profile,
        'bonus_music_score': bonus_music_score,
        'user_follower_profile_score': profile_scores,
    }, OK


@cmd('chThirdStreamStage')
def h_ch_third_stream_stage(req, player, ctx):
    p = _payload(req)
    user = state.get_user(p.get('uuid') or ctx.get('uuid'))
    if not user:
        return {}, OK
    try:
        stage_id = int(p.get('i_id', 0) or 0)
        count = max(1, int(p.get('count', 1) or 1))
    except (TypeError, ValueError):
        return {}, OK

    ap_cost = count * AP_USE
    spent, ap = _spend_ap(user, ap_cost)
    if not spent:
        return {'clear': 0, 'user_ap': ap}, {'code': 1, 'errmsg': 'Not enough Cookie'}

    config = _stage_config(stage_id) or {}
    all_reward_data = {}
    for run_idx in range(1, count + 1):
        run_rewards = _stage_rewards(config)
        all_reward_data[run_idx] = run_rewards
        _grant_gift_rewards(user, run_rewards)

    exp_per_run = 200 if stage_id >= 2000 else 100
    total_exp_gain = exp_per_run * count

    girl_profile = _get_or_create_girl_profile(user)
    from server.handlers.follower import _follower_data, _apply_profile_exp
    _, _, level_data, _, _ = _follower_data()
    gg_levels = level_data.get(100000, {})
    _apply_profile_exp(girl_profile, gg_levels, total_exp_gain)

    state.save_user(user)

    return {
        'i_id': stage_id,
        'user_ap': ap,
        'user_follower_profile': girl_profile,
        'reward_data': all_reward_data,
    }, OK


@cmd('getChThirdStarReward')
@cmd('setChThirdChapterReward')
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
    stages = user.get('user_ch_third_stage') or user.get('user_chthird_stage') or []
    earned_stars = sum(int(stage.get('i_Star', 0) or 0)
                       for stage in stages
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

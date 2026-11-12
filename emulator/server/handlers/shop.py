import os
import json
import time
from server import state
from server.handlers.registry import cmd, OK, _payload

# game_data.json lives at emulator/gamedata/ -- resolve absolutely so price lookups don't depend
# on the process CWD (the old relative 'emulator/gamedata/...' silently failed -> flat fallback).
_GAME_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'gamedata', 'game_data.json')

_SHOP_TABLE_CACHE = None
_REWARD_TABLE_CACHE = None
_AD_LEVEL_TABLE_CACHE = None

# Shop idx -> AdLevel group_id (Table 37)
AD_SHOP_GROUP_MAP = {
    3: 200010,   # Free Chocolate (Lv 1..20)
    2: 210010,   # Free Likes Ch1 (Lv 1..30)
    18: 220010,  # Free Hearts Ch2 (Lv 1..30)
}
AD_GROUP_SHOP_MAP = {v: k for k, v in AD_SHOP_GROUP_MAP.items()}
AD_EXP_PER_CLAIM = 5


def _load_shop_tables():
    global _SHOP_TABLE_CACHE, _REWARD_TABLE_CACHE, _AD_LEVEL_TABLE_CACHE
    if _SHOP_TABLE_CACHE is not None and _REWARD_TABLE_CACHE is not None and _AD_LEVEL_TABLE_CACHE is not None:
        return _SHOP_TABLE_CACHE, _REWARD_TABLE_CACHE, _AD_LEVEL_TABLE_CACHE
    shop_map = {}
    reward_map = {}
    ad_level_map = {}
    try:
        with open(_GAME_DATA_PATH, 'r', encoding='utf-8') as f:
            gd = json.load(f)
        for row in gd.get('12', []):
            sid = int(row.get('1', 0) or 0)
            if sid:
                shop_map[sid] = row
        for row in gd.get('13', []):
            rg = int(row.get('2', 0) or 0)
            if rg:
                reward_map.setdefault(rg, []).append(row)
        for row in gd.get('37', []):
            gid = int(row.get('1', 0) or 0)
            if gid:
                ad_level_map.setdefault(gid, []).append({
                    'i_id': gid,
                    'i_Level': int(row.get('2', 1) or 1),
                    'i_RequireEXP': int(row.get('3', 0) or 0),
                    'i_RewardGroup': int(row.get('4', gid) or gid),
                })
        for gid in ad_level_map:
            ad_level_map[gid].sort(key=lambda x: x['i_Level'])
    except Exception:
        pass
    _SHOP_TABLE_CACHE = shop_map
    _REWARD_TABLE_CACHE = reward_map
    _AD_LEVEL_TABLE_CACHE = ad_level_map
    return shop_map, reward_map, ad_level_map


def _calc_ad_level_and_reward_group(group_id, exp_val):
    _, _, ad_level_map = _load_shop_tables()
    rows = ad_level_map.get(int(group_id), [])
    if not rows:
        return 1, int(group_id)
    best_lvl = 1
    best_rg = int(group_id)
    for r in rows:
        if int(exp_val) >= r['i_RequireEXP']:
            best_lvl = r['i_Level']
            best_rg = r['i_RewardGroup']
        else:
            break
    return best_lvl, best_rg


def _normalise_user_shop(user):
    """Deduplicate user_shop and normalize cooldown/daily items so free items never hit a 4-claim wall."""
    if not user:
        return []
    raw_shop = user.get('user_shop', [])
    if not isinstance(raw_shop, list):
        raw_shop = []

    shop_map, _, _ = _load_shop_tables()
    now_ts = int(time.time())
    today_ymd = time.strftime('%Y%m%d', time.localtime(now_ts))

    by_id = {}
    for item in raw_shop:
        if not isinstance(item, dict):
            continue
        iid = int(item.get('i_id', 0) or 0)
        if iid <= 0:
            continue
        cnt = int(item.get('i_Count', 0) or 0)
        tot = max(cnt, int(item.get('i_TotalCount', 0) or 0))
        ptime = int(item.get('i_PurchaseTime', 0) or 0)
        if ptime > now_ts:
            ptime = now_ts
        upd = int(item.get('upd_day', ptime) or ptime)
        lvl = max(1, int(item.get('i_Level', 1) or 1))

        if iid in by_id:
            prev = by_id[iid]
            prev['i_Count'] = max(prev['i_Count'], cnt)
            prev['i_TotalCount'] = max(prev['i_TotalCount'], tot)
            prev['i_PurchaseTime'] = max(prev['i_PurchaseTime'], ptime)
            prev['upd_day'] = max(prev['upd_day'], upd)
            prev['i_Level'] = max(prev['i_Level'], lvl)
        else:
            by_id[iid] = {
                'i_id': iid,
                'i_Level': lvl,
                'i_Count': cnt,
                'i_TotalCount': tot,
                'i_PurchaseTime': ptime,
                'upd_day': upd,
            }

    for iid, entry in by_id.items():
        srow = shop_map.get(iid, {})
        cond_type = int(srow.get('36', 0) or 0)
        if cond_type == 4 or iid in AD_SHOP_GROUP_MAP:
            # Cooldown-only free items (idx = 2, 3, 18): never cap by i_Count
            entry['i_Count'] = 0
        elif cond_type == 5 or iid == 10012:
            # Daily-limited items (idx = 10012 Fever Time): reset when calendar day changes
            ptime = int(entry.get('i_PurchaseTime', 0) or 0)
            p_ymd = time.strftime('%Y%m%d', time.localtime(ptime)) if ptime > 0 else ''
            if p_ymd != today_ymd:
                entry['i_Count'] = 0
                entry['i_PurchaseTime'] = 0

    result = list(by_id.values())
    user['user_shop'] = result
    return result


def _normalise_user_ad_level(user):
    """Ensure user['user_ad_level'] has all 3 groups (200010, 210010, 220010) synced with Table 37."""
    if not user:
        return [
            {'i_id': 200010, 'i_Level': 1, 'i_EXP': 0},
            {'i_id': 210010, 'i_Level': 1, 'i_EXP': 0},
            {'i_id': 220010, 'i_Level': 1, 'i_EXP': 0},
        ]

    shop_list = _normalise_user_shop(user)
    shop_totals = {
        int(it.get('i_id', 0) or 0): int(it.get('i_TotalCount', 0) or 0)
        for it in shop_list if isinstance(it, dict)
    }

    raw_ad = user.get('user_ad_level')
    existing = {}
    if isinstance(raw_ad, list):
        for x in raw_ad:
            if isinstance(x, dict) and x.get('i_id'):
                gid = int(x['i_id'])
                existing[gid] = x
    elif isinstance(raw_ad, dict) and raw_ad.get('i_id'):
        existing[int(raw_ad['i_id'])] = raw_ad

    result = []
    for gid in (200010, 210010, 220010):
        shop_idx = AD_GROUP_SHOP_MAP[gid]
        hist_exp = shop_totals.get(shop_idx, 0) * AD_EXP_PER_CLAIM
        cur_entry = existing.get(gid)
        cur_exp = int(cur_entry.get('i_EXP', 0) or 0) if cur_entry else 0
        # Replace legacy placeholder i_EXP=1 with 0 if no claims were made
        if cur_exp == 1 and hist_exp == 0:
            cur_exp = 0
        final_exp = max(cur_exp, hist_exp)
        lvl, _ = _calc_ad_level_and_reward_group(gid, final_exp)
        result.append({
            'i_id': gid,
            'i_Level': lvl,
            'i_EXP': final_exp,
        })
        # Also keep i_Level in user_shop entry synced for convenience
        for it in shop_list:
            if int(it.get('i_id', 0) or 0) == shop_idx:
                it['i_Level'] = lvl

    user['user_ad_level'] = result
    return result


def _advance_user_ad_level(user, shop_idx):
    """Grant +5 EXP to the UserAdLevel group for shop_idx (2, 3, or 18) and return (entry_dict, reward_group)."""
    gid = AD_SHOP_GROUP_MAP.get(int(shop_idx))
    if not gid:
        return None, None
    ad_levels = _normalise_user_ad_level(user)
    target = next((x for x in ad_levels if int(x.get('i_id', 0) or 0) == gid), None)
    if not target:
        target = {'i_id': gid, 'i_Level': 1, 'i_EXP': 0}
        ad_levels.append(target)

    # First get the reward_group for the CURRENT level being claimed (or after level-up)
    # In Guitar Girl, claiming at Level L grants Level L's reward and adds +5 EXP toward Level L+1
    _, claim_rg = _calc_ad_level_and_reward_group(gid, target['i_EXP'])
    new_exp = int(target.get('i_EXP', 0) or 0) + AD_EXP_PER_CLAIM
    new_lvl, _ = _calc_ad_level_and_reward_group(gid, new_exp)
    target['i_EXP'] = new_exp
    target['i_Level'] = new_lvl
    return dict(target), claim_rg

VARIETY_STORE_CATALOG = {
    1: {'cost': 10, 'reward_type': 4, 'reward_id': 1, 'reward_value': 1},
    2: {'cost': 30, 'reward_type': 4, 'reward_id': 2, 'reward_value': 1},
    3: {'cost': 30, 'reward_type': 4, 'reward_id': 3, 'reward_value': 1},
    4: {'cost': 50, 'reward_type': 4, 'reward_id': 4, 'reward_value': 1},
    5: {'cost': 50, 'reward_type': 4, 'reward_id': 5, 'reward_value': 1},
    6: {'cost': 50, 'reward_type': 4, 'reward_id': 6, 'reward_value': 1},
    7: {'cost': 100, 'reward_type': 4, 'reward_id': 7, 'reward_value': 1},
    8: {'cost': 100, 'reward_type': 4, 'reward_id': 8, 'reward_value': 1},
    9: {'cost': 100, 'reward_type': 4, 'reward_id': 9, 'reward_value': 1},
    10: {'cost': 150, 'reward_type': 4, 'reward_id': 10, 'reward_value': 1},
    11: {'cost': 50, 'reward_type': 1, 'reward_id': 4, 'reward_value': 3000},
    12: {'cost': 100, 'reward_type': 1, 'reward_id': 1, 'reward_value': 10},
    13: {'cost': 150, 'reward_type': 4, 'reward_id': 11, 'reward_value': 1},
    14: {'cost': 150, 'reward_type': 4, 'reward_id': 12, 'reward_value': 1},
    15: {'cost': 150, 'reward_type': 4, 'reward_id': 13, 'reward_value': 1},
    16: {'cost': 200, 'reward_type': 4, 'reward_id': 14, 'reward_value': 1},
    17: {'cost': 200, 'reward_type': 4, 'reward_id': 15, 'reward_value': 1},
    18: {'cost': 200, 'reward_type': 4, 'reward_id': 16, 'reward_value': 1},
    19: {'cost': 200, 'reward_type': 4, 'reward_id': 17, 'reward_value': 1},
}

def _resolve_user_and_id(p, ctx):
    u_ident = p.get('device_uuid') or p.get('uuid') or (ctx.get('uuid') if ctx else None) or str(p.get('u_seq', '')) or str(p.get('u_id', ''))
    user = state.get_user(u_ident)
    canonical_uuid = (user.get('uuid') if user else None) or ((user.get('userdata') or {}).get('uuid') if user else None) or u_ident
    return user, canonical_uuid

@cmd('buyVarietyStore')
def h_buy_variety(req, player, ctx):
    p = _payload(req)
    user, uuid = _resolve_user_and_id(p, ctx)
    
    idx = int(p.get('idx', 1) or 1)
    item_info = VARIETY_STORE_CATALOG.get(idx)
    if not item_info:
        item_info = {'cost': 50, 'reward_type': 4, 'reward_id': idx, 'reward_value': 1}
    
    paid = False
    if user:
        paid = _deduct_currency(uuid, user, 'GP', item_info['cost'])
    if paid:
        import time
        now = int(time.time())
        today = int(time.strftime('%Y%m%d'))
        # 1. Update user_candy_shop
        cs_list = user.setdefault('user_candy_shop', [])
        cs_item = next((x for x in cs_list if x.get('i_id') == idx), None)
        if cs_item:
            if cs_item.get('upd_day') != today:
                cs_item['i_CurrentBuyCount'] = 1
            else:
                cs_item['i_CurrentBuyCount'] = cs_item.get('i_CurrentBuyCount', 0) + 1
            cs_item['i_TotalBuyCount'] = cs_item.get('i_TotalBuyCount', 0) + 1
            cs_item['l_LastBuyTick'] = now
            cs_item['upd_day'] = today
        else:
            cs_list.append({
                'i_id': idx,
                'i_CurrentBuyCount': 1,
                'i_TotalBuyCount': 1,
                'l_LastBuyTick': now,
                'upd_day': today,
            })

        # 2. Grant reward
        rtype = item_info['reward_type']
        rid = item_info['reward_id']
        rval = item_info['reward_value']
        ud = user.setdefault('userdata', {})
        if rtype == 4:  # Prop
            props = user.setdefault('user_prop', [])
            prop = next((x for x in props if int(x.get('i_id', 0) or 0) == rid), None)
            if prop:
                prop['i_Level'] = prop.get('i_Level', 1) + 1
            else:
                props.append({'i_id': rid, 'i_Level': 1})
        elif rtype in (1, 11):  # Table 1: Currency / Items
            if rid == 1:  # Chocolate (Socola) -> u_cp
                ud['u_cp'] = int(ud.get('u_cp', 0) or 0) + int(rval)
                state.increment_currency(uuid, cp=int(rval))
            elif rid == 2:  # Candy (Kẹo)
                ud['u_candy'] = ud.get('u_candy', 0.0) + float(rval)
                state.increment_currency(uuid, candy=float(rval))
            elif rid in (3, 4):  # Like (Lượt thích)
                ud['u_like'] = ud.get('u_like', 0.0) + float(rval)
                state.increment_currency(uuid, like=float(rval))
            elif rid == 8:  # Fans
                ud['u_fans'] = ud.get('u_fans', 0) + int(rval)
                state.increment_currency(uuid, fans=int(rval))
            elif rid == 11:  # Cookie (Bánh quy)
                state.add_ap(user, int(rval))

        state.save_user(user)

    ud = user['userdata'] if user else {'u_cp': 0, 'u_candy': 0.0}
    return {
        'u_cp': ud.get('u_cp', 0),
        'u_candy': float(ud.get('u_candy', 0.0)),
        'reward_type': item_info['reward_type'],
        'reward_id': item_info['reward_id'],
        'reward_value': item_info['reward_value'],
        'status': 'Y' if paid else 'N'
    }, OK

def _check_purchase_eligibility(user, idx):
    if not user:
        return False, 'User not found'
    try:
        idx = int(idx)
    except (ValueError, TypeError):
        return False, 'Invalid item ID'

    shop_list = _normalise_user_shop(user)

    # Check Star Pass tickets (1000..1999)
    if 1000 <= idx < 2000:
        season_num = idx % 1000
        sub_list = user.get('user_subscribe_list', [])
        if any(int(s.get('i_SubscribeID', 0) or 0) in (season_num, 1000 + season_num) and int(s.get('i_isActive', 1) or 0) == 1 for s in sub_list):
            return False, 'Bạn đã sở hữu Thẻ Sao mùa này rồi!'
        tickets = user.get('user_ticketcollection', [])
        if any(int(t.get('i_id', 0) or 0) == season_num for t in tickets):
            return False, 'Bạn đã sở hữu Thẻ Sao mùa này rồi!'

    # Check Star Pass merchandise packs (2000..3020)
    if 2000 <= idx <= 3020:
        season_num = idx % 1000
        pack_ids = {2000 + season_num, 3000 + season_num}
        if any(int(item.get('i_id', 0) or 0) in pack_ids and int(item.get('i_Count', item.get('i_TotalCount', 0)) or 0) > 0 for item in shop_list):
            return False, 'Bạn đã sở hữu gói vật phẩm này rồi!'

    # Check Table 12 condition rules:
    # - col 35 = b_IsActive (1)
    # - col 36 = i_Condition:
    #     1, 2 -> One-time purchase limit (col 37 = max count, usually 1)
    #     4    -> Cooldown-only free items (idx = 2, 3, 18; col 37 = 900s cooldown, NO count cap!)
    #     5    -> Daily limit (idx = 10012 Fever Time; col 37 = 1 per day, resets each calendar day)
    shop_map, _, _ = _load_shop_tables()
    row = shop_map.get(idx)
    if row:
        cond_type = int(row.get('36', 0) or 0)
        cond_val = int(row.get('37', 0) or 0)
        if cond_type in (1, 2) and cond_val > 0:
            cur_cnt = sum(int(it.get('i_Count', it.get('i_TotalCount', 0)) or 0) for it in shop_list if int(it.get('i_id', 0) or 0) == idx)
            if cur_cnt >= cond_val:
                return False, 'Vật phẩm đã đạt giới hạn mua tối đa!'
        elif cond_type == 5 and cond_val > 0:
            today_ymd = time.strftime('%Y%m%d', time.localtime())
            cur_cnt = 0
            for it in shop_list:
                if int(it.get('i_id', 0) or 0) == idx:
                    ptime = int(it.get('i_PurchaseTime', 0) or 0)
                    p_ymd = time.strftime('%Y%m%d', time.localtime(ptime)) if ptime > 0 else ''
                    if p_ymd == today_ymd:
                        cur_cnt += int(it.get('i_Count', 0) or 0)
            if cur_cnt >= cond_val:
                return False, 'Vật phẩm đã đạt giới hạn mua trong ngày!'

    return True, ''

@cmd('buyCheck')
def h_buy_check(req, player, ctx):
    p = _payload(req)
    user, uuid = _resolve_user_and_id(p, ctx)
    idx = p.get('idx')
    if idx is not None and user:
        eligible, err_msg = _check_purchase_eligibility(user, idx)
        if not eligible:
            return {'result': 'fail'}, {'code': 1, 'errmsg': err_msg}
    # libil2cpp.so at 0x21E0D44 compares data.Data.Result with "ok" (OrdinalIgnoreCase)
    return {'result': 'ok'}, OK

@cmd('checkBuyShop')
def h_check_buy_shop(req, player, ctx):
    p = _payload(req)
    user, uuid = _resolve_user_and_id(p, ctx)
    shop_id = p.get('shop_id')
    try:
        idx = int(shop_id)
    except (TypeError, ValueError):
        idx = 0
    is_owner = 0
    if idx and user:
        eligible, _ = _check_purchase_eligibility(user, idx)
        if not eligible:
            is_owner = 1
    return {'is_owner': is_owner}, OK

@cmd('buyShop')
def h_buy_shop(req, player, ctx):
    p = _payload(req)
    user, uuid = _resolve_user_and_id(p, ctx)
    if not user:
        return {}, {'code': 1, 'errmsg': 'User not found'}

    idx = int(p.get('idx', 1))

    eligible, err_msg = _check_purchase_eligibility(user, idx)
    if not eligible:
        return {}, {'code': 1, 'errmsg': err_msg}
    
    sell_type = 1
    price = 0
    reward_group = 0
    cond_type = 0
    shop_map, reward_map, _ = _load_shop_tables()
    srow = shop_map.get(idx)
    if srow:
        sell_type = int(srow.get('33', 1) or 0)
        price = int(srow.get('34', 0) or 0)
        reward_group = int(srow.get('31', 0) or 0)
        cond_type = int(srow.get('36', 0) or 0)

    if idx in (2003, 3003):
        # Season 3 discounted live pack is 50 CP
        price = 50
        
    paid = False
    is_star_pass = (1000 <= idx <= 3020)
    if is_star_pass:
        paid = _deduct_currency(uuid, user, 'CP', price)
        if not paid:
            return {}, {'code': 1, 'errmsg': 'Không đủ Socola!'}
    elif sell_type == 1:
        paid = _deduct_currency(uuid, user, 'CP', price)
        if not paid:
            return {}, {'code': 1, 'errmsg': 'Not enough CP'}
    elif sell_type in (0, 2):
        paid = True

    # If this is an AdLevel free shop item (idx in 2, 3, 18), advance UserAdLevel (+5 EXP)
    # and use the player's current AdLevel reward_group (e.g. 200010 -> 200020 -> ... -> 200200)
    updated_ad_level = None
    if idx in AD_SHOP_GROUP_MAP:
        updated_ad_level, ad_rg = _advance_user_ad_level(user, idx)
        if ad_rg:
            reward_group = ad_rg
    else:
        _normalise_user_ad_level(user)

    rewards = []
    for r in reward_map.get(reward_group, []):
        rewards.append({
            'reward_type': int(r.get('3', 1)),
            'reward_id': int(r.get('4', 0)),
            'reward_value': int(r.get('5', 0))
        })

    # Apply granted rewards to server state so returned balances are up-to-date
    ud = user.setdefault('userdata', {})
    for rew in rewards:
        rtype = rew['reward_type']
        rid = rew['reward_id']
        rval = rew['reward_value']
        if rtype in (1, 11):
            if rid == 1: # Chocolate (Socola)
                ud['u_cp'] = int(ud.get('u_cp', 0) or 0) + int(rval)
                state.increment_currency(uuid, cp=int(rval))
            elif rid == 2: # Candy (Kẹo)
                ud['u_candy'] = ud.get('u_candy', 0.0) + float(rval)
                state.increment_currency(uuid, candy=float(rval))
            elif rid in (3, 4): # Like (Lượt thích)
                ud['u_like'] = ud.get('u_like', 0.0) + float(rval)
                state.increment_currency(uuid, like=float(rval))
            elif rid == 8: # Fans
                ud['u_fans'] = ud.get('u_fans', 0) + int(rval)
                state.increment_currency(uuid, fans=int(rval))
            elif rid == 11: # Cookie (Bánh quy)
                state.add_ap(user, int(rval))
        elif rtype == 2: # Music
            musics = user.setdefault('user_music', [])
            if not any(int(m.get('i_id', 0) or 0) == rid for m in musics):
                musics.append({'i_id': rid, 'i_Level': 1, 'i_BonusLevel': 0, 'b_EncoreBonusAppear': 0, 'l_EncoreBonusActivateTime': 0, 'i_EncoreBonusFollowerId': 0, 'i_ChThirdActiveTime': 0})
        elif rtype == 3: # Costume
            costumes = user.setdefault('costumes', [])
            if not any(int(c.get('i_id', 0) or 0) == rid for c in costumes):
                costumes.append({'i_id': rid, 'i_Level': 1, 'i_BonusLevel': 0})
        elif rtype == 4: # Prop
            props = user.setdefault('user_prop', [])
            prop = next((x for x in props if int(x.get('i_id', 0) or 0) == rid), None)
            if prop:
                prop['i_Level'] = prop.get('i_Level', 1) + 1
            else:
                props.append({'i_id': rid, 'i_Level': 1})
        elif rtype == 6: # Timed Buff (Table 6, e.g. rid=2 Fever Time x2 for rval seconds)
            now_ts = int(time.time())
            dur = int(rval)
            buffs = user.setdefault('user_buff', [])
            b_entry = next((b for b in buffs if int(b.get('i_id', 0) or 0) == int(rid)), None)
            if b_entry:
                cur_end = int(b_entry.get('i_EndTime', b_entry.get('i_ExpiredTime', 0)) or 0)
                b_entry['i_Level'] = max(1, int(b_entry.get('i_Level', 1) or 1))
                b_entry['i_ActiveTime'] = now_ts
                b_entry['i_EndTime'] = max(now_ts, cur_end) + dur
                b_entry.pop('i_BuffTime', None)
                b_entry.pop('i_ExpiredTime', None)
            else:
                buffs.append({
                    'i_id': int(rid),
                    'i_Level': 1,
                    'i_ActiveTime': now_ts,
                    'i_EndTime': now_ts + dur,
                })
        elif rtype == 9: # Guitar
            guitars = user.setdefault('user_guitar', [])
            if not any(int(g.get('i_id', 0) or 0) == rid for g in guitars):
                guitars.append({'i_id': rid, 'i_Level': 1, 'i_BonusLevel': 0})
        elif rtype == 10: # Star Pass (Subscribe Pass)
            sub_list = user.setdefault('user_subscribe_list', [])
            season_num = rid % 1000 if rid > 1000 else rid
            now_ts = int(time.time())
            for pid in {rid, season_num, 1000 + season_num}:
                if not any(int(s.get('i_SubscribeID', 0) or 0) == pid for s in sub_list):
                    sub_list.append({'i_SubscribeID': pid, 'i_ActiveTime': now_ts, 'i_isActive': 1})
            tickets = user.setdefault('user_ticketcollection', [])
            for tid in {rid, season_num, 1000 + season_num}:
                if not any(int(t.get('i_id', 0) or 0) == tid for t in tickets):
                    tickets.append({'i_id': tid})

    # Direct purchase of Star Pass or Star Pass merchandise packs
    season_num = idx % 1000
    if 1 <= season_num <= 13 and (1000 <= idx <= 3020):
        sub_list = user.setdefault('user_subscribe_list', [])
        now_ts = int(time.time())
        pids_to_sub = {season_num, 1000 + season_num}
        for pid in pids_to_sub:
            if not any(int(s.get('i_SubscribeID', 0) or 0) == pid for s in sub_list):
                sub_list.append({'i_SubscribeID': pid, 'i_ActiveTime': now_ts, 'i_isActive': 1})
        tickets = user.setdefault('user_ticketcollection', [])
        for tid in pids_to_sub:
            if not any(int(t.get('i_id', 0) or 0) == tid for t in tickets):
                tickets.append({'i_id': tid})
        if not any(rew.get('reward_type') == 10 for rew in rewards):
            rewards.append({'reward_type': 10, 'reward_id': 1000 + season_num, 'reward_value': 1})

    lst = _normalise_user_shop(user)
    now = int(time.time())
    ids_to_record = [idx]
    if 2000 <= idx <= 3020:
        season_num = idx % 1000
        ids_to_record = list({idx, 2000 + season_num, 3000 + season_num})

    new_lvl_for_shop = int(updated_ad_level['i_Level']) if updated_ad_level else 1
    for it_id in ids_to_record:
        item = next((x for x in lst if int(x.get('i_id', 0) or 0) == it_id), None)
        is_cooldown_free = (cond_type == 4 or it_id in AD_SHOP_GROUP_MAP)
        if item:
            item['i_Count'] = 0 if is_cooldown_free else (item.get('i_Count', 0) + 1)
            item['i_TotalCount'] = item.get('i_TotalCount', 0) + 1
            item['i_PurchaseTime'] = now
            item['upd_day'] = now
            if updated_ad_level and it_id == idx:
                item['i_Level'] = new_lvl_for_shop
        else:
            lst.append({
                'i_id': it_id,
                'i_Level': new_lvl_for_shop if (updated_ad_level and it_id == idx) else 1,
                'i_Count': 0 if is_cooldown_free else 1,
                'i_TotalCount': 1,
                'i_PurchaseTime': now,
                'upd_day': now,
            })
    from server.handlers.auth import _normalise_ticketcollection
    _normalise_ticketcollection(user)
    state.save_user(user)

    ret_payload = {
        'u_cp': ud.get('u_cp', 0),
        'u_candy': float(ud.get('u_candy', 0.0)),
        'reward_data': rewards,
    }
    if updated_ad_level is not None:
        ret_payload['user_ad_level'] = updated_ad_level
    return ret_payload, OK

def _get_price(table_id, item_id, currency_col, price_col):
    try:
        with open(_GAME_DATA_PATH, 'r', encoding='utf-8') as f:
            gd = json.load(f)
            for row in gd.get(str(table_id), []):
                if str(row.get('1')) == str(item_id):
                    currency = str(row.get(str(currency_col), ''))
                    price = int(row.get(str(price_col), 0))
                    if str(table_id) == '2' and price == 0:
                        alt_price = int(row.get('46', 0) or 0)
                        if alt_price > 0:
                            price = alt_price
                    if price < 0:
                        return None, None
                    return currency, price
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return None, None

def _get_variety_price(item_id):
    info = VARIETY_STORE_CATALOG.get(int(item_id))
    if info:
        return 'GP', info['cost']
    return 'GP', 50

def _deduct_currency(uuid, user, currency, price):
    if not user or not currency or price is None:
        return False
    try:
        price = int(price)
    except (TypeError, ValueError):
        return False
    if price < 0:
        return False
    if price == 0:
        return True
    currency = str(currency).upper()
    if currency in ('CP', 'CHOCOLATE', 'SOCOLA'):
        is_cp = True
    elif currency in ('GP', 'CANDY'):
        is_cp = False
    else:
        # Package/real-money and malformed catalogue rows must not be charged
        # as Candy by an offline purchase endpoint.
        return False
    canonical_uuid = uuid or user.get('uuid') or (user.get('userdata') or {}).get('uuid')
    if not state.spend_currency(canonical_uuid, currency='cp' if is_cp else 'candy', amount=price):
        return False
    ud = user.setdefault('userdata', {})
    if is_cp:
        ud['u_cp'] = int(ud.get('u_cp', 0) or 0) - price
    else:
        ud['u_candy'] = float(ud.get('u_candy', 0.0) or 0.0) - price
    return True

@cmd('buyMusic')
def h_buy_music(req, player, ctx):
    p = _payload(req)
    user, uuid = _resolve_user_and_id(p, ctx)
    
    idx = int(p.get('idx', 1) or 1)
    currency, price = _get_price(2, idx, 45, 39)
    
    paid = False
    already_owned = user and any(int(x.get('i_id', 0) or 0) == idx for x in user.get('user_music', []))
    if user and not already_owned:
        paid = _deduct_currency(uuid, user, currency, price)
    if paid:
        lst = user.setdefault('user_music', [])
        if not any(int(x.get('i_id', 0) or 0) == idx for x in lst):
            lst.append({'i_id': idx, 'i_Level': 1, 'i_BonusLevel': 0, 'b_EncoreBonusAppear': 0, 'l_EncoreBonusActivateTime': 0, 'i_EncoreBonusFollowerId': 0, 'i_ChThirdActiveTime': 0})
        state.save_user(user)
        
    ud = user['userdata'] if user else {}
    return {
        'u_gold': ud.get('u_candy', 0),
        'u_cp': ud.get('u_cp', 0),
        'u_mp': 0,
        'music': {idx: {'music_idx': idx, 'score1': 0, 'score2': 0, 'score3': 0}} if paid else {}
    }, OK

@cmd('buyAvatar')
def h_buy_avatar(req, player, ctx):
    p = _payload(req)
    user, uuid = _resolve_user_and_id(p, ctx)
    
    idx = p.get('idx', 1)
    currency, price = _get_price(3, idx, 29, 30)
    
    paid = False
    already_owned = user and any(x.get('i_id') == idx for x in user.get('costumes', []))
    if user and not already_owned:
        paid = _deduct_currency(uuid, user, currency, price)
    if paid:
        lst = user.setdefault('costumes', [])
        if not any(x.get('i_id') == idx for x in lst):
            lst.append({'i_id': idx, 'i_Level': 1, 'i_BonusLevel': 0})
        state.save_user(user)
        
    ud = user['userdata'] if user else {}
    return {
        'avatar_idx': idx,
        'u_gold': ud.get('u_candy', 0),
        'u_cp': ud.get('u_cp', 0),
        'u_mp': 0
    }, OK

@cmd('buyItem')
def h_buy_item(req, player, ctx):
    p = _payload(req)
    user, uuid = _resolve_user_and_id(p, ctx)
    
    idx = p.get('idx', 1)
    currency, price = _get_variety_price(idx)
    
    paid = False
    if user:
        paid = _deduct_currency(uuid, user, currency, price)
    if paid:
        state.save_user(user)
        
    ud = user['userdata'] if user else {}
    return {
        'idx': idx,
        'u_gold': ud.get('u_candy', 0),
        'u_cp': ud.get('u_cp', 0),
        'u_mp': 0,
        'u_credit': 0
    }, OK

def _get_upgrade_cost(table_id, item_id, current_level):
    try:
        with open(_GAME_DATA_PATH, 'r', encoding='utf-8') as f:
            gd = json.load(f)
            for row in gd.get(str(table_id), []):
                if str(row.get('1')) == str(item_id):
                    if str(table_id) == '7':
                        # Unit: Table 7
                        # Col 28: GoodsType ('CP')
                        # Col 29: Base Cost
                        # Col 30: Cost Increase Value
                        cur = str(row.get('28', 'CP'))
                        base_cost = int(row.get('29', 200))
                        inc = int(float(row.get('30', 0) or 0))
                        lvl = max(0, int(current_level))
                        # Leveling up from lvl costs Base + lvl * inc
                        cost = base_cost + lvl * inc if lvl > 0 else base_cost
                        return cur, cost
                    elif str(table_id) == '8':
                        # Skill: Table 8
                        # Col 29: GoodsType ('CP')
                        # Col 30: Base Cost
                        # Col 31: Cost Increase Value
                        cur = str(row.get('29', 'CP'))
                        base_cost = int(row.get('30', 100))
                        inc = int(float(row.get('31', 10) or 10))
                        lvl = max(1, int(current_level))
                        cost = base_cost + (lvl - 1) * inc
                        return cur, cost
    except Exception:
        pass
    return 'CP', 100

@cmd('buyContents')
def h_buy_contents(req, player, ctx):
    p = _payload(req)
    user, uuid = _resolve_user_and_id(p, ctx)
    
    ctype = p.get('type', '')
    idx = int(p.get('idx', 1) or 1)
    
    ret = {}
    if user:
        ud = user['userdata']
        
        if ctype == 'unit':
            lst = user.setdefault('user_unit', [])
            item = next((x for x in lst if x.get('i_id') == idx), None)
            cur_lvl = item.get('i_Level', 0) if item else 0
            cur, price = _get_upgrade_cost(7, idx, cur_lvl)
            
            if _deduct_currency(uuid, user, cur, price):
                if item:
                    item['i_Level'] = min(20, cur_lvl + 1)
                else:
                    item = {'i_id': idx, 'i_Level': 1}
                    lst.append(item)
                ret['user_unit'] = item
            
        elif ctype == 'skill':
            lst = user.setdefault('user_skill', [])
            item = next((x for x in lst if x.get('i_id') == idx), None)
            cur_lvl = item.get('i_Level', 1) if item else 1
            max_lvl = 20
            try:
                with open(_GAME_DATA_PATH, 'r', encoding='utf-8') as f:
                    gd = json.load(f)
                    for row in gd.get('8', []):
                        if int(row.get('1', 0)) == idx:
                            max_lvl = int(row.get('28', 20) or 20)
                            break
            except Exception:
                pass
            if cur_lvl >= max_lvl:
                ret['user_skill'] = item
            else:
                cur, price = _get_upgrade_cost(8, idx, cur_lvl)
                if _deduct_currency(uuid, user, cur, price):
                    if item:
                        item['i_Level'] = cur_lvl + 1
                    else:
                        item = {'i_id': idx, 'i_Level': 2, 'i_ActiveTime': 0}
                        lst.append(item)
                    ret['user_skill'] = item

        elif ctype == 'guitar':
            lst = user.setdefault('user_guitar', [])
            item = next((x for x in lst if x.get('i_id') == idx), None)
            cur, price = _get_price(20, idx, 30, 31)
            if not item and _deduct_currency(uuid, user, cur, price):
                item = {'i_id': idx, 'i_Level': 1, 'i_BonusLevel': 0}
                lst.append(item)

        elif ctype == 'costume':
            lst = user.setdefault('costumes', [])
            item = next((x for x in lst if x.get('i_id') == idx), None)
            cur, price = _get_price(3, idx, 29, 30)
            if not item and _deduct_currency(uuid, user, cur, price):
                item = {'i_id': idx, 'i_Level': 1, 'i_BonusLevel': 0}
                lst.append(item)
            
        state.save_user(user)
        ret['u_cp'] = ud.get('u_cp', 0)
        ret['u_candy'] = float(ud.get('u_candy', 0.0))
        
    return ret, OK

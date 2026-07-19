import os
from server import state
from server.handlers.registry import cmd, OK, _payload

# game_data.json lives at emulator/gamedata/ -- resolve absolutely so price lookups don't depend
# on the process CWD (the old relative 'emulator/gamedata/...' silently failed -> flat fallback).
_GAME_DATA_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'gamedata', 'game_data.json')

@cmd('buyVarietyStore')
def h_buy_variety(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    
    idx = p.get('idx', 1)
    currency, price = _get_price(30, idx, 2, 3) 
    
    if user:
        _deduct_currency(uuid, user, currency, price)
        lst = user.setdefault('user_shop', [])
        
        import time
        now = int(time.time())
        item = next((x for x in lst if x.get('i_id') == idx), None)
        if item:
            item['i_Count'] = item.get('i_Count', 0) + 1
            item['i_TotalCount'] = item.get('i_TotalCount', 0) + 1
            item['i_PurchaseTime'] = now
            item['Upd_day'] = now
        else:
            lst.append({'i_id': idx, 'i_Count': 1, 'i_TotalCount': 1, 'i_PurchaseTime': now, 'Upd_day': now})
        
        state.save_user(user)

    ud = user['userdata'] if user else {'u_cp': 0, 'u_candy': 0.0}
    return {'u_cp': ud.get('u_cp', 0), 'u_candy': ud.get('u_candy', 0.0),
            'reward_type': 4, 'reward_id': idx, 'reward_value': 1, 'status': 'Y'}, OK

@cmd('buyCheck')
def h_buy_check(req, player, ctx):
    return {'result': 'Y'}, OK
import json

def _get_price(table_id, item_id, currency_col, price_col):
    try:
        with open(_GAME_DATA_PATH, 'r', encoding='utf-8') as f:
            gd = json.load(f)
            for row in gd.get(str(table_id), []):
                if str(row.get('1')) == str(item_id):
                    currency = str(row.get(str(currency_col), ''))
                    price = int(row.get(str(price_col), 0))
                    return currency, price
    except:
        pass
    return 'GP', 100

def _deduct_currency(uuid, user, currency, price):
    if not user or price <= 0: return
    if 'CP' in currency:
        state.increment_currency(uuid, cp=-price)
        user['userdata']['u_cp'] = user['userdata'].get('u_cp', 0) - price
    else:
        state.increment_currency(uuid, candy=-price)
        user['userdata']['u_candy'] = user['userdata'].get('u_candy', 0.0) - price

@cmd('buyMusic')
def h_buy_music(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    
    idx = p.get('idx', 1)
    currency, price = _get_price(2, idx, 45, 46)
    
    if user:
        _deduct_currency(uuid, user, currency, price)
        lst = user.setdefault('user_music', [])
        if not any(x.get('i_id') == idx for x in lst):
            lst.append({'i_id': idx, 'i_Level': 1, 'i_BonusLevel': 0, 'b_EncoreBonusAppear': 0, 'l_EncoreBonusActivateTime': 0, 'i_EncoreBonusFollowerId': 0, 'i_ChThirdActiveTime': 0})
        state.save_user(user)
        
    ud = user['userdata'] if user else {}
    return {
        'u_gold': ud.get('u_candy', 0),
        'u_cp': ud.get('u_cp', 0),
        'u_mp': 0,
        'music': {'i_id': idx, 'i_Level': 1, 'i_BonusLevel': 0}
    }, OK

@cmd('buyAvatar')
def h_buy_avatar(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    
    idx = p.get('idx', 1)
    currency, price = _get_price(3, idx, 29, 44)
    
    if user:
        _deduct_currency(uuid, user, currency, price)
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
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    
    idx = p.get('idx', 1)
    currency, price = _get_price(30, idx, 3, 4) # fallback
    
    if user:
        _deduct_currency(uuid, user, currency, price)
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
                        return str(row.get('28', 'CP')), int(row.get('29', 200)) + (current_level - 1) * int(row.get('31', 30))
                    elif str(table_id) == '8':
                        return str(row.get('29', 'CP')), int(row.get('30', 100)) + (current_level - 1) * int(row.get('31', 10))
    except:
        pass
    return 'CP', 100

@cmd('buyContents')
def h_buy_contents(req, player, ctx):
    p = _payload(req)
    uuid = p.get('uuid') or ctx.get('uuid')
    user = state.get_user(uuid)
    
    ctype = p.get('type', '')
    idx = p.get('idx', 1)
    
    ret = {}
    if user:
        ud = user['userdata']
        
        if ctype == 'unit':
            lst = user.setdefault('user_unit', [])
            item = next((x for x in lst if x.get('i_id') == idx), None)
            cur_lvl = item.get('i_Level', 1) if item else 1
            cur, price = _get_upgrade_cost(7, idx, cur_lvl)
            
            _deduct_currency(uuid, user, cur, price)
            if item:
                item['i_Level'] = cur_lvl + 1
            else:
                item = {'i_id': idx, 'i_Level': 2}
                lst.append(item)
            ret['user_unit'] = item
            
        elif ctype == 'skill':
            lst = user.setdefault('user_skill', [])
            item = next((x for x in lst if x.get('i_id') == idx), None)
            cur_lvl = item.get('i_Level', 1) if item else 1
            cur, price = _get_upgrade_cost(8, idx, cur_lvl)
            
            _deduct_currency(uuid, user, cur, price)
            if item:
                item['i_Level'] = cur_lvl + 1
            else:
                item = {'i_id': idx, 'i_Level': 2, 'i_ActiveTime': 0}
                lst.append(item)
            ret['user_skill'] = item
            
        state.save_user(user)
        ret['u_cp'] = ud.get('u_cp', 0)
        ret['u_candy'] = ud.get('u_candy', 0.0)
        
    return ret, OK

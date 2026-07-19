import time, datetime
from server.handlers.registry import cmd, OK

def _server_time(tz_offset_hours=9):  # Asia/Seoul = UTC+9
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=tz_offset_hours)
    return {'time': int(time.time()), 'datetime': int(now.strftime('%Y%m%d%H%M%S'))}

@cmd('Request')   # init / routing
def h_init(req, player, ctx):
    return {'idx': 253, 'game_url': ctx['game_url'], 'cdn_url': ctx['cdn_url']}, OK

@cmd('getServerTime')
def h_server_time(req, player, ctx):
    return _server_time(), OK

@cmd('getUpdateTime')
def h_update_time(req, player, ctx):
    return {'upd_time': 1761876067}, OK

@cmd('defaultSettingList')
def h_default_settings(req, player, ctx):
    settings = [
        ('shop_call_wait', '2'), ('ad_cancel_delay', '5'), ('force_menu_restric', 'true'),
        ('max_bundle_texutre_loading', '1'), ('weather_snow', 'true'), ('check_time_cheat', 'false'),
        ('ap_max', '60'), ('ap_time', '300'), ('ap_use', '5'), ('character_exp', '45'),
        ('ap_shop_id', '31'), ('ap_ad_list_id', '2'), ('ch_third_unlock_follower_id', '5'),
        ('ch_third_unlock_follower_level', '1'), ('ad_follower_profile_exp_persent', '0.1'),
        ('follower_profile_bonus_percent', '1'), ('spine_load_max_count', '0'), ('log_flag', 'true'),
        ('weather_cherry_blossom', 'false'), ('active_goods_ticket_buff', 'true'),
        ('active_fan_art_costume', 'true'), ('pass_goods_sale_start_time', '2022-02-19 00:00'),
        ('pass_goods_sale_end_time', '2999-02-27 23:59'), ('attendacne_buff_value', '0.01'),
        ('attendacne_buff_limit_day', '10000'), ('log_flag_unfinished_purchase', 'true'),
        ('jp_laws_flag', 'true'),
    ]
    return {'status': 'Y',
            'setting_list': [{'setting_key': k, 'setting_value': v} for k, v in settings]}, OK

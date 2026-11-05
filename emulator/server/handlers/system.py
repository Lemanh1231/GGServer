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

# Fixed master-table revision timestamp (2023-11-14).
# Must remain > 0 (so a fresh install with local_uptime=0 downloads getGameDataList once)
# and constant/<= existing local_uptime so RunPatchProcess (0x1d0de34) does NOT enter
# CoDownloadTableFromServer (State 7) before CoLoadUserTableFromPrefab (State 9).
# Returning int(time.time()) here forced CoDownloadTableFromServer -> ReqGetVarietyStore ->
# premature userLogin BEFORE PlayerPrefs were loaded into memory (m_dicData.Count == 0),
# causing CheckIntegrity (0x204ab0c) to fail and overwrite local PlayerPrefs level-ups
# with old server data, as well as racing with State 10 RunLogin and hanging at startup.
GAME_DATA_UPD_TIME = 1700000000

@cmd('getUpdateTime')
def h_update_time(req, player, ctx):
    return {'upd_time': GAME_DATA_UPD_TIME}, OK

from server import event_manager

@cmd('defaultSettingList')
def h_default_settings(req, player, ctx):
    snow_val = 'true' if event_manager.is_weather_snow_enabled() else 'false'
    cherry_val = 'true' if event_manager.is_weather_cherry_blossom_enabled() else 'false'
    fan_art_val = 'true' if event_manager.is_fan_art_costume_enabled() else 'false'
    sale_end_val = '2999-12-31 23:59' if event_manager.is_pass_goods_sale_enabled() else '2020-01-01 00:00'

    settings = [
        ('shop_call_wait', '2'), ('ad_cancel_delay', '0'), ('force_menu_restric', 'true'),
        ('max_bundle_texutre_loading', '1'), ('weather_snow', snow_val), ('check_time_cheat', 'false'),
        ('ap_max', '70'), ('ap_time', '300'), ('ap_use', '5'), ('character_exp', '45'),
        ('ap_shop_id', '31'), ('ap_ad_list_id', '2'), ('ch_third_unlock_follower_id', '5'),
        ('ch_third_unlock_follower_level', '1'), ('ad_follower_profile_exp_persent', '0.1'),
        ('follower_profile_bonus_percent', '1'), ('spine_load_max_count', '0'), ('log_flag', 'true'),
        ('weather_cherry_blossom', cherry_val), ('active_goods_ticket_buff', 'true'),
        ('active_fan_art_costume', fan_art_val),
        ('pass_goods_sale_start_time', '2020-01-01 00:00'),
        ('pass_goods_sale_end_time', sale_end_val), ('attendacne_buff_value', '0.01'),
        ('attendacne_buff_limit_day', '10000'), ('log_flag_unfinished_purchase', 'true'),
        ('jp_laws_flag', 'true'),
    ]
    return {'status': 'Y',
            'setting_list': [{'setting_key': k, 'setting_value': v} for k, v in settings]}, OK

@cmd('hibernationLog')
def h_hibernation_log(req, player, ctx):
    return {'action': 0}, OK

@cmd('completeLog')
def h_complete_log(req, player, ctx):
    return {'status': '1'}, OK

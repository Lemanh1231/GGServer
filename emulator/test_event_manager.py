"""Unit tests for Event Manager, Hot-Reload, and Admin Web Dashboard API."""
import unittest
import json
import urllib.request
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))
from server import event_manager, state
import copy
from server.handlers import reward, auth, event_mode, ch_third


class TestEventManager(unittest.TestCase):
    def setUp(self):
        # Save a deep backup of current config
        self.original_config = copy.deepcopy(event_manager.load_event_config())

    def tearDown(self):
        # Restore original config after test
        event_manager.save_event_config(self.original_config)

    def test_attendance_event_hot_reload(self):
        """Attendance events can be enabled/disabled instantly without restart."""
        # Enable Event 2 (Anniversary)
        event_manager.set_attendance_event_enabled(2, True)
        self.assertTrue(event_manager.is_attendance_event_enabled(2))
        data, err = reward.h_get_event_reward_list({'uuid': 'test_u'}, None, {'uuid': 'test_u'})
        self.assertIn(2, data)

        # Disable Event 2
        event_manager.set_attendance_event_enabled(2, False)
        self.assertFalse(event_manager.is_attendance_event_enabled(2))
        data2, err2 = reward.h_get_event_reward_list({'uuid': 'test_u'}, None, {'uuid': 'test_u'})
        self.assertNotIn(2, data2)

    def test_star_pass_season_switching(self):
        """Star Pass season can be switched between 1 and 13 dynamically."""
        user = {'userdata': {'u_seq': 1}}
        event_manager.set_star_pass(enabled=True, season=7, paid_gold=False)
        self.assertEqual(event_manager.get_active_star_pass_season(), 7)

        evp = auth._normalise_event_points(user)
        pass_entry = next((e for e in evp if e.get('s_EventType') == 'Pass'), None)
        self.assertIsNotNone(pass_entry)
        self.assertEqual(pass_entry.get('i_DataID'), 7)
        self.assertEqual(pass_entry.get('i_Version'), reward._get_pass_version(7))

        # Switch to Season 13
        event_manager.set_star_pass(season=13)
        self.assertEqual(event_manager.get_active_star_pass_season(), 13)
        evp2 = auth._normalise_event_points(user)
        self.assertEqual(evp2[0].get('i_DataID'), 13)

    def test_star_pass_gold_entitlement(self):
        """When Star Pass Gold is enabled, player gets Gold entitlement."""
        user = {'userdata': {'u_seq': 1}}
        event_manager.set_star_pass(enabled=True, season=13, paid_gold=True)
        self.assertTrue(event_manager.is_paid_star_card_enabled())

        subs = auth._normalise_subscribe_list(user)
        paid_sub = next((s for s in subs if s.get('i_SubscribeID') == 13), None)
        self.assertIsNotNone(paid_sub)
        self.assertEqual(paid_sub.get('i_isActive'), 1)

        # Disable gold
        event_manager.set_star_pass(paid_gold=False)
        self.assertFalse(event_manager.is_paid_star_card_enabled())
        subs2 = auth._normalise_subscribe_list(user)
        paid_sub2 = next((s for s in subs2 if s.get('i_SubscribeID') == 13), None)
        self.assertIsNone(paid_sub2, "Unsubscribed pass must be removed from user_subscribe_list")

    def test_meowfest_hot_reload(self):
        """Meowfest event can be toggled on and off."""
        event_manager.set_meowfest_enabled(True)
        res_on, _ = event_mode.h_get_samseck_list({}, None, {})
        self.assertEqual(len(res_on.get('rewardList', [])), 3)

        event_manager.set_meowfest_enabled(False)
        res_off, _ = event_mode.h_get_samseck_list({}, None, {})
        self.assertEqual(len(res_off.get('rewardList', [])), 0)

    def test_chapter3_tour_hot_reload(self):
        """Chapter 3 Tour stages can be toggled on and off."""
        u = state.create_user('test_ch3_u', 'test_ch3_u')
        event_manager.set_chapter3_tour_enabled(True)
        res_on, err_on = ch_third.h_get_ch_third({'uuid': 'test_ch3_u'}, None, {'uuid': 'test_ch3_u'})
        self.assertEqual(err_on.get('code'), 0)
        self.assertTrue(len(res_on.get('user_ch_third_stage', [])) >= 1)

        event_manager.set_chapter3_tour_enabled(False)
        res_off, err_off = ch_third.h_get_ch_third({'uuid': 'test_ch3_u'}, None, {'uuid': 'test_ch3_u'})
        self.assertEqual(err_off.get('code'), 1)
        state.delete_user('test_ch3_u')

    def test_admin_api_via_http(self):
        """Verify Admin Web Dashboard and API routes work via HTTP."""
        admin_auth_hdr = {'Authorization': 'Bearer Stingdau@1231@@'}

        # GET /admin without auth -> shows login page
        req_unauth = urllib.request.Request('http://127.0.0.1:8080/admin')
        with urllib.request.urlopen(req_unauth) as resp:
            self.assertEqual(resp.status, 200)
            body_unauth = resp.read().decode('utf-8')
            self.assertIn('Đăng nhập Quản trị', body_unauth)

        # GET /admin with auth -> shows admin dashboard
        req = urllib.request.Request('http://127.0.0.1:8080/admin', headers=admin_auth_hdr)
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            body = resp.read().decode('utf-8')
            self.assertIn('Guitar Girl', body)
            self.assertIn('Trung Tâm Quản Trị', body)

        # GET /admin/api/events with auth
        req_api = urllib.request.Request('http://127.0.0.1:8080/admin/api/events', headers=admin_auth_hdr)
        with urllib.request.urlopen(req_api) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertTrue(data.get('success'))
            self.assertEqual(len(data.get('seasons', [])), 13)

        # POST /admin/api/events with auth
        post_data = copy.deepcopy(self.original_config)
        post_data['attendance_events']['2']['enabled'] = True
        body_bytes = json.dumps(post_data).encode('utf-8')
        post_headers = {'Content-Type': 'application/json', **admin_auth_hdr}
        req_post = urllib.request.Request(
            'http://127.0.0.1:8080/admin/api/events',
            data=body_bytes,
            headers=post_headers
        )
        with urllib.request.urlopen(req_post) as resp:
            self.assertEqual(resp.status, 200)
            ret = json.loads(resp.read().decode('utf-8'))
            self.assertTrue(ret.get('success'))
            self.assertTrue(event_manager.is_attendance_event_enabled(2))

        # Restore immediately to prevent leaving Event 2 active on live server
        event_manager.save_event_config(self.original_config)

    def test_pass_goods_sale_and_weather_toggling(self):
        """Pass goods sale, weather, and fan art costume reflect in defaultSettingList."""
        from server.handlers import system

        # Enable goods sale, snow, fan art, disable cherry
        event_manager.set_pass_goods_sale_enabled(True)
        event_manager.set_weather_festival(snow=True, cherry_blossom=False)
        event_manager.set_fan_art_costume_enabled(True)

        res, err = system.h_default_settings({}, None, {})
        s_map = {item['setting_key']: item['setting_value'] for item in res['setting_list']}
        self.assertEqual(s_map['pass_goods_sale_end_time'], '2999-12-31 23:59')
        self.assertEqual(s_map['weather_snow'], 'true')
        self.assertEqual(s_map['weather_cherry_blossom'], 'false')
        self.assertEqual(s_map['active_fan_art_costume'], 'true')

        # Disable goods sale and snow, enable cherry
        event_manager.set_pass_goods_sale_enabled(False)
        event_manager.set_weather_festival(snow=False, cherry_blossom=True)
        event_manager.set_fan_art_costume_enabled(False)

        res2, _ = system.h_default_settings({}, None, {})
        s_map2 = {item['setting_key']: item['setting_value'] for item in res2['setting_list']}
        self.assertEqual(s_map2['pass_goods_sale_end_time'], '2020-01-01 00:00')
        self.assertEqual(s_map2['weather_snow'], 'false')
        self.assertEqual(s_map2['weather_cherry_blossom'], 'true')
        self.assertEqual(s_map2['active_fan_art_costume'], 'false')

    def test_event_ranking_handlers(self):
        """Event ranking getEventMain, getEventRank, eventRewardList return correct structures."""
        # Enabled
        event_manager.set_event_ranking_enabled(True)
        main_res, err_main = event_mode.h_get_event_main({'uuid': 'test_u'}, None, {'uuid': 'test_u'})
        self.assertEqual(err_main.get('code'), 0)
        self.assertEqual(main_res.get('idx'), 1)
        self.assertIn('title', main_res)

        rank_res, err_rank = event_mode.h_get_event_rank({'uuid': 'test_u'}, None, {'uuid': 'test_u'})
        self.assertEqual(err_rank.get('code'), 0)
        self.assertTrue(len(rank_res) >= 1)
        self.assertEqual(rank_res[0].get('rank'), 1)

        rew_res, err_rew = event_mode.h_event_reward_list({}, None, {})
        self.assertEqual(err_rew.get('code'), 0)
        self.assertEqual(rew_res.get('event_idx'), 1)
        self.assertTrue(len(rew_res.get('reward_list', [])) >= 1)

        # Disabled
        event_manager.set_event_ranking_enabled(False)
        _, err_dis = event_mode.h_get_event_main({}, None, {})
        self.assertEqual(err_dis.get('code'), 1)
        _, err_rank_dis = event_mode.h_get_event_rank({}, None, {})
        self.assertEqual(err_rank_dis.get('code'), 1)


if __name__ == '__main__':
    unittest.main()

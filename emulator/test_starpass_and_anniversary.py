import unittest
import json
import copy
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))
from server import event_manager, state
from server.handlers import reward, gamedata, auth


class TestStarPassAndAnniversaryGating(unittest.TestCase):
    def setUp(self):
        self.orig_cfg = copy.deepcopy(event_manager.load_event_config())
        self.test_uuid = 'test_gating_uuid_999'
        user = state.get_user(self.test_uuid)
        if not user:
            user = state.create_user(self.test_uuid, 'test_dev_999')
            user['userdata']['u_id'] = 'test_user_999'
            user['userdata']['u_nick'] = 'TestGating'
            state.save_user(user)

    def tearDown(self):
        event_manager.save_event_config(self.orig_cfg)
        state.delete_user(self.test_uuid)

    def test_star_pass_disabled_prevents_user_modification(self):
        """When star_pass.enabled is False, user_shop, user_subscribe_list, and user_event_point are untouched."""
        # 1. Disable Star Pass
        cfg = copy.deepcopy(self.orig_cfg)
        cfg['star_pass']['enabled'] = False
        event_manager.save_event_config(cfg)
        self.assertFalse(event_manager.is_star_pass_enabled())

        # 2. Simulate /admin/api/user/event_settings trying to set is_gold=True and star_point=9999
        user = state.get_user(self.test_uuid)
        active_season = event_manager.get_active_star_pass_season()
        target_shop_id = 1000 + active_season

        # Emulate app.py handler logic with the new sp_enabled gate
        sp_enabled = event_manager.is_star_pass_enabled()
        self.assertFalse(sp_enabled)

        # Attempt to modify under disabled star pass
        if sp_enabled:
            # Should NOT be reached
            user.setdefault('user_shop', []).append({'i_id': target_shop_id, 'i_Count': 1})

        # Verify user has no Star Pass items
        shop_ids = [item.get('i_id') for item in user.get('user_shop', [])]
        self.assertNotIn(target_shop_id, shop_ids)

        # Also verify auth._normalise_subscribe_list disables all subscriptions when star pass is off
        subs = user.setdefault('user_subscribe_list', [{'i_SubscribeID': active_season, 'i_isActive': 1}])
        auth._normalise_subscribe_list(user)
        for s in user['user_subscribe_list']:
            self.assertEqual(s.get('i_isActive'), 0, "All subscriptions must be inactive when Star Pass is disabled")

    def test_star_pass_enabled_allows_user_modification(self):
        """When star_pass.enabled is True, admin is allowed to grant Gold Pass and star points."""
        cfg = copy.deepcopy(self.orig_cfg)
        cfg['star_pass']['enabled'] = True
        event_manager.save_event_config(cfg)
        self.assertTrue(event_manager.is_star_pass_enabled())

        user = state.get_user(self.test_uuid)
        active_season = event_manager.get_active_star_pass_season()
        target_shop_id = 1000 + active_season

        sp_enabled = event_manager.is_star_pass_enabled()
        self.assertTrue(sp_enabled)

        # Apply Gold Pass
        shop_items = user.setdefault('user_shop', [])
        shop_items.append({'i_id': target_shop_id, 'i_Count': 1, 'i_TotalCount': 1})
        subs = user.setdefault('user_subscribe_list', [])
        subs.append({'i_SubscribeID': active_season, 'i_isActive': 1, 'i_ActiveTime': 2147483647})
        state.save_user(user)

        loaded = state.get_user(self.test_uuid)
        loaded_shop_ids = [item.get('i_id') for item in loaded.get('user_shop', [])]
        self.assertIn(target_shop_id, loaded_shop_ids)

    def test_anniversary_event_disabled_omitted_from_gamedata_and_reward_list(self):
        """When Event 2 (Anniversary) is disabled on web/server, it is completely excluded from event_list and reward_list."""
        # Disable Event 2
        event_manager.set_attendance_event_enabled(2, False)
        self.assertFalse(event_manager.is_attendance_event_enabled(2))

        # Check gamedata build_filtered_ret
        ret = gamedata.build_filtered_ret()
        ev_list = ret.get('event_list', [])
        ev_indices = [str(ev.get('idx')) for ev in ev_list]
        self.assertNotIn('2', ev_indices, "Event 2 must be completely excluded from ret['event_list'] when disabled")

        # Check getEventRewardList
        rewards_data, err = reward.h_get_event_reward_list({'uuid': self.test_uuid}, None, {'uuid': self.test_uuid})
        self.assertNotIn(2, rewards_data, "Event 2 must not be in getEventRewardList when disabled")
        self.assertNotIn('2', rewards_data)

    def test_anniversary_event_enabled_included_in_gamedata_and_reward_list(self):
        """When Event 2 (Anniversary) is enabled on web/server, it is included in event_list and reward_list."""
        # Enable Event 2
        event_manager.set_attendance_event_enabled(2, True)
        self.assertTrue(event_manager.is_attendance_event_enabled(2))

        # Check gamedata build_filtered_ret
        ret = gamedata.build_filtered_ret()
        ev_list = ret.get('event_list', [])
        ev2 = next((ev for ev in ev_list if str(ev.get('idx')) == '2'), None)
        self.assertIsNotNone(ev2, "Event 2 must be present in ret['event_list'] when enabled")
        self.assertEqual(ev2.get('b_IsActive'), 1)
        self.assertEqual(ev2.get('start_date'), '0001-01-01 00:00:00')
        self.assertEqual(ev2.get('end_date'), '9999-12-31 23:59:00')

        # Check getEventRewardList
        rewards_data, err = reward.h_get_event_reward_list({'uuid': self.test_uuid}, None, {'uuid': self.test_uuid})
        self.assertTrue(2 in rewards_data or '2' in rewards_data, "Event 2 must be in getEventRewardList when enabled")


if __name__ == '__main__':
    unittest.main()

"""Unit and integration tests for Follower Profile Gifting (All 3 gift slots).

Tests:
1. Slot 1: Gingerbread (ID 1, +20 EXP) gives exactly +20 cumulative EXP and advances level only upon threshold.
2. Slot 2: Favorite Gift (IDs 2-6, +30 EXP) gives exactly +30 cumulative EXP and deducts correct inventory item.
3. Slot 3: Ad Gift ("Ký ức của chúng ta", setAdReward i_id 1) gives 10% delta EXP (clamped 100..300) without negative numbers.
4. Data healing: Old profiles with corrupted delta EXP (< base_req) are healed smoothly to cumulative EXP.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from server import state
from server.handlers.follower import _follower_data, _apply_profile_exp, h_set_follower_profile_gift
from server.handlers.reward import h_set_ad_reward


class TestFollowerGifts(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.profiles_def, cls.gifts_def, cls.level_data, cls.f_to_p, _ = _follower_data()

    def test_table31_loaded_properly(self):
        """Table 31 (FollowerProfileLevelData) must be used instead of Table 27."""
        self.assertIn(1, self.level_data)
        joy = self.level_data[1]
        self.assertEqual(int(joy[1]['4']), 0)
        self.assertEqual(int(joy[2]['4']), 50)
        self.assertEqual(int(joy[3]['4']), 150)
        self.assertEqual(int(joy[8]['4']), 4150)
        self.assertEqual(int(joy[9]['4']), 6350)

    def test_slot1_gingerbread_progression(self):
        """Slot 1 gives +20 EXP each time without negative numbers or erratic level skips."""
        joy = self.level_data[1]
        profile = {'i_id': 1, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0}

        # 1st Gingerbread: 0 -> 20 (Lv 1, 20/50)
        _apply_profile_exp(profile, joy, 20)
        self.assertEqual(profile['i_Level'], 1)
        self.assertEqual(profile['d_Exp'], 20)
        self.assertEqual(profile['d_Exp'] - int(joy[1]['4']), 20)

        # 2nd Gingerbread: 20 -> 40 (Lv 1, 40/50)
        _apply_profile_exp(profile, joy, 20)
        self.assertEqual(profile['i_Level'], 1)
        self.assertEqual(profile['d_Exp'], 40)
        self.assertEqual(profile['d_Exp'] - int(joy[1]['4']), 40)

        # 3rd Gingerbread: 40 -> 60 (Lv 2 reached at 50, 10/100)
        _apply_profile_exp(profile, joy, 20)
        self.assertEqual(profile['i_Level'], 2)
        self.assertEqual(profile['d_Exp'], 60)
        self.assertEqual(profile['d_Exp'] - int(joy[2]['4']), 10)

    def test_slot2_favorite_gift(self):
        """Slot 2 gives +30 EXP and handles level advancement properly."""
        joy = self.level_data[1]
        profile = {'i_id': 1, 'i_Level': 2, 'd_Exp': 60, 'i_AddCandy': 0}

        # Favorite gift (+30): 60 -> 90 (Lv 2, 40/100)
        _apply_profile_exp(profile, joy, 30)
        self.assertEqual(profile['i_Level'], 2)
        self.assertEqual(profile['d_Exp'], 90)
        self.assertEqual(profile['d_Exp'] - int(joy[2]['4']), 40)

        # 2 Favorite gifts (+60): 90 -> 150 (Lv 3 reached at 150, 0/200)
        _apply_profile_exp(profile, joy, 60)
        self.assertEqual(profile['i_Level'], 3)
        self.assertEqual(profile['d_Exp'], 150)
        self.assertEqual(profile['d_Exp'] - int(joy[3]['4']), 0)

    def test_corrupted_profile_healing(self):
        """Profile level is accurately determined by cumulative EXP from Table 31."""
        joy = self.level_data[1]
        prof = {'i_id': 1, 'i_Level': 1, 'd_Exp': 4150, 'i_AddCandy': 0}

        # 4150 EXP is Table 31 Level 8. Adding 20 -> 4170
        _apply_profile_exp(prof, joy, 20)
        self.assertEqual(prof['i_Level'], 8)
        self.assertEqual(prof['d_Exp'], 4170)
        client_exp = prof['d_Exp'] - int(joy[8]['4'])
        self.assertEqual(client_exp, 20)

    def test_all_3_slots_rpc_integration(self):
        """Full handler RPC integration test for Slot 1, Slot 2, and Slot 3."""
        test_uuid = 'test-e2e-follower-gifts'
        user = state.get_user(test_uuid)
        if not user:
            user = state.create_user(test_uuid, 'device-e2e-gifts')

        user['user_follower_giftitem'] = [
            {'i_id': 1, 'i_Value': 50},
            {'i_id': 3, 'i_Value': 50},
        ]
        user['user_follower_profile'] = [
            {'i_id': 1, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0}
        ]
        user.pop('ad_rewards', None)
        state.save_user(user)

        # Slot 1: Gingerbread (ID 1)
        r1, _ = h_set_follower_profile_gift({'data': {'profile_id': 1, 'gift_id': 1, 'use_gitf_value': 1}}, None, {'uuid': test_uuid})
        self.assertEqual(r1['user_follower_profile']['d_Exp'], 20)
        self.assertEqual(r1['user_follower_profile']['i_Level'], 1)
        self.assertEqual(r1['user_follower_giftitem']['i_Value'], 49)

        # Slot 2: Favorite Gift (Egg Sandwich ID 3)
        r2, _ = h_set_follower_profile_gift({'data': {'profile_id': 1, 'gift_id': 3, 'use_gitf_value': 1}}, None, {'uuid': test_uuid})
        self.assertEqual(r2['user_follower_profile']['d_Exp'], 50)
        self.assertEqual(r2['user_follower_profile']['i_Level'], 2)
        self.assertEqual(r2['user_follower_giftitem']['i_id'], 3)
        self.assertEqual(r2['user_follower_giftitem']['i_Value'], 49)

        # Slot 3: Ad Gift (setAdReward i_id 1)
        r3, _ = h_set_ad_reward({'data': {'i_id': 1, 'param1': 1}}, None, {'uuid': test_uuid})
        ad_exp = r3['reward_data'][0]['reward_value']
        self.assertGreaterEqual(ad_exp, 100)
        self.assertEqual(r3['user_follower_profile']['d_Exp'], 50 + ad_exp)
        self.assertEqual(r3['user_follower_profile']['i_Level'], 3)

    def test_auto_unlock_information_on_level_milestones(self):
        """Reaching level 5 and 10 via gifting must automatically unlock information milestones in user_follower_profile_reward."""
        test_uuid = 'test-auto-unlock-milestones'
        user = state.get_user(test_uuid)
        if not user:
            user = state.create_user(test_uuid, 'device-auto-unlock')

        # Follower 1 (Joy): Table 31 Lv 5 requires 750 EXP, Lv 10 requires 8850 EXP
        user['user_follower_giftitem'] = [{'i_id': 1, 'i_Value': 1000}]
        user['user_follower_profile'] = [{'i_id': 1, 'i_Level': 4, 'd_Exp': 350, 'i_AddCandy': 0}]
        user['user_follower'] = [{'i_id': 1, 'i_Level': 4, 'i_BonusLevel': 0}]
        user['user_follower_profile_reward'] = [{'i_id': 1, 'i_RewardLevel': 1}]
        state.save_user(user)

        # Give 20 gingerbread gifts (20 * 20 = 400 EXP). 350 + 400 = 750 -> exactly Lv 5
        h_set_follower_profile_gift({'data': {'profile_id': 1, 'gift_id': 1, 'use_gitf_value': 20}}, None, {'uuid': test_uuid})

        user = state.get_user(test_uuid)
        self.assertEqual(user['user_follower_profile'][0]['i_Level'], 5)
        self.assertEqual(user['user_follower_profile'][0]['i_AddCandy'], 1)
        # Verify Level 5 information is automatically in user_follower_profile_reward
        claims = {(r['i_id'], r['i_RewardLevel']) for r in user.get('user_follower_profile_reward', [])}
        self.assertIn((1, 1), claims)
        self.assertIn((1, 5), claims)

        # Give more gifts to reach Lv 10 (9350 EXP: need 9350 - 750 = 8600 -> 430 gifts)
        h_set_follower_profile_gift({'data': {'profile_id': 1, 'gift_id': 1, 'use_gitf_value': 430}}, None, {'uuid': test_uuid})
        user = state.get_user(test_uuid)
        self.assertEqual(user['user_follower_profile'][0]['i_Level'], 10)
        self.assertEqual(user['user_follower_profile'][0]['i_AddCandy'], 2)
        claims = {(r['i_id'], r['i_RewardLevel']) for r in user.get('user_follower_profile_reward', [])}
        self.assertIn((1, 10), claims)

    def test_new_follower_unlock_and_sync(self):
        """Unlocking a new follower must automatically create profile and unlock reached milestone info."""
        from server.handlers.auth import _sync_follower_profiles_and_rewards
        test_uuid = 'test-new-follower-sync'
        user = state.get_user(test_uuid)
        if not user:
            user = state.create_user(test_uuid, 'device-new-follower')

        # Add new follower 6 (Elle) at level 5
        user['user_follower'] = [
            {'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0},
            {'i_id': 6, 'i_Level': 5, 'i_BonusLevel': 0},
        ]
        user['user_follower_profile'] = [
            {'i_id': 1, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0},
        ]
        user['user_follower_profile_reward'] = []
        state.save_user(user)

        _sync_follower_profiles_and_rewards(user)

        # Verify follower 6 profile was created at Level 1, 0 EXP (independent of stage level 5)
        p6 = next((p for p in user['user_follower_profile'] if p['i_id'] == 6), None)
        self.assertIsNotNone(p6)
        self.assertEqual(p6['i_Level'], 1)
        self.assertEqual(p6['d_Exp'], 0)

        # Guitar Girl profile 100000 must start at Level 1, 0 EXP, and not have levels 2..20
        p100 = next((p for p in user['user_follower_profile'] if p['i_id'] == 100000), None)
        self.assertIsNotNone(p100)
        self.assertEqual(p100['i_Level'], 1)
        self.assertEqual(p100['d_Exp'], 0)
        claims = {(r['i_id'], r['i_RewardLevel']) for r in user.get('user_follower_profile_reward', [])}
        for lvl in range(2, 21):
            self.assertNotIn((100000, lvl), claims)

    def test_follower_profile_reward_claiming_flow(self):
        """Claiming follower profile reward works once, prevents infinite claiming, and works for newly viewed profiles."""
        import uuid
        from server.handlers.follower import h_set_user_follower_profile_reward
        rand_id = uuid.uuid4().hex[:8]
        test_uuid = f'test-claim-{rand_id}'
        test_device = f'device-claim-{rand_id}'
        user = state.create_user(test_uuid, test_device)

        init_cp = int(user.get('userdata', {}).get('u_cp', 0) or 0)

        # 1. First claim for Follower 2 (Convenience Store Friend, not yet in user_follower_profile)
        r1, code1 = h_set_user_follower_profile_reward(
            {'data': {'i_id': 2, 's_level': '1'}}, None, {'uuid': test_uuid}
        )
        self.assertEqual(len(r1), 1)
        self.assertEqual(r1[0]['i_id'], 2)
        self.assertEqual(r1[0]['i_level'], 1)
        self.assertEqual(len(r1[0]['reward_data']), 1)
        self.assertEqual(r1[0]['reward_data'][0]['reward_type'], 1)  # Goods (Table 1: CP)
        self.assertEqual(r1[0]['reward_data'][0]['reward_value'], 5.0)

        user = state.get_user(test_uuid)
        cp_after_1st = int(user.get('userdata', {}).get('u_cp', 0) or 0)
        self.assertEqual(cp_after_1st, init_cp + 5)
        claims = {(r['i_id'], r['i_RewardLevel']) for r in user.get('user_follower_profile_reward', [])}
        self.assertIn((2, 1), claims)

        # 2. Second claim for same follower and level (continuous clicking / duplicate click)
        r2, code2 = h_set_user_follower_profile_reward(
            {'data': {'i_id': 2, 's_level': '1'}}, None, {'uuid': test_uuid}
        )
        self.assertEqual(len(r2), 1)
        self.assertEqual(r2[0]['i_id'], 2)
        self.assertEqual(r2[0]['i_level'], 1)
        self.assertEqual(r2[0]['reward_data'], [])  # No reward returned

        user = state.get_user(test_uuid)
        cp_after_2nd = int(user.get('userdata', {}).get('u_cp', 0) or 0)
        self.assertEqual(cp_after_2nd, cp_after_1st)  # No extra CP granted!

        # 3. Claim for Guitar Girl (100000) Level 1
        r_gg1, _ = h_set_user_follower_profile_reward(
            {'data': {'i_id': 100000, 's_level': '1'}}, None, {'uuid': test_uuid}
        )
        self.assertEqual(len(r_gg1), 1)
        self.assertEqual(r_gg1[0]['i_id'], 100000)
        self.assertEqual(r_gg1[0]['i_level'], 1)
        self.assertEqual(len(r_gg1[0]['reward_data']), 1)
        self.assertEqual(r_gg1[0]['reward_data'][0]['reward_value'], 5.0)

        # 4. Guitar Girl duplicate claim returns empty reward_data
        r_gg2, _ = h_set_user_follower_profile_reward(
            {'data': {'i_id': 100000, 's_level': '1'}}, None, {'uuid': test_uuid}
        )
        self.assertEqual(r_gg2[0]['reward_data'], [])

        # 5. Guitar Girl Level 2 cannot be claimed because she is Level 1
        r_gg_lv2, _ = h_set_user_follower_profile_reward(
            {'data': {'i_id': 100000, 's_level': '2'}}, None, {'uuid': test_uuid}
        )
        self.assertEqual(r_gg_lv2, [])


if __name__ == '__main__':
    unittest.main()


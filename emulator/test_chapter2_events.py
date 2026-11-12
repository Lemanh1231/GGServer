"""Tests for Chapter 2 (Happy Bakery / Tiệm bánh Hạnh phúc) events and skills."""
import unittest
import time
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from server import state
from server.handlers import reward, auth


class TestChapter2Events(unittest.TestCase):
    def setUp(self):
        self.dev_uuid = f'test_ch2_dev_{int(time.time()*1000)}'
        self.user = state.create_user(self.dev_uuid, self.dev_uuid)
        self.ctx = {'uuid': self.dev_uuid}

    def tearDown(self):
        state.delete_user(self.dev_uuid)

    def test_happy_bakery_daily_attendance_reward_list(self):
        """getEventRewardList returns Event 3 (DailyAttendance / Happy Bakery)."""
        data, err = reward.h_get_event_reward_list({'uuid': self.dev_uuid}, None, self.ctx)
        self.assertEqual(err.get('code'), 0)
        self.assertTrue(3 in data or '3' in data, "Event 3 (DailyAttendance) must be present in reward list")
        ev3 = data.get(3) or data.get('3')
        rewards = ev3.get('reward_list', [])
        self.assertEqual(len(rewards), 7, "Event 3 must have 7 days of rewards")
        # Day 1 reward is AP / Cookies
        self.assertEqual(rewards[0]['reward_num'], 1)
        self.assertEqual(rewards[0]['reward_type'], 11)
        self.assertEqual(rewards[0]['reward_value'], 50)

    def test_happy_bakery_claim_daily_attendance(self):
        """setEventReward with event_idx: 3 gives Gingerbread gift item without inflating CP."""
        initial_cp = int(self.user['userdata'].get('u_cp', 0) or 0)
        initial_ap = int(self.user.get('user_ap', {}).get('i_Ap', 70) or 70)
        initial_gifts = sum(int(g.get('i_Value', 0) or 0) for g in self.user.get('user_follower_giftitem', []) if int(g.get('i_id', 0) or 0) == 1)

        # Claim Day 1 of Event 3 (Reward: 50 Gingerbread / Gift item 1)
        res, err = reward.h_set_event_reward({'uuid': self.dev_uuid, 'event_idx': 3}, None, self.ctx)
        self.assertEqual(err.get('code'), 0)
        self.assertEqual(res.get('status'), 'Y')
        self.assertEqual(res.get('reward_type'), 11)
        self.assertEqual(res.get('reward_value'), 50)

        # Verify player data
        u_after = state.get_user(self.dev_uuid)
        # CP should NOT have increased
        self.assertEqual(int(u_after['userdata'].get('u_cp', 0) or 0), initial_cp)
        # AP should NOT have changed on Day 1 (Day 1 is Gift, not AP)
        ap_after = int(u_after.get('user_ap', {}).get('i_Ap', 0) or 0)
        self.assertEqual(ap_after, initial_ap)
        # Gingerbread (Gift item 1) should have increased by 50
        gifts_after = sum(int(g.get('i_Value', 0) or 0) for g in u_after.get('user_follower_giftitem', []) if int(g.get('i_id', 0) or 0) == 1)
        self.assertEqual(gifts_after, initial_gifts + 50)

        # Same day duplicate claim should be rejected
        res2, err2 = reward.h_set_event_reward({'uuid': self.dev_uuid, 'event_idx': 3}, None, self.ctx)
        self.assertEqual(res2.get('status'), 'N')

    def test_character_2_skills_unlock_gating(self):
        """Character 2 (Busking Guitar Girl) skills 21..24 unlock based on character 2 level."""
        # In normal gameplay Character 2 is unlocked with Chapter 2. Add Character 2 Lv 20 to test its skills.
        self.user['characters'].append({'i_id': 2, 'i_Level': 20, 'i_BonusLevel': 0})
        contents = auth._user_contents(self.user)
        skills = self.user.get('user_skill', [])
        skill_ids = [s.get('i_id') for s in skills]
        self.assertIn(24, skill_ids, "Skill 24 (Skill Reset) should be unlocked at Lv 20")
        self.assertNotIn(21, skill_ids, "Skill 21 (Vivace) should not unlock before Lv 100")
        self.assertNotIn(22, skill_ids, "Skill 22 (Festival) should not unlock before Lv 300")
        self.assertNotIn(23, skill_ids, "Skill 23 (Musician) should not unlock before Lv 500")

        # Level up Character 2 to 100
        for c in self.user.get('characters', []):
            if c.get('i_id') == 2:
                c['i_Level'] = 100
        auth._user_contents(self.user)
        skills = self.user.get('user_skill', [])
        skill_ids = [s.get('i_id') for s in skills]
        self.assertIn(21, skill_ids, "Skill 21 should unlock when Character 2 is Lv 100")
        self.assertNotIn(22, skill_ids, "Skill 22 should not unlock at Lv 100")

        # Level up Character 2 to 500
        for c in self.user.get('characters', []):
            if c.get('i_id') == 2:
                c['i_Level'] = 500
        auth._user_contents(self.user)
        skills = self.user.get('user_skill', [])
        skill_ids = [s.get('i_id') for s in skills]
        self.assertIn(21, skill_ids)
        self.assertIn(22, skill_ids)
        self.assertIn(23, skill_ids)
        self.assertIn(24, skill_ids)

    def test_default_area2_data(self):
        """Area 2 defaults to Costume 201, Guitar 201, Music 201."""
        areas = state._default_areas()
        self.assertIn(2, areas)
        a2 = areas[2]
        self.assertEqual(a2['i_SelectedCostumeId'], 201)
        self.assertEqual(a2['i_SelectedGuitarId'], 201)
        self.assertEqual(a2['i_SelectedMusicId'], 201)

        # Login returns area_map with Area 2
        u_seq = self.user['userdata']['u_seq']
        res, err = auth.h_user_login({'uuid': self.dev_uuid, 'u_seq': u_seq}, None, self.ctx)
        self.assertEqual(err.get('code'), 0)
        area_map = res.get('area_data', {})
        self.assertIn(2, area_map)
        self.assertEqual(area_map[2]['i_SelectedCostumeId'], 201)

    def test_buy_music_chapter2_price(self):
        """Chapter 2 music prices fall back to column 46 (e.g. 100 GP for Music 201)."""
        from server.handlers import shop
        currency, price = shop._get_price(2, 201, 45, 39)
        self.assertEqual(currency, 'GP')
        self.assertEqual(price, 100, "Music 201 price must be 100 GP from column 46")

        # Test purchase: start with 0 Candy -> purchase rejected
        self.user['userdata']['u_candy'] = 0.0
        state.save_user(self.user)
        # Remove music 201 to test buying it
        self.user['user_music'] = [m for m in self.user.get('user_music', []) if m.get('i_id') != 201]
        state.save_user(self.user)

        res, err = shop.h_buy_music({'uuid': self.dev_uuid, 'idx': 201}, None, self.ctx)
        u_mid = [m.get('i_id') for m in state.get_user(self.dev_uuid).get('user_music', [])]
        self.assertNotIn(201, u_mid, "Music 201 should not be bought with 0 Candy")

        # Give 200 Candy -> purchase succeeds
        state.increment_currency(self.dev_uuid, candy=200.0)
        u = state.get_user(self.dev_uuid)
        u['userdata']['u_candy'] = 200.0
        state.save_user(u)

        res, err = shop.h_buy_music({'uuid': self.dev_uuid, 'idx': 201}, None, self.ctx)
        self.assertEqual(err.get('code'), 0)
        u_mid = [m.get('i_id') for m in state.get_user(self.dev_uuid).get('user_music', [])]
        self.assertIn(201, u_mid, "Music 201 should be bought successfully with sufficient Candy")

    def test_skill_reset_max_level(self):
        """Skill 4 and Skill 24 (Skill Reset) cannot be upgraded beyond max level 1."""
        from server.handlers import shop
        state.increment_currency(self.dev_uuid, cp=1000)
        u = state.get_user(self.dev_uuid)
        u['userdata']['u_cp'] = 1000
        # Character 2 at Lv 20 unlocks Skill 24 at Lv 1
        u['characters'] = [{'i_id': 1, 'i_Level': 100}, {'i_id': 2, 'i_Level': 20}]
        auth._user_contents(u)
        state.save_user(u)

        # Attempt to upgrade Skill 24
        res, err = shop.h_buy_contents({'uuid': self.dev_uuid, 'type': 'skill', 'idx': 24}, None, self.ctx)
        self.assertEqual(err.get('code'), 0)

        u = state.get_user(self.dev_uuid)
        s24 = next((s for s in u.get('user_skill', []) if s.get('i_id') == 24), None)
        self.assertIsNotNone(s24)
        self.assertEqual(s24.get('i_Level'), 1, "Skill 24 must not exceed max level 1")


if __name__ == '__main__':
    unittest.main()

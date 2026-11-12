import unittest
import uuid
import json

from server import state
from server.handlers.follower import (
    h_set_user_follower_quest,
    _sync_follower_messenger,
    _load_follower_quest_tables,
)
from server.handlers.auth import _user_contents
from server.handlers.ch_third import _stage_rewards, h_get_ch_third, h_ch_third_stage
from server.handlers.music import h_get_music_reward


class TestUserFixesFourIssues(unittest.TestCase):
    def setUp(self):
        self.dev_id = f"test_fix_{uuid.uuid4().hex[:12]}"
        self.user = state.create_user(self.dev_id, self.dev_id)

    def tearDown(self):
        conn = state.get_db()
        conn.execute('DELETE FROM user_inventory WHERE uuid = ?', (self.dev_id,))
        conn.execute('DELETE FROM user_data WHERE uuid = ?', (self.dev_id,))
        conn.commit()

    # ---------------------------------------------------------
    # Issue 1: FollowerQuest (Joy #ỦnghộGuitarGirl) claim fix
    # ---------------------------------------------------------
    def test_follower_quest_reward_grant_and_completion(self):
        """Test Table 26 FollowerQuest grants rewards and advances next_flg."""
        quests_def, rewards_def = _load_follower_quest_tables()
        self.assertTrue(len(quests_def) > 0, "Table 26 followerquest must be loaded")
        self.assertTrue(len(rewards_def) > 0, "Table 13 reward_group must be loaded")

        # Joy quest 1
        req1 = {'CurrentID': 1, 'SubID': 1, 'ConditionValue': 5.0}
        ctx = {'uuid': self.dev_id}
        res1, err1 = h_set_user_follower_quest({'call': 'setUserFollowerQuest', 'tapsonic_data': '', 'data': req1}, None, ctx)
        self.assertEqual(err1['code'], 0)
        self.assertEqual(res1['i_RewardReceived1'], 1)
        self.assertEqual(res1['next_flg'], 0)
        self.assertTrue(len(res1['reward_data']) > 0, "Must return reward_data from Table 13")

        # Joy quest sub_id 2
        req2 = {'CurrentID': 1, 'SubID': 2, 'ConditionValue': 1.0}
        res2, err2 = h_set_user_follower_quest({'call': 'setUserFollowerQuest', 'tapsonic_data': '', 'data': req2}, None, ctx)
        self.assertEqual(err2['code'], 0)
        self.assertEqual(res2['i_RewardReceived2'], 1)
        self.assertEqual(res2['next_flg'], 0)

        # Joy quest sub_id 3 (All 3 complete -> next_flg = 1)
        req3 = {'CurrentID': 1, 'SubID': 3, 'ConditionValue': 1.0}
        res3, err3 = h_set_user_follower_quest({'call': 'setUserFollowerQuest', 'tapsonic_data': '', 'data': req3}, None, ctx)
        self.assertEqual(err3['code'], 0)
        self.assertEqual(res3['i_RewardReceived3'], 1)
        self.assertEqual(res3['next_flg'], 1)
        self.assertEqual(res3['i_CompleteID'], 1)

        # Verify user contents includes user_follower_quest advanced to Quest 2
        user = state.get_user(self.dev_id)
        contents = _user_contents(user)
        self.assertIn('user_follower_quest', contents)
        stored_quests = contents['user_follower_quest']
        self.assertEqual(len(stored_quests), 1)
        self.assertEqual(stored_quests[0]['i_id'], 1)
        self.assertEqual(stored_quests[0]['i_CurrentID'], 2)
        self.assertEqual(stored_quests[0]['i_CompleteID'], 1)

    # ---------------------------------------------------------
    # Issue 2: Chapter 1 Follower Chat Room Visibility Fix
    # ---------------------------------------------------------
    def test_chapter1_follower_chat_room_visibility(self):
        """Unlocking followers in CH1 must have i_LastConfirmIndex = 0 so the client displays them."""
        # Add Chapter 1 followers: 2 (Convenience Store), 3 (Homeroom Teacher), 4 (Quiet Senior)
        self.user['user_follower'].extend([
            {'i_id': 2, 'i_Level': 1, 'i_BonusLevel': 0},
            {'i_id': 3, 'i_Level': 1, 'i_BonusLevel': 0},
            {'i_id': 4, 'i_Level': 1, 'i_BonusLevel': 0},
        ])
        ms = _sync_follower_messenger(self.user)
        room_map = {r['i_MessengerChatRoomId']: r for r in ms}

        for rid in [1, 2, 3, 4]:
            self.assertIn(rid, room_map, f"Room {rid} must exist")
            self.assertEqual(
                room_map[rid]['i_LastConfirmIndex'], 0,
                f"Room {rid} must have i_LastConfirmIndex = 0 (not -1) to prevent client hiding it"
            )
            self.assertTrue(len(room_map[rid]['s_UnlockGroupList']) > 0)

    # ---------------------------------------------------------
    # Issue 3: Chapter 3 Moa Tutorial (Sunshine High School) Fix
    # ---------------------------------------------------------
    def test_chapter3_moa_tutorial_not_pre_seeded(self):
        """Fresh accounts must NOT have pre-seeded stage 1001 so Moa tutorial triggers properly."""
        contents = _user_contents(self.user)
        self.assertIn('user_chthird_stage', contents)
        self.assertEqual(contents['user_chthird_stage'], [], "user_chthird_stage must default to [] for fresh user")

        # When player plays tutorial stage 1001, it must succeed and clear with 3 stars
        stage_cfg = {'1': 1001, '5': 100, '6': 150, '7': 200, '34': 'Normal', '37': '301010, 301015'}
        # Clear stage 1001
        from server import event_manager
        orig_tour = event_manager.is_chapter3_tour_enabled
        try:
            event_manager.is_chapter3_tour_enabled = lambda: True
            res, err = h_ch_third_stage({'call': 'chThirdStage', 'tapsonic_data': '', 'data': {'i_id': 1001, 'uuid': self.dev_id}}, None, {'uuid': self.dev_id})
            self.assertEqual(err['code'], 0)
            self.assertEqual(res['clear'], 1)
            self.assertEqual(res['star'], 3)
            self.assertEqual(res['user_ch_third_stage']['i_id'], 1001)
        finally:
            event_manager.is_chapter3_tour_enabled = orig_tour

    # ---------------------------------------------------------
    # Issue 4: Music Discs & Performance Gift Drop Rates
    # ---------------------------------------------------------
    def test_music_discs_and_encore_rewards(self):
        """Verify music discs and encore candy/exp rewards."""
        contents = _user_contents(self.user)
        musics = contents['user_music']
        music_ids = {m['i_id'] for m in musics}
        self.assertIn(1, music_ids, "Starter song 1 must be present")
        self.assertIn(201, music_ids, "Starter song 201 must be present")

        # Test encore reward claim
        req = {'i_ids': [1], 'i_levels': [1], 'uuid': self.dev_id}
        res, err = h_get_music_reward({'call': 'getMusicReward', 'tapsonic_data': '', 'data': req}, None, {'uuid': self.dev_id})
        self.assertEqual(err['code'], 0)
        self.assertGreaterEqual(res['total_reward_value'], 10, "Base encore candy for level 1 song is 10")
        self.assertEqual(res['reward_music_id'], [1])

    def test_chapter3_stage_drop_rate_sampling(self):
        """Table 36 sampling must produce varied drop amounts matching drop table."""
        stage_cfg = {'1': 1001, '37': '301010, 301015'}
        drops = [_stage_rewards(stage_cfg) for _ in range(50)]
        self.assertTrue(any(len(d) > 0 for d in drops), "Drops must occur")
        # In Table 36 group 301010, reward_value can be 1, 2, 3, or 4
        all_vals = {r['reward_value'] for d in drops for r in d if r['reward_id'] == 1}
        # With 50 rolls, at least 2 different drop amounts should be observed
        self.assertGreater(len(all_vals), 1, f"Expected varied drop amounts from Table 36, got {all_vals}")


if __name__ == '__main__':
    unittest.main()

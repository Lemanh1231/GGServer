import unittest
from server import state
from server.handlers import auth, follower


class TestFollowerQuest(unittest.TestCase):
    def setUp(self):
        self.uuid = 'test_fq_user_999999'
        conn = state.get_db()
        conn.execute('DELETE FROM user_inventory WHERE uuid = ?', (self.uuid,))
        conn.execute('DELETE FROM user_data WHERE uuid = ?', (self.uuid,))
        conn.commit()
        self.user = state.create_user(self.uuid, self.uuid)

    def tearDown(self):
        conn = state.get_db()
        conn.execute('DELETE FROM user_inventory WHERE uuid = ?', (self.uuid,))
        conn.execute('DELETE FROM user_data WHERE uuid = ?', (self.uuid,))
        conn.commit()

    def test_1_login_normalises_follower_quest_with_id_1(self):
        resp, err = auth.h_user_login({'data': {'uuid': self.uuid, 'u_seq': self.user['userdata']['u_seq']}}, None, {})
        self.assertEqual(err['code'], 0)
        ufq = resp['user_contents']['user_follower_quest']
        self.assertEqual(len(ufq), 1)
        self.assertEqual(ufq[0]['i_id'], 1)
        self.assertEqual(ufq[0]['i_CurrentID'], 1)
        self.assertEqual(ufq[0]['i_CompleteID'], 0)

    def test_2_claim_sub_missions_and_advance_to_next_quest(self):
        # Sub 1 of Quest 1 (Helping Joy): 3000 Likes (rg 500101 -> rtype=1, rid=4, rval=3000)
        r1, err = follower.h_set_user_follower_quest({
            'data': {'uuid': self.uuid, 'i_CurrentID': 1, 'i_SubID': 1, 'd_ConditionValue': 5.0}
        }, None, {})
        self.assertEqual(err['code'], 0)
        self.assertEqual(r1['i_CurrentID'], 1)
        self.assertEqual(r1['i_RewardReceived1'], 1)
        self.assertEqual(r1['next_flg'], 0)
        self.assertEqual(r1['reward_data'], [{'reward_type': 1, 'reward_id': 4, 'reward_value': 3000.0}])

        # Simulate userSave from client (which omits i_id and i_RewardReceived1..3)
        auth.h_user_save({
            'data': {
                'uuid': self.uuid,
                'user_follower_quest': [
                    {'i_CurrentID': 1, 'd_ConditionValue1': 5.0, 'd_ConditionValue2': 1.0, 'd_ConditionValue3': 2.0}
                ]
            }
        }, None, {})

        # Verify i_id=1 and i_RewardReceived1=1 were NOT wiped by userSave!
        u = state.get_user(self.uuid)
        self.assertEqual(len(u['user_follower_quest']), 1)
        self.assertEqual(u['user_follower_quest'][0]['i_id'], 1)
        self.assertEqual(u['user_follower_quest'][0]['i_RewardReceived1'], 1)
        self.assertEqual(u['user_follower_quest'][0]['d_ConditionValue3'], 2.0)

        # Sub 2 of Quest 1: 300s Buff 2 (rg 500102 -> rtype=6, rid=2, rval=300)
        r2, err = follower.h_set_user_follower_quest({
            'data': {'uuid': self.uuid, 'i_CurrentID': 1, 'i_SubID': 2, 'd_ConditionValue': 1.0}
        }, None, {})
        self.assertEqual(err['code'], 0)
        self.assertEqual(r2['i_CurrentID'], 1)
        self.assertEqual(r2['i_RewardReceived1'], 1)
        self.assertEqual(r2['i_RewardReceived2'], 1)
        self.assertEqual(r2['next_flg'], 0)
        self.assertEqual(r2['reward_data'], [{'reward_type': 6, 'reward_id': 2, 'reward_value': 300.0}])

        # Sub 3 of Quest 1: 10 CP (rg 500103 -> rtype=1, rid=1, rval=10) -> completes Quest 1 and advances to Quest 2!
        r3, err = follower.h_set_user_follower_quest({
            'data': {'uuid': self.uuid, 'i_CurrentID': 1, 'i_SubID': 3, 'd_ConditionValue': 3.0}
        }, None, {})
        self.assertEqual(err['code'], 0)
        self.assertEqual(r3['next_flg'], 1)
        self.assertEqual(r3['i_CompleteID'], 1)
        self.assertEqual(r3['i_CurrentID'], 2)
        self.assertEqual(r3['i_RewardReceived1'], 1)
        self.assertEqual(r3['i_RewardReceived2'], 1)
        self.assertEqual(r3['i_RewardReceived3'], 1)
        self.assertEqual(r3['reward_data'], [{'reward_type': 1, 'reward_id': 1, 'reward_value': 10.0}])

        # Verify persisted state has advanced to Quest 2 with i_id=1 and reset reward flags
        u = state.get_user(self.uuid)
        self.assertEqual(u['user_follower_quest'][0]['i_id'], 1)
        self.assertEqual(u['user_follower_quest'][0]['i_CurrentID'], 2)
        self.assertEqual(u['user_follower_quest'][0]['i_CompleteID'], 1)
        self.assertEqual(u['user_follower_quest'][0]['i_RewardReceived1'], 0)
        self.assertEqual(u['user_follower_quest'][0]['i_RewardReceived2'], 0)
        self.assertEqual(u['user_follower_quest'][0]['i_RewardReceived3'], 0)

    def test_3_completing_last_normal_quest_42_transitions_to_infinite_quest(self):
        u = state.get_user(self.uuid)
        u['user_follower_quest'] = [{
            'i_id': 1,
            'i_CurrentID': 42,
            'i_CompleteID': 41,
            'd_ConditionValue1': 1.0,
            'd_ConditionValue2': 1.0,
            'd_ConditionValue3': 0.0,
            'i_RewardReceived1': 1,
            'i_RewardReceived2': 1,
            'i_RewardReceived3': 0,
            'i_isInfinity': 0,
        }]
        state.save_user(u)

        r3, err = follower.h_set_user_follower_quest({
            'data': {'uuid': self.uuid, 'i_CurrentID': 42, 'i_SubID': 3, 'd_ConditionValue': 10.0}
        }, None, {})
        self.assertEqual(err['code'], 0)
        self.assertEqual(r3['next_flg'], 1)
        self.assertEqual(r3['i_CompleteID'], 42)
        self.assertGreaterEqual(r3['i_CurrentID'], 902)
        u2 = state.get_user(self.uuid)
        self.assertEqual(u2['user_follower_quest'][0]['i_isInfinity'], 1)


if __name__ == '__main__':
    unittest.main()

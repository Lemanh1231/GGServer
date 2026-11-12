import unittest
import urllib.request
import json
import uuid

from server import state
from server.handlers.follower import (
    FOLLOWER_MESSENGER_MAP,
    _sync_follower_messenger,
    _merge_user_messenger,
)
from server.handlers.auth import _starter_messenger, _user_contents


class TestFollowerMessengerSync(unittest.TestCase):
    def setUp(self):
        self.dev_id = f"test_msg_{uuid.uuid4().hex[:12]}"

    def tearDown(self):
        conn = state.get_db()
        conn.execute("DELETE FROM user_inventory WHERE uuid LIKE 'test_%'")
        conn.execute("DELETE FROM user_data WHERE uuid LIKE 'test_%' OR device_uuid LIKE 'test_%'")
        conn.commit()
        conn.close()

    def test_starter_user_only_has_room_1(self):
        user = state.create_user(self.dev_id, self.dev_id)
        ms = _starter_messenger(user)
        self.assertEqual(len(ms), 1)
        self.assertEqual(ms[0]['i_MessengerChatRoomId'], 1)
        self.assertEqual(ms[0]['i_LastConfirmIndex'], 0)
        self.assertEqual(ms[0]['s_UnlockGroupList'], '1')

    def test_unlocking_follower_2_adds_chat_room_2(self):
        user = state.create_user(self.dev_id, self.dev_id)
        # Follower 2 unlocked
        user['user_follower'].append({'i_id': 2, 'i_Level': 1, 'i_BonusLevel': 0})
        ms = _sync_follower_messenger(user)
        
        room_ids = [r['i_MessengerChatRoomId'] for r in ms]
        self.assertIn(1, room_ids)
        self.assertIn(2, room_ids)

        r2 = next(r for r in ms if r['i_MessengerChatRoomId'] == 2)
        self.assertEqual(r2['i_LastConfirmIndex'], 0)
        self.assertEqual(r2['s_UnlockGroupList'], '2')

    def test_unlocking_happy_bakery_adds_chat_room_12(self):
        user = state.create_user(self.dev_id, self.dev_id)
        # Follower 12 (Happy Bakery) unlocked
        user['user_follower'].append({'i_id': 12, 'i_Level': 1, 'i_BonusLevel': 0})
        ms = _sync_follower_messenger(user)

        r12 = next((r for r in ms if r['i_MessengerChatRoomId'] == 12), None)
        self.assertIsNotNone(r12)
        self.assertEqual(r12['i_LastConfirmIndex'], 0)
        self.assertEqual(r12['s_UnlockGroupList'], '80')

    def test_unlocking_chapter2_followers(self):
        user = state.create_user(self.dev_id, self.dev_id)
        # Follower 203 (Reading Fox) and 204 (Ruby)
        user['user_follower'].extend([
            {'i_id': 203, 'i_Level': 1, 'i_BonusLevel': 0},
            {'i_id': 204, 'i_Level': 1, 'i_BonusLevel': 0},
        ])
        ms = _sync_follower_messenger(user)

        r203 = next((r for r in ms if r['i_MessengerChatRoomId'] == 203), None)
        self.assertIsNotNone(r203)
        self.assertEqual(r203['s_UnlockGroupList'], '114')
        self.assertEqual(r203['i_LastConfirmIndex'], 0)

        r204 = next((r for r in ms if r['i_MessengerChatRoomId'] == 204), None)
        self.assertIsNotNone(r204)
        self.assertEqual(r204['s_UnlockGroupList'], '127')
        self.assertEqual(r204['i_LastConfirmIndex'], 0)

        # Room 12 has 103 completed (prerequisite for Fox 203)
        r12 = next((r for r in ms if r['i_MessengerChatRoomId'] == 12), None)
        self.assertIsNotNone(r12)
        self.assertIn('103', r12['s_UnlockGroupList'].split(','))

        # Room 16 has 118 completed (prerequisite for Ruby 204)
        r16 = next((r for r in ms if r['i_MessengerChatRoomId'] == 16), None)
        self.assertIsNotNone(r16)
        self.assertIn('118', r16['s_UnlockGroupList'].split(','))

    def test_chapter2_full_follower_progression(self):
        user = state.create_user(self.dev_id, self.dev_id)
        # 1. Unlock CH2 starters (Joy 201, Moa 202, Reading Fox 203)
        user['user_follower'].extend([
            {'i_id': 201, 'i_Level': 1, 'i_BonusLevel': 0},
            {'i_id': 202, 'i_Level': 1, 'i_BonusLevel': 0},
            {'i_id': 203, 'i_Level': 1, 'i_BonusLevel': 0},
        ])
        ms = _sync_follower_messenger(user)
        room_ids = {r['i_MessengerChatRoomId']: r for r in ms}

        self.assertIn(1, room_ids)
        self.assertIn('111', room_ids[1]['s_UnlockGroupList'].split(','))
        self.assertIn(5, room_ids)
        self.assertIn('110', room_ids[5]['s_UnlockGroupList'].split(','))
        self.assertIn(12, room_ids)
        self.assertIn('103', room_ids[12]['s_UnlockGroupList'].split(','))
        self.assertIn(16, room_ids)
        self.assertIn('104', room_ids[16]['s_UnlockGroupList'].split(','))
        self.assertIn(203, room_ids)
        self.assertEqual(room_ids[203]['s_UnlockGroupList'], '114')
        self.assertEqual(room_ids[203]['i_LastConfirmIndex'], 0)

        # 2. Unlock Follower 205 (Friend Alex)
        user['user_follower'].append({'i_id': 205, 'i_Level': 500, 'i_BonusLevel': 0})
        ms = _sync_follower_messenger(user)
        room_ids = {r['i_MessengerChatRoomId']: r for r in ms}
        self.assertIn(205, room_ids)
        self.assertEqual(room_ids[205]['s_UnlockGroupList'], '138')
        self.assertEqual(room_ids[205]['i_LastConfirmIndex'], 0)
        # Room 16 must have 132 completed (prerequisite for Alex 205)
        self.assertIn('132', room_ids[16]['s_UnlockGroupList'].split(','))

        # 3. Unlock Follower 206 (Busking TV)
        user['user_follower'].append({'i_id': 206, 'i_Level': 1000, 'i_BonusLevel': 0})
        ms = _sync_follower_messenger(user)
        room_ids = {r['i_MessengerChatRoomId']: r for r in ms}
        self.assertIn(206, room_ids)
        self.assertEqual(room_ids[206]['s_UnlockGroupList'], '178')
        self.assertEqual(room_ids[206]['i_LastConfirmIndex'], 0)
        # Room 17 must have 173 completed (prerequisite for Busking TV 206)
        self.assertIn(17, room_ids)
        self.assertIn('173', room_ids[17]['s_UnlockGroupList'].split(','))

        # 4. Unlock Follower 207 (Sora) and 208 (Jessica)
        user['user_follower'].extend([
            {'i_id': 207, 'i_Level': 1000, 'i_BonusLevel': 0},
            {'i_id': 208, 'i_Level': 1000, 'i_BonusLevel': 0},
        ])
        ms = _sync_follower_messenger(user)
        room_ids = {r['i_MessengerChatRoomId']: r for r in ms}
        self.assertIn(207, room_ids)
        self.assertEqual(room_ids[207]['s_UnlockGroupList'], '181')
        self.assertEqual(room_ids[207]['i_LastConfirmIndex'], 0)
        self.assertIn(208, room_ids)
        self.assertEqual(room_ids[208]['s_UnlockGroupList'], '186')
        self.assertEqual(room_ids[208]['i_LastConfirmIndex'], 0)
        # Room 16 must have 171 completed (prerequisite for Sora 207 and Jessica 208)
        self.assertIn('171', room_ids[16]['s_UnlockGroupList'].split(','))

    def test_preserve_read_progress_across_sync_and_merge(self):
        user = state.create_user(self.dev_id, self.dev_id)
        user['user_follower'].append({'i_id': 2, 'i_Level': 1, 'i_BonusLevel': 0})
        _sync_follower_messenger(user)

        # User reads messages in Room 2: confirm index becomes 22, unlock groups "2,5"
        incoming = [
            {'i_MessengerChatRoomId': 1, 'i_LastConfirmIndex': 17, 's_UnlockGroupList': '1,3'},
            {'i_MessengerChatRoomId': 2, 'i_LastConfirmIndex': 22, 's_UnlockGroupList': '2,5', 'l_UpdateTimeTicks': 12345},
        ]
        _merge_user_messenger(user, incoming)
        _sync_follower_messenger(user)

        r2 = next(r for r in user['user_messenger'] if r['i_MessengerChatRoomId'] == 2)
        self.assertEqual(r2['i_LastConfirmIndex'], 22)
        self.assertEqual(r2['s_UnlockGroupList'], '2,5')
        self.assertEqual(r2['l_UpdateTimeTicks'], 12345)

        # Unlock Follower 3 - Room 2's progress must remain unchanged!
        user['user_follower'].append({'i_id': 3, 'i_Level': 1, 'i_BonusLevel': 0})
        _sync_follower_messenger(user)

        r2_after = next(r for r in user['user_messenger'] if r['i_MessengerChatRoomId'] == 2)
        self.assertEqual(r2_after['i_LastConfirmIndex'], 22)
        self.assertEqual(r2_after['s_UnlockGroupList'], '2,5')

        r3 = next(r for r in user['user_messenger'] if r['i_MessengerChatRoomId'] == 3)
        self.assertEqual(r3['i_LastConfirmIndex'], 0)
        self.assertEqual(r3['s_UnlockGroupList'], '6')

    def test_locked_followers_do_not_appear(self):
        user = state.create_user(self.dev_id, self.dev_id)
        # Only Follower 1
        ms = _sync_follower_messenger(user)
        room_ids = [r['i_MessengerChatRoomId'] for r in ms]
        self.assertEqual(room_ids, [1])
        # Follower 2, 3, etc. are NOT in user_messenger
        self.assertNotIn(2, room_ids)
        self.assertNotIn(3, room_ids)
        self.assertNotIn(10, room_ids)

    def test_http_user_save_and_login_e2e(self):
        import io
        import codec
        from server import dispatch
        SERVER = "http://127.0.0.1:8080"

        def _multipart(fields):
            boundary = '----gg' + uuid.uuid4().hex
            out = io.BytesIO()
            for k, v in fields.items():
                out.write(('--%s\r\n' % boundary).encode())
                out.write(('Content-Disposition: form-data; name="%s"\r\n\r\n' % k).encode())
                out.write(v.encode() if isinstance(v, str) else v)
                out.write(b'\r\n')
            out.write(('--%s--\r\n' % boundary).encode())
            return boundary, out.getvalue()

        def rpc(cmd_full, call, data):
            env = {'call': call, 'data': data, 'common_data': {'client_ver': 800, 'type': 'aos', 'os': 1}}
            b64 = codec.encode_response(cmd_full, env)
            boundary, body = _multipart({'call': call, 'tapsonic_data': b64, 'access_token': '', 'current_time': '0'})
            ns = cmd_full.split('.')[0]
            req = urllib.request.Request(SERVER + '/%s/%s/vi/' % (ns, call), data=body,
                                         headers={'Content-Type': 'multipart/form-data; boundary=%s' % boundary})
            raw = urllib.request.urlopen(req, timeout=10).read().decode()
            named, _ = codec.decode_request(raw, dispatch.return_dto_for(cmd_full))
            return named

        dev = f"test_e2e_msg_{uuid.uuid4().hex[:12]}"
        join_res = rpc('main.userJoin', 'userJoin', {'device_uuid': dev, 'uuid': dev})
        self.assertIsNotNone(join_res)
        u_seq = join_res[5][1]

        # Initial login: only Room 1
        login_res = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'device_uuid': dev, 'u_seq': u_seq})
        ms = login_res['data']['user_contents']['user_messenger']
        self.assertEqual(len(ms), 1)
        self.assertEqual(ms[0]['i_MessengerChatRoomId'], 1)

        # Client saves with Follower 2 unlocked
        save_payload = {
            'uuid': dev,
            'device_uuid': dev,
            'user_follower': [
                {'i_id': 1, 'i_Level': 100, 'i_BonusLevel': 0},
                {'i_id': 2, 'i_Level': 1, 'i_BonusLevel': 0},
            ],
            'user_messenger': [
                {'i_MessengerChatRoomId': 1, 'i_LastConfirmIndex': 10, 's_UnlockGroupList': '1,3', 'l_UpdateTimeTicks': 111},
            ]
        }
        save_res = rpc('user.userSave', 'userSave', save_payload)
        self.assertEqual(save_res.get('data', {}).get('status'), 'Y')

        # Next login: user_contents must contain both Room 1 and Room 2!
        login2_res = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'device_uuid': dev, 'u_seq': u_seq})
        ms2 = login2_res['data']['user_contents']['user_messenger']
        room_ids = [r['i_MessengerChatRoomId'] for r in ms2]
        self.assertIn(1, room_ids)
        self.assertIn(2, room_ids)

        r1 = next(r for r in ms2 if r['i_MessengerChatRoomId'] == 1)
        self.assertEqual(r1['i_LastConfirmIndex'], 10)
        self.assertEqual(r1['s_UnlockGroupList'], '1,3')

        r2 = next(r for r in ms2 if r['i_MessengerChatRoomId'] == 2)
        self.assertEqual(r2['i_LastConfirmIndex'], 0)
        self.assertEqual(r2['s_UnlockGroupList'], '2')




    def test_unlocking_all_ch1_followers_satisfies_prerequisites(self):
        user = state.create_user(self.dev_id, self.dev_id)
        # Unlock all 15 Chapter 1 followers
        user['user_follower'] = [{'i_id': i, 'i_Level': 100, 'i_BonusLevel': 0} for i in range(1, 16)]
        ms = _sync_follower_messenger(user)
        room_map = {r['i_MessengerChatRoomId']: r for r in ms}

        # All 15 follower rooms must exist
        for rid in range(1, 16):
            self.assertIn(rid, room_map, f"Room {rid} must exist for CH1 follower")

        # Key prerequisite chains must be satisfied
        r1_groups = set(room_map[1]['s_UnlockGroupList'].split(','))
        self.assertTrue({'4', '7', '10', '12', '15', '16', '47', '57', '75'}.issubset(r1_groups))

        r6_groups = set(room_map[6]['s_UnlockGroupList'].split(','))
        self.assertIn('18', r6_groups)

        r7_groups = set(room_map[7]['s_UnlockGroupList'].split(','))
        self.assertIn('58', r7_groups)

        r16_groups = set(room_map[16]['s_UnlockGroupList'].split(','))
        self.assertTrue({'76', '78', '79'}.issubset(r16_groups))

    def test_all_15_ch1_followers_have_initial_groups_active(self):
        """Verify that every unlocked follower in Chapter 1 has their introductory group active."""
        user = state.create_user(self.dev_id, self.dev_id)
        user['user_follower'] = [{'i_id': i, 'i_Level': 1, 'i_BonusLevel': 0} for i in range(1, 16)]
        ms = _sync_follower_messenger(user)
        room_map = {r['i_MessengerChatRoomId']: r for r in ms}

        expected_proceeding = {
            1: 1, 2: 2, 3: 6, 4: 9, 5: 13, 6: 18, 7: 20, 8: 51,
            9: 62, 10: 54, 11: 74, 12: 80, 13: 88, 14: 90, 15: 91
        }
        for rid, expected_group in expected_proceeding.items():
            self.assertIn(rid, room_map, f"Follower {rid} must have room {rid}")
            groups = [int(x.strip()) for x in room_map[rid]['s_UnlockGroupList'].split(',')]
            self.assertEqual(groups[-1], expected_group,
                             f"Room {rid} active proceeding group must be {expected_group}, got {groups[-1]}")
            self.assertEqual(room_map[rid]['i_LastConfirmIndex'], 0)

    def test_all_ch2_followers_have_initial_groups_active(self):
        """Verify that every unlocked follower in Chapter 2 has their introductory group active."""
        user = state.create_user(self.dev_id, self.dev_id)
        # Unlock all CH1 and CH2 followers
        user['user_follower'] = [{'i_id': i, 'i_Level': 1, 'i_BonusLevel': 0} for i in range(1, 16)] + \
                                [{'i_id': i, 'i_Level': 1, 'i_BonusLevel': 0} for i in range(201, 209)]
        ms = _sync_follower_messenger(user)
        room_map = {r['i_MessengerChatRoomId']: r for r in ms}

        expected_ch2_proceeding = {
            203: 114, 204: 127, 205: 138, 206: 178, 207: 181, 208: 186,
            1: 111, 5: 157, 12: 109, 16: 172, 17: 174
        }
        for rid, expected_group in expected_ch2_proceeding.items():
            self.assertIn(rid, room_map, f"CH2 room {rid} must exist")
            groups = [int(x.strip()) for x in room_map[rid]['s_UnlockGroupList'].split(',')]
            self.assertEqual(groups[-1], expected_group,
                             f"CH2 room {rid} active proceeding group must be {expected_group}, got {groups[-1]}")
            self.assertEqual(room_map[rid]['i_LastConfirmIndex'], 0)

    def test_auto_heal_corrupted_legacy_rooms(self):
        """Verify that rooms corrupted with late-game proceeding groups are automatically healed."""
        user = state.create_user(self.dev_id, self.dev_id)
        user['user_follower'] = [{'i_id': i, 'i_Level': 1, 'i_BonusLevel': 0} for i in range(1, 16)]
        # Inject corrupted rooms as seen in legacy database
        user['user_messenger'] = [
            {'i_MessengerChatRoomId': 1, 'i_LastConfirmIndex': 0, 's_UnlockGroupList': '1,4,7,10,12,15,16,24,30,32,33,35,36,41,45,47,56,57,75', 'l_UpdateTimeTicks': 0},
            {'i_MessengerChatRoomId': 2, 'i_LastConfirmIndex': 0, 's_UnlockGroupList': '2,5,11,77', 'l_UpdateTimeTicks': 0},
            {'i_MessengerChatRoomId': 3, 'i_LastConfirmIndex': 0, 's_UnlockGroupList': '6,31,44', 'l_UpdateTimeTicks': 0},
            {'i_MessengerChatRoomId': 5, 'i_LastConfirmIndex': 0, 's_UnlockGroupList': '13,14,21,25,28,40,46,55', 'l_UpdateTimeTicks': 0},
            {'i_MessengerChatRoomId': 6, 'i_LastConfirmIndex': 0, 's_UnlockGroupList': '18,26,43', 'l_UpdateTimeTicks': 0},
            {'i_MessengerChatRoomId': 7, 'i_LastConfirmIndex': 0, 's_UnlockGroupList': '20,23,29,34,37,38,39,42,53,58', 'l_UpdateTimeTicks': 0},
            {'i_MessengerChatRoomId': 16, 'i_LastConfirmIndex': 0, 's_UnlockGroupList': '76,78,79', 'l_UpdateTimeTicks': 0},
        ]
        ms = _sync_follower_messenger(user)
        room_map = {r['i_MessengerChatRoomId']: r for r in ms}

        self.assertEqual([int(x) for x in room_map[2]['s_UnlockGroupList'].split(',')][-1], 2)
        self.assertEqual([int(x) for x in room_map[3]['s_UnlockGroupList'].split(',')][-1], 6)
        self.assertEqual([int(x) for x in room_map[5]['s_UnlockGroupList'].split(',')][-1], 13)
        self.assertEqual([int(x) for x in room_map[6]['s_UnlockGroupList'].split(',')][-1], 18)
        self.assertEqual([int(x) for x in room_map[7]['s_UnlockGroupList'].split(',')][-1], 20)
        self.assertEqual([int(x) for x in room_map[1]['s_UnlockGroupList'].split(',')][-1], 1)

    def test_ch2_sync_preserves_progressed_groups_and_ch1_prereqs(self):
        """Verify CH2 sync keeps progressed proceeding groups and satisfies CH1 prerequisites."""
        user = state.create_user(self.dev_id, self.dev_id)
        user['user_follower'] = [{'i_id': i, 'i_Level': 1500, 'i_BonusLevel': 0} for i in range(1, 16)] + \
                                [{'i_id': i, 'i_Level': 1500, 'i_BonusLevel': 0} for i in range(201, 209)]
        user['user_messenger'] = [
            {'i_MessengerChatRoomId': 2, 'i_LastConfirmIndex': 0, 's_UnlockGroupList': '8,5,11,22,77,116,148,2', 'l_UpdateTimeTicks': 0},
            {'i_MessengerChatRoomId': 5, 'i_LastConfirmIndex': 2, 's_UnlockGroupList': '13,14,21,25,28,40,46,55,110,164,52,167,157', 'l_UpdateTimeTicks': 0},
            {'i_MessengerChatRoomId': 6, 'i_LastConfirmIndex': 0, 's_UnlockGroupList': '26,43,106,113,129,168,18', 'l_UpdateTimeTicks': 0},
            {'i_MessengerChatRoomId': 7, 'i_LastConfirmIndex': 14, 's_UnlockGroupList': '20,23,29,42,53', 'l_UpdateTimeTicks': 0},
            {'i_MessengerChatRoomId': 16, 'i_LastConfirmIndex': 12, 's_UnlockGroupList': '76,78,79,81,82,104,105,108,115,118,128,132,135,171,119,120,172', 'l_UpdateTimeTicks': 0},
            {'i_MessengerChatRoomId': 17, 'i_LastConfirmIndex': 17, 's_UnlockGroupList': '139,140,142,144,146,149,151,152,153,154,155,162,173,176,177,174', 'l_UpdateTimeTicks': 0},
        ]
        ms = _sync_follower_messenger(user)
        room_map = {r['i_MessengerChatRoomId']: r for r in ms}

        # Yanked starter groups are moved back before later groups, preserving latest proceeding group
        self.assertEqual([int(x) for x in room_map[2]['s_UnlockGroupList'].split(',')][-1], 148)
        self.assertEqual([int(x) for x in room_map[5]['s_UnlockGroupList'].split(',')][-1], 167)
        self.assertEqual([int(x) for x in room_map[6]['s_UnlockGroupList'].split(',')][-1], 168)
        self.assertEqual([int(x) for x in room_map[16]['s_UnlockGroupList'].split(',')][-1], 120)
        self.assertEqual([int(x) for x in room_map[17]['s_UnlockGroupList'].split(',')][-1], 177)

        # Room 1 and Room 7 still receive CH1 prerequisites even when has_ch2 is True
        r1_completed = [int(x) for x in room_map[1]['s_UnlockGroupList'].split(',')][:-1]
        self.assertIn(36, r1_completed)
        self.assertIn(57, r1_completed)
        r7_completed = [int(x) for x in room_map[7]['s_UnlockGroupList'].split(',')][:-1]
        self.assertIn(58, r7_completed)


if __name__ == '__main__':
    unittest.main()

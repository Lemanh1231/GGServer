#!/usr/bin/env python3
"""Test suite verifying the 6 server bug fixes from Agent 2 audit report."""
import datetime
import io
import json
import os
import sys
import time
import unittest
import urllib.request
import uuid as uuidlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codec
from server import dispatch, state

SERVER = os.environ.get('GG_TEST_URL', 'http://127.0.0.1:8080')


def _multipart(fields):
    boundary = '----gg' + uuidlib.uuid4().hex
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(('--%s\r\n' % boundary).encode())
        out.write(('Content-Disposition: form-data; name="%s"\r\n\r\n' % k).encode())
        out.write(v.encode() if isinstance(v, str) else v)
        out.write(b'\r\n')
    out.write(('--%s--\r\n' % boundary).encode())
    return boundary, out.getvalue()


def rpc(cmd_full, call, data, ns=None):
    env = {'call': call, 'data': data, 'common_data': {'client_ver': 800, 'type': 'aos', 'os': 1}}
    b64 = codec.encode_response(cmd_full, env)
    boundary, body = _multipart({'call': call, 'tapsonic_data': b64, 'access_token': '', 'current_time': '0'})
    endpoint_ns = ns or cmd_full.split('.')[0]
    req = urllib.request.Request(
        f'{SERVER}/{endpoint_ns}/{call}/vi/',
        data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
    )
    raw = urllib.request.urlopen(req, timeout=10).read().decode()
    return_dto = dispatch.return_dto_for(cmd_full)
    named, _ = codec.decode_request(raw, return_dto)
    return named


class TestAgent2Fixes(unittest.TestCase):
    def setUp(self):
        self.test_users = []

    def tearDown(self):
        for dev in self.test_users:
            try:
                conn = state.get_db()
                conn.execute('DELETE FROM user_data WHERE uuid = ?', (dev,))
                conn.execute('DELETE FROM user_inventory WHERE uuid = ?', (dev,))
                conn.commit()
                conn.close()
            except Exception:
                pass

    def create_user(self):
        dev = 'fix-test-' + uuidlib.uuid4().hex[:10]
        self.test_users.append(dev)
        join_res = rpc('user.userJoin', 'userJoin', {'uuid': dev, 'device_uuid': dev})
        u_seq = join_res['data']['u_seq']
        login_res = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        return dev, u_seq, login_res

    # 1. Bảng điểm danh hàng ngày: setAttendance('check') phải trả về 'status': 'Y' nếu chưa nhận thưởng
    def test_attendance_status_flow(self):
        dev, u_seq, _ = self.create_user()

        # Step 1: Client sends 'add' during startup
        res_add = rpc('user.setAttendance', 'setAttendance', {'uuid': dev, 'device_uuid': dev, 'type': 'add'})
        self.assertEqual(res_add['data']['status'], 'Y', "setAttendance(add) must return status 'Y'")

        # Step 2: Client sends 'check' before claiming reward -> must return 'Y' so UI opens!
        res_check = rpc('user.setAttendance', 'setAttendance', {'uuid': dev, 'device_uuid': dev, 'type': 'check'})
        self.assertEqual(res_check['data']['status'], 'Y', "setAttendance(check) before claiming must return status 'Y'")

        # Step 3: Claim day 1 reward
        res_claim = rpc('user.setEventReward', 'setEventReward', {'uuid': dev, 'device_uuid': dev, 'event_idx': 1})
        self.assertEqual(res_claim['data']['status'], 'Y', "Claiming attendance reward must succeed")

        # Step 4: After claiming today, setAttendance(check) should return 'N' (already claimed today)
        res_check_after = rpc('user.setAttendance', 'setAttendance', {'uuid': dev, 'device_uuid': dev, 'type': 'check'})
        self.assertEqual(res_check_after['data']['status'], 'N', "setAttendance(check) after claiming today must return status 'N'")

    # 2. Star Pass Point cập nhật i_Step khi làm nhiệm vụ & chơi nhạc
    def test_star_pass_step_update(self):
        dev, u_seq, _ = self.create_user()

        # Set user event points close to step 1 threshold (2000 points)
        u = state.get_user(dev)
        u['user_event_point'] = [
            {'s_EventType': 'Pass', 'i_DataID': 13, 'i_Point': 1990, 'i_Step': 0, 'i_ADViewTime': 0, 'i_Version': 13}
        ]
        # Ensure user has daily mission available
        u['daily_mission'] = [{'i_id': 1, 'i_State': 1, 'i_Count': 1}]
        state.save_user(u)

        # Claim daily mission reward (+10 points -> 2000 points = Step 1)
        res_rew = rpc('user.setGameReward', 'setGameReward', {
            'uuid': dev, 'device_uuid': dev, 'type': 'daily_mission', 'id': 1, 'level': 1
        })
        self.assertEqual(res_rew['data']['status'], 'Y')

        u = state.get_user(dev)
        ep = next(x for x in u['user_event_point'] if x.get('s_EventType') == 'Pass')
        self.assertEqual(ep['i_Point'], 2000)
        self.assertEqual(ep['i_Step'], 1, "i_Step must be updated to 1 when points reach 2000")

        # Test music reward (+10 points per song, push from 3990 to 4000 = Step 2)
        ep['i_Point'] = 3990
        ep['i_Step'] = 1
        u['user_music'] = [{'i_id': 1, 'i_Level': 1, 'i_BonusLevel': 0, 'b_EncoreBonusAppear': 1, 'l_EncoreBonusActivateTime': 0, 'i_EncoreBonusFollowerId': 1, 'i_ChThirdActiveTime': 0}]
        state.save_user(u)

        res_music = rpc('user.getMusicReward', 'getMusicReward', {
            'uuid': dev, 'device_uuid': dev, 'idx': [1]
        })
        self.assertIn(1, res_music['data']['reward_music_id'])

        u = state.get_user(dev)
        ep = next(x for x in u['user_event_point'] if x.get('s_EventType') == 'Pass')
        self.assertEqual(ep['i_Point'], 4000)
        self.assertEqual(ep['i_Step'], 2, "i_Step must be updated to 2 when music reward pushes points to 4000")

    # 3. Mua Thẻ Sao đơn lẻ (ID 1013) có reward_type: 10 và đăng ký cả 13 và 1013
    def test_buy_star_pass_single_item(self):
        dev, u_seq, _ = self.create_user()

        # Give CP to buy Thẻ Sao 1013 (cost 150 CP)
        state.increment_currency(dev, cp=500)

        res_buy = rpc('store.buyShop', 'buyShop', {
            'uuid': dev, 'device_uuid': dev, 'idx': 1013
        }, ns='store')
        rewards = res_buy['data'].get('reward_data', [])
        self.assertTrue(any(r.get('reward_type') == 10 and r.get('reward_id') == 1013 for r in rewards),
                        "Rewards must include Star Pass (reward_type: 10, reward_id: 1013)")

        u = state.get_user(dev)
        sub_ids = [s.get('i_SubscribeID') for s in u.get('user_subscribe_list', [])]
        self.assertIn(13, sub_ids, "user_subscribe_list must contain season 13")
        self.assertIn(1013, sub_ids, "user_subscribe_list must contain 1013")

        ticket_ids = [t.get('i_id') for t in u.get('user_ticketcollection', [])]
        self.assertIn(13, ticket_ids, "user_ticketcollection must contain 13")
        self.assertIn(1013, ticket_ids, "user_ticketcollection must contain 1013")

    # 4. Thiếu trường bonus_music_score trong response Chapter 3
    def test_ch_third_stage_bonus_music_score(self):
        dev, u_seq, _ = self.create_user()

        res_stage = rpc('user.chThirdStage', 'chThirdStage', {
            'uuid': dev, 'device_uuid': dev, 'i_id': 1001, 'music_id': 1,
            'costume_id': 1, 'guitar_id': 1, 'selected_profile_ids': [1]
        })
        data = res_stage['data']
        self.assertIn('bonus_music_score', data, "Response data must include bonus_music_score field")
        self.assertIsInstance(data['bonus_music_score'], int)

    # 5. Envelope datetime lệch múi giờ (UTC+9)
    def test_envelope_datetime_timezone(self):
        dev, u_seq, _ = self.create_user()

        res = rpc('main.getServerTime', 'getServerTime', {'call': 'getServerTime'}, ns='main')
        st_data = res['data']
        st_server_time = res['server_time']

        # Both st_data['datetime'] and st_server_time['datetime'] must have same KST date/hour
        data_dt_str = str(st_data['datetime'])
        env_dt_str = str(st_server_time['datetime'])
        self.assertEqual(data_dt_str[:10], env_dt_str[:10],
                         f"Envelope datetime ({env_dt_str}) must match getServerTime datetime ({data_dt_str})")

    # 6. Bổ sung các Handlers cho 5 RPC còn thiếu
    def test_missing_rpcs(self):
        dev, u_seq, _ = self.create_user()

        # A. setReviewPopup
        res_review = rpc('user.setReviewPopup', 'setReviewPopup', {'uuid': dev, 'device_uuid': dev})
        self.assertEqual(res_review['data']['status'], 'Y')
        u = state.get_user(dev)
        self.assertEqual(u.get('userdata', {}).get('u_review_popup'), 'Y')

        # B. setUserFollowerQuest
        res_quest = rpc('user.setUserFollowerQuest', 'setUserFollowerQuest', {
            'uuid': dev, 'device_uuid': dev, 'i_CurrentID': 5, 'i_SubID': 2, 'd_ConditionValue': 3.5
        })
        self.assertEqual(res_quest['data']['i_CurrentID'], 5)
        self.assertEqual(res_quest['data']['d_ConditionValue2'], 3.5)
        u = state.get_user(dev)
        q = next((x for x in u.get('user_follower_quest', []) if x.get('i_CurrentID') == 5), None)
        self.assertIsNotNone(q)
        self.assertEqual(q.get('d_ConditionValue2'), 3.5)

        # C. hibernationLog
        res_hib = rpc('user.hibernationLog', 'hibernationLog', {'uuid': dev, 'device_uuid': dev})
        self.assertEqual(res_hib['data']['action'], 0)

        # D. completeLog
        res_comp = rpc('user.completeLog', 'completeLog', {'uuid': dev, 'device_uuid': dev, 'type': 'test'})
        self.assertEqual(res_comp['data']['status'], '1')

        # E. checkBuyShop
        # For unowned item 1013 (user has not bought it yet)
        res_check1 = rpc('user.checkBuyShop', 'checkBuyShop', {'uuid': dev, 'device_uuid': dev, 'shop_id': '1013'}, ns='store')
        self.assertEqual(res_check1['data']['is_owner'], 0, "Unowned item must return is_owner: 0")

        # Now mark user as owner of Star Pass 13
        u = state.get_user(dev)
        u['user_subscribe_list'] = [{'i_SubscribeID': 13, 'i_ActiveTime': int(time.time()), 'i_isActive': 1}]
        state.save_user(u)

        res_check2 = rpc('user.checkBuyShop', 'checkBuyShop', {'uuid': dev, 'device_uuid': dev, 'shop_id': '1013'}, ns='store')
        self.assertEqual(res_check2['data']['is_owner'], 1, "Owned item must return is_owner: 1")


if __name__ == '__main__':
    unittest.main()

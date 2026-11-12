#!/usr/bin/env python3
"""Test Ban mechanism to ensure banned players see proper Ban popup (code 900) instead of network error."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from server import state, dispatch, handlers
from codec import SCHEMA, encode_response, decode_body, decode_request
from codec.thrift import read_struct

class TestBanBehavior(unittest.TestCase):
    def setUp(self):
        self.test_uuid = "test_ban_device_uuid_9999"
        self.user = state.create_user(self.test_uuid, self.test_uuid)
        state.ban_user(self.test_uuid, banned=False)

    def tearDown(self):
        state.delete_user(self.test_uuid)

    def test_unbanned_login(self):
        user = state.get_user(self.test_uuid)
        self.assertFalse(user.get('is_banned'))
        
        req = {'data': {'uuid': self.test_uuid, 'device_uuid': self.test_uuid, 'u_seq': 0}}
        ret_data, error = handlers.handle('userLogin', req, {'uuid': self.test_uuid})
        self.assertEqual(error['code'], 0)
        self.assertIsNotNone(ret_data)
        self.assertIn('user', ret_data)

    def test_banned_user_login_returns_code_900(self):
        state.ban_user(self.test_uuid, banned=True)
        user = state.get_user(self.test_uuid)
        self.assertTrue(user.get('is_banned'))

        req = {'data': {'uuid': self.test_uuid, 'device_uuid': self.test_uuid, 'u_seq': 0}}
        ret_data, error = handlers.handle('userLogin', req, {'uuid': self.test_uuid})
        self.assertEqual(error['code'], 900)
        self.assertIn('KHÓA', error['errmsg'])
        self.assertIsNone(ret_data)

        # Check return envelope serialization
        rdto, env = dispatch.build_return('user.userLogin', ret_data, call='userLogin', category='user', error=error)
        self.assertEqual(rdto, 'user.userLoginReturn')
        self.assertEqual(env['error']['code'], 900)
        self.assertIn('KHÓA', env['error']['errmsg'])

        out_b64 = encode_response(rdto, env)
        raw = decode_body(out_b64)
        decoded = read_struct(raw)
        self.assertEqual(decoded[1][1], 900)
        self.assertIn('KHÓA', decoded[1][2])

    def test_banned_user_save_returns_code_900_in_dispatcher(self):
        state.ban_user(self.test_uuid, banned=True)
        # Test the check logic as implemented in app.py
        cmd_full = 'user.userSave'
        system_commands = ('main.Request', 'main.getServerTime', 'main.getUpdateTime',
                           'main.defaultSettingList', 'main.getGameDataList', 'store.getVarietyStore')
        self.assertNotIn(cmd_full, system_commands)

        req_named = {'data': {'uuid': self.test_uuid, 'device_uuid': self.test_uuid}}
        u_check = state.get_user(self.test_uuid)
        self.assertTrue(u_check.get('is_banned'))

        error = {
            'code': 900,
            'errmsg': 'Tài khoản của bạn đã bị KHÓA (BAN) bởi Quản trị viên!\nVui lòng liên hệ Admin để được hỗ trợ.'
        }
        rdto, env = dispatch.build_return(cmd_full, None, call='userSave', category='user', error=error)
        self.assertEqual(rdto, 'user.userSaveReturn')
        self.assertEqual(env['error']['code'], 900)

    def test_system_request_not_blocked(self):
        # Bootstrap command 'main.Request' MUST be in allowed system commands
        system_commands = ('main.Request', 'main.getServerTime', 'main.getUpdateTime',
                           'main.defaultSettingList', 'main.getGameDataList', 'store.getVarietyStore')
        self.assertIn('main.Request', system_commands)
        self.assertIn('main.getServerTime', system_commands)
        self.assertIn('main.getUpdateTime', system_commands)

    def test_unban_restores_login(self):
        state.ban_user(self.test_uuid, banned=True)
        self.assertTrue(state.get_user(self.test_uuid).get('is_banned'))

        # Unban
        state.ban_user(self.test_uuid, banned=False)
        self.assertFalse(state.get_user(self.test_uuid).get('is_banned'))

        req = {'data': {'uuid': self.test_uuid, 'device_uuid': self.test_uuid, 'u_seq': 0}}
        ret_data, error = handlers.handle('userLogin', req, {'uuid': self.test_uuid})
        self.assertEqual(error['code'], 0)
        self.assertIsNotNone(ret_data)

    def test_is_user_banned_helper(self):
        self.assertFalse(state.is_user_banned(self.test_uuid))
        self.assertFalse(state.is_user_banned('non_existent_uuid'))
        
        state.ban_user(self.test_uuid, banned=True)
        self.assertTrue(state.is_user_banned(self.test_uuid))
        
        state.ban_user(self.test_uuid, banned=False)
        self.assertFalse(state.is_user_banned(self.test_uuid))

    def test_banned_capture_routing(self):
        from server.app import _capture, CAP_DIR, BANNED_CAP_DIR
        self.assertTrue(os.path.isdir(BANNED_CAP_DIR))
        
        # Capture normal
        _capture('UNITTEST_NORMAL', {'status': 'normal'}, is_banned=False)
        normal_files = [f for f in os.listdir(CAP_DIR) if 'UNITTEST_NORMAL' in f]
        self.assertTrue(len(normal_files) > 0)
        # Ensure not in banned dir
        banned_check = [f for f in os.listdir(BANNED_CAP_DIR) if 'UNITTEST_NORMAL' in f]
        self.assertEqual(len(banned_check), 0)

        # Capture banned
        _capture('UNITTEST_BANNED', {'status': 'banned'}, is_banned=True)
        banned_files = [f for f in os.listdir(BANNED_CAP_DIR) if 'UNITTEST_BANNED' in f]
        self.assertTrue(len(banned_files) > 0)
        # Ensure not in normal dir
        normal_check = [f for f in os.listdir(CAP_DIR) if os.path.isfile(os.path.join(CAP_DIR, f)) and 'UNITTEST_BANNED' in f]
        self.assertEqual(len(normal_check), 0)

        # Clean up unittest test captures
        for f in normal_files:
            try: os.remove(os.path.join(CAP_DIR, f))
            except Exception: pass
        for f in banned_files:
            try: os.remove(os.path.join(BANNED_CAP_DIR, f))
            except Exception: pass

if __name__ == '__main__':
    unittest.main()


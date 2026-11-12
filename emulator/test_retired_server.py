"""Run in a fresh process: python3 -m unittest discover -s emulator -p test_retired_server.py."""
import json
import sys
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request

import codec
from server import dispatch, retired


class RetiredTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = retired.make_server('127.0.0.1', 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_every_known_return_is_an_error_without_game_data(self):
        count = 0
        for command in dispatch.COMMANDS:
            dto = dispatch.return_dto_for(command)
            if not dto:
                continue
            body = urllib.parse.urlencode({'call': command}).encode()
            with urllib.request.urlopen(self.base + '/' + command.replace('.', '/') + '/en/', data=body) as response:
                self.assertEqual(200, response.status)
                result, _ = codec.decode_request(response.read().decode(), dto)
            if command in retired.BOOTSTRAP:
                self.assertEqual(0, result['error']['code'], command)
                self.assertIn('data', result)
            else:
                self.assertEqual(900, result['error']['code'], command)
                self.assertIn(retired.DOWNLOAD_URL, result['error']['errmsg'])
                self.assertNotIn('data', result)
            count += 1
        self.assertGreater(count, 100)

    def test_no_player_modules_loaded(self):
        for module in ('server.state', 'server.auth', 'server.handlers', 'server.app'):
            self.assertNotIn(module, sys.modules)

    def test_auth_admin_and_assets_are_not_available(self):
        for path in ('/api/login', '/admin'):
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(self.base + path, data=b'{}' if path.startswith(('/api/', '/accounts/')) else None)
            self.assertEqual(410, error.exception.code)
            self.assertIn(retired.DOWNLOAD_URL, error.exception.read().decode())

    def test_sdk_bootstrap_is_nonpersistent_then_game_login_is_blocked(self):
        with urllib.request.urlopen(self.base + '/api/accounts/v3/global/login', data=b'device_cd=retired-test') as response:
            self.assertEqual('000', json.load(response)['result_code'])
        with urllib.request.urlopen(self.base + '/user/userLogin/en/', data=b'call=userLogin') as response:
            result, _ = codec.decode_request(response.read().decode(), 'user.userLoginReturn')
        self.assertEqual(900, result['error']['code'])
        self.assertNotIn('data', result)

    def test_health_reports_retired(self):
        with urllib.request.urlopen(self.base + '/health') as response:
            self.assertEqual(False, json.load(response)['gameplay'])

    def test_direct_cached_domain_bootstrap_restores_apk_gateway(self):
        request = urllib.request.Request(self.base + '/main/Request/vi/', data=b'call=Request',
                                         headers={'Host': 'kotori.click', 'X-Forwarded-Proto': 'https'})
        with urllib.request.urlopen(request) as response:
            result, _ = codec.decode_request(response.read().decode(), 'main.initReturn')
        self.assertEqual(0, result['error']['code'])
        self.assertEqual('http://127.0.0.1:28765', result['data']['game_url'])
        self.assertEqual('http://127.0.0.1:28765', result['data']['cdn_url'])


if __name__ == '__main__':
    unittest.main()

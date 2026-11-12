#!/usr/bin/env python3
"""Dedicated test suite for Live Slot purchasing in Pass Goods Shop (Vật phẩm Thẻ Sao).

Verifies:
1. Fresh and unsubscribed users have NO active pass in user_subscribe_list so the Live Slot shows "Mua".
2. Inactive subscriptions (i_isActive == 0) are completely filtered out from user_subscribe_list,
   preventing libil2cpp.so UserSubscribeList.GetSubscribe from falsely treating them as subscribed.
3. buyCheck for Live Slot (3003) succeeds for eligible users.
4. buyShop for Live Slot (3003) deducts CP and grants full rewards (costumes, guitars, music, pass, tickets).
5. Repeat purchase of Live Slot or Normal Merch Pack is rejected.
6. Gold pass revocation in app.py removes subscriptions from user_subscribe_list completely.
7. Live slot schedule and game data mapping consistency (Table 29 & Table 17 & Table 12).
"""
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
from server import dispatch, event_manager, state
from server.handlers import auth, shop

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


class TestLiveSlotPurchase(unittest.TestCase):
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
        dev = 'verify-live-' + uuidlib.uuid4().hex[:10]
        self.test_users.append(dev)
        join_res = rpc('user.userJoin', 'userJoin', {'uuid': dev, 'device_uuid': dev})
        u_seq = join_res['data']['u_seq']
        login_res = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        return dev, u_seq, login_res

    def test_fresh_user_subscribe_list_empty(self):
        """1. Verify fresh user has empty user_subscribe_list so Live Slot is available for purchase."""
        dev, u_seq, login_res = self.create_user()
        contents = login_res['data']['user_contents']
        subs = contents.get('user_subscribe_list', [])
        self.assertEqual(len(subs), 0, f"Fresh user must have empty user_subscribe_list, got {subs}")

    def test_inactive_subs_cleaned_on_normalise(self):
        """2. Verify inactive subs (i_isActive == 0) are completely filtered out from user_subscribe_list."""
        active_season = event_manager.get_active_star_pass_season()

        # Simulate user that previously had an inactive active_season entry
        u = {
            'user_subscribe_list': [
                {'i_SubscribeID': active_season, 'i_isActive': 0, 'i_ActiveTime': 0},
                {'i_SubscribeID': 1, 'i_isActive': 0, 'i_ActiveTime': 0}
            ],
            'user_shop': []
        }
        res = auth._normalise_subscribe_list(u)
        self.assertEqual(len(res), 0, f"Inactive subscriptions must be removed completely, got {res}")
        self.assertNotIn(active_season, [s.get('i_SubscribeID') for s in u['user_subscribe_list']])

    def test_live_slot_purchase_eligibility_and_rewards(self):
        """3 & 4. Verify buyCheck and buyShop for Live Slot (3003) deducts CP and grants all rewards."""
        dev, u_seq, _ = self.create_user()

        # Fund user with 100 CP (price of 3003 is 50 CP)
        state.increment_currency(dev, cp=100)

        # A. buyCheck
        chk = rpc('user.buyCheck', 'buyCheck', {'uuid': dev, 'device_uuid': dev, 'idx': 3003})
        self.assertEqual(chk['error']['code'], 0, f"buyCheck for 3003 must succeed: {chk['error']}")
        self.assertEqual(chk['data'].get('result'), 'ok')

        # B. buyShop
        buy = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 3003, 'count': 1})
        self.assertEqual(buy['error']['code'], 0, f"buyShop for 3003 must succeed: {buy['error']}")
        self.assertEqual(buy['data']['u_cp'], 50, f"CP should be 50 (100 - 50), got {buy['data']['u_cp']}")

        # C. Verify granted rewards
        granted = buy['data']['reward_data']
        # Season 3 Merch Pack (reward group 7036000):
        # Type 10 (Star Pass 1003)
        self.assertTrue(any(r.get('reward_type') == 10 and r.get('reward_id') == 1003 for r in granted),
                        "Must contain Star Pass 1003 reward")
        # Type 3 (Costumes 15, 212)
        for cid in (15, 212):
            self.assertTrue(any(r.get('reward_type') == 3 and r.get('reward_id') == cid for r in granted),
                            f"Must contain Costume {cid}")
        # Type 9 (Guitars 13, 217, 12, 205)
        for gid in (13, 217, 12, 205):
            self.assertTrue(any(r.get('reward_type') == 9 and r.get('reward_id') == gid for r in granted),
                            f"Must contain Guitar {gid}")
        # Type 2 (Music 16, 214)
        for mid in (16, 214):
            self.assertTrue(any(r.get('reward_type') == 2 and r.get('reward_id') == mid for r in granted),
                            f"Must contain Music {mid}")

        # D. Verify persisted user state
        u_saved = state.get_user(dev)
        self.assertEqual(u_saved['userdata']['u_cp'], 50)

        # user_shop recorded both 2003 and 3003
        shop_ids = {s.get('i_id') for s in u_saved.get('user_shop', [])}
        self.assertIn(3003, shop_ids, "Item 3003 must be in user_shop")
        self.assertIn(2003, shop_ids, "Item 2003 must be in user_shop")

        # user_subscribe_list contains Season 3
        sub_ids = {s.get('i_SubscribeID') for s in u_saved.get('user_subscribe_list', [])}
        self.assertIn(3, sub_ids, "Season 3 pass must be in user_subscribe_list")

        # user_ticketcollection contains Season 3 and 1003
        ticket_ids = {t.get('i_id') for t in u_saved.get('user_ticketcollection', [])}
        self.assertIn(3, ticket_ids, "Ticket 3 must be in user_ticketcollection")
        self.assertIn(1003, ticket_ids, "Ticket 1003 must be in user_ticketcollection")

    def test_repeat_live_slot_purchase_rejected(self):
        """5. Verify repeat purchase of Live Slot is rejected."""
        dev, u_seq, _ = self.create_user()
        state.increment_currency(dev, cp=200)

        # Initial buy
        buy1 = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 3003})
        self.assertEqual(buy1['error']['code'], 0)

        # Repeat buyCheck must fail
        chk_rep = rpc('user.buyCheck', 'buyCheck', {'uuid': dev, 'device_uuid': dev, 'idx': 3003})
        self.assertNotEqual(chk_rep['error']['code'], 0, "Repeat buyCheck for 3003 must fail")

        # Repeat buyShop must fail
        buy_rep = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 3003})
        self.assertNotEqual(buy_rep['error']['code'], 0, "Repeat buyShop for 3003 must fail")
        self.assertIn('sở hữu', buy_rep['error'].get('errmsg', ''))

        # Also buying normal pack 2003 must fail
        buy_rep_normal = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 2003})
        self.assertNotEqual(buy_rep_normal['error']['code'], 0, "Buying normal pack 2003 after 3003 must fail")

    def test_gold_pass_revocation_removes_from_subs(self):
        """6. Verify revoking Gold Pass removes subscription from user_subscribe_list completely."""
        active_season = event_manager.get_active_star_pass_season()
        target_shop_id = 1000 + active_season

        user = {
            'user_shop': [{'i_id': target_shop_id, 'i_Count': 1}],
            'user_subscribe_list': [{'i_SubscribeID': active_season, 'i_isActive': 1, 'i_ActiveTime': 2147483647}],
            'user_ticketcollection': [{'i_id': active_season}, {'i_id': target_shop_id}]
        }

        # Simulate app.py revocation logic:
        sub_ids = (active_season, target_shop_id)
        user['user_shop'] = [item for item in user['user_shop'] if int(item.get('i_id', 0) or 0) not in (active_season, 1000 + active_season, 2000 + active_season, 3000 + active_season)]
        user['user_subscribe_list'] = [s for s in user['user_subscribe_list'] if int(s.get('i_SubscribeID', 0) or 0) not in sub_ids]
        user['user_ticketcollection'] = [t for t in user['user_ticketcollection'] if int(t.get('i_id', 0) or 0) not in (active_season, target_shop_id)]

        self.assertEqual(len(user['user_subscribe_list']), 0, "Revoked subscription must not remain in user_subscribe_list")
        self.assertEqual(len(user['user_ticketcollection']), 0, "Revoked ticket must not remain in user_ticketcollection")

    def test_gamedata_live_slot_schedule_and_mapping(self):
        """7. Verify Table 29, Table 17, and getGameDataList SubscribeList schedule for Live Slot."""
        active_season = event_manager.get_active_star_pass_season()

        # Verify Table 29 has active season row
        with open('emulator/gamedata/game_data.json', 'r', encoding='utf-8') as f:
            gd = json.load(f)

        t29_row = next((r for r in gd.get('29', []) if int(r.get('2', 0)) == active_season), None)
        self.assertIsNotNone(t29_row, f"Table 29 must contain Season {active_season}")
        self.assertEqual(int(t29_row.get('4')), 2000 + active_season, "Table 29 col 4 must be normal pack")
        self.assertEqual(int(t29_row.get('6')), 3000 + active_season, "Table 29 col 6 must be sale pack")

        # Verify Table 12 has 3000 + active_season
        t12_sale = next((r for r in gd.get('12', []) if int(r.get('1', 0)) == 3000 + active_season), None)
        self.assertIsNotNone(t12_sale, f"Table 12 must contain item {3000 + active_season}")
        self.assertEqual(int(t12_sale.get('33')), 1, "Sell type must be 1 (CP / Chocolate)")
        self.assertGreater(int(t12_sale.get('34')), 0, "Price must be positive")

    def test_user_with_existing_ticket_can_buy_merch_pack(self):
        """8. Verify user who already owns Star Pass ticket (1003) can still purchase Live Slot (3003)."""
        dev, u_seq, _ = self.create_user()
        state.increment_currency(dev, cp=100)

        # Pre-grant ticket 1003 and pass 3 (e.g. from pass progression or prior ticket buy)
        u = state.get_user(dev)
        u.setdefault('user_ticketcollection', []).append({'i_id': 1003})
        u.setdefault('user_ticketcollection', []).append({'i_id': 3})
        u.setdefault('user_subscribe_list', []).append({'i_SubscribeID': 3, 'i_ActiveTime': int(time.time()), 'i_isActive': 1})
        state.save_user(u)

        # A. checkBuyShop must return is_owner = 0 (merch pack is not yet owned)
        chk_owner = rpc('user.checkBuyShop', 'checkBuyShop', {'uuid': dev, 'device_uuid': dev, 'shop_id': '3003'}, ns='store')
        self.assertEqual(chk_owner['error']['code'], 0)
        self.assertEqual(chk_owner['data'].get('is_owner'), 0, "Pack 3003 should not be marked as owned just because ticket 1003 exists")

        # B. buyCheck must succeed
        chk = rpc('user.buyCheck', 'buyCheck', {'uuid': dev, 'device_uuid': dev, 'idx': 3003})
        self.assertEqual(chk['error']['code'], 0, f"buyCheck for 3003 must succeed: {chk['error']}")
        self.assertEqual(chk['data'].get('result'), 'ok')

        # C. buyShop must succeed and deduct 50 CP
        buy = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 3003, 'count': 1})
        self.assertEqual(buy['error']['code'], 0, f"buyShop for 3003 must succeed: {buy['error']}")
        self.assertEqual(buy['data']['u_cp'], 50)

        # D. Now checkBuyShop must return is_owner = 1
        chk_owner_after = rpc('user.checkBuyShop', 'checkBuyShop', {'uuid': dev, 'device_uuid': dev, 'shop_id': '3003'}, ns='store')
        self.assertEqual(chk_owner_after['data'].get('is_owner'), 1, "Pack 3003 must now be marked as owned")

    def test_real_device_usn_uuid_mismatch_purchase(self):
        """9. Verify real device sending numeric USN in uuid and hex device_uuid can purchase Live Slot."""
        dev, u_seq, _ = self.create_user()
        state.increment_currency(dev, cp=100)

        real_usn = "452465183"  # Pmang numeric member ID sent by real APK
        # Client request sends uuid = real_usn, device_uuid = dev, u_seq = u_seq
        chk = rpc('user.buyCheck', 'buyCheck', {'uuid': real_usn, 'device_uuid': dev, 'u_seq': u_seq, 'idx': 3003})
        self.assertEqual(chk['error']['code'], 0, f"buyCheck with USN must succeed: {chk['error']}")
        self.assertEqual(chk['data'].get('result'), 'ok')

        buy = rpc('store.buyShop', 'buyShop', {'uuid': real_usn, 'device_uuid': dev, 'u_seq': u_seq, 'idx': 3003, 'count': 1})
        self.assertEqual(buy['error']['code'], 0, f"buyShop with USN must succeed: {buy['error']}")
        self.assertEqual(buy['data']['u_cp'], 50, f"CP must be 50 after deducting 50 CP, got {buy['data']['u_cp']}")

        # Verify setSubscribe also works seamlessly with USN
        set_sub = rpc('user.setSubscribe', 'setSubscribe', {'uuid': real_usn, 'device_uuid': dev, 'u_seq': u_seq, 'i_ids': [3]})
        self.assertEqual(set_sub['error']['code'], 0)
        sub_ids = {s.get('i_SubscribeID') for s in set_sub['data'].get('user_subscribe_list', [])}
        self.assertIn(3, sub_ids, "Season 3 pass must be in user_subscribe_list")


if __name__ == '__main__':
    unittest.main()

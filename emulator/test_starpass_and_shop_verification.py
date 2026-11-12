#!/usr/bin/env python3
"""Dedicated Verification Test Suite for GGServer.

Verifies:
1. Table 17 Season 13 StartYear is 2021 (not 2026) so it is not treated as a broken live slot.
2. Season 13 Pass Goods item 3013 purchase via buyShop deducting 200 CP and properly granting rewards.
3. Insufficient CP rejection for Star Pass purchases.
4. General Shop does not show Star Pass items (Category 0).
5. Attendance 7-day popup and Chapter 3 tutorial pointing behavior.
"""
import io
import json
import os
import sys
import unittest
import urllib.request
import uuid as uuidlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codec
from server import dispatch, state

SERVER = os.environ.get('GG_TEST_URL', 'http://127.0.0.1:8080')
GAME_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gamedata', 'game_data.json')


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


def fetch_gamedata_rpc():
    boundary, body = _multipart({'call': 'getGameDataList', 'tapsonic_data': 'x'})
    req = urllib.request.Request(
        f'{SERVER}/main/getGameDataList/en/',
        data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'}
    )
    raw = urllib.request.urlopen(req, timeout=10).read().decode()
    named, _ = codec.decode_request(raw, 'main.getGameDataListReturn')
    return named.get('data', {}).get('ret', {})


class TestGGServerFeatures(unittest.TestCase):
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
        dev = 'verify-' + uuidlib.uuid4().hex[:10]
        self.test_users.append(dev)
        join_res = rpc('user.userJoin', 'userJoin', {'uuid': dev, 'device_uuid': dev})
        u_seq = join_res['data']['u_seq']
        login_res = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        return dev, u_seq, login_res

    # =========================================================================
    # 1. Table 17 Season 13 StartYear is 2021 (not 2026)
    # =========================================================================
    def test_table17_season13_startyear(self):
        """Verify Table 17 Season 13 StartYear is 2021 (not 2026)."""
        # A. Check raw game_data.json
        with open(GAME_DATA_PATH, 'r', encoding='utf-8') as f:
            gd = json.load(f)

        table_17 = gd.get('17', [])
        self.assertGreater(len(table_17), 0, "Table 17 in game_data.json must not be empty")

        s13_raw = next((r for r in table_17 if int(r.get('1', 0)) == 13), None)
        self.assertIsNotNone(s13_raw, "Season 13 must exist in Table 17")
        self.assertEqual(int(s13_raw.get('11', 0)), 2021,
                         f"Table 17 Season 13 StartYear in game_data.json must be 2021, got {s13_raw.get('11')}")
        self.assertNotEqual(int(s13_raw.get('11', 0)), 2026,
                            "Table 17 Season 13 StartYear must NOT be 2026 (broken live slot)")
        self.assertEqual(int(s13_raw.get('12', 0)), 6, "Season 13 RepeatMonth must be 6")
        self.assertEqual(int(s13_raw.get('13', 0)), 1, "Season 13 MonthGroupIndex must be 1")

        # B. Check live RPC response from running server
        rpc_data = fetch_gamedata_rpc()
        subscribe_list = rpc_data.get('SubscribeList', [])
        self.assertGreater(len(subscribe_list), 0, "getGameDataList SubscribeList must not be empty")

        s13_rpc = next((s for s in subscribe_list if s.get('i_id') == 13), None)
        self.assertIsNotNone(s13_rpc, "Season 13 must be returned in getGameDataList SubscribeList")
        self.assertEqual(s13_rpc.get('i_StartYear'), 2021,
                         f"RPC Season 13 i_StartYear must be 2021, got {s13_rpc.get('i_StartYear')}")
        self.assertNotEqual(s13_rpc.get('i_StartYear'), 2026,
                            "RPC Season 13 i_StartYear must NOT be 2026")
        self.assertIn(s13_rpc.get('b_IsActive'), (0, 1), "Season 13 b_IsActive must be binary 0 or 1")
        active_seasons = [s for s in subscribe_list if s.get('b_IsActive') == 1]
        self.assertEqual(len(active_seasons), 1, "Exactly one season should be marked active")

        # Verify all seasons 1-13 have historic StartYear <= 2021
        for s in subscribe_list:
            sid = s.get('i_id')
            syear = s.get('i_StartYear')
            self.assertIn(syear, (2020, 2021),
                          f"Season {sid} StartYear {syear} should be historic (2020 or 2021), not future year")

    # =========================================================================
    # 2. Season 13 Pass Goods item 3013 purchase via buyShop deducting 200 CP
    #    and properly granting rewards
    # =========================================================================
    def test_pass_goods_3013_purchase_and_rewards(self):
        """Verify purchasing item 3013 deducts 200 CP and grants full rewards."""
        dev, u_seq, _ = self.create_user()

        # Fund user with 300 CP
        state.increment_currency(dev, cp=300)
        u = state.get_user(dev)
        u['userdata']['u_cp'] = 300
        state.save_user(u)

        # Baseline checks
        self.assertEqual(state.get_user(dev)['userdata']['u_cp'], 300)
        self.assertFalse(any(x.get('i_id') == 3013 for x in u.get('user_shop', [])))

        # Buy item 3013 (Season 13 Pass Goods Pack, price 200 CP)
        res = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 3013})
        self.assertEqual(res['error']['code'], 0, f"buyShop 3013 must succeed, got {res['error']}")
        self.assertEqual(res['data']['u_cp'], 100, f"Returned CP must be 100 (300 - 200), got {res['data']['u_cp']}")

        # Verify reward items in response
        granted_rewards = res['data']['reward_data']
        self.assertGreater(len(granted_rewards), 0, "Reward data must not be empty")

        # Reward group 7136000 components:
        # Type 10 (Star Pass): 1013
        self.assertTrue(any(r.get('reward_type') == 10 and r.get('reward_id') == 1013 for r in granted_rewards),
                        "Must contain Star Pass 1013 reward")
        # Type 3 (Costumes): 32, 229
        self.assertTrue(any(r.get('reward_type') == 3 and r.get('reward_id') == 32 for r in granted_rewards),
                        "Must contain Costume 32 reward")
        self.assertTrue(any(r.get('reward_type') == 3 and r.get('reward_id') == 229 for r in granted_rewards),
                        "Must contain Costume 229 reward")
        # Type 9 (Guitars): 39, 40, 245, 246
        for gid in (39, 40, 245, 246):
            self.assertTrue(any(r.get('reward_type') == 9 and r.get('reward_id') == gid for r in granted_rewards),
                            f"Must contain Guitar {gid} reward")
        # Type 2 (Music): 26, 224
        for mid in (26, 224):
            self.assertTrue(any(r.get('reward_type') == 2 and r.get('reward_id') == mid for r in granted_rewards),
                            f"Must contain Music {mid} reward")

        # Verify persisted user state
        u_saved = state.get_user(dev)
        self.assertEqual(u_saved['userdata']['u_cp'], 100, "Persisted CP must be 100")

        # User shop record
        shop_rec = next((x for x in u_saved.get('user_shop', []) if x.get('i_id') == 3013), None)
        self.assertIsNotNone(shop_rec, "Item 3013 must be recorded in user_shop")
        self.assertEqual(shop_rec.get('i_Count'), 1, "Item 3013 count must be 1")

        # Star Pass subscription
        self.assertTrue(any(s.get('i_SubscribeID') in (13, 1013) for s in u_saved.get('user_subscribe_list', [])),
                        "user_subscribe_list must include Season 13 pass")

        # Ticket collection
        self.assertTrue(any(t.get('i_id') == 13 for t in u_saved.get('user_ticketcollection', [])),
                        "user_ticketcollection must include Season 13 ticket")

        # Owned Guitars
        guitar_ids = {g.get('i_id') for g in u_saved.get('user_guitar', [])}
        for gid in (39, 40, 245, 246):
            self.assertIn(gid, guitar_ids, f"Guitar {gid} must be owned in user_guitar")

        # Owned Costumes
        costume_ids = {c.get('i_id') for c in u_saved.get('costumes', [])}
        for cid in (32, 229):
            self.assertIn(cid, costume_ids, f"Costume {cid} must be owned in costumes")

        # Owned Music
        music_ids = {m.get('i_id') for m in u_saved.get('user_music', [])}
        for mid in (26, 224):
            self.assertIn(mid, music_ids, f"Music {mid} must be owned in user_music")

    # =========================================================================
    # 3. Insufficient CP rejection for Star Pass purchases
    # =========================================================================
    def test_insufficient_cp_rejection(self):
        """Verify Star Pass purchases reject when CP is insufficient."""
        dev, u_seq, _ = self.create_user()

        # Case A: 0 CP user tries to buy Star Pass 1013 (price 150 CP)
        res_0 = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 1013})
        self.assertNotEqual(res_0['error']['code'], 0, "Buying Star Pass 1013 with 0 CP must fail")
        self.assertIn('Socola', res_0['error']['errmsg'], "Error message must indicate insufficient Socola")

        u = state.get_user(dev)
        self.assertEqual(u['userdata']['u_cp'], 0, "CP must remain 0")
        self.assertFalse(any(s.get('i_SubscribeID') == 1013 for s in u.get('user_subscribe_list', [])),
                         "Star Pass 1013 must not be granted")

        # Case B: User has 100 CP, tries to buy Season 13 Pass Goods 3013 (price 200 CP)
        state.set_currency(dev, cp=100, candy=0.0)

        res_partial = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 3013})
        self.assertNotEqual(res_partial['error']['code'], 0,
                            "Buying Pass Goods 3013 with 100 CP (price 200 CP) must fail")
        self.assertIn('Socola', res_partial['error']['errmsg'])

        u2 = state.get_user(dev)
        self.assertEqual(u2['userdata']['u_cp'], 100, "CP must remain 100 after rejected purchase")
        self.assertFalse(any(x.get('i_id') == 3013 for x in u2.get('user_shop', [])),
                         "Item 3013 must not be in user_shop")
        self.assertFalse(any(s.get('i_SubscribeID') in (13, 1013) for s in u2.get('user_subscribe_list', [])),
                         "Pass 13/1013 must not be granted")

        # Case C: User tries to buy Star Pass 1001 (price 50 CP) with insufficient CP (e.g. 20 CP)
        state.set_currency(dev, cp=20, candy=0.0)
        res_1001 = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 1001})
        self.assertNotEqual(res_1001['error']['code'], 0, "Buying Pass 1001 with 20 CP (price 50) must fail")

    # =========================================================================
    # 4. General Shop does not show Star Pass items (Category 0)
    # =========================================================================
    def test_general_shop_excludes_category_0_starpass(self):
        """Verify General Shop items (Category 1) do not include Star Pass items (Category 0)."""
        rpc_data = fetch_gamedata_rpc()
        shop_table = rpc_data.get('shop', [])
        self.assertGreater(len(shop_table), 0, "Shop table must not be empty")

        # Separate items by Category
        category_0_items = [item for item in shop_table if item.get('i_ShopCategory') == 0]
        general_shop_items = [item for item in shop_table if item.get('i_ShopCategory') == 1]
        category_3_items = [item for item in shop_table if item.get('i_ShopCategory') == 3]

        # 1. Verify Category 0 contains Star Pass items (1001 - 1013)
        cat0_ids = [item.get('i_id') for item in category_0_items]
        self.assertEqual(len(cat0_ids), 13, f"Category 0 should contain exactly 13 Star Pass items, got {len(cat0_ids)}")
        for s_idx in range(1001, 1014):
            self.assertIn(s_idx, cat0_ids, f"Star Pass item {s_idx} must belong to Category 0")

        # 2. Verify General Shop (Category 1) contains ONLY non-Star-Pass items
        gen_ids = [item.get('i_id') for item in general_shop_items]
        for s_idx in range(1001, 1014):
            self.assertNotIn(s_idx, gen_ids,
                             f"Star Pass item {s_idx} must NOT appear in General Shop (Category 1)")

        # Verify no items in General Shop have Category == 0
        for item in general_shop_items:
            self.assertEqual(item.get('i_ShopCategory'), 1,
                             f"General shop item {item.get('i_id')} must have Category 1")

        # 3. Check raw game_data.json Table 12
        with open(GAME_DATA_PATH, 'r', encoding='utf-8') as f:
            gd = json.load(f)
        table_12 = gd.get('12', [])

        raw_cat0 = [r for r in table_12 if int(r.get('4', -1)) == 0]
        raw_cat1 = [r for r in table_12 if int(r.get('4', -1)) == 1]

        raw_cat0_ids = {int(r.get('1')) for r in raw_cat0}
        raw_cat1_ids = {int(r.get('1')) for r in raw_cat1}

        self.assertTrue(all(1001 <= i <= 1013 for i in raw_cat0_ids),
                        "All raw Category 0 items must be Star Pass IDs 1001-1013")
        self.assertTrue(raw_cat0_ids.isdisjoint(raw_cat1_ids),
                        "Category 0 and General Shop Category 1 item IDs must be completely disjoint")

    # =========================================================================
    # 5. Attendance 7-day popup and Chapter 3 tutorial pointing behavior
    # =========================================================================
    def test_attendance_7day_popup_flow(self):
        """Verify Attendance 7-day popup check/add and claim flow."""
        dev, u_seq, _ = self.create_user()

        # Step 1: Client performs setAttendance(check) upon login
        chk_res = rpc('user.setAttendance', 'setAttendance', {'uuid': dev, 'device_uuid': dev, 'type': 'check'})
        self.assertEqual(chk_res['data']['status'], 'Y', "Fresh user setAttendance(check) must return status 'Y'")
        self.assertEqual(chk_res['data']['attendance_count'], 1, "Fresh user attendance_count must be 1 (Day 1)")

        # Step 2: Client inspects getEventRewardList board
        ev_list = rpc('main.getEventRewardList', 'getEventRewardList', {'uuid': dev, 'device_uuid': dev})
        board1 = ev_list['data'].get(1) or ev_list['data'].get('1', {})
        self.assertIn('reward_list', board1, "Event board 1 must have reward_list")
        day1_slot = next((r for r in board1['reward_list'] if r.get('reward_num') == 1), None)
        self.assertIsNotNone(day1_slot, "Day 1 slot must exist in board 1")
        self.assertEqual(day1_slot.get('reward_flg'), 'Y', "Day 1 must be available to claim (reward_flg 'Y')")
        self.assertEqual(day1_slot.get('get_date'), 0, "Unclaimed Day 1 must have get_date == 0")

        # Step 3: Login process executes setAttendance(add)
        add_res = rpc('user.setAttendance', 'setAttendance', {'uuid': dev, 'device_uuid': dev, 'type': 'add'})
        self.assertEqual(add_res['data']['status'], 'Y', "setAttendance(add) must record today's attendance")

        # Step 4: Player views 7-day attendance popup and claims Day 1
        claim_res = rpc('user.setEventReward', 'setEventReward', {'uuid': dev, 'device_uuid': dev, 'event_idx': 1})
        self.assertEqual(claim_res['data']['status'], 'Y', "setEventReward must succeed with status 'Y'")
        self.assertEqual(claim_res['data']['reward_type'], 1, "Day 1 reward_type must be 1 (Goods/CP)")
        self.assertEqual(claim_res['data']['reward_id'], 1, "Day 1 reward_id must be 1 (Socola/CP)")
        self.assertEqual(claim_res['data']['reward_value'], 100, "Day 1 reward_value must be 100 CP")
        self.assertEqual(claim_res['data']['u_cp'], 100, "User's CP must reflect +100 CP")

        # Step 5: Duplicate claim on the same day must be rejected
        dup_claim = rpc('user.setEventReward', 'setEventReward', {'uuid': dev, 'device_uuid': dev, 'event_idx': 1})
        self.assertEqual(dup_claim['data']['status'], 'N', "Duplicate same-day claim must return status 'N'")
        self.assertEqual(dup_claim['data']['reward_value'], 0, "Duplicate claim reward_value must be 0")
        self.assertEqual(dup_claim['data']['u_cp'], 100, "User's CP must remain unchanged at 100")

        # Step 6: Board now shows Day 1 as received, future days unclaimed
        ev_list_after = rpc('main.getEventRewardList', 'getEventRewardList', {'uuid': dev, 'device_uuid': dev})
        board1_after = ev_list_after['data'].get(1) or ev_list_after['data'].get('1', {})
        day1_after = next((r for r in board1_after['reward_list'] if r.get('reward_num') == 1), None)
        self.assertEqual(day1_after.get('reward_flg'), 'N', "Claimed Day 1 must have reward_flg 'N'")
        self.assertNotEqual(day1_after.get('get_date'), 0, "Claimed Day 1 must have valid get_date")
        day2_after = next((r for r in board1_after['reward_list'] if r.get('reward_num') == 2), None)
        self.assertEqual(day2_after.get('reward_flg'), 'Y', "Day 2 must remain unclaimed")
        self.assertEqual(day2_after.get('get_date'), 0, "Day 2 get_date must be 0")

        # Step 7: Subsequent setAttendance(check) today returns 'N' (popup dismissed)
        chk_res2 = rpc('user.setAttendance', 'setAttendance', {'uuid': dev, 'device_uuid': dev, 'type': 'check'})
        self.assertEqual(chk_res2['data']['status'], 'N',
                         "setAttendance(check) after claiming today must return 'N'")

    def test_chapter3_tutorial_pointing_behavior(self):
        """Verify Chapter 3 tutorial pointing behavior and progression persistence."""
        dev, u_seq, login_res = self.create_user()

        # Step 1: Verify starter tutorial and Chapter 3 initial state in userLogin
        contents = login_res['data']['user_contents']
        tut_list = contents.get('user_tutorial', [])
        initial_tut_ids = {t.get('i_id') for t in tut_list}
        self.assertTrue(set(range(1, 8)).issubset(initial_tut_ids),
                        f"Starter tutorials 1-7 must be pre-unlocked to avoid replaying intro: got {initial_tut_ids}")

        # Chapter 3 stages start empty [] so Moa tutorial triggers properly (BUG.md Section 4.13)
        ch3_stages = contents.get('user_chthird_stage', [])
        self.assertEqual(ch3_stages, [], "Fresh user ch3 stages must start empty [] for Moa tutorial")

        # Step 2: Client completes Chapter 3 tutorial (Tutorial 14) and sends setTutorialNew
        tut_res = rpc('user.setTutorialNew', 'setTutorialNew', {'uuid': dev, 'device_uuid': dev, 'i_ids': [14]})
        self.assertEqual(tut_res['error']['code'], 0, "setTutorialNew must succeed")
        returned_tut_ids = {t.get('i_id') for t in tut_res['data']['tutorial']}
        self.assertIn(14, returned_tut_ids, "setTutorialNew response must contain tutorial 14")

        # Step 3: Relogin confirms tutorial 14 is permanently persisted
        relogin = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        relogin_tut_ids = {t.get('i_id') for t in relogin['data']['user_contents']['user_tutorial']}
        self.assertIn(14, relogin_tut_ids, "Tutorial 14 must be persisted across relogin")

        # Step 4: Playing Chapter 3 Tutorial Stage (1001) via chThirdStage clears with 3 stars
        stg_res = rpc('user.chThirdStage', 'chThirdStage', {
            'uuid': dev, 'device_uuid': dev, 'i_id': 1001, 'music_id': 1, 'profile_ids': '1'
        })
        self.assertEqual(stg_res['error']['code'], 0, "chThirdStage 1001 must succeed")
        self.assertEqual(stg_res['data']['clear'], 1, "Stage 1001 must clear successfully")
        self.assertEqual(stg_res['data']['star'], 3, "Stage 1001 must award 3 stars (tutorial stage rule)")
        self.assertEqual(stg_res['data']['user_ch_third_stage']['i_Star'], 3,
                         "Updated user_ch_third_stage must maintain 3 stars")

    def test_starpass_merch_pack_ticket_collection_and_no_repeat_buy(self):
        """Merch pack purchase grants Table 22 PASS_GOODS tickets (1000+S) and prevents repeat buy."""
        dev, u_seq, _ = self.create_user()

        state.increment_currency(dev, cp=500)
        u = state.get_user(dev)
        u['userdata']['u_cp'] = 500
        state.save_user(u)

        # 1. Purchase Season 3 merch pack (2003)
        chk = rpc('user.buyCheck', 'buyCheck', {'uuid': dev, 'device_uuid': dev, 'idx': 2003})
        self.assertEqual(chk['error']['code'], 0, f"buyCheck for 2003 must succeed: {chk['error']}")

        buy = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 2003, 'count': 1})
        self.assertEqual(buy['error']['code'], 0, f"buyShop for 2003 must succeed: {buy['error']}")

        # 2. Verify tickets in user record
        u_saved = state.get_user(dev)
        tickets = [t.get('i_id') for t in u_saved.get('user_ticketcollection', [])]
        self.assertIn(3, tickets, "Season 3 ticket (3) must be in user_ticketcollection")
        self.assertIn(1003, tickets, "Season 3 merch illustration ticket (1003) must be in user_ticketcollection")

        subs = [s.get('i_SubscribeID') for s in u_saved.get('user_subscribe_list', [])]
        self.assertIn(3, subs, "Season 3 pass must be in user_subscribe_list")
        self.assertIn(1003, subs, "Season 3 merch pass must be in user_subscribe_list")

        # 3. Prevent repeat purchase
        chk_repeat = rpc('user.buyCheck', 'buyCheck', {'uuid': dev, 'device_uuid': dev, 'idx': 2003})
        self.assertNotEqual(chk_repeat['error']['code'], 0, "Repeat purchase of 2003 must be rejected")
        self.assertIn('sở hữu', chk_repeat['error'].get('errmsg', ''))

        chk_repeat_3003 = rpc('user.buyCheck', 'buyCheck', {'uuid': dev, 'device_uuid': dev, 'idx': 3003})
        self.assertNotEqual(chk_repeat_3003['error']['code'], 0, "Repeat purchase of 3003 must be rejected")

        # 4. Verify login payload returns both tickets to client
        login_res = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        self.assertEqual(login_res['error']['code'], 0)
        login_tickets = [t.get('i_id') for t in login_res['data']['user_contents']['user_ticketcollection']]
        self.assertIn(3, login_tickets, "userLogin must return ticket 3")
        self.assertIn(1003, login_tickets, "userLogin must return ticket 1003")


def main():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestGGServerFeatures)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == '__main__':
    main()

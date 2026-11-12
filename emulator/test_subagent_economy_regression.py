#!/usr/bin/env python3
"""Comprehensive QA & Regression Test Suite for Guitar Girl Emulator Economy Systems.

Systems Tested:
1. Follower Gifting ("Ký ức của chúng ta" / Our Memories - Ad Gift ID 1):
   - 5 claims daily limit (DAY_LIMIT: 5)
   - Cooldown 600s (COOLTIME: 600)
   - Rejection after 5 claims or when on cooldown
   - Slot 1 (Gingerbread) and Slot 2 (Favorite gifts): inventory deduction, no infinite gifting
   - Follower profile level progression is strictly independent of stage level
2. Mailbox (user_post / openPost / delPost):
   - Opening post grants items and marks claimed (have_reward=0, status=1, flg=1)
   - Deleting post permanently removes it; relogging does NOT resurrect deleted or claimed posts
3. Shop & Star Pass:
   - Season 13 Merch pack (3013) purchase costs 200 CP, grants pass goods tickets (1013, 13)
   - Cannot purchase non-repeatable packs again
   - Category 0 goods excluded from general store
   - Insufficient CP rejection
4. Attendance & Daily Missions:
   - 7-day attendance progression, board rollover, duplicate claim prevention
   - Daily mission new day rollover, attendance mission 1 auto-completion, mission 6 sync with 1..5
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
from server import dispatch, state
from server.handlers.post import send_post

SERVER = os.environ.get('GG_TEST_URL', 'http://127.0.0.1:8080')
GAME_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gamedata', 'game_data.json')

# 7-day Attendance (Event 1) canonical rewards: Day -> (reward_type, reward_id, reward_value)
# Day 1: 100 CP, Day 2: Costume 9, Day 3: 200 CP, Day 4: 50 Candy, Day 5: 300 CP, Day 6: 50 Candy, Day 7: Music 13
EV1_DAYS = {
    1: (1, 1, 100),
    2: (3, 9, 1),
    3: (1, 1, 200),
    4: (1, 2, 50),
    5: (1, 1, 300),
    6: (1, 2, 50),
    7: (2, 13, 1),
}


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


def rpc(cmd_full, call, data, ns=None, lang='vi'):
    env = {'call': call, 'data': data, 'common_data': {'client_ver': 800, 'type': 'aos', 'os': 1}}
    b64 = codec.encode_response(cmd_full, env)
    boundary, body = _multipart({'call': call, 'tapsonic_data': b64, 'access_token': '', 'current_time': '0'})
    endpoint_ns = ns or cmd_full.split('.')[0]
    req = urllib.request.Request(
        f'{SERVER}/{endpoint_ns}/{call}/{lang}/',
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


class BaseEconomyTestCase(unittest.TestCase):
    def setUp(self):
        self.created_users = []

    def tearDown(self):
        for dev in self.created_users:
            try:
                conn = state.get_db()
                conn.execute('DELETE FROM user_data WHERE uuid = ?', (dev,))
                conn.execute('DELETE FROM user_inventory WHERE uuid = ?', (dev,))
                conn.commit()
                conn.close()
            except Exception:
                pass

    def create_account(self, prefix='eco-test'):
        dev = f'{prefix}-' + uuidlib.uuid4().hex[:10]
        self.created_users.append(dev)
        join_res = rpc('user.userJoin', 'userJoin', {'uuid': dev, 'device_uuid': dev})
        self.assertEqual(join_res['error']['code'], 0, f"userJoin must succeed: {join_res}")
        u_seq = join_res['data']['u_seq']
        login_res = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        self.assertEqual(login_res['error']['code'], 0, f"userLogin must succeed: {login_res}")
        return dev, u_seq, login_res


# =============================================================================
# 1. FOLLOWER GIFTING REGRESSION
# =============================================================================
class TestFollowerGiftingRegression(BaseEconomyTestCase):
    """Test Follower Gifting regression: Ad Gift ID 1 limit/cooldown, Slot 1/2 inventory deduction,
    prevention of infinite gifting, and stage level independence."""

    def test_ad_gift_cooldown_and_rejection(self):
        """Ad Gift ID 1 ('Ký ức của chúng ta') grants EXP on first claim, but rejects claims during 600s cooldown."""
        dev, u_seq, login_res = self.create_account('fg-cool')

        # Follower 1 (Joy): initial profile
        profiles = login_res['data']['user_contents'].get('user_follower_profile', [])
        p1 = next((p for p in profiles if p.get('i_id') == 1), None)
        self.assertIsNotNone(p1, "Follower 1 profile should exist")
        init_exp = int(p1.get('d_Exp', 0))

        # 1. First claim: succeeds, grants EXP (100..300), count increments to 1, sets last view time
        c1 = rpc('user.setAdReward', 'setAdReward', {'uuid': dev, 'device_uuid': dev, 'i_id': 1, 'param1': '1'})
        self.assertEqual(c1['error']['code'], 0)
        c1_data = c1['data']
        self.assertEqual(c1_data['user_ad_list']['i_id'], 1)
        self.assertEqual(c1_data['user_ad_list']['i_Count'], 1)
        self.assertGreater(c1_data['user_ad_list']['i_LastViewTime'], 0)
        rewards = c1_data.get('reward_data', [])
        self.assertEqual(len(rewards), 1, "First ad claim must grant reward")
        granted_exp = rewards[0]['reward_value']
        self.assertGreaterEqual(granted_exp, 100)
        self.assertEqual(c1_data['user_follower_profile']['d_Exp'], init_exp + granted_exp)

        # 2. Second claim immediately (cooldown active: <600s): must be REJECTED!
        c2 = rpc('user.setAdReward', 'setAdReward', {'uuid': dev, 'device_uuid': dev, 'i_id': 1, 'param1': '1'})
        self.assertEqual(c2['error']['code'], 0)
        c2_data = c2['data']
        self.assertEqual(c2_data['user_ad_list']['i_Count'], 1, "Count must stay 1 while on cooldown")
        self.assertEqual(len(c2_data.get('reward_data', [])), 0, "Claim during cooldown must return empty reward_data")
        self.assertEqual(c2_data['user_follower_profile']['d_Exp'], init_exp + granted_exp, "EXP must NOT increase during cooldown")

        # 3. Simulate elapsed cooldown (rewind i_LastViewTime by 601s)
        u = state.get_user(dev)
        u['ad_rewards']['1']['i_LastViewTime'] = int(time.time()) - 601
        state.save_user(u)

        # 4. Third claim (cooldown now elapsed): succeeds!
        c3 = rpc('user.setAdReward', 'setAdReward', {'uuid': dev, 'device_uuid': dev, 'i_id': 1, 'param1': '1'})
        c3_data = c3['data']
        self.assertEqual(c3_data['user_ad_list']['i_Count'], 2, "Count must increment to 2 after cooldown expires")
        self.assertEqual(len(c3_data.get('reward_data', [])), 1, "Reward must be granted once cooldown expires")
        self.assertEqual(c3_data['user_follower_profile']['d_Exp'], init_exp + granted_exp + c3_data['reward_data'][0]['reward_value'])

    def test_ad_gift_daily_limit_5_and_new_day_reset(self):
        """Ad Gift ID 1 strictly enforces DAY_LIMIT: 5. 6th claim is rejected. Next calendar day resets count to 0."""
        dev, u_seq, _ = self.create_account('fg-limit')

        # Fast forward user state to claim 5 times
        u = state.get_user(dev)
        now = int(time.time())
        today = int(time.strftime('%Y%m%d', time.localtime()))
        u['ad_rewards'] = {
            '1': {
                'i_id': 1,
                'i_Count': 5,
                'i_TotalCount': 5,
                'i_LastViewTime': now - 1000,  # Cooldown long past
                'upd_day': today,
            }
        }
        state.save_user(u)

        # Attempt 6th claim on the same day: REJECTED!
        c6 = rpc('user.setAdReward', 'setAdReward', {'uuid': dev, 'device_uuid': dev, 'i_id': 1, 'param1': '1'})
        c6_data = c6['data']
        self.assertEqual(c6_data['user_ad_list']['i_Count'], 5, "Count must remain capped at 5")
        self.assertEqual(len(c6_data.get('reward_data', [])), 0, "6th claim must return empty reward_data")

        # Simulate new calendar day rollover (rewind upd_day to yesterday)
        u = state.get_user(dev)
        u['ad_rewards']['1']['upd_day'] = 20261001
        u['ad_rewards']['1']['i_LastViewTime'] = now - 1000
        state.save_user(u)

        # First claim of new calendar day: count resets and claim succeeds!
        new_day_claim = rpc('user.setAdReward', 'setAdReward', {'uuid': dev, 'device_uuid': dev, 'i_id': 1, 'param1': '1'})
        nd_data = new_day_claim['data']
        self.assertEqual(nd_data['user_ad_list']['i_Count'], 1, "New calendar day must reset count to 1 on claim")
        self.assertEqual(len(nd_data.get('reward_data', [])), 1, "New calendar day must grant reward")

    def test_slot1_gingerbread_inventory_deduction_and_no_infinite_gifting(self):
        """Slot 1 (Gingerbread, ID 1, +20 EXP) deducts inventory and blocks gifting when inventory is 0 or negative."""
        dev, u_seq, _ = self.create_account('fg-slot1')

        # Give user exactly 3 Gingerbread gifts (ID 1)
        u = state.get_user(dev)
        u['user_follower_giftitem'] = [{'i_id': 1, 'i_Value': 3}]
        u['user_follower_profile'] = [{'i_id': 1, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0}]
        state.save_user(u)

        # 1. Use 1 Gingerbread: 3 -> 2, EXP 0 -> 20 (+20)
        r1 = rpc('user.setFollowerProfileGift', 'setFollowerProfileGift', {
            'uuid': dev, 'device_uuid': dev, 'profile_id': 1, 'gift_id': 1, 'use_gitf_value': 1
        })
        self.assertEqual(r1['error']['code'], 0)
        self.assertEqual(r1['data']['user_follower_giftitem']['i_Value'], 2)
        self.assertEqual(r1['data']['user_follower_profile']['d_Exp'], 20)

        # 2. Use 2 Gingerbreads: 2 -> 0, EXP 20 -> 60 (+40)
        r2 = rpc('user.setFollowerProfileGift', 'setFollowerProfileGift', {
            'uuid': dev, 'device_uuid': dev, 'profile_id': 1, 'gift_id': 1, 'use_gitf_value': 2
        })
        self.assertEqual(r2['data']['user_follower_giftitem']['i_Value'], 0)
        self.assertEqual(r2['data']['user_follower_profile']['d_Exp'], 60)
        self.assertEqual(r2['data']['user_follower_profile']['i_Level'], 2)  # Lv 2 reached at 50 EXP

        # 3. Attempt to gift when inventory is 0 (No infinite gifting!): rejected/no EXP added
        r3 = rpc('user.setFollowerProfileGift', 'setFollowerProfileGift', {
            'uuid': dev, 'device_uuid': dev, 'profile_id': 1, 'gift_id': 1, 'use_gitf_value': 1
        })
        self.assertEqual(r3['data']['user_follower_giftitem']['i_Value'], 0, "Inventory must stay 0")
        self.assertEqual(r3['data']['user_follower_profile']['d_Exp'], 60, "EXP must NOT change with 0 inventory")

        # 4. Partial inventory clamp: user has 2 gifts, asks to use 5 -> clamps to 2, uses 2, grants 2*20=40
        u = state.get_user(dev)
        u['user_follower_giftitem'] = [{'i_id': 1, 'i_Value': 2}]
        state.save_user(u)

        r4 = rpc('user.setFollowerProfileGift', 'setFollowerProfileGift', {
            'uuid': dev, 'device_uuid': dev, 'profile_id': 1, 'gift_id': 1, 'use_gitf_value': 5
        })
        self.assertEqual(r4['data']['user_follower_giftitem']['i_Value'], 0, "Inventory must be fully exhausted (clamped to 2)")
        self.assertEqual(r4['data']['user_follower_profile']['d_Exp'], 100, "Should gain 2*20=40 EXP (60+40=100), not 5*20=100")

    def test_slot2_favorite_gifts_inventory_deduction_and_no_infinite_gifting(self):
        """Slot 2 (Favorite Gift, IDs 2-6, +30 EXP) deducts specific favorite gift item and prevents infinite gifting."""
        dev, u_seq, _ = self.create_account('fg-slot2')

        # Follower 1 (Joy): Favorite gift is Egg Sandwich (ID 3). Give user 2 Egg Sandwiches and 5 Gingerbreads
        u = state.get_user(dev)
        u['user_follower_giftitem'] = [
            {'i_id': 1, 'i_Value': 5},
            {'i_id': 3, 'i_Value': 2},
        ]
        u['user_follower_profile'] = [{'i_id': 1, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0}]
        state.save_user(u)

        # 1. Use 1 Egg Sandwich: ID 3 inventory 2 -> 1, +30 EXP
        r1 = rpc('user.setFollowerProfileGift', 'setFollowerProfileGift', {
            'uuid': dev, 'device_uuid': dev, 'profile_id': 1, 'gift_id': 3, 'use_gitf_value': 1
        })
        self.assertEqual(r1['error']['code'], 0)
        self.assertEqual(r1['data']['user_follower_giftitem']['i_id'], 3)
        self.assertEqual(r1['data']['user_follower_giftitem']['i_Value'], 1)
        self.assertEqual(r1['data']['user_follower_profile']['d_Exp'], 30)

        # Verify ID 1 (Gingerbread) inventory was NOT touched
        u_saved = state.get_user(dev)
        gb = next(g for g in u_saved['user_follower_giftitem'] if g['i_id'] == 1)
        self.assertEqual(gb['i_Value'], 5, "Other gift items must not be affected")

        # 2. Use 2nd Egg Sandwich: 1 -> 0, +30 EXP (30 -> 60, reaches Lv 2)
        r2 = rpc('user.setFollowerProfileGift', 'setFollowerProfileGift', {
            'uuid': dev, 'device_uuid': dev, 'profile_id': 1, 'gift_id': 3, 'use_gitf_value': 1
        })
        self.assertEqual(r2['data']['user_follower_giftitem']['i_Value'], 0)
        self.assertEqual(r2['data']['user_follower_profile']['d_Exp'], 60)
        self.assertEqual(r2['data']['user_follower_profile']['i_Level'], 2)

        # 3. Third attempt with 0 Egg Sandwiches: blocked, no EXP gained
        r3 = rpc('user.setFollowerProfileGift', 'setFollowerProfileGift', {
            'uuid': dev, 'device_uuid': dev, 'profile_id': 1, 'gift_id': 3, 'use_gitf_value': 1
        })
        self.assertEqual(r3['data']['user_follower_giftitem']['i_Value'], 0)
        self.assertEqual(r3['data']['user_follower_profile']['d_Exp'], 60)

    def test_follower_profile_level_progression_independent_of_stage_level(self):
        """Follower intimacy profile level (user_follower_profile.i_Level) must be strictly independent of stage level."""
        dev, u_seq, _ = self.create_account('fg-stage')

        # Simulate player leveling Follower 1 (Joy) stage level to 88 with Likes
        u = state.get_user(dev)
        u['user_follower'] = [{'i_id': 1, 'i_Level': 88, 'i_BonusLevel': 0}]
        u['user_follower_giftitem'] = [{'i_id': 1, 'i_Value': 10}]
        u['user_follower_profile'] = [{'i_id': 1, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0}]
        state.save_user(u)

        # 1. Relogin must NOT overwrite profile level with stage level 88
        login_res = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        prof = next(p for p in login_res['data']['user_contents']['user_follower_profile'] if p['i_id'] == 1)
        self.assertEqual(prof['i_Level'], 1, "Profile level must remain 1, independent of stage level 88")
        self.assertEqual(prof['d_Exp'], 0)

        # 2. Gifting advances profile level: give 3 Gingerbreads (3 * 20 = 60 EXP -> Level 2)
        r_gift = rpc('user.setFollowerProfileGift', 'setFollowerProfileGift', {
            'uuid': dev, 'device_uuid': dev, 'profile_id': 1, 'gift_id': 1, 'use_gitf_value': 3
        })
        self.assertEqual(r_gift['data']['user_follower_profile']['i_Level'], 2)
        self.assertEqual(r_gift['data']['user_follower_profile']['d_Exp'], 60)

        # 3. Follower stage level on stage must remain strictly 88 (NOT downgraded to 2!)
        u_saved = state.get_user(dev)
        f1 = next(f for f in u_saved['user_follower'] if f['i_id'] == 1)
        self.assertEqual(f1['i_Level'], 88, "Stage level must remain 88")

        # 4. Level up stage level to 120 directly
        f1['i_Level'] = 120
        state.save_user(u_saved)

        # 5. Subsequent relogin preserves stage level 120 and profile level 2
        login_res2 = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        contents = login_res2['data']['user_contents']
        f_login = next(f for f in contents['user_follower'] if f['i_id'] == 1)
        p_login = next(p for p in contents['user_follower_profile'] if p['i_id'] == 1)
        self.assertEqual(f_login['i_Level'], 120, "Stage level remains 120")
        self.assertEqual(p_login['i_Level'], 2, "Profile level remains 2")


# =============================================================================
# 2. MAILBOX REGRESSION (user_post / openPost / delPost)
# =============================================================================
class TestMailboxRegression(BaseEconomyTestCase):
    """Test Mailbox regression: opening posts grants items, marks claimed (status=1, flg=1),
    deleting posts permanently removes them, and relogging never resurrects claimed or deleted mail."""

    def test_open_post_grants_items_and_marks_claimed(self):
        """Opening a post (providePost) grants items, increases currency, and marks post claimed & read."""
        dev, u_seq, _ = self.create_account('mb-open')

        # Send test mail with 500 CP, 75 Candy, and 2000 Likes
        mail = send_post(
            uuid=dev,
            title="Thưởng sự kiện kinh tế",
            memo="Nhận quà thử nghiệm hệ thống",
            items=[
                {'i_RewardType': 1, 'i_RewardId': 1, 'd_RewardQuantity': 500.0},
                {'i_RewardType': 1, 'i_RewardId': 2, 'd_RewardQuantity': 75.0},
                {'i_RewardType': 1, 'i_RewardId': 3, 'd_RewardQuantity': 2000.0},
            ]
        )
        self.assertIsNotNone(mail)
        mail_idx = mail['idx']

        # Verify mail appears in getPost
        post_res = rpc('post.getPost', 'getPost', {'uuid': dev, 'device_uuid': dev})
        m = next((p for p in post_res['data']['post_list'] if p['idx'] == mail_idx), None)
        self.assertIsNotNone(m)
        self.assertEqual(m['have_reward'], 1)
        self.assertEqual(m['status'], 0)
        self.assertEqual(m['flg'], 0)

        # Baseline currency
        u_before = state.get_user(dev)
        cp_before = int(u_before['userdata'].get('u_cp', 0) or 0)
        candy_before = float(u_before['userdata'].get('u_candy', 0.0) or 0.0)
        like_before = float(u_before['userdata'].get('u_like', 0.0) or 0.0)

        # Claim mail rewards via providePost (openPost)
        prov = rpc('post.providePost', 'providePost', {'uuid': dev, 'device_uuid': dev, 'idx': mail_idx})
        self.assertEqual(prov['error']['code'], 0)
        received_items = prov['data']
        self.assertEqual(len(received_items), 3, "Must receive all 3 reward items")

        # Verify currency in DB/state increased properly
        u_after = state.get_user(dev)
        self.assertEqual(int(u_after['userdata']['u_cp']), cp_before + 500)
        self.assertEqual(float(u_after['userdata']['u_candy']), candy_before + 75.0)
        self.assertEqual(float(u_after['userdata']['u_like']), like_before + 2000.0)

        # Verify mail state updated to have_reward=0, status=1, flg=1
        post_res2 = rpc('post.getPost', 'getPost', {'uuid': dev, 'device_uuid': dev})
        m_after = next(p for p in post_res2['data']['post_list'] if p['idx'] == mail_idx)
        self.assertEqual(m_after['have_reward'], 0, "have_reward must be 0 after opening")
        self.assertEqual(m_after['status'], 1, "status must be 1 (claimed)")
        self.assertEqual(m_after['flg'], 1, "flg must be 1 (read flag prevents red dot loop)")

        # Repeat claim attempt on already opened post: returns empty list, no double-crediting
        prov_repeat = rpc('post.providePost', 'providePost', {'uuid': dev, 'device_uuid': dev, 'idx': mail_idx})
        self.assertEqual(len(prov_repeat['data']), 0, "Duplicate open must return empty items")
        u_repeat = state.get_user(dev)
        self.assertEqual(int(u_repeat['userdata']['u_cp']), cp_before + 500, "Currency must not be duplicated")

    def test_delete_post_permanently_removes_it(self):
        """Deleting a post (delPost / deletePost) permanently removes it from user's mailbox."""
        dev, u_seq, _ = self.create_account('mb-del')

        mail = send_post(uuid=dev, title="Thư xóa", memo="Thư này sẽ bị xóa", items=[])
        mail_idx = mail['idx']

        # Confirm post exists
        post_res = rpc('post.getPost', 'getPost', {'uuid': dev, 'device_uuid': dev})
        self.assertTrue(any(p['idx'] == mail_idx for p in post_res['data']['post_list']))

        # Delete post
        del_res = rpc('post.deletePost', 'deletePost', {'uuid': dev, 'device_uuid': dev, 'idx': mail_idx})
        self.assertEqual(del_res['error']['code'], 0)
        self.assertEqual(del_res['data']['idx'], mail_idx)

        # getPost no longer contains the deleted post
        post_after = rpc('post.getPost', 'getPost', {'uuid': dev, 'device_uuid': dev})
        self.assertFalse(any(p['idx'] == mail_idx for p in post_after['data']['post_list']),
                         "Deleted post must not appear in getPost")

        # Verify deleted index recorded in user state
        u = state.get_user(dev)
        self.assertIn(mail_idx, u.get('deleted_post_indices', []))

    def test_relogin_does_not_resurrect_deleted_or_claimed_posts(self):
        """Relogging in (userLogin) must NOT resurrect deleted posts or reset claimed posts back to unclaimed."""
        dev, u_seq, _ = self.create_account('mb-relog')

        # 1. Create Post 1 (claimed) and Post 2 (deleted)
        p1 = send_post(uuid=dev, title="Post 1 Claimed", memo="M1", items=[{'i_RewardType': 1, 'i_RewardId': 1, 'd_RewardQuantity': 100.0}])
        p2 = send_post(uuid=dev, title="Post 2 To Delete", memo="M2", items=[])
        p1_idx = p1['idx']
        p2_idx = p2['idx']

        # Claim Post 1
        rpc('post.providePost', 'providePost', {'uuid': dev, 'device_uuid': dev, 'idx': p1_idx})

        # Delete Post 2
        rpc('post.deletePost', 'deletePost', {'uuid': dev, 'device_uuid': dev, 'idx': p2_idx})

        # Verify pre-relog mailbox state
        pre_posts = rpc('post.getPost', 'getPost', {'uuid': dev, 'device_uuid': dev})['data']['post_list']
        self.assertFalse(any(p['idx'] == p2_idx for p in pre_posts), "Post 2 must be deleted")
        p1_rec = next(p for p in pre_posts if p['idx'] == p1_idx)
        self.assertEqual(p1_rec['have_reward'], 0)
        self.assertEqual(p1_rec['status'], 1)

        # 2. Relog (userLogin)
        relogin_res = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        self.assertEqual(relogin_res['error']['code'], 0)

        # 3. Inspect post list after relogin
        post_after_relogin = rpc('post.getPost', 'getPost', {'uuid': dev, 'device_uuid': dev})['data']['post_list']

        # Deleted post 2 must NOT be resurrected
        self.assertFalse(any(p['idx'] == p2_idx for p in post_after_relogin),
                         "Relog must NOT resurrect deleted post 2!")

        # Claimed post 1 must remain claimed (have_reward=0, status=1, flg=1)
        p1_after = next((p for p in post_after_relogin if p['idx'] == p1_idx), None)
        self.assertIsNotNone(p1_after, "Claimed post 1 should still exist in read history")
        self.assertEqual(p1_after['have_reward'], 0, "Claimed post must NOT resurrect rewards")
        self.assertEqual(p1_after['status'], 1, "Claimed post must maintain status 1")
        self.assertEqual(p1_after['flg'], 1, "Claimed post must maintain read flg 1")

    def test_batch_delete_all_read_posts(self):
        """Batch delete (deletePost idx=0, type=1) removes all claimed/read posts while preserving unread posts."""
        dev, u_seq, _ = self.create_account('mb-batch')

        # Create Post A (with rewards, claimed) and Post B (with rewards, UNCLAIMED)
        pa = send_post(uuid=dev, title="Post A", memo="A", items=[{'i_RewardType': 1, 'i_RewardId': 1, 'd_RewardQuantity': 50.0}])
        pb = send_post(uuid=dev, title="Post B", memo="B", items=[{'i_RewardType': 1, 'i_RewardId': 1, 'd_RewardQuantity': 100.0}])
        pa_idx = pa['idx']
        pb_idx = pb['idx']

        # Claim Post A
        rpc('post.providePost', 'providePost', {'uuid': dev, 'device_uuid': dev, 'idx': pa_idx})

        # Batch delete read mail
        del_batch = rpc('post.deletePost', 'deletePost', {'uuid': dev, 'device_uuid': dev, 'idx': 0, 'type': 1})
        self.assertEqual(del_batch['error']['code'], 0)

        # Inspect posts
        posts = rpc('post.getPost', 'getPost', {'uuid': dev, 'device_uuid': dev})['data']['post_list']
        self.assertFalse(any(p['idx'] == pa_idx for p in posts), "Read/claimed Post A must be deleted")
        self.assertTrue(any(p['idx'] == pb_idx for p in posts), "Unread/unclaimed Post B must NOT be deleted")


# =============================================================================
# 3. SHOP & STAR PASS REGRESSION
# =============================================================================
class TestShopAndStarPassRegression(BaseEconomyTestCase):
    """Test Shop and Star Pass regression: Season 13 Merch Pack 3013 costs 200 CP, grants tickets 1013 & 13,
    prevents repeat purchases, excludes Category 0 from General Store, and rejects insufficient CP."""

    def test_season13_merch_pack_3013_purchase_and_tickets(self):
        """Item 3013 purchase costs 200 CP, grants Star Pass 1013 & tickets (1013, 13) in user collections."""
        dev, u_seq, _ = self.create_account('sp-pack3013')

        # Fund user with 350 CP
        state.increment_currency(dev, cp=350)
        u = state.get_user(dev)
        u['userdata']['u_cp'] = 350
        state.save_user(u)

        # Verify eligibility via buyCheck
        chk = rpc('user.buyCheck', 'buyCheck', {'uuid': dev, 'device_uuid': dev, 'idx': 3013})
        self.assertEqual(chk['error']['code'], 0, f"buyCheck for 3013 must succeed: {chk['error']}")

        # Purchase Season 13 Merch Pack (3013)
        buy = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 3013})
        self.assertEqual(buy['error']['code'], 0, f"buyShop for 3013 must succeed: {buy['error']}")

        # Verify 200 CP deducted: 350 - 200 = 150
        self.assertEqual(buy['data']['u_cp'], 150, "CP must be reduced by 200")
        u_saved = state.get_user(dev)
        self.assertEqual(u_saved['userdata']['u_cp'], 150, "Persisted CP must be 150")

        # Verify granted rewards
        granted = buy['data'].get('reward_data', [])
        self.assertTrue(any(r['reward_type'] == 10 and r['reward_id'] == 1013 for r in granted),
                        "Must contain Star Pass 1013 reward")

        # Verify tickets collection (both 13 and 1013)
        ticket_ids = {t['i_id'] for t in u_saved.get('user_ticketcollection', [])}
        self.assertIn(13, ticket_ids, "Season 13 ticket (13) must be in user_ticketcollection")
        self.assertIn(1013, ticket_ids, "Season 13 Merch ticket (1013) must be in user_ticketcollection")

        # Verify subscriptions list (both 13 and 1013 active)
        sub_ids = {s['i_SubscribeID'] for s in u_saved.get('user_subscribe_list', []) if s.get('i_isActive')}
        self.assertIn(13, sub_ids, "Season 13 subscription must be active")
        self.assertIn(1013, sub_ids, "Season 13 Merch subscription must be active")

        # Verify user_shop purchase record for both 3013 and 2013
        shop_ids = {s['i_id'] for s in u_saved.get('user_shop', [])}
        self.assertIn(3013, shop_ids, "3013 must be recorded in user_shop")
        self.assertIn(2013, shop_ids, "2013 must also be recorded in user_shop")

        # Verify relogin returns both tickets to client
        login_res = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        relogin_tickets = {t['i_id'] for t in login_res['data']['user_contents']['user_ticketcollection']}
        self.assertIn(13, relogin_tickets)
        self.assertIn(1013, relogin_tickets)

    def test_cannot_purchase_non_repeatable_pack_again(self):
        """User cannot purchase non-repeatable pack (3013 or 2013) again once owned."""
        dev, u_seq, _ = self.create_account('sp-norepeat')

        # Fund and purchase 3013 once
        state.increment_currency(dev, cp=500)
        u = state.get_user(dev)
        u['userdata']['u_cp'] = 500
        state.save_user(u)

        r_buy1 = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 3013})
        self.assertEqual(r_buy1['error']['code'], 0)
        self.assertEqual(r_buy1['data']['u_cp'], 300)

        # 1. Attempt buyCheck for 3013 again: REJECTED!
        chk_repeat = rpc('user.buyCheck', 'buyCheck', {'uuid': dev, 'device_uuid': dev, 'idx': 3013})
        self.assertNotEqual(chk_repeat['error']['code'], 0, "Repeat buyCheck for 3013 must be rejected")
        self.assertIn('sở hữu', chk_repeat['error']['errmsg'])

        # 2. Attempt buyShop for 3013 again: REJECTED!
        buy_repeat = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 3013})
        self.assertNotEqual(buy_repeat['error']['code'], 0, "Repeat buyShop for 3013 must be rejected")
        self.assertIn('sở hữu', buy_repeat['error']['errmsg'])

        # 3. Attempt buyCheck and buyShop for companion pack 2013: REJECTED!
        chk_2013 = rpc('user.buyCheck', 'buyCheck', {'uuid': dev, 'device_uuid': dev, 'idx': 2013})
        self.assertNotEqual(chk_2013['error']['code'], 0, "Companion pack 2013 buyCheck must be rejected")
        buy_2013 = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 2013})
        self.assertNotEqual(buy_2013['error']['code'], 0, "Companion pack 2013 buyShop must be rejected")

        # Persisted CP remains strictly 300 (no further deduction)
        u_final = state.get_user(dev)
        self.assertEqual(u_final['userdata']['u_cp'], 300)

    def test_category_0_goods_excluded_from_general_store(self):
        """Category 0 goods (Star Pass items 1001..1013) must be strictly excluded from General Shop (Category 1)."""
        rpc_data = fetch_gamedata_rpc()
        shop_table = rpc_data.get('shop', [])
        self.assertGreater(len(shop_table), 0, "Shop table must not be empty")

        cat0_items = [it for it in shop_table if it.get('i_ShopCategory') == 0]
        cat1_items = [it for it in shop_table if it.get('i_ShopCategory') == 1]

        cat0_ids = {it['i_id'] for it in cat0_items}
        cat1_ids = {it['i_id'] for it in cat1_items}

        # Category 0 must contain all Star Passes 1001-1013
        for s in range(1001, 1014):
            self.assertIn(s, cat0_ids, f"Star Pass item {s} must belong to Category 0")

        # Category 1 (General shop) must NOT contain any Category 0 items
        for s in range(1001, 1014):
            self.assertNotIn(s, cat1_ids, f"Star Pass item {s} must NOT appear in General Shop (Category 1)")

        self.assertTrue(cat0_ids.isdisjoint(cat1_ids),
                        "Category 0 items and General Shop Category 1 items must be completely disjoint")

    def test_insufficient_cp_rejection(self):
        """Shop and Star Pass purchases reject when user has insufficient CP."""
        dev, u_seq, _ = self.create_account('sp-nocp')

        # User has 100 CP, tries to buy 3013 (price 200 CP): REJECTED
        state.set_currency(dev, cp=100, candy=0.0)
        res_3013 = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 3013})
        self.assertNotEqual(res_3013['error']['code'], 0, "Buying item 3013 with 100 CP (price 200) must fail")
        self.assertIn('Socola', res_3013['error']['errmsg'])

        # User has 0 CP, tries to buy Star Pass 1013 (price 150 CP): REJECTED
        state.set_currency(dev, cp=0, candy=0.0)
        res_1013 = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 1013})
        self.assertNotEqual(res_1013['error']['code'], 0, "Buying item 1013 with 0 CP (price 150) must fail")
        self.assertIn('Socola', res_1013['error']['errmsg'])

        # Verify nothing was granted
        u = state.get_user(dev)
        self.assertEqual(u['userdata']['u_cp'], 0)
        self.assertFalse(any(s.get('i_SubscribeID') in (13, 1013) for s in u.get('user_subscribe_list', [])))
        self.assertFalse(any(t.get('i_id') in (13, 1013) for t in u.get('user_ticketcollection', [])))


# =============================================================================
# 4. ATTENDANCE & DAILY MISSIONS REGRESSION
# =============================================================================
class TestAttendanceAndDailyMissionsRegression(BaseEconomyTestCase):
    """Test Attendance and Daily Missions regression: 7-day progression, duplicate claim prevention,
    board rollover to Day 1, Mission 1 auto-completion, Mission 6 sync, and new day reset."""

    def test_7day_attendance_progression_and_duplicate_prevention(self):
        """Walk the full 7-day attendance progression, verify exact daily rewards, and duplicate prevention."""
        dev, u_seq, _ = self.create_account('att-prog')

        # Day 1 initial check
        chk = rpc('user.setAttendance', 'setAttendance', {'uuid': dev, 'device_uuid': dev, 'type': 'check'})
        self.assertEqual(chk['data']['attendance_count'], 1, "Fresh account must start at Day 1")
        self.assertEqual(chk['data']['status'], 'Y')

        # Record login via add
        rpc('user.setAttendance', 'setAttendance', {'uuid': dev, 'device_uuid': dev, 'type': 'add'})

        # Claim Day 1 reward
        c1 = rpc('user.setEventReward', 'setEventReward', {'uuid': dev, 'device_uuid': dev, 'event_idx': 1})
        self.assertEqual(c1['data']['status'], 'Y')
        self.assertEqual(c1['data']['reward_type'], EV1_DAYS[1][0])
        self.assertEqual(c1['data']['reward_id'], EV1_DAYS[1][1])
        self.assertEqual(c1['data']['reward_value'], EV1_DAYS[1][2])

        # Duplicate claim Day 1 on the same day: REJECTED!
        dup1 = rpc('user.setEventReward', 'setEventReward', {'uuid': dev, 'device_uuid': dev, 'event_idx': 1})
        self.assertEqual(dup1['data']['status'], 'N', "Duplicate same-day claim must return status 'N'")
        self.assertEqual(dup1['data']['reward_value'], 0)

        # Walk Days 2 through 7 simulating daily calendar progression
        for target_day in range(2, 8):
            # Rewind ymd to simulate next calendar day
            u = state.get_user(dev)
            u['attendance']['1']['ymd'] = 0
            state.save_user(u)

            # setAttendance(check) reports target day
            chk_day = rpc('user.setAttendance', 'setAttendance', {'uuid': dev, 'device_uuid': dev, 'type': 'check'})
            self.assertEqual(chk_day['data']['attendance_count'], target_day, f"Must report Day {target_day}")

            # Claim reward
            c_day = rpc('user.setEventReward', 'setEventReward', {'uuid': dev, 'device_uuid': dev, 'event_idx': 1})
            self.assertEqual(c_day['data']['status'], 'Y', f"Day {target_day} claim must succeed")
            exp_type, exp_id, exp_val = EV1_DAYS[target_day]
            self.assertEqual(c_day['data']['reward_type'], exp_type, f"Day {target_day} reward_type mismatch")
            self.assertEqual(c_day['data']['reward_id'], exp_id, f"Day {target_day} reward_id mismatch")
            self.assertEqual(c_day['data']['reward_value'], exp_val, f"Day {target_day} reward_value mismatch")

            # Duplicate claim on same day rejected
            dup_day = rpc('user.setEventReward', 'setEventReward', {'uuid': dev, 'device_uuid': dev, 'event_idx': 1})
            self.assertEqual(dup_day['data']['status'], 'N', f"Duplicate claim on Day {target_day} must be rejected")

        # Rollover after Day 7: wraps back to Day 1!
        u = state.get_user(dev)
        u['attendance']['1']['ymd'] = 0
        state.save_user(u)

        chk_wrap = rpc('user.setAttendance', 'setAttendance', {'uuid': dev, 'device_uuid': dev, 'type': 'check'})
        self.assertEqual(chk_wrap['data']['attendance_count'], 1, "Board must wrap back to Day 1 after Day 7")

        c_wrap = rpc('user.setEventReward', 'setEventReward', {'uuid': dev, 'device_uuid': dev, 'event_idx': 1})
        self.assertEqual(c_wrap['data']['status'], 'Y')
        self.assertEqual((c_wrap['data']['reward_type'], c_wrap['data']['reward_id'], c_wrap['data']['reward_value']), EV1_DAYS[1],
                         "Wrap to Day 1 must grant Day 1 reward (100 CP)")

    def test_daily_mission_auto_completion_and_mission6_sync(self):
        """Mission 1 is auto-completed upon login, Mission 6 syncs with completed count, and userSave cannot tamper it."""
        dev, u_seq, login_res = self.create_account('dm-auto')

        # 1. Inspect daily missions from login
        dm = login_res['data']['user_contents']['user_daily_mission']
        m1 = next(m for m in dm if m['i_id'] == 1)
        m6 = next(m for m in dm if m['i_id'] == 6)

        self.assertEqual(m1['d_Quantity'], 1, "Mission 1 ('Đăng nhập nhiều hơn 1 lần') must start at 1/1")
        self.assertEqual(m1['i_Level'], 1, "Mission 1 must start at Level 1 (unclaimed)")
        self.assertEqual(m6['d_Quantity'], 1, "Mission 6 must reflect 1 completed mission (1/5)")

        # 2. Claim Mission 1 reward via setGameReward
        u_init = state.get_user(dev)
        cp_init = int(u_init['userdata'].get('u_cp', 0) or 0)

        claim1 = rpc('user.setGameReward', 'setGameReward', {
            'uuid': dev, 'device_uuid': dev, 'id': 1, 'level': 1, 'type': 'daily_mission'
        })
        self.assertEqual(claim1['error']['code'], 0)
        self.assertEqual(claim1['data']['status'], 'Y')
        self.assertEqual(claim1['data']['reward_value'], 10, "Mission 1 must award 10 CP")
        self.assertEqual(claim1['data']['level'], 2, "Mission 1 level must advance to 2")

        # Verify CP added
        u_after = state.get_user(dev)
        self.assertEqual(int(u_after['userdata']['u_cp']), cp_init + 10)

        # 3. Duplicate claim on the same day: REJECTED!
        claim_dup = rpc('user.setGameReward', 'setGameReward', {
            'uuid': dev, 'device_uuid': dev, 'id': 1, 'level': 1, 'type': 'daily_mission'
        })
        self.assertEqual(claim_dup['data']['status'], 'N', "Duplicate daily mission claim must return status 'N'")
        self.assertEqual(claim_dup['data']['reward_value'], 0)

        # 4. Tamper protection: client userSave sending d_Quantity=0 or i_Level=1 CANNOT revert Mission 1
        save_res = rpc('user.userSave', 'userSave', {
            'uuid': dev, 'device_uuid': dev,
            'user_daily_mission': [
                {'i_id': 1, 'd_Quantity': 0, 'i_Level': 1},
                {'i_id': 2, 'd_Quantity': 100},
                {'i_id': 3, 'd_Quantity': 0},
                {'i_id': 4, 'd_Quantity': 0},
                {'i_id': 5, 'd_Quantity': 0},
                {'i_id': 6, 'd_Quantity': 0},
            ]
        })
        self.assertEqual(save_res['data']['status'], 'Y')

        u_saved = state.get_user(dev)
        m1_saved = next(m for m in u_saved['user_daily_mission'] if m['i_id'] == 1)
        m6_saved = next(m for m in u_saved['user_daily_mission'] if m['i_id'] == 6)
        self.assertEqual(m1_saved['d_Quantity'], 1, "Mission 1 d_Quantity cannot be reverted to 0")
        self.assertEqual(m1_saved['i_Level'], 2, "Mission 1 claimed level 2 cannot be downgraded")
        self.assertEqual(m6_saved['d_Quantity'], 1, "Mission 6 must keep count 1")

    def test_daily_mission_new_day_rollover(self):
        """New calendar day rollover resets all daily missions, initializes Mission 1 to 1/1, and allows claiming again."""
        dev, u_seq, _ = self.create_account('dm-roll')

        # Claim Mission 1 today
        rpc('user.setGameReward', 'setGameReward', {'uuid': dev, 'device_uuid': dev, 'id': 1, 'level': 1, 'type': 'daily_mission'})
        u = state.get_user(dev)
        cp_day1 = int(u['userdata'].get('u_cp', 0) or 0)

        # Simulate new calendar day: rewind daily_mission_date to yesterday
        u['daily_mission_date'] = 20261001
        state.save_user(u)

        # Relogin on new day
        new_day_login = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        dm_new = new_day_login['data']['user_contents']['user_daily_mission']
        nd_m1 = next(m for m in dm_new if m['i_id'] == 1)
        nd_m2 = next(m for m in dm_new if m['i_id'] == 2)

        self.assertEqual(nd_m1['i_Level'], 1, "New day must reset Mission 1 level to 1")
        self.assertEqual(nd_m1['d_Quantity'], 1, "New day must auto-complete Mission 1 to 1/1")
        self.assertEqual(nd_m2['d_Quantity'], 0, "Other missions must reset to 0")

        # Claim Mission 1 for the new day: succeeds and awards 10 CP again!
        claim_nd = rpc('user.setGameReward', 'setGameReward', {'uuid': dev, 'device_uuid': dev, 'id': 1, 'level': 1, 'type': 'daily_mission'})
        self.assertEqual(claim_nd['data']['status'], 'Y')
        self.assertEqual(claim_nd['data']['reward_value'], 10)
        self.assertEqual(claim_nd['data']['level'], 2)

        u_final = state.get_user(dev)
        self.assertEqual(int(u_final['userdata']['u_cp']), cp_day1 + 10, "CP must increase by 10 for new day claim")


# =============================================================================
# MAIN RUNNER
# =============================================================================
def main():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestFollowerGiftingRegression))
    suite.addTests(loader.loadTestsFromTestCase(TestMailboxRegression))
    suite.addTests(loader.loadTestsFromTestCase(TestShopAndStarPassRegression))
    suite.addTests(loader.loadTestsFromTestCase(TestAttendanceAndDailyMissionsRegression))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        print(f"\n[FAIL] Test suite failed with {len(result.failures)} failures and {len(result.errors)} errors.")
        sys.exit(1)
    else:
        print(f"\n[SUCCESS] 100% of {result.testsRun} tests PASSED with zero failures and zero errors!")
        sys.exit(0)


if __name__ == '__main__':
    main()

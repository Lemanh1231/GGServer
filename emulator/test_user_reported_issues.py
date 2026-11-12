#!/usr/bin/env python3
"""Automated verification test for the 3 user-reported issues:
1. Guitar Girl skill cooldowns in getGameDataList.
2. Calico Cat Meowfest event (rewards types & unit lock/unlock).
3. Music purchasing (d_UnlockCost price & MAP<I32, musicData> return format).
"""
import os
import sys
import io
import uuid as uuidlib
import urllib.request
import unittest

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

class TestUserReportedIssues(unittest.TestCase):

    def test_issue_1_skill_cooldowns(self):
        """Verify getGameDataList serves correct canonical skill cooldowns (field 36)."""
        boundary, body = _multipart({'call': 'getGameDataList', 'tapsonic_data': 'x'})
        req = urllib.request.Request(f'{SERVER}/main/getGameDataList/en/', data=body,
                                     headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
        raw = urllib.request.urlopen(req, timeout=10).read().decode()
        named, _ = codec.decode_request(raw, 'main.getGameDataListReturn')
        
        skills = named['data']['ret']['skill']
        skill_map = {s['i_id']: s['f_Cooltime'] for s in skills}
        
        expected_cooldowns = {
            1: 1800.0,  # Shining Heart: 30m
            2: 3600.0,  # Heartful Song: 1h
            3: 7200.0,  # Light of Dawn Melody: 2h
            4: 900.0,   # Skill Reset: 15m
            21: 1800.0, # Vivace: 30m
            22: 3600.0, # Note Festival: 1h
            23: 7200.0, # Street Musician: 2h
            24: 900.0   # Skill Reset (Area 2): 15m
        }
        for sid, cd in expected_cooldowns.items():
            self.assertIn(sid, skill_map, f"Skill {sid} must be present in getGameDataList")
            self.assertEqual(skill_map[sid], cd, f"Skill {sid} cooldown should be {cd}s, got {skill_map[sid]}s")

    def test_issue_2_calico_cat_meowfest(self):
        """Verify Meowfest reward types (Guitar 9, Costume 3, Unit 7) and starter unit behavior."""
        dev = 'cat-test-' + uuidlib.uuid4().hex[:8]
        join_res = rpc('user.userJoin', 'userJoin', {'uuid': dev, 'device_uuid': dev})
        u_seq = join_res['data']['u_seq']
        login_res = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        
        # New account must start with 0 units (Calico Cat Navi locked by default)
        user_units = login_res['data'].get('user_unit', [])
        self.assertEqual(len(user_units), 0, f"New user must start with empty user_unit, got {user_units}")
        
        # Verify Meowfest milestone rewards
        sam_list = rpc('eventMode.getSamSeckList', 'getSamSeckList', {'uuid': dev, 'device_uuid': dev})
        rewards = {r['i_id']: (r['i_RewardType'], r['i_RewardId'], r['d_RewardQuantity'])
                   for r in sam_list['data']['rewardList']}
        
        # 1: Guitar 10 (Calico Cat Scratcher)
        self.assertEqual(rewards[1], (9, 10, 1.0), "Slot 1 must be Guitar 10")
        # 2: Costume 13 (Calico Cat Overalls)
        self.assertEqual(rewards[2], (3, 13, 1.0), "Slot 2 must be Costume 13")
        # 3: Unit 1 (Calico Cat Navi)
        self.assertEqual(rewards[3], (7, 1, 1.0), "Slot 3 must be Unit 1")
        
        # Claim step 3 via event
        rpc('eventMode.getSamSeckReward', 'getSamSeckReward', {'uuid': dev, 'device_uuid': dev, 'i_id': 3})
        u = state.get_user(dev)
        units = u.get('user_unit', [])
        self.assertTrue(any(u.get('i_id') == 1 and u.get('i_Level') == 1 for u in units),
                        "Claiming step 3 must unlock Calico Cat Navi at level 1")

    def test_issue_3_buy_music(self):
        """Verify buyMusic charges correct candy cost (d_UnlockCost) and returns valid Thrift map."""
        dev = 'music-test-' + uuidlib.uuid4().hex[:8]
        join_res = rpc('user.userJoin', 'userJoin', {'uuid': dev, 'device_uuid': dev})
        u_seq = join_res['data']['u_seq']
        rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        
        # Give user 100 candy
        state.increment_currency(dev, candy=100.0)
        u = state.get_user(dev)
        u['userdata']['u_candy'] = 100.0
        state.save_user(u)
        
        # Buy Song 2 (Table 2 row: d_UnlockCost is 30 candy, sortOrder is 200)
        res = rpc('user.buyMusic', 'buyMusic', {'uuid': dev, 'device_uuid': dev, 'idx': 2})
        self.assertEqual(res['error']['code'], 0, f"buyMusic must succeed: {res}")
        
        # Candy should be 100 - 30 = 70 (not 100 - 200 < 0!)
        u_after = state.get_user(dev)
        self.assertEqual(u_after['userdata']['u_candy'], 70.0,
                         f"Candy must be deducted by 30 (d_UnlockCost), got {u_after['userdata']['u_candy']}")
        
        # Verify returned music map
        music_map = res['data'].get('music', {})
        self.assertIn(2, music_map, f"Returned music map must contain key 2, got {music_map}")
        self.assertNotIn(0, music_map, f"Returned music map must NOT contain phantom key 0, got {music_map}")
        self.assertEqual(music_map[2]['music_idx'], 2, "Returned musicData.music_idx must be 2")

    def test_issue_4_ad_profile_free_gift_limit(self):
        """Verify Our Memories ('Kí ức của chúng ta') adheres to 5 daily limit & 600s cooldown."""
        dev = 'ad-test-' + uuidlib.uuid4().hex[:8]
        join_res = rpc('user.userJoin', 'userJoin', {'uuid': dev, 'device_uuid': dev})
        u_seq = join_res['data']['u_seq']
        login_res = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        
        # user_ad_list must be returned in login contents
        user_contents = login_res['data'].get('user_contents', {})
        ad_list = user_contents.get('user_ad_list', [])
        ad1 = next((a for a in ad_list if a.get('i_id') == 1), None)
        self.assertIsNotNone(ad1, f"user_ad_list in login must contain entry for ad 1: {ad_list}")
        self.assertEqual(ad1.get('i_Count', 0), 0, "Initial ad 1 count must be 0")

        # First claim: should succeed with reward and update i_Count to 1, i_LastViewTime > 0
        claim1 = rpc('user.setAdReward', 'setAdReward', {'uuid': dev, 'device_uuid': dev, 'i_id': 1, 'param1': '1'})
        ad_ret1 = claim1['data'].get('user_ad_list', {})
        self.assertEqual(ad_ret1.get('i_id'), 1)
        self.assertEqual(ad_ret1.get('i_Count'), 1)
        self.assertGreater(ad_ret1.get('i_LastViewTime', 0), 0)
        self.assertTrue(len(claim1['data'].get('reward_data', [])) > 0, "First claim must grant EXP reward")

        # Second claim immediately (cooltime active): must not grant reward
        claim2 = rpc('user.setAdReward', 'setAdReward', {'uuid': dev, 'device_uuid': dev, 'i_id': 1, 'param1': '1'})
        ad_ret2 = claim2['data'].get('user_ad_list', {})
        self.assertEqual(ad_ret2.get('i_Count'), 1, "Count must stay 1 while on cooldown")
        self.assertEqual(len(claim2['data'].get('reward_data', [])), 0, "Claim during cooldown must yield empty reward")

        # Fast forward time to simulate 5 gifts reached
        u = state.get_user(dev)
        u['ad_rewards']['1']['i_Count'] = 5
        u['ad_rewards']['1']['i_LastViewTime'] = 1000  # long ago
        state.save_user(u)

        # 6th claim attempt when daily limit is reached: must be denied
        claim6 = rpc('user.setAdReward', 'setAdReward', {'uuid': dev, 'device_uuid': dev, 'i_id': 1, 'param1': '1'})
        ad_ret6 = claim6['data'].get('user_ad_list', {})
        self.assertEqual(ad_ret6.get('i_Count'), 5, "Count must remain capped at 5")
        self.assertEqual(len(claim6['data'].get('reward_data', [])), 0, "Claim after 5/5 daily limit must yield empty reward")

    def test_issue_5_follower_profile_gifting_level_progression(self):
        """Verify follower profile gifting levels up properly without maxing out or coupling to stage level."""
        dev = 'gift-test-' + uuidlib.uuid4().hex[:8]
        join_res = rpc('user.userJoin', 'userJoin', {'uuid': dev, 'device_uuid': dev})
        u_seq = join_res['data']['u_seq']
        login_res = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})

        # Simulate user leveling up Follower 1 (Joy) on stage to level 30 with Likes/Fans
        u = state.get_user(dev)
        u['user_follower'] = [{'i_id': 1, 'i_Level': 30, 'i_BonusLevel': 0}]
        u['user_follower_giftitem'] = [{'i_id': 1, 'i_Value': 100}]
        state.save_user(u)

        # Login must NOT overwrite profile level with stage level 30
        login_res2 = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})
        profiles = login_res2['data'].get('user_contents', {}).get('user_follower_profile', [])
        p1 = next((p for p in profiles if p.get('i_id') == 1), None)
        self.assertIsNotNone(p1)
        self.assertEqual(p1['i_Level'], 1, "Profile level must start at 1, NOT follower stage level 30")
        self.assertEqual(p1['d_Exp'], 0, "Initial profile EXP must be 0")

        # 1st gift (Gingerbread: 1 count = +20 EXP)
        # Level 1 requires 0, Level 2 requires 50 -> should remain Level 1 with 20 EXP
        res1 = rpc('user.setFollowerProfileGift', 'setFollowerProfileGift', {
            'uuid': dev, 'device_uuid': dev, 'profile_id': 1, 'gift_id': 1, 'use_gitf_value': 1
        })
        p1_g1 = res1['data']['user_follower_profile']
        self.assertEqual(p1_g1['i_Level'], 1, "1 gift (20 EXP) must NOT level up to 2 (needs 50 EXP)")
        self.assertEqual(p1_g1['d_Exp'], 20)

        # Verify follower stage level on stage is NOT overwritten by profile level
        u_mid = state.get_user(dev)
        f1_mid = next((f for f in u_mid.get('user_follower', []) if f.get('i_id') == 1), None)
        self.assertEqual(f1_mid['i_Level'], 30, "Follower stage level must remain 30, not downgraded to 1")

        # 2nd gift (2 counts = +40 EXP, total 60 EXP)
        # 60 EXP >= 50 EXP (Level 2) and < 150 EXP (Level 3) -> should reach Level 2 with 60 EXP
        res2 = rpc('user.setFollowerProfileGift', 'setFollowerProfileGift', {
            'uuid': dev, 'device_uuid': dev, 'profile_id': 1, 'gift_id': 1, 'use_gitf_value': 2
        })
        p1_g2 = res2['data']['user_follower_profile']
        self.assertEqual(p1_g2['i_Level'], 2, "60 EXP must reach Level 2")
        self.assertEqual(p1_g2['d_Exp'], 60)

        # Song encore bonus (50 EXP) -> total 110 EXP -> still Level 2 (< 150)
        res_music = rpc('user.getMusicReward', 'getMusicReward', {
            'uuid': dev, 'device_uuid': dev, 'i_ids': [1], 'i_levels': [1]
        })
        p_music = next((p for p in res_music['data']['user_follower_profile'] if p.get('i_id') == 1), None)
        self.assertEqual(p_music['i_Level'], 2, "110 EXP must still be Level 2 (Level 3 requires 150 EXP)")
        self.assertEqual(p_music['d_Exp'], 110)

        # Claims in user_follower_profile_reward must NOT have auto-unlocked level 5 or higher
        u_final = state.get_user(dev)
        claims = u_final.get('user_follower_profile_reward', [])
        self.assertFalse(any(c.get('i_id') == 1 and c.get('i_RewardLevel') >= 5 for c in claims),
                         f"No milestone rewards >= 5 should be pre-claimed: {claims}")

    def test_issue_6_ch_third_stage_and_stream_stage_guitar_girl_exp(self):
        """Verify Chapter 2 manual stage play and stream stage award Guitar Girl intimacy EXP."""
        dev = 'verify-ch3-gg-exp-' + uuidlib.uuid4().hex[:8]
        rpc('main.userJoin', 'userJoin', {'device_uuid': dev, 'uuid': dev})
        rpc('user.userLogin', 'userLogin', {'device_uuid': dev, 'uuid': dev})

        u = state.get_user(dev)
        u['userdata']['u_ap'] = 70
        u['user_ap'] = {'i_Ap': 70, 'i_FullApTime': 0, 'i_MaxAp': 70}
        u['characters'] = [{'i_id': 1, 'i_Level': 20}]
        u['user_music'] = [{'i_id': 201, 'i_Level': 10}]
        # Guitar Girl starts at Level 10 (18,700 EXP)
        u['user_follower_profile'] = [
            {'i_id': 100000, 'i_Level': 10, 'd_Exp': 18700, 'i_AddCandy': 0},
            {'i_id': 1, 'i_Level': 10, 'd_Exp': 9350, 'i_AddCandy': 2},
            {'i_id': 2, 'i_Level': 10, 'd_Exp': 9350, 'i_AddCandy': 2},
            {'i_id': 5, 'i_Level': 10, 'd_Exp': 9350, 'i_AddCandy': 2},
        ]
        # Set chapter 2 stage 2002 unlocked
        u['user_ch_third_stage'] = [
            {'i_id': 1001, 'i_ChapterId': 1, 'i_StageIndex': 1, 'i_Star': 3},
            {'i_id': 2001, 'i_ChapterId': 2, 'i_StageIndex': 1, 'i_Star': 0},
            {'i_id': 2002, 'i_ChapterId': 2, 'i_StageIndex': 2, 'i_Star': 3},
        ]
        u['user_chthird_stage'] = u['user_ch_third_stage']
        state.save_user(u)

        # 1. Manual play on Chapter 2 Stage 2002
        res_manual = rpc('user.chThirdStage', 'chThirdStage', {
            'uuid': dev, 'device_uuid': dev, 'i_id': 2002, 'music_id': 201, 'profile_ids': '1,2,5'
        })
        self.assertEqual(res_manual['data']['clear'], 1)
        gg_prof_manual = res_manual['data']['user_follower_profile']
        self.assertIsNotNone(gg_prof_manual)
        self.assertEqual(gg_prof_manual['i_id'], 100000)
        # 18700 + 200 = 18900
        self.assertEqual(gg_prof_manual['d_Exp'], 18900)
        self.assertEqual(gg_prof_manual['i_Level'], 10)

        # 2. Auto-play / Stream stage on Chapter 2 Stage 2002 (count=5)
        res_stream = rpc('user.chThirdStreamStage', 'chThirdStreamStage', {
            'uuid': dev, 'device_uuid': dev, 'i_id': 2002, 'count': 5
        })
        gg_prof_stream = res_stream['data']['user_follower_profile']
        self.assertIsNotNone(gg_prof_stream)
        self.assertEqual(gg_prof_stream['i_id'], 100000)
        # 18900 + (5 * 200) = 19900
        self.assertEqual(gg_prof_stream['d_Exp'], 19900)
        self.assertEqual(gg_prof_stream['i_Level'], 10)
        # Verify rewards map contains 5 runs
        self.assertEqual(len(res_stream['data']['reward_data']), 5)

        # Verify DB persistence
        u_saved = state.get_user(dev)
        p100_db = next((p for p in u_saved.get('user_follower_profile', []) if p['i_id'] == 100000), None)
        self.assertEqual(p100_db['d_Exp'], 19900)

if __name__ == '__main__':
    unittest.main()

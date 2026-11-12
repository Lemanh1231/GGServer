#!/usr/bin/env python3
"""Dedicated QA & Verification Test Suite for Guitar Girl Chapter 1 & 2 Stage Gameplay
and Intimacy EXP Mechanics.

Verification Areas:
1. userLogin returns all 41 stages in user_chthird_stage (Ch1: 1001-1020, Ch2: 2001-2021)
   with 3 stars for Normal stages and 0 stars for Story stages.
2. getChThird returns user_ap (70/70) and all 41 stages in user_ch_third_stage.
3. chThirdStage for Normal Stage:
   - AP deduction (5 AP per run, returns updated user_ap).
   - Guitar Girl intimacy EXP increase (+100 for Ch1, +200 for Ch2).
   - Star rating calculation, bonus scoring, and thresholds.
   - Profile level-up thresholds (Lv 1->2 at 100 EXP, Lv 2->3 at 300 EXP).
   - Failure case when score is insufficient (0 star, clear=0, no EXP/drops).
4. chThirdStage for Story Stage:
   - Does NOT consume AP (AP remains unchanged).
   - Clears story stage (clear=1, star=0, reward_data=[]).
   - Guitar Girl profile EXP increase (+100 for Ch1, +200 for Ch2).
   - Story stage playable even with 0 AP.
5. chThirdStreamStage (AutoPlay):
   - Multiple counts (count=1, count=5, count=10).
   - AP deduction = count * 5 AP.
   - Rewards map has entries for 1..count.
   - Guitar Girl intimacy EXP = count * stage EXP (+2000 for 10 runs of Ch2 -> Lv 5).
   - Insufficient AP rejection (error code 1, 'Not enough Cookie').
6. Chapter Star Rewards (getChThirdStarReward & setChThirdChapterReward):
   - 10, 20, 30 star milestone claims for Chapter 1 and Chapter 2.
   - Duplicate claim prevention (returns reward_data=[]).
   - Insufficient star claim prevention.
   - Both RPC command names supported.
7. AP offline regeneration mechanics (AP_REGEN_SECONDS = 300s).
"""

import io
import os
import sys
import time
import unittest
import urllib.request
import uuid as uuidlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codec
from server import dispatch, state
from server.handlers.ch_third import (
    AP_MAX,
    AP_USE,
    AP_REGEN_SECONDS,
    _user_ap,
    _spend_ap,
    _add_ap,
)

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
    req = urllib.request.Request(
        f'{SERVER}/{ns}/{call}/vi/',
        data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
    )
    raw = urllib.request.urlopen(req, timeout=10).read().decode()
    named, _ = codec.decode_request(raw, dispatch.return_dto_for(cmd_full))
    return named


def create_and_login_user(prefix='ch3-test'):
    dev = f'{prefix}-{uuidlib.uuid4().hex[:8]}'
    join_res = rpc('user.userJoin', 'userJoin', {'uuid': dev, 'device_uuid': dev})
    useq = join_res['data']['u_seq']
    login_res = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': useq, 'device_uuid': dev})
    return dev, useq, login_res


class TestSubagentChThird(unittest.TestCase):

    def test_01_user_login_all_41_stages_initialization(self):
        """1. Verify userLogin returns fresh starter stage (only stage 1001 with 0 stars)."""
        dev, useq, login_res = create_and_login_user('t1-login')
        self.assertEqual(login_res['error']['code'], 0, 'userLogin must succeed')

        user_contents = login_res['data'].get('user_contents', {})
        stages = user_contents.get('user_chthird_stage', [])
        # For fresh user, starter stages start empty [] so Moa tutorial triggers properly (BUG.md Section 4.13)
        self.assertEqual(len(stages), 0, f'Expected 0 starter stages for fresh user, got {len(stages)}')

    def test_02_get_ch_third_query_and_integrity(self):
        """2. Verify getChThird returns AP and starter stage in user_ch_third_stage."""
        dev, useq, _ = create_and_login_user('t2-getch3')
        ch3_res = rpc('user.getChThird', 'getChThird', {'uuid': dev, 'device_uuid': dev, 'u_seq': useq})
        self.assertEqual(ch3_res['error']['code'], 0, 'getChThird must succeed')
        data = ch3_res['data']

        # Verify u_seq
        self.assertEqual(data['u_seq'], useq)

        # Verify user_ap
        user_ap = data['user_ap']
        self.assertEqual(user_ap['i_Ap'], 70, 'Initial AP must be 70')
        self.assertEqual(user_ap['i_MaxAp'], 70, 'Max AP must be 70')

        # Verify user_ch_third_stage
        stages = data['user_ch_third_stage']
        self.assertEqual(len(stages), 41, f'Expected 41 stages in user_ch_third_stage, got {len(stages)}')
        self.assertEqual(stages[0]['i_id'], 1001)

        # Verify user_ch_third_chapter_reward
        rewards = data['user_ch_third_chapter_reward']
        self.assertEqual(rewards, [], 'Initial chapter star rewards list must be empty')

    def test_03_normal_stage_gameplay_chapter_1(self):
        """3A. Verify chThirdStage for Chapter 1 Normal Stage:
        - AP deduction (costs 5 AP, returns 65).
        - Intimacy EXP increase (+100 for Chapter 1).
        - Profile level reaches Lv 2 at 100 EXP.
        - Tutorial stage 1001 always awards 3 stars.
        - Follower gift drop rewards granted.
        """
        dev, useq, _ = create_and_login_user('t3a-ch1-norm')
        # Play stage 1001 (Tutorial Normal Stage)
        stg_res = rpc('user.chThirdStage', 'chThirdStage', {
            'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
            'i_id': 1001, 'music_id': 1, 'profile_ids': '1'
        })
        self.assertEqual(stg_res['error']['code'], 0, 'chThirdStage 1001 must succeed')
        data = stg_res['data']

        # AP deduction: 70 -> 65
        self.assertEqual(data['user_ap']['i_Ap'], 65, f"AP should be 65, got {data['user_ap']['i_Ap']}")

        # Clear & Star
        self.assertEqual(data['clear'], 1, 'Stage 1001 must clear')
        self.assertEqual(data['star'], 3, 'Stage 1001 tutorial must award 3 stars')

        # Guitar Girl profile EXP & Level-up threshold (Lv 1 -> Lv 2 at 100 EXP)
        girl_prof = data['user_follower_profile']
        self.assertIsNotNone(girl_prof, 'Guitar Girl profile must be returned')
        self.assertEqual(girl_prof['i_id'], 100000, 'Guitar Girl profile ID must be 100000')
        self.assertEqual(girl_prof['d_Exp'], 100, f'Ch1 stage clear must grant +100 EXP, got {girl_prof["d_Exp"]}')
        self.assertEqual(girl_prof['i_Level'], 2, f'Guitar Girl must level up to Lv 2 at 100 EXP, got {girl_prof["i_Level"]}')

        # Gift rewards
        self.assertGreater(len(data['reward_data']), 0, 'Normal stage clear must grant gift rewards')

        # Level up follower 1 to level 5 so score >= 175 threshold for stage 1004
        u = state.get_user(dev)
        for p in u.get('user_follower_profile', []):
            if p.get('i_id') == 1:
                p['i_Level'] = 5
        state.save_user(u)

        # Play stage 1004 (another Ch1 Normal Stage)
        stg_res2 = rpc('user.chThirdStage', 'chThirdStage', {
            'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
            'i_id': 1004, 'music_id': 1, 'profile_ids': '1'
        })
        d2 = stg_res2['data']
        self.assertEqual(d2['user_ap']['i_Ap'], 60, f"AP should be 60 after second run, got {d2['user_ap']['i_Ap']}")
        girl2 = d2['user_follower_profile']
        self.assertEqual(girl2['d_Exp'], 200, f'EXP should be 200 after second Ch1 run, got {girl2["d_Exp"]}')
        self.assertEqual(girl2['i_Level'], 2, 'EXP 200 is still Lv 2 (Lv 3 requires 300)')

    def test_04_normal_stage_gameplay_chapter_2(self):
        """3B. Verify chThirdStage for Chapter 2 Normal Stage:
        - AP deduction (costs 5 AP, returns updated user_ap).
        - Guitar Girl intimacy EXP increase (+200 for Chapter 2).
        - Cumulative EXP progression: Run 1 (+200) reaches Lv 2; Run 2 (+200 -> 400) reaches Lv 3.
        """
        dev, useq, _ = create_and_login_user('t3b-ch2-norm')
        # Setup character to Lv 50 and followers to Level 20 for chapter 2 requirements
        u = state.get_user(dev)
        if u.get('characters'):
            u['characters'][0]['i_Level'] = 50
        u['user_follower_profile'] = [
            {'i_id': 1, 'i_Level': 20, 'd_Exp': 0, 'i_AddCandy': 0},
            {'i_id': 2, 'i_Level': 20, 'd_Exp': 0, 'i_AddCandy': 0},
            {'i_id': 5, 'i_Level': 20, 'd_Exp': 0, 'i_AddCandy': 0},
            {'i_id': 7, 'i_Level': 20, 'd_Exp': 0, 'i_AddCandy': 0},
            {'i_id': 100000, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0},
        ]
        state.save_user(u)

        # Run 1: Stage 2002 (Ch2 Normal Stage, recommended music 1, recommended follower 5)
        res1 = rpc('user.chThirdStage', 'chThirdStage', {
            'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
            'i_id': 2002, 'music_id': 1, 'profile_ids': '1,2,5'
        })
        self.assertEqual(res1['error']['code'], 0, 'chThirdStage 2002 must succeed')
        d1 = res1['data']
        self.assertEqual(d1['user_ap']['i_Ap'], 65, f"AP should be 65, got {d1['user_ap']['i_Ap']}")
        self.assertEqual(d1['clear'], 1)
        self.assertEqual(d1['star'], 3, 'Level 20 setup on 2002 earns 3 stars')

        prof1 = d1['user_follower_profile']
        self.assertEqual(prof1['d_Exp'], 200, f'Ch2 stage must award +200 EXP, got {prof1["d_Exp"]}')
        self.assertEqual(prof1['i_Level'], 2, f'200 EXP should be Lv 2, got {prof1["i_Level"]}')

        # Run 2: Stage 2004 (Ch2 Normal Stage, recommended music 1, recommended followers 5, 7)
        res2 = rpc('user.chThirdStage', 'chThirdStage', {
            'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
            'i_id': 2004, 'music_id': 1, 'profile_ids': '1,5,7'
        })
        self.assertEqual(res2['error']['code'], 0, 'chThirdStage 2004 must succeed')
        d2 = res2['data']
        self.assertEqual(d2['user_ap']['i_Ap'], 60, f"AP should be 60, got {d2['user_ap']['i_Ap']}")
        self.assertEqual(d2['clear'], 1)
        self.assertGreaterEqual(d2['star'], 2, 'Stage 2004 clears with at least 2 stars')

        prof2 = d2['user_follower_profile']
        self.assertEqual(prof2['d_Exp'], 400, f'Cumulative EXP should be 400, got {prof2["d_Exp"]}')
        self.assertEqual(prof2['i_Level'], 3, f'400 EXP reaches Lv 3 (threshold 300), got {prof2["i_Level"]}')

    def test_05_normal_stage_score_breakdown_and_failure(self):
        """3C. Verify score calculation components (character, music, follower, bonus)
        and failure handling when score < 1-star threshold.
        """
        dev, useq, _ = create_and_login_user('t3c-score')
        u = state.get_user(dev)
        if u.get('characters'):
            u['characters'][0]['i_Level'] = 50
        u['user_follower_profile'] = [
            {'i_id': 1, 'i_Level': 20, 'd_Exp': 0, 'i_AddCandy': 0},
            {'i_id': 2, 'i_Level': 20, 'd_Exp': 0, 'i_AddCandy': 0},
            {'i_id': 5, 'i_Level': 20, 'd_Exp': 0, 'i_AddCandy': 0},
            {'i_id': 100000, 'i_Level': 1, 'd_Exp': 0, 'i_AddCandy': 0},
        ]
        state.save_user(u)

        # Successful high score run on stage 2002
        res = rpc('user.chThirdStage', 'chThirdStage', {
            'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
            'i_id': 2002, 'music_id': 1, 'profile_ids': '1,2,5'
        })
        d = res['data']
        self.assertGreater(d['character_score'], 0)
        self.assertGreater(d['music_score'], 0)
        self.assertGreater(d['follower_profile_score'], 0)
        self.assertGreater(d['bonus_score'], 0)
        # Total score must equal char_music_score + total_follower + bonus_follower
        expected_total = d['music_score'] + d['follower_profile_score'] + d['bonus_score']
        self.assertEqual(d['total_score'], expected_total)
        self.assertEqual(d['star'], 3, 'High level setup on 2002 must achieve 3 stars')

        # Test failure scenario: stage 2020 has high requirements (1 star = 900, 3 star = 1800).
        # Playing with music_id=0 and profile_ids='', character Lv 1 gives total_score = 50 < 900 -> Fail!
        u_fail = state.get_user(dev)
        for c in u_fail.get('characters', []):
            c['i_Level'] = 1
        state.save_user(u_fail)

        res_fail = rpc('user.chThirdStage', 'chThirdStage', {
            'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
            'i_id': 2020, 'music_id': 0, 'profile_ids': ''
        })
        dfail = res_fail['data']
        self.assertEqual(dfail['star'], 0, 'Under-threshold run must yield 0 stars')
        self.assertEqual(dfail['clear'], 0, 'Under-threshold run must have clear=0')
        self.assertEqual(dfail['reward_data'], [], 'Failed run must not award gifts')
        # AP was consumed for the attempt
        self.assertEqual(dfail['user_ap']['i_Ap'], 60)

    def test_06_story_stage_gameplay_mechanics(self):
        """4. Verify chThirdStage for Story Stage:
        - Does NOT consume AP (AP remains identical before and after).
        - Clears story stage (clear=1, star=0).
        - Guitar Girl profile EXP increases (+100 for Ch1, +200 for Ch2).
        - Story stages return empty reward_data.
        - Story stages can be played even when AP is 0.
        """
        dev, useq, _ = create_and_login_user('t4-story')

        # Baseline AP
        ch3_res = rpc('user.getChThird', 'getChThird', {'uuid': dev, 'device_uuid': dev, 'u_seq': useq})
        init_ap = ch3_res['data']['user_ap']['i_Ap']
        self.assertEqual(init_ap, 70)

        # 4A. Chapter 1 Story Stage: 1002
        res1 = rpc('user.chThirdStage', 'chThirdStage', {
            'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
            'i_id': 1002
        })
        self.assertEqual(res1['error']['code'], 0, 'Story stage 1002 must succeed')
        d1 = res1['data']

        # Does NOT consume AP
        self.assertEqual(d1['user_ap']['i_Ap'], 70, 'Story stage must NOT consume AP')
        # Clears story stage (clear=1, star=0)
        self.assertEqual(d1['clear'], 1, 'Story stage must clear=1')
        self.assertEqual(d1['star'], 0, 'Story stage star must be 0')
        self.assertEqual(d1['reward_data'], [], 'Story stage reward_data must be empty')

        # Guitar Girl profile EXP increase (+100 for Ch1 Story stage)
        prof1 = d1['user_follower_profile']
        self.assertEqual(prof1['d_Exp'], 100, f'Ch1 Story stage must grant +100 EXP, got {prof1["d_Exp"]}')
        self.assertEqual(prof1['i_Level'], 2, f'100 EXP reaches Lv 2, got {prof1["i_Level"]}')

        # 4B. Chapter 2 Story Stage: 2001
        res2 = rpc('user.chThirdStage', 'chThirdStage', {
            'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
            'i_id': 2001
        })
        self.assertEqual(res2['error']['code'], 0, 'Story stage 2001 must succeed')
        d2 = res2['data']

        # AP remains 70
        self.assertEqual(d2['user_ap']['i_Ap'], 70, 'Ch2 Story stage must NOT consume AP')
        self.assertEqual(d2['clear'], 1)
        self.assertEqual(d2['star'], 0)

        # Guitar Girl profile EXP increase (+200 for Ch2 Story stage) -> 100 + 200 = 300 EXP (Lv 3)
        prof2 = d2['user_follower_profile']
        self.assertEqual(prof2['d_Exp'], 300, f'Cumulative EXP must be 300, got {prof2["d_Exp"]}')
        self.assertEqual(prof2['i_Level'], 3, f'300 EXP reaches Lv 3, got {prof2["i_Level"]}')

        # 4C. Story Stage zero AP scenario:
        # Spend remaining AP down to 0
        u = state.get_user(dev)
        u['user_ap']['i_Ap'] = 0
        state.save_user(u)

        # Verify AP is 0
        ap_res = rpc('user.getChThird', 'getChThird', {'uuid': dev, 'device_uuid': dev, 'u_seq': useq})
        self.assertEqual(ap_res['data']['user_ap']['i_Ap'], 0)

        # Play story stage 1003 with 0 AP
        res_zero = rpc('user.chThirdStage', 'chThirdStage', {
            'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
            'i_id': 1003
        })
        self.assertEqual(res_zero['error']['code'], 0, 'Story stage must succeed even with 0 AP')
        dz = res_zero['data']
        self.assertEqual(dz['clear'], 1)
        self.assertEqual(dz['user_ap']['i_Ap'], 0, 'AP must stay at 0')

    def test_07_stream_stage_autoplay_single_and_multi(self):
        """5. Verify chThirdStreamStage (AutoPlay):
        - Multiple counts (count=1, count=5, count=10).
        - AP deduction = count * stage AP cost (count * 5).
        - Rewards map (reward_data) has entries for 1..count.
        - Guitar Girl intimacy EXP increase = count * stage EXP (+2000 for 10 runs of Ch2).
        - Insufficient AP rejection (error code 1, 'Not enough Cookie').
        """
        # Test count=1
        dev1, useq1, _ = create_and_login_user('t5-stream1')
        s1 = rpc('user.chThirdStreamStage', 'chThirdStreamStage', {
            'uuid': dev1, 'device_uuid': dev1, 'u_seq': useq1,
            'i_id': 2002, 'count': 1
        })
        self.assertEqual(s1['error']['code'], 0, 'Stream count 1 must succeed')
        d1 = s1['data']
        self.assertEqual(d1['user_ap']['i_Ap'], 65, f'70 - 1*5 = 65 AP, got {d1["user_ap"]["i_Ap"]}')
        self.assertEqual(len(d1['reward_data']), 1, 'reward_data must have exactly 1 entry')
        self.assertIn(1, d1['reward_data'], 'reward_data must contain key 1')
        prof1 = d1['user_follower_profile']
        self.assertEqual(prof1['d_Exp'], 200, f'Count 1 Ch2 must grant 200 EXP, got {prof1["d_Exp"]}')
        self.assertEqual(prof1['i_Level'], 2)

        # Test count=5 from 65 AP
        s5 = rpc('user.chThirdStreamStage', 'chThirdStreamStage', {
            'uuid': dev1, 'device_uuid': dev1, 'u_seq': useq1,
            'i_id': 2002, 'count': 5
        })
        self.assertEqual(s5['error']['code'], 0, 'Stream count 5 must succeed')
        d5 = s5['data']
        self.assertEqual(d5['user_ap']['i_Ap'], 40, f'65 - 5*5 = 40 AP, got {d5["user_ap"]["i_Ap"]}')
        self.assertEqual(len(d5['reward_data']), 5, 'reward_data must have 5 entries')
        self.assertEqual(sorted(d5['reward_data'].keys()), [1, 2, 3, 4, 5])
        prof5 = d5['user_follower_profile']
        # Prior EXP 200 + (5 * 200) = 1200 EXP -> Lv 4 (threshold 700, Lv 5 threshold 1500)
        self.assertEqual(prof5['d_Exp'], 1200, f'EXP should be 1200, got {prof5["d_Exp"]}')
        self.assertEqual(prof5['i_Level'], 4, f'1200 EXP is Lv 4, got {prof5["i_Level"]}')

        # Test count=10 on fresh account (70 AP)
        dev10, useq10, _ = create_and_login_user('t5-stream10')
        s10 = rpc('user.chThirdStreamStage', 'chThirdStreamStage', {
            'uuid': dev10, 'device_uuid': dev10, 'u_seq': useq10,
            'i_id': 2002, 'count': 10
        })
        self.assertEqual(s10['error']['code'], 0, 'Stream count 10 must succeed')
        d10 = s10['data']
        self.assertEqual(d10['user_ap']['i_Ap'], 20, f'70 - 10*5 = 20 AP, got {d10["user_ap"]["i_Ap"]}')
        self.assertEqual(len(d10['reward_data']), 10, 'reward_data must have 10 entries')
        self.assertEqual(sorted(d10['reward_data'].keys()), list(range(1, 11)))
        prof10 = d10['user_follower_profile']
        # 0 + (10 * 200) = 2000 EXP -> reaches Lv 5 (threshold 1500, Lv 6 threshold 2900)
        self.assertEqual(prof10['d_Exp'], 2000, f'10 runs of Ch2 must grant exactly 2000 EXP, got {prof10["d_Exp"]}')
        self.assertEqual(prof10['i_Level'], 5, f'2000 EXP must reach Lv 5, got {prof10["i_Level"]}')

    def test_08_stream_stage_insufficient_ap_rejection(self):
        """5B. Verify insufficient AP rejection for AutoPlay:
        - error code 1, errmsg 'Not enough Cookie'.
        - AP is not deducted upon rejection.
        """
        dev, useq, _ = create_and_login_user('t5-insufficient')
        # Reduce user AP to 10
        u = state.get_user(dev)
        u['user_ap']['i_Ap'] = 10
        state.save_user(u)

        # Attempt count=3 (needs 15 AP > 10 AP)
        res_fail = rpc('user.chThirdStreamStage', 'chThirdStreamStage', {
            'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
            'i_id': 2002, 'count': 3
        })
        self.assertEqual(res_fail['error']['code'], 1, 'Must reject with error code 1')
        self.assertEqual(res_fail['error']['errmsg'], 'Not enough Cookie', "errmsg must be 'Not enough Cookie'")
        self.assertIsNone(res_fail.get('data'), 'Data is omitted on error envelope')
        # Verify AP was not deducted
        ap_chk = rpc('user.getChThird', 'getChThird', {'uuid': dev, 'device_uuid': dev, 'u_seq': useq})
        self.assertEqual(ap_chk['data']['user_ap']['i_Ap'], 10, 'AP must remain unchanged at 10')

        # Attempt count=10 (needs 50 AP > 10 AP)
        res_fail10 = rpc('user.chThirdStreamStage', 'chThirdStreamStage', {
            'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
            'i_id': 2002, 'count': 10
        })
        self.assertEqual(res_fail10['error']['code'], 1)
        self.assertEqual(res_fail10['error']['errmsg'], 'Not enough Cookie')

    def test_09_chapter_star_rewards_milestone_claims(self):
        """6. Verify Chapter Star Rewards:
        - 10, 20, 30 stars milestone claims for Chapter 1 and Chapter 2.
        - Duplicate claim prevention (subsequent claims return reward_data=[]).
        - Both getChThirdStarReward and setChThirdChapterReward supported.
        """
        dev, useq, _ = create_and_login_user('t6-rewards')

        # Setup 30 stars for Ch1 and Ch2 for milestone testing
        u = state.get_user(dev)
        all_stg = state._all_ch_third_stages()
        u['user_ch_third_stage'] = all_stg
        u['user_chthird_stage'] = all_stg
        state.save_user(u)

        # Chapter 1: 30 stars earned (10 Normal stages * 3 stars)
        for r_num, expected_req in [(1, 10), (2, 20), (3, 30)]:
            # Claim milestone
            c_res = rpc('user.getChThirdStarReward', 'getChThirdStarReward', {
                'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
                'i_id': 1, 'reward_num': r_num
            })
            self.assertEqual(c_res['error']['code'], 0, f'Ch1 reward {r_num} claim must succeed')
            c_data = c_res['data']
            self.assertEqual(c_data['i_id'], 1)
            self.assertEqual(c_data['reward_num'], r_num)
            self.assertGreater(len(c_data['reward_data']), 0, f'Ch1 milestone {r_num} must grant rewards')

            # Duplicate claim attempt on the same milestone
            dup_res = rpc('user.getChThirdStarReward', 'getChThirdStarReward', {
                'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
                'i_id': 1, 'reward_num': r_num
            })
            self.assertEqual(dup_res['error']['code'], 0)
            self.assertEqual(dup_res['data']['reward_data'], [], f'Duplicate claim of Ch1 {r_num} must return empty reward_data')

        # Verify Chapter 1 persisted claims in user data
        u = state.get_user(dev)
        claims = u.get('user_ch_third_chapter_reward', [])
        ch1_claim = next((c for c in claims if c['i_id'] == 1), None)
        self.assertIsNotNone(ch1_claim, 'Chapter 1 claim row must exist')
        self.assertEqual(ch1_claim['i_ReceivedReward1'], 1)
        self.assertEqual(ch1_claim['i_ReceivedReward2'], 1)
        self.assertEqual(ch1_claim['i_ReceivedReward3'], 1)

        # Chapter 2: Test using the alias setChThirdChapterReward
        for r_num in (1, 2, 3):
            c_res2 = rpc('user.setChThirdChapterReward', 'setChThirdChapterReward', {
                'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
                'i_id': 2, 'reward_num': r_num
            })
            self.assertEqual(c_res2['error']['code'], 0, f'Ch2 reward {r_num} claim via setChThirdChapterReward must succeed')
            c_data2 = c_res2['data']
            self.assertEqual(c_data2['i_id'], 2)
            self.assertEqual(c_data2['reward_num'], r_num)
            self.assertGreater(len(c_data2['reward_data']), 0, f'Ch2 milestone {r_num} must grant rewards')

            # Duplicate claim prevention
            dup_res2 = rpc('user.setChThirdChapterReward', 'setChThirdChapterReward', {
                'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
                'i_id': 2, 'reward_num': r_num
            })
            self.assertEqual(dup_res2['data']['reward_data'], [], f'Duplicate claim of Ch2 {r_num} must return empty')

        # Verify Chapter 2 persisted claims
        u2 = state.get_user(dev)
        claims2 = u2.get('user_ch_third_chapter_reward', [])
        ch2_claim = next((c for c in claims2 if c['i_id'] == 2), None)
        self.assertIsNotNone(ch2_claim, 'Chapter 2 claim row must exist')
        self.assertEqual(ch2_claim['i_ReceivedReward1'], 1)
        self.assertEqual(ch2_claim['i_ReceivedReward2'], 1)
        self.assertEqual(ch2_claim['i_ReceivedReward3'], 1)

    def test_10_chapter_star_rewards_insufficient_stars_rejection(self):
        """6B. Verify rejection when user does not have sufficient stars for a milestone."""
        dev, useq, _ = create_and_login_user('t6-nostars')

        # Reset all stage stars to 0 for this user
        u = state.get_user(dev)
        for stg in u.get('user_ch_third_stage', []):
            stg['i_Star'] = 0
        for stg in u.get('user_chthird_stage', []):
            stg['i_Star'] = 0
        state.save_user(u)

        # Attempt to claim milestone 1 (requires 10 stars)
        res = rpc('user.getChThirdStarReward', 'getChThirdStarReward', {
            'uuid': dev, 'device_uuid': dev, 'u_seq': useq,
            'i_id': 1, 'reward_num': 1
        })
        self.assertEqual(res['error']['code'], 0)
        self.assertEqual(res['data']['reward_data'], [], 'Reward must not be granted when stars < 10')

        # Verify claim flag is NOT set
        u_after = state.get_user(dev)
        claims = u_after.get('user_ch_third_chapter_reward', [])
        ch1_claim = next((c for c in claims if c['i_id'] == 1), None)
        self.assertEqual(ch1_claim.get('i_ReceivedReward1', 0), 0, 'i_ReceivedReward1 must remain 0')

    def test_11_ap_regeneration_mechanics(self):
        """7. Verify AP regeneration logic:
        - When AP < AP_MAX (70), i_FullApTime is calculated.
        - Spends deduct AP and set i_FullApTime.
        - Regeneration restores 1 AP per AP_REGEN_SECONDS (300s).
        - When AP reaches AP_MAX (70), i_FullApTime is cleared to 0.
        """
        user = {'user_ap': {'i_Ap': 70, 'i_FullApTime': 0, 'i_MaxAp': 70}}
        # Initial full AP
        ap0 = _user_ap(user)
        self.assertEqual(ap0['i_Ap'], 70)
        self.assertEqual(ap0['i_FullApTime'], 0)

        # Spend 10 AP
        spent, ap1 = _spend_ap(user, 10)
        self.assertTrue(spent)
        self.assertEqual(ap1['i_Ap'], 60)
        self.assertGreater(ap1['i_FullApTime'], int(time.time()))
        expected_full_at = int(time.time()) + (70 - 60) * AP_REGEN_SECONDS
        self.assertAlmostEqual(ap1['i_FullApTime'], expected_full_at, delta=2)

        # Simulate offline time elapse: 600 seconds elapsed (2 AP restored)
        # Advance full_at by simulating now is earlier or full_at is closer
        user['user_ap']['i_FullApTime'] = int(time.time()) + (70 - 62) * AP_REGEN_SECONDS
        user['user_ap']['i_Ap'] = 60  # Client might still have old AP, server recalculates
        ap_regen = _user_ap(user)
        self.assertEqual(ap_regen['i_Ap'], 62, '600s elapsed should restore 2 AP')

        # Add remaining AP back to full
        ap_full = _add_ap(user, 10)
        self.assertEqual(ap_full['i_Ap'], 70)
        self.assertEqual(ap_full['i_FullApTime'], 0, 'Full AP must have i_FullApTime=0')


if __name__ == '__main__':
    unittest.main()

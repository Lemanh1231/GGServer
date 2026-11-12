#!/usr/bin/env python3
"""Test for Daily Missions (user_daily_mission) lifecycle.

Verifies:
1. Daily Mission 1 ("Đăng nhập nhiều hơn 1 lần") starts at progress 1 (1/1) on login.
2. Claiming Mission 1 grants 10 CP and advances i_Level to 2.
3. userSave sending d_Quantity=0 cannot overwrite Mission 1 back to 0.
4. Mission 6 ("Hoàn thành toàn bộ Nhiệm vụ hàng ngày") automatically reflects completed count (1/5).
5. Logging in again on the same day preserves progress and claimed state.
6. Simulating a new calendar day resets all missions, with Mission 1 ready as 1/1 for the new day.
"""
import os, sys, io, json, uuid as uuidlib, urllib.request

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
    req = urllib.request.Request(SERVER + '/user/%s/vi/' % call, data=body,
                                 headers={'Content-Type': 'multipart/form-data; boundary=%s' % boundary})
    raw = urllib.request.urlopen(req, timeout=10).read().decode()
    named, _ = codec.decode_request(raw, dispatch.return_dto_for(cmd_full))
    return named['data']


def main():
    dev = 'dm-test-' + uuidlib.uuid4().hex[:8]
    j = rpc('user.userJoin', 'userJoin', {'uuid': dev, 'device_uuid': dev})
    useq = j['u_seq']

    # 1. Login should return user_daily_mission with Mission 1 at d_Quantity=1
    login_resp = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'device_uuid': dev, 'u_seq': useq})
    dm = login_resp['user_contents']['user_daily_mission']
    m1 = next(m for m in dm if m['i_id'] == 1)
    m6 = next(m for m in dm if m['i_id'] == 6)

    assert m1['d_Quantity'] == 1, f"Mission 1 must start with d_Quantity=1, got {m1['d_Quantity']}"
    assert m1['i_Level'] == 1, f"Mission 1 must start at i_Level=1, got {m1['i_Level']}"
    assert m6['d_Quantity'] == 1, f"Mission 6 must reflect 1 completed mission, got {m6['d_Quantity']}"
    print("[PASS] Login initializes Mission 1 at 1/1, Mission 6 at 1/5")

    # 2. Claim Mission 1 reward
    claim_resp = rpc('user.setGameReward', 'setGameReward', {
        'uuid': dev, 'device_uuid': dev, 'id': 1, 'level': 1, 'type': 'daily_mission'
    })
    assert claim_resp['status'] == 'Y', f"Claim must succeed, got {claim_resp['status']}"
    assert claim_resp['reward_value'] == 10, f"Claim must grant 10 CP, got {claim_resp['reward_value']}"
    assert claim_resp['level'] == 2, f"Mission 1 level must advance to 2, got {claim_resp['level']}"
    print("[PASS] Claim Mission 1 granted 10 CP, advanced level to 2")

    # 3. Simulate client userSave sending compact payload with d_Quantity=0 for Mission 1
    save_resp = rpc('user.userSave', 'userSave', {
        'uuid': dev, 'device_uuid': dev,
        'user_daily_mission': [
            {'i_id': 1, 'd_Quantity': 0},
            {'i_id': 2, 'd_Quantity': 50},
            {'i_id': 3, 'd_Quantity': 0},
            {'i_id': 4, 'd_Quantity': 0},
            {'i_id': 5, 'd_Quantity': 100},
            {'i_id': 6, 'd_Quantity': 0},
        ]
    })
    assert save_resp['status'] == 'Y', f"userSave failed: {save_resp}"

    # Verify user state after userSave
    u = state.get_user(dev)
    u_m1 = next(m for m in u['user_daily_mission'] if m['i_id'] == 1)
    u_m6 = next(m for m in u['user_daily_mission'] if m['i_id'] == 6)
    assert u_m1['d_Quantity'] == 1, f"userSave must NOT revert Mission 1 to 0, got {u_m1['d_Quantity']}"
    assert u_m1['i_Level'] == 2, f"userSave must preserve claimed level 2, got {u_m1['i_Level']}"
    assert u_m6['d_Quantity'] == 1, f"Mission 6 must keep count 1, got {u_m6['d_Quantity']}"
    print("[PASS] userSave cannot overwrite Mission 1 back to 0 or reset level")

    # 4. Same-day reconnect / login preserves claimed state
    relogin_resp = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'device_uuid': dev, 'u_seq': useq})
    dm_relogin = relogin_resp['user_contents']['user_daily_mission']
    rel_m1 = next(m for m in dm_relogin if m['i_id'] == 1)
    assert rel_m1['i_Level'] == 2, f"Same day relogin must preserve level 2, got {rel_m1['i_Level']}"
    assert rel_m1['d_Quantity'] == 1, f"Same day relogin must preserve d_Quantity 1, got {rel_m1['d_Quantity']}"
    print("[PASS] Same-day relogin preserves claimed state")

    # 5. Simulate next calendar day (rewind daily_mission_date to yesterday)
    u['daily_mission_date'] = 20261001
    state.save_user(u)

    next_day_login = rpc('user.userLogin', 'userLogin', {'uuid': dev, 'device_uuid': dev, 'u_seq': useq})
    dm_next_day = next_day_login['user_contents']['user_daily_mission']
    nd_m1 = next(m for m in dm_next_day if m['i_id'] == 1)
    nd_m2 = next(m for m in dm_next_day if m['i_id'] == 2)
    assert nd_m1['i_Level'] == 1, f"New day must reset Mission 1 level to 1, got {nd_m1['i_Level']}"
    assert nd_m1['d_Quantity'] == 1, f"New day must set Mission 1 quantity to 1, got {nd_m1['d_Quantity']}"
    assert nd_m2['d_Quantity'] == 0, f"New day must reset Mission 2 quantity to 0, got {nd_m2['d_Quantity']}"
    print("[PASS] New calendar day resets all daily missions, Mission 1 ready as 1/1")

    # Cleanup test user
    try:
        conn = state.get_db()
        conn.execute('DELETE FROM user_data WHERE uuid = ?', (dev,))
        conn.commit()
    except Exception:
        pass

    print("\nALL DAILY MISSION TESTS PASSED!")


if __name__ == '__main__':
    main()

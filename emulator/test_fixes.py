#!/usr/bin/env python3
"""Automated tests for:
1. Star Pass item purchase: rejects when CP is insufficient, deducts CP when sufficient.
2. 7-day attendance event: claimable via setEventReward even after setAttendance(add), reject duplicates.
3. Meow event: rewards 1x scratcher guitar (not 333).
"""
import os, sys, io, uuid as uuidlib, urllib.request
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

def main():
    dev = 'fix-test-' + uuidlib.uuid4().hex[:8]
    j = rpc('user.userJoin', 'userJoin', {'uuid': dev, 'device_uuid': dev})
    u_seq = j['data']['u_seq']
    rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})

    # ==========================================
    # Test 1: Star Pass purchase & CP deduction
    # ==========================================
    # Fresh user has 0 CP. Trying to buy Star Pass 1013 (price: 150 CP) must fail.
    res = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 1013})
    assert res['error']['code'] != 0, f"Buying Star Pass with 0 CP must fail, got {res}"
    print("[PASS] Star Pass purchase rejected when CP is insufficient: %s" % res['error']['errmsg'])

    # Add 200 CP to user
    state.increment_currency(dev, cp=200)
    u = state.get_user(dev)
    u['userdata']['u_cp'] = 200
    state.save_user(u)

    # Now buy Star Pass 1013 (price: 150 CP)
    res = rpc('store.buyShop', 'buyShop', {'uuid': dev, 'device_uuid': dev, 'idx': 1013})
    assert res['error']['code'] == 0, f"Buying Star Pass with 200 CP must succeed, got {res}"
    u_after = state.get_user(dev)
    assert u_after['userdata']['u_cp'] == 50, f"CP must be deducted to 50, got {u_after['userdata']['u_cp']}"
    assert any(s.get('i_SubscribeID') == 1013 for s in u_after.get('user_subscribe_list', [])), "Must have 1013 in subscribe list"
    assert any(t.get('i_id') == 13 for t in u_after.get('user_ticketcollection', [])), "Must have Season 13 ticket"
    print("[PASS] Star Pass purchase deducted 150 CP and granted pass (remaining CP: %s)" % u_after['userdata']['u_cp'])

    # ==========================================
    # Test 2: 7-Day Attendance Event
    # ==========================================
    # Simulate login calling setAttendance(add)
    att_res = rpc('user.setAttendance', 'setAttendance', {'uuid': dev, 'device_uuid': dev, 'type': 'add'})
    assert att_res['data']['status'] == 'Y', "setAttendance(add) should return Y"

    # User opens 7-day attendance popup and claims Day 1
    ev_res = rpc('user.setEventReward', 'setEventReward', {'uuid': dev, 'device_uuid': dev, 'event_idx': 1})
    assert ev_res['data']['status'] == 'Y', f"setEventReward must succeed with status Y, got {ev_res['data']['status']}"
    assert ev_res['data']['reward_type'] == 1 and ev_res['data']['reward_id'] == 1 and ev_res['data']['reward_value'] == 100, \
        "Day 1 must give 100 Socola (CP)"
    # User's CP was 50, now + 100 = 150
    assert ev_res['data']['u_cp'] == 150, f"Day 1 reward must add 100 CP, got {ev_res['data']['u_cp']}"
    print("[PASS] 7-Day Attendance Day 1 successfully claimed after login sequence (CP: %s)" % ev_res['data']['u_cp'])

    # Second claim on the same day must be rejected
    ev_res2 = rpc('user.setEventReward', 'setEventReward', {'uuid': dev, 'device_uuid': dev, 'event_idx': 1})
    assert ev_res2['data']['status'] == 'N', "Second claim on same day must be rejected with N"
    print("[PASS] 7-Day Attendance duplicate claim rejected")

    # ==========================================
    # Test 3: Meow Event 1x reward (not 333)
    # ==========================================
    sam_list = rpc('eventMode.getSamSeckList', 'getSamSeckList', {'uuid': dev, 'device_uuid': dev})
    for slot in sam_list['data']['rewardList']:
        assert slot['d_RewardQuantity'] == 1.0, f"Slot {slot['i_id']} quantity must be 1.0, got {slot['d_RewardQuantity']}"
    print("[PASS] Meow event rewardList offers 1.0 quantity for all slots")

    # Claim step 1 (Calico Cat Scratcher guitar)
    claim_sam = rpc('eventMode.getSamSeckReward', 'getSamSeckReward', {'uuid': dev, 'device_uuid': dev, 'i_id': 1})
    u_sam = state.get_user(dev)
    guitars_10 = [g for g in u_sam.get('user_guitar', []) if g.get('i_id') == 10]
    assert len(guitars_10) == 1, f"User should have exactly 1 guitar 10, got {len(guitars_10)}"
    print("[PASS] Meow event step 1 granted exactly 1 guitar (not 333)")

    # Cleanup test user
    try:
        conn = state.get_db()
        conn.execute('DELETE FROM user_data WHERE uuid = ?', (dev,))
        conn.execute('DELETE FROM user_inventory WHERE uuid = ?', (dev,))
        conn.commit()
    except Exception:
        pass

    print("\nALL 3 FIX VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    main()

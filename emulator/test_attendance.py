#!/usr/bin/env python3
"""End-to-end test for the attendance / event-reward (출석부) flow.

Drives the running server exactly as the client would (multipart WWWForm + the real
base64/bzip2/thrift codec) and asserts the corrected behaviour:

  1. progression starts at DAY 1 (not a jump to day 7),
  2. each board (event_idx) gives at most ONE reward per calendar day,
  3. the day advances by exactly one per calendar day, wrapping after the last day,
  4. boards are independent of each other,
  5. setAttendance reports the same day that setEventReward will grant.

Calendar-day rollover is simulated by rewinding the stored `ymd` in the user file
(the same thing a real "next day" would produce), so the whole 7-day cycle is covered
without waiting. Run the server first:  python3 run.py --port 8080
"""
import os, sys, io, json, uuid as uuidlib, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codec
from server import dispatch, state

SERVER = os.environ.get('GG_TEST_URL', 'http://127.0.0.1:8080')

# event_idx 1 (출석부) reward table, day -> (reward_type, reward_id, reward_value), from getEventRewardList
EV1_DAYS = {1: (1, 1, 100), 2: (3, 9, 1), 3: (1, 1, 200), 4: (1, 2, 50),
            5: (1, 1, 300), 6: (1, 2, 50), 7: (2, 13, 1)}


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


def claim(dev, event_idx):
    return rpc('user.setEventReward', 'setEventReward',
               {'uuid': dev, 'device_uuid': dev, 'event_idx': event_idx})


def attendance(dev):
    return rpc('user.setAttendance', 'setAttendance',
               {'uuid': dev, 'device_uuid': dev, 'type': 'check'})


def rewind_day(dev, event_idx):
    """Pretend a calendar day passed for one board by clearing its last-claim date."""
    u = state.get_user(dev)
    u['attendance'][str(event_idx)]['ymd'] = 0
    state.save_user(u)


def main():
    dev = 'att-test-' + uuidlib.uuid4().hex[:8]
    rpc('user.userJoin', 'userJoin', {'uuid': dev, 'device_uuid': dev})

    # --- starts at DAY 1, and setAttendance agrees ---
    assert attendance(dev)['attendance_count'] == 1, "fresh user must show day 1"
    d = claim(dev, 1)
    base_candy = d['u_candy']
    assert d['status'] == 'Y' and (d['reward_type'], d['reward_id'], d['reward_value']) == EV1_DAYS[1], \
        "first claim must grant day-1 reward"
    print("day1  board1 -> Y %s candy=%s" % (EV1_DAYS[1], d['u_candy']))

    # --- one claim per board per day: a repeat is rejected with no currency change ---
    d2 = claim(dev, 1)
    assert d2['status'] == 'N' and d2['reward_value'] == 0 and d2['u_candy'] == base_candy, \
        "second same-day claim must be rejected and grant nothing"
    print("day1  board1 again -> N (blocked, candy unchanged=%s)" % d2['u_candy'])

    # --- boards are independent: board 3 still claimable the same day ---
    d3 = claim(dev, 3)
    assert d3['status'] == 'Y' and (d3['reward_type'], d3['reward_id'], d3['reward_value']) == (11, 1, 50), \
        "board 3 is a separate daily and must grant its day-1 reward"
    print("day1  board3 -> Y (11,1,50) independent")

    # --- walk the full 7-day cycle for board 1, one reward per simulated day ---
    for day in range(2, 8):
        rewind_day(dev, 1)
        assert attendance(dev)['attendance_count'] == day, "setAttendance must show day %d" % day
        d = claim(dev, 1)
        assert d['status'] == 'Y' and (d['reward_type'], d['reward_id'], d['reward_value']) == EV1_DAYS[day], \
            "day %d reward mismatch: got %s" % (day, (d['reward_type'], d['reward_id'], d['reward_value']))
        print("day%-2d board1 -> Y %s" % (day, EV1_DAYS[day]))

    # --- after the last day it wraps back to day 1 ---
    rewind_day(dev, 1)
    assert attendance(dev)['attendance_count'] == 1, "after day 7 the board must wrap to day 1"
    d = claim(dev, 1)
    assert (d['reward_type'], d['reward_id'], d['reward_value']) == EV1_DAYS[1], "wrap must grant day-1 reward"
    print("day8  board1 -> Y %s (wrapped to day 1)" % (EV1_DAYS[1],))

    # cleanup test user
    try:
        os.remove(state._path(dev))
    except OSError:
        pass

    print("\nALL ATTENDANCE E2E TESTS PASSED")


if __name__ == '__main__':
    main()

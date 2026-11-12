#!/usr/bin/env python3
"""Automated tests for user notifications (posts/mail) in Guitar Girl emulator."""
import os, sys, io, uuid as uuidlib, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codec
from server import dispatch, state
from server.handlers.post import send_post

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
    dev = 'notif-test-' + uuidlib.uuid4().hex[:8]
    j = rpc('user.userJoin', 'userJoin', {'uuid': dev, 'device_uuid': dev})
    u_seq = j['data']['u_seq']
    rpc('user.userLogin', 'userLogin', {'uuid': dev, 'u_seq': u_seq, 'device_uuid': dev})

    # 1. Fetch initial posts (should have welcome post)
    res = rpc('post.getPost', 'getPost', {'uuid': dev, 'device_uuid': dev})
    posts = res['data']['post_list']
    assert len(posts) >= 1, "User should receive initial post"
    print(f"[PASS] Initial getPost returned {len(posts)} post(s)")

    # 2. Send test notification with 300 CP and 50 Candy to this user
    notif = send_post(
        uuid=dev,
        title="Thông báo thử nghiệm hệ thống",
        memo="Đây là thông báo test gửi đến người chơi qua hệ thống hòm thư!",
        items=[
            {'i_RewardType': 1, 'i_RewardId': 1, 'd_RewardQuantity': 300.0},
            {'i_RewardType': 1, 'i_RewardId': 2, 'd_RewardQuantity': 50.0},
        ]
    )
    assert notif is not None, "send_post should succeed"
    notif_idx = notif['idx']
    print(f"[PASS] Sent test notification #{notif_idx} with 300 CP and 50 Candy")

    # 3. getPost should now include this new notification
    res = rpc('post.getPost', 'getPost', {'uuid': dev, 'device_uuid': dev})
    posts = res['data']['post_list']
    target = next((p for p in posts if p.get('idx') == notif_idx), None)
    assert target is not None, f"Notification #{notif_idx} should be in user's post list"
    assert target['title_vi'] == "Thông báo thử nghiệm hệ thống"
    assert target['have_reward'] == 1
    print(f"[PASS] getPost confirmed receipt of notification #{notif_idx}")

    # 4. Check initial currency
    u_before = state.get_user(dev)
    cp_before = int(u_before['userdata'].get('u_cp', 0) or 0)
    candy_before = float(u_before['userdata'].get('u_candy', 0.0) or 0.0)

    # 5. Claim rewards via providePost
    prov = rpc('post.providePost', 'providePost', {'uuid': dev, 'device_uuid': dev, 'idx': notif_idx})
    items_received = prov['data']
    assert len(items_received) == 2, f"Should receive 2 reward items, got {len(items_received)}"

    u_after = state.get_user(dev)
    cp_after = int(u_after['userdata'].get('u_cp', 0) or 0)
    candy_after = float(u_after['userdata'].get('u_candy', 0.0) or 0.0)

    assert cp_after == cp_before + 300, f"CP should increase by 300, was {cp_before} -> {cp_after}"
    assert candy_after == candy_before + 50.0, f"Candy should increase by 50, was {candy_before} -> {candy_after}"
    print(f"[PASS] providePost successfully claimed rewards: CP {cp_before}->{cp_after}, Candy {candy_before}->{candy_after}")

    # 5.1 Verify that after claiming, post has have_reward=0, status=1, AND flg=1 (read flag)
    # so client's AnyoneConfirm() does NOT trigger red dot notification!
    res_claimed = rpc('post.getPost', 'getPost', {'uuid': dev, 'device_uuid': dev})
    p_claimed = next(p for p in res_claimed['data']['post_list'] if p.get('idx') == notif_idx)
    assert p_claimed['have_reward'] == 0, "Claimed post should have have_reward=0"
    assert p_claimed['status'] == 1, "Claimed post should have status=1"
    assert p_claimed['flg'] == 1, "Claimed post should have flg=1 so client treats it as read!"
    print(f"[PASS] Claimed post properly flagged with have_reward=0, status=1, flg=1")

    # 5.2 Test readPost for text notifications
    text_notif = send_post(uuid=dev, title="Thông báo chữ", memo="Nội dung đọc", items=[])
    text_idx = text_notif['idx']
    rpc('post.readPost', 'readPost', {'uuid': dev, 'device_uuid': dev, 'idx': text_idx})
    res_read = rpc('post.getPost', 'getPost', {'uuid': dev, 'device_uuid': dev})
    p_read = next(p for p in res_read['data']['post_list'] if p.get('idx') == text_idx)
    assert p_read['status'] == 1 and p_read['flg'] == 1, "Read post should have status=1 and flg=1"
    print(f"[PASS] readPost properly flagged with status=1, flg=1")

    # 6. Test Delete All Read Mail via deletePost(idx=0, type=1)
    del_all = rpc('post.deletePost', 'deletePost', {'uuid': dev, 'device_uuid': dev, 'idx': 0, 'type': 1})
    res_after_all = rpc('post.getPost', 'getPost', {'uuid': dev, 'device_uuid': dev})
    remaining_after_all = [p for p in res_after_all['data']['post_list'] if p.get('idx') in (notif_idx, text_idx)]
    assert len(remaining_after_all) == 0, "Delete All Read Mail (idx=0, type=1) should remove read/claimed posts"
    print(f"[PASS] deletePost(idx=0, type=1) successfully deleted all read/claimed mail")

    # 7. Test Honkai: Star Rail Mailbox Rule (New accounts do NOT receive historical broadcasts)
    import time
    dev_newer = 'notif-hsr-' + uuidlib.uuid4().hex[:8]
    time.sleep(1)
    bc_mail = send_post(uuid=None, title="Thông báo bảo trì trước đó", memo="Thư hệ thống cũ")
    time.sleep(1)

    # Register user AFTER broadcast was dispatched
    j_newer = rpc('user.userJoin', 'userJoin', {'uuid': dev_newer, 'device_uuid': dev_newer})
    rpc('user.userLogin', 'userLogin', {'uuid': dev_newer, 'u_seq': j_newer['data']['u_seq'], 'device_uuid': dev_newer})
    res_newer = rpc('post.getPost', 'getPost', {'uuid': dev_newer, 'device_uuid': dev_newer})
    newer_posts = res_newer['data']['post_list']

    # Must only receive Welcome Post (idx 1), not the pre-existing broadcast
    assert len(newer_posts) == 1, f"New account must only have 1 post (Welcome), got {len(newer_posts)}"
    assert newer_posts[0]['idx'] == 1, "New account post must be Welcome post"
    assert not any(p.get('idx') == bc_mail['idx'] for p in newer_posts), "New account must NOT receive old broadcast!"
    print(f"[PASS] Honkai Star Rail rule verified: New account did not receive historical broadcast #{bc_mail['idx']}")

    # Clean up test users
    try:
        conn = state.get_db()
        conn.execute('DELETE FROM user_data WHERE uuid IN (?, ?)', (dev, dev_newer))
        conn.execute('DELETE FROM user_inventory WHERE uuid IN (?, ?)', (dev, dev_newer))
        conn.commit()
    except Exception:
        pass

    # Clean up test broadcast from broadcasts
    from server.handlers import post
    broadcasts = [b for b in post._load_broadcast_posts() if b.get('idx') != bc_mail['idx']]
    post._save_broadcast_posts(broadcasts)

    print("\nALL NOTIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""End-to-end test: simulate the client's exact encoding, POST to the running server,
decode responses as the client would. Exercises the full boot/login chain + auth + CDN."""
import os, sys, io, json, uuid as uuidlib, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import codec
from server import dispatch

SERVER = os.environ.get('GG_TEST_URL', 'http://127.0.0.1:8080')

def multipart_body(fields):
    boundary = '----gg' + uuidlib.uuid4().hex
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(('--%s\r\n' % boundary).encode())
        out.write(('Content-Disposition: form-data; name="%s"\r\n\r\n' % k).encode())
        out.write(v.encode() if isinstance(v, str) else v)
        out.write(b'\r\n')
    out.write(('--%s--\r\n' % boundary).encode())
    return boundary, out.getvalue()

def rpc(cmd_full, call, envelope):
    b64 = codec.encode_response(cmd_full, envelope)
    boundary, body = multipart_body({'call': call, 'tapsonic_data': b64,
                                     'access_token': '', 'current_time': '0'})
    req = urllib.request.Request(SERVER + '/main/%s/en/' % call, data=body,
        headers={'Content-Type': 'multipart/form-data; boundary=%s' % boundary})
    raw = urllib.request.urlopen(req, timeout=10).read().decode()
    rdto = dispatch.return_dto_for(cmd_full)
    named, _ = codec.decode_request(raw, rdto)
    return named

def env(call, data):
    return {'call': call, 'data': data, 'common_data': {'client_ver': 800, 'type': 'aos', 'os': 1}}

def main():
    dev = 'emu-test-' + uuidlib.uuid4().hex[:8]

    out = rpc('main.Request', 'Request', env('Request', {'type': 'aos', 'os': 1, 'ver': 800, 'device_uuid': dev}))
    print("INIT  error=%s idx=%s game_url=%s cdn_url=%s" % (out['error'], out['data']['idx'],
          out['data']['game_url'], out['data']['cdn_url']))
    assert out['error']['code'] == 0 and out['data']['idx'] == 253

    out = rpc('user.userJoin', 'userJoin', env('userJoin', {'uuid': dev, 'device_uuid': dev}))
    print("JOIN  u_seq=%s u_id=%s" % (out['data']['u_seq'], out['data']['u_id']))
    assert out['data']['u_seq'] > 0

    out = rpc('user.userLogin', 'userLogin', env('userLogin', {'uuid': dev, 'u_seq': out['data']['u_seq'], 'device_uuid': dev}))
    uc = out['data']['user_contents']
    print("LOGIN nick=%s areas=%s contents_nonempty=%d/27 followers=%d music=%d shop=%d tickets=%d" % (
        out['data']['user']['u_nick'], list(out['data']['area_data'].keys()),
        sum(1 for v in uc.values() if v), len(uc.get('user_follower', [])),
        len(uc.get('user_music', [])), len(uc.get('user_shop', [])), len(uc.get('user_ticketcollection', []))))
    assert out['error']['code'] == 0 and out['data']['user']['u_seq'] > 0
    assert len(uc['user_follower']) == 4 and len(uc['user_ticketcollection']) == 13

    out = rpc('main.getServerTime', 'getServerTime', env('getServerTime', {'device_uuid': dev}))
    print("TIME  %s" % out['data']); assert out['data']['time'] > 0

    out = rpc('main.getUpdateTime', 'getUpdateTime', env('getUpdateTime', {'device_uuid': dev}))
    print("UPDT  %s" % out['data']); assert out['data']['upd_time'] > 0

    out = rpc('main.defaultSettingList', 'defaultSettingList', env('defaultSettingList', {}))
    print("SETT  status=%s n=%d" % (out['data']['status'], len(out['data']['setting_list'])))
    assert out['data']['status'] == 'Y' and len(out['data']['setting_list']) == 27

    # static getGameDataList
    boundary, bod = multipart_body({'call': 'getGameDataList', 'tapsonic_data': 'x'})
    r = urllib.request.Request(SERVER + '/main/getGameDataList/en/', data=bod,
        headers={'Content-Type': 'multipart/form-data; boundary=%s' % boundary})
    gd = urllib.request.urlopen(r, timeout=10).read().decode()
    st = codec.thrift.read_struct(codec.decode_body(gd))
    ntables = len(st[5]['ret']) if isinstance(st.get(5), dict) and 'ret' in st[5] else (len(st[5]) if isinstance(st.get(5), dict) else 0)
    print("GAMEDATA bytes=%d top_ids=%s tables=%s" % (len(gd), sorted(st.keys()), ntables))
    assert st[1] == {1: 0, 2: ''} and len(gd) > 1000

    # auth login (JSON)
    boundary, bod = multipart_body({'app_id': '100', 'device_cd': dev, 'udid': dev})
    r = urllib.request.Request(SERVER + '/api/accounts/v3/global/login', data=bod,
        headers={'Content-Type': 'multipart/form-data; boundary=%s' % boundary})
    aj = json.loads(urllib.request.urlopen(r, timeout=10).read())
    print("AUTH  result=%s member=%s guest=%s" % (aj['result_code'], aj['value']['member']['member_id'],
          aj['value']['is_guest_login']))
    assert aj['result_code'] == '000' and aj['value']['member']['member_id'] == 429071553

    # CDN
    cd = urllib.request.urlopen(SERVER + '/AssetBundles/Android/Android', timeout=10).read()
    print("CDN   Android bundle bytes=%d (UnityFS=%s)" % (len(cd), cd[:7] == b'UnityFS'))
    assert len(cd) > 100

    print("\nALL E2E TESTS PASSED")

if __name__ == '__main__':
    main()

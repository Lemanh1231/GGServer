"""NeonAPI / PmangPlus account endpoints (JSON), ported from the reference auth_service.go.
These run on the same server; the client reaches them after global.neonapi.com is redirected.
"""
import json, time, os

API_OK = 'API_OK'
_MEMBER_ID = 429071553
_UNKNOWN_OPT = '618de92ee950717f49afcd82d359bc92b2c34a7f'
_SERVER_LOCALE = 'KR'
_STATIC = os.path.join(os.path.dirname(__file__), '..', 'static')


def _login(form):
    now_ms = int(time.time() * 1000)
    app_id = form.get('app_id', '0')
    device_cd = form.get('device_cd', '')
    access_token = f"{_MEMBER_ID}|{app_id}|{device_cd}|{_SERVER_LOCALE}|{_UNKNOWN_OPT}|{now_ms}"
    member = {
        'crt_dt': now_ms, 'upd_dt': now_ms, 'status_cd': 'OK', 'member_id': _MEMBER_ID,
        'nickname': 'User', 'profile_img_url': None, 'feeling': None, 'adult_auth_yn': 'N',
        'adult_auth_dt': None, 'recent_login_dt': None, 'recent_app_id': _int(app_id),
        'email': None, 'anonymous_yn': 'Y', 'friend_accept_cd': None, 'reg_path': None,
        'recent_app_title': 'Guitar Girl', 'last_msg_dt': None, 'new_msg_yn': None,
        'conflict_member_id': 0, 'reg_ip': '127.0.0.1', 'reg_nation': 'US',
        'is_guest_login': True, 'provider_display_name': '', 'pushgroup': None, 'locale': None,
    }
    value = {
        'access_token': access_token, 'member': member, 'force_receipt': None,
        'conflict_member_id': None, 'is_guest_login': True, 'old_member_id': None,
        'jailbreak_yn': 'N', 'fcm_send_lang': 'EN', 'unreg_status': 'NO',
        'unreg_remain_time': None, 'callTime': 0,
    }
    return {'value': value, 'result_code': '000', 'result_msg': API_OK}


def _gcm_register():
    return {'value': {'unsubscription': [], 'subscription': [],
                      'fcmheader': 'CsYsPQf1UEU:APA91bE1dMmiUqnw5HACZ9GstHG8U_K-5sNxSgWWPbNZBOfP93v2M7PzjATrXetY_vnzRc5aFQAbS2TGpKDniifN5DDcfUlPG4MVWkhSHjUHS_X6ViwpImmU5BteBUZhjBAAAAq1Zi1q'},
            'result_code': '', 'result_msg': ''}


def _simple(value):
    return {'value': value, 'result_code': '000', 'result_msg': API_OK}


def _int(s, d=0):
    try:
        return int(s)
    except Exception:
        return d


def handle(path, form):
    """Return (body_bytes, content_type) for an /api/... auth path, or None if unmatched."""
    p = path.split('?', 1)[0]
    if p == '/api/accounts/v3/global/login':
        return _json(_login(form))
    if p.startswith('/api/eula/'):
        f = os.path.join(_STATIC, 'eula.html')
        data = open(f, 'rb').read() if os.path.exists(f) else b'<html>OK</html>'
        return data, 'text/html; charset=utf-8'
    if p == '/api/referrer/save':
        return _json(_simple('OK'))
    if p.startswith('/api/gcm/'):
        return _json(_gcm_register())
    if p == '/api/analytics' or p.endswith('/analytics'):
        return _json(_simple(True))
    if 'geoip' in p:
        return _json(_simple('US'))
    # default: generic OK for any other /api/ call so the client proceeds
    if p.startswith('/api/'):
        return _json(_simple(True))
    return None


def _json(obj):
    return json.dumps(obj).encode('utf-8'), 'application/json; charset=utf-8'

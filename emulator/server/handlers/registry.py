import json

HANDLERS = {}

def cmd(name):
    def deco(fn):
        HANDLERS[name] = fn
        return fn
    return deco

def _err(code, msg):
    return {'code': code, 'errmsg': msg}

def _payload(req):
    if isinstance(req, dict):
        d = req.get('data')
        if isinstance(d, dict):
            return d
    return {}

OK = {'code': 0, 'errmsg': ''}

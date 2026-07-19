from server.handlers.registry import HANDLERS, cmd
from . import auth, shop, reward, system, profile, music, follower, event_mode

def handle(cmd_simple, req, ctx):
    """Return (ret_data, error). Unimplemented commands -> empty success payload."""
    fn = HANDLERS.get(cmd_simple)
    if fn:
        return fn(req, None, ctx)
    return {}, {'code': 0, 'errmsg': ''}

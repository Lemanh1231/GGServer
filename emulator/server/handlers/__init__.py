"""Handler registry, with development hot reload for emulator debugging."""
import importlib
import os
import threading

from server.handlers.registry import HANDLERS, cmd
from . import auth, shop, reward, system, profile, music, follower, event_mode, ch_third

_MODULES = (auth, shop, reward, system, profile, music, follower, event_mode, ch_third)
_MODULE_MTIMES = {}
_RELOAD_LOCK = threading.RLock()


def _changed_modules():
    changed = []
    for module in _MODULES:
        path = getattr(module, '__file__', None)
        if not path:
            continue
        try:
            mtime = os.stat(path).st_mtime_ns
        except OSError:
            continue
        if _MODULE_MTIMES.get(path) != mtime:
            changed.append((module, path, mtime))
    return changed


def reload_if_changed():
    """Reload handlers after a source edit without interrupting the server.

    This is intentionally enabled for the local emulator by default.  Set
    ``GG_HOT_RELOAD=0`` only when a fixed production-like process is desired.
    """
    if os.environ.get('GG_HOT_RELOAD', '1') != '1':
        return
    changed = _changed_modules()
    if not changed:
        return
    with _RELOAD_LOCK:
        changed = _changed_modules()
        if not changed:
            return
        # Decorators repopulate this mapping as each module reloads.  Clearing
        # first also removes handlers intentionally deleted in a later edit.
        HANDLERS.clear()
        # Reload every handler after any edit so the registry remains complete;
        # reloading only the edited module after clearing would lose commands
        # registered by the untouched modules.
        for module in _MODULES:
            importlib.reload(module)
        for module in _MODULES:
            path = getattr(module, '__file__', None)
            if path:
                try:
                    _MODULE_MTIMES[path] = os.stat(path).st_mtime_ns
                except OSError:
                    pass

def handle(cmd_simple, req, ctx):
    """Return (ret_data, error). Unimplemented commands -> empty success payload."""
    reload_if_changed()
    fn = HANDLERS.get(cmd_simple)
    if fn:
        return fn(req, None, ctx)
    return {}, {'code': 0, 'errmsg': ''}

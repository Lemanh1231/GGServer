#!/usr/bin/env python3
# ==============================================================================
#  GUITAR GIRL EMULATOR SERVER - LIVE CONTROL CENTER & TUI DASHBOARD
#  Bảng điều khiển 2 cột (Dual-Column Split TUI) đồng bộ chiều cao & độ rộng:
#    • Cột trái : Trạng thái Server, Tài nguyên Hệ thống, Danh sách Người chơi
#                 & Sự kiện trực tiếp (SQLite), Phím điều khiển nhanh
#    • Cột phải : Bảng nhật ký Telemetry thời gian thực (tự động ánh xạ IP -> UID,
#                 gộp dòng POST 200 trùng lặp, phân loại màu theo nhóm lệnh RPC)
# ==============================================================================

import os
import sys
import time
import re
import json
import sqlite3
import unicodedata
import shutil
import select
import termios
import tty
import subprocess
import urllib.request
from datetime import datetime

# Thư mục dự án
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
EMULATOR_DIR = os.path.join(ROOT_DIR, "emulator")
RUN_SH = os.path.join(ROOT_DIR, "run.sh")
DB_PATH = os.path.join(EMULATOR_DIR, "data", "database.db")
EVENT_CFG_PATH = os.path.join(EMULATOR_DIR, "event_config.json")


def load_env():
    env_vars = {}
    for p in [os.path.join(ROOT_DIR, ".env"), os.path.join(EMULATOR_DIR, ".env")]:
        if os.path.isfile(p):
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_vars[k.strip()] = v.strip().strip("'\"")
    return env_vars


ENV = load_env()
PORT = os.environ.get("PORT") or ENV.get("PORT", "8080")
LOG_FILE = os.environ.get("GG_LOG") or ENV.get("GG_LOG", "/tmp/gg_server.log")
GG_PUBLIC_BASE = os.environ.get("GG_PUBLIC_BASE") or ENV.get("GG_PUBLIC_BASE", "https://kotori.click")
GG_ADMIN_PASSWORD = os.environ.get("GG_ADMIN_PASSWORD") or ENV.get("GG_ADMIN_PASSWORD", "admin123")

# Bảng mã màu ANSI 256
C_BORDER  = "\033[38;5;39m"      # Bright Azure Border
C_TITLE   = "\033[1;38;5;231m"   # Crisp Bold White
C_SUB     = "\033[38;5;153m"     # Soft Sky Blue
C_LABEL   = "\033[38;5;222m"     # Warm Soft Gold
C_VAL     = "\033[1;38;5;255m"   # Bold White
C_DIM     = "\033[38;5;243m"     # Muted Slate Gray
C_TRACK   = "\033[38;5;239m"     # Progress Bar Empty Track
C_HEADER  = "\033[1;38;5;117m"   # Table Column Header

C_GREEN   = "\033[1;38;5;48m"    # Emerald Green
C_RED     = "\033[1;38;5;203m"   # Coral Red
C_YELLOW  = "\033[1;38;5;220m"   # Golden Amber
C_CYAN    = "\033[1;38;5;51m"    # Neon Cyan
C_MAGENTA = "\033[1;38;5;213m"   # Rose Magenta
C_BLUE    = "\033[1;38;5;75m"    # Sky Blue
C_ORANGE  = "\033[1;38;5;214m"   # Warm Orange
C_RESET   = "\033[0m"

# Badges phân loại nhóm lệnh (cố định đúng 7 ký tự hiển thị)
BADGE_AUTH = "\033[1;38;5;51m[LOGIN]\033[0m"
BADGE_SAVE = "\033[1;38;5;48m[SAVE ]\033[0m"
BADGE_FOLL = "\033[1;38;5;213m[QUEST]\033[0m"
BADGE_REWD = "\033[1;38;5;220m[REWRD]\033[0m"
BADGE_SHOP = "\033[1;38;5;214m[SHOP ]\033[0m"
BADGE_DATA = "\033[1;38;5;75m[DATA ]\033[0m"
BADGE_RPC  = "\033[1;38;5;177m[RPC  ]\033[0m"
BADGE_HTTP = "\033[1;38;5;120m[HTTP ]\033[0m"
BADGE_WARN = "\033[1;38;5;220m[WARN!]\033[0m"
BADGE_ERR  = "\033[1;97;41m[ERROR]\033[0m"

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def char_width(ch):
    if unicodedata.category(ch) in ("Mn", "Me", "Cf"):
        return 0
    ea = unicodedata.east_asian_width(ch)
    if ea in ("W", "F"):
        return 2
    return 1


def visible_width(s):
    clean = ANSI_RE.sub("", s)
    return sum(char_width(ch) for ch in clean)


def pad_visible(s, target_w, align="left"):
    vw = visible_width(s)
    if vw > target_w:
        return truncate_visible(s, target_w)
    diff = target_w - vw
    if align == "right":
        return (" " * diff) + s
    if align == "center":
        lpad = diff // 2
        rpad = diff - lpad
        return (" " * lpad) + s + (" " * rpad)
    return s + (" " * diff)


def truncate_visible(s, max_w):
    if max_w <= 0:
        return ""
    if visible_width(s) <= max_w:
        return s
    # Giữ nguyên mã màu ANSI khi cắt chuỗi
    w = 0
    out = []
    i = 0
    n = len(s)
    while i < n:
        if s[i] == "\x1b":
            m = ANSI_RE.match(s, i)
            if m:
                out.append(m.group(0))
                i = m.end()
                continue
        ch = s[i]
        cw = char_width(ch)
        if w + cw > max_w - 1:
            out.append("\033[0m…")
            break
        out.append(ch)
        w += cw
        i += 1
    out.append(C_RESET)
    return "".join(out)


def draw_bar(pct, width=16):
    pct = max(0.0, min(100.0, float(pct)))
    filled = int(round(pct * width / 100.0))
    empty = width - filled
    if pct >= 85.0:
        bar_color = C_RED
    elif pct >= 65.0:
        bar_color = C_YELLOW
    else:
        bar_color = C_GREEN
    return f"{C_DIM}[{C_RESET}{bar_color}{'█' * filled}{C_TRACK}{'━' * empty}{C_DIM}]{C_RESET}"


# ==============================================================================
#  THU THẬP THÔNG SỐ HỆ THỐNG, DATABASE & SỰ KIỆN (CÓ CACHE NHẸ)
# ==============================================================================
prev_cpu_idle = 0
prev_cpu_total = 0


def get_cpu_usage():
    global prev_cpu_idle, prev_cpu_total
    try:
        with open("/proc/stat", "r") as f:
            line = f.readline()
        parts = [float(x) for x in line.split()[1:8]]
        idle = parts[3] + parts[4]
        total = sum(parts)
        if prev_cpu_total == 0:
            prev_cpu_idle = idle
            prev_cpu_total = total
            return 0.0
        diff_idle = idle - prev_cpu_idle
        diff_total = total - prev_cpu_total
        prev_cpu_idle = idle
        prev_cpu_total = total
        if diff_total > 0:
            return max(0.0, min(100.0, 100.0 * (1.0 - diff_idle / diff_total)))
    except Exception:
        pass
    return 0.0


def get_sys_memory():
    try:
        mem = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    mem[parts[0].strip()] = int(parts[1].strip().split()[0])
        total_mb = mem.get("MemTotal", 0) / 1024.0
        avail_mb = mem.get("MemAvailable", 0) / 1024.0
        used_mb = max(0.0, total_mb - avail_mb)
        pct = (used_mb / total_mb * 100.0) if total_mb > 0 else 0.0
        return used_mb / 1024.0, total_mb / 1024.0, pct
    except Exception:
        return 0.0, 0.0, 0.0


def get_sys_disk():
    try:
        st = os.statvfs("/")
        total_gb = (st.f_blocks * st.f_frsize) / (1024.0**3)
        free_gb = (st.f_bavail * st.f_frsize) / (1024.0**3)
        used_gb = total_gb - free_gb
        pct = (used_gb / total_gb * 100.0) if total_gb > 0 else 0.0
        return used_gb, total_gb, pct
    except Exception:
        return 0.0, 0.0, 0.0


def get_sys_uptime():
    try:
        with open("/proc/uptime", "r") as f:
            up_secs = float(f.read().split()[0])
        days = int(up_secs // 86400)
        hours = int((up_secs % 86400) // 3600)
        mins = int((up_secs % 3600) // 60)
        return f"{days}d {hours:02d}h {mins:02d}m"
    except Exception:
        return "N/A"


def get_sys_load():
    try:
        l1, l5, l15 = os.getloadavg()
        return f"{l1:.2f}, {l5:.2f}, {l15:.2f}"
    except Exception:
        return "N/A"


def get_server_pid():
    try:
        out = subprocess.check_output(f"ss -ltnp 2>/dev/null | grep ':{PORT} '", shell=True).decode()
        m = re.search(r"pid=(\d+)", out)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    try:
        out = subprocess.check_output("pgrep -f 'run.py --host' 2>/dev/null", shell=True).decode().strip()
        lines = out.split()
        if lines:
            return int(lines[0])
    except Exception:
        pass
    return None


def get_proc_stats(pid):
    if not pid:
        return None
    try:
        out = subprocess.check_output(
            f"ps -p {pid} -o %cpu,%mem,rss,etime --no-headers 2>/dev/null", shell=True
        ).decode().strip()
        if out:
            p_cpu, p_mem, rss, etime = out.split()
            rss_mb = float(rss) / 1024.0
            return {
                "cpu": float(p_cpu),
                "mem_pct": float(p_mem),
                "rss_mb": rss_mb,
                "etime": etime,
            }
    except Exception:
        pass
    return None


def check_health():
    t0 = time.time()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}/health", headers={"User-Agent": "GG-Monitor"})
        with urllib.request.urlopen(req, timeout=0.4) as resp:
            data = resp.read().decode("utf-8", errors="ignore").strip()
            latency_ms = (time.time() - t0) * 1000.0
            if "GG emulator OK" in data:
                return True, f"200 OK ({latency_ms:.1f}ms)"
            return True, "200 OK"
    except Exception:
        return False, "FAIL"


_db_cache_ts = 0.0
_db_cache_data = {"users": [], "ip_map": {}, "events": {}}


def get_game_snapshot():
    """Đọc nhanh danh sách người chơi & cấu hình sự kiện (cache 2.0s)."""
    global _db_cache_ts, _db_cache_data
    now = time.time()
    if now - _db_cache_ts < 2.0:
        return _db_cache_data

    users = []
    ip_map = {}
    if os.path.isfile(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH, timeout=2.0)
            conn.execute("PRAGMA query_only=ON")
            conn.execute("PRAGMA busy_timeout=2000")
            rows = conn.execute(
                "SELECT u_id, u_seq, ip, is_banned, u_cp, u_candy, user_contents_json FROM user_data ORDER BY u_seq"
            ).fetchall()
            for r in rows:
                u_id, u_seq, ip, is_banned, u_cp, u_candy, raw_json = r
                ip = (ip or "").strip()
                if ip:
                    ip_map[ip] = u_id
                gg_lvl = 1
                last_save = ""
                last_save_ts = 0
                fol_cnt = 1
                try:
                    d = json.loads(raw_json or "{}")
                    last_save_ts = int(d.get("last_save_time", 0) or 0)
                    ud = d.get("userdata", {})
                    last_save = str(ud.get("u_save_date") or ud.get("u_last_login") or "")
                    for c in d.get("characters", []):
                        if int(c.get("i_id", 0) or 0) == 1:
                            gg_lvl = int(c.get("i_Level", 1) or 1)
                            break
                except Exception:
                    pass
                try:
                    fc = conn.execute(
                        "SELECT COUNT(*) FROM user_inventory WHERE uuid=(SELECT uuid FROM user_data WHERE u_id=?) AND item_type='follower'",
                        (u_id,),
                    ).fetchone()
                    if fc and fc[0]:
                        fol_cnt = int(fc[0])
                except Exception:
                    pass

                # Rút gọn ngày giờ: 2026-11-06 03:29:41 -> 06/11 03:29
                short_save = "—"
                if len(last_save) >= 16 and "-" in last_save:
                    try:
                        dt_part, tm_part = last_save.split(" ")[:2]
                        y, m, day = dt_part.split("-")
                        short_save = f"{day}/{m} {tm_part[:5]}"
                    except Exception:
                        short_save = last_save[:11]

                users.append({
                    "u_id": u_id or f"guest_{u_seq}",
                    "u_seq": u_seq,
                    "ip": ip,
                    "is_banned": bool(is_banned),
                    "u_cp": int(u_cp or 0),
                    "u_candy": int(float(u_candy or 0)),
                    "gg_lvl": gg_lvl,
                    "fol_cnt": fol_cnt,
                    "short_save": short_save,
                    "last_save_ts": last_save_ts,
                })
            conn.close()
        except Exception:
            pass

    # Sắp xếp người chơi mới hoạt động nhất lên đầu
    users.sort(key=lambda u: (u["last_save_ts"], u["u_seq"]), reverse=True)

    events_info = {"sp_season": 13, "sp_on": True, "meow_on": True, "att_count": 2, "weather": "Tuyết rơi"}
    if os.path.isfile(EVENT_CFG_PATH):
        try:
            with open(EVENT_CFG_PATH, "r", encoding="utf-8") as f:
                ecfg = json.load(f)
            sp = ecfg.get("star_pass", {})
            events_info["sp_on"] = bool(sp.get("enabled", True))
            events_info["sp_season"] = int(sp.get("active_season", 13) or 13)
            events_info["meow_on"] = bool(ecfg.get("meowfest", {}).get("enabled", True))
            att = ecfg.get("attendance_events", {})
            events_info["att_count"] = sum(1 for v in att.values() if isinstance(v, dict) and v.get("enabled"))
            wf = ecfg.get("weather_festival", {})
            if wf.get("snow_enabled"):
                events_info["weather"] = "Tuyết rơi"
            elif wf.get("cherry_blossom_enabled"):
                events_info["weather"] = "Hoa đào"
            else:
                events_info["weather"] = "Mặc định"
        except Exception:
            pass

    _db_cache_data = {"users": users, "ip_map": ip_map, "events": events_info}
    _db_cache_ts = now
    return _db_cache_data


# ==============================================================================
#  BỘ PHÂN TÍCH & ĐỊNH DẠNG BẢNG LOG THỜI GIAN THỰC (TELEMETRY TABLE)
# ==============================================================================
def classify_rpc(action):
    a = action.lower()
    if a in ("userlogin", "userjoin", "facebookuserjoin", "request", "getservertime", "getupdatetime", "defaultsettinglist"):
        return BADGE_AUTH, C_CYAN
    if a in ("usersave", "userload", "lastsavetime"):
        return BADGE_SAVE, C_GREEN
    if "follower" in a or "messenger" in a:
        return BADGE_FOLL, C_MAGENTA
    if "reward" in a or "attendance" in a or "post" in a or "achievement" in a or "event" in a or "samseck" in a:
        return BADGE_REWD, C_YELLOW
    if a.startswith("buy") or "shop" in a or "store" in a:
        return BADGE_SHOP, C_ORANGE
    if "gamedata" in a or "chthird" in a or "ch_third" in a:
        return BADGE_DATA, C_BLUE
    return BADGE_RPC, C_VAL


def calc_log_cols(content_w):
    # Định dạng 6 cột: TIME | BADGE(7) | ACTOR | DOMAIN | ACTION/PATH | RESULT
    # Tổng khoảng trắng giữa 6 cột = 5; cộng BADGE(7) = 12 ký tự cố định
    if content_w >= 100:
        col_time, col_actor, col_dom, col_res = 14, 29, 14, 14
    elif content_w >= 86:
        col_time, col_actor, col_dom, col_res = 14, 22, 13, 13
    elif content_w >= 72:
        col_time, col_actor, col_dom, col_res = 14, 15, 13, 11
    else:
        col_time, col_actor, col_dom, col_res = 8, 13, 13, 8
    col_act = max(10, content_w - col_time - col_actor - col_dom - col_res - 12)
    return col_time, col_actor, col_dom, col_act, col_res


def format_domain(dom, col_dom):
    d = (dom or "").strip().lower()
    if not d or d == "—":
        return pad_visible(f"{C_DIM}—{C_RESET}", col_dom)
    if d in ("local", "127.0.0.1", "localhost", "::1"):
        return pad_visible(f"{C_DIM}local{C_RESET}", col_dom)
    if d == "kotori.click":
        color = C_CYAN
    elif d == "kotorin.click":
        color = C_GREEN
    elif d == "kotorin.dev":
        color = C_MAGENTA
    elif d == "kotorin.me":
        color = C_YELLOW
    else:
        color = C_BLUE
    return pad_visible(f"{color}{d}{C_RESET}", col_dom)


def format_actor(ip, ip_map, col_actor, fallback_label=None):
    ip_clean = (ip or "").strip()
    if not ip_clean or ip_clean in ("127.0.0.1", "localhost", "::1"):
        if fallback_label:
            return pad_visible(f"{C_DIM}{fallback_label}{C_RESET}", col_actor), None
        if not ip_clean:
            return pad_visible(f"{C_DIM}—{C_RESET}", col_actor), None
    uid = ip_map.get(ip_clean)
    if uid:
        disp = f"{C_VAL}{uid}{C_RESET} {C_DIM}({ip_clean}){C_RESET}" if col_actor >= 24 else f"{C_VAL}{uid}{C_RESET}"
        return pad_visible(disp, col_actor), uid
    return pad_visible(f"{C_SUB}{ip_clean}{C_RESET}", col_actor), ip_clean


def parse_logs(max_lines, content_w, ip_map, show_http_200=False):
    cols = calc_log_cols(content_w)
    col_time, col_actor, col_dom, col_act, col_res = cols

    if not os.path.isfile(LOG_FILE):
        return [f"{C_DIM}(Chưa có tệp nhật ký — Nhấn [1] để khởi động server){C_RESET}"], {"rpc": 0, "err": 0, "last_actor": "—", "cols": cols}

    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            raw_lines = f.readlines()[-400:]
    except Exception:
        return [f"{C_DIM}(Không thể đọc tệp nhật ký){C_RESET}"], {"rpc": 0, "err": 0, "last_actor": "—", "cols": cols}

    entries = []
    rpc_count = 0
    err_count = 0
    last_actor = "—"

    for raw in raw_lines:
        line = raw.strip()
        if not line:
            continue
        if any(ign in line for ign in [
            "/health", "GET / HTTP", "HEAD / HTTP", "GET /admin", "POST /admin",
            "CONNECT", "/SDK/", "favicon.ico", "Ctrl-C to stop.",
        ]):
            continue
        if line.startswith("listening http"):
            addr = line.split("listening ", 1)[1].strip()
            entries.append(truncate_visible(
                f"{pad_visible('', col_time)} \033[1;38;5;48m[START]\033[0m {C_GREEN}Máy chủ đã khởi động lắng nghe tại {addr}{C_RESET}",
                content_w,
            ))
            continue

        m_time = re.match(r"^\[(\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}|\d{2}:\d{2}:\d{2})\]\s*(.*)$", line)
        ts_raw = ""
        rest = line
        if m_time:
            ts_raw = m_time.group(1)
            if col_time == 8 and len(ts_raw) >= 8:
                ts_raw = ts_raw[-8:]
            elif len(ts_raw) == 17 and ts_raw[2] == "/" and ts_raw[5] == "/":
                ts_raw = ts_raw[:5] + ts_raw[8:]
            rest = m_time.group(2)

        ts_col = pad_visible(f"{C_DIM}{ts_raw}{C_RESET}", col_time)

        # Tách tiền tố [IP @ domain] hoặc [IP] (tương thích cả log mới lẫn log cũ)
        m_ctx = re.match(r"^\[([0-9a-fA-F.:]+)(?:\s*@\s*([^\]]+))?\]\s+(.*)$", rest)
        if m_ctx:
            ip_val = m_ctx.group(1).strip()
            dom_val = (m_ctx.group(2) or "").strip()
            body_rest = m_ctx.group(3).strip()
        else:
            ip_val, dom_val, body_rest = "", "", rest

        # 1. Phát hiện Lỗi / Cảnh báo / Banned
        low = body_rest.lower()
        if "banned user blocked" in low or any(k in low for k in ["traceback", "exception", "error:", "errno 104", "failed"]):
            err_count += 1
            if "connectionreset" in low or "errno 104" in low:
                badge = BADGE_WARN
                msg = f"{C_YELLOW}ConnectionReset (Client đóng kết nối sớm){C_RESET}"
            else:
                badge = BADGE_ERR
                msg = f"{C_RED}{body_rest}{C_RESET}"
            if ip_val or dom_val:
                actor_col, _ = format_actor(ip_val, ip_map, col_actor)
                dom_col = format_domain(dom_val, col_dom)
                entries.append(truncate_visible(f"{ts_col} {badge} {actor_col} {dom_col} {msg}", content_w))
            else:
                entries.append(truncate_visible(f"{ts_col} {badge} {msg}", content_w))
            continue

        # 2. Phát hiện Game RPC: action -> dto (136 B) hoặc -> dynamic (...)
        if ip_val:
            m_rpc = re.match(r"^([a-zA-Z0-9_]+)\s+->\s+(.+)$", body_rest)
        else:
            m_rpc = None
        if m_rpc:
            action, rhs = m_rpc.groups()
            rpc_count += 1
            actor_col, actor_lbl = format_actor(ip_val, ip_map, col_actor)
            dom_col = format_domain(dom_val, col_dom)
            if actor_lbl:
                last_actor = f"{actor_lbl} @ {dom_val}" if dom_val else actor_lbl

            badge, act_color = classify_rpc(action)
            act_col = pad_visible(f"{act_color}{action}{C_RESET}", col_act)

            m_sz = re.search(r"\((\d+\s*B)\)", rhs)
            sz_txt = m_sz.group(1) if m_sz else "OK"
            if col_res < 11:
                res_str = f"{C_GREEN}✓ DYN{C_RESET}" if "dynamic" in rhs else f"{C_GREEN}✓ 200{C_RESET}"
            elif "dynamic" in rhs:
                res_str = f"{C_GREEN}✓ DYN{C_RESET} {C_DIM}({sz_txt}){C_RESET}"
            else:
                res_str = f"{C_GREEN}✓ 200{C_RESET} {C_DIM}({sz_txt}){C_RESET}"
            res_col = pad_visible(res_str, col_res)

            entries.append(truncate_visible(f"{ts_col} {badge} {actor_col} {dom_col} {act_col} {res_col}", content_w))
            continue

        # 3. Phát hiện AUTH handshake
        m_auth = re.match(r"^AUTH(?:-GET)?\s+(\S+)\s*(.*)$", body_rest)
        if m_auth:
            auth_path, auth_extra = m_auth.groups()
            rpc_count += 1
            actor_col, actor_lbl = format_actor(ip_val, ip_map, col_actor, fallback_label="Auth Client")
            dom_col = format_domain(dom_val, col_dom)
            if actor_lbl:
                last_actor = f"{actor_lbl} @ {dom_val}" if dom_val else actor_lbl
            act_col = pad_visible(f"{C_CYAN}AUTH {auth_path}{C_RESET}", col_act)
            res_str = f"{C_RED}✗ BANNED{C_RESET}" if "banned=True" in auth_extra else f"{C_GREEN}✓ AUTH{C_RESET}"
            res_col = pad_visible(res_str, col_res)
            entries.append(truncate_visible(f"{ts_col} {BADGE_AUTH} {actor_col} {dom_col} {act_col} {res_col}", content_w))
            continue

        # 4. Phát hiện tải APK
        if "DOWNLOAD" in body_rest and "APK" in body_rest:
            apk_name = os.path.basename(body_rest.split(":")[-1].strip())
            actor_col, actor_lbl = format_actor(ip_val, ip_map, col_actor, fallback_label="APK Client")
            dom_col = format_domain(dom_val, col_dom)
            if actor_lbl and dom_val and last_actor == "—":
                last_actor = f"{actor_lbl} @ {dom_val}"
            act_col = pad_visible(f"{C_YELLOW}⬇ {apk_name}{C_RESET}", col_act)
            res_col = pad_visible(f"{C_GREEN}✓ APK{C_RESET}", col_res)
            entries.append(truncate_visible(f"{ts_col} {BADGE_DATA} {actor_col} {dom_col} {act_col} {res_col}", content_w))
            continue

        # 5. Phát hiện CDN Asset
        if body_rest.startswith("CDN ") or "CDN " in body_rest:
            asset_short = os.path.basename(body_rest.split("CDN ")[-1].strip())
            actor_col, _ = format_actor(ip_val, ip_map, col_actor, fallback_label="AssetBundle")
            dom_col = format_domain(dom_val, col_dom)
            act_col = pad_visible(f"{C_ORANGE}{asset_short}{C_RESET}", col_act)
            res_col = pad_visible(f"{C_GREEN}✓ CDN{C_RESET}", col_res)
            entries.append(truncate_visible(f"{ts_col} {BADGE_DATA} {actor_col} {dom_col} {act_col} {res_col}", content_w))
            continue

        # 6. Phát hiện HTTP Request
        m_http = re.search(r'\"([A-Z]+)\s+([^\"\s]+)(?:\s+HTTP/[0-9.]+)?\"?\s+(\d{3})\s*(-|\d*)', body_rest)
        if m_http:
            method, path, status, size = m_http.groups()
            # Ẩn dòng HTTP 200 trùng lặp của Game RPC / Auth / CDN / APK trừ khi bật show_http_200
            if status.startswith("2") and not show_http_200:
                if method == "POST" and any(seg in path for seg in (
                    "/main/", "/user/", "/rank", "/tour/", "/music/", "/store/",
                    "/eventMode/", "/post/", "/multi/", "/ch_third/",
                    "/api/", "/accounts/", "/referrer/", "/gcm/", "/app/",
                )):
                    continue
                if method == "GET" and (path.startswith("/AssetBundles/") or path in ("/download/apk", "/apk") or path.endswith(".apk")):
                    continue

            if status.startswith("2"):
                badge = BADGE_HTTP
                res_str = f"{C_GREEN}✓ {status}{C_RESET}" if col_res < 11 else f"{C_GREEN}✓ {status} OK{C_RESET}"
            elif status.startswith("4"):
                err_count += 1
                badge = BADGE_WARN
                res_str = f"{C_YELLOW}! {status}{C_RESET}" if col_res < 11 else f"{C_YELLOW}! {status} WARN{C_RESET}"
            else:
                err_count += 1
                badge = BADGE_ERR
                res_str = f"{C_RED}✗ {status}{C_RESET}" if col_res < 11 else f"{C_RED}✗ {status} ERR{C_RESET}"

            actor_col, actor_lbl = format_actor(ip_val, ip_map, col_actor, fallback_label=f"HTTP {method}")
            dom_col = format_domain(dom_val, col_dom)
            if actor_lbl and dom_val and last_actor == "—":
                last_actor = f"{actor_lbl} @ {dom_val}"
            act_lbl = f"{method} {path}" if ip_val else path
            act_col = pad_visible(f"{C_SUB}{act_lbl}{C_RESET}", col_act)
            res_col = pad_visible(res_str, col_res)
            entries.append(truncate_visible(f"{ts_col} {badge} {actor_col} {dom_col} {act_col} {res_col}", content_w))
            continue

        entries.append(truncate_visible(f"{ts_col} {C_DIM}• {rest}{C_RESET}", content_w))

    if not entries:
        entries = [f"{C_DIM}(Đang chờ kết nối mới từ thiết bị người chơi...){C_RESET}"]

    stats = {"rpc": rpc_count, "err": err_count, "last_actor": last_actor, "cols": cols}
    return entries[-max_lines:], stats


# ==============================================================================
#  HÀM VẼ KHUNG BOX CHUẨN ĐỘ RỘNG KÝ TỰ (100% RAZOR-STRAIGHT BORDERS)
# ==============================================================================
def make_box_line(content, width, border_color=C_BORDER):
    inner_w = width - 4
    padded = pad_visible(content, inner_w)
    return f"{border_color}│{C_RESET} {padded} {border_color}│{C_RESET}"


def make_box_top(width, title="", border_color=C_BORDER):
    if not title:
        return f"{border_color}╭{'─' * (width - 2)}╮{C_RESET}"
    t_vw = visible_width(title)
    if t_vw + 6 >= width:
        return f"{border_color}╭{'─' * (width - 2)}╮{C_RESET}"
    return f"{border_color}╭─ {title} {border_color}{'─' * (width - t_vw - 5)}╮{C_RESET}"


def make_box_bot(width, title="", border_color=C_BORDER):
    if not title:
        return f"{border_color}╰{'─' * (width - 2)}╯{C_RESET}"
    t_vw = visible_width(title)
    if t_vw + 6 >= width:
        return f"{border_color}╰{'─' * (width - 2)}╯{C_RESET}"
    return f"{border_color}╰─ {title} {border_color}{'─' * (width - t_vw - 5)}╯{C_RESET}"


def make_box_sep(width, title="", border_color=C_BORDER):
    if not title:
        return f"{border_color}├{'─' * (width - 2)}┤{C_RESET}"
    t_vw = visible_width(title)
    if t_vw + 6 >= width:
        return f"{border_color}├{'─' * (width - 2)}┤{C_RESET}"
    return f"{border_color}├─ {title} {border_color}{'─' * (width - t_vw - 5)}┤{C_RESET}"


# ==============================================================================
#  RENDER GIAO DIỆN CHÍNH (DUAL-COLUMN SYMMETRICAL TUI)
# ==============================================================================
def render_dashboard(flash_msg=None, show_http_200=False, show_pass=False):
    term_w, term_h = shutil.get_terminal_size((120, 34))
    is_split = term_w >= 104

    pid = get_server_pid()
    proc_info = get_proc_stats(pid)
    is_running = pid is not None

    health_ok, health_str = check_health() if is_running else (False, "OFFLINE")
    health_badge = f"{C_GREEN}● {health_str}{C_RESET}" if health_ok else f"{C_RED}● {health_str}{C_RESET}"

    cpu_pct = get_cpu_usage()
    ram_used, ram_total, ram_pct = get_sys_memory()
    disk_used, disk_total, disk_pct = get_sys_disk()
    uptime_str = get_sys_uptime()
    load_str = get_sys_load()
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    snap = get_game_snapshot()
    users = snap["users"]
    ip_map = snap["ip_map"]
    ev = snap["events"]

    pass_display = f"{C_YELLOW}{GG_ADMIN_PASSWORD}{C_RESET}" if show_pass else f"{C_DIM}{'•' * min(10, len(GG_ADMIN_PASSWORD))} (Nhấn [p] hiện){C_RESET}"

    # ================= CHẾ ĐỘ 2 CỘT CÂN ĐỐI (SIDE-BY-SIDE) =================
    if is_split:
        LEFT_W = 54
        RIGHT_W = max(56, term_w - LEFT_W - 2)
        target_rows = max(31, term_h - 2)

        # ---- 1. CỘT TRÁI: TRẠNG THÁI + TÀI NGUYÊN + NGƯỜI CHƠI + PHÍM NÓNG ----
        left_top = []
        left_top.append(make_box_top(LEFT_W, f"{C_TITLE}◆ GUITAR GIRL SERVER • CONTROL{C_RESET}"))
        left_top.append(make_box_line(f"{C_SUB}Kotori Emulator Node{C_RESET} {C_DIM}│ Linux x86_64{C_RESET}", LEFT_W))
        left_top.append(make_box_line(f"{C_DIM}Thời gian:{C_RESET} {C_VAL}{now_str}{C_RESET} {C_DIM}│ Up:{C_RESET} {C_VAL}{uptime_str}{C_RESET}", LEFT_W))

        # Section: Thông tin Server
        left_top.append(make_box_sep(LEFT_W, f"{C_CYAN}▸ THÔNG TIN MÁY CHỦ{C_RESET}"))
        if is_running:
            up_proc = proc_info["etime"] if proc_info else "—"
            status_txt = f"{C_GREEN}● RUNNING{C_RESET} {C_DIM}(PID: {C_VAL}{pid}{C_DIM}){C_RESET}"
            proc_txt = f"{C_VAL}{proc_info['cpu']:.1f}%{C_RESET} CPU {C_DIM}│{C_RESET} {C_VAL}{proc_info['rss_mb']:.1f}M{C_RESET} RAM {C_DIM}│ Up {C_VAL}{up_proc}{C_RESET}" if proc_info else f"PID {pid}"
        else:
            status_txt = f"{C_RED}● STOPPED{C_RESET} {C_DIM}(Cổng {PORT} đang đóng){C_RESET}"
            proc_txt = f"{C_DIM}Không hoạt động{C_RESET}"

        left_top.append(make_box_line(f"{C_LABEL}• Trạng thái :{C_RESET} {status_txt}", LEFT_W))
        left_top.append(make_box_line(f"{C_LABEL}• Cổng & API :{C_RESET} {C_VAL}127.0.0.1:{PORT}{C_RESET} {C_DIM}│{C_RESET} {health_badge}", LEFT_W))
        left_top.append(make_box_line(f"{C_LABEL}• Public URL :{C_RESET} {C_CYAN}{GG_PUBLIC_BASE}{C_RESET} {C_DIM}(+3 tên miền){C_RESET}", LEFT_W))
        left_top.append(make_box_line(f"{C_LABEL}• Web Admin  :{C_RESET} {C_MAGENTA}{GG_PUBLIC_BASE}/admin{C_RESET}", LEFT_W))
        left_top.append(make_box_line(f"{C_LABEL}• Admin Pass :{C_RESET} {pass_display}", LEFT_W))
        left_top.append(make_box_line(f"{C_LABEL}• Tiến trình :{C_RESET} {proc_txt}", LEFT_W))

        # Section: Tài nguyên hệ thống
        left_top.append(make_box_sep(LEFT_W, f"{C_CYAN}▸ TÀI NGUYÊN HỆ THỐNG{C_RESET}"))
        cpu_bar = draw_bar(cpu_pct, 12)
        ram_bar = draw_bar(ram_pct, 12)
        disk_bar = draw_bar(disk_pct, 12)
        load_short = load_str.split(",")[0] if "," in load_str else load_str

        left_top.append(make_box_line(f"{C_LABEL}• CPU Load   :{C_RESET} {cpu_bar} {C_VAL}{cpu_pct:5.1f}%{C_RESET} {C_DIM}(Load {load_short}){C_RESET}", LEFT_W))
        left_top.append(make_box_line(f"{C_LABEL}• Bộ nhớ RAM :{C_RESET} {ram_bar} {C_VAL}{ram_pct:5.1f}%{C_RESET} {C_DIM}({ram_used:.1f}/{ram_total:.1f}G){C_RESET}", LEFT_W))
        left_top.append(make_box_line(f"{C_LABEL}• Ổ đĩa (/)  :{C_RESET} {disk_bar} {C_VAL}{disk_pct:5.1f}%{C_RESET} {C_DIM}({disk_used:.1f}/{disk_total:.1f}G){C_RESET}", LEFT_W))

        # Section: Người chơi & Sự kiện
        sp_badge = f"{C_GREEN}Mùa {ev['sp_season']}{C_RESET}" if ev["sp_on"] else f"{C_RED}TẮT{C_RESET}"
        mw_badge = f"{C_GREEN}BẬT{C_RESET}" if ev["meow_on"] else f"{C_RED}TẮT{C_RESET}"
        left_top.append(make_box_sep(LEFT_W, f"{C_CYAN}▸ NGƯỜI CHƠI ({len(users)}) & SỰ KIỆN LIVE{C_RESET}"))
        left_top.append(make_box_line(
            f"{C_DIM}StarPass:{C_RESET} {sp_badge} {C_DIM}│ Meowfest:{C_RESET} {mw_badge} {C_DIM}│ Mùa:{C_RESET} {C_VAL}{ev['weather']}{C_RESET}",
            LEFT_W,
        ))
        left_top.append(make_box_line(
            f"{C_HEADER}{'TÀI KHOẢN':<14} {'LV.GG':>6} {'SOCOLA':>9}   {'HOẠT ĐỘNG CUỐI':<14}{C_RESET}",
            LEFT_W,
        ))

        # Phần đáy cố định của cột trái (Phím điều khiển: 5 dòng)
        left_bot = []
        left_bot.append(make_box_sep(LEFT_W, f"{C_YELLOW}▸ PHÍM ĐIỀU KHIỂN NHANH{C_RESET}"))
        k1 = pad_visible(f"{C_GREEN}[1]{C_RESET} Start", 16)
        k2 = pad_visible(f"{C_RED}[2]{C_RESET} Stop", 16)
        k3 = pad_visible(f"{C_CYAN}[3]{C_RESET} Restart", 16)
        k4 = pad_visible(f"{C_YELLOW}[4]{C_RESET} Xem Log", 16)
        k5 = pad_visible(f"{C_MAGENTA}[5]{C_RESET} Reset DB", 16)
        k6 = pad_visible(f"{C_BLUE}[6]{C_RESET} Chạy Test", 16)
        filter_lbl = "Hiện HTTP" if not show_http_200 else "Gộp RPC"
        kf = pad_visible(f"{C_ORANGE}[f]{C_RESET} {filter_lbl}", 16)
        kc = pad_visible(f"{C_YELLOW}[c]{C_RESET} Xoá Log", 16)
        kq = pad_visible(f"{C_VAL}[q]{C_RESET} Thoát TUI", 16)
        left_bot.append(make_box_line(f"{k1}{k2}{k3}", LEFT_W))
        left_bot.append(make_box_line(f"{k4}{k5}{k6}", LEFT_W))
        left_bot.append(make_box_line(f"{kf}{kc}{kq}", LEFT_W))
        left_bot.append(make_box_bot(LEFT_W, f"{C_DIM}[p] Ẩn/Hiện Pass{C_RESET}"))

        # Số dòng dành cho danh sách người chơi để cột trái cao bằng đúng target_rows
        avail_user_rows = max(1, target_rows - len(left_top) - len(left_bot))
        user_lines = []
        for idx, u in enumerate(users[:avail_user_rows]):
            dot = f"{C_GREEN}●{C_RESET}" if idx == 0 else f"{C_DIM}•{C_RESET}"
            uid_col = pad_visible(u["u_id"], 12)
            lvl_col = pad_visible(f"Lv.{u['gg_lvl']}", 7, align="right")
            cp_col = pad_visible(f"{u['u_cp']:,} CP", 10, align="right")
            tm_col = pad_visible(u["short_save"], 14)
            row_color = C_VAL if idx == 0 else "\033[38;5;252m"
            user_lines.append(make_box_line(
                f"{dot} {row_color}{uid_col}{C_RESET} {C_CYAN}{lvl_col}{C_RESET} {C_YELLOW}{cp_col}{C_RESET}   {C_DIM}{tm_col}{C_RESET}",
                LEFT_W,
            ))

        extra_info = [
            f"{C_DIM}• Domains (4 SSL)  :{C_RESET} {C_CYAN}kotori.click, kotorin.*{C_RESET}",
            f"{C_DIM}• Điểm danh 7 ngày :{C_RESET} {C_GREEN}● Đang bật ({ev['att_count']} bảng){C_RESET}",
            f"{C_DIM}• Cửa hàng StarPass:{C_RESET} {C_GREEN}● Đang mở bán (Pass Sale){C_RESET}",
            f"{C_DIM}• Tour Chapter 3   :{C_RESET} {C_GREEN}● Đang mở (20 màn){C_RESET}",
            f"{C_DIM}• Đồng bộ Level/Save:{C_RESET} {C_GREEN}● Bảo vệ chống tụt Level{C_RESET}",
        ]
        ext_idx = 0
        while len(user_lines) < avail_user_rows:
            if len(user_lines) == len(users) and (avail_user_rows - len(user_lines)) >= 2:
                user_lines.append(make_box_sep(LEFT_W, f"{C_CYAN}▸ TRẠNG THÁI TÍNH NĂNG GAME{C_RESET}"))
            elif len(user_lines) > len(users) and ext_idx < len(extra_info):
                user_lines.append(make_box_line(extra_info[ext_idx], LEFT_W))
                ext_idx += 1
            else:
                user_lines.append(make_box_line("", LEFT_W))

        left_lines = left_top + user_lines + left_bot

        # ---- 2. CỘT PHẢI: BẢNG TELEMETRY LOG THỜI GIAN THỰC ----
        avail_log_rows = max(4, len(left_lines) - 5)
        logs, lstats = parse_logs(max_lines=avail_log_rows, content_w=RIGHT_W - 4, ip_map=ip_map, show_http_200=show_http_200)
        col_time, col_actor, col_dom, col_act, col_res = lstats.get("cols", calc_log_cols(RIGHT_W - 4))

        right_lines = []
        mode_badge = f"{C_GREEN}Gộp gọn RPC{C_RESET}" if not show_http_200 else f"{C_YELLOW}Đầy đủ HTTP{C_RESET}"
        right_lines.append(make_box_top(RIGHT_W, f"{C_CYAN}◆ NHẬT KÝ HOẠT ĐỘNG THỜI GIAN THỰC (LIVE TELEMETRY){C_RESET}"))

        summary_line = (
            f"{C_DIM}Tổng RPC:{C_RESET} {C_VAL}{lstats['rpc']}{C_RESET} "
            f"{C_DIM}│ Lỗi:{C_RESET} {C_RED if lstats['err'] else C_GREEN}{lstats['err']}{C_RESET} "
            f"{C_DIM}│ Vừa thao tác:{C_RESET} {C_CYAN}{lstats['last_actor']}{C_RESET} "
            f"{C_DIM}│ Chế độ:{C_RESET} {mode_badge}"
        )
        right_lines.append(make_box_line(summary_line, RIGHT_W))

        hdr_time = pad_visible("THỜI GIAN", col_time)
        hdr_type = pad_visible("NHÓM", 7)
        hdr_actor = pad_visible("NGƯỜI CHƠI (IP)" if col_actor >= 16 else "NGƯỜI CHƠI", col_actor)
        hdr_dom = pad_visible("TÊN MIỀN", col_dom)
        hdr_act = pad_visible("LỆNH API / TÀI NGUYÊN" if col_act >= 20 else "LỆNH API", col_act)
        hdr_res = pad_visible("KẾT QUẢ", col_res)
        right_lines.append(make_box_sep(RIGHT_W))
        right_lines.append(make_box_line(
            f"{C_HEADER}{hdr_time} {hdr_type} {hdr_actor} {hdr_dom} {hdr_act} {hdr_res}{C_RESET}",
            RIGHT_W,
        ))

        # Giữ trọn các dòng log mới nhất ở cuối bảng, nếu ít hơn thì đệm dòng trống ở dưới
        log_display = list(logs[-avail_log_rows:])
        while len(log_display) < avail_log_rows:
            log_display.append("")

        for l in log_display:
            right_lines.append(make_box_line(l, RIGHT_W))

        legend = (
            f"{C_CYAN}■ LOGIN{C_RESET} {C_DIM}│{C_RESET} "
            f"{C_GREEN}■ SAVE{C_RESET} {C_DIM}│{C_RESET} "
            f"{C_MAGENTA}■ QUEST{C_RESET} {C_DIM}│{C_RESET} "
            f"{C_YELLOW}■ REWARD{C_RESET} {C_DIM}│{C_RESET} "
            f"{C_ORANGE}■ SHOP{C_RESET} {C_DIM}│{C_RESET} "
            f"{C_RED}■ ERROR{C_RESET}"
        )
        right_lines.append(make_box_bot(RIGHT_W, legend))

        # Ghép 2 cột song song (cùng chiều cao tuyệt đối)
        combined = []
        total_h = max(len(left_lines), len(right_lines))
        for i in range(total_h):
            l_str = left_lines[i] if i < len(left_lines) else (" " * LEFT_W)
            r_str = right_lines[i] if i < len(right_lines) else (" " * RIGHT_W)
            combined.append(f"{l_str}  {r_str}\033[K")

        if flash_msg:
            footer = f" \033[1;38;5;226m▸ THÔNG BÁO: {flash_msg}{C_RESET}\033[K"
        else:
            footer = (
                f" {C_DIM}Tự động làm mới 0.8s │ Phím tắt: "
                f"{C_VAL}[1-3]{C_DIM} Server  {C_VAL}[4]{C_DIM} Log  {C_VAL}[5]{C_DIM} Reset  "
                f"{C_VAL}[6]{C_DIM} Test  {C_VAL}[f]{C_DIM} Chế độ Log  {C_VAL}[p]{C_DIM} Mật khẩu  "
                f"{C_VAL}[c]{C_DIM} Xoá Log  {C_VAL}[q]{C_DIM} Thoát{C_RESET}\033[K"
            )

        return "\033[H" + "\n".join(combined) + "\n" + footer

    # ================= CHẾ ĐỘ 1 CỘT (MÀN HÌNH HẸP < 104 CỘT) =================
    W = max(78, term_w - 1)
    frame = []
    frame.append(make_box_top(W, f"{C_TITLE}◆ GUITAR GIRL SERVER • LIVE CONTROL{C_RESET}"))
    if is_running:
        st = f"{C_GREEN}● RUNNING{C_RESET} (PID {pid})"
    else:
        st = f"{C_RED}● STOPPED{C_RESET}"
    frame.append(make_box_line(f"{C_LABEL}Trạng thái:{C_RESET} {st}  {C_DIM}│{C_RESET} {C_LABEL}Cổng:{C_RESET} {C_VAL}{PORT}{C_RESET}  {C_DIM}│{C_RESET} {health_badge}", W))
    frame.append(make_box_line(f"{C_LABEL}URL:{C_RESET} {C_CYAN}{GG_PUBLIC_BASE}{C_RESET}  {C_DIM}│{C_RESET} {C_LABEL}Admin:{C_RESET} {C_MAGENTA}{GG_PUBLIC_BASE}/admin{C_RESET}", W))
    frame.append(make_box_sep(W, f"{C_CYAN}▸ TÀI NGUYÊN & NGƯỜI CHƠI ({len(users)}){C_RESET}"))
    frame.append(make_box_line(f"CPU: {draw_bar(cpu_pct, 10)} {cpu_pct:4.1f}% │ RAM: {draw_bar(ram_pct, 10)} {ram_pct:4.1f}% │ Disk: {disk_pct:4.1f}%", W))

    frame.append(make_box_sep(W, f"{C_CYAN}▸ NHẬT KÝ HOẠT ĐỘNG (LIVE TELEMETRY){C_RESET}"))
    log_rows = max(7, term_h - 13)
    logs, lstats_1 = parse_logs(max_lines=log_rows, content_w=W - 4, ip_map=ip_map, show_http_200=show_http_200)
    c_t, c_a, c_d, c_ac, c_r = lstats_1.get("cols", calc_log_cols(W - 4))
    frame.append(make_box_line(
        f"{C_HEADER}{pad_visible('THỜI GIAN', c_t)} {pad_visible('NHÓM', 7)} {pad_visible('NGƯỜI CHƠI', c_a)} {pad_visible('TÊN MIỀN', c_d)} {pad_visible('LỆNH API', c_ac)} {pad_visible('KẾT QUẢ', c_r)}{C_RESET}",
        W,
    ))
    for l in logs:
        frame.append(make_box_line(l, W))

    frame.append(make_box_sep(W, f"{C_YELLOW}▸ PHÍM ĐIỀU KHIỂN{C_RESET}"))
    frame.append(make_box_line(f"{C_GREEN}[1]{C_RESET}Start {C_RED}[2]{C_RESET}Stop {C_CYAN}[3]{C_RESET}Restart {C_YELLOW}[4]{C_RESET}Log {C_MAGENTA}[5]{C_RESET}Reset {C_BLUE}[6]{C_RESET}Test {C_ORANGE}[f]{C_RESET}Lọc {C_YELLOW}[c]{C_RESET}Xoá {C_VAL}[q]{C_RESET}Thoát", W))
    frame.append(make_box_bot(W))

    footer = f" \033[1;38;5;226m▸ {flash_msg}{C_RESET}\033[K" if flash_msg else f" {C_DIM}Nhấn [1-6, f, p, c, q] để thao tác...{C_RESET}\033[K"
    return "\033[H" + "\n".join(line + "\033[K" for line in frame) + "\n" + footer


# ==============================================================================
#  VÒNG LẶP CHÍNH (LIVETIME LOOP 0.8s)
# ==============================================================================
def run_subcommand(args):
    subprocess.run(["bash", RUN_SH] + args)
    print(f"\n{C_DIM}Nhấn Enter để quay lại Dashboard...{C_RESET}")
    try:
        input()
    except (KeyboardInterrupt, EOFError):
        pass


def main():
    if not sys.stdin.isatty():
        print("Dashboard yêu cầu terminal tương tác (TTY).")
        sys.exit(1)

    sys.stdout.write("\033[?1049h\033[?25l\033[2J")
    sys.stdout.flush()

    old_termios = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())

    flash_msg = None
    flash_time = 0.0
    show_http_200 = False
    show_pass = False

    try:
        while True:
            if flash_msg and (time.time() - flash_time > 3.5):
                flash_msg = None

            output = render_dashboard(flash_msg, show_http_200=show_http_200, show_pass=show_pass)
            sys.stdout.write(output)
            sys.stdout.flush()

            r, _, _ = select.select([sys.stdin], [], [], 0.8)
            if r:
                ch = sys.stdin.read(1)
                if ch in ("q", "Q", "\x03"):
                    break
                elif ch in ("f", "F"):
                    show_http_200 = not show_http_200
                    mode_name = "Hiển thị đầy đủ HTTP 200" if show_http_200 else "Chế độ Gộp gọn RPC (ẩn POST 200 trùng lặp)"
                    flash_msg = f"Đã chuyển sang: {mode_name}"
                    flash_time = time.time()
                elif ch in ("p", "P"):
                    show_pass = not show_pass
                    flash_msg = "Đã hiện mật khẩu Admin" if show_pass else "Đã ẩn mật khẩu Admin"
                    flash_time = time.time()
                elif ch in ("c", "C"):
                    try:
                        with open(LOG_FILE, "w"):
                            pass
                        flash_msg = "Đã dọn sạch tệp nhật ký (log) thành công!"
                    except Exception as e:
                        flash_msg = f"Lỗi khi dọn log: {e}"
                    flash_time = time.time()
                elif ch in ("1", "2", "3", "4", "5", "6"):
                    cmd_map = {
                        "1": ["start"],
                        "2": ["stop"],
                        "3": ["restart"],
                        "4": ["logs"],
                        "5": ["clear"],
                        "6": ["test"],
                    }
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_termios)
                    sys.stdout.write("\033[?1049l\033[?25h\033[2J\033[H")
                    sys.stdout.flush()
                    try:
                        if ch == "4":
                            subprocess.run(["bash", RUN_SH, "logs"])
                        else:
                            run_subcommand(cmd_map[ch])
                    except KeyboardInterrupt:
                        pass
                    sys.stdout.write("\033[?1049h\033[?25l\033[2J")
                    sys.stdout.flush()
                    tty.setcbreak(sys.stdin.fileno())
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_termios)
        sys.stdout.write("\033[?1049l\033[?25h")
        sys.stdout.flush()

        pid = get_server_pid()
        print(f"\n{C_GREEN}✓ Đã đóng giao diện Monitor.{C_RESET}")
        if pid:
            print(f"{C_CYAN}ℹ️  LƯU Ý: Guitar Girl Server vẫn đang CHẠY NGẦM an toàn (PID: {C_VAL}{pid}{C_CYAN}, Cổng: {C_VAL}{PORT}{C_CYAN}).{C_RESET}")
            print(f"{C_CYAN}   Có thể yên tâm ngắt kết nối SSH mà server vẫn tiếp tục phục vụ!{C_RESET}")
        print(f"   Gõ {C_VAL}./run.sh{C_RESET} bất cứ lúc nào để mở lại bảng điều khiển.\n")


if __name__ == "__main__":
    main()

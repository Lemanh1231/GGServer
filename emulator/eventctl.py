#!/usr/bin/env python3
"""CLI utility to manage Guitar Girl server events."""
import sys
import os

# Add emulator dir to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from server import event_manager

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def format_status(enabled):
    return f"{GREEN}[BẬT]{RESET}" if enabled else f"{RED}[TẮT]{RESET}"


def cmd_list():
    cfg = event_manager.load_event_config()
    print(f"\n{BOLD}{CYAN}=== GUITAR GIRL SERVER - DANH SÁCH SỰ KIỆN ==={RESET}\n")

    # Group 1
    print(f"{BOLD}[1] SỰ KIỆN ĐIỂM DANH & ĐĂNG NHẬP (Attendance & Login){RESET}")
    print("-" * 70)
    for eid, item in cfg.get('attendance_events', {}).items():
        st = format_status(item.get('enabled'))
        name = item.get('name', '')
        desc = item.get('description', '')
        print(f"  ID {eid:<7}: {st}  {BOLD}{name}{RESET} - {desc}")
    print()

    # Group 2
    sp = cfg.get('star_pass', {})
    s_id = sp.get('active_season', 13)
    s_info = next((s for s in event_manager.STAR_PASS_SEASONS if s['id'] == s_id), {'name_vi': 'Unknown'})
    print(f"{BOLD}[2] THẺ SAO / STAR PASS (13 Mùa giải xoay vòng){RESET}")
    print("-" * 70)
    print(f"  Trạng thái Pass     : {format_status(sp.get('enabled'))}")
    print(f"  Mùa giải hoạt động  : {BOLD}Mùa {s_id}{RESET} - {s_info.get('name_vi')} ({s_info.get('name_en', '')})")
    print(f"  Thẻ Sao Gold Trả Phí: {format_status(sp.get('paid_card_enabled'))}")
    print()

    # Group 3
    pgs = cfg.get('pass_goods_sale', {})
    print(f"{BOLD}[3] CỬA HÀNG GIẢM GIÁ STAR PASS (Pass Goods Sale / Merch Shop){RESET}")
    print("-" * 70)
    print(f"  Trạng thái: {format_status(pgs.get('enabled'))}  {BOLD}{pgs.get('name')}{RESET}")
    print(f"  Chi tiết  : {pgs.get('description')}")
    print()

    # Group 4
    mf = cfg.get('meowfest', {})
    print(f"{BOLD}[4] SỰ KIỆN NUÔI MÈO MEOWFEST (SamSeck 333 Event){RESET}")
    print("-" * 70)
    print(f"  Trạng thái: {format_status(mf.get('enabled'))}  {BOLD}{mf.get('name')}{RESET}")
    print(f"  Chi tiết  : {mf.get('description')}")
    print()

    # Group 5
    c3 = cfg.get('chapter3_tour', {})
    print(f"{BOLD}[5] BIỂU DIỄN SÂN KHẤU TOUR CHAPTER 3 (Sunshine High School){RESET}")
    print("-" * 70)
    print(f"  Trạng thái: {format_status(c3.get('enabled'))}  {BOLD}{c3.get('name')}{RESET}")
    print(f"  Chi tiết  : {c3.get('description')}")
    print()

    # Group 6
    wf = cfg.get('weather_festival', {})
    print(f"{BOLD}[6] LỄ HỘI HIỆU ỨNG THỜI TIẾT MÙA (Weather Festival){RESET}")
    print("-" * 70)
    print(f"  Tuyết rơi mùa đông (Snow)       : {format_status(wf.get('snow_enabled'))}")
    print(f"  Hoa anh đào mùa xuân (Cherry)   : {format_status(wf.get('cherry_blossom_enabled'))}")
    print()

    # Group 7
    fac = cfg.get('fan_art_costume', {})
    print(f"{BOLD}[7] TRANG PHỤC BẢN GIỚI HẠN FAN ART 2021{RESET}")
    print("-" * 70)
    print(f"  Trạng thái: {format_status(fac.get('enabled'))}  {BOLD}{fac.get('name')}{RESET}")
    print(f"  Chi tiết  : {fac.get('description')}")
    print()

    # Group 8
    er = cfg.get('event_ranking', {})
    print(f"{BOLD}[8] ĐUA TOP XẾP HẠNG SỰ KIỆN (Event Ranking Leaderboard){RESET}")
    print("-" * 70)
    print(f"  Trạng thái: {format_status(er.get('enabled'))}  {BOLD}{er.get('name')}{RESET}")
    print(f"  Chi tiết  : {er.get('description')}")
    print()
    print(f"{YELLOW}* Mọi thay đổi áp dụng tức thì (zero-downtime hot reload) không cần restart server.{RESET}\n")


def cmd_enable(target):
    cfg = event_manager.load_event_config()
    t = target.lower()

    if t in cfg.get('attendance_events', {}):
        event_manager.set_attendance_event_enabled(t, True)
        name = cfg['attendance_events'][t]['name']
        print(f"{GREEN}✓ Đã BẬT sự kiện điểm danh ID {t} ({name}){RESET}")
    elif t in ('pass', 'starpass', 'star_pass'):
        event_manager.set_star_pass(enabled=True)
        print(f"{GREEN}✓ Đã BẬT Thẻ Sao (Star Pass){RESET}")
    elif t in ('gold', 'paid_gold', 'starpass_gold'):
        event_manager.set_star_pass(paid_gold=True)
        print(f"{GREEN}✓ Đã BẬT Thẻ Sao Gold Trả Phí (Paid Pass Gold){RESET}")
    elif t in ('sale', 'goodssale', 'pass_sale'):
        event_manager.set_pass_goods_sale_enabled(True)
        print(f"{GREEN}✓ Đã BẬT Cửa hàng Giảm giá Star Pass (Pass Goods Sale){RESET}")
    elif t in ('meow', 'meowfest', 'cat', 'samseck'):
        event_manager.set_meowfest_enabled(True)
        print(f"{GREEN}✓ Đã BẬT Sự kiện Nuôi Mèo Meowfest (SamSeck){RESET}")
    elif t in ('ch3', 'tour', 'chapter3'):
        event_manager.set_chapter3_tour_enabled(True)
        print(f"{GREEN}✓ Đã BẬT Sự kiện Tour Chapter 3 (Sunshine High School){RESET}")
    elif t in ('snow', 'tuyet'):
        event_manager.set_weather_festival(snow=True)
        print(f"{GREEN}✓ Đã BẬT Hiệu ứng Tuyết rơi mùa đông (Snow Festival){RESET}")
    elif t in ('cherry', 'cherryblossom', 'hoaanhdao'):
        event_manager.set_weather_festival(cherry_blossom=True)
        print(f"{GREEN}✓ Đã BẬT Hiệu ứng Cánh hoa anh đào rơi (Cherry Blossom Date){RESET}")
    elif t in ('fanart', 'costume'):
        event_manager.set_fan_art_costume_enabled(True)
        print(f"{GREEN}✓ Đã BẬT Trang phục Thiết kế Fan Art 2021{RESET}")
    elif t in ('rank', 'ranking', 'duatop'):
        event_manager.set_event_ranking_enabled(True)
        print(f"{GREEN}✓ Đã BẬT Đua Top Xếp Hạng Sự Kiện (Event Ranking){RESET}")
    elif t == 'all':
        for eid in cfg.get('attendance_events', {}):
            event_manager.set_attendance_event_enabled(eid, True)
        event_manager.set_star_pass(enabled=True, paid_gold=True)
        event_manager.set_pass_goods_sale_enabled(True)
        event_manager.set_meowfest_enabled(True)
        event_manager.set_chapter3_tour_enabled(True)
        event_manager.set_weather_festival(snow=True, cherry_blossom=True)
        event_manager.set_fan_art_costume_enabled(True)
        event_manager.set_event_ranking_enabled(True)
        print(f"{GREEN}✓ Đã BẬT TẤT CẢ các sự kiện!{RESET}")
    else:
        print(f"{RED}✗ Mục không hợp lệ: '{target}'. Dùng: 1, 2, 3, 202110, 202111, pass, gold, sale, meowfest, ch3, snow, cherry, fanart, rank, all{RESET}")


def cmd_disable(target):
    cfg = event_manager.load_event_config()
    t = target.lower()

    if t in cfg.get('attendance_events', {}):
        event_manager.set_attendance_event_enabled(t, False)
        name = cfg['attendance_events'][t]['name']
        print(f"{YELLOW}✓ Đã TẮT sự kiện điểm danh ID {t} ({name}){RESET}")
    elif t in ('pass', 'starpass', 'star_pass'):
        event_manager.set_star_pass(enabled=False)
        print(f"{YELLOW}✓ Đã TẮT Thẻ Sao (Star Pass){RESET}")
    elif t in ('gold', 'paid_gold', 'starpass_gold'):
        event_manager.set_star_pass(paid_gold=False)
        print(f"{YELLOW}✓ Đã TẮT Thẻ Sao Gold Trả Phí (Paid Pass Gold){RESET}")
    elif t in ('sale', 'goodssale', 'pass_sale'):
        event_manager.set_pass_goods_sale_enabled(False)
        print(f"{YELLOW}✓ Đã TẮT Cửa hàng Giảm giá Star Pass (Pass Goods Sale){RESET}")
    elif t in ('meow', 'meowfest', 'cat', 'samseck'):
        event_manager.set_meowfest_enabled(False)
        print(f"{YELLOW}✓ Đã TẮT Sự kiện Nuôi Mèo Meowfest (SamSeck){RESET}")
    elif t in ('ch3', 'tour', 'chapter3'):
        event_manager.set_chapter3_tour_enabled(False)
        print(f"{YELLOW}✓ Đã TẮT Sự kiện Tour Chapter 3 (Sunshine High School){RESET}")
    elif t in ('snow', 'tuyet'):
        event_manager.set_weather_festival(snow=False)
        print(f"{YELLOW}✓ Đã TẮT Hiệu ứng Tuyết rơi mùa đông (Snow Festival){RESET}")
    elif t in ('cherry', 'cherryblossom', 'hoaanhdao'):
        event_manager.set_weather_festival(cherry_blossom=False)
        print(f"{YELLOW}✓ Đã TẮT Hiệu ứng Cánh hoa anh đào rơi (Cherry Blossom Date){RESET}")
    elif t in ('fanart', 'costume'):
        event_manager.set_fan_art_costume_enabled(False)
        print(f"{YELLOW}✓ Đã TẮT Trang phục Thiết kế Fan Art 2021{RESET}")
    elif t in ('rank', 'ranking', 'duatop'):
        event_manager.set_event_ranking_enabled(False)
        print(f"{YELLOW}✓ Đã TẮT Đua Top Xếp Hạng Sự Kiện (Event Ranking){RESET}")
    elif t == 'all':
        for eid in cfg.get('attendance_events', {}):
            event_manager.set_attendance_event_enabled(eid, False)
        event_manager.set_star_pass(enabled=False, paid_gold=False)
        event_manager.set_pass_goods_sale_enabled(False)
        event_manager.set_meowfest_enabled(False)
        event_manager.set_chapter3_tour_enabled(False)
        event_manager.set_weather_festival(snow=False, cherry_blossom=False)
        event_manager.set_fan_art_costume_enabled(False)
        event_manager.set_event_ranking_enabled(False)
        print(f"{YELLOW}✓ Đã TẮT TẤT CẢ các sự kiện!{RESET}")
    else:
        print(f"{RED}✗ Mục không hợp lệ: '{target}'. Dùng: 1, 2, 3, 202110, 202111, pass, gold, sale, meowfest, ch3, snow, cherry, fanart, rank, all{RESET}")


def cmd_season(season_num):
    try:
        s_val = int(season_num)
        if not (1 <= s_val <= 13):
            raise ValueError()
    except ValueError:
        print(f"{RED}✗ Số mùa giải không hợp lệ: '{season_num}'. Vui lòng chọn từ 1 đến 13.{RESET}")
        return

    event_manager.set_star_pass(season=s_val)
    s_info = next((s for s in event_manager.STAR_PASS_SEASONS if s['id'] == s_val), {})
    print(f"{GREEN}✓ Đã chuyển Star Pass sang Mùa {s_val}: {s_info.get('name_vi')} ({s_info.get('name_en')}){RESET}")


def cmd_gold(state_val):
    v = state_val.lower() in ('on', 'true', '1', 'enable', 'bat', 'bật')
    event_manager.set_star_pass(paid_gold=v)
    st = "BẬT" if v else "TẮT"
    print(f"{GREEN}✓ Đã {st} Thẻ Sao Gold Trả Phí (Paid Star Pass Gold){RESET}")


def cmd_sendmail(args):
    if len(args) < 2:
        print(f"{RED}Cú pháp: ./emulator/eventctl.sh sendmail <tiêu_đề> <nội_dung> [cp] [kẹo] [cookies]{RESET}")
        return
    title = args[0]
    memo = args[1]
    cp = int(args[2]) if len(args) > 2 and args[2].isdigit() else 0
    candy = float(args[3]) if len(args) > 3 else 0.0
    cookies = int(args[4]) if len(args) > 4 and args[4].isdigit() else 0

    from server.handlers import post
    items = []
    if cp > 0:
        items.append({'i_RewardType': 1, 'i_RewardId': 1, 'd_RewardQuantity': float(cp)})
    if candy > 0:
        items.append({'i_RewardType': 1, 'i_RewardId': 2, 'd_RewardQuantity': float(candy)})
    if cookies > 0:
        items.append({'i_RewardType': 1, 'i_RewardId': 11, 'd_RewardQuantity': float(cookies)})

    p = post.send_post(uuid=None, title=title, memo=memo, items=items)
    print(f"{GREEN}✓ Đã gửi thư thành công vào game! (ID thư: {p.get('idx')}){RESET}")
    if items:
        print(f"{CYAN}  Quà đính kèm: {cp} CP, {candy} Kẹo, {cookies} Cookies{RESET}")

    if trigger_soft_resume():
        print(f"{YELLOW}⚡ Đã tự động kích hoạt soft-sync tới game qua ADB! Client đã cập nhật hòm thư tức thì.{RESET}")


def trigger_soft_resume():
    try:
        import subprocess
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=2)
        if "\tdevice" in res.stdout:
            subprocess.run([
                "adb", "shell", "am", "start", "-n",
                "com.neowiz.game.guitargirl/com.google.firebase.MessagingUnityPlayerActivity"
            ], capture_output=True, text=True, timeout=3)
            return True
    except Exception:
        pass
    return False


def print_help():
    print(f"""{BOLD}Hướng dẫn sử dụng công cụ điều khiển sự kiện (eventctl):{RESET}
  {CYAN}./emulator/eventctl.sh list{RESET}               : Hiển thị trạng thái tất cả các sự kiện
  {CYAN}./emulator/eventctl.sh enable <mục>{RESET}       : Bật sự kiện (1, 2, 3, 202110, 202111, pass, gold, sale, meowfest, ch3, snow, cherry, fanart, rank, all)
  {CYAN}./emulator/eventctl.sh disable <mục>{RESET}      : Tắt sự kiện (1, 2, 3, 202110, 202111, pass, gold, sale, meowfest, ch3, snow, cherry, fanart, rank, all)
  {CYAN}./emulator/eventctl.sh season <1-13>{RESET}     : Đặt mùa giải Star Pass (1 đến 13)
  {CYAN}./emulator/eventctl.sh gold <on|off>{RESET}     : Bật/tắt Thẻ Sao Gold trả phí
  {CYAN}./emulator/eventctl.sh sendmail <tiêu_đề> <nội_dung> [cp] [kẹo] [cookies]{RESET} : Gửi thư & quà trực tiếp vào game
""")


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help', 'help'):
        print_help()
        sys.exit(0)

    cmd = args[0].lower()
    if cmd in ('list', 'status', 'ls'):
        cmd_list()
    elif cmd in ('enable', 'on', 'start'):
        if len(args) < 2:
            print(f"{RED}Thiếu mục cần bật! Ví dụ: ./emulator/eventctl.sh enable 3{RESET}")
        else:
            cmd_enable(args[1])
    elif cmd in ('disable', 'off', 'stop'):
        if len(args) < 2:
            print(f"{RED}Thiếu mục cần tắt! Ví dụ: ./emulator/eventctl.sh disable 2{RESET}")
        else:
            cmd_disable(args[1])
    elif cmd in ('season', 'setseason'):
        if len(args) < 2:
            print(f"{RED}Thiếu số mùa giải! Ví dụ: ./emulator/eventctl.sh season 13{RESET}")
        else:
            cmd_season(args[1])
    elif cmd == 'gold':
        if len(args) < 2:
            print(f"{RED}Thiếu trạng thái! Ví dụ: ./emulator/eventctl.sh gold on{RESET}")
        else:
            cmd_gold(args[1])
    elif cmd in ('sendmail', 'mail', 'post'):
        cmd_sendmail(args[1:])
    else:
        print(f"{RED}Lệnh không xác định: '{cmd}'.{RESET}")
        print_help()

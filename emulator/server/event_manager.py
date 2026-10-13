"""Event Manager for Guitar Girl Server.

Provides unified runtime event configuration, zero-downtime hot reloading,
and synchronization across Attendance, Star Pass, Goods Sale, Meowfest, Chapter 3 Tour,
Seasonal Weather Festivals, Fan Art Costumes, and Event Leaderboards.
"""
import os
import json
import copy

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'event_config.json')

STAR_PASS_SEASONS = [
    {'id': 1, 'name_vi': 'Vị chanh Kỳ nghỉ', 'name_en': 'Lemon Flavored Vacation', 'year': 2020, 'month': 8},
    {'id': 2, 'name_vi': 'Một điều ước gửi đến mặt trăng', 'name_en': 'Make a wish to the moon', 'year': 2020, 'month': 9},
    {'id': 3, 'name_vi': 'Ngọt ngào Bữa tiệc Halloween', 'name_en': 'Sweet Halloween Party', 'year': 2020, 'month': 10},
    {'id': 4, 'name_vi': 'Buổi chụp ảnh đặc biệt! Thần tượng ngọt ngào', 'name_en': 'Sweet Idol Photoshoot!', 'year': 2020, 'month': 11},
    {'id': 5, 'name_vi': 'Lấp lánh Giáng Sinh mộng mơ', 'name_en': 'Twinkling Dreamy Christmas', 'year': 2020, 'month': 12},
    {'id': 6, 'name_vi': 'Lễ hội tuyết', 'name_en': 'Snow Festival', 'year': 2021, 'month': 1},
    {'id': 7, 'name_vi': 'Thiếu nữ ngày Tình nhân', 'name_en': 'Maid in Valentine', 'year': 2021, 'month': 2},
    {'id': 8, 'name_vi': 'Hẹn hò mùa hoa anh đào', 'name_en': 'Cherry Blossom Date', 'year': 2021, 'month': 3},
    {'id': 9, 'name_vi': 'Thông điệp mùa xuân dễ thương', 'name_en': 'Pleasant Spring Message', 'year': 2021, 'month': 4},
    {'id': 10, 'name_vi': 'Picnic Tối Đầy Nắng', 'name_en': 'Sunny Evening Picnic', 'year': 2021, 'month': 5},
    {'id': 11, 'name_vi': 'Ký Ức Màu Phấn Mơ Mộng', 'name_en': 'Dreaming Pastel Memories', 'year': 2021, 'month': 6},
    {'id': 12, 'name_vi': 'Mùa Hè Lấp Lánh', 'name_en': 'Shining Summer', 'year': 2021, 'month': 7},
    {'id': 13, 'name_vi': 'Cưỡi một vòng đu quay lãng mạn', 'name_en': 'Riding a Romantic Ferris Wheel', 'year': 2021, 'month': 8},
]

DEFAULT_CONFIG = {
    'attendance_events': {
        '1': {
            'name': 'Điểm danh 7 ngày tân thủ',
            'description': 'Nhận CP, Kẹo, Trang phục Váy đầm hoa tuyết và Nhạc Bông hoa chưa được đặt tên',
            'enabled': True,
        },
        '2': {
            'name': 'Điểm danh kỷ niệm 1 năm',
            'description': 'Sự kiện 1st Anniversary mừng sinh nhật game (14 ngày: Guitar Đêm tím, Trang phục Ký ức vĩnh cửu)',
            'enabled': False,
        },
        '3': {
            'name': 'Tiệm bánh Hạnh phúc (CH2)',
            'description': 'Điểm danh hằng ngày Cửa hàng tiện lợi Chapter 2 (7 ngày Bánh gừng, Kẹo, Năng lượng Cookie AP)',
            'enabled': True,
        },
        '202110': {
            'name': 'Điểm danh Halloween (10/2021)',
            'description': 'Sự kiện đăng nhập lễ hội Halloween 14 ngày (Guitar Hoa hạnh nhân, Trang phục Cô gái hồng)',
            'enabled': False,
        },
        '202111': {
            'name': 'Chọn quà tân thủ (11/2021)',
            'description': 'Sự kiện chọn quà đăng nhập tân thủ 7 ngày',
            'enabled': False,
        },
    },
    'star_pass': {
        'name': 'Thẻ Sao / Star Pass',
        'description': 'Vé mùa Star Pass với chuỗi nhiệm vụ và phần thưởng độc quyền 13 mùa giải',
        'enabled': True,
        'active_season': 13,
        'paid_card_enabled': False,
    },
    'pass_goods_sale': {
        'name': 'Cửa hàng Giảm giá Star Pass (Pass Goods Sale)',
        'description': 'Mở biểu tượng nút Sale trên sảnh chính để mua lại toàn bộ Trang phục & Guitar của 13 mùa Star Pass đã qua',
        'enabled': True,
    },
    'meowfest': {
        'name': 'Sự kiện Nuôi Mèo Meowfest (SamSeck)',
        'description': 'Mở khóa 3 mốc nuôi mèo Tam Thể nhận Cây cào móng (Guitar 10), Quần yếm (Costume 13), Bé mèo Navi (Unit 1)',
        'enabled': True,
    },
    'chapter3_tour': {
        'name': 'Tour Chapter 3 (Sunshine High School)',
        'description': 'Biểu diễn sân khấu trường trung học Sunshine 20 màn với Năng lượng Cookie / AP',
        'enabled': True,
    },
    'weather_festival': {
        'name': 'Lễ hội Hiệu ứng Thời tiết Mùa',
        'description': 'Hiệu ứng tuyết rơi mùa đông (Snow Festival) hoặc cánh hoa anh đào rơi mùa xuân (Cherry Blossom Date)',
        'snow_enabled': True,
        'cherry_blossom_enabled': False,
    },
    'fan_art_costume': {
        'name': 'Trang phục Thiết kế Fan Art',
        'description': 'Kích hoạt bộ trang phục nghệ thuật do cộng đồng người hâm mộ sáng tạo',
        'enabled': True,
    },
    'event_ranking': {
        'name': 'Đua Top Xếp Hạng Sự Kiện (Event Ranking)',
        'description': 'Bảng xếp hạng đua top điểm sự kiện trực tiếp với danh sách Top 100 cao thủ',
        'enabled': True,
    },
}


def _normalize_config(raw):
    """Normalize raw dict ensuring all required sections exist and keep backward compatibility."""
    if not isinstance(raw, dict):
        raw = copy.deepcopy(DEFAULT_CONFIG)

    cfg = copy.deepcopy(DEFAULT_CONFIG)

    # 1. Attendance events
    att = raw.get('attendance_events')
    if not isinstance(att, dict):
        legacy = raw.get('events', {})
        if isinstance(legacy, dict):
            att = legacy

    if isinstance(att, dict):
        for k, def_item in cfg['attendance_events'].items():
            if k in att and isinstance(att[k], dict):
                user_item = att[k]
                cfg['attendance_events'][k]['enabled'] = bool(user_item.get('enabled', def_item['enabled']))
                if 'name' in user_item:
                    cfg['attendance_events'][k]['name'] = user_item['name']
                if 'description' in user_item:
                    cfg['attendance_events'][k]['description'] = user_item['description']

    # 2. Star Pass
    sp = raw.get('star_pass')
    if isinstance(sp, dict):
        cfg['star_pass']['enabled'] = bool(sp.get('enabled', True))
        try:
            s_val = int(sp.get('active_season', 13))
            if 1 <= s_val <= 13:
                cfg['star_pass']['active_season'] = s_val
        except (ValueError, TypeError):
            pass
        if 'paid_card_enabled' in sp:
            cfg['star_pass']['paid_card_enabled'] = bool(sp.get('paid_card_enabled', False))
    elif 'paid_star_card' in raw and isinstance(raw['paid_star_card'], dict):
        cfg['star_pass']['paid_card_enabled'] = bool(raw['paid_star_card'].get('enabled', False))

    # 3. Pass Goods Sale
    pgs = raw.get('pass_goods_sale')
    if isinstance(pgs, dict):
        cfg['pass_goods_sale']['enabled'] = bool(pgs.get('enabled', True))

    # 4. Meowfest
    mf = raw.get('meowfest')
    if isinstance(mf, dict):
        cfg['meowfest']['enabled'] = bool(mf.get('enabled', True))

    # 5. Chapter 3 Tour
    c3 = raw.get('chapter3_tour')
    if isinstance(c3, dict):
        cfg['chapter3_tour']['enabled'] = bool(c3.get('enabled', True))

    # 6. Weather Festival
    wf = raw.get('weather_festival')
    if isinstance(wf, dict):
        cfg['weather_festival']['snow_enabled'] = bool(wf.get('snow_enabled', True))
        cfg['weather_festival']['cherry_blossom_enabled'] = bool(wf.get('cherry_blossom_enabled', False))

    # 7. Fan Art Costume
    fac = raw.get('fan_art_costume')
    if isinstance(fac, dict):
        cfg['fan_art_costume']['enabled'] = bool(fac.get('enabled', True))

    # 8. Event Ranking
    er = raw.get('event_ranking')
    if isinstance(er, dict):
        cfg['event_ranking']['enabled'] = bool(er.get('enabled', True))

    # Backward compatibility fields
    cfg['events'] = {}
    for k, v in cfg['attendance_events'].items():
        cfg['events'][k] = {
            'name': v['name'],
            'enabled': v['enabled'],
            'state': 'active' if v['enabled'] else 'ended',
        }
    cfg['paid_star_card'] = {
        'name': 'Thẻ Sao Gold trả tiền',
        'enabled': cfg['star_pass']['paid_card_enabled'],
        'price': 0,
    }

    return cfg


def load_event_config():
    """Load configuration from disk on every invocation for zero-downtime hot reload."""
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        return _normalize_config(raw)
    except Exception:
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        return _normalize_config(cfg)


def save_event_config(cfg, notify_in_game=False):
    """Normalize and persist configuration atomically to disk."""
    normalized = _normalize_config(cfg)
    tmp_path = CONFIG_PATH + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, CONFIG_PATH)

    try:
        from server.handlers import gamedata
        gamedata.invalidate_cache()
    except Exception:
        pass

    if notify_in_game:
        try:
            from server.handlers import post
            sp = normalized.get('star_pass', {})
            s_id = sp.get('active_season', 13)
            s_info = next((s for s in STAR_PASS_SEASONS if s['id'] == s_id), {})
            title = "Cập nhật Sự kiện Trực tiếp"
            memo = f"Sự kiện máy chủ đã được đồng bộ! Star Pass: Mùa {s_id} - {s_info.get('name_vi', '')}. Chúc bạn có những phút giây thư giãn tuyệt vời!"
            post.send_post(uuid=None, title=title, memo=memo)
        except Exception:
            pass

    return normalized


# Query helpers
def is_attendance_event_enabled(event_idx):
    cfg = load_event_config()
    k = str(event_idx)
    return bool(cfg.get('attendance_events', {}).get(k, {}).get('enabled', False))


def is_star_pass_enabled():
    cfg = load_event_config()
    return bool(cfg.get('star_pass', {}).get('enabled', True))


def get_active_star_pass_season():
    cfg = load_event_config()
    try:
        val = int(cfg.get('star_pass', {}).get('active_season', 13))
        return val if 1 <= val <= 13 else 13
    except Exception:
        return 13


def is_paid_star_card_enabled():
    cfg = load_event_config()
    sp = cfg.get('star_pass', {})
    return bool(sp.get('paid_card_enabled', False) or cfg.get('paid_star_card', {}).get('enabled', False))


def is_pass_goods_sale_enabled():
    cfg = load_event_config()
    return bool(cfg.get('pass_goods_sale', {}).get('enabled', True))


def is_meowfest_enabled():
    cfg = load_event_config()
    return bool(cfg.get('meowfest', {}).get('enabled', True))


def is_chapter3_tour_enabled():
    cfg = load_event_config()
    return bool(cfg.get('chapter3_tour', {}).get('enabled', True))


def is_weather_snow_enabled():
    cfg = load_event_config()
    return bool(cfg.get('weather_festival', {}).get('snow_enabled', True))


def is_weather_cherry_blossom_enabled():
    cfg = load_event_config()
    return bool(cfg.get('weather_festival', {}).get('cherry_blossom_enabled', False))


def is_fan_art_costume_enabled():
    cfg = load_event_config()
    return bool(cfg.get('fan_art_costume', {}).get('enabled', True))


def is_event_ranking_enabled():
    cfg = load_event_config()
    return bool(cfg.get('event_ranking', {}).get('enabled', True))


# Mutation helpers
def set_attendance_event_enabled(event_idx, enabled):
    cfg = load_event_config()
    k = str(event_idx)
    if k in cfg.get('attendance_events', {}):
        cfg['attendance_events'][k]['enabled'] = bool(enabled)
        return save_event_config(cfg)
    return cfg


def set_star_pass(enabled=None, season=None, paid_gold=None):
    cfg = load_event_config()
    sp = cfg.setdefault('star_pass', {})
    if enabled is not None:
        sp['enabled'] = bool(enabled)
    if season is not None:
        try:
            s_val = int(season)
            if 1 <= s_val <= 13:
                sp['active_season'] = s_val
        except (ValueError, TypeError):
            pass
    if paid_gold is not None:
        sp['paid_card_enabled'] = bool(paid_gold)
    return save_event_config(cfg)


def set_pass_goods_sale_enabled(enabled):
    cfg = load_event_config()
    cfg.setdefault('pass_goods_sale', {})['enabled'] = bool(enabled)
    return save_event_config(cfg)


def set_meowfest_enabled(enabled):
    cfg = load_event_config()
    cfg.setdefault('meowfest', {})['enabled'] = bool(enabled)
    return save_event_config(cfg)


def set_chapter3_tour_enabled(enabled):
    cfg = load_event_config()
    cfg.setdefault('chapter3_tour', {})['enabled'] = bool(enabled)
    return save_event_config(cfg)


def set_weather_festival(snow=None, cherry_blossom=None):
    cfg = load_event_config()
    wf = cfg.setdefault('weather_festival', {})
    if snow is not None:
        wf['snow_enabled'] = bool(snow)
    if cherry_blossom is not None:
        wf['cherry_blossom_enabled'] = bool(cherry_blossom)
    return save_event_config(cfg)


def set_fan_art_costume_enabled(enabled):
    cfg = load_event_config()
    cfg.setdefault('fan_art_costume', {})['enabled'] = bool(enabled)
    return save_event_config(cfg)


def set_event_ranking_enabled(enabled):
    cfg = load_event_config()
    cfg.setdefault('event_ranking', {})['enabled'] = bool(enabled)
    return save_event_config(cfg)

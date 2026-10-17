"""Admin Web Dashboard for Guitar Girl Server - Tab-based Management."""
import json
from server import event_manager

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Guitar Girl - Quản lý Sự kiện & Quản Lý Người Chơi</title>
    <style>
        :root {
            --bg-color: #0f111a;
            --card-bg: #181b29;
            --card-border: #262c45;
            --text-main: #f0f3ff;
            --text-sub: #8b9bb4;
            --accent-pink: #ff5e97;
            --accent-cyan: #38ef7d;
            --accent-blue: #4a90e2;
            --accent-purple: #9b51e0;
            --accent-indigo: #6c5ce7;
            --switch-off: #2c324b;
            --switch-on: #38ef7d;
            --danger: #ff4757;
            --warning: #ffa502;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: radial-gradient(circle at 50% 0%, #1a1e36 0%, var(--bg-color) 70%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 20px 12px 60px;
        }
        .container {
            max-width: 1020px;
            margin: 0 auto;
        }
        header {
            text-align: center;
            margin-bottom: 20px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--card-border);
        }
        .logo-title {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            margin-bottom: 6px;
        }
        .logo-icon {
            font-size: 2.2rem;
        }
        h1 {
            font-size: 1.7rem;
            font-weight: 700;
            background: linear-gradient(135deg, #ff8eb6, #6ee7b7);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            color: var(--text-sub);
            font-size: 0.9rem;
        }
        .server-status {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: rgba(56, 239, 125, 0.1);
            color: var(--accent-cyan);
            border: 1px solid rgba(56, 239, 125, 0.3);
            border-radius: 20px;
            padding: 4px 14px;
            font-size: 0.8rem;
            margin-top: 10px;
            font-weight: 600;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            background: var(--accent-cyan);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--accent-cyan);
        }

        
        /* Language Switcher */
        .lang-switch-group {
            display: inline-flex;
            gap: 4px;
            background: rgba(24, 27, 41, 0.95);
            padding: 4px;
            border-radius: 20px;
            border: 1px solid var(--card-border);
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        .lang-btn {
            background: transparent;
            border: none;
            color: var(--text-sub);
            padding: 5px 14px;
            border-radius: 16px;
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .lang-btn:hover {
            color: var(--text-main);
        }
        .lang-btn.active {
            background: linear-gradient(135deg, #ff5e97, #ff8eb6);
            color: #ffffff;
            box-shadow: 0 2px 10px rgba(255, 94, 151, 0.4);
        }

        /* Top Navigation Tabs */
        .nav-tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 22px;
            background: rgba(24, 27, 41, 0.9);
            backdrop-filter: blur(10px);
            padding: 6px;
            border-radius: 14px;
            border: 1px solid var(--card-border);
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }
        .nav-tab {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 12px 18px;
            background: transparent;
            border: none;
            border-radius: 10px;
            color: var(--text-sub);
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.25s ease;
        }
        .nav-tab:hover {
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.05);
        }
        .nav-tab.active {
            background: linear-gradient(135deg, #6c5ce7, #a367dc);
            color: #ffffff;
            box-shadow: 0 4px 14px rgba(108, 92, 231, 0.4);
        }
        .tab-badge {
            background: rgba(0, 0, 0, 0.35);
            color: #fff;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        .nav-tab.active .tab-badge {
            background: rgba(255, 255, 255, 0.25);
        }

        /* Stat Grid for Users */
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 14px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            padding: 16px 18px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            transition: transform 0.2s;
        }
        .stat-card:hover {
            transform: translateY(-2px);
        }
        .stat-card-title {
            font-size: 0.82rem;
            color: var(--text-sub);
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .stat-card-value {
            font-size: 1.6rem;
            font-weight: 700;
            color: var(--text-main);
        }

        /* Toolbar & Search Bar */
        .user-toolbar {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
            margin-bottom: 12px;
        }
        .search-input {
            flex: 2;
            min-width: 220px;
            padding: 10px 14px;
            background: #121524;
            border: 1px solid var(--card-border);
            border-radius: 10px;
            color: #fff;
            font-size: 0.88rem;
            outline: none;
            transition: border-color 0.2s;
        }
        .search-input:focus {
            border-color: #6c5ce7;
            box-shadow: 0 0 8px rgba(108, 92, 231, 0.3);
        }
        .filter-select {
            flex: 1;
            min-width: 150px;
            padding: 10px 14px;
            background: #121524;
            border: 1px solid var(--card-border);
            border-radius: 10px;
            color: #fff;
            font-size: 0.88rem;
            outline: none;
            cursor: pointer;
        }

        /* Buttons & Actions */
        .btn {
            padding: 10px 16px;
            border-radius: 10px;
            border: none;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #ff5e97, #ff2a74);
            color: white;
            box-shadow: 0 4px 14px rgba(255, 94, 151, 0.4);
        }
        .btn-primary:hover {
            opacity: 0.95;
            transform: translateY(-1px);
        }
        .btn-secondary {
            background: #232840;
            color: var(--text-main);
            border: 1px solid var(--card-border);
        }
        .btn-secondary:hover {
            background: #2a314f;
        }
        .btn-setting-event {
            background: linear-gradient(135deg, #6c5ce7, #8e44ad);
            color: white;
            border: none;
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 0.82rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn-setting-event:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(108, 92, 231, 0.4);
        }
        .btn-mail {
            background: rgba(74, 144, 226, 0.15);
            color: #4a90e2;
            border: 1px solid rgba(74, 144, 226, 0.4);
            padding: 6px 10px;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .btn-mail:hover {
            background: #4a90e2;
            color: #fff;
        }
        .btn-ban {
            background: rgba(255, 71, 87, 0.15);
            color: #ff4757;
            border: 1px solid rgba(255, 71, 87, 0.4);
            padding: 6px 10px;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-ban:hover {
            background: #ff4757;
            color: #fff;
        }
        .btn-unban {
            background: rgba(46, 213, 115, 0.15);
            color: #2ed573;
            border: 1px solid rgba(46, 213, 115, 0.4);
            padding: 6px 10px;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-unban:hover {
            background: #2ed573;
            color: #fff;
        }
        .btn-delete-user {
            background: rgba(255, 71, 87, 0.15);
            color: #ff4757;
            border: 1px solid rgba(255, 71, 87, 0.4);
            padding: 6px 10px;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .btn-delete-user:hover {
            background: #ff4757;
            color: #fff;
        }

        /* Copy UUID badge */
        .uuid-pill {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-family: monospace;
            font-size: 0.74rem;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(255, 255, 255, 0.08);
            padding: 2px 6px;
            border-radius: 4px;
            color: var(--text-sub);
            cursor: pointer;
            margin-top: 2px;
        }
        .uuid-pill:hover {
            color: #fff;
            border-color: #6c5ce7;
            background: rgba(108, 92, 231, 0.15);
        }

        /* Action Bar for Events Tab */
        .action-bar {
            position: sticky;
            top: 12px;
            z-index: 100;
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
            background: rgba(24, 27, 41, 0.88);
            backdrop-filter: blur(10px);
            padding: 12px;
            border-radius: 14px;
            border: 1px solid var(--card-border);
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }

        /* Cards */
        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.25);
        }
        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }
        .card-title {
            font-size: 1.15rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .event-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 0;
            border-bottom: 1px solid rgba(255,255,255,0.04);
            gap: 16px;
        }
        .event-item:last-child {
            border-bottom: none;
        }
        .event-info {
            flex: 1;
        }
        .event-name {
            font-weight: 600;
            font-size: 1rem;
            margin-bottom: 4px;
        }
        .event-desc {
            color: var(--text-sub);
            font-size: 0.82rem;
            line-height: 1.4;
        }

        /* Switch */
        .switch {
            position: relative;
            display: inline-block;
            width: 50px;
            height: 28px;
            flex-shrink: 0;
        }
        .switch input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        .slider {
            position: absolute;
            cursor: pointer;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: var(--switch-off);
            transition: .3s;
            border-radius: 28px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .slider:before {
            position: absolute;
            content: "";
            height: 20px;
            width: 20px;
            left: 4px;
            bottom: 3px;
            background-color: white;
            transition: .3s;
            border-radius: 50%;
        }
        input:checked + .slider {
            background-color: var(--switch-on);
            box-shadow: 0 0 12px rgba(56, 239, 125, 0.4);
        }
        input:checked + .slider:before {
            transform: translateX(22px);
        }

        /* Weather Radio Selection */
        .weather-radio-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 13px 16px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            user-select: none;
        }
        .weather-radio-card:hover {
            background: rgba(255, 255, 255, 0.05);
            border-color: rgba(255, 255, 255, 0.18);
            transform: translateY(-1px);
        }
        .weather-radio-card.active {
            background: rgba(108, 92, 231, 0.12);
            border-color: #6c5ce7;
            box-shadow: 0 4px 14px rgba(108, 92, 231, 0.25);
        }

        /* Form elements */
        .form-group {
            margin-top: 14px;
        }
        .form-label {
            display: block;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 6px;
            color: var(--text-sub);
        }
        select {
            width: 100%;
            padding: 10px 14px;
            background: #121524;
            border: 1px solid var(--card-border);
            border-radius: 10px;
            color: var(--text-main);
            font-size: 0.95rem;
            outline: none;
            cursor: pointer;
        }

        /* Toast */
        #toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #1e2337;
            color: white;
            padding: 14px 22px;
            border-radius: 12px;
            border: 1px solid var(--card-border);
            border-left: 4px solid var(--accent-cyan);
            box-shadow: 0 8px 30px rgba(0,0,0,0.5);
            display: none;
            z-index: 9999;
            font-size: 0.9rem;
            animation: slideUp 0.3s ease;
        }
        @keyframes slideUp {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        /* User Table */
        .user-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.86rem;
            text-align: left;
        }
        .user-table th {
            background: rgba(255, 255, 255, 0.03);
            color: var(--text-sub);
            padding: 12px 14px;
            font-weight: 600;
            border-bottom: 1px solid var(--card-border);
            white-space: nowrap;
        }
        .user-table td {
            padding: 12px 14px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            vertical-align: middle;
        }
        .user-table tr:hover {
            background: rgba(255, 255, 255, 0.02);
        }
        .user-badge-gold {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: linear-gradient(135deg, rgba(255, 193, 7, 0.15), rgba(255, 152, 0, 0.25));
            color: #ffc107;
            border: 1px solid rgba(255, 193, 7, 0.4);
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.78rem;
            font-weight: 600;
        }
        .user-badge-free {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-sub);
            border: 1px solid var(--card-border);
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.78rem;
        }
        .user-badge-banned {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: rgba(255, 71, 87, 0.2);
            color: #ff4757;
            border: 1px solid rgba(255, 71, 87, 0.4);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.72rem;
            font-weight: 700;
            margin-left: 6px;
        }

        /* Modals */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(8px);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 16px;
        }
        .modal-overlay.active {
            display: flex;
        }
        .modal-dialog {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            width: 100%;
            max-width: 530px;
            box-shadow: 0 16px 40px rgba(0,0,0,0.6);
            animation: modalPop 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            overflow: hidden;
        }
        @keyframes modalPop {
            from { transform: scale(0.95); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            border-bottom: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.02);
        }
        .modal-header h3 {
            font-size: 1.1rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .modal-close {
            background: transparent;
            border: none;
            color: var(--text-sub);
            font-size: 1.4rem;
            cursor: pointer;
            line-height: 1;
            padding: 4px;
        }
        .modal-close:hover {
            color: #fff;
        }
        .modal-body {
            padding: 20px;
            max-height: 75vh;
            overflow-y: auto;
        }
        .modal-footer {
            display: flex;
            gap: 10px;
            padding: 14px 20px;
            border-top: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.02);
        }

        /* CLI Reference */
        .cli-box {
            background: #0d101a;
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 14px;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
            font-size: 0.8rem;
            color: #a0aec0;
            overflow-x: auto;
            margin-top: 10px;
        }
        .cli-box code { color: #38ef7d; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div style="display: flex; justify-content: flex-end; margin-bottom: 10px;">
                <div class="lang-switch-group">
                    <button type="button" id="lang-btn-vi" class="lang-btn active" onclick="setLanguage('vi')">🇻🇳 Tiếng Việt</button>
                    <button type="button" id="lang-btn-en" class="lang-btn" onclick="setLanguage('en')">🇬🇧 English</button>
                </div>
            </div>
            <div class="logo-title">
                <span class="logo-icon">🎸</span>
                <h1 data-i18n="app_title">Guitar Girl - Trung Tâm Quản Trị</h1>
            </div>
            <div class="server-status" style="display: flex; align-items: center; justify-content: center; gap: 14px; flex-wrap: wrap;">
                <div>
                    <span class="status-dot"></span>
                    <span data-i18n="server_status">Server Trực Tuyến &bull; Zero-Downtime Hot-Reload</span>
                </div>
                <a href="/download" target="_blank" style="text-decoration: none; padding: 5px 14px; border-radius: 20px; background: rgba(255, 94, 151, 0.15); border: 1px solid var(--accent-pink); color: var(--accent-pink); font-size: 0.85rem; font-weight: 600; display: inline-flex; align-items: center; gap: 6px;">
                    <span data-i18n="download_apk">📥 Tải Game APK (458 MB)</span>
                </a>
            </div>
        </header>

        <!-- Top Navigation Tabs -->
        <nav class="nav-tabs">
            <button class="nav-tab active" id="tab-btn-users" onclick="switchTab('users')">
                <span style="font-size: 1.1rem;">👥</span>
                <span data-i18n="tab_users">Quản Lý Toàn Bộ Người Chơi</span>
                <span class="tab-badge" id="tab-users-count">0</span>
            </button>
            <button class="nav-tab" id="tab-btn-events" onclick="switchTab('events')">
                <span style="font-size: 1.1rem;">🎉</span>
                <span data-i18n="tab_events">Cấu Hình Sự Kiện Server</span>
            </button>
        </nav>

        <!-- ================= TAB 1: QUẢN LÝ NGƯỜI CHƠI (ALL USERS) ================= -->
        <div id="tab-users-view">
            <!-- 1. Stats Grid -->
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-card-title" data-i18n="stat_total">👥 Tổng Người Chơi</div>
                    <div class="stat-card-value" id="stat-total-users" style="color: #a29bfe;">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-title" data-i18n="stat_real">📱 Thiết Bị Thật</div>
                    <div class="stat-card-value" id="stat-real-users" style="color: #2ed573;">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-title" data-i18n="stat_test">🧪 Tài Khoản Test Auto</div>
                    <div class="stat-card-value" id="stat-test-users" style="color: #ffa502;">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-title" data-i18n="stat_banned">🚫 Đã Khóa (Banned)</div>
                    <div class="stat-card-value" id="stat-banned-users" style="color: #ff4757;">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-title" data-i18n="stat_gold">⭐ Sở Hữu Gold Pass</div>
                    <div class="stat-card-value" id="stat-gold-users" style="color: #ffd32a;">0</div>
                </div>
            </div>

            <!-- 2. Search & Filter Bar -->
            <div class="card" style="padding: 16px; margin-bottom: 18px;">
                <div class="user-toolbar">
                    <input type="text" id="user-search-input" class="search-input" data-i18n-placeholder="search_placeholder" placeholder="🔍 Tìm kiếm theo Tên, ID, Seq, UUID..." oninput="filterUsers()">
                    <select id="user-status-filter" class="filter-select" onchange="filterUsers()">
                        <option value="all" data-i18n="filter_all">Tất cả người chơi</option>
                        <option value="real" data-i18n="filter_real">📱 Chỉ thiết bị thật (Ẩn test)</option>
                        <option value="test" data-i18n="filter_test">🧪 Chỉ tài khoản test tự động</option>
                        <option value="active" data-i18n="filter_active">🟢 Đang hoạt động (Bình thường)</option>
                        <option value="banned" data-i18n="filter_banned">🚫 Đã bị khóa (BANNED)</option>
                        <option value="gold" data-i18n="filter_gold">⭐ Đã có Thẻ Sao Gold</option>
                        <option value="free" data-i18n="filter_free">⚪ Thẻ Sao Thường (Free)</option>
                    </select>
                    <button class="btn btn-secondary" style="padding: 10px 14px; font-size: 0.88rem; flex: 0 0 auto;" onclick="loadUsers()" data-i18n="btn_refresh">🔄 Làm mới</button>
                    <button class="btn" style="padding: 10px 14px; font-size: 0.88rem; flex: 0 0 auto; background: rgba(255, 71, 87, 0.15); color: #ff6b81; border: 1px solid rgba(255, 71, 87, 0.35);" onclick="cleanupTestUsers()" data-i18n="btn_cleanup_tests" data-i18n-title="cleanup_tests_title" title="Xóa bỏ toàn bộ các tài khoản giả lập tự sinh khi chạy kiểm thử">🧹 Dọn Dẹp Acc Test</button>
                    <button class="btn btn-primary" style="padding: 10px 14px; font-size: 0.88rem; flex: 0 0 auto;" onclick="openSendMailModal()" data-i18n="btn_server_mail">✉️ Gửi Thư Toàn Server</button>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.82rem; color: var(--text-sub); padding: 0 4px;">
                    <div><span data-i18n="showing_prefix">Đang hiển thị</span> <span id="filtered-count" style="color: #fff; font-weight: 700;">0</span> / <span id="total-count" style="color: #fff; font-weight: 700;">0</span> <span data-i18n="showing_suffix">tài khoản</span></div>
                    <div data-i18n="copy_hint">Nhấp vào UUID để sao chép nhanh</div>
                </div>
            </div>

            <!-- 3. Players Table Card -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title" data-i18n="players_list_title">📋 Danh Sách Chi Tiết Toàn Bộ Người Chơi</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)" data-i18n="players_list_sub">Quản lý độc lập từng tài khoản</span>
                </div>
                <div id="users-table-container" style="overflow-x: auto;">
                    <div style="text-align: center; color: var(--text-sub); padding: 24px;">Đang tải danh sách người chơi...</div>
                </div>
            </div>
        </div>

        <!-- ================= TAB 2: CẤU HÌNH SỰ KIỆN (EVENTS) ================= -->
        <div id="tab-events-view" style="display: none;">
            <div class="action-bar" style="flex-wrap: wrap;">
                <button class="btn btn-secondary" onclick="loadConfig()" data-i18n="btn_reload_cfg">🔄 Tải lại cấu hình</button>
                <button class="btn btn-primary" onclick="saveConfig()" data-i18n="btn_save_events">💾 Lưu thay đổi sự kiện</button>
                <div style="width: 100%; display: flex; justify-content: center; margin-top: 4px;">
                    <label style="display:inline-flex; align-items:center; gap:8px; font-size:0.85rem; color:var(--text-sub); cursor:pointer;">
                        <input type="checkbox" id="auto-notify-mail" checked>
                        <span data-i18n="chk_auto_notify">📬 Tự động gửi thư thông báo vào game khi lưu sự kiện</span>
                    </label>
                </div>
            </div>

            <!-- 1. Attendance Events -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title" data-i18n="card_att_title">📅 Sự kiện Điểm danh & Đăng nhập</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">Daily Attendance</span>
                </div>
                <div id="attendance-list">
                    <!-- Injected via JS -->
                </div>
            </div>

            <!-- 2. Star Pass -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title" data-i18n="card_sp_title">⭐ Vé Sao / Star Pass</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)" data-i18n="card_sp_sub">13 Mùa giải</span>
                </div>
                
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name" data-i18n="sp_enable_title">Kích hoạt Thẻ Sao (Star Pass)</div>
                        <div class="event-desc" data-i18n="sp_enable_desc">Bật/tắt thanh tiến trình Star Pass và icon sự kiện ngoài sảnh chính</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="sp-enabled">
                        <span class="slider"></span>
                    </label>
                </div>

                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name" data-i18n="sp_gold_title">Mở khóa Thẻ Sao Gold Trả Phí Toàn Server (Paid Pass)</div>
                        <div class="event-desc" data-i18n="sp_gold_desc">Tặng vé Gold Pass toàn bộ người chơi (Khuyên dùng nút Setting trong Tab Người chơi để cấp riêng)</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="sp-gold">
                        <span class="slider"></span>
                    </label>
                </div>

                <div class="form-group">
                    <label class="form-label" for="sp-season" data-i18n="sp_season_label">Chọn Mùa giải Star Pass hoạt động:</label>
                    <select id="sp-season">
                        <!-- Injected via JS -->
                    </select>
                </div>
            </div>

            <!-- 3. Pass Goods Sale -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title" data-i18n="card_sale_title">🏷️ Cửa hàng Giảm giá Star Pass (Pass Goods Sale)</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">Merch Shop & LIVE SALE</span>
                </div>
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name" id="pgs-name" data-i18n="pgs_name">Cửa hàng Giảm giá Star Pass</div>
                        <div class="event-desc" id="pgs-desc" data-i18n="pgs_desc">Mở biểu tượng nút Sale trên sảnh chính để mua lại toàn bộ Trang phục & Guitar của 13 mùa Star Pass đã qua với giá ưu đãi Socola (50-200 CP)</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="pgs-enabled">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>

            <!-- 4. Meowfest -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title" data-i18n="card_mf_title">🐱 Sự kiện Nuôi Mèo Meowfest (SamSeck)</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">SamSaek Event</span>
                </div>
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name" id="mf-name" data-i18n="mf_name">Sự kiện Nuôi Mèo Meowfest</div>
                        <div class="event-desc" id="mf-desc" data-i18n="mf_desc">Mở khóa 3 cột mốc nuôi mèo Tam Thể nhận Cây cào móng (Guitar 10), Quần yếm (Costume 13), Bé mèo Navi (Unit 1)</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="mf-enabled">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>

            <!-- 5. Chapter 3 Tour -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title" data-i18n="card_c3_title">🏫 Tour Sân khấu Sunshine High School (CH3)</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">Chapter 3 Tour</span>
                </div>
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name" id="c3-name" data-i18n="c3_name">Tour Chapter 3 (Sunshine High School)</div>
                        <div class="event-desc" id="c3-desc" data-i18n="c3_desc">Biểu diễn sân khấu Sunshine High School 20 màn với Năng lượng Cookie / AP</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="c3-enabled">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>

            <!-- 6. Weather Festival -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title" data-i18n="card_wf_title">❄️🌸 Hiệu Ứng Thời Tiết Mùa (Seasonal Weather)</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)" data-i18n="card_wf_sub">Chọn 1 hiệu ứng duy nhất</span>
                </div>
                <div style="font-size:0.85rem; color:var(--text-sub); margin-bottom:14px; line-height:1.4;">
                    Hệ thống chỉ kích hoạt <b>1 hiệu ứng thời tiết duy nhất</b> tại một thời điểm để phân chia rõ ràng, tránh bị chồng đè hạt hiệu ứng lên nhau trong màn chơi:
                </div>
                <div style="display: flex; flex-direction: column; gap: 10px;">
                    <label class="weather-radio-card" id="card-wf-snow" onclick="selectWeatherMode('snow')">
                        <div style="display: flex; align-items: center; gap: 14px;">
                            <input type="radio" name="weather_mode" value="snow" id="wf-mode-snow" style="width: 20px; height: 20px; accent-color: #6c5ce7; cursor: pointer;">
                            <div>
                                <div style="font-weight: 600; color: #fff; font-size: 0.95rem;" data-i18n="wf_snow_title">❄️ Lễ hội Tuyết rơi Mùa đông (Snow Festival)</div>
                                <div style="font-size: 0.8rem; color: var(--text-sub); margin-top: 3px;" data-i18n="wf_snow_desc">Kích hoạt các hạt bông tuyết trắng rơi lãng mạn ngoài khung cửa sổ phòng & sảnh chính</div>
                            </div>
                        </div>
                        <span style="background: rgba(116, 185, 255, 0.15); color: #74b9ff; padding: 4px 10px; border-radius: 8px; font-size: 0.75rem; font-weight:600;" data-i18n="wf_snow_tag">Mùa đông</span>
                    </label>

                    <label class="weather-radio-card" id="card-wf-cherry" onclick="selectWeatherMode('cherry')">
                        <div style="display: flex; align-items: center; gap: 14px;">
                            <input type="radio" name="weather_mode" value="cherry" id="wf-mode-cherry" style="width: 20px; height: 20px; accent-color: #ff5e97; cursor: pointer;">
                            <div>
                                <div style="font-weight: 600; color: #fff; font-size: 0.95rem;" data-i18n="wf_cherry_title">🌸 Hẹn hò Mùa Hoa Anh Đào (Cherry Blossom Date)</div>
                                <div style="font-size: 0.8rem; color: var(--text-sub); margin-top: 3px;" data-i18n="wf_cherry_desc">Kích hoạt những cánh hoa anh đào màu hồng bay bay trong không gian mùa xuân</div>
                            </div>
                        </div>
                        <span style="background: rgba(255, 118, 117, 0.15); color: #ff7675; padding: 4px 10px; border-radius: 8px; font-size: 0.75rem; font-weight:600;" data-i18n="wf_cherry_tag">Mùa xuân</span>
                    </label>

                    <label class="weather-radio-card" id="card-wf-none" onclick="selectWeatherMode('none')">
                        <div style="display: flex; align-items: center; gap: 14px;">
                            <input type="radio" name="weather_mode" value="none" id="wf-mode-none" style="width: 20px; height: 20px; accent-color: #a4b0be; cursor: pointer;">
                            <div>
                                <div style="font-weight: 600; color: #fff; font-size: 0.95rem;" data-i18n="wf_none_title">🚫 Tắt toàn bộ hiệu ứng thời tiết</div>
                                <div style="font-size: 0.8rem; color: var(--text-sub); margin-top: 3px;" data-i18n="wf_none_desc">Trở về không gian ban đầu mặc định của trò chơi, không có hạt thời tiết rơi</div>
                            </div>
                        </div>
                        <span style="background: rgba(255, 255, 255, 0.08); color: var(--text-sub); padding: 4px 10px; border-radius: 8px; font-size: 0.75rem; font-weight:600;" data-i18n="wf_none_tag">Mặc định</span>
                    </label>
                </div>

                <div style="margin-top: 12px; padding: 10px 14px; background: rgba(255, 118, 117, 0.08); border-left: 3px solid #ff7675; border-radius: 6px; font-size: 0.8rem; color: #fab1a0; line-height: 1.45;">
                    💡 <b>Lưu ý về Mùa hoa anh đào:</b> Theo thiết kế đồ họa gốc của nhà sản xuất game, hiệu ứng <b>Cánh hoa anh đào rơi</b> chỉ xuất hiện tại cảnh <b>Chapter 2 (Phố Hongdae / Tiệm bánh)</b>; trong khi hiệu ứng <b>Tuyết rơi</b> xuất hiện ở cả Chapter 1 & Chapter 2. Nếu tài khoản chưa mở Chapter 2, hãy sang tab <b>👥 Quản Lý Người Chơi &gt; ⚙️ Setting &gt; Bật "Mở khóa Chapter 2"</b> để test ngay!
                </div>
            </div>

            <!-- 7. Fan Art Costume -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title" data-i18n="card_fac_title">🎨 Trang phục Bản giới hạn Fan Art 2021</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">Fan Art Grand Prize</span>
                </div>
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name" id="fac-name" data-i18n="fac_name">Trang phục Thiết kế Fan Art</div>
                        <div class="event-desc" id="fac-desc" data-i18n="fac_desc">Kích hoạt bộ trang phục Nàng tiên mùa xuân (Spring Fairy) và Guitar Giai điệu nàng tiên (Fairy's Melody)</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="fac-enabled">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>

            <!-- 8. Event Ranking -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title" data-i18n="card_er_title">🏆 Đua Top Xếp Hạng Sự Kiện (Event Ranking)</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">Live Leaderboard</span>
                </div>
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name" id="er-name" data-i18n="er_name">Bảng Xếp Hạng Đua Top Sự Kiện</div>
                        <div class="event-desc" id="er-desc" data-i18n="er_desc">Kích hoạt tính năng đua top điểm sự kiện trực tiếp với bảng xếp hạng Top 100 cao thủ</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="er-enabled">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>

            <!-- 9. Live In-Game Push & Mailbox -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title" data-i18n="card_mail_title">📬 Gửi Thư & Tặng Quà Toàn Server (Broadcast Mail)</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)" data-i18n="card_mail_sub">Đồng bộ tức thì không cần out game</span>
                </div>
                <p style="font-size:0.85rem; color:var(--text-sub); margin-bottom: 12px;">
                    Gửi thư thông báo và tặng tài nguyên trực tiếp vào Hộp thư in-game của toàn bộ người chơi. Client đang chơi game sẽ tự động hiện dấu chấm đỏ (Red Dot) lập tức mà không cần thoát game!
                </p>
                <div class="form-group" style="margin-bottom: 10px;">
                    <label class="form-label">Tiêu đề thư:</label>
                    <input type="text" id="mail-title" value="Quà tặng Sự kiện Hệ thống" style="width:100%; padding:8px 12px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                </div>
                <div class="form-group" style="margin-bottom: 10px;">
                    <label class="form-label">Nội dung thư:</label>
                    <input type="text" id="mail-memo" value="Chúc bạn chơi game vui vẻ! Hãy nhận quà tặng đặc biệt từ hệ thống nhé." style="width:100%; padding:8px 12px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                </div>
                <div style="display:flex; gap:10px; margin-bottom: 14px;">
                    <div style="flex:1;">
                        <label class="form-label">Socola (CP):</label>
                        <input type="number" id="mail-cp" value="500" style="width:100%; padding:8px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                    </div>
                    <div style="flex:1;">
                        <label class="form-label">Kẹo (Candy):</label>
                        <input type="number" id="mail-candy" value="100" style="width:100%; padding:8px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                    </div>
                    <div style="flex:1;">
                        <label class="form-label">Bánh quy (AP):</label>
                        <input type="number" id="mail-cookies" value="50" style="width:100%; padding:8px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                    </div>
                </div>
                <button class="btn btn-primary" style="width:100%; padding:10px;" onclick="sendDirectMail()" data-i18n="btn_send_broadcast">🚀 Gửi Thư & Quà Tới Toàn Server</button>
            </div>

            <!-- CLI Guide Card -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title" data-i18n="card_cli_title">💻 Lệnh điều khiển Terminal (CLI)</div>
                </div>
                <p style="font-size:0.85rem; color:var(--text-sub)" data-i18n="cli_sub">Bạn cũng có thể điều khiển trực tiếp trên terminal server bằng lệnh:</p>
                <div class="cli-box">
                    ./emulator/eventctl.sh list<br>
                    ./emulator/eventctl.sh enable 3 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# Bật điểm danh CH2<br>
                    ./emulator/eventctl.sh season 13 &nbsp;&nbsp;&nbsp;# Đặt Star Pass Mùa 13<br>
                    ./emulator/eventctl.sh enable sale &nbsp;&nbsp;# Bật Giảm giá Star Pass<br>
                    ./emulator/eventctl.sh enable snow &nbsp;&nbsp;# Bật Tuyết rơi mùa đông<br>
                    ./emulator/eventctl.sh enable cherry # Bật Hoa anh đào rơi
                </div>
            </div>
        </div>
    </div>

    <!-- ================= MODAL: CÀI ĐẶT CÁ NHÂN NGƯỜI CHƠI ================= -->
    <div class="modal-overlay" id="user-event-modal">
        <div class="modal-dialog">
            <div class="modal-header">
                <h3 data-i18n="modal_user_title">⚙️ Cài Đặt Cá Nhân Người Chơi</h3>
                <button class="modal-close" onclick="closeUserModal()">&times;</button>
            </div>
            <div class="modal-body">
                <input type="hidden" id="modal-uuid">
                <input type="hidden" id="modal-useq">
                
                <div style="margin-bottom: 14px; background: rgba(255,255,255,0.03); padding: 12px; border-radius: 10px; border: 1px solid var(--card-border);">
                    <div id="modal-user-name" style="font-weight: 700; font-size: 1.1rem; color: #fff;"></div>
                    <div id="modal-user-sub" style="font-size: 0.76rem; color: var(--text-sub); margin-top: 2px;"></div>
                    <div id="modal-user-lastlogin" style="font-size: 0.8rem; color: var(--accent-cyan); margin-top: 4px;"></div>
                </div>

                <!-- 0. Ban Switch -->
                <div class="event-item" style="padding: 10px 0; margin-bottom: 12px; background: rgba(255, 71, 87, 0.08); padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(255, 71, 87, 0.25);">
                    <div class="event-info">
                        <div class="event-name" style="color: #ff6b81;" data-i18n="modal_ban_title">🚫 Khóa Tài Khoản (Ban Player)</div>
                        <div class="event-desc" data-i18n="modal_ban_desc">Khóa tài khoản người chơi. Game sẽ hiện thông báo "Tài khoản đã bị KHÓA" thay vì lỗi mạng.</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="modal-is-banned">
                        <span class="slider"></span>
                    </label>
                </div>

                <!-- 1. Star Pass Toggle -->
                <div id="modal-sp-disabled-notice" style="display:none; margin-bottom:12px; padding:10px 14px; background:rgba(235, 77, 75, 0.12); border:1px solid rgba(235, 77, 75, 0.4); border-radius:8px; font-size:0.8rem; color:#ff7675; line-height:1.45;">
                    ⚠️ <b>Thẻ Sao (Star Pass) hiện đang TẮT trong Cài Đặt Sự Kiện.</b><br>
                    Không thể chỉnh vé Thẻ Sao Gold hoặc Điểm Thẻ Sao cho người chơi (cần kích hoạt Thẻ Sao trong tab Sự Kiện trước để tránh lỗi dữ liệu game).
                </div>

                <div class="event-item" id="modal-sp-group" style="padding: 10px 0;">
                    <div class="event-info">
                        <div class="event-name" data-i18n="modal_sp_gold_title">⭐ Thẻ Sao Gold Trả Phí (Paid Pass)</div>
                        <div class="event-desc" data-i18n="modal_sp_gold_desc">Mở khóa vé Thẻ Sao Gold riêng cho tài khoản người chơi này</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="modal-is-gold">
                        <span class="slider"></span>
                    </label>
                </div>

                <!-- 2. Star Pass Points -->
                <div class="form-group" id="modal-sp-point-group" style="margin-top:10px; padding-top:10px;">
                    <label class="form-label" data-i18n="modal_sp_points_lbl">Điểm Thẻ Sao (Star Points):</label>
                    <input type="number" id="modal-star-point" min="0" style="width:100%; padding:9px 12px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                    <div style="font-size:0.75rem; color:var(--text-sub); margin-top:4px;" data-i18n="modal_sp_points_sub">Cập nhật điểm để nhận quà các cấp độ mốc sao (Tự động tính level quà tương ứng).</div>
                </div>

                <!-- 3. Currencies (Tim/Likes, Socola/CP, Kẹo/Candy) -->
                <div style="margin-top:14px; padding-top:12px; border-top:1px solid rgba(255,255,255,0.06);">
                    <div style="font-weight:600; font-size:0.9rem; color:#fff; margin-bottom:8px;" data-i18n="modal_curr_title">💰 Tài Nguyên (Tim, Socola, Kẹo)</div>
                    <div style="display:flex; gap:10px; margin-bottom:10px;">
                        <div style="flex:1;">
                            <label class="form-label" data-i18n="modal_add_likes">Thêm Tim (Likes):</label>
                            <input type="text" id="modal-add-like" value="0" placeholder="vd: 1000, 10A, 42.877G..." oninput="updateLikePreviews()" style="width:100%; padding:9px 12px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                            <div id="modal-add-like-preview" style="font-size:0.75rem; color:#ff6b81; margin-top:3px; min-height:16px;"></div>
                        </div>
                        <div style="flex:1;">
                            <label class="form-label" data-i18n="modal_add_cp">Thêm Socola (CP):</label>
                            <input type="number" id="modal-add-cp" value="0" style="width:100%; padding:9px 12px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                        </div>
                        <div style="flex:1;">
                            <label class="form-label" data-i18n="modal_add_candy">Thêm Kẹo (Candy):</label>
                            <input type="number" id="modal-add-candy" value="0" style="width:100%; padding:9px 12px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                        </div>
                    </div>
                    <div>
                        <label class="form-label" style="display:flex; justify-content:space-between;">
                            <span data-i18n="modal_set_likes">❤️ Đặt chính xác số Tim (Hỗ trợ đơn vị game: 42.877G, 100H, 10AA...):</span>
                            <span id="modal-user-like" style="color:#ff6b81; font-weight:600;">Hiện có: 0</span>
                        </label>
                        <input type="text" id="modal-set-like" oninput="updateLikePreviews()" placeholder="Nhập số Tim (ví dụ: 1000, 42.877G, 100H, 10AA)..." style="width:100%; padding:9px 12px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                        <div id="modal-set-like-preview" style="font-size:0.78rem; color:#ff6b81; margin-top:3px; min-height:18px;"></div>
                    </div>
                </div>

                <!-- 4. TÙY CHỈNH ĐIỂM DANH SỰ KIỆN (COMPACT & HỖ TRỢ TẤT CẢ SỰ KIỆN) -->
                <div style="margin-top:14px; padding:14px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.08); border-radius:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span style="font-weight:600; font-size:0.9rem; color:#fff; display:inline-flex; align-items:center; gap:6px;">
                            <span data-i18n="modal_att_title">📅 Tùy Chỉnh Điểm Danh Sự Kiện</span>
                        </span>
                        <span id="modal-att-status" style="font-size:0.8rem; color:#a29bfe; font-weight:600; background:rgba(162,155,254,0.15); padding:2px 8px; border-radius:6px;"></span>
                    </div>

                    <div style="display:grid; grid-template-columns: 1.2fr 1fr; gap:10px; margin-bottom:10px;">
                        <div>
                            <label class="form-label" style="font-size:0.78rem; color:var(--text-sub); margin-bottom:4px;" data-i18n="modal_att_target">Sự kiện muốn chỉnh:</label>
                            <select id="modal-att-event-select" onchange="onModalAttEventChange()" style="width:100%; padding:8px 10px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px; font-size:0.85rem;">
                                <option value="1">📅 Tân thủ 7 ngày (Event 1)</option>
                                <option value="3">🏪 Cửa hàng tiện lợi (CH2 - Event 3)</option>
                                <option value="202110">🎃 Halloween 14 ngày (Event 202110)</option>
                                <option value="202111">🎁 Chọn quà Tân thủ (Event 202111)</option>
                                <option value="2">🎂 Kỷ niệm 1 năm (14 ngày - Event 2)</option>
                            </select>
                        </div>
                        <div>
                            <label class="form-label" style="font-size:0.78rem; color:var(--text-sub); margin-bottom:4px;" data-i18n="modal_att_day_lbl">Mốc ngày đặt:</label>
                            <select id="modal-att-day" onchange="onModalAttDayChange()" style="width:100%; padding:8px 10px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px; font-size:0.85rem;">
                            </select>
                        </div>
                    </div>

                    <div style="display:flex; flex-direction:column; gap:8px;">
                        <label style="display:inline-flex; align-items:center; gap:8px; font-size:0.82rem; color:var(--text-sub); cursor:pointer;">
                            <input type="checkbox" id="modal-att-unlock" onchange="onModalAttUnlockChange()" checked>
                            <span data-i18n="modal_att_unlock_lbl">🔓 Mở khóa nhận quà ngay hôm nay (Xóa giới hạn chờ 24h)</span>
                        </label>
                        <label style="display:inline-flex; align-items:center; gap:8px; font-size:0.82rem; color:#f5cd79; cursor:pointer;">
                            <input type="checkbox" id="modal-att-direct-grant" onchange="onModalAttGrantChange()">
                            <span id="modal-att-grant-label" data-i18n="modal_att_grant_lbl">🎁 Nhận ngay trọn bộ quà sự kiện này vào tài khoản</span>
                        </label>
                    </div>
                </div>

                <!-- 4.5 MỞ KHÓA CHAPTER 2 (NHÃN NGUY HIỂM / CHỈ BẬT KHI TEST) -->
                <div style="margin-top:14px; padding:12px; background:rgba(235, 77, 75, 0.08); border:1px solid rgba(235, 77, 75, 0.35); border-radius:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <span style="font-weight:700; font-size:0.88rem; color:#ff6b6b; display:inline-flex; align-items:center; gap:6px;">
                            <span data-i18n="modal_ch2_title">⚠️ Mở khóa Ch2: Tiệm bánh Hạnh phúc</span>
                        </span>
                        <span class="badge" style="background:#eb4d4b; color:#fff; font-size:0.68rem; padding:2px 8px; border-radius:4px; font-weight:700;"><span data-i18n="modal_ch2_badge">NGUY HIỂM / TEST</span></span>
                    </div>
                    <div style="font-size:0.77rem; color:#ccc; margin-bottom:8px; line-height:1.45;">
                        Tự động nâng <b>Độ nổi tiếng Khu vực 1 lên cấp 4</b> và <b>Tiệm bánh Hạnh phúc (Follower 12) lên cấp 15</b> để vượt qua điều kiện gốc, lập tức mở bản đồ Chapter 2 (Hongdae) để test sự kiện & hiệu ứng hoa anh đào.
                    </div>
                    <label style="display:inline-flex; align-items:center; gap:8px; font-size:0.84rem; color:#ff7675; cursor:pointer; font-weight:600;">
                        <input type="checkbox" id="modal-unlock-ch2" style="width:17px; height:17px; accent-color:#eb4d4b;">
                        <span data-i18n="modal_ch2_enable">🔓 Bật Mở Khóa Chapter 2 Ngay Cho Người Chơi Này</span>
                    </label>
                </div>

                <!-- 5. Mail notice toggle -->
                <div style="margin-top:14px; padding-top:12px; border-top:1px solid rgba(255,255,255,0.06);">
                    <label style="display:inline-flex; align-items:center; gap:8px; font-size:0.85rem; color:var(--text-sub); cursor:pointer;">
                        <input type="checkbox" id="modal-send-mail">
                        <span data-i18n="modal_sendmail_chk">📬 Gửi kèm thư thông báo vào Hòm thư in-game của người chơi</span>
                    </label>
                </div>
            </div>
            <div class="modal-footer" style="flex-wrap: wrap;">
                <button type="button" class="btn btn-secondary" onclick="closeUserModal()" style="flex:1;" data-i18n="btn_cancel">Hủy</button>
                <button type="button" class="btn btn-primary" onclick="saveUserModal()" style="flex:1;" data-i18n="btn_save_user">💾 Lưu Cài Đặt Riêng</button>
                <button type="button" class="btn btn-delete-user" onclick="deleteCurrentModalUser()" style="width:100%; margin-top:8px; padding:10px;" data-i18n="btn_delete_user">
                    🗑️ Xóa Toàn Bộ Dữ Liệu Tài Khoản Này (Reset Sạch Về Đầu)
                </button>
            </div>
        </div>
    </div>

    <!-- ================= MODAL: GỬI THƯ & QUÀ RIÊNG CHO NGƯỜI CHƠI ================= -->
    <div class="modal-overlay" id="mail-modal">
        <div class="modal-dialog">
            <div class="modal-header">
                <h3 id="mail-modal-title">✉️ Gửi Thư & Quà Riêng Cho Người Chơi</h3>
                <button class="modal-close" onclick="closeMailModal()">&times;</button>
            </div>
            <div class="modal-body">
                <input type="hidden" id="modal-mail-uuid">
                <div id="modal-mail-target-info" style="margin-bottom: 14px; padding: 10px 14px; background: rgba(108, 92, 231, 0.12); border: 1px solid rgba(108, 92, 231, 0.3); border-radius: 8px; font-size: 0.85rem; color: #a29bfe; font-weight: 600;"></div>
                
                <div class="form-group" style="margin-bottom: 10px;">
                    <label class="form-label">Tiêu đề thư:</label>
                    <input type="text" id="modal-mail-title" value="Quà Tặng Từ Quản Trị Viên" style="width:100%; padding:9px 12px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                </div>
                <div class="form-group" style="margin-bottom: 12px;">
                    <label class="form-label">Nội dung thư:</label>
                    <input type="text" id="modal-mail-memo" value="Chúc bạn chơi game Guitar Girl thật vui vẻ! Hãy nhận phần quà này nhé." style="width:100%; padding:9px 12px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                </div>
                <div style="display:flex; gap:10px; margin-bottom: 14px;">
                    <div style="flex:1;">
                        <label class="form-label">🍫 Socola (CP):</label>
                        <input type="number" id="modal-mail-cp" value="500" style="width:100%; padding:9px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                    </div>
                    <div style="flex:1;">
                        <label class="form-label">🍬 Kẹo (Candy):</label>
                        <input type="number" id="modal-mail-candy" value="100" style="width:100%; padding:9px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                    </div>
                    <div style="flex:1;">
                        <label class="form-label">🍪 Bánh quy (AP):</label>
                        <input type="number" id="modal-mail-cookies" value="50" style="width:100%; padding:9px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeMailModal()" style="flex:1;" data-i18n="btn_cancel">Hủy</button>
                <button type="button" class="btn btn-primary" onclick="sendModalMail()" style="flex:1;" data-i18n="btn_send_now">🚀 Gửi Ngay Vào Game</button>
            </div>
        </div>
    </div>

    <div id="toast"></div>

    <script>
        const I18N = {
            vi: {
                app_title: "Guitar Girl - Trung Tâm Quản Trị",
                server_status: "Server Trực Tuyến &bull; Zero-Downtime Hot-Reload",
                download_apk: "📥 Tải Game APK (458 MB)",
                tab_users: "Quản Lý Toàn Bộ Người Chơi",
                tab_events: "Cấu Hình Sự Kiện Server",
                stat_total: "👥 Tổng Người Chơi",
                stat_real: "📱 Thiết Bị Thật",
                stat_test: "🧪 Tài Khoản Test Auto",
                stat_banned: "🚫 Đã Khóa (Banned)",
                stat_gold: "⭐ Sở Hữu Gold Pass",
                search_placeholder: "🔍 Tìm kiếm theo Tên, ID, Seq, UUID...",
                filter_all: "Tất cả người chơi",
                filter_real: "📱 Chỉ thiết bị thật (Ẩn test)",
                filter_test: "🧪 Chỉ tài khoản test tự động",
                filter_active: "🟢 Đang hoạt động (Bình thường)",
                filter_banned: "🚫 Đã bị khóa (BANNED)",
                filter_gold: "⭐ Đã có Thẻ Sao Gold",
                filter_free: "⚪ Thẻ Sao Thường (Free)",
                btn_refresh: "🔄 Làm mới",
                btn_cleanup_tests: "🧹 Dọn Dẹp Acc Test",
                cleanup_tests_title: "Xóa bỏ toàn bộ các tài khoản giả lập tự sinh khi chạy kiểm thử",
                btn_server_mail: "✉️ Gửi Thư Toàn Server",
                showing_prefix: "Đang hiển thị",
                showing_suffix: "tài khoản",
                copy_hint: "Nhấp vào UUID để sao chép nhanh",
                players_list_title: "📋 Danh Sách Chi Tiết Toàn Bộ Người Chơi",
                players_list_sub: "Quản lý độc lập từng tài khoản",
                empty_users_filter: "Không tìm thấy người chơi nào phù hợp với bộ lọc.<br><span style='font-size:0.8rem; margin-top:4px; display:inline-block;'>Hãy thử xóa bộ lọc hoặc kiểm tra lại từ khóa tìm kiếm.</span>",
                th_player: "Người Chơi",
                th_last_login: "Đăng Nhập Gần Nhất",
                th_resources: "Tài Nguyên",
                th_attendance: "Sự Kiện Điểm Danh",
                th_starpass: "Thẻ Sao",
                th_actions: "Thao Tác",
                badge_banned: "🚫 BANNED",
                badge_test: "🧪 Test Auto",
                badge_real: "📱 Máy Thật",
                badge_gold: "⭐ Gold Pass",
                badge_free: "⚪ Free Pass",
                badge_disabled: "⚪ Đang tắt",
                lbl_newbie: "📅 Tân Thủ",
                lbl_bakery: "🏪 Tiện Lợi",
                lbl_ch2_opened: "🔓 CH2: Đã mở",
                lbl_ch2_locked: "🔒 CH2: Chưa mở",
                currency_tim: "Tim",
                lbl_pts: "điểm",
                lbl_tier: "Cấp",
                btn_mail: "Thư",
                btn_unban: "Mở",
                btn_ban: "Ban",
                btn_delete: "Xóa",
                btn_reload_cfg: "🔄 Tải lại cấu hình",
                btn_save_events: "💾 Lưu thay đổi sự kiện",
                chk_auto_notify: "📬 Tự động gửi thư thông báo vào game khi lưu sự kiện",
                card_att_title: "📅 Sự kiện Điểm danh & Đăng nhập",
                card_sp_title: "⭐ Vé Sao / Star Pass",
                card_sp_sub: "13 Mùa giải",
                sp_enable_title: "Kích hoạt Thẻ Sao (Star Pass)",
                sp_enable_desc: "Bật/tắt thanh tiến trình Star Pass và icon sự kiện ngoài sảnh chính",
                sp_gold_title: "Mở khóa Thẻ Sao Gold Trả Phí Toàn Server (Paid Pass)",
                sp_gold_desc: "Tặng vé Gold Pass toàn bộ người chơi (Khuyên dùng nút Setting trong Tab Người chơi để cấp riêng)",
                sp_season_label: "Chọn Mùa giải Star Pass hoạt động:",
                card_sale_title: "🏷️ Cửa hàng Giảm giá Star Pass (Pass Goods Sale)",
                pgs_name: "Cửa hàng Giảm giá Star Pass",
                pgs_desc: "Mở biểu tượng nút Sale trên sảnh chính để mua lại toàn bộ Trang phục & Guitar của 13 mùa Star Pass đã qua với giá ưu đãi Socola (50-200 CP)",
                card_mf_title: "🐱 Sự kiện Nuôi Mèo Meowfest (SamSeck)",
                mf_name: "Sự kiện Nuôi Mèo Meowfest",
                mf_desc: "Mở khóa 3 cột mốc nuôi mèo Tam Thể nhận Cây cào móng (Guitar 10), Quần yếm (Costume 13), Bé mèo Navi (Unit 1)",
                card_c3_title: "🏫 Tour Sân khấu Sunshine High School (CH3)",
                c3_name: "Tour Chapter 3 (Sunshine High School)",
                c3_desc: "Biểu diễn sân khấu Sunshine High School 20 màn với Năng lượng Cookie / AP",
                card_wf_title: "❄️🌸 Hiệu Ứng Thời Tiết Mùa (Seasonal Weather)",
                card_wf_sub: "Chọn 1 hiệu ứng duy nhất",
                wf_desc: "Hệ thống chỉ kích hoạt <b>1 hiệu ứng thời tiết duy nhất</b> tại một thời điểm để phân chia rõ ràng, tránh bị chồng đè hạt hiệu ứng lên nhau trong màn chơi:",
                wf_snow_title: "❄️ Lễ hội Tuyết rơi Mùa đông (Snow Festival)",
                wf_snow_desc: "Kích hoạt các hạt bông tuyết trắng rơi lãng mạn ngoài khung cửa sổ phòng & sảnh chính",
                wf_snow_tag: "Mùa đông",
                wf_cherry_title: "🌸 Hẹn hò Mùa Hoa Anh Đào (Cherry Blossom Date)",
                wf_cherry_desc: "Kích hoạt những cánh hoa anh đào màu hồng bay bay trong không gian mùa xuân",
                wf_cherry_tag: "Mùa xuân",
                wf_none_title: "🚫 Tắt toàn bộ hiệu ứng thời tiết",
                wf_none_desc: "Trở về không gian ban đầu mặc định của trò chơi, không có hạt thời tiết rơi",
                wf_none_tag: "Mặc định",
                card_fac_title: "🎨 Trang phục Bản giới hạn Fan Art 2021",
                fac_name: "Trang phục Thiết kế Fan Art",
                fac_desc: "Kích hoạt bộ trang phục Nàng tiên mùa xuân (Spring Fairy) và Guitar Giai điệu nàng tiên (Fairy's Melody)",
                card_er_title: "🏆 Đua Top Xếp Hạng Sự Kiện (Event Ranking)",
                er_name: "Bảng Xếp Hạng Đua Top Sự Kiện",
                er_desc: "Kích hoạt tính năng đua top điểm sự kiện trực tiếp với bảng xếp hạng Top 100 cao thủ",
                card_mail_title: "📬 Gửi Thư & Tặng Quà Toàn Server (Broadcast Mail)",
                card_mail_sub: "Đồng bộ tức thì không cần out game",
                btn_send_broadcast: "🚀 Gửi Thư & Quà Tới Toàn Server",
                card_cli_title: "💻 Lệnh điều khiển Terminal (CLI)",
                cli_sub: "Bạn cũng có thể điều khiển trực tiếp trên terminal server bằng lệnh:",
                modal_user_title: "⚙️ Cài Đặt Cá Nhân Người Chơi",
                modal_ban_title: "🚫 Khóa Tài Khoản (Ban Player)",
                modal_ban_desc: "Khóa tài khoản người chơi. Game sẽ hiện thông báo 'Tài khoản đã bị KHÓA' thay vì lỗi mạng.",
                modal_sp_gold_title: "⭐ Thẻ Sao Gold Trả Phí (Paid Pass)",
                modal_sp_gold_desc: "Mở khóa vé Thẻ Sao Gold riêng cho tài khoản người chơi này",
                modal_sp_points_lbl: "Điểm Thẻ Sao (Star Points):",
                modal_sp_points_sub: "Cập nhật điểm để nhận quà các cấp độ mốc sao (Tự động tính level quà tương ứng).",
                modal_curr_title: "💰 Tài Nguyên (Tim, Socola, Kẹo)",
                modal_add_likes: "Thêm Tim (Likes):",
                modal_add_cp: "Thêm Socola (CP):",
                modal_add_candy: "Thêm Kẹo (Candy):",
                modal_set_likes: "❤️ Đặt chính xác số Tim (Hỗ trợ đơn vị game: 42.877G, 100H, 10AA...):",
                modal_att_title: "📅 Tùy Chỉnh Điểm Danh Sự Kiện",
                modal_att_target: "Sự kiện muốn chỉnh:",
                modal_att_day_lbl: "Mốc ngày đặt:",
                modal_att_unlock_lbl: "🔓 Mở khóa nhận quà ngay hôm nay (Xóa giới hạn chờ 24h)",
                modal_att_grant_lbl: "🎁 Nhận ngay trọn bộ quà sự kiện này vào tài khoản",
                modal_ch2_title: "⚠️ Mở khóa Ch2: Tiệm bánh Hạnh phúc",
                modal_ch2_badge: "NGUY HIỂM / TEST",
                modal_ch2_enable: "🔓 Bật Mở Khóa Chapter 2 Ngay Cho Người Chơi Này",
                modal_sendmail_chk: "📬 Gửi kèm thư thông báo vào Hòm thư in-game của người chơi",
                btn_cancel: "Hủy",
                btn_save_user: "💾 Lưu Cài Đặt Riêng",
                btn_delete_user: "🗑️ Xóa Toàn Bộ Dữ Liệu Tài Khoản Này (Reset Sạch Về Đầu)",
                btn_send_now: "🚀 Gửi Ngay Vào Game"
            },
            en: {
                app_title: "Guitar Girl - Admin Dashboard",
                server_status: "Server Online &bull; Zero-Downtime Hot-Reload",
                download_apk: "📥 Download Game APK (458 MB)",
                tab_users: "Player Management",
                tab_events: "Server Event Configuration",
                stat_total: "👥 Total Players",
                stat_real: "📱 Real Devices",
                stat_test: "🧪 Auto Test Accounts",
                stat_banned: "🚫 Banned Accounts",
                stat_gold: "⭐ Gold Pass Holders",
                search_placeholder: "🔍 Search by Name, ID, Seq, UUID...",
                filter_all: "All Players",
                filter_real: "📱 Real Devices Only (Hide Tests)",
                filter_test: "🧪 Auto Test Accounts Only",
                filter_active: "🟢 Active (Normal)",
                filter_banned: "🚫 Banned Accounts",
                filter_gold: "⭐ Gold Star Pass Holders",
                filter_free: "⚪ Free Star Pass",
                btn_refresh: "🔄 Refresh",
                btn_cleanup_tests: "🧹 Clean Test Accs",
                cleanup_tests_title: "Delete all auto-generated test accounts from automated test suites",
                btn_server_mail: "✉️ Server Mail",
                showing_prefix: "Showing",
                showing_suffix: "accounts",
                copy_hint: "Click UUID to quick copy",
                players_list_title: "📋 Detailed Player List",
                players_list_sub: "Manage each account individually",
                empty_users_filter: "No players found matching your filter.<br><span style='font-size:0.8rem; margin-top:4px; display:inline-block;'>Try clearing filters or search keywords.</span>",
                th_player: "Player",
                th_last_login: "Last Login",
                th_resources: "Resources",
                th_attendance: "Attendance Events",
                th_starpass: "Star Pass",
                th_actions: "Actions",
                badge_banned: "🚫 BANNED",
                badge_test: "🧪 Test Auto",
                badge_real: "📱 Real Device",
                badge_gold: "⭐ Gold Pass",
                badge_free: "⚪ Free Pass",
                badge_disabled: "⚪ Disabled",
                lbl_newbie: "📅 Newbie",
                lbl_bakery: "🏪 Bakery",
                lbl_ch2_opened: "🔓 CH2: Unlocked",
                lbl_ch2_locked: "🔒 CH2: Locked",
                currency_tim: "Likes",
                lbl_pts: "pts",
                lbl_tier: "Tier",
                btn_mail: "Mail",
                btn_unban: "Unban",
                btn_ban: "Ban",
                btn_delete: "Delete",
                btn_reload_cfg: "🔄 Reload Config",
                btn_save_events: "💾 Save Changes",
                chk_auto_notify: "📬 Send notification mail in-game when saving",
                card_att_title: "📅 Attendance & Login Events",
                card_sp_title: "⭐ Star Pass",
                card_sp_sub: "13 Seasons",
                sp_enable_title: "Enable Star Pass",
                sp_enable_desc: "Toggle Star Pass progress bar and lobby event icon",
                sp_gold_title: "Unlock Paid Gold Pass Server-Wide",
                sp_gold_desc: "Grant Gold Pass to all players (Recommended to use Setting button in Players tab for individuals)",
                sp_season_label: "Select Active Star Pass Season:",
                card_sale_title: "🏷️ Pass Goods Sale",
                pgs_name: "Pass Goods Sale",
                pgs_desc: "Open Sale icon on main lobby to rebuy Costumes & Guitars from past 13 Star Pass seasons at discounted CP prices (50-200 CP)",
                card_mf_title: "🐱 Meowfest Event (SamSeck)",
                mf_name: "Meowfest Raising Cat Event",
                mf_desc: "Unlock 3 Calico cat raising milestones for Scratching Post (Guitar 10), Overalls (Costume 13), Navi Cat (Unit 1)",
                card_c3_title: "🏫 Sunshine High School Tour (CH3)",
                c3_name: "Chapter 3 Tour (Sunshine High School)",
                c3_desc: "Perform 20 Sunshine High School tour stages with Cookie / AP Energy",
                card_wf_title: "❄️🌸 Seasonal Weather Effects",
                card_wf_sub: "Select 1 single active effect",
                wf_desc: "The system activates only <b>1 weather effect at a time</b> to keep visuals distinct and prevent overlapping particles:",
                wf_snow_title: "❄️ Winter Snow Festival",
                wf_snow_desc: "Enable soft white snowfall particles outside the room window & main lobby",
                wf_snow_tag: "Winter",
                wf_cherry_title: "🌸 Cherry Blossom Date",
                wf_cherry_desc: "Enable pink cherry blossom petals fluttering through the spring atmosphere",
                wf_cherry_tag: "Spring",
                wf_none_title: "🚫 Disable All Weather Effects",
                wf_none_desc: "Return to default clean room atmosphere with no weather particles",
                wf_none_tag: "Default",
                card_fac_title: "🎨 Fan Art 2021 Limited Costumes",
                fac_name: "Fan Art Design Costumes",
                fac_desc: "Activate Spring Fairy costume and Fairy's Melody guitar",
                card_er_title: "🏆 Event Ranking Leaderboard",
                er_name: "Event Top Leaderboard",
                er_desc: "Enable real-time event score race with Top 100 players leaderboard",
                card_mail_title: "📬 Server Broadcast Mail & Gifts",
                card_mail_sub: "Instant sync without leaving the game",
                btn_send_broadcast: "🚀 Send Mail & Gifts to Server",
                card_cli_title: "💻 Terminal Commands (CLI)",
                cli_sub: "You can also manage server events directly via terminal commands:",
                modal_user_title: "⚙️ Individual Player Settings",
                modal_ban_title: "🚫 Ban Player Account",
                modal_ban_desc: "Ban player account. The game will show 'Account is BANNED' message instead of connection error.",
                modal_sp_gold_title: "⭐ Paid Gold Star Pass",
                modal_sp_gold_desc: "Unlock Gold Star Pass entitlement exclusively for this player",
                modal_sp_points_lbl: "Star Pass Points:",
                modal_sp_points_sub: "Update points to claim tiered milestone rewards (automatically calculates corresponding tier).",
                modal_curr_title: "💰 Resources (Likes, CP, Candy)",
                modal_add_likes: "Add Likes (Tim):",
                modal_add_cp: "Add Chocolate (CP):",
                modal_add_candy: "Add Candy:",
                modal_set_likes: "❤️ Set Exact Likes (Supports game units: 42.877G, 100H, 10AA...):",
                modal_att_title: "📅 Customize Attendance Events",
                modal_att_target: "Select Event to Edit:",
                modal_att_day_lbl: "Target Day Milestone:",
                modal_att_unlock_lbl: "🔓 Unlock reward claiming today (Bypass 24h cooldown)",
                modal_att_grant_lbl: "🎁 Directly grant all milestone rewards for this event",
                modal_ch2_title: "⚠️ Unlock Ch2: Happy Bakery",
                modal_ch2_badge: "DANGER / TEST",
                modal_ch2_enable: "🔓 Enable Chapter 2 Unlock For This Player",
                modal_sendmail_chk: "📬 Send notification mail to player's in-game mailbox",
                btn_cancel: "Cancel",
                btn_save_user: "💾 Save Individual Settings",
                btn_delete_user: "🗑️ Delete All Account Data (Clean Reset to Start)",
                btn_send_now: "🚀 Send In-Game Now"
            }
        };

        let currentLang = localStorage.getItem('gg_admin_lang') || 'vi';

        function t(key, fallback = '') {
            if (I18N[currentLang] && I18N[currentLang][key] !== undefined) {
                return I18N[currentLang][key];
            }
            return fallback || key;
        }

        function setLanguage(lang) {
            currentLang = lang;
            localStorage.setItem('gg_admin_lang', lang);
            document.documentElement.lang = lang;

            const btnVi = document.getElementById('lang-btn-vi');
            const btnEn = document.getElementById('lang-btn-en');
            if (btnVi) btnVi.classList.toggle('active', lang === 'vi');
            if (btnEn) btnEn.classList.toggle('active', lang === 'en');

            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (I18N[lang] && I18N[lang][key] !== undefined) {
                    el.innerHTML = I18N[lang][key];
                }
            });
            document.querySelectorAll('[data-i18n-title]').forEach(el => {
                const key = el.getAttribute('data-i18n-title');
                if (I18N[lang] && I18N[lang][key] !== undefined) {
                    el.setAttribute('title', I18N[lang][key]);
                }
            });
            document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
                const key = el.getAttribute('data-i18n-placeholder');
                if (I18N[lang] && I18N[lang][key] !== undefined) {
                    el.setAttribute('placeholder', I18N[lang][key]);
                }
            });

            // Re-render UI elements
            renderUI();
            if (cachedUsers && cachedUsers.length > 0) {
                filterUsers();
            }
        }

        let currentConfig = null;
        let seasonsList = [];
        let cachedUsers = [];

        function showToast(msg, isError = false) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.borderLeftColor = isError ? 'var(--danger)' : 'var(--accent-cyan)';
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 3500);
        }

        // ================= TABS NAVIGATION =================
        function switchTab(tab) {
            const isUsers = (tab === 'users');
            document.getElementById('tab-btn-users').classList.toggle('active', isUsers);
            document.getElementById('tab-btn-events').classList.toggle('active', !isUsers);
            document.getElementById('tab-users-view').style.display = isUsers ? 'block' : 'none';
            document.getElementById('tab-events-view').style.display = !isUsers ? 'block' : 'none';
            localStorage.setItem('gg_admin_active_tab', tab);
            if (isUsers) {
                loadUsers();
            }
        }

        function copyToClipboard(text, label = 'UUID') {
            navigator.clipboard.writeText(text).then(() => {
                showToast(`📋 Đã sao chép ${label}!`);
            }).catch(() => {
                const input = document.createElement('input');
                input.value = text;
                document.body.appendChild(input);
                input.select();
                document.execCommand('copy');
                document.body.removeChild(input);
                showToast(`📋 Đã sao chép ${label}!`);
            });
        }

        // ================= EVENT CONFIG LOGIC =================
        async function loadConfig() {
            try {
                const res = await fetch('/admin/api/events');
                const data = await res.json();
                if (!data.success) throw new Error('Không thể tải cấu hình');
                currentConfig = data.config;
                seasonsList = data.seasons || [];
                renderUI();
            } catch (e) {
                showToast('Lỗi tải cấu hình: ' + e.message, true);
            }
        }

        function selectWeatherMode(mode) {
            document.querySelectorAll('input[name="weather_mode"]').forEach(r => {
                r.checked = (r.value === mode);
            });
            document.getElementById('card-wf-snow')?.classList.toggle('active', mode === 'snow');
            document.getElementById('card-wf-cherry')?.classList.toggle('active', mode === 'cherry');
            document.getElementById('card-wf-none')?.classList.toggle('active', mode === 'none');
        }

        function renderUI() {
            if (!currentConfig) return;

            // Attendance list
            const attContainer = document.getElementById('attendance-list');
            attContainer.innerHTML = '';
            for (const [id, ev] of Object.entries(currentConfig.attendance_events || {})) {
                const div = document.createElement('div');
                div.className = 'event-item';
                div.innerHTML = `
                    <div class="event-info">
                        <div class="event-name">${ev.name}</div>
                        <div class="event-desc">${ev.description}</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="att-${id}" ${ev.enabled ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                `;
                attContainer.appendChild(div);
            }

            // Star pass
            document.getElementById('sp-enabled').checked = !!currentConfig.star_pass.enabled;
            document.getElementById('sp-gold').checked = !!currentConfig.star_pass.paid_card_enabled;

            // Seasons dropdown
            const seasonSelect = document.getElementById('sp-season');
            seasonSelect.innerHTML = '';
            seasonsList.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                const nameVi = s.name_vi || s.name || `Mùa ${s.id}`;
                const nameEn = s.name_en ? ` (${s.name_en})` : '';
                const dateInfo = (s.month && s.year) ? ` [T${s.month}/${s.year}]` : '';
                opt.text = `Mùa ${s.id}: ${nameVi}${nameEn}${dateInfo}`;
                if (s.id === currentConfig.star_pass.active_season) opt.selected = true;
                seasonSelect.appendChild(opt);
            });

            // Pass Goods Sale
            if (currentConfig.pass_goods_sale) {
                document.getElementById('pgs-enabled').checked = !!currentConfig.pass_goods_sale.enabled;
                if (currentConfig.pass_goods_sale.name) document.getElementById('pgs-name').innerText = currentConfig.pass_goods_sale.name;
                if (currentConfig.pass_goods_sale.description) document.getElementById('pgs-desc').innerText = currentConfig.pass_goods_sale.description;
            }

            // Meowfest
            document.getElementById('mf-enabled').checked = !!currentConfig.meowfest.enabled;
            if (currentConfig.meowfest.name) document.getElementById('mf-name').innerText = currentConfig.meowfest.name;
            if (currentConfig.meowfest.description) document.getElementById('mf-desc').innerText = currentConfig.meowfest.description;

            // Chapter 3 Tour
            document.getElementById('c3-enabled').checked = !!currentConfig.chapter3_tour.enabled;
            if (currentConfig.chapter3_tour.name) document.getElementById('c3-name').innerText = currentConfig.chapter3_tour.name;
            if (currentConfig.chapter3_tour.description) document.getElementById('c3-desc').innerText = currentConfig.chapter3_tour.description;

            // Weather Festival (Mutually Exclusive)
            if (currentConfig.weather_festival) {
                const snow = !!currentConfig.weather_festival.snow_enabled;
                const cherry = !!currentConfig.weather_festival.cherry_blossom_enabled;
                const mode = currentConfig.weather_festival.mode || (snow ? 'snow' : (cherry ? 'cherry' : 'none'));
                selectWeatherMode(mode);
            }

            // Fan Art
            if (currentConfig.fan_art_costume) {
                document.getElementById('fac-enabled').checked = !!currentConfig.fan_art_costume.enabled;
                if (currentConfig.fan_art_costume.name) document.getElementById('fac-name').innerText = currentConfig.fan_art_costume.name;
                if (currentConfig.fan_art_costume.description) document.getElementById('fac-desc').innerText = currentConfig.fan_art_costume.description;
            }

            // Event Ranking
            if (currentConfig.event_ranking) {
                document.getElementById('er-enabled').checked = !!currentConfig.event_ranking.enabled;
                if (currentConfig.event_ranking.name) document.getElementById('er-name').innerText = currentConfig.event_ranking.name;
                if (currentConfig.event_ranking.description) document.getElementById('er-desc').innerText = currentConfig.event_ranking.description;
            }
        }

        async function saveConfig() {
            if (!currentConfig) return;

            for (const id of Object.keys(currentConfig.attendance_events || {})) {
                const el = document.getElementById(`att-${id}`);
                if (el) currentConfig.attendance_events[id].enabled = el.checked;
            }

            currentConfig.star_pass.enabled = document.getElementById('sp-enabled').checked;
            currentConfig.star_pass.paid_card_enabled = document.getElementById('sp-gold').checked;
            currentConfig.star_pass.active_season = parseInt(document.getElementById('sp-season').value) || 13;

            currentConfig.pass_goods_sale = currentConfig.pass_goods_sale || {};
            currentConfig.pass_goods_sale.enabled = document.getElementById('pgs-enabled').checked;

            currentConfig.meowfest.enabled = document.getElementById('mf-enabled').checked;
            currentConfig.chapter3_tour.enabled = document.getElementById('c3-enabled').checked;

            currentConfig.weather_festival = currentConfig.weather_festival || {};
            const selectedWeather = document.querySelector('input[name="weather_mode"]:checked')?.value || 'none';
            currentConfig.weather_festival.snow_enabled = (selectedWeather === 'snow');
            currentConfig.weather_festival.cherry_blossom_enabled = (selectedWeather === 'cherry');
            currentConfig.weather_festival.mode = selectedWeather;

            currentConfig.fan_art_costume = currentConfig.fan_art_costume || {};
            currentConfig.fan_art_costume.enabled = document.getElementById('fac-enabled').checked;

            currentConfig.event_ranking = currentConfig.event_ranking || {};
            currentConfig.event_ranking.enabled = document.getElementById('er-enabled').checked;

            currentConfig.notify_in_game = document.getElementById('auto-notify-mail').checked;

            try {
                const res = await fetch('/admin/api/events', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(currentConfig)
                });
                const data = await res.json();
                if (!data.success) throw new Error(data.error || 'Lưu thất bại');
                currentConfig = data.config;
                renderUI();
                showToast('✅ Đã lưu và áp dụng cấu hình sự kiện thành công!');
            } catch (e) {
                showToast('❌ Lỗi khi lưu: ' + e.message, true);
            }
        }

        async function sendDirectMail() {
            const title = document.getElementById('mail-title').value.trim() || 'Thông báo Quản trị';
            const memo = document.getElementById('mail-memo').value.trim() || 'Quà tặng từ quản trị viên';
            const cp = parseInt(document.getElementById('mail-cp').value) || 0;
            const candy = parseFloat(document.getElementById('mail-candy').value) || 0;
            const cookies = parseInt(document.getElementById('mail-cookies').value) || 0;

            try {
                const res = await fetch('/admin/api/send_post', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, memo, cp, candy, cookies })
                });
                const data = await res.json();
                if (!data.success) throw new Error(data.error || 'Gửi thất bại');
                showToast('🚀 Đã gửi thư và quà thành công vào game! Người chơi sẽ thấy chấm đỏ.');
            } catch (e) {
                showToast('❌ Lỗi khi gửi thư: ' + e.message, true);
            }
        }

        const GAME_UNITS = [];
        for (let i = 0; i < 26; i++) GAME_UNITS.push(String.fromCharCode(65 + i)); // A..Z
        for (let i = 0; i < 26; i++) {
            for (let j = 0; j < 26; j++) {
                GAME_UNITS.push(String.fromCharCode(65 + i) + String.fromCharCode(65 + j)); // AA..ZZ
            }
        }

        function formatNumber(num) {
            if (num === null || num === undefined) return '0';
            const s = String(num).trim();
            if (!s || s === '0') return '0';
            const n = Number(num);
            if (!isNaN(n) && n >= 0 && n < 1000) {
                return Math.floor(n).toLocaleString();
            }
            if (s.includes('e') || s.includes('E') || s.includes('.')) {
                if (isNaN(n) || !isFinite(n)) return '0';
                const exp = Math.floor(Math.log10(n));
                const unitIdx = Math.floor(exp / 3);
                if (unitIdx <= 0) return Math.floor(n).toLocaleString();
                const unitName = GAME_UNITS[unitIdx - 1] || 'ZZ';
                const mantissa = n / Math.pow(10, unitIdx * 3);
                return mantissa.toFixed(3) + unitName;
            }
            const digits = s.length;
            const unitIdx = Math.floor((digits - 1) / 3);
            if (unitIdx <= 0) return Number(s).toLocaleString();
            const unitName = GAME_UNITS[unitIdx - 1] || 'ZZ';
            const intLen = ((digits - 1) % 3) + 1;
            const intPart = s.substring(0, intLen);
            const decPart = s.substring(intLen, intLen + 3).padEnd(3, '0');
            return `${intPart}.${decPart}${unitName}`;
        }

        function parseGameCurrencyPreview(inputStr) {
            if (!inputStr) return '';
            const trimmed = inputStr.trim();
            if (!trimmed || trimmed === '0') return '';
            const m = trimmed.match(/^([+-]?\\d+(?:\\.\\d+)?(?:[eE][+-]?\\d+)?)\\s*([a-zA-Z]*)$/);
            if (!m) return '';
            const num = parseFloat(m[1]);
            const unit = m[2].toUpperCase();
            if (isNaN(num)) return '';
            if (!unit) {
                return 'Quy đổi: ' + formatNumber(num) + ' Tim';
            }
            const idx = GAME_UNITS.indexOf(unit);
            if (idx === -1) {
                if (unit === 'K') return 'Quy đổi: ' + (num * 1e3).toLocaleString() + ' Tim (10.000A)';
                return '⚠️ Đơn vị không hợp lệ (hợp lệ: A, B, C... G, H... ZZ)';
            }
            const exp = (idx + 1) * 3;
            return `✨ Đơn vị game: ${num.toFixed(3)}${unit} (10^${exp})`;
        }

        function updateLikePreviews() {
            const addLikeVal = document.getElementById('modal-add-like') ? document.getElementById('modal-add-like').value : '';
            const setLikeVal = document.getElementById('modal-set-like') ? document.getElementById('modal-set-like').value : '';
            const addPrev = document.getElementById('modal-add-like-preview');
            const setPrev = document.getElementById('modal-set-like-preview');
            if (addPrev) addPrev.innerText = parseGameCurrencyPreview(addLikeVal);
            if (setPrev) setPrev.innerText = parseGameCurrencyPreview(setLikeVal);
        }

        // ================= USERS MANAGEMENT LOGIC =================
        let currentActiveSeason = 13;

        async function loadUsers() {
            const container = document.getElementById('users-table-container');
            try {
                const res = await fetch('/admin/api/users');
                const data = await res.json();
                if (!data.success) throw new Error('Không thể tải danh sách người chơi');
                cachedUsers = data.users || [];
                currentActiveSeason = data.active_season || 13;

                updateUserStats();
                filterUsers();
            } catch (e) {
                container.innerHTML = `<div style="color: var(--danger); padding: 16px; text-align: center;">Lỗi tải dữ liệu người chơi: ${e.message}</div>`;
            }
        }

        function updateUserStats() {
            const total = cachedUsers.length;
            const real = cachedUsers.filter(u => !u.is_test).length;
            const test = cachedUsers.filter(u => u.is_test).length;
            const banned = cachedUsers.filter(u => u.is_banned).length;
            const gold = cachedUsers.filter(u => u.is_gold).length;

            document.getElementById('stat-total-users').innerText = total;
            document.getElementById('stat-real-users').innerText = real;
            document.getElementById('stat-test-users').innerText = test;
            document.getElementById('stat-banned-users').innerText = banned;
            document.getElementById('stat-gold-users').innerText = gold;
            document.getElementById('tab-users-count').innerText = total;
            document.getElementById('total-count').innerText = total;
        }

        function filterUsers() {
            const q = (document.getElementById('user-search-input').value || '').trim().toLowerCase();
            const filter = document.getElementById('user-status-filter').value;

            let filtered = cachedUsers.filter(u => {
                if (filter === 'real' && u.is_test) return false;
                if (filter === 'test' && !u.is_test) return false;
                if (filter === 'active' && u.is_banned) return false;
                if (filter === 'banned' && !u.is_banned) return false;
                if (filter === 'gold' && !u.is_gold) return false;
                if (filter === 'free' && u.is_gold) return false;

                if (!q) return true;
                const nick = (u.u_nick || '').toLowerCase();
                const id = (u.u_id || '').toLowerCase();
                const seq = String(u.u_seq || '');
                const uuid = (u.uuid || '').toLowerCase();
                const devUuid = (u.device_uuid || '').toLowerCase();
                return nick.includes(q) || id.includes(q) || seq.includes(q) || uuid.includes(q) || devUuid.includes(q);
            });

            document.getElementById('filtered-count').innerText = filtered.length;
            renderUsersTable(filtered);
        }

        async function cleanupTestUsers() {
            if (!confirm('Bạn có chắc chắn muốn DỌN DẸP toàn bộ tài khoản test tự động không?\\nCác thiết bị người chơi thật sẽ được bảo toàn nguyên vẹn 100%.')) return;
            try {
                const res = await fetch('/admin/api/users/cleanup_tests', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({})
                });
                const data = await res.json();
                if (!data.success) throw new Error(data.error || 'Dọn dẹp thất bại');
                showToast('🧹 ' + data.message);
                loadUsers();
            } catch (e) {
                showToast('❌ Lỗi: ' + e.message, true);
            }
        }

        function renderUsersTable(users) {
            const container = document.getElementById('users-table-container');
            if (users.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; color: var(--text-sub); padding: 32px; background: rgba(0,0,0,0.2); border-radius: 10px;">
                        Không tìm thấy người chơi nào phù hợp với bộ lọc.<br>
                        <span style="font-size:0.8rem; margin-top:4px; display:inline-block;">Hãy thử xóa bộ lọc hoặc kiểm tra lại từ khóa tìm kiếm.</span>
                    </div>
                `;
                return;
            }

            const spEnabled = !!currentConfig?.star_pass?.enabled;

            let html = `
                <table class="user-table">
                    <thead>
                        <tr>
                            <th>${t('th_player', 'Người Chơi')}</th>
                            <th>${t('th_last_login', 'Đăng Nhập Gần Nhất')}</th>
                            <th>${t('th_resources', 'Tài Nguyên')}</th>
                            <th>${t('th_attendance', 'Sự Kiện Điểm Danh')}</th>
                            <th>${t('th_starpass', 'Thẻ Sao')} ${spEnabled ? `(${currentLang === 'en' ? 'Season' : 'Mùa'} ${currentActiveSeason})` : `(${t('badge_disabled', 'Đang Tắt')})`}</th>
                            <th style="text-align: right;">${t('th_actions', 'Thao Tác')}</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            users.forEach(u => {
                const passBadge = !spEnabled
                    ? `<span style="display:inline-block; font-size:0.75rem; color:#888; background:rgba(255,255,255,0.06); padding:2px 8px; border-radius:4px; border:1px solid rgba(255,255,255,0.08);">${t("badge_disabled", "⚪ Đang tắt")}</span>`
                    : (u.is_gold
                        ? `<span class="user-badge-gold">${t("badge_gold", "⭐ Gold Pass")}</span>`
                        : `<span class="user-badge-free">${t("badge_free", "⚪ Free Pass")}</span>`);
                const banBadge = u.is_banned
                    ? `<span class="user-badge-banned">🚫 BANNED</span>`
                    : '';
                const deviceBadge = u.is_test
                    ? `<span style="display:inline-flex; align-items:center; background:rgba(255,165,2,0.15); color:#ffa502; border:1px solid rgba(255,165,2,0.35); font-size:0.68rem; padding:1px 6px; border-radius:4px; font-weight:700; margin-left:6px;">${t("badge_test", "🧪 Test Auto")}</span>`
                    : `<span style="display:inline-flex; align-items:center; background:rgba(46, 213, 115, 0.15); color:#2ed573; border:1px solid rgba(46, 213, 115, 0.35); font-size:0.68rem; padding:1px 6px; border-radius:4px; font-weight:700; margin-left:6px;">${t("badge_real", "📱 Máy Thật")}</span>`;
                const shortUuid = u.uuid ? (u.uuid.length > 14 ? u.uuid.substring(0, 14) + '...' : u.uuid) : '-';

                html += `
                    <tr>
                        <td>
                            <div style="font-weight: 700; color: #fff; font-size: 0.95rem; display:flex; align-items:center; flex-wrap:wrap; gap:4px;">
                                <span>${escapeHtml(u.u_nick)}</span>
                                ${deviceBadge}
                                ${banBadge}
                            <div style="font-size: 0.8rem; color: #55efc4; font-weight: 700; margin-top: 3px; display:flex; align-items:center; gap:6px;">
                                <span style="background:rgba(85,239,196,0.12); border:1px solid rgba(85,239,196,0.3); padding:1px 6px; border-radius:4px;">UID: #${u.u_seq}</span>
                                <span style="color:var(--text-sub); font-weight:400; font-size:0.75rem;">${escapeHtml(u.u_id || '-')}</span>
                            </div>
                            <div class="uuid-pill" onclick="copyToClipboard('${u.uuid}', 'UUID')" title="Bấm để sao chép toàn bộ UUID">
                                📋 ${escapeHtml(shortUuid)}
                            </div>
                        </td>
                        <td>
                            <div style="color: var(--text-main); font-size: 0.85rem; font-weight: 500;">🕒 ${escapeHtml(u.u_last_login)}</div>
                        </td>
                        <td>
                            <div style="font-size: 0.82rem; color: #ff6b81; font-weight: 600;">❤️ ${formatNumber(u.u_like)} ${t('currency_tim', 'Tim')}</div>
                            <div style="font-size: 0.82rem; color: #f5cd79; font-weight: 500;">🍫 ${formatNumber(u.u_cp)} CP</div>
                            <div style="font-size: 0.82rem; color: #68d8d6; font-weight: 500;">🍬 ${formatNumber(u.u_candy)} Candy</div>
                        </td>
                        <td>
                            <div style="font-size: 0.82rem; color: #a29bfe; font-weight: 500;">${t('lbl_newbie', '📅 Tân Thủ')}: <b>${u.attendance_day || 0}/7</b></div>
                            <div style="font-size: 0.82rem; color: #55efc4; font-weight: 500; margin-top: 3px;">${t('lbl_bakery', '🏪 Tiện Lợi')}: <b>${u.ch2_attendance_day || 0}/7</b></div>
                            ${u.ch2_unlocked
                                ? `<div style="font-size: 0.74rem; color: #2ed573; font-weight: 600; margin-top: 3px;">${t('lbl_ch2_opened', '🔓 CH2: Đã mở')}</div>`
                                : `<div style="font-size: 0.74rem; color: var(--text-sub); margin-top: 3px;">${t('lbl_ch2_locked', '🔒 CH2: Chưa mở')}</div>`}
                        </td>
                        <td>
                            <div>${passBadge}</div>
                            <div style="font-size: 0.76rem; color: var(--text-sub); margin-top: 3px;">
                                ${spEnabled ? `${Number(u.star_point || 0).toLocaleString()} ${t('lbl_pts', 'điểm')} &bull; ${t('lbl_tier', 'Cấp')} ${u.star_step || 0}` : '<span style="color:#666;">' + t('not_activated', 'Chưa kích hoạt') + '</span>'}
                            </div>
                        </td>
                        <td style="text-align: right; white-space: nowrap;">
                            <div style="display: inline-flex; gap: 6px; align-items: center; justify-content: flex-end;">
                                <button class="btn-setting-event" onclick="openUserModal('${u.uuid || ""}', ${u.u_seq})" title="Cài đặt sự kiện & tài nguyên cá nhân">
                                    ⚙️ Setting
                                </button>
                                <button class="btn-mail" onclick="openSendMailModal('${u.uuid || ""}', '${escapeHtml(u.u_nick)}')" title="Gửi thư và quà riêng cho người chơi này">
                                    ✉️ ${t('btn_mail', 'Thư')}
                                </button>
                                <button class="${u.is_banned ? 'btn-unban' : 'btn-ban'}" onclick="toggleBan('${u.uuid || ""}', ${!u.is_banned}, ${u.u_seq})" title="${u.is_banned ? 'Mở khóa tài khoản' : 'Khóa tài khoản'}">
                                    ${u.is_banned ? '✅ ' + t('btn_unban', 'Mở') : '🚫 ' + t('btn_ban', 'Ban')}
                                </button>
                                <button class="btn-delete-user" onclick="deleteUser('${u.uuid || ""}', '${escapeHtml(u.u_nick)}', ${u.u_seq})" title="Xóa toàn bộ dữ liệu">
                                    🗑️ ${t('btn_delete', 'Xóa')}
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });

            html += `</tbody></table>`;
            container.innerHTML = html;
        }

        function escapeHtml(text) {
            if (!text) return '';
            return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        async function toggleBan(uuid, banState, uSeq) {
            const actionText = banState ? 'KHÓA (BAN)' : 'MỞ KHÓA';
            if (!confirm(`Bạn có chắc chắn muốn ${actionText} tài khoản người chơi này?\n${banState ? 'Khi bị khóa, game sẽ hiển thị thông báo "Tài khoản của bạn đã bị KHÓA" thay vì lỗi mạng.' : 'Sau khi mở khóa, người chơi sẽ có thể đăng nhập bình thường.'}`)) return;
            try {
                const res = await fetch('/admin/api/user/ban', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ uuid: (uuid && uuid !== 'null') ? uuid : '', banned: banState, u_seq: uSeq })
                });
                const data = await res.json();
                if (!data.success) throw new Error(data.error || 'Thao tác thất bại');
                showToast(data.message || 'Thành công!');
                loadUsers();
            } catch (e) {
                showToast('❌ Lỗi: ' + e.message, true);
            }
        }

        async function deleteUser(uuid, nick, uSeq) {
            if (!confirm(`⚠️ CẢNH BÁO NGUY HIỂM!\n\nBạn có chắc chắn muốn XÓA TOÀN BỘ DỮ LIỆU của người chơi [${nick}]?\nToàn bộ tiến trình, Tim, CP, sự kiện sẽ bị xóa vĩnh viễn khỏi server. Khi vào lại game sẽ là tài khoản mới tinh.`)) {
                return;
            }
            try {
                const res = await fetch('/admin/api/user/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ uuid: (uuid && uuid !== 'null') ? uuid : '', u_seq: uSeq })
                });
                const data = await res.json();
                if (!data.success) throw new Error(data.error || 'Xóa thất bại');
                showToast(data.message || '✅ Đã xóa toàn bộ dữ liệu người chơi!');
                loadUsers();
            } catch (e) {
                showToast('❌ Lỗi: ' + e.message, true);
            }
        }

        function deleteCurrentModalUser() {
            const uuid = document.getElementById('modal-uuid').value;
            const uSeq = document.getElementById('modal-useq').value;
            const nick = document.getElementById('modal-user-name').innerText;
            deleteUser(uuid, nick, uSeq);
            closeUserModal();
        }

        // Metadata for all Attendance Events
        const ATT_EVENTS_INFO = {
            '1': {
                name: '📅 Tân thủ 7 ngày (Event 1)',
                totalDays: 7,
                rewardsDesc: 'Nhạc 13 + Váy 9 + 600 CP + 100 Kẹo',
                dayNames: {
                    1: '100 CP',
                    2: 'Váy đầm hoa tuyết',
                    3: '200 CP',
                    4: '50 Kẹo',
                    5: '300 CP',
                    6: '50 Kẹo',
                    7: 'Nhạc Bông hoa chưa được đặt tên'
                }
            },
            '3': {
                name: '🏪 Cửa hàng tiện lợi (CH2 - Event 3)',
                totalDays: 7,
                rewardsDesc: '250 AP + 100 Kẹo + 150 CP',
                dayNames: {
                    1: '50 AP Bánh quy',
                    2: '50 Kẹo',
                    3: '50 AP Bánh quy',
                    4: '50 Kẹo',
                    5: '50 AP Bánh quy',
                    6: '100 AP Bánh quy',
                    7: '150 CP Socola'
                }
            },
            '202110': {
                name: '🎃 Halloween 14 ngày (Event 202110)',
                totalDays: 14,
                rewardsDesc: 'Trang phục & Guitar Halloween + CP + Kẹo',
                dayNames: {}
            },
            '202111': {
                name: '🎁 Chọn quà Tân thủ (Event 202111)',
                totalDays: 7,
                rewardsDesc: 'Bộ quà chọn Tân thủ 7 ngày',
                dayNames: {}
            },
            '2': {
                name: '🎂 Kỷ niệm 1 năm (14 ngày - Event 2)',
                totalDays: 14,
                rewardsDesc: 'Trọn bộ quà kỷ niệm 1 năm 14 ngày',
                dayNames: {}
            }
        };

        let currentModalUserAttData = {};
        let currentModalAttEventKey = '1';

        function renderModalAttEvent(eventKey) {
            currentModalAttEventKey = eventKey;
            const meta = ATT_EVENTS_INFO[eventKey] || { name: 'Sự kiện ' + eventKey, totalDays: 7, rewardsDesc: 'Quà sự kiện', dayNames: {} };
            const state = currentModalUserAttData[eventKey] || { day: 0, unlock_today: true, grant_all: false, modified: false, mode: 'claim_day' };

            const statusElem = document.getElementById('modal-att-status');
            const daySelect = document.getElementById('modal-att-day');
            const unlockElem = document.getElementById('modal-att-unlock');
            const grantElem = document.getElementById('modal-att-direct-grant');
            const grantLabel = document.getElementById('modal-att-grant-label');

            const isEvEnabled = !!currentConfig?.attendance_events?.[eventKey]?.enabled;
            if (!isEvEnabled) {
                statusElem.innerText = `⚠️ Đang TẮT trên hệ thống (Đã nhận ${state.day}/${meta.totalDays} ngày)`;
                statusElem.style.background = 'rgba(235, 77, 75, 0.2)';
                statusElem.style.color = '#ff6b6b';
            } else {
                statusElem.innerText = `Đã nhận ${state.day}/${meta.totalDays} ngày`;
                statusElem.style.background = 'rgba(162,155,254,0.15)';
                statusElem.style.color = '#a29bfe';
            }
            grantLabel.innerText = `🎁 Nhận ngay trọn bộ quà vào tài khoản (${meta.rewardsDesc})`;

            // Populate options for day select
            let opts = '';
            opts += `<option value="completed">✅ Đã hoàn thành trọn bộ ${meta.totalDays}/${meta.totalDays} ngày</option>`;
            for (let d = meta.totalDays; d >= 1; d--) {
                const desc = meta.dayNames[d] ? `: ${meta.dayNames[d]}` : '';
                opts += `<option value="claim_${d}">📅 Mở sẵn nhận Ngày ${d}${desc}</option>`;
            }
            opts += `<option value="reset">🔄 Đặt lại từ đầu (0/${meta.totalDays} ngày)</option>`;
            daySelect.innerHTML = opts;

            // Set current value
            if (state.day >= meta.totalDays) {
                daySelect.value = 'completed';
            } else if (state.mode === 'reset' || state.day === 0) {
                daySelect.value = (state.modified && state.mode === 'reset') ? 'reset' : 'claim_1';
            } else {
                daySelect.value = 'claim_' + Math.min(meta.totalDays, state.day + 1);
            }

            unlockElem.checked = state.unlock_today !== false;
            grantElem.checked = !!state.grant_all;
        }

        function onModalAttEventChange() {
            const newKey = document.getElementById('modal-att-event-select').value;
            renderModalAttEvent(newKey);
        }

        function onModalAttDayChange() {
            const val = document.getElementById('modal-att-day').value;
            const meta = ATT_EVENTS_INFO[currentModalAttEventKey] || { totalDays: 7 };
            const state = currentModalUserAttData[currentModalAttEventKey] || { day: 0 };
            state.modified = true;

            if (val === 'completed') {
                state.target_day = meta.totalDays;
                state.mode = 'complete';
            } else if (val === 'reset') {
                state.target_day = 0;
                state.mode = 'reset';
            } else if (val.startsWith('claim_')) {
                state.target_day = parseInt(val.replace('claim_', ''));
                state.mode = 'claim_day';
            }
            currentModalUserAttData[currentModalAttEventKey] = state;
        }

        function onModalAttUnlockChange() {
            const state = currentModalUserAttData[currentModalAttEventKey] || { day: 0 };
            state.unlock_today = document.getElementById('modal-att-unlock').checked;
            state.modified = true;
            currentModalUserAttData[currentModalAttEventKey] = state;
        }

        function onModalAttGrantChange() {
            const state = currentModalUserAttData[currentModalAttEventKey] || { day: 0 };
            state.grant_all = document.getElementById('modal-att-direct-grant').checked;
            state.modified = true;
            currentModalUserAttData[currentModalAttEventKey] = state;
        }

        function openUserModal(uuid, uSeq) {
            const u = cachedUsers.find(x => (uuid && uuid !== 'null' && x.uuid === uuid) || (uSeq !== undefined && x.u_seq === Number(uSeq)));
            if (!u) {
                showToast('Không tìm thấy người chơi!', true);
                return;
            }
            document.getElementById('modal-uuid').value = u.uuid || '';
            document.getElementById('modal-useq').value = u.u_seq;
            document.getElementById('modal-user-name').innerText = u.u_nick;
            document.getElementById('modal-user-sub').innerText = `🆔 UID: #${u.u_seq} • ID: ${u.u_id || '-'} • UUID: ${u.uuid || '-'}`;
            document.getElementById('modal-user-lastlogin').innerText = `🕒 Đăng nhập gần nhất: ${u.u_last_login}`;
            document.getElementById('modal-is-banned').checked = !!u.is_banned;

            // Star Pass activation check: do not allow editing if Star Pass is not active globally
            const spEnabled = !!currentConfig?.star_pass?.enabled;
            const spNotice = document.getElementById('modal-sp-disabled-notice');
            const isGoldEl = document.getElementById('modal-is-gold');
            const starPointEl = document.getElementById('modal-star-point');
            const spGroup = document.getElementById('modal-sp-group');
            const spPointGroup = document.getElementById('modal-sp-point-group');

            if (!spEnabled) {
                if (spNotice) spNotice.style.display = 'block';
                if (isGoldEl) {
                    isGoldEl.checked = false;
                    isGoldEl.disabled = true;
                }
                if (starPointEl) {
                    starPointEl.value = u.star_point || 0;
                    starPointEl.disabled = true;
                }
                if (spGroup) {
                    spGroup.style.opacity = '0.45';
                    spGroup.style.pointerEvents = 'none';
                }
                if (spPointGroup) {
                    spPointGroup.style.opacity = '0.45';
                    spPointGroup.style.pointerEvents = 'none';
                }
            } else {
                if (spNotice) spNotice.style.display = 'none';
                if (isGoldEl) {
                    isGoldEl.checked = !!u.is_gold;
                    isGoldEl.disabled = false;
                }
                if (starPointEl) {
                    starPointEl.value = u.star_point || 0;
                    starPointEl.disabled = false;
                }
                if (spGroup) {
                    spGroup.style.opacity = '1';
                    spGroup.style.pointerEvents = 'auto';
                }
                if (spPointGroup) {
                    spPointGroup.style.opacity = '1';
                    spPointGroup.style.pointerEvents = 'auto';
                }
            }

            // Currencies
            document.getElementById('modal-user-like').innerText = 'Hiện có: ' + formatNumber(u.u_like) + ' Tim';
            document.getElementById('modal-add-like').value = '';
            document.getElementById('modal-add-cp').value = 0;
            document.getElementById('modal-add-candy').value = 0;
            document.getElementById('modal-set-like').value = '';
            updateLikePreviews();

            // Build attendance state for all events from user
            currentModalUserAttData = {};
            const attMap = u.attendance_map || {};
            for (const k of ['1', '3', '202110', '202111', '2']) {
                let d = 0;
                let y = 0;
                if (attMap[k]) {
                    d = attMap[k].day || 0;
                    y = attMap[k].ymd || 0;
                } else if (k === '1') {
                    d = u.attendance_day || 0;
                    y = u.attendance_ymd || 0;
                } else if (k === '3') {
                    d = u.ch2_attendance_day || 0;
                    y = u.ch2_attendance_ymd || 0;
                }
                const maxD = ATT_EVENTS_INFO[k]?.totalDays || 7;
                currentModalUserAttData[k] = {
                    day: d,
                    ymd: y,
                    target_day: d >= maxD ? maxD : d + 1,
                    mode: d >= maxD ? 'complete' : 'claim_day',
                    unlock_today: true,
                    grant_all: false,
                    modified: false
                };
            }
            document.getElementById('modal-att-event-select').value = '1';
            renderModalAttEvent('1');

            // Chapter 2 Unlock (Danger / Test mode)
            document.getElementById('modal-unlock-ch2').checked = !!u.ch2_unlocked;

            document.getElementById('modal-send-mail').checked = false;
            document.getElementById('user-event-modal').classList.add('active');
        }

        function closeUserModal() {
            document.getElementById('user-event-modal').classList.remove('active');
        }

        async function saveUserModal() {
            const uuid = document.getElementById('modal-uuid').value;
            const uSeq = document.getElementById('modal-useq').value;
            const is_banned = document.getElementById('modal-is-banned').checked;
            const spEnabled = !!currentConfig?.star_pass?.enabled;
            const is_gold = spEnabled ? document.getElementById('modal-is-gold').checked : undefined;
            const star_point = spEnabled ? (parseInt(document.getElementById('modal-star-point').value) || 0) : undefined;

            const add_cp = parseInt(document.getElementById('modal-add-cp').value) || 0;
            const add_candy = parseFloat(document.getElementById('modal-add-candy').value) || 0;
            const add_like = document.getElementById('modal-add-like').value.trim();
            const set_like_val = document.getElementById('modal-set-like').value.trim();

            const unlock_ch2 = document.getElementById('modal-unlock-ch2').checked;
            const send_mail = document.getElementById('modal-send-mail').checked;

            // Backward-compatible fallback fields for Event 1 and Event 3
            const att1State = currentModalUserAttData['1'] || {};
            const att3State = currentModalUserAttData['3'] || {};

            try {
                const res = await fetch('/admin/api/user/event_settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        uuid,
                        u_seq: uSeq,
                        is_banned,
                        is_gold,
                        star_point,
                        add_cp,
                        add_candy,
                        add_like,
                        set_like: set_like_val ? set_like_val : null,
                        attendance_events_custom: currentModalUserAttData,
                        attendance_day: att1State.target_day,
                        attendance_mode: att1State.mode,
                        attendance_unlock_today: att1State.unlock_today,
                        grant_rewards: att1State.grant_all,
                        ch2_attendance_day: att3State.target_day,
                        ch2_attendance_mode: att3State.mode,
                        ch2_unlock_today: att3State.unlock_today,
                        grant_ch2_rewards: att3State.grant_all,
                        unlock_ch2,
                        send_mail
                    })
                });
                const data = await res.json();
                if (!data.success) throw new Error(data.error || 'Lưu thất bại');
                showToast('✅ Cập nhật tài khoản người chơi thành công!');
                closeUserModal();
                loadUsers();
            } catch (e) {
                showToast('❌ Lỗi khi cập nhật: ' + e.message, true);
            }
        }

        // ================= PERSONAL / DIRECT MAIL MODAL =================
        function openSendMailModal(targetUuid = '', targetNick = '') {
            document.getElementById('modal-mail-uuid').value = targetUuid || '';
            const titleElem = document.getElementById('mail-modal-title');
            const infoElem = document.getElementById('modal-mail-target-info');

            if (targetUuid && targetNick) {
                titleElem.innerText = `✉️ Gửi Thư Riêng Cho [${targetNick}]`;
                infoElem.innerText = `Thư và quà sẽ được gửi đích danh cho người chơi ${targetNick} (ID: ${targetUuid.substring(0, 16)}...)`;
            } else {
                titleElem.innerText = '✉️ Gửi Thư & Quà Toàn Bộ Server';
                infoElem.innerText = 'Thư và quà sẽ được gửi tới TẤT CẢ người chơi trên máy chủ';
            }
            document.getElementById('mail-modal').classList.add('active');
        }

        function closeMailModal() {
            document.getElementById('mail-modal').classList.remove('active');
        }

        async function sendModalMail() {
            const targetUuid = document.getElementById('modal-mail-uuid').value.trim() || null;
            const title = document.getElementById('modal-mail-title').value.trim() || 'Thông báo Quản trị';
            const memo = document.getElementById('modal-mail-memo').value.trim() || 'Quà tặng từ quản trị viên';
            const cp = parseInt(document.getElementById('modal-mail-cp').value) || 0;
            const candy = parseFloat(document.getElementById('modal-mail-candy').value) || 0;
            const cookies = parseInt(document.getElementById('modal-mail-cookies').value) || 0;

            try {
                const res = await fetch('/admin/api/send_post', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ uuid: targetUuid, title, memo, cp, candy, cookies })
                });
                const data = await res.json();
                if (!data.success) throw new Error(data.error || 'Gửi thất bại');
                showToast(targetUuid ? '🚀 Đã gửi thư và quà riêng cho người chơi thành công!' : '🚀 Đã gửi thư và quà cho toàn bộ server thành công!');
                closeMailModal();
            } catch (e) {
                showToast('❌ Lỗi khi gửi: ' + e.message, true);
            }
        }

        // ================= INITIAL LOAD =================
        document.addEventListener('DOMContentLoaded', () => {
            setLanguage(currentLang);
            loadConfig();
            loadUsers();
            const savedTab = localStorage.getItem('gg_admin_active_tab') || 'users';
            switchTab(savedTab);
        });
    </script>
</body>
</html>
"""

def get_admin_html():
    return DASHBOARD_HTML

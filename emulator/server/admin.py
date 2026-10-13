"""Admin Web Dashboard for Guitar Girl Server - Tab-based Management."""
import json
from server import event_manager

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Guitar Girl - Quản Lý Máy Chủ & Người Chơi</title>
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
            <div class="logo-title">
                <span class="logo-icon">🎸</span>
                <h1>Guitar Girl - Trung Tâm Quản Trị</h1>
            </div>
            <p class="subtitle">Hệ thống điều khiển máy chủ, quản lý người chơi và cấu hình sự kiện trực tiếp</p>
            <div class="server-status">
                <span class="status-dot"></span>
                <span>Server Trực Tuyến &bull; Zero-Downtime Hot-Reload</span>
            </div>
        </header>

        <!-- Top Navigation Tabs -->
        <nav class="nav-tabs">
            <button class="nav-tab active" id="tab-btn-users" onclick="switchTab('users')">
                <span style="font-size: 1.1rem;">👥</span>
                <span>Quản Lý Toàn Bộ Người Chơi</span>
                <span class="tab-badge" id="tab-users-count">0</span>
            </button>
            <button class="nav-tab" id="tab-btn-events" onclick="switchTab('events')">
                <span style="font-size: 1.1rem;">🎉</span>
                <span>Cấu Hình Sự Kiện Server</span>
            </button>
        </nav>

        <!-- ================= TAB 1: QUẢN LÝ NGƯỜI CHƠI (ALL USERS) ================= -->
        <div id="tab-users-view">
            <!-- 1. Stats Grid -->
            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-card-title">👥 Tổng Người Chơi</div>
                    <div class="stat-card-value" id="stat-total-users" style="color: #a29bfe;">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-title">🟢 Đang Hoạt Động</div>
                    <div class="stat-card-value" id="stat-active-users" style="color: #2ed573;">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-title">🚫 Đã Khóa (Banned)</div>
                    <div class="stat-card-value" id="stat-banned-users" style="color: #ff4757;">0</div>
                </div>
                <div class="stat-card">
                    <div class="stat-card-title">⭐ Sở Hữu Gold Pass</div>
                    <div class="stat-card-value" id="stat-gold-users" style="color: #ffd32a;">0</div>
                </div>
            </div>

            <!-- 2. Search & Filter Bar -->
            <div class="card" style="padding: 16px; margin-bottom: 18px;">
                <div class="user-toolbar">
                    <input type="text" id="user-search-input" class="search-input" placeholder="🔍 Tìm kiếm theo Tên, ID, Seq, UUID..." oninput="filterUsers()">
                    <select id="user-status-filter" class="filter-select" onchange="filterUsers()">
                        <option value="all">Tất cả người chơi</option>
                        <option value="active">🟢 Đang hoạt động (Bình thường)</option>
                        <option value="banned">🚫 Đã bị khóa (BANNED)</option>
                        <option value="gold">⭐ Đã có Thẻ Sao Gold</option>
                        <option value="free">⚪ Thẻ Sao Thường (Free)</option>
                    </select>
                    <button class="btn btn-secondary" style="padding: 10px 14px; font-size: 0.88rem; flex: 0 0 auto;" onclick="loadUsers()">🔄 Làm mới</button>
                    <button class="btn btn-primary" style="padding: 10px 14px; font-size: 0.88rem; flex: 0 0 auto;" onclick="openSendMailModal()">✉️ Gửi Thư Toàn Server</button>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.82rem; color: var(--text-sub); padding: 0 4px;">
                    <div>Đang hiển thị <span id="filtered-count" style="color: #fff; font-weight: 700;">0</span> / <span id="total-count" style="color: #fff; font-weight: 700;">0</span> tài khoản</div>
                    <div>Nhấp vào UUID để sao chép nhanh</div>
                </div>
            </div>

            <!-- 3. Players Table Card -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📋 Danh Sách Chi Tiết Toàn Bộ Người Chơi</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">Quản lý độc lập từng tài khoản</span>
                </div>
                <div id="users-table-container" style="overflow-x: auto;">
                    <div style="text-align: center; color: var(--text-sub); padding: 24px;">Đang tải danh sách người chơi...</div>
                </div>
            </div>
        </div>

        <!-- ================= TAB 2: CẤU HÌNH SỰ KIỆN (EVENTS) ================= -->
        <div id="tab-events-view" style="display: none;">
            <div class="action-bar" style="flex-wrap: wrap;">
                <button class="btn btn-secondary" onclick="loadConfig()">🔄 Tải lại cấu hình</button>
                <button class="btn btn-primary" onclick="saveConfig()">💾 Lưu thay đổi sự kiện</button>
                <div style="width: 100%; display: flex; justify-content: center; margin-top: 4px;">
                    <label style="display:inline-flex; align-items:center; gap:8px; font-size:0.85rem; color:var(--text-sub); cursor:pointer;">
                        <input type="checkbox" id="auto-notify-mail" checked>
                        <span>📬 Tự động gửi thư thông báo vào game khi lưu sự kiện</span>
                    </label>
                </div>
            </div>

            <!-- 1. Attendance Events -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📅 Sự kiện Điểm danh & Đăng nhập</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">Daily Attendance</span>
                </div>
                <div id="attendance-list">
                    <!-- Injected via JS -->
                </div>
            </div>

            <!-- 2. Star Pass -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">⭐ Vé Sao / Star Pass</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">13 Mùa giải</span>
                </div>
                
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name">Kích hoạt Thẻ Sao (Star Pass)</div>
                        <div class="event-desc">Bật/tắt thanh tiến trình Star Pass và icon sự kiện ngoài sảnh chính</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="sp-enabled">
                        <span class="slider"></span>
                    </label>
                </div>

                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name">Mở khóa Thẻ Sao Gold Trả Phí Toàn Server (Paid Pass)</div>
                        <div class="event-desc">Tặng vé Gold Pass toàn bộ người chơi (Khuyên dùng nút Setting trong Tab Người chơi để cấp riêng)</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="sp-gold">
                        <span class="slider"></span>
                    </label>
                </div>

                <div class="form-group">
                    <label class="form-label" for="sp-season">Chọn Mùa giải Star Pass hoạt động:</label>
                    <select id="sp-season">
                        <!-- Injected via JS -->
                    </select>
                </div>
            </div>

            <!-- 3. Pass Goods Sale -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🏷️ Cửa hàng Giảm giá Star Pass (Pass Goods Sale)</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">Merch Shop & LIVE SALE</span>
                </div>
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name" id="pgs-name">Cửa hàng Giảm giá Star Pass</div>
                        <div class="event-desc" id="pgs-desc">Mở biểu tượng nút Sale trên sảnh chính để mua lại toàn bộ Trang phục & Guitar của 13 mùa Star Pass đã qua với giá ưu đãi Socola (50-200 CP)</div>
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
                    <div class="card-title">🐱 Sự kiện Nuôi Mèo Meowfest (SamSeck)</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">SamSaek Event</span>
                </div>
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name" id="mf-name">Sự kiện Nuôi Mèo Meowfest</div>
                        <div class="event-desc" id="mf-desc">Mở khóa 3 cột mốc nuôi mèo Tam Thể nhận Cây cào móng (Guitar 10), Quần yếm (Costume 13), Bé mèo Navi (Unit 1)</div>
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
                    <div class="card-title">🏫 Tour Sân khấu Sunshine High School (CH3)</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">Chapter 3 Tour</span>
                </div>
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name" id="c3-name">Tour Chapter 3 (Sunshine High School)</div>
                        <div class="event-desc" id="c3-desc">Biểu diễn sân khấu Sunshine High School 20 màn với Năng lượng Cookie / AP</div>
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
                    <div class="card-title">❄️🌸 Lễ hội Hiệu ứng Thời tiết Mùa (Weather Festival)</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">Hiệu ứng sảnh chính</span>
                </div>
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name">Lễ hội Tuyết rơi Mùa đông (Snow Festival)</div>
                        <div class="event-desc">Kích hoạt hiệu ứng những bông tuyết trắng rơi lãng mạn trên màn hình</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="wf-snow-enabled">
                        <span class="slider"></span>
                    </label>
                </div>
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name">Hẹn hò Mùa Hoa Anh Đào (Cherry Blossom Date)</div>
                        <div class="event-desc">Kích hoạt hiệu ứng những cánh hoa anh đào hồng bay bay trong không gian</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="wf-cherry-enabled">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>

            <!-- 7. Fan Art Costume -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🎨 Trang phục Bản giới hạn Fan Art 2021</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">Fan Art Grand Prize</span>
                </div>
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name" id="fac-name">Trang phục Thiết kế Fan Art</div>
                        <div class="event-desc" id="fac-desc">Kích hoạt bộ trang phục Nàng tiên mùa xuân (Spring Fairy) và Guitar Giai điệu nàng tiên (Fairy's Melody)</div>
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
                    <div class="card-title">🏆 Đua Top Xếp Hạng Sự Kiện (Event Ranking)</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">Live Leaderboard</span>
                </div>
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-name" id="er-name">Bảng Xếp Hạng Đua Top Sự Kiện</div>
                        <div class="event-desc" id="er-desc">Kích hoạt tính năng đua top điểm sự kiện trực tiếp với bảng xếp hạng Top 100 cao thủ</div>
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
                    <div class="card-title">📬 Gửi Thư & Tặng Quà Toàn Server (Broadcast Mail)</div>
                    <span style="font-size:0.8rem; color:var(--text-sub)">Đồng bộ tức thì không cần out game</span>
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
                <button class="btn btn-primary" style="width:100%; padding:10px;" onclick="sendDirectMail()">🚀 Gửi Thư & Quà Tới Toàn Server</button>
            </div>

            <!-- CLI Guide Card -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">💻 Lệnh điều khiển Terminal (CLI)</div>
                </div>
                <p style="font-size:0.85rem; color:var(--text-sub)">Bạn cũng có thể điều khiển trực tiếp trên terminal server bằng lệnh:</p>
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
                <h3>⚙️ Cài Đặt Cá Nhân Người Chơi</h3>
                <button class="modal-close" onclick="closeUserModal()">&times;</button>
            </div>
            <div class="modal-body">
                <input type="hidden" id="modal-uuid">
                
                <div style="margin-bottom: 14px; background: rgba(255,255,255,0.03); padding: 12px; border-radius: 10px; border: 1px solid var(--card-border);">
                    <div id="modal-user-name" style="font-weight: 700; font-size: 1.1rem; color: #fff;"></div>
                    <div id="modal-user-sub" style="font-size: 0.76rem; color: var(--text-sub); margin-top: 2px;"></div>
                    <div id="modal-user-lastlogin" style="font-size: 0.8rem; color: var(--accent-cyan); margin-top: 4px;"></div>
                </div>

                <!-- 0. Ban Switch -->
                <div class="event-item" style="padding: 10px 0; margin-bottom: 12px; background: rgba(255, 71, 87, 0.08); padding: 8px 12px; border-radius: 8px; border: 1px solid rgba(255, 71, 87, 0.25);">
                    <div class="event-info">
                        <div class="event-name" style="color: #ff6b81;">🚫 Khóa Tài Khoản (Ban Player)</div>
                        <div class="event-desc">Khóa tài khoản người chơi. Game sẽ hiện thông báo "Tài khoản đã bị KHÓA" thay vì lỗi mạng.</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="modal-is-banned">
                        <span class="slider"></span>
                    </label>
                </div>

                <!-- 1. Star Pass Toggle -->
                <div class="event-item" style="padding: 10px 0;">
                    <div class="event-info">
                        <div class="event-name">⭐ Thẻ Sao Gold Trả Phí (Paid Pass)</div>
                        <div class="event-desc">Mở khóa vé Thẻ Sao Gold riêng cho tài khoản người chơi này</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" id="modal-is-gold">
                        <span class="slider"></span>
                    </label>
                </div>

                <!-- 2. Star Pass Points -->
                <div class="form-group" style="margin-top:10px; padding-top:10px;">
                    <label class="form-label">Điểm Thẻ Sao (Star Points):</label>
                    <input type="number" id="modal-star-point" min="0" style="width:100%; padding:9px 12px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                    <div style="font-size:0.75rem; color:var(--text-sub); margin-top:4px;">Cập nhật điểm để nhận quà các cấp độ mốc sao (Tự động tính level quà tương ứng).</div>
                </div>

                <!-- 3. Currencies (Tim/Likes, Socola/CP, Kẹo/Candy) -->
                <div style="margin-top:14px; padding-top:12px; border-top:1px solid rgba(255,255,255,0.06);">
                    <div style="font-weight:600; font-size:0.9rem; color:#fff; margin-bottom:8px;">💰 Tài Nguyên (Tim, Socola, Kẹo)</div>
                    <div style="display:flex; gap:10px; margin-bottom:10px;">
                        <div style="flex:1;">
                            <label class="form-label">Thêm Tim (Likes):</label>
                            <input type="number" id="modal-add-like" value="0" style="width:100%; padding:9px 12px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                        </div>
                        <div style="flex:1;">
                            <label class="form-label">Thêm Socola (CP):</label>
                            <input type="number" id="modal-add-cp" value="0" style="width:100%; padding:9px 12px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                        </div>
                        <div style="flex:1;">
                            <label class="form-label">Thêm Kẹo (Candy):</label>
                            <input type="number" id="modal-add-candy" value="0" style="width:100%; padding:9px 12px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                        </div>
                    </div>
                    <div>
                        <label class="form-label" style="display:flex; justify-content:space-between;">
                            <span>❤️ Đặt chính xác số Tim (Ghi đè số Tim hiện tại):</span>
                            <span id="modal-user-like" style="color:#ff6b81; font-weight:600;">Hiện có: 0</span>
                        </label>
                        <input type="text" id="modal-set-like" placeholder="Nhập số Tim muốn đặt (ví dụ: 100000000000000000000)..." style="width:100%; padding:9px 12px; background:#121524; border:1px solid var(--card-border); color:#fff; border-radius:8px;">
                    </div>
                </div>

                <!-- 4. Điểm Danh 7 Ngày Tân Thủ -->
                <div style="margin-top:14px; padding-top:12px; border-top:1px solid rgba(255,255,255,0.06);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span style="font-weight:600; font-size:0.9rem; color:#fff;">📅 Điểm Danh 7 Ngày Tân Thủ (7-Day Attendance)</span>
                        <span id="modal-att-status" style="font-size:0.78rem; color:var(--text-sub);"></span>
                    </div>
                    
                    <label class="form-label">Chọn mốc ngày điểm danh:</label>
                    <select id="modal-att-day" style="margin-bottom:10px;">
                        <option value="claim_7">⭐ Ngày 7 (Mở khóa nhận quà Ngày 7 ngay: Nhạc Bông hoa chưa được đặt tên)</option>
                        <option value="claim_2">👗 Ngày 2 (Mở khóa nhận quà Ngày 2: Váy đầm hoa tuyết)</option>
                        <option value="claim_1">📅 Ngày 1 (Bắt đầu ngày 1: 100 CP)</option>
                        <option value="claim_3">🍫 Ngày 3 (Mở khóa nhận Ngày 3: 200 CP)</option>
                        <option value="claim_4">🍬 Ngày 4 (Mở khóa nhận Ngày 4: 50 Kẹo)</option>
                        <option value="claim_5">🍫 Ngày 5 (Mở khóa nhận Ngày 5: 300 CP)</option>
                        <option value="claim_6">🍬 Ngày 6 (Mở khóa nhận Ngày 6: 50 Kẹo)</option>
                        <option value="completed">✅ Đã hoàn thành trọn bộ 7/7 ngày</option>
                        <option value="reset">🔄 Đặt lại từ đầu (0/7 ngày)</option>
                    </select>

                    <div style="display:flex; flex-direction:column; gap:8px;">
                        <label style="display:inline-flex; align-items:center; gap:8px; font-size:0.82rem; color:var(--text-sub); cursor:pointer;">
                            <input type="checkbox" id="modal-att-unlock" checked>
                            <span>🔓 Mở khóa nhận quà ngay hôm nay (Xóa giới hạn chờ 24h)</span>
                        </label>
                        <label style="display:inline-flex; align-items:center; gap:8px; font-size:0.82rem; color:#f5cd79; cursor:pointer;">
                            <input type="checkbox" id="modal-att-direct-grant">
                            <span>🎁 Nhận ngay trọn bộ quà 7 ngày vào tài khoản (Nhạc 13 + Váy 9 + 600 CP + 100 Kẹo)</span>
                        </label>
                    </div>
                </div>

                <!-- 4.2 Điểm Danh Cửa Hàng Tiện Lợi Hạnh Phúc (CH2 - Event 3) -->
                <div style="margin-top:14px; padding-top:12px; border-top:1px solid rgba(255,255,255,0.06);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span style="font-weight:600; font-size:0.9rem; color:#fff;">🏪 Cửa Hàng Tiện Lợi Hạnh Phúc (CH2 - Event 3)</span>
                        <span id="modal-ch2-att-status" style="font-size:0.78rem; color:var(--text-sub);"></span>
                    </div>
                    
                    <label class="form-label">Chọn mốc ngày điểm danh tiện lợi:</label>
                    <select id="modal-ch2-att-day" style="margin-bottom:10px;">
                        <option value="claim_7">🍫 Ngày 7 (Mở khóa nhận quà Ngày 7: 150 CP Socola)</option>
                        <option value="claim_6">🍪 Ngày 6 (Mở khóa nhận quà Ngày 6: 100 AP Bánh quy)</option>
                        <option value="claim_3">🍪 Ngày 3 (Mở khóa nhận quà Ngày 3: 50 AP Bánh quy)</option>
                        <option value="claim_1">🍪 Ngày 1 (Mở khóa nhận quà Ngày 1: 50 AP Bánh quy)</option>
                        <option value="claim_2">🍬 Ngày 2 (Mở khóa nhận quà Ngày 2: 50 Kẹo)</option>
                        <option value="claim_4">🍬 Ngày 4 (Mở khóa nhận quà Ngày 4: 50 Kẹo)</option>
                        <option value="claim_5">🍪 Ngày 5 (Mở khóa nhận quà Ngày 5: 50 AP Bánh quy)</option>
                        <option value="completed">✅ Đã hoàn thành trọn bộ 7/7 ngày</option>
                        <option value="reset">🔄 Đặt lại từ đầu (0/7 ngày)</option>
                    </select>

                    <div style="display:flex; flex-direction:column; gap:8px;">
                        <label style="display:inline-flex; align-items:center; gap:8px; font-size:0.82rem; color:var(--text-sub); cursor:pointer;">
                            <input type="checkbox" id="modal-ch2-att-unlock" checked>
                            <span>🔓 Mở khóa nhận quà ngay hôm nay (Xóa giới hạn chờ 24h)</span>
                        </label>
                        <label style="display:inline-flex; align-items:center; gap:8px; font-size:0.82rem; color:#68d8d6; cursor:pointer;">
                            <input type="checkbox" id="modal-ch2-direct-grant">
                            <span>🎁 Nhận ngay trọn bộ quà tiện lợi vào tài khoản (250 AP + 100 Kẹo + 150 CP)</span>
                        </label>
                    </div>
                </div>

                <!-- 5. Mail notice toggle -->
                <div style="margin-top:14px; padding-top:12px; border-top:1px solid rgba(255,255,255,0.06);">
                    <label style="display:inline-flex; align-items:center; gap:8px; font-size:0.85rem; color:var(--text-sub); cursor:pointer;">
                        <input type="checkbox" id="modal-send-mail">
                        <span>📬 Gửi kèm thư thông báo vào Hòm thư in-game của người chơi</span>
                    </label>
                </div>
            </div>
            <div class="modal-footer" style="flex-wrap: wrap;">
                <button type="button" class="btn btn-secondary" onclick="closeUserModal()" style="flex:1;">Hủy</button>
                <button type="button" class="btn btn-primary" onclick="saveUserModal()" style="flex:1;">💾 Lưu Cài Đặt Riêng</button>
                <button type="button" class="btn btn-delete-user" onclick="deleteCurrentModalUser()" style="width:100%; margin-top:8px; padding:10px;">
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
                <button type="button" class="btn btn-secondary" onclick="closeMailModal()" style="flex:1;">Hủy</button>
                <button type="button" class="btn btn-primary" onclick="sendModalMail()" style="flex:1;">🚀 Gửi Ngay Vào Game</button>
            </div>
        </div>
    </div>

    <div id="toast"></div>

    <script>
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
                opt.text = `${s.id}. ${s.name}`;
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

            // Weather Festival
            if (currentConfig.weather_festival) {
                document.getElementById('wf-snow-enabled').checked = !!currentConfig.weather_festival.snow_enabled;
                document.getElementById('wf-cherry-enabled').checked = !!currentConfig.weather_festival.cherry_blossom_enabled;
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
            currentConfig.weather_festival.snow_enabled = document.getElementById('wf-snow-enabled').checked;
            currentConfig.weather_festival.cherry_blossom_enabled = document.getElementById('wf-cherry-enabled').checked;

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

        function formatNumber(num) {
            if (num === null || num === undefined) return '0';
            const n = Number(num);
            if (isNaN(n)) return '0';
            if (n >= 1e15) {
                return n.toExponential(2);
            }
            return Math.floor(n).toLocaleString();
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
            const banned = cachedUsers.filter(u => u.is_banned).length;
            const active = total - banned;
            const gold = cachedUsers.filter(u => u.is_gold).length;

            document.getElementById('stat-total-users').innerText = total;
            document.getElementById('stat-active-users').innerText = active;
            document.getElementById('stat-banned-users').innerText = banned;
            document.getElementById('stat-gold-users').innerText = gold;
            document.getElementById('tab-users-count').innerText = total;
            document.getElementById('total-count').innerText = total;
        }

        function filterUsers() {
            const q = (document.getElementById('user-search-input').value || '').trim().toLowerCase();
            const filter = document.getElementById('user-status-filter').value;

            let filtered = cachedUsers.filter(u => {
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

            let html = `
                <table class="user-table">
                    <thead>
                        <tr>
                            <th>Người Chơi</th>
                            <th>Đăng Nhập Gần Nhất</th>
                            <th>Tài Nguyên</th>
                            <th>Sự Kiện Điểm Danh</th>
                            <th>Thẻ Sao (Mùa ${currentActiveSeason})</th>
                            <th style="text-align: right;">Thao Tác</th>
                        </tr>
                    </thead>
                    <tbody>
            `;

            users.forEach(u => {
                const passBadge = u.is_gold
                    ? `<span class="user-badge-gold">⭐ Gold Pass</span>`
                    : `<span class="user-badge-free">⚪ Free Pass</span>`;
                const banBadge = u.is_banned
                    ? `<span class="user-badge-banned">🚫 BANNED</span>`
                    : '';
                const shortUuid = u.uuid ? (u.uuid.length > 14 ? u.uuid.substring(0, 14) + '...' : u.uuid) : '-';

                html += `
                    <tr>
                        <td>
                            <div style="font-weight: 700; color: #fff; font-size: 0.95rem;">${escapeHtml(u.u_nick)} ${banBadge}</div>
                            <div style="font-size: 0.76rem; color: var(--text-sub); margin-top: 2px;">Seq: #${u.u_seq} &bull; ID: ${escapeHtml(u.u_id || '-')}</div>
                            <div class="uuid-pill" onclick="copyToClipboard('${u.uuid}', 'UUID')" title="Bấm để sao chép toàn bộ UUID">
                                📋 ${escapeHtml(shortUuid)}
                            </div>
                        </td>
                        <td>
                            <div style="color: var(--text-main); font-size: 0.85rem; font-weight: 500;">🕒 ${escapeHtml(u.u_last_login)}</div>
                        </td>
                        <td>
                            <div style="font-size: 0.82rem; color: #ff6b81; font-weight: 600;">❤️ ${formatNumber(u.u_like)} Tim</div>
                            <div style="font-size: 0.82rem; color: #f5cd79; font-weight: 500;">🍫 ${formatNumber(u.u_cp)} CP</div>
                            <div style="font-size: 0.82rem; color: #68d8d6; font-weight: 500;">🍬 ${formatNumber(u.u_candy)} Candy</div>
                        </td>
                        <td>
                            <div style="font-size: 0.82rem; color: #a29bfe; font-weight: 500;">📅 Tân Thủ: <b>${u.attendance_day || 0}/7</b></div>
                            <div style="font-size: 0.82rem; color: #55efc4; font-weight: 500; margin-top: 3px;">🏪 Tiện Lợi: <b>${u.ch2_attendance_day || 0}/7</b></div>
                        </td>
                        <td>
                            <div>${passBadge}</div>
                            <div style="font-size: 0.76rem; color: var(--text-sub); margin-top: 3px;">
                                ${Number(u.star_point || 0).toLocaleString()} điểm &bull; Cấp ${u.star_step || 0}
                            </div>
                        </td>
                        <td style="text-align: right; white-space: nowrap;">
                            <div style="display: inline-flex; gap: 6px; align-items: center; justify-content: flex-end;">
                                <button class="btn-setting-event" onclick="openUserModal('${u.uuid}')" title="Cài đặt sự kiện & tài nguyên cá nhân">
                                    ⚙️ Setting
                                </button>
                                <button class="btn-mail" onclick="openSendMailModal('${u.uuid}', '${escapeHtml(u.u_nick)}')" title="Gửi thư và quà riêng cho người chơi này">
                                    ✉️ Thư
                                </button>
                                <button class="${u.is_banned ? 'btn-unban' : 'btn-ban'}" onclick="toggleBan('${u.uuid}', ${!u.is_banned})" title="${u.is_banned ? 'Mở khóa tài khoản' : 'Khóa tài khoản'}">
                                    ${u.is_banned ? '✅ Mở' : '🚫 Ban'}
                                </button>
                                <button class="btn-delete-user" onclick="deleteUser('${u.uuid}', '${escapeHtml(u.u_nick)}')" title="Xóa toàn bộ dữ liệu">
                                    🗑️ Xóa
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

        async function toggleBan(uuid, banState) {
            const actionText = banState ? 'KHÓA (BAN)' : 'MỞ KHÓA';
            if (!confirm(`Bạn có chắc chắn muốn ${actionText} tài khoản người chơi này?\n${banState ? 'Khi bị khóa, game sẽ hiển thị thông báo "Tài khoản của bạn đã bị KHÓA" thay vì lỗi mạng.' : 'Sau khi mở khóa, người chơi sẽ có thể đăng nhập bình thường.'}`)) return;
            try {
                const res = await fetch('/admin/api/user/ban', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ uuid, banned: banState })
                });
                const data = await res.json();
                if (!data.success) throw new Error(data.error || 'Thao tác thất bại');
                showToast(data.message || 'Thành công!');
                loadUsers();
            } catch (e) {
                showToast('❌ Lỗi: ' + e.message, true);
            }
        }

        async function deleteUser(uuid, nick) {
            if (!confirm(`⚠️ CẢNH BÁO NGUY HIỂM!\n\nBạn có chắc chắn muốn XÓA TOÀN BỘ DỮ LIỆU của người chơi [${nick}]?\nToàn bộ tiến trình, Tim, CP, sự kiện sẽ bị xóa vĩnh viễn khỏi server. Khi vào lại game sẽ là tài khoản mới tinh.`)) {
                return;
            }
            try {
                const res = await fetch('/admin/api/user/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ uuid })
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
            const nick = document.getElementById('modal-user-name').innerText;
            deleteUser(uuid, nick);
            closeUserModal();
        }

        function openUserModal(uuid) {
            const u = cachedUsers.find(x => x.uuid === uuid);
            if (!u) {
                showToast('Không tìm thấy người chơi!', true);
                return;
            }
            document.getElementById('modal-uuid').value = u.uuid;
            document.getElementById('modal-user-name').innerText = u.u_nick;
            document.getElementById('modal-user-sub').innerText = `ID: ${u.u_id || '-'} | Seq: #${u.u_seq} | UUID: ${u.uuid}`;
            document.getElementById('modal-user-lastlogin').innerText = `🕒 Đăng nhập gần nhất: ${u.u_last_login}`;
            document.getElementById('modal-is-banned').checked = !!u.is_banned;
            document.getElementById('modal-is-gold').checked = !!u.is_gold;
            document.getElementById('modal-star-point').value = u.star_point || 0;

            // Currencies
            document.getElementById('modal-user-like').innerText = 'Hiện có: ' + formatNumber(u.u_like) + ' Tim';
            document.getElementById('modal-add-like').value = 0;
            document.getElementById('modal-add-cp').value = 0;
            document.getElementById('modal-add-candy').value = 0;
            document.getElementById('modal-set-like').value = '';

            // Attendance (Event 1 - 7 ngày tân thủ)
            const currentClaimed = u.attendance_day || 0;
            const currentNext = Math.min(7, currentClaimed + 1);
            document.getElementById('modal-att-status').innerText = `Đã nhận ${currentClaimed}/7 ngày`;
            if (currentClaimed >= 7) {
                document.getElementById('modal-att-day').value = 'completed';
            } else if (currentClaimed === 6) {
                document.getElementById('modal-att-day').value = 'claim_7';
            } else {
                document.getElementById('modal-att-day').value = 'claim_' + currentNext;
            }
            document.getElementById('modal-att-unlock').checked = true;
            document.getElementById('modal-att-direct-grant').checked = false;

            // Attendance (Event 3 - Cửa hàng tiện lợi hạnh phúc)
            const ch2Claimed = u.ch2_attendance_day || 0;
            const ch2Next = Math.min(7, ch2Claimed + 1);
            document.getElementById('modal-ch2-att-status').innerText = `Đã nhận ${ch2Claimed}/7 ngày`;
            if (ch2Claimed >= 7) {
                document.getElementById('modal-ch2-att-day').value = 'completed';
            } else if (ch2Claimed === 6) {
                document.getElementById('modal-ch2-att-day').value = 'claim_7';
            } else {
                document.getElementById('modal-ch2-att-day').value = 'claim_' + ch2Next;
            }
            document.getElementById('modal-ch2-att-unlock').checked = true;
            document.getElementById('modal-ch2-direct-grant').checked = false;

            document.getElementById('modal-send-mail').checked = false;
            document.getElementById('user-event-modal').classList.add('active');
        }

        function closeUserModal() {
            document.getElementById('user-event-modal').classList.remove('active');
        }

        async function saveUserModal() {
            const uuid = document.getElementById('modal-uuid').value;
            const is_banned = document.getElementById('modal-is-banned').checked;
            const is_gold = document.getElementById('modal-is-gold').checked;
            const star_point = parseInt(document.getElementById('modal-star-point').value) || 0;

            const add_cp = parseInt(document.getElementById('modal-add-cp').value) || 0;
            const add_candy = parseFloat(document.getElementById('modal-add-candy').value) || 0;
            const add_like = parseFloat(document.getElementById('modal-add-like').value) || 0;
            const set_like_val = document.getElementById('modal-set-like').value.trim();

            const attVal = document.getElementById('modal-att-day').value;
            let attendance_day = null;
            let attendance_mode = 'claim_day';
            if (attVal === 'reset') {
                attendance_day = 0;
            } else if (attVal === 'completed') {
                attendance_day = 7;
                attendance_mode = 'complete';
            } else if (attVal.startsWith('claim_')) {
                attendance_day = parseInt(attVal.replace('claim_', ''));
            }

            const unlock_today = document.getElementById('modal-att-unlock').checked;
            const grant_rewards = document.getElementById('modal-att-direct-grant').checked;

            const ch2Val = document.getElementById('modal-ch2-att-day').value;
            let ch2_attendance_day = null;
            let ch2_attendance_mode = 'claim_day';
            if (ch2Val === 'reset') {
                ch2_attendance_day = 0;
            } else if (ch2Val === 'completed') {
                ch2_attendance_day = 7;
                ch2_attendance_mode = 'complete';
            } else if (ch2Val.startsWith('claim_')) {
                ch2_attendance_day = parseInt(ch2Val.replace('claim_', ''));
            }

            const ch2_unlock_today = document.getElementById('modal-ch2-att-unlock').checked;
            const grant_ch2_rewards = document.getElementById('modal-ch2-direct-grant').checked;

            const send_mail = document.getElementById('modal-send-mail').checked;

            try {
                const res = await fetch('/admin/api/user/event_settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        uuid,
                        is_banned,
                        is_gold,
                        star_point,
                        add_cp,
                        add_candy,
                        add_like,
                        set_like: set_like_val ? set_like_val : null,
                        attendance_day,
                        attendance_mode,
                        attendance_unlock_today: unlock_today,
                        grant_rewards,
                        ch2_attendance_day,
                        ch2_attendance_mode,
                        ch2_unlock_today,
                        grant_ch2_rewards,
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

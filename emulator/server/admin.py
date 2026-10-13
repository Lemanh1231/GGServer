"""Admin Web Dashboard for Guitar Girl Server Event Management."""
import json
from server import event_manager

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Guitar Girl - Quản lý Sự kiện (Event Manager)</title>
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
            --switch-off: #2c324b;
            --switch-on: #38ef7d;
            --danger: #ff4757;
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
            max-width: 900px;
            margin: 0 auto;
        }
        header {
            text-align: center;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--card-border);
        }
        .logo-title {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            margin-bottom: 8px;
        }
        .logo-icon {
            font-size: 2rem;
        }
        h1 {
            font-size: 1.6rem;
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
        .action-bar {
            position: sticky;
            top: 12px;
            z-index: 100;
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
            background: rgba(24, 27, 41, 0.85);
            backdrop-filter: blur(10px);
            padding: 12px;
            border-radius: 14px;
            border: 1px solid var(--card-border);
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }
        .btn {
            flex: 1;
            padding: 12px 18px;
            border-radius: 10px;
            border: none;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
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
            padding-bottom: 4px;
        }
        .event-info {
            flex: 1;
        }
        .event-name {
            font-weight: 600;
            font-size: 0.95rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .event-badge {
            font-size: 0.7rem;
            padding: 2px 6px;
            border-radius: 6px;
            background: #262c45;
            color: #a0aec0;
            font-family: monospace;
        }
        .event-desc {
            font-size: 0.8rem;
            color: var(--text-sub);
            margin-top: 4px;
            line-height: 1.35;
        }
        /* Switch Toggle */
        .switch {
            position: relative;
            display: inline-block;
            width: 52px;
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
            left: 3px;
            bottom: 3px;
            background-color: white;
            transition: .3s;
            border-radius: 50%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        input:checked + .slider {
            background-color: var(--switch-on);
            box-shadow: 0 0 10px rgba(56, 239, 125, 0.4);
        }
        input:checked + .slider:before {
            transform: translateX(24px);
        }
        /* Form Controls */
        .form-group {
            margin-top: 14px;
            padding-top: 14px;
            border-top: 1px solid rgba(255,255,255,0.06);
        }
        .form-label {
            display: block;
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-sub);
            margin-bottom: 8px;
        }
        select {
            width: 100%;
            padding: 12px 14px;
            background: #202438;
            border: 1px solid var(--card-border);
            border-radius: 10px;
            color: var(--text-main);
            font-size: 0.9rem;
            outline: none;
            transition: border-color 0.2s;
        }
        select:focus {
            border-color: var(--accent-pink);
        }
        /* Toast Notification */
        #toast {
            position: fixed;
            bottom: 24px;
            right: 24px;
            background: #1e243d;
            border-left: 4px solid var(--accent-cyan);
            color: white;
            padding: 14px 20px;
            border-radius: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            font-size: 0.9rem;
            display: none;
            z-index: 1000;
            animation: fadeIn 0.3s;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
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
                <h1>Guitar Girl - Quản lý Sự kiện</h1>
            </div>
            <p class="subtitle">Điều khiển bật/tắt toàn bộ sự kiện ingame trong runtime (Hot-Reload tức thì)</p>
            <div class="server-status">
                <span class="status-dot"></span>
                <span>Server Trực Tuyến &bull; Zero-Downtime</span>
            </div>
        </header>

        <div class="action-bar" style="flex-wrap: wrap;">
            <button class="btn btn-secondary" onclick="loadConfig()">🔄 Tải lại cấu hình</button>
            <button class="btn btn-primary" onclick="saveConfig()">💾 Lưu thay đổi</button>
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
                    <div class="event-name">Mở khóa Thẻ Sao Gold Trả Phí (Paid Pass)</div>
                    <div class="event-desc">Cho phép nhận toàn bộ phần thưởng cao cấp hàng trên (Gold rewards)</div>
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
                <div class="card-title">📬 Gửi Thư & Tặng Quà Trực Tiếp Vào Game (Live In-Game Push)</div>
                <span style="font-size:0.8rem; color:var(--text-sub)">Đồng bộ tức thì không cần out game</span>
            </div>
            <p style="font-size:0.85rem; color:var(--text-sub); margin-bottom: 12px;">
                Gửi thư thông báo và tặng tài nguyên trực tiếp vào Hộp thư in-game. Client đang chơi game sẽ tự động hiện dấu chấm đỏ (Red Dot) lập tức mà không cần thoát game!
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
            <button class="btn btn-primary" style="width:100%; padding:10px;" onclick="sendDirectMail()">🚀 Gửi Thư & Quà Vào Game Ngay</button>
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

    <div id="toast"></div>

    <script>
        let currentConfig = null;
        let seasonsList = [];

        function showToast(msg, isError = false) {
            const t = document.getElementById('toast');
            t.innerText = msg;
            t.style.borderLeftColor = isError ? 'var(--danger)' : 'var(--accent-cyan)';
            t.style.display = 'block';
            setTimeout(() => { t.style.display = 'none'; }, 3500);
        }

        async function loadConfig() {
            try {
                const res = await fetch('/admin/api/events');
                const data = await res.json();
                if (!data.success) throw new Error('Không thể tải cấu hình');
                currentConfig = data.config;
                seasonsList = data.seasons || [];
                renderUI();
                showToast('Đã tải cấu hình mới nhất từ server!');
            } catch (e) {
                showToast('Lỗi: ' + e.message, true);
            }
        }

        function renderUI() {
            if (!currentConfig) return;

            // 1. Attendance Events
            const attContainer = document.getElementById('attendance-list');
            attContainer.innerHTML = '';
            const attEvents = currentConfig.attendance_events || {};
            for (const [key, item] of Object.entries(attEvents)) {
                const div = document.createElement('div');
                div.className = 'event-item';
                div.innerHTML = `
                    <div class="event-info">
                        <div class="event-name">
                            ${item.name}
                            <span class="event-badge">ID: ${key}</span>
                        </div>
                        <div class="event-desc">${item.description || ''}</div>
                    </div>
                    <label class="switch">
                        <input type="checkbox" data-att-id="${key}" ${item.enabled ? 'checked' : ''}>
                        <span class="slider"></span>
                    </label>
                `;
                attContainer.appendChild(div);
            }

            // 2. Star Pass
            const sp = currentConfig.star_pass || {};
            document.getElementById('sp-enabled').checked = !!sp.enabled;
            document.getElementById('sp-gold').checked = !!sp.paid_card_enabled;

            const seasonSelect = document.getElementById('sp-season');
            seasonSelect.innerHTML = '';
            seasonsList.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.id;
                opt.text = `Mùa ${s.id}: ${s.name_vi} (${s.name_en})`;
                if (s.id === sp.active_season) {
                    opt.selected = true;
                }
                seasonSelect.appendChild(opt);
            });

            // 3. Pass Goods Sale
            const pgs = currentConfig.pass_goods_sale || {};
            document.getElementById('pgs-enabled').checked = !!pgs.enabled;

            // 4. Meowfest
            const mf = currentConfig.meowfest || {};
            document.getElementById('mf-enabled').checked = !!mf.enabled;
            if (mf.name) document.getElementById('mf-name').innerText = mf.name;
            if (mf.description) document.getElementById('mf-desc').innerText = mf.description;

            // 5. Chapter 3 Tour
            const c3 = currentConfig.chapter3_tour || {};
            document.getElementById('c3-enabled').checked = !!c3.enabled;
            if (c3.name) document.getElementById('c3-name').innerText = c3.name;
            if (c3.description) document.getElementById('c3-desc').innerText = c3.description;

            // 6. Weather Festival
            const wf = currentConfig.weather_festival || {};
            document.getElementById('wf-snow-enabled').checked = !!wf.snow_enabled;
            document.getElementById('wf-cherry-enabled').checked = !!wf.cherry_blossom_enabled;

            // 7. Fan Art Costume
            const fac = currentConfig.fan_art_costume || {};
            document.getElementById('fac-enabled').checked = !!fac.enabled;

            // 8. Event Ranking
            const er = currentConfig.event_ranking || {};
            document.getElementById('er-enabled').checked = !!er.enabled;
        }

        async function saveConfig() {
            if (!currentConfig) return;

            // Collect UI state
            const attCheckboxes = document.querySelectorAll('[data-att-id]');
            attCheckboxes.forEach(cb => {
                const id = cb.getAttribute('data-att-id');
                if (currentConfig.attendance_events[id]) {
                    currentConfig.attendance_events[id].enabled = cb.checked;
                }
            });

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

        window.onload = loadConfig;
    </script>
</body>
</html>
"""

def get_admin_html():
    return DASHBOARD_HTML

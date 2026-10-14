"""Download Landing Page for Guitar Girl Patched APK."""
import os

DOWNLOAD_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tải Guitar Girl v8.0.0 - Private Server</title>
    <style>
        :root {
            --bg-color: #0c0e17;
            --card-bg: #16192b;
            --card-border: #282e4b;
            --text-main: #f0f3ff;
            --text-sub: #8d9bb0;
            --accent-pink: #ff5e97;
            --accent-green: #2ed573;
            --accent-cyan: #00cec9;
            --accent-purple: #a29bfe;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: radial-gradient(circle at 50% 10%, #1c2140 0%, var(--bg-color) 75%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px 16px;
        }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            max-width: 580px;
            width: 100%;
            padding: 36px 28px;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        .card::before {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; height: 5px;
            background: linear-gradient(90deg, #ff5e97, #a29bfe, #00cec9);
        }
        .logo-icon {
            font-size: 3.5rem;
            margin-bottom: 12px;
            display: inline-block;
            filter: drop-shadow(0 4px 12px rgba(255, 94, 151, 0.4));
        }
        h1 {
            font-size: 1.85rem;
            font-weight: 800;
            margin-bottom: 6px;
            background: linear-gradient(135deg, #ff8eb6, #a29bfe, #74b9ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            color: var(--text-sub);
            font-size: 0.95rem;
            margin-bottom: 22px;
        }
        .badge-list {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 8px;
            margin-bottom: 26px;
        }
        .badge {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 6px 14px;
            font-size: 0.8rem;
            color: #d1d8e0;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .badge.highlight {
            border-color: rgba(46, 213, 115, 0.4);
            background: rgba(46, 213, 115, 0.1);
            color: var(--accent-green);
            font-weight: 600;
        }
        .download-box {
            background: rgba(0, 0, 0, 0.25);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            padding: 20px;
            margin-bottom: 26px;
        }
        .file-info {
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            color: var(--text-sub);
            margin-bottom: 16px;
            padding: 0 4px;
        }
        .file-info strong {
            color: var(--text-main);
        }
        .btn-download {
            display: block;
            width: 100%;
            background: linear-gradient(135deg, #ff5e97, #e056fd);
            color: #fff;
            text-decoration: none;
            font-size: 1.15rem;
            font-weight: 700;
            padding: 16px 20px;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(255, 94, 151, 0.4);
            transition: all 0.2s ease;
            letter-spacing: 0.5px;
        }
        .btn-download:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 30px rgba(255, 94, 151, 0.6);
            filter: brightness(1.05);
        }
        .btn-download:active {
            transform: translateY(1px);
        }
        .guide-box {
            text-align: left;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 20px;
            font-size: 0.85rem;
            line-height: 1.6;
            color: #cbd5e1;
        }
        .guide-title {
            font-weight: 700;
            color: var(--accent-cyan);
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .guide-box ol {
            padding-left: 20px;
        }
        .guide-box li {
            margin-bottom: 4px;
        }
        .footer-links {
            display: flex;
            justify-content: center;
            gap: 16px;
            font-size: 0.85rem;
        }
        .footer-links a {
            color: var(--text-sub);
            text-decoration: none;
            transition: color 0.2s;
        }
        .footer-links a:hover {
            color: var(--accent-pink);
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="logo-icon">🎸</div>
        <h1>Guitar Girl - Private Server</h1>
        <p class="subtitle">Bản cài đặt APK chính thức &bull; Phiên bản v8.0.0 Standalone</p>

        <div class="badge-list">
            <span class="badge highlight">🟢 Server Online (kotori.click)</span>
            <span class="badge">🚫 Đã tách Google Play</span>
            <span class="badge">📦 1 File Cài Đơn</span>
            <span class="badge">☁️ Tự Động Lưu Cloud</span>
        </div>

        <div class="download-box">
            <div class="file-info">
                <span>Tên file: <strong>Guitar_Girl_v8.0.0_NoGooglePlay.apk</strong></span>
                <span>Dung lượng: <strong>~458 MB</strong></span>
            </div>
            <a href="/download/apk" class="btn-download">
                ⬇️ TẢI GAME APK NGAY
            </a>
        </div>

        <div class="guide-box">
            <div class="guide-title">📱 Hướng dẫn cài đặt nhanh:</div>
            <ol>
                <li><strong>Điện thoại Android</strong>: Bấm nút tải ở trên &rarr; Mở file vừa tải để cài đặt (Cho phép cài ứng dụng ngoài nếu máy hỏi) &rarr; Mở game chơi trực tiếp.</li>
                <li><strong>Giả lập PC (BlueStacks / LDPlayer / Nox)</strong>: Tải file APK về &rarr; Kéo thả trực tiếp file APK vào cửa sổ giả lập để cài đặt.</li>
            </ol>
            <p style="margin-top: 8px; font-size: 0.8rem; color: #94a3b8;">
                <em>* Lưu ý: Hãy gỡ bản game cũ trước khi cài đặt bản mới để tránh xung đột chữ ký.</em>
            </p>
        </div>

        <div class="footer-links">
            <a href="/admin">⚙️ Web Admin Dashboard</a>
            <span>&bull;</span>
            <a href="/health">🩺 Kiểm tra Máy Chủ</a>
        </div>
    </div>
</body>
</html>
"""

def get_download_html():
    return DOWNLOAD_HTML

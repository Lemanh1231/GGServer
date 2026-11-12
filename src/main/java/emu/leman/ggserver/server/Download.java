package emu.leman.ggserver.server;

/** Standalone download landing page; APK binaries use root/out, then parent(root)/out. */
public final class Download {
    public static final String APK_FILENAME="Guitar_Girl_v8.0.0_NoGooglePlay.apk";
    private Download() {}
    public static String getDownloadHtml() {
        return """
            <!DOCTYPE html>
            <html lang="vi"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Tải Guitar Girl v8.0.0 - Private Server</title>
            <style>*{box-sizing:border-box}body{font-family:system-ui,sans-serif;background:radial-gradient(circle at 50% 10%,#1c2140,#0c0e17 75%);color:#f0f3ff;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px 16px;margin:0}.card{background:#16192b;border:1px solid #282e4b;border-radius:20px;max-width:580px;padding:36px 28px;text-align:center;box-shadow:0 20px 50px #0008}h1{color:#ff8eb6}p{color:#cbd5e1}.badge{display:inline-block;border:1px solid #282e4b;border-radius:20px;padding:6px 14px;margin:4px;font-size:.8rem;color:#2ed573}.download{display:block;background:linear-gradient(135deg,#ff5e97,#e056fd);padding:16px;border-radius:12px;color:white;text-decoration:none;font-weight:700;margin:24px 0}a{color:#00cec9}.guide{text-align:left;font-size:.85rem;line-height:1.6}</style>
            </head><body><main class="card"><div style="font-size:3.5rem">🎸</div><h1>Guitar Girl - Private Server</h1>
             <p>APK tùy chỉnh cho máy chủ riêng &bull; v8.0.0 Standalone</p>
             <span class="badge">Java Server</span><span class="badge">Bản mới: java-8181-v1</span><span class="badge">🛡️ Tự Chuyển Mạch 4 Tên Miền</span>
            <span class="badge">✨ Đồng Bộ UID Chuẩn (#u_seq)</span><span class="badge">👥 Fix Follower CH1/CH2</span>
            <span class="badge">🚫 Đã tách Google Play</span><span class="badge">📦 1 File Cài Đơn</span><span class="badge">☁️ Tự Động Lưu Cloud</span>
             <p>Tên file: <strong>Guitar_Girl_v8.0.0_NoGooglePlay.apk</strong><br>Dung lượng: <strong>~458 MiB</strong></p>
             <a href="/download/Guitar_Girl_v8.0.0_Java_8181.apk" class="download">⬇️ TẢI BẢN MỚI — JAVA 8181</a>
             <p>Liên kết thay thế (cùng bản APK): <a href="/download/Guitar_Girl_v8.0.0_Universal.apk">Guitar_Girl_v8.0.0_Universal.apk</a></p>
             <p>HTTPS: kotori.click · kotorin.click · kotorin.dev · kotorin.me<br><a href="/health">Kiểm tra máy chủ hiện tại</a></p>
            <section class="guide"><h3>📱 Hướng dẫn cài đặt nhanh:</h3><ol>
            <li><strong>Điện thoại Android</strong>: Bấm nút tải ở trên → Mở file vừa tải để cài đặt (Cho phép cài ứng dụng ngoài nếu máy hỏi) → Mở game chơi trực tiếp.</li>
            <li><strong>Giả lập PC (BlueStacks / LDPlayer / Nox)</strong>: Tải file APK về → Kéo thả trực tiếp file APK vào cửa sổ giả lập để cài đặt.</li></ol>
             <p>Nếu đang dùng bản cùng chữ ký, có thể cài cập nhật trực tiếp. <strong>Không gỡ game hoặc xóa dữ liệu</strong> trước khi lưu thông tin tài khoản; guest ID có thể mất khi gỡ ứng dụng.</p>
             <p><em>Bản Google Play/APKPure có thể khác chữ ký. Nếu Android từ chối cập nhật, hãy kiểm tra và sao lưu tài khoản trước, không tự gỡ bản đang chơi.</em></p>
            </section></main></body></html>
            """;
    }
}

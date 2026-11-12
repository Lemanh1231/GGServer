# GGServer Java

Guitar Girl server viết bằng **Java 21**, package `emu.leman.ggserver`.
Nhánh `java-server` chỉ chứa server Java, test Java và tài nguyên runtime cần thiết;
không chứa server/script Python, APK, tài khoản hay cấu hình production.

## Chạy độc lập

Cần JDK 21; Gradle Wrapper được kèm sẵn (lần build đầu cần Internet).

```bash
git clone --branch java-server --single-branch https://github.com/Lemanh1231/GGServer.git
cd GGServer
cp resources/server-config.example.json resources/server-config.json
# Đặt giá trị ngẫu nhiên riêng cho từng biến; không dùng chuỗi ví dụ làm mật khẩu.
export GG_ADMIN_PASSWORD="$(openssl rand -hex 32)"
export GG_SECRET_KEY="$(openssl rand -hex 32)"
./gradlew test fatJar
java -jar build/libs/ggserver-1.0.0-all.jar --config resources/server-config.json
```

Windows dùng `gradlew.bat`. Mẫu mặc định dùng SQLite, bind **127.0.0.1:8181**,
bật bắt buộc session do server cấp. Dữ liệu mới nằm trong `resources/data/`.
Không trỏ bản thử nghiệm vào database hoặc thư mục dữ liệu đang chạy production.

```bash
curl --fail http://127.0.0.1:8181/health
./serverctl.sh start
./serverctl.sh status
./serverctl.sh logs
./serverctl.sh stop
```

Chọn **một** cách chạy: trực tiếp hoặc `serverctl.sh`. Script quản lý chỉ dừng
process do chính nó tạo, không nhận/dừng process chiếm cổng khác. Dừng server trước
khi build đè JAR đang chạy. Có thêm `./eventctl.sh --help` và
`./send-notification.sh --help` cho công cụ quản trị Java.

## Cấu hình và bảo mật

- Chỉnh bản riêng `resources/server-config.json`; file này được `.gitignore`.
- `root` và các thư mục tương đối được resolve từ vị trí file cấu hình.
- Dùng `GG_ADMIN_PASSWORD`, `GG_SECRET_KEY`, `GG_PUBLIC_BASE`, `GG_CDN_URL`,
  `GG_MONGO_URI`, `GG_MONGO_DATABASE` khi cần override bằng môi trường.
- `scripts/common.sh` có thể đọc `.env` hoặc `resources/.env` riêng trong checkout;
  không đọc `.env` ở thư mục cha. Không commit các file này.
- **Luôn đặt admin password mạnh**: mã tương thích cũ có fallback `admin123`
  nếu bỏ trống. Không triển khai với mặc định đó.
- Không tắt `sessions.required` trên server public. Cơ chế guest dựa vào thiết bị
  và session server cấp, không thay thế xác minh mật mã của nhà cung cấp đăng nhập.
- Đặt reverse proxy TLS trước Java nếu public; giữ MongoDB và admin route hạn chế
  bằng firewall/allowlist hoặc VPN. Không log token, request body hay URI có mật khẩu.

Xem [SECURITY.md](SECURITY.md) trước khi public. `.gitignore` chỉ là lớp phòng vệ,
không phát hiện bí mật bị ghi cứng trong source hoặc file đã được track.

## MongoDB có xác thực

Không cần Python. Có thể dùng MongoDB sẵn có hoặc mẫu local ở
[`deploy/mongodb/README.md`](deploy/mongodb/README.md). Đổi trong config riêng:

```json
"database": { "backend": "mongo", "name": "ggserver" }
```

Đặt `GG_MONGO_URI` bằng URI của user ứng dụng có `readWrite` trên đúng database,
không dùng tài khoản root cho Java. URI phải URL-encode ký tự đặc biệt trong mật khẩu.
MongoDB dùng nhiều collection tách biệt cho profile/inventory; xem
[MONGO_COLLECTIONS.md](MONGO_COLLECTIONS.md). Backup phải bao gồm **toàn bộ collection**.
Không tự động restore, import dữ liệu cũ hoặc tạo lại định danh tài khoản khi lỗi kết nối.

## Tài nguyên đi kèm

`resources/schema/`, `resources/gamedata/`, `resources/cdn_files/` và
`resources/static/` cung cấp schema, catalog, bảng AssetBundle tối thiểu và EULA.
Không kèm toàn bộ asset game/APK. Client cần asset nào khác phải được cung cấp riêng.
`broadcast_posts.json` và `post_seq.json` được khởi tạo rỗng; không phải bài đăng,
mail hoặc sequence của server thật. `event_config.json` là cấu hình sự kiện mẫu.

Tài nguyên không được nhúng vào fat JAR: chạy từ checkout hoặc mang cả thư mục
`resources/` bên cạnh. `./gradlew installDist` tạo distribution kèm tài nguyên và
**chỉ cấu hình mẫu**, không đóng gói cấu hình thật; cần tự tạo config và đặt secrets.

## Kiểm thử và công cụ Java

```bash
./gradlew test
./gradlew fatJar
```

Test dùng thư mục/database tạm và MongoDB giả lập trong JVM, không cần Python hay
MongoDB production. Các CLI migration trong package `migration` là Java offline,
chỉ đọc dữ liệu nguồn khi người vận hành gọi rõ ràng. Không phải dependency runtime
và không tự chạy khi khởi động. Sao lưu, dừng mọi writer và dùng dry-run trước khi
thao tác chuyển đổi database.

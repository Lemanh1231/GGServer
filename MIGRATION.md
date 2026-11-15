# Chuyển từ emulator Python sang Java

## Nguyên tắc an toàn

1. Giữ nguyên `emulator/` và các thay đổi chưa commit của dự án gốc.
2. Backup dữ liệu và ba file `event_config.json`, `broadcast_posts.json`, `post_seq.json`.
3. Chạy kiểm thử Java với database tạm trước khi chuyển người chơi.
4. Khi cutover thật, **dừng server Python và Java**. Snapshot nhất quán không tránh
   được mất các cập nhật mới nếu bản Python vẫn tiếp tục nhận request sau snapshot.
5. Không cho cả hai server ghi cùng database. Không dùng `cp database.db` đơn lẻ
   khi SQLite còn dữ liệu chưa checkpoint trong WAL.

## Import vào thư mục Java mới

```bash
cd GGServerJava
./gradlew test fatJar
./gradlew importPythonData
```

Đổi nguồn nếu cần:

```bash
./gradlew importPythonData -PpythonRoot=/absolute/path/to/emulator
```

Nếu database đích đã tồn tại, lệnh sẽ dừng thay vì ghi đè. Chỉ khi thật sự muốn
thay thế, dừng Java và dùng:

```bash
java -cp build/libs/ggserver-1.0.0-all.jar emu.leman.ggserver.migration.ImportPythonData \
  --source ../emulator --root resources --replace
```

`--replace` tạo snapshot backup của database Java cũ trước khi thay thế.
Database nguồn được mở read-only; integrity/schema được kiểm tra trước khi import.
Không import nhầm `emulator/database.db`: bản Python hiện tại sử dụng
**`emulator/data/database.db`**.

## Cấu hình đang hoạt động

Bản project có sẵn snapshot các file cấu hình ở thời điểm chuyển đổi. Nếu chúng
đã đổi trong quá trình thử nghiệm, copy lại từng file sau khi dừng server:

```bash
cp ../emulator/event_config.json ./resources/event_config.json
cp ../emulator/broadcast_posts.json ./resources/broadcast_posts.json
cp ../emulator/post_seq.json ./resources/post_seq.json
```

Không cần chuyển request captures để chạy server. APK trong `../out/` và ADB là
tài nguyên/công cụ triển khai bên ngoài; chúng không được đóng vào executable JAR.

## Rollback

Dừng Java rồi khởi động lại bản Python với **database Python đã backup trước cutover**.
Nếu Java đã nhận tiến trình mới, giữ nguyên database Java và đối chiếu/migrate các
cập nhật đó trước; không ghi đè database nào với giả định tự đồng bộ hai chiều.

## Phạm vi xác nhận

Đối chiếu wire/schema, command inventory, kiểm thử unit/integration và các flow game
có thể tự động hóa. Cần kiểm tra thêm trên APK thật: login/load/save, mua đồ, nhận
thưởng, follower/messenger, Chapter 3, CDN, TLS/proxy và trang quản trị trước production.
Không thay đổi các script khởi động Python của repository gốc trong lần chuyển đổi này.

Java cần build/restart khi sửa mã nguồn handler; không mô phỏng `importlib.reload`
cho các file `.py`. Hot reload cấu hình sự kiện là cơ chế riêng và không yêu cầu
Python runtime. Hiệu năng cần được đo dưới tải thực tế; việc tổ chức OOP hoặc dùng
Java không tự chứng minh server nhanh hơn.

### Giới hạn cần giữ khi vận hành

- Chạy một instance Java cho mỗi thư mục dữ liệu. Khóa nghiệp vụ bảo vệ request
  và thao tác quản trị trong cùng tiến trình, không thay thế distributed lock.
- Gửi broadcast gồm file JSON và nhiều transaction người dùng; một sự cố giữa
  chừng không có rollback xuyên toàn bộ file/database. Giữ backup trước batch lớn.
- Các khác biệt ở input không hợp lệ/replay được ghi trong
  `verification/SOCIAL_DIFFERENCES.md`; kết quả của nguồn Python hiện tại (kể cả
  test baseline có sẵn bị fail) được phân biệt với lỗi chuyển đổi Java.
# Backend MongoDB và session

Server mới chọn MongoDB qua `resources/server-config.json`; không tự động chuyển database
khi khởi động. Xem [hướng dẫn SQLite → MongoDB](src/main/java/emu/leman/ggserver/migration/MONGO_MIGRATION.md)
để dry-run, kiểm tra collision và import tường minh bằng `--apply`.
Giữ nguyên database SQLite gốc và backup; không chạy hai backend ghi song song
trong lúc cutover. Session đang hoạt động không được migration; client đăng nhập lại.

Phần snapshot dưới đây dành cho chế độ **SQLite tương thích**, không import vào MongoDB.

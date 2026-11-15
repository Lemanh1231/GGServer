# GGServer Java

Server Guitar Girl viết bằng **Java 21**, package/application ID **`emu.leman.ggserver`**.
Build và chạy bằng **Gradle Wrapper**; không cần cài Maven hay Gradle hệ thống.

## Audit và bản sửa source mới

- [RPC inventory](RPC_INVENTORY.md) và [logic audit](RPC_LOGIC_AUDIT.md).
- [Session latency audit](REQUEST_LATENCY_AUDIT.md).
- [Các việc còn mở/chờ triển khai](CURRENT_ISSUES.md) và
  [đối chiếu tài liệu lỗi cũ](BUG_DISPOSITION.md).
- [Native patch guard tests](patcher/README.md) (chỉ source, không APK/keystore).

Source đã sửa không đồng nghĩa production hoặc Android UI đã được xác minh.

## Build và chạy

```bash
cd GGServerJava
./gradlew test fatJar
java -jar build/libs/ggserver-1.0.0-all.jar
```

Windows dùng `gradlew.bat`. Lần build đầu cần Internet để tải Gradle và dependency.
Server tự tìm `resources/server-config.json`. Cấu hình chọn **MongoDB**, database
`ggserver`; kiểm tra `database.uri` và bảo đảm MongoDB sẵn sàng trước khi chạy.

```bash
./gradlew run
./gradlew installDist
```

Không chạy bản Python và Java trên cùng cổng hoặc cùng database trong quá trình chuyển đổi.

## Cấu hình

Chỉnh trực tiếp [resources/server-config.json](resources/server-config.json):

```json
{
  "host": "127.0.0.1",
  "port": 8080,
  "root": ".",
  "database": {
    "backend": "mongo",
    "uri": "mongodb://127.0.0.1:27017",
    "name": "ggserver"
  },
  "sessions": {
    "timeoutSeconds": 86400,
    "cleanupSeconds": 60,
    "maxSessions": 10000,
    "required": false
  },
  "folders": {
    "data": "data",
    "cdn": "cdn_files",
    "gamedata": "gamedata",
    "schema": "schema",
    "static": "static",
    "captures": "captures",
    "apk": "../../out"
  }
}
```

`root` và `certificate` tương đối theo thư mục chứa config; các mục `folders`
tương đối theo `root`. CDN/gamedata có thể trỏ ra ổ/thư mục khác bằng đường dẫn
tuyệt đối. `data` chứa file quản trị/chứng chỉ và database khi chọn `sqlite`,
không phải thư mục dữ liệu của tiến trình MongoDB. `event_config.json`,
`broadcast_posts.json`, `post_seq.json` vẫn nằm dưới `root`.

Mặc định `root` chính là **`GGServerJava/resources/`**. Tất cả config, schema,
gamedata, CDN, static và dữ liệu vận hành nằm chung tại đây; không cần truyền
đường dẫn khi chạy. Xem [cây resources và hướng dẫn chuyển layout cũ](resources/README.md).
Admin HTML được nhúng sẵn trong JAR; APK vẫn trỏ tới `out/` của repo để dùng
output patcher hiện có. `.env` trong `resources/` chỉ được shell script nạp;
khi chạy Java trực tiếp hãy export biến môi trường hoặc sửa config.

Đổi file bằng `GG_CONFIG=/path/server-config.json` hoặc `--config FILE`.
Tham số CLI cũ vẫn được hỗ trợ làm override, không bắt buộc khi chạy bình thường.
`https`, `http`, `httpPort`, `certificate`, `certificatePassword`, `publicBase`,
`cdnUrl`, `verbose`, `adminPassword`, `secretKey` cũng nằm trong config.

Biến môi trường ưu tiên hơn file cho `GG_PUBLIC_BASE`/`GG_PUBLIC_HOST`,
`GG_CDN_URL`, `GG_VERBOSE`, `GG_ADMIN_PASSWORD`, `GG_SECRET_KEY`,
`GG_CERT_PASSWORD`, `GG_MONGO_URI`, `GG_MONGO_DATABASE`.
Không commit mật khẩu, private key, database người chơi hoặc capture request.
Không thay package Android của game: `emu.leman.ggserver` là package của **server Java**.

```bash
export GG_PUBLIC_BASE=https://your-domain.example
export GG_ADMIN_PASSWORD='replace-with-a-strong-password'
java -jar build/libs/ggserver-1.0.0-all.jar
```

Dùng reverse proxy để kết thúc TLS nếu triển khai public; giữ backend trên loopback
và chỉ cho proxy tin cậy đặt các header chuyển tiếp IP/domain.
Game dùng `base64(BZip2(Thrift))`, không phải REST/JSON; chỉ auth, admin và một số
endpoint phụ trợ trả JSON hoặc HTML.

Đổi mật khẩu admin trước khi public: để trống hiện vẫn dùng fallback tương thích
`admin123`. Không bật `sessions.required` trước khi kiểm tra client thực sự gửi
token ở tất cả RPC: chế độ mặc định vẫn hỗ trợ request cũ không có token.
Session được lưu trong RAM; restart server làm mất các session đã phát hành.

### MongoDB: các collection dữ liệu người chơi

Backend mới tách profile, kho đồ, khu vực, thư và tiến trình khỏi blob
`users.contents`; `users` giữ định danh/số dư/trạng thái và tham chiếu phiên bản.
Xem [MONGO_COLLECTIONS.md](MONGO_COLLECTIONS.md) để biết schema, cách query dữ liệu
hiện hành, cơ chế lưu nguyên tử và migration có backup. Dữ liệu cũ vẫn đọc được;
không chạy migration live khi chưa xác nhận đúng database và dừng mọi writer.

### Docker + MongoDB

```bash
export GG_ADMIN_PASSWORD='replace-with-a-strong-password'
docker compose up --build -d
```

[resources/docker/server-config.json](resources/docker/server-config.json) bind `0.0.0.0` trong container
và dùng host `mongo`; bản chạy trực tiếp dùng địa chỉ `host` trong config.
MongoDB không được publish cổng ra host. Compose này dành cho một server instance;
triển khai production cần backup, xác thực MongoDB và kiểm tra quyền volume riêng.

### Log gọn kiểu Nebula

Console dùng SLF4J/Logback, không in tên thread/class hay payload mỗi request:

```text
[10:20:30] [INFO] Starting GGServer 1.0.0
[10:20:30] [INFO] Database ready: mongo
[10:20:30] [INFO] Registered 60 game handlers
[10:20:30] [INFO] Listening http://0.0.0.0:8181
[10:20:31] [INFO] SEND: userLogin | 884 B | 61 ms
[10:20:32] [WARN] SEND: buyShop | code=1 | 212 B | 8 ms
```

Trong `resources/server-config.json`:

```json
"verbose": true,
"logging": { "level": "INFO", "file": true }
```

- `verbose=false` (hoặc `GG_VERBOSE=0`): tắt log RPC thành công, giữ startup/cảnh báo/lỗi.
- `logging.level=DEBUG` hoặc `GG_LOG_LEVEL=DEBUG`: thêm dòng `RECV` và thông tin cấu hình.
- File mặc định `resources/logs/latest.log`, có ngày giờ đầy đủ; xoay theo ngày hoặc
  10 MB, nén `.gz`, giữ tối đa 14 ngày và giới hạn archive 256 MB.
- Đổi thư mục bằng `folders.logs`; đặt `logging.file=false` để chỉ log console.
- Lỗi xử lý HTTP/admin vẫn có stack trace, không bị ẩn theo `verbose`.
  Log MongoDB thông thường được giảm xuống WARN. Console không in token/payload/URI database.
- Capture JSON để phân tích protocol vẫn độc lập tại `resources/captures/`;
  đây là dữ liệu nhạy cảm cần quản lý riêng, không phải file log đã xoay vòng.

## Chuyển dữ liệu Python

Xem [MIGRATION.md](MIGRATION.md). Không tự động copy dữ liệu tài khoản khi khởi động.
Có script Python độc lập tại [scripts/sqlite_to_mongo.py](scripts/sqlite_to_mongo.py),
xem [cách dùng và chính sách merge an toàn](scripts/SQLITE_TO_MONGO.md).
Chuyển sang MongoDB theo hướng dẫn
[SQLite → MongoDB](src/main/java/emu/leman/ggserver/migration/MONGO_MIGRATION.md).
Dừng các tiến trình ghi, backup cả SQLite và WAL, rồi chạy dry-run trước:

```bash
java -cp build/libs/ggserver-1.0.0-all.jar \
  emu.leman.ggserver.migration.SqliteToMongo \
  --config resources/server-config.json --source ../emulator/data/database.db --dry-run
```

Chỉ thay `--dry-run` bằng `--apply` sau khi kiểm tra báo cáo; không tự động xóa
database SQLite, không ghi đè tài khoản đã có trong MongoDB.

Nếu cần tiếp tục dùng backend SQLite tương thích, đổi `database.backend` thành
`sqlite` rồi dùng công cụ snapshot cũ:

```bash
./gradlew importPythonData
```

Lệnh này đọc `../emulator/data/database.db`, tạo snapshot nhất quán gồm cả WAL và
ghi vào `./resources/data/database.db`. Mặc định từ chối ghi đè database đã tồn tại.

## Vận hành domain / menu Java

Root `../run.sh` hiện là control center Java (menu, lifecycle an toàn, log,
build/test và kiểm tra HTTPS). Cả 4 domain cũ cùng `/admin` và `/download` đã
chuyển qua Nginx sang Java `8181`. Xem [DEPLOYMENT.md](DEPLOYMENT.md) để vận hành,
kiểm tra APK và rollback có backup; không cần rebuild APK cho cùng 4 domain.

## Kiến trúc

### Game data theo nhóm (APK/schema → catalog)

Java tự load **39 bảng / 4.065 dòng** có tên trường rõ ràng từ
[`resources/gamedata/catalog/`](resources/gamedata/catalog/README.md). Item, skill,
quest, reward, shop, follower, chapter… được chia folder riêng; `manifest.json`
khai báo schema/khóa ID và loader kiểm tra lúc khởi động. Tra ID/field tại
[`TABLES.md`](resources/gamedata/catalog/TABLES.md) và `reference/ids.json`.

Tên trường đối chiếu DTO từ APK; giá trị gameplay hiện có giữ nguồn gốc server/
capture riêng, không giả định toàn bộ bảng có sẵn trong APK. Có tool inventory và
giải TextAsset JSON/CSV cho các lần nghiên cứu APK tiếp theo:
[`scripts/GAME_DATA.md`](scripts/GAME_DATA.md). Python chỉ dùng offline.

```text
src/main/java/emu/leman/ggserver/
├── Main.java / Services.java       # Entry point và khởi tạo dependency
├── config/                        # Cấu hình server và đường dẫn
├── database/                      # StateStore, repository MongoDB/SQLite
├── data/                          # ResourceLoader, DataTable, khóa ID có kiểm tra
├── game/
│   ├── GameContext.java           # Đăng ký và quản lý module
│   ├── GameModule.java
│   ├── GameData.java / ContentCapture.java
│   ├── account/                   # Login, save/load, auth API
│   ├── economy/                   # Shop, currency, reward, attendance
│   ├── social/                    # Follower, mailbox, social reward
│   ├── content/                   # Event, chapter, music
│   └── player/                    # Player, profile manager và profile packet
├── net/                           # Packet, handler registry, session
│   ├── CmdId.java                 # Tập trung tên command và mapping đặc biệt
│   └── codec/                     # Base64/BZip2/Thrift
├── server/                        # HTTP, TLS, CDN, dispatch
│   └── admin/                     # API và HTML quản trị
├── cli/                           # Công cụ vận hành
├── migration/                     # Import và kiểm tra migration
└── util/                          # JSON dùng chung
```

**8 nhóm cấp gốc**, thay vì tách riêng `auth`, `handler`, `module`, `state`,
`codec`, `http`, `admin`. Mỗi tính năng giữ module và helper cạnh nhau, như Nebula;
không tạo thêm `handlers/services/managers/impl` khi chỉ có vài lớp.
Module tự đăng ký command, không có lớp wrapper chỉ chuyển tiếp sang handler.
Các lớp packet/session dùng chung nằm trực tiếp ở `net`, các repository ở
`database` (không cần folder con cho một implementation).

Test có package/thư mục tương ứng với code chính. Thêm tính năng nhỏ vào nhóm
hiện có; chỉ tạo `game/<feature>` mới khi có nghiệp vụ độc lập đủ lớn. Chi tiết
lifecycle/packet/player: [game/README.md](src/main/java/emu/leman/ggserver/game/README.md).

Kiến trúc tham khảo Nebula, nhưng không dùng protobuf, mã hóa hay packet ID của game khác.
Các module giữ nguyên nghiệp vụ cũ, khóa ghi theo canonical account và 60 command;
đợt dọn cấu trúc này không đổi schema database hoặc giao thức,
và không tuyên bố đã chuyển mọi field dữ liệu sang entity Java có kiểu.

`resources/schema/`, `resources/gamedata/`, `resources/cdn_files/`,
`resources/static/` và các file cấu hình JSON được lấy
từ bản Python hiện tại. Đây là dữ liệu tài nguyên, không phải dependency runtime
vào Python. Runtime Java không gọi tiến trình Python.

Tên command khai báo chung tại `net/CmdId.java` (129 tên trong schema, gồm cả
command chưa có handler). Các module dùng `CmdId.USER_LOGIN`, `CmdId.BUY_SHOP`…
thay vì string rải rác. Có 60 handler thực tế; command schema-only giữ fallback
cũ. Schema Thrift vẫn là tài nguyên codec, không phải registry command bên ngoài.

## Kiểm chứng

```bash
./gradlew test
```

Các công cụ trong `verification/` dùng Python làm oracle kiểm thử giao thức/nghiệp vụ,
không phải thành phần chạy server. Chạy chúng trên database tạm, không trên dữ liệu thật.
Kết quả kiểm thử và giới hạn kiểm chứng của lần chuyển đổi được ghi riêng trong
`verification/`; việc build thành công không tự nó chứng minh mọi hành vi đã tương đương.

## Công cụ vận hành

```bash
./serverctl.sh start
./serverctl.sh status
./serverctl.sh stop
./eventctl.sh list
./eventctl.sh season 8
./eventctl.sh enable meowfest
./send-notification.sh --title 'Thông báo' --memo 'Cảm ơn bạn!' --cp 100 --cookie 10
```

Gửi thư cần server Java đang chạy và `GG_ADMIN_PASSWORD` hợp lệ. Các script shell
cần Bash/Linux, `curl` và `flock`; Java server vẫn có thể chạy trực tiếp trên nền
tảng có Java 21. Không build ghi đè JAR đang được JVM chạy: dừng server trước khi
build/redeploy hoặc triển khai bằng tên JAR phiên bản riêng.
# Quy ước giờ gameplay — UTC+7

Source hiện tại dùng `Asia/Ho_Chi_Minh` cho lịch gameplay, ngày điểm danh,
daily/shop, tháng/năm Pass và `server_time.datetime`/`getServerTime.datetime`.
Mốc đổi ngày là **00:00 Việt Nam (17:00 UTC ngày trước)**, độc lập timezone của
host/JVM. Unix timestamp và các cooldown tính theo số giây không bị cộng/trừ7h.
Không chuyển đổi lại receipt hoặc timestamp lịch sử. Việc sửa source không có
nghĩa binary production đã được deploy; kiểm JAR/version trước khi vận hành.

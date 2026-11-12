# Game catalog — dữ liệu có tên trường, chia theo tính năng

Đây là nguồn dữ liệu được Java ưu tiên load khi `catalog/` tồn tại. Không cần
tham số khởi động, Python hay UnityPy ở runtime. Không tự quét mọi `.json` trong
thư mục: chỉ load các file được khai báo trong `manifest.json`.

## Cấu trúc

```text
catalog/
├── manifest.json            # Version, nguồn + SHA-256, schema, file, khóa từng bảng
├── TABLES.md                # 39 bảng và từ điển tên/type/Thrift ID của mọi trường
├── tables/                  # Giá trị dùng cho nghiệp vụ server
│   ├── items/               # Consume, costume, prop/level, guitar, ticket, gift
│   ├── skills/              # Skill, buff
│   ├── quests/              # Achievement, daily mission, follower quest
│   ├── followers/           # Follower, profile, profile level
│   ├── characters/          # Character, unit, fan level
│   ├── music/               # Music, level
│   ├── rewards/             # Reward group, drop candidate, select reward
│   ├── shops/               # Product, pass goods
│   ├── passes/              # Season, rules, reward, reward information
│   ├── chapters/            # Stage, score, chapter
│   ├── ads/                 # Placement, level
│   ├── events/              # Meowfest, schedule
│   └── localization/        # String, notification, local push
├── client/                  # Chỉ những bảng capture khác giá trị server
│   ├── music/music.json
│   ├── followers/followers.json
│   └── shops/products.json
└── reference/               # Công cụ tra cứu, không tự đưa vào wire response
    ├── ids.json             # Khóa ID + nhãn tiếng Anh, theo từng bảng
    ├── client_enums.json    # 24 enum client trích từ dump IL2CPP
    └── apk_inventory.json   # Hash APK, 12 TextAsset, phân loại và giới hạn lần quét
```

## Nguồn và giới hạn

- **Tên trường/type/Thrift ID**: schema suy ra từ DTO của APK; đã đối chiếu tên
  39 DTO với `work/out/dump.cs`. Không gán nghĩa mới cho trường chưa hiểu.
- **4.065 dòng dữ liệu gameplay**: `game_data.json` hiện có của server, không
  tuyên bố tất cả giá trị này được nhúng trong APK.
- **Client variant**: capture `getGameDataList.b64`. Có khác biệt giá hiển thị shop
  và biểu diễn số DOUBLE lớn; giữ riêng để không thay đổi kinh tế hay wire cũ.
  Sửa bảng server không tự sửa client variant; phải review cả hai khi cần.
- `reference/client_enums.json`: giữ nguyên tên/số enum, kể cả tên bị obfuscate.
  Enum UI không phải bằng chứng rằng server đã triển khai tính năng tương ứng.
- Quét 3 APK hiện có tìm được 12 TextAsset, gồm intro CSV, localization mẫu,
  animation Spine và cấu hình phụ trợ. Không tìm thấy toàn bộ 39 bảng gameplay
  dạng JSON TextAsset trong APK. MonoBehaviour bị strip cần type tree/đối chiếu
  code riêng; không được diễn giải dữ liệu nhị phân bằng phỏng đoán.

## Quy tắc ID và load

- ID có phạm vi **từng bảng**, không phải một ID chung cho mọi đồ vật.
- `Fan` dùng khóa ghép `(i_Area, i_Grade)`; `music_level` dùng `i_Level`;
  `percent` và `ad_level` có ID ở trường 6. Không mặc định cột 1 luôn unique.
- Không gom reward theo group thành một dòng: dùng `matching()` để giữ mọi phần
  thưởng/candidate. Thứ tự row và field vắng mặt giữ nguyên.
- Loader từ chối thiếu bảng, sai schema/type, trùng khóa, sai số dòng và file
  vượt khỏi catalog. Catalog lỗi **không fallback âm thầm** sang file cũ.
- `game_data.json` / `.b64` cũ được giữ làm baseline tương thích và dùng khi
  deployment chưa có thư mục catalog. Không sửa đồng thời hai nguồn khác nhau.
- Không hot reload: sửa file, kiểm tra rồi restart để mỗi process dùng một bộ
  dữ liệu nhất quán. Tài khoản/session không nằm trong catalog.

## Dùng khi viết tính năng mới

```java
var skill = services.gameData.resource("skill").find(1).orElseThrow();
var quests = services.gameData.resource("followerquest").rows();
var fanLevel = services.gameData.resource("Fan").find(1, 2);
var candidates = services.gameData.resource("percent").matching("i_GroupID", 301010);
```

`DataTable` trả bản sao để caller không sửa nhầm resource cache. Code cũ vẫn dùng
`table(8)` / `row(8, id)` với tên cột số như trước; chúng đọc từ cùng catalog.
Named resource API là snapshot lúc load, không phải view của các map mutable
legacy dùng trong fixture/test. Không sửa `GameData.data()` để hot patch runtime.

## Cập nhật an toàn

Nhánh Java-only không kèm bộ trích xuất dữ liệu offline. Chỉnh dữ liệu trong
thư mục riêng, review diff và chạy `./gradlew test fatJar` trước khi triển khai.
`rowCount` là số dòng mong đợi:
khi thêm/xóa row có chủ đích cần cập nhật rowCount của bảng và tổng manifest.
Nguồn SHA-256 ghi nhận baseline export, không phải chữ ký bảo mật cho file chỉnh tay.
Chạy wire audit trên server disposable sau khi thay đổi kinh tế/quest/reward.

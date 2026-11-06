# 🎸 Guitar Girl Private Server Emulator (GGServer)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Android%207.0%2B%20%7C%20BlueStacks-3DDC84.svg?logo=android&logoColor=white)](https://developer.android.com/)
[![Protocol](https://img.shields.io/badge/Protocol-Apache%20Thrift%20Binary-00599C.svg?logo=apache&logoColor=white)](https://thrift.apache.org/)
[![Failover](https://img.shields.io/badge/Network-4--Domain%20Active--Passive%20Failover-00b894.svg)](#en-failover)
[![Web Admin](https://img.shields.io/badge/Web%20Admin-English%20%7C%20Tiếng%20Việt-E03E2D.svg)](#en-admin)
[![License](https://img.shields.io/badge/License-Educational%20%2F%20Preservation-6f42c1.svg)](#full-legal-disclaimer)

> **Bilingual Documentation / Tài liệu Song ngữ**:  
> 🇬🇧 **[English Documentation](#en)** &nbsp;|&nbsp; 🇻🇳 **[Tài liệu Tiếng Việt](#vi)** &nbsp;|&nbsp; ⚖️ **[Disclaimer / Miễn trừ trách nhiệm](#full-legal-disclaimer)**

---

<a id="disclaimer"></a>
## ⚖️ Disclaimer / Miễn trừ trách nhiệm

> [!IMPORTANT]
> **English**: This project is strictly created for **educational, non-commercial, historical preservation, and digital archival purposes** following the official End-of-Service (EOS) of the mobile game *Guitar Girl* (v8.0.0).  
> - **No Affiliation**: This project is independent and is **NOT** affiliated with, endorsed by, sponsored by, or connected to **NEOWIZ Corp.**, **StickyHands Inc.**, or any of their parent companies, subsidiaries, or affiliates.
> - **Intellectual Property**: All trademarks, game titles, character designs, 2D/3D art, illustrations, animations, musical compositions, sound effects, story scripts, and proprietary game assets belong exclusively to **NEOWIZ Corp.** and **StickyHands Inc.**
> - **Non-Commercial**: This repository does not sell anything, does not solicit donations, and contains zero monetization or real-money transactions.
> - **No Copyrighted Binary Redistribution**: This repository does not distribute copyrighted original APK files or extracted proprietary assets. Users must provide their own legitimately acquired client binaries.
> - **No Warranty**: Provided on an "AS IS" basis without warranty of any kind.
>
> *(See the [full legal disclaimer section](#full-legal-disclaimer) at the bottom for comprehensive clauses).*

> [!IMPORTANT]
> **Tiếng Việt**: Dự án này được phát triển hoàn toàn vì mục đích **học tập, nghiên cứu kỹ thuật đảo ngược, bảo tồn di sản số và lưu trữ phi thương mại** sau khi trò chơi di động *Guitar Girl* (phiên bản v8.0.0) chính thức đóng cửa (End-of-Service).  
> - **Không liên kết**: Dự án hoàn toàn độc lập và **KHÔNG** liên kết, không được chứng thực, tài trợ hay trực thuộc **NEOWIZ Corp.**, **StickyHands Inc.** hay bất kỳ công ty liên kết nào.
> - **Quyền sở hữu trí tuệ**: Toàn bộ nhãn hiệu, tiêu đề trò chơi, thiết kế nhân vật, đồ họa 2D/3D, hình minh họa, hoạt ảnh, tác phẩm âm nhạc, hiệu ứng âm thanh, kịch bản cốt truyện và tài nguyên trò chơi thuộc quyền sở hữu trí tuệ độc quyền của **NEOWIZ Corp.** và **StickyHands Inc.**
> - **Phi thương mại**: Dự án hoàn toàn miễn phí, không thương mại hóa, không nhận quyên góp và không có bất kỳ tính năng thanh toán tiền thật nào.
> - **Không phân phối tệp bản quyền**: Kho lưu trữ này không phân phối file APK gốc có bản quyền hoặc tài nguyên trích xuất độc quyền. Người dùng cần tự chuẩn bị tệp cài đặt hợp pháp của mình.
> - **Miễn trừ bảo hành**: Phần mềm được cung cấp "NGUYÊN TRẠNG" (AS IS) mà không có bất kỳ bảo đảm nào.
>
> *(Xem [điều khoản miễn trừ trách nhiệm pháp lý chi tiết](#full-legal-disclaimer) ở cuối tài liệu).*

---

<a id="en"></a>
# 🇬🇧 English

A complete private server revival emulator, multi-domain high-availability client patcher, and live telemetry control suite for the End-of-Service (EOS) mobile game **Guitar Girl** (*v8.0.0* by Neowiz / StickyHands).

GGServer faithfully reconstructs the game's Apache Thrift Binary RPC protocol, PmangPlus Guest authentication, NeonAPI endpoints, CDN AssetBundle delivery, live seasonal events, and BigNumber economy engine—paired with an interactive Dual-Column Terminal UI (`run.sh`), domain-aware packet captures, and a bilingual Web Admin Dashboard (`/admin`).

---

### 📑 English Table of Contents
1. [Key Features](#en-features)
2. [Multi-Domain Active-Passive Failover](#en-failover)
3. [Project Architecture](#en-architecture)
4. [Prerequisites](#en-prerequisites)
5. [Quick Start Guide](#en-quickstart)
6. [Live TUI Control Center & Domain Telemetry](#en-tui)
7. [Web Admin Dashboard & Download Portal](#en-admin)
8. [CLI Management Utilities](#en-cli)
9. [Technical Documentation](#en-docs)

---

<a id="en-features"></a>
### ✨ Key Features

#### 🎮 Full Gameplay Restoration & Save Protection
- **All 3 Story Chapters Fully Playable**:
  - **Chapter 1 (Guitar Girl's Room)**: Unlock and chat with **all 15/15 followers** (Joy, Convenience Store Friend, Homeroom Teacher, Quiet Senior, Moa, Elle, Amber, Yeri, Mocha Latte, Nova, Sua, Jae, etc.), including group chat rooms and authentic story DAG triggers.
  - **Chapter 2 (Sweet Bakery)**: Seamless storyline and chat progression connecting original followers and 8 Chapter 2 followers (Reading Fox, Ruby, Alex, Busking TV, Sora, Jessica) across chat rooms 12, 16, and 17.
  - **Chapter 3 (Sunshine High School)**: Complete Tour mode stages `1001–2010` with authentic weighted Encore gift drops and preserved Moa tutorial intro sequence.
- **Anti-Rollback Level & Save Synchronization**:
  - Stabilized `getUpdateTime` and refreshed `server_time` handshakes prevent startup hangs or level rollbacks.
  - Safe two-way `userSave` merging guarantees server-granted items, costumes, guitars, followers, and levels are never overwritten by stale client snapshots.
- **Music Discs & BigNumber Economy (`currency.py`)**:
  - All 50 music discs restored (26 in Area 1, 24 in Area 2), including Mozart's Piano Sonata event disc.
  - Solves 64-bit integer overflow (`> 1.84e19`) across all 702 Unity IL2CPP Alphabet tiers (`A` through `ZZ`, up to $10^{2109}$) with live formatting previews in Web Admin.

#### 🎁 Live Events & Hardened Mailbox
- **Star Pass (Seasons 1–13)**: Switch between all 13 official localized Star Pass seasons and purchase Live Slots directly in the Star Pass Goods Shop (`item_buy` category 20).
- **Attendance & Weather Festivals**: 7-Day Novice Attendance, Chapter 2 Attendance, Meowfest, and Snow / Cherry Blossom room weather toggles with hot-reload from Web Admin.
- **Honkai: Star Rail-Style Mailbox (`post.py`)**:
  - New accounts receive only a clean Welcome Mail—never flooded with historical broadcasts sent prior to registration.
  - Strictly monotonic global `idx` allocator (`post_seq.json` + SQLite scan) prevents ID collisions between private admin gifts and server-wide broadcasts.
  - Full support for **"Claim All" (`type=1` / `idx=0`)** batch claiming and 12 client languages (`ko`, `en`, `jp`, `zh_chs`, `zh_cht`, `vi`, `es`, `it`, `id`, `th`, `pt`, `hi`).

#### 🛠️ Standalone Universal APK & In-Place Upgrades
- **Rootless & Google Play-Free**: Works on physical Android 7.0+ phones and emulators (BlueStacks, LDPlayer, Nox) without root or Google Play Games.
- **Dalvik & ARM64 IL2CPP Patching**:
  - Automatic PmangPlus Guest login, automatic EULA acceptance, and `AppSecurityValidator` signature bypass.
  - Unlocks Push Notification toggles, CP free/paid breakdown in Settings, and Star Pass Live Slot interactive popups.
  - Synchronizes in-game `UID: #<u_seq>` display (replacing legacy USN) to match Web Admin 100%.
- **Seamless In-Place Updates**: Consistent `gg.keystore` signing (v1/v2/v3) allows players to install new server APK updates directly on top of existing ones without uninstalling or losing their `device_uuid` / progress.

---

<a id="en-failover"></a>
### 🛡️ Multi-Domain Active-Passive Failover

To protect players against regional ISP blocks, DNS failures, or domain outages, the patched APK embeds an in-process loopback HTTP-to-HTTPS gateway (`DomainFailoverGateway` + `MultiDomainFailoverProviderV1` compiled into `classes5.dex`):

1. **Zero Idle Overhead (Sticky Primary / Active-Passive)**:
   - On launch, the gateway binds locally to `http://127.0.0.1:28765` and routes Unity traffic to **1 active HTTPS domain** (remembering the last healthy domain in `SharedPreferences`).
   - As long as the active domain responds normally, **zero connections and zero DNS queries** are made to the remaining 3 backup domains.
2. **Instant Transparent Mid-Session Failover**:
   - Only when the active domain encounters a network/DNS/TLS failure, timeout, or HTTP `5xx` / `408` / `429` error does the gateway automatically switch to the next configured domain, replay the exact Thrift RPC or CDN AssetBundle request in-flight, and persist the newly promoted healthy domain.
3. **Dynamic Multi-Domain Server Routing (`app.py`)**:
   - A single GGServer instance serves any number of SSL domains behind Nginx/Cloudflare simultaneously, dynamically adapting `Host`, `X-Forwarded-Proto`, and `X-GG-Local-Proxy` headers.

---

<a id="en-architecture"></a>
### 📂 Project Architecture

```text
GGServer/
├── run.sh                           # Unified Server Control Center (Detached daemon + Live TUI)
├── tools/
│   └── dashboard.py                 # Dual-Column Live TUI Monitor & Domain Telemetry Table
├── emulator/                        # Python 3 Private Server Emulator
│   ├── run.py                       # Main server entrypoint (HTTP + Thrift Binary RPC)
│   ├── serverctl.sh                 # CLI process controller (start/stop/restart/status/log)
│   ├── eventctl.sh / eventctl.py    # Event manager CLI & broadcast mailer
│   ├── broadcast_posts.json         # Multi-language broadcast mailbox store
│   ├── event_config.json            # Runtime Star Pass, Attendance & Weather configuration
│   ├── gamedata/                    # Static game data tables & CDN AssetBundles
│   ├── schema/                      # Extracted Thrift DTO schemas
│   ├── data/                        # SQLite player database (local-only, gitignored)
│   ├── captures/                    # Domain-tagged JSON RPC captures (local-only, gitignored)
│   └── server/                      # Core backend modules
│       ├── app.py                   # Multi-domain HTTP router, domain logger & packet capturer
│       ├── admin.py                 # Bilingual Web Admin Dashboard (/admin)
│       ├── download.py              # Standalone APK Download Landing Page (/download)
│       ├── state.py                 # Atomic SQLite persistence, IP & domain tracking
│       ├── currency.py              # BigNumber currency engine (A..ZZ)
│       ├── event_manager.py         # Live Star Pass & Attendance controller
│       └── handlers/                # Thrift RPC handlers (auth, follower, music, post, shop...)
├── patcher/                         # Client APK Patcher & Failover Compiler
│   ├── build.sh                     # Automated compile, patch, merge & sign pipeline
│   ├── patch_apk.py                 # Dalvik bytecode, classes5.dex & metadata patcher
│   ├── merge_apk.py                 # AXML manifest patcher, ARM64 patcher & Split APK merger
│   ├── patch_metadata.py            # Rewrites API URLs inside global-metadata.dat
│   ├── classes5.dex                 # Compiled Multi-Domain Failover Gateway DEX
│   ├── java/                        # Java source for DomainFailoverGateway & ContentProvider
│   └── uber-apk-signer.jar          # APK v1/v2/v3 signing utility
├── orig_apk/                        # User-supplied original v8.0.0 split APKs (gitignored)
├── out/                             # Patched & signed output APKs (gitignored)
├── BUG.md                           # Detailed analysis of 39+ reverse-engineered bug fixes
├── ANDROID_SETUP.md                 # Setup guide for BlueStacks & Android devices
├── PROTOCOL.md                      # Apache Thrift Binary RPC specification
└── README.md                        # Project documentation (this file)
```

---

<a id="en-prerequisites"></a>
### 💻 Prerequisites

- **OS**: Linux, macOS, or Windows (WSL2 recommended)
- **Python**: `3.10+`
- **Java**: OpenJDK `17+` or `21+` (for APK signing and optional `classes5.dex` recompilation)
- **ADB** *(optional)*: `android-tools-adb` if installing via USB / emulator command line

```bash
sudo apt update
sudo apt install -y python3 python3-pip openjdk-21-jdk-headless android-tools-adb zip unzip
```

---

<a id="en-quickstart"></a>
### 🚀 Quick Start Guide

#### Step 1: Prepare Original v8.0.0 Split APKs
Place the 3 original *Guitar Girl v8.0.0* split APKs into `orig_apk/`:
- `orig_apk/com.neowiz.game.guitargirl.apk`
- `orig_apk/config.arm64_v8a.apk`
- `orig_apk/base_assets.apk`

#### Step 2: Patch & Build Standalone APK
Choose the network mode matching your deployment:

```bash
# Option A (Default): 4-Domain Active-Passive Failover APK (via local 127.0.0.1:28765 gateway)
bash patcher/build.sh --multidomain

# Option B: Single Public HTTPS Domain
bash patcher/build.sh https://your-domain.example

# Option C: Local LAN HTTP Server
bash patcher/build.sh http://192.168.1.50:8080
```

Output APKs are generated in `out/`:
- `out/Guitar_Girl_v8.0.0_NoGooglePlay.apk` *(Recommended standalone build)*
- `out/Guitar_Girl_v8.0.0_Universal.apk`

#### Step 3: Launch the Server
Configure `.env` (optional: `PORT=8080`, `GG_PUBLIC_BASE=https://your-domain.example`, `GG_ADMIN_PASSWORD=your_strong_password`), then launch the unified control center:

```bash
./run.sh
```

Or manage via non-interactive CLI commands:
```bash
./run.sh start      # Start detached background daemon (survives SSH disconnect)
./run.sh stop       # Gracefully stop server
./run.sh restart    # Restart server daemon
./run.sh status     # Display PID, uptime, CPU/RAM & health check
./run.sh logs       # Tail live filtered server logs ([IP @ domain])
```

#### Step 4: Install on Android / Emulator
- **Direct Web Download**: Open `https://your-domain.example/download` on your Android device to download and install/update directly.
- **Via ADB**:
  ```bash
  adb install --no-incremental -r out/Guitar_Girl_v8.0.0_NoGooglePlay.apk
  ```

---

<a id="en-tui"></a>
### 📊 Live TUI Control Center & Domain Telemetry

Running `./run.sh` opens a symmetrical Dual-Column Terminal UI (`tools/dashboard.py`):
- **Left Panel**: Live Server PID/Uptime/Health, CPU/RAM/Disk progress bars, Active SQLite Players (`UID`, `Lv.GG`, `CP`, `Last Save`), Active Event Status, and Single-Key Shortcuts (`[1-6, f, p, c, q]`).
- **Right Panel (`LIVE TELEMETRY`)**: Real-time request table displaying:
  `TIME | GROUP | PLAYER (IP) | DOMAIN | API COMMAND / RESOURCE | RESULT`
  - Automatically maps client IPs to `guest_XXXXXX` accounts and highlights each connected domain in a distinct color.
- **Domain-Tagged Captures**: Every decoded packet saved in `emulator/captures/*.json` includes `timestamp`, `domain`, `host_header`, `active_domain_header`, `via_failover_apk`, and `client_ip` at the top of the JSON file.

---

<a id="en-admin"></a>
### 🖥️ Web Admin Dashboard & Download Portal

- **Web Admin (`/admin`)**:
  - Secured with `GG_ADMIN_PASSWORD` and HMAC-SHA256 `HttpOnly` session cookies (`gg_admin_token`).
  - Instant **🇻🇳 Tiếng Việt / 🇬🇧 English** switch.
  - Displays player **`🌐 <IP>`** and **`🔗 <Last Connected Domain>`** badges, real device vs. automated test account badges (with 1-click test cleanup), Ban/Unban controls, currency/level editors with BigNumber live preview, Star Pass/Attendance/Weather toggles, and Private or Server-Wide Gift Mailer.
- **Download Portal (`/download`)**:
  - Sleek dark-themed landing page serving `Guitar_Girl_v8.0.0_NoGooglePlay.apk` with clear in-place update instructions.

---

<a id="en-cli"></a>
### ⌨️ CLI Management Utilities

```bash
# Event & Broadcast Mail CLI
./emulator/eventctl.sh list
./emulator/eventctl.sh season 13
./emulator/eventctl.sh sendmail "Weekend Gift" "Enjoy your relaxing guitar melodies!" 500 100 50
```

---

<a id="en-docs"></a>
### 📖 Technical Documentation
- 🐞 **[BUG.md](BUG.md)**: Deep-dive analysis of 39+ reverse-engineered client/server bugs & `libil2cpp.so` ARM64 patches.
- 📱 **[ANDROID_SETUP.md](ANDROID_SETUP.md)**: Setup guide for BlueStacks and physical Android devices.
- 📡 **[PROTOCOL.md](PROTOCOL.md)**: Apache Thrift Binary RPC framing and DTO specification.

---

<a id="vi"></a>
# 🇻🇳 Tiếng Việt

Bộ giả lập máy chủ riêng (Private Server), công cụ vá APK tự động chuyển mạch 4 tên miền và trung tâm giám sát Telemetry thời gian thực dành cho tựa game di động đã ngừng phát hành (End-of-Service - EOS) **Guitar Girl** (*Cô gái Guitar*, phiên bản *v8.0.0* của Neowiz / StickyHands).

Dự án tái tạo trọn vẹn giao thức nhị phân Apache Thrift RPC, xác thực PmangPlus Guest, hệ thống CDN AssetBundle, các sự kiện trực tiếp và bộ xử lý tiền tệ số lớn BigNumber—kết hợp cùng giao diện điều khiển Terminal 2 cột (`run.sh`), hệ thống log/capture gắn nhãn tên miền và trang quản trị Web Admin song ngữ (`/admin`).

---

### 📑 Mục lục Tiếng Việt
1. [Tính năng nổi bật](#vi-features)
2. [Cơ chế Tự chuyển mạch 4 Tên miền (Active-Passive Failover)](#vi-failover)
3. [Cấu trúc dự án](#vi-architecture)
4. [Yêu cầu hệ thống](#vi-prerequisites)
5. [Hướng dẫn cài đặt nhanh](#vi-quickstart)
6. [Bảng điều khiển TUI & Giám sát Tên miền thời gian thực](#vi-tui)
7. [Web Admin Dashboard & Cổng tải APK](#vi-admin)
8. [Công cụ dòng lệnh CLI](#vi-cli)
9. [Tài liệu kỹ thuật liên quan](#vi-docs)

---

<a id="vi-features"></a>
### ✨ Tính năng nổi bật

#### 🎮 Khôi phục trọn vẹn Gameplay & Bảo vệ đồng bộ Save
- **Đầy đủ 3 Chương cốt truyện (Chapters 1, 2, 3)**:
  - **Chương 1 (Phòng của Guitar Girl)**: Mở khóa và nhận đủ tin nhắn của **15/15 người theo dõi** (Joy, Bạn tiệm tiện lợi, Thầy chủ nhiệm, Tiền bối trầm lặng, Moa, Elle, Amber, Yeri, Mocha Latte, Nova, Sua, Jae...), bao gồm phòng chat nhóm Joy & Moa đúng chuẩn kịch bản DAG gốc.
  - **Chương 2 (Tiệm bánh hạnh phúc)**: Đồng bộ mượt mà chuỗi hội thoại giữa người theo dõi cũ và 8 người theo dõi mới (Reading Fox, Ruby, Alex, Busking TV, Sora, Jessica) qua các phòng 12, 16, 17.
  - **Chương 3 (Trường cấp 3 Sunshine)**: Đầy đủ 20 màn Tour (`1001–2010`) với tỉ lệ rơi quà Encore chuẩn xác và giữ nguyên hướng dẫn tân thủ của Moa.
- **Bảo vệ chống tụt Level & Treo màn hình khởi động**:
  - Ổn định mốc `getUpdateTime`, làm mới `server_time` và hợp nhất an toàn hai chiều trong `userSave` giúp không bao giờ mất vật phẩm hoặc bị rollback cấp độ nhân vật/người theo dõi.
- **50 Đĩa nhạc & Bộ xử lý Số lớn BigNumber (`currency.py`)**:
  - Khôi phục toàn bộ 50 bản nhạc (26 bài Khu vực 1, 24 bài Khu vực 2).
  - Xử lý triệt để tràn số nguyên 64-bit (`> 1.84e19`), hỗ trợ đủ 702 bậc đơn vị `A..ZZ` (lên tới $10^{2109}$) kèm khung xem trước trực tiếp trên Web Admin.

#### 🎁 Sự kiện Trực tiếp & Hòm thư chống trùng lặp
- **Thẻ Sao (Star Pass Mùa 1–13)**: Chuyển đổi linh hoạt cả 13 mùa giải chính thức và hỗ trợ mua Mở khóa Slot Live trực tiếp trong cửa hàng Thẻ Sao (`item_buy` category 20).
- **Điểm danh & Thời tiết Lễ hội**: Điểm danh 7 ngày (Chương 1 & Chương 2), sự kiện Meowfest, hiệu ứng Tuyết rơi / Hoa anh đào bật tắt tức thì từ Web Admin.
- **Hòm thư chuẩn Honkai: Star Rail (`post.py`)**:
  - Tài khoản mới chỉ nhận duy nhất Thư chào mừng, không bị dội lại thư phát sóng cũ trước thời điểm tạo nick.
  - Bộ cấp phát mã thư `idx` đơn điệu toàn cục (`post_seq.json` + quét toàn bộ SQLite) triệt tiêu hoàn toàn lỗi trùng mã giữa thư riêng và thư toàn server.
  - Hỗ trợ đầy đủ nút **"Nhận tất cả" (`type=1` / `idx=0`)** và hiển thị trên cả **12 ngôn ngữ** của game.

#### 🛠️ Universal APK Độc lập & Hỗ trợ Cài đè (Update trực tiếp)
- **Không cần Root, không phụ thuộc Google Play**: Chạy mượt trên mọi điện thoại Android 7.0+ và giả lập PC (BlueStacks, LDPlayer, Nox).
- **Vá nhị phân Dalvik & ARM64 IL2CPP**:
  - Tự động đăng nhập Guest, tự chấp nhận điều khoản EULA, bỏ kiểm tra chữ ký `AppSecurityValidator`.
  - Mở khóa bật/tắt Thông báo đẩy, chi tiết Socola CP trong Cài đặt, và đồng bộ hiển thị **`UID: #<u_seq>`** khớp 100% với Web Admin.
- **Cài đè giữ nguyên dữ liệu**: Ký số nhất quán bằng khóa riêng (`v1/v2/v3`), cho phép người chơi đang dùng bản của server tải APK mới về **cài đè (Cập nhật) trực tiếp** mà không mất tài khoản `guest_XXXXXX` hay tiến trình chơi.

---

<a id="vi-failover"></a>
### 🛡️ Cơ chế Tự chuyển mạch 4 Tên miền (Active-Passive Failover)

Để đảm bảo kết nối xuyên suốt ngay cả khi một tên miền bị chặn DNS, nghẽn mạng hoặc gặp sự cố, bộ vá tích hợp sẵn cổng chuyển mạch nội bộ ngay bên trong tiến trình APK (`DomainFailoverGateway` + `MultiDomainFailoverProviderV1` trong `classes5.dex`):

1. **Chế độ Active-Passive thuần túy (Không gây tải thừa)**:
   - Khi mở game, gateway lắng nghe cục bộ tại `http://127.0.0.1:28765` và chỉ kết nối tới **1 tên miền HTTPS duy nhất đang hoạt động tốt** (tự động ghi nhớ tên miền khỏe nhất trong `SharedPreferences`).
   - Khi tên miền hiện tại phản hồi bình thường, **3 tên miền dự phòng hoàn toàn không phát sinh bất kỳ kết nối hay truy vấn DNS nào**.
2. **Tự động chuyển mạch không gián đoạn phiên chơi**:
   - Chỉ khi tên miền hiện tại gặp lỗi (chặn DNS, timeout TCP/TLS, hoặc lỗi HTTP `5xx` / `408` / `429`), gateway mới tự động chuyển sang tên miền kế tiếp, phát lại nguyên vẹn gói RPC / AssetBundle đang gửi dở và lưu tên miền mới làm mặc định.
3. **Định tuyến Đa tên miền trên 1 Server (`app.py`)**:
   - Một tiến trình GGServer duy nhất phục vụ đồng thời cả 4 tên miền SSL sau Nginx/Cloudflare thông qua nhận diện động `Host`, `X-Forwarded-Proto` và `X-GG-Local-Proxy`.

---

<a id="vi-architecture"></a>
### 📂 Cấu trúc dự án

```text
GGServer/
├── run.sh                           # Trung tâm điều khiển Server (Chạy ngầm bền bỉ + Bảng TUI 2 cột)
├── tools/
│   └── dashboard.py                 # Giao diện TUI 2 cột & Bảng Telemetry giám sát tên miền trực tiếp
├── emulator/                        # Máy chủ giả lập Python 3
│   ├── run.py                       # Điểm khởi chạy server chính (HTTP + Thrift Binary RPC)
│   ├── serverctl.sh                 # Script điều khiển tiến trình (start/stop/restart/status/log)
│   ├── eventctl.sh / eventctl.py    # Công cụ CLI quản lý sự kiện & gửi thư toàn server
│   ├── broadcast_posts.json         # Dữ liệu thư phát sóng đa ngôn ngữ
│   ├── event_config.json            # Cấu hình Star Pass, Điểm danh & Thời tiết
│   ├── gamedata/                    # Bảng dữ liệu tĩnh & các gói AssetBundle CDN
│   ├── schema/                      # Đặc tả cấu trúc gói tin Thrift DTO
│   ├── data/                        # CSDL SQLite lưu tiến trình người chơi (chỉ lưu cục bộ)
│   ├── captures/                    # Các gói capture JSON kèm tên miền kết nối (chỉ lưu cục bộ)
│   └── server/                      # Nhân xử lý phía máy chủ
│       ├── app.py                   # Định tuyến đa tên miền, ghi log [IP @ domain] & capture
│       ├── admin.py                 # Bảng quản trị Web Admin song ngữ (/admin)
│       ├── download.py              # Trang tải APK chính thức (/download)
│       ├── state.py                 # Lưu trữ SQLite nguyên tử, theo dõi IP & tên miền gần nhất
│       ├── currency.py              # Bộ xử lý tiền tệ số lớn BigNumber (A..ZZ)
│       ├── event_manager.py         # Quản lý mùa giải Star Pass & Điểm danh
│       └── handlers/                # Bộ xử lý lệnh RPC (auth, follower, music, post, shop...)
├── patcher/                         # Bộ công cụ biên dịch & vá Client APK
│   ├── build.sh                     # Quy trình tự động biên dịch, vá, gộp & ký số APK
│   ├── patch_apk.py                 # Vá Dalvik bytecode, nhúng classes5.dex & vá metadata
│   ├── merge_apk.py                 # Vá nhị phân AndroidManifest.xml, libil2cpp.so & gộp Split APK
│   ├── patch_metadata.py            # Chuyển hướng endpoint trong global-metadata.dat
│   ├── classes5.dex                 # Bytecode DEX của bộ chuyển mạch 4 tên miền
│   ├── java/                        # Mã nguồn Java của DomainFailoverGateway & ContentProvider
│   └── uber-apk-signer.jar          # Công cụ ký số APK chuẩn v1/v2/v3
├── orig_apk/                        # Thư mục đặt 3 file APK gốc v8.0.0 (người dùng tự chuẩn bị)
├── out/                             # Thư mục xuất APK thành phẩm (gitignored)
├── BUG.md                           # Tài liệu phân tích hơn 39 lỗi kỹ thuật & bản vá ARM64
├── ANDROID_SETUP.md                 # Hướng dẫn cài đặt trên BlueStacks & điện thoại Android
├── PROTOCOL.md                      # Tài liệu đặc tả giao thức nhị phân Apache Thrift
└── README.md                        # Tài liệu hướng dẫn dự án (file này)
```

---

<a id="vi-prerequisites"></a>
### 💻 Yêu cầu hệ thống

- **Hệ điều hành**: Linux, macOS, hoặc Windows (khuyến nghị WSL2)
- **Python**: Phiên bản `3.10` trở lên
- **Java**: OpenJDK `17+` hoặc `21+` (dùng để ký APK và biên dịch lại `classes5.dex` khi cần)
- **ADB** *(tùy chọn)*: `android-tools-adb` nếu muốn cài APK qua cáp USB hoặc giả lập

```bash
sudo apt update
sudo apt install -y python3 python3-pip openjdk-21-jdk-headless android-tools-adb zip unzip
```

---

<a id="vi-quickstart"></a>
### 🚀 Hướng dẫn cài đặt nhanh

#### Bước 1: Chuẩn bị 3 file APK gốc v8.0.0
Đặt 3 tệp Split APK gốc của *Guitar Girl v8.0.0* vào thư mục `orig_apk/`:
- `orig_apk/com.neowiz.game.guitargirl.apk`
- `orig_apk/config.arm64_v8a.apk`
- `orig_apk/base_assets.apk`

#### Bước 2: Đóng gói & Ký số APK
Chọn chế độ kết nối phù hợp với hạ tầng máy chủ của bạn:

```bash
# Cách A (Mặc định - Khuyên dùng): Đóng gói APK Tự chuyển mạch 4 Tên miền (qua cổng nội bộ 127.0.0.1:28765)
bash patcher/build.sh --multidomain

# Cách B: Kết nối cố định 1 tên miền HTTPS duy nhất
bash patcher/build.sh https://your-domain.example

# Cách C: Chạy mạng nội bộ LAN HTTP
bash patcher/build.sh http://192.168.1.50:8080
```

File APK hoàn chỉnh sẽ được xuất ra tại `out/`:
- `out/Guitar_Girl_v8.0.0_NoGooglePlay.apk` *(Bản khuyên dùng)*
- `out/Guitar_Girl_v8.0.0_Universal.apk`

#### Bước 3: Khởi chạy Máy chủ Giả lập
Thiết lập biến môi trường trong `.env` (tùy chọn: `PORT=8080`, `GG_PUBLIC_BASE=https://your-domain.example`, `GG_ADMIN_PASSWORD=mat_khau_quan_tri`), sau đó chạy trung tâm điều khiển:

```bash
./run.sh
```

Hoặc điều khiển nhanh bằng các lệnh CLI:
```bash
./run.sh start      # Chạy ngầm độc lập (ngắt kết nối SSH server vẫn hoạt động an toàn)
./run.sh stop       # Dừng tiến trình server
./run.sh restart    # Khởi động lại server
./run.sh status     # Xem PID, Uptime, CPU/RAM và trạng thái Health Check
./run.sh logs       # Theo dõi luồng log trực tiếp kèm nhãn [IP @ tên_miền]
```

#### Bước 4: Cài đặt lên Điện thoại / Giả lập
- **Tải trực tiếp qua Web**: Mở `https://your-domain.example/download` trên điện thoại để tải và cài đặt (hoặc cài đè cập nhật giữ nguyên tài khoản).
- **Cài qua ADB**:
  ```bash
  adb install --no-incremental -r out/Guitar_Girl_v8.0.0_NoGooglePlay.apk
  ```

---

<a id="vi-tui"></a>
### 📊 Bảng điều khiển TUI & Giám sát Tên miền thời gian thực

Gõ `./run.sh` để mở giao diện giám sát 2 cột đối xứng (`tools/dashboard.py`):
- **Cột trái**: Trạng thái Server (PID, Uptime, Health Check), thanh tiến trình CPU / RAM / Disk, danh sách Người chơi trực tiếp từ SQLite (`UID`, `Lv.GG`, `CP`, thời gian lưu cuối), trạng thái Sự kiện và bảng Phím tắt nhanh (`[1-6, f, p, c, q]`).
- **Cột phải (`LIVE TELEMETRY`)**: Bảng nhật ký thời gian thực hiển thị đầy đủ 6 cột:
  `THỜI GIAN | NHÓM | NGƯỜI CHƠI (IP) | TÊN MIỀN | LỆNH API / TÀI NGUYÊN | KẾT QUẢ`
  - Tự động ánh xạ IP sang tài khoản `guest_XXXXXX` và tô màu riêng biệt cho từng tên miền kết nối để quản trị viên nhận diện ngay lập tức thiết bị đang đi qua cổng tên miền nào.
- **Capture gắn nhãn Tên miền**: Mọi gói tin lưu trong `emulator/captures/*.json` đều ghi sẵn `timestamp`, `domain`, `host_header`, `active_domain_header`, `via_failover_apk` và `client_ip` ngay đầu tệp JSON.

---

<a id="vi-admin"></a>
### 🖥️ Web Admin Dashboard & Cổng tải APK

- **Trang quản trị Web (`/admin`)**:
  - Bảo vệ bằng mật khẩu `GG_ADMIN_PASSWORD` và phiên đăng nhập HMAC-SHA256 `HttpOnly` Cookie (`gg_admin_token`).
  - Hỗ trợ chuyển đổi tức thì **🇻🇳 Tiếng Việt / 🇬🇧 English**.
  - Hiển thị nhãn **`🌐 <IP>`** và **`🔗 <Tên miền kết nối gần nhất>`** cho từng tài khoản, phân biệt `📱 Máy Thật` / `🧪 Test Auto` (kèm nút dọn tài khoản test 1 chạm), khóa/mở khóa (Ban/Unban) hiển thị thông báo gốc trong game, chỉnh sửa tiền tệ BigNumber có khung xem trước, bật/tắt sự kiện và gửi Thư & Quà riêng hoặc toàn server.
- **Cổng tải game (`/download`)**:
  - Trang đích giao diện tối hiện đại phục vụ tải trực tiếp APK kèm hướng dẫn cài đè an toàn không mất dữ liệu.

---

<a id="vi-cli"></a>
### ⌨️ Công cụ dòng lệnh CLI

```bash
# Quản lý sự kiện & gửi quà hòm thư qua dòng lệnh
./emulator/eventctl.sh list
./emulator/eventctl.sh season 13
./emulator/eventctl.sh sendmail "Quà tặng cuối tuần" "Chúc bạn chơi game thư giãn vui vẻ!" 500 100 50
```

---

<a id="vi-docs"></a>
### 📖 Tài liệu kỹ thuật liên quan
- 🐞 **[BUG.md](BUG.md)**: Tổng hợp phân tích chuyên sâu hơn 39 lỗi kỹ thuật & bản vá assembly ARM64 trong `libil2cpp.so`.
- 📱 **[ANDROID_SETUP.md](ANDROID_SETUP.md)**: Hướng dẫn thiết lập môi trường trên BlueStacks và điện thoại Android không cần Root.
- 📡 **[PROTOCOL.md](PROTOCOL.md)**: Đặc tả giao thức nhị phân Apache Thrift RPC của trò chơi.

---

<a id="full-legal-disclaimer"></a>
## 📜 Full Legal Disclaimer / Điều khoản Pháp lý Chi tiết

### 🇬🇧 English: Comprehensive Legal Disclaimer & Terms of Use

1. **Purpose of Preservation & Research**:
   This software repository is created strictly for **educational, historical preservation, interoperability research, and digital archiving purposes**. It was developed in response to the official termination and End-of-Service (EOS) of the mobile game *Guitar Girl* (v8.0.0), aimed at studying legacy network protocols and preserving digital cultural artifacts that are no longer accessible to the public through official channels.

2. **No Affiliation or Endorsement**:
   This project is an independent open-source initiative. It is **NOT** associated with, affiliated with, sponsored by, authorized by, or endorsed by **NEOWIZ Corp.**, **StickyHands Inc.**, or any of their parent entities, subsidiaries, or licensors.

3. **Intellectual Property Rights**:
   All trademarks, service marks, trade names, character likenesses, 2D illustrations, 3D models, textures, animations, voice recordings, sound effects, musical compositions, lyrics, and story scripts relating to *Guitar Girl* are the exclusive intellectual property of **NEOWIZ Corp.** and **StickyHands Inc.** No copyright transfer or license grant is implied or intended.

4. **Strict Non-Commercial & Anti-Monetization Policy**:
   This software is distributed 100% free of charge. The authors and contributors:
   - Do **NOT** sell, license, or monetize any portion of this project.
   - Do **NOT** solicit, accept, or process donations, tips, subscriptions, or financial contributions of any kind.
   - Strictly prohibit third parties from utilizing this codebase for commercial server hosting, real-money transactions, or microtransaction implementations.

5. **No Proprietary Asset Redistribution**:
   In strict compliance with intellectual property standards, this repository **DOES NOT** contain, host, or distribute any proprietary original APK files, copyrighted music tracks, or raw Unity AssetBundles. All users are expected to supply their own legally acquired client binaries obtained prior to the service termination.

6. **Disclaimer of Warranty & Limitation of Liability**:
   THIS SOFTWARE IS PROVIDED BY THE AUTHORS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHORS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE.

---

### 🇻🇳 Tiếng Việt: Điều khoản Miễn trừ trách nhiệm pháp lý toàn diện

1. **Mục đích Bảo tồn & Nghiên cứu Khoa học**:
   Kho lưu trữ phần mềm này được xây dựng hoàn toàn vì mục đích **nghiên cứu học thuật, giáo dục, nghiên cứu khả năng tương tác kỹ thuật đảo ngược (Reverse Engineering) và bảo tồn di sản văn hóa số**. Dự án ra đời nhằm lưu giữ trải nghiệm trò chơi sau khi trò chơi di động *Guitar Girl* (phiên bản v8.0.0) chính thức ngừng cung cấp dịch vụ (End of Service - EOS) trên toàn cầu và không còn khả năng tiếp cận qua các kênh phân phối chính thức.

2. **Tuyên bố Không liên kết & Không ủy quyền**:
   Dự án này là một sáng kiến độc lập phi lợi nhuận. Dự án hoàn toàn **KHÔNG** liên kết, không thuộc quyền sở hữu, không được ủy quyền, tài trợ hoặc chứng thực dưới bất kỳ hình thức nào bởi **NEOWIZ Corp.**, **StickyHands Inc.** hay bất kỳ chi nhánh, đối tác hoặc đơn vị cấp phép nào của họ.

3. **Quyền Sở hữu Trí tuệ**:
   Mọi nhãn hiệu hàng hóa, tên thương mại, hình tượng nhân vật, hình ảnh đồ họa 2D, mô hình 3D, chuyển động hoạt ảnh, bản thu âm, hiệu ứng âm thanh, tác phẩm âm nhạc, giai điệu, lời bài hát và kịch bản cốt truyện liên quan đến *Guitar Girl* đều thuộc quyền sở hữu trí tuệ độc quyền và bất khả xâm phạm của **NEOWIZ Corp.** và **StickyHands Inc.** Dự án không tuyên bố bất kỳ quyền sở hữu nào đối với các tài sản trí tuệ nói trên.

4. **Chính sách Phi thương mại & Nghiêm cấm trục lợi**:
   Phần mềm này được phát hành hoàn toàn miễn phí. Đội ngũ phát triển và người đóng góp:
   - **KHÔNG** mua bán, kinh doanh, cấp phép lại hoặc thương mại hóa bất kỳ phần nào của dự án.
   - **KHÔNG** kêu gọi, nhận đóng góp tài chính, tiền donate hay phí duy trì dịch vụ dưới bất kỳ hình thức nào.
   - Nghiêm cấm bất kỳ bên thứ ba nào sử dụng mã nguồn này để mở dịch vụ máy chủ thu phí, bán vật phẩm trong game hoặc tiến hành giao dịch bằng tiền thật.

5. **Không phân phối tài nguyên có bản quyền**:
   Nhằm tuân thủ nghiêm ngặt các quy định về quyền tác giả, kho lưu trữ này **HOÀN TOÀN KHÔNG** lưu trữ, phân phối hay cung cấp các tệp APK gốc có bản quyền, các bản nhạc số hay các gói tài nguyên AssetBundle độc quyền của trò chơi. Người dùng có trách nhiệm tự chuẩn bị các tệp cài đặt trò chơi hợp pháp mà mình đã sở hữu trước thời điểm dịch vụ chính thức đóng cửa.

6. **Miễn trừ Bảo hành & Giới hạn Trách nhiệm**:
   PHẦN MỀM ĐƯỢC CUNG CẤP DƯỚI DẠNG "NGUYÊN TRẠNG" (AS IS) VÀ KHÔNG KÈM THEO BẤT KỲ SỰ BẢO ĐẢM NÀO, DÙ ĐƯỢC NÊU RÕ HAY NGỤ Ý. TRONG MỌI TRƯỜNG HỢP, CÁC TÁC GIẢ HOẶC NGƯỜI ĐÓNG GÓP SẼ KHÔNG CHỊU TRÁCH NHIỆM CHO BẤT KỲ THIỆT HẠI TRỰC TIẾP, GIÁN TIẾP, NGẪU NHIÊN, ĐẶC BIỆT HOẶC HỆ QUẢ NÀO (BAO GỒM MẤT MÁT DỮ LIỆU, THIỆT HẠI THIẾT BỊ HOẶC CÁC TRANH CHẤP PHÁP LÝ LIÊN QUAN) PHÁT SINH TỪ VIỆC CÀI ĐẶT, SỬ DỤNG HOẶC KHÔNG THỂ SỬ DỤNG PHẦN MỀM NÀY.

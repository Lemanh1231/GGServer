# 🎸 Guitar Girl Private Server Emulator (GGServer)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Android%20%7C%20BlueStacks-3DDC84.svg?logo=android&logoColor=white)](https://developer.android.com/)
[![Protocol](https://img.shields.io/badge/Protocol-Apache%20Thrift%20Binary-00599C.svg?logo=apache&logoColor=white)](https://thrift.apache.org/)
[![License](https://img.shields.io/badge/License-Educational%20%2F%20Preservation-6f42c1.svg)](#-disclaimer--miễn-trừ-trách-nhiệm)
[![Web Admin](https://img.shields.io/badge/Web%20Admin-English%20%7C%20Tiếng%20Việt-E03E2D.svg)](#-web-admin-dashboard)

> **Bilingual Documentation / Tài liệu Song ngữ**:  
> 🇬🇧 **[English Documentation](#-english)** &nbsp;|&nbsp; 🇻🇳 **[Tài liệu Tiếng Việt](#-tiếng-việt)** &nbsp;|&nbsp; ⚖️ **[Disclaimer / Miễn trừ trách nhiệm](#️-disclaimer--miễn-trừ-trách-nhiệm)**

---

## ⚖️ Disclaimer / Miễn trừ trách nhiệm

> [!IMPORTANT]
> **English**: This project is strictly created for **educational, non-commercial, historical preservation, and digital archival purposes** following the official End-of-Service (EOS) of the mobile game *Guitar Girl* (v8.0.0).  
> - **No Affiliation**: This project is independent and is **NOT** affiliated with, endorsed by, sponsored by, or connected to **NEOWIZ Corp.**, **StickyHands Inc.**, or any of their parent companies, subsidiaries, or affiliates.
> - **Intellectual Property**: All trademarks, game titles, character designs, 2D/3D art, illustrations, animations, musical compositions, sound effects, story scripts, and proprietary game assets belong exclusively to **NEOWIZ Corp.** and **StickyHands Inc.**
> - **Non-Commercial**: This repository does not sell anything, does not solicit donations, and contains zero monetization or real-money transactions.
> - **No Copyrighted Binary Redistribution**: This repository does not distribute copyrighted original APK files or extracted proprietary assets. Users must provide their own legitimately acquired client binaries.
> - **No Warranty**: Provided on an "AS IS" basis without warranty of any kind.
>
> *(See the [full legal disclaimer section](#️-disclaimer--miễn-trừ-trách-nhiệm) at the bottom for comprehensive clauses).*

> [!IMPORTANT]
> **Tiếng Việt**: Dự án này được phát triển hoàn toàn vì mục đích **học tập, nghiên cứu kỹ thuật đảo ngược, bảo tồn di sản số và lưu trữ phi thương mại** sau khi trò chơi di động *Guitar Girl* (phiên bản v8.0.0) chính thức đóng cửa (End-of-Service).  
> - **Không liên kết**: Dự án hoàn toàn độc lập và **KHÔNG** liên kết, không được chứng thực, tài trợ hay trực thuộc **NEOWIZ Corp.**, **StickyHands Inc.** hay bất kỳ công ty liên kết nào.
> - **Quyền sở hữu trí tuệ**: Toàn bộ nhãn hiệu, tiêu đề trò chơi, thiết kế nhân vật, đồ họa 2D/3D, hình minh họa, hoạt ảnh, tác phẩm âm nhạc, hiệu ứng âm thanh, kịch bản cốt truyện và tài nguyên trò chơi thuộc quyền sở hữu trí tuệ độc quyền của **NEOWIZ Corp.** và **StickyHands Inc.**
> - **Phi thương mại**: Dự án hoàn toàn miễn phí, không thương mại hóa, không nhận quyên góp và không có bất kỳ tính năng thanh toán tiền thật nào.
> - **Không phân phối tệp bản quyền**: Kho lưu trữ này không phân phối file APK gốc có bản quyền hoặc tài nguyên trích xuất độc quyền. Người dùng cần tự chuẩn bị tệp cài đặt hợp pháp của mình.
> - **Miễn trừ bảo hành**: Phần mềm được cung cấp "NGUYÊN TRẠNG" (AS IS) mà không có bất kỳ bảo đảm nào.
>
> *(Xem [điều khoản miễn trừ trách nhiệm pháp lý chi tiết](#️-disclaimer--miễn-trừ-trách-nhiệm) ở cuối tài liệu).*

---

# 🇬🇧 English

A comprehensive private server revival emulator and client patcher suite for the End-of-Service (EOS) mobile game **Guitar Girl** (*v8.0.0* by Neowiz / StickyHands).

The project faithfully reconstructs the game's Apache Thrift Binary RPC protocol, PmangPlus guest authentication, NeonAPI endpoints, static CDN AssetBundle distribution, live event systems, in-game economy engine, and provides a modern bilingual Web Admin Dashboard and CLI management tools.

---

### 📑 English Table of Contents
1. [Key Features](#-key-features)
2. [Project Architecture](#-project-architecture)
3. [Prerequisites](#-prerequisites)
4. [Quick Start Guide](#-quick-start-guide)
   - [Step 1: Prepare Original APKs](#step-1-prepare-original-apks)
   - [Step 2: Patch and Build Client APK](#step-2-patch-and-build-client-apk)
   - [Step 3: Install APK via ADB](#step-3-install-apk-via-adb)
   - [Step 4: Launch the Emulator Server](#step-4-launch-the-emulator-server)
5. [Web Admin Dashboard](#-web-admin-dashboard)
6. [CLI Management Utilities](#-cli-management-utilities)
7. [Automated Testing Suite](#-automated-testing-suite)
8. [Technical Documentation](#-technical-documentation)

---

### ✨ Key Features

#### 🎮 Full Gameplay Restoration & Bug Fixes
- **All 3 Story Chapters Fully Playable**:
  - **Chapter 1 (Guitar Girl's Room)**: Unlock and chat with **all 15/15 followers** (Joy, Convenience Store Friend, Homeroom Teacher, Quiet Senior, Moa, Elle, Amber, Yeri, Mocha Latte, Nova, Sua, Jae, etc.), including group chat rooms for Joy & Moa with authentic story triggers.
  - **Chapter 2 (Sweet Bakery)**: Smooth storyline and chat room progression connecting original followers and 8 new Chapter 2 followers (Reading Fox, Ruby, Alex, Busking TV, Sora, Jessica) across chat rooms 12, 16, and 17.
  - **Chapter 3 (Sunshine High School)**: Complete Tour mode stages 1001–2010 with authentic Encore gift drop probabilities; fully preserved Moa tutorial intro sequence when first unlocked.
- **Music Discs System**:
  - All 50 music discs restored (26 songs in Area 1, 24 songs in Area 2).
  - Mozart's Piano Sonata (Song 12) event disc correctly labeled and formatted.
- **BigNumber Currency Engine (`currency.py`)**:
  - Resolves 64-bit integer overflow (`uint64` / `int64` limit $1.84 \times 10^{19}$) when accounts reach high Heart tiers ($10^{21} = \text{G}, 10^{24} = \text{H} \dots 10^{2109} = \text{ZZ}$).
  - Fully supports 702 Alphabet units (`A` through `ZZ`) adhering to Unity IL2CPP notation.
  - Safe mathematical clamping with real-time live preview in Web Admin.

#### 🎁 Live Events & Economy
- **Star Pass (Thẻ Sao)**:
  - Supports all 13 official seasons (Seasons 1–13) with localized season names and authentic Free/Gold reward tracks.
  - Full support for purchasing Live Slots in the Star Pass item shop (`item_buy.py` category 20).
- **Attendance Events**:
  - 7-Day Novice Attendance and 1st Anniversary Attendance events with hot-reload toggle from Web Admin.
- **Honkai: Star Rail-Style Mailbox**:
  - Newly created accounts receive only a clean Welcome Letter without being flooded with expired past broadcast/maintenance letters.
  - Official multi-language system mail support for all **12 client languages**: `ko`, `en`, `jp`, `zh_chs`, `zh_cht`, `vi`, `es`, `it`, `id`, `th`, `pt`, `hi`.
- **Joy Follower Quests**:
  - Immediate reward claims for `#CheerGuitarGirl` quest lines (Chocolates CP, Candies, Likes, AP Cookies).

#### 🛠️ Client Patcher & Universal APK (No Google Play)
- **Rootless Device Support**: Runs seamlessly on BlueStacks (macOS / Windows) and real physical Android devices without requiring root privileges.
- **Dalvik Bytecode & ARM64 IL2CPP Binary Patching**:
  - Automatic PmangPlus Guest login bypass (no Google Play Games required).
  - Automatic Terms of Service / EULA agreement.
  - Bypasses application signature verification (`AppSecurityValidator`).
  - Unhides Push Notifications and CP Breakdown toggles in the game Settings menu.
  - Displays user ID as `UID: #<u_seq>` instead of Google Play USN, matching the server sequence ID.
- **Split APKs Merger**: Merges `base.apk`, `base_assets.apk`, and `config.arm64_v8a.apk` into a single standalone Universal APK signed with v1/v2/v3 schemes.

#### 🌐 Bilingual Web Admin Dashboard
- **Instant Language Toggle**: Switch seamlessly between 🇻🇳 **Tiếng Việt** and 🇬🇧 **English** with `localStorage` persistence.
- **Player Management**: Search players by username or `u_seq`, inspect profiles, and edit Levels, Likes (with BigNumber notation preview), Chocolates CP, Candies, AP Cookies, and Collection Tickets.
- **Data Integrity Guards**: Automatically disables and warns administrators when modifying Star Pass fields while the global Star Pass feature is turned off.
- **Live Event Manager**: Toggle attendance events, switch Star Pass seasons (1–13), and broadcast reward-bearing system mail directly to all players.

---

### 📂 Project Architecture

```text
GGServer/
├── emulator/                        # Python 3 Private Server Emulator
│   ├── run.py                       # Main server entrypoint (HTTP + Thrift API)
│   ├── serverctl.sh                 # Process management script (start/stop/restart/log)
│   ├── eventctl.sh / eventctl.py    # Event manager CLI & broadcast mailer
│   ├── broadcast_posts.json         # System broadcast mailbox database (12 languages)
│   ├── event_config.json            # Runtime event configuration & Star Pass state
│   ├── gamedata/                    # Static game data tables (game_data.json, .b64, .ab)
│   ├── codec/                       # Apache Thrift Binary RPC encoder/decoder
│   ├── data/                        # SQLite storage (database.db)
│   ├── server/                      # Server backend core logic
│   │   ├── app.py                   # HTTP routing & API dispatching
│   │   ├── admin.py                 # Bilingual Web Admin Dashboard
│   │   ├── state.py                 # SQLite persistence & user session management
│   │   ├── currency.py              # BigNumber currency engine (A..ZZ)
│   │   ├── event_manager.py         # Star Pass & Attendance event manager
│   │   └── handlers/                # Thrift RPC handlers (auth, follower, music, post...)
│   └── test_*.py                    # Automated test suites
├── patcher/                         # Client APK Patcher Toolchain
│   ├── build.sh                     # Automated patch and packaging pipeline
│   ├── merge_apk.py                 # Merges Split APKs into 1 Universal APK
│   ├── patch_apk.py                 # Applies Dalvik bytecode & ARM64 native patches
│   ├── patch_metadata.py            # Rewrites server endpoints in global-metadata.dat
│   └── uber-apk-signer.jar          # Universal APK signing tool (v1, v2, v3)
├── orig_apk/                        # Original v8.0.0 APK files (user-supplied)
├── out/                             # Output directory for patched & signed APKs
├── BUG.md                           # Comprehensive documentation of 28+ technical bug fixes
├── ANDROID_SETUP.md                 # Setup guide for BlueStacks and Android devices
├── PROTOCOL.md                      # Apache Thrift RPC reverse engineering specification
└── README.md                        # Project documentation (this file)
```

---

### 💻 Prerequisites

- **Operating System**: Linux, macOS, or Windows (WSL2 recommended).
- **Python**: Version 3.10 or higher.
- **Java**: OpenJDK 11+ or JRE (required for `uber-apk-signer.jar`).
- **Android Platform Tools**: `adb` command-line utility for device installation and debugging.
- **Emulator / Device**: BlueStacks 5 (Nougat 64-bit / Pie 64-bit) or any physical device running Android 7.0+.

Install dependencies on Ubuntu / Debian:
```bash
sudo apt update
sudo apt install -y python3 python3-pip openjdk-17-jre-headless android-tools-adb zip unzip
```

---

### 🚀 Quick Start Guide

#### Step 1: Prepare Original APKs
Obtain the official v8.0.0 Guitar Girl installation package (as XAPK/APKs from reputable sources). Place the 3 original split APK files into the `orig_apk/` directory:
- `orig_apk/base_assets.apk`
- `orig_apk/com.neowiz.game.guitargirl.apk`
- `orig_apk/config.arm64_v8a.apk`

#### Step 2: Patch and Build Client APK
Choose your server deployment mode:

##### Option A: Local Network (LAN HTTP)
```bash
# Provide the local server IP (or let the script auto-detect your local IP)
bash patcher/build.sh http://192.168.1.50:8080
```

##### Option B: Public Internet (HTTPS Reverse Proxy / Cloudflare Tunnel - Recommended)
When using a domain with a valid SSL certificate, Android connects securely without requiring custom root CA certificates:
```bash
bash patcher/build.sh https://your-domain.example
```

The script will automatically:
1. Rewrite API endpoints inside `global-metadata.dat`.
2. Apply Dalvik bytecode (`classes3.dex`) and ARM64 binary patches (`libil2cpp.so`).
3. Merge split APKs into a single Universal APK and sign it.
4. Output ready-to-install APK at: `out/Guitar_Girl_v8.0.0_NoGooglePlay.apk`.

#### Step 3: Install APK via ADB
Enable **Android Debug Bridge (ADB)** on your emulator (BlueStacks Settings → Advanced) or Android phone (Developer Options → USB Debugging):

```bash
# 1. Connect to emulator or device (e.g., BlueStacks port 5555)
adb connect 127.0.0.1:5555

# 2. Install the Universal APK (always use --no-incremental)
adb install --no-incremental -r out/Guitar_Girl_v8.0.0_NoGooglePlay.apk
```

#### Step 4: Launch the Emulator Server

##### Using the Process Manager (Recommended):
```bash
# Start server in the background (default port 8080)
./emulator/serverctl.sh start

# If running behind a public domain:
GG_PUBLIC_BASE="https://your-domain.example" ./emulator/serverctl.sh start

# Check status:
./emulator/serverctl.sh status

# Follow logs in real time:
./emulator/serverctl.sh log
```

##### Or run directly via Python:
```bash
python3 emulator/run.py --port 8080
```

Launch Guitar Girl on your device and enjoy!

---

### 🖥️ Web Admin Dashboard

Access the administration dashboard in your web browser at:
```text
http://<SERVER_IP>:8080/admin
```
*(Or `https://your-domain.example/admin` if using a reverse proxy).*

- **Bilingual Interface**: Toggle between 🇻🇳 **Tiếng Việt** and 🇬🇧 **English** at any time. Preference is remembered across browser sessions.
- **Player Inspection & Editing**: Edit Player Level, Chocolates CP, Candies, AP Cookies, Collection Tickets, and Likes (Hearts). The Likes input field features real-time BigNumber preview (e.g., typing `42.877G` instantly previews `42,877,000,000,000,000,000,000`).
- **Star Pass Safety Lock**: Automatically prevents editing Star Pass levels when Star Pass is disabled server-wide, preventing database inconsistencies.
- **Live Event Controls**: Hot-reload attendance events, toggle Star Pass seasons 1–13, and dispatch system letters with rewards.

---

### ⌨️ CLI Management Utilities

#### 1. Server Controller (`serverctl.sh`)
```bash
./emulator/serverctl.sh start      # Start emulator in background
./emulator/serverctl.sh stop       # Gracefully stop emulator
./emulator/serverctl.sh restart    # Restart emulator
./emulator/serverctl.sh status     # Check process status, PID, and healthcheck
./emulator/serverctl.sh log        # Stream server logs (Ctrl+C to exit)
```

#### 2. Event Controller (`eventctl.sh`)
```bash
# List all active events and their statuses
./emulator/eventctl.sh list

# Switch active Star Pass season (1 to 13)
./emulator/eventctl.sh season 13

# Toggle attendance events
./emulator/eventctl.sh enable 1      # Enable 7-Day Novice Attendance
./emulator/eventctl.sh disable 2     # Disable 1st Anniversary Attendance

# Broadcast mailbox letter to all players:
# Syntax: sendmail <title> <body> [cp] [candy] [cookie]
./emulator/eventctl.sh sendmail "Weekend Gift" "Enjoy your relaxing guitar melodies!" 100 500 10
```

---

### 🧪 Automated Testing Suite

The repository includes a comprehensive regression testing suite verifying RPC serialization, game economy, follower chat triggers, and Star Pass purchases:

```bash
# Follower messenger, notification, and recent bug fixes
PYTHONPATH=emulator python3 -m unittest emulator/test_follower_messenger.py \
                                       emulator/test_live_slot_purchase.py \
                                       emulator/test_notification.py \
                                       emulator/test_starpass_and_anniversary.py \
                                       emulator/test_user_fixes_four_issues.py

# Attendance, daily missions, and ban behavior
PYTHONPATH=emulator python3 -m unittest emulator/test_attendance.py \
                                       emulator/test_ban_behavior.py \
                                       emulator/test_daily_mission.py \
                                       emulator/test_event_manager.py
```

---

### 📖 Technical Documentation

For in-depth technical analysis and reverse-engineering findings:
- 🐞 **[BUG.md](BUG.md)**: Exhaustive documentation of 28+ technical bugs, ARM64 disassembly analysis in `libil2cpp.so`, and solutions.
- 📱 **[ANDROID_SETUP.md](ANDROID_SETUP.md)**: Step-by-step setup guide for BlueStacks and physical Android devices without root.
- 📡 **[PROTOCOL.md](PROTOCOL.md)**: Binary protocol specification for Apache Thrift RPC framing and opcode mappings.

---

# 🇻🇳 Tiếng Việt

Bộ giả lập máy chủ riêng và công cụ vá client hoàn chỉnh dành cho trò chơi di động đã ngừng hoạt động (End-of-Service - EOS) **Guitar Girl** (*Cô gái Guitar*, phiên bản *v8.0.0* của Neowiz / StickyHands).

Dự án tái lập chuẩn xác giao thức RPC nhị phân Apache Thrift, cơ chế xác thực PmangPlus Guest, các endpoint NeonAPI, phân phối AssetBundle qua CDN tĩnh, hệ thống sự kiện thời gian thực, bộ xử lý kinh tế số lớn và cung cấp Bảng điều khiển Quản trị Web song ngữ cùng các công cụ dòng lệnh (CLI).

---

### 📑 Mục lục Tiếng Việt
1. [Tính năng nổi bật](#-tính-năng-nổi-bật)
2. [Cấu trúc dự án](#-cấu-trúc-dự-án)
3. [Yêu cầu hệ thống](#-yêu-cầu-hệ-thống)
4. [Hướng dẫn cài đặt nhanh](#-hướng-dẫn-cài-đặt-nhanh)
   - [Bước 1: Chuẩn bị file APK gốc](#bước-1-chuẩn-bị-file-apk-gốc)
   - [Bước 2: Vá và đóng gói APK](#bước-2-vá-và-đóng-gói-apk)
   - [Bước 3: Cài đặt lên thiết bị Android qua ADB](#bước-3-cài-đặt-lên-thiết-bị-android-qua-adb-1)
   - [Bước 4: Khởi chạy máy chủ giả lập](#bước-4-khởi-chạy-máy-chủ-giả-lập)
5. [Bảng điều khiển Web Admin](#-bảng-điều-khiển-web-admin)
6. [Công cụ dòng lệnh CLI](#-công-cụ-dòng-lệnh-cli)
7. [Kiểm thử tự động](#-kiểm-thử-tự-động)
8. [Tài liệu kỹ thuật liên quan](#-tài-liệu-kỹ-thuật-liên-quan)

---

### ✨ Tính năng nổi bật

#### 🎮 Khôi phục gameplay trọn vẹn & Đã sửa lỗi triệt để
- **Toàn bộ 3 Chương cốt truyện (Full Chapters 1, 2, 3)**:
  - **Chương 1 (Phòng của Guitar Girl)**: Mở khóa và trò chuyện đầy đủ với **toàn bộ 15/15 người theo dõi** (Joy, Bạn tiệm tiện lợi, Thầy chủ nhiệm, Tiền bối trầm lặng, Moa, Elle, Amber, Yeri, Mocha Latte, Nova, Sua, Jae, v.v.), bao gồm các phòng chat nhóm Joy & Moa với kịch bản chuẩn gốc.
  - **Chương 2 (Tiệm bánh hạnh phúc)**: Kết nối mượt mà cốt truyện phòng chat giữa người theo dõi cũ và 8 người theo dõi mới (Reading Fox, Ruby, Alex, Busking TV, Sora, Jessica) qua các chuỗi câu chuyện phòng 12, 16, 17.
  - **Chương 3 (Trường cấp 3 Sunshine)**: Chế độ Tour màn chơi 1001–2010 với tỉ lệ rơi quà biểu diễn (Encore gifts) ngẫu nhiên theo đúng bảng trọng số gốc; bảo toàn trọn vẹn kịch bản hướng dẫn tân thủ (Tutorial) của Moa khi lần đầu mở khóa.
- **Hệ thống Âm nhạc (Music Discs)**:
  - Đầy đủ 50 đĩa nhạc (26 bài Khu vực 1, 24 bài Khu vực 2).
  - Chuẩn hóa hiển thị vật phẩm sự kiện Bản Sonata của Mozart (Song 12) chuẩn dạng "Không thể mua".
- **Bộ chuyển đổi Số lớn BigNumber (`currency.py`)**:
  - Khắc phục triệt để lỗi tràn số nguyên 64-bit (`uint64` / `int64` overflow > $1.84 \times 10^{19}$) khi tài khoản đạt số Tim bậc cao ($10^{21} = \text{G}, 10^{24} = \text{H} \dots 10^{2109} = \text{ZZ}$).
  - Hỗ trợ đầy đủ 702 đơn vị chuẩn Alphabet notation theo IL2CPP Unity (`A` đến `ZZ`).
  - Kẹp biên an toàn và hiển thị xem trước trực quan (Live Preview) trong Web Admin.

#### 🎁 Sự kiện & Kinh tế game cân bằng
- **Thẻ Sao (Star Pass)**:
  - Hỗ trợ trọn vẹn 13 Mùa giải (Seasons 1–13) với tên mùa bản địa hóa chính thức, nhận mốc thưởng Free Pass chuẩn xác theo Bảng dữ liệu Neowiz.
  - Hỗ trợ mua Mở khóa Slot Live trong cửa hàng Thẻ Sao (`item_buy.py` category 20).
- **Sự kiện Điểm danh (Attendance)**:
  - Điểm danh tân thủ 7 ngày và Kỷ niệm 1 năm (1st Anniversary) với cơ chế bật/tắt hot-reload tức thì từ Web Admin.
- **Hòm thư hệ thống chuẩn Honkai: Star Rail**:
  - Tài khoản mới tạo (tân thủ) chỉ nhận duy nhất Thư chào mừng khởi đầu, hoàn toàn không bị dội lại hàng chục thư sự kiện/bảo trì cũ trong quá khứ.
  - Hỗ trợ phát hành thư hệ thống đa ngôn ngữ chuẩn xác cho toàn bộ **12 ngôn ngữ client**: `ko`, `en`, `jp`, `zh_chs`, `zh_cht`, `vi`, `es`, `it`, `id`, `th`, `pt`, `hi`.
- **Nhiệm vụ người theo dõi Joy (Follower Quest)**:
  - Hỗ trợ chuỗi nhiệm vụ `#ỦnghộGuitarGirl` nhận quà tức thì (Socola CP, Kẹo, Lượt thích, Bánh quy AP).

#### 🛠️ Bộ vá Client & Universal APK (Không cần Google Play)
- **Hoạt động không cần Root thiết bị**: Thích hợp cho BlueStacks (macOS/Windows) và mọi điện thoại Android thật.
- **Vá nhị phân Dalvik bytecode & ARM64 IL2CPP**:
  - Tự động đăng nhập Guest / PmangPlus bypass Google Play Games.
  - Tự động chấp nhận Điều khoản dịch vụ (EULA).
  - Vô hiệu hóa kiểm tra chữ ký ứng dụng (`AppSecurityValidator`).
  - Mở khóa tính năng Thông báo đẩy (Push Notifications) và Thống kê Socola (CP breakdown) trong menu Cài đặt.
  - Tự động đồng bộ mã định danh `UID: #<u_seq>` chuẩn xác giữa game client và máy chủ, chuyển đổi định dạng `USN` sang `UID`.
- **Hợp nhất Split APKs**: Tự động gộp `base.apk`, `base_assets.apk`, `config.arm64_v8a.apk` thành một file **Universal APK duy nhất**, ký số chuẩn v1/v2/v3 schemes.

#### 🌐 Web Admin Dashboard Song ngữ
- **Chuyển đổi ngôn ngữ tức thì**: Hỗ trợ 🇻🇳 **Tiếng Việt** và 🇬🇧 **English**, tự động lưu tùy chọn qua `localStorage`.
- **Quản lý người chơi trực quan**: Tìm kiếm, xem chi tiết, điều chỉnh Cấp độ, Socola CP, Kẹo, Lượt thích (với thanh Live Preview đơn vị game A..ZZ), Bánh quy AP, Vé sưu tập, Thẻ sao Gold & Điểm thẻ sao.
- **Ràng buộc an toàn dữ liệu**: Tự động khóa điều khiển Thẻ sao trong modal người chơi khi tính năng Thẻ sao đang tắt trên toàn server, tránh lỗi bất đồng bộ cơ sở dữ liệu.
- **Bảng điều khiển Sự kiện**: Bật/tắt điểm danh, đổi mùa Thẻ sao (1–13), cấu hình Chapter 3 Tour, gửi thư phát sóng hòm thư trực tiếp kèm quà tặng.

---

### 📂 Cấu trúc dự án

```text
GGServer/
├── emulator/                        # Máy chủ giả lập (Python 3 Server)
│   ├── run.py                       # Điểm khởi chạy server chính (HTTP + Thrift API)
│   ├── serverctl.sh                 # Script quản lý tiến trình (start/stop/restart/log)
│   ├── eventctl.sh / eventctl.py    # CLI điều khiển sự kiện & gửi thư phát sóng
│   ├── broadcast_posts.json         # Danh sách thư phát sóng hòm thư (12 ngôn ngữ)
│   ├── event_config.json            # Cấu hình trạng thái sự kiện & Star Pass
│   ├── gamedata/                    # Bảng dữ liệu tĩnh của game (game_data.json, .b64, .ab)
│   ├── codec/                       # Bộ mã hóa/giải mã Thrift Binary RPC
│   ├── data/                        # Cơ sở dữ liệu SQLite (database.db)
│   ├── server/                      # Core backend logic
│   │   ├── app.py                   # HTTP routing & API dispatching
│   │   ├── admin.py                 # Bảng điều khiển Web Admin song ngữ
│   │   ├── state.py                 # Quản lý trạng thái SQLite & User Session
│   │   ├── currency.py              # Xử lý số lớn BigNumber (A..ZZ)
│   │   ├── event_manager.py         # Quản lý sự kiện & Star Pass Seasons
│   │   └── handlers/                # Các bộ xử lý Thrift RPC (auth, follower, music, post...)
│   └── test_*.py                    # Bộ kiểm thử tự động (Unit Tests)
├── patcher/                         # Bộ công cụ vá Client APK
│   ├── build.sh                     # Script tự động vá và ký số APK
│   ├── merge_apk.py                 # Hợp nhất Split APKs thành 1 Universal APK
│   ├── patch_apk.py                 # Áp dụng các bản vá Dalvik bytecode & ARM64 IL2CPP
│   ├── patch_metadata.py            # Chuyển hướng domain trong global-metadata.dat
│   └── uber-apk-signer.jar          # Trình ký số APK (v1, v2, v3 schemes)
├── orig_apk/                        # Thư mục chứa 3 file APK gốc v8.0.0 (người dùng tự chuẩn bị)
├── out/                             # Thư mục xuất APK thành phẩm đã vá và ký
├── BUG.md                           # Báo cáo chi tiết 28+ lỗi kỹ thuật & phương án khắc phục
├── ANDROID_SETUP.md                 # Hướng dẫn chi tiết thiết lập BlueStacks & Android
├── PROTOCOL.md                      # Phân tích giao thức Apache Thrift của Guitar Girl
└── README.md                        # Tài liệu hướng dẫn sử dụng này
```

---

### 💻 Yêu cầu hệ thống

- **Hệ điều hành**: Linux, macOS, hoặc Windows (khuyến nghị dùng WSL2).
- **Python**: Phiên bản 3.10 trở lên.
- **Java**: OpenJDK 11+ hoặc JRE (cần thiết để chạy `uber-apk-signer.jar`).
- **Android Platform Tools**: Công cụ dòng lệnh `adb` để cài đặt và debug trên máy thật hoặc giả lập.
- **Giả lập / Thiết bị**: BlueStacks 5 (Nougat 64-bit / Pie 64-bit) hoặc bất kỳ thiết bị Android 7.0+ nào (không cần root).

Cài đặt các gói phụ thuộc trên Ubuntu / Debian:
```bash
sudo apt update
sudo apt install -y python3 python3-pip openjdk-17-jre-headless android-tools-adb zip unzip
```

---

### 🚀 Hướng dẫn cài đặt nhanh

#### Bước 1: Chuẩn bị file APK gốc
Tải bản cài đặt Guitar Girl phiên bản **v8.0.0** (dưới dạng XAPK/APKs từ các nguồn uy tín). Đặt 3 file APK thành phần vào thư mục `orig_apk/`:
- `orig_apk/base_assets.apk`
- `orig_apk/com.neowiz.game.guitargirl.apk`
- `orig_apk/config.arm64_v8a.apk`

#### Bước 2: Vá và đóng gói APK
Chọn chế độ kết nối mạng phù hợp:

##### Trường hợp A: Mạng nội bộ (LAN HTTP)
```bash
# Nhập IP máy chủ nội bộ (hoặc để script tự động nhận diện IP)
bash patcher/build.sh http://192.168.1.50:8080
```

##### Trường hợp B: Chơi qua Internet (Cloudflare Tunnel / HTTPS Reverse Proxy - Khuyến nghị)
Khi sử dụng tên miền có chứng chỉ SSL hợp lệ, Android kết nối an toàn mà không cần cài thêm chứng chỉ root CA:
```bash
bash patcher/build.sh https://your-domain.example
```

Script sẽ tự động:
1. Chuyển hướng endpoint sang máy chủ của bạn trong `global-metadata.dat`.
2. Áp dụng các bản vá bytecode trong `classes3.dex` và native ARM64 trong `libil2cpp.so`.
3. Hợp nhất các split APKs thành file Universal APK duy nhất và ký số.
4. File APK hoàn thiện được lưu tại: `out/Guitar_Girl_v8.0.0_NoGooglePlay.apk`.

#### Bước 3: Cài đặt lên thiết bị Android qua ADB
Bật tính năng **Android Debug Bridge (ADB)** trên BlueStacks (Settings → Advanced) hoặc trên điện thoại thật (Developer Options → USB Debugging):

```bash
# 1. Kết nối với thiết bị / giả lập (ví dụ cổng 5555 của BlueStacks)
adb connect 127.0.0.1:5555

# 2. Cài đặt file Universal APK (luôn sử dụng cờ --no-incremental)
adb install --no-incremental -r out/Guitar_Girl_v8.0.0_NoGooglePlay.apk
```

#### Bước 4: Khởi chạy máy chủ giả lập

##### Sử dụng Script Quản lý (Khuyến nghị):
```bash
# Khởi chạy server nền (port mặc định 8080)
./emulator/serverctl.sh start

# Nếu chạy với Domain công khai:
GG_PUBLIC_BASE="https://your-domain.example" ./emulator/serverctl.sh start

# Kiểm tra trạng thái:
./emulator/serverctl.sh status

# Xem log thời gian thực:
./emulator/serverctl.sh log
```

##### Hoặc chạy trực tiếp qua Python:
```bash
python3 emulator/run.py --port 8080
```

Khởi động game Guitar Girl trên thiết bị và thưởng thức trọn vẹn những giai điệu êm dịu!

---

### 🖥️ Bảng điều khiển Web Admin

Truy cập bảng điều khiển quản trị trên trình duyệt web tại:
```text
http://<IP_MÁY_CHỦ>:8080/admin
```
*(Hoặc `https://your-domain.example/admin` nếu chạy qua HTTPS reverse proxy).*

- **Chuyển đổi ngôn ngữ tức thì**: Nhấp vào nút `🇻🇳 Tiếng Việt` hoặc `🇬🇧 English` trên thanh tiêu đề. Lựa chọn ngôn ngữ được ghi nhớ tự động qua các phiên duyệt web.
- **Xem & Chỉnh sửa Người chơi**: Chỉnh sửa Cấp độ, Socola CP, Kẹo, Bánh quy AP, Vé sưu tập và Lượt thích (Tim). Ô nhập Lượt thích hỗ trợ xem trước số lớn BigNumber trực tiếp (ví dụ nhập `42.877G` hiển thị ngay `42,877,000,000,000,000,000,000`).
- **Khóa an toàn Thẻ Sao**: Tự động khóa trường chỉnh sửa Thẻ Sao khi tính năng Thẻ Sao đang tắt trên server, tránh việc tạo dữ liệu không hợp lệ.
- **Quản trị Sự kiện thời gian thực**: Bật/tắt điểm danh, chuyển mùa Thẻ Sao từ 1 đến 13 và phát thư hòm thư kèm phần quà cho toàn bộ người chơi.

---

### ⌨️ Công cụ dòng lệnh CLI

#### 1. Quản lý Server (`serverctl.sh`)
```bash
./emulator/serverctl.sh start      # Khởi chạy server ở chế độ nền
./emulator/serverctl.sh stop       # Dừng server an toàn
./emulator/serverctl.sh restart    # Khởi động lại server
./emulator/serverctl.sh status     # Xem tiến trình PID, cổng lắng nghe & trạng thái Healthcheck
./emulator/serverctl.sh log        # Xem log hoạt động trực tiếp (Ctrl+C để thoát)
```

#### 2. Quản lý Sự kiện & Hòm thư (`eventctl.sh`)
```bash
# Xem trạng thái hoạt động của toàn bộ sự kiện trong game
./emulator/eventctl.sh list

# Chuyển đổi mùa giải Star Pass (từ mùa 1 đến 13)
./emulator/eventctl.sh season 13

# Bật hoặc tắt sự kiện điểm danh
./emulator/eventctl.sh enable 1      # Bật điểm danh tân thủ 7 ngày
./emulator/eventctl.sh disable 2     # Tắt sự kiện kỷ niệm 1 năm

# Gửi thư thông báo và quà tặng vào hòm thư toàn server:
# Cú pháp: sendmail <tiêu_đề> <nội_dung> [cp] [kẹo] [bánh_quy]
./emulator/eventctl.sh sendmail "Quà tặng cuối tuần" "Chúc bạn có những phút giây thư giãn cùng âm nhạc!" 100 500 10
```

---

### 🧪 Kiểm thử tự động

Hệ thống tích hợp bộ unit test toàn diện nhằm bảo đảm độ ổn định cao, ngăn ngừa hồi quy lỗi kinh tế, tiến trình người theo dõi và mua sắm Thẻ Sao:

```bash
# Chạy kiểm thử tin nhắn người theo dõi, live slot và các lỗi vừa sửa:
PYTHONPATH=emulator python3 -m unittest emulator/test_follower_messenger.py \
                                       emulator/test_live_slot_purchase.py \
                                       emulator/test_notification.py \
                                       emulator/test_starpass_and_anniversary.py \
                                       emulator/test_user_fixes_four_issues.py

# Chạy kiểm thử điểm danh, nhiệm vụ hàng ngày và xử lý khóa tài khoản:
PYTHONPATH=emulator python3 -m unittest emulator/test_attendance.py \
                                       emulator/test_ban_behavior.py \
                                       emulator/test_daily_mission.py \
                                       emulator/test_event_manager.py
```

---

### 📖 Tài liệu kỹ thuật liên quan

Để tìm hiểu sâu hơn về kiến trúc kỹ thuật và kết quả phân tích đảo ngược:
- 🐞 **[BUG.md](BUG.md)**: Tổng hợp chi tiết 28+ lỗi kỹ thuật, mã giả lập, phân tích disassembly ARM64 trong `libil2cpp.so` và hướng dẫn khắc phục triệt để.
- 📱 **[ANDROID_SETUP.md](ANDROID_SETUP.md)**: Hướng dẫn chi tiết thiết lập môi trường chơi game trên BlueStacks và điện thoại Android không cần quyền Root.
- 📡 **[PROTOCOL.md](PROTOCOL.md)**: Tài liệu đặc tả cấu trúc gói tin nhị phân Apache Thrift RPC, phân giải opcode và tuần tự hóa dữ liệu.

---

## ⚖️ Disclaimer / Miễn trừ trách nhiệm

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

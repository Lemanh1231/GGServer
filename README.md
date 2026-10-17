# 🎸 Guitar Girl Private Server Emulator (GGServer)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Android%20%7C%20BlueStacks-green.svg)](https://developer.android.com/)
[![Protocol](https://img.shields.io/badge/Protocol-Apache%20Thrift%20Binary-orange.svg)](https://thrift.apache.org/)
[![License](https://img.shields.io/badge/License-Educational%20%2F%20Preservation-purple.svg)](#disclaimer--miễn-trừ-trách-nhiệm)
[![Web Admin](https://img.shields.io/badge/Web%20Admin-Tiếng%20Việt%20%7C%20English-red.svg)](#-web-admin-dashboard-quản-trị-web)

A private server revival emulator and client patcher suite for the End-of-Service (EOS) mobile game **Guitar Girl** (*Cô gái Guitar*, v8.0.0) by Neowiz. This project faithfully reconstructs the game's Apache Thrift RPC protocol, PmangPlus authentication, NeonAPI endpoints, static CDN AssetBundles, live event systems, and provides an interactive bilingual Web Admin Dashboard.

> **Dự án Giả lập Máy chủ Riêng và Bộ Vá Client cho Game Guitar Girl (v8.0.0)**: Khôi phục trọn vẹn trải nghiệm gameplay sau khi game đóng cửa (EOS), bao gồm toàn bộ Chương 1, Chương 2, Chương 3, hệ thống tin nhắn người theo dõi, sự kiện điểm danh, Thẻ Sao, hòm thư đa ngôn ngữ và bảng điều khiển quản trị web song ngữ (Tiếng Việt & English).

---

## 📑 Mục lục / Table of Contents
1. [Tính năng nổi bật / Key Features](#-tính-năng-nổi-bật--key-features)
2. [Cấu trúc thư mục / Project Architecture](#-cấu-trúc-thư-mục--project-architecture)
3. [Yêu cầu hệ thống / Prerequisites](#-yêu-cầu-hệ-thống--prerequisites)
4. [Hướng dẫn cài đặt nhanh / Quick Start Guide](#-hướng-dẫn-cài-đặt-nhanh--quick-start-guide)
   - [Bước 1: Chuẩn bị APK gốc](#bước-1-chuẩn-bị-apk-gốc)
   - [Bước 2: Vá và Build APK (Client Patcher)](#bước-2-vá-và-build-apk-client-patcher)
   - [Bước 3: Cài đặt lên thiết bị Android qua ADB](#bước-3-cài-đặt-lên-thiết-bị-android-qua-adb)
   - [Bước 4: Khởi chạy Máy chủ Giả lập (Server Emulator)](#bước-4-khởi-chạy-máy-chủ-giả-lập-server-emulator)
5. [Web Admin Dashboard (Quản trị Web)](#-web-admin-dashboard-quản-trị-web)
6. [Công cụ dòng lệnh / CLI Utilities](#-công-cụ-dòng-lệnh--cli-utilities)
7. [Kiểm thử tự động / Automated Testing](#-kiểm-thử-tự-động--automated-testing)
8. [Tài liệu kỹ thuật liên quan / Documentation](#-tài-liệu-kỹ-thuật-liên-quan--documentation)
9. [Disclaimer / Miễn trừ trách nhiệm](#disclaimer--miễn-trừ-trách-nhiệm)

---

## ✨ Tính năng nổi bật / Key Features

### 🎮 Gameplay trọn vẹn & Đã sửa lỗi triệt để
- **Toàn bộ 3 Chương cốt truyện (Full Chapters 1, 2, 3)**:
  - **Chương 1**: Mở khóa và trò chuyện đầy đủ với **toàn bộ 15/15 người theo dõi** (Joy, Bạn tiệm tiện lợi, Thầy chủ nhiệm, Tiền bối trầm lặng, Moa, Elle, Amber, Yeri, Mocha Latte, Nova, Sua, Jae, v.v.) cùng phòng chat nhóm Joy & Moa.
  - **Chương 2 (Tiệm bánh hạnh phúc)**: Kết nối mượt mà cốt truyện phòng chat giữa người theo dõi cũ và 8 người theo dõi mới (Reading Fox, Ruby, Alex, Busking TV, Sora, Jessica) với chuỗi câu chuyện phòng 12, 16, 17.
  - **Chương 3 (Trường cấp 3 Sunshine)**: Chế độ Tour màn chơi 1001–2010 với tỉ lệ rơi quà biểu diễn (Encore gifts) ngẫu nhiên theo đúng bảng trọng số gốc; bảo toàn toàn bộ kịch bản hướng dẫn tân thủ (Tutorial) của Moa khi lần đầu mở khóa.
- **Hệ thống Âm nhạc (Music Discs)**: Đầy đủ 50 đĩa nhạc (26 bài Khu vực 1, 24 bài Khu vực 2). Chuẩn hóa hiển thị vật phẩm sự kiện Bản Sonata của Mozart (Song 12) chuẩn dạng "Không thể mua".
- **Bộ chuyển đổi Số lớn BigNumber (Currency Engine)**:
  - Khắc phục triệt để lỗi tràn số nguyên 64-bit (`uint64` / `int64` overflow > $1.84 \times 10^{19}$) khi tài khoản đạt số Tim bậc cao ($10^{21} = \text{G}, 10^{24} = \text{H}... 10^{2109} = \text{ZZ}$).
  - Hỗ trợ đầy đủ 702 đơn vị chuẩn Alphabet notation theo IL2CPP Unity, kẹp biên an toàn và hiển thị trực quan cả trong game lẫn Web Admin.

### 🎁 Sự kiện & Kinh tế game cân bằng
- **Thẻ Sao (Star Pass)**: Hỗ trợ trọn vẹn 13 Mùa giải (Seasons 1–13) với tên mùa bản địa hóa chính thức, nhận mốc thưởng Free Pass chuẩn xác theo Bảng dữ liệu Neowiz.
- **Sự kiện Điểm danh (Attendance)**: Sự kiện tân thủ 7 ngày và Kỷ niệm 1 năm (1st Anniversary) với cơ chế bật/tắt hot-reload đồng bộ từ Web Admin, không tự động kích hoạt ngoài ý muốn.
- **Hòm thư hệ thống chuẩn Honkai: Star Rail**:
  - Tài khoản mới tạo (tân thủ) chỉ nhận duy nhất Thư chào mừng khởi đầu, hoàn toàn không bị dội lại hàng chục thư sự kiện/bảo trì cũ trong quá khứ.
  - Hỗ trợ phát hành thư đa ngôn ngữ chuẩn xác cho toàn bộ **12 ngôn ngữ client** (`ko`, `en`, `jp`, `zh_chs`, `zh_cht`, `vi`, `es`, `it`, `id`, `th`, `pt`, `hi`).
- **Nhiệm vụ người theo dõi Joy (Follower Quest)**: Hỗ trợ chuỗi nhiệm vụ `#ỦnghộGuitarGirl` nhận quà tức thì (Socola CP, Kẹo, Lượt thích, Bánh quy AP).

### 🛠️ Bộ vá Client & Universal APK (No Google Play)
- **Hoạt động không cần Root thiết bị**: Thích hợp cho BlueStacks (macOS/Windows) và mọi điện thoại Android thật.
- **Vá nhị phân Dalvik & IL2CPP ARM64**:
  - Tự động đăng nhập Guest / PmangPlus bypass Google Play Games.
  - Tự động chấp nhận EULA / Điều khoản dịch vụ.
  - Vô hiệu hóa kiểm tra chữ ký ứng dụng (`AppSecurityValidator`).
  - Mở khóa tính năng Thông báo đẩy (Push Notifications) và Thống kê Socola (CP breakdown) trong menu Cài đặt.
  - Tự động đồng bộ mã định danh `UID: #<u_seq>` chuẩn xác giữa game client và máy chủ, chuyển đổi định dạng `USN` sang `UID`.
- **Hợp nhất Split APKs**: Tự động gộp `base.apk`, `base_assets.apk`, `config.arm64_v8a.apk` thành một file **Universal APK duy nhất**, ký số chuẩn v1/v2/v3.

### 🌐 Web Admin Dashboard Song ngữ (Bilingual)
- **Chuyển đổi ngôn ngữ tức thì**: Hỗ trợ 🇻🇳 **Tiếng Việt** và 🇬🇧 **English**, lưu lựa chọn tự động qua `localStorage`.
- **Quản lý người chơi trực quan**: Tìm kiếm, xem chi tiết, điều chỉnh Cấp độ, Socola CP, Kẹo, Lượt thích (với Live Preview đơn vị game A..ZZ), Bánh quy AP, Vé sưu tập, Thẻ sao Gold & Điểm thẻ sao.
- **Ràng buộc an toàn dữ liệu**: Tự động khóa điều khiển Thẻ sao trong modal người chơi khi tính năng Thẻ sao đang tắt trên toàn server, tránh lỗi bất đồng bộ.
- **Bảng điều khiển Sự kiện**: Bật/tắt điểm danh, đổi mùa Thẻ sao, cấu hình Chapter 3 Tour, gửi thư phát sóng hòm thư trực tiếp.

---

## 📂 Cấu trúc thư mục / Project Architecture

```text
GGServer/
├── emulator/                        # Máy chủ giả lập (Python 3 Server)
│   ├── run.py                       # Điểm khởi chạy server chính
│   ├── serverctl.sh                 # Script quản lý tiến trình server (start/stop/restart/log)
│   ├── eventctl.sh / eventctl.py    # CLI điều khiển sự kiện & gửi thư phát sóng
│   ├── broadcast_posts.json         # Danh sách thư phát sóng hòm thư (12 ngôn ngữ chuẩn)
│   ├── event_config.json            # Cấu hình trạng thái sự kiện & Star Pass
│   ├── gamedata/                    # Bảng dữ liệu tĩnh của game (game_data.json, .b64, .ab)
│   ├── codec/                       # Bộ mã hóa/giải mã Thrift Binary RPC
│   ├── server/                      # Core backend logic
│   │   ├── app.py                   # HTTP routing & API dispatching
│   │   ├── admin.py                 # Web Admin Dashboard (HTML/CSS/JS song ngữ)
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
├── orig_apk/                        # Thư mục chứa 3 file APK gốc v8.0.0 (chưa vá)
├── out/                             # Thư mục xuất APK thành phẩm đã vá và ký
├── BUG.md                           # Báo cáo chi tiết 28+ lỗi kỹ thuật & phương án khắc phục
├── ANDROID_SETUP.md                 # Hướng dẫn chi tiết thiết lập BlueStacks & Android
├── PROTOCOL.md                      # Phân tích giao thức Apache Thrift của Guitar Girl
└── README.md                        # Tài liệu hướng dẫn sử dụng này
```

---

## 💻 Yêu cầu hệ thống / Prerequisites

- **Hệ điều hành**: Linux, macOS, hoặc Windows (WSL2 khuyến nghị).
- **Python**: Phiên bản 3.10 trở lên.
- **Java**: OpenJDK 11+ hoặc JRE (cần thiết để chạy `uber-apk-signer.jar`).
- **Android Platform Tools**: Công cụ `adb` để cài đặt và debug trên máy thật hoặc giả lập.
- **Giả lập / Thiết bị**: BlueStacks 5 (không cần root) hoặc bất kỳ thiết bị Android 7.0+ nào.

Cài đặt các gói phụ thuộc trên Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y python3 python3-pip openjdk-17-jre-headless android-tools-adb zip unzip
```

---

## 🚀 Hướng dẫn cài đặt nhanh / Quick Start Guide

### Bước 1: Chuẩn bị APK gốc
Tải bản cài đặt Guitar Girl phiên bản **v8.0.0** (từ APKPure hoặc nguồn uy tín dưới dạng XAPK/APKs). Đặt 3 file APK thành phần vào thư mục `orig_apk/`:
- `orig_apk/base_assets.apk`
- `orig_apk/com.neowiz.game.guitargirl.apk`
- `orig_apk/config.arm64_v8a.apk`

### Bước 2: Vá và Build APK (Client Patcher)
Chọn chế độ kết nối mạng phù hợp:

#### Trường hợp A: Chơi trong mạng nội bộ (LAN HTTP)
```bash
# Tự động phát hiện IP máy chủ nội bộ hoặc truyền trực tiếp IP
bash patcher/build.sh http://192.168.1.50:8080
```

#### Trường hợp B: Chơi qua Internet (Cloudflare Tunnel / Nginx HTTPS - Khuyến nghị)
Khi dùng domain có SSL hợp lệ, Android không cần cài đặt chứng chỉ bảo mật (CA):
```bash
bash patcher/build.sh https://your-domain.example
```

Script sẽ tự động:
1. Chuyển hướng endpoint sang máy chủ của bạn trong `global-metadata.dat`.
2. Áp dụng các bản vá bytecode trong `classes3.dex` và native ARM64 trong `libil2cpp.so`.
3. Hợp nhất các split APKs thành file Universal APK duy nhất và ký số.
4. File APK hoàn thiện được lưu tại: `out/Guitar_Girl_v8.0.0_NoGooglePlay.apk` (hoặc trong `out/patched-apks/`).

### Bước 3: Cài đặt lên thiết bị Android qua ADB

Bật tính năng **Android Debug Bridge (ADB)** trên BlueStacks (Settings → Advanced) hoặc trên điện thoại thật (Developer Options → USB Debugging):

```bash
# 1. Kết nối với giả lập / thiết bị (ví dụ cổng 5555 của BlueStacks)
adb connect 127.0.0.1:5555

# 2. Cài đặt file Universal APK (luôn sử dụng cờ --no-incremental)
adb install --no-incremental -r out/Guitar_Girl_v8.0.0_NoGooglePlay.apk

# Hoặc nếu sử dụng bộ 3 file Split APKs:
adb install-multiple -r out/patched-apks/com.neowiz.game.guitargirl.apk \
                        out/patched-apks/config.arm64_v8a.apk \
                        out/patched-apks/base_assets.apk
```

### Bước 4: Khởi chạy Máy chủ Giả lập (Server Emulator)

#### Sử dụng Script Quản lý (Khuyến nghị):
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

#### Hoặc chạy trực tiếp qua Python:
```bash
python3 emulator/run.py --port 8080
```

Khởi động game Guitar Girl trên thiết bị và thưởng thức trọn vẹn âm nhạc!

---

## 🖥️ Web Admin Dashboard (Quản trị Web)

Truy cập bảng điều khiển quản trị trên trình duyệt tại:
```text
http://<IP_MÁY_CHỦ>:8080/admin
```
*(Hoặc `https://your-domain.example/admin` nếu chạy qua HTTPS reverse proxy).*

### 🌐 Chuyển đổi ngôn ngữ Tiếng Việt & English
Tại thanh tiêu đề trên cùng bên phải, nhấp vào nút ngôn ngữ:
- `🇻🇳 Tiếng Việt`: Toàn bộ giao diện, thẻ thống kê, cột bảng, modal người chơi và thông báo chuyển sang Tiếng Việt.
- `🇬🇧 English`: Toàn bộ giao diện lập tức chuyển đổi sang Tiếng Anh chuẩn quốc tế.
- Lựa chọn ngôn ngữ được lưu tự động trên trình duyệt (`localStorage`).

### 👤 Quản lý người chơi & Công cụ chỉnh sửa tiền tệ BigNumber
- Xem danh sách người chơi, tìm kiếm theo Tên hoặc User Sequence ID (`u_seq`).
- Điều chỉnh trực tiếp:
  - **Lượt thích (Likes / Tim)**: Hỗ trợ nhập trực tiếp đơn vị game (`42.877G`, `100H`, `1.5AA`...) kèm thanh xem trước giá trị (Live Preview) tức thì, loại bỏ nguy cơ nhập sai hoặc tràn số.
  - **Socola (CP)**, **Kẹo (Candy)**, **Bánh quy AP**, **Vé sưu tập (Collection Tickets)**.
  - **Cấp độ (Level)** nhân vật.
  - **Thẻ sao Gold & Điểm Thẻ sao**: Bảo vệ an toàn tự động — nếu Thẻ sao đang tắt trên hệ thống, modal sẽ khóa và cảnh báo người quản trị bật Thẻ sao trước để bảo vệ tính toàn vẹn dữ liệu.

### 📅 Quản lý Sự kiện & Hòm thư trực tuyến
- Bật/tắt tức thì các sự kiện điểm danh (7 Ngày, Kỷ niệm 1 năm).
- Đổi Mùa giải Thẻ Sao từ Mùa 1 đến Mùa 13 chỉ với 1 click.
- Soạn thảo và gửi thư phát sóng kèm quà tặng trực tiếp tới hòm thư của người chơi trong game.

---

## ⌨️ Công cụ dòng lệnh / CLI Utilities

### 1. Quản lý Server (`serverctl.sh`)
```bash
./emulator/serverctl.sh start      # Khởi chạy server ở chế độ nền
./emulator/serverctl.sh stop       # Dừng server an toàn
./emulator/serverctl.sh restart    # Khởi động lại server
./emulator/serverctl.sh status     # Xem tiến trình PID, cổng lắng nghe & trạng thái Healthcheck
./emulator/serverctl.sh log        # Xem log hoạt động trực tiếp (Ctrl+C để thoát)
```

### 2. Quản lý Sự kiện & Hòm thư (`eventctl.sh`)
```bash
# Xem trạng thái hoạt động của toàn bộ sự kiện trong game
./emulator/eventctl.sh list

# Chuyển đổi mùa giải Star Pass (ví dụ mùa 13)
./emulator/eventctl.sh season 13

# Bật hoặc tắt sự kiện điểm danh tân thủ / kỷ niệm
./emulator/eventctl.sh enable 1      # Bật điểm danh tân thủ 7 ngày
./emulator/eventctl.sh disable 2     # Tắt sự kiện kỷ niệm 1 năm

# Gửi thư thông báo và quà tặng vào hòm thư toàn server:
# Cú pháp: sendmail <tiêu_đề> <nội_dung> [cp] [kẹo] [bánh_quy]
./emulator/eventctl.sh sendmail "Quà tặng cuối tuần" "Chúc bạn có những giây phút thư giãn cùng âm nhạc!" 100 500 10
```

---

## 🧪 Kiểm thử tự động / Automated Testing

Hệ thống tích hợp bộ unit test toàn diện để bảo đảm tính ổn định, ngăn ngừa hồi quy lỗi kinh tế, dữ liệu hòm thư và tiến trình người theo dõi:

```bash
# Chạy bộ kiểm thử các tính năng người theo dõi, thông báo và sự kiện vừa cập nhật:
PYTHONPATH=emulator python3 -m unittest emulator/test_follower_messenger.py \
                                       emulator/test_notification.py \
                                       emulator/test_starpass_and_anniversary.py \
                                       emulator/test_user_fixes_four_issues.py

# Chạy kiểm thử hệ thống điểm danh và bảo mật tài khoản:
PYTHONPATH=emulator python3 -m unittest emulator/test_attendance.py \
                                       emulator/test_ban_behavior.py \
                                       emulator/test_daily_mission.py
```

---

## 📖 Tài liệu kỹ thuật liên quan / Documentation

Để tìm hiểu sâu hơn về kiến trúc kỹ thuật và kết quả reverse-engineering, vui lòng tham khảo các tài liệu chuyên đề:
- 🐞 **[BUG.md](BUG.md)**: Tổng hợp chi tiết 28+ lỗi kỹ thuật, mã giả lập, phân tích ARM64 disassembly trong `libil2cpp.so` và hướng dẫn khắc phục triệt để.
- 📱 **[ANDROID_SETUP.md](ANDROID_SETUP.md)**: Hướng dẫn chi tiết thiết lập môi trường chơi game trên BlueStacks (macOS/Windows) không cần quyền Root.
- 📡 **[PROTOCOL.md](PROTOCOL.md)**: Tài liệu đặc tả cấu trúc gói tin nhị phân Apache Thrift RPC, cách phân giải opcode và mã hóa Thrift binary.

---

## 🛡️ Disclaimer / Miễn trừ trách nhiệm

- Dự án này được phát triển hoàn toàn vì mục đích **học tập, nghiên cứu kỹ thuật đảo ngược (Reverse Engineering) và bảo tồn trò chơi điện tử** sau khi nhà phát hành chính thức dừng dịch vụ (End of Service).
- Tất cả hình ảnh, tài nguyên đồ họa, âm nhạc và thương hiệu *Guitar Girl* thuộc quyền sở hữu trí tuệ của **Neowiz** và các tác giả liên quan.
- Dự án hoàn toàn phi lợi nhuận, không chứa bất kỳ cơ chế thương mại hóa hay mua bán vật phẩm bằng tiền thật nào.

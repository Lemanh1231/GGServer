# Báo cáo tổng hợp Lỗi và Cách khắc phục (Bug Fixes & Solutions)

Tài liệu này tổng hợp toàn bộ các lỗi gặp phải trong quá trình phát triển, reverse engineering, vá APK (client patcher) và giả lập máy chủ (emulator server) cho Guitar Girl, cùng nguyên nhân chi tiết và phương pháp khắc phục.

---

## MỤC LỤC
1. [Lỗi Client APK, Google Play Services, EULA & Màn hình đen](#1-lỗi-client-apk-google-play-services-eula--màn-hình-đen)
2. [Lỗi Server, Nginx Routing & PmangPlus / NeonAPI Auth](#2-lỗi-server-nginx-routing--pmangplus--neonapi-auth)
3. [Lỗi Database, Dữ liệu người dùng & Hệ thống Ban](#3-lỗi-database-dữ-liệu-người-dùng--hệ-thống-ban)
4. [Lỗi Gameplay, Logic Server & Dữ liệu trong game](#4-lỗi-gameplay-logic-server--dữ-liệu-trong-game)
5. [Quy trình Build, Cài đặt và Kiểm tra chuẩn](#5-quy-trình-build-cài-đặt-và-kiểm-tra-chuẩn)

---

## 1. Lỗi Client APK, Google Play Services, EULA & Màn hình đen

### 1.1. Treo màn hình đen vĩnh viễn sau khi chấp nhận Điều khoản (Terms of Service / EULA)
- **Hiện tượng**: Khởi động game trên thiết bị thật / giả lập, sau khi tích chọn đồng ý Điều khoản dịch vụ (EULA / PPPublisherPolicy) và bấm "Agree and Play", màn hình chuyển sang màu đen hoàn toàn và bị treo vô hạn, không thể vào màn hình tiêu đề hay sảnh.
- **Nguyên nhân**:
  1. Bản vá cũ điều hướng Activity `GooglePlayAuth` và `GamePlayLogin` sang `GuestAuth` (`com.pmangplus.ui.activity.firebase.GuestAuth`). Lớp này thực chất là Firebase Anonymous Auth (`FirebaseAuth.getInstance().signInAnonymously()`). Do không có backend Firebase và API Key thật, lệnh này thất bại và kích hoạt `CallbackManager.LOGIN.onError(...)`.
  2. Khi stub `onCreate()` của Activity bằng lệnh `finish()`, Android trả về mã kết quả `RESULT_CANCELED` (0).
  3. Lớp facade của Unity (`PPFacade`) yêu cầu callback `UnitySendMessage(..., "onLogin", ...)` thành công để khởi tạo và resume SurfaceView. Khi callback thất bại hoặc bị hủy, Unity không bao giờ resume SurfaceView, dẫn đến màn hình đen vĩnh viễn.
- **Cách khắc phục**:
  - Không điều hướng sang `GuestAuth`. Giữ nguyên Activity đích là `GamePlayLogin` (`com.pmangplus.ui.activity.login.GamePlayLogin`).
  - Trong Dalvik bytecode của `GamePlayLogin.onCreate()` (`classes3.dex`), thay thế hoàn toàn lời gọi Google Play Games Client (`PlayGames.getGamesSignInClient().signIn()`) bằng việc gọi trực tiếp phương thức native `GamePlayLogin.login("guest", "user")`.
  - Lệnh này kích hoạt luồng đăng nhập gốc của PmangPlus gửi lên server giả lập tại `/accounts/v3/global/login`, từ đó kích hoạt `GamePlayLogin$1.onSuccess(...)` -> gửi callback `onLogin` thành công về Unity, giúp game resume màn hình và tải tiếp bình thường.

---

### 1.2. Lỗi ART Verifier: `invoke-super/virtual can't be used on private method GamePlayLogin.login`
- **Hiện tượng**: Ứng dụng crash ngay khi khởi chạy với thông báo lỗi:
  ```text
  java.lang.VerifyError: Verifier rejected class com.pmangplus.ui.activity.login.GamePlayLogin: 
  void com.pmangplus.ui.activity.login.GamePlayLogin.onCreate(android.os.Bundle) failed to verify: 
  [0x2E] invoke-super/virtual can't be used on private method void GamePlayLogin.login(java.lang.String, java.lang.String)
  ```
- **Nguyên nhân**: Trong Dalvik bytecode, phương thức `GamePlayLogin.login(String, String)` có cờ truy cập là `0x2` (`ACC_PRIVATE`). Máy ảo Android ART yêu cầu mọi phương thức private phải được gọi bằng opcode `invoke-direct` (`0x70`), không được dùng `invoke-virtual` (`0x6e`).
- **Cách khắc phục**:
  - Đổi opcode từ `6e 30 f5 a0 02 01` sang `70 30 f5 a0 02 01` (`invoke-direct {v2, v0, v1}, GamePlayLogin.login`).

---

### 1.3. Lỗi thiếu thanh ghi `outs_size` trong Code Item Header của Dalvik
- **Hiện tượng**: Lời gọi `invoke-direct` truyền 3 tham số (`this`, `"guest"`, `"user"`) có thể gây tràn frame hoặc bị từ chối bởi ART bytecode verifier.
- **Nguyên nhân**: Header của phương thức `onCreate` ban đầu khai báo `outs_size = 2` (vì trước đó chỉ gọi các hàm tối đa 2 tham số). Khi gọi `login` với 3 tham số, `outs_size` không đủ.
- **Cách khắc phục**:
  - Tại code item header của `GamePlayLogin.onCreate` (offset `3886124 - 16`), chỉnh sửa trường `outs_size` từ `0x0002` thành `0x0003` (`0300`).

---

### 1.4. Lỗi hỏng cấu trúc String Table DEX (`Out-of-order string_ids` & `String longer than indicated size 0`)
- **Hiện tượng**: Khởi động app crash với lỗi `ClassNotFoundException: Didn't find class "FirebaseInitProvider"` do ART từ chối load toàn bộ file `classes3.dex`. Khi chạy `dexdump -f` báo lỗi:
  ```text
  dexdump: Failure to verify dex file: Out-of-order string_ids
  dexdump: Failure to verify dex file: String longer than indicated size 0
  ```
- **Nguyên nhân**:
  1. Thay thế chuỗi `www.neonapi.com/api` (19 ký tự) bằng `kotori.click/api` (16 ký tự) và chèn các byte `\x00` padding. Trình kiểm tra `DexFileVerifier` của ART quét tuần tự từng byte trong string data section; các byte `0x00` bị hiểu nhầm là chuỗi độ dài 0 không có terminator hợp lệ.
  2. Bảng định danh chuỗi (`string_ids`) trong file DEX bắt buộc phải sắp xếp theo thứ tự bảng chữ cái (lexicographical MUTF-8 order). Chuỗi `kotori.click` (bắt đầu bằng `'k'`) nằm giữa `www.gstatic` và `www.recaptcha` (bắt đầu bằng `'w'`) làm sai lệch trật tự sắp xếp của file DEX.
- **Cách khắc phục**:
  - Không sửa đổi trực tiếp vào String Table của file DEX. 
  - Toàn bộ URL cấu hình dịch vụ mạng (bao gồm các domain `neonapi.com` và `pmang.cloud`) đều đã được điều hướng sạch sẽ thông qua `patch_metadata.py` trong `global-metadata.dat` của Unity C#, giúp `classes3.dex` duy trì cấu trúc nhị phân nguyên bản 100% hợp lệ.

---

### 1.5. Lỗi kiểm tra tính toàn vẹn chữ ký APK (`AppSecurityValidator`)
- **Hiện tượng**: Khi APK được giải nén, chỉnh sửa và ký lại bằng keystore tùy chỉnh (`gg.keystore`), game gọi API kiểm tra chữ ký và bị server từ chối / báo lỗi bảo mật 403.
- **Nguyên nhân**: Lớp `AppSecurityValidator` của Neowiz tính toán hash chữ ký của APK và so sánh với chứng chỉ phát hành chính thức.
- **Cách khắc phục**:
  - Trong `classes3.dex` tại offset `0x3b81d8`, thay thế các chỉ mục kiểm tra của phương thức `AppSecurityValidator.checkAppSignatureValidity()` bằng opcode `0e00000000000000` (`return-void`), vô hiệu hóa hoàn toàn cơ chế kiểm tra chữ ký của game.

---

### 1.6. Tự động đồng ý Điều khoản (Bypass EULA Popup)
- **Hiện tượng**: Popup Điều khoản dịch vụ và Chính sách quyền riêng tư thường xuyên hiện lại hoặc gây xung đột giao diện trên một số dòng máy.
- **Cách khắc phục**:
  - Tại các offset `0x3be470`, `0x3be510`, `0x3be558` trong `classes3.dex`, thay thế phần thân của 3 hàm:
    - `Utility.isAgreeAllEula()`
    - `Utility.isAgreeMobileServiceEula()`
    - `Utility.isAgreePrivacyEula()`
  - Thay bằng bytecode `12100f0000000000` (`const/4 v0, #1; return v0; nop; nop`), khiến game luôn coi như người chơi đã đồng ý mọi điều khoản, không bao giờ bật popup EULA lên nữa.

---

### 1.7. Lỗi cài đặt Split APK & Incremental Install trên Android 14 / HyperOS
- **Hiện tượng**: Chạy `adb install` thông thường báo `Success` nhưng hệ thống báo `Unable to find package: com.neowiz.game.guitargirl` hoặc không tìm thấy Activity.
- **Nguyên nhân**: Android 12+ mặc định kích hoạt cờ `--incremental`. Khi đường truyền mạng ADB ngắt kết nối daemon streaming trước khi file nạp xong hoàn toàn, quá trình cài đặt bị treo dở dang.
- **Cách khắc phục**:
  - Luôn sử dụng cờ `--no-incremental` khi cài đặt qua ADB:
    ```bash
    adb install --no-incremental -r out/Guitar_Girl_v8.0.0_NoGooglePlay.apk
    ```
  - Hợp nhất toàn bộ Split APKs (`base.apk`, `base_assets.apk`, `config.arm64_v8a.apk`) thành một file APK Universal duy nhất thông qua công cụ [merge_apk.py](file:///root/project/GGServer/patcher/merge_apk.py) để người dùng chỉ cần cài 1 file APK duy nhất.

---

## 2. Lỗi Server, Nginx Routing & PmangPlus / NeonAPI Auth

### 2.1. Lỗi Nginx 404/403 cho các endpoint PmangPlus không có tiền tố `/api/`
- **Hiện tượng**: Ứng dụng gọi các API xác thực tài khoản như `/accounts/v3/global/login`, `/referrer/save`, `/gcm/...` nhưng Nginx trả về lỗi `404 Not Found`.
- **Nguyên nhân**: Cấu hình Nginx trước đây chỉ proxy các request bắt đầu bằng `^/api/`, trong khi SDK PmangPlus gọi cả hai dạng: có `/api/` và không có `/api/`.
- **Cách khắc phục**:
  - Cập nhật cấu hình `/etc/nginx/sites-available/kotori.click`:
    ```nginx
    location ~ ^/(api/|accounts/|eula/|referrer/|gcm/|app/|store/|main/|user/) {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    ```
  - Cập nhật [auth.py](file:///root/project/GGServer/emulator/server/auth.py) và [app.py](file:///root/project/GGServer/emulator/server/app.py) để tự động chuẩn hóa (strip `/api/`) cho mọi route xác thực.

---

### 2.2. Lỗi ERROR_90004 khi đăng nhập lần đầu
- **Hiện tượng**: Màn hình game hiển thị hộp thoại `Không thể kết nối mạng. Thử lại ngay? (ERROR_90004) USN: 452465183(PlayGame)`.
- **Nguyên nhân**: Sau khi đăng nhập, client đồng thời yêu cầu tải dữ liệu bảng `table_bundlesize.ab` và đồng bộ tiến trình ban đầu (`userLogin` và `userSave`). Khi thời gian phản hồi giữa các request có độ trễ hoặc token phiên vừa tạo chưa đồng bộ với save state, client bật popup thử lại.
- **Cách khắc phục**:
  - Đảm bảo endpoint `userLogin` luôn trả về đầy đủ cấu trúc `user`, `area_data`, `user_contents` và `attendance_date`.
  - Phục vụ đầy đủ AssetBundle manifest và file `table_bundlesize.ab` với header ETag và 200 OK. Khi bấm "Kết nối lại", game tự động lưu phiên thành công và vào sảnh chính mượt mà.

---

## 3. Lỗi Database, Dữ liệu người dùng & Hệ thống Ban

### 3.1. Dữ liệu rác và xung đột Device Token khi reset tài khoản
- **Hiện tượng**: Khi xóa người dùng hoặc làm sạch database, client cũ gửi lên các token hoặc ID người dùng không còn tồn tại, gây lỗi `IntegrityError` hoặc ngoại lệ khóa ngoại trong SQLite.
- **Cách khắc phục**:
  - Khi dọn dẹp cơ sở dữ liệu: sao lưu file `.db`, drop toàn bộ bảng cũ, tạo lại schema sạch và reset sequence `sqlite_sequence`.
  - Bộ sinh profile dự phòng (`fallback profile`) tự động tạo mới tài khoản với `u_seq` kế tiếp nếu không tìm thấy bản ghi cũ, không làm gián đoạn trải nghiệm của người chơi.

### 3.2. Chặn thiết bị / tài khoản (Ban System)
- **Cơ chế**: Khi một tài khoản hoặc thiết bị nằm trong danh sách đen (`is_banned = 1`):
  - Mọi request `userSave` gửi lên bị chặn lại và lưu vào thư mục cách ly `emulator/captures/banned/`.
  - Trả về mã lỗi thích hợp để client ngưng đồng bộ tài nguyên gian lận lên hệ thống máy chủ.

---

## 4. Lỗi Gameplay, Logic Server & Dữ liệu trong game

### 4.1. Sự kiện đăng nhập 7 ngày (Attendance Event) bị ẩn và không thể nhận thưởng
- **Nguyên nhân**: Server luôn trả về `status = N` cho `setAttendance(check)` và tự động cộng dồn phần thưởng hàng ngày khi tạo danh sách `getEventRewardList`. Client hiểu rằng sự kiện đăng nhập đã hoàn thành trước khi người chơi nhìn thấy.
- **Cách khắc phục**:
  - `setAttendance(check)` trả về `Y` khi phần thưởng hôm nay chưa được nhận.
  - `setAttendance(add)` thực hiện nhận thưởng 1 lần duy nhất, cập nhật trạng thái điểm danh và trao thưởng tương ứng.
  - Loại bỏ logic tự động nhận thưởng bên trong `getEventRewardList`.
  - Chặn nhận thưởng lặp lại trong cùng một ngày.

---

### 4.2. Khởi tạo tài khoản mới bị gán số dư CP và Kẹo khổng lồ
- **Nguyên nhân**: Tài khoản mới được seed với 1,000,000 CP và 100,000 Candy, làm mất đi tính cân bằng và trải nghiệm cày cuốc ban đầu của game.
- **Cách khắc phục**:
  - Đặt lại giá trị mặc định cho tài khoản mới: `u_cp = 0`, `u_candy = 0`, và `u_free_cp = 0`.
  - Tự động di chuyển (migrate) các tài khoản cũ có seed 1,000,000 CP về mức cân bằng khi đăng nhập.

---

### 4.3. Nâng cấp kỹ năng (Skill Upgrade) trả về đối tượng rỗng `{}`
- **Nguyên nhân**: Hàm `state.save_user()` xóa các trường nội bộ trực tiếp trên đối tượng bộ nhớ (in-place mutation). Lúc này handler `buyContents` đã nạp đối tượng đó vào response, dẫn đến client nhận được `{}` rỗng và tưởng nâng cấp thất bại.
- **Cách khắc phục**:
  - Cơ chế lưu trữ luôn làm việc trên bản sao độc lập (`deepcopy`), không bao giờ biến đổi trực tiếp các object đang nằm trong response handler.

---

### 4.4. Kỹ năng bị mở khóa trước cấp độ yêu cầu (Skill Level Gate)
- **Nguyên nhân**: Profile mặc định chèn thêm kỹ năng cấp cao ngay từ lúc tạo mới.
- **Cách khắc phục**:
  - Giới hạn chỉ trả về kỹ năng khởi đầu dưới level 10. Kỹ năng kế tiếp chỉ được cấp phát khi nhân vật đạt đủ level 10 trở lên.

---

### 4.5. Star Pass trả về phần thưởng và thẻ tháng giả mạo
- **Nguyên nhân**: `setSubscribe` trả về danh sách 100 gói đăng ký ảo và `setPassReward` luôn phát sinh phần thưởng giả lập không có trong game data.
- **Cách khắc phục**:
  - Đọc cấu hình phần thưởng Free Star Pass trực tiếp từ `SubscribePassReward` và `reward_group` trong `game_data.json`.
  - Đảm bảo tính idempotent: nhận lại bước đã claim sẽ không trả thêm quà.
  - Không cấp phát thẻ Gold Star Card trả phí nhằm giữ game hoạt động theo cơ chế Free Pass nguyên bản.

---

## 5. Quy trình Build, Cài đặt và Kiểm tra chuẩn

### 5.1. Build APK không Google Play
Chạy script build với domain máy chủ:
```bash
bash patcher/build.sh https://kotori.click
```
Script sẽ tự động:
1. Vá URL trong `global-metadata.dat` sang domain máy chủ đích.
2. Áp dụng các bản vá Dalvik bytecode trong `classes3.dex` (auto-login, auto-agree EULA, disarm validator).
3. Hợp nhất các file Split APKs thành bản Universal APK duy nhất.
4. Ký số APK bằng `uber-apk-signer` với scheme v1, v2, v3.
5. Xuất file tại: `out/Guitar_Girl_v8.0.0_NoGooglePlay.apk`.

### 5.2. Cài đặt lên thiết bị Android qua ADB
```bash
# 1. Gỡ cài đặt bản cũ (nếu muốn làm sạch hoàn toàn) hoặc cài đè
adb -s <DEVICE_IP:PORT> install --no-incremental -r out/Guitar_Girl_v8.0.0_NoGooglePlay.apk

# 2. Khởi chạy game
adb -s <DEVICE_IP:PORT> shell am start -n com.neowiz.game.guitargirl/com.google.firebase.MessagingUnityPlayerActivity
```

### 5.3. Khởi chạy Server Giả lập
```bash
cd /root/project/GGServer
python3 emulator/run.py --port 8080
```
Server chạy phía sau Nginx HTTPS reverse proxy (`https://kotori.click`).

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
  1. Thay thế chuỗi `www.neonapi.com/api` (19 ký tự) bằng domain ngắn hơn (ví dụ 16 ký tự) và chèn các byte `\x00` padding. Trình kiểm tra `DexFileVerifier` của ART quét tuần tự từng byte trong string data section; các byte `0x00` bị hiểu nhầm là chuỗi độ dài 0 không có terminator hợp lệ.
  2. Bảng định danh chuỗi (`string_ids`) trong file DEX bắt buộc phải sắp xếp theo thứ tự bảng chữ cái (lexicographical MUTF-8 order). Một chuỗi mới có chữ cái đầu lệch vị trí sẽ phá vỡ trật tự bảng chữ cái của file DEX.
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

### 1.8. Lỗi khóa Offline các nút Thông báo (Push Notifications) và Thống kê Socola (CP Breakdown) trong Cài đặt
- **Hiện tượng** (hình `image.png` và `image copy.png`):
  1. Trong menu Cài đặt (`Cài đặt`), mục `Thông báo`: hai nút bật/tắt "Bật thông báo đẩy" (Day Push Notifications) và "Bật thông báo đẩy vào ban đêm (9h tối đến 8h sáng)" (Night Push Notifications) hiển thị icon đỏ mất kết nối (biểu tượng sóng wifi gạch chéo), bấm vào không có phản hồi và không thể bật tắt.
  2. Mục `Socola` (Chocolate / CP Breakdown): hiển thị dạng gạch ngang mất kết nối `[ - ] + [ - ] = [ - ]` cùng các icon đỏ mất kết nối, không hiển thị số lượng CP miễn phí và CP trả phí.
- **Nguyên nhân chi tiết (Reverse-Engineering qua IL2CPP Dump & ARM64 Disassembly)**:
  1. Trong `libil2cpp.so`, các hàm khởi tạo giao diện Cài đặt và sự kiện click:
     - `GgUIInGameSettingManager.SetupNotifications` (RVA `0x1E17CB0`, file offset `0x1E13CB0`)
     - `GgUIInGameSettingManager.OnUIEventClickDayNotifications_KR` (RVA `0x1E177AC`, file offset `0x1E137AC`)
     - `GgUIInGameSettingManager.OnUIEventClickNightNotifications_KR` (RVA `0x1E1C750`, file offset `0x1E18750`)
     - `GgUIInGameSettingManager.OnUIEventClickNotifications_GO` (RVA `0x1E19248`, file offset `0x1E15248`)
     - `GgUIInGameSettingManager_Goods.SetGoodsOnline` (RVA `0x1ED88F0`, file offset `0x1ED48F0`)
  2. Game thực hiện 2 tầng kiểm tra:
     - Kiểm tra trạng thái mạng: `GlobalManagerSGT.get_IsOffline()` (`0x1D22A44`).
     - Kiểm tra kiểu tài khoản: `ApiServerSGT.JoinType` (field offset `0x80`) == `1` (`PmangPlus`).
  3. Khi chạy qua máy chủ giả lập hoặc đăng nhập ẩn danh / Guest (`is_guest_login: True`), `JoinType` được đặt là `0` (`Guest`). Vì `JoinType != 1`, lệnh điều kiện `b.ne` rẽ nhánh trực tiếp sang khối Offline:
     - Gọi `m_goNotifications_Offline_KR.SetActive(true)` (chứa icon đỏ gạch chéo) và `m_goNotifications_Online_KR.SetActive(false)`.
     - Các sự kiện click toggle thoát sớm (`b.ne` tới `ret`), bỏ qua hàm lưu cài đặt thông báo.
     - Tương tự với CP: gọi `SetGoodsOnline(false)`, hiển thị `m_goGoods_Offline` (`[ - ] + [ - ] = [ - ]`) và không gọi `ReqUserLoad_UpdateCP`.
- **Cách khắc phục triệt để**:
  1. **Binary Patch trực tiếp trên ARM64 `libil2cpp.so`**:
     - Vô hiệu hóa toàn bộ các lệnh nhảy rẽ nhánh kiểm tra offline và `JoinType` thành `NOP` (`1f2003d5`), ép luồng thực thi luôn đi vào nhánh Online:
       - Offset `0x1E13D04`: `e0080037` (`tbnz`) -> `1f2003d5` (`NOP`)
       - Offset `0x1E13D1C`: `21080054` (`b.ne`) -> `1f2003d5` (`NOP`)
       - Offset `0x1E137D0`: `80010037` (`tbnz`) -> `1f2003d5` (`NOP`)
       - Offset `0x1E137E8`: `c1000054` (`b.ne`) -> `1f2003d5` (`NOP`)
       - Offset `0x1E18774`: `80010037` (`tbnz`) -> `1f2003d5` (`NOP`)
       - Offset `0x1E1878C`: `c1000054` (`b.ne`) -> `1f2003d5` (`NOP`)
       - Offset `0x1E1526C`: `80010037` (`tbnz`) -> `1f2003d5` (`NOP`)
       - Offset `0x1E15284`: `c1000054` (`b.ne`) -> `1f2003d5` (`NOP`)
       - Offset `0x1ED4904`: `00010036` (`tbz`) -> `08000014` (`b #0x1ed8924`)
       - Offset `0x1ED493C`: `e1179f1a` (`cset w1, eq`) -> `21008052` (`mov w1, #1`)
       - Offset `0x1ED4950`: `a1000054` (`b.ne`) -> `1f2003d5` (`NOP`)
     - Tích hợp tự động vào [patch_apk.py](file:///root/project/GGServer/patcher/patch_apk.py) và [merge_apk.py](file:///root/project/GGServer/patcher/merge_apk.py). Cả Universal APK và Split APK đều được tự động áp dụng khi chạy `./build.sh`.
  2. **Đồng bộ Server PmangPlus Auth & State**:
     - Trong [auth.py](file:///root/project/GGServer/emulator/server/auth.py): Đổi `'is_guest_login': False`, `'anonymous_yn': 'N'`, `'provider_display_name': 'PmangPlus'` trong API `/accounts/v3/global/login`.
     - Trong [state.py](file:///root/project/GGServer/emulator/server/state.py): Đặt `'u_join_type': 1` trong default userdata và trong hàm `_reconstruct_user`, đảm bảo `userLogin` và `userLoad` luôn trả về `u_join_type: 1`.

---

## 2. Lỗi Server, Nginx Routing & PmangPlus / NeonAPI Auth

### 2.1. Lỗi Nginx 404/403 cho các endpoint PmangPlus không có tiền tố `/api/`
- **Hiện tượng**: Ứng dụng gọi các API xác thực tài khoản như `/accounts/v3/global/login`, `/referrer/save`, `/gcm/...` nhưng Nginx trả về lỗi `404 Not Found`.
- **Nguyên nhân**: Cấu hình Nginx trước đây chỉ proxy các request bắt đầu bằng `^/api/`, trong khi SDK PmangPlus gọi cả hai dạng: có `/api/` và không có `/api/`.
- **Cách khắc phục**:
  - Cập nhật cấu hình Nginx (ví dụ `/etc/nginx/sites-available/your-domain.conf`):
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

### 4.6. Lỗi tràn số nguyên uint64 (> 1.84e19) khi quy đổi số Tim (Likes) sang các bậc đơn vị lớn (G, H, ... ZZ)
- **Hiện tượng**: Khi tài khoản đạt số Tim lớn (từ bậc G trở lên, ví dụ $42.877\text{G} = 4.2877 \times 10^{22}$), server gặp ngoại lệ:
  ```text
  OverflowError: Python int too large to convert to SQLite INTEGER
  struct.error: 'q' format requires -9223372036854775808 <= number <= 9223372036854775807
  ```
  Dẫn đến việc lưu trữ thất bại, không lưu được tiến trình hoặc HUD hiển thị sai số lượng Tim.
- **Phân tích Reverse Engineering Client IL2CPP**:
  - Trích xuất cấu trúc từ `libil2cpp.so` + `global-metadata.dat` (TypeDef `ShortScaleString`, phương thức `parseBigInteger` tại `0x20E2DD0`):
    - Game sử dụng `System.Numerics.BigInteger.ToString()` để lấy chuỗi chữ số, tính `len = s.Length`, `unit_idx = (len - 1) / 3`.
    - Client khởi tạo mảng 702 đơn vị (`field_1`): 26 chữ cái đơn `A` ($10^3$)..`Z` ($10^{78}$) và 676 chữ cái đôi `AA` ($10^{81}$)..`ZZ` ($10^{2109}$).
    - $10^3 = \text{A}$, $10^6 = \text{B}$, $10^9 = \text{C}$, $10^{12} = \text{D}$, $10^{15} = \text{E}$, $10^{18} = \text{F}$ ($\approx \text{uint64 max} \approx 1.84 \times 10^{19}$).
    - $10^{21} = \text{G}$, $10^{24} = \text{H}$... hoàn toàn vượt quá ngưỡng 64-bit nguyên!
    - Giới hạn client: `d_Like` (trong `userAreaData`) và `u_like` (trong `userData`) được truyền tải qua Thrift dưới dạng `DOUBLE` (IEEE 754 float64, tối đa $1.7976931348623157 \times 10^{308}$, tương đương đơn vị `CX`/`CY`). Chuỗi nguyên lớn được lưu trong `s_Gp1` / `s_Gp2` (Thrift `STRING`).
- **Nguyên nhân kỹ thuật**:
  1. Python `sqlite3`: Driver C của SQLite chuyển đổi Python `int` thành C `long long` (int64 signed, max $2^{63}-1 \approx 9.22 \times 10^{18}$). Khi truyền một Python `int` lớn hơn $2^{63}-1$ vào câu lệnh `UPDATE user_data SET u_like = ?`, dù cột SQLite khai báo kiểu `REAL`, driver Python vẫn raise `OverflowError` ngay trước khi gửi câu lệnh đến engine SQLite.
  2. Thrift Serializer: Khi pack giá trị `I64` bằng `struct.pack('>q', v)`, nếu một trường bị nhầm kiểu hoặc tràn, Python ném ra `struct.error`.
- **Cách khắc phục triệt để**:
  1. **Tạo module quy đổi chuẩn [currency.py](file:///root/project/GGServer/emulator/server/currency.py)**:
     - Định nghĩa đủ 702 đơn vị game `A`..`ZZ` chuẩn xác theo metadata IL2CPP.
     - Hàm `parse_currency(val)`: Chấp nhận mọi định dạng đầu vào (số nguyên, số thực, chuỗi khoa học `1e22`, chuỗi đơn vị game `42.877G`, `100H`, `1.2AA`). Sử dụng `decimal.Decimal` để tính toán chính xác tuyệt đối, kẹp biên ở `MAX_FLOAT` ($1.79 \times 10^{308}$) để tránh tràn bộ nhớ.
     - Hàm `format_currency(val)`: Định dạng chuẩn `{0}.{1}{2}` (`42.877G`, `100.000H`) khớp 100% với giao diện Unity client.
  2. **Vá cơ chế lưu SQLite & Đồng bộ State**:
     - Trong [state.py](file:///root/project/GGServer/emulator/server/state.py), luôn ép kiểu `float(like_f)` khi bind vào tham số SQL cho cột `u_like` (SQLite `REAL`), kích hoạt `PyFloat_AsDouble` thay vì `PyLong_AsLongLong`, hỗ trợ an toàn tới $1.79 \times 10^{308}$.
     - `s_Gp1` trong `areas` lưu trữ chuỗi số nguyên lớn chính xác `s_str` để client Unity parse thành `BigInteger`.
  3. **Vá Thrift Binary Codec**:
     - Trong [thrift.py](file:///root/project/GGServer/emulator/codec/thrift.py), bổ sung cơ chế clamp tự động cho `Writer.i16`, `Writer.i32`, `Writer.i64`, `Writer.dbl`, loại bỏ hoàn toàn nguy cơ sập luồng do `struct.error`.
  4. **Nâng cấp Admin Dashboard UI**:
     - Cho phép quản trị viên nhập trực tiếp đơn vị game (`42.877G`, `100H`...) tại cả hai ô "Thêm Tim" và "Đặt chính xác số Tim".
     - Tích hợp tính năng live preview tức thì ngay dưới ô nhập liệu để kiểm tra giá trị quy đổi trước khi lưu.

---

### 4.7. Lỗi Hòm thư hệ thống nhận hàng loạt Thư thông báo cũ khi tạo Tài khoản mới (Honkai: Star Rail Mailbox Rule)
- **Hiện tượng**:
  - Khi một tài khoản mới được tạo (tân thủ), ngay khi mở Hòm thư (Post / Mailbox) lần đầu, người chơi nhận tới hàng chục lá thư thông báo cũ đã phát hành từ trước đó (như các thông báo bảo trì, sự kiện trực tiếp cũ...).
  - Ngược lại với các game gacha / online hiện đại như *Honkai: Star Rail* hay *Genshin Impact*, người chơi mới chỉ được nhận Thư chào mừng khởi đầu (Welcome Starter Mail), tuyệt đối không nhận lại các thư thông báo phát sóng (broadcast mail) đã gửi trước thời điểm đăng ký tài khoản.
- **Nguyên nhân chi tiết**:
  1. Trong [post.py](file:///root/project/GGServer/emulator/server/handlers/post.py), hàm `_get_user_posts(user)` đọc toàn bộ danh sách thông báo từ `emulator/broadcast_posts.json` và chèn tất cả các mục chưa có trong `user['posts']` mà không kiểm tra thời điểm gửi của thư (`create_time`) so với thời gian tạo tài khoản (`created_at`).
  2. Không kiểm tra hạn sử dụng của thư (`del_time`): các thư đã hết hạn (`del_time <= now`) vẫn tồn tại trong file broadcast và bị nhồi vào hòm thư người chơi mới.
  3. Cấu trúc `user_data` ban đầu chưa theo dõi chính xác timestamp đăng ký tài khoản `created_at` (chỉ có trường `u_create_time` dạng ngày `YYYYMMDD` trong userdata hoặc `last_save_time`).
- **Cách khắc phục triệt để**:
  1. **Theo dõi thời điểm khởi tạo tài khoản (`created_at`)**:
     - Trong [state.py](file:///root/project/GGServer/emulator/server/state.py):
       - Khi tạo mới user (`create_user`), gán `'created_at': now_ts`, khởi tạo danh sách rỗng `'posts': []`, `'deleted_post_indices': []`, và `'welcome_post_sent': False`.
       - Trong `_reconstruct_user`, nếu tài khoản chưa có trường `created_at`, tự động phân giải từ `u_create_time` (`YYYYMMDD`) hoặc `last_save_time`.
  2. **Áp dụng quy tắc Honkai: Star Rail & Lọc thư quá hạn (Expiration Pruning)**:
     - Trong [post.py](file:///root/project/GGServer/emulator/server/handlers/post.py):
       - Khi gửi thư qua `send_post`: bổ sung tham số `applies_to_new_users=False`. Mặc định thư phát sóng chỉ gửi đến những người chơi đã tồn tại. Nếu muốn thư phát cho cả người chơi tương lai (như quà tân thủ mở rộng), có thể bật cờ này. Đồng thời tự động dọn dẹp các thư phát sóng đã quá hạn khi lưu file `broadcast_posts.json`.
       - Trong `_get_user_posts`:
         - Bổ sung cơ chế dọn dẹp các thư đã quá hạn (`del_time <= now and not unlimit_flg`).
         - Dọn dẹp các thư phát sóng cũ đã lỡ nạp vào tài khoản nếu thư đó được gửi trước thời điểm người chơi đăng ký (`b_create < user_created_at`). Thư Chào mừng khởi đầu (`idx: 1`) luôn được bảo lưu cho tân thủ.
         - Trong vòng lặp nạp broadcast: chỉ gửi thư phát sóng nếu thư chưa hết hạn VÀ (`applies_to_new_users == True` HOẶC `b_create >= user_created_at`).
         - Đảm bảo Thư chào mừng (`_default_welcome_post`) chỉ được gửi 1 lần duy nhất cho tân thủ.
  3. **Kiểm thử tự động toàn diện**:
     - Bổ sung kịch bản kiểm thử quy tắc Honkai: Star Rail trong [test_notification.py](file:///root/project/GGServer/emulator/test_notification.py), kiểm tra và đảm bảo tài khoản mới tạo sau khi phát thông báo hoàn toàn không nhận thư cũ mà chỉ nhận duy nhất Thư chào mừng.

---

### 4.8. Lỗi Người theo dõi ở Chương 2 (Tiệm bánh hạnh phúc) khi mở khóa không có tin nhắn / không hiển thị phòng chat
- **Hiện tượng**:
  - Ở Chương 2: Tiệm bánh hạnh phúc (Chapter 2: Happy Bakery), khi người chơi mở khóa các Người theo dõi mới (Follower 203..208: Reading Fox, Bạn Ruby, Bạn Alex, Busking TV, Bạn Sora, Jessica) hoặc chuyển giao Người theo dõi cũ từ Chương 1 (Joy 201, Moa 202):
    1. Phòng chat của Người theo dõi mới hoàn toàn không hiển thị trong danh sách Messenger của game ("ko có tin nhắn của người theo dõi đó").
    2. Nếu có hiển thị, khi bấm vào phòng chat hoàn toàn trống trơn không có tin nhắn nào, không có huy hiệu thông báo tin nhắn chưa đọc.
    3. Người theo dõi cũ (Joy 201, Moa 202) không kích hoạt các đoạn hội thoại độc quyền của Chương 2.
- **Phân tích Reverse-Engineering Client (IL2CPP + ARM64 Disassembly + SQLite Game Tables)**:
  1. **Nguyên nhân phòng chat bị ẩn hoàn toàn khỏi giao diện**:
     - Trong `libil2cpp.so` tại RVA `0x1F7B1E8` và `0x1F7BBE0` (`GgUIInGameMessengerManager_Chatting` - hàm dựng danh sách phòng chat Messenger):
       - Client duyệt qua tất cả phòng chat trong `user_messenger`.
       - Với mỗi phòng, client kiểm tra: nếu `GetProceedingIndex(roomId) < 0` VÀ `GetLastCompleteProgressGroup(roomId) < 1`:
         - Nếu `roomId == 1` (Joy tân thủ): Game có ngoại lệ fallback tại `0x1f7ad24`.
         - Nếu `roomId != 1`: Lệnh rẽ nhánh `b.ne 0x1f7b844` **BỎ QUA HOÀN TOÀN PHÒNG CHAT ĐÓ KHỎI GIAO DIỆN!**
       - Khi server trước đây khởi tạo phòng mới với `i_LastConfirmIndex: -1` và một nhóm ban đầu (ví dụ `'114'`), nhóm đó trở thành nhóm đang tiến hành (`m_iProceedingGroup`), còn danh sách nhóm hoàn thành (`m_listCompleteProgressGroup`) rỗng (`Count == 0`). Do đó `GetLastCompleteProgressGroup` trả về `-1`, và `GetProceedingIndex` trả về `-1`. Kết quả là client ẩn vĩnh viễn phòng chat khỏi UI.
  2. **Nguyên nhân phòng chat trống không có tin nhắn**:
     - Tại RVA `0x1EF1CF8` (`GgUIInGameMessengerManager_ChattingDetail` - hiển thị chi tiết tin nhắn trong phòng):
       - Nếu `GetCompleteProgressGroupList` rỗng và `proceedingIndex < 0`, không có tin nhắn nào được thêm vào khung chat (`m_listViewChattingItem`).
  3. **Chuỗi điều kiện tiên quyết liên phòng (`CheckRequirement` & `Contains_CompleteProgressGroup`)**:
     - Tại RVA `0x2242928` (`CheckRequirement(groupId)`):
       - Mỗi nhóm tin nhắn trong `table_db.ab` (bảng `Messenger`) có các điều kiện tiên quyết: yêu cầu cấp độ người theo dõi và đặc biệt là nhóm tin nhắn trước đó ở phòng liên quan phải nằm trong `m_listCompleteProgressGroup` (`Contains_CompleteProgressGroup(reqRoomId, reqGroupId)`).
       - Cụ thể theo đồ thị quan hệ trong game:
         - Follower 203 (Reading Fox - Nhóm 114) yêu cầu Nhóm 103 ở Phòng 12 (Happy Bakery).
         - Follower 204 (Ruby - Nhóm 127) yêu cầu Nhóm 118 ở Phòng 16 (Group chat Joy & Moa).
         - Follower 205 (Alex - Nhóm 138) yêu cầu Nhóm 132 ở Phòng 16.
         - Follower 206 (Busking TV - Nhóm 178) yêu cầu Nhóm 173 ở Phòng 17 (Group chat 4 người).
         - Follower 207 (Sora - Nhóm 181) và Follower 208 (Jessica - Nhóm 186) yêu cầu Nhóm 171 ở Phòng 16.
       - Nếu chuỗi hoàn thành ở các phòng trung gian 12, 16, 17 chưa đạt đến nhóm yêu cầu, client từ chối mở khóa tiến trình tiếp theo.
  4. **Cơ chế Người theo dõi cũ (CH1 sang CH2)**:
     - Người theo dõi 201 (Joy CH2) và 202 (Moa CH2) trong `MessengerChatRoom` không có ID phòng 201 hay 202 riêng. Họ dùng chung Phòng 1 (Joy) và Phòng 5 (Moa), kết hợp các Phòng chat nhóm 16 và 17.
     - Ở CH2, Joy có nhóm độc quyền 111 (Phòng 1), Moa có nhóm độc quyền 110 (Phòng 5).
- **Cách khắc phục triệt để trên Server ([follower.py](file:///root/project/GGServer/emulator/server/handlers/follower.py))**:
  1. **Hiển thị ngay phòng chat với tin nhắn chào mừng và huy hiệu chưa đọc**:
     - Khi mở khóa bất kỳ người theo dõi Chương 2 nào (201..208), khởi tạo `i_LastConfirmIndex: 0` (thay vì `-1`). Điều này giúp `GetProceedingIndex >= 0`, vượt qua điều kiện kiểm tra ở `0x1F7BBE0`, phòng chat xuất hiện ngay lập tức trong Messenger với tin nhắn thứ 0 và icon chấm đỏ chưa đọc.
  2. **Bắc cầu phòng chat Phòng 12 (Happy Bakery)**:
     - Tự động hoàn thành nhóm 103 và mở nhóm 109 (`'80,103,109'`) khi người chơi vào Chương 2 để đáp ứng điều kiện tiên quyết cho Reading Fox (203) và câu chuyện Joy CH2.
  3. **Đồng bộ chuỗi câu chuyện Phòng 16 & Phòng 17**:
     - Phòng 16 (Joy & Moa Group Chat): Duyệt chuỗi tiến trình (`[76, 78, 79, 81, 82, 104]`), tự động mở rộng qua `118` khi có Ruby (204), qua `132` khi có Alex (205), và qua `171` khi có Sora (207) / Jessica (208).
     - Phòng 17 (Group Chat Joy, Moa, Ruby, Alex): Tự động mở khi mở khóa 204..208, hoàn thành qua `173` khi mở khóa Busking TV (206).
  4. **Tách biệt và đồng bộ Người theo dõi cũ (Joy & Moa)**:
     - Follower 201 nhận nhóm 111 tại Phòng 1.
     - Follower 202 nhận nhóm 110 tại Phòng 5 (`'13,110'`).
  5. **Bảo toàn tiến trình đọc của người chơi**:
     - Dùng hàm `_merge_groups_seq` bảo toàn các nhóm người chơi đã xem / hoàn thành, không ghi đè hoặc hạ lùi tiến trình.

---

## 5. Quy trình Build, Cài đặt và Kiểm tra chuẩn

### 5.1. Build APK không Google Play
Chạy script build với domain máy chủ (hoặc IP LAN):
```bash
# Với domain riêng (HTTPS):
bash patcher/build.sh https://your-domain.example

# Hoặc với IP LAN:
bash patcher/build.sh http://192.168.1.50:8080
```
Script sẽ tự động:
1. Nạp cấu hình từ `.env` nếu có (hoặc dùng tham số truyền vào).
2. Vá URL trong `global-metadata.dat` sang domain máy chủ đích.
3. Áp dụng các bản vá Dalvik bytecode trong `classes3.dex` (auto-login, auto-agree EULA, disarm validator).
4. Hợp nhất các file Split APKs thành bản Universal APK duy nhất.
5. Ký số APK bằng `uber-apk-signer` với scheme v1, v2, v3.
6. Xuất file tại: `out/Guitar_Girl_v8.0.0_NoGooglePlay.apk`.

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
Server có thể chạy trực tiếp hoặc đứng sau Nginx / Cloudflare Tunnel HTTPS reverse proxy (`https://your-domain.example`).

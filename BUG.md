# Báo cáo tổng hợp Lỗi và Cách khắc phục (Bug Fixes & Solutions)

Tài liệu này tổng hợp toàn bộ các lỗi gặp phải trong quá trình phát triển, reverse engineering, vá APK (client patcher) và giả lập máy chủ (emulator server) cho Guitar Girl, cùng nguyên nhân chi tiết và phương pháp khắc phục.

---

## MỤC LỤC
1. [Lỗi Client APK, Google Play Services, EULA & Màn hình đen](#1-lỗi-client-apk-google-play-services-eula--màn-hình-đen)
   - [1.1. Treo màn hình đen vĩnh viễn sau khi chấp nhận Điều khoản (Terms of Service / EULA)](#11-treo-màn-hình-đen-vĩnh-viễn-sau-khi-chấp-nhận-điều-khoản-terms-of-service--eula)
   - [1.2. Lỗi ART Verifier: `invoke-super/virtual can't be used on private method GamePlayLogin.login`](#12-lỗi-art-verifier-invoke-supervirtual-cant-be-used-on-private-method-gameplayloginlogin)
   - [1.3. Lỗi thiếu thanh ghi `outs_size` trong Code Item Header của Dalvik](#13-lỗi-thiếu-thanh-ghi-outs_size-trong-code-item-header-của-dalvik)
   - [1.4. Lỗi hỏng cấu trúc String Table DEX (`Out-of-order string_ids` & `String longer than indicated size 0`)](#14-lỗi-hỏng-cấu-trúc-string-table-dex-out-of-order-string_ids--string-longer-than-indicated-size-0)
   - [1.5. Lỗi kiểm tra tính toàn vẹn chữ ký APK (`AppSecurityValidator`)](#15-lỗi-kiểm-tra-tính-toàn-vẹn-chữ-ký-apk-appsecurityvalidator)
   - [1.6. Tự động đồng ý Điều khoản (Bypass EULA Popup)](#16-tự-động-đồng-ý-điều-khoản-bypass-eula-popup)
   - [1.7. Lỗi cài đặt Split APK & Incremental Install trên Android 14 / HyperOS](#17-lỗi-cài-đặt-split-apk--incremental-install-trên-android-14--hyperos)
   - [1.8. Lỗi khóa Offline các nút Thông báo (Push Notifications) và Thống kê Socola (CP Breakdown) trong Cài đặt](#18-lỗi-khóa-offline-các-nút-thông-báo-push-notifications-và-thống-kê-socola-cp-breakdown-trong-cài-đặt)
2. [Lỗi Server, Nginx Routing & PmangPlus / NeonAPI Auth](#2-lỗi-server-nginx-routing--pmangplus--neonapi-auth)
   - [2.1. Lỗi Nginx 404/403 cho các endpoint PmangPlus không có tiền tố `/api/`](#21-lỗi-nginx-404403-cho-các-endpoint-pmangplus-không-có-tiền-tố-api)
   - [2.2. Lỗi ERROR_90004 khi đăng nhập lần đầu](#22-lỗi-error_90004-khi-đăng-nhập-lần-đầu)
3. [Lỗi Database, Dữ liệu người dùng & Hệ thống Ban](#3-lỗi-database-dữ-liệu-người-dùng--hệ-thống-ban)
   - [3.1. Dữ liệu rác và xung đột Device Token khi reset tài khoản](#31-dữ-liệu-rác-và-xung-đột-device-token-khi-reset-tài-khoản)
   - [3.2. Chặn thiết bị / tài khoản (Ban System)](#32-chặn-thiết-bị--tài-khoản-ban-system)
4. [Lỗi Gameplay, Logic Server & Dữ liệu trong game](#4-lỗi-gameplay-logic-server--dữ-liệu-trong-game)
   - [4.1. Sự kiện đăng nhập 7 ngày (Attendance Event) bị ẩn và không thể nhận thưởng](#41-sự-kiện-đăng-nhập-7-ngày-attendance-event-bị-ẩn-và-không-thể-nhận-thưởng)
   - [4.2. Khởi tạo tài khoản mới bị gán số dư CP và Kẹo khổng lồ](#42-khởi-tạo-tài-khoản-mới-bị-gán-số-dư-cp-và-kẹo-khổng-lồ)
   - [4.3. Nâng cấp kỹ năng (Skill Upgrade) trả về đối tượng rỗng `{}`](#43-nâng-cấp-kỹ-năng-skill-upgrade-trả-về-đối-tượng-rỗng-)
   - [4.4. Kỹ năng bị mở khóa trước cấp độ yêu cầu (Skill Level Gate)](#44-kỹ-năng-bị-mở-khóa-trước-cấp-độ-yêu-cầu-skill-level-gate)
   - [4.5. Star Pass trả về phần thưởng và thẻ tháng giả mạo](#45-star-pass-trả-về-phần-thưởng-và-thẻ-tháng-giả-mạo)
   - [4.6. Lỗi tràn số nguyên uint64 (> 1.84e19) khi quy đổi số Tim (Likes) sang các bậc đơn vị lớn (G, H, ... ZZ)](#46-lỗi-tràn-số-nguyên-uint64--184e19-khi-quy-đổi-số-tim-likes-sang-các-bậc-đơn-vị-lớn-g-h--zz)
   - [4.7. Lỗi Hòm thư hệ thống nhận hàng loạt Thư thông báo cũ khi tạo Tài khoản mới (Honkai: Star Rail Mailbox Rule)](#47-lỗi-hòm-thư-hệ-thống-nhận-hàng-loạt-thư-thông-báo-cũ-khi-tạo-tài-khoản-mới-honkai-star-rail-mailbox-rule)
   - [4.8. Lỗi Người theo dõi ở Chương 2 (Tiệm bánh hạnh phúc) khi mở khóa không có tin nhắn / không hiển thị phòng chat](#48-lỗi-người-theo-dõi-ở-chương-2-tiệm-bánh-hạnh-phúc-khi-mở-khóa-không-có-tin-nhắn--không-hiển-thị-phòng-chat)
   - [4.9. Lỗi Sự kiện Kỷ niệm 1 năm (1st Anniversary Event) tự động mở trong game dù trên Web Dashboard không bật](#49-lỗi-sự-kiện-kỷ-niệm-1-năm-1st-anniversary-event-tự-động-mở-trong-game-dù-trên-web-dashboard-không-bật)
   - [4.10. Khóa điều khiển Thẻ Sao (Star Pass / Star Card) trong Admin khi máy chủ chưa kích hoạt Thẻ Sao](#410-khóa-điều-khiển-thẻ-sao-star-pass--star-card-trong-admin-khi-máy-chủ-chưa-kích-hoạt-thẻ-sao)
   - [4.11. Lỗi sự kiện Nhiệm vụ người theo dõi Joy (`FollowerQuest` - #ỦnghộGuitarGirl) không nhận được quà dù đã đạt đủ điều kiện (`image.png`)](#411-lỗi-sự-kiện-nhiệm-vụ-người-theo-dõi-joy-followerquest---ủnghộguitargirl-không-nhận-được-quà-dù-đã-đạt-đủ-điều-kiện-imagepng)
   - [4.12. Lỗi mở khóa người theo dõi ở Chương 1 (Bạn tiệm tiện lợi, Giáo viên chủ nhiệm, Tiền bối trầm lặng...) nhưng không có tin nhắn / phòng chat biến mất (`image copy.png` & `image copy 2.png`)](#412-lỗi-mở-khóa-người-theo-dõi-ở-chương-1-bạn-tiệm-tiện-lợi-giáo-viên-chủ-nhiệm-tiền-bối-trầm-lặng-nhưng-không-có-tin-nhắn--phòng-chat-biến-mất-image-copypng--image-copy-2png)
   - [4.13. Lỗi mất hướng dẫn (Tutorial) của Moa tại CH3: Trường cấp 3 Sunshine khi mở khóa Moa lần đầu](#413-lỗi-mất-hướng-dẫn-tutorial-của-moa-tại-ch3-trường-cấp-3-sunshine-khi-mở-khóa-moa-lần-đầu)
   - [4.14. Kiểm tra đĩa nhạc (Music Discs) và tỉ lệ nhận Quà tặng biểu diễn (Encore Gift Drop Rates)](#414-kiểm-tra-đĩa-nhạc-music-discs-và-tỉ-lệ-nhận-quà-tặng-biểu-diễn-encore-gift-drop-rates)
   - [4.15. Lỗi hiển thị nút "Mua" màu hồng kèm chữ "Không thể mua" ở Bản Sonata của Mozart (Song 12)](#415-lỗi-hiển-thị-nút-mua-màu-hồng-kèm-chữ-không-thể-mua-ở-bản-sonata-của-mozart-song-12)
   - [4.16. Lỗi không nhận được tin nhắn hoặc chỉ có 2 người theo dõi gửi tin nhắn khi mở khóa toàn bộ 15 người theo dõi ở Chapter 1 và đồng bộ tin nhắn Chapter 2](#416-lỗi-không-nhận-được-tin-nhắn-hoặc-chỉ-có-2-người-theo-dõi-gửi-tin-nhắn-khi-mở-khóa-toàn-bộ-15-người-theo-dõi-ở-chapter-1-và-đồng-bộ-tin-nhắn-chapter-2)
   - [4.17. Quy đổi số tim thành đơn vị chuẩn trong game tránh lỗi tràn số nguyên uint64 (BigNumber Conversion)](#417-quy-đổi-số-tim-thành-đơn-vị-chuẩn-trong-game-tránh-lỗi-tràn-số-nguyên-uint64-bignumber-conversion)
   - [4.18. Hệ thống Hòm thư (Mailbox): Tài khoản mới không nhận thư hệ thống cũ và chuẩn hóa đa ngôn ngữ](#418-hệ-thống-hòm-thư-mailbox-tài-khoản-mới-không-nhận-thư-hệ-thống-cũ-và-chuẩn-hóa-đa-ngôn-ngữ)
   - [4.19. Ràng buộc cấu hình Admin: Chặn chỉnh Thẻ sao khi chưa bật & Đồng bộ sự kiện 1 năm (Anniversary)](#419-ràng-buộc-cấu-hình-admin-chặn-chỉnh-thẻ-sao-khi-chưa-bật--đồng-bộ-sự-kiện-1-năm-anniversary)
   - [4.20. Đồng bộ hóa mã định danh: Chuyển đổi USN Google Play sang UID chuẩn máy chủ (`u_seq`)](#420-đồng-bộ-hóa-mã-định-danh-chuyển-đổi-usn-google-play-sang-uid-chuẩn-máy-chủ-u_seq)
   - [4.21. Lỗi không thể mua Live Slot trong Cửa hàng Vật phẩm Thẻ Sao (Pass Goods Sale Live Slot Unable to Buy)](#421-lỗi-không-thể-mua-live-slot-trong-cửa-hàng-vật-phẩm-thẻ-sao-pass-goods-sale-live-slot-unable-to-buy)
5. [Quy trình Build, Cài đặt và Kiểm tra chuẩn](#5-quy-trình-build-cài-đặt-và-kiểm-tra-chuẩn)
   - [5.1. Build APK không Google Play](#51-build-apk-không-google-play)
   - [5.2. Cài đặt lên thiết bị Android qua ADB](#52-cài-đặt-lên-thiết-bị-android-qua-adb)
   - [5.3. Khởi chạy Server Giả lập](#53-khởi-chạy-server-giả-lập)

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

### 4.9. Lỗi Sự kiện Kỷ niệm 1 năm (1st Anniversary Event) tự động mở trong game dù trên Web Dashboard không bật
- **Hiện tượng**:
  - Dù trên Web Dashboard Admin không bật Sự kiện kỷ niệm 1 năm (Event 2 - `1st Anniversary Event`), hoặc người quản trị đã tắt, nhưng khi người chơi vào game, sự kiện 1 năm vẫn tự động mở, hiển thị popup nhận thưởng 14 ngày và biểu tượng ngoài sảnh chính.
- **Nguyên nhân chi tiết (Reverse-Engineering qua ARM64 Disassembly & Cấu trúc Dữ liệu)**:
  1. **Cơ chế kiểm tra `IsOpen()` của Client bỏ qua ngày kết thúc**:
     - Trong `libil2cpp.so` tại RVA `0x225590c` (phương thức kiểm tra sự kiện mở `IsOpen()`):
       - Đối với sự kiện loại 3 (`DailyReward_PeriodCheck_First` / Event 2):
       - Client gọi `UserDailyReward.Get(2)`. Nếu người chơi đã từng có dữ liệu điểm danh sự kiện 2, hoặc có slot quà chưa nhận (`x20 != null`), tại offset `0x22559cc`, lệnh `cbnz x20, #0x2255a6c` **rẽ nhánh trực tiếp đến lệnh trả về 1 (True - Luôn Mở)!**
       - Client hoàn toàn **bỏ qua** cờ `b_IsActive` và bỏ qua ngày kết thúc `end_date`!
  2. **Handler `gamedata.py` vẫn gửi sự kiện bị tắt xuống Client**:
     - Handler `build_filtered_ret()` trong `gamedata.py` trước đây vẫn gửi toàn bộ các sự kiện điểm danh trong `ret['event_list']` (chỉ gán `b_IsActive: 0`, `start_date: 2020`, `end_date: 2020`).
     - Do game vẫn thấy Event 2 nằm trong bảng `event_list` nạp vào `EventManager`, kết hợp với nhánh `0x22559cc` bỏ qua ngày hết hạn, game lập tức coi sự kiện là đang diễn ra và mở giao diện lên.
  3. **Biến chứng do Unit Test làm thay đổi file cấu hình trên đĩa**:
     - Kịch bản test `test_event_manager.py` trước đây sử dụng `dict(self.original_config)` (shallow copy), làm thay đổi ngầm `self.original_config` khi gán `post_data['attendance_events']['2']['enabled'] = True`. Sau khi test chạy xong, `tearDown()` đã lưu đè giá trị `enabled: True` của Event 2 vào file cấu hình trên đĩa `event_config.json`.
- **Cách khắc phục triệt để**:
  1. **Lọc sạch `event_list` trong [gamedata.py](file:///root/project/GGServer/emulator/server/handlers/gamedata.py)**:
     - Nếu sự kiện điểm danh đang bị tắt (`not is_attendance_event_enabled(eidx)`), **loại bỏ hoàn toàn khỏi `ret['event_list']`** (dùng `continue`), không gửi xuống client.
     - Khi client không nhận được định nghĩa Event 2 trong `event_list`, `EventManager.Get(2)` trả về `null`, client tuyệt đối không bao giờ mở hay kích hoạt sự kiện 1 năm.
  2. **Đồng bộ hóa kiểm tra Server trong [reward.py](file:///root/project/GGServer/emulator/server/handlers/reward.py) và [app.py](file:///root/project/GGServer/emulator/server/app.py)**:
     - `getEventRewardList` bỏ qua hoàn toàn các sự kiện chưa được bật.
     - API lưu cấu hình người chơi `/admin/api/user/event_settings` chặn không cho ghi đè dữ liệu điểm danh của sự kiện đang bị tắt trên máy chủ.
  3. **Làm sạch cấu hình & Khắc phục test**:
     - Cập nhật `event_config.json` đặt Event 2 về `enabled: false`, `state: ended`.
     - Sử dụng `copy.deepcopy` trong `test_event_manager.py` và khôi phục cấu hình ngay sau bài test.
     - Dọn dẹp dữ liệu điểm danh rác Event 2 trong cơ sở dữ liệu người dùng (`database.db`).

---

### 4.10. Khóa điều khiển Thẻ Sao (Star Pass / Star Card) trong Admin khi máy chủ chưa kích hoạt Thẻ Sao
- **Hiện tượng**:
  - Trong Web Admin Dashboard (modal Cài đặt cá nhân người chơi), admin vẫn có thể bật Thẻ Sao Gold (`is_gold`) và chỉnh Điểm Thẻ Sao (`star_point`) ngay cả khi Thẻ Sao (Star Pass) toàn server đang bị TẮT trong tab Sự Kiện.
  - Việc cấp thẻ sao hoặc cộng điểm khi mùa giải chưa mở khiến dữ liệu client bị xung đột, không thể tính toán mốc quà hoặc gây lỗi logic trong game.
- **Cách khắc phục triệt để**:
  1. **Khóa giao diện Web Admin ([admin.py](file:///root/project/GGServer/emulator/server/admin.py))**:
     - Trong modal người chơi, kiểm tra `currentConfig?.star_pass?.enabled`. Nếu Thẻ Sao đang tắt:
       - Vô hiệu hóa checkbox `modal-is-gold` (`disabled = true`, `checked = false`).
       - Vô hiệu hóa ô nhập `modal-star-point` (`disabled = true`).
       - Giảm độ mờ (`opacity: 0.45`) và vô hiệu hóa tương tác click (`pointer-events: none`).
       - Hiển thị banner cảnh báo màu đỏ: *"⚠️ Thẻ Sao (Star Pass) hiện đang TẮT trong Cài Đặt Sự Kiện. Không thể chỉnh vé Thẻ Sao Gold hoặc Điểm Thẻ Sao cho người chơi (cần kích hoạt Thẻ Sao trong tab Sự Kiện trước để tránh lỗi dữ liệu game)."*
     - Trong bảng danh sách người chơi (Players Table): Cột Thẻ Sao hiển thị nhãn `Thẻ Sao (Đang Tắt)` và badge `⚪ Đang tắt` thay vì hiển thị mùa giải đang hoạt động.
     - Trong tùy chỉnh điểm danh sự kiện: Hiển thị nhãn cảnh báo đỏ nếu sự kiện được chọn đang tắt trên máy chủ.
  2. **Bảo vệ Backend API ([app.py](file:///root/project/GGServer/emulator/server/app.py))**:
     - Trong handler `/admin/api/user/event_settings`:
       - Thêm điều kiện kiểm tra `sp_enabled = event_manager.is_star_pass_enabled()`.
       - Nếu `sp_enabled` là `False`, bỏ qua hoàn toàn việc chỉnh sửa `is_gold`, `star_point`, không cập nhật `user_shop`, `user_subscribe_list`, `user_ticketcollection` hay `user_event_point` cho Thẻ Sao.

---

### 4.11. Lỗi sự kiện Nhiệm vụ người theo dõi Joy (`FollowerQuest` - #ỦnghộGuitarGirl) không nhận được quà dù đã đạt đủ điều kiện (`image.png`)
- **Dump dữ liệu sự kiện (Table 26 & Table 13)**:
  - Sự kiện trong hình ảnh là **Nhiệm vụ người theo dõi (Follower Quest)**, định nghĩa tại Bảng 26 (`followerquest`).
  - **Điều kiện mở khóa**: Người theo dõi 1 (Joy) đạt Cấp độ 250 (`i_UnlockFollowerLevel: 250`, `b_IsActive: 1`).
  - Chuỗi nhiệm vụ gồm 3 yêu cầu con:
    1. `SubID: 1` (`BigHeartTouchCount: 5`) -> Nhóm quà `500101`: 3.000 Lượt thích (`Type: 1, ID: 4, Value: 3000`).
    2. `SubID: 2` (`SkillUseCount: 1`) -> Nhóm quà `500102`: 10 Bánh quy / Cookie AP (`Type: 1, ID: 11, Value: 10`).
    3. `SubID: 3` (`AchievementPopupTime: 3`) -> Nhóm quà `500103`: 10 Socola / CP (`Type: 1, ID: 1, Value: 10`).
- **Nguyên nhân lỗi bấm nút "Nhận" (Claim) không phản hồi**:
  - Khi hoàn thành điều kiện, client gửi Thrift RPC `user.setUserFollowerQuest(i_CurrentID, i_SubID, d_ConditionValue)`.
  - Trong implementation cũ của [follower.py](file:///root/project/GGServer/emulator/server/handlers/follower.py), handler luôn trả về `i_RewardReceived1/2/3 = 0`, `next_flg = 0`, và mảng `reward_data: []` rỗng, đồng thời không hề cấp phát tiền tệ (Lượt thích, CP, Cookie) vào tài khoản người chơi.
  - Tại RVA `0x1E2E394` trong `libil2cpp.so` (`GgUIFollowerQuestManagerSGT.OnRecv(setUserFollowerQuest)`), client kiểm tra `reward_data.Count > 0` và cờ trạng thái. Do server trả về dữ liệu rỗng, client coi như thất bại, tiếp tục giữ nguyên nút "Nhận" thay vì chuyển sang trạng thái "Đã nhận" (Received), khiến người chơi không thể lấy thưởng và không thể hoàn thành sự kiện.
- **Cách khắc phục triệt để trên Server**:
  1. Trong [follower.py](file:///root/project/GGServer/emulator/server/handlers/follower.py), nạp Table 26 (`followerquest`) và Table 13 (`reward_group`).
  2. Xác định chính xác nhóm phần thưởng theo `i_SubID` (`13` cho Sub 1, `14` cho Sub 2, `15` cho Sub 3).
  3. Cấp phát đúng tiền tệ tương ứng cho người chơi thông qua `_grant_follower_quest_reward` (Socola `u_cp`, Kẹo `u_candy`, Lượt thích `u_like`, Fans `u_fans`, Bánh quy `state.add_ap`, hoặc Vé sưu tập `user_ticketcollection`).
  4. Cập nhật `i_RewardReceived{sub_id} = 1`. Khi cả 3 nhiệm vụ con hoàn thành (`r1 == 1 and r2 == 1 and r3 == 1`), gán `next_flg = 1` và `i_CompleteID = cur_id`.
  5. Đưa `user_follower_quest` vào danh sách `_user_contents` trong [auth.py](file:///root/project/GGServer/emulator/server/handlers/auth.py) và lưu bền vững qua `userSave`.

---

### 4.12. Lỗi mở khóa người theo dõi ở Chương 1 (Bạn tiệm tiện lợi, Giáo viên chủ nhiệm, Tiền bối trầm lặng...) nhưng không có tin nhắn / phòng chat biến mất (`image copy.png` & `image copy 2.png`)
- **Hiện tượng**:
  - Khi người chơi đạt cấp độ mở khóa các người theo dõi Chương 1 (ID 2: Bạn tiệm tiện lợi, ID 3: Giáo viên chủ nhiệm, ID 4: Tiền bối trầm lặng...), trong ứng dụng Messenger trong game không xuất hiện phòng chat hoặc danh sách tin nhắn bị trống trơn.
- **Nguyên nhân chi tiết từ ARM64 Disassembly (`0x1F7B8C0` - `GgUIInGameMessengerManager_Chatting`)**:
  - Khi duyệt danh sách phòng chat trong `user_messenger`, client gọi hàm kiểm tra tiến trình `GetProceedingIndex(roomId)`.
  - Tại RVA `0x1F7BBE0`:
    - Nếu `roomId != 1`:
      - Nếu `GetProceedingIndex(roomId) < 0`: client gọi tiếp `GetLastCompleteProgressGroup(roomId)`.
      - Nếu `GetLastCompleteProgressGroup < 1`, lệnh `b.lt #0x1f7bd88` **bỏ qua hoàn toàn và ẩn giấu phòng chat khỏi giao diện Messenger!**
  - Trước đây trong `follower.py` và `state.py`, các phòng chat CH1 được khởi tạo với `i_LastConfirmIndex: -1` (với suy đoán là người chơi chưa đọc tin nào). Giá trị `-1` này khiến `GetProceedingIndex` trả về `-1`, và do nhóm tiến trình ban đầu chưa hoàn thành (`< 1`), client đã ẩn phòng chat đi hoàn toàn!
- **Cách khắc phục triệt để**:
  1. Trong [follower.py](file:///root/project/GGServer/emulator/server/handlers/follower.py) và [state.py](file:///root/project/GGServer/emulator/server/state.py), khởi tạo `i_LastConfirmIndex: 0` cho toàn bộ các người theo dõi được mở khóa (cả CH1 lẫn CH2).
  2. Bổ sung vòng lặp an toàn trong `_sync_follower_messenger`: tự động chuẩn hóa mọi phòng chat có `i_LastConfirmIndex < 0` về `0`.
  3. Khi `i_LastConfirmIndex: 0`, `GetProceedingIndex` trả về `0 >= 0`, client hiển thị ngay lập tức phòng chat trong danh sách Messenger kèm tin nhắn đầu tiên và huy hiệu chấm đỏ thông báo tin nhắn mới.

---

### 4.13. Lỗi mất hướng dẫn (Tutorial) của Moa tại CH3: Trường cấp 3 Sunshine khi mở khóa Moa lần đầu
- **Hiện tượng**:
  - Khi một tài khoản lần đầu mở khóa người theo dõi Moa ở Chương 3 (Sunshine High School), game không kích hoạt kịch bản hướng dẫn tân thủ (Tutorial) của Moa mà nhảy thẳng vào màn hình thường.
- **Nguyên nhân chi tiết từ ARM64 Disassembly (`0x1CF4080` & `0x1CF41C0` - `GgUIInGame1ManagerSGT.CheckUnlockChThird`)**:
  - Chuỗi hướng dẫn Chương 3 của game diễn ra tuần tự:
    - *Area 3 Tutorial* (Tutorial ID 43, 44) -> *Area 4 Tutorial* (Tutorial ID 45..55) -> *Stage 1001 Play* -> *Area 5 Tutorial* (Tutorial ID 56..59).
  - Tại `0x1CF4080`, phương thức kiểm tra `CheckUnlockChThird` đếm số lượng màn chơi trong danh sách `user_chthird_stage.Count`.
  - Nếu `Count > 0`, client thiết lập cờ `[x20, #0x89] = 1`, coi như người chơi **đã hoàn thành giai đoạn giới thiệu Chapter 3 từ trước**, và bỏ qua vĩnh viễn toàn bộ chuỗi hướng dẫn của Moa!
  - Trên server cũ (`auth.py`, `state.py`, `ch_third.py`), các tài khoản mới bị gán sẵn màn 1001 hoàn thành: `[{'i_id': 1001, 'i_ChapterId': 1, 'i_StageIndex': 1, 'i_Star': 3}]`. Do đó `Count = 1 > 0`, làm client lập tức tắt chuỗi hướng dẫn của Moa.
- **Cách khắc phục triệt để**:
  1. Trong [state.py](file:///root/project/GGServer/emulator/server/state.py) và [auth.py](file:///root/project/GGServer/emulator/server/handlers/auth.py), mặc định `user_ch_third_stage` và `user_chthird_stage` là mảng rỗng `[]` cho tài khoản mới chưa chơi Chapter 3.
  2. Trong [ch_third.py](file:///root/project/GGServer/emulator/server/handlers/ch_third.py), cả `h_get_ch_third` và `h_ch_third_stage` đều giữ nguyên mảng rỗng `[]` nếu người chơi chưa bắt đầu chơi.
  3. Khi người chơi lần đầu bước vào CH3, client thấy mảng `user_chthird_stage` rỗng (`Count == 0`), kích hoạt trọn vẹn kịch bản hướng dẫn sinh động của Moa.
  4. Khi người chơi hoàn thành màn chơi hướng dẫn 1001, logic `is_tutorial = (stage_id == 1001)` trong `h_ch_third_stage` tự động cấp 3 sao và lưu màn 1001 vào hồ sơ người chơi.

---

### 4.14. Kiểm tra đĩa nhạc (Music Discs) và tỉ lệ nhận Quà tặng biểu diễn (Encore Gift Drop Rates)
- **1. Danh mục Đĩa nhạc (Music Discs)**:
  - Bảng 2 trong `game_data.json` định nghĩa toàn bộ **50 bản nhạc**:
    - **26 bài hát Khu vực 1** (ID 1 đến 26): bắt đầu từ bài *Cô gái với những giấc mơ* (ID 1 - *Girl with Dreams*).
    - **24 bài hát Khu vực 2** (ID 201 đến 224): bắt đầu từ bài *Hơi thở mùa xuân* (ID 201 - *Spring Breeze*).
  - Tài khoản mới tạo được cấp sẵn 2 bài hát khởi đầu: Bài 1 và Bài 201 trong `user_music`.
  - Toàn bộ 48 bài hát còn lại được mở khóa và nâng cấp chuẩn xác thông qua thăng cấp người theo dõi, đạt mốc danh tiếng hoặc mua trong Cửa hàng qua API `buyMusic` ([shop.py](file:///root/project/GGServer/emulator/server/handlers/shop.py)).
- **2. Tỉ lệ nhận Quà tặng biểu diễn tiếp (Encore Gift / Biểu diễn encore)**:
  - **Tỉ lệ xuất hiện Encore**: Khi người chơi kết thúc bài hát, client tính toán tỉ lệ xuất hiện Quà tặng Biểu diễn tiếp dựa trên Bảng 11 cột 2 (`f_EncoreBonusAppearRate`):
    - Cấp 1: 10% cơ hội xuất hiện.
    - Tăng dần theo cấp độ bài hát (+5% mỗi cấp): Cấp 2 (15%), Cấp 3 (20%), Cấp 4 (25%), Cấp 5 (30%)... đến Cấp 10 đạt 100% cơ hội xuất hiện.
  - **Phần thưởng Encore ([music.py](file:///root/project/GGServer/emulator/server/handlers/music.py))**:
    - Khi bấm nhận thưởng quà encore (`getMusicReward`), server cấp phát:
      - 10 Kẹo cơ bản (`_i_EncoreBonusGiftAmount` - Table 11 Col 6).
      - Thưởng Kẹo cộng thêm từ cấp độ Người theo dõi phụ trách encore (`i_AddCandy` - Table 31).
      - 50 EXP hồ sơ người theo dõi (`_i_EncoreFollowerProfileExp` - Table 11 Col 7).
      - 10 Điểm Thẻ Sao (Star Pass Point).
  - **Khắc phục tỉ lệ rơi Quà tặng người theo dõi ở Chapter 3 ([ch_third.py](file:///root/project/GGServer/emulator/server/handlers/ch_third.py))**:
    - Trong chế độ Tour Chapter 3, mỗi màn chơi liên kết với các nhóm quà trong Bảng 36 (`percent`).
    - Trước đây `_stage_rewards` luôn chọn cố định phần tử đầu tiên của mỗi nhóm (deterministic selection), dẫn đến:
      - Nhóm có tỉ lệ rơi 50% (1 rớt, 1 không rớt) bị biến thành 100% luôn rớt.
      - Nhóm có số lượng quà ngẫu nhiên từ 1 đến 4 luôn chỉ rơi đúng 1 cái (0% cơ hội nhận 2, 3, 4).
    - Đã cập nhật thuật toán lấy mẫu ngẫu nhiên có trọng số (`random.choices(candidates, weights=weights)`). Nhờ đó, tỉ lệ rơi quà tặng biểu diễn tại Chapter 3 hoàn toàn trùng khớp 100% với tỉ lệ gốc của nhà phát triển Neowiz.

---

### 4.15. Lỗi hiển thị nút "Mua" màu hồng kèm chữ "Không thể mua" ở Bản Sonata của Mozart (Song 12)
- **Hiện tượng**: Trong danh mục Âm nhạc (Music), Bản Sonata của Mozart (ID 12) hiển thị nút "Mua" màu hồng có dòng phụ "Không thể mua" thay vì hiển thị nút khóa xám "🔒 Không thể mua" như các vật phẩm sự kiện không bán trong cửa hàng (ví dụ Trang phục 10 - Đồng phục thủy thủ).
- **Nguyên nhân**:
  1. Trong cấu hình gốc của Neowiz tại Bảng 2 (`music`), bài hát 12 có `s_GoodsType: 'Package'`, `i_AcquisitionType: 2` (Shop), `i_AcquisitionId: 5`.
  2. Trong mã nguồn IL2CPP (`GgUIMusicItemController.SetData`), khi `s_GoodsType == 'Package'` và `i_AcquisitionType == 2`, client Unity sẽ bật `m_buttonUnlock_Shop_Enable` (nút bấm mua hàng màu hồng). Tuy nhiên do không có gói Package nào khớp với ID 5 nên client điền chuỗi "Không thể mua" vào nút.
  3. Đối với các vật phẩm không bán trong Shop như Costume 10 (*Đồng phục thủy thủ*), client quy định `s_GoodsType: 'NotForSale'`, `i_AcquisitionType: 1` (Event) và `i_AcquisitionId: 1290049` (chuỗi ID bản địa hóa "Không thể mua"). Khi đó client kích hoạt `m_textUnlockRequirement` với biểu tượng ổ khóa màu xám và ẩn nút "Mua" màu hồng.
- **Cách khắc phục**:
  - Cập nhật cả [game_data.json](file:///root/project/GGServer/emulator/gamedata/game_data.json) và mã hóa lại [getGameDataList.b64](file:///root/project/GGServer/emulator/gamedata/getGameDataList.b64) cho dòng Song 12:
    - `s_GoodsType`: `'NotForSale'`
    - `i_AcquisitionType`: `1`
    - `i_AcquisitionId`: `1290049`
  - Client nhận dữ liệu mới sẽ hiển thị nút xám có ổ khóa **`🔒 Không thể mua`** hoàn toàn chuẩn mực và đồng bộ với giao diện của Trang phục.

---

### 4.16. Lỗi không nhận được tin nhắn hoặc chỉ có 2 người theo dõi gửi tin nhắn khi mở khóa toàn bộ 15 người theo dõi ở Chapter 1 và đồng bộ tin nhắn Chapter 2
- **Hiện tượng**:
  1. Khi người chơi mở khóa toàn bộ 15 người theo dõi ở Chapter 1 (Phòng Guitar Girl), danh sách Messenger chỉ có tối đa 2 người theo dõi (hoặc 4 người) gửi tin nhắn (Phòng 4 - Tiền bối trầm lặng và Phòng 10 - Mèo quản gia).
  2. Toàn bộ các người theo dõi còn lại (Bạn tiệm tiện lợi, Giáo viên chủ nhiệm, Moa, Amber, Elle, Yeri, Sua, Jae, Huấn luyện viên...) không hề gửi tin nhắn, hoặc phòng chat bị biến mất, hoặc hội thoại khởi đầu bị bỏ qua.
  3. Ở Chapter 2 (Tiệm bánh hạnh phúc), tin nhắn của các người theo dõi mới (Reading Fox, Ruby, Alex, Busking TV, Sora, Jessica) và người theo dõi chuyển tiếp (Joy 201, Moa 202) không kích hoạt chuẩn xác.

- **Phân tích Reverse-Engineering Client IL2CPP (`libil2cpp.so`)**:
  1. **Cơ chế khởi tạo nhóm tiến trình (`GgMessengerManagerSGT.Initialize` - RVA `0x1DA1A10`, file offset `0x1D9DA10`)**:
     - Client phân tách chuỗi `s_UnlockGroupList` theo dấu phẩy `,`.
     - Tất cả các nhóm nằm phía trước (từ phần tử `0` đến `n-2`) được thêm vào danh sách nhóm đã hoàn thành `CompleteProgressGroupList`.
     - **PHẦN TỬ CUỐI CÙNG (`index - 1`) của `s_UnlockGroupList` được gán trực tiếp làm nhóm đang tiến hành (`m_proceedingGroup` tại offset `0x1da12b8`)!**
     - Client đặt chỉ số tin nhắn hiện tại: `m_proceedingIndex = min(group.max_messages, i_LastConfirmIndex)` (`0x1da0e30`).
     - Tiếp theo, hàm `DoNextProgressAll()` tăng `m_proceedingIndex` thêm 1 nếu còn tin nhắn chưa đọc.
  2. **Điều kiện hiển thị phòng chat và tin nhắn (`0x1F7B6C8` & `0x2235634`)**:
     - Với mỗi phòng trong `user_messenger`, client gọi `GetProceedingGroup(roomId)` và `GetProceedingIndex(roomId)`.
     - Nếu `GetProceedingIndex(roomId) >= 0`, client tải tin nhắn `GetMessage(group, index)`.
     - Trong `GgUIInGameMessengerChattingItemController.SetData` (`0x2235DB8`), phòng chat **chỉ hiển thị nếu `item._message != null` hoặc `item.IsOnUserInput == true`**. Nếu không, client gọi `gameObject.SetActive(false)` và ẩn hoàn toàn phòng chat khỏi giao diện!
     - Huy hiệu thông báo đỏ được kích hoạt khi số tin chưa đọc `unread = GetProceedingIndex(roomId) - i_LastConfirmIndex > 0`.
  3. **Nguyên nhân cốt lõi khiến chỉ có 2 người theo dõi gửi tin nhắn**:
     - Trước đây, máy chủ cố gắng giải quyết điều kiện tiên quyết bằng cách gộp chuỗi nhóm phụ thuộc vào từng phòng mà không chỉ định nhóm tiến hành đích (`target_proceeding`), dẫn đến việc nối các nhóm cốt truyện cấp cao vào cuối danh sách:
       - Phòng 2 nhận `[2, 5, 11, 77]` $\to$ Nhóm 77 (yêu cầu Bạn Tiệm Tiện Lợi Lv 1100) bị đặt ở cuối và trở thành `m_proceedingGroup`! Nhóm 2 khởi đầu bị đánh dấu hoàn thành mà người chơi chưa đọc. Vì người chơi chưa đạt Lv 1100 nên Nhóm 77 không có tin nhắn hợp lệ $\to$ Phòng 2 không gửi tin nhắn.
       - Phòng 3 nhận `[6, 31, 44]` $\to$ Nhóm 44 (yêu cầu Cấp 650) thành nhóm tiến hành $\to$ bị kẹt.
       - Phòng 5 nhận `[13, ..., 55]` $\to$ Nhóm 55 (yêu cầu Cấp 625) thành nhóm tiến hành $\to$ bị kẹt.
       - Phòng 6 nhận `[18, ..., 43]` $\to$ Nhóm 43 (yêu cầu Cấp 250) thành nhóm tiến hành $\to$ bị kẹt.
       - Phòng 7 nhận `[20, ..., 58]` $\to$ Nhóm 58 (yêu cầu Cấp 375) thành nhóm tiến hành $\to$ bị kẹt.
       - Phòng 1 nhận `[1, ..., 75]` $\to$ Nhóm 75 (yêu cầu Joy Lv 1250) thành nhóm tiến hành $\to$ toàn bộ đoạn chat tân thủ của Joy bị nhảy cóc.
       - Các người theo dõi cấp cao (11, 12, 13, 14, 15) yêu cầu các nhóm điều kiện ở Phòng 7, Phòng 16, Phòng 1 phải nằm trong `CompleteProgressGroupList`, nhưng vì các nhóm này đang bị kẹt làm nhóm tiến hành ở cuối chuỗi nên điều kiện bị chặn hoàn toàn!
       - **Chỉ có Phòng 4 (Nhóm 9) và Phòng 10 (Nhóm 54)** không bị gán nhóm cấp cao ở cuối nên giữ nguyên được nhóm khởi đầu $\to$ Đúng như người dùng phản ánh: *"khi mở full 15 người theo dõi chỉ có 2 người theo dõi là gửi tin nhắn"*.

- **Cách khắc phục triệt để**:
  1. **Bảo đảm vị trí nhóm tiến hành với `target_proceeding` ([follower.py](file:///root/project/GGServer/emulator/server/handlers/follower.py))**:
     - Nâng cấp thuật toán `_merge_groups_seq(existing_str, new_groups, target_proceeding=...)`:
       - Tách biệt rõ ràng: toàn bộ các nhóm điều kiện tiên quyết được xếp vào phía trước (được thêm vào `CompleteProgressGroupList` của client).
       - Nhóm hội thoại ban đầu của người theo dõi (`target_proceeding`) luôn luôn được đặt ở **vị trí cuối cùng** (index `-1`), bảo đảm client nạp chính xác làm `m_proceedingGroup`.
  2. **Bản đồ hội thoại chuẩn xác cho Chapter 1 (15 người theo dõi + Phòng đặc biệt)**:
     - Follower 1 (Joy): Phòng 1 $\to$ Nhóm 1 (`target_proceeding=1`). Các nhóm tiên quyết `[4, 7, 10, 12, 15, 16, 24, 30, 32, 33, 35, 36, 41, 45, 47, 56, 57, 75]` đứng trước.
     - Follower 2 (Bạn tiệm tiện lợi): Phòng 2 $\to$ Nhóm 2.
     - Follower 3 (Giáo viên chủ nhiệm): Phòng 3 $\to$ Nhóm 6.
     - Follower 4 (Tiền bối trầm lặng): Phòng 4 $\to$ Nhóm 9.
     - Follower 5 (Moa): Phòng 5 $\to$ Nhóm 13.
     - Follower 6 (Elle): Phòng 6 $\to$ Nhóm 18.
     - Follower 7 (Amber): Phòng 7 $\to$ Nhóm 20 (kèm nhóm điều kiện `53, 58` hoàn thành ở phía trước).
     - Follower 8 (Yeri): Phòng 8 $\to$ Nhóm 51.
     - Follower 9 (Sua): Phòng 9 $\to$ Nhóm 62.
     - Follower 10 (Mèo quản gia): Phòng 10 $\to$ Nhóm 54.
     - Follower 11 (Jae): Phòng 11 $\to$ Nhóm 74.
     - Follower 12 (Tiệm bánh hạnh phúc): Phòng 12 $\to$ Nhóm 80.
     - Follower 13 (Nova): Phòng 13 $\to$ Nhóm 88.
     - Follower 14 (Mocha Latte): Phòng 14 $\to$ Nhóm 90.
     - Follower 15 (Huấn luyện viên thể dục): Phòng 15 $\to$ Nhóm 91.
     - Phòng 16 (Chat nhóm Joy & Moa CH1): Nhóm 81 (`'76,78,79,81'`).
  3. **Đồng bộ hóa toàn diện cho Chapter 2 (Tiệm bánh hạnh phúc)**:
     - Follower 201 (Joy CH2): Phòng 1 $\to$ Nhóm 111 (`'1,75,111'`).
     - Follower 202 (Moa CH2): Phòng 5 $\to$ Nhóm 110 (`'13,110'`).
     - Follower 203 (Reading Fox): Phòng 203 $\to$ Nhóm 114.
     - Follower 204 (Ruby): Phòng 204 $\to$ Nhóm 127.
     - Follower 205 (Alex): Phòng 205 $\to$ Nhóm 138.
     - Follower 206 (Busking TV): Phòng 206 $\to$ Nhóm 178.
     - Follower 207 (Sora): Phòng 207 $\to$ Nhóm 181.
     - Follower 208 (Jessica): Phòng 208 $\to$ Nhóm 186.
     - Phòng 12 (Cầu nối CH2): Nhóm 103 (`'80,103'`).
     - Phòng 16 (Cốt truyện CH2 Joy & Moa): Nhóm 104 (`'76,78,79,81,82,...,104'`).
     - Phòng 17 (Chat nhóm 4 người): Nhóm 139 (`'...,173,139'`).
  4. **Cơ chế tự sửa lỗi dữ liệu cũ (Auto-healing `CORRUPT_CH1_HEAL`)**:
     - Tự động nhận diện các tài khoản đã bị lưu chuỗi nhóm lỗi trong `database.db` (như Phòng 2 kết thúc bằng 77, Phòng 3 kết thúc bằng 44, Phòng 5 kết thúc bằng 55, Phòng 6 kết thúc bằng 43, Phòng 7 kết thúc bằng 58).
     - Khi người chơi đăng nhập hoặc đồng bộ dữ liệu, server tự động khôi phục chuỗi nhóm sạch chuẩn mực, đặt `i_LastConfirmIndex = 0` để kích hoạt thông báo tin nhắn mới tức thì.
  5. **Kết quả**:
     - Toàn bộ **15/15 người theo dõi Chapter 1** và **tất cả người theo dõi Chapter 2** đều gửi tin nhắn chào mừng, hiển thị phòng chat đầy đủ cùng huy hiệu thông báo tin nhắn chưa đọc màu đỏ, hoạt động hoàn hảo và mượt mà.

---

### 4.17. Quy đổi số tim thành đơn vị chuẩn trong game tránh lỗi tràn số nguyên uint64 (BigNumber Conversion)
- **Hiện tượng**: Khi số Tim hoặc Lượt thích tích lũy quá lớn vượt quá giới hạn 64-bit uint64 (`18,446,744,073,709,551,615`), hệ thống server và client có thể bị crash, tràn số âm hoặc hiển thị chuỗi số mũ khoa học (`3.487e+22`) gây lỗi hiển thị trong game.
- **Nguyên nhân**: Game Guitar Girl sử dụng ký hiệu đơn vị lớn dạng Alphabet notation (A, B, C... G, H... AA, AB... CX...) với hệ số cơ số mũ `10^3` (ví dụ `1A = 1,000`, `1B = 1,000,000`, `1C = 1,000,000,000`, v.v.).
- **Cách khắc phục**:
  - Chuẩn hóa module chuyển đổi số lớn hai chiều trên server và Web Admin Dashboard.
  - Hỗ trợ nhập và quy đổi linh hoạt mọi đơn vị game: ví dụ nhập `42.877G`, `100H`, `10AA` tự động parse chính xác sang cơ số 10 và format ngược lại hiển thị trực quan.
  - Thêm cơ chế kẹp giá trị an toàn (clamp) và định dạng chuẩn chuỗi Alphabet notation, loại bỏ hoàn toàn nguy cơ tràn số nguyên uint64.

---

### 4.18. Hệ thống Hòm thư (Mailbox): Tài khoản mới không nhận thư hệ thống cũ và chuẩn hóa đa ngôn ngữ
- **Hiện tượng**:
  1. Người chơi tạo tài khoản mới tinh sau khi vào game thì bị nhận hàng loạt thư thông báo và quà sự kiện đã phát sóng từ nhiều tháng trước trong quá khứ.
  2. Các trường ngôn ngữ trong [broadcast_posts.json](file:///root/project/GGServer/emulator/broadcast_posts.json) (`title_ko`, `title_en`, `title_jp`...) đều bị copy nguyên bản tiếng Việt, khiến người chơi chọn ngôn ngữ khác (Tiếng Anh, Tiếng Nhật, Tiếng Hàn...) vẫn bị hiển thị tiếng Việt.
- **Cách khắc phục**:
  - **Lọc thư cho tài khoản mới**: Thêm thuộc tính `applies_to_new_users: false` cho toàn bộ các thư phát sóng sự kiện lịch sử trong [broadcast_posts.json](file:///root/project/GGServer/emulator/broadcast_posts.json). Khi người dùng đăng nhập hoặc nhận thư, server đối chiếu `create_time` của thư với thời điểm tạo tài khoản; chỉ các thư phát hành sau khi tạo nick mới được gửi vào hòm thư.
  - **Chuẩn hóa đa ngôn ngữ**: Khai thác dữ liệu bản địa hóa chính thức từ Bảng 22 trong `game_data.json` để dịch toàn bộ tiêu đề và nội dung thư phát sóng sang đủ **12 ngôn ngữ** (`ko`, `en`, `jp`, `zh_chs`, `zh_cht`, `vi`, `es`, `it`, `id`, `th`, `pt`, `hi`). Cập nhật `send_post` trong [post.py](file:///root/project/GGServer/emulator/server/handlers/post.py) hỗ trợ truyền dictionary đa ngôn ngữ tự động.

---

### 4.19. Ràng buộc cấu hình Admin: Chặn chỉnh Thẻ sao khi chưa bật & Đồng bộ sự kiện 1 năm (Anniversary)
- **Hiện tượng**:
  1. Khi tính năng Thẻ Sao (Star Pass) chưa bật trên Web Admin, quản trị viên vẫn có thể mở modal người chơi và tích chọn Thẻ Sao Gold hoặc nâng điểm Star Pass, gây lỗi bất đồng bộ dữ liệu game.
  2. Sự kiện Kỷ niệm 1 năm (1st Anniversary) tự động hiển thị trong game dù toggle trên Web Admin đang tắt.
- **Cách khắc phục**:
  - Trong Web Admin Dashboard, thêm cơ chế kiểm tra `currentConfig.star_pass.enabled`. Nếu Star Pass đang tắt, modal quản lý người chơi sẽ tự động ẩn các trường chỉnh sửa Star Pass và hiển thị cảnh báo hướng dẫn bật Star Pass trước.
  - Đồng bộ chặt chẽ danh sách sự kiện đăng nhập trong `build_filtered_ret` ([gamedata.py](file:///root/project/GGServer/emulator/server/handlers/gamedata.py)) và `getEventRewardList` ([event_reward.py](file:///root/project/GGServer/emulator/server/handlers/event_reward.py)) theo đúng trạng thái bật/tắt của từng sự kiện (bao gồm Kỷ niệm 1 năm - Event 2).


---

### 4.20. Đồng bộ hóa mã định danh: Chuyển đổi USN Google Play sang UID chuẩn máy chủ (`u_seq`)
- **Hiện tượng**:
  1. Trong menu Cài đặt và hộp thoại báo lỗi của game hiển thị định danh theo dạng `USN: 452465183(PlayGame)` hoặc `USN: 429071553(PmangPlus)`.
  2. Ngược lại, máy chủ và Web Admin Dashboard lại quản lý người chơi theo `u_seq` (`100001`), `u_id` (`guest_100001`) và `device_uuid`.
  3. Khi người chơi cần hỗ trợ hoặc sao chép USN gửi cho Admin, số USN trên máy không khớp với số ID trên bảng quản trị, gây khó khăn cho việc tra cứu tài khoản.
- **Nguyên nhân chi tiết (Reverse-Engineering qua Unity IL2CPP & PmangPlus SDK)**:
  1. Trong mã nguồn IL2CPP (`GgUtil.GetUSN` tại RVA `0x1CF8B30`), game đọc trường `ppMemberId` từ `PPMembershipManager` (lớp singleton quản lý phiên đăng nhập PmangPlus).
  2. Trước đây máy chủ giả lập trong [auth.py](file:///root/project/GGServer/emulator/server/auth.py) trả về giá trị `_MEMBER_ID = 429071553` cố định cho mọi request đăng nhập `/accounts/v3/global/login`.
  3. Định dạng chuỗi hiển thị trong `global-metadata.dat` được biên dịch sẵn là `USN: {0}({1})`.
- **Cách khắc phục triệt để (Phương án Kết hợp toàn diện)**:
  1. **Đồng bộ hóa tức thì từ Máy chủ ([auth.py](file:///root/project/GGServer/emulator/server/auth.py))**:
     - Trong handler `/accounts/v3/global/login`, trích xuất `device_cd` từ form yêu cầu của client.
     - Sử dụng `state.create_user(device_cd, device_cd)` để tra cứu (hoặc cấp phát) số thứ tự tài khoản chính xác của thiết bị (`u_seq`, ví dụ `100001`).
     - Gán `member_id = u_seq` và nạp vào cấu trúc JSON trả về (`member.member_id = 100001`).
     - Kết quả: Toàn bộ các bản APK (kể cả bản cũ đang cài đặt) tự động nhận `100001` làm USN; nút "Sao chép USN" trong game copy chính xác chuỗi `100001` khớp 100% với Web Admin.
  2. **Vá giao diện APK từ USN sang UID ([patch_metadata.py](file:///root/project/GGServer/patcher/patch_metadata.py))**:
     - Bổ sung quy tắc vá `CUSTOM_LITERALS`:
       - Chuỗi `USN: {0}({1})` (13 ký tự) được ghi đè in-place thành `UID: {0}({1})` (13 ký tự).
       - Chuỗi nhãn `USN` (3 ký tự) được ghi đè in-place thành `UID` (3 ký tự).
     - Cập nhật chuỗi thông báo sao chép trong bảng dữ liệu hệ thống Bảng 16 ([game_data.json](file:///root/project/GGServer/emulator/gamedata/game_data.json) & [getGameDataList.b64](file:///root/project/GGServer/emulator/gamedata/getGameDataList.b64)) sang `[b][UID][/b] đã được sao chép vào clipboard`.
  3. **Nâng cấp Web Admin Dashboard ([admin.py](file:///root/project/GGServer/emulator/server/admin.py))**:
     - Hiển thị badge nổi bật **`UID: #100001`** ngay cạnh tên người chơi trong bảng danh sách và trong modal cài đặt cá nhân.
     - Thanh tìm kiếm hỗ trợ tra cứu tức thì theo bất kỳ thông tin nào (`u_seq`, `guest_100001`, `nickname`, hoặc `device_uuid`).

---

### 4.21. Lỗi không thể mua Live Slot trong Cửa hàng Vật phẩm Thẻ Sao (Pass Goods Sale Live Slot Unable to Buy)
- **Hiện tượng**:
  1. Trong Cửa hàng Vật phẩm Thẻ Sao (Pass Goods Sale / Merch Shop, UI 19 `GgUIIngamePassGoodsShop`), ô **Live Slot** (`GgUIIngamePassGoodsLiveSlot` - ô sự kiện nổi bật trên cùng hiển thị Mùa Thẻ Sao đang diễn ra) hiển thị trạng thái "Đã đăng ký" hoặc "Không thể mua" (`Common_Error_UnableBuy` / "Không thể mua thêm.") đối với các tài khoản người chơi chưa từng mua Thẻ Sao / Gói quà Merch Pack mùa này.
  2. Khi người chơi bấm vào ô Live Slot, game không mở popup chi tiết gói vật phẩm (`GgUIIngamePassGoodsDetail`, Popup 20), hoặc nếu mở được thì khi bấm "Mua" sẽ bị lỗi không thể hoàn tất.
- **Nguyên nhân chi tiết (Reverse-Engineering qua Unity IL2CPP ARM64 `libil2cpp.so`)**:
  1. **Hàm tra cứu Subscription của Client bỏ qua trạng thái kích hoạt**:
     - Trong mã máy ARM64 tại RVA `0x20C81E4` (offset file `0x20C41E4` của `libil2cpp.so` - hàm `UserSubscribeList.GetSubscribe(int subscribeId)`):
       ```arm64
       0x20c42ac: bl #0x1b25c04         // ObscuredInt -> int
       0x20c42b0: cmp w0, w19           // item.SubscribeID == targetId
       0x20c42b4: b.ne #0x20c428c
       0x20c42b8: mov x0, x20           // return item!
       ```
       Client duyệt mảng `user_subscribe_list` và so sánh mã `SubscribeID`. Trình xử lý của client **hoàn toàn không kiểm tra cờ `i_isActive`**! Bất kỳ bản ghi nào tồn tại trong `user_subscribe_list` (kể cả khi mang giá trị `i_isActive = 0`), hàm này đều trả về đối tượng khác `null`.
  2. **Khóa luồng hiển thị và bấm nút Mua của Live Slot**:
     - Tại `SubscribePassManager.Init` (RVA `0x1DE798C`), client gán `m_cLiveData.field_0x40 = UserSubscribeList.GetSubscribe(activeSeason)`.
     - Tại `GgUIIngamePassGoodsLiveSlot.Refresh` (RVA `0x1FE2DE0`), client gọi `GetIsSubscribedCurrentPass()`. Do `field_0x40 != null`, hàm trả về `1` (True):
       - Live Slot ẩn nút "Mua" (`m_goBuy`) và kích hoạt nhãn "Đã đăng ký" (`m_goSubscribed`).
     - Tại `GgUIIngamePassGoodsShop.OnClickLiveSlot` (RVA `0x20D7FE0`), client kiểm tra:
       ```arm64
       0x20d3ffc: bl #0x1de5b64         // GetIsSubscribedCurrentPass()
       0x20d4000: cbz w0, #0x20d4010   // Nếu == 0 mới mở Popup 20!
       0x20d4004: mov x0, x20          // Nếu != 0: gọi Refresh() và return luôn!
       0x20d4008: bl #0x1fdeddc
       0x20d400c: b #0x20d4044
       ```
       Do client nghĩ người chơi đã đăng ký thẻ mùa này, nó thoát ngay lập tức mà không mở popup chi tiết gói vật phẩm.
  3. **Khóa giao dịch tại trình quản lý mua sắm**:
     - Tại `GgPurchaseManagerSGT.GetIsPurchaseAvailable` (RVA `0x21D1C14`), client gọi `UserSubscribeList.GetSubscribe(SubscribeID)`. Do tìm thấy bản ghi, hàm trả về `0` (Unavailable), kích hoạt popup lỗi `Common_Error_UnableBuy` (chuỗi 10068 trong Bảng 16: "Không thể mua thêm.").
  4. **Lỗi logic máy chủ khi khởi tạo và chuẩn hóa danh sách Subscription**:
     - Trước đây trong `auth.py` (hàm `_normalise_subscribe_list`), khi người chơi chưa mua thẻ hoặc chưa kích hoạt thẻ Gold (`not (paid_enabled or season_bought)`), server thực hiện:
       ```python
       else:
           if paid_sub:
               paid_sub['i_isActive'] = 0
               paid_sub['i_ActiveTime'] = 0
       ```
       Server giữ lại phần tử `paid_sub` trong mảng `user_subscribe_list` với `i_isActive = 0`. Tương tự, khi quản trị viên thu hồi Thẻ Sao Gold trong `app.py`, server cũng chỉ gán `i_isActive = 0` chứ không xóa khỏi mảng. Vì client bỏ qua `i_isActive`, người chơi chưa mua thẻ vẫn bị client coi là đã mua.
- **Cách khắc phục triệt để**:
  1. **Lọc sạch hoàn toàn các Subscription không hoạt động ([auth.py](file:///root/project/GGServer/emulator/server/handlers/auth.py))**:
     - Trong hàm `_normalise_subscribe_list`, loại bỏ triệt để các phần tử không có trạng thái hoạt động thực sự. Chỉ duy trì các mục có `i_isActive == 1` do người chơi thực sự mua trong `user_shop` hoặc do quản trị viên cấp quyền `paid_star_card`.
     - Tuyệt đối không trả về bất kỳ bản ghi nào có `i_isActive == 0` về cho client trong `user_subscribe_list`.
  2. **Thu hồi sạch sẽ khi tắt Thẻ Sao Gold ([app.py](file:///root/project/GGServer/emulator/server/app.py))**:
     - Khi quản trị viên hủy kích hoạt Thẻ Sao Gold cho người chơi trên Web Admin Dashboard, `user['user_subscribe_list']` lọc bỏ hoàn toàn các ID thuộc mùa bị thu hồi thay vì đổi cờ `i_isActive = 0`.
  3. **Chuẩn hóa luồng mua gói vật phẩm Merch Pack ([shop.py](file:///root/project/GGServer/emulator/server/handlers/shop.py))**:
     - Khi mua gói Live Slot Merch Pack (`3000 + season_num`, ví dụ 3003) hoặc gói thường (`2000 + season_num`, ví dụ 2003):
       - Kiểm tra tính hợp lệ qua `_check_purchase_eligibility` (cho phép mua nếu chưa sở hữu gói trong `user_shop`).
       - Trừ đúng số CP theo giá chiết khấu trong Bảng 12 (ví dụ Mùa 3 là 50 CP).
       - Trao đầy đủ phần thưởng nhóm quà Merch Pack (Guitars, Costumes, Music, Star Pass).
       - Thêm cả `season_num` và `1000 + season_num` vào `user_subscribe_list` (với `i_isActive: 1`) và `user_ticketcollection`.
       - Ghi nhận cả hai mã gói `2000 + season_num` và `3000 + season_num` vào `user_shop` để ngăn chặn mua lặp lại.
  4. **Xác minh qua Bộ kiểm thử tự động ([test_live_slot_purchase.py](file:///root/project/GGServer/emulator/test_live_slot_purchase.py))**:
     - Tạo bộ kiểm thử độc lập bao quát toàn bộ 6 kịch bản thực tế:
       - Kiểm tra tài khoản mới có `user_subscribe_list` rỗng, Live Slot hiển thị sẵn sàng mua.
       - Kiểm tra cơ chế tự động dọn sạch subscription rác/inactive khi đăng nhập.
       - Kiểm tra RPC `buyCheck` và `buyShop` cho gói Live Slot 3003 thành công, trừ đúng 50 CP và cấp đủ 9 vật phẩm thưởng.
       - Kiểm tra từ chối mua lặp lại đối với cả gói giảm giá 3003 lẫn gói thường 2003.
       - Kiểm tra quy trình thu hồi Thẻ Sao Gold dọn sạch danh sách subscription.
       - Kiểm tra tính toàn vẹn cấu trúc dữ liệu Bảng 29, Bảng 17 và Bảng 12.

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

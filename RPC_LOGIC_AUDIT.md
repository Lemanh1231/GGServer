# Rà RPC và logic — source hiện tại, không phải production

## Phạm vi và kết luận

Đã đối chiếu toàn bộ **134 wire RPC / 129 tên đơn** trong schema với đăng ký
runtime `GameContext`, DTO request/return và đường fallback. Có **65 wire route
dùng handler / 61 tên đơn**, còn **69 route / 68 tên đơn dùng legacy fallback**.
Mọi route có Return DTO; thử encode/decode envelope rỗng không lỗi. Điều này
không chứng minh payload gameplay hoặc native UI của từng route hoạt động đúng.

Rà logic account/save/profile, economy/shop/reward/Pass/ad, social/follower/mail,
content/event và routing/session/codec. Không báo lại các lỗi CH3, Encore,
attendance UTC+7, Pass/shop/price, catalog hoặc guest identity đã sửa. Full-suite
sau patch dùng để kiểm regression, không tính lỗi lịch sử thành phát hiện mới.

**Bốn phát hiện mới** bên dưới có reproduction bằng tài khoản/DB giả trên
SQLite và Mongo-memory. Có kiểm qua HTTP localhost với `sessions.required=true`,
token server cấp, codec request/return native. Không có thao tác tài khoản thật.
Đã sửa source cho bốn phát hiện và chuyển characterization thành regression
hành vi mong muốn. **Chưa deploy hoặc push**; kết quả full-suite cũ không được
dùng làm bằng chứng cho patch mới.

## Phát hiện mới — đã sửa source và qua regression, chưa deploy

### RPC-01 — Request thiếu/hỏng body vẫn chạy handler ghi dữ liệu (ưu tiên cao)

- `server/GameServer.java:149–150,178–193`: thiếu message giữ `request=null`;
  decode lỗi đổi thành `_decode_error`, nhưng không trả lỗi trước khi dispatch.
- Session hợp lệ vẫn được chấp nhận khi payload không có claim; context cung cấp
  canonical account cho handler. Đây không phải bypass token hay truy cập account khác.
- Tái hiện HTTP `user.updateNickName` không có native message, hoặc message hỏng:
  trả code0 và ghi nickname thành `Guitarist` thay vì từ chối, trên cả hai backend.
- Rủi ro: request hỏng/transport lỗi gây mutation mặc định. Không suy rộng thành
  mua hàng mất tiền: phép thử `buyShop` hỏng bị chặn bởi invalid default ID.
- Hướng sửa: chặn body thiếu/decode lỗi trước handler ở biên transport; xác định
  ngoại lệ bootstrap/no-body thực sự cần thiết; không đổi semantics optional
  identity claim của request hợp lệ và không trả success trước save.
- Patch: code400 cho protected RPC thiếu message/data hoặc decode lỗi; bootstrap
  không-body hợp lệ vẫn giữ. Kiểm session trước khi dispatch như cũ.
  `Dispatch.findMessageField` không chọn call/access_token/session_token làm
  message fallback; vẫn nhận message ở legacy field khác nếu có. Có test HTTP
  bootstrap không-body với SDK token cũ, tránh regression do sniff nhầm form.

### RPC-02 — Cookie ad bỏ qua cờ active thật của catalog (ưu tiên cao)

- `game/economy/EconomyModule.java:824–846` không kiểm `b_IsActive` của row2.
- Schema bảng32: **cột20 là `b_IsActive`; cột2 là `i_Category`, không phải active**.
- Tái hiện catalog giả giữ nguyên mọi giá/reward, chỉ đổi row2/cột20=0 trước
  startup: `user.setAdReward(i_id=2)` vẫn code0, trả reward và lưu thêm25 AP.
- Cờ id1 hiện cũng kiểm cột2; chưa tái hiện đường profile-ad trong lượt này nên
  không tính thêm một lỗi độc lập.
- Hướng sửa: đọc field active đúng từ catalog, fail closed trước grant; kiểm lại
  cả profile/cookie ad. Không sửa số AP, không thay catalog live để che lỗi.
- Patch: cả id1/id2 kiểm cột20, thiếu/inactive definition bị từ chối trước grant.

### RPC-03 — Cookie ad retry bỏ qua cooldown 300 giây (ưu tiên cao)

- `EconomyModule.java:843–846`: biểu thức `id == 2 || ...` luôn bỏ cooldown
  cho cookie. Daily limit5 vẫn tồn tại, nên không phải grant vô hạn trong ngày.
- Catalog row2 điều kiện1 `DAY_LIMIT=5`, điều kiện2 `COOLTIME=300`.
- Hai HTTP request hợp lệ liên tiếp dưới300giây đều trả reward, AP tăng50,
  count tăng2 trên SQLite/Mongo. Giữ nguyên catalog, không giả clock của server.
- Test lịch sử `EconomyModuleTest` đang chấp nhận5 lượt liên tiếp; phải xử lý
  xung đột semantics này khi sửa, không âm thầm đổi test để tuyên bố tương thích.
- Chưa có trace Android chứng minh UI có gửi retry nhanh; lỗi server enforcement
  đã tái hiện, không khẳng định mọi lần xem ad trên UI đang bị lỗi.
- Hướng sửa: diễn giải đúng hai condition có tên từ catalog, kiểm ngày UTC+7,
  cooldown duration bằng epoch không cộng7giờ; test trước/đúng boundary, restart,
  future last-view, retry đồng thời và save-failure rollback.
- Patch: đọc hai condition theo tên thay vì vị trí/hardcode; loại bypass id2.
  Test lịch sử năm grant liên tiếp đã đổi rõ ràng thành năm grant cách300giây;
  mỗi retry ngay lập tức không nhận thêm quà. Reward vẫn25AP.

### RPC-04 — Xem profile đích lại trả profile người gửi (ưu tiên vừa)

- Request `user.getProfileDataInfo.get_u_seq` là I64, tách khỏi identity người gửi.
- `game/player/ProfilePackets.java:23,55–57` luôn dùng `packet.identity()`, bỏ target.
- Hai account giả nickname khác nhau: người A gửi `get_u_seq=B`; DTO decoded còn
  nguyên UID B nhưng response trả nickname A, kể cả qua HTTP có session A.
- Đây là đọc sai đối tượng public profile, không phải lỗ hổng đổi identity session.
- Hướng sửa: dùng target UID chỉ cho read public projection, không dùng nó thay
  identity của update; quy định rõ target thiếu/không tồn tại. Không tự thay raw
  nickname/avatar/title legacy vốn có test tương thích riêng.
- Patch: thiếu target/0 giữ self profile; UID đích không tồn tại trả lỗi.
  Đọc snapshot đã lưu, chỉ project public fields, không khóa chéo tài khoản;
  update nickname/avatar/title vẫn theo identity requester.

## Nghi vấn bị loại / không tính là lỗi mới

- **Daily mission stale tier**: direct Map có thể gửi `i_Level`, nhưng native
  `user.saveUserDailyMission` chỉ có `i_id,d_Quantity`. Codec loại field tier;
  claim rồi native userSave vẫn giữ level2 trên SQLite/Mongo. Không có wire exploit
  hạ tier như nghi vấn ban đầu. Counter quantity là client-authoritative hiện có.
- **CH3 stage/ticket trong userSave**: có direct-handler keys, không có trong
  native `userSaveDataInfo`; không báo exploit dựa trên payload không hợp schema.
- **Skill/unit acquisition gate**: không tính là phát hiện mới vì `BUG.md` đã ghi.
  Theo scope fix BUG.md, đã bổ sung `UpgradeAccess` theo level/prerequisite/active
  catalog cho first acquisition; skill projection dùng chung gate thay hardcode.
  Không revoke skill đã kiếm được, giữ level/timer và semantics giá/upgrade cũ.
  Kết quả đối chiếu mục lịch sử ở `BUG_DISPOSITION.md`; tài liệu BUG.md cũ đã
  xóa theo yêu cầu. Các việc xác minh/deploy còn mở vẫn ghi trong `CURRENT_ISSUES.md`.
- **Legacy profile updates**: không suy ra ownership/avatar/title rules mới khi
  test hiện có chủ động giữ raw legacy values.
- **Pass paid reward semantics / offline progress counters**: không tự áp mô hình
  real-money hoặc server-authoritative khác với config/test đã xác nhận.
- **Event ranking**: handler chủ động trả unsupported; fallback rank/music/store
  legacy là thiếu triển khai/contract, không phải bằng chứng gian lận gameplay.

## Namespace và giới hạn coverage

Registry chỉ đăng ký tên đơn. Năm cặp trùng tên:

| Tên | Wire namespace |
| --- | --- |
| buyCheck | store / user |
| buyVarietyStore | store / user |
| getPostTime | post / tour |
| playMusic | user / tour |
| storeList | main / store |

`Dispatch.resolveSimple` chọn match đầu schema, không dựa URL namespace;
GameServer dispatch handler bằng tên đơn cả khi form dùng full name.
Đặc biệt `user.playMusic` và `tour.playMusic` có return contract khác nhau;
handler hiện là legacy stub. Chưa có native call-site/trace để quy kết thành
lỗi gameplay đang xảy ra. Cần test/thiết kế namespace-aware trước khi triển khai
những route này; không viết lại toàn bộ routing trong lượt audit.

**Không phải 134/134 route đã được end-to-end gameplay test.** Inventory đủ,
phân loại handler/fallback đủ; test sâu mới tập trung những nghi vấn mới, còn
các invariant đã sửa được đối chiếu test/source lịch sử. Các route schema-only
cần native contract để xác nhận functionality, không có cơ sở tuyên bố sạch lỗi.

## Evidence và cách chạy

- `src/test/java/emu/leman/ggserver/server/RpcLogicAuditTest.java`: đã thay các
  assertion reproduction thành regression và bổ sung catalog boundary/no-charge,
  preservation, concurrent retry và reciprocal profile reads trên hai backend.
- `EconomyModuleTest`: thêm boundary299/300giây, clock lùi, midnightVN, reopen và
  save-failure rollback trên SQLite. Mongo-memory không thay thế failover thật.
- Build/test output riêng `/tmp/opencode/rpc-logic-audit-build`, không chạm live JAR.
- Lệnh focused: `./gradlew -I /tmp/opencode/rpc-logic-audit.init.gradle test --tests '*RpcLogicAuditTest' --console=plain`.
- Lệnh full cuối (working directory `/tmp/opencode/rpc-fixes-validation`):
  `./gradlew -I /tmp/opencode/rpc-fixes-validation.init.gradle test fatJar --console=plain`.
  Init script đặt build directory ngoại vi và JVMtimezoneUTC; không dùng output
  `GGServerJava/build` đang chứa JAR production.
- Inventory máy đọc `/tmp/opencode/rpc-logic-inventory.json` ghi từng wire route,
  owner, request DTO, Return DTO, Return data DTO và bootstrap. Danh mục dễ đọc
  lưu tại `RPC_INVENTORY.md`; test có thể xuất lại JSON bằng system property
  `rpc.audit.inventory`.
- Log reproduction cũ `/tmp/opencode/rpc-logic-audit-final.log`. Backend Mongo dùng memory,
  không chứng minh replication/failover/CAS thực tế trên production.
- Full suite388/388 là kết quả identity fix **trước audit này**, không tính thêm
  thành full-suite mới. Validation patch được ghi riêng sau khi hoàn tất.
- Focused patch cuối: **42/42 qua, 0 failure/error/skip**:23RPCaudit trên
  SQLite/Mongo-memory,17economy,2catalog prerequisite. Log
  `/tmp/opencode/rpc-fixes-boundaries.log`. Kết quả full-suite cuối ghi riêng bên dưới.
- Candidate ngoại vi `/tmp/opencode/rpc-fixes-validated-build/libs/ggserver-1.0.0-all.jar`;
  SHA256 cuối `90c15a78d2532c2e810e8165f8b3b34604a79c424de6af1af9404b2ec33fd2a8`.
  Tất cả application class giống local compile; không có DB/APK/keystore/config
  runtime/capture trong JAR. Evidence `/tmp/opencode/rpc-fixes-artifact-audit.json`.
  JAR production hash vẫn `6e9e150212e5d0f5b13817ea5b1022a0bae2d3ca792731829daee085f87237ab`.
  Cây sanitized giữ HTML/config/resource sạch từ lượt validation trước; không
  đưa thay đổi dashboard local không liên quan vào candidate. Candidate chứa cả
  fix lịch sử chưa deploy và identity optimization, không phải hotfixRPC đơn lẻ.
  So với identity candidate trước đó8class thêm/đổi (gồm nested generated class):
  AuthContent,UpgradeAccess,EconomyModule,ProfileManager,ProfilePackets$GetProfile,
  GameServer,Dispatch,Dispatch$Envelope; không xóa application class.
- Full-suite sanitized lượt đầu418test còn1lỗi fixture: cây lọc không có
  `resources/server-config.json` mà ResourcesLayoutTest yêu cầu. Đã tạo config
  SQLite/localhost giả trong cây ngoại vi để chạy lại; không copy config private,
  không đổi test để skip và không sửa config nguồn/live.
- Sau bổ sung fixture config giả:full418/418qua,test/fatJar thành công (trước
  Dispatchfix cuối). Regression bootstrap cuối35/35qua (12transport+23RPCaudit),
  log `/tmp/opencode/rpc-fixes-bootstrap.log`.
- **Full-suite cuối419/419qua,0failure/error/skip,53suite, JVMUTC**; `test fatJar`
  thành công trên source/bytecode candidate90c15a78. Log
  `/tmp/opencode/rpc-fixes-final-validated.log`, summary
  `/tmp/opencode/rpc-fixes-final-test-summary.json`. Source Java local/cây lọc
  giống nhau, catalog/schema/weights giống nhau; config kiểm thử là synthetic.
  Đây là source regression, không chứng nhận AndroidUI, Mongo failover hay live.
- Validation riêng cây publication ngày16/11/2026: **419/419qua,53suite,
  0failure/error/skip,JVMUTC**, `test fatJar` thành công. Cây này dùng
  `ResourcesLayoutTest` đọc config example sạch, không cần runtime config private.
  Log `/tmp/opencode/java-publish-rpc-final.log`, summary
  `/tmp/opencode/java-publish-rpc-test-summary.json`. JAR publication khớp chính
  xác SHA256 candidate90c15a78 ở trên;104application class giống nhau.
  Năm synthetic native guard test cũng qua. Không deploy/rebuildAPK/sửa playerDB.

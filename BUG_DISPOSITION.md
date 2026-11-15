# Đối chiếu BUG.md với Java hiện tại

Ngày: 16/11/2026. Đây là kết quả đối chiếu tài liệu cũ, **không phải chứng nhận production/Android đã hết lỗi**.
Không áp lại hướng dẫn Python/APK, reset account hoặc bù thưởng vào production.
Đã xóa `BUG.md` theo yêu cầu mới. Không lưu bản sao của tài liệu cũ;
các giới hạn xác minh còn áp dụng tiếp tục được theo dõi trong `CURRENT_ISSUES.md`.

| Mục cũ | Đối chiếu / xử lý hiện tại |
| --- | --- |
| 1.1–1.7 | Lịch sử patch APK/DEX, EULA, chữ ký và cài split. Java không thể xác minh ART/cài đặt/UI Android; không rebuild APK trong lượt này. |
| 1.8 | Notification từng được hủy; CP breakdown phụ thuộc native UI. Không tự khôi phục công việc đã hủy. |
| 1.9 | Hook UI Live Slot/giá/refresh thuộc APK. Server sale gate/giá đã có fix riêng; không coi đó là chứng minh hook Android đúng. |
| 2.1 | `GameServer.authPath` nhận cả `/accounts`, `/app`, `/referrer`, `/gcm`, `/eula` và `/api`; Nginx live vẫn cần kiểm cấu hình riêng. |
| 2.2 | Login/identity đã có regression SessionAccess/GuestLogin/Transport. Không sửa account thật để né lỗi đăng nhập; source mới chưa deploy. |
| 3.1 | Quy trình reset/cleanup lịch sử, không phải lệnh cần chạy. Không xóa DB, token hoặc tài khoản. |
| 3.2 | Ban được kiểm ở transport/repository; giữ test hiện có. Chưa xác minh firewall/proxy live. |
| 4.1 | Attendance đã tách login khỏi board claim, có duplicate/future receipt/UTC+7 tests. Không áp hướng dẫn cũ tự grant từ `setAttendance(add)`. |
| 4.2 | Seed Java mặc định 0; legacy migration đã có test. Không chạy reset số dư người chơi. |
| 4.3 | Storage snapshot không sửa response in-place; bổ sung kiểm native buyContents trả item sau save. |
| 4.4 | Đã bổ sung source gate acquisition skill/unit theo catalog, dùng chung skill projection; không xóa skill/level/timer đã kiếm được. Focused boundary/prerequisite/no-charge tests qua; source chưa deploy. |
| 4.5 | Reward/entitlement Pass theo catalog và cấu hình đã có test. Không áp lại Free-only mâu thuẫn với chính sách Gold hiện tại. |
| 4.6, 4.17, 4.22 | Currency/BigNumber và offline authority đã có `CurrencyTest`, `OfflineCurrencyAuditTest`, admin tests; không đổi hệ số đơn vị theo mô tả lịch sử mâu thuẫn. |
| 4.7, 4.18 | Mailbox cutoff theo creation time, persistence và locale đã có `MailboxPersistenceTest`/`SocialModuleTest`; không xóa thư account thật. |
| 4.8, 4.12, 4.16, 4.27 | Giữ Messenger progress, story gates/DAG; không ép complete mọi group. Có account/social/follower regressions; chưa có trace native cho mọi phòng chat. |
| 4.9, 4.19 | EventManager/projection lọc anniversary theo switch, không dựa lịch capture cũ. Source tests không chứng nhận icon/cache APK live. |
| 4.10 | Admin/event validation đã có; không đổi quyền bật thẻ hay secret production. |
| 4.11 | Follower quest và claim đã có `FollowerAuditReproductionTest`/`GeneralAuditRegressionTest`; không cấp bù thủ công. |
| 4.13 | CH3 tutorial/progress có `ContentChapterRegressionTest`; chưa xác nhận UI Android hiện tại. |
| 4.14 | Encore/drop/music đã có `ChapterEncoreRegressionTest`, weights catalog; không sửa xác suất hoặc thưởng. |
| 4.15 | AcquisitionRules phân biệt offline music purchase/CP/real-money; giữ contract đã kiểm, không mở mọi bài bằng bypass. |
| 4.20 | Canonical UID/session/device đã có các regression identity; không rewrite UID DB hoặc USN native. |
| 4.21 | Sale entitlement/gate/giá có `StarPassPurchaseRegressionTest`/`StarPassShopRulesTest`; source chưa deploy, APK popup chưa xác minh. |
| 4.23 | `AdminAuth` có HMAC/password; kiểm secret/TLS/throttle/proxy là việc triển khai còn mở. Không đưa private config vào báo cáo. |
| 4.24 | Launcher/giám sát là vận hành; chưa rõ nguyên nhân tiến trình cũ biến mất. Không restart/deploy trong lượt này. |
| 4.25 | IP persistence/transport đã có; độ tin cậy forwarded headers phụ thuộc proxy, vẫn là rủi ro cần xác minh. |
| 4.26 | Java mặc định bind loopback, xử lý CONNECT ở biên HTTP; isolation origin/firewall và bot rate limit chưa được xác minh. |
| 4.28 | Lịch sử xác nhận lỗi bản dịch, không có bằng chứng thiếu hệ số thưởng. Không tính lại/cấp bù/reset achievement; source localization đã sửa, UI runtime còn giới hạn xác minh. |
| 5.1–5.3 | Hướng dẫn build/cài/chạy, không phải defect để thực thi tự động. Không dùng để suy ra quyền build APK/restart production. |

## Bổ sung từ audit RPC

- RPC-01: transport từ chối missing/decode-error trước handler; bootstrap không-body
  hợp lệ vẫn giữ (không sniff call/token thành body), session vẫn được kiểm.
  Không đổi quyền identity của request hợp lệ.
- RPC-02/03: cả hai ad dùng cột20 active, điều kiện có tên `DAY_LIMIT`/`COOLTIME`;
  giữ 25 AP, limit/cooldown catalog, epoch duration và ngày Việt Nam.
- RPC-04: đọc public projection đúng `get_u_seq`, target không tồn tại trả lỗi;
  không lấy target làm identity update, không lồng hai account stripe locks.
- Chi tiết và kết quả validation ở `RPC_LOGIC_AUDIT.md`; chưa deploy production.
- Full-suite source sanitized cuối:419/419qua,0failure/error/skip,53suite,JVMUTC;
  `test fatJar` thành công. Không coi kết quả này là chứng nhận mọi mục APK/live.

## Quy tắc giữ nguyên khi sửa gate

- Catalog skill1/21 mở100,2/22 mở300,3/23 mở500; reset4/24 mở1.
  Mô tả “level10” cũ không khớp dữ liệu hiện tại, nên không ép mọi skill về10.
- Skill absent đủ gate vẫn mua upgrade1→2 theo contract cũ; unit absent0→1;
  không thêm unlock fee hoặc đổi công thức CP/maxlevel.
- Gate chỉ áp dụng acquisition mới. Ownership/upgrade/timer đã lưu không bị xóa
  khi characterlevel thấp hoặc catalog đổi. Không migration thu hồi đồ lịch sử.
- Test prerequisite dùng catalog giả riêng; catalog thật hiện chưa có prerequisite
  nonzero trong14row skill/unit. Không sửa game data để tạo ca test.

## Kiểm phần patcher không build APK

- Reference policy host-only:17scenario qua (preserve timers/progress, chapter
  isolation, cooldown/expiry/reset/replay/overflow), lệnh chạy riêng thành công,
  log `/tmp/opencode/bug-policy-final.log`.
- Đã cài dependency đúng phiên bản vào `/tmp/opencode/bug-final-python-deps`,
  không cài hệ thống. Hai module ARM64 V2/narrow vẫn chưa thực thi được vì thiếu
  exact-base APK `Guitar_Girl_v8.0.0_Java_8181_IdentityFix.apk`; không thay bằng
  binary khác hoặc bỏ hash guard. Log `/tmp/opencode/bug-final-patcher.log`.
- Sửa `patcher/merge_apk.py`: kiểm toàn bộ site trước khi patch; input lạ/truncated
  bị từ chối thay vì âm thầm xuất bản vá thiếu; retry known patch idempotent.
  Có5ca synthetic guard, không build/sign/publish APK. Dependency test được ghim
  trong `patcher/requirements-test.txt`.
- Lượt host cuối **27/27 test qua**:5native guard,17policy,5gateway/release.
  Log `/tmp/opencode/bug-final-host-validation.log`. Hai suite exact-base ARM64
  bị chặn được ghi riêng, không tính vào27test đã qua.

## Giới hạn xác minh sau khi bỏ tài liệu cũ

- Chốt mục APK/UI bằng contract/trace hoặc kiểm thử thiết bị, không dùng Java
  tests làm bằng chứng thay thế; vẫn giữ ranh giới không sửa APK đã xác nhận.
- Kiểm proxy/origin/launcher và triển khai source theo một yêu cầu riêng có
  phê duyệt; không coi việc build candidate là production đã được sửa.
- Những chỉ dẫn reset/cleanup, Free-only, ép Messenger complete và level10 cũ
  đã được loại khỏi phương án sửa hiện tại, không phải công việc đang chờ chạy.
- Những route legacy/schema-only thiếu native contract vẫn ghi rõ giới hạn ở
  `RPC_LOGIC_AUDIT.md`, không tự triển khai chức năng hoặc đổi namespace hàng loạt.

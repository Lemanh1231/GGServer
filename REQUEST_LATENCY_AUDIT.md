# Audit request latency — 16/11/2026

## Kết luận và phạm vi

Đã kiểm đường xử lý chung HTTP/session/registry/storage và các luồng ưu tiên:
claim event 7 ngày, CH3 chơi thường, sweep x1/x5, mua Cookie product31,
preflight mua và mở CH3. **Không phải chứng nhận đã kiểm hết mọi RPC hoặc UI Android.**

Nguyên nhân chi phí chung xác nhận trong code là tải account đầy đủ nhiều lần
để kiểm alias/lấy khóa, rồi handler lại tải và lưu snapshot Mongo nhiều section.
Chưa đo riêng thời gian mạng Mongo production hoặc chờ khóa khi có nhiều người.
Không có bằng chứng sweep x5 bị chậm chủ yếu vì vòng lặp 5 lần.

Lượt audit ban đầu không sửa Java/runtime config, không deploy/push, không gọi
claim/mua trên account thật. Chỉ đọc log/capture live và dùng DB/account giả.
Không kèm identity, token, địa chỉ người chơi hoặc số dư live.

## Bằng chứng live

Log `resources/logs/latest.log` sau restart; không cộng lần hai bản sao `server.log`:

| RPC | Thời gian server RPC (ms) |
| --- | ---: |
| setEventReward, event1, status Y/error0 | 404 |
| setAttendance, hai lượt | 274 / 325 |
| userSave | 493 |
| getEventRewardList | 365 |
| getGameDataList | 693 |
| userLogin, hai lượt | 264 / 270 |

Đây là mẫu ít sau restart, không phải p50/p95. Timer bắt đầu trong `GameServer.rpc`
sau decode HTTP/request; bao gồm session, handler, encode và ghi capture đồng bộ,
nhưng không bao gồm toàn bộ decode trước đó, final send, mạng/client callback/UI.
Claim thành công không đồng nghĩa đã hết chậm. Capture lúc kiểm chưa có CH3/cookie.

## Đo cô lập trên chính JAR

- Live JAR SHA256: `6e9e150212e5d0f5b13817ea5b1022a0bae2d3ca792731829daee085f87237ab`.
- Published JAR SHA256: `b403a0fe5fdaa05bc5e01fb9092755586b68b010ffa20ca89b09efd8d564fcd3`.
- Published source: branch `java-server`, commit `2647e8672ea7d3a8d4a782c3c0f8ecee627dff7e`.
  Published không phải JAR đang phục vụ và chứa nhiều fix kết hợp, không chỉ performance.
- Catalog/schema thật, account giả có inventory theo catalog, CP giả đủ mua,
  AP70, stage1001 đã3sao, team hợp lệ. HTTP localhost đi qua codec/session thật.
- Mỗi kịch bản/binary có Mongo-memory DB và JVM riêng; 5 warmup + 10 mẫu đo.
  Gửi đủ `uuid`, `device_uuid`, `u_seq`, `u_id`; kiểm codec roundtrip giữ đủ alias.
- `session`: gọi đúng `SessionAccess.validate`; `registry`: khóa + handler;
  `HTTP`: thời gian client Java localhost toàn request. Các phase đo riêng,
  **không cộng/trừ median để suy ra chính xác thời gian phase còn lại**.
- Tất cả14 lượt isolated chạy thành công; kiểm registry claim statusY, sweep trừ
  5AP/lượt và đủ nhóm kết quả, cookie trừ100CP và tăngAP; HTTP kiểm status200/error0.
  Không coi các invariant này là so sánh toàn bộ reward/DTO trước-sau.

### Mongo-memory: p50 / p95, đơn vị ms

| Kịch bản | Live session | Live registry | Live HTTP | Published session | Published registry | Published HTTP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Claim7d event1 | 112.5 / 131.4 | 138.9 / 156.0 | 289.1 / 320.2 | 92.6 / 107.3 | 60.6 / 81.6 | 201.0 / 248.6 |
| CH3 play | 95.7 / 123.4 | 81.8 / 91.8 | 221.4 / 305.7 | 106.1 / 135.4 | 71.0 / 168.0 | 352.5 / 452.2 |
| CH3 sweep x1 | 99.4 / 109.1 | 87.7 / 98.5 | 229.6 / 275.0 | 109.5 / 138.6 | 63.9 / 83.8 | 202.4 / 232.8 |
| CH3 sweep x5 | 94.6 / 113.4 | 88.7 / 100.0 | 204.4 / 236.1 | 99.3 / 113.9 | 59.8 / 70.5 | 192.0 / 233.8 |
| Cookie buy31 | 93.1 / 109.3 | 84.8 / 102.1 | 215.9 / 259.8 | 92.3 / 104.8 | 57.7 / 65.2 | 186.0 / 223.9 |
| Cookie preflight | 72.2 / 82.0 | 38.3 / 54.2 | 140.4 / 162.8 | 79.3 / 113.1 | 19.9 / 34.2 | 137.2 / 183.7 |
| CH3 open | 98.8 / 111.9 | 82.4 / 95.4 | 213.9 / 218.6 | 99.4 / 126.5 | 62.7 / 80.4 | 199.6 / 223.8 |

Load đầy đủ p50 live khoảng18–27ms, save32–41ms; published load19–27ms,
save35–45ms. Session vẫn gần chi phí bốn lượt load. Published registry nhiều
luồng giảm chi phí lấy khóa nhưng **không giải quyết session load lặp**.
CH3 play published HTTP có mẫu chậm hơn; không bỏ mẫu này hoặc tuyên bố mọi RPC
đều nhanh hơn. Cần lặp nhiều lần/đảo thứ tự và profiling trước khi kết luận regression.

Giới hạn: 10 mẫu là nhỏ (p95 ở đây là mẫu lớn nhất); JIT/GC, scheduling,
HTTP buffering/delayed ACK, I/O capture và thứ tự chạy đều có thể ảnh hưởng.
Mongo-memory không mô phỏng đầy đủ index/query planner, disk/journaling hay mạng
của Mongo thật. Account benchmark lớn hơn một số account thực tế.

Lượt exploratory đầu chạy 8 kịch bản chung một DB (cả SQLite và Mongo-memory),
chỉ gửi2alias. Mongo-memory chậm dần theo lịch sử snapshot tích lũy; **không dùng
kết quả đó để xếp hạng các kịch bản**, suy ra chi phí x5 hoặc tốc độ production.
Lượt isolated cân bằng số vòng/lịch sử giữa kịch bản, nhưng vẫn giữ snapshot trong
từng lượt; chưa phải benchmark steady-state dài hạn.

## Các điểm cần xử lý theo ưu tiên

### 1. Session tải toàn account để kiểm từng alias — xác nhận

`src/main/java/emu/leman/ggserver/server/SessionAccess.java:52` gọi `getUser`
cho cả4alias. Request claim/attendance/save thật có đủ4trường, kể cả u_id/u_seq
cùng giá trị vẫn lookup riêng. `MongoUserRepository.getUser` reconstruct mọi
section; `MongoUserSections.read` truy vấn theo từng field trong manifest.

Hướng sửa: API identity nhẹ, giữ nguyên semantics tìm alias và kiểm mọi claim;
chỉ đọc metadata cần thiết khi xử lý provider placeholder, kiểm exact stored
device và collision như hiện tại. Không thay bằng tin session/payload một chiều,
không cache alias lâu dài hoặc bỏ check alias xung đột. Cần regression cả backend,
unknown alias, cross-account, placeholder, delete/recreate, expired session.

### 2. Load/save Mongo toàn snapshot — xác nhận

JARlive lấy canonical lock qua load đầy đủ; published đã dùng `canonicalIdentity`
ở registry. Handler vẫn load đầy đủ. `saveUser` đọc section cũ để giữ semantics
partial inventory rồi stage toàn snapshot, insert theo field, CAS publish account.
Việc giữ snapshot lịch sử làm dung lượng tăng; benchmark memory cho thấy chi phí
tăng theo lịch sử, **chưa chứng minh cùng mức suy giảm trên Mongo production**.

Hướng xử lý tiếp: đo command count và explain/index trên môi trường Mongo giống
production; nghiên cứu reuse section bất biến/đọc đúng phần cần merge, hoặc gom
query/insert theo collection. Giữ manifest count/order/type checks, snapshot
visibility, CAS retry và cleanup chỉ snapshot chưa publish. Không tự chạy GC,
migration hoặc xóa lịch sử đang được reader dùng.

### 3. Khóa dùng chung tạo hàng chờ giữa account — rủi ro từ code

`EconomyModule.bind` giữ `s.state` suốt handler, cả event board và preflight mua;
login/save, mail và một số reward khác cũng dùng monitor này. Account A đang
save chậm có thể giữ B chờ dù B là account khác. Single-client benchmark không
đo được thời gian chờ này; chưa có bằng chứng định lượng contention live.

Hướng sửa: instrument lock-wait trước, kiểm toàn bộ account/global/broadcast
lock ordering và concurrency. Không xóa monitor chỉ vì đã có account lock.

### 4. Một số thao tác đọc vẫn ghi — xác nhận

- `getChThird` normalizeAP rồi save toàn account mỗi lần mở màn hình.
- `getChThirdStarReward` cũng save khi không có reward mới.
- Attendance(add) có thể save lần1 để tăng ngày, lần2 nếu mở infinite quest.
- `buyCheck` không save reward nhưng vẫn load account đầy đủ và giữ economy monitor.
- Mua Cookie có thể gồm preflight + buy + refresh; chưa có capture thật để xác
  nhận chuỗi Android, không cộng median các request làm thời gian UI.

Hướng sửa: gom thay đổi attendance thành một lần save; chỉ save khi có mutation
thực sự ở read-like request, sau khi kiểm kỹ normalization/persistence contract.
Giữ deduction+reward+receipt atomic, không acknowledge trước save thành công.

### 5. Capture/catalog/config — cần profiling tách phase

`GameServer.capture` serialize pretty JSON và ghi file đồng bộ trước send;
catalog bootstrap còn copy/project/encode payload lớn. `GameData.varietyStore`
đọc/decode resource lúc request. `EventManager.snapshot` reload file để hot config
có hiệu lực ngay. Đây là công việc trên critical path, chưa đo phần trăm chi phí.

Ưu tiên thêm metric decode/auth/lock/load/handler/save/encode/capture/send,
không ghi identity/token. Nếu cache catalog/config phải invalidate đúng và giữ
Sale/event toggle cập nhật ngay; queue capture cần bounded/backpressure/retention,
không làm mất kiểm soát bộ nhớ hoặc che lỗi lưu gameplay.

## Kiểm logic chức năng

Chạy source đã publish với JVM UTC: **67/67 test qua**, 0failure/error/skip:
17 `ContentChapterRegressionTest`,16 `ContentModuleTest`,7 shop/event,
8 UTC/attendance,12 economy,2 Mongo sections,5 session.

Bao gồm gate stage/team/ownership, AP regeneration và cookie overflow,
sweep count/3sao/reward groups, story một lần/concurrency, claim/day boundaries,
shop eligibility và session. Đây không thay thế full-suite hoặc kiểm mọi trường
hợp failure/concurrency trên Mongo production. Không đổi AP5/lượt, count1..5,
reward weights, cooldown hay giá trong lượt audit.

Evidence cục bộ (file tạm, không cần publish log thô):

- `/tmp/opencode/RequestLogicAudit.java`
- `/tmp/opencode/request-isolated-{live,published}-<scenario>.{json,log}`
- `/tmp/opencode/request-logic-{live,published}-{sqlite,mongo}.{json,log}` (exploratory)
- `/tmp/opencode/request-logic-correctness-expanded.log`

Chưa có phase metric/live CH3/cookie hoặc client trace. Do đó kết luận hiện tại
là xác định chi phí chung và thứ tự tối ưu an toàn, không phải đã sửa hết lag.
Thay đổi source sau khi được yêu cầu tiếp tục được ghi riêng dưới đây.

## Tiếp theo: sửa identity lookup theo yêu cầu ưu tiên phần quan trọng

Đã sửa source, **chưa deploy/push**:

- Thêm `UserIdentity` và `getIdentity` ở repository/StateStore. SQLite dùng cùng
  alias resolver rồi SELECT uuid/device; Mongo dùng cùng resolver với projection
  `_id/device_uuid`. Không cache, không migration, không ghi dữ liệu lúc lookup.
- `SessionAccess` giữ nguyên từng check và thứ tự check, lỗi, skip empty/0,
  unknown-canonical fallback, touch session, bootstrap và placeholder normalization;
  thay `getUser` bằng lookup metadata. Exact-device và collision vẫn bắt buộc.
- `UserIdentity.toString()` redacted vì device là dữ liệu nhạy cảm; không log identity.
- Không thay AuthApi guest-login fix, account/global locks, Mongo section CAS,
  save atomicity, CH3 AP/RNG, price/reward hay receipt.

Giới hạn bảo mật giữ nguyên, không mở rộng cam kết: optional/blank claims và
unknown-canonical fallback có semantics cũ; không thêm account-generation/session
revocation policy cho trường hợp xóa rồi tạo lại đúng canonicalUUID. Test
reassignment ở đây bảo vệ alias cũ chuyển sang canonical khác, không khẳng định
thu hồi mọi session sau mọi dạng restore/recreate. Feature snapshot hỏng vẫn
phải bị handler/storage từ chối khi đọc gameplay; lookup identity nhẹ không
chữa hoặc bỏ qua lỗi toàn vẹn snapshot trong gameplay.

Regression mới trên cả SQLite/Mongo: đúng/sai từngalias, unknownalias,
placeholder exactdevice/collision/không mutate request khi reject, alias reassigned,
lookup read-only và tương thích resolver. Test phá feature storage trong DB giả
chứng minh gameplay getUser vẫn fail closed nhưng session không cần đọc inventory.
Trước sửa fail2ca feature-storage như dự kiến; focused sau sửa110/110qua.
Bản cuối có10ca regression mới (5case ×2backend), **388/388 full-suite qua**,
0failure/error/skip, JVM UTC; `test fatJar` thành công trên cây sạch với resources
đã lọc. Focused identity/session/guest-login bản cuối19/19qua. Bytecode toàn bộ
class ở build local và cây sạch giống nhau; chỉ6class identity/session thay đổi
so với published baseline. Benchmark bản cuối đã hoàn tất bên dưới; không coi
đây là đã hết lag live.

Candidate cuối (không chép vào production):
`/tmp/opencode/request-identity-validated-build/libs/ggserver-1.0.0-all.jar`, SHA256
`cebe6d7572f7ffebf8bea3b7bfa61f9ad021a820d122468abecee31a4b070465`.
Log `/tmp/opencode/request-identity-final-full.log`; review diff riêng
`/tmp/opencode/request-identity-source-review.diff`.

Đo phụ SQLite trên JAR local đã build (5warmup/10mẫu,4alias), claim/cookie đều
thành công: session p50 claim8.53→0.63ms, cookie7.39→0.65ms. Tuy nhiên HTTP
p50 claim29.48→57.45ms, cookie44.53→53.86ms ở lượt này; không tuyên bố cải thiện
HTTP SQLite. Chưa tách encode/capture/transport hoặc lặp kiểm nguyên nhân, nên
chỉ kết luận lookup nhẹ giảm thời gian riêng session. Không lấy tỷ lệ session
làm tỷ lệ tăng tốc toàn request/client.

### Đối chứng Mongo-memory trên JAR cuối — đã hoàn tất

Hai vòng chạy độc lập, vòng2 đảo thứ tự kịch bản và chạy after trước before;
mỗi binary/kịch bản/vòng dùng DB/JVM giả riêng,5warmup+10mẫu,đủ4alias.
**16/16 lượt thành công**, giữ các invariant claim/AP/cookie của harness.
Before là published baseline, không phải production JAR cũ. After là candidate
SHA256 ở trên. Không gộp percentile giữa hai vòng.

| Kịch bản | Session p50 trước, vòng0 / vòng1 (ms) | Session p50 sau, vòng0 / vòng1 (ms) | HTTP p50 trước, vòng0 / vòng1 (ms) | HTTP p50 sau, vòng0 / vòng1 (ms) |
| --- | ---: | ---: | ---: | ---: |
| Claim7d event1 | 86.17 / 89.84 | 2.68 / 2.97 | 178.33 / 183.61 | 84.52 / 89.39 |
| CH3 sweep x1 | 96.51 / 107.46 | 2.73 / 2.83 | 194.42 / 182.69 | 91.41 / 92.67 |
| CH3 sweep x5 | 97.90 / 96.64 | 3.16 / 2.66 | 191.39 / 185.49 | 105.30 / 92.17 |
| Cookie buy31 | 94.94 / 87.00 | 2.60 / 2.47 | 202.42 / 199.54 | 88.09 / 99.31 |

HTTP p50 giảm khoảng45–56% trong cả8cặp so sánh; session p50 còn2.47–3.16ms.
HTTP p95 từng vòng cũng thấp hơn baseline: claim215.26/213.36→114.88/105.57ms;
sweepx1 215.33/226.26→115.56/109.18ms; sweepx5 214.91/208.11→132.51/124.49ms;
cookie235.47/254.10→108.28/107.84ms. Mỗi vòng chỉ10mẫu, p95 là mẫu lớn nhất.
Đây là kết quả synthetic localhost/Mongo-memory, không phải SLA hoặc xác nhận
client hết lag; SQLite HTTP không cho kết quả cải thiện như đã ghi ở trên.

Evidence `/tmp/opencode/request-identity-final-summary.json`,
`/tmp/opencode/request-identity-final-r{0,1}-{before,after}-<scenario>.{json,log}`;
script `/tmp/opencode/request-identity-final-benchmark.py`. Hash production JAR
kiểm lại vẫn nguyên. Chưa deploy/push hoặc gọi claim/mua trên account thật.

# Các lỗi đã sửa

## Encore CH1/CH2 và receipt legacy
- **Lỗi:** Game hiện quà nhưng nhận bị từ chối, kể cả quà mới ở CH2.
- **Nguyên nhân:** Receipt legacy bằng 0 bị hiểu là lượt nhận thật; cooldown bắt đầu nhầm khi client gửi quà mới.
- **Sửa:** Chuẩn hóa trạng thái khi load/merge, phân biệt placeholder không có thời điểm kích hoạt; giữ receipts, pending hợp lệ và chống replay. Bản sửa đầu chưa bao phủ trạng thái không quà lúc login, đã bổ sung regression và xử lý tiếp.
- **Trạng thái:** Đã triển khai; suite tương ứng từng đạt 473/473, chờ xác nhận trong game. Không đưa dữ liệu tài khoản hoặc backup lên GitHub.

## Điểm danh sự kiện lựa chọn
- **Lỗi:** Ngày đầu sự kiện chọn trang phục báo Invalid attendance reward.
- **Nguyên nhân:** Ngày 1–6 có reward 0/0/0, không phải vật phẩm để validator cấp thưởng kiểm tra.
- **Sửa:** Ghi nhận ngày không vật phẩm đúng catalog; giữ kiểm tra lựa chọn ngày 7 và chống nhận lặp.
- **Trạng thái:** Đã triển khai, có regression; chưa coi test tự động là xác nhận người dùng.

## Revision danh mục và admin React
- **Lỗi:** Bật sự kiện riêng nhưng client dùng danh mục cũ; editor điểm danh/log cần kiểm tra chặt.
- **Sửa:** Revision lưu bền theo catalog/cấu hình hiệu lực và scope tài khoản; bổ sung override riêng, editor điểm danh, log live và frontend React có source/build.
- **Trạng thái:** Đã triển khai, phần UI hoàn thiện còn được theo dõi riêng trong bug.md.

## Java4Shell
- **Rủi ro:** Decode Base64 trước xác thực trên JVM có intrinsic bị ảnh hưởng.
- **Sửa vận hành:** Tắt intrinsic bằng drop-in riêng service; xác minh runtime Ubuntu 24.04 chạy bản vá 21.0.13.1+2-1~24.04.1 ngày 2026-11-20 và health đạt.
- **Phạm vi:** Repo chứa hướng dẫn và template, không tự áp dụng cấu hình lên máy khác. Không thay JAR để chữa lỗi runtime.

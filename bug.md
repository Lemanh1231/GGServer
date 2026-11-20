# Lỗi chưa hoàn tất

## Mua trang phục CH2 chậm
- **User báo:** Mua trang phục chậm.
- **Bằng chứng:** Request thành công, thời gian server quan sát khoảng 172–220 ms; chưa đủ chứng minh chờ nhiều giây do server.
- **Khoanh vùng:** BuyContents save cả khi không đổi inventory; Mongo đọc/stage nhiều sections. Chưa có profile tách thời gian queue/read/write và callback client.
- **Trạng thái:** Chưa viết lại hoặc triển khai tối ưu cho lỗi này.

## Thứ tự bài hát CH1/CH2 đổi sau khi mua
- **User báo:** Bài mới mua chuyển lên trên bài trước đó; không phải màn hình tự cuộn.
- **Nguyên nhân khoanh vùng:** Comparator client ưu tiên ownership rồi sort order; ownership đổi làm vị trí đổi.
- **Đề xuất:** Giữ thứ tự catalog ổn định, ID làm tiêu chí phụ; cần sửa/test client và giữ chữ ký APK.
- **Trạng thái:** Chưa patch hoặc build APK; không coi sửa thứ tự DTO server là khắc phục.

## Hoàn thiện admin
- **Trạng thái:** Còn kiểm thử tương tác mobile/desktop, bản dịch đầy đủ và banner download; không coi frontend đã hoàn thiện toàn bộ.

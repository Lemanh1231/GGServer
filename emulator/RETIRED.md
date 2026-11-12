# Python legacy endpoint — ngừng phục vụ gameplay

Python hiện chạy nền ở cổng **8080**, chỉ trả thông báo chuyển phiên bản:

> Đã ngắt kết nối: máy chủ Python cũ đã ngừng phục vụ.
> Vui lòng tải phiên bản mới tại website: https://kotori.click/download

```bash
python3 -u emulator/run.py --retired --host 0.0.0.0 --port 8080
```

Chỉ dùng `--retired` cho endpoint cũ. Không chạy thêm lệnh này khi tiến trình
hiện tại còn chạy. Bỏ cờ này sẽ chạy emulator gameplay cũ, không phải chế độ
thông báo. Không dùng `emulator/serverctl.sh` để stop theo port vì script cũ
không có kiểm tra ownership an toàn như launcher Java.

- Chỉ import codec/schema/dispatch và parser multipart; **không load state,
  auth hoặc gameplay handlers**, không mở SQLite, không tạo session/account.
- Giống ban user: cho phép 6 RPC bootstrap `Request`, `getServerTime`,
  `getUpdateTime`, `defaultSettingList`, `getGameDataList`, `getVarietyStore`
  cùng tài nguyên CDN chỉ đọc để UI khởi tạo trước khi báo lỗi.
- RPC userLogin/userJoin/save và gameplay: HTTP 200 với lỗi Thrift code 900,
  nội dung yêu cầu tải bản mới, **không có data tài khoản**. Giữ 200 để client
  decode lỗi thay vì chỉ báo lỗi mạng/failover. Cần test lại popup trên Android.
- SDK NeonAPI có handshake tương thích với token tạm không lưu/không đăng ký;
  không cấp session game, không mở account DB. `userLogin` vẫn luôn bị chặn.
- Admin và request không nhận dạng: HTTP 410.
- `/download` chuyển tới website Java, `/health` ghi rõ `retired`, `gameplay:false`.
- Log: `GGServerJava/resources/logs/python-retired.log`.
- PID/start-time triển khai: `GGServerJava/resources/.run/python-retired.json`.
- Test: `python3 -m unittest discover -s emulator -p test_retired_server.py`.

**Routing hiện tại:** 4 domain HTTPS tách theo header `X-GG-Client-Release`.
APK mới có giá trị `java-8181-v1` → Java 8181; APK cũ không có header đó → Python
8080 (game RPC, SDK, CDN). `/admin`, `/download`, `/health` luôn tới Java.
APK mới đã publish ở `/download/Guitar_Girl_v8.0.0_Java_8181.apk`, giữ khóa ký cũ.
Header chỉ chọn deployment, không thay thế session/authentication.

SQLite nguồn được kiểm tra giữ nguyên SHA-256 khi khởi động chế độ retired.
Không thêm dịch vụ tự khởi động sau reboot.

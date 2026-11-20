# Web Guitar Girl

Admin, login và download dùng React 19, Tailwind CSS 4, daisyUI 5; Java phục vụ HTML đã bundle, không cần Node ở runtime hoặc CDN.

```sh
cd GGServerJava/web-admin
npm ci
npm test
npm run build
```

Chạy build web trước Gradle khi sửa frontend. Build ghi lại `server/admin/login.html`, `server/admin/dashboard.html`, `server/download.html` dưới `src/main/java/emu/leman/ggserver/`; sửa nguồn trong `web-admin/src/`, không sửa HTML sinh ra.

Banner download: đặt ảnh được user cung cấp ở `resources/static/guitar-girl-banner.jpg` của resource root thực tế. Khi thiếu ảnh, trang hiện nền dự phòng; không dùng lại minh họa SVG cũ.

API admin giữ cookie HttpOnly và same-origin. Không lưu token/mật khẩu trong localStorage. Bộ test Node chỉ kiểm payload; test Java kiểm boundary API. Kiểm thử UI bằng tài khoản/dữ liệu thử trước khi thao tác ghi thật.

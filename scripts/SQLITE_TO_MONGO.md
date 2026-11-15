# Merge SQLite → MongoDB bằng Python

Script này dành riêng cho schema Guitar Girl trong `emulator/data/database.db`
và backend MongoDB của `GGServerJava`, không phải công cụ copy bảng bất kỳ.

```bash
cd GGServerJava
python3 -m pip install -r scripts/requirements-migration.txt

# Không ghi MongoDB; kiểm tra nguồn và tài khoản trùng trước.
python3 scripts/sqlite_to_mongo.py \
  --source ../emulator/data/database.db --config resources/server-config.json --dry-run

# Ghi sau khi kiểm tra báo cáo.
python3 scripts/sqlite_to_mongo.py \
  --source ../emulator/data/database.db --config resources/server-config.json --apply
```

**Dừng cả server Python, Java và mọi tiến trình ghi trước khi chạy.** Backup
SQLite cùng file `-wal` nếu có, và backup MongoDB đích. Không xóa database gốc.
Config phải chọn `database.backend: "mongo"`; dùng `database.uri`/`database.name`
hoặc biến `GG_MONGO_URI`/`GG_MONGO_DATABASE` cho kết nối.

- `users`: gộp `user_data` và `user_inventory` thành account document đúng schema
  Java, giữ UUID/device/guest ID/sequence, currency, inventory extras, mail,
  ban, IP/domain, thời gian và các field JSON khác.
- SQL identity/currency ưu tiên hơn JSON cũ; inventory JSON được giữ nếu loại đó
  chưa có hàng trong bảng inventory. GP chuỗi không bị ép về số thực.
- `counters.user_sequence` được nâng bằng `$max`, không reset/đánh lại sequence.
- Mặc định account trùng bất kỳ alias nào làm toàn bộ preflight thất bại.
  `--skip-existing` bỏ qua **cả tài khoản** đã trùng, chỉ thêm tài khoản chưa có.
  Không cộng tiền, ghép inventory hay ghi đè tiến trình của account trùng vì dễ
  nhân đôi reward hoặc mất dữ liệu. Không có tùy chọn `--replace`.
- Dry-run không ghi collection/index/counter. Apply tạo unique indexes giống Java
  và dùng `insert_one`, không upsert account. Mỗi account là một lần ghi nguyên tử;
  không có transaction bao toàn bộ migration. Khi lỗi giữa chừng, báo `partial`;
  giữ báo cáo, kiểm tra đích rồi dry-run lại trước khi quyết định skip/resume.
- Chỉ truy vấn bản copy SQLite riêng, bao gồm committed WAL; so SHA-256 main file
  và sidecar trước/sau để phát hiện nguồn thay đổi. Không checkpoint nguồn.
- Script nạp dữ liệu vào RAM để preflight toàn bộ; phù hợp database emulator,
  chưa tối ưu streaming cho database rất lớn. Session không được chuyển.

Kiểm thử:

```bash
python3 -m unittest discover -s scripts -p test_sqlite_to_mongo.py -v
# Tùy chọn test integration, tạo/xóa database test tên ngẫu nhiên riêng:
GG_TEST_MONGO_URI=mongodb://127.0.0.1:27017 \
  python3 -m unittest discover -s scripts -p test_sqlite_to_mongo.py -v
```

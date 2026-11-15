# APK → resource research tools

Các tool ở đây chỉ chạy offline để phát triển. Java server không gọi Python,
UnityPy, IL2CPP dumper hoặc APK khi khởi động. Không đọc database tài khoản.

## 1. Inventory và TextAsset từ APK

UnityPy là dependency tùy chọn của extractor; không tự cài vào môi trường runtime.
Môi trường dùng kiểm tra hiện tại đã có UnityPy. Khi dùng môi trường mới, cài trong
virtualenv riêng và ghi lại version (`inventory.json` cũng lưu version).

```bash
python3 scripts/extract_apk_data.py \
  --apk ../orig_apk/com.neowiz.game.guitargirl.apk \
  --apk ../orig_apk/config.arm64_v8a.apk \
  --apk ../orig_apk/base_assets.apk \
  --output /tmp/opencode/gg-apk-assets-next
```

`--zip-only` không cần UnityPy. Tool chỉ đọc APK, không sửa/repack, không giải nén
ZIP path trực tiếp. Nó ghép `.split0`/`.split1`, kiểm tra Unity header, dùng pure
Python type-tree parser và xuất:

- `inventory.json`: SHA-256 APK, entry/CRC, Unity object counts, nguồn container/
  path ID, hash của từng TextAsset và lỗi/giới hạn.
- `text_assets/`: bản byte nguyên gốc; JSON và CSV decode giữ bên cạnh.
- Phân loại JSON chưa rõ, Spine animation và CSV candidate, **không tự nhập bất kỳ
  file nào vào gameplay catalog**. Review tên/ID/schema/code trước khi dùng.

APK chỉ có thể chứa client assets/code hoặc cache cũ, còn bảng server có thể
được tải qua mạng. Không suy ra tỷ lệ drop/quest condition chỉ từ tên file.
MonoBehaviour stripped chưa được giải mã; không tính là nội dung đã phân giải.

## 2. Named game catalog

`build_game_catalog.py` dùng stdlib, không import `emulator/server` hay DB. Nó
chuyển cột số sang đúng tên trường schema, tách 39 bảng vào feature folders,
giữ giá trị server và client capture riêng, kiểm tra khóa kể cả composite IDs,
và sinh từ điển ID/field/enum. Xem
[`resources/gamedata/catalog/README.md`](../resources/gamedata/catalog/README.md).

Xuất vào thư mục mới rồi review, không ghi đè data curated. Khi có APK phiên bản
mới cần tạo schema/dump đúng phiên bản, so sánh ID/type và kiểm thử wire trước
khi thay baseline. Trùng tên file không chứng minh tương thích phiên bản.

## Kết quả baseline hiện tại

- 3 APK gốc, 1.691 ZIP entries dưới `assets/`, 12 TextAsset, 0 lỗi extractor.
- 39 bảng / 4.065 row từ dữ liệu server hiện có; 39 DTO được cross-check với dump.
- 24 enum gameplay/UI liên quan, giữ nguyên literal và tên bị obfuscate.
- File tham khảo ID nằm trong `catalog/reference/ids.json`.
- Artifacts đầy đủ lần quét: `/tmp/opencode/gg-apk-catalog-extraction`.
  Không đưa ảnh/audio/binary APK vào distribution server.

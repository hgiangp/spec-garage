---
name: spec-parameterize
description: Extract hard-coded values (times, thresholds, counts, voltages, percentages) from spec prose into a named parameter table and reference them by name in the text. Use when asked to parameterize a section, pull values into a table, or make values configurable/traceable.
---

# spec-parameterize

> Draft. Hoàn thiện ở Phase 2.

## Quy trình

1. **Nạp tri thức:** đọc `data/knowledge/glossary.md` (mục Naming), `knowledge/templates/parameter-table.md` và `data/knowledge/lessons.md`.
2. **Lấy section:** `sg get <ID>`.
3. **Tìm mọi giá trị số** kèm đơn vị trong văn xuôi, bảng và chú thích. Với mỗi giá trị ghi lại: câu gốc, ý nghĩa, đơn vị, dung sai (nếu có).
4. **Kiểm tra trùng:** giá trị này đã là parameter ở section khác chưa (`sg related`, grep tên parameter trong vault)?
   - Đã có: dùng lại tên đó.
   - Chưa có: đề xuất tên mới theo quy ước Naming. Nếu quy ước chưa chốt thì đánh dấu `> [!question]` để expert chốt tên.
5. **Tạo hoặc cập nhật bảng Parameters** trong section. Trong câu gốc, thay giá trị bằng tên parameter.
6. **Giá trị không có đơn vị hoặc mơ hồ:** không đoán. Ghi `TBD` kèm `ASSUMPTION`.
7. **Kết thúc:** `status: proposed`, chạy `sg validate`, rồi tóm tắt cho ghi chú review: danh sách parameter mới / tái sử dụng, và các điểm TBD.

## Không được làm
- Làm tròn hoặc đổi đơn vị giá trị.
- Gộp hai giá trị giống nhau nhưng khác ý nghĩa vào một parameter.

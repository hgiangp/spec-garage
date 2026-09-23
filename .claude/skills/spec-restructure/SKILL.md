---
name: spec-restructure
description: Reorganize a spec section (or a small cluster of related sections) into a clear structure using the section templates — overview, inputs/outputs, behavior as one-requirement-per-line, states, parameters, fault handling — without changing meaning. Use when asked to restructure, reorganize, clean up or apply a template to a spec section.
---

# spec-restructure

> Draft. Hoàn thiện ở Phase 2, sau khi có vault và `sg` (get, related, validate).

Sắp xếp lại cách trình bày. **Nội dung kỹ thuật giữ nguyên.**

## Đầu vào
- Section ID (hoặc một cụm ID liên quan).
- Nên có report của `spec-analyze` cho section đó. Nếu chưa có thì chạy trước.

## Quy trình

1. **Nạp tri thức:** đọc `knowledge/style-guide.md`, `data/knowledge/lessons.md`, `data/knowledge/glossary.md`.
2. **Lấy dữ liệu:** `sg get <ID>`, `sg related <ID>` và report analyze (`data/reports/analyze/<ID>.md`).
3. **Chọn template** trong `knowledge/templates/` theo loại section: function, state machine, signal table, timing, DTC.
4. **Liệt kê mọi "fact" trong bản gốc** trước khi viết lại: requirement, giá trị, điều kiện, link. Đây là checklist để bảo toàn nội dung.
5. **Viết lại theo template:**
   - Mỗi requirement một dòng, theo EARS.
   - Thiếu thông tin thì ghi `ASSUMPTION` / `question`, không tự điền.
6. **Đối chiếu:** mọi fact ở bước 4 phải còn trong bản mới. Không có fact mới nào ngoài các mục đánh dấu `ASSUMPTION`.
7. **Cập nhật metadata:**
   - Giữ `id`, `anchors`, `legacy_number`, và các comment `<!-- id: … -->` của heading con.
   - Heading con mới: lấy ID mới qua `sg` (không tự đánh số).
   - Đặt `status: proposed`.
8. **Chạy `sg validate`.**
9. **Tóm tắt thay đổi** cho ghi chú review (commit message của branch improve): cấu trúc cũ → mới, danh sách `ASSUMPTION` và `question`.

## Không được làm
- Đổi giá trị, điều kiện, thứ tự hành vi.
- Xoá thông tin vì "có vẻ thừa". Nếu trùng với section khác thì thay bằng link và ghi rõ trong ghi chú review.
- Đổi tên signal.

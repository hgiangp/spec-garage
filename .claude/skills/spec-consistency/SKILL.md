---
name: spec-consistency
description: Cross-check a spec section against the sections it references and that reference it, including across spec files (e.g. Warning vs LIN COMM), and report contradictions in values, signal names, states, conditions and timing. Report only, no edits. Use when asked to check consistency, find contradictions, or verify references between sections or specs.
---

# spec-consistency

> Draft. Hoàn thiện ở Phase 2, cần `sg related` (có cross-file).

Chỉ **báo cáo**.

## Quy trình

1. **Nạp tri thức:** đọc `data/knowledge/glossary.md`, `data/knowledge/lessons.md`.
2. **Lấy dữ liệu:**
   - `sg get <ID>`
   - `sg related <ID>`: cả chiều ra (section này refer tới) và chiều vào (section khác refer tới nó), kể cả spec khác.
3. **Rút "fact" có thể so sánh** từ mỗi section: tên signal, giá trị, đơn vị, trạng thái, điều kiện, timing.
4. **So khớp theo từng fact:**
   - Cùng signal nhưng khác giá trị, khác đơn vị hoặc khác ý nghĩa.
   - Cùng parameter nhưng khác giá trị.
   - Điều kiện chồng lấn hoặc mâu thuẫn.
   - Link trỏ tới section không nói về nội dung được nhắc.
5. **Ghi report** vào `data/reports/consistency/<ID>.md`. Dùng cùng format bảng Issues như `spec-analyze`, và mỗi issue ghi **cả hai vị trí**.

## Quy tắc
- **Không kết luận bên nào đúng.** Nêu mâu thuẫn và hỏi expert.
- Nếu phát hiện spec được refer nhưng không có trong `specs.yaml`, ghi vào mục "Out-of-scope specs".
- **Ngôn ngữ output:** report và mọi nội dung ghi vào spec/vault viết bằng **tiếng Anh**.

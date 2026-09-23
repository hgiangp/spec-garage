---
name: spec-analyze
description: Analyze one section (or a cluster of related sections) of an automotive spec and report quality issues — ambiguity, missing values/units, merged requirements, contradictions, broken or suspicious references — without editing anything. Use when asked to review, audit, check or find problems in a spec section, or before improving a section.
---

# spec-analyze

Chỉ **báo cáo**, không sửa spec. Output là một file report để expert đọc và để các skill improve dùng làm đầu vào.

## Đầu vào

Một trong:
- **Section ID** (`WRN-0342`), sau khi đã có vault.
- **File + heading** trong `data/sources/`, trước khi có vault. Xác định khoảng dòng của section bằng `grep -n '^#' <file>` rồi đọc đúng khoảng đó.

## Quy trình

1. **Nạp tri thức:** đọc `knowledge/quality-checklist.md`, `knowledge/style-guide.md`, `data/knowledge/glossary.md` và `data/knowledge/lessons.md`.
2. **Lấy section:**
   - Có vault: `sg get <ID>` (Phase 1).
   - Chưa có vault: đọc khoảng dòng của section kèm heading cha để biết ngữ cảnh.
3. **Lấy section liên quan:**
   - Có vault: `sg related <ID>`.
   - Chưa có vault: theo các link `#_Ref…` / `#_Toc…` trong section, tìm anchor tương ứng bằng grep.
   - Đọc các section đó ở mức đủ để kiểm tra nhất quán, không phân tích sâu.
4. **Kiểm tra** từng requirement theo Q1–Q8 và toàn section theo S1–S7 trong checklist.
5. **Ghi report** vào `data/reports/analyze/<ID>.md` (có vault) hoặc `data/reports/analyze/<CODE>-L<start>-L<end>.md` (chưa có vault, ví dụ `WRN-L120-L245.md`) theo format dưới đây.

## Format report

```markdown
---
target: WRN-0342            # hoặc data/sources/WRN/<file>.md#L120-L245
related: [WRN-0120, LIN-0033]
date: YYYY-MM-DD
---

# Analyze: <title>

## Tóm tắt
<2–4 câu: tình trạng chung, vấn đề lớn nhất.>

## Issues
| # | Mức | Mã | Vị trí (dòng / câu trích ngắn) | Vấn đề | Gợi ý hướng xử lý |
|---|---|---|---|---|---|
| 1 | High | Q1 | "…turn on immediately…" | "immediately" không kiểm tra được | Thay bằng parameter thời gian; giá trị cần expert |

## Câu hỏi cho expert
- <những điểm agent không tự quyết được>

## Gợi ý cải tổ cấu trúc
- <ví dụ: gom 6 giá trị timing thành bảng parameter; tách behavior thành state machine>
```

## Quy tắc

- **Không suy đoán giá trị.** Nếu thấy thiếu, ghi là thiếu và đưa vào "Câu hỏi cho expert".
- **Trích ngắn** (≤ 15 từ) để định vị. Không chép nguyên đoạn dài.
- **Mâu thuẫn giữa các section** (Q6) phải nêu cả hai vị trí.
- **Mức độ** theo bảng trong `quality-checklist.md`. Sắp xếp issue từ High xuống Low.
- Nếu một rule trong `lessons.md` áp dụng được, ghi mã rule (`L-00x`) ở cột Mã.

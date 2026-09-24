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
   - Signals, inputs and cross-spec references: read `data/reports/trace/<ID>.md`; if it does not exist, run the `spec-trace` skill first.
   - Chưa có vault: theo các link `#_Ref…` / `#_Toc…` trong section, tìm anchor tương ứng bằng grep.
   - Đọc các section đó ở mức đủ để kiểm tra nhất quán, không phân tích sâu.
4. **Kiểm tra** từng requirement theo Q1–Q8 và toàn section theo S1–S7 trong checklist.
5. **Ghi report** vào `data/reports/analyze/<ID>.md` (có vault) hoặc `data/reports/analyze/<CODE>-L<start>-L<end>.md` (chưa có vault, ví dụ `WRN-L120-L245.md`) theo format dưới đây.

## Format report

```markdown
---
target: WRN-0342            # or data/sources/WRN/<file>.md#L120-L245
related: [WRN-0120, LIN-0033]
date: YYYY-MM-DD
---

# Analyze: <title>

## Summary
<2–4 sentences: overall state, the most important problem.>

## Issues
| # | Severity | Code | Location (line / short quote) | Problem | Suggested direction |
|---|---|---|---|---|---|
| 1 | High | Q1 | "…turn on immediately…" | "immediately" is not verifiable | Replace with a time parameter; value needed from expert |

## Questions for the expert
- <points the agent cannot decide on its own>

## Restructuring suggestions
- <e.g. collect 6 timing values into a parameter table; move behavior into a state machine>
```

## Quy tắc

- **Không suy đoán giá trị.** Nếu thấy thiếu, ghi là thiếu và đưa vào "Questions for the expert".
- **Ngôn ngữ output:** report và mọi nội dung ghi vào spec/vault viết bằng **tiếng Anh**.
- **Trích ngắn** (≤ 15 từ) để định vị. Không chép nguyên đoạn dài.
- **Mâu thuẫn giữa các section** (Q6) phải nêu cả hai vị trí.
- **Mức độ** theo bảng trong `quality-checklist.md`. Sắp xếp issue từ High xuống Low.
- Nếu một rule trong `lessons.md` áp dụng được, ghi mã rule (`L-00x`) ở cột Mã.

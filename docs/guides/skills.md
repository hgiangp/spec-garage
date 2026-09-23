# Guide: skill improve và tri thức đi kèm

| | |
|---|---|
| **Task** | F2, S1–S6 ([tasks](../tasks.md)) |
| **Code** | `.claude/skills/*/SKILL.md`, `knowledge/`, `data/knowledge/` |
| **Quyết định** | D8 (cấu trúc skill), D9 (guardrail), D10 (vòng review) trong [design doc](../spec-pipeline-design.md) |

## Trạng thái từng skill

| Skill | Làm gì | Có sửa spec không | Trạng thái | Cần |
|---|---|---|---|---|
| `spec-analyze` | Báo lỗi chất lượng: mơ hồ, thiếu giá trị/đơn vị, gộp requirement, mâu thuẫn, ref gãy | Không (chỉ báo cáo) | ✅ **Dùng được ngay**, kể cả trên `data/sources/` trước khi có vault | |
| `spec-restructure` | Sắp xếp lại theo template, mỗi requirement một dòng (EARS) | Có | Draft | T3 (`sg get/related`), T4 |
| `spec-parameterize` | Rút giá trị cứng ra bảng parameter | Có | Draft | T3, T4 |
| `spec-consistency` | Đối chiếu với các section liên quan, kể cả spec khác | Không (chỉ báo cáo) | Draft | T3 (`related` cross-file) |
| `spec-diagram` | Mô tả ảnh, chuyển sang Mermaid, giữ ảnh gốc | Có | Draft | T3, T4 |

## Cách dùng (trên máy dữ liệu, với Claude Code)

Mở Claude Code ở gốc repo. Skill trong `.claude/skills/` được nhận diện tự động. Gọi bằng câu lệnh tự nhiên hoặc `/spec-analyze`.

**Trước khi có vault**, chỉ định file và heading:
```
/spec-analyze data/sources/WRN/7820ZXXXXG000_E_(Warning)_260220.md, section "3.2 Buzzer Control"
```
Report được ghi vào `data/reports/analyze/WRN-L<start>-L<end>.md`.

**Sau khi có vault:**
```
/spec-analyze WRN-0342
```
Report được ghi vào `data/reports/analyze/WRN-0342.md`.

Report gồm: tóm tắt, bảng issue (mức High/Medium/Low, mã Q1–Q8 / S1–S7, vị trí, gợi ý), câu hỏi cho expert, gợi ý cải tổ cấu trúc.

## Tri thức skill dùng

| File | Repo | Nội dung | Ai sửa |
|---|---|---|---|
| `knowledge/style-guide.md` | public | shall/should, EARS, đơn vị, từ mơ hồ, đánh dấu cho expert | Máy phát triển, sau khi expert đồng ý |
| `knowledge/quality-checklist.md` | public | Q1–Q8, S1–S7 theo ISO/IEC/IEEE 29148, mức độ | Như trên |
| `knowledge/templates/*.md` | public | function, parameter-table, state-machine, signal-table, timing, dtc | Như trên |
| `data/knowledge/glossary.md` | data | Thuật ngữ, ECU, signal, quy ước đặt tên | Expert, trên máy dữ liệu |
| `data/knowledge/lessons.md` | data | Rule `L-00x` rút ra từ review. **Ưu tiên hơn style guide** | Expert, trên máy dữ liệu |

Các file trong `knowledge/` đều là **bản nháp**, cần expert review.

## Guardrail (D9), áp dụng cho mọi skill có sửa spec

1. **Không bịa giá trị.** Thiếu thông tin thì ghi `> [!todo] ASSUMPTION: …`.
2. **Không đổi ngữ nghĩa** khi chưa được expert xác nhận. Mỗi lần improve là một branch trong repo `data/`.
3. **Giữ nguyên** ID, `anchors`, `legacy_number` và comment `<!-- id: … -->`. ID mới chỉ lấy qua `sg new-id`.
4. Chạy `sg validate` sau khi sửa (khi T4 xong).

## Vòng review (D10)

```
skill đề xuất → branch improve/<ID>-… trong data/ → expert xem git diff
  → accept / reject / sửa, KÈM LÝ DO → merge vào main của data/
  → lý do chưng cất thành L-00x trong data/knowledge/lessons.md
  → section đã duyệt thành eval case trong data/evals/skills/<skill>/
```

Cải tiến **quy trình** của skill (không chứa nội dung domain) thì gửi về máy phát triển để sửa `SKILL.md`.

## Giới hạn đã biết

- 4 skill draft phụ thuộc vào `sg get`, `sg related`, `sg validate`, hiện chưa có. Trước khi có các lệnh này, chỉ nên dùng `spec-analyze`.
- Chưa có bộ eval, nên chưa đo được chất lượng skill (S5).

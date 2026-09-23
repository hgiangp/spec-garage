# Phase 0: kết quả profile và đề xuất quyết định

> Nguồn: `sg profile` chạy trên máy dữ liệu, 2026-09-23 (trước P0.5).
> **Cập nhật sau khi có mẫu thật và lệnh convert:** xem [`handoff.md`](handoff.md) §3. F2 và F4 bên dưới đã được đính chính.
> File này chỉ ghi **số liệu tổng hợp**, không chứa nội dung spec, tên heading hay tên slug.
> Guide đọc số liệu: [`guides/profile.md`](guides/profile.md). Task: P0.2–P0.5 trong [`tasks.md`](tasks.md).

## 1. Số liệu chính

| | WRN (Warning) | EWA (EnlargeWA) | LIN (LIN COMM) |
|---|---|---|---|
| Dòng | 25,468 | 8,047 | 6,220 |
| Token (ước lượng) | ~211k | ~89k | ~44k |
| Heading (H1/H2/H3/H4/H5) | 1593 (64/174/483/614/258) | 394 (14/73/107/123/77) | 219 (4/13/62/122/18) |
| Heading có số | 1570 (98.6 %) | 393 (99.7 %) | 219 (100 %) |
| Heading có anchor trên cùng dòng | 0 | 4 | 0 |
| Anchor tường minh (đều là HTML) | 598 | 207 | 69 |
| Link nội bộ | 2224 | 1042 | 456 |
| … không resolve được (trước P0.5) | 942 (42 %) | 278 (27 %) | 156 (34 %) |
| Link cross-file | 0 | 0 | 0 |
| Bảng pipe / HTML | 307 / 219 | 120 / 64 | 26 / 54 |
| Ảnh (thiếu file) | 301 (0) | 98 (0) | 9 (0) |
| Heading trùng tiêu đề | 166 | 2 | 7 |
| Nhảy cấp heading | 5 | 21 | 0 |

## 2. Phát hiện và xử lý

| # | Phát hiện | Hệ quả | Xử lý |
|---|---|---|---|
| F1 | Gần như mọi heading đều có số trong tiêu đề | `legacy_number` lấy thẳng từ tiêu đề | T2: đọc từ tiêu đề. Heading không có số thì để trống |
| F2 | 0 heading có anchor trên cùng dòng, dù có hàng trăm anchor HTML | **Đính chính:** pandoc thay bookmark trên heading bằng slug và viết lại link (mẫu thật cho thấy vậy). Các anchor HTML là anchor của **caption bảng/hình** (`<span id class="anchor">`). Không có rủi ro gán nhầm section | P0.5 resolve slug. Placement `before_heading` giữ lại, vô hại |
| F3 | Link không resolve 27–42 %. Ở LIN, phần lớn là link dạng slug tiêu đề | Converter tạo link tới heading bằng slug kiểu pandoc | P0.5: sinh anchor ngầm từ tiêu đề (pandoc + GitHub) |
| F4 | Ở WRN và EWA, phần lớn anchor chưa resolve là `_Ref…` | Không phải tham chiếu tới heading (vì pandoc đã viết lại những link đó). Có thể là bookmark trong shape (đã thành PNG) hoặc trong ô bảng (bị chuyển sang GFM) | **Chưa rõ.** Xem câu hỏi Q1–Q3 trong `handoff.md` §4 |
| F5 | Không có link cross-file | Tham chiếu giữa các spec chỉ ở dạng chữ | Profile giờ đếm số tài liệu được nhắc trong nội dung. `spec-consistency` dựa vào đó và vào tên signal |
| F6 | Nhiều bảng HTML (WRN 219) | T2 không được cắt giữa bảng HTML. Export phải giữ nguyên | Ghi vào đặc tả T2 và T5 |
| F7 | Heading trùng tiêu đề nhiều (WRN 166) dù có số | Có thể số heading bị lặp (đánh số lại theo chương) | Profile giờ có `duplicate numbers`. **Cần chạy lại** |
| F8 | Có section lá vượt ngưỡng ở mọi mức (WRN tới ~16.5k token) | Một note rất lớn, nhiều khả năng là bảng lớn | Profile giờ liệt kê theo số heading (`over:`). Expert xem |

## 3. Ngưỡng tách (D1)

| Ngưỡng | WRN note (p90 / tiny / over) | EWA | LIN | Tổng note |
|---|---|---|---|---|
| 2000 | 359 (1,316 / 74 / 2) | 154 (1,294 / 26 / 2) | 105 (961 / 24 / 2) | 618 |
| **3000** | **247 (2,202 / 42 / 2)** | **127 (1,660 / 20 / 2)** | **71 (1,742 / 12 / 1)** | **445** |
| 5000 | 152 (3,785 / 17 / 2) | 90 (2,496 / 11 / 1) | 40 (3,384 / 10 / 1) | 282 |
| 8000 | 100 (4,780 / 8 / 2) | 60 (4,548 / 7 / 0) | 36 (4,229 / 8 / 0) | 196 |

**Đề xuất: 3000 cho cả 3 spec.**
- **Đúng đơn vị làm việc của improve:** 90 % note ≤ khoảng 2.2k token. Một note cộng các note liên quan và `knowledge/` vẫn nằm gọn trong context.
- **Diff dễ review:** mỗi lần improve chỉ động tới một vài note nhỏ.
- **Note "tiny" chấp nhận được:** 74 note tiny trên tổng 445 (heading cha chỉ có tiêu đề hoặc đoạn mở đầu ngắn). Chúng đóng vai trò mục lục của chương.
- **So với 5000:** giảm được note tiny nhưng note to gần gấp đôi (p90 khoảng 3.8k), đơn vị review thô hơn.
- **Section lá vượt ngưỡng** (1–2 mỗi spec) giữ nguyên là một note. Expert quyết định có tách theo nội dung ở Phase 2 không.

- [ ] Expert xác nhận ngưỡng 3000 (P0.4)

## 4. Việc tiếp theo

Chuyển sang máy dữ liệu, xem [`handoff.md`](handoff.md):
- §4: câu hỏi Q1–Q5, bắt đầu bằng `sg profile --diagnose`;
- §8: thứ tự việc.

Khi chạy lại profile trên máy dữ liệu, cập nhật số liệu ở §1 và cột "Xử lý" ở §2 của file này. Chỉ ghi số tổng hợp, không ghi tên slug hay tiêu đề heading.

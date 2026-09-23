---
status: draft  # expert cần review
---

# Style guide viết spec

Quy tắc viết áp dụng khi improve. Spec viết bằng **tiếng Anh**.

## 1. Từ khoá bắt buộc

| Từ | Nghĩa | Dùng khi |
|---|---|---|
| **shall** | Bắt buộc | Mọi requirement |
| **should** | Khuyến nghị | Hạn chế dùng. Cần lý do |
| **may** | Tuỳ chọn | Hành vi được phép, không bắt buộc |
| **will / is** | Mô tả, không phải requirement | Mô tả bối cảnh, hành vi của hệ thống khác |

Không dùng `must`, `need to`, `has to` cho requirement. Chuyển sang `shall`.

## 2. Mẫu câu requirement (EARS)

| Loại | Mẫu |
|---|---|
| Luôn đúng | `The <system> shall <response>.` |
| Theo sự kiện | `When <trigger>, the <system> shall <response>.` |
| Theo trạng thái | `While <state>, the <system> shall <response>.` |
| Lỗi / ngoại lệ | `If <condition>, then the <system> shall <response>.` |
| Tuỳ chọn tính năng | `Where <feature is present>, the <system> shall <response>.` |
| Kết hợp | `While <state>, when <trigger>, the <system> shall <response>.` |

- **Một câu = một requirement.** Không gộp nhiều hành vi bằng "and" khi chúng kiểm tra được riêng.
- **Chủ ngữ rõ ràng:** tên ECU hoặc function, không dùng "it" hay "the system" chung chung nếu có nhiều hệ thống.

## 3. Giá trị và đơn vị

- **Mọi giá trị số có đơn vị**, cách một khoảng trắng: `100 ms`, `12 V`, `5 %`.
- **Giá trị dùng lại hoặc có thể hiệu chỉnh** thì đặt tên parameter và đưa vào bảng parameter (xem `templates/parameter-table.md`). Trong câu chỉ tham chiếu tên: `within T_LampOn`.
- **Dung sai ghi rõ:** `100 ms ± 10 ms` hoặc min/typ/max.
- **Không dùng từ mơ hồ:** `fast`, `immediately`, `about`, `approximately`, `sufficient`, `as soon as possible`, `etc.`, `and/or`, `normally`. Thay bằng giá trị cụ thể, hoặc ghi `ASSUMPTION` nếu chưa biết.

## 4. Tên signal, parameter, trạng thái

- Giữ nguyên tên signal như trong spec gốc hoặc spec giao tiếp (LIN/CAN). **Không tự đổi tên.**
- Đặt tên parameter mới theo quy ước trong `glossary.md` (mục Naming). Nếu chưa có quy ước, đề xuất và đánh dấu để expert chốt.
- Trạng thái (state) viết hoa nhất quán, ví dụ `OFF`, `ON`, `BLINK`, và liệt kê trong bảng hoặc sơ đồ state machine.

## 5. Cấu trúc section

- Mỗi section function nên theo `templates/function.md`.
- Bảng dùng pipe table markdown, có hàng tiêu đề và cột đơn vị riêng nếu có số.
- Diagram: giữ ảnh gốc. Nếu chuyển sang Mermaid thì đặt ngay dưới ảnh, ảnh gốc vẫn giữ.

## 6. Đánh dấu cho expert

| Ký hiệu | Dùng khi |
|---|---|
| `> [!todo] ASSUMPTION: …` | Thiếu thông tin, agent không được tự điền |
| `> [!question] …` | Cần expert trả lời: mơ hồ, mâu thuẫn |
| `> [!note] CHANGE: …` | Giải thích một thay đổi đáng chú ý trong PR |

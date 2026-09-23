---
status: draft  # expert cần review
---

# Quality checklist cho requirement và section

Dựa trên các đặc tính chất lượng của ISO/IEC/IEEE 29148. Dùng cho `spec-analyze` (báo lỗi) và để tự kiểm tra sau mỗi lần improve.

## Theo từng requirement

| Mã | Đặc tính | Câu hỏi kiểm tra |
|---|---|---|
| Q1 | Unambiguous | Chỉ có một cách hiểu? Không có từ mơ hồ (xem style-guide §3)? |
| Q2 | Verifiable | Viết được test case pass/fail không? Có giá trị, điều kiện, thời gian cụ thể? |
| Q3 | Singular | Chỉ một requirement trong câu? |
| Q4 | Complete | Đủ trigger, điều kiện, phản hồi, giá trị và đơn vị? |
| Q5 | Feasible | Có mâu thuẫn rõ ràng với giới hạn vật lý hoặc timing không? (chỉ báo, không tự sửa) |
| Q6 | Consistent | Có mâu thuẫn với section khác hoặc spec khác không? |
| Q7 | Correct terms | Tên signal, parameter, trạng thái đúng theo glossary và spec giao tiếp? |
| Q8 | Traceable | Có ID (section ID) và link tới section liên quan? |

## Theo từng section

| Mã | Kiểm tra |
|---|---|
| S1 | Có mục đích / tổng quan ngắn ở đầu? |
| S2 | Giá trị số rải rác trong văn xuôi, nên gom thành bảng parameter? |
| S3 | Hành vi theo trạng thái, nên có bảng hoặc sơ đồ state machine? |
| S4 | Trường hợp lỗi / ngoại lệ đã được mô tả? |
| S5 | Link trỏ đi có hợp lệ, có trỏ đúng nội dung? |
| S6 | Cấu trúc heading hợp lý (không nhảy cấp, không section rỗng)? |
| S7 | Nội dung lặp với section khác? Nên thay bằng link? |

## Mức độ

| Mức | Ý nghĩa |
|---|---|
| **High** | Có thể dẫn tới implement sai: mơ hồ về giá trị hoặc điều kiện, mâu thuẫn |
| **Medium** | Khó verify hoặc khó bảo trì: thiếu đơn vị, gộp nhiều requirement |
| **Low** | Trình bày: format, câu chữ |

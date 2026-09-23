---
name: spec-diagram
description: Describe a spec figure (state machine, sequence, timing or block diagram) in text and, where the figure's type allows, add an equivalent Mermaid diagram next to it, keeping the original image. Use when asked to describe, transcribe or convert a diagram/image in a spec section.
---

# spec-diagram

> Draft. Hoàn thiện ở Phase 2 (D4).

## Quy trình

1. **Lấy section:** `sg get <ID>`, xác định các ảnh (`![[…]]`) trong section.
2. **Với mỗi ảnh:** đọc ảnh, xác định loại (state machine, sequence, timing chart, block diagram, bảng dạng ảnh, khác).
3. **Viết mô tả text** trong callout ngay dưới ảnh:
   ```markdown
   > [!figure] <type>: <short title>
   > <description: components, flow/transitions, values written on the figure>
   ```
4. **Nếu là state machine hoặc sequence:** thêm khối Mermaid tương đương dưới mô tả. Phải đối chiếu với text trong section:
   - Thứ gì có trong hình mà không có trong text, hoặc ngược lại: ghi `> [!question]`.
5. **Giữ ảnh gốc.** Không xoá, không đổi tên file ảnh.
6. **Kết thúc:** `status: proposed`, chạy `sg validate`.

## Quy tắc
- Chữ trên hình đọc không chắc chắn thì ghi `[unclear]`. **Không đoán.**
- **Ngôn ngữ output:** report và mọi nội dung ghi vào spec/vault viết bằng **tiếng Anh**.
- Timing chart: chỉ ghi các giá trị có ghi trên hình. Không ước lượng từ tỷ lệ.

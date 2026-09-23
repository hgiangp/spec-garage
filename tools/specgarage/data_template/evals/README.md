# Eval cho skill (D10)

Mỗi case là một thư mục:

```
data/evals/skills/<skill>/<case-id>/
├─ input.md        # section trước khi improve (bản sao từ vault tại thời điểm tạo case)
├─ expected.md     # bản expert đã duyệt
└─ notes.md        # điểm chấm: fact phải giữ, lỗi không được mắc, lý do
```

Eval case và bộ câu hỏi viết bằng **tiếng Anh**.

Mục tiêu: 10–20 case cho mỗi skill. Chạy lại mỗi khi sửa skill hoặc `knowledge/`.

Câu hỏi vàng cho giai đoạn RAG (D12) nằm ở `data/evals/qa/`.

# Template: Function section

Dùng cho section mô tả một function. Mục nào không áp dụng thì bỏ, không để rỗng.

```markdown
## <Function name>

### Overview
<1–3 câu: function làm gì, cho ai, trong điều kiện nào.>

### Inputs
| Signal / Parameter | Source | Description |
|---|---|---|

### Outputs
| Signal / Actuator | Destination | Description |
|---|---|---|

### Preconditions
- <điều kiện để function hoạt động: nguồn, trạng thái xe, …>

### Behavior
<Requirement theo EARS, mỗi dòng một requirement.>
- When <trigger>, the <system> shall <response>.

### States
<Nếu có trạng thái: link tới state machine, hoặc dùng templates/state-machine.md>

### Parameters
<Bảng theo templates/parameter-table.md>

### Fault handling
- If <fault condition>, then the <system> shall <response>.

### Related
- [[<ID>|<title>]]: <quan hệ: dùng signal từ, bị ảnh hưởng bởi, …>
```

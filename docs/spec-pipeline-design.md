# Spec Garage: phương án ingest, improve và đánh giá spec

> Trạng thái: **Draft, đang chờ chốt các quyết định**
> Cập nhật: 2026-09-23
> **Trọng tâm hiện tại: G2 (improve spec).** G3 (RAG, so sánh before/after) và MCPVault được lùi về giai đoạn sau. Xem [§1.4](#14-phạm-vi-giai-đoạn-hiện-tại).

Tài liệu này dùng để **chọn phương án, đánh ưu tiên và chốt quyết định** cho các công đoạn phía sau. Mỗi quyết định có mã `D#`, các lựa chọn, đề xuất và ô trạng thái. Khi đã chốt thì cập nhật ô trạng thái để phần implementation bám theo.

---

## 1. Bối cảnh

### 1.1 Dữ liệu

- Spec automotive được convert từ Word sang Markdown, ảnh nằm trong folder đi kèm.
- File rất dài: 8.000 dòng, 26.000 dòng, …
- Heading sâu tới H5–H6. Độ dài section không đều: có section rất dài, có section chỉ vài dòng.
- Có nhiều spec file và chúng **refer lẫn nhau**.
- Trong section có cross-reference. Hyperlink Word được giữ lại khi convert, thường ở dạng anchor/bookmark như `#_Ref…`, `#_Toc…`.

### 1.2 Ba mục tiêu

| #  | Mục tiêu                                  | Kết quả mong muốn                                                                                                                                             |
| -- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| G1 | **Ingest** spec một cách hiệu quả | Spec có cấu trúc, địa chỉ hoá được đến từng section, tra cứu được bởi người, agent và chatbot                                               |
| G2 | **Skills improve spec**               | Bộ skill giúp agent cùng domain expert sắp xếp lại, làm rõ, mở rộng và parameter hoá spec. Skill được hoàn thiện dần qua các vòng làm việc |
| G3 | **So sánh before/after**             | Ingest cả hai phiên bản, hỏi đáp bằng chatbot (RAG) và đo được mức cải thiện khả năng "AI đọc hiểu"                                          |

### 1.3 Phạm vi một lần improve

Thường là **1 section**, hoặc **một vài section liên quan** (liên quan qua cross-ref, hoặc cùng function/domain).

### 1.4 Phạm vi giai đoạn hiện tại

Giai đoạn này **ưu tiên improve trước**. Những gì cần và chưa cần:

| Cần ngay                                                              | Chưa cần (giai đoạn sau)                     |
| ---------------------------------------------------------------------- | ------------------------------------------------ |
| Tách spec thành section note (D1)                                    | Index chunk, embedding, vector store (D5, D6)    |
| Section ID ổn định (D2)                                             | Chatbot RAG, bộ câu hỏi vàng, eval (D7, D12) |
| Resolve hyperlink thành link giữa các note (D3)                     | MCPVault (D13)                                   |
| Script hỗ trợ:`get_section`, `related`, `validate`, `export` | Model embedding (một phần D11)                 |
| Skills improve + guardrail + vòng review (D8, D9, D10)                |                                                  |
| Git (repo `data/` local): mỗi lần improve là một branch            |                                                  |

Mặc dù G3 để sau, D2 (Section ID) vẫn phải làm đúng ngay từ đầu. Nếu thiếu nó thì sau này không so sánh before/after được.

**Công cụ cho agent:** dùng Claude Code, hoặc agent nào có quyền truy cập filesystem, làm việc trực tiếp trên vault qua `Read`, `grep`, `Edit` và git. **Obsidian chỉ dùng làm viewer** cho domain expert: mở thư mục vault là có graph view, backlink và ảnh, không cần cài thêm gì. Để được vậy, chỉ cần giữ format tương thích Obsidian: `[[wikilink]]`, frontmatter YAML, `![[ảnh]]`.

---

## 2. Kết luận về MCPVault: có embedding không?

**Không có embedding.** Đã kiểm tra trực tiếp source code `bitbonsai/mcpvault` v0.16.0, file `src/search.ts`:

- **Dependencies** chỉ gồm `@modelcontextprotocol/server`, `gray-matter`, `yaml`, `trash`. Không có thư viện embedding hay vector nào.
- **`search_notes` là BM25 tính tại thời điểm query** (k1 = 1.2, b = 0.75):
  - **Không có index lưu sẵn.** Mỗi lần search, nó đọc lại toàn bộ file `.md` trong vault rồi tính điểm.
  - **Đơn vị xếp hạng là cả note (cả file).** Một file spec 26k dòng tính là 1 document.
  - Match dạng **substring, không phân biệt hoa thường**: `abs` cũng match `absolute`. Không có stemming, synonym hay hiểu ngữ nghĩa.
  - Query nhiều từ: một note được coi là ứng viên nếu match **bất kỳ** từ nào, rồi mới rank.
  - `limit` mặc định **5**, tối đa **20**. Excerpt trả về chỉ khoảng ±21 ký tự quanh vị trí match đầu tiên.
  - Có filter `pathPrefix` và `excludePaths`, tức là lọc được theo thư mục (theo spec, theo domain).
- **Các tool hữu ích cho spec dài:**
  - `get_note_outline`: trả về cây heading kèm số dòng, không cần đọc cả file.
  - `read_note_lines`: đọc đúng một khoảng dòng (một section).
  - Ngoài ra có `read_multiple_notes`, `patch_note`, `update_frontmatter`, `get_frontmatter`, `manage_tags`, `wiki_link`, `move_note`.
- Không cần mở Obsidian. Có chế độ read-only.

### Hệ quả cho thiết kế

1. MCPVault chỉ là cầu nối MCP để AI đọc, ghi và search markdown. **Agent đã có quyền truy cập filesystem (Claude Code) thì làm được tất cả những việc đó mà không cần nó**, nên giai đoạn improve không dùng MCPVault (xem D13). Nó cũng **không thay được tầng semantic retrieval** của chatbot RAG ở G3.
2. Vì BM25 xếp hạng theo note, **độ mịn của vault quyết định chất lượng search**. Nếu để nguyên file 26k dòng, search chỉ trả lời được "file nào có từ này", không định vị được section. Đây là thêm một lý do để **tách vault theo section** (xem D1).
3. Muốn có semantic search trong Obsidian thì phải thêm thành phần khác, ví dụ plugin Smart Connections, một MCP server có vector store, hoặc index do mình tự build (xem D5).

---

## 3. Kiến trúc tổng thể (đề xuất)

Giai đoạn hiện tại làm **P1, P2, P3, P6**. **P4, P5** làm sau.

```
 .md gốc + ảnh (before)
        │
        ▼
 [P1 Parser] heading tree H1–H6, anchor/bookmark, bảng, ảnh, hyperlink
        │
        ▼
 [P2 Vault Obsidian]  ← nguồn sự thật (single source of truth), git
   - 1 note = 1 section logic, frontmatter: id, spec, path, refs, status
   - hyperlink Word → [[wikilink]] (trong file và giữa các file)
   - _index.json: id ↔ heading path ↔ vị trí trong file gốc
        │                         ▲
        │                         │ diff / PR, expert review
        │                  [P3 Skills improve] ← agent (Claude Code: Read/grep/Edit + scripts)
        │                                        Obsidian = viewer cho expert
        ▼
 ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ giai đoạn sau ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
 [P4 Indexer] chunk + breadcrumb + mô tả ảnh + ref graph
        │                     │
   index_before          index_after
        └────────┬────────────┘
                 ▼
 [P5 Chatbot + Eval]  RAG | agentic search | full-context
   bộ câu hỏi vàng → metrics → UI so sánh side-by-side
        │
        ▼
 [P6 Export] vault → ghép lại 1 file .md / .docx
```

Nguyên tắc cốt lõi:

- **Tách "đơn vị lưu trữ/chỉnh sửa" (section note trong vault) khỏi "đơn vị retrieval" (chunk trong index).**
  - Vault do người và agent sửa, được version bằng git.
  - Chunk do pipeline sinh tự động, có thể xoá đi build lại.
- **Section ID ổn định là "xương sống"** cho cả improve, traceability và so sánh before/after.

---

## 4. Các quyết định cần chốt

Mức ưu tiên: **P0** chặn mọi thứ phía sau, **P1** cần trước khi làm công đoạn tương ứng, **P2** tối ưu, làm sau được.

### D1: Có tách spec thành nhiều note không? Tách ở mức nào? `P0`

| Lựa chọn                                                         | Ưu                                                                                                       | Nhược                                                                                                       |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| A. Giữ nguyên 1 file, thêm`_index.json` (id → khoảng dòng) | Không phá cấu trúc gốc, export dễ                                                                   | BM25 của MCPVault chỉ định vị tới file. Diff và review khó. Nhiều agent sửa cùng lúc dễ conflict |
| **B. Tách vault theo section logic (ngưỡng động)**      | Search, review, diff đều theo section. Obsidian graph và backlink có ý nghĩa. Hợp phạm vi improve | Cần script round-trip để ghép lại. Phải quản lý tên note                                             |
| C. Tách cứng theo một level (ví dụ luôn H3)                  | Đơn giản                                                                                               | Section dài ngắn không đều nên có note rất to, có note chỉ 2 dòng                                  |

**Đề xuất: B.** Duyệt cây heading từ trên xuống, dừng ở node thoả một trong các điều kiện:

- Node có kích thước dưới ngưỡng (khởi điểm khoảng 3–5k token, chốt sau khi profile).
- Node đại diện cho một function/domain trọn vẹn (có thể khai báo thủ công cho từng spec).

Các heading sâu hơn (H4–H6) nằm luôn trong note đó.

- [ ] Chốt phương án
- [ ] Chốt ngưỡng sau khi profile (xem Phase 0). **Đề xuất: 3000**, xem `docs/phase0-findings.md` §3

### D2: Section ID `P0` ✅ Đề xuất đã có

**Đã xác nhận: spec không có requirement ID sẵn.** Vì vậy ID sẽ do hệ thống tự sinh.

#### Format: `<SPEC>-<NNNN>`

Ví dụ: `WRN-0342`, `LIN-0017`.

| Thành phần | Quy tắc |
|---|---|
| `<SPEC>` | Mã spec gồm 2–5 chữ in hoa, khai báo trong `specs.yaml`. Đã đề xuất: `WRN` (Warning), `EWA` (EnlargeWA), `LIN` (LIN COMM), xem `specs.yaml`. Mã không đổi kể cả khi tên file spec đổi |
| `-` | Dấu phân cách |
| `<NNNN>` | Số thứ tự 4 chữ số, đếm riêng cho từng spec. Nếu spec có hơn 9999 heading thì dùng 5 chữ số cho toàn spec đó |

#### Quy tắc cấp phát
1. **Gán cho mọi heading (H1–H6)**, không chỉ những heading trở thành note. Nhờ vậy hyperlink trỏ tới một H5 vẫn có ID để resolve.
2. Lần build đầu tiên gán theo **thứ tự xuất hiện trong tài liệu**: `0001`, `0002`, …
3. **ID mới luôn là `max + 1`** của spec đó. Không chèn số vào giữa, không dùng lại ID đã xoá. Có file `ids.lock` (hoặc `next_id` trong manifest) để tránh cấp trùng khi nhiều người cùng làm.
4. **ID không mang ý nghĩa**: không mã hoá số heading, cấp bậc hay nội dung. Nhờ đó section có thể di chuyển, đổi tên hay đánh số lại mà ID không đổi. Thứ tự và cấu trúc cây được lưu riêng trong `_manifest.yaml` (xem D3).
5. **Tách, gộp, xoá khi improve:**
   - Tách 1 thành 2: section cũ giữ ID ở phần chính, phần mới nhận ID mới kèm `derived_from: [WRN-0342]`.
   - Gộp 2 thành 1: giữ ID của section chính, section kia ghi `merged_into: WRN-0342` trong `_manifest.yaml` (phần `retired`).
   - Xoá: ID chuyển vào `retired` kèm lý do, không bao giờ cấp lại.

#### Vì sao không dùng các cách khác

| Cách | Vấn đề |
|---|---|
| Số heading (`3.2.4`) | Improve sẽ đánh số lại, làm vỡ link và so sánh before/after |
| Hash nội dung | Đổi mỗi khi sửa nội dung, tức là không ổn định |
| UUID | Ổn định nhưng người đọc và gõ khó; review PR khó |
| Slug theo tiêu đề | Đổi khi đổi tiêu đề, dễ trùng ("Overview") |

#### Vị trí lưu ID

**Heading gốc của note:** ID nằm trong frontmatter và cũng là tên file.

```yaml
---
id: WRN-0342
spec: WRN
title: Buzzer Parameters
aliases: ["3.2.4 Buzzer Parameters", "Buzzer Parameters"]
legacy_number: "3.2.4"          # số heading trong bản gốc, chỉ để truy vết
heading_path: ["3 Function Description", "3.2 Buzzer Control", "3.2.4 Buzzer Parameters"]
level: 3
anchors: [_Ref512345678, _Toc98765432]   # bookmark Word trỏ vào section này
refs_out: [WRN-0120, LIN-0033]            # do script sinh, không sửa tay
status: original                # original | proposed | reviewed | approved
derived_from: []
---
```

**Heading con bên trong note (H4–H6):** ID nằm trong một comment HTML ngay dưới heading. Comment này không hiển thị trong Obsidian, grep được và giữ nguyên khi export.

```markdown
#### Timing constraints
<!-- id: WRN-0345 | legacy: 3.2.4.1 | anchors: _Ref512349999 -->
```

- [x] Kiểm tra spec có requirement ID không: **không có**
- [ ] Chốt format `<SPEC>-<NNNN>` và danh sách mã spec trong `specs.yaml`

### D3: Quy ước tên note, link và cấu trúc `P0`

- **Tên file chỉ là ID:** `WRN-0342.md`. Tên file không chứa tiêu đề, để đổi tiêu đề không làm vỡ link. Tiêu đề đọc được nằm trong `title` và `aliases`.
- **Link:**
  - Tới note: `[[WRN-0342|Buzzer Parameters]]`. Phần sau `|` là chữ hiển thị.
  - Tới heading con: `[[WRN-0342#Timing constraints|…]]`. `validate` kiểm tra heading đích còn tồn tại và khớp với ID `WRN-0345`.
  - Hyperlink Word `#_Ref…`, `#_Toc…` được resolve qua trường `anchors` sang dạng link trên.
- **Cross-file ref:** resolve theo `anchors` của spec đích. Ref không resolve được thì giữ link gốc, gắn tag `#broken-ref` và đưa vào báo cáo của `validate`.
- **Thư mục vault phẳng theo spec:** `vault/WRN/WRN-0342.md`. Không lồng thư mục theo chương, để việc di chuyển section không kéo theo di chuyển file.
- **Cấu trúc cây và thứ tự** nằm trong `vault/WRN/_manifest.yaml`. Đây là nguồn duy nhất cho thứ tự khi export. Mọi thay đổi cấu trúc hiện rõ trong diff của file này.

  ```yaml
  spec: WRN
  next_id: 1289
  tree:
    - WRN-0001:
        - WRN-0002
        - WRN-0339:
            - WRN-0340
            - WRN-0342
  retired:
    - { id: WRN-0343, merged_into: WRN-0342, reason: "timeout table merged" }
  ```
- **Mục lục cho người đọc:** `vault/WRN/_toc.md` do script sinh từ manifest. Mở trong Obsidian để điều hướng theo cây heading.
- **Ảnh:** copy vào `vault/attachments/WRN/`, nhúng bằng `![[...]]`.
- **Cập nhật:** Obsidian là tuỳ chọn. Cú pháp link (markdown chuẩn hay wikilink) chưa chốt, khuyến nghị markdown chuẩn. Xem `docs/handoff.md` §5.

- [ ] Chốt quy ước

### D4: Xử lý ảnh `P1`

| Lựa chọn                                                                             | Ghi chú                                                                           |
| -------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| A. Chỉ giữ link ảnh                                                                 | RAG coi như không thấy nội dung ảnh                                           |
| **B. Vision model sinh mô tả text, lưu cạnh ảnh** (callout `> [!figure]`) | State machine, sequence và block diagram trở nên tìm kiếm được             |
| C. Chuyển diagram sang Mermaid/PlantUML                                               | Tốt nhất về lâu dài, và có thể là**một output của skill improve** |

**Đề xuất:** B khi ingest, C là mục tiêu của skill improve.

- [ ] Chốt

### D5: Tầng retrieval cho chatbot `P1`

| Lựa chọn                                                         | Ưu                                                     | Nhược                                                               |
| ------------------------------------------------------------------ | ------------------------------------------------------- | --------------------------------------------------------------------- |
| A. Chỉ dùng MCPVault (BM25)                                      | Có sẵn, không phải build                            | Không có ngữ nghĩa, rank theo cả note, tối đa 20 kết quả     |
| **B. Tự build index hybrid (BM25 + embedding) trên chunk** | Kiểm soát được, tái lập được cho before/after | Phải build và vận hành                                            |
| C. Plugin Obsidian (Smart Connections, …)                         | Có sẵn trong Obsidian                                 | Khó kiểm soát chunking/model và khó dùng để làm thí nghiệm |

**Đề xuất:** B cho chatbot và eval. Chọn vector store đơn giản, chạy local (ví dụ LanceDB, Chroma hoặc SQLite + sqlite-vec). Model embedding chốt sau (xem D11).

- [ ] Chốt

### D6: Chiến lược chunk `P1`

Đề xuất mặc định. Nên **giữ cố định giữa before và after**.

1. Tách theo heading, **gộp** section con quá nhỏ với anh em cùng cấp, **cắt** section quá lớn theo đoạn văn. Không bao giờ cắt giữa bảng, list hay code block.
2. **Prepend breadcrumb** vào mỗi chunk: `[Spec-A > 3 Braking > 3.2 ABS > 3.2.4 Parameters]`.
3. **Parent–child:** retrieve bằng chunk nhỏ, đưa cho LLM cả section note cha.
4. **Bảng parameter/signal:** giữ nguyên bảng. Có thể index thêm từng dòng, mỗi dòng lặp lại header.
5. **Ref expansion:** khi đã retrieve một section, kéo thêm các section nó refer (1 hop, có giới hạn token).

- [ ] Chốt kích thước chunk sau khi profile

### D7: Chế độ trả lời cần so sánh `P2`

- **RAG** (D5 + D6)
- **Agentic search:** agent tự dùng MCPVault hoặc grep, kết hợp `get_note_outline` và `read_note_lines`.
- **Full-context:** nhét nguyên spec vào context (spec 26k dòng ước chừng vài trăm nghìn token, cần đo lại).

**Đề xuất:** bắt đầu với RAG, thêm agentic search làm baseline thứ hai. Full-context chỉ dùng cho spec nhỏ hoặc để kiểm chứng.

- [ ] Chốt

### D8: Cấu trúc bộ skill improve `P1`

| Lựa chọn                                                              | Ghi chú                                                      |
| ----------------------------------------------------------------------- | ------------------------------------------------------------- |
| A. Một skill lớn`spec-improve`                                      | Dễ bắt đầu, nhưng về sau khó kiểm soát               |
| **B. Nhiều skill nhỏ theo chức năng, dùng chung references** | Mỗi skill có một nhiệm vụ rõ ràng, eval riêng được |

Đề xuất B:

| Skill                 | Nhiệm vụ                                                                            | Có sửa file không    |
| --------------------- | ------------------------------------------------------------------------------------- | ----------------------- |
| `spec-analyze`      | Phát hiện mơ hồ, trùng lặp, mâu thuẫn, thiếu parameter, ref gãy             | Không (chỉ báo cáo) |
| `spec-restructure`  | Sắp xếp lại, áp template theo loại section                                       | Có (diff)              |
| `spec-parameterize` | Rút giá trị cứng trong văn xuôi ra bảng parameter                              | Có (diff)              |
| `spec-consistency`  | Đối chiếu section với các section refer tới / được refer, kể cả cross-file | Không (chỉ báo cáo) |
| `spec-diagram`      | Chuyển mô tả ảnh / diagram sang Mermaid                                           | Có (diff)              |

Tài nguyên dùng chung (vị trí cụ thể xem [§6 Cấu trúc repo](#6-cấu-trúc-repo)):

```
knowledge/                # tri thức domain, dùng chung cho mọi skill
├─ style-guide.md         # shall/should, EARS, đơn vị, format bảng
├─ quality-checklist.md   # ISO/IEC/IEEE 29148
├─ templates/             # function, signal table, state machine, DTC, timing…
├─ glossary.md            # ← domain, lớn dần
└─ lessons.md             # ← rule rút ra từ review của expert
.claude/skills/<skill>/SKILL.md   # chỉ chứa quy trình, trỏ tới knowledge/
tools/ (CLI sg)           # get, related, validate, export
```

- [ ] Chốt

### D9: Guardrail cho improve `P0` (gần như bắt buộc)

- **Không bịa giá trị.** Thiếu thông tin thì đánh dấu `> [!todo] ASSUMPTION: …` để expert điền.
- **Không đổi ngữ nghĩa** nếu chưa được expert duyệt. Mọi thay đổi đi dưới dạng **branch + diff** trong repo `data/`.
- **Giữ ID** (D2). Khi tách hoặc gộp section thì ghi `derived_from`.
- **`validate.py` chạy sau mỗi lần sửa:** link gãy, ID trùng, bảng thiếu cột, đơn vị không chuẩn.
- Mỗi note có `status: original | proposed | reviewed | approved` trong frontmatter.

- [ ] Chốt

### D10: Vòng lặp "domain dạy agent" `P1`

1. Agent chạy skill trên section (hoặc cụm section) và đề xuất diff.
2. Expert accept / reject / sửa, **kèm lý do ngắn**.
3. Lý do được chưng cất thành rule trong `lessons.md` hoặc `glossary.md`. Có thể dùng một skill phụ để đề xuất rule, expert duyệt.
4. Mỗi khoảng N section thì chạy lại **bộ eval của skill**: 10–20 section mẫu, mỗi section có bản improve đã được expert duyệt.

"Skill hoàn chỉnh" chính là bộ references đã ổn định và eval đạt ngưỡng.

- [ ] Chốt người review, nhịp review, nơi ghi feedback (commit message / `data/reports/review/`)

### D11: Model và chính sách dữ liệu `P0` ✅ Chính sách đã chốt

**Đã xác nhận:**
- **Claude Code được phép** làm việc trực tiếp trên spec. Đây là agent chính cho việc improve (D13).
- **Không đưa spec vào các dịch vụ LLM cloud khác** (chat app, API bên thứ ba…).

Việc còn lại cho giai đoạn sau:
- Model embedding (D5) và vision model mô tả ảnh (D4): dùng model local, hoặc chỉ dùng kênh đã được phê duyệt. Cần xác nhận trước khi làm Phase 3.
- Embedding cần đa ngôn ngữ nếu hỏi tiếng Việt trên spec tiếng Anh.
- Chatbot và LLM-as-judge (D12): tương tự, chỉ dùng kênh đã được phê duyệt.

- [x] Xác nhận chính sách dữ liệu
- [ ] Xác nhận kênh được phép cho embedding / vision / chatbot (giai đoạn sau)

### D12: Phương pháp đánh giá before/after `P1`

- **Cùng pipeline, cùng chunking, cùng model, cùng prompt.** Chỉ khác data.
- **Bộ câu hỏi vàng** 50–150 câu, viết bằng **tiếng Anh** (cùng ngôn ngữ với spec). Mỗi câu gồm đáp án và ID section nguồn. Nhờ D2, câu hỏi dùng được cho cả hai phiên bản. Phân loại:
  - Tra parameter
  - Hành vi / điều kiện / chuyển trạng thái
  - Cross-section / cross-file
  - Câu **không có** trong spec, để đo khả năng từ chối thay vì bịa
- **Metrics:**
  - Retrieval hit@k / recall@k theo section ID
  - Độ đúng của câu trả lời
  - Faithfulness / citation đúng
  - Tỷ lệ bịa ở các câu không có đáp án
- **Chấm điểm:** LLM-as-judge, sau đó expert chấm lại khoảng 20% mẫu để hiệu chỉnh.
- **UI side-by-side** để demo. Kết luận lấy từ metrics.

- [ ] Chốt nguồn câu hỏi (expert viết / LLM sinh rồi expert duyệt)
- [ ] Chốt ngưỡng "cải thiện đáng kể"

### D13: Công cụ cho agent làm việc trên vault `P0`

| Lựa chọn                                           | Ưu                                                                                                         | Nhược                                                                                                                        |
| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| **A. Claude Code (filesystem) + script + git** | Có sẵn đủ đọc, grep, sửa. grep chính xác với tên signal, parameter, ID. Review bằng git diff/PR | Người dùng cần làm quen terminal/git, hoặc chỉ review qua PR                                                            |
| B. MCPVault                                          | Dùng được từ client không có filesystem (Claude Desktop, chat app). Có chế độ read-only          | Thêm một thành phần phải vận hành. Không có embedding. BM25 quét toàn vault mỗi lần query. Không có review/diff |

So sánh cụ thể:

| Việc                       | MCPVault                               | Claude Code                   |
| --------------------------- | -------------------------------------- | ----------------------------- |
| Đọc note hoặc section    | `read_note`, `read_note_lines`     | `Read` (theo khoảng dòng) |
| Tìm kiếm                  | `search_notes` (BM25)                | `grep`, `rg`              |
| Sửa nội dung, frontmatter | `patch_note`, `update_frontmatter` | `Edit` hoặc script         |
| Xem cây heading            | `get_note_outline`                   | `grep -n '^#'`              |
| Review thay đổi           | Không có                             | git diff, PR                  |

**Đề xuất: A cho giai đoạn improve.** Chỉ thêm B khi có một trong các nhu cầu sau:

- Domain expert muốn hỏi và sửa trực tiếp qua chat, không dùng terminal hay git.
- Agent phải chạy trong client không có filesystem.
- Cần phân quyền read-only cho người chỉ xem.

Vault giữ format tương thích Obsidian nên có thể cắm MCPVault vào bất cứ lúc nào mà không phải đổi gì.

- [ ] Chốt

---

## 5. Bảng ưu tiên tổng hợp

| Ưu tiên | Quyết định                                                                            | Chặn công đoạn        | Giai đoạn                   |
| --------- | ---------------------------------------------------------------------------------------- | ------------------------- | ----------------------------- |
| P0        | D1 tách vault, D2 Section ID, D3 quy ước tên/link, D9 guardrail, D13 công cụ agent | Mọi thứ                 | **Hiện tại**          |
| P0 | ~~D11 chính sách dữ liệu~~: đã chốt | | **Hiện tại** |
| P1        | D8 cấu trúc skill, D10 vòng lặp review                                               | Phase 2 (skills)          | **Hiện tại**          |
| P1        | D4 ảnh (mô tả ảnh, diagram sang Mermaid)                                             | Skill`spec-diagram`     | Hiện tại, có thể làm sau |
| P1        | D5 retrieval, D6 chunk, D12 eval                                                         | Phase 3–4                | Sau                           |
| P2        | D7 chế độ so sánh, D11 (chọn model embedding)                                       | Tối ưu                  | Sau                           |

---

## 6. Cấu trúc repo

**Mô hình hai máy (đã chốt):**
- **Repo public** trên GitHub chỉ chứa code, skill, tri thức chung và tài liệu. Máy phát triển push lên đó.
- **Máy dữ liệu** chỉ pull. Mọi thứ rút ra từ spec nằm trong `data/`: bị repo public ignore, và là **một git repo local riêng**.

Chi tiết vận hành: `docs/next-steps.md` §0.

```
spec-garage/                  # ── REPO PUBLIC ──
├─ README.md
├─ CLAUDE.md                  # quy ước ID/link, guardrail D9, lệnh sg, chính sách dữ liệu
├─ specs.yaml                 # registry: mã spec ↔ file nguồn (data/sources/…)
├─ docs/
│  ├─ spec-pipeline-design.md # tài liệu này
│  └─ next-steps.md           # hướng dẫn triển khai, đặc tả Phase 1
├─ knowledge/                 # TRI THỨC CHUNG (không chứa nội dung domain)
│  ├─ style-guide.md          # shall/should, EARS, đơn vị, format bảng
│  ├─ quality-checklist.md    # ISO/IEC/IEEE 29148
│  └─ templates/              # function, signal-table, state-machine, dtc, timing…
├─ .claude/skills/            # Claude Code tự nhận diện skill ở đây
│  └─ spec-analyze/ spec-restructure/ spec-parameterize/ spec-consistency/ spec-diagram/
├─ tools/                     # Python package, CLI `sg` (chạy: uv run --project tools sg …)
│  ├─ specgarage/
│  │  ├─ cli.py  config.py  parse.py  profile.py  init_data.py
│  │  ├─ (Phase 1) ids.py, build_vault.py, section.py, validate.py, export.py
│  │  └─ data_template/       # khung cho data/ (sg init-data)
│  └─ tests/                  # fixtures/ là spec GIẢ LẬP
├─ build/                     # ignore: bản export
│
└─ data/                      # ── IGNORE bởi repo public; GIT REPO LOCAL trên máy dữ liệu ──
   ├─ README.md  .gitignore
   ├─ sources/<CODE>/         # spec gốc Word→md + ảnh, chỉ đọc
   ├─ vault/                  # OBSIDIAN VAULT = nguồn sự thật sau Phase 1
   │  ├─ .obsidian/           # config chung
   │  ├─ WRN/                 # _manifest.yaml, _toc.md, WRN-0000.md, WRN-0001.md…
   │  └─ attachments/WRN/
   ├─ knowledge/              # TRI THỨC DOMAIN: glossary.md, lessons.md
   ├─ reports/                # profile, analyze, consistency, validate, review
   └─ evals/                  # skills/ (D10), qa/ (D12, giai đoạn sau)
```

### Skill cho agent nằm ở đâu?

- **`.claude/skills/<tên-skill>/SKILL.md`**: nơi Claude Code tự nhận diện skill khi mở repo. File này chỉ chứa **quy trình**: các bước, lệnh CLI `sg` cần gọi, checklist, format output. Có thể kèm `references/` cho hướng dẫn riêng của skill đó.
- **Tri thức mà skill dùng tới:**
  - **Chung** (`knowledge/`, repo public): style guide, checklist, templates.
  - **Domain** (`data/knowledge/`, repo dữ liệu): glossary, lessons.
  - Skill trỏ tới bằng đường dẫn.
- **`CLAUDE.md`** ở gốc repo: luôn được nạp vào mọi phiên. Chứa quy ước chung (ID, link, guardrail D9) và danh sách lệnh `sg`, để skill không phải lặp lại.
- **Quy tắc khi skill tiến hoá:**
  - Thay đổi **quy trình** thì sửa `SKILL.md` trên máy phát triển.
  - Thay đổi **tri thức domain** thì sửa `data/knowledge/` trên máy dữ liệu.
  - Nếu một `SKILL.md` bắt đầu chứa nội dung domain, chuyển nội dung đó sang `data/knowledge/` và chỉ để lại tham chiếu.
- Vì skill theo định dạng `SKILL.md` chuẩn và tri thức nằm riêng, nếu sau này đổi sang agent khác thì chỉ cần trỏ agent đó tới cùng các file này.

### Ghi chú thiết kế
- **`data/sources/` và `data/vault/` tách riêng.** `sources/` giữ nguyên bản Word→md để có thể build lại vault (ví dụ khi sửa parser). Sau tag `baseline-original` thì **chỉ sửa trong `vault/`**, không build lại đè lên.
- **Mọi thao tác máy móc đi qua CLI `sg`**, ví dụ `sg get WRN-0342`, `sg related WRN-0342`, `sg validate`, `sg export WRN`. Skill gọi CLI thay vì tự xử lý file, nên kết quả nhất quán và test được.
- **Mở Obsidian đúng thư mục `data/vault/`**, không mở cả repo, để Obsidian không index `tools/`, `knowledge/`…
- **Ảnh nặng:** nếu repo `data/` có remote nội bộ, cân nhắc dùng Git LFS cho `sources/**/images` và `vault/attachments`.
- **Quy trình Git trong `data/`:**
  - `main` luôn là bản đã được duyệt.
  - Mỗi lần improve là một branch `improve/WRN-0342-<mô tả>`, review bằng `git diff`. Diff gồm note, manifest (nếu đổi cấu trúc) và report.
  - Tag `baseline-original` sau lần build vault đầu tiên được duyệt. Có thể gắn thêm tag theo mốc, ví dụ `improve-round-1`.

---

## 7. Lộ trình implementation

### Giai đoạn hiện tại: improve

#### Phase 0: Profile dữ liệu (1–2 ngày)

Đầu vào là 1–2 spec mẫu kèm folder ảnh. **`sg profile` đã có** (`uv run --project tools sg profile --out reports/profile.txt`). Script đo:

- Phân bố heading H1–H6
- Phân bố độ dài section (token)
- Số lượng bảng và ảnh
- Định dạng hyperlink/anchor thực tế
- Tỷ lệ ref resolve được, số ref cross-file
- ~~Có requirement ID hay không~~: đã xác nhận **không có** (xem D2)
- ~~Anchor/bookmark có giữ được khi convert không~~: đã xác nhận **giữ được**, đã có quy trình verify

Kết quả của phase này dùng để chốt D1 (ngưỡng tách) và D2 (ID).

#### Phase 1: Parser, vault và script hỗ trợ (P1, P2, P6)

- `parse_spec.py`: md sang cây heading, bảng anchor và danh sách ref.
- `build_vault.py`: tách note, gán ID, viết frontmatter, chuyển ref sang wikilink, copy ảnh.
- `export_spec.py`: ghép vault lại thành một file. Test round-trip bằng cách so bản export với bản gốc (diff chỉ được khác ở phần link).
- **Script để skill gọi:**
  - `get_section <id>`: trả về section kèm breadcrumb.
  - `related <id>`: các section nó refer tới và các section refer tới nó, kể cả ở file khác.
  - `validate`: kiểm tra link gãy, ID trùng, bảng thiếu cột, đơn vị không chuẩn.
- **Git tag `baseline-original`** ngay sau lần build vault đầu tiên. Tag này chính là bản **before** cho G3 sau này.
- Mở vault bằng Obsidian để expert kiểm tra kết quả tách.

#### Phase 2: Skills improve (P3)

- Viết `knowledge/` khởi điểm (style guide, checklist, template, glossary) và `CLAUDE.md`.
- Bắt đầu với `spec-analyze`, vì chỉ báo cáo nên rủi ro thấp và giúp hiểu dữ liệu.
- Sau đó đến `spec-restructure` và `spec-parameterize` trên một cụm section thí điểm.
- Vận hành vòng lặp D10: mỗi lần improve là một branch trong repo `data/`, tích luỹ `data/knowledge/lessons.md`, xây bộ eval 10–20 section mẫu cho skill.
- Tuỳ chọn: `spec-diagram` (D4).

### Giai đoạn sau: đánh giá bằng AI đọc hiểu

#### Phase 3: Index + chatbot baseline (P4, P5)

- Chunker (D6), mô tả ảnh (D4), vector store và BM25 (D5).
- Chatbot CLI hoặc UI đơn giản, trả lời có citation theo section ID.
- Xây bộ câu hỏi vàng (D12) và chạy trên bản `baseline-original`.

#### Phase 4: So sánh before/after

- Build `index_after` với cùng pipeline trên bản đã improve.
- Chạy bộ câu hỏi vàng, báo cáo metrics và dựng UI side-by-side.
- Phân tích lỗi: câu nào tốt lên hoặc xấu đi, vì sao, rồi đưa ngược vào skill.

#### Tuỳ chọn: MCPVault (D13)

- Cắm vào vault khi domain expert cần hỏi và sửa qua chat, hoặc cần phân quyền read-only.

---

## 8. Rủi ro và câu hỏi mở

| Rủi ro / câu hỏi                                                   | Ảnh hưởng                             | Hướng xử lý                                                                                         |
| --------------------------------------------------------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| ~~Spec có được đưa lên cloud LLM không?~~ | | **Đã chốt:** Claude Code được phép, dịch vụ LLM cloud khác thì không (D11) |
| ~~Anchor trong md bị mất hoặc sai khi convert từ Word~~ | | **Đã xác nhận giữ được**, đã có quy trình verify |
| AI "improve" mà thay đổi ngữ nghĩa                               | Sai spec, rủi ro an toàn               | Guardrail D9, bắt buộc expert review                                                                  |
| Improve làm tách/gộp section, khiến before/after không khớp 1-1 | Eval sai                                 | `derived_from` (D2) và chấm theo tập section                                                       |
| Đổi chunking giữa hai phiên bản                                  | Không biết cải thiện đến từ đâu | Cố định pipeline (D12)                                                                               |
| BM25 của MCPVault quét toàn bộ vault mỗi lần query              | Chậm khi vault lớn                     | Giai đoạn improve không dùng MCPVault (D13). Nếu dùng về sau thì giới hạn bằng`pathPrefix` |
| Mất bản gốc sau nhiều vòng improve                               | Không còn bản before để so sánh    | Git tag`baseline-original` ngay sau Phase 1                                                           |
| Expert không quen terminal/git                                       | Review chậm, nghẽn vòng lặp D10      | Xem vault bằng Obsidian, dùng giao diện git (VS Code, Obsidian Git) để xem diff. Cân nhắc MCPVault nếu vẫn vướng                |
| Tên note trùng ("Overview", "Requirements")                         | Wikilink sai đích                      | Đặt tên theo ID (D3)                                                                                 |

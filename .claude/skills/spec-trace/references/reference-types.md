# Reference types: recognition and resolution

Details for step 2 and step 3 of `SKILL.md`. All names below are synthetic.

## Contents
- [Tools](#tools)
- [anchor](#anchor)
- [ref-data (Rule 1)](#ref-data-rule-1)
- [spec-text (Rule 2)](#spec-text-rule-2)
- [section-text](#section-text)
- [bare-name](#bare-name)
- [external](#external)
- [Statuses](#statuses)

## Tools

| Command | What it gives you |
|---|---|
| `sg get <ID>` | The text of a section or sub-heading, its file:lines and breadcrumb |
| `sg related <ID>` | Sections the section links to / is linked from, through anchors |
| `sg find "<term>" [--spec NAME] [--kind heading\|table\|text]` | Every hit as *smallest section ID + kind + file:line + snippet*. Whole-word and case-insensitive by default, so `FOO_REQ` does not match `X_FOO_REQ` and `R_FOO` does not match `R_FOO_UP` (`_` is part of a name); `--substring` and `--case-sensitive` change that. Headings sort first. The preamble (table of contents) is skipped unless `--include-preamble`. Exit 1 when there are no hits; then stderr lists the longer names that contain the term, if any. `--json` hits also carry `matches`, the text matched on the line |
| `sg specs --lookup "<name>"` | The registered spec for a code, title or alias (case, spaces, dots and quotes ignored). Exit 1 if not registered |

Prefer `sg find` over raw grep: it returns section IDs you can pass to `sg get`, and skips ID comments and the table of contents.

## anchor

- Recognize: `[text](#slug)`, `[text](#_Ref123)`, `[text](<ID>.md)` or `[text](<ID>.md#slug)`.
- Resolve: `sg related <ID>` lists each target with the anchor it came through (`via #slug`). Match the anchor to the link in the text.
- Links inside the section that point back into the same section do not show up in `related`; read them in place.
- If an anchor is missing from `related`'s output, or the link carries `#broken-ref`, the status is `broken-link`. Do not look for a "probable" target.

## ref-data (Rule 1)

Reference data is data made by **another function block** and only consumed here. The section tells you the name, not the producer, so the producer has to be read from the Input chapter.

1. **Recognize.** Signals:
   - an explicit tag such as `(Reference data Input)` or `reference data`;
   - a signal/operation name used as an input but defined nowhere in the section.
2. **Find the declaration in this spec.** `sg find "Reference data" --spec <CODE> --kind heading` → usually a sub-heading of the Input chapter. Then `sg find "<term>" --spec <CODE> --kind table` and keep the hit that sits inside that sub-heading. Read the row: `| No | Data Name | Source Function |`.
   - **One spec may hold several function blocks**, each with its own Input chapter and its own Reference data table (e.g. chapters 1–10 for one function, chapter 11 onward for another). Use the table of the block the traced section belongs to: compare the top-level headings in the breadcrumbs (they usually share a function-name prefix) or read `data/vault/<CODE>/_toc.md`. If the term is in the table of another block only, record that as an observation and status `ambiguous`.
   - Headings such as "Reference data (Input from GUI Model)" are a separate kind of input; they often just point to another SPEC (Rule 2).
   - Not in the table although tagged as reference data → note it (the tag and the table disagree) and continue with a `bare-name` search.
3. **Map the source to a spec.** `sg specs --lookup "<Source Function>"`.
   - Exit 1 → `unregistered-spec`. Record the Source Function name as written; stop tracing this term.
4. **Find the definition in the target spec.** `sg find "<term>" --spec <TARGET>`. Typical hits:
   - `heading` with the term as its title → the definition. Read it with `sg get <sub-ID>`.
   - `table` in an Output / Transmitting data section → confirms the target spec produces the term.
   - `table` in an interface section (e.g. a GUI IF table mapping the term to another name) → record the other name as an alias seen in the target spec.
   - `text` → usage; read only if there is no heading.
   - **The defining heading may not carry the data name.** Raw received signals are often defined as a row of a receiving-spec table (columns like "reference data output name", byte/bit, value) that points to a sub-heading with a descriptive title (e.g. data `FOO_PUSH` → heading "x.y.z. FOO SW press"). When there is no same-name heading, read the table row, follow it to its sub-heading, and cite both.
5. **Record the nature** of the definition in the target's words, and list what the definition refers to next under "Not followed".

Checks worth recording as observations:
- The target spec has a definition but no Output-table row, or an Output row but no definition.
- Terms the section tags identically (all "Reference data Input") turn out to be of different nature in the target (e.g. some raw signals, some derived operations).
- The target defines the term only under conditions (configuration parameters) that the section does not mention.
- The value type differs from what the section implies (e.g. a step count 0–7 where the section reads it as a 0/1 press).
- Other sections of **this** spec attribute the same term to a different source: run `sg find "<term>" --spec <CODE>` once and scan for `refer to SPEC …` next to the term. Record a conflict with both locations, even if it lies outside the traced section.

## spec-text (Rule 2)

- Recognize: `SPEC"Name"`, `SPEC “Name”`, `refer to SPEC ”Name”`, `(Refer to SPEC "Name")`. Quote characters vary; the lookup ignores them.
- Resolve: `sg specs --lookup "Name"` → `sg find "<term next to the mention>" --spec <CODE>` → `sg get` the definition.
- If the text names only a spec (e.g. "the list of inputs refer to SPEC "Name""), look for the most relevant section with `sg find` on the key words of the sentence and record it; status `resolved` only if you found the section that the sentence clearly means, otherwise `ambiguous`.
- Not registered → `unregistered-spec`.

## section-text

- Recognize: `refer to 3.2`, `(refer to 3.2)`, `see chapter 5`, `Table 1-3`, `Figure 2-1` without a link.
- Resolve a section number: `sg find "3.2." --spec <CODE> --kind heading` (whole-word matching keeps `3.2.1.` out). Compare the heading title with any title quoted in the text.
- Resolve a table/figure number: `sg find "Table 1-3" --spec <CODE> --kind text` finds the caption line; the section holding it is the target. A plain hyphen in the search also matches the non-breaking hyphen Word uses (`1‑3`).
- Several matching headings, or a title mismatch → `ambiguous`.

## bare-name

- Recognize: upper-case identifiers (`DEMO_STATE`), parameter codes (`XX-S01`, `P99`), names used as if the reader knew them.
- Resolve in this order and stop at the first definition:
  1. The current spec's Parameter chapter and Input tables: `sg find "<term>" --spec <CODE> --kind heading --kind table`.
  2. The current spec's text.
  3. Other registered specs: `sg find "<term>"`.
- Found in a Reference data table → switch to the `ref-data` procedure.
- Found only in other specs without a Reference data declaration here → record it and flag "used without being declared as input".

## external

- Recognize: `DWG`, drawing numbers, standards, documents not in the spec set and not named as a SPEC.
- Do not trace. Record the mention. Ask the expert only if the section cannot be understood without it.

## Statuses

| Status | Meaning |
|---|---|
| `resolved` | Definition found and read with `sg get`; the row names its section ID |
| `resolved-fuzzy` | Found only through a name variant; the row names the matched text |
| `ambiguous` | Several candidate definitions, or number and title disagree |
| `not-found` | Nothing matched in the spec(s) searched; searches listed |
| `unregistered-spec` | The source/target spec is not in `data/specs.yaml` |
| `broken-link` | Anchor link that does not resolve |
| `external` | Outside the spec set; not traced |

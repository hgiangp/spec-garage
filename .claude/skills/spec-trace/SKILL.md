---
name: spec-trace
description: Trace every reference in one spec section to where it is actually defined — explicit anchor links, "(Reference data Input)" terms that must be looked up in the spec's Input/Reference data table and followed to the source function's spec, `refer to SPEC "…"` mentions, "refer to 3.2"-style section numbers, and bare signal/parameter names — and write a reference map with a status per term plus questions for the expert. Read-only. Use this whenever a section's inputs, signals, operations or parameters need to be understood before analyzing, checking consistency, restructuring or improving it, when the user asks where a signal or operation comes from, which module or spec sends it, what a term in a section means, or to follow references across spec files (e.g. Warning ↔ LIN COMM), even if they do not say "trace".
---

# spec-trace

Read and report only; never edit the spec. The output is a **reference map**: every term or reference in the section, followed to the place that defines it (same spec or another spec), with a status and questions for the expert. `spec-analyze`, `spec-consistency` and `spec-restructure` use this map as context instead of each re-tracing on its own.

Why a separate skill: references between specs here are **plain text only** (there are no cross-file links), and references inside one spec are partly anchored links and partly implicit. Without a systematic trace, an agent tends to guess what a signal means from its name — exactly the kind of error experts catch in review.

## Input

A section ID (`EWA-0057`, or the ID of a sub-heading). Optionally a list of terms the expert wants to focus on.

All commands below run from the repo root as `uv run --project tools sg …`; the prefix is omitted for brevity.

## Workflow

### 1. Load context

- `data/knowledge/glossary.md` and `data/knowledge/lessons.md`. A lesson (`L-00x`) may already say how to resolve a kind of reference; lessons win over this skill when they disagree.
- `sg specs` — which specs are registered (code, title, aliases).
- `sg get <ID>` — the section itself.

### 2. List the references and classify them

Read the section and list **everything** a reader would have to look up elsewhere to understand it. Give each one a type:

| Type | How to recognize it | Example (synthetic) |
|---|---|---|
| `anchor` | Markdown link `[..](#…)` or `[..](<ID>.md#…)` | `[P-01](#p-01)` |
| `ref-data` | Tagged "(Reference data Input)" / "reference data", **or** a signal/operation name the section uses but does not define | `MODE_SW (Reference data Input)` |
| `spec-text` | Another spec named in prose | `refer to SPEC "Demo Bus"`, `(Refer to SPEC “Demo Bus”)` |
| `section-text` | A section, table or figure number of the same spec, without a link | `refer to 3.2`, `see Table 1-3` |
| `bare-name` | Upper-case parameter/signal name or code like `XX-S01`, with no tag and no link | `DEMO_STATE` |
| `external` | A document outside the spec set (drawing, standard, …) | `refer to DWG` |

Merge all occurrences of the same term into **one** row. Recognition details and edge cases: [references/reference-types.md](references/reference-types.md).

### 3. Resolve each reference

Commands and fallbacks for each type are in the reference file; in short:

- **`anchor`** — `sg related <ID>` shows which section each link points to (through `_anchors.yaml`). Read the target with `sg get`. A link marked `#broken-ref`, or missing from `related`, is `broken-link`. Never guess a target.
- **`ref-data` (Rule 1)** — the data comes from another module, so find out which one before reading anything:
  1. Find the Reference data table in the Input chapter of **this** spec: `sg find "Reference data" --spec <CODE> --kind heading`. A spec can contain several function blocks, each with its own Input chapter; use the table of the block the section belongs to.
  2. Find the term's row: `sg find "<term>" --spec <CODE> --kind table`, and read its Source Function column.
  3. Map the Source Function to a spec: `sg specs --lookup "<Source Function>"`. Exit code 1 means the spec is not registered: status `unregistered-spec`, stop there.
  4. Search the target spec: `sg find "<term>" --spec <TARGET>`. The definition is usually a **heading with the same name**; raw signals are often a row in a receiving-spec table that points to a sub-heading with a descriptive title instead. A row in the target's Output/Transmitting data table confirms that the spec really produces the term. Read the definition with `sg get <sub-ID>`.
  5. Check whether other sections of this spec attribute the term to a different source (`refer to SPEC …` next to it). A conflicting attribution is worth an observation even when it lies outside the traced section.
- **`spec-text` (Rule 2)** — the module is already known: `sg specs --lookup "<name>"`, then `sg find` the accompanying term (if any) in that spec and read its definition. If the text names only the spec, record the spec and the most relevant section you found.
- **`section-text`** — find the heading by number: `sg find "3.2." --spec <CODE> --kind heading`. Several hits, or a number whose heading does not match the quoted title, means `ambiguous`.
- **`bare-name`** — search the current spec first (Input and Parameter tables), then the others: `sg find "<term>"`. If it turns up in a Reference data table, handle it as `ref-data`.
- **`external`** — do not trace. Record it, and ask about it if understanding the section depends on it.

For every definition you find, write its **nature** in one sentence or less, in the target spec's own words: a raw switch signal, a logical operation derived from other signals depending on configuration, a state, a parameter value, a value range… This column is what exposes terms that share a label but differ in nature.

**Depth: one hop into another spec.** When the definition in the target spec refers further (parameters, other sections, raw signals), list those under "Not followed" and stop, unless the user asks you to go deeper.

### 4. When nothing is found

- Try **controlled name variants**: drop/add the suffix " operation" or " SW", `_` ↔ space, `L_`/`R_` prefixes, hyphens. Use `--substring` if needed.
- A match found only through a variant has status `resolved-fuzzy` and names the matched text. It is not a conclusion; put it in the questions for the expert.
- If nothing matches, the status is `not-found`; list the searches you tried.
- **Never** fill in a meaning from the name, from "usual automotive practice" or from memory.

### 5. Write the report

Write `data/reports/trace/<ID>.md` in **English**, using exactly the template in [references/report-template.md](references/report-template.md). Then tell the user the report path and the 3–5 most important findings.

## When to ask the expert

Add a question under "Questions for the expert" when:
- a source spec is not in `specs.yaml` (`unregistered-spec`), even if the name looks close to a registered one — ask whether an alias should be added;
- the term is not found in the target spec, or only through a name variant;
- there are several definitions, or the definition contradicts how the section uses the term;
- the target spec defines the term but does not list it in its Output table, or the other way round;
- you meet a kind of reference these rules do not cover — describe it so the expert can add a rule to `lessons.md`.

## Rules

- **Read-only.** Do not edit the vault or `specs.yaml`. Suggest aliases or new specs as questions.
- **No guessing.** Every `resolved` row must name a target section ID that you actually read with `sg get`.
- **Observe, do not judge.** State what you see (e.g. two groups of terms with the same tag but a different nature) and leave the fix to the expert.
- **Short quotes** (≤ 15 words) to locate things.
- **Keep spec content local.** No web search, WebFetch or other external services; use only `sg` and files in the repo.
- **Output language:** English.

# Report template

Write `data/reports/trace/<ID>.md` with exactly these sections. Empty sections stay, with "None.".

```markdown
---
target: <ID>
title: <section title>
specs_touched: [<CODE>, …]        # every spec you read a definition from
date: YYYY-MM-DD
depth: 1                          # hops into other specs
---

# Trace: <section title> (<ID>)

## Summary
<2–4 sentences: how many references, how many resolved, the most important observation.>

## References
| # | Term (as written) | Type | Occurrences | Declared in (this spec) | Source → spec | Defined in | Nature (target's words) | Status |
|---|---|---|---|---|---|---|---|---|
| 1 | MODE_SW | ref-data | EWX-0102 ×2 | EWX-0007 row 9 | Demo Bus → DMB | DMB-0173 "3.6.2. MODE_SW" | Logical operation derived from raw switch signals per P99 | resolved |
| 2 | P-01 | anchor | EWX-0102 | — | — | EWX-0018 | Configuration parameter: applicable SW type | resolved |
| 3 | Mode info | ref-data | EWX-0102 | EWX-0007 row 2 | TripCfg → (none) | — | — | unregistered-spec |

Column notes:
- *Occurrences*: sub-section IDs where the term appears in the traced section.
- *Declared in*: where this spec declares the term (Reference data row, parameter table…); "—" if not declared.
- *Defined in*: section ID plus a ≤ 15-word quote of the heading or line.

## Observations
- <Patterns seen while tracing, each with both locations: same tag but different nature,
  declaration and definition disagree, missing Output-table row, conditions in the definition
  that the section does not mention… State facts; do not decide which side is right.>

## Not followed
| From | Reference | Why not followed |
|---|---|---|
| DMB-0173 | P99, B999, section 3.3 | Depth limit (1 hop) |

## Missing specs
| Name as written | Where | Terms affected |
|---|---|---|
| TripCfg | EWX-0007 row 2 | Mode info |

## Questions for the expert
1. <One question per point the agent cannot settle: unregistered specs (add an alias?),
   fuzzy matches, ambiguous targets, uncovered reference patterns.>

## Searches
<The `sg find` / `sg specs --lookup` commands that returned nothing or were ambiguous, so the
expert can reproduce them.>
```

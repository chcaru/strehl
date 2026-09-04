# M133 Phase 1 independent blocker derivation

Generated mechanically by `parse_blockers.py` before reading or comparing
`docs/STATUS.md` §2.9.26.

## Rule

The cleared set ranges over `{a,b,c,d}`. An axis is measurable iff its
blocking-code set (its extracted codes minus `e`) is a subset of the
cleared set. Code `e` is retained in the exact extracted code set and in
the per-code census, but is excluded from the blocking-code set because
the source defines it as “scientifically measurable now” and warns that
it does not imply a run has occurred.

Source definition:

```text
docs/proposals/2026-09-sota-scorecard.md:414: This table separates scientific blockers from the baseline's single pre-metric
docs/proposals/2026-09-sota-scorecard.md:415: refusal. Codes are the owner's requested categories: **(a)** missing admissible
docs/proposals/2026-09-sota-scorecard.md:416: detail instrument, **(b)** unresolved native-scale/`cover=scale` geometry,
docs/proposals/2026-09-sota-scorecard.md:417: **(c)** missing or under-powered capture, **(d)** unavailable common-input
docs/proposals/2026-09-sota-scorecard.md:418: Zerene/Helicon output, and **(e)** scientifically measurable now. An **(e)** does not
docs/proposals/2026-09-sota-scorecard.md:419: mean a result has been run.
```

## Extracted rows

| Axis | Source | Exact codes | Blocking codes | Blocker count |
|---|---:|---|---|---:|
| M1 | `docs/proposals/2026-09-sota-scorecard.md:423` | `{a,b,c,d}` | `{a,b,c,d}` | 4 |
| M2 | `docs/proposals/2026-09-sota-scorecard.md:424` | `{a,b,d}` | `{a,b,d}` | 3 |
| M3 | `docs/proposals/2026-09-sota-scorecard.md:425` | `{a,b,d}` | `{a,b,d}` | 3 |
| M4 | `docs/proposals/2026-09-sota-scorecard.md:426` | `{a,b,d}` | `{a,b,d}` | 3 |
| M5 | `docs/proposals/2026-09-sota-scorecard.md:427` | `{a,b,c,d}` | `{a,b,c,d}` | 4 |
| M6 | `docs/proposals/2026-09-sota-scorecard.md:428` | `{a,b,c,d}` | `{a,b,c,d}` | 4 |
| M7 | `docs/proposals/2026-09-sota-scorecard.md:429` | `{b,c,d}` | `{b,c,d}` | 3 |
| M8 | `docs/proposals/2026-09-sota-scorecard.md:430` | `{e}` | `{}` | 0 |
| M9 | `docs/proposals/2026-09-sota-scorecard.md:431` | `{a,b,c}` | `{a,b,c}` | 3 |
| M10 | `docs/proposals/2026-09-sota-scorecard.md:432` | `{b,c}` | `{b,c}` | 2 |
| M11 | `docs/proposals/2026-09-sota-scorecard.md:433` | `{a,b,d}` | `{a,b,d}` | 3 |
| M12 | `docs/proposals/2026-09-sota-scorecard.md:434` | `{e}` | `{}` | 0 |

## Verbatim row audit

**M1 → `{a,b,c,d}` (docs/proposals/2026-09-sota-scorecard.md:423)**

```text
| M1 | **(a)(b)(c)(d)** | No active detail statistic or bar exists; scored matched repeats and comparator arms are also absent. |
```

**M2 → `{a,b,d}` (docs/proposals/2026-09-sota-scorecard.md:424)**

```text
| M2 | **(a)(b)(d)** | Residual noise can be computed diagnostically, but the registered matched-information verdict cannot. |
```

**M3 → `{a,b,d}` (docs/proposals/2026-09-sota-scorecard.md:425)**

```text
| M3 | **(a)(b)(d)** | Artifact counts without a licensed detail/matched-presentation arm cannot support the competitive claim. |
```

**M4 → `{a,b,d}` (docs/proposals/2026-09-sota-scorecard.md:426)**

```text
| M4 | **(a)(b)(d)** | Flatness is computable diagnostically, but its detail-preserving comparator verdict is blocked. |
```

**M5 → `{a,b,c,d}` (docs/proposals/2026-09-sota-scorecard.md:427)**

```text
| M5 | **(a)(b)(c)(d)** | No scored dense/sparse repeat unit exists, and failure coverage needs a licensed detail test. |
```

**M6 → `{a,b,c,d}` (docs/proposals/2026-09-sota-scorecard.md:428)**

```text
| M6 | **(a)(b)(c)(d)** | The rail census is executable, but the registered capture set has fewer than 10,000 recoverable samples and the full axis includes detail retention and comparators. |
```

**M7 → `{b,c,d}` (docs/proposals/2026-09-sota-scorecard.md:429)**

```text
| M7 | **(b)(c)(d)** | No traceable colour target exists. |
```

**M8 → `{e}` (docs/proposals/2026-09-sota-scorecard.md:430)**

```text
| M8 | **(e)** | The v1.4 source-hull invariant needs neither detail nor a comparator and may use the development-only flat slide. Its checker still must be commissioned before a result is admitted. |
```

**M9 → `{a,b,c}` (docs/proposals/2026-09-sota-scorecard.md:431)**

```text
| M9 | **(a)(b)(c)** | Repeat calibration captures are absent and the shipping product emits no admissible acuity/variance certificate. |
```

**M10 → `{b,c}` (docs/proposals/2026-09-sota-scorecard.md:432)**

```text
| M10 | **(b)(c)** | No scored geometric-truth capture or compatible depth product exists. The tilted slide is development-only. |
```

**M11 → `{a,b,d}` (docs/proposals/2026-09-sota-scorecard.md:433)**

```text
| M11 | **(a)(b)(d)** | A quiet host is additionally required; native-decode timing alone is a diagnostic, not the registered competitive verdict. |
```

**M12 → `{e}` (docs/proposals/2026-09-sota-scorecard.md:434)**

```text
| M12 | **(e), scheduled; formal value UNMEASURED** | Hashes and process-tree RSS need no detail, comparator or holdout. Existing out-of-protocol evidence diagnoses fixed-worker determinism as holding and cross-worker scaling invariance as failing, but the registered N/worker matrix still requires the reserved quiet host. |
```

## Per-code census

| Code | Count | Axes |
|---|---:|---|
| `a` | 8 | M1 M2 M3 M4 M5 M6 M9 M11 |
| `b` | 10 | M1 M2 M3 M4 M5 M6 M7 M9 M10 M11 |
| `c` | 6 | M1 M5 M6 M7 M9 M10 |
| `d` | 8 | M1 M2 M3 M4 M5 M6 M7 M11 |
| `e` | 2 | M8 M12 |

## Full brute-force table

| Cleared | Count | Measurable axes |
|---|---:|---|
| `nothing` | 2 | M8 M12 |
| `a` | 2 | M8 M12 |
| `b` | 2 | M8 M12 |
| `c` | 2 | M8 M12 |
| `d` | 2 | M8 M12 |
| `a+b` | 2 | M8 M12 |
| `a+c` | 2 | M8 M12 |
| `a+d` | 2 | M8 M12 |
| `b+c` | 3 | M8 M10 M12 |
| `b+d` | 2 | M8 M12 |
| `c+d` | 2 | M8 M12 |
| `a+b+c` | 4 | M8 M9 M10 M12 |
| `a+b+d` | 6 | M2 M3 M4 M8 M11 M12 |
| `a+c+d` | 2 | M8 M12 |
| `b+c+d` | 4 | M7 M8 M10 M12 |
| `a+b+c+d` | 12 | M1 M2 M3 M4 M5 M6 M7 M8 M9 M10 M11 M12 |

## Internal consistency

- Parsed row count: 12.
- Rows carrying both `e` and a blocker: none.
- Rows carrying no codes: none.

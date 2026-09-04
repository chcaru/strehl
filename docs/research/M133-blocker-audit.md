# M133 blocker audit

## 1. VERDICT

**VERIFIED — YES: the conjunctive blocker result holds. Every count and axis
list actually stated in `docs/STATUS.md` §2.9.26 matches an independent
mechanical parse of the scorecard. The STATUS combination table is incomplete,
not arithmetically wrong: it omits four of the 16 subsets (`c`, `a+b+c`,
`a+c+d`, and `b+c+d`).**

Phase 1 was completed and persisted before §2.9.26 was read:

- parser: `experiments/M133-blocker-audit/parse_blockers.py`
- exact parse and calculations: `experiments/M133-blocker-audit/parsed_rows.json`
- human-readable pre-comparison record:
  `experiments/M133-blocker-audit/phase1-independent-derivation.md`
- Phase 2 comparison: `experiments/M133-blocker-audit/compare_status.py`
- machine-readable comparison:
  `experiments/M133-blocker-audit/status-comparison.json`

The commands used were:

```powershell
python experiments\M133-blocker-audit\parse_blockers.py
python experiments\M133-blocker-audit\compare_status.py
```

**ASSUMED:** this audit tests the scorecard's classification and the arithmetic
induced by it. It does not independently establish that the scorecard assigned
the scientifically correct blockers to each axis, nor that any blocker has
actually been cleared. Within the requested model, a listed blocker is treated
as necessary, and an axis is measurable exactly when all its listed blockers
have been cleared.

## 2. Discrepancy table

The prior combination table claims to follow a computation over “every
combination of removals”:

> **Then the result that explains the last six days.** I computed which axes
> become measurable under every combination of removals:
> (`docs/STATUS.md:2939-2940`)

Its complete displayed table is:

> `| cleared | axes measurable |`
> (`docs/STATUS.md:2942`)
> `| nothing -- today | **2 of 12** (M8, M12) |`
> (`docs/STATUS.md:2944`)
> `| any **one** of a, b, d | **2** |`
> (`docs/STATUS.md:2945`)
> ``| any **two** except `b+c` | **2** |``
> (`docs/STATUS.md:2946`)
> ``| `b+c` | **3** (adds M10) |``
> (`docs/STATUS.md:2947`)
> ``| **`a+b+d`** | **6** (adds M2 M3 M4 M11) |``
> (`docs/STATUS.md:2948`)
> ``| **`a+b+c+d`** | **12** |``
> (`docs/STATUS.md:2949`)

**VERIFIED:** no stated numeric or axis-list cell differs. The only
discrepancies are completeness omissions:

| Cell/subset | Prior table | Independent result | Assessment |
|---|---|---|---|
| `c` | Not displayed; the singleton row names only `a, b, d` (`docs/STATUS.md:2945`) | **2:** M8 M12 | Coverage omission; no arithmetic contradiction |
| `a+b+c` | Not displayed in the complete six-row table (`docs/STATUS.md:2942-2949`) | **4:** M8 M9 M10 M12 | Coverage omission; roadmap-relevant intermediate state |
| `a+c+d` | Not displayed in the complete six-row table (`docs/STATUS.md:2942-2949`) | **2:** M8 M12 | Coverage omission; no arithmetic contradiction |
| `b+c+d` | Not displayed in the complete six-row table (`docs/STATUS.md:2942-2949`) | **4:** M7 M8 M10 M12 | Coverage omission; roadmap-relevant intermediate state |

## 3. Independent derivation

### 3.1 Rule and treatment of `(e)`

The source defines the codes verbatim:

> This table separates scientific blockers from the baseline's single
> pre-metric
> refusal. Codes are the owner's requested categories: **(a)** missing
> admissible
> detail instrument, **(b)** unresolved native-scale/`cover=scale` geometry,
> **(c)** missing or under-powered capture, **(d)** unavailable common-input
> Zerene/Helicon output, and **(e)** scientifically measurable now. An **(e)**
> does not
> mean a result has been run.
> (`docs/proposals/2026-09-sota-scorecard.md:414-419`)

**DERIVED rule:** let `B(axis)` be the extracted codes intersected with
`{a,b,c,d}`. For a cleared subset `S`, an axis is measurable iff
`B(axis) ⊆ S`.

**VERIFIED treatment of `(e)`:** `(e)` remains in the exact extracted code set
and in the per-code census, but it is not a blocker. It means “scientifically
measurable now,” while the source expressly says that it does not mean a run
has occurred (`docs/proposals/2026-09-sota-scorecard.md:418-419`). Therefore M8
and M12 have empty blocker sets for this calculation; calling them measurable
does not call them already measured.

### 3.2 Mechanical parse of all 12 rows

| Axis | Verbatim Class cell and source | Exact codes | Blocking codes | Blocker count |
|---|---|---|---|---:|
| M1 | `**(a)(b)(c)(d)**` (`docs/proposals/2026-09-sota-scorecard.md:423`) | `{a,b,c,d}` | `{a,b,c,d}` | 4 |
| M2 | `**(a)(b)(d)**` (`docs/proposals/2026-09-sota-scorecard.md:424`) | `{a,b,d}` | `{a,b,d}` | 3 |
| M3 | `**(a)(b)(d)**` (`docs/proposals/2026-09-sota-scorecard.md:425`) | `{a,b,d}` | `{a,b,d}` | 3 |
| M4 | `**(a)(b)(d)**` (`docs/proposals/2026-09-sota-scorecard.md:426`) | `{a,b,d}` | `{a,b,d}` | 3 |
| M5 | `**(a)(b)(c)(d)**` (`docs/proposals/2026-09-sota-scorecard.md:427`) | `{a,b,c,d}` | `{a,b,c,d}` | 4 |
| M6 | `**(a)(b)(c)(d)**` (`docs/proposals/2026-09-sota-scorecard.md:428`) | `{a,b,c,d}` | `{a,b,c,d}` | 4 |
| M7 | `**(b)(c)(d)**` (`docs/proposals/2026-09-sota-scorecard.md:429`) | `{b,c,d}` | `{b,c,d}` | 3 |
| M8 | `**(e)**` (`docs/proposals/2026-09-sota-scorecard.md:430`) | `{e}` | `{}` | 0 |
| M9 | `**(a)(b)(c)**` (`docs/proposals/2026-09-sota-scorecard.md:431`) | `{a,b,c}` | `{a,b,c}` | 3 |
| M10 | `**(b)(c)**` (`docs/proposals/2026-09-sota-scorecard.md:432`) | `{b,c}` | `{b,c}` | 2 |
| M11 | `**(a)(b)(d)**` (`docs/proposals/2026-09-sota-scorecard.md:433`) | `{a,b,d}` | `{a,b,d}` | 3 |
| M12 | `**(e), scheduled; formal value UNMEASURED**` (`docs/proposals/2026-09-sota-scorecard.md:434`) | `{e}` | `{}` | 0 |

The parser scopes itself between the `### 3.1` and `### 3.2` headings, matches
only `M1` through `M12` table rows, and fails unless it obtains exactly the
ordered tuple M1 through M12. It extracts parenthesized codes from the Class
cell rather than inferring them from prose.

For direct audit, four verbatim source lines beside their extracted sets are:

**M1 → `{a,b,c,d}`**

> `| M1 | **(a)(b)(c)(d)** | No active detail statistic or bar exists; scored matched repeats and comparator arms are also absent. |`
> (`docs/proposals/2026-09-sota-scorecard.md:423`)

**M8 → `{e}`**

> `| M8 | **(e)** | The v1.4 source-hull invariant needs neither detail nor a comparator and may use the development-only flat slide. Its checker still must be commissioned before a result is admitted. |`
> (`docs/proposals/2026-09-sota-scorecard.md:430`)

**M10 → `{b,c}`**

> `| M10 | **(b)(c)** | No scored geometric-truth capture or compatible depth product exists. The tilted slide is development-only. |`
> (`docs/proposals/2026-09-sota-scorecard.md:432`)

**M12 → `{e}`**

> `| M12 | **(e), scheduled; formal value UNMEASURED** | Hashes and process-tree RSS need no detail, comparator or holdout. Existing out-of-protocol evidence diagnoses fixed-worker determinism as holding and cross-worker scaling invariance as failing, but the registered N/worker matrix still requires the reserved quiet host. |`
> (`docs/proposals/2026-09-sota-scorecard.md:434`)

### 3.3 Independently derived per-code table

**DERIVED** from the exact row sets above:

| Code | Blocks/status count | Axes |
|---|---:|---|
| `(a)` | 8 | M1 M2 M3 M4 M5 M6 M9 M11 |
| `(b)` | 10 | M1 M2 M3 M4 M5 M6 M7 M9 M10 M11 |
| `(c)` | 6 | M1 M5 M6 M7 M9 M10 |
| `(d)` | 8 | M1 M2 M3 M4 M5 M6 M7 M11 |
| `(e)` | 2 | M8 M12 |

The prior cells are verbatim:

> `| **(b)** geometry | **10** | M1 M2 M3 M4 M5 M6 M7 M9 M10 M11 |`
> (`docs/STATUS.md:2931`)
> `| **(a)** detail instrument | 8 | M1 M2 M3 M4 M5 M6 M9 M11 |`
> (`docs/STATUS.md:2932`)
> `| **(d)** comparator | 8 | M1 M2 M3 M4 M5 M6 M7 M11 |`
> (`docs/STATUS.md:2933`)
> `| **(c)** capture | 6 | M1 M5 M6 M7 M9 M10 |`
> (`docs/STATUS.md:2934`)
> `| **(e)** measurable now | 2 | M8, M12 |`
> (`docs/STATUS.md:2935`)

**VERIFIED cell-by-cell comparison:** all five counts and all five ordered axis
lists match.

### 3.4 Full 16-subset brute-force table

**DERIVED** by enumerating every subset of `{a,b,c,d}` and applying
`B(axis) ⊆ S`:

| Cleared subset | Measurable count | Specific axes |
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

Expanded cell-by-cell against every subset represented by the compressed prior
table:

| Subset represented in STATUS | Prior value | Independent value | Result |
|---|---|---|---|
| `nothing` | 2, M8 M12 (`docs/STATUS.md:2944`) | 2, M8 M12 | match |
| `a` | 2 (`docs/STATUS.md:2945`) | 2, M8 M12 | count match |
| `b` | 2 (`docs/STATUS.md:2945`) | 2, M8 M12 | count match |
| `d` | 2 (`docs/STATUS.md:2945`) | 2, M8 M12 | count match |
| `a+b` | 2 (`docs/STATUS.md:2946`) | 2, M8 M12 | count match |
| `a+c` | 2 (`docs/STATUS.md:2946`) | 2, M8 M12 | count match |
| `a+d` | 2 (`docs/STATUS.md:2946`) | 2, M8 M12 | count match |
| `b+c` | 3, adds M10 (`docs/STATUS.md:2947`) | 3, adds M10 | match |
| `b+d` | 2 (`docs/STATUS.md:2946`) | 2, M8 M12 | count match |
| `c+d` | 2 (`docs/STATUS.md:2946`) | 2, M8 M12 | count match |
| `a+b+d` | 6, adds M2 M3 M4 M11 (`docs/STATUS.md:2948`) | 6, adds M2 M3 M4 M11 | match |
| `a+b+c+d` | 12 (`docs/STATUS.md:2949`) | 12, all axes | count match |

The other four subsets are the completeness discrepancies listed in §2.

## 4. Q5–Q8

### Q5 — Is `b+c` really special?

**VERIFIED — yes, among two-blocker subsets.** Every pair except `b+c` leaves
only M8 and M12 measurable; `b+c` also admits M10, for 3 total.

M10's exact source row is:

> `| M10 | **(b)(c)** | No scored geometric-truth capture or compatible depth product exists. The tilted slide is development-only. |`
> (`docs/proposals/2026-09-sota-scorecard.md:432`)

No other blocked row has a blocker set contained in a two-code subset. The
prior cell says exactly:

> ``| `b+c` | **3** (adds M10) |``
> (`docs/STATUS.md:2947`)

### Q6 — Is the `a+b+d` → 6 step real?

**VERIFIED — yes.** It adds exactly M2, M3, M4, and M11 to M8 and M12.
The four added rows are verbatim:

> `| M2 | **(a)(b)(d)** | Residual noise can be computed diagnostically, but the registered matched-information verdict cannot. |`
> (`docs/proposals/2026-09-sota-scorecard.md:424`)
> `| M3 | **(a)(b)(d)** | Artifact counts without a licensed detail/matched-presentation arm cannot support the competitive claim. |`
> (`docs/proposals/2026-09-sota-scorecard.md:425`)
> `| M4 | **(a)(b)(d)** | Flatness is computable diagnostically, but its detail-preserving comparator verdict is blocked. |`
> (`docs/proposals/2026-09-sota-scorecard.md:426`)
> `| M11 | **(a)(b)(d)** | A quiet host is additionally required; native-decode timing alone is a diagnostic, not the registered competitive verdict. |`
> (`docs/proposals/2026-09-sota-scorecard.md:433`)

The prior cell is identical:

> ``| **`a+b+d`** | **6** (adds M2 M3 M4 M11) |``
> (`docs/STATUS.md:2948`)

### Q7 — Sensitivity

**VERIFIED blocker counts:** M1=4, M2=3, M3=3, M4=3, M5=4, M6=4, M7=3,
M8=0, M9=3, M10=2, M11=3, M12=0. These counts come directly from the
verbatim Class cells at
`docs/proposals/2026-09-sota-scorecard.md:423-434`.

**VERIFIED:** no blocked axis carries exactly one blocker. M8 and M12 carry
zero blockers because their exact Class cells are `(e)` only
(`docs/proposals/2026-09-sota-scorecard.md:430,434`). Among the axes that are
not already scientifically measurable, **M10 is uniquely closest**, with two
blockers, exactly `(b)(c)` (`docs/proposals/2026-09-sota-scorecard.md:432`).
Therefore no single blocker clearance unlocks a currently blocked axis.

This agrees with the prior headline:

> **The blockers are conjunctive. No single fix unlocks a single axis.**
> (`docs/STATUS.md:2951`)

### Q8 — Is the scorecard table internally consistent?

**VERIFIED — yes, for code structure.**

- It contains exactly 12 data rows, the contiguous M1–M12 rows at
  `docs/proposals/2026-09-sota-scorecard.md:423-434`.
- No row carries both `(e)` and any of `(a)`–`(d)`. The only `(e)` rows are M8
  and M12, whose verbatim Class cells are `(e)` and
  `(e), scheduled; formal value UNMEASURED`
  (`docs/proposals/2026-09-sota-scorecard.md:430,434`).
- No row carries no codes; every Class cell at
  `docs/proposals/2026-09-sota-scorecard.md:423-434` contains at least one of
  `(a)`–`(e)`.
- No malformed, duplicate, or unknown single-letter code was found by the
  parser.

## 5. Consequences for the roadmap

The prior roadmap maps the three actions as:

> ``1. **`(b)` -- build crop-early.** Pure software, no capture, no purchase.``
> (`docs/STATUS.md:2962`)
> ``2. **`(d)` -- obtain common-input Zerene or Helicon output.**``
> (`docs/STATUS.md:2970`)
> ``3. **`(a)`+`(c)` -- shoot one capture session.**``
> (`docs/STATUS.md:2983`)

**VERIFIED endpoint consequence:** unchanged. All three actions together clear
`a+b+c+d` and make all 12 axes measurable. No one action alone moves the
2-of-12 count.

**DERIVED sequencing consequence from the four omitted cells:** if the ordering
objective is earliest movement in measurable-axis count, buying `(d)` should
be last:

| Actions completed | Cleared set | Measurable axes |
|---|---|---|
| crop-early only | `b` | 2: M8 M12 |
| Zerene only | `d` | 2: M8 M12 |
| capture only | `a+c` | 2: M8 M12 |
| crop-early + Zerene | `b+d` | 2: M8 M12 |
| crop-early + capture | `a+b+c` | **4: M8 M9 M10 M12** |
| Zerene + capture | `a+c+d` | 2: M8 M12 |
| all three | `a+b+c+d` | 12: all axes |

Thus the scorecard arithmetic favors completing **crop-early and the capture
session before buying Zerene** if interim scoreboard movement is the goal; it
does not distinguish whether crop-early or capture comes first, because each
first step remains at 2. This is a sequencing refinement, not a change to the
final “all three are required” roadmap. Non-scorecard considerations such as
cost, owner availability, or an operational dependency could still justify
the recorded `b → d → (a+c)` order; this audit did not assume or verify any
such dependency.

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

## 6. Follow-up: are M8 and M12 actually scored?

**Q3 — VERIFIED: 1 of 12 axes has a produced-and-read score today: M8 is
scored FAIL; M12 remains formally UNMEASURED.**

This follow-up read existing files only. It did not invoke the M12 harness,
run a stacker, or start a benchmark. The retained artifact parser is
`experiments/M133-blocker-audit/audit_score_state.py`; its output is
`experiments/M133-blocker-audit/followup-artifact-audit.json`. Documentation
phrase checks use whitespace-collapsed regular expressions so wrapped prose is
not missed.

### Q1 — M8 actual result state

#### Axis, readiness row, and bar

The scorecard's at-a-glance row is:

> ``| M8 | Invented values / source-hull certificate | Per-frame resampler-hull violations and final-output source-hull violations: each exactly `0.0000%`. |``
> (`docs/proposals/2026-09-sota-scorecard.md:399`)

The full §3.1 readiness row is:

> `| M8 | **(e)** | The v1.4 source-hull invariant needs neither detail nor a comparator and may use the development-only flat slide. Its checker still must be commissioned before a result is admitted. |`
> (`docs/proposals/2026-09-sota-scorecard.md:430`)

The detailed success clause says:

> **Success.** **PROPOSAL BAR (M8-O):** final-output violation fraction exactly
> `0.0000%`. **SCORECARD ADDITION (M8-R):** resampler violation fraction exactly
> `0.0000%`; the crop/reference identity arm also has zero violations. A missing
> pre-clamp trace is `UNMEASURED`, not a pass.
> (`docs/proposals/2026-09-sota-scorecard.md:863-866`)

#### Has a score been produced and read?

**VERIFIED — yes. M8 has a produced-and-read score, and it is FAIL.** The M8
report identifies itself as the scorecard reading:

> **Verdict: FAIL; no blocker.**
> (`docs/research/M8-overshoot.md:3`)
> I measured scorecard v1.7's M8 text
> (`docs/research/M8-overshoot.md:10`)

The checker was commissioned before the reading:

> Commissioning passed both directions: fractional Catmull hard step
> `28/252` violations, 14 each sign, extrema `-0.0625/+0.0625`; copy null
> `0/252`, exact-copy error `0`; convex bilinear null `0/300`.
> (`docs/research/M8-overshoot.md:37-40`)

The actual score is nonzero on both mandatory censuses:

> Aggregate M8-R is `63,191,176 / 6,131,678,976` (1.030569%);
> aggregate M8-O is `983,648 / 74,173,536` (1.326144%)
> (`docs/research/M8-overshoot.md:55-57`)
> M8-R is decisively nonzero on every arm, so the registered source-hull
> invariant fails.
> (`docs/research/M8-overshoot.md:61-62`)

The orchestrator then explicitly read it:

> **M8 is measured. It reads FAIL.** After eleven closed gates and nine
> refusals, an axis finally carries a value instead of a reason it cannot be
> read.
> (`docs/STATUS.md:1994-1995`)
> `docs/research/M8-overshoot.md`, commit `76b3d9cc`. Every number above was
> checked against that file before this section was written.
> (`docs/STATUS.md:2004-2005`)

**VERIFIED stale text:** the scorecard's front matter still says “No v1.7 score
output has been read” and “0 measured / 12 unmeasured”
(`docs/proposals/2026-09-sota-scorecard.md:7-14`), and its standing table still
calls M8 “ready but unread”
(`docs/proposals/2026-09-sota-scorecard.md:1152`). Those statements predate and
conflict with the later committed result and explicit STATUS read above. This
lane reports the conflict and does not edit either governing document.

#### What stands in the way?

**VERIFIED:** nothing remains to obtain an M8 score; it already exists. What
remains is product work before M8 can pass. The attribution report separates
two failures:

> Changing only the warp-map resampler line, with every placement fixed, gives
> bilinear M8-R **`0/6,131,678,976 = 0.000000%`**
> (`docs/research/M8-overshoot.md:117-119`)
> Therefore all 63,191,176 accepted M8-R violations are attributable to the
> **Catmull-Rom gather**
> (`docs/research/M8-overshoot.md:121-123`)
> M8-O is a separate downstream failure, not the source of M8-R. Bilinear still
> reads `980,097/74,173,536 = 1.321357%`
> (`docs/research/M8-overshoot.md:128-131`)

Thus an M8 pass needs both a resampler-side repair and the independently
observed downstream M8-O repair, followed by a rerun of the already
commissioned instrument. No compute estimate is needed to get a first M8
score; that milestone is complete.

#### Is `M8COMP` the scorecard M8?

**VERIFIED — no, not as a score authority.** It uses the M8-O instrument family
for a foreign/comparative question, but its own governance says:

> Any result is a **candidate comparative reading**, not an M8 score. The
> scorecard currently owns M8 as a strehl self-check and is read-only to this
> lane.
> (`docs/research/M8-COMPARATIVE.md:133-136`)

Its retained and controlled foreign arms did not produce a score:

> **Final verdict: exact comparative M8-O and its requested magnitude
> distributions are UNMEASURED**
> (`docs/research/M8-COMPARATIVE.md:3-6`)
> **Final controlled `focus-stack` result: `UNMEASURED`.**
> (`docs/research/M8-COMPARATIVE.md:603`)

The report itself distinguishes that work from the existing score:

> The only commissioned strehl reading remains the already-published,
> **non-common-stack** development result; it was not repeated
> (`docs/research/M8-COMPARATIVE.md:225-227`)

Therefore the pristine-upstream `focus-stack` work was a provenance and
comparative-contract lane related to M8's statistic, not a replacement for or
the source of the scorecard M8 FAIL.

### Q2 — M12 actual result state

#### Axis, readiness row, and bar

The scorecard's at-a-glance row is:

> ``| M12 | Memory, determinism, and scaling invariance | Warm peak process-tree memory `<=6 GiB`; 299/33-frame peak ratio `<=1.10`; every fixed-worker repeat is byte-identical and the outputs at 1/2/4/8/16 workers are mutually byte-identical while 16 workers passes M11; N-mod-4 per-frame spread `<=2%`. |``
> (`docs/proposals/2026-09-sota-scorecard.md:403`)

The full §3.1 readiness row, including the requested context, is:

> `| M12 | **(e), scheduled; formal value UNMEASURED** | Hashes and process-tree RSS need no detail, comparator or holdout. Existing out-of-protocol evidence diagnoses fixed-worker determinism as holding and cross-worker scaling invariance as failing, but the registered N/worker matrix still requires the reserved quiet host. |`
> (`docs/proposals/2026-09-sota-scorecard.md:434`)
> Thus M8 is the only complete quality axis ready now. M12 is scientifically
> unblocked, but its complete registered run is deliberately deferred to a
> quiet host.
> (`docs/proposals/2026-09-sota-scorecard.md:436-437`)

The detailed bar is:

> **Success.** The proposal bars are warm peak `<=6 GiB` and byte invariance.
> The **SCORECARD ADDITIONS** that make “flat” numeric are
> `peak_N299/peak_N33<=1.10` and N-mod-4 per-frame spread `<=2%`. M12-D requires
> exactly one distinct hash in every fixed-worker six-run cell. M12-S requires
> exactly one distinct hash across all five worker counts at every N, and the
> 16-worker output must simultaneously pass M11.
> (`docs/proposals/2026-09-sota-scorecard.md:1064-1069`)

#### Has a score been produced and read?

**VERIFIED — no formal M12 score exists.** The only run manifest labels the
campaign:

> `"registration_status": "operator-authorized-diagnostic",`
> (`experiments/m12-scorecard/out/RUN-MANIFEST.operator-diagnostic.json:3`)
> `"scope": "Native-ARW shipping-path candidate measured at the owner's explicit 2026-09-03T19:14:34-07:00 instruction. Diagnostic, not a registrar-approved formal scorecard reading, because experiments/SCORECARD/RUN-MANIFEST.json is absent.",`
> (`experiments/m12-scorecard/out/RUN-MANIFEST.operator-diagnostic.json:4`)

The post-run audit agrees:

> `"classification": "operator-authorized diagnostic; not a registrar-approved formal M12 reading",`
> (`experiments/m12-scorecard/out/campaign-16bc3e3d/audit.json:2`)

No current documentation reads that campaign as a formal M12 result. The last
explicit registrar ruling remains:

> - **M12-D, fixed-worker determinism** -- diagnostic PASS, and it holds.
> - **M12-S, cross-worker scaling invariance** -- diagnostic FAIL.
> - Both formal sub-bars remain **UNMEASURED**. This is therefore still not the
>   first scorecard reading.
> (`docs/STATUS.md:1501-1504`)

#### How much of the matrix has data?

**VERIFIED — all of it.** The current artifacts refute the description of
`campaign-16bc3e3d` as partial. The registered design is:

> Run native ARWs at N=33/105/299 with workers 1/2/4/8/16, one warm-up then
> six alternating-order scored repetitions per cell
> (`docs/proposals/2026-09-sota-scorecard.md:1097-1099`)
> Run N=96/97/98/99 at 16 workers with the same warm-up/six-sweep timing
> protocol for the modulo bar.
> (`docs/proposals/2026-09-sota-scorecard.md:1100-1101`)

Mechanical parsing of all 133 JSONL records found:

| Matrix component | Expected | Present | Missing |
|---|---:|---:|---:|
| N=33/105/299 × 5-worker warm-ups | 15 | 15 | 0 |
| N=33/105/299 × 5 workers × 6 scored repetitions | 90 | 90 | 0 |
| N=96/97/98/99 modulo warm-ups | 4 | 4 | 0 |
| N=96/97/98/99 × 6 scored repetitions | 24 | 24 | 0 |
| **Total** | **133** | **133 valid** | **0** |

The retained audit records `"record_count": 133` and
`"invalid_render_count": 0`
(`experiments/m12-scorecard/out/campaign-16bc3e3d/audit.json:446-498`).
The independent parser reproduces the 133 expected/133 present breakdown with
empty missing lists
(`experiments/M133-blocker-audit/followup-artifact-audit.json:125-160`).
The first record is a diagnostic N=33/W1 warm-up
(`experiments/m12-scorecard/out/campaign-16bc3e3d/records.jsonl:1`); the final
record is the sixth diagnostic N=96/W16 modulo repetition
(`experiments/m12-scorecard/out/campaign-16bc3e3d/records.jsonl:133`).

So the absent `out/RUN-MANIFEST.json` correctly means **no formal score
closed**, but it does **not** mean the invocation matrix failed to run. A full
diagnostic matrix ran.

The current STATUS recovery note is therefore stale on data coverage:

> M12's tree is not empty — it holds a 50 KB commissioned harness, a planted/
> restored build pair, a preflight, and a partial campaign `16bc3e3d` with a
> 546 KB `records.jsonl`. What is missing is the closing manifest, so **the
> scored matrix never ran**.
> (`docs/STATUS.md:3177-3180`)

The missing-manifest conclusion remains correct for formal admission; “partial”
and “never ran” do not match the current 133/133 diagnostic artifacts.

#### What do the diagnostic data say?

**VERIFIED diagnostic-only results:**

- M12-D passes: all 15 fixed-worker cells contain six runs and one hash; the
  artifact's aggregate is `"pass": true`
  (`experiments/m12-scorecard/out/campaign-16bc3e3d/audit.json:54-177`).
- M12-S fails at every N: N=33, 105, and 299 each produced five distinct
  cross-worker hashes
  (`experiments/m12-scorecard/out/campaign-16bc3e3d/audit.json:179-240`).
- Sampled process-tree private commit reached `35.53202438354492 GiB`, and the
  maximum 299/33 envelope was `1.4489937322064963`; both exceed the 6-GiB and
  1.10 bars
  (`experiments/m12-scorecard/out/campaign-16bc3e3d/audit.json:256-264`).
- The observed modulo spread was `0.017487048718701974`, below 2%, but its
  scorecard verdict is `"UNMEASURED"`
  (`experiments/m12-scorecard/out/campaign-16bc3e3d/audit.json:424-427`).

These values strongly predict a formal M12 FAIL, but the artifacts expressly
deny them formal score status.

#### What specifically is missing?

1. **A pre-output formal scorecard freeze.** The contract says:

   > Before any stacker runs, commit these files under
   > `experiments/SCORECARD/`
   > (`docs/proposals/2026-09-sota-scorecard.md:132-134`)
   > `RUN-MANIFEST.json`: hardware, OS, power plan, program hashes, licences,
   > versions, complete settings, worker count, cache state, and output contract
   > (`docs/proposals/2026-09-sota-scorecard.md:139-140`)

   The current filesystem has neither
   `experiments/m12-scorecard/out/RUN-MANIFEST.json` nor
   `experiments/SCORECARD/RUN-MANIFEST.json`; it has only the explicitly
   diagnostic manifest
   (`experiments/M133-blocker-audit/followup-artifact-audit.json:166-169`).

2. **The reserved quiet host and its load evidence.** The campaign audit says
   `"load_gate_applied": false`, `"preload_busy_measured": false`, and
   `"verified_load_gated_invocation_count": 0`
   (`experiments/m12-scorecard/out/campaign-16bc3e3d/audit.json:7-18`).

3. **The registered 10-ms memory cadence.** The scorecard requires process-tree
   sampling every 10 ms (`docs/proposals/2026-09-sota-scorecard.md:1100`), but
   the audit records `"sampling_protocol_exactly_achieved": false`, up to
   `6910` missed intervals, and a worst gap of `1048.092800017912 ms`
   (`experiments/m12-scorecard/out/campaign-16bc3e3d/audit.json:243-348`).

4. **A new admitted run.** **ASSUMED, conservatively and from the explicit
   freeze-before-output rule:** the diagnostic campaign cannot be relabelled
   after its outputs were read. The formal manifests and load gates must be
   committed first, then the matrix rerun on the quiet host.

The complete diagnostic campaign took `9379.637669` seconds, or 156.3 minutes
(`experiments/m12-scorecard/out/campaign-16bc3e3d/audit.json:445-446`).
The program's retained estimate adds 11.1 minutes for pre-load gating and
grants 210 uninterrupted minutes:

> **210 uninterrupted minutes granted.** M12's own estimate, from a previously
> measured 133-invocation matrix at `156.3` minutes plus `11.1` minutes of
> pre-load gating
> (`docs/STATUS.md:3097-3099`)

**Compute estimate:** about 167.4 minutes measured plus closure/headroom; reserve
the already-authorized 210-minute quiet-host window.

### Q4 — Cheapest path from N scored axes to N+1

**VERIFIED recommendation:** with N=1, the cheapest next score is M12. Do not
buy Zerene to obtain the next score. Wait for a genuinely quiet host, commit
the formal pre-output manifests and load gates, and rerun the 133-invocation
M12 matrix inside the 210-minute reservation.

M8 cannot increase the scored-axis count because it is already scored FAIL.
M12 needs no purchase, no new capture, and no new metric implementation: its
harness and controls are commissioned, and a complete diagnostic rehearsal
already exists. The remaining cost is about 2.8 hours of measured run-plus-gate
time inside the already reserved 3.5-hour exclusive host window, plus formal
evidence closure.

### Could not determine

- **VERIFIED absence / could not determine identity:** the current milestone
  allocation ledger contains no `M8COMP` row
  (`AGENTS.md:844-1103`; mechanical result at
  `experiments/M133-blocker-audit/followup-artifact-audit.json:117-121`).
  Therefore its exact dispatch identity cannot be established from the ledger,
  even though `M8-COMPARATIVE.md` conclusively establishes that its output is
  not the scorecard M8 score.
- **Could not determine:** whether the registrar would accept any fatal M12
  sub-bar from the diagnostic campaign without a rerun. No such admission is
  recorded; the campaign repeatedly labels itself non-formal, so this report
  counts M12 as UNMEASURED and recommends the strict rerun.
- **Could not determine:** the exact duration of the future admitted run. The
  210-minute recommendation is an evidence-based reservation, not a guarantee.

## 7. Are the twelve bars well-formed and achievable?

**SUMMARY — VERIFIED against the written instrument, with achievability
judgments tagged separately below: 0 of 12 axes currently has a bar that is
simultaneously precise, achievable, and backed by a complete commissioned or
concretely plannable checker. The failing set is M1–M12.**

That does **not** mean all twelve scientific objectives are impossible.
**ASSUMED:** the ten precision defects are repairable before outputs. M1 has
no active instrument or bar at all, and M8-O has a demonstrated
representational impossibility under its present 16-bit rail semantics.

The count is conjunctive at the axis level: every mandatory sub-bar must pass
all three tests. This follows the scorecard's own decision rule:

> Every primary metric is a hard gate. No win compensates for a loss.
>
> `UNMEASURED`, an uncommissioned checker, an invalid comparator arm, or an
> under-powered capture blocks a SOTA claim; it is not a pass or a loss.
> (`docs/proposals/2026-09-sota-scorecard.md:86-88`)

This audit read documents and existing artifacts only. It ran no renderer,
stacker, campaign, or benchmark. The retained extractor and rail checker are
`experiments/M133-blocker-audit/audit_bar_cards.py`; their deterministic output
is `experiments/M133-blocker-audit/bar-card-audit.json`. It mechanically
extracts all twelve bars and uses whitespace-collapsed matching for wrapped
prose. The audited scorecard is commit `a0413b73`, SHA-256
`170B37816900AFA08BEB5211F9BB9580762EE79A190AF05181834C9A7BA947F8`
(`experiments/M133-blocker-audit/bar-card-audit.json:2-8`).

Evidence convention: every factual finding in this section is **VERIFIED**
unless explicitly tagged **ASSUMED** or **Could not determine**.

### Per-axis result

| Axis | (i) Precisely stated? | (ii) Achievable in principle? | (iii) Checker state | (iv) What a pass would license |
|---|---|---|---|---|
| M1 | **VERIFIED FAIL.** Bar: “**NO ADMISSIBLE BAR — WITHDRAWN.** `f_licensed` is blind; native `S_25` fails sharpening and tone, while tone-hardened derivatives reverse the optical controls.” (`docs/proposals/2026-09-sota-scorecard.md:392`) | **Could not determine.** There is no quantity or threshold to test. | **VERIFIED FAIL.** The old instrument was defeated and withdrawn; only requirements for a future replacement exist (`docs/proposals/2026-09-sota-scorecard.md:498-578`). | **VERIFIED: nothing today.** The scorecard says no detail, matched-information, comparator-quality, or SOTA claim is licensed (`docs/proposals/2026-09-sota-scorecard.md:559-562`). |
| M2 | **VERIFIED FAIL.** Bar: “Cross-fit efficiency `<=1.10`; 95% upper bound of strehl / quietest qualifying comparator `<=0.950`.” (`docs/proposals/2026-09-sota-scorecard.md:393`) Per-ROI `eta` is defined, but its aggregation and RGB-channel reduction are not. | **ASSUMED YES.** The limits are not exact-zero floors, and the commissioned untouched-mean null read `eta=1.0035`; no physical impossibility was found (`docs/research/SCORECARD-BASELINE.md:44-45`). The unrun commercial comparison remains empirical. | **VERIFIED PARTIAL.** The residual/blur core was commissioned red/green, but the complete matched-information comparator verdict is not executable while M1 is absent (`docs/research/SCORECARD-BASELINE.md:44-45`; `docs/proposals/2026-09-sota-scorecard.md:424`). | **VERIFIED:** near-ideal cross-fit noise and at least a 5% pooled noise advantage over the quietest equally informative qualifying comparator; no standalone detail claim (`docs/proposals/2026-09-sota-scorecard.md:579-619`). |
| M3 | **VERIFIED FAIL.** Bar: “Median excess `<=1%` edge step, p99 `<=5%`; edges above 5% `<=1%` with Wilson upper bound `<=2%`; local source coherence `>=0.90`; no worse than best comparator.” (`docs/proposals/2026-09-sota-scorecard.md:394`) The comparator's singular “paired p99” has no referent, and no percentile convention is frozen. | **ASSUMED YES.** The tolerances are nonzero, source-referenced, and the proposed 6% rim/veil and raw-null controls could in principle bracket them (`docs/proposals/2026-09-sota-scorecard.md:657-665`). | **VERIFIED PLAN ONLY.** The scorecard specifies a plant and null, but states that full-reach sites and the checker remain absent (`docs/proposals/2026-09-sota-scorecard.md:663-665,1147`). | **VERIFIED:** bounded stack-induced narrow rim and broad veil while preserving edge width/coherence, no worse than a qualifying comparator; not general resolution (`docs/proposals/2026-09-sota-scorecard.md:621-665`). |
| M4 | **VERIFIED FAIL.** Bar: “Median flat-patchwork ratio `<=1.00`; sites above `1.25` or ghost ratio above `0.10`: `<=1%`, Wilson upper bound `<=2%`; no worse than best comparator.” (`docs/proposals/2026-09-sota-scorecard.md:395`) `noise_floor` is undefined, and no flat/edge site-mixture denominator is frozen. | **ASSUMED YES.** The fixed-weight mean is explicitly expected to produce at most 1% failures, so no numerical floor makes the target impossible (`docs/proposals/2026-09-sota-scorecard.md:697-701`). | **VERIFIED INCOMPLETE PLAN.** A selector plant and mean null are specified, but no v1.7 site manifest or control run exists, and the undefined denominator prevents a complete implementation (`docs/proposals/2026-09-sota-scorecard.md:697-701,1148`). | **VERIFIED:** a low rate of output-created flat patchwork and secondary-edge ghosts at registered sites, with a qualifying comparator guard (`docs/proposals/2026-09-sota-scorecard.md:667-701`). |
| M5 | **VERIFIED FAIL.** Bar: “`>=99%` of eligible tiles pass `rho_best>=0.90` and focus margin `>=0.05`; Wilson lower bound `>=98%`; longest failed run `<=1%` of sweep.” (`docs/proposals/2026-09-sota-scorecard.md:396`) “source-signal” and the run construction on non-planar tile maps are undefined. | **ASSUMED YES.** Correlation, margin, coverage, and run tolerances are nonzero; no quantisation or noise floor forces failure once eligible truth and a complete focus sweep exist. | **VERIFIED INCOMPLETE PLAN.** Development captures and defect/null controls are named, but the checker is not commissioned and the run statistic is not implementable uniquely (`docs/proposals/2026-09-sota-scorecard.md:709-748,1149`). | **VERIFIED:** at least 99% coverage of input-eligible depth tiles, no long focus hole, retained field of view, and comparator parity; it says nothing about ineligible regions (`docs/proposals/2026-09-sota-scorecard.md:704-748`). |
| M6 | **VERIFIED FAIL.** Bar: “Recoverable high-rail and low-rail clipping each `<=0.10%`; highlight-detail retention `>=0.90`; no worse than best comparator.” (`docs/proposals/2026-09-sota-scorecard.md:397`) The common image is RGB, but recoverability, clipping, and `rho_best` never say per-channel, any-channel, all-channel, or luminance; those choices change both denominator and verdict. | **ASSUMED YES.** The clipping allowance is nonzero, recoverability requires an interior source sample, and 16-bit quantisation does not itself force a sample to either rail. | **VERIFIED PARTIAL.** The rail eligibility census was commissioned red/green, while the full detail/comparator checker remains a plan and the registered capture is under-powered (`docs/research/SCORECARD-BASELINE.md:48`; `docs/proposals/2026-09-sota-scorecard.md:428,750-780`). | **VERIFIED:** recovery of input-recoverable highlights and shadows without erasing their detail, no worse than the qualifying comparator (`docs/proposals/2026-09-sota-scorecard.md:750-780`). |
| M7 | **VERIFIED FAIL.** Bar: “Median DeltaE00 `<=1.0`, p95 `<=2.0`, maximum `<=3.0`, boundary-seam p99 `<=1.0`; ICC/300-DPI conformance `100%`; no worse than best comparator.” (`docs/proposals/2026-09-sota-scorecard.md:398`) The patch population is bounded, but the boundary-seam population, boundary constructor, minimum count, and percentile convention are absent. | **ASSUMED YES.** The DeltaE limits are far from an exact quantisation floor, and an identity colour transform is the proposed passing null (`docs/proposals/2026-09-sota-scorecard.md:814-817`). | **VERIFIED INCOMPLETE PLAN.** Patch computation and colour plants are specified, but no traceable target exists and the seam arm cannot yet be instantiated uniquely (`docs/proposals/2026-09-sota-scorecard.md:789-817,1151`). | **VERIFIED:** traceable patch colour accuracy, bounded focus-boundary colour discontinuity, and deliverable ICC/tag conformance; not general natural-object agreement (`docs/proposals/2026-09-sota-scorecard.md:782-817`). |
| M8 | **VERIFIED PASS on precision.** Bar: “Per-frame resampler-hull violations and final-output source-hull violations: each exactly `0.0000%`.” (`docs/proposals/2026-09-sota-scorecard.md:399`) Population, tolerance, coordinates, and denominator are explicit (`docs/proposals/2026-09-sota-scorecard.md:834-866`). | **VERIFIED FAIL for M8-O as applied.** M8-R can reach zero with bilinear, but 977,684 of 980,097 bilinear M8-O violations are full-rail samples whose lower hull exceeds the maximum representable 16-bit value. No u16 output can pass those coordinates without changing the domain or bar (`experiments/M133-blocker-audit/bar-card-audit.json:1471-1491`). | **VERIFIED COMMISSIONED.** The checker passed Catmull-Rom, explicit high/low plants, copy, and bilinear nulls before the admitted FAIL (`docs/proposals/2026-09-sota-scorecard.md:430,1152`; `experiments/M8-overshoot/results.json:27-66`). | **VERIFIED:** only the internal claim that gathered/final samples remain within independently reconstructed source support. The scorecard explicitly says M8 alone is not SOTA (`docs/proposals/2026-09-sota-scorecard.md:881-887`). |
| M9 | **VERIFIED FAIL.** Bar: “False-certification Wilson upper bound `<=1%`; true-band coverage `>=90%`; nominal 95% interval coverage `93%`–`97%`; variance ratio `0.90`–`1.10`.” (`docs/proposals/2026-09-sota-scorecard.md:400`) Its acuity truth is the nonexistent “future independently commissioned M1 condition”; decile construction is also unfrozen. | **ASSUMED YES after repair.** Calibrated coverage and variance intervals have no exact physical floor, and the proposed all-valid/all-invalid/1.25x controls can exercise both directions (`docs/proposals/2026-09-sota-scorecard.md:928-934`). | **VERIFIED FAIL TODAY.** There is no compatible certificate product or M1 truth from which to build the acuity checker; the variance-channel outline alone is not a complete checker (`docs/research/SCORECARD-BASELINE.md:50-52`; `docs/proposals/2026-09-sota-scorecard.md:908-934`). | **VERIFIED:** a calibrated statement about where/frequency the output is trustworthy and whether its `n_eff`/variance intervals have honest coverage; not image superiority by itself (`docs/proposals/2026-09-sota-scorecard.md:890-934`). |
| M10 | **VERIFIED FAIL.** Bar: “Valid target pixels `>=99%`; rank correlation `>=0.99`; median error `<=0.5` focus step, p95 `<=1.0` step; physical slope error `<=5%`.” (`docs/proposals/2026-09-sota-scorecard.md:401`) “valid” and “layer confusion” are undefined, while required boundary bias is reported without any pass threshold. | **ASSUMED YES.** Error tolerances are nonzero, and the card requires an exact truth map to pass every bar, providing a constructive numerical null (`docs/proposals/2026-09-sota-scorecard.md:971-978`). | **VERIFIED INCOMPLETE PLAN.** Physical and synthetic controls are proposed, but no compatible depth product/checker exists and the missing definitions prevent unique implementation (`docs/research/SCORECARD-BASELINE.md:50-52`; `docs/proposals/2026-09-sota-scorecard.md:948-978`). | **VERIFIED:** coverage, ordering, typical/tail step error, and ruler slope on registered targets. It licenses no bounded boundary-accuracy claim because boundary bias has no gate. |
| M11 | **VERIFIED FAIL.** Bar: “Warm common-input throughput `>=2.00x` fastest quality-qualified comparator; candidate/default baseline ratio `<=2.00`; native-RAW CPU at 16 workers `<=0.15 s/frame`; hybrid `<=0.06 s/frame`; cold `<=warm+20 s`; 100-frame live master `<=10 s` after last shutter.” (`docs/proposals/2026-09-sota-scorecard.md:402`) The live arm gives no capture/replay cadence, permitted pre-last-frame work, or initial state. | **ASSUMED YES.** No physical or numerical floor precludes the timing bars; actual attainment on the frozen host and named comparators is unmeasured. | **VERIFIED INCOMPLETE PLAN.** The end-to-end timer, six sweeps, load gate, sleep plant, async-child plant, and cold reset are planned, but no complete arm is commissioned and the live-input generator is unspecified (`docs/proposals/2026-09-sota-scorecard.md:994-1035,1155`; `docs/research/M-PHASE0-PIPE.md:240-258`). | **VERIFIED:** end-to-end common-input comparator speed plus native product CPU/hybrid/cold/live latency on the frozen host; not a hardware-independent speed claim (`docs/proposals/2026-09-sota-scorecard.md:981-1035`). |
| M12 | **VERIFIED FAIL.** Bar: “Warm peak process-tree memory `<=6 GiB`; 299/33-frame peak ratio `<=1.10`; every fixed-worker repeat is byte-identical and the outputs at 1/2/4/8/16 workers are mutually byte-identical while 16 workers passes M11; N-mod-4 per-frame spread `<=2%`.” (`docs/proposals/2026-09-sota-scorecard.md:403`) Matrix/trials are exact, but “sample every 10 ms” has no allowed jitter, missed-interval, or maximum-gap rule. | **ASSUMED YES.** Bounded streaming and a worker-independent reduction order can satisfy memory and exact-byte bars in principle; exact determinism is an algorithmic requirement, not a sensor-noise floor. | **VERIFIED COMMISSIONED BUT PROTOCOL-INCOMPLETE.** Hash and 7-GiB process-tree plants went red and nulls green, but the real diagnostic missed the 10-ms cadence and therefore refused the ratio as formal (`experiments/m12-scorecard/out/commission.json:137-145,409`; `experiments/m12-scorecard/out/memory-commission.json:93-100`; `experiments/m12-scorecard/out/campaign-16bc3e3d/audit.json:332-348`). | **VERIFIED:** bounded process-tree memory, fixed- and cross-worker reproducibility, and absence of N-mod-4 timing cliffs while the 16-worker output also meets M11; not image quality (`docs/proposals/2026-09-sota-scorecard.md:1038-1103`). |

### Why each axis fails

#### Cross-cutting precision defects

**VERIFIED:** the scorecard freezes Wilson/bootstrap confidence mechanics but
never freezes an empirical percentile convention. The extractor found no
`quantile type`, `percentile method`, or `nearest-rank` definition
(`experiments/M133-blocker-audit/bar-card-audit.json:1359`). This can change
M3 p99, M4's denominator-defining B99, M7 p95/p99, and M10 p95 at a threshold.
The issue is especially material for M7's minimum 24-patch population.

**VERIFIED:** the common quality object is RGB:

> Write **uncompressed** 16-bit **linear ProPhoto RGB, D50** TIFFs
> (`docs/proposals/2026-09-sota-scorecard.md:154-157`)

Yet the core computations for M2–M6 contain no channel/luminance reduction,
while M7 explicitly moves to Lab:

> `"rgb_core_computation_channel_semantics": {`
> `"M2": [],`
> `"M3": [],`
> `"M4": [],`
> `"M5": [],`
> `"M6": [],`
> `"M7": [`
> (`experiments/M133-blocker-audit/bar-card-audit.json:1403-1411`)

M2–M5 already fail for independent reasons below. For M6 this omission is
verdict-changing by itself: “at least one input is `>=0.98`” can mean a
channel sample, any channel in an RGB pixel, every channel, or luminance.

#### M1 — there is deliberately no test

**VERIFIED:** this is not a weak bar; it is no bar:

> There is deliberately no active numeric success bar. M1 remains
> **UNMEASURED**, and no detail, matched-information, quality-qualified
> comparator or SOTA claim is licensed until a replacement statistic and
> numeric bar survive commissioning.
> (`docs/proposals/2026-09-sota-scorecard.md:559-562`)

The old checker does not satisfy criterion (iii), because the document
explicitly withdraws it after its controls reversed or failed
(`docs/proposals/2026-09-sota-scorecard.md:498-541`). A future challenge
battery is specified
(`docs/proposals/2026-09-sota-scorecard.md:566-578`), but the measured quantity
and admission threshold are not. M1 fails (i), cannot be assessed under (ii),
and fails (iii).

#### M2 — no verdict-level aggregation

The card computes one `eta` from each output/reference residual:

> For each cross-fit output `O` and held-out 16-frame mean `R`, compute the
> `0.15–0.35 cyc/px` residual and
> `sigma_res = 1.4826 * MAD(BP(O-R))`.
> (`docs/proposals/2026-09-sota-scorecard.md:591-593`)

It then states only:

> `eta = sigma_res / sigma_ideal`.
> (`docs/proposals/2026-09-sota-scorecard.md:600-603`)

**VERIFIED:** it never says median, mean, maximum, per-site all-pass, or a
pooled functional across the at-least-32 ROIs and reversed cross-fits. The
earlier baseline audit already named this exact defect verbatim:

> M2 specifies no aggregation functional for eta.
> (`docs/research/SCORECARD-BASELINE.md:74`)

The current extractor again finds no aggregation term
(`experiments/M133-blocker-audit/bar-card-audit.json:1360`). Two checkers can
therefore produce different pass/fail results from the same ROI values.

#### M3 — the comparator statistic and quantile are ambiguous

The absolute gates say p99 “of each”:

> median `h_e` and `v_e <=0.01`; p99 of each `<=0.05`
> (`docs/proposals/2026-09-sota-scorecard.md:652-653`)

but the comparator gate becomes singular:

> strehl’s paired p99 is no greater than the best comparator’s.
> (`docs/proposals/2026-09-sota-scorecard.md:654-655`)

**VERIFIED:** the document does not say whether that is p99 of `h_e`, `v_e`,
`max(h_e,v_e)`, or paired site-wise excess. The extractor finds exactly one
undefined `paired p99` occurrence and no global percentile method
(`experiments/M133-blocker-audit/bar-card-audit.json:1359-1361`). M3 fails
(i). **ASSUMED:** its plant/null plan is concrete enough to repair before
output.

#### M4 — an undefined denominator and unfrozen population mix

The defining formula is:

> `Q_flat = RMS(BP_20-60(O)) / max(B99, noise_floor)`.
> (`docs/proposals/2026-09-sota-scorecard.md:685`)

**VERIFIED:** `noise_floor` appears nowhere else in the scorecard
(`experiments/M133-blocker-audit/bar-card-audit.json:1362`). The card also
requires “at least 500 sites overall” but supplies neither a minimum flat-site
count nor a minimum edge-site count
(`docs/proposals/2026-09-sota-scorecard.md:674-676`). Since flat and edge sites
fail different gates, changing their mix changes the combined failed-site
rate. M4 fails (i) and its checker plan is not complete until both quantities
are frozen.

#### M5 — eligibility and “longest run” are not executable uniquely

The eligibility gate uses an undefined quantity:

> A tile is eligible only when its best/far source-signal ratio is `>=2.0`
> with bootstrap lower bound `>=1.5`.
> (`docs/proposals/2026-09-sota-scorecard.md:721-722`)

The run gate says only:

> A connected run is measured along the known focus-sweep direction.
> (`docs/proposals/2026-09-sota-scorecard.md:730-731`)

**VERIFIED:** “source-signal” occurs only there, with no estimator or channel
definition (`experiments/M133-blocker-audit/bar-card-audit.json:1363`).
Likewise, the baseline audit already found:

> M5's “longest failed run along the focus-sweep direction” is undefined for
> non-planar flower/duck/pill tile maps.
> (`docs/research/SCORECARD-BASELINE.md:75-76`)

The current wording adds “connected” but still supplies no adjacency,
projection, width, or tie rule. M5 fails (i).

#### M6 — the rail denominator is not defined for RGB

M6's scalar rules are:

> A high-rail pixel is recoverable when at least one common input is `>=0.98`
> and at least one aligned input lies in `[0.20,0.95]`. A low-rail pixel is
> recoverable when at least one input is `<=0.02` and another lies in
> `[0.05,0.80]`.
> (`docs/proposals/2026-09-sota-scorecard.md:758-761`)

and:

> `clip_high` is the fraction of recoverable high pixels with output
> `>=65534/65535`; `clip_low` is the mirrored fraction `<=1/65535`.
> (`docs/proposals/2026-09-sota-scorecard.md:762-764`)

**VERIFIED:** these lines never select a channel, luminance, or RGB reduction.
The checker can therefore count three channel samples, one RGB pixel if any
channel qualifies, one only if all qualify, or a luminance value. The existing
rail census commissioned threshold detection, not this missing population
choice (`docs/research/SCORECARD-BASELINE.md:48`). M6 fails (i); its checker is
only partial.

#### M7 — the seam arm has no registered population

The patch arm has a minimum:

> At least 24 valid patches, including all neutral patches and at least 12
> chromatic patches, must survive.
> (`docs/proposals/2026-09-sota-scorecard.md:789-792`)

The seam arm does not:

> Across input-defined focus boundaries, compute the p99 DeltaE00
> discontinuity after subtracting the target’s true patch-to-patch difference.
> (`docs/proposals/2026-09-sota-scorecard.md:801-802`)

**VERIFIED:** there is no focus-boundary construction, no minimum boundary or
sample count, no empty-population rule, and no p99 convention
(`experiments/M133-blocker-audit/bar-card-audit.json:1359,1364`). M7 fails
(i). A capture and checker can be planned only after those are frozen.

#### M8 — M8-R is achievable; the present M8-O rail bar is not

The governing output contract is finite:

> Each program must emit a native-size 16-bit linear TIFF.
> (`docs/proposals/2026-09-sota-scorecard.md:175`)

M8-O nevertheless compares that serialized output against the unbounded source
hull:

> define `lo_O=min_k(lo_k)` and `hi_O=max_k(hi_k)` over every geometrically
> valid input frame
>
> For a 16-bit serialized audit only, add exactly `0.5/65535` quantisation
> tolerance
> (`docs/proposals/2026-09-sota-scorecard.md:852-856`)

and demands:

> final-output violation fraction exactly `0.0000%`.
> (`docs/proposals/2026-09-sota-scorecard.md:863-864`)

The retained parser independently read the existing bilinear-stage violation
arrays by their frozen SHA-256s. **VERIFIED:**

> `"violation_coordinates": 980097,`
> `"full_rail": 977684,`
> `"full_rail_below_hull": 977684,`
> `"nonrail": 2413,`
> (`experiments/M133-blocker-audit/bar-card-audit.json:1480-1484`)

For those 977,684 coordinates, the encoded output is exactly `65535`, while
the smallest observed `lo-tolerance` is `1.0000004768371582` and the largest is
`2.0605216026306152`
(`experiments/M133-blocker-audit/bar-card-audit.json:1471-1477`). Therefore
even the maximum u16 value, `65535/65535 = 1`, is below the registered hull.
No alternative u16 output value can pass.

This is not Catmull-Rom overshoot: the nonnegative bilinear M8-R census is
exactly `0 / 6,131,678,976`, while M8-O still has the rail failures
(`experiments/M133-blocker-audit/bar-card-audit.json:1489-1491`). **VERIFIED:
M8-R is achievable; M8-O as currently applied is not.**

The bar needs a pre-results semantic choice: intersect the final hull with the
deliverable domain, audit an unclamped floating deliverable, or classify
out-of-domain source rails under M6 rather than as invented values. Until then,
an implementation cannot pass M8-O on the observed 6-second arm no matter how
its resampler behaves.

#### M9 — its truth predicate does not exist

M9 defines truth as:

> truth is the future independently commissioned M1 condition.
> (`docs/proposals/2026-09-sota-scorecard.md:908-911`)

M1 explicitly has no admitted computation or bar
(`docs/proposals/2026-09-sota-scorecard.md:553-562`). **VERIFIED:** therefore
`truth_valid`, false-certification, and true-band coverage cannot be computed
today. The card also does not freeze decile edges, weighting, an empirical
variance estimator, or how multiple tile-band/repeat cells aggregate
(`docs/proposals/2026-09-sota-scorecard.md:918-925`). M9 fails (i) and (iii);
its checker becomes plannable only after M1 exists.

#### M10 — three reported concepts lack executable gates

The exact-computation section requires:

> Report valid-pixel fraction, Spearman rank correlation, median and p95
> absolute error
>
> report layer confusion and boundary bias separately.
> (`docs/proposals/2026-09-sota-scorecard.md:961-965`)

The success paragraph gates “valid target pixels” and “synthetic layer
confusion” but never defines either, and it omits boundary bias entirely
(`docs/proposals/2026-09-sota-scorecard.md:967-969`;
`experiments/M133-blocker-audit/bar-card-audit.json:1365-1366`). **VERIFIED:**
an output can have arbitrarily bad layer-boundary depth and still pass every
written M10 gate. M10 fails (i), and a pass would not license a boundary
accuracy claim.

#### M11 — “after last shutter” has no input-time contract

The live bar is:

> first-100 streaming master closed and readable `<=10 s` after
> `DSC00100.ARW` becomes available.
> (`docs/proposals/2026-09-sota-scorecard.md:1020-1021`)

**VERIFIED:** neither the M11 card nor the separate execution plan specifies
frame-arrival cadence, whether the first 99 frames may be preloaded or
preprocessed, the delay between file close and availability, or the live arm's
initial cache/process state. The extractor finds no capture-, arrival-, or
replay-cadence term
(`experiments/M133-blocker-audit/bar-card-audit.json:1367`). A slow stacker
given minutes before frame 100 and a fast stacker given all 100 at once are
not the same test. M11 fails (i), and its live checker is not concretely
plannable until the replay contract is frozen.

#### M12 — the sampling target has no admission tolerance

M12 requires:

> Sample process-tree private committed bytes and working set every 10 ms;
> report peak committed bytes.
> (`docs/proposals/2026-09-sota-scorecard.md:1051-1052`)

The commissioned monitor's diagnostic campaign recorded:

> `"ratio_protocol_caveat": "diagnostic only because the 10 ms cadence was not
> maintained under load",`
>
> `"sampling_protocol_exactly_achieved": false,`
>
> `"worst_max_gap_ms": 1048.092800017912`
> (`experiments/m12-scorecard/out/campaign-16bc3e3d/audit.json:332-348`)

**VERIFIED:** the scorecard contains no allowed jitter, maximum gap, missed
interval count, or alternative peak-accounting rule
(`experiments/M133-blocker-audit/bar-card-audit.json:1368`). This is not
academic: the existing checker itself refuses the memory ratio on that basis.
The 6-GiB diagnostic FAIL remains certain because missed samples can hide only
a higher peak, but a future apparent PASS cannot be admitted reproducibly
until the sampling-validity rule is numeric. M12 fails (i), despite strong
commissioning of its hash and allocation controls.

### Refusal answer

**VERIFIED refusal: M1.** I would refuse to spend the owner's money, capture
time, or comparator effort to “unlock M1” under this revision. The governing
instrument itself says there is no admitted statistic or numeric bar
(`docs/proposals/2026-09-sota-scorecard.md:392,559-562`). Clearing `(b)`, buying
`(d)`, and shooting `(c)` cannot turn an undefined test into a score.

**VERIFIED additional stop condition:** I would also refuse implementation
spend aimed at making M8-O green until its rail domain is corrected. The
current checker classifies a maximum representable output as below a source
hull that starts above the maximum; no resampler change can repair that
contradiction.

This does not imply refusing every future Zerene purchase. **ASSUMED:** M6 is
physically achievable, its missing channel rule is cheap to freeze, and the
other textual gaps are likewise repairable before outputs. The verified
consequence is that the scorecard should be repaired before the owner spends
money expecting the present “unlocked” axes to yield interpretable pass/fail
values.

### Assumptions

- **ASSUMED:** nonzero M2–M7 and M9–M12 thresholds are physically/numerically
  achievable unless a specific contradiction is identified above. No
  scorecard run exists to prove actual attainment.
- **ASSUMED:** “concretely plannable” means a competent independent implementer
  can write the checker without inventing a population, reduction, threshold,
  or timing-validity rule. A list of desired outputs is not by itself a
  concrete checker plan.
- **ASSUMED:** the existing M8 bilinear-stage arrays are valid read-only
  artifacts. The retained audit records and checks their exact SHA-256s; it
  does not promote them to a formal score.
- **ASSUMED:** u16 code value `65535` represents normalized linear value `1.0`,
  consistent with the checker's own `encoded/65535` convention and the
  scorecard's `0.5/65535` quantisation tolerance.

### Could not determine

- Whether the scorecard author intended a particular library's percentile
  convention. No convention is written.
- Whether M2's `eta` was intended to pass per ROI, per cross-fit, by a median,
  or by a hierarchical pooled estimator.
- Whether M6 intended a per-channel or luminance rail census.
- Whether M11 intended recorded real-camera arrival times or a synthetic file
  replay for the live arm.
- Whether M12's “every 10 ms” means a nominal polling request or a hard
  maximum gap. The existing audit treats failure to maintain it as
  disqualifying, but the governing document supplies no tolerance.
- Whether the named commercial outputs make M2's strict 5% advantage and
  M11's 2x advantage attainable in practice. Those outputs do not yet exist.

## 8. Did the scorecard drift from the plan?

**VERIFIED — summary: yes, in bounded but material ways.** Across the 19
required primary trace rows (M1–M12 plus decision rules 1–7), the relationship
is **3 faithful, 11 legitimate completions, 2 weakenings, and 3
contradictions**. The mixed decision-rule rows additionally contain **one
omission** (the proposal-pinned fork comparator) and **one unlabelled
addition** (rule 4's `98%` threshold). Counting distinct material divergences
rather than rows gives **9: 5 contradictions, 2 weakenings, 1 omission, and 1
unlabelled addition**. The nine are enumerated in §8.4.

The audit treats the proposal including its two appended amendments as the
authoritative plan. For negative phrase checks, I stripped Markdown
blockquote markers and collapsed all whitespace before searching. The
normalised proposal contains zero occurrences of `98%`, `replacement M1`,
`quality-qualified`, `information score`, `each capture must pass`, `pooling
may not rescue`, `0.25 cyc/native px`, and `UNLICENSED_GT_0.25`.

### 8.1 Q1 — D8/M115 was genuinely withdrawn

**VERIFIED — the M1 state is not a silent omission of a still-admitted D8/M115
instrument.** The original proposal did prescribe it:

> The best-commissioned instrument in the corpus is **M115 §2's split-half
> channel**: fold two interleaved disjoint half-stacks through the entire
> pipeline, each re-deriving every data-dependent weight inside its own half;
> the cross-spectrum of the two outputs is signal
> (`docs/proposals/2026-08-sota-path.md:1696-1699`)

and turned it into three product faces: per-stack tuning, per-tile FRC acuity,
and a shipped half-difference null
(`docs/proposals/2026-08-sota-path.md:1706-1725`).

The commissioned implementation lane then withdrew that product path:

> **Verdict: KILL — STOP/REMOVE RUST; retain the split instrument offline.**
> (`docs/research/M-PHASE0-SPLIT.md:3`)

> the exact historical M115 numbers reproduce, but their controls do not
> transfer to the common-mode and data-dependent-tuning failures on which D8
> depends.
> (`docs/research/M-PHASE0-SPLIT.md:5-8`)

That is a withdrawal of productisation, tuning, and certification, not a claim
that the arithmetic vanished. The report says the useful instrument remains
offline and that reopening needs a genuinely independent repeat or
independently commissioned sensor-pattern subtraction, a non-degenerate
partition, and a transferring tuner plant
(`docs/research/M-PHASE0-SPLIT.md:266-274`).

The authoritative proposal itself then recorded the retirement:

> **The headline clause at lines 192--197 currently has no licensing instrument
> for its first and most important claim.**
> (`docs/proposals/2026-08-sota-path.md:2179-2181`)

> Both are now dead
> (`docs/proposals/2026-08-sota-path.md:2181-2183`)

> **Consequence, stated plainly: strehl can currently prove harm and cannot
> prove benefit.**
> (`docs/proposals/2026-08-sota-path.md:2208-2210`)

> **Independent repeats. Closed; this was FRC's route.**
> (`docs/proposals/2026-08-sota-path.md:2224-2231`)

Amendment 2 later says, without qualification, “Amendment 1 stands in full”
(`docs/proposals/2026-08-sota-path.md:2336-2339`). The scorecard agrees:

> **Same-frame split-half FRC/SNR: dropped.**
> (`docs/proposals/2026-09-sota-scorecard.md:1119`)

and says M1/M9 use repeated exposures only after the failed common-mode and
null controls (`docs/proposals/2026-09-sota-scorecard.md:1119-1124`).

The first repeat-capture attempt did not revive it:

> **Final verdict: NOT ROBUST / NO BUILD.**
> (`docs/research/M-PHASE0-SPLIT2.md:3`)

> No real FRC or `P_sig/P_noise` result was retained
> (`docs/research/M-PHASE0-SPLIT2.md:11-13`)

There is a distinct repeat-pair research route, but it is not an admitted
revival:

> **GO to commission repeat-pair FRC now on synthetic and existing development
> data; NO-GO to admit the current Hann-tiled estimator as M1 before that
> battery passes.**
> (`docs/research/M-FRC-VIABILITY.md:6-8`)

and even a complete GREEN would license FRC only “as one component of M1,”
never the proposal's full `FRC + slant-edge` claim
(`docs/research/M-FRC-VIABILITY.md:631-636`). Git history places both revisions
of that memo before proposal Amendment 1 (`58d04408` and `bc3b3af0`, followed
by `7d1e4b96`). **VERIFIED conclusion:** same-stack D8/M115 is a killed offline
instrument, not an omitted active answer; repeat-pair FRC is a separate,
unadmitted candidate. M1's “no admissible bar” state is documentarily correct.

### 8.2 Axis-by-axis trace

The scorecard declares that numbers it supplies where the proposal is silent,
approximate, or contains `[bar]` are **SCORECARD ADDITIONS**
(`docs/proposals/2026-09-sota-scorecard.md:405-410`). I treat a disclosed
numeric completion with a proposal basis as legitimate completion, not drift.

| Axis | Scorecard bar, verbatim | Proposal source, verbatim | Relationship and consequence |
|---|---|---|---|
| M1 | “**NO ADMISSIBLE BAR — WITHDRAWN.** `f_licensed` is blind; native `S_25` fails sharpening and tone, while tone-hardened derivatives reverse the optical controls.” (`docs/proposals/2026-09-sota-scorecard.md:392`) | “The headline clause ... currently has no licensing instrument” and “Both are now dead” (`docs/proposals/2026-08-sota-path.md:2179-2183`). | **VERIFIED — faithful.** The later amendment supersedes original D1/D8. No integration-only M115 lane is licensed. |
| M2 | “Cross-fit efficiency `<=1.10`; 95% upper bound of strehl / quietest qualifying comparator `<=0.950`.” (`docs/proposals/2026-09-sota-scorecard.md:393`) | “at strictly lower noise (existing flat-ROI instrument)” (`docs/proposals/2026-08-sota-path.md:192-194`). | **VERIFIED — legitimate completion.** It turns “strictly lower” into an executable margin and adds a self-efficiency guard. **Consequence: checker/claim; no new owner purchase.** |
| M3 | “Median excess `<=1%` edge step, p99 `<=5%`; edges above 5% `<=1%` with Wilson upper bound `<=2%`; local source coherence `>=0.90`; no worse than best comparator.” (`docs/proposals/2026-09-sota-scorecard.md:394`) | “no occlusion veil above [bar] (halo instrument at full reach)” (`docs/proposals/2026-08-sota-path.md:195`). | **VERIFIED — legitimate completion.** It fills the literal placeholder and supplies anti-blur controls. **Consequence: checker and the already-planned full-reach capture.** |
| M4 | “Median flat-patchwork ratio `<=1.00`; sites above `1.25` or ghost ratio above `0.10`: `<=1%`, Wilson upper bound `<=2%`; no worse than best comparator.” (`docs/proposals/2026-09-sota-scorecard.md:395`) | The plan requires a “flat-ground plateau census ... [with] no band-domain patchwork” (`docs/proposals/2026-08-sota-path.md:518-524`) and says the depth field closes that class structurally (`docs/proposals/2026-08-sota-path.md:647-650`). | **VERIFIED — legitimate completion.** It promotes a named acceptance failure into a quantified primary gate. **Consequence: checker/lane priority, not owner action.** |
| M5 | “`>=99%` of eligible tiles pass `rho_best>=0.90` and focus margin `>=0.05`; Wilson lower bound `>=98%`; longest failed run `<=1%` of sweep.” (`docs/proposals/2026-09-sota-scorecard.md:396`) | A5 requires recovered depth “within [bar] of truth,” no planted-defect regression, and no excessive displaced depth steps (`docs/proposals/2026-08-sota-path.md:657-665`); D3 expressly consumes “M27's coverage criterion” (`docs/proposals/2026-08-sota-path.md:1595-1598`). | **VERIFIED — legitimate completion.** It supplies the missing output-coverage definition; M10 separately owns depth accuracy. **Consequence: checker plus a fresh controlled-slide holdout after the old unit burned (`docs/proposals/2026-09-sota-scorecard.md:704-716`).** |
| M6 | “Recoverable high-rail and low-rail clipping each `<=0.10%`; highlight-detail retention `>=0.90`; no worse than best comparator.” (`docs/proposals/2026-09-sota-scorecard.md:397`) | The plan keeps “Highlight retention” as an axis (`docs/proposals/2026-08-sota-path.md:175`) and B2 requires the foam colour climb to flatten while forbidding values beyond their evidence (`docs/proposals/2026-08-sota-path.md:746-749`). | **VERIFIED — legitimate completion.** It numerically completes the claim and adds the symmetric low-rail arm. **Consequence: capture power/checker; each scored capture needs 10,000 recoverable pixels (`docs/proposals/2026-09-sota-scorecard.md:754-758`).** |
| M7 | “Median DeltaE00 `<=1.0`, p95 `<=2.0`, maximum `<=3.0`, boundary-seam p99 `<=1.0`; ICC/300-DPI conformance `100%`; no worse than best comparator.” (`docs/proposals/2026-09-sota-scorecard.md:398`) | D7 requires “ICC + 300 DPI” and owner decisions on paper-profile soft proof and tone (`docs/proposals/2026-08-sota-path.md:1682-1691`). | **VERIFIED — legitimate completion.** It adds the absent colourimetric score. **Consequence: new owner capture — a tilted traceable ColorChecker under a measured illuminant (`docs/proposals/2026-09-sota-scorecard.md:786-792`).** D7's untested residue is recorded in §8.6. |
| M8 | “Per-frame resampler-hull violations and final-output source-hull violations: each exactly `0.0000%`.” (`docs/proposals/2026-09-sota-scorecard.md:399`) | The manifest must carry “the out-of-hull census result (`0.0000%` or the exceptions, with coordinates)” (`docs/proposals/2026-08-sota-path.md:1581-1584`). | **VERIFIED — legitimate completion.** M8-O preserves the proposal; M8-R is an expressly labelled extra stage gate. **Consequence: checker/spec only; the achievability defect is separately proved in §7.** |
| M9 | “False-certification Wilson upper bound `<=1%`; true-band coverage `>=90%`; nominal 95% interval coverage `93%`–`97%`; variance ratio `0.90`–`1.10`.” (`docs/proposals/2026-09-sota-scorecard.md:400`) | D2 requires an empirical FRC channel, a single-image decorrelation channel, and an explicit disagreement flag beside the model channel (`docs/proposals/2026-08-sota-path.md:1568-1574`). | **VERIFIED — weakening.** Removing same-frame FRC is justified by Amendment 1, but M9 does not require the surviving decorrelation channel, a replacement independent product channel, or a shipped disagreement result. A pass licenses less than D2's still-written product claim. |
| M10 | “Valid target pixels `>=99%`; rank correlation `>=0.99`; median error `<=0.5` focus step, p95 `<=1.0` step; physical slope error `<=5%`.” (`docs/proposals/2026-09-sota-scorecard.md:401`) | C5 says A5 supplies `z(x,y) ± σ_z` and calls for a “depth + uncertainty TIFF,” normals, physical reshoot advice, and synthetic-aperture re-rendering (`docs/proposals/2026-08-sota-path.md:1159-1163,1179-1185`). | **VERIFIED — weakening.** M10 tests depth values, not uncertainty calibration; a pass cannot license the uncertainty or derivative-product claims. |
| M11 | “Warm common-input throughput `>=2.00x` fastest quality-qualified comparator; candidate/default baseline ratio `<=2.00`; native-RAW CPU at 16 workers `<=0.15 s/frame`; hybrid `<=0.06 s/frame`; cold `<=warm+20 s`; 100-frame live master `<=10 s` after last shutter.” (`docs/proposals/2026-09-sota-scorecard.md:402`) | D15 registers “≥2×,” `≤0.15 s/frame`, `≤0.06 s/frame`, cold `≤ warm + 20 s`, and master `≤10 s` after the last shutter (`docs/proposals/2026-08-sota-path.md:1975-1984`); D5 says quality must stay within “roughly 2×” the current wall (`docs/proposals/2026-08-sota-path.md:1648-1652`). | **VERIFIED — legitimate completion.** The exact bars are faithful; freezing “roughly” at `2.00` is disclosed. **Consequence: lane/quiet-host work plus comparator access; rule 4 separately changes its priority.** |
| M12 | “Warm peak process-tree memory `<=6 GiB`; 299/33-frame peak ratio `<=1.10`; every fixed-worker repeat is byte-identical and the outputs at 1/2/4/8/16 workers are mutually byte-identical while 16 workers passes M11; N-mod-4 per-frame spread `<=2%`.” (`docs/proposals/2026-09-sota-scorecard.md:403`) | D15 requires “memory ≤6 GiB warm; bytes invariant to worker count ... per-frame cost flat in N mod 4” (`docs/proposals/2026-08-sota-path.md:1981-1982`), while D9 fixes the reduction lattice so bytes are invariant by construction (`docs/proposals/2026-08-sota-path.md:1755-1765`). | **VERIFIED — legitimate completion.** The scorecard supplies numeric meanings for “flat” and separates fixed-worker determinism from cross-worker invariance. **Consequence: quiet-host/checker work, not a purchase.** |

### 8.3 Q3 — decision-rule trace

**VERIFIED — rule 4 is the scorecard author's rule, not a requirement traceable
to the owner's proposal.** Its general concern about comparing matched quality
has support, but its M1 dependency and `98%` cutoff do not
(`docs/proposals/2026-09-sota-scorecard.md:93-98`;
`docs/proposals/2026-08-sota-path.md:174,1975-1978,2208-2210`).
`git blame` places the original rule in scorecard commit `90bced75` and its
replacement-M1 wording in `64d9d675`; neither originates in the proposal.

| Rule | Scorecard requirement | Proposal trace | Relationship and consequence |
|---|---|---|---|
| 1 | “Every primary metric is a hard gate. No win compensates for a loss.” (`docs/proposals/2026-09-sota-scorecard.md:86`) | The intended public sentence joins detail, noise, hull, veil, trust/depth, and speed conjunctively (`docs/proposals/2026-08-sota-path.md:192-197`). | **VERIFIED — faithful.** A conjunctive sentence is reasonably formalised as non-compensating gates. |
| 2 | Missing instrumentation, comparator validity, or power blocks SOTA (`docs/proposals/2026-09-sota-scorecard.md:87-88`). | The proposal admits an instrument only after a planted-defect failure and untuned-null pass (`docs/proposals/2026-08-sota-path.md:164-167`) and makes detail contingent on missing capture/licence inputs (`docs/proposals/2026-08-sota-path.md:183-187`). | **VERIFIED — faithful.** It supplies an honest `UNMEASURED` state rather than treating absence as failure or success. |
| 3 | The envelope is Zerene PMax/DMap plus Helicon A/B/C, best per metric (`docs/proposals/2026-09-sota-scorecard.md:89-92`). | D1 pins “licensed Zerene (PMax *and* DMap), the fork rebuilt at its best-known build, Helicon if obtainable” (`docs/proposals/2026-08-sota-path.md:1535-1539`). | **VERIFIED — contradiction, with an embedded omission.** The scorecard changes optional Helicon into a mandatory named product and drops the fork. Exact mode/settings and comparator-favouring direction are legitimate completions; the product-set changes are not. |
| 4 | Every noise, artifact, speed, or memory comparator mode must retain `98%` of the best replacement-M1 score; none qualifies before M1 exists (`docs/proposals/2026-09-sota-scorecard.md:93-98`). | The proposal instead calls noise “Nothing — quotable now” (`docs/proposals/2026-08-sota-path.md:174`) and Amendment 1 says the noise, veil, and invented-structure clauses retain live instruments while detail does not (`docs/proposals/2026-08-sota-path.md:2208-2210`). D15 asks only for comparators “at matched output” (`docs/proposals/2026-08-sota-path.md:1975-1978`). | **VERIFIED — contradiction.** The dependency is scorecard-authored, not the owner's rule. The `98%` number itself is an **unlabelled addition** with no proposal occurrence. |
| 5 | Every capture and the pooled one-sided 95% bar must pass; pooling cannot rescue one (`docs/proposals/2026-09-sota-scorecard.md:99-100`). | The terminal claim is explicitly “On [subjects]” and the detail evidence is said to need its CI (`docs/proposals/2026-08-sota-path.md:178-179,192-197`), but no aggregation rule is supplied. | **VERIFIED — legitimate completion.** It resolves a missing multi-capture decision rule conservatively. **Consequence: capture design/power; one bad subject can now fail an otherwise-green pool.** |
| 6 | CIs resample physical sites with 10,000 fixed-seed hierarchical draws; rates use one-sided Wilson bounds (`docs/proposals/2026-09-sota-scorecard.md:101-103`). | The proposal requires pre-registration and commissioned instruments and repeatedly leaves statistical bars/CI details open (`docs/proposals/2026-08-sota-path.md:164-167,178-179`). | **VERIFIED — legitimate completion.** The statistical unit and resampling count make the intended claim executable. **Consequence: checker/sample-size work, not a purchase.** |
| 7 | No pass/fail or public detail number may use frequency above `0.25 cyc/native px` (`docs/proposals/2026-09-sota-scorecard.md:104-106`). | The owner plan says the scorecard needs a subject “with real contrast above 0.25 cyc/px” (`docs/proposals/2026-08-sota-path.md:183-187`), and C1 claims genuine super-Nyquist recovery (`docs/proposals/2026-08-sota-path.md:1015-1018`) with C12 explicitly reading energy between plane and sensor Nyquist (`docs/proposals/2026-08-sota-path.md:1441-1453`). | **VERIFIED — contradiction.** The rule makes the planned high-frequency capture and the defining C1/C12 claims incapable of earning a score. Amendments preserve workstreams A/B/C (`docs/proposals/2026-08-sota-path.md:2241-2246,2336-2339`), so no proposal retirement resolves it. |

### 8.4 Material divergence register

The following count is clause-based so mixed rule rows are not hidden:

| Divergence | Class | Consequence |
|---|---|---|
| After legitimately removing same-frame FRC, M9 still does not require D2's surviving decorrelation channel, a replacement independent product channel, or the disagreement flag (`docs/proposals/2026-08-sota-path.md:1568-1574`; `docs/proposals/2026-09-sota-scorecard.md:908-925`). | **VERIFIED — weakening** | A green M9 would license calibrated reported bands and variance, not the planned multi-channel trust product. Add product-presence/disagreement gates or narrow the claim. |
| M10 has no depth-uncertainty calibration bar despite C5's `z ± σ_z` and uncertainty TIFF (`docs/proposals/2026-08-sota-path.md:1159-1163,1179-1185`; `docs/proposals/2026-09-sota-scorecard.md:953-969`). | **VERIFIED — weakening** | A green M10 cannot license calibrated uncertainty, normals, physical reshoot advice, or refocusability. |
| Helicon changes from “if obtainable” to required; the scorecard says failure of either commercial product to produce a valid linear output leaves SOTA `UNMEASURED` (`docs/proposals/2026-08-sota-path.md:1535-1539`; `docs/proposals/2026-09-sota-scorecard.md:198-218`). | **VERIFIED — contradiction** | The literal purchase/access requirement is not just Zerene Prosumer; it includes Helicon. The owner must ratify that expansion before `$189` is represented as clearing `(d)`. |
| Rule 4 makes M1 a prerequisite for otherwise independently live comparative clauses (`docs/proposals/2026-09-sota-scorecard.md:93-98,559-562`) despite the proposal preserving the noise/veil/hull instruments (`docs/proposals/2026-08-sota-path.md:2208-2210`). | **VERIFIED — contradiction** | The `(a)` assignments and purchase ordering cannot be presented as owner-mandated. Re-derive readiness after the owner accepts, narrows, or rejects this coupling. |
| Rule 7 suppresses every claim above `0.25 cyc/native px` although the plan asks the owner for such a subject and proposes super-Nyquist channels (`docs/proposals/2026-09-sota-scorecard.md:104-106`; `docs/proposals/2026-08-sota-path.md:183-187,1015-1018,1441-1453`). | **VERIFIED — contradiction** | Do not spend capture or implementation effort on C1/C12 expecting scorecard credit until this is reconciled. |
| The proposal requires a perceptual axis using SSIMULACRA2/butteraugli (`docs/proposals/2026-08-sota-path.md:1528-1536`); the scorecard explicitly rejects them for natural stacks (`docs/proposals/2026-09-sota-scorecard.md:1125-1128`). | **VERIFIED — contradiction** | A 12/12 score supports no perceptual-superiority claim. This is a transparent evidence-based rejection, but the proposal has not been amended to narrow the claim set. |
| Competitive quality must consume a common already-demosaiced TIFF, and a native-RAW run cannot establish the competitive quality win (`docs/proposals/2026-09-sota-scorecard.md:147-169`). C1's defining claim is to stop feeding “resampled estimates” and consume actual photosites, including 2× super-Nyquist recovery (`docs/proposals/2026-08-sota-path.md:912-918,1008-1018`). | **VERIFIED — contradiction** | The current competitive protocol cannot exercise the plan's main RAW-fusion mechanism. A C1 build can improve the product yet receive no competitive quality credit. |
| D1 pins “the fork rebuilt at its best-known build” (`docs/proposals/2026-08-sota-path.md:1535-1539`); the scorecard's exhaustive comparator list contains only Zerene and Helicon (`docs/proposals/2026-09-sota-scorecard.md:89-92,198-213`). | **VERIFIED — omission** | Restore it as a registered free comparator or formally retire it. Its restoration does not remove the proposal's explicit Zerene PMax/DMap requirement. |
| Rule 4's `98%` retained-information threshold appears in the scorecard (`docs/proposals/2026-09-sota-scorecard.md:93-98`) but nowhere in the whitespace-normalised proposal; the nearest source says only “matched output” (`docs/proposals/2026-08-sota-path.md:1975-1978`). | **VERIFIED — unlabelled addition** | The exact threshold needs owner ratification or an explicit SCORECARD ADDITION label before it governs lanes or purchases. |

**VERIFIED counts for this register:** contradictions **5**; weakenings **2**;
omissions **1**; unlabelled additions **1**.

### 8.5 Q2 — information-ledger coverage

The proposal says a novel-physics plan “owes an argument that the list is
complete” and then enumerates fourteen channels
(`docs/proposals/2026-08-sota-path.md:875-897`). Against the exhaustive M1–M12
list (`docs/proposals/2026-09-sota-scorecard.md:388-403`):

| Proposal ledger channel | Scorecard representation |
|---|---|
| Focus modulus — depth/through-focus shape (`docs/proposals/2026-08-sota-path.md:884`) | **VERIFIED — direct:** M5 coverage and M10 depth. |
| Focus phase — signed defocus, registration, pupil, inversion (`docs/proposals/2026-08-sota-path.md:885`) | **VERIFIED — none:** XSPEC is only a closed phase-0 decision gate expressly carrying “No axis score” (`docs/proposals/2026-09-sota-scorecard.md:454`). |
| Spatial sampling phase — aliased super-Nyquist structure (`docs/proposals/2026-08-sota-path.md:886`) | **VERIFIED — none:** there is no alias/SR axis, and rule 7 forbids its defining frequency region (`docs/proposals/2026-09-sota-scorecard.md:104-106`). |
| Wavelength/CFA — longitudinal CA and per-wavelength cutoff (`docs/proposals/2026-08-sota-path.md:887`) | **VERIFIED — partial:** M7 can see final colour error, but the LCA gate expressly “is not M7 colour fidelity” and supplies no axis score (`docs/proposals/2026-09-sota-scorecard.md:456`). |
| G1/G2 quincunx — within-frame noise and alias energy (`docs/proposals/2026-08-sota-path.md:888`) | **VERIFIED — none:** neither the noise probe nor `alias_energy_present` is an M-axis output. |
| Orientation — astigmatism/coma anisotropy (`docs/proposals/2026-08-sota-path.md:889`) | **VERIFIED — none:** M1/M9 have no orientation-resolved result or coverage bar. |
| Amplitude statistics — self-calibration and censoring (`docs/proposals/2026-08-sota-path.md:890`) | **VERIFIED — direct:** M2, M6, and M9 test noise, recoverable rails, and variance calibration. |
| Fixed pattern versus sliding scene (`docs/proposals/2026-08-sota-path.md:891`) | **VERIFIED — partial:** M2/M9 consume independent FPN controls, but no axis tests C6's in-situ calibration product. |
| Depth-dependent geometry (`docs/proposals/2026-08-sota-path.md:892`) | **VERIFIED — partial:** M10 sees final physical depth; the C4c mechanism was killed as a decision gate, explicitly not an axis (`docs/proposals/2026-09-sota-scorecard.md:453`). |
| Time within bracket — sensor/light/rig state and frame quality (`docs/proposals/2026-08-sota-path.md:893`) | **VERIFIED — none:** M11 times computation, not capture-state inference; no axis tests B5's ledger. |
| The file itself — vendor tables, compression, capture flags (`docs/proposals/2026-08-sota-path.md:894`) | **VERIFIED — none:** manifests record metadata, but no axis tests C13 use or B5 classifier behavior. |
| Split-stack halves — empirical noise/resolution truth (`docs/proposals/2026-08-sota-path.md:895`) | **VERIFIED — retired:** same-frame D8 was withdrawn; independent repeats are only an unadmitted future M1/M9 input (`docs/proposals/2026-09-sota-scorecard.md:1119-1124`). |
| Illumination — active texture/specular split/normals (`docs/proposals/2026-08-sota-path.md:896`) | **VERIFIED — partial:** M3/M6 may observe output consequences, but no axis tests the C8/C9/D3 capture capability or its product artifacts. |
| Aperture — blur-ratio depth, occlusion discs, PSF family, pupil factor (`docs/proposals/2026-08-sota-path.md:897`) | **VERIFIED — partial:** M5/M10 use multi-aperture captures, but no axis tests C11 fusion, blur-ratio agreement, or PSF/pupil calibration. |

**VERIFIED tally:** **2 direct, 5 partial, 6 with no direct M-axis, and 1
retired**. The six wholly unrepresented channels are focus phase, spatial
sampling phase, G1/G2 quincunx, orientation, time within bracket, and the
vendor-file payload.

This is not automatically a hole in the narrow terminal SOTA claim. The
proposal expressly says:

> Nothing in C is load-bearing for A/B/D; the plan degrades gracefully if any
> bet dies
> (`docs/proposals/2026-08-sota-path.md:428-431`)

**VERIFIED consequence:** a scorecard pass may still license the proposal's
core output claim, but it cannot license claims that those six channels were
exploited, nor the four partially represented channel-specific product claims.

### 8.6 Q4 — explicit plan commitments no axis would test

**VERIFIED — yes.** A complete 12/12 pass, as presently written, would not prove
completion of the owner's whole plan:

1. **Architecture/default:** the plan says “one merge,” “the backend fork
   retires,” and “confidence ships by default”
   (`docs/proposals/2026-08-sota-path.md:435-438,559-564`). No M-axis tests
   backend retirement or one-path architecture.
2. **Portability, state, and persistence:** phase 2 promises
   `Provenance::Measured` on an unknown body, B5's state/quality ledger, and B7's
   re-renderable master (`docs/proposals/2026-08-sota-path.md:675-711,771-813,
   839-869,2084-2091`). M2/M9 contain only the registered current-body
   repeat/calibration inputs (`docs/proposals/2026-09-sota-scorecard.md:583-588,
   898-905`); no axis exercises an unknown body, per-frame anomaly verdict, or
   re-render.
3. **Trust-product form:** D2 as still written requires model,
   empirical/decorrelation, and disagreement outputs
   (`docs/proposals/2026-08-sota-path.md:1554-1584`). Amendment 1 retires the
   same-frame FRC face, but neither amendment defines a reduced replacement
   product; M9 does not test the surviving decorrelation/disagreement
   obligations.
4. **Depth-product form:** C5 requires uncertainty, normals, physical reshoot
   advice, and refocusable output (`docs/proposals/2026-08-sota-path.md:1154-1185`).
   M10 tests only the depth values.
5. **Planner/live semantics:** D3 specifies predicted step, count, coverage,
   noise, and acuity, while D10 claims a live closed loop that tells the owner
   whether and where to continue shooting
   (`docs/proposals/2026-08-sota-path.md:1586-1627,1777-1798`). M11 tests only
   the ten-second delivery latency, not advice correctness or tether operation.
6. **Print decisions:** D7 still requires the owner's paper-profile soft-proof
   census, tone-policy decision, and dust-default decision
   (`docs/proposals/2026-08-sota-path.md:1682-1691`). M7 does not test them.
7. **Novel channel products:** phase 3 expressly expects a demosaic-free 1×
   merge, 2× fusion, C12 alias gating, and C10 products
   (`docs/proposals/2026-08-sota-path.md:2093-2101`). Its FRC/split-half exit
   language is superseded by Amendment 1 and is not counted as a live
   omission. Rule 7 and the common-TIFF contract still make the surviving
   C1/C12 high-frequency claim unscoreable; the remaining ledger gaps are in
   §8.5.
8. **Perceptual quality:** D1 names a perceptual axis
   (`docs/proposals/2026-08-sota-path.md:1528-1536`), and the scorecard rejects
   it rather than replacing it (`docs/proposals/2026-09-sota-scorecard.md:1125-1128`).

The proposal also says the scorecard, not the roadmap document, decides “SOTA”
(`docs/proposals/2026-08-sota-path.md:2108-2113`). **VERIFIED interpretation:**
these omissions do not all need to become M-axes; they do require a separate
plan-completion ledger so “12/12” is never reported as “the owner's plan is
complete.”

### 8.7 Consequences for lanes, owner action, and purchases

1. **D8/M115:** **VERIFIED — no owner action changes.** Do not restore the old
   same-stack split implementation on documentary grounds. Its product path was
   explicitly killed; any repeat-pair successor must win admission as a new
   instrument.
2. **Rule 4:** **VERIFIED — owner decision required before it governs the
   roadmap.** It is not traceable to the owner's plan and conflicts with the
   plan's statement that noise/veil/hull retain live instruments. The current
   `(a)` assignments and `a+b+c`/purchase ordering are valid under the
   scorecard, but they are not owner-authored requirements. Removing or
   narrowing rule 4 would require re-deriving the blocker table; this audit
   does not assume which `(a)` cells disappear.
3. **Comparator purchase:** **VERIFIED — `$189` Zerene alone does not clear the
   scorecard literally.** The proposal requires Zerene PMax/DMap and makes
   Helicon conditional; the scorecard requires both commercial products.
   Resolve that governance choice, and whether the fork returns, before telling
   the owner what purchase clears `(d)`.
4. **High-frequency capture/C1/C12:** **VERIFIED — pause scorecard-motivated
   spend.** The proposal asks for content above `0.25 cyc/px`, but the scorecard
   forbids using it and its common-TIFF arm bypasses raw photosite fusion.
   Reconcile the protocol before building or shooting these channels for
   scorecard credit.
5. **M9/M10:** **VERIFIED — checker/spec work precedes claim work.** Add or
   explicitly waive the D2 multi-channel/disagreement outputs and depth
   uncertainty/product bars. A present-form pass would overstate the plan.
6. **Additional capture obligations:** **VERIFIED — disclose them as scorecard
   completions, not owner-plan quotations.** M5 needs a fresh controlled-slide
   holdout (`docs/proposals/2026-09-sota-scorecard.md:704-716`), M6 needs
   10,000 recoverable rail samples per scored capture
   (`docs/proposals/2026-09-sota-scorecard.md:754-758`), M7 needs a tilted
   traceable ColorChecker under a measured illuminant
   (`docs/proposals/2026-09-sota-scorecard.md:786-792`), and M10 may need new
   external angle metrology (`docs/proposals/2026-09-sota-scorecard.md:368-380`).

### 8.8 Assumptions

- **ASSUMED:** “owner's plan” means the full current
  `2026-08-sota-path.md`, including Amendments 1 and 2, rather than only the
  unamended revision-3 body. That is the only reading under which later
  evidence can supersede D8 without rewriting history.
- **ASSUMED:** an outcome axis may legitimately cover several implementation
  workstreams; lack of a one-to-one workstream axis is not itself drift unless
  the scorecard can pass while the proposal's stated claim remains untested.
- **ASSUMED:** the six wholly absent C-ledger channels remain non-load-bearing
  for the narrow SOTA sentence because the proposal says so explicitly. They
  remain load-bearing for any channel-specific novelty or product claim.

### 8.9 Could not determine

- Whether the owner has independently ratified rule 4, its `98%` threshold, or
  the change from optional to mandatory Helicon. No such ratification appears
  in the authoritative proposal.
- Whether “matched output” was intended to imply some quality floor for speed
  and noise comparators. It supports a floor in principle, but it does not
  specify M1, `98%`, or that no comparator can qualify before M1 exists.
- Whether a future common-input protocol can expose raw-CFA/sample-level fusion
  fairly. No such protocol is written in either governing document.
- Whether the live M135 technical adjudication will justify a new D8-derived
  instrument. This documentary audit neither reads that lane as authority nor
  pre-judges its technical result.

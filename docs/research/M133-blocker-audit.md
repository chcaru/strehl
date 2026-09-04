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

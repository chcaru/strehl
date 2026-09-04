# M158 — scorecard drift audit

Status: **COMPLETE — 58 gate-bearing blocks examined; 14 distinct drift findings**

## Audit basis and counting rule

This audit treats `docs/proposals/2026-08-sota-path.md` as the owner's controlling
plan and `docs/proposals/2026-09-sota-scorecard.md` as a derived instrument. I read
both documents in full, including all five plan amendments and every scorecard metric,
protocol, readiness row, and publication rule.

The line citations below are pinned to these exact snapshots:

| document | lines | SHA-256 |
|---|---:|---|
| `docs/proposals/2026-08-sota-path.md` | 2,655 | `218a7a0c8748ac3e5e13594ff9b11f13c23f559f19d81ff3accdca597111cc22` |
| `docs/proposals/2026-09-sota-scorecard.md` | 1,394 | `91fd7087b91881c3ebc4625755c9a948a84a6bd51abea3902740e9bcdbcde82d` |

For a reproducible examined-item count, I split the scorecard at blank lines and
selected every paragraph block containing at least one of:
`must`, `required`, `prerequisite`, `forbidden`, `UNMEASURED`, `unmet`,
`ineligible`, `invalid`, `disqualif*`, or `block*`. That produced **58
gate-bearing blocks**. I audited all 58 against the full plan. I also read all 12
metric cards end to end so that requirements phrased only as formulae or Success bars
were not missed. Findings below are deduplicated by requirement; one finding can
therefore cover several repeated blocks.

For every absence claim I used at least three checks: the full-document read,
whitespace-collapsed regex searches, and synonym/paraphrase searches. Exact searches
alone were not treated as proof.

## Tag legend

- **A — INVENTED:** the scorecard imposes a gate or prerequisite with no plan
  counterpart.
- **B — HARDENED:** the plan makes an item optional, conditional, or aspirational,
  but the scorecard makes its absence fatal.
- **C — CONTRADICTORY:** the scorecard changes the plan's threshold, scope, subject,
  or comparator set.
- **PLAN SILENT:** no operative counterpart survived full read plus normalized and
  synonym searches. This is weaker than **PLAN CONTRADICTS**.
- **BLOCKING:** the clause itself can force `UNMEASURED`, an unmet prerequisite, or
  exclusion from a claim.
- **DUPLICATE BLOCKER:** removing this occurrence alone does not unlock an axis
  because another scorecard clause independently recreates it.
- **NONBLOCKING:** the drift weakens or changes claim scope but does not stop work.

Severity describes governance impact, not whether the underlying scientific concern
is sensible.

## Priority verdicts

**TARGET 1 — MIXED, NOT A FREE M2 SCORE:** the scorecard contradicts the plan by
making unavailable M1, M4, and already-failed M8 prerequisites for a noise-only claim,
with the invented `98%` threshold layered on top (scorecard lines 93–98, 165,
655–674; plan lines 174, 2208–2210, 2399–2406), but the plan's historical
“quotable now” numbers do not satisfy the current comparative claim because their own
source leaves the detail cost unmeasured.

**TARGET 2 — M8 FAIL STANDS, BUT ONE LIMB WAS MIS-SPECIFIED:** M8-O's exact-zero
principle is plan-authored and M8-R's exact-zero extension is traceable to the plan's
convexity/sample-set discipline; the old M8-O domain was impossible as written, but
M8-R independently failed at `1.030569%`, so the axis verdict is not erased
(scorecard lines 926–973, 977–1018, 1316; plan lines 176, 417–420, 1024–1030,
1581–1584).

**STRUCTURE — YES, 12/12 DEMANDS MORE THAN THE SIX-CLAUSE PRINT SENTENCE:** the
sentence maps to M1, M2, M3, M8, M9, M10, and M11; M4, M5, M6, M7, and M12 are not
named licensing conditions for any clause, yet the scorecard makes all five fatal.

## Findings

| # | scorecard requirement | scorecard line | plan position | plan line | class (A/B/C) | blocks what | severity |
|---:|---|---:|---|---:|:---:|---|---|
| 1 | Zerene **and** Helicon are mandatory named comparators; failure of either leaves SOTA `UNMEASURED` | 74–75, 89–92, 254–262 | **PLAN OPTIONAL:** “Helicon if obtainable”; later purchase instruction is singular | 1535–1538, 2302–2305 | B | Comparator blocker `(d)` on M1–M7 and M11: 8 axes; other blockers still remain | **Critical** |
| 2 | Decision rule 4 makes replacement M1 a prerequisite for noise, artifact, speed, and memory comparator modes | 93–98 | **PLAN CONTRADICTS** and expressly calls the rule the scorecard author's invention | 2399–2413 | A | Nominally M2/M3/M4/M11; **0 unique immediate unlock** because finding 4 duplicates it | High |
| 3 | Rule 4's retained-information cutoff is exactly `98%` | 93–98, 655–657 | **PLAN SILENT**, and the plan expressly says the threshold appears nowhere | 2403–2406 | A | Same four-axis qualifier as finding 2; **0 unique immediate unlock** | High |
| 4 | Independent joint/card clauses still require M1 for M2, M3, M4, and M11 even if rule 4 is deleted | 165–166, 655–674, 747, 782, 267, 1179–1180 | **PLAN CONTRADICTS:** those four axes are stated not to require M1 intrinsically; noise/veil/hull instruments remain live | 2208–2210, 2531–2537 | C | M2, M3, M4, M11: 4 axes; explains why deleting rule 4 alone unlocks none | **Critical** |
| 5 | Competitive quality is restricted to one already-demosaiced RGB-TIFF boundary; native-RAW runs cannot establish a competitive win | 196–218 | **PLAN CONTRADICTS:** C1's defining mechanism consumes actual photosites and subsumes demosaic, including a 2× sampling claim | 910–920, 1008–1029, 2093–2102 | C | C1 cannot earn competitive credit; scorecard expressly withholds M1/M2/M6/M7 wins from the native path: 4 axes | **Critical** |
| 6 | No pass/fail or public detail claim may use frequency above `0.25 cyc/native px` | 151–153, 609–611, 1064–1069 | **PLAN CONTRADICTS:** the plan requires an above-0.25 subject and proposes genuine super-Nyquist C1/C12 channels | 183–187, 1015–1022, 1439–1464 | C | High-frequency portions of M1 and M9, plus the defining C1 2× and C12 activities: 2 axes + 2 workstreams | High |
| 7 | M11 requires an unconditional `<=0.06 s/frame` hybrid result as one limb of a hard primary gate | 86–88, 457, 1182–1185 | **PLAN OPTIONAL:** the numeric target exists, but GPU is explicitly optional/opt-in and CPU is the reference/end-state claim | 192–197, 1658–1660, 1944–1955, 1977–1981 | B | M11 whenever no qualifying hybrid backend exists; not its only current blocker | Medium |
| 8 | M12-S's 16-worker output must pass **all of M11**, not merely demonstrate determinism at the production-speed worker count | 169, 458, 1228–1234 | **PLAN SILENT** on a full-axis dependency; it couples worker invariance to a speed refund, but never to comparator, hybrid, cold, and live-latency gates | 1755–1764, 1973–1985 | A | M12-S, and therefore the complete M12 verdict, whenever any unrelated M11 limb fails: 1 axis | Medium |
| 9 | The required comparator set omits “the fork rebuilt at its best-known build” | 89–92, 245–267 | **PLAN CONTRADICTS:** the fork is explicitly pinned beside Zerene and optional Helicon | 1535–1538 | C | **NONBLOCKING** today; weakens the evidence a future pass would cover | Low |
| 10 | M9 can pass on claimed-band and variance calibration without the surviving single-image decorrelation product channel (or a replacement independent channel) and emitted disagreement flag | 1045–1091 | **PLAN REQUIRES BROADER SCOPE:** model, empirical/decorrelation, and explicit disagreement channels | 1554–1579 | C | **NONBLOCKING**; permits a false-green narrower trust product | Low |
| 11 | M10 can pass on depth-value accuracy without calibrating `sigma_z` or requiring the plan's first listed depth product, a depth + uncertainty TIFF | 1093–1143 | **PLAN REQUIRES BROADER SCOPE:** `z(x,y) ± sigma_z` and a depth + uncertainty TIFF | 1154–1164, 1179–1187 | C | **NONBLOCKING**; permits a false-green narrower depth product | Low |
| 12 | The original M8-O implementation tests an unprojected source hull against bounded `u16`, making some pass sets empty, then retains the resulting FAIL | 959–986 | **PLAN SILENT** on this impossible cross-domain comparison; it asks for zero invented values, not for penalising representational saturation | 176, 417–420, 1581–1584 | A | M8-O under v1.4: 1 axis; **0 unique current unlock** because M8-R independently fails | High |
| 13 | A SOTA verdict requires all 12 primary axes although the plan's printable sentence names licensing instruments mapping to only seven | 70–88, 443–458, 1380–1389 | **PLAN CONTRADICTS in publication scope:** six clauses map to M1/M2/M3/M8/M9/M10/M11 | 164–181, 189–197 | C | Adds M4, M5, M6, M7, and M12 as fatal publication prerequisites: 5 axes | **Critical** |
| 14 | M2 cannot produce a noise-only claim unless the same render also passes M4 and M8; the existing M8 FAIL therefore vetoes M2 | 165, 1310–1316 | **PLAN CONTRADICTS:** noise is independently “Ahead, measured” and “quotable now”; the later amendment keeps the noise instrument live | 174, 2208–2210 | C | M2: 1 axis, independently of M1 and comparator blockers | High |

## Priority target 1 / finding 14 — noise: overblocked, but not already scored

### The contradiction

The plan's current-state table is unambiguous:

> “Noise, flat/defocused ground | **Ahead, measured.** 4.5× vs the fork
> (≥2.4× worst-case grade-corrected); 0.746× vs one unstacked frame at gate 4.5;
> 9.9× flat-field rms on the deepest stack with the compound eye indistinguishable
> ... | **Nothing — quotable now**.”  
> — plan line 174

The intended sentence then says:

> “at strictly lower noise (**existing flat-ROI instrument**)”  
> — plan lines 192–194

The scorecard instead records:

> “M2 | Noise efficiency | **UNMEASURED** ... Prior numbers were not produced under
> this matched-information protocol.”  
> — scorecard line 1310

and makes M1, M4, and M8 fatal to an M2 claim:

> “M1 information + M2 noise + M4 flat power + M8 hull ... publish the
> replacement detail value with `(eta, Q_flat, M8-R, M8-O)` from the same output
> and pass every bar simultaneously. Until then neither a noise-only nor a detail
> claim is valid.”  
> — scorecard line 165

> “a future replacement M1 must remain green ... Until M1 is replaced, `eta` is
> diagnostic only.”  
> — scorecard lines 669–674

That directly contradicts the later plan amendment:

> “The noise clause, the veil clause and the invented-structure clause ... retain
> live instruments. The detail clause does not.”  
> — plan lines 2208–2210

and the plan's explicit ruling that M2 is not intrinsically M1-dependent (plan
lines 2531–2537).

### What M2 adds, item by item

| Scorecard requirement | Plan relationship | Ruling |
|---|---|---|
| Replacement M1 must exist/pass before M2 can claim | Plan says noise remains live and M2 does not intrinsically require M1 | **C — contradictory, blocking** |
| Comparator mode must retain `98%` of replacement-M1 information | Plan expressly says the threshold appears nowhere | **A — invented, blocking** |
| Zerene and Helicon must both qualify | Plan requires Zerene and says “Helicon if obtainable” | **B — Helicon hardened, blocking** |
| Cross-fit held-out means, independent repeats, input-only ROIs, temporal `sigma_1`, and `eta<=1.10` | Concrete protection against texture/FPN leakage and a self-efficiency check | **Legitimate operationalization** |
| Comparator UCB95 ratio `<=0.950` | Numeric completion of “strictly lower noise” | **Legitimate operationalization** |
| Publishing noise, flat-power, and hull values from the same output/settings | Prevents a quiet blurred render from being compared with a different quality render | **Legitimate operationalization** |
| Requiring M4 and M8 themselves to pass before any noise-only claim is valid | Plan says the noise axis is independently quotable and later preserves its live instrument | **C — contradictory, blocking; current M8 FAIL vetoes M2** |
| Common linear-input/transfer controls | Corrects the old asymmetric development comparison for M2 | **Evidence-backed and legitimate for M2**; the exclusive demosaiced boundary still contradicts C1 globally (finding 5) |
| Both 32-frame light blocks must satisfy the non-translation eligibility limit | Plan says no capture blocks the old result, but measured scene-motion leakage invalidates one required arm | **Evidence-backed supersession, not drift** |

### The gap in the other direction

The plan's “quotable now” status is too strong for the current M2 claim. The source
report for the `0.746x` number says:

> “Without a commissioned detail statistic the trade cannot be priced, and 0.746x
> must not be read as ‘better’.”  
> — `docs/research/BUILD-PYRNOISE.md` lines 425–431

It concludes:

> “At what cost in detail? **Unmeasured** ... Until one survives, the noise column is
> half a trade.”  
> — `docs/research/BUILD-PYRNOISE.md` lines 458–462

The scorecard also records that the older head-to-head used asymmetric development
(scorecard lines 1347–1350). Thus the historical number supports a narrower statement
against one frame/the fork; it is not a v1.7 M2 PASS against the best shipping
commercial comparator at controlled information.

Nor is M2 a free score after deleting the invented M1 clauses. M146 found that the
required second-light repeat misses the frozen non-translation limit
(`0.107703 px`, independently `0.105202 px`) and that M2 still lacks a verdict-level
ROI/cross-fit aggregation and RGB reduction
(`docs/research/M146-unlock-audit.md` lines 112–160).

The current readiness row is itself stale in both directions. It lists M2 as
`(a)(b)(d)` (scorecard line 479), while the same scorecard now says blocker `(b)` is
**CLEARED** by M130 (line 513). Conversely it omits `(c)`, although M146 proves the
second-light input fails its registered eligibility gate. After reconciling the
documents, the legitimate remaining path is not “obtain M1”: define the M2
aggregation/channel reduction, obtain an eligible two-light unit, and obtain the
required Zerene common-input arm; Helicon remains optional under the plan.

The bare status mismatch is therefore not counted a second time as drift: evidence
does overturn the old “quotable now” status for a current commercial-comparator
verdict. Finding 14 is the narrower contradiction that remains after that correction:
the scorecard refuses even an independently valid noise-axis result unless unrelated
M4/M8 axes also pass.

**Target 1 ruling:** the plan is too optimistic about the old result, while the
scorecard is too restrictive about what can replace it. Preserve M2's independent
noise instrument and local anti-blur/information control; remove the global M1,
`98%`, M4-pass, and M8-pass prerequisites. That creates a shorter path to M2, but not
an honest free score from the archived number.

## Priority target 2 / finding 12 — M8: faithful invariant, flawed historical M8-O domain

### Scorecard success criteria, verbatim

> “M8 has two mandatory censuses because a final broad hull can hide an interpolator
> excursion that another frame happens to bracket. M8-R is a **SCORECARD ADDITION**;
> M8-O is the proposal's per-file invariant.”  
> — scorecard lines 938–942

> “**Success.** **PROPOSAL BAR (M8-O):** final-output violation fraction exactly
> `0.0000%`. **SCORECARD ADDITION (M8-R):** resampler violation fraction exactly
> `0.0000%`; the crop/reference identity arm also has zero violations. A missing
> pre-clamp trace is `UNMEASURED`, not a pass.”  
> — scorecard lines 970–973

The admitted result is:

> “M8-R `1.030569%`, M8-O `1.326144%` against a bar of exactly `0.0000%`.”  
> — scorecard line 1316

### Plan requirement, verbatim

> “Invented structure | **Ahead.** `0.0000%` out-of-hull for every convex arm, held
> as a discipline ... | Keep it an axis, so it cannot be quietly traded away...”  
> — plan line 176

> “**Convexity:** every estimator of `R_c` this project ships is a convex combination
> of measured samples (the hull discipline, `0.0000%` for every convex arm...)”  
> — plan lines 417–420

> C1 acceptance includes “hull discipline per contributing sample set.”  
> — plan lines 1024–1030

> The manifest gains “the out-of-hull census result (`0.0000%` or the exceptions,
> with coordinates)” so the file can state “this file provably contains no invented
> values.”  
> — plan lines 1581–1584

Amendment 1 keeps that requirement alive and says its promotion to a comparative axis
is a “change of role rather than a new instrument” (plan lines 2212–2217).

### Classification and validity of the only score

- **M8-O's exact-zero principle is faithful, not drift.** It is stated repeatedly in
  the plan.
- **M8-R is a disclosed scorecard addition, but not an invented requirement under
  class A.** The plan already requires every shipped estimator to be convex and C1 to
  preserve the hull per contributing sample set. M8-R observes the stage where that
  requirement can be violated instead of allowing downstream clamping to hide it.
- **The original v1.4 M8-O domain is invented and invalid.** The scorecard now admits
  that comparing bounded `[0,1]` `u16` output with an unprojected source hull can make
  the satisfying set empty and charge a container limit as an algorithmic defect
  (scorecard lines 977–986). That is finding 12.
- **The overall M8 FAIL nevertheless stands.** M8-R independently reads
  `1.030569%`, is achievable at zero with the convex bilinear control, and is traced
  to Catmull-Rom's negative-lobe gather
  (`docs/research/M8-overshoot.md` lines 55–62, 117–126). Even the prospective
  representable-domain M8-O rule reports 31,148 shipping-Catmull violations while
  bilinear remains zero (scorecard lines 988–1000), although that prospective M8-O
  has not yet produced a formal score.

**Target 2 ruling:** the scorecard did not invent the no-invented-values standard, and
the only scored axis is genuinely red. The historical `1.326144%` M8-O magnitude must
carry the v1.4 domain caveat; the independent `1.030569%` M8-R failure is sufficient
to preserve the FAIL. The plan's “Ahead” label was limited to convex arms and did not
establish that the shipping Catmull-Rom path was ahead.

## Structural finding 13 — the publication rule adds five fatal axes

The plan's exact printable sentence and its named licensing instruments map as
follows:

| Plan sentence clause (plan lines 189–197) | Scorecard axis |
|---|---|
| detail at or beyond best shipping comparator — D1 | M1 |
| strictly lower noise — existing flat-ROI instrument | M2 |
| zero invented structure — hull census | M8 |
| no occlusion veil — halo instrument | M3 |
| certified acuity / `n_eff` — D2/D8 | M9 |
| physical depth — A5/C5 | M10 |
| seconds per frame on CPU — existing harness | M11 |

The scorecard accurately recites those clauses at lines 70–72, then makes an
unsupported jump:

> “**Therefore** ... the shipping default passes every primary bar below...”  
> — scorecard lines 73–77

Decision rule 1 makes every primary metric a hard gate (scorecard lines 84–88), and
the publication rule makes any required missing metric fatal (scorecard
lines 1380–1389). The twelve-axis table is at scorecard lines 443–458.

The five extra fatal axes are:

1. **M4 — non-edge artifact rate**
2. **M5 — depth-of-field coverage / stack failure**
3. **M6 — highlight/shadow retention**
4. **M7 — colour fidelity**
5. **M12 — memory, determinism, and scaling invariance**

These are not necessarily bad tests or plan-silent research goals. M6 and memory
appear in the preceding plan axis table; M4, M5, and M7 have workstream-level
counterparts elsewhere. The contradiction is narrower and documentary: none is a
named licensing instrument for any clause of the sentence the plan says the project
should be able to print. M4/M5 can serve as opposed controls, but the plan does not
make them separate publication vetoes; M11 already supplies the sentence's CPU-speed
clause, so M12 is additional.

**Classification: C — CONTRADICTORY scope expansion. BLOCKING.** A build can satisfy
every clause and every parenthesized licensing instrument in the owner's sentence yet
remain barred from printing it because any one of M4, M5, M6, M7, or M12 is
`UNMEASURED` or FAIL. Owner ratification is required either to expand the intended
sentence or to demote those five from terminal publication gates.

## M1 context requested by the orchestrator

The M1 withdrawal does **not** exceed the plan. The scorecard withdraws the old
instrument because its sharpening and tone controls failed (scorecard lines 546–617).
Plan Amendment 1 independently says the headline detail clause has no licensing
instrument and that both D1 instruments are dead (plan lines 2173–2206). M135's
replacement work is therefore plan-authorized; the drift begins only when absent M1
is propagated into otherwise live axes such as M2.

## 1. Helicon was hardened from optional to fatal

### Scorecard

> “SOTA means that the shipping default passes every primary bar below against
> licensed Zerene Stacker **and Helicon Focus**...”  
> — scorecard lines 73–77

> “If either product cannot produce a linear output that passes §1.3, the
> named-comparator requirement is unmet and the SOTA verdict remains
> `UNMEASURED`.”  
> — scorecard lines 260–262

### Plan

> “Comparators pinned and priced: licensed Zerene (PMax *and* DMap ...), the fork
> rebuilt at its best-known build ..., **Helicon if obtainable**.”  
> — plan lines 1535–1538

> “`(d)` — licence **a commercial comparator**. Zerene Stacker is already installed
> here but its trial expired...”  
> — plan lines 2302–2305

**Classification: B — HARDENED. BLOCKING.**

The plan's “if obtainable” is an explicit condition, not a blank for the scorecard to
fill. Amendment 2 repeats a scorecard-derived blocker label, “unavailable
common-input Zerene/Helicon output” (plan lines 2257–2263), but its operative owner
action remains singular and names Zerene. It does not rescind the earlier conditional.

The scorecard assigns `(d)` to M1, M2, M3, M4, M5, M6, M7, and M11 (scorecard
lines 478–488). Correcting this does not make those axes immediately measurable
because their other blockers remain; it removes an unauthorized second-product
purchase/export condition from eight axes.

## 2. Decision rule 4 is invented

### Scorecard

> “Once a replacement M1 is admitted, a comparator mode may define a noise, artifact,
> speed, or memory envelope only if it ... retains at least `98%` of the highest
> replacement-M1 information score...”  
> — scorecard lines 93–98

### Plan

> “**Decision rule 4 of the scorecard is the scorecard author's invention, not a
> requirement traceable to this proposal.**”  
> — plan lines 2397–2402

> “Blocker counts and spending advice cannot be presented as owner-mandated while
> they rest on an unratified authored rule.”  
> — plan lines 2408–2412

**Classification: A — INVENTED. DUPLICATE BLOCKER.**

The nominal reach is M2, M3, M4, and M11. The scorecard now correctly records that
striking rule 4 alone changes no current measurable-axis count (scorecard
lines 116–145). Finding 4 identifies the independent copies that keep the same four
axes tied to M1. This remains drift because it changes the meaning of a passing claim,
even though its current marginal unlock is zero.

## 3. The `98%` cutoff is separately invented

### Scorecard

> A comparator mode must retain “at least `98%` of the highest replacement-M1
> information score.”  
> — scorecard lines 93–98

The same cutoff is embedded again in M2:

> “The comparator ratio uses paired ROIs and only modes within `98%` of a future
> replacement-M1 information envelope.”  
> — scorecard lines 655–657

### Plan

> “The `98%` threshold appears **nowhere** in this document; the nearest source asks
> only for comparators *‘at matched output’*...”  
> — plan lines 2403–2406

**Classification: A — INVENTED. DUPLICATE BLOCKER.**

“Matched output” supports controlling quality; it does not supply this threshold,
this denominator, or M1 as the universal matching instrument. The threshold affects
the same M2/M3/M4/M11 comparator qualification as rule 4. It has no unique current
unlock because the broader M1 dependencies remain.

## 4. M1 prerequisites survive outside rule 4

### Scorecard

The independent clauses are not merely references to decision rule 4:

> “M1 information + M2 noise + M4 flat power + M8 hull ... pass every bar
> simultaneously. Until then neither a noise-only nor a detail claim is valid.”  
> — scorecard line 165

> “The [M3] build must also pass a future commissioned M1...”  
> — scorecard line 166

> “Until M1 is replaced, `eta` is diagnostic only.”  
> — scorecard lines 669–674

> “A future replacement M1 ... catch[es] blur.”  
> — scorecard lines 746–748 and 782–783

> “For speed it is the fastest mode that passes the complete quality scorecard” and
> “Comparator speed uses the fastest mode that passes all quality gates...”  
> — scorecard lines 265–267 and 1179–1180

### Plan

> “The noise clause, the veil clause and the invented-structure clause ... retain
> live instruments. The detail clause does not.”  
> — plan lines 2208–2210

> “Scorecard decision rule 4 ... propagates blocker `(a)` to four axes that do not
> require it intrinsically ... `M2, M3, M4, M11`.”  
> — plan lines 2531–2537

**Classification: C — CONTRADICTORY. BLOCKING.**

The plan says these axes are nonintrinsic to M1 and attributes their dependency to
rule 4. The scorecard independently recreates that dependency in its joint
constraints, metric controls, and comparator-speed definition. This blocks all four
axes after rule 4 is removed. M146 independently demonstrated the practical result:
removing rule 4 alone unlocks none of them.

An anti-blur control is legitimate. Making the unavailable global M1 verdict the only
such control is the drift. Local width/coherence, transfer, and same-output tuple
controls may remain without making all four axes inherit M1.

## 5. The exclusive demosaiced-TIFF protocol excludes C1

### Scorecard

> “Competitive quality is measured **only** at a common merge boundary...”  
> “Demosaic once. Write uncompressed 16-bit linear ProPhoto RGB ... TIFFs...”  
> “Zerene, Helicon, and strehl must receive the exact same TIFF bytes.”  
> — scorecard lines 194–213

> “A native-RAW run is reported as a product diagnostic but cannot establish a
> competitive detail, noise, clipping, or colour win...”  
> — scorecard lines 215–218

### Plan

> “The single largest un-refuted quality lever ... [is] to stop feeding the merge
> resampled estimates and start feeding it the sensor's actual samples ... one
> estimator that subsumes demosaic, warp resampling, merge, and ... super-resolution.”  
> — plan lines 910–920

> “What it buys at 2×: alias-unfolded R/B at full resolution ... and genuine
> super-Nyquist recovery...”  
> — plan lines 1015–1022

> “C1 lands in two rungs: 1× lattice first (demosaic-free merge ...), then 2×...”  
> — plan lines 2093–2102

**Classification: C — CONTRADICTORY. BLOCKING.**

The fair-input principle is legitimate; the selected boundary is not neutral to the
plan. It removes the raw photosites before the algorithm whose defining claim is to
merge those photosites. The native-product escape clause does not repair this because
the scorecard expressly denies that arm competitive detail, noise, clipping, and
colour credit. At minimum M1, M2, M6, and M7 cannot credit C1's mechanism under the
current protocol.

The correction is not “let strehl use better inputs.” It is to define a common
pre-demosaic sample contract, or another auditable paired protocol, that both controls
development asymmetry and can exercise C1.

## 6. Rule 7 forbids the frequency region the plan asks to measure

### Scorecard

> “No pass/fail decision or public numerical detail claim may use a frequency above
> `0.25 cyc/native px`. A checker that reads higher must emit only
> `UNLICENSED_GT_0.25`.”  
> — scorecard lines 151–153

M9 repeats the restriction:

> “Bands above `0.25 cyc/px` must be labelled `UNLICENSED` and cannot improve the
> score.”  
> — scorecard lines 1064–1069

### Plan

> “The scorecard needs ... one subject with real contrast **above 0.25 cyc/px** ...
> and every fine-detail claim in this proposal is contingent on [it].”  
> — plan lines 183–187

> C1 claims “genuine super-Nyquist recovery” where the optics deliver it.  
> — plan lines 1015–1022

> C12 reads “energy the scene carries between plane Nyquist and sensor Nyquist” and
> uses it as a “super-Nyquist focus cue.”  
> — plan lines 1439–1464

**Classification: C — CONTRADICTORY. BLOCKING.**

The later plan amendments kill the current single-image high-frequency instruments;
they do not forbid all future independent-reference measurements above 0.25. The
plan also says workstreams A, B, and C stand (plan lines 2336–2340). Rule 7 therefore
prevents the very capture and C1/C12 measurements the plan preserved from ever
earning scorecard credit. It blocks the high-frequency portions of M1 and M9 and the
defining claims of C1 and C12.

## 7. The hybrid target was hardened despite explicit optionality

### Scorecard

> “Every primary metric is a hard gate.”  
> — scorecard lines 84–88

> M11 Success requires “native-RAW CPU-only at 16 workers `<=0.15 s/frame`; hybrid
> `<=0.06 s/frame`; cold `<=warm+20 s`...”  
> — scorecard lines 1182–1185

### Plan

The number itself is real:

> “extend to `<=0.15 s/frame` CPU-only and `<=0.06 s/frame` hybrid...”  
> — plan lines 1977–1981

But its status is conditional:

> “GPU stays optional and non-contending...”  
> — plan lines 1658–1660

> “the fallback is per-adapter freeze rows and `--gpu` staying opt-in with CPU as the
> reference implementation.”  
> — plan lines 1944–1947

The terminal public sentence also ends in CPU speed, not GPU/hybrid speed (plan
lines 189–197).

**Classification: B — HARDENED. BLOCKING.**

The scorecard did not invent `0.06`; it invented the consequence of missing it.
The plan registers a target for the conditional hybrid path while explicitly keeping
that path optional. Making every M11 limb mandatory turns an optional backend into a
fatal SOTA prerequisite. This reaches M11 only and is not M11's sole current blocker.

## 8. M12-S is coupled to the entirety of M11

### Scorecard

> “The primary CPU result is the 16-worker output; it must meet M11 ... while meeting
> M12.”  
> — scorecard line 169

> “M12-S requires exactly one distinct hash across all five worker counts at every N,
> and the 16-worker output must simultaneously pass M11.”  
> — scorecard lines 1228–1234

### Plan

The plan does connect worker-invariant reduction to recovering parallel speed:

> “Partition frames into a fixed number of chunks independent of the worker count ...
> Bytes are then invariant to worker count by construction ... and
> `available_parallelism()` becomes usable...”  
> — plan lines 1755–1764

It also lists speed, memory, worker invariance, and modulo scaling together (plan
lines 1973–1985). It does **not** say that a determinism result is invalid unless the
same output also passes M11's commercial-comparator ratio, optional hybrid target,
cold-start bound, and live-capture latency.

**Classification: A — INVENTED, PLAN SILENT on the full-axis dependency. BLOCKING.**

The legitimate opposed control is narrower: demonstrate invariance at the
production-speed worker count rather than obtaining it by serial execution. Requiring
all of M11 imports unrelated comparator, hybrid, cold, and live prerequisites into
M12-S. This can block the complete M12 verdict even though the readiness table calls
M12 scientifically unblocked (scorecard lines 489–492).

Absence checks on whitespace-collapsed plan text found zero operative matches for
`simultaneously\s+pass`, for an M11-equivalent full speed/comparator prerequisite,
and for determinism/worker invariance conditioned on hybrid, cold, or live latency.

## 9. The plan-required fork comparator disappeared

### Scorecard

> “A comparative quality gate uses the best qualifying comparator envelope: Zerene
> PMax, Zerene DMap, and Helicon Methods A, B, and C...”  
> — scorecard lines 89–92

The exhaustive settings section likewise lists Zerene, Helicon, and strehl only
(scorecard lines 245–267).

### Plan

> “Comparators pinned and priced: licensed Zerene ..., **the fork rebuilt at its
> best-known build** ..., Helicon if obtainable.”  
> — plan lines 1535–1538

**Classification: C — CONTRADICTORY comparator set. NONBLOCKING.**

This omission makes the scorecard easier, not harder, so it unlocks no axis. It still
changes the evidence set that a future SOTA verdict claims to cover. The scorecard
snapshot has zero whitespace-normalized matches for both
`\bthe\s+fork\b` and `best[-\s]+known\s+build`; synonym searches for the plan's
2.4× fork comparator found only generic “best comparator” language, never a
registered fork arm.

## 10. M9 narrows the planned trust product

### Scorecard

M9 acknowledges that D2 proposed a model and empirical channel, then scores claimed
bands and variance calibration:

> “D2 proposes a CRLB channel and an empirical channel ... but the proposed
> same-capture split channel is no longer admissible.”  
> — scorecard lines 1047–1052

> Success is false-certification, true-band coverage, interval coverage, and a
> variance ratio.  
> — scorecard lines 1062–1091

### Plan

> “Two channels now stand beside the model-based one ... D8's empirical per-tile FRC
> ... and a single-image decorrelation estimate where halves are unavailable. Where
> model and empirical channels disagree beyond their joint bars, the map says so —
> disagreement is a defect flag...”  
> — plan lines 1568–1574

**Classification: C — CONTRADICTORY narrower scope. NONBLOCKING.**

Evidence invalidates the same-capture FRC channel, so removing that channel is
legitimate. The scorecard does not, however, require the surviving single-image
decorrelation channel, a replacement independent product channel, or an emitted
disagreement flag. A green M9 therefore licenses less than the still-written D2
product. This does not block work; it risks a false-green claim and should be repaired
by adding the surviving product requirements or narrowing the claimed product.

## 11. M10 omits uncertainty calibration

### Scorecard

> M10 reports valid-pixel fraction, rank correlation, depth errors, slope, flatness,
> and layer confusion, with Success bars for those quantities.  
> — scorecard lines 1093–1143

Although its rationale says uncertainty should survive truth (lines 1095–1098), no
Success limb calibrates reported uncertainty or requires the downstream products.

### Plan

> “A5 supplies `z(x,y) ± sigma_z`...”  
> — plan lines 1154–1164

> “Products, in increasing ambition: depth + uncertainty TIFF ... surface normals ...
> reshoot advisor ... and synthetic aperture re-rendering...”  
> — plan lines 1179–1187

**Classification: C — CONTRADICTORY narrower scope. NONBLOCKING.**

M10 can pass while `sigma_z` is absent or miscalibrated and while the plan's first
listed product, the depth + uncertainty TIFF, is absent. The normals, reshoot, and
refocus products are explicitly “in increasing ambition,” so this audit does not
treat all of them as mandatory; it records only that M10 also supplies no evidence
for those broader claims. This does not make an axis unmeasurable. Add an uncertainty
calibration/product-presence gate or narrow the claim the scorecard licenses.

## Checked and found legitimate

The purpose of this section is to distinguish “examined and cleared” from “not
examined.” These were all checked against the plan and are **not** findings:

| Checked item | Ruling |
|---|---|
| Decision rule 1: non-compensation among the axes that license the plan's clauses | Legitimate operationalization of the conjunctive sentence. Extending the terminal veto to M4/M5/M6/M7/M12 is finding 13, not cleared here. |
| Decision rule 2: missing/invalid/under-powered evidence is `UNMEASURED` | Legitimate consequence of commissioned-instrument and named-comparator requirements at plan lines 164–187. |
| Per-capture pass plus pooled confidence result; hierarchical bootstrap and Wilson bounds | Legitimate pre-registration/statistical completion. The plan asks for CIs and leaves exact aggregation open. |
| Positive plants and untuned nulls | Direct plan requirement at lines 164–167. |
| Output-transfer ramp, frozen manifests, hashes, settings, and no post-stack enhancement | Legitimate controls against known development asymmetry; exact tolerances are disclosed scorecard additions. |
| `>=99%` retained common-overlap field of view | Not the plan's `>=80%` crop gate: the denominators differ. M130 independently records that distinction. |
| Fresh holdout quarantine and session-burn rule | Legitimate pre-registration/anti-leakage implementation; later plan amendments explicitly require a new capture session. |
| M2–M7 and M9–M12 numeric Success bars generally | Legitimate completions of qualitative goals or literal `[bar]` placeholders. Findings 7, 8, 10, and 11 concern scope/fatality, not the numerical values themselves. |
| M3's new per-side maximum for a one-sided veil | Evidence-driven tightening after the prior statistic failed its required plant; no score had been read. This is “evidence proves otherwise,” not quiet relaxation. |
| M6's symmetric low-rail arm | Legitimate anti-cheat completion of retention: it prevents darkening from buying a highlight pass and is paired with the transfer sentinel. |
| M7 ColorChecker/DeltaE and seam coupon | Legitimate concrete instrument for D7's colour/print objective, despite creating a new capture obligation. |
| M8-R per-frame hull census | Legitimate extension of the plan's “hull discipline per contributing sample set” at plan lines 1024–1029. The impossible original M8-O output-domain rule is separately finding 12. |
| M9 independent repeats and external FPN treatment | Legitimate evidence-driven replacement for the plan's invalid same-capture split channel. |
| M10 external physical metrology | Legitimate implementation of depth “in physical units”; the omission of uncertainty/product scope is finding 11. |
| M11 `>=2x`, CPU `<=0.15`, cold `<=warm+20`, live `<=10 s`, and baseline `<=2x` bars | Direct targets or disclosed concretizations of plan lines 1648–1652 and 1973–1985. Only making the optional hybrid limb fatal is finding 7. |
| M12 `<=6 GiB`, byte invariance, fixed-worker determinism, and numeric flat-scaling bars | Direct targets or legitimate numeric completions of D9/D15. Only importing all of M11 is finding 8. |
| Rejecting SSIMULACRA2/butteraugli as primary natural-stack evidence | Evidence-backed departure: the scorecard identifies the missing truth-reference problem. Under the owner's “unless evidence proves otherwise” instruction, this is not counted as drift, though the public claim must not imply a passed perceptual axis. |

### Coverage ledger

The 58 machine-selected gate blocks were distributed as follows. Counts are blocks,
not findings; repeated clauses remain separate blocks in this ledger.

| scorecard area | gate-bearing blocks examined |
|---|---:|
| Revision history, global rules, protocols, corpus, readiness, phase-0 census | 19 |
| M1 | 4 |
| M2 | 3 |
| M3 | 4 |
| M4 | 2 |
| M5 | 2 |
| M6 | 1 |
| M7 | 2 |
| M8 | 4 |
| M9 | 3 |
| M10 | 3 |
| M11 | 3 |
| M12 | 3 |
| Final scoreboard, audit objections, stress-test disposition, publication rule | 5 |
| **Total** | **58** |

## Absence-search record

The following negative findings were not inferred from one literal grep:

| Question | Whitespace-normalized searches | Result |
|---|---|---|
| Does the scorecard register the fork? | `\bthe\s+fork\b`; `best[-\s]+known\s+build`; `2\.4.{0,40}fork`; inspected both comparator sections and M11 | No registered fork arm; exact first two searches return zero. |
| Does the plan require shadow retention as a separate fatal limb? | `shadow\s+retention`; `recover\w*\s+(?:a\s+)?shadow`; `shadow\s+recover`; `low[-\s]+rail`; `clip[_\s-]*low`; inspected B2/B7 | No such requirement. I nevertheless treated M6's low-rail arm as legitimate anti-cheat completion, not drift. |
| Does the plan require M12-S to pass all of M11? | `simultaneously\s+pass`; determinism/worker terms within 160 characters of comparator/hybrid/cold/live prerequisite terms; inspected D9 and D15 | No full-axis dependency. The plan supports same-run performance discipline, not importing every M11 limb. |
| Does the plan prohibit scoring above 0.25? | `above\s+0\.25`; `UNLICENSED`; `no.{0,40}frequency`; `Nyquist`; inspected §1, C1, C12, and amendments | Opposite: it requests above-0.25 content and preserves super-Nyquist work. |
| Does the plan make Helicon mandatory later? | every `Helicon` occurrence; `commercial\s+comparator`; `licen[cs]e.{0,30}comparator`; inspected Amendments 2–5 | No. The original says “if obtainable”; the later owner action remains singular and names Zerene. |
| Does the plan require the original M8-O unprojected cross-domain comparison? | normalized searches for output-domain projection, representable intervals, unprojected source bounds, empty/passless hulls, and saturation handling; inspected every hull/certificate prescription | No. The plan requires a zero-invention certificate, but never requires counting values made unreachable solely by the `u16` output domain. |

## Ranked corrections by false-gate reach versus cost

“Axes reached” means axes from which the correction removes this unauthorized
condition. It does **not** claim the axis becomes immediately scoreable; legitimate
capture, geometry, checker, and Zerene blockers remain conjunctive.

1. **Restore Helicon's conditional status — 8 axes, documentation-only.** Change
   “Zerene and Helicon”/“either product” to licensed Zerene plus Helicon when
   obtainable, then re-derive blocker `(d)`. This is the largest false-gate removal
   for the least cost.
2. **Align the terminal gate set with the owner's printable sentence — 5 axes,
   documentation/owner-ratification work.** Either demote M4/M5/M6/M7/M12 from
   terminal vetoes or expand the owner's sentence explicitly. This does not discard
   their evidence; it decides whether each is required to print the named claim.
3. **Remove the complete nonintrinsic M1 dependency bundle — 4 axes,
   documentation/checker-contract work.** Correct rule 4, its `98%` copies, the M2/M4
   joint tuple, M3's global-M1 clause, and M11's “all quality gates” requirement
   together. Editing rule 4 alone unlocks zero.
4. **Make the common-input boundary compatible with C1 — at least 4 axes, higher
   protocol/adapter cost.** Preserve equal inputs without requiring C1 to surrender
   its actual-photosite mechanism before the comparison starts.
5. **Remove or scope rule 7 to the invalidated instrument family — 2 axes plus C1/C12,
   documentation first.** Do not license a high-frequency result until a commissioned
   instrument exists, but do not forbid the plan's frequency region categorically.
6. **Narrow M12's opposed control to production-speed execution rather than all of
   M11 — 1 axis, documentation-only.**
7. **Make the `0.06 s/frame` hybrid limb conditional on the optional backend
   existing — 1 axis, documentation-only.** Retain it as a target/reporting row.
8. **Let M2 report its own verdict without requiring M4/M8 to pass — 1 axis,
   documentation-only.** Keep same-output tuple reporting, but do not turn the
   currently red M8 into a veto on an independently valid noise result.
9. **Replace the impossible historical M8-O domain prospectively — 1 axis in form,
   0 unique current unlock.** The scorecard already specifies the prospective repair;
   M8-R remains independently red, so this corrects attribution rather than producing
   a pass.
10. **Restore the fork arm — 0 axes unblocked, modest build/run cost.** This repairs
   comparator completeness rather than a blocker.
11. **Restore or explicitly narrow M9/M10 product scope — 0 axes unblocked,
   implementation/claim-definition cost.** These prevent future false-green claims.

## Bottom line

The audit found **14 distinct drifts in 58 gate-bearing scorecard blocks**:
four invented prerequisites/domain rules, two optional items hardened into fatal
gates, and eight scope/comparator contradictions. Eleven findings can block an axis, a
plan activity, or the terminal publication sentence; three are nonblocking
weakenings/omissions. The highest-leverage correction is the
Helicon one: the scorecard makes both products mandatory at lines 74–75 and 260–262,
while the plan says “Helicon if obtainable” at lines 1535–1538 and instructs the
owner to license “a commercial comparator” at lines 2302–2305.

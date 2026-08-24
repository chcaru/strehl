# M112 — should the aligner crop instead of enlarge? (Phase 0 go/no-go)

**Milestone:** M112
**Role:** measure the ceiling on removing `fit_to_cover`'s coverage rescale
*before* building anything, and stop if the ceiling is too low.
**Question:** `align_cmd::fit_to_cover` composes a uniform scale `k ≤ 1` onto
**every** placement so that every frame covers every output pixel. The output
keeps its pixel dimensions, so the render is an interpolated enlargement by
`1/k` — **+7.35%** on `bee-3-cpl` (facts 1289, 1400). The docstring declines to
crop instead because that *"would break the byte-frozen measurement path"*. Is
that trade costing the owner real sharpness?
**Status:** **Phase 0 complete. VERDICT: NO-GO. Phases 1 and 2 not built**, per
the pre-registered stopping rule.
**Everything below is MEASURED unless labelled otherwise.**

---

## 0. PRE-REGISTRATION

`experiments/M112-real-pixels/PRE-REGISTRATION.md`, committed at `386ee63`
**before any arm was run** — the ROI, the band, the bar, the arms, the controls
and five falsifiable predictions. That file is the authority; this section is
the summary, and no departure from it was needed.

| | registered |
| --- | --- |
| **ROI** | the 40 sharpest non-overlapping 256 px tiles, **≥ 384 px inside every border**, chosen once on the unresampled control image and reused unchanged by every arm |
| **High band** | **0.30–0.48 cyc/px**, normalised by a 0.02–0.10 cyc/px low band, **band-matched** to each arm's own sampling step |
| **WORTH BUILDING** | recovery **> +0.10 dex** |
| **DEAD** | recovery **< +0.03 dex** |

The ROI is interior by construction and this discharges the brief's requirement
directly: the coverage crop drops 6.85% of width, i.e. **~241 px at each edge**,
and `384 > 241`, so **no tile can touch a region any frame failed to cover.**

Band-matching is also the answer to the brief's Phase 2 worry about putting two
arms of different dimensions on a common footing without resampling the arm
claimed to be sharper: **nothing is resampled — the band edges move, not the
pixels.** An arm sampling at step `s` carries the scene's Nyquist at `0.5·s`.

---

## 1. I built no sharpness instrument (discipline 716, fact 1442)

The brief warned that an instrument had been commissioned three times that
night. Before designing anything I grepped `experiments/`, `docs/research/` and
`SYNTHESIS.md`. **This exact question has been pre-registered and answered
before**, with the same `0.10 dex` bar:

| Where | What |
| --- | --- |
| `experiments/M95-coverage/PRE-REGISTRATION.md` §B2 | the identical question and the identical ship bar |
| `experiments/M95-coverage/src/x8_fix.py` | the harness — `NOW` / `FIX` / `SNAP` arms on real sidecar warps |
| `experiments/M95-coverage/src/m95cov.py` | the instrument — Catmull-Rom gather, band-matched `band_ratio` |
| `experiments/M95-coverage/out/x7b_scale_field.json` | the corrected `k` ladder (X7 was withdrawn as defective) |

So this milestone **contains no sharpness arithmetic of its own.**
`p0_recovery.py` *imports* M95's committed `x8_fix` and `m95cov` and calls them,
changing only two values M95 hard-coded — the sidecar path and `K_COVER`. A copy
can drift from its original; an import cannot.

**Control `C0` — PASSED.** Both imported files are byte-identical to `git HEAD`,
asserted mechanically at run time, so every number below is attributable to
M95's arithmetic rather than to a re-typing of it.

---

## 2. The measurement

Harness `experiments/M112-real-pixels/src/p0_recovery.py`, results
`experiments/M112-real-pixels/out/p0.json`.

**Inputs, per rule 47.** Base image
`C:\dev\strehl-out\M95-resample\single-noalign.tif` (`D1DE6C08…`, 7032 × 4688) —
this is the single unresampled in-focus frame, i.e. fact 1286's own reference
point, and it is built into the statistic: every cost below is measured *against
it*, so the arms are on the published scale by construction. Warp sidecar
`C:\dev\strehl-out\M106\warpmap-corpus-snapshot.txt` (`4B56096D45128083`,
`stack-digest 8d023c0fe355d109`, **299 frames, reference 149**). No file under
`D:\` was opened.

### 2.1 Controls first (rule 9 — run the control *first*, not as a closing check)

| control | true value | read | |
| --- | --- | --- | --- |
| `K1` identity warp, no coverage scale | exactly 0 | **−0.000041 dex** | PASS |
| `K4` integer translation, unit scale | ~0 | **−0.000126 dex** | PASS |
| `SNAP` integer translation, unit scale, real offsets | ~0 if the cost is phase | **−0.0003 dex** | — |

`SNAP` is the finding underneath everything else: **with integer offsets and
unit scale the gather is free.** The entire cost is sub-pixel sampling phase.

### 2.2 The decision arm — and it comes out negative

On the shipped 299-frame / reference-149 solve:

| arm | cost (dex) | sem | n | mean step |
| --- | --- | --- | --- | --- |
| `NOW` — real warp **+** coverage scale `k = 0.9315` | **+0.1813** | 0.0031 | 960 | 0.93327 |
| `FIX` — real warp, coverage scale **removed** | **+0.1855** | 0.0017 | 960 | 1.00190 |
| `NOW_all` — same, **all 299 placed frames** | **+0.1824** | 0.0009 | 11 960 | 0.93282 |
| `FIX_all` — same, all 299 placed frames | **+0.1854** | 0.0005 | 11 960 | 1.00142 |

**Recovery = −0.0042 dex** on M95's 24-frame subsample and **−0.0030 dex** over
all 299 placed frames. I re-chose the frame sampling rather than re-computing
M95's (rule 24) and the answer did not move.

**The registered `DEAD` bar fires.** The recovery is not merely below the
`+0.10 dex` requirement — it is **the wrong sign**. Cropping instead of
enlarging is, if anything, very slightly *worse* than the enlargement it
replaces. It is ~30× below the bar and ~100× below the **0.3693 dex** deficit
(fact 1286) it was meant to explain.

**Input stability (fact 1446).** An independent copy of the same solve
(`ORCH-gallery3`, same SHA-256) was run as a separate arm and reproduced every
number **to the printed digit**. The comparison is not sitting on a poisoned
input.

### 2.3 The brief's sharpest argument is right, and worth 1 frame in 299

The brief's strongest point was that under `k < 1` **even the reference frame is
resampled**, though its transform is identity and it could have passed through
untouched. That is correct, and I measured it. The reference row is identity to
f64 rounding (`a = 0.9999999999999999 − 8.7e-19i`, `b = 0 − 2.2e-16i`):

| the reference frame alone | cost (dex) | sem |
| --- | --- | --- |
| `REFONLY_NOW` — with the coverage scale | **+0.1836** | 0.0132 |
| `REFONLY_FIX` — coverage scale removed | **−0.0000** | 0.0028 |

**Recovery for that frame: +0.1836 dex.** Under `NOW` the one frame that needs
no warping pays the full resampling price; under `FIX` it becomes an exact
no-op. The mechanism the brief described is real and is now measured.

It is also worth **one frame out of 299**, which is why the whole-render number
is zero.

**This doubles as the rule-20 discharge.** Before running a gate you must name
an input that would make it fail and check that such an input exists. `REFONLY`
**is** that input: on the same tiles, the same band and the same instrument, the
recovery arm reads **+0.1836 dex**, far above the `+0.10` bar. The gate has the
power to fire. It did not fire on the real warp set.

### 2.4 The brief's proposed null fires — as pre-registered — and voids nothing

The brief required a null on *"a stack where `fit_to_cover` already returns
k ≈ 1.0 … Arms 1 and 2 must then agree to within noise. If this null shows a
difference, your instrument is measuring something other than the scale and
every other number is void."*

I registered **before running** that this null would fire and must not void
anything. It fires:

| arm | cost (dex) |
| --- | --- |
| identity sidecar, `k = 0.9974` | **+0.1851** |
| identity sidecar, `k = 0.9315` | **+0.1836** |
| identity sidecar, `k = 1.0` (exact no-op) | **−0.0000** |
| **difference** | **+0.1851** |

The null is misdesigned, and the brief's own fact 1419 says why: the cost is a
**threshold on whether the sampling phase is integral**, not a dose in `|1−k|`.
On an identity sidecar `k = 1.0` is an exact no-op while `k = 0.9974` is a full
non-integer resample, so the two arms are **maximally** different rather than
equal. **A 0.26% enlargement costs the same as a 7.35% one.**

Had I run the brief's rule as written, a correct instrument would have declared
its own valid measurements void. **A null whose true value is not zero is not a
null** — it is a positive control wearing a null's name. I substituted `K1`,
whose true value is zero by construction, plus a byte-identical input re-run.

This also independently reproduces M95's corrected X7B ladder (`k = 0.9974`
→ +0.1851 there, +0.1851 here) and agrees with M104's P4 dose ladder from a
completely different instrument on a real photograph.

---

## 3. Scope — is this specific to the owner's bracket, or corpus-wide?

`bee-3-cpl` has 6.05 px mean per-frame displacement, so its gather is already
deeply non-integer and removing `k` cannot rescue it. A **shallow** stack was
the live possibility. Scanned nine real sidecars with the same imported
arithmetic, the same tiles and the same band
(`src/p0b_scope.py`, `out/p0b.json`).

**Gate on the `fit_to_cover` port (rule 21 — gate a computed constant against an
independently predicted value).** The scan needs `k` per stack, so
`fit_to_cover`'s corner bisection is ported. It refuses to print unless it
reproduces two values obtained by routes independent of this code:

| stack | port | expected | source | |
| --- | --- | --- | --- | --- |
| `bee-3-cpl` | **0.931464** | 0.9315 ± 1e-4 | tool printout (fact 1400) + ruler photograph (fact 1289, M98) | PASS |
| `flat-on-ruler-cpl` | **0.970798** | 0.970813 ± 2e-3 | M104 P1, `1/k = 1.030078` | PASS |

| stack | N | `k` | enlargement | int-phase % | `NOW` | `FIX` | recovery | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `bee-3-cpl` | 299 | 0.93146 | 7.36% | 0.3% | +0.1824 | +0.1854 | **−0.0030** | DEAD |
| `flat-on-ruler-cpl` | 79 | 0.97080 | 3.01% | 1.3% | +0.1955 | +0.1800 | **+0.0155** | DEAD |
| `tweezers-cpl` | 100 | 0.97261 | 2.82% | 1.0% | +0.1941 | +0.1791 | **+0.0150** | DEAD |
| `leaf-2-cpl` | 182 | 0.93441 | 7.02% | 0.5% | +0.1832 | +0.1874 | **−0.0042** | DEAD |
| `foam` | 100 | 0.87609 | 14.14% | 1.0% | +0.1542 | +0.1872 | **−0.0330** | DEAD |
| `lavendar-cpl` | 299 | 0.93865 | 6.54% | 0.3% | +0.1907 | +0.1787 | **+0.0120** | DEAD |
| `flowers-cpl` | 176 | 0.93677 | 6.75% | 0.6% | +0.1814 | +0.1863 | **−0.0049** | DEAD |
| `lead-1-cpl` | 123 | 0.95641 | 4.56% | 0.8% | +0.1923 | +0.1838 | **+0.0085** | DEAD |
| `flower-bud-alone-cpl` | 205 | **0.99700** | **0.30%** | **17.1%** | +0.1786 | **+0.0270** | **+0.1516** | **SHIPS** |

**Eight of nine are DEAD**, spanning −0.0330 to +0.0155 dex against a `+0.10`
requirement.

**`foam` is the one to look at twice.** Its **14.14% enlargement is the largest
in the corpus** and its recovery is the **most negative**. Cost is not
proportional to enlargement; over this range it is close to inverted. That
independently reproduces M95's X7B ladder and M104's P4 (*"Cost ∝ enlargement is
false"*) on a third instrument.

**The exception is the mechanism in one row.** `flower-bud-alone-cpl` has the
*smallest* enlargement here (0.30%) and is the only stack that ships, because
its per-frame warps are near-identity (`|a|−1` within ±1.3e-4, mean `|b|`
0.054 px, max 0.38 px) — so removing `k` leaves a **near-no-op** rather than
another non-integer gather. The solve is not degenerate: 205 distinct scales and
205 distinct translations. **The crop pays exactly when the warp is already
integer-phase, and not otherwise.**

**Caveat, stated (rule 8).** `int-phase %` is `|a−1| < 1e-4` and both
translations within 0.05 px of an integer. It **undercounts**: `flower-bud`'s
`FIX` cost of +0.0270 is far below what 17.1% of frames going free would
explain, because the gather stays cheap out to ~0.125 px of offset (M95's DOSE
control). Reported as **indicative, not calibrated**. Its value is that it is a
predictor computable **from the sidecar alone, with no render**.

**Second caveat.** Sidecars other than `bee-3-cpl`'s are single quarantined
copies; only `bee-3-cpl`'s is confirmed byte-identical across three independent
milestones. Given rule 45's documented sidecar thrash, the eight non-`bee` rows
are **indicative of geometry**, and the decision-relevant row is `bee-3-cpl`.
`arm()` prices a *mapping*, not a stack's own pixels, so this scan prices
**geometry** — that is the correct isolation for this question, and it is what
M95's committed harness does.

---

## 4. Fact 1419 was measured on an 8-frame sidecar (rule 47)

`x8_fix.py` is committed **twice**, with **opposite-signed** headlines and
**no change to its arithmetic** — the only diff is a fallback sidecar path:

| commit | `NOW` | `FIX` | recovery |
| --- | --- | --- | --- |
| `1024ddc` | +0.1813 | +0.1855 | **−0.0042 dex** |
| `2a4ebac` | +0.1844 | +0.1701 | **+0.0143 dex** ← folded as **fact 1419** |

I tested this rather than asserting it, by running the same arithmetic against
each candidate input:

| input | `NOW` | `FIX` | `SNAP` | `K1` | recovery |
| --- | --- | --- | --- | --- | --- |
| 299 frames, ref 149, digest `8d023c0fe355d109` (`4B56096D…`) | +0.1813 | +0.1855 | −0.0003 | −0.000041 | **−0.0042** |
| **8 frames, ref 4**, digest `165a1ff35968c615` (`3158ADEF…`) | **+0.1844** | **+0.1701** | **−0.0002** | −0.000041 | **+0.0143** |

The 8-frame sidecar reproduces **all four** of fact 1419's published quantities
**digit for digit**, and the 299-frame solve reproduces commit `1024ddc`'s
equally exactly. The two sidecars carry **different `stack-digest` values**, so
they are not two copies of one solve — the aligner itself recorded them as
different stacks.

**So fact 1419's `+0.0143 dex` is a number about an 8-frame solve over a
different subset from a different reference — not about the shipped render**,
whose every corpus quality number uses 299 frames at reference 149. This is
rule 45's sidecar thrash landing *inside a folded fact*. The row's **verdict is
unaffected** — both inputs are DEAD, and the real solve is more dead — but its
provenance is not what the row says, and the arithmetic in its "7.8% of the
gather cost" clause is computed from the wrong stack.

`x8_fix.py`'s own docstring and printout say *"299 placed frames"*; the JSON it
writes records `n_frames: 24` and **no frame count and no sidecar identity**.
That is exactly the hole rule 47 exists to close, in a milestone that ran two
hours after rule 47 was written.

---

## 5. VERDICT — NO-GO, and Phase 1 was not built

**Phase 0's registered stopping rule fires.** On the owner's photograph the crop
recovers **−0.0030 dex** of a **0.3693 dex** deficit. The pre-registered
requirement was **+0.10 dex** and the pre-registered `DEAD` line was **+0.03**.

The reason, in one sentence: **`fit_to_cover` returns one composed mapping and
one gather, so removing `k` moves the sampling step from 0.9315 to 1.0014 —
which is still non-integer, and any non-integer step pays nearly the full
price.** Confirmed here on a third independent instrument, with a positive
control (`REFONLY`, +0.1836 dex) proving the bar was reachable.

**The +7.35% enlargement is still real, still an unpaid bill, and still worth
removing on its own terms** — it costs the owner 7% of linear resolution as a
*geometry* fact, and facts 1289/1400 stand. What is now measured is that
removing it **is not a sharpness fix**, on eight of nine real stacks and most
firmly on the one the owner is complaining about. Fact 1402's recommendation
survives; its ranking was already retracted by fact 1419 and is now retracted
by measurement on the real solve too.

**The lever is elsewhere and the corpus already names it**: the gather kernel.
Fact 1420 measures `lanczos3` at **−0.0663 dex** against the shipped
`catmull-rom`'s **−0.2006 dex** — a gain of **+0.1343 dex**, which that row puts
at **9.4× the rescale fix**, with a verified patch already carried in
`crates/strehl-cli/examples/m95-lanczos.rs`. Fact 1374 confirms the same lever
by eye at 1:1, and fact 1373 records that the kernel is **already switchable end
to end**. My −0.0030 dex sits against that +0.1343 dex.

I did **not** implement `STREHL_FIT=crop`, did not touch
`crates/strehl-cli/src/align_cmd.rs`, did not add a byte-freeze row, and did not
render the Phase 2 comparison. Building a CFA-phase-safe crop, a new output
geometry and a freeze row to buy −0.003 dex would be work with a measured
negative return.

---

## 6. Lane and hygiene

- **Files changed: none in `crates/`.** No edit to `align_cmd.rs`, `merge.rs`,
  `merge_cmd.rs` or `align.rs`. M110's `pen_w` clippy failure was not touched.
- Everything written lives under `experiments/M112-real-pixels/`. Renders and
  scratch would have gone to `C:\dev\strehl-out\M112\`.
- `D:\personal\macro` and `D:\macro-dark-frames` were **never opened** — not
  read, not written. Every input came from `C:\dev\strehl-out\`.
- Commits are path-scoped (`git commit -- <paths>`, rule 42) and each was
  audited with `git show --name-only`. No `git add -A`, no directory adds, no
  push.
- **Rule 41:** there is **no `M112` row in the AGENTS.md ledger.** I did not add
  one — the ledger is written at dispatch by the orchestrator. No collision:
  no `docs/research/M112*`, no `experiments/M112*` and no `M112` in any commit
  subject before this milestone.

---

## 7. Candidate facts (rule 28 — numbered `P1…`, absolute numbers are the orchestrator's)

**P1 — MEASURED.** Removing `fit_to_cover`'s coverage scale from the shipped
299-frame / reference-149 `bee-3-cpl` solve recovers **−0.0030 dex**
(all 299 placed frames; **−0.0042** on a 24-frame subsample) of high-band power
over 0.30–0.48 cyc/px, against a pre-registered `+0.10 dex` ship bar and a
`+0.03 dex` DEAD bar. **The crop is not a sharpness fix**, and its sign is
negative. Controls `K1 −0.000041`, `K4 −0.000126`, `C0` byte-identical to HEAD.

**P2 — MEASURED.** The brief's claim that the coverage scale needlessly
resamples the reference frame is **correct and priced**: the reference row is
identity to f64 rounding, and alone it goes from **+0.1836 dex** of loss under
the scale to **−0.0000 dex** without it. It is **one frame in 299**, which is
why the whole-render recovery is zero. This arm doubles as the rule-20 proof
that the `+0.10 dex` gate could have fired.

**P3 — MEASURED.** Across **nine** real sidecars the crop is DEAD on **eight**,
spanning **−0.0330 to +0.0155 dex**. The exception, `flower-bud-alone-cpl`,
recovers **+0.1516 dex** and has the **smallest** enlargement of the nine
(0.30%, `k = 0.99700`) with near-identity warps (`|a|−1` ≤ 1.3e-4, mean `|b|`
0.054 px) and a non-degenerate solve (205 distinct scales). **The crop pays
exactly when the warp is already integer-phase.** `foam`, with the **largest**
enlargement (14.14%), has the **most negative** recovery (−0.0330) — cost is not
proportional to enlargement and over this range is close to inverted,
independently reproducing M95's X7B and M104's P4 on a third instrument.

**P4 — MEASURED.** Fact 1419's published quantities (`NOW +0.1844`,
`FIX +0.1701`, `SNAP −0.0002`, `K1 −0.000041`, recovery `+0.0143`) reproduce
**digit for digit** against an **8-frame, reference-4** quarantined sidecar, and
**not** against the 299-frame / reference-149 solve, which instead reproduces
the earlier commit `1024ddc`'s numbers exactly. **Fact 1419 is a measurement of
an 8-frame solve over a different subset from a different reference than the
render every corpus quality number is measured on.** Its DEAD verdict is
unaffected and is strengthened; its provenance and its "7.8% of the gather cost"
arithmetic are not what the row says.

**P5 — MEASURED.** The brief's proposed null — *"a stack where `fit_to_cover`
already returns k ≈ 1.0; arms 1 and 2 must agree to within noise"* — **fires at
+0.1851 dex**, pre-registered as a prediction before running. On an identity
sidecar `k = 1.0` is an exact no-op while `k = 0.9974` is a full non-integer
resample, so the arms are **maximally different by construction**. Applied as
written, the brief's rule would have voided a correct instrument's valid
measurements.

**P6 — MEASURED.** A port of `align_cmd::fit_to_cover`'s corner bisection
reproduces `k = 0.931464` for `bee-3-cpl` against **0.9315** measured by two
routes independent of the code (the tool's own printout, fact 1400; a photograph
of a millimetre ruler, fact 1289 / M98) and `0.970798` for
`flat-on-ruler-cpl` against M104 P1's `1/k = 1.030078`. `fit_to_cover` is
therefore reproducible outside the binary, which makes `k` a **sidecar-derivable
quantity** needing no render.

**P7 — ARGUED, routed, not adjudicated.** M104 §2.3 registered that on
`flat-on-ruler-cpl` *"the fix's ceiling is also its floor: it should recover
essentially all of it"*, predicting post-fix `+0.0049 ± 0.0073` dex. My arm on
that stack's geometry recovers **+0.0155 of +0.1955** — it leaves +0.1800, not
~0. The instruments differ (M104's baseline is an unregistered *merge* in object
space; mine is a single unresampled frame), so this is **not** a refutation and
I do not claim one. It is a live disagreement worth scoring now that M95's fix
exists, and I am not the agent to score it.

## 8. Candidate disciplines

**D1 — A null whose true value is not zero is a positive control wearing a
null's name, and it will void correct work.** The brief specified a null and a
consequence (*"every other number is void"*) whose premise its own cited fact
contradicted. Before accepting a null, compute what it reads **when everything
is working**; if that is not zero, it is not a null. Pre-register the prediction
so the disagreement is visible before the number can be argued about.

**D2 — A sidecar is an input, so a result without its sidecar's identity is not
a record.** `x8_fix.py` printed its frame count but wrote **neither the frame
count nor the sidecar identity** into the JSON that was folded, and the same
arithmetic on two different sidecars produced opposite-signed headlines. Rule 47
should name **the warp sidecar, by SHA-256, frame count and reference index**,
alongside the flags and the environment.

**D3 — When two committed runs of one harness disagree and the code did not
change, the input changed: find it, do not average it.** Re-running each
candidate input under the original arithmetic attributed both numbers exactly
and cost one command. The alternative — treating the discrepancy as noise —
would have left a folded fact pointing at the wrong stack.

**D4 — Reason about a resampler's cost as a threshold on sampling phase, never
as a dose in the geometric change.** Three independent instruments now agree
(M95 X7B, M104 P4, M112 §2.4/§3): a 0.30% enlargement costs the same as a 7.35%
one, and the *largest* enlargement in the corpus has the *smallest* cost.
Fact 1402 was wrong for exactly this reason and it is an easy error to repeat —
the size of a geometric change carries almost no information about the size of
its quality effect.

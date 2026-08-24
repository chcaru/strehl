# M112 — pre-registration, Phase 0 (the go/no-go gate)

Written and committed **before any arm was run**. Nothing below was chosen after
seeing a number produced by this milestone.

## The question

`align_cmd::fit_to_cover` composes a uniform scale `k <= 1` onto **every**
placement so that every frame covers every output pixel. The output keeps its
pixel dimensions, so the render is an interpolated enlargement by `1/k`. On
`bee-3-cpl`, `k = 0.9315`, i.e. **+7.35%** (facts 1289, 1400).

The proposal is to **crop instead of enlarge**: force `k = 1.0`, keep the warps,
and emit only pixels every frame genuinely covers.

**Phase 0 asks one thing: how much high-band power does that recover?**

## Prior art searched first (rule 40, discipline 716, fact 1442)

Grepped `docs/research/`, `experiments/` and `SYNTHESIS.md` for this question
before designing anything. It has been asked before and I am **not** building a
new instrument:

| Where | What it is |
| --- | --- |
| `experiments/M95-coverage/PRE-REGISTRATION.md` §B2 | the identical question, with the identical `0.10 dex` ship bar |
| `experiments/M95-coverage/src/x8_fix.py` | the harness — real sidecar warps, `NOW`/`FIX`/`SNAP` arms |
| `experiments/M95-coverage/src/m95cov.py` | the instrument — Catmull-Rom gather, band-matched `band_ratio` |
| `experiments/M95-coverage/out/x7b_scale_field.json` | the corrected `k` ladder (X7 was withdrawn as defective) |
| `experiments/M88-optical-ceiling/src/` | the ISO-12233 slanted-edge SFR estimator |
| `experiments/M104c-mtf/mtf.py` | the validated ISO-12233 implementation |
| SYNTHESIS facts 1286, 1287, 1289, 1400, 1402, 1419 | the folded record |

**I reuse M95's instrument.** The gather and the band statistic are taken
verbatim; the only edits are to *inputs that were hard-coded* (the sidecar path,
`K_COVER`) and the output path. A byte-level check that the arithmetic is
unchanged is part of the run (`C0` below).

## ROI — chosen on geometry, before any arm is read

`m95cov.pick_tiles`: the **40 sharpest non-overlapping 256x256 tiles** of the
base image, constrained to lie at least `PAD = 384 px` inside every border.

- Tiles are selected **once, on the unresampled control image**
  (`single-noalign.tif`), and the *same* tile list is used by every arm. No arm
  can move the ROI, so the ROI cannot be tuned to an answer.
- **Interior by construction.** The coverage crop drops 6.85% of width, i.e.
  ~241 px at each edge. `PAD = 384 > 241`, so **no tile can touch a region any
  frame failed to cover.** This discharges the brief's requirement directly.
- Selecting the *sharpest* tiles is a power choice, not an outcome choice: a
  flat tile has no high band to lose. It is applied identically to all arms.

## High band — stated in cyc/px

- **High band: 0.30–0.48 cyc/px.** Normalised by a **low band of 0.02–0.10
  cyc/px**; the statistic is `log10(mean high power / mean low power)`, in dex.
- **Band-matched.** An arm sampling the source at step `s` carries the scene's
  Nyquist at `0.5*s`, so its band edges are scaled by its own `s`. Comparing at
  a fixed cyc/px band across arms of different sampling density is a units error
  that penalises the magnified arm and compares real content against a
  guaranteed spectral hole above `0.5*s`. (M95 §B3 measured that bias at
  **−0.0112 dex**.) This is also the answer to the brief's Phase 2 question of
  how two arms with different dimensions are put on a common footing **without
  resampling either one**: nothing is resampled — the *band edges* move, not the
  pixels.
- Cost of an arm = `band_ratio(unresampled base) − band_ratio(arm)`, in dex.
  Positive = sharpness lost.

## Bar — registered before measuring

- **WORTH BUILDING if recovery > +0.10 dex.** Adopted from the brief and
  identical to M95 §B2's ship bar, so the two are directly comparable.
  Justification: the deficit to be explained is **0.3693 dex** (fact 1286). A
  fix that returns less than ~27% of it does not change what the owner sees,
  and Phase 1 costs a new output geometry, a CFA-phase hazard, and a byte-freeze
  row. `0.10 dex` is a 1.26x power ratio — about the smallest change I would
  defend as visible at 1:1.
- **DEAD if recovery < +0.03 dex.** Adopted from M95 §B2 for comparability.
- Between the two: partial, reported as such, no build without a further ruling.

## Arms

| arm | what |
| --- | --- |
| `NOW` | real per-frame warps **with** the coverage scale `k = 0.9315` — what ships today |
| `FIX` | the same warps with the coverage scale **removed** (`k = 1.0`) — the crop |
| `SNAP` | integer translation, unit scale — the geometry floor; no aligner can beat it |
| `BASE` | the single unresampled in-focus frame — fact 1286's reference point (the control) |
| `REFONLY` | `NOW` vs `FIX` for the **reference frame alone**, whose warp is exact identity |

`REFONLY` is new in this milestone. It prices the brief's sharpest claim — that
under `k < 1` even the reference frame, which needs no warping, is interpolated
for nothing.

## Controls

- **`C0` arithmetic-unchanged.** The `arm()` gather and `m95cov.band_ratio` must
  be **AST-identical** to M95's committed versions. Asserted mechanically.
- **`K1` null.** Identity warp, no coverage scale. True value is exactly zero.
  Must read `|cost| < 0.005 dex`. If it fails, no arm is reported.
- **`K4` integer shift.** An integer translation at unit scale must read ~0.
- **`SNAP`** doubles as the positive-direction anchor: it must be ~0 if the cost
  really is sub-pixel phase.
- **`INPUT`** — every arm records the **SHA-256, frame count and reference** of
  the sidecar it read. Rule 47: a number without its whole invocation is not a
  record, and an unrecorded sidecar is exactly how this measurement has already
  gone wrong once (see below).

## The brief's null is misdesigned — registered here, before running

The brief specifies: *"the same comparison on a stack where `fit_to_cover`
already returns k ≈ 1.0 … Arms 1 and 2 must then agree to within noise. If this
null shows a difference, your instrument is measuring something other than the
scale and every other number is void."*

**I register, in advance, that this null will FIRE, and that its firing must not
void anything.** The reasoning is the brief's own fact 1419: the cost is a
*threshold on whether the sampling phase is integral*, not a dose in `|1-k|`. On
a stack whose sidecar is identity, `k = 1.0` makes every placement an exact
no-op (integer phase, free) while `k = 0.9974` is a full non-integer resample.
The two arms are therefore **maximally** different, not equal.

This is already measured on the committed corrected ladder
(`x7b_scale_field.json`): **`k = 0.9974` costs +0.1851 dex**, against `k =
0.9315`'s **+0.1836** and `k = 1.0`'s **−0.0000**. A 0.26% enlargement costs the
same as a 7.35% one.

- **Prediction: the brief's null reads ~+0.18 dex, not ~0.**
- I therefore substitute a null whose true value **is** zero by construction:
  `K1` (identity warp, no coverage scale), plus re-running an arm on a
  byte-identical input and requiring the identical number.
- I run the brief's version anyway, as `NULLQ`, and report it as a **threshold
  probe**, not as a null.

## An input-provenance defect I must not repeat

`x8_fix.py` has been run twice and committed twice with **opposite signs** on
its headline:

| commit | `NOW` | `FIX` | recovery |
| --- | --- | --- | --- |
| `1024ddc` | +0.1813 | +0.1855 | **−0.0042 dex** |
| `2a4ebac` | +0.1844 | +0.1701 | **+0.0143 dex** ← folded as fact 1419 |

The only code change between them was a **fallback sidecar path**. The
arithmetic is identical, so the input must have changed. I will test that
directly (`A1`/`A2`) rather than assert it.

## Predictions, registered

1. `FIX` recovers **between −0.01 and +0.03 dex** on the real 299-frame warps →
   **NO-GO**, below both the 0.10 bar and the 0.03 DEAD line.
2. `SNAP` reads ~0, confirming the cost is sub-pixel phase.
3. `REFONLY` shows a **large** recovery for that one frame (it becomes a true
   no-op) — and is worth **~1/299 of the render**, so it does not move the total.
4. The 8-frame sidecar reproduces fact 1419's `+0.0143`; the 299-frame sidecar
   reproduces `−0.0042`.
5. `NULLQ` fires at ~+0.18 dex.

If prediction 1 holds, **Phase 0 stops the milestone and Phases 1 and 2 are not
built.** That is the registered success condition for a negative result.

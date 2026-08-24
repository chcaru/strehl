# M97q — wiring `photometric.rs` into the merge

Status: SHIPPED, opt-in, default OFF. Milestone M97, at the orchestrator's
request after its unwired-subsystem inventory (facts 1449–1450).

## 1. What it is

`--photometric` (and `STREHL_PHOTOMETRIC=1`) fits a per-frame affine
photometric gain and applies it to every frame before the focus measure.

`photometric.rs` — 1365 lines, 24 passing tests — had **no caller outside
`lib.rs` and `examples/`**. It compiled clean, its tests were green, and its
results had been folded as measured, while the render never called it. `pub`
suppresses `dead_code` in a lib crate, so every green signal was telling the
truth about code that did nothing. This milestone connects it.

**The job was connection, not construction.** The affine form, the fitting
rule, the region and the noise interaction were all decided and written down in
`docs/research/M99-photometric.md`. Nothing here re-derives them.

## 2. The four decisions, stated because each one invalidates something if wrong

**Ordering: the gain is applied AFTER registration and BEFORE the focus
measure.** The field, the gate and the estimator therefore all see normalised
data. The orchestrator's stated fear — that this would retire every gate number
in the corpus — does not materialise, but not for the reason M99 gives. See §4.

**Propagation: ON.** The noise model is scaled with the data. This is not
optional and it is the single most important line in the patch: the model is
`σ²(S) = g·S + (RN·g)²`, so scaling data by `c` without scaling the model
under-estimates σ by between `√c` and `c`, and the gate — which is calibrated
in units of focus noise — then misfires on exactly the frames that were
brightened. Bar F2r-ii below is a plant that proves this line is load-bearing.

**Statistic: the MEAN, never a median.** M28 §6 and M99 §13.1 measured this
independently: mean 0.0216% against median 7.9376% spurious gain, a factor of
**368.1**. A median over a subject-weighted area absorbs focus signal and calls
it exposure. This is the third independent confirmation in the corpus
(M87 98.8×, M99 Phase C 18.2 vs 8.7).

**Region: a fixed, reference-derived, ERODED low-detail region — not the whole
frame.** M28 §6 says "all pixels" and M99 §7.3 says "a region"; both are right
on different axes. M28's warning was against a *subject-centred* region, which
is a real trap; M99's region is deliberately subject-*avoiding*, so it dodges
that error from the other side. The reason the whole frame is wrong is
measured: on the two auto-exposure decks the whole-frame and background flux
ladders sit **7.1%** (`bee-3-cpl`) and **5.5%** (`bee-2-cpl`) apart, because the
AE meter holds *total* flux roughly constant while defocus moves light between
the sharp core and the smooth surround. Correcting with the whole-frame ladder
left **44%** and **42%** of the defect standing.

Erosion (16 px) is not a refinement either. On a flux-conserving blur sweep
whose true answer is exactly zero, M99's own un-eroded mask reports **3.63%**
spurious gain against a registered 2× bar — **168× over** — because defocus
spills light across the mask's long perimeter. Eroded: **0.0000%**.

## 3. Pre-registered bars and results

Written before the code (`prereg-F.txt`). Fast config: `flat-on-ruler-cpl`,
`--limit 20 --gate 4`, `STREHL_ALIGN=0`, private cache — the same config that
recorded `09FA927898ABF314` at commit `8e5eb6e`, so F1 compares against a hash
taken before this work existed.

| bar | result |
|---|---|
| F1 default path bit-identical | **PASS** — `09FA927898ABF314`, exact |
| F1b plant: flag must move bytes | **PASS** — `878E16DD07D17D15` |
| F5 env twin equals flag | **PASS** — identical hash |
| F2 election neutrality via `--index-map` | **VACUOUS — see §4** |
| F2b plant on `--index-map` | **FAILED — 0 px, same as the null** |
| F2r-i gain reaches the gate (`n_eff`) | **PASS** — 289 835 px, 3.51% |
| F2r-ii plant: propagation is connected | **PASS** — 763 987 px, 9.26% |
| F3 fit is real and reported | **PASS** — span 1.0220 over 20 frames |
| F4 region guard refuses on a sliver | **UNEXERCISED** — see §6 |

Byte-freeze 5/5 HOLD (both frozen rows, including the sidecar row
`119936E6…`), 67 unit tests pass, `clippy --bins --all-targets` exit 0,
`corpus_lint.py` 0 violations.

## 4. The pre-registered bar that was vacuous, and what the plant found

**F2 read `0 px re-elected` out of 8 250 880 — and so did its plant.** Under
discipline 598 that is not a null; it is a disconnected probe, and it would
have shipped as a headline "election neutrality confirmed, 0 px" if the plant
had not been mandatory.

**Diagnosis, MEASURED:** `merge_cmd.rs:1788` writes the election map from
`p1.stats.best_index()`, and the photometric fit is built at `:1837` — *after*
it. Pass one runs with `photometric: None` because the gains cannot exist until
pass one has read every frame. So the election map is uncorrected in **both**
arms by construction, and `--index-map` is structurally incapable of expressing
the photometric term. The instrument could not see the quantity.

The plant was re-aimed onto `n_eff`, which is a pass-**two** quantity and is
precisely what the noise calibration controls. It then fired: breaking the
propagation while leaving the gain applied — exactly the bug M99 warns is
silent — moved **763 987 px (9.26%)** and dropped mean `n_eff` from 4.5638 to
**4.5256**, with the merged bytes differing. The real effect is 3.51%, so the
plant separates from the signal by 2.6× in the same instrument.

**Consequence for the corpus, which is better news than expected.** The
election in this pipeline is decided *entirely in pass one*, which never sees a
gain. Election neutrality is therefore true **by construction**, not by M99's
invariance argument — a stronger and simpler guarantee. **No election-based
measurement in the corpus is invalidated by this wiring**, and none of M99's
`contrast/σ` invariance reasoning is tested by anything I ran. Gate and `n_eff`
numbers measured *with* `--photometric` are a different pipeline from those
measured without it; the flag defaults OFF so no existing number moves.

## 5. What is NOT claimed

**No quality number.** M99's headline **+6.88%** early-decile figure was fitted
over the un-eroded region that leaks 3.63% of flux, so it is an inflated upper
bound of unmeasured size and is not reproduced here. This milestone corrects
frame **level**. Whether it sharpens anything is for a verifier.

The measured span on the fast config is **1.0220** — 2.2% of drift on a stack
that is not one of the owner's. M24's corpus range is 0.91% to 11.70%.

## 6. Known gaps

**F4 is UNEXERCISED, not passed.** The region guard (`< 1024 px` after erosion
⇒ refuse) never fired: the ruler stack keeps 1 744 561 px of 2 558 489 (68.2%).
It is a live path with no real-data evidence, exactly as E4 was for the n_eff
range guard. Recording it as PASS would be the disconnected-probe error again.

**A photometrically refused frame is merged uncorrected at gain 1.0, not
dropped.** Its geometry is still good and gain 1.0 is exactly the status quo
for it. The refusal is reported once before the passes run. Not exercised on
real data.

**One extra decode.** The region prologue decodes the reference frame once
(~130 ms) to build and erode the mask, and only when the flag is on.

## 7. Facts

- **V1** (MEASURED) `photometric.rs`, 1365 lines and 24 green tests, had no
  caller outside `lib.rs`/`examples/` before this commit. `pub` suppresses
  `dead_code` in a lib crate, so it compiled and tested clean while the render
  never called it.
- **V2** (MEASURED) With `--photometric` absent, the merged image is
  bit-identical to the hash recorded at `8e5eb6e`: `09FA927898ABF314`. With the
  flag it is `878E16DD07D17D15`; `STREHL_PHOTOMETRIC=1` reproduces the flag
  exactly.
- **V3** (MEASURED) `--index-map` cannot express the photometric term in either
  arm: the election map is written at `merge_cmd.rs:1788` from pass one's
  `best_index()`, and the fit is built at `:1837`. The comparison and its plant
  both read 0 px of 8 250 880.
- **V4** (MEASURED) On `n_eff`, a pass-two quantity, the gain moves 289 835 px
  (3.51%) and a deliberately mis-propagated build — gain applied, noise model
  held — moves 763 987 px (9.26%), dropping mean `n_eff` 4.5638 → 4.5256. The
  noise propagation is connected and load-bearing.
- **V5** (DERIVED, from V3) Election neutrality under photometric correction is
  true by construction in this two-pass design, because pass one never sees a
  gain. No election-based corpus measurement is invalidated by this wiring, and
  M99's `contrast/σ` invariance argument is untested by anything measured here.
- **V6** (MEASURED) The eroded region keeps 1 744 561 px of 2 558 489 (68.2%)
  on `flat-on-ruler-cpl`; fitted gain span over 20 frames is 1.0220.

## 8. Disciplines

- **D-V1** A pre-registered bar can be vacuous in a way only its plant reveals.
  F2 and its plant both read exactly 0 px; the bar looked like a clean null and
  was a dead probe. Re-aim the plant at a quantity the code path can actually
  reach, and report the vacuous bar rather than deleting it.
- **D-V2** Before believing a two-pass pipeline is invariant under a change,
  check *which pass* computes the thing you are measuring. The election was
  immune here for a structural reason, not the physical one the design document
  gave, and only the line numbers distinguish those two explanations.
- **D-V3** When wiring an existing subsystem, the neighbouring rule is often the
  opposite one. Scaling *data* by `c` and correcting an unchanged frame *by* `c`
  transform the noise model in opposite directions; copying the wrong one
  under-estimates σ silently.

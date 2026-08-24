# M101 — did removing the coverage rescale do what it claims? (independent verification)

**Milestone:** M101
**Role:** independent verifier of M95's coverage-rescale fix. M95 implements;
M95 does not verify its own work.
**Question:** `fit_to_cover` scales the field of view by `k ≤ 1` and then
upsamples back to the original output dimensions, so every registered render is
an interpolated enlargement by `1/k` (M98 P10: `k = 0.9315` on `bee-3-cpl`,
**+7.35%**). M95 is changing the merge to emit the cropped region at its
**native sampling**. Does that do what it says, and does it buy what was
predicted?
**Status:** Phase 1 complete — baseline established and bars registered before
the fix exists. Phase 2 pending M95.

---

## 0. PRE-REGISTRATION

The full pre-registration is `experiments/M101-resample-verify/PREREG.md`,
committed **before the fix existed and before any post-fix number existed**
(rule 12). This section is the summary; that file is the authority, and every
departure is declared in the report as a departure.

**HEAD:** `6a8ac3078d4c11df7ac9818fda0c381dd7fd625e`.
**Fix status at pre-registration: NOT LANDED** — `merge_cmd.rs:1246` still reads
*"then upsampled to keep the output dimensions"*, verified before writing.
Every baseline number below is a genuine *before*.

**Milestone number.** `M101` claimed after checking for a stem collision: no
`docs/research/M101*`, no `experiments/M101*`, no `M101` in any commit subject,
zero mentions in `SYNTHESIS.md` or `docs/`. `M100` is the frontier. (The
orchestrator warned that `M93` is held by two agents.)

### Why this instrument, and why not the obvious ones

1. **The output dimensions change**, so any tile mapping that assumes
   7032 × 4688 will silently mis-register after the fix and read as blur. A
   millimetre ruler is **dimension-agnostic by construction**: tick pitch is a
   physical constant, so the comb frequency measures the *sampling*, and a
   change of dimensions at unchanged sampling reads as **no change**.
2. **A "sharper" verdict from a gradient-energy metric is inadmissible.** Fact
   1273 records its **third independent death**. Discipline 605 and fact 1235
   both stand **RETRACTED** (fact 1250) — which, per discipline 633, forecloses
   re-deriving the claim rather than inviting it. No such metric appears here.
3. **Magnification reads as sharpness** (discipline 606; fact 1250 is that error
   made a second time in one night). A pixel-space comparison of pre- against
   post-fix is contaminated *by the very quantity being fixed*.

**Rule 18, stated for the headline.** Removing an upsample makes the render
smaller in pixels, so **every per-pixel metric improves for free**. That bias
runs toward "the fix worked". Every headline here is in **object space**; any
pixel-space number is a labelled diagnostic.

### Hypotheses and falsifiers

| # | Hypothesis | Falsifier |
|---|---|---|
| **H1** | the fix removes the resample: ruler magnification reads **1.000** where it now reads ~1.030 | post-fix \|`mag` − 1\| > 2 SE, either direction |
| **H2** | the fix recovers resolved detail in object space | post-fix modulation ratio < 1.000 − 2 SE |
| **H3** | the fix changes sampling, **not** field of view | subject extent moves > 1% |
| **H4** | the high-band deficit falls, ~+0.3693 → ~+0.1301 dex | falls < 50% of the predicted 0.2392 dex drop, or overshoots past zero |

### Bars, numeric and fixed in advance

`B1` post-fix `mag` = 1.000 ± 2 SE, pre-fix 1.03008 excluded at ≥ 2σ ·
`B2` `flat-on-ruler-cpl` binned dims **3417 × 2276** ± 4 px ·
`B3` `bee-3-cpl` binned dims **3275 × 2184** ± 4 px ·
`B4` object-space modulation ratio ≥ 1.000 − 2 SE ·
`B5` subject extent within **1%** ·
`B6` `D_hi` deficit falls by ≥ **50%** of the predicted 0.2392 dex ·
`B7` **`OVERSHOOT`** — the post-fix deficit must **not** go below +0.02 dex.

**B7 is a FAIL, not a celebration.** If the deficit lands better than the
rescale alone can explain, something else changed in the same commit and the
measurement no longer isolates the fix. **A verification that cannot fail upward
is not a verification.**

**What would make me say the fix failed even though the picture looks better:**
B1 passing while B5 fails — magnification gone but field of view moved — means
the crop changed rather than the resample being removed. Those are different
operations. That is a FAIL.

### Controls, each with its failing input

`SELF` same file twice → exactly `1.000000` · **`NCX`** the negative control made
to go red: resample one copy by exactly `1.030000` and `SELF` must read
`1.030000 ± 0.004` and go RED · `DOSE` plant 1.000/1.010/1.030/1.075, each
within ±0.004, monotone · **`DIM`** the dimension trap as a control: crop to
different output dimensions at unchanged sampling, `mag` must hold
`1.000 ± 0.004` · `PL` placebo, swapping reference and test must invert to `1/x`
within 1e−6 · `INERT` comb must clear sidebands ≥ 3× on ≥ 8 ROIs or the ruler is
**no evidence**, not a null.

### Registered predictions, to be scored

(a) post-fix `mag` in `[0.998, 1.002]` · (b) B4 passes but is **boring**, ratio
in `[1.000, 1.010]` · (c) the pre-fix object-space price of the rescale on
`flat-on-ruler-cpl` is **under 2%** · (d) `bee-3-cpl` post-fix binned dims are
**3275 × 2184** exactly · (e) B6 passes with residual deficit in `[0.08, 0.18]`
dex, bracketing the orchestrator's 0.1301.

---

*Sections 1 onwards are written after measurement. Phase 1 (baseline, controls)
below; Phase 2 (verification against these bars) when M95 reports.*

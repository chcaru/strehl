# M104 — did removing the coverage rescale do what it claims? (independent verification)

**Milestone:** M104
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

The full pre-registration is `experiments/M104-resample-verify/PREREG.md`,
committed **before the fix existed and before any post-fix number existed**
(rule 12). This section is the summary; that file is the authority, and every
departure is declared in the report as a departure.

**HEAD:** `6a8ac3078d4c11df7ac9818fda0c381dd7fd625e`.
**Fix status at pre-registration: NOT LANDED** — `merge_cmd.rs:1246` still reads
*"then upsampled to keep the output dimensions"*, verified before writing.
Every baseline number below is a genuine *before*.

**Milestone number.** `M104` claimed after checking for a stem collision: no
`docs/research/M104*`, no `experiments/M104*`, no `M104` in any commit subject,
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

---

## 0a. STEM COLLISION — this milestone was M101 and has moved to M104

I checked for a collision before claiming M101 (no files, no commit subjects,
zero mentions in `SYNTHESIS.md` or `docs/`) and committed the pre-registration
as `599a6e0`. Another agent then claimed the same stem in `d9019ce`
(*"M101: pre-register the defect-map and election bars"*), which is a different
investigation entirely.

**I moved rather than stand on precedence.** I committed first, so I could have
kept it, but a stem that resolves to two unrelated investigations is a
permanent ambiguity in every future citation — precisely the problem the
orchestrator flagged when he warned that `M93` is held by two agents. Moving
cost me six file renames; leaving it would have cost the corpus a defect that
cannot be repaired later without rewriting citations.

`M104` verified free at the moment of the move against all four registers
(`docs/research/`, `experiments/`, every commit subject on every branch, and
`SYNTHESIS.md`). **The commit subject of `599a6e0` still reads "M101"** and
cannot be rewritten in a shared working tree; the trail is `599a6e0` →
this document. **The other agent's `M101-defect` is untouched.**

**A general point worth folding.** A stem check is not a lock. Mine passed and
was still wrong within the hour, because two agents can check and claim
concurrently and neither sees the other. The check answers *has this been
taken*, but what a claimant needs is *will this be taken*, and no read can
answer that. Numbering by verified-free-at-read-time will keep colliding at
this concurrency.

---

## 1. PHASE 1 — the instrument, and the *before* baseline

Everything in this section was measured at HEAD `6a8ac30` with the fix **not
landed**, re-verified immediately before writing (`merge_cmd.rs:1246` still
reads *"then upsampled to keep the output dimensions"*).

### 1.1 The controls failed first, and are reported as a failure

The first run of `c1_controls.py` went **red on four of seven controls**:

| control | first run | bar | |
|---|---|---|---|
| INERT | 7 live ROIs | ≥ 8 | RED |
| DOSE 1.075 | `0.9537 ± 0.1297` | ±0.004 | RED |
| DIM 90% | `0.9910 ± 0.0541` | ±0.004 | RED |
| PL | residue `1.27e-3` | ≤ 1e-6 | RED |

The standard errors are the tell: `0.13` and `0.20` against a `0.004` bar is
not noise, it is a bimodal readout. **Three defects, all in my instrument and
none in the renders:**

1. **The test arm's comb was searched globally and filtered only by angle.** A
   comb and its own second harmonic *share an angle*, so any ROI whose harmonic
   outran its fundamental returned `mag ≈ 2` or `≈ 0.5`. My own docstring
   described the correct algorithm — search near the reference — and the code
   did not implement it. **The comment was right and the code was wrong, and
   only the control could tell them apart.**
2. **Magnifications were averaged arithmetically.** A magnification is a ratio,
   and `mean(x) · mean(1/x) ≠ 1`. The placebo was *unsatisfiable in principle*
   with that estimator, so its red was my specification's fault, not the
   instrument's.
3. **The INERT gate was applied to the reference arm only**, so the ROI sample
   silently changed when the arms were swapped — which made the placebo
   untestable rather than failed.

Fixed by seeding the search from a frozen prior constrained to **±15% radial,
±0.15 rad angular** (twice the largest effect measured here, so it cannot force
the answer — and the DOSE arm at 1.075 is what proves it is not forcing),
aggregating with the **geometric mean**, and requiring **both** arms to clear
INERT. ROI geometry (384 px, 8 × 6, non-overlapping, 14 seeded) was chosen by
`c0_geometry.py` **against the control image, before any baseline number
existed**.

### 1.2 The instrument, re-run: admitted

| control | measured | bar | |
|---|---|---|---|
| INERT | **13** live of 48, S/B median 3.76 | ≥ 8 | GREEN |
| SELF | **`1.000000000`**, worst per-ROI deviation **`0.000e+00`** | exactly 1.000000000 | GREEN |
| DOSE 1.000 | `1.000000 ± 0.000000` | ±0.004 | GREEN |
| DOSE 1.010 | `1.010140 ± 0.000720` | ±0.004 | GREEN |
| DOSE 1.030 | `1.030740 ± 0.001213` | ±0.004 | GREEN |
| DOSE 1.075 | `1.074744 ± 0.000745` | ±0.004, monotone | GREEN |
| **NCX** | planted **exactly `1.030000`** → read `1.030740 ± 0.001213`, **25.34σ from 1.000** | **must go RED** | GREEN — it went red |
| DIM 90% | `1.001408 ± 0.000952` at 3168×2109 | 1.000 ± 0.004 | GREEN |
| DIM 80% | `1.001920 ± 0.001558` at 2816×1875 | 1.000 ± 0.004 | GREEN |
| PL | per-ROI worst `1.110e-16`, product `1.000000000000` | ≤ 1e-6 | GREEN |

**NCX is the one that licenses a post-fix reading of 1.000 to mean anything.**
A planted 3.0% enlargement — the same size as the ruler stack's real one — is
rejected at 25.34σ by the very bar the post-fix render must pass. So if the
post-fix render reads 1.000, that is a measurement and not a blindness.

**DIM is the orchestrator's trap, converted into a control.** Cropping to
different output dimensions *without* resampling moves the readout by
**0.14%** and **0.19%**, inside a 0.4% bar, at 3168×2109 and 2816×1875. The
instrument does not care about pixel dimensions — which is the entire reason it
is the right instrument for a fix that changes them.

### 1.3 The *before* baseline

Reference arm `STREHL_ALIGN=0`, gate 0. Test arm alignment ON, gate 0. **Gate 0
takes one frame per pixel**, so the only difference between the arms is the
warp and the coverage rescale. Sidecar SHA-256 recorded for both stacks; Phase 2
must render against the same solve or the comparison is confounded by a
re-solve rather than isolating M95's change.

#### `flat-on-ruler-cpl` — the clean subject

| quantity | pre-fix | note |
|---|---|---|
| emitted dims, both arms | **3520 × 2344** | identical, as the defect requires |
| aligner declares | `k = 0.9708` → `1/k = 1.030078` | from the render log |
| **`mag` = f0(A0)/f0(ALN)** | **`1.025027 ± 0.003170`** | **1.59σ from the aligner's own number** |
| extent ratio (ticks across frame) | `0.975585 ± 0.003017` | vs `k` = 0.9708 |
| object-space modulation at the comb | `1.021387 ± 0.018096` | f0 = 0.14021 cyc/px |
| `D_hi`, comb band [0.210, 0.351] cyc/px | **`+0.0604 ± 0.0195` dex** | 3.10σ |
| **`D_nyq`, [0.30, 0.48] cyc/px, object-corrected** | **`+0.1408 ± 0.0060` dex**, power **1.3829×** | **23.57σ** |

**The instrument recovers the aligner's own `k` from a photograph of a ruler at
1.59σ, with a standard error 7.5× tighter than M98's (`0.00317` vs `0.02390`).**
That is an independent confirmation of P10 by a sharper version of the same
optical route — and `k` is an *output* of the check, never an input to it.

**The resample's cost is entirely at high frequency, and that is the new
result.** Three bands on the same ROIs, same renders, same pass:

```
f = 0.140 cyc/px  (the comb itself)   +2.14% modulation   null, 1.18 sigma
f in [0.210, 0.351]                   +0.0604 dex         3.10 sigma
f in [0.300, 0.480]                   +0.1408 dex         23.57 sigma
```

A **3.01% enlargement** costs **1.383× in power near Nyquist** and is
*invisible* at the comb frequency. This is why the defect survived: every
metric that averages across frequency dilutes it toward nothing, and the eye
looking at midtone structure sees nothing wrong.

#### `bee-3-cpl` — the deep bracket, and a null that explains the silence

| quantity | pre-fix | note |
|---|---|---|
| emitted dims, both arms | **3516 × 2344** | |
| aligner declares | `k = 0.9315` → `1/k = 1.073537` | |
| **`mag`** | **`1.068148 ± 0.006961`** | **0.77σ from the aligner's own number** |
| extent ratio | `0.936200 ± 0.006101` | vs `k` = 0.9315 |
| `D_nyq`, object-corrected | **`−0.0343 ± 0.0425` dex** | **−0.81σ — a null** |

`bee-3-cpl` has no ruler, and the instrument still recovered the **+7.35%**
enlargement at **0.77σ** by tracking each ROI's own dominant spatial frequency.
`mag` needs only that the *same* feature is tracked in both arms, which the
±15% / ±0.15 rad window enforces; it does not need the feature's absolute scale
to be known. So P10 is now confirmed on the owner's actual subject, not only on
a test target.

**Its object-space bands are NOT admissible and I am not claiming them.** On
this subject the reference arm is an unregistered gate-0 render of a bracket
that drifts 232.7–603 px, so the two arms are images of *different effective
objects*, and the per-ROI `f0` is a feature of unknown identity rather than a
known physical scale. The `+24.64%` modulation and `−0.1910` dex comb-band
figures are recorded in the JSON as diagnostics and carry no bar.

**The near-Nyquist null is the interesting part, and it is admissible**, because
it is a *sign* claim about the sum of two effects rather than a magnitude claim
about either. On the deep bracket, registered-and-rescaled versus
unregistered-and-native is **statistically indistinguishable at −0.81σ**: the
detail registration recovers and the detail the resample destroys **cancel**.
That is a direct explanation of why this defect went unnoticed for the whole
project — on the subject where the rescale is *worst* (7.35%), its cost is
exactly masked by the benefit of the thing that causes it.

### 1.4 AMENDMENT to B6 and B7 — declared before any post-fix number exists

**B6 as registered is unsatisfiable, and I found this by measuring my own
baseline rather than by measuring the fix.** The registered text was:

> `B6` `D_hi` deficit falls by ≥ **50%** of the predicted 0.2392 dex ·
> `B7` **`OVERSHOOT`** — the post-fix deficit must **not** go below +0.02 dex.

I imported `+0.3693` and `+0.2392` dex from the orchestrator's measurement
(facts 1286, 1287) as if they were my chain's numbers. They are not, for three
reasons that were all knowable in advance and that I did not check:

1. **Different subject, different `k`.** His figure is `bee-3-cpl` at a 7.35%
   enlargement; my clean subject is the ruler at **3.01%**. Less than half the
   dose cannot produce the same deficit.
2. **Different reference arm.** His is a single frame decoded by rawpy; mine is
   `STREHL_ALIGN=0` gate 0 through strehl's own decoder — chosen deliberately
   to keep the chains independent, which necessarily also makes the absolute
   levels non-transferable.
3. **Different band and different binning.** My renders are binned, so
   `[0.30, 0.48]` cyc/px is not his `[0.30, 0.48]` cyc/px in object terms.

Measured, my pre-fix deficit is `+0.1408 dex`, so "fall by 0.2392 dex" would
require it to land at `−0.0984` — **a bar that could only be passed by the
instrument breaking.** A bar that cannot be passed by a correct fix is as
useless as one that cannot be failed by a broken one.

**The repair, which is legitimate only because no post-fix number exists and
which is why the amendment is timestamped in its own commit:** re-express the
bar *relative to my own measured baseline*, on the ruler, near Nyquist.

| | amended bar | value |
|---|---|---|
| **B6′** PASS | post-fix `D_nyq`(ruler) ≤ 50% of pre-fix | **≤ +0.0704 dex** |
| **B6″** strong | the rescale is *removed*, so the deficit should vanish | **\|`D_nyq`\| ≤ 0.0120** (2 SE) |
| **B7′** OVERSHOOT → FAIL | post-fix `D_nyq` must not go below | **−0.0120 dex** |

**B7′ remains a FAIL and not a celebration.** Nothing in "stop upsampling" can
*create* detail that the native-sampling reference already has. If the post-fix
render beats its own reference, something else changed in the same commit and
this measurement no longer isolates the fix.

**Additional predictions registered now, before the fix exists:**

- (f) post-fix ruler dims **3417 × 2276** ± 4 px
- (g) post-fix `bee-3-cpl` dims **3275 × 2183** ± 4 px
- (h) post-fix `mag`(ruler) = **1.000 ± 0.0063** (2 SE)
- (i) **B5**: post-fix extent ratio stays at **0.9756 ± 0.0098** (1%) — the FOV
  must not move, because removing an upsample is not a crop
- (j) post-fix `D_nyq`(`bee-3-cpl`) becomes **more negative by 0.10–0.45 dex**.
  The range is wide because it is an extrapolation: linear scaling of my
  ruler's 3.01% cost predicts `+0.344` dex at 7.35%, while the orchestrator's
  synthetic Catmull-Rom gather predicts `+0.239`. **Those two disagree by
  0.105 dex and the post-fix `bee-3-cpl` reading will discriminate between
  them** — which makes (j) the most informative single number in Phase 2.


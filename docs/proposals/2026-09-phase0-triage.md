# Phase-0 decision-value triage

> **Status: Investigation.** Produced 2026-09-02 by an independent read-only subagent
> (gpt-5.6-sol, max effort) commissioned by the orchestrator. It was asked one question:
> for each remaining phase-0 claim, **if it resolves either way, what code actually
> changes?** It changed no files.
>
> **Why it was commissioned.** Across 63 commits, phase 0 had changed zero lines of Rust
> and produced no decision that altered the stacker. The owner's judgement was that this
> is not acceptable progress. This triage exists to find out which remaining gates can
> pay out and which cannot.
>
> **It is one agent's assessment and is NOT self-certifying.** Its central claims -- in
> particular that C2/LCA is already answered TRUE with a 4-7.5% R and 3.5-7.1% B gain
> available, and that A2 and D8 are already answered -- are being independently audited
> by the lane agents now building on them, each of which was instructed to STOP rather
> than build if the prior finding fails audit. Treat the recommendations below as a plan
> of record, not as established fact.
# Phase-0 decision-value triage

## Executive verdict

Your nine-item list is correct but incomplete. The proposal also defines three phase-0 speed gates:

- D11 / `M-PHASE0-DECODE`
- D13 / `M-PHASE0-IDLE`
- D15 / `M-PHASE0-NVME`

That leaves **12 gates**. `docs\STATUS.md` marks PHASE, PTC, QUINCUNX, ZFIELD, and the supporting RHO lane closed; none of the remaining twelve is listed as in progress.

My recommendation is blunt:

- **Close six from evidence already in the repository:** LCA, DPAR, SPLIT, V-VEIL2, DECODE, NVME.
- **Drop CURV from phase 0:** it cannot change the current image.
- **Park five:** XSPEC, ASTIG, MAKERNOTE, IDLE, TETHER.
- **Run no further phase-0 lane before changing Rust.**

The alleged 17–27% fine-detail deficit is dead. `V-HEADTOHEAD.md` retracts it; `V-HEADTOHEAD2.md` shows tone explaining **94.8%, 109.9%, and 267.1%** of the apparent three-band gap. Strehl is not known to trail Helicon or Zerene in detail. Speculative detail investigations therefore do not outrank already-measured improvements.

I treated uncommissioned measurements skeptically under `AGENTS.md` rules 9, 18, and 35. The repository prior-art search instrument was itself commissioned before use.

## Capture inventory verified

`D:\personal\macro\requests` currently contains:

| request | ARWs |
|---|---:|
| `10-paper-iso-var` | 110 |
| `12-bee-iso-var-no-bracket-32-repeat-diff-light` | 576 |
| `19-razor-edge` | 789 |
| `30-calibration-grid` | 242 |
| `6-11-extended-dark-frames` | 506 |
| `7-aperture-pairs` | 623 |
| `8-tilted-planar` | 270 |
| `misc-diagnostic` | 135 |

---

## 1. C2 / M-PHASE0-LCA

1. **Assertion:** Red and blue reach best focus at different frame indices from green, so reusing green’s temporal selection sacrifices chromatic detail.

2. **If TRUE:** Keep green-only election in `crates\strehl-core\src\focus.rs`, but use temporally shifted R/B samples or weights. On the current default backend this touches `crates\strehl-core\src\pyramid.rs` and frame buffering in `crates\strehl-cli\src\merge_cmd.rs`; the estimator equivalent is `crates\strehl-core\src\merge.rs`. Rig-specific defaults could live in `optics.rs`.

   The proposal’s “one-line gather-index change” is stale: the current pyramid default performs per-band weighted accumulation, not a simple winner gather. Selection weights and value-frame data must be decoupled.

3. **If FALSE:** Nothing changes. Retain one green-derived selection for all CFA planes.

4. **Existing answer:** **Yes—strongly TRUE.** `docs\research\BUILD-CHROMA.md` independently replicated M107:

   - R peak: **−0.66 to −0.90 frames**
   - B peak: **−0.48 to −0.75 frames**
   - G1−G2 null: **+0.0005 to +0.0113 frames**
   - Green election forfeits **4.22–7.54%** R gradient energy and **3.51–7.13%** B.

   It used planted offsets, an on-axis discriminator, a same-sensor green null, threshold ladders, and a 256× quantisation sensitivity test. The known bias—lateral drift or content masquerading as axial CA—was explicitly tested.

5. **Cost:** **Zero additional measurement cost.** Existing stacks suffice. A rounded-offset prototype is approximately 1–3 engineering days; fractional temporal interpolation requires a separate photometric test.

**Disposition:** `ALREADY ANSWERED (close it)`

---

## 2. D8 / M-PHASE0-SPLIT

1. **Assertion:** Two interleaved half-stack renders provide a calibrated, noise-resistant per-stack SNR/FRC objective suitable for tuning and for an empirical null image.

2. **If TRUE:** Productise two independent half accumulations in `merge_cmd.rs` and `pyramid.rs`; add `strehl null` in `main.rs`; emit FRC/acuity products through `image_out.rs`; and likely add a dedicated core split/FRC module. Fixed-pattern correction in `noise.rs` must be bounded or subtracted.

3. **If FALSE:** No current merge code changes. Keep the split instrument offline in Python and do not add self-tuning or a null command.

4. **Existing answer:** **Yes, in substance.**

   `docs\research\M115-deconv-headroom.md` commissioned the corrected split statistic:

   - planted blur recovered at **0.9938–0.9974**
   - post-filter invariance within **0.54%** despite naïve metrics moving **8.25×**
   - exact power identity **1.0000**.

   `V-SOFTCHECK-coherence.md` and `V-SOFTCHECK-selection-vs-alignment.md` already staged interleaved file lists through the hashed shipping pyramid binary on three subjects. They also establish two mandatory safeguards:

   - Raw half coherence is gameable: averaging the halves achieves perfect coherence while losing **29.6%** band power.
   - Residual half-to-half warp can account for up to **87.3%** of observed incoherence on the deep bee stack.

   Thus the product must use M115’s matched-contrast SNR/FRC, not raw coherence. The literal Rust port remains implementation, not unresolved science.

5. **Cost:** No additional experiment is needed. A product port is roughly 3–7 engineering days. Ordinary existing stacks suffice. The 576-frame request is explicitly “no-bracket,” so it is not D8’s gold repeated-focus-bracket capture.

**Disposition:** `ALREADY ANSWERED (close it)`

---

## 3. A2 / V-VEIL2

1. **Assertion:** The two-layer haze is correct high-frequency detail placed on an incorrect low-frequency pedestal, and the repaired probe can specifically detect its correction.

2. **If TRUE:** Add spatially gated admitted-set base/coarse accumulation to the default pyramid in `pyramid.rs`, using `election_coherence.rs` and wiring in `merge_cmd.rs`. Related estimator machinery already exists in `merge.rs`, but `STREHL_VEIL` is default-off and estimator-only.

3. **If FALSE:** Leave `BaseBand::Mean` and `DEFAULT_MEAN_COARSE=0` unchanged. Do not port the veil machinery to the default path.

4. **Existing answer:** **Yes—the formal acceptance instrument is complete.**

   `experiments\V-VEILCLAW\README.md` found:

   - control: one peak at f244
   - null: flat
   - probe: peaks at f182 and f288, **106 frames apart**
   - sharp claw base **0.581**
   - foreground base **0.892**
   - master base **0.802**
   - master detail correlation **+0.852** with the sharp claw frame and **−0.035** with the foreground.

   `ORCH-veiling.md` §59.3 independently reproduced the numbers. The repaired detector passed **7/7** curves and found **3/3** two-layer cases; the original missed **3/3**. `BUILD-VEILMAP\README.md` found 96-pixel multi-peak fractions of **32.4%, 19.9%, and 11.7%** on the three bee stacks, versus a corpus median of **0.7%**.

   This answers V-VEIL2, not whether a particular A2 implementation is safe corpus-wide.

5. **Cost:** Zero to close the gate. Existing `bee-3-cpl` data suffice. Porting and gallery validation are approximately 2–5 engineering days plus render time.

**Disposition:** `ALREADY ANSWERED (close it)`

---

## 4. C10 / M-PHASE0-XSPEC

1. **Assertion:** Complex cross-spectrum phase contains stable information absent from modulus-only focus curves: finer registration, signed defocus, pupil aberrations, and contrast-inversion detection.

2. **If TRUE:** This is actually four independent changes, not one:

   - phase-ramp registration in `crates\strehl-core\src\align.rs`
   - signed through-focus data in `through_focus.rs`
   - phase-coherence admission in `pyramid.rs`
   - pupil/PSF profiles in `optics.rs`, eventually consumed by `restore.rs`.

   `merge_cmd.rs` would wire and cache the results.

3. **If FALSE:** Nothing changes in current Rust. Reads 2–3—signed defocus and pupil retrieval—die. Registration and inversion must each fail independently before those reads are also killed. A single global TRUE/FALSE verdict must not license all four.

4. **Existing answer:** **No.** `M70-through-focus-spectrum.md` explicitly says phase was never measured and calls it “the single highest-value unmeasured thing M70 touched.” Its ISO correlation, **+0.755** on powered stacks, remains confounded. `M78-blur-equalised-edges.md` tested a bilinear half-shift and explicitly did **not** test Fourier shifting or an upsampled/phase-ramp estimator.

   The main bias direction is toward a false positive: registration error and phase wrapping can look like odd-in-defocus physics. Commissioning therefore needs known Fourier shifts, a same-frame null, phase unwrapping checks, and held-out spatial registration—not a checker that applies and removes its own transform.

5. **Cost:** Approximately 8–16 engineering hours and under 1–2 compute-hours. No new capture is needed: `10-paper-iso-var` already contains 110 ARWs for the requested ISO control.

**Disposition:** `DO LATER`

---

## 5. C7 / M-PHASE0-ASTIG

1. **Assertion:** Off-axis horizontal and vertical structure reach best focus at different frame indices by enough to justify orientation-aware admission or fusion.

2. **If TRUE:** Split Sobel responses in `focus.rs`; retain two orientation-resolved curves in `through_focus.rs`; widen admission through the measured interval; and, only if FRC warrants it, add directional finest-band selection in `pyramid.rs`. Orientation-aware maps would need output wiring in `merge_cmd.rs`/`image_out.rs`.

3. **If FALSE:** Nothing changes. Keep scalar gradient magnitude and the current shared band weights.

4. **Existing answer:** **No.** No report maps sagittal-versus-tangential peak displacement through focus. `M88-optical-ceiling.md` concerns optical resolution, not this split. The razor capture cannot provide precision SFR: `docs\STATUS.md` reports **1.23 green-pixel RMS** edge-locus wander against pass at 0.02/fail at 0.03—**54× over**. That does not automatically invalidate a coarse peak-offset pilot, but it prevents using the razor as clean optical ground truth.

   The major false-TRUE bias is scene orientation: different horizontal and vertical objects can occupy different depths. A credible test needs orthogonal features at the same field point, rotation/placebo controls, and field-radius matching.

5. **Cost:** About 8–16 engineering hours and under two compute-hours. `30-calibration-grid` has 242 ARWs and is the best existing same-frame orthogonal target. `19-razor-edge` has 789 ARWs but is disqualified for precision optical metrology. No new capture is required for a pilot.

**Disposition:** `DO LATER`

---

## 6. C13 / M-PHASE0-MAKERNOTE

1. **Assertion:** Sony’s embedded distortion and chromatic-aberration arrays can be independently decoded, assigned trustworthy semantics, and outperform the current scalar optical profile.

2. **If TRUE:** Extend the bounds-checked TIFF/maker-note walker in `crates\strehl-raw\src\identity.rs` to carry correction arrays. Add knot profiles to `crates\strehl-core\src\optics.rs`. Because `OpticalProfile::compose` currently returns a global `Similarity`, a 16-knot nonlinear profile cannot be inserted there unchanged; sample coordinates in `align_cmd.rs`/the gather path must apply the radial spline in the existing interpolation pass. Distortion seeds may also affect `align.rs` and `warpmap.rs`.

3. **If FALSE:** Nothing changes. Retain the measured scalar R/B profile and current similarity-based gather.

4. **Existing answer:** **Partly, and it sharply reduces the expected payoff.**

   `F-camera-lens-optics.md` observed 16 distortion values, 32 CA values, and zero vignetting values in corpus ARWs. However, its layout/semantic interpretation crosses the proposal’s GPL licence fence and cannot be reused as clean-room implementation evidence.

   The repository already has an independent TIFF/maker-note walker in `identity.rs`, although it reads lens identity, not these arrays.

   More importantly, the proposal’s CA premise is stale. `BUILD-CROP.md` refitted red to **−508.4 ppm**; the current profile beats the former scalar on **18/22** scored subjects, with median improvement only **0.25%** but several larger wins. `BUILD-CHROMA.md` supplied blue’s **+174.4 ppm**. The remaining CA reward is therefore smaller than the proposal suggests. Distortion is the more plausible consumer.

   The main flattering bias would be fitting candidate knot semantics against the same scalar profile used to validate them. A held-out grid geometry is required.

5. **Cost:** Approximately 2–5 engineering days, little compute. No new capture: every ARW carries the payload and `30-calibration-grid` provides 242 validation frames. The proposal still contains an unspecified acceptance `[bar]`, which must be fixed first.

**Disposition:** `DO LATER`

---

## 7. C4c / M-PHASE0-DPAR

1. **Assertion:** Alignment residuals contain a depth-dependent radial magnification term that one similarity transform per frame cannot represent.

2. **If TRUE:** Add a depth-conditioned residual warp to `align.rs`/`warpmap.rs`, consume depth from `through_focus.rs`, and apply `W_i(x,z)` in `align_cmd.rs` during the existing gather. A one-parameter per-frame approximation could precede the full per-pixel form.

3. **If FALSE:** Nothing changes. `align.rs` remains similarity-only and no depth-conditioned warp is built.

4. **Existing answer:** **Yes—FALSE at the measured sensitivity.** `M6-residual-halo-measured.md` is the experiment C4c asks for, with independent reproduction and controls that detected planted depth-dependent scale:

   - depth-organised radial anomaly: **+0.066 / +0.135 / −0.100**, all `p > 0.22`
   - radial bias: **+0.033 / +0.001 / +0.020 px**, none significant
   - planted depth term fired strongly
   - planted symmetric blur fired the blur statistic but stayed radial-null.

   The observed residual instead rises with defocus mismatch: in-focus tiles **0.144–0.172 px**, far tiles **0.247–0.689 px**. The report concludes the right response is blur-aware tile weighting, not a depth-dependent lens warp.

5. **Cost:** Zero. The original full rerun took roughly nine minutes and required no new capture.

**Disposition:** `ALREADY ANSWERED (close it)`

---

## 8. C5 / M-PHASE0-CURV

1. **Assertion:** The lens has a repeatable focal-surface bowl that must be separated from scene depth before emitting metrically correct depth, normals, or physical reshoot advice.

2. **If TRUE:** Add field-curvature coefficients to `optics.rs` and subtract them in a future depth-product path using `through_focus.rs` and `image_out.rs`.

   **No current merge pixels change.**

3. **If FALSE:** Nothing changes. Future depth output uses its solved surface directly.

4. **Existing answer:** The bowl itself has not been fitted. But `F-camera-lens-optics.md` §6.5 already gives the decisive current-product result: per-pixel image selection absorbs field curvature, so explicit modelling buys nothing for the merged image. ZFIELD measured response curvature/uncertainty, not the lens’s global focal-surface bowl.

   The false-TRUE bias is severe: subject non-planarity or residual target tilt will be fitted as lens curvature unless tilt and repeat captures are explicitly separated.

5. **Cost:** Around 4–8 analysis hours and under one compute-hour. Existing data are ample: `8-tilted-planar` has 270 ARWs, `30-calibration-grid` has 242, and the main corpus has `flat-on-ruler-cpl` and `dime-flat-narrow-slices-cpl`.

   Nevertheless, there is no current code consumer.

**Disposition:** `DROP (no decision value)`

This means drop it from current phase 0, not erase the idea. Revive it only after a metric depth product exists.

---

## 9. D10 / M-PHASE0-TETHER

1. **Assertion:** The A7C II can provide a stable, low-latency full-RAW tether stream fast enough for a live fold and reshoot advisor.

2. **If TRUE:** Add a proprietary-SDK wrapper crate, a live command in `strehl-cli\src\main.rs`, incremental input handling in `merge_cmd.rs`, and incremental alignment/coverage logic in `align_cmd.rs`. The current parallel chunk fold assumes a known file list, so “already streaming” does not mean the live product is already implemented.

3. **If FALSE:** Nothing changes. Strehl remains a post-capture stacker/advisor.

4. **Existing answer:** **Partially.** No repository experiment measures latency or 299-frame stability. Sony’s current official Camera Remote SDK page lists:

   - `ILCE-7CM2` as supported
   - Windows 11 and USB support
   - still-image transfer/control
   - model-specific focus-position commands.

   Therefore “is the body supported?” is already TRUE. Full-RAW transfer latency, backpressure, disconnect recovery, and long-bracket stability remain unmeasured.

   The flattering failure mode is receiving only a preview/thumbnail while calling it RAW throughput; every transferred object must be size/hash checked and successfully decoded.

5. **Cost:** One hardware day, SDK registration/download, camera and cable, and a fresh approximately 299-frame tether run. None of the stored request captures can test a live transport.

**Disposition:** `DO LATER`

D10 is phase-4 product surface over B5/D2/D3. Running it now cannot improve today’s stack.

---

## 10. D11 / M-PHASE0-DECODE

1. **Assertion:** The shipped decoder is already at or above the proposal’s throughput threshold and is not the default-path bottleneck, so an owned Sony LJPEG decoder is unwarranted.

2. **If TRUE:** Nothing changes. Keep the current decoder; at most retain a future bounded decode/fold overlap seam.

3. **If FALSE:** Add an owned tiled decoder in `crates\strehl-raw\src\lib.rs`, a bounded producer/consumer decode queue in `merge_cmd.rs`, and possibly an optional decoded-plane cache.

4. **Existing answer:** **Yes—TRUE.**

   `M1-decode-measured.md` reports:

   - cold parallel: **1,245 MB/s**, 60 frames in **1.78 s**
   - warm parallel: **2,424 MB/s**, 60 frames in **0.91 s**
   - 122/122 successful real-file decodes.

   `M8-scratch-measured.md` measures one decode at `RAYON_NUM_THREADS=1` in **240.4 ms**. Against the 73.4 MB output buffer, that is approximately **305 MB/s of decoded output per core**, above D11’s 200 MB/s threshold. M8 itself was awaiting independent reproduction, but M1 and the shipping-binary measurements are independent corroboration.

   `BUILD-SPEED\REPORT.md` places **98.5%** of the current warm default run in the pyramid fold, not decode.

   Caching and internal decoder threading can flatter benchmarks, but these results are far enough across both registered thresholds that the decision is not close.

5. **Cost:** Zero. An exact `divan` rerun would cost about 1–2 hours and cannot change the current decision.

**Disposition:** `ALREADY ANSWERED (close it)`

---

## 11. D13 / M-PHASE0-IDLE

1. **Assertion:** Pyramid folding continues scaling beyond eight workers on an idle 16-core machine sufficiently to justify worker-count-independent reduction and memory redesign.

2. **If TRUE:** Implement D9’s fixed reduction lattice and dynamic memory budget around `merge_cmd.rs::band_workers`; later add shared spatial/strip accumulation in `pyramid.rs`.

3. **If FALSE:** No immediate code changes. Stop pursuing more frame-level workers and focus future speed work on SIMD, pass fusion, and memory traffic.

4. **Existing answer:** **Partial only.** `BUILD-SPEED\REPORT.md` measured a loaded-box sweep:

   | workers | wall |
   |---:|---:|
   | 1 | 59.02 s |
   | 2 | 29.55 s |
   | 4 | 17.28 s |
   | 8 | 13.41 s |

   Scaling is **2.00×, 1.71×, then 1.29×**. Eight workers establish that the four-worker cap leaves performance available. But 8→16→32 was not measured, and machine busy fraction explained **R² 0.88** of timing variance. The 102.2-second overnight log anchors idle performance but is not the requested scaling sweep.

5. **Cost:** One idle evening; approximately 1–3 wall-clock hours, no captures. Bias from machine contention acts against finding scaling, which is why the current data cannot answer the precise gate.

**Disposition:** `DO LATER`

Strehl is already much faster than the measured open-source field; this does not improve image quality and should not delay phase-1 work.

---

## 12. D15 / M-PHASE0-NVME

1. **Assertion:** Uncached storage I/O is a material cold-path bottleneck worth asynchronous IOCP readahead.

2. **If TRUE:** Add bounded asynchronous read/prefetch around RAW enumeration and decoding in `merge_cmd.rs`/`strehl-raw`, preserving the memory planner’s O(workers) bound.

3. **If FALSE:** Nothing changes. Keep ordinary parallel reads and spend cold-path work on the 73.4-second registration solve instead.

4. **Existing answer:** The exact bare-device GB/s figure is not isolated, but **the code decision is substantially answered FALSE**:

   - `M1-decode-measured.md`: real cold parallel decode plus read sustains **1,245 MB/s**.
   - `V-SPEED.md` §4: the measured cold-versus-warm penalty on 79 ARWs is **4.07 s / 16.4%**.
   - `BUILD-SPEED\REPORT.md`: a cold 299-frame run spends **73.4 s** in registration solve, while the warm path is fold-dominated.

   `V-SPEED` correctly admits that “cold” could not be proven against every other process on the shared machine. That weakens the exact number, not the ordering: registration and fold dwarf the measured I/O penalty today. Measuring a synthetic drive rate instead of the product penalty would be less decision-relevant.

5. **Cost:** Zero for the decision. A standalone disk benchmark is under an hour and would only replace an assumed number, not alter current Rust priorities.

**Disposition:** `ALREADY ANSWERED (close it)`

---

# Ranked decision-value table

Ranking is by probability-weighted ability to change the current default output, not by scientific interest.

| claim | asserts | changes code if TRUE | changes code if FALSE | already answered? | cost | recommendation |
|---|---|---|---|---|---|---|
| **C2 / LCA** | R/B focus peaks differ materially from G | Channel-shifted pyramid values/weights in `pyramid.rs` + `merge_cmd.rs` | Nothing | **Yes: TRUE**, 4–7.5% R and 3.5–7.1% B gain available | 0 to resolve | **ALREADY ANSWERED (close it)** |
| **D8 / SPLIT** | Half stacks provide usable SNR/FRC self-calibration | Dual accumulators, FRC/acuity/null products | Nothing; retain offline instrument | **Yes in substance** | 0 to resolve; days to build | **ALREADY ANSWERED (close it)** |
| **A2 / V-VEIL2** | Visible veil is a wrong pedestal and is specifically measurable | Depth/coherence-gated base/coarse merge on pyramid | Nothing | **Yes: instrument and mechanism confirmed** | 0 to resolve | **ALREADY ANSWERED (close it)** |
| **C10 / XSPEC** | Phase adds registration, signed-defocus, pupil, or inversion information | `align.rs`, `through_focus.rs`, `pyramid.rs`, `optics.rs`, `restore.rs` | Nothing; kill failed reads separately | No | 8–16 h, no capture | **DO LATER** |
| **C7 / ASTIG** | Orthogonal detail peaks at different z | Orientation-resolved focus/admission/fine bands | Nothing | No | 8–16 h; grid exists | **DO LATER** |
| **C13 / MAKERNOTE** | Embedded knot profiles beat scalar optics | Extend `identity.rs`; nonlinear gather/profile | Nothing | Payload seen; semantics unresolved; premise weakened | 2–5 days; grid exists | **DO LATER** |
| **D13 / IDLE** | Fold scales usefully past 8 workers | Fixed lattice, dynamic budget, strip cooperation | No worker redesign | Partial: only 1→8 under load | 1 idle evening | **DO LATER** |
| **D10 / TETHER** | Stable full-RAW live tether is feasible | New SDK/live-capture and incremental pipeline | Nothing | Body support yes; latency/stability no | 1 hardware day/new captures | **DO LATER** |
| **C4c / DPAR** | Residual warp depends on scene depth | Depth-conditioned warp | Nothing | **Yes: FALSE** at commissioned sensitivity | 0 | **ALREADY ANSWERED (close it)** |
| **D11 / DECODE** | Current decoder is fast enough | Nothing | Owned decoder and overlap queue | **Yes: TRUE**, 1.245 GB/s cold aggregate | 0 | **ALREADY ANSWERED (close it)** |
| **D15 / NVME** | Cold reads materially bottleneck product | IOCP prefetch | Nothing | Decision answered; exact device rate not isolated | 0 | **ALREADY ANSWERED (close it)** |
| **C5 / CURV** | Lens bowl must be removed from metric depth | Future depth-profile correction only | Nothing | Bowl not fitted; no current consumer | 4–8 h, captures exist | **DROP (no decision value)** |

There is intentionally **no `DO NEXT` row**.

# Direct answer

> Which two or three claims, if resolved, would most plausibly make this stacker measurably better than Helicon and Zerene—and is anything remaining worth doing before simply building and measuring?

**The three best bets are C2/LCA, D8/SPLIT, and A2/V-VEIL2—and all three already have the measurements needed to begin building.**

- **LCA** is the strongest: it identifies a direct, measured loss of channel detail and a capability competing stackers are unlikely to provide.
- **SPLIT** can tune the noise/detail trade per stack using an objective post-sharpening cannot fake.
- **V-VEIL2/A2** targets a real visible failure with a commissioned control and null.

Among genuinely unanswered claims, only **XSPEC** and **ASTIG** have credible comparator-visible detail upside. Both are speculative; neither answers a known Helicon/Zerene deficit, because that deficit was retracted.

**Nothing remaining is worth doing before building. Stop phase 0.** Close the already-answered gates, implement a guarded LCA prototype, cash V-VEIL2 into the phase-1 pyramid work, productise the split-SNR/FRC channel, and run a tone-neutral head-to-head. Time-box XSPEC only after those builds; leave ASTIG until a measured residual gap justifies it.

No files were changed.

# M-PHASE0-VEIL2 — A2 depth-aware base-band acceptance instrument

Status: **REGISTERED, NOT YET MEASURED**

This document was written before this lane decoded or rendered a measurement
frame and before its instrument was run on a real pixel. Prior numbers quoted
below are labelled as prior. The registration is committed separately so the
ordering is in Git rather than in recollection.

## 1. The question, corrected against the authoritative proposal

The dispatch's informal description is optical veiling glare: lens/camera
scatter around a bright edge. That is **not claim A2**.
`docs/proposals/2026-08-sota-path.md` defines A2 as a stack-induced,
depth-boundary **pedestal error**: selected detail is reconstructed on
`BaseBand::Mean`, an unweighted mean over all frames. At a two-layer pixel most
frames can contain a defocused foreground, so the correct detail can sit on the
wrong low-frequency base. A2 proposes an admitted-set base, ramped by election
coherence, while retaining the plain mean on incoherent flat ground.

The exact phase-0 question is therefore:

> On linear product-path data, does the shipped pyramid's claw base lie
> materially toward the foreground-hair layer while its detail still matches
> the claw-resolving layer, and can one instrument detect that displacement
> without crediting blur, a global tone/contrast change, or flat-field wander?

The primary site is the previously observed `bee-3-cpl` claw at full-resolution
master coordinates `y=2640:2830, x=2080:2270` (binned coordinates
`y=1320:1415, x=1040:1135`). Prior, uncommissioned continuity values are:
background/claw frame 288 base 0.581, foreground-hair frame 180 base 0.892,
master base 0.802, and master detail correlations +0.852 / -0.035
(`ORCH-veiling` §59.3). They set the bars; they are not this lane's result.

`19-razor-edge` and `7-aperture-pairs` are deliberately excluded. They can
separate an optical PSF tail from diffraction by aperture, but they contain no
focus-stack arm and cannot test which frames supplied a pyramid base. A2 neither
models nor promises to correct lens/camera scatter common to every frame.

## 2. Prior work and the unresolved point

1. `V-VEILCLAW` directly viewed two structures in the inherited claw window:
   foreground hairs around frames 171–198 and the claw around 285–291. Its
   Gaussian split reported the continuity values above. It did **not** supply
   uncertainty, used an arbitrary sigma, and its local registration and
   normalization were not an acceptance instrument.
2. `ORCH-veiling` §59.3 confirmed in source that `BaseBand::Mean` is an
   unweighted base and inferred that this mechanism caused the pedestal.
3. `BUILD-VEILMAP` found multi-peak curves concentrated on deep, hairy subjects,
   but explicitly did not cross-reference those curves to a master
   base/detail mismatch.
4. `M63-bimodality` later refuted the generic inference
   “two response peaks = two depths”: a single defocused edge produces side
   lobes and the flags do not reproduce across captures. Consequently this lane
   uses bimodality only as a potency diagnostic. Layer identity comes from the
   already observed frame contents, never from the curve shape.
5. `BUILD-BLEND` measured the losing global alternative:
   `WeightedFromCoarsest` caused 835 DN of position-dependent flat-field
   structure versus 45 DN for `Mean`.
6. `V-veiling` showed inherited veiling explains at most 37% of a different,
   broad flower-bud aura. A2 must not be reported as a complete explanation of
   that aura or as a universal optical-glare correction.

This lane is a **confirmation or narrowing**, not a first discovery. What is
unresolved is whether the §59.3 pedestal survives a commissioned, linear,
product-path measurement and whether its proposed acceptance metric can reject
the known flattering alternatives.

## 3. Declared bias and failure directions (AGENTS rule 18)

My selection bias is **toward SURVIVE**: the ROI was inherited from a visibly
hazy flagship crop and the prior values were used to design this lane.

The primary mixing statistic can be fooled upward by global darkening or a
contrast curve that makes the master resemble the darker layer. The detail
correlation can be fooled upward by shared resampling or sharpening. The
flat-wander statistic can be fooled downward by fitting away structure. The
countermeasures are, respectively: explicitly linear output plus independent
tone/null gates; independently rendered single-frame references; a blur plant
and detail-retention gate; and a fixed plane-only detrend commissioned on a
known bowl.

## 4. Frozen inputs and rendering

Binary:
`C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe`, expected SHA-256
`2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7`,
source commit `6af834dac08d6605aee7ea3ad75809fdf6313770`.

Every numerical render is binned, 16-bit, **linear sRGB**, with the complete
resolved configuration recorded from the banner:

```text
strehl.exe stack <stack> -o <out.tiff>
  --merge pyramid --pyramid-bands 7 --pyramid-gate 2.0
  --pyramid-exponent 2.0 --pyramid-sharpen 1.4
  --pyramid-select soft --pyramid-base mean --linear-srgb
```

`--demosaic`, `--srgb`, exposure, restoration, photometric fitting, and CA
overrides are absent. `STREHL_WARPMAP` names a separate lane-local sidecar for
every full-stack or one-frame run. All other `STREHL_*` variables are cleared
and recorded. Single-frame references use `STREHL_ONLY_FRAME=<zero-based k>`;
their local geometry is registered to the master from high-pass structure,
never from the low-pass quantity being scored.

Frozen bee reference sets: foreground hairs `F={176,180,184}`; resolved claw
`B={285,288,291}`. Frame 180 / 288 is also reported alone for continuity.

The current DELIVER-V6 sRGB masters may be used only to choose native-resolution
contact-sheet sites, never for a number.

## 5. Exact statistics

### 5.1 Base and mixing fraction — primary

`P7(I)` is the reconstruction obtained by seven applications of the Rust
pyramid's `[1,4,6,4,1]/16` separable reduce with replicated borders, retaining
only the coarsest Gaussian residual, then applying the matching expand seven
times. It is evaluated per linear-sRGB channel; green is primary and red/blue
are required sensitivity arms.

Each image is divided by the median of the inherited plain-paper null
`y=50:200, x=3250:3450` on the binned grid. Let `b(I,R)` be the mean of `P7(I)`
over the fixed ROI. Let `b_F` and `b_B` be pixelwise medians over the registered
F and B frame sets. The primary statistic is one ratio of aggregate bases:

```text
theta = (b(master,R) - b_B(R)) / (b_F(R) - b_B(R))
```

`theta=0` is the resolved-claw pedestal; `theta=1` is the foreground-hair
pedestal. The site refuses if the denominator is non-positive or below 0.15 of
paper white. Per-pixel ratios are forbidden.

Uncertainty is a deterministic 20,000-replicate cluster bootstrap
(seed 5903002): resample the three F frames and three B frames, then resample
non-overlapping 16×16-pixel spatial blocks of the ROI. Report bootstrap SE and
percentile 95% CI. Pixels are not treated as independent.

### 5.2 Detail identity — anti-blur gate

`H(I)=I-P7(I)`. After the same high-pass registration and paper normalization:

```text
D = corr(H_master, median(H_B)) - corr(H_master, median(H_F))
```

The instrument is potent only if `lower95(D) > 0.30`. A treatment later retains
detail only if its projection on `H_B` is at least 0.98 of baseline and its
correlation falls by no more than 0.01. Blur cannot be called a veil win.

### 5.3 Null, tone, geometry, and flat-wander gates

* Paper null: normalized base displacement in the fixed paper window must have
  absolute median <=0.02 and p95-p05 <=0.04.
* Tone locality: two additional fixed anchor windows, one midtone and one dark,
  are chosen from the alignment-reference frame before theta is computed.
  A least-squares affine map fitted on the three anchors may not explain more
  than 25% of the claw displacement. A global gamma/S-curve plant must be
  rejected.
* Geometry: high-pass phase correlation on two disjoint subwindows must agree
  within 0.75 binned pixel. Perturbing the accepted transform by each of the
  eight `(dy,dx)` combinations in `{-1,0,1}² \ {(0,0)}` must not change verdict
  class.
* Flat wander for a future mean-vs-A2 pair is
  `W=p95(D')-p05(D')` in the fixed least-subject flower-bud quadrant, where
  `D'` is candidate-minus-mean after subtracting only its fitted plane.
  Acceptance is upper95(W)<=100 DN. Commissioning requires a planted 835-DN
  bowl to read lower95(W)>400 DN. No higher-order surface may be fitted.

### 5.4 Chia replication

Before computing any chia score, tile the linear master into unresized
<=400-pixel crops. In raster order retain the first three 96×96 binned crevice
sites that meet all of these content-only predicates in contact sheets:
(a) the same seed crevice remains in the box, (b) at least four contiguous
frames visibly resolve the crevice, (c) a separate run of at least four frames
at least 15 indices away contains a defocused bright seed lip in the box, and
(d) the paper/null is outside the box. Freeze coordinates and frame ranges in
`roi-manifest.json` before theta is computed. Through-focus peak count may not
choose a site or frame. Fewer than three eligible sites is `UNMEASURABLE`, not
zero and not KILL.

The chia summary is the median site theta, with a hierarchical bootstrap over
sites, frame runs, and 16×16 blocks.

## 6. Commissioning — inputs that must make every check fail

Commissioning runs before real measurement. Synthetic planes are constructed
from constant bases and independently generated zero-mean textures; the
checker does not generate them. A fixed hand-computed plateau fixture is also
read against direct `numpy.mean`, outside the P7 implementation. The six
single-frame RAW references are external predicates not touched by the
full-stack merge.

Eight controls and their planted RED inputs:

| check | passing control | defect planted; required RED |
| --- | --- | --- |
| C1 known theta | theta ladder 0/.25/.5/.75/1 within 0.02 | zero-effect theta=0 offered as SURVIVE |
| C2 layer sign | foreground base > background by 0.30 | F/B labels swapped |
| C3 detail identity | master texture is B texture | Gaussian blur sigma 1.5 |
| C4 tone locality | ROI-only pedestal mixture | global gamma chosen to improve raw theta |
| C5 paper null | untouched fixed paper | +0.06 paper offset |
| C6 geometry | identical disjoint shifts | one subwindow translated by 1 pixel |
| C7 flat wander | constant/plane-only delta | 835-DN broad bowl |
| C8 layer truth | fixed, externally labelled two-layer fixture | single-depth defocused edge with a secondary response lobe |

Every planted defect must make its named check RED. A control that never fires
does not count. The recorded output includes the observed statistic at full
effect, not only the physical plant amplitude.

## 7. Verdict lookup

All eight controls must pass, all eight plants must go RED, the encoding and
provenance checks must pass, and `lower95(D)>0.30`; otherwise the result is
`NOT ROBUST`, never KILL.

* **SURVIVE:** `lower95(theta_claw) >= 0.50`, all registered sensitivities stay
  in class, and chia has three valid sites with
  `lower95(median theta_chia) >= 0.25`.
* **NARROWED:** `lower95(theta_claw) > 0.25`, but either the 0.50 claw bar or
  chia replication is not met. This licenses only a specimen-scoped,
  non-default phase-1 arm.
* **KILL:** with every potency/commissioning gate valid,
  `upper95(theta_claw) <= 0.25`, or detail does not preferentially match the
  claw-resolving frames.
* **NOT ROBUST:** the claw CI crosses 0.25; a channel, P6/P8, ROI erosion/dilation
  by 8 px, frame-pair, or registration perturbation changes verdict class; two
  independent decoders disagree; or any required gate/provenance check fails.

An A2 implementation later passes this frozen instrument only if claw theta is
reduced by at least 50% with `lower95(delta theta)>0`, chia median theta falls
by at least 25% with 75% of sites moving correctly, detail retention passes,
and flat-wander `upper95<=100 DN`. The paper and tone anchors must remain inside
their baseline CIs.

## 8. Consequence for Rust, fixed before the verdict

* SURVIVE routes a phase-1 control arm to
  `crates/strehl-core/src/pyramid.rs` (a third base policy and admitted-base
  accumulators), `crates/strehl-core/src/election_coherence.rs` (base-grid
  coherence ramp), and `crates/strehl-cli/src/merge_cmd.rs` (pyramid-path
  admission/coherence plumbing and banner). `crates/strehl-cli/src/main.rs`
  exposes it as a non-default arm. Default `BaseBand::Mean` may change only
  after the future acceptance above passes.
* NARROWED permits the same modules only as a non-default specimen-scoped arm.
* KILL or NOT ROBUST changes no production Rust; `BaseBand::Mean` stays.

This phase-0 lane itself is prohibited from editing Rust.

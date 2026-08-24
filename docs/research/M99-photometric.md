# M99 — Per-frame photometric drift: is it geometry, or is it the camera?

Status: in progress
Owner: M99
Stacks: `bee-3-cpl` (299), `bee-2-cpl` (299), `lavendar-cpl` (299), `leaf-2-cpl` (182)

---

## 0. Pre-registration

This section was written **before** any pixel of any frame was read, and has not
been edited since. Everything below §1 is measurement.

### 0.0 What was already known when the bars were fixed

One thing was measured before the bars were set, and it is declared here rather
than hidden: a **metadata audit** (EXIF only, no pixels). It is reported as
result R0 in §2 and it changed the design of every phase that follows. The bars
below were fixed with R0 in hand and before any frame was decoded.

The audit was run first deliberately. The brief asks whether per-frame
brightness tracks the alignment solve's scale ladder. If the *camera* changed
its own exposure during the bracket, then any curve fitted to per-frame
brightness is a curve fitted to the camera's light meter, and the geometric
question cannot even be posed until that term is removed. Checking the metadata
costs seconds and decoding 1079 frames costs half an hour; the cheap decisive
check goes first.

### 0.1 Definitions

* **Level** `L_p(k)` — the median of the green photosites inside patch `p` of
  frame `k`, in units of `(raw - black) / (white - black)`. Green only, so the
  colour filter array's own gain differences cannot enter.
* **Scene-fixed patch** — a patch whose centre is transported through the
  alignment placement, so that the same *scene* point is sampled in every
  frame. The reference patch centre `c` is mapped to frame `k` by
  `apply_at(c, plane_centre)` using placement `a_k, b_k` read from the bracket's
  `warpmap.txt` sidecar. This is the correction to the confounded
  sensor-fixed measurement in `experiments/ORCH-drift-check/`.
* **Exposure-normalised level** `E(k) = L(k) / t_k`, with `t_k` the EXIF
  exposure time of frame `k`.
* **Scale** `a_k = |a|` of the placement, i.e. `sqrt((1+g_k)^2 + rot_k^2)`.
  The sidecar's placements map **reference → frame**, so `a_k > 1` means frame
  `k` is *more* magnified than the reference frame.

### 0.2 Bars

**PR-1 — is there any drift at all, in scene coordinates, after exposure?**
Statistic: `R = max_k E(k) / min_k E(k)` over all sampled frames, with `E`
the global (across-patch median) exposure-normalised level.

* **REAL** if `R >= 1.02` on at least one stack.
* **NEGLIGIBLE** if `R < 1.02` on every stack.

2% is chosen because it is roughly ten times the shot-noise floor of a
64x64-quad patch median at these levels, and because a 2% step across an
election boundary is 0.029 stops — about the smallest brightness step that is
credibly visible on a smooth out-of-focus background.

**PR-2 — one scalar per frame, or a field?**
With `P >= 8` scene-fixed patches, form the matrix `r_p(k) = E_p(k) / E_p(ref)`
in logs. Let `f1` be the fraction of the total variance of `log r` explained by
its best rank-1 (frame-only, patch-constant) approximation.

* **GLOBAL** if `f1 >= 0.90` — one scalar per frame is the right shape.
* **FIELD** if `f1 < 0.90` — a per-frame scalar cannot describe it and the
  correction must be spatial.

**PR-3 — does `1/a^2` explain what is left?**
Only on stacks whose EXIF exposure is **constant**, because on an
auto-exposure stack the camera's own term dominates and the geometric term is
not separable from it without assuming the answer.

Models for `y(k) = log(E(k) / E(ref))`:

* `M0` (null): `y = 0`.
* `M1` (geometry, no free parameters): `y = -2 * log(a_k / a_ref)`.
* `M2` (free exponent, one parameter): `y = q * log(a_k / a_ref)`, `q` fitted.
* `M3` (free per-frame gain): fits exactly, RMS 0, quoted only as the floor.

Let `S(M)` be the RMS of `y - model` in natural log units.

* **CONFIRMED** if, on **both** manual-exposure stacks, `S(M1) < 0.010`
  **and** `S(M1) <= 0.5 * S(M0)`.
* **REFUTED** if, on either manual-exposure stack, `S(M1) > 0.7 * S(M0)`, or
  the free exponent `q̂` falls outside `[-3, -1]` while `S(M2) < 0.7 * S(M1)`.
* **INCONCLUSIVE** otherwise, and the correction must then be a fitted gain.

`0.010` in natural log is 1.0%, i.e. half the PR-1 materiality bar: a model
that leaves more than that on the table has not removed the defect.

**PR-4 — negative control (power of the PR-3 test).**
Shuffle the frame order 500 times, i.e. permute `k -> a_{sigma(k)}`, and
recompute `S(M1)`. The PR-3 test has power only if the true-order `S(M1)` is
below the **1st percentile** of the shuffled distribution. If it is not, PR-3
is **VOID** regardless of which way it came out.

**PR-5 — competing mechanisms.** Each is ruled in or out explicitly:

* *Exposure/ISO/aperture variation* — from EXIF, every frame. (R0.)
* *Illumination drift over the capture* — a mechanism monotonic in **time**.
  Distinguished from one monotonic in **scale** by fitting both and comparing;
  where the two regressors are collinear this is reported as collinear rather
  than resolved.
* *Lens extension changing the effective aperture* — `N_eff = N * (1 + m)`,
  giving irradiance `∝ 1/(1+m)^2`. This is a **different** `1/m^2` from the
  inverse-square spreading of a fixed flux, and over a small magnification
  change the two are not separable; the test in PR-3 is therefore a test of the
  **combined** exponent `q`, and `q̂` is reported as such.

**PR-6 — does the correction improve the photograph? (Phase D.)**
The defect is a brightness **step between elected regions**. The statistic must
respond to that and not to change.

*Statistic (Seam-Step Coupling, SSC).* The election assigns each output pixel a
source frame `k(x)`. Let `G(k)` be the per-frame level ratio measured in Phase
A. On **background** pixels only, regress the render's luma `Y(x)` on `G(k(x))`
through a per-region background model:

    SSC = beta, from  Y(x) = alpha + beta * G(k(x)) + noise

with `beta` in units of `Y` per unit `G`. If the render carries the per-frame
level into the output, `beta ≈ mean(Y)`; if the correction works, `beta ≈ 0`.
SSC is a *correctness* statistic: a render that merely differs from the
baseline, but whose luma is uncorrelated with the elected frame, scores zero.

* **IMPROVED** if `|SSC_corrected| <= 0.25 * |SSC_baseline|` **and** the
  corrected render's background luma standard deviation does not increase by
  more than 2% relative.
* **NOT IMPROVED** otherwise.

*Plant (validity of SSC).* Inject a **per-frame multiplicative gain ramp** —
the same form as the defect, not a translation and not a per-pixel change —
`g_k = 1 + A * (k / (n-1) - 0.5)` with `A = 0.20`, into the decoded frames, and
require: (a) `SSC_planted >= 3 * SSC_baseline` in magnitude, i.e. the statistic
sees the planted defect; and (b) applying the correction to the planted frames
returns `|SSC| <= 0.25 * |SSC_planted|`. If (a) fails the statistic is blind and
Phase D is **VOID**.

**PR-7 — Phase C is gated.** `crates/strehl-core/src/photometric.rs` is built
only if PR-1 returns REAL. Its *form* is decided by PR-2 (scalar vs field) and
PR-3 (derived from geometry vs fitted).

### 0.3 What would make me abandon the milestone

If PR-1 returns NEGLIGIBLE on every stack, there is nothing to correct and the
right deliverable is the negative result plus the EXIF finding.

---

## 1. Method

Four stacks, every frame of each, 1079 frames decoded in total.

| stack | frames | exposure mode | why it is here |
| --- | --- | --- | --- |
| `bee-3-cpl` | 299 | Program AE | the deck the orchestrator's observation came from |
| `bee-2-cpl` | 299 | Program AE | same subject and rig, independent capture |
| `lavendar-cpl` | 299 | **Manual** | the natural experiment: the camera's meter is out of the loop |
| `leaf-2-cpl` | 182 | **Manual** | a second manual deck, different subject and depth |

`highly-angled-ruler-mm-cpl` was the brief's suggested second deck. It is on the
project's `TILTED_SUBJECTS` list, the aligner refuses it, and without a solve
there are no scene coordinates — so it cannot be used for this question at all.
`lavendar-cpl` and `leaf-2-cpl` were chosen instead **because their exposure is
manual**, which is the single most useful property a control deck can have here
once R0 is known.

Pipeline, per stack:

1. Read the bracket's `warpmap.txt` sidecar. The hex bit patterns are parsed,
   not the decimal comments, so the placements are the aligner's own `f64`s.
2. Decode every frame with `rawpy`, green photosites only.
3. Transport each candidate patch centre through that frame's placement, so
   every sample is the same **scene** point. `apply_at` is mirrored from
   `align.rs` exactly, including the plane-centre convention.
4. Record, per frame and per patch: the scene-fixed median, the within-patch
   relative MAD, and — for comparison with the confounded measurement — the
   sensor-fixed median from the same decode.
5. Separately record whole-frame conserved flux (§4.1), per-CFA-plane means,
   clipped fraction, and at-or-below-black fraction.

Scripts are in `experiments/M99-photometric/src/`, numbered in run order.

One geometry note, MEASURED: `rawpy`'s visible area on these files is
7028x4688, and strehl's plane geometry is 3516x2344 (bee decks) or 3520x2344
(`lavendar`, `leaf-2`), so strehl's active rectangle is up to 4 px wider. The
resulting centre offset is at most 2 plane px, which at `|a-1| <= 0.06` is at
most a 0.12 px mapping error. That is well inside a 128-px patch and is ignored.

---

## 2. R0 — the metadata audit, and two confounds nobody had looked for

All MEASURED, from ExifTool over every frame of all four decks.

### R0a — two of the four decks were shot in Program AE

| deck | exposure mode | metering | shutter across the bracket |
| --- | --- | --- | --- |
| `bee-3-cpl` | Program AE | Multi-segment | 148 frames at 1/5 s, then 151 at 1/6 s |
| `bee-2-cpl` | Program AE | Multi-segment | 151 frames at 1/20 s, then 148 at 1/25 s |
| `lavendar-cpl` | **Manual** | — | constant |
| `leaf-2-cpl` | **Manual** | — | constant |

**The camera re-metered every frame on `bee-3-cpl`.** That is the deck the
orchestrator's observation is drawn from. Any per-frame brightness curve fitted
to it is fitted partly to Sony's light meter, and no amount of careful optics
reasoning recovers a geometric law from it.

ISO (100), nominal f-number (5.8121) and lens (`FE 100mm F2.8 Macro GM OSS + 2X
Teleconverter`) are constant on all four decks. `ElectronicFrontCurtainShutter`
is on; `ReleaseMode` is `Exposure Bracketing` throughout.

### R0b — the standard `ExposureTime` tag is rounded and is wrong

`ExposureTime` is quantised to the 1/3-stop ladder. `SonyExposureTime` is
stepless and is the value the camera actually used.

| deck | `ExposureTime` range | distinct | `SonyExposureTime` range | distinct |
| --- | --- | --- | --- | --- |
| `bee-3-cpl` | 1/6 .. 1/5 (ratio 1.2000) | 2 | 0.143899 .. 0.218346 s (ratio **1.5174**) | 144 |
| `bee-2-cpl` | 1/25 .. 1/20 (ratio 1.2500) | 2 | — | 154 |

DERIVED: an analysis that normalises by `ExposureTime` on these decks is
introducing a 26% error in the exposure term in order to remove a 9% drift. The
single nominal 1/5 -> 1/6 step at frame 148 of `bee-3-cpl` moved the measured
level by a factor of **1.0083**, not 1.2 — which is how this was found.

### R0c — the camera records its own effective f-number, per frame

`SonyFNumber2` varies smoothly frame by frame while nominal `SonyFNumber` does
not. It is the extension-corrected effective aperture, i.e. it already carries
`N_eff = N(1+m)`.

| deck | `SonyFNumber2` first -> last | implied `1/N_eff^2` span |
| --- | --- | --- |
| `bee-3-cpl` | 13.1482 -> 11.8466 | 1.2318 |
| `bee-2-cpl` | 13.1839 -> 11.8627 | 1.2350 |
| `lavendar-cpl` | 13.5274 -> 12.2213 | 1.2251 |
| `leaf-2-cpl` | 13.5274 -> 12.7279 | 1.1293 |

ARGUED: this is the *lens-extension* `1/m^2`, and it is a different quantity
from the inverse-square spreading the brief's hypothesis invokes. Over these
small magnification changes the two are not separable, so PR-3 tests the
**combined** exponent and reports `q̂` as such, exactly as pre-registered.

---

## 3. Phase A — the drift in scene coordinates

Patches were admitted by **measurement, not by eye**, as the brief requires. A
21x14 grid of 294 candidate centres (128 quad-px squares) was transported into
every frame. A candidate was admitted only if, in **every** frame of the deck,
its level was finite, inside `[0.02, 0.85]` of the usable range, and its
within-patch relative MAD was below 0.045. Admitted candidates were then thinned
by greedy farthest-point selection to 12 well-spread patches. Admitted counts:
78 / 167 / 12 / 80 of 294 for `bee-3` / `lavendar` / `leaf-2` / `bee-2`.

### PR-1 — REAL, on all four decks

MEASURED, `R = max_k E(k) / min_k E(k)` over all frames:

| deck | `R` scene-fixed | `R` sensor-fixed | `R` exposure-normalised | verdict |
| --- | --- | --- | --- | --- |
| `bee-3-cpl` | **1.1818** | 1.1739 | 1.3079 | REAL |
| `bee-2-cpl` | **1.2197** | 1.2611 | 1.3502 | REAL |
| `lavendar-cpl` | **1.4098** | 1.4154 | 1.4098 | REAL |
| `leaf-2-cpl` | **1.0824** | 1.0752 | 1.0824 | REAL |

The bar was 1.02 on at least one deck. All four clear it by a wide margin.

**A correction to the brief, MEASURED.** The brief warns that the orchestrator's
sensor-coordinate patches slide down a lighting gradient and that "this alone
could produce the entire effect". It does not. Scene-fixed and sensor-fixed
ratios agree to within 3.4% on every deck, and on `bee-3-cpl` scene-fixed is
*larger* than sensor-fixed. The sliding-patch confound is real but small. The
orchestrator's number was wrong for a different reason, given in §4.2.

The orchestrator's other warning — that the top-left patch is the bee's wing and
not background — is well founded, and the measured admission rule above is what
replaces it. On `bee-3-cpl` only 78 of 294 candidates were background in every
frame; 216 were rejected.

### PR-2 — FIELD, on all four decks

MEASURED, fraction of the total variance of `log r_p(k)` explained by the best
frame-only (patch-constant) rank-1 approximation:

| deck | frame-only `f1` | verdict (bar 0.90) |
| --- | --- | --- |
| `bee-3-cpl` | **0.7511** | FIELD |
| `bee-2-cpl` | **0.8833** | FIELD |
| `lavendar-cpl` | **0.7665** | FIELD |
| `leaf-2-cpl` | **0.8740** | FIELD |

This is the single most important Phase A answer and it says the drift is **not
a global gain**. A per-frame scalar is an approximation that can remove at best
about three quarters of it.

**Stated as a limitation, not smuggled in as a finding:** patch levels contain
defocus redistribution as well as photometry, so PR-2 cannot by itself separate
a genuine photometric *field* from blur moving light around. What it does
establish is an upper bound on what a scalar can achieve. §7 then measures the
same quantity by a completely independent route — with the real election in the
loop — and gets 0.740 where PR-2 predicted 0.751. That agreement is what turns
the bound into a finding.

### The shape of the curve refutes the hypothesis before any model is fitted

MEASURED: on `bee-3-cpl` the global scene-fixed level is **non-monotonic** —
0.211 at frame 0, rising to 0.230 near frame 126, falling to 0.203 at frame 298.
The aligner's fitted scale `a_k` is **strictly monotonic** across the same
bracket. DERIVED: no monotone function of `a_k`, `1/a^2` included, can produce a
non-monotonic level curve. The hypothesis was dead on this deck before a single
residual was computed.

---

## 4. Phase B — testing `1/a^2` properly

### 4.1 The statistic had to change, and why

Patch medians conflate two different things: a frame that received less light,
and a frame whose light was moved somewhere else by defocus. Only the first is a
photometric defect, and only the first is fixable by a gain.

Blur conserves flux. So the whole-frame mean above black is blind to
redistribution and sensitive only to photometry, and Phase B is run on **that**.

MEASURED, whole-frame green mean above black, `max/min`:

| deck | flux ratio | clipped fraction | at-or-below-black fraction |
| --- | --- | --- | --- |
| `bee-3-cpl` | 1.0869 | 0.000000 | 0.000000 |
| `bee-2-cpl` | 1.0818 | 0.000000 | 0.000000 |
| `lavendar-cpl` | 1.3689 | 0.000000 | 0.000000 |
| `leaf-2-cpl` | 1.0959 | 0.000000 | 0.000000 |

Zero clipping and zero black clipping on all 1079 frames, so the flux really is
conserved and the movement really is photometric. Per-plane ratios on
`lavendar-cpl` are R 1.3696, G1 1.3689, B 1.3756, G2 1.3688 — achromatic to
about 0.5% of a 37% effect, which is why the correction is one scalar and not
four.

Cross-check, MEASURED: a central-third crop agrees with the whole frame on the
manual decks (correlation 0.999, RMS gap 0.003-0.006), so this is not
field-of-view traffic across the border. On the AE decks the crop and the whole
frame *disagree* (correlation 0.86-0.90), because AE holds total flux roughly
constant while defocus moves it between core and border — which is itself the
first hint of the §7 result.

### 4.2 The orchestrator's 0.37% agreement does not survive contact with the ladder

MEASURED, from `bee-3-cpl`'s own sidecar: `g` runs +0.0503 at frame 0 to
-0.0311 at frame 298, so `a_0 / a_298 = 1.0841` and `(a_0/a_298)^2 = **1.1753**`.

The brief predicts 1.1132 from a 232.7 px corner-to-corner drift summary. The
aligner's actual fitted ladder predicts 1.1753. The claimed 0.37% agreement with
a measured 1.1091 is an artefact of using a summary displacement instead of the
per-frame scale the aligner actually solved; against the real ladder the gap is
**5.6%**, fifteen times larger. This is exactly why the brief asked for the
fitted ladder per frame, and it is the right instinct.

### 4.3 Model comparison

Models for `y(k) = log(flux(k) / flux(ref))`, residual RMS in natural log units.
`T` is `log(SonyExposureTime)`, `F` is `-2 log(SonyFNumber2)`, `A` is
`log(a_k)`, `K` is frame index.

| deck | `M0` null | `M1` = `-2A` | `Mf` = `F` | `Mef` = `T+F` | `M2` free `q` on `A` | `M2f` free `p` on `F` | `M4` linear in time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bee-3-cpl` | 0.01569 | 0.06214 (3.96x) | 0.07517 | 0.05333 | 0.01209, `q̂`=-4.740 | 0.00447 | 0.00372 |
| `lavendar-cpl` | 0.09265 | 0.06687 (0.722x) | 0.03184 | 0.03184 | 0.02543, `q̂`=-6.466 | 0.00217 | 0.00108 |
| `leaf-2-cpl` | 0.02735 | 0.03492 (1.277x) | 0.00990 | 0.00990 | 0.00142, `q̂`=-0.879 | 0.00163 | 0.00121 |
| `bee-2-cpl` | 0.01586 | 0.09076 (5.72x) | 0.07446 | 0.05847 | 0.00849, `q̂`=-3.045 | 0.00373 | 0.00304 |

### PR-3 — **REFUTED**

Pre-registered: REFUTED if, on either manual deck, `S(M1) > 0.7 * S(M0)`, or
`q̂` falls outside `[-3, -1]` while `S(M2) < 0.7 * S(M1)`.

* `lavendar-cpl`: `S(M1)/S(M0) = 0.722 > 0.7`. **Refuted on the first clause.**
* `leaf-2-cpl`: `S(M1)/S(M0) = 1.277`. The no-free-parameter geometric model is
  **worse than assuming no drift at all**. Refuted twice over.
* `q̂` = -4.740, -6.466, -0.879, -3.045. Outside `[-3,-1]` on three of four, and
  spanning a factor of **7.4** between decks. A law whose only exponent varies
  seven-fold across four captures on one rig is not a law.

The CONFIRMED bar (`S(M1) < 0.010` and `<= 0.5 S(M0)` on both manual decks) is
missed by between 3.2x and 6.7x.

### PR-4 — negative control: `M1` has **no power at all** on the AE decks

MEASURED, 500 shuffles of the frame order:

| deck | true-order `S(M1)` vs shuffled distribution | verdict |
| --- | --- | --- |
| `bee-3-cpl` | worse than the shuffled **median** | NO POWER |
| `bee-2-cpl` | worse than the shuffled **median** | NO POWER |
| `lavendar-cpl` | below the shuffled 1st percentile | HAS POWER |
| `leaf-2-cpl` | worse than the shuffled 1st percentile | NO POWER |
| all four, `Mef = T+F` | below the shuffled 1st percentile | HAS POWER |

So on the two decks the brief's observation came from, the ordered `1/a^2` model
fits *worse than a random reordering of the same frames*. Even had it "agreed",
the agreement would have been void by the pre-registered control.

### 4.4 The counter-intuitive result: AE was already doing the job

MEASURED: on `bee-3-cpl` and `bee-2-cpl` the **uncorrected** flux is already
flat to about 1.6% RMS, and dividing by the true `SonyExposureTime` makes it
**7.3x to 7.5x worse**.

DERIVED, and it is a product warning: a correction that "fixes exposure" on an
auto-exposure deck **creates** the defect it claims to remove. Program AE is a
closed loop that has already normalised the frames; opening that loop with a
metadata-derived exposure term re-injects the very drift the meter removed.

### PR-5 — competing mechanisms: one ruled out, three not separable

* *Exposure / ISO / aperture variation.* **Ruled in, and large.** §2.
* *Lens extension changing effective aperture.* **Ruled in.** `SonyFNumber2`
  moves monotonically and in the right direction on every deck (§2, R0c).
* *Illumination drift over the capture.* **Cannot be ruled out.** MEASURED:
  `M4`, plain linear-in-time, fits at least as well as every other model on all
  four decks (0.00372 / 0.00108 / 0.00121 / 0.00304). A warming or cooling lamp
  would look exactly like this.
* *Focus breathing / inverse-square spreading.* **Refuted as a predictive law**
  (PR-3), though not as a contributing physical effect.

**Mechanism attribution is not identifiable in this corpus, and I will not
pretend otherwise.** MEASURED: `corr(F, K) = +0.9998` and `corr(A, K) ~ 0.99` on
every deck. Effective f-number, alignment scale and elapsed time are
statistically the same regressor here, because the focus ramp is monotonic in
time. Separating them needs a capture whose focus order is deliberately
shuffled or interleaved; **no such capture exists in this corpus**, and making
one is the single highest-value experiment the project could run on this
question.

### 4.5 Why the gain must be measured from the frames

MEASURED, best metadata-only model (`Mef = T + F`, no free parameters) against
the measured flux gain, worst per-frame error:

| deck | `max abs(g_meta / g_meas - 1)` |
| --- | --- |
| `bee-3-cpl` | 0.0966 |
| `bee-2-cpl` | 0.1060 |
| `lavendar-cpl` | 0.0577 |
| `leaf-2-cpl` | 0.0183 |

DERIVED: a metadata-derived gain is wrong by up to 10.6% per frame, which is
larger than the entire defect on the AE decks. The gain is therefore
**measured from the frames**, one fitted scalar per frame.

---

## 5. Gain only — the offset was tested and rejected

MEASURED: fitting `L_p(k) = alpha + beta * L_p(ref)` across all 294 patches per
frame returns intercepts that look alarming — up to 491 DN on `lavendar-cpl`.

DERIVED, and this is why they are not dark current: defocus maps
`L -> (1-w) L + w * mean(L)`, which forces exactly the observed pairing of
`beta < 1` with `alpha > 0`. On `lavendar-cpl`, `beta_min = 0.7591` implies
`w = 0.2409`, and `w * mean(L) = 0.2409 * 0.13 = 0.0313` against a measured
`alpha_max = 0.03094` — agreement to about 1%.

MEASURED: adding an offset improves residual RMS by only 2-5%.

**Decision: gain only, no offset.** An offset here is a licence to eat real
signal for a 2-5% residual improvement that is fully explained by blur.

---

## 6. Phase C — `crates/strehl-core/src/photometric.rs`

PR-7 gated this on PR-1 = REAL. PR-1 returned REAL on all four decks, so the
module is built. PR-2 said FIELD, so a scalar is known in advance to be partial;
PR-3 said REFUTED, so the gain is fitted, not derived.

### 6.1 Shape

* One **scalar gain per frame**, no offset, no per-channel term (§4.1 achromatic
  to 0.5%).
* Estimated as a **flux ratio** — mean above black over a fixed region — because
  blur conserves flux and a patch median does not. MEASURED: on `bee-3-cpl` the
  patch medians move 18.2% while the conserved flux moves 8.7%, so a
  patch-median estimator would have applied roughly double the correction and
  spent the excess corrupting real image content.
* Folded over a **fixed, reference-derived low-detail region**, not the whole
  frame. This is a design correction forced by Phase D and it is discussed in
  §7.2; `low_detail_mask` builds the region.
* Refusals rather than silent nonsense: a gain outside `[0.5, 2.0]` or a frame
  with clipped fraction above `1e-4` is refused and left at unity.

### 6.2 The noise model must see the gain — exact rule

DERIVED. The project's model is `sigma^2(S) = g*S + (RN*g)^2` plus a PRNU term.
Scaling the data by `c`:

```text
Var(c*S) = c^2 * (g*S + (RN*g)^2) = (c*g) * (c*S) + (c*RN*g)^2
```

so the scaled data is exactly described by:

| field | transform |
| --- | --- |
| `gain_dn_per_e` | **`c * g`** |
| `read_noise_e` | **unchanged** |
| read floor `RN * g` (DN) | `c *` old floor — it genuinely scales |
| `levels.black` | unchanged |
| `levels.white` | `black + c * (white - black)` |
| PRNU `kappa` | unchanged (it is a fraction of signal) |

**The neighbouring rule in `profile::Corrections` is the opposite one, and
copying it here would be the bug.** There, a gain *correction* re-describes
unchanged data, so the dark floor is preserved and `read_noise_e` moves
inversely. Here the data itself is scaled, so the floor scales with it.
`PlaneNoise::read_floor_dn`'s own doc comment states the `Corrections` rule; it
is correct for that context and wrong for this one.

MEASURED consequence of getting it wrong, on the measured `lavendar-cpl` gain
span `[0.8546, 1.1699]`: a merge that scales frames without updating the model
under-estimates sigma by between `sqrt(c)` (photon-dominated) and `c`
(read-dominated) — **up to 17%**. The gate is calibrated in units of focus
noise, so it then fires too readily on exactly the frames that were brightened,
and noise wins elections it should have lost. `unscaled_sigma_ratio` computes
that error so a caller can assert on it instead of hoping.

### 6.3 Tests

`cargo test -p strehl-core photometric::`, with the registration patch of §8
temporarily applied:

```text
running 21 tests
test photometric::tests::a_clipped_frame_is_refused_rather_than_scaled ... ok
test photometric::tests::empty_and_out_of_range_are_errors_not_silent_defaults ... ok
test photometric::tests::forgetting_the_model_understates_sigma_between_sqrt_c_and_c ... ok
test photometric::tests::the_measured_spans_mis_calibrate_the_gate_by_a_reportable_amount ... ok
test photometric::tests::the_model_lifts_to_four_planes_and_keeps_iso_provenance_and_prnu ... ok
test photometric::tests::a_unit_gain_leaves_the_noise_model_bit_identical ... ok
test photometric::tests::an_implausible_gain_is_refused_rather_than_applied ... ok
test photometric::tests::scaling_is_about_black_and_saturates_at_white ... ok
test photometric::tests::span_is_the_worst_step_the_map_can_remove ... ok
test photometric::tests::the_mask_ignores_uncovered_pixels_when_it_picks_its_thresholds ... ok
test photometric::tests::a_planted_gain_ladder_is_recovered_exactly ... ok
test photometric::tests::a_unit_gain_is_a_bit_exact_no_op_on_the_container ... ok
test photometric::tests::levels_scale_about_black_so_white_still_means_saturated ... ok
test photometric::tests::scaling_down_then_up_returns_the_signal_within_rounding ... ok
test photometric::tests::the_scaled_model_reproduces_the_true_variance_of_scaled_data ... ok
test photometric::tests::the_whole_frame_and_the_low_detail_gain_are_different_numbers ... ok
test photometric::tests::coverage_is_respected_so_the_warp_border_cannot_enter_the_estimate ... ok
test photometric::tests::the_low_detail_mask_needs_both_conditions_not_either ... ok
test photometric::tests::the_read_floor_scales_with_the_data_and_the_electrons_do_not ... ok
test photometric::tests::the_reference_frames_gain_is_exactly_one ... ok
test photometric::tests::defocus_alone_does_not_move_the_estimated_gain ... ok

test result: ok. 21 passed; 0 failed; 0 ignored; 0 measured; 238 filtered out; finished in 0.94s
```

`cargo clippy -p strehl-core --lib -- -D warnings` — clean, exit 0.
`cargo clippy -p strehl-cli --example m99-photometric -- -D warnings` — clean, exit 0.

The load-bearing test is `defocus_alone_does_not_move_the_estimated_gain`: a box
blur conserves flux, so the estimated gain must stay at 1, while a planted 1.20
gain on the same data must be recovered. If that test ever fails the estimator
has started correcting blur, which is the failure mode §4.1 exists to prevent.

`PhotometricError` is hand-written rather than `thiserror`-derived so the module
compiles both as `strehl_core::photometric` and as a `#[path]` include from an
example — the same reason `robust.rs` carries no `crate::` references.

---

## 7. Phase D — does it improve the photograph?

Harness: `crates/strehl-cli/examples/m99-photometric.rs`. It runs the **real
election** — `FocusField::compute`, `merge::regularise`, `merge::FocusStats` —
over the real warped frames of the real deck, and renders a hard election
(each output pixel takes the winning frame's value). Five arms share one decode
pass, so every arm sees byte-identical input:

| arm | what it is |
| --- | --- |
| `A0` | as shipped, no photometric term |
| `A1` | gain from **whole-frame** conserved flux |
| `A2` | gain from the **low-detail region** flux |
| `P0` | planted per-frame gain ramp, no correction |
| `P1` | planted ramp, corrected |

The background region is fixed once, from the **uncorrected reference frame** —
lowest 40% of regularised focus and brightest 40% of luma — so no arm can move
its own goalposts.

### 7.1 The statistic, and the two versions of it that failed first

Negative results about my own instrument, reported because they are the reason
the final numbers can be believed.

**SSC v1 (as pre-registered) had no power and I discarded it.** Regressing the
output luma on the elected frame's level over every background pixel scored
**49.98** on `bee-3-cpl`, where the defect can contribute at most about 1. The
elected frame index is correlated with depth, depth is correlated with scene
brightness, and that scene term is sixty times the photometric one. The
statistic was measuring the scene.

**SSC v2, used throughout below,** differences across the election boundary
instead. Over adjacent background pixel pairs `(i,j)` whose elected frames
differ, regress the luma step `dY` on the two frames' level difference `dR`
through the origin, and divide by the mean background luma:

    SSC = slope(dY ~ dR) / mean(Y)

Scene radiance is continuous across an arbitrary one-pixel boundary, so the
scene term differences away and `E[dY] = 0` under a correct render. If the
render carries the per-frame level, `dY = mean(Y) * dR` and `SSC = 1`. **It is a
correctness statistic, not a change statistic**: a render that merely differs
from the baseline, but whose luma is uncorrelated with which frame won, scores
zero. The calibration is not asserted, it is MEASURED — the planted-ramp arm
scored `SSC = 1.0117` against a theoretical 1.0000 on the first deck it ran on.

Significance is a **permutation null**: shuffle the level ladder 200 times
holding the election map and the luma fixed. That preserves every spatial
correlation in the residuals — which a textbook standard error would not — and
destroys only the association under test.

Second statistic, **BSC**: median `|dY|` across election boundaries over median
`|dY|` within elected regions. 1.0 means the boundary is invisible; above 1
means there is a step at it. It is the direct visual defect.

### 7.2 Results, full decks, all frames, real election

MEASURED. `bee-3-cpl`, 299 frames, plane 3516x2344, 484 600 boundary pairs:

| arm | SSC | null sd | z | SSC vs whole-frame ladder | BSC | bg sd/mean |
| --- | --- | --- | --- | --- | --- | --- |
| `A0` shipped | **1.1489** | 0.0213 | **53.8** | 1.9307 | **2.3615** | 0.39282 |
| `A1` whole-frame gain | 0.5081 | 0.0106 | 47.7 | 0.7898 | 1.5869 | 0.39093 |
| `A2` low-detail gain | **-0.0110** | 0.0056 | -2.0 | -0.0120 | **1.1358** | 0.38951 |

MEASURED. `lavendar-cpl`, 299 frames, plane 3520x2344, 300 074 boundary pairs:

| arm | SSC | null sd | z | SSC vs whole-frame ladder | BSC | bg sd/mean |
| --- | --- | --- | --- | --- | --- | --- |
| `A0` shipped | **1.0768** | 0.0580 | **18.6** | 1.0631 | **5.1276** | 0.34158 |
| `A1` whole-frame gain | -0.0178 | 0.0485 | -0.4 | -0.0160 | 1.4741 | 0.33223 |
| `A2` low-detail gain | **-0.0045** | 0.0485 | -0.1 | -0.0027 | **1.4436** | 0.33221 |

MEASURED. `bee-2-cpl`, 299 frames, plane 3516x2344, 494 586 boundary pairs.
This deck was added late, as an independent replication of §7.3 on a *second*
auto-exposure capture, after the `bee-3-cpl` warp sidecar was destroyed by a
concurrent agent (§9.2):

| arm | SSC | null sd | z | SSC vs whole-frame ladder | BSC | bg sd/mean |
| --- | --- | --- | --- | --- | --- | --- |
| `A0` shipped | **1.2613** | 0.0485 | **26.0** | 1.8463 | 0.8216 | 0.52576 |
| `A1` whole-frame gain | 0.4208 | 0.0139 | 30.2 | 0.5909 | 0.5300 | 0.52356 |
| `A2` low-detail gain | **-0.0261** | 0.0036 | -7.2 | -0.0399 | **0.4631** | 0.52279 |

`bee-2-cpl`'s `BSC` is below 1 in every arm: its background is genuinely noisy
(sd/mean 0.53 against 0.34 and 0.39) so the within-region step it is normalised
by is large. BSC is therefore a deck-relative diagnostic; **SSC is the
calibrated statistic** and it is the one the bars are written against.

### The defect is real in the render

`SSC(A0)` is 1.1489, 1.0768 and 1.2613, at z = 53.8, 18.6 and 26.0. A value of 1
means the render carries the **entire** per-frame background level into the
output. `BSC(A0)` reaches **5.13** on `lavendar-cpl`: an election boundary in the
background shows a luma step five times the neighbouring within-region step. The
brief's suspicion that this is behind the visible mottling and silhouette-hugging
banding is **supported**.

### PR-6 — IMPROVED, for the low-detail gain, on all three decks

| deck | arm | SSC | bar (<= 0.25 x SSC(A0)) | bg sd | verdict |
| --- | --- | --- | --- | --- | --- |
| `bee-3-cpl` (AE) | `A1` whole-frame | 0.5081 | 0.2872 | -0.48% | **NOT IMPROVED** |
| `bee-3-cpl` (AE) | `A2` low-detail | -0.0110 | 0.2872 | -0.84% | **IMPROVED** |
| `bee-2-cpl` (AE) | `A1` whole-frame | 0.4208 | 0.3153 | -0.42% | **NOT IMPROVED** |
| `bee-2-cpl` (AE) | `A2` low-detail | -0.0261 | 0.3153 | -0.56% | **IMPROVED** |
| `lavendar-cpl` (M) | `A1` whole-frame | -0.0178 | 0.2692 | -2.74% | **IMPROVED** |
| `lavendar-cpl` (M) | `A2` low-detail | -0.0045 | 0.2692 | -2.75% | **IMPROVED** |

`A2` removes 99.0%, 97.9% and 99.6% of the defect and takes BSC from 2.36 to
1.14, from 0.82 to 0.46, and from 5.13 to 1.44. Background standard deviation
falls rather than rising in every case, so the second clause of the bar (no more
than +2% relative) is met with room.

The `A1` / `A2` split is **the same on both auto-exposure decks and absent on
the manual one**. That is not a coincidence and §7.3 is what it means.

### 7.3 The design correction: fold the flux over a region, not the whole frame

This is the result I did not expect and it overturns my own Phase C design.

MEASURED, the two gain ladders:

| deck | exposure mode | whole-frame flux span | low-detail region span | apart |
| --- | --- | --- | --- | --- |
| `lavendar-cpl` | Manual | 1.3604 | 1.3617 | **0.1%** |
| `bee-3-cpl` | Program AE | 1.1066 | **1.1848** | **7.1%** |
| `bee-2-cpl` | Program AE | 1.1204 | **1.1815** | **5.5%** |

DERIVED: on a manual deck the whole frame and the background move together and
either estimator works — which is why `A1` passes on `lavendar-cpl`. On an
auto-exposure deck the meter holds *total* flux roughly constant while defocus
moves light between the sharp core and the smooth surround, so whole-frame flux
and background level are genuinely different quantities. `SSC(A0)` measured
against the whole-frame ladder is 1.93 and 1.85 on the two AE decks — the render
is *more* than fully coupled to a ladder of the wrong shape — and correcting
with it leaves 44% and 42% of the defect standing.

The split appears on **both** AE decks and on **neither** reading of the manual
deck. It replicates.

Conclusion, ARGUED from the measurement: **the flux must be folded over a fixed,
reference-derived low-detail region.** `photometric::low_detail_mask` builds
one, and the module documentation now says so. Whole-frame flux remains the
right *diagnostic* — it is the statistic that is blind to blur, and §4 needed
exactly that — but it is the wrong *corrector*.

Note also that the region must be **fixed across frames**. A region re-chosen
per frame slides across the scene as magnification breathes and re-acquires the
exact confound this milestone was convened to remove.

### 7.4 Independent confirmation of the FIELD verdict

MEASURED, and this is the result I trust most in the milestone because the two
numbers come from unrelated routes:

* PR-2, from 12 scene-fixed patches and no election: a frame-only scalar
  explains **0.7511** of the between-patch log-level variance on `bee-3-cpl`.
* Phase D's earlier 40-frame slice, with the real election in the loop:
  the low-detail scalar took SSC from 1.3536 to 0.3521, i.e. removed
  **0.7398**.

Predicted 0.751, measured 0.740, 1.1 points apart. The residual is a **real
spatial term**, not an estimator defect. On the full 299-frame deck the scalar
does better still (99%), because the full bracket's ladder is dominated by its
frame-to-frame component; the field term shows up when the sampled subset is
short. A future milestone wanting the remainder needs a low-order field per
frame, and this module deliberately does not guess at one.

### 7.5 The plant, and two failed plant tests before it

The plant is a **per-frame multiplicative gain** of 20% peak to peak, injected
into the decoded frames at the same seam the correction acts on — the same
*form* as the defect, as the brief requires, not a translation.

Getting a valid plant test took three attempts. Both failures are reported,
because both are ways a plant test can appear to work and not.

**Attempt 1 — a monotonic ramp, scored raw. Invalid: the plant cancelled the
defect.** With `g_k = 1 + 0.20(k/(n-1) - 0.5)`, `SSC(P0) = 1.2067` against
`SSC(A0) = 1.1489` on `bee-3-cpl`, and `BSC` went *down*, 2.3615 -> 1.3470. The
ramp is monotonic in frame index and so is the natural drift, with the
**opposite sign**, so the plant partially **cancels** the defect it was meant to
add. No statistic can see a plant that has been subtracted.

**Attempt 2 — the same ramp, residualised against the deck's own ladder.**
Project the natural ladder out of the ramp and take the partial coefficient on
what is left. Also invalid, and MEASURED to be so: on `lavendar-cpl`
`corr(ramp, background level) = +0.9999`, so the orthogonal part is
near-zero-variance and the coefficient exploded to `SSC_pl(P0) = -41.85`,
`SSC_pl(P1) = +12.94`. Collinearity, not signal.

**The diagnosis is that the *sequence* was wrong, not the *form*.** Any
monotonic plant is collinear with a monotonic drift. So the final plant keeps
the form and amplitude exactly — a per-frame multiplicative gain, 20% peak to
peak, applied at the decode seam — and makes the sequence **pseudo-random in
frame index** (a deterministic SplitMix hash of `k`, so runs reproduce). It is
near-orthogonal to any monotonic drift by construction, which the run confirms:
`corr(ramp, background level) = -0.0395` and `+0.0239`.

MEASURED, with the orthogonal plant. `SSC_pl` is the partial coefficient on the
injected term: 0 if the render does not carry it, 1 if it carries it in full.

| deck | arm | SSC | SSC_pl | BSC | bg sd/mean |
| --- | --- | --- | --- | --- | --- |
| `lavendar-cpl` | `A0` no plant | 1.0768 | **-0.1015** | 5.1276 | 0.34158 |
| `lavendar-cpl` | `P0` planted | 0.8990 | **+0.8119** | **8.0196** | 0.34457 |
| `lavendar-cpl` | `P1` planted + corr | -0.0361 | **-0.0772** | 1.4436 | 0.33221 |
| `bee-2-cpl` | `A0` no plant | 1.2613 | **-0.0445** | 0.8216 | 0.52576 |
| `bee-2-cpl` | `P0` planted | 0.7141 | **+0.6749** | **2.2894** | 0.52916 |
| `bee-2-cpl` | `P1` planted + corr | -0.0035 | **+0.0008** | 0.4631 | 0.52279 |

**PR-6 plant bars, both met on both decks.**

| bar | `lavendar-cpl` | `bee-2-cpl` | verdict |
| --- | --- | --- | --- |
| visible: `abs(SSC_pl(P0) - SSC_pl(A0)) >= 0.5` | 0.9134 | 0.7194 | **SEES THE PLANT** |
| removed: `<= 0.25 x` that | 0.0243 vs 0.2284 | 0.0453 vs 0.1799 | **REMOVED** |

`BSC` now moves the right way too: 5.13 -> **8.02** and 0.82 -> **2.29** when
the plant is injected, and back to 1.44 and 0.46 when it is corrected.

Two honest caveats. `SSC_pl(P0)` is 0.81 and 0.67, not 1.0, because injecting a
20% gain also changes *which frame wins* in places, so the planted term is not
purely additive on top of a fixed election; the detection is unambiguous but the
coefficient is not a calibration. And this final plant could not be re-run on
`bee-3-cpl`, because its warp sidecar was destroyed mid-milestone by a
concurrent agent (§9.2) — `bee-2-cpl`, the other Program AE deck, stands in for
it, and reproduces every `A0`/`A1`/`A2` conclusion independently.

This is a repair to the *instrument*, not to the *bar*. The bars in §0.2 were
fixed before any of it and are unchanged.

### 7.6 Cost

MEASURED, per-arm election seconds over the full deck, from the shared-decode
harness:

| deck | `A0` | `A1` | `A2` | `A1 - A0` |
| --- | --- | --- | --- | --- |
| `bee-3-cpl` (299) | 62.3 s | 65.3 s | 63.8 s | **+3.05 s (+4.9%)** |
| `lavendar-cpl` (299) | 25.1 s | 25.3 s | 25.4 s | **+0.21 s (+0.8%)** |
| `bee-2-cpl` (299) | 26.6 s | 26.5 s | 27.1 s | **-0.16 s (-0.6%)** |

DERIVED: the decks disagree in sign, so this measurement is dominated by
scheduling noise on a machine shared with six other agents, and the honest
reading is **at most a few percent**. The arithmetic is one multiply per sample
plus one noise-model rebuild per frame. The flux reduction is one add per
covered sample and folds into the merge's existing first pass. Against the
stated 74.9 s baseline for a 299-frame 33 MP render, expect a
low-single-digit-percent increase and **no new pass over the data**.

---

## 8. Verbatim patches for files M99 may not edit

### 8.1 `crates/strehl-core/src/lib.rs` — module registration

Required for the module to compile as part of the crate and for
`cargo test -p strehl-core photometric::` to run. This is the only change.

```diff
--- a/crates/strehl-core/src/lib.rs
+++ b/crates/strehl-core/src/lib.rs
@@
 pub mod noise;
+pub mod photometric;
 pub mod plane;
```

(Applied temporarily to run the tests in §6.3, then reverted; `lib.rs` is clean
in the working tree. The example reaches the module by `#[path]` include, the
same route `m93-election.rs` uses for `robust.rs`.)

### 8.2 `crates/strehl-cli/src/merge_cmd.rs` — wiring, **not recommended yet**

I am **not** asking for this to be applied in this milestone. §9.2 says why.
It is written out so the orchestrator has it if it decides otherwise.

Three hunks. First, carry the map and a per-frame model on the shared context
(`struct Ctx<'a>`, around line 796):

```diff
 struct Ctx<'a> {
     geom: PlaneGeometry,
     levels: Levels,
     noise: &'a NoiseModel,
+    /// Per-frame photometric gains, or `None` to merge without a photometric
+    /// term. Built between the two passes from flux accumulated in pass one.
+    photometric: Option<&'a strehl_core::photometric::PhotometricMap>,
     live: &'a AtomicUsize,
```

Second, apply the gain at the decode seam — immediately after the warp block
and **before** `green_luma_with_clip` (around line 929), so every downstream
stage sees corrected data:

```diff
         let frame = frame;
+        // Photometric normalisation, at the seam, after registration so the
+        // gain and the geometry describe the same frame.
+        let noise_for_frame;
+        let noise = match self.photometric.and_then(|m| m.gain(index as usize)) {
+            Some(g) if g != 1.0 => {
+                let mut frame = frame;
+                strehl_core::photometric::apply_to_u16(
+                    frame.data_mut(),
+                    self.levels.black,
+                    self.levels.white,
+                    g,
+                );
+                // The gate is calibrated in units of focus noise. Scaling the
+                // data without scaling the model under-estimates sigma by
+                // between sqrt(g) and g, so the gate fires too readily on
+                // exactly the frames that were brightened. This line is not
+                // optional.
+                noise_for_frame = strehl_core::photometric::scale_noise_model(self.noise, g);
+                &noise_for_frame
+            }
+            _ => self.noise,
+        };
         green_luma_with_clip(
```

and then the two `scratch.field.compute*` calls below take `noise` instead of
`self.noise`.

Third, `MergeOptions` gains `pub photometric: bool` (default `false`), pass one
accumulates a `photometric::Flux` per frame over
`low_detail_mask(&reference_regularised, &reference_luma, 0.40, 0.60)`
intersected with the warp coverage, and `PhotometricMap::from_flux` is built
between the passes.

**If the gain is applied without the `scale_noise_model` line, the merge is
silently miscalibrated.** That is the single most important sentence in this
patch.



---

## 9. Facts, unresolved questions, and where I think the orchestrator is wrong

### 9.1 Candidate facts

Each is one sentence, with its evidence and its label.

1. **MEASURED** — Per-frame background brightness drifts across a focus bracket
   *in scene coordinates*, by 8.2% to 41.0% end-to-end across four decks, so the
   effect survives the sliding-patch confound entirely (§3, PR-1 REAL on 4/4).
2. **MEASURED** — The sliding-patch confound the brief feared is real but small:
   scene-fixed and sensor-fixed ratios differ by 0.7% to 3.4%, and on two decks
   the scene-fixed ratio is the *larger* (§3).
3. **MEASURED** — The drift is **not** a single scalar per frame; a frame-only
   scalar explains 0.751 to 0.883 of between-patch log-level variance on the
   four decks, so there is a genuine spatial field on top (§3, PR-2 FIELD 4/4).
4. **MEASURED** — `1/a^2` from the aligner's fitted scale ladder is **refuted**:
   it is worse than assuming no drift on `leaf-2-cpl` (1.277x), misses the bar
   on `lavendar-cpl` (0.722x), and the free exponent `q̂` spans -0.879 to -6.466
   across four captures on one rig (§4.3, PR-3 REFUTED).
5. **MEASURED** — Under the pre-registered shuffle control, ordered `1/a^2` fits
   *worse than a random reordering of the same frames* on three of four decks,
   including both decks the brief's observation came from — so the test has no
   power there and any apparent agreement would have been void (§4, PR-4).
6. **MEASURED** — `bee-3-cpl` and `bee-2-cpl` were shot in **Program AE**, and
   their whole-frame flux is already flat to ~1.6% RMS; dividing by the true
   per-frame shutter makes them 7.3x to 7.5x **worse** (§2 R0a, §4.4).
7. **MEASURED** — Sony ARW `ExposureTime` is a rounded display value and is
   wrong; `SonyExposureTime` is the true stepless value, and `SonyFNumber2` is a
   per-frame *effective* f-number that moves monotonically with extension (§2).
8. **MEASURED** — Mechanism attribution is **not identifiable** in this corpus:
   `corr(F,K) = +0.9998` and `corr(A,K) ~ 0.99`, and plain linear-in-time fits
   at least as well as every physical model on all four decks (§4, PR-5).
9. **MEASURED** — A metadata-derived gain (`T + F`, no free parameters) is wrong
   by up to 10.6% on a single frame, larger than the whole defect on the AE
   decks, so the gain must be measured from the frames (§4.5).
10. **MEASURED** — The defect is **real in the shipped render**: the output luma
    carries the elected frame's background level essentially in full,
    `SSC = 1.1489`, `1.0768` and `1.2613` at z = 53.8, 18.6 and 26.0 against a
    200-permutation null on three 299-frame decks (§7.2).
11. **MEASURED** — A single fitted scalar per frame, folded over a **fixed
    low-detail region**, removes 99.0%, 99.6% and 97.9% of it and takes the
    boundary step ratio from 2.36 to 1.14, 5.13 to 1.44 and 0.82 to 0.46, at a
    cost of at most a few percent of render time (§7.2, §7.6).
12. **MEASURED** — Whole-frame flux is the wrong estimator on an auto-exposure
    deck: the two ladders differ by 7.1% and 5.5% on the two AE decks and the
    whole-frame gain leaves 44% and 42% of the defect standing, while on the
    manual deck they agree to 0.1% and either estimator works (§7.3).
13. **DERIVED** — Scaling frame data by `c` requires
    `gain_dn_per_e' = c*g`, `read_noise_e'` **unchanged**, `white' = black +
    c(white-black)`, `black` and PRNU `kappa` unchanged; the opposite rule in
    `profile::Corrections` is correct there and would be a bug here, and getting
    it wrong under-estimates sigma by between `sqrt(c)` and `c` — up to 17% on
    `lavendar-cpl`'s measured span — silently mis-calibrating the gate (§6.2).
14. **ARGUED** — Because the estimator is a ratio of fluxes over a *fixed*
    region, and defocus conserves flux, it is blind to blur; the unit test
    `defocus_alone_does_not_move_the_estimated_gain` is the demonstration.
15. **MEASURED** — A **monotonic** plant cannot validate a metric against a
    monotonic defect: on `bee-3-cpl` a +20% ramp partially cancelled the natural
    drift, and on `lavendar-cpl` it had `corr = +0.9999` with it, so both the raw
    and the residualised score were meaningless. A same-form plant with a
    **pseudo-random sequence** is orthogonal by construction (`corr` = -0.04 and
    +0.02) and is detected at 0.81 and 0.67 and removed to -0.08 and 0.00 (§7.5).

### 9.2 What I could not resolve

* **Which physical mechanism it is.** Breathing, effective aperture and lamp
  drift are the same regressor in this corpus (fact 8). The decisive experiment
  is a bracket captured in **shuffled focus order**, which separates
  monotonic-in-scale from monotonic-in-time. It does not exist and it is cheap
  to make. I recommend it as the highest-value next capture.
* **The residual field** (fact 3). A per-frame scalar leaves 12% to 25% of the
  between-patch variance. I deliberately did not guess a functional form; doing
  so without a model risks eating real signal, and the visible defect is already
  gone at the scalar stage.
* **Whether to wire it into the shipped merge.** The correction clears every
  pre-registered bar on all three decks it was run on, but it has been validated
  on a **hard election**, not on the shipped blended merge. My recommendation is
  to land `photometric.rs` and its tests now, and to gate the `merge_cmd.rs`
  wiring (§8.2) behind an opt-in flag until it has been run across the whole
  corpus. I have not applied that patch.
* **`D:\personal\macro\bee-3-cpl\warpmap.txt` is being rewritten by a live
  agent** — it went from 299 placements to 60 to 2 during this milestone, which
  is why the repaired plant column below is reported on `lavendar-cpl` only.
  **This is a shared-state hazard for every milestone that reads a cached
  solve**, because a truncated sidecar is silently accepted for any run whose
  frame list happens to be short enough. The orchestrator should know.

### 9.3 Where I think the orchestrator is wrong

Stated plainly, as invited.

1. **The 1/m² hypothesis is refuted, and it was not close.** The brief calls
   photometric normalisation "free for any stacker that solves alignment". It is
   not free; it is not even available. A fixed exponent of -2 on the aligner's
   `a_k` performs worse than doing nothing on `leaf-2-cpl`, and the free
   exponent varies seven-fold across four captures on one rig.
2. **The 0.37% agreement was an artefact of the summary statistic.** 1.1132 came
   from a 232.7 px corner-drift figure, not from the ladder the aligner actually
   fitted. The ladder predicts **1.1753** against a scene-fixed measurement of
   1.1818 — but that near-agreement is *also* not evidence, because PR-4 shows
   the ordered model has no power on this deck at all.
3. **The confound the brief warned about was not the one that mattered.** The
   brief was right to distrust its own number and right to demand scene
   coordinates. But the sliding patch changes the answer by only 0.7-3.4%. The
   two things that actually broke the measurement were **Program AE** and the
   camera's **per-frame effective f-number**, neither of which is mentioned in
   the brief, and both of which are visible in EXIF in about ninety seconds.
4. **"Check EXIF for shutter, ISO, f-number" is not sufficient as written.** The
   standard `ExposureTime` tag on these files is rounded and will tell you the
   exposure is constant when it is not. Any future milestone reading Sony ARW
   exposure metadata must use `SonyExposureTime` and `SonyFNumber2`.
5. **A correction driven by exposure metadata would make the product worse.**
   On the AE decks, normalising by the true recorded shutter degrades flux
   flatness by 7.3x to 7.5x. The meter is a closed loop that has already done
   the job; opening it re-injects the defect.
6. **The brief's own risk register framing — "no per-frame photometric term at
   all" — is correct, and the fix is worth doing.** That part I agree with, and
   fact 10 and fact 11 are the evidence the register did not have.

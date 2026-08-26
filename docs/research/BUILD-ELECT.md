# BUILD-ELECT: the wrong-depth patches inside the subject

Implementation notes for a fix I did not write. What the mechanism is, what
proved it, what killed the alternatives, what the remedy costs.

**Nothing here has been independently verified.** Every number is mine. Read it
as UNVERIFIED until a verifier repeats it.

Pin: `1cacb61`, binary `C:\dev\strehl-out\pin-1cacb61\target\release\strehl.exe`,
source matched at `C:\dev\strehl-out\pin-1cacb61\`. Subject
`flower-bud-alone-cpl`, 205 frames. Scripts in `experiments/BUILD-ELECT/src/`,
renders and pictures in `C:\dev\strehl-out\BUILD-ELECT\`.

Claims are labelled **MEASURED** (a number I computed, script named) or
**ARGUED** (reasoning, attackable cheaply).

---

## 0. Verdict

**The mechanism is proven. All four of the owner's hypotheses are dead, and so is
a fifth I added.**

The patches are **veiling glare from the defocused silhouette being scored as
focus**. As a frame defocuses, the bright backdrop's blurred edge spreads a broad,
smooth luminance ramp *inward* across the subject. `focus.rs` ranks frames by a
box-aggregated Sobel magnitude, and a first derivative cannot tell a fine sharp
texture from a smooth steep ramp. Deep into the bracket the ramp out-scores the
real surface texture, so `argmax` elects a badly defocused frame over the correct
one. The patch is that band. Its boundary is the contour where the ramp stops
winning, which is why it follows the silhouette's shape and scallops. `n_eff = 2`
over the subject means pass two does not blend the step away.

The one-line version: **the focus measure is not measuring focus near a bright
silhouette, and it is decisively confident about it.**

---

## 1. The picture, first

`C:\dev\strehl-out\BUILD-ELECT\pics\H2-upper-lobe.png` is the whole finding in one
frame. Top: the owner's flat pale wash with its scalloped edge against the
textured leaf. Bottom: the winner field underneath it. The elected index climbs in
a smooth ramp from the silhouette inward until it pins near 204 — the last frame
of the bracket — and then snaps back at a hard scalloped seam. **The red region in
the winner field is the pale wash in the image above it, outline for outline.**

`pics/MECH-pale-wash.png` is the mechanism at one ROI. Frame 40 shows real surface
texture; its high-pass gradient is bright and structured, its low-pass gradient is
black. Frame 136 is a featureless grey gradient with no detail at all; its
high-pass gradient is at the noise floor (median 26.1) but its **low-pass gradient
is 131 and the full measure strehl ranks on reads 138.3 — its maximum**.

`pics/DEPTH-profile.png` is the same claim over the whole subject rather than one
ROI.

---

## 2. The mechanism

### 2.1 The election owns the boundary (MEASURED)

`src/overlay.py` paints winner-field discontinuities on the toned merge.
`pics/A4-scallop-j20.png`: the painted seams land pixel-perfect on every scallop,
lobe and notch of the visible boundary. The defect is in the election, not
downstream of it.

### 2.2 The focus measure follows the ramp, not the texture (MEASURED)

`src/focusdecomp.py` replicates `focus.rs`'s operator — Sobel scaled by 0.125,
box mean at `WINDOW_RADIUS = 13`, divided by `green_luma_sigma` — on the
demosaiced green binned to the plane grid, then splits the luma into
`low = gaussian(L, 8)` and `high = L - low` and runs the identical pipeline on
each. The divisor is taken from the full luma in all three cases, as `focus.rs`
does, so the three curves differ only in which spatial frequencies reach the
gradient operator.

**Commissioning.** A replica that cannot reproduce the shipped election explains
nothing about the shipped election, so the replica's `argmax` is scored against
the index the binary actually elected, read from the dumped election map:

| ROI | replica argmax | shipped elected | shipped band (p5–p95) | band | median |
|---|---|---|---|---|---|
| `pale-wash` | f136 | f133 | [110, 156] | HIT | HIT |
| `leaf-infocus` | f40 | f37 | [34, 40] | HIT | HIT |
| `dark-patch` | f24 | f22 | [21, 46] | HIT | HIT |
| `subject-sharp` | f40 | f66 | [36, 74] | HIT | MISS |

**4/4 on the band, 3/4 on the stricter median test.** The replica reproduces the
shipped election, including the pathological f133 at `pale-wash`.

**The split.** With the replica commissioned:

| ROI | full argmax | high-pass argmax | low-pass argmax | |
|---|---|---|---|---|
| `pale-wash` | **f136** | **f40** | f136 | **SPLIT** |
| `leaf-infocus` | f40 | f40 | f40 | agree |
| `dark-patch` | f24 | f24 | f24 | agree |
| `subject-sharp` | f40 | f40 | f56 | agree |

**The split appears at exactly one of four ROIs, and it is the broken one.** A
split that appeared everywhere would be an artifact of splitting.

At `pale-wash` the high-frequency term peaks at f40 at **2.1× its own
out-of-focus floor** and is otherwise flat at ~0.51 across every other frame —
including at the elected frame. The low-frequency term is ~0.15–0.30 until f104
and then explodes to 2.14 by f120. The high-frequency **share of the full measure
falls from 93.6% at the true peak to 23.5% at the elected frame** (`normalise=1`;
the `normalise=0` arm gives the same conclusion and a better commissioning, so the
result does not depend on my estimate of the output DN scale).

### 2.3 The spatial fingerprint over the whole subject (MEASURED)

Four ROIs can be cherry-picked. The mechanism makes a prediction they cannot fake:
if the ramp is cast by the defocused silhouette, the elected index must be high
near the silhouette and decay inward. `src/depthprofile.py`, whole subject:

| depth inward (plane px) | 10 | 50 | 90 | 130 | 170 | 210 | 250 | 290 | 390 |
|---|---|---|---|---|---|---|---|---|---|
| **subject** elected median | 114 | **120** | 108 | 81 | 60 | 46 | 39 | **34** | **34** |
| **backdrop** elected median | 103 | 44 | 3 | 2 | 107 | 136 | 137 | 134 | 133 |

**The subject curve falls monotonically from 120 to an asymptote of 34 and stays
there.** 34 is the true surface focus, independently measured at three ROIs
(f24–f48). The contaminated band reaches **~250 plane px, 500 px on the output
grid**, inward from the silhouette.

The backdrop row is the control that gives this meaning: it is computed with the
same distance transform and has a completely different, non-monotone shape. The
statistic is reading the picture, not the distance transform.

*(The backdrop dip to 2–3 at 90–130 px is the veiling rim. That is BUILD-HALO's
territory and I make no claim on it.)*

### 2.4 Why the boundary is hard, and why it scallops (ARGUED, on MEASURED parts)

Hard, because pass one is an `argmax` and pass two does not blend across it:
`src/seams.py` measures `n_eff` median **2.0**, mean 2.8, **80.3% at ≤ 3** over
the subject, against median **204** over the backdrop (MEASURED). Where the
picture actually is, the noise-gated average has degenerated to selection.

Scalloped, because the boundary is the contour where the decaying ramp score
crosses the texture score, and the ramp is cast by the silhouette. Its shape is
the silhouette's shape, smoothed. Nothing in it comes from the sampling grid,
which is why H1 and H3 both died.

---

## 3. What killed the alternatives

| | hypothesis | verdict | what killed it |
|---|---|---|---|
| **H1** | box-window plateau at 27 px | **DEAD** | Seam orientation **12.75%** within 10° of an axis against a **22.22%** uniform null (mean distance to axis 38.01° vs 22.50°) — the seams are *anti*-axis-aligned. Plateau median equivalent diameter **7.4 px**, p90 23.5 px, against the 27 px window. `src/geometry.py` |
| **H2** | the regulariser | **DEAD** | Two independent kills. (a) The commissioned replica contains **no regulariser at all** and still reproduces the shipped election — the misranking exists upstream of regularisation. (b) Rendering with `STREHL_EDGE_AWARE=0`, which swaps `regularise_guided` for the plain 17×17 box, leaves **86.18% of winner pixels bit-identical** and the defect visually unchanged (`pics/H2-upper-lobe.png`). |
| **H3** | tile grid leaking through | **DEAD** | Whole-plane spectra of the winner field show **no integer pitch and no harmonic ladder**; rows and cols disagree (18.1 px z=4.1 vs 52.1 px z=5.8). `src/geometry.py` |
| **H4** | the null: an honest coverage gap | **DEAD** | The through-focus curve at `pale-wash` has a clear texture peak at **f40, 2.1× its own floor**, that the election missed by ~96 frames. The data has an answer; the election did not take it. `src/ladder.py`, `src/focusdecomp.py` |
| **H5** | *mine:* quantised adaptive selection radius | **DEAD** | The defect is identical at mean radius **5.17 px** and **12.99 px**. `src/crops.py` |
| — | alignment | **DEAD** | `STREHL_ALIGN=0` render essentially identical. `pics/B1-noalign-*.png` |

H4 deserves the plainest statement, because the owner asked for it to be taken
seriously: **this is not a bad capture.** The bracket covers the surface. Frame 40
holds the detail. The stacker threw it away.

---

## 4. The specification

### 4.1 Where

`crates/strehl-core/src/focus.rs` — `gradient_magnitude`, consumed by
`FocusField::compute`, `compute_with_fine`, `compute_scaled` and
`compute_layered`. **Not** `merge.rs`: the regulariser and the gate are downstream
of the misranking and are exonerated in §3.

### 4.2 The invariant

> The focus response at a pixel must be invariant, to within the noise floor, to
> the addition of an arbitrary linear luminance ramp across the selection window.

A ramp carries no resolvable detail. Any operator that scores it as focus can be
beaten by defocus, because defocus manufactures ramps out of edges.

This is a unit test, not a render: synthesise a flat noise field, add a ramp of
increasing slope, and assert the response moves by less than `FOCUS_NOISE_SD`.
The shipped operator fails it by construction — `|grad|` of a ramp is the slope.

### 4.3 The target number

The subject-interior depth profile of §2.3 must be **flat to within ±8 frames from
40 px to 400 px inward from the silhouette**. It is currently **120 → 34, an 86
frame excursion**. `src/depthprofile.py` computes it and is the acceptance
instrument.

Secondary, cheaper to watch during development: at the `pale-wash` ROI the elected
index must fall inside the texture mode, `[24, 56]`, not `[110, 156]`.

### 4.4 The guard

A remedy that changes the winner field everywhere is a different defect, not a
fix. Three guards, in increasing cost:

1. **The correct regions must not move.** `dark-patch`, `leaf-infocus` and
   `subject-sharp` must keep their current elected mode. In simulation the
   remedy already passes this: at `dark-patch` the two arms give an identical
   winner field — median f32 both, `|A−B|` black except hairline contour traces
   (`pics/SIMFIX-dark-patch.png`).
2. **The backdrop profile shape must survive.** The backdrop row of §2.3 is
   correct behaviour and must not be flattened along with the subject row.
3. **`FOCUS_NOISE_SD` and the gate must be re-measured.** `FOCUS_NOISE_SD =
   0.015214` and `DEFAULT_GATE = 4.0` are calibrated against the *current*
   operator. Changing the operator invalidates both. This is the expensive part
   and it is not optional — the gate constant is what decides `n_eff`.

### 4.5 Evidence the remedy works, and its limits

`src/simfix.py` elects a winner at every pixel of the seam crop twice: with the
shipped operator and with `|grad(L - blur(L))|`. Arm A reproduces the seam (its
commissioning). Arm B: the fraction of the crop electing the far mode falls from
**41.7% to 9.7%**, and the control crop is untouched.

**This is a simulation and I am not going to overstate it.** It runs on 21 of 205
frames, on demosaiced green rather than the raw CFA green, with no regulariser, no
gate and no pass two. It shows the *ranking* changes. It cannot show what the
shipped merge would output.

---

## 5. The cost

**1. The argmax goes noisy where there is genuinely no texture.** Removing the
ramp removes a large spurious signal, and where the surface has no high-frequency
content there is nothing left to elect on, so the winner field becomes
noise-dominated. Measured: seam energy in the simulated arm **rose from 1.33 to
2.16**. The blotchy red speckle in `pics/SIMFIX-pale-wash.png` panel 3 is that
cost, visible. The regulariser and gate exist to absorb exactly this and are
omitted from the simulation, so 2.16 is an upper bound rather than a prediction —
but the direction is real and it will not be free.

**2. Smooth surfaces lose their only focus cue.** A genuinely smooth, low-texture
surface lit by broad shading has *only* low-frequency signal. The shipped operator
elects something there; a ramp-invariant one may have nothing above the noise
floor and will fall through to whatever the regulariser propagates in. On this
subject that is a good trade. On a subject that is mostly smooth it may not be.

**3. Recalibration.** `FOCUS_NOISE_SD`, the gate, and every downstream number
calibrated on them — `n_eff`, the confidence output, and the published
window-ladder and gate-sweep results — are measured against the current operator
and must be re-measured. This is the largest cost by effort and the easiest to
skip by accident.

**4. It does not fix the picture on its own.** §2.4 shows pass two is not blending
(`n_eff = 2`). Correcting the ranking removes the *wrong-depth* content; it does
not by itself guarantee a seam-free join where two valid depths meet. That may
still need work in `merge.rs`, and it is where this lane touches BUILD-HALO's.

---

## 6. What I did not verify

- **The remedy in-crate.** I was scoped out of `crates/`. Everything in §4.5 is a
  numpy simulation on 21 frames, 2 crops, 1 subject.
- **Any subject other than `flower-bud-alone-cpl`.** The depth profile, the
  decomposition and the `n_eff` numbers are one capture. The mechanism is generic
  to gradient-based focus measures (ARGUED), but the reach of 250 plane px is
  specific to this bracket, this aperture and this backdrop brightness.
- **The exact operator.** My replica works on demosaiced green, not the raw CFA
  green, and omits the edge-aware layer support. It commissions 4/4 on the band
  and 3/4 on the median; the `subject-sharp` median miss is unexplained.
- **`LOW_SIGMA = 8` is a choice, not a calibration.** I picked it as the
  regulariser's own scale. The right cut frequency for a shipped operator should
  be derived from the PSF, not from my convenience.
- **Whether the lower lobe is the same defect.** `dark-patch` elects at its own
  texture peak (f24) with `n_eff = 2` and shows no split. The lower-lobe
  "polygon" is therefore probably a *milder or different* thing — possibly a tone
  step rather than a sharpness step (`dark-patch` band-pass 7.258% vs
  `patch-outside` 6.886%). I did not chase it. **This is the one part of the
  owner's brief I have not accounted for.**
- **Frame 168 onward.** The ladder OOM'd at f168 with five agents sharing the
  machine. Curves cover f0–f160.

---

## 7. Three things the owner should know that were not the assignment

**1. The brief's "three merge arms" premise is wrong.** `ORCH-rim/twoside.py`
does not render three arms. It renders one `merge-lin.tif` and applies two
post-hoc numpy edits whose weights only touch pixels within `REACH = 60` px of the
silhouette. The three crop centres are *literally the same pixels* — the script's
own log prints `core detail 1.000x`. The patches being "identical in all three
panels" carries no information about the veiling work.

**2. `STREHL_ONLY_FRAME` breaks registration, and a live instrument depends on
it.** It re-solves alignment against the single frame it is given (`reference
frame 0, 1 placed`), so single-frame renders sit in their own coordinates, not the
merge's. `ORCH-rim/twoside.py` folds per-pixel `min`/`max` over misregistered
frames. Workaround: `STREHL_ALIGN=0` on both the merge and every single frame.

**3. Over the subject, the merge is not averaging.** `n_eff` median **2.0**, 80.3%
at ≤ 3, against median 204 over the backdrop. The product's headline claim that
averaging beats selection does not apply where the picture is.

---

## 8. Reproduction

```
# renders (pinned binary, align off so every arm shares one frame of reference)
STREHL_ALIGN=0 STREHL_DUMP_ELECTION=... STREHL_DUMP_NEFF=...  strehl stack ... --demosaic
STREHL_ALIGN=0 STREHL_EDGE_AWARE=0 STREHL_DUMP_ELECTION=...   strehl stack ... --demosaic

python src/ladder2.py --frames 0:205:8 --tag crops   # ~10 min, keeps crops
python src/focusdecomp.py --tag crops --normalise 0  # commissioning + the split
python src/mechanism.py                              # pics/MECH-*.png
python src/simfix.py                                 # pics/SIMFIX-*.png
python src/h2control.py                              # pics/H2-*.png
python src/depthprofile.py                           # pics/DEPTH-profile.png
```

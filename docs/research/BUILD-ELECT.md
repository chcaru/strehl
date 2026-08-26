# BUILD-ELECT: the wrong-depth patches inside the subject

Implementation notes for a fix I did not write. What the mechanism is, what
proved it, what killed the alternatives, what the remedy costs.

**Nothing here has been independently verified.** Every number is mine. Read it
as UNVERIFIED until a verifier repeats it.

Pin: `1cacb61`, binary `C:\dev\strehl-out\pin-1cacb61\target\release\strehl.exe`,
source matched at `C:\dev\strehl-out\pin-1cacb61\`. Subjects
`flower-bud-alone-cpl`, 205 frames (sections 1 to 8) and `bee-1-cpl`, 299 frames
(section 9). Scripts in `experiments/BUILD-ELECT/src/`, renders and pictures in
`C:\dev\strehl-out\BUILD-ELECT\`.

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

**Amended by section 9, after a second subject.** `bee-1-cpl` reproduces the
mechanism (Spearman -0.998 inward, drop 77 frames) and shows that the bright
outline tracing the silhouette is the same defect, not a separate one. But it
also shows the null H4 is **true at some pixels**: two of three defect ROIs have
no texture peak anywhere in 299 frames. The election does not abstain there, it
elects on veil strength alone, and section 4's remedy alone makes those regions
**worse**. The specification is therefore two-part and the parts must ship
together. See sections 9.6 to 9.9.

**Amended by section 10, after H5.** The owner's fifth hypothesis — that the
focus measure rewards edge *density* and a box `max` would fix it — is **dead**:
0 of 1 defect ROIs on `flower-bud`, 0 of 3 on the bee, controls preserved. At the
defect the veil ramp's own *peak* gradient (162.5) exceeds the texture's peak
gradient (122.5), so no order statistic of `|grad|` on the full luma can elect the
right frame. **The discriminating axis is spatial scale, not order statistic**,
and the two are orthogonal. What survives is a refinement, not a mechanism:
`max` is a better aggregate than `mean` wherever an answer exists, and `hp max|g|`
gives the largest election margin measured anywhere (41.22x against 9.50x
shipped), at the same asymptotic cost. Section 10 adopts it into the section 4
specification. H5's instrument also **independently re-confirms H4**, killing the
main open threat to section 9.6.

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

**Amended by section 10.10.** Also `box_mean` in the same file: the window
aggregate should become a running **max** (van Herk/Gil-Werman, O(1) per pixel, so
no speed trade). The filter change and the aggregate change are independent and
compose; the filter is what fixes the defect, the aggregate is what widens the
margin.

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

**Amended by section 10.10.** A third number, cheapest of the three and requiring
no render: the dynamic range of `hp max|g|` at the bee's `leg-good` ROI must be
`>= 30x`. Measured 41.22x with the specified operator; 9.50x with the shipped one.
`src/h5.py` computes it from `.npz` crops already on disk.

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

---

## 9. `bee-1-cpl`: a second subject, and what it changes

The owner rendered the whole library from the same pin, looked at
`gallery-1cacb61\bee-1-cpl.jpg` at full frame, and reported a hard bright outline
tracing the entire silhouette with a **jagged, stair-stepped boundary**. He
proposed that this and the interior patches are one mechanism: a **blocky winner
field**. He also warned that the image he looked at was a JPEG downsampled 2.93x
from the 7032 px render, and that both steps can manufacture stair-stepping.

299 frames, dark bee on a white paper sweep. Renders in
`C:\dev\strehl-out\BUILD-ELECT\bee\`: `D-*` aligned, `E-noalign-*` with
`STREHL_ALIGN=0`, both with the election and `n_eff` dumps.

**His unification is right. His mechanism is wrong. And on this subject the null
he told me to test is partly TRUE, which changes the specification.**

### 9.1 The caution, tested first (MEASURED)

`bee1.py` crops the linear 16-bit TIFF at 1:1 beside the same region of the JPEG,
under one fixed tone transform taken from measured paper white, with no per-panel
autoscaling.

The jaggedness is **real at 1:1**. It is not JPEG and not resampling. The crops
also show more than he described: large flat featureless taupe blobs laid over the
foreleg and the upper-left body, with hard boundaries carrying straight segments
and sharp angular corners, while the surrounding pixels carry fine hair detail.

Pictures: `pics/BEE1-left-foreleg.png`, `pics/BEE1-upper-left-body.png`.

### 9.2 His sharp test, confirmed (MEASURED)

He predicted that dumping the election should show the same jagged boundary in the
field itself, spatially coincident with the outline. `bee2.py` renders merge,
winner index, `|grad winner|`, `n_eff` and painted seams at 1:1 with
nearest-neighbour upsampling only.

**Confirmed exactly.** Seams trace every lobe, notch and angular corner of the
visible blobs. The winner field is a piecewise-constant patchwork spanning f36 to
f298 inside a single 760 px crop, and `n_eff` median 2 to 3 means nothing blends.

Pictures: `pics/BEE2-D-left-foreleg.png`, `pics/BEE2-D-upper-left-body.png`.

### 9.3 His mechanism, refuted (MEASURED)

A blocky field from a box window or a tile grid must leave seams preferentially
axis-aligned. `bee3_orient.py` measures seam tangent orientation against two
baselines: the picture's own edges, and a uniform null at 22.22% within 10 degrees
of an axis.

| region | seams within 10 deg of axis | picture edges | uniform null |
| --- | --- | --- | --- |
| silhouette band, 40 px | 20.49% | 15.43% | 22.22% |
| interior | 19.72% | 24.61% | 22.22% |

Both regions are **below** the uniform null. There is no grid signature. This
matches the flower-bud result (12.75% against the same null) on a subject with a
completely different silhouette.

An instrument defect found and fixed here: the first verdict rule compared seams
only against the picture's own edges, and declared grid leakage live in the
silhouette band purely because the picture's edges there happened to be unusually
non-axial. A criterion has to beat the theoretical null as well as the data
baseline. Corrected, both regions read clean.

Picture: `pics/BEE3-orientation.png`.

### 9.4 Alignment is not the cause (MEASURED)

The bee's alignment is poor by the project's own standard: held-out error
**17.001 px** against M86's `T_usable` of 4.0, and coverage rescaled the FOV to
0.9236 before upsampling. So it had to be ruled out rather than assumed.

Re-running the whole comparison on `E-noalign-*` reproduces the defect
identically: same flat blobs, same seams tracing them, `n_eff` median 2, winner
p5 to p95 34 to 210 on the foreleg crop. Alignment is not the cause, exactly as on
flower-bud.

### 9.5 The veiling fingerprint is present here too (MEASURED)

This is the cross-subject confirmation section 6 listed as missing. `beedepth.py`
profiles the elected index against distance inward from the silhouette, with the
backdrop as a control.

| | bee-1-cpl | flower-bud-alone-cpl |
| --- | --- | --- |
| elected index at the silhouette | f175 | f120 |
| deep inside the subject | f98 | f34 |
| drop | 77 frames | 86 frames |
| Spearman, inward | **-0.998** | -0.97 |
| Spearman, backdrop control | -0.648 | non-monotone |

The mechanism generalises. The middle panel of the picture is the plainest
statement of it in this whole document: the thorax core elects f30 to f50, which
is correct, and a broad band electing f200 to f280 hugs the entire silhouette.
**That band is the bright outline the owner saw.** The outline is not a rim light
and not a cut-out artifact. It is the veil ramp winning the election in a collar
around the subject.

Two honesty notes. The subject mask needed a fixed region chosen by eye
(`Y_KEEP = 0.86`) because the shaded foreground lip of the paper sweep is below
any luma threshold that keeps the bee and joins it across the full width of the
frame, so no morphological rule separates them. And the backdrop control at -0.648
is weaker than flower-bud's, because a paper sweep genuinely recedes and so
genuinely has a monotone depth.

Picture: `pics/BEE-depthprofile.png`.

### 9.6 H4 is ACCEPTED here, at two of three defect ROIs (MEASURED)

The brief requires the null to be tested before any fix is proposed. On flower-bud
it died: there was a clear texture peak at f40 that the election missed by 96
frames. On the bee it does not die.

`beeladder.py` renders 26 single frames spanning f0 to f298 with `STREHL_ALIGN=0`,
keeping crops. `beedecomp.py` runs the `focus.rs` replica over them and splits the
luma into a veil part and a texture part. The replica commissions **5/5** on band
and 4/5 on median against the shipped align-off election, and the `bee-sharp`
control passes: the test correctly reports that the election is right there.

| ROI | elected | texture peak | peak / own floor | verdict |
| --- | --- | --- | --- | --- |
| `blob` | f270 | f204 | **1.25** | H4 ACCEPTED, curve flat |
| `fringe` | **f298** | f36 | **1.13** | H4 ACCEPTED, curve flat |
| `fringe-ok` | f108 | f264 | 1.70 | H4 rejected, election missed it |
| `leg-good` | f177 | f180 | 17.14 | election correct |
| `bee-sharp` | f45 | f48 | 4.35 | election correct, control PASS |

At `blob` and `fringe` the texture response is flat to within 1.13x to 1.25x of
its own floor across all 299 frames, against 17.14x at a neighbouring ROI 90 px
away. The contact sheet says the same thing without arithmetic: those crops are
featureless in **every** frame in the bracket. `fringe` elects f298, the very last
frame, which is the classic symptom of an argmax that never had anything to turn
over on.

So for those pixels the capture genuinely has no answer, and the patch is the
correct answer to a bad capture in the narrow sense the brief meant.

**This does not make the stacker blameless.** When every frame is featureless, the
gradient aggregate is not flat, because it still ranks frames by veil strength.
The election therefore does not abstain; it confidently imports a wash from a
frame 90 or more steps away from the local surface, and lays it against
neighbours that did have an answer. The hard seam is manufactured by the election
even though the depth information was never there. **The defect is the absence of
abstention, not only the choice of measure.**

Pictures: `pics/BEE-H4-sheet.png` (the pixels, elected frame ringed in red),
`pics/BEE-H4-curves-n0.png` (the curves).

### 9.7 My own remedy, tested per pixel, and where it fails (MEASURED)

Section 4 proposed high-passing the luma before the gradient. That was measured on
a subject where a texture peak existed. A flat curve is the case that breaks it,
because argmax over a flat curve is a coin flip and a coin flip per pixel is
speckle, which is invisible in an ROI median. `beesimfix.py` therefore runs three
rules per pixel over whole crops: **A** `argmax(full)`, what ships; **B**
`argmax(high)`, the section 4 remedy; **C** B plus abstention, where a pixel whose
peak does not clear its own floor by 1.30 does not vote and takes the mean of the
confident pixels within 12 px instead.

| ROI | abstain | seam A | seam B | seam C | spread A | spread B | spread C |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `leg-good` | 2.0% | 1.57 | **1.00** | **0.87** | 168 | **12** | **12** |
| `bee-sharp` | 0.0% | 0.93 | **0.73** | **0.73** | 120 | **48** | **48** |
| `fringe-ok` | 11.1% | 2.89 | 3.17 | **2.02** | 240 | 108 | 92 |
| `blob` | 35.0% | 3.48 | **5.13** | 3.99 | 298 | 192 | 192 |
| `fringe` | 53.0% | 3.21 | **10.12** | 8.23 | 262 | **274** | 274 |

Where the data has an answer the remedy is not marginal, it is dramatic:
`leg-good` collapses from a 168-frame spread of veil bands to a **12-frame**
near-uniform field. Where the data has no answer it is actively harmful, and the
worse the coverage the worse the damage.

**Falsification attempt against my own claim.** A, B and C above are raw
per-pixel argmax, while the shipped field is regularised (`merge_cmd.rs`
1167-1215, `REGULARISER_RADIUS = 8`). If regularisation absorbs B's speckle the
harm claim is overstated. Applying a median filter at the shipped radius equally
to all three:

| ROI | seam A* | seam B* | seam C* |
| --- | --- | --- | --- |
| `leg-good` | 1.17 | **0.37** | **0.29** |
| `bee-sharp` | 0.64 | **0.31** | **0.31** |
| `fringe-ok` | 1.78 | **1.01** | **0.87** |
| `blob` | 1.74 | 1.69 | **1.42** |
| `fringe` | 1.49 | **3.21** | 2.71 |

The claim **survives only in narrowed form**. Regularisation absorbs the damage at
`blob`, and B is a clear win at three of five ROIs. At `fringe`, the 53%-abstain
ROI, B remains 2.2x worse than A after regularisation and its spread stays at 274
frames against A's 262. Abstention improves it to 2.71 but does not repair it,
because there is nothing nearby to borrow from.

Picture: `pics/BEE-simfix.png`.

### 9.8 The amended specification

Section 4 stands and is unchanged, but it is **necessary and not sufficient**. It
needs a second part, and shipping the first without the second will make
low-coverage regions worse.

**Part 2, where.** `crates/strehl-core/src/merge.rs`, at the point the winner is
chosen, and in the `Estimator` that already knows the per-frame focus responses.

**Part 2, the invariant.** *A pixel whose through-focus texture response does not
rise above its own floor by a prominence threshold must not elect a frame by
`argmax`.* It must instead take the elected index from the confident pixels around
it, and must be marked in a per-pixel confidence output.

**Part 2, the target number.** Prominence `max/min` of the high-passed response,
threshold **1.30**. Measured separation at that threshold: 17.14 and 4.35 for the
two correctly-elected ROIs against 1.13 and 1.25 for the two H4-accepted ROIs.
That is an order of magnitude of daylight, not a tuned edge.

**Part 2, the guard.** Abstention fraction must be **0.0% at `bee-sharp` and
2.0% at `leg-good`**. If a change makes correctly-elected regions abstain, it has
broken the instrument rather than the defect. And the confidence output must be
emitted, not just used internally, because the brief's own answer for a region
with no answer is to report it rather than fabricate detail.

The abstention mask in column 5 of `pics/BEE-simfix.png` is already that product
deliverable in prototype: on this subject it marks exactly the regions a
photographer would want flagged as un-stacked.

### 9.9 What the amended fix costs, beyond section 5

- **It admits the stacker cannot always answer.** 53% of one ROI and 35% of
  another get flagged rather than filled. That is honest and it is also a visibly
  weaker product claim than the current silent confidence.
- **A borrowed index is still not the truth.** Rule C fills from neighbours, which
  is a smoothness prior, not a measurement. It will be wrong across a genuine
  depth discontinuity, which is precisely where occlusion lives.
- **Part 1 without part 2 is a regression** in low-coverage regions, measured at
  2.2x seam energy after regularisation. These two changes must ship together.

### 9.10 What I did not verify on the bee

- I did not run the amended rule inside the binary. Everything in 9.7 is a
  replica of `focus.rs` operating on ladder renders, commissioned 5/5 on band but
  never on the shipped merge path.
- The regularisation mimic is a median filter at the shipped radius, **not** the
  shipped regulariser, which is guided and gated. It is a proxy and its numbers
  should not be quoted as the regulariser's.
- 26 rungs over 299 frames. A texture peak narrower than 12 frames would be
  invisible to this ladder, and a flat curve is exactly what a missed narrow peak
  would look like. This is the strongest surviving threat to the H4 acceptance in
  9.6 and I could not close it without a denser ladder.
- I did not establish **why** `blob` and `fringe` are featureless in every frame:
  a genuinely smooth surface, a see-through gap to blank paper, and a region
  washed out by veil in every frame all produce the same flat curve here.
- The three defect ROIs are three ROIs. I have not measured what fraction of the
  whole subject is H4-accepted, so I cannot say how much of the outline is
  recoverable and how much only reportable.

### 9.11 Bee reproduction

```
python src/beerois.py                                 # pick + draw ROIs, check by eye
python src/beeladder.py --frames 0:299:12 --tag crops # ~7 min, 26 rungs, keeps crops
python src/beedecomp.py --tag crops --normalise 0     # commissioning, H4, contact sheet
python src/beesimfix.py --tag crops                   # three rules + regulariser mimic
python src/beedepth.py                                # whole-subject fingerprint
python src/bee2.py --tag E-noalign                    # winner-field coincidence
python src/bee3_orient.py                             # seam orientation
```

---

## 10. H5: "the focus measure rewards edge density, not edge sharpness"

The owner ranked this first and asked for it to be tested before anything else.
**It is not supported.** It fails at 0 of 1 defect ROIs on `flower-bud` and 0 of 3
on the bee, with every control preserved. The reason it fails is more useful than
the hypothesis would have been if it were true, so this section is mostly about
the reason.

### 10.1 The hypothesis, as stated

A box **sum** of `|grad|` answers "how much edge energy is in this window", not
"is this window in focus". Blur conserves total variation, so on a fringe of fine
hairs a defocused frame can carry a *larger* window sum than the sharp one: each
hair spreads into a wide low-contrast smear, the smears overlap, and more of them
fall inside the window. A box **max** is not TV-conserving — peak gradient falls
monotonically under blur — so the prediction is sharp:

> At pixels inside the bright band, `mean|g|` elects a defocused frame and
> `max|g|` elects the in-focus one.

### 10.2 The instrument (MEASURED)

`src/h5.py` computes six candidate statistics over the **same** `r = 13` window on
the **same** ladder crops already used in sections 2 and 9, so nothing but the
statistic changes: `mean|g|`, `mean|g|^2`, `mean|g|^4`, `max|g|`, `hp mean|g|`,
`hp max|g|`, where `hp` is the high-pass `L - blur(L)` of section 4. It also
carries two diagnostics that are not candidates: `_lp max|g|`, the peak gradient of
the *low-pass* residual (the veil ramp alone), and `_hp max|g|` (the texture
alone).

Commissioning: the shipped statistic `mean|g|` must reproduce the frame the
production merge actually elected at each ROI, to within the p5–p95 band of the
elected index there. It does, **4/4 on `flower-bud` and 5/5 on the bee**. The
replica is the same one commissioned in sections 2.2 and 9.6.

The control criterion is band-based, not median-based. An earlier version compared
against the median alone and produced a false "CONTROL BROKEN" at `subject-sharp`;
that was an instrument defect and it is fixed.

### 10.3 The result (MEASURED)

`flower-bud`, elected frame per statistic (dynamic range in brackets):

| roi | shipped | `mean\|g\|` | `max\|g\|` | `hp max\|g\|` |
| --- | --- | --- | --- | --- |
| **pale-wash** (the defect) | 133 | f136 (8.87x) | **f120** (4.92x) | **f40** (2.72x) |
| leaf-infocus | 37 | f40 (1.94x) | f40 (2.43x) | f40 (2.56x) |
| dark-patch | 22 | f24 (3.38x) | f24 (5.27x) | f24 (4.84x) |
| subject-sharp | 66 | f40 (2.63x) | f40 (4.34x) | f40 (3.56x) |

The texture mode at `pale-wash` is `[24, 56]` and the veil mode is `[110, 156]`
(section 4.3). `max|g|` moves the election from f136 to f120 — **which is still
inside the veil mode.** It moves by 16 frames along a 96-frame error. The
high-pass moves it to f40, into the texture mode, as section 4 already specified.

The bee, at its three defect ROIs:

| roi | `mean\|g\|` | `max\|g\|` | `hp max\|g\|` |
| --- | --- | --- | --- |
| blob | f264 (1.93x) | f252 (1.44x) | f192 (1.34x) |
| fringe | f298 (2.12x) | f298 (1.56x) | f36 (1.17x) |
| fringe-ok | f264 (1.53x) | f264 (2.56x) | f264 (2.56x) |

`max|g|` does not move `fringe` at all, moves `blob` by one rung, and leaves
`fringe-ok` where it was. No control moves anywhere on either subject.

**The decisive evidence is a picture, not the table.**
`pics/H5-choice-flower-bud.png` renders the frame each statistic elects. At
`pale-wash`, `mean|g|` elects f136 — a featureless bright-to-dark ramp with no
botanical structure at all. `max|g|` elects f120 and renders **the same
featureless ramp**. `hp mean|g|` elects f40 and the bud surface, its ridges and a
diagonal structure are all plainly there. Three control rows below it are
identical across all three statistics. Whatever H5 changes, it does not change
what the picture shows.

### 10.4 Why it fails, and the general statement (MEASURED)

The `_lp max|g|` and `_hp max|g|` diagnostics answer this directly. They are the
**peak** gradient of the veil ramp and the **peak** gradient of the texture — the
exact quantity H5 argues falls monotonically under blur.

| roi | ramp peak `_lp max\|g\|` | texture peak `_hp max\|g\|` | who wins |
| --- | --- | --- | --- |
| **pale-wash** (the defect) | **162.5** | 122.5 | **ramp, by 1.33x** |
| leaf-infocus | 15.9 | 118.8 | texture, by 7.47x |
| dark-patch | 32.4 | 188.6 | texture, by 5.82x |
| subject-sharp | 24.2 | 134.5 | texture, by 5.56x |

At the defect, and only at the defect, **the veil ramp's peak gradient exceeds the
texture's peak gradient.** So the substitution H5 proposes cannot work: no order
statistic of `|grad|` computed on the full luma — not the mean, not the max, not
any percentile between them — can elect the texture frame at a pixel where the
ramp's own maximum is the largest gradient present. The quantity being ranked is
already larger for the wrong feature.

The general statement, and it is the part worth keeping:

> **H5 moves along the order-statistic axis. The defect lives on the spatial-scale
> axis. They are orthogonal.**

Mean to max is a change in *how the responses inside the window are pooled*. The
veil and the texture are separated by *how fast they vary in space*, and no
pooling rule can recover a distinction the pooled quantity never encoded. Only a
scale-selective filter can, which is why the high-pass works and the max does not.
The three power statistics `mean|g|`, `mean|g|^2`, `mean|g|^4` make the same point
from the other end: raising the exponent from 1 to 4 walks the statistic from mean
toward max and the elected frame at `pale-wash` never moves off f136.

### 10.5 The stated premise is measurably false (MEASURED)

H5 rests on the claim that a box mean of `|grad|` is "nearly blind to defocus" on
this kind of structure. At `pale-wash` the shipped `mean|g|` has a dynamic range
of **8.87x across the bracket — the largest of any ROI measured on that subject**,
larger than at `dark-patch` (3.38x), `subject-sharp` (2.63x) or `leaf-infocus`
(1.94x).

The operator is not blind. It is **confidently peaked, on the wrong feature**.
That distinction matters for the fix: a blind statistic would be rescued by making
it more discriminating, which is what H5 proposes. A confidently wrong statistic
is made *worse* by that, because sharpening the discrimination sharpens the error
too. This is visible in the table above — `max|g|` at `pale-wash` produces a
**cleaner** peak on the ramp, not a weaker one.

### 10.6 What survives, and is worth taking (MEASURED)

The instinct behind H5 is right about something real, just not about the defect.
Where an answer **does** exist, peak-based statistics are strictly better
discriminators than the shipped mean:

| roi (all correctly elected) | `mean\|g\|` shipped | `max\|g\|` | `hp max\|g\|` |
| --- | --- | --- | --- |
| leg-good (bee) | 9.50x | 23.62x | **41.22x** |
| bee-sharp | 3.77x | 5.90x | **7.10x** |
| dark-patch | 3.38x | **5.27x** | 4.84x |
| subject-sharp | 2.63x | **4.34x** | 3.56x |
| leaf-infocus | 1.94x | 2.43x | **2.56x** |
| fringe-ok (bee) | 1.53x | 2.56x | **2.69x** |

`hp max|g|` gives the largest dynamic range measured anywhere in this
investigation: **41.22x at `leg-good` against 9.50x for the shipped statistic, a
4.3x improvement in the margin the election has to work with.** A larger margin is
directly a lower probability that noise decides the argmax, which is the
mechanism section 2.4 blames for the hard boundary.

Two honesties about that table. `hp max|g|` wins at 4 of 6, not 6 of 6 — it loses
to plain `max|g|` at `dark-patch` and `subject-sharp`. Both are `flower-bud` ROIs
where the veil is present, and the diagnostic says why: `_lp max|g|` has a range of
12.65x and 9.88x there, so part of plain `max|g|`'s extra margin at those two ROIs
**is veil contribution that happens to peak on the right frame**. That is not a
virtue. It is the same contribution that elects f120 at `pale-wash`, and it is
luck that it points the right way at those two. `hp max|g|` gives up the luck along
with the contamination.

And a running max is O(1) per pixel by van Herk/Gil-Werman, the same cost class as
the running box sum already in `focus.rs`, so **this is not a speed trade.** That
matters given the project's mandate.

### 10.7 H5's instrument independently re-confirms H4 (MEASURED)

This was not the purpose of the experiment and it is the strongest incidental
result in it. Section 9.6 accepted the null at two of three bee defect ROIs on the
grounds that the texture response is flat across 299 frames. The obvious threat to
that acceptance — logged as an open question in section 9.10 — is that flatness
could be an artifact of the *mean*, a real peak washed out by averaging.

`hp max|g|` is a maximum, not a mean, and it is computed on the high-pass, so it is
the statistic least able to hide a narrow texture peak. Across the whole bracket it
gives:

| roi | `hp max\|g\|` dynamic range |
| --- | --- |
| blob | **1.34x** |
| fringe | **1.17x** |
| leg-good (control, same subject) | **41.22x** |

A 31x separation between the defect ROIs and a good ROI on the same subject, from a
statistic chosen by someone trying to prove a different point. **H4 stands, and it
now stands on two statistics that fail in opposite directions.** It is not closed —
the ladder is still 26 rungs of 299 and a peak narrower than ~12 frames would fall
between them — but the mean-washout explanation is dead.

### 10.8 The spilled-milk band, measured (MEASURED)

The owner's first constraint was that the band is "brighter than the subject and
about as bright as the far backdrop". `src/milk.py` profiles the merged luma and
the elected index against signed distance from the silhouette on the align-off
merge. `pics/MILK-profile.png`.

| region | luma | / clean backdrop |
| --- | --- | --- |
| clean backdrop (frame corners) | 17893 DN | 1.00 |
| **the band**, collar at d = -15 px | **19865 DN** | **1.11** |
| deep subject, d > 150 px | 3320 DN | 0.19 |

**The constraint is confirmed.** The band is 6.0x brighter than the deep subject
and 1.11x the clean backdrop — the merge is producing better-than-clean-backdrop
values in a zone that should be subject or veiled backdrop.

Two things the profile shows that were not asked for:

1. **The election is non-monotonic across the silhouette, and the shape is
   diagnostic.** Far backdrop elects f137; a ring at d = -90 to -140 px collapses to
   **f2**, the near end of the bracket, with luma dipping to 0.90 (this is the grey
   veil, and it is BUILD-HALO's lane); then the collar at d = -15 px **bounces back
   to f115** with luma at its 1.11 peak. A monotonic optical falloff cannot produce
   a collapse and a bounce. An election can.
2. **Brightness and election co-vary inside the subject: Spearman +0.888 over 40
   distance bins.** Where the merge elects a far frame it is also bright, and both
   decay together inward. This is the same coupling section 2.2 established at a
   single ROI, now measured over the whole subject as a function of distance.

A note on method that is itself a small finding. The subject mask is drawn by
brightness, at 0.55x clean backdrop. The artifact *is* excess brightness. So the
band lands just **outside** the mask, and only 0.5% of pixels inside the mask reach
90% of clean backdrop. That is not a flaw to work around: a threshold that
separates a dark green bud from a white sweep can only put the band on the backdrop
side **if the band has been rendered at backdrop levels**. The mask failure is the
measurement.

### 10.9 The trichome claim is untested (ARGUED)

The owner's third constraint — "its lobes and drips sit at the hair/trichome
positions" — is the one clue I have **not** measured, and I am flagging it rather
than quietly adopting it.

My account is that veil reach depends on local silhouette geometry: a convoluted
boundary admits ramps from several directions at once, they superpose, and the
contour where the ramp stops winning bulges outward there. The trichome fringe is
the most convoluted part of this silhouette, so lobes at trichome positions follow
from geometry alone and do not require the hairs to be doing anything special.

That is an argument, not a measurement, and it competes with the owner's reading
that the hairs themselves are the cause. **The test that would settle it:** extract
the local boundary convexity (or a windowed count of silhouette-crossing per unit
arc length) along the contour, and rank-correlate it against the band's outward
reach at the same arc position. If reach tracks convolutedness, geometry is
sufficient. If it tracks hair density independently of convolutedness, it does not.
Roughly an hour, no new renders. I did not run it.

### 10.10 Amendment to section 4

Section 4 specified the high-pass. This section adds the pooling rule, and the two
are independent choices that compose:

- **Section 4 stands unchanged as to the filter.** The high-pass is what fixes the
  defect. The scale axis is the one that matters and nothing here weakens that.
- **Adopt `max` rather than `mean` as the window aggregate**, i.e. `hp max|g|`
  rather than `hp mean|g|`. This does not fix anything section 4 does not already
  fix — both elect f40 at `pale-wash` — but it raises the election margin at
  correctly-elected pixels from 9.50x to 41.22x at the best-measured ROI, at the
  same asymptotic cost.
- **New target number for the guard:** `hp max|g|` dynamic range at `leg-good` must
  be >= 30x (measured 41.22x; shipped 9.50x). This is a cheap regression sentinel
  that does not require a full render.
- **The guard of section 4.4 is unchanged and is not optional.** Changing the
  aggregate from a mean to a max changes the *distribution* of the focus response,
  so `FOCUS_NOISE_SD = 0.015214` and `DEFAULT_GATE = 4.0` must be re-measured for
  the new operator. Both are calibrated against a box mean. Shipping the max
  without recalibrating the gate would change `n_eff` by an unknown factor.

### 10.11 Reproduction

```powershell
cd experiments\BUILD-ELECT\src
python h5.py            # both subjects, from the ladder .npz already on disk
python milk.py          # flower-bud, from the align-off merge already on disk
```

Neither needs a render. `h5.py` reads
`C:\dev\strehl-out\BUILD-ELECT\ladder-crops\` and
`C:\dev\strehl-out\BUILD-ELECT\bee\ladder-crops\`.

Pictures: `pics/H5-choice-flower-bud.png` (the decisive one),
`pics/H5-curves-flower-bud.png`, `bee/pics/H5-choice-bee.png`,
`bee/pics/H5-curves-bee.png`, `pics/MILK-profile.png`.

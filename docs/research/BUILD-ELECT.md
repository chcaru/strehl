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

**Amended by section 11, after running the owner's pre-registered acceptance
test on real merges.** A modified pin (commissioned bit-identical at the shipped
setting, potency-checked) rendered `flower-bud` and `coffee-bean` under all four
candidate focus statistics. **Every one fails his ring test, including mine:**
12.47% shipped, 13.89% under H5's box max, 12.44% under section 4's high-pass,
12.26% under section 10.10. The negative control never moves and the veiling term
never moves, so the arms are neither inert nor random — the bright ring simply is
not a focus-statistic defect. It is **H4 at d = +21 px**: no frame in 205
resolves the trichome fringe there (peak gradient flat to 1.32x while brightness
climbs monotonically 60.5% to 103.5%), and the merge's band edge carries **7.6x
more gradient than any source frame**, so the scalloped boundary is manufactured
at a seam rather than selected. Section 2's mechanism was measured *inside* the
subject and I carried it to the band without re-testing; that was wrong. The band
needs abstention and a coverage output, not a better statistic. See sections 11.3
to 11.7.

**Amended by section 12, after looking at a real winner field at 1:1.** The
mechanism is now measured, and it unifies the band, the polygonal patches and the
owner's own 52x fringed-versus-smooth separation. On `lavendar-cpl` the field is
**smooth on the subject** (0.741 frames mean neighbour difference) and **20.4x
rougher in the backdrop** (15.094): the 191-frame excursions another lane
reported are the paper sweep, not seams cutting photographed detail, so the
speckle reading wins and the blocky-field reading dies. But the picture showed
what no first-difference statistic could report, because it is *smooth*: a
**coherent lobed collar** of extreme index hugging the silhouette. Roughness
rises monotonically outward, 1.04 to 17.32 frames, so the election is at its most
confident exactly where the artifact is, and the collar elects ~220 while the
subject elects 108. The mechanism: the near backdrop has no texture in any frame
but does carry the **veil**, a smooth ramp whose steepness varies frame to frame,
which a box aggregate of gradient magnitude cannot distinguish from texture. It
ranks veil steepness and returns a confident wrong answer; far out the veil is
gone and the field collapses to noise. **The scalloped boundary is the handover
contour between those two regimes**, and a handover contour follows silhouette
morphology, which is why a fringe produces lobes and a smooth bean does not. This
is why all four focus statistics failed: they reorder a ranking, and in the collar
there is nothing to rank. The fix is abstention plus nearest-confident propagation,
specified in section 12.6. One instrument failure of my own is recorded in 12.1:
my component test returned SEAMS at 137.92x a random null and was **wrong**,
because the null was drawn from the whole frame while the excursions are confined
to one region, so region membership scored as shape. The picture caught it.

**Superseded by section 13. This lane is closed: the defect is solved by another
route.** BUILD-BLEND's Laplacian multi-band merge was run against the owner's
pre-registered acceptance test on one common mask. **The ring goes 12.47% (pinned
gallery baseline) to 5.68% (BUILD-BLEND's own control) to 0.37% (blend), against a
pre-registered bar of 1%** — and it is *absent*, not reduced, because the blend's
profile no longer turns over between d=1 and d=205 px at all. The negative control
holds: `coffee-bean` stays at or below 0.33% within 40 px in every arm. **The
patches are gone too**, judged at 1:1 at the four *worst* places for the blend,
where the control holds hard-edged flat plateaus cutting across plant material and
the blend holds resolved trichomes. Section 12's mechanism predicts exactly this:
the election's error is a **low-frequency** one committed by a **hard per-pixel
selection**, and a band decomposition stops selecting the low bands per pixel, so
it removes the mechanism rather than trimming its output. Two corrections against
myself in 13.4: my do-no-harm estimator reported -23.1% "REAL SOFTENING" and was
wrong twice, once by selecting on the control's own extremes (**the sign flips on
all three subjects when the selection is reversed**) and once by using a
level-dependent metric where the blend legitimately darkens a region **20710 DN to
1417 DN**. Real costs do survive: `lavendar` loses 12.4% to 25.0% of subject
contrast with a sign that survives reversal, and the blend reaches into
BUILD-HALO's veiling term (-19.4% to -15.7%). What survives from this lane is not
a merge change but the **coverage output** of 12.6: no frame in `flower-bud`'s
bracket resolves the trichome fringe, so "the artifact is gone" and "the detail is
there" are different claims and only the first is supported.

**Corrected by section 14, after independent verification.** Section 13 measured on
a **tone curve**: `bm/...-ctrl.tif` was rendered `--srgb` (black 0.00985, white
0.35458) and `bm/...-blend.tif` came from a **different executable with a different
black point**, so its two arms differed photometrically as well as in the merge. A
compliant pair — one binary, both arms linear — was already on disk in `flip/`, and
I read that directory and inferred from filenames what its logs state in their
first line. Three numbers are withdrawn: the **0.37%** headline, the **12.47 ->
5.68** attribution split, and the deep-interior **+4.46%** level change, which
reverses to **-11.83%** on a compliant instrument. **The conclusion is unchanged
and the finding is stronger.** On one binary with both arms linear the control —
which is the default ship path — reads **12.65% at d=21 px**, matching the pinned
gallery baseline's 12.47% to 0.18 points, and the blend has **no interior local
maximum anywhere inside d=275 px**. So nothing removed half the ring before the
blend: **the whole of it is the blend**, and section 13 under-credited another lane
by inventing a step that does not exist. One measurement now runs against the
blend, in 14.4: on `coffee-bean`, the pre-registered placebo, the blend introduces
profile structure in the **47-93 px band** that the control does not have, **1.17%
against 0.07%** at the same distance. At d <= 40 px the placebo still holds.

**Amended by section 15, after looking at 14.4 and having the look verified.** I
tried to withdraw 14.4 and got half of it. What is right: the control's bright
stripe on the paper sweep is **invented** — it appears in **no source frame** —
and the same holds on the subject, where three of six ground-truthed sites show
the control carrying a hard-edged banded plateau no frame has. What is wrong: my
exculpation. "The blend moved the placebo because it reduced the veil" relocates
the violation to the veil rule instead of clearing it, and the veil is another
lane's. My contrast number was also inflated three ways — naive Weber **-30.05%**
becomes **-11.24%** once clipping is excluded and the veil ramp detrended, against
**-8.18%** in the deep interior, so a 6x localisation is really **1.37x**. And I
missed the largest fact about that band: **20.48% of it is clipped at 65535 in
the blend arm against 0.0952% in the control, a 215x increase**, with `clip
census` disabled in that path. **14.4 is reworded, not withdrawn.** Three defects
in my own instruments are fixed in 15.7, including one caveat I had published
against my own number and which was simply false. The lane still closes; three
items are routed out of it, in 15.9.

**Amended by section 16, which withdraws a finding of mine, and then by 16.10,
which withdraws my first reason for withdrawing it.** The owner gave me back the
shadow-washout claim I had reported outside my brief -- that both arms lose about
a third of a real, **focus-invariant** shadow on `coffee-bean` at d=120..250.
**It is withdrawn, and it should stay withdrawn.** What holds: the truth value is
not obtainable, because mean versus median on identical pixels moves it **3.39
points**, larger than the 2.6-point effect claimed; 15.5's per-frame masks slide
by **4.99 points of frame area, IoU down to 56%**, so its invariance test never
held the region fixed; and the band does not lie on a cast shadow at all -- on a
second subject it traces the edge of a bright sweep while the rule's own shadow,
at negative d, is never sampled.

What does **not** hold is the mechanism I first offered. I wrote that the deficit
is focus-dependent (r = +0.654, +0.982) and therefore defocus bleed. A verifier
refuted it: **bracket index predicts the deficit better than sharpness does, r =
+0.9887**, the "sharpest" frames are merely the late ones, and detrending the
bracket collapses the effect to **0.13 points** and reverses its sign on the
second subject. The cause is measured in 16.9 -- **~176 full-res px of scene
motion across the bracket, reversing sign across the frame, i.e. a magnification
change from focus breathing** -- against a band 130 px wide. So 15.5 held the
scene and moved the mask; I held the pixel window and let the scene move.
**Neither instrument ever held scene content fixed.** The single-frame ladder's
exoneration list is also cut from eight stages to five: the two output TIFFs are
**100.0000% identical**, and the hull clamp, Laplacian reconstruct, photometric
fit, clip census and regulariser are inert or forced at n=1 rather than measured
innocent. The d=120..250 row of 15.5's table is retracted; so is 16.4's bleed
claim. Two further instruments of mine failed their own commissioning and are
reported dead in 16.8.

**Amended by section 17, which retracts my arc ordering after the owner opened
the picture.** I reported that the blend *introduces* an arc at d~275 and that
the control "has no arc there", on a SIGNAL/NULL ratio of 12.1x against 0.9x.
**Backwards.** The control carries a dark aura averaging **-10.13% of far field
(-1935 DN)** over d=100..500 and reaching **-25.48%** at d=112, negative in
**all 19 sectors**, not recovering to within 1% until d=488. The blend over the
same band is **+0.21% (+39 DN)** and recovers by d=112. My statistic scored a
local **maximum** over its outward trough, so a monotonically recovering
**depression** has no interior peak and returned exactly **0.00** -- a bump
detector pointed at a hole -- and separately its null window (700..1050) sat
**inside** its own reference window (600..1400). Either bug alone would have
been fatal. What survives is the azimuthal point: per sector the blend's
residual is a *localised bright* excursion of **+7.69%** in sector 2, which the
whole-frame +0.21% understates exactly as 15.9 predicted averaging would.

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

**And the picture says it better than the ratios do.** In
`bee/pics/H5-choice-bee.png` the `blob` row is three featureless smooth gradients:
f264, f252 and f204 are visually indistinguishable and none of them contains any
structure at all. The `fringe` row is the strongest single frame in this whole
investigation — `mean|g|` and `max|g|` elect **f298**, the high-pass elects
**f36**, and the two panels are *identically blank*. Those frames are 262 apart in
a 299-frame bracket. Two nearly opposite ends of the capture render the same empty
wash, which means the information is not somewhere else in the bracket; it is
nowhere in the bracket. Compare the `leg-good` row directly below, same subject,
same render, where individual hairs are resolved with specular highlights on them.

No change to the election can fix `blob` and `fringe`. This is what abstention is
for, and it is why section 9.8's part two is not optional.

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

---

## 11. The owner's pre-registered acceptance test, run for real

**All four candidate focus statistics fail it, including my own.** The bright
ring is not produced by the focus statistic, and no change to the election can
remove it. This section is a negative result against section 4 and I am stating
it plainly.

### 11.1 His numbers, independently re-derived (MEASURED)

`src/ringprofile.py` is written from scratch, not adapted from his
`rimprofile.py`: different bin grid (uniform 2 px where the ring lives, against
his hand-placed edges), different peak finder. Two of his design choices are
copied deliberately because they are correct — prominence measured against the
trough **outside** the peak rather than the far field, and the whole profile
printed above the verdict.

| | his number | mine | agree |
| --- | --- | --- | --- |
| flower-bud ring | 12.0% at d = 18 px | **12.47% at d = 21 px** | yes |
| flower-bud darkening | -36.5% | **-40.4%** | yes |
| coffee-bean darkening | -38.2% | **-39.4%** | yes |

His headline number reproduces. Better than that: my baseline render `fb-mean`
is **bit-identical by SHA-256** to the `fb-1cacb61-lin.tif` he measured, so the
two instruments read the same pixels and the 0.47 point difference is binning
alone.

One number does not reproduce. He reports coffee-bean's only interior peak as
0.23% at 450 px; I find **1.92% at 155 px**, with a whole ladder of far-field
peaks his coarse bins stepped over. This does not damage his argument — at the
*matched* location where flower-bud's ring lives, coffee-bean reads **0.02% at
9 px**, so at like-for-like distance the separation is far larger than the 52x
he claimed, not smaller.

### 11.2 The instrument: a modified pin, commissioned (MEASURED)

To run his test against real merges rather than ROI simulations I cloned the pin
to `C:\dev\strehl-out\pin-elect\` and added one env-gated selector to
`focus.rs::compute_at_radius`, following the existing `STREHL_WINDOW_RADIUS`
convention. `crates/` in the repo is untouched.

`STREHL_FOCUS_STAT` = `mean` (shipped) | `max` (H5) | `hp` (section 4) |
`hpmax` (section 10.10). A separable running max via a monotonic deque provides
the max pooling.

Two gates, both required, both passed:

- **Commissioning.** `STREHL_FOCUS_STAT=mean` on `coffee-bean` is
  **bit-identical by SHA-256** to the shipped binary. The clone did not drift.
- **Potency.** `fb-max` differs from `fb-mean` (3.79% of samples, max delta
  15970 DN) and `fb-hp` differs too (0.69%, max delta 16365 DN). The env var
  reaches the production election. This check was not optional: `merge_cmd.rs`
  branches to `compute_with_fine` when statistics are enabled, which bypasses the
  patched function, and an inert arm would have produced four identical "results"
  that looked like a clean finding.

### 11.3 The result (MEASURED)

**Target — `flower-bud`, must go from 12.47% toward 0.23%:**

| arm | ring prominence | vs shipped | veiling darkening |
| --- | --- | --- | --- |
| `mean` (shipped) | 12.47% | — | -40.4% |
| `max` (H5's fix) | **13.89%** | **worse by 11%** | -39.5% |
| `hp` (section 4, mine) | **12.44%** | unchanged | -40.4% |
| `hpmax` (section 10.10) | **12.26%** | -1.7% | -40.4% |

**Negative control — `coffee-bean`, must not move:**

| arm | ring at 155 px | at 9 px | darkening |
| --- | --- | --- | --- |
| shipped | 1.92% | 0.02% | -39.4% |
| `max` | 1.92% | 0.10% | -39.4% |
| `hp` | 1.92% | 0.02% | -39.4% |
| `hpmax` | 1.92% | 0.09% | -39.4% |

The negative control **passes for every arm** — nothing moved. And his fourth
constraint holds: the veiling darkening does not move under `hp` or `hpmax`
(-40.4% throughout). I did not reach into the other lane's term.

So the arms are not inert and they are not random. They simply do not touch the
ring.

**The picture is the result, not the table.** `pics/ACCEPT-fb-arms.png` shows one
crop across the silhouette in all three arms under one fixed tone transform. The
white scalloped band is present, thick and identical in all three: band luma
102.7%, 102.6%, 102.6% of the far field. The difference maps below show both arms
moved only hairline contours; the median of `|hp - mean|` **inside the band is
0 DN**. My fix does not touch the artifact it was proposed to fix.

### 11.4 Why: H4, at the band, which I had never tested there (MEASURED)

Six single frames spanning the bracket already existed. At the band locus:

| frame | band luma | % far field | `hp` peak gradient |
| --- | --- | --- | --- |
| f025 | 11524 | 60.5% | 184 |
| f051 | 13035 | 68.5% | 192 |
| f076 | 16030 | 84.2% | 208 |
| f127 | 19552 | 102.7% | 242 |
| f153 | 19603 | 103.0% | 240 |
| f178 | 19689 | 103.5% | 243 |
| **the merge** | **19854** | **104.3%** | **1853** |

Two things, and both are decisive.

**There is no in-focus frame at the band.** Peak gradient runs 184 to 243 across
the bracket — flat to **1.32x**, the same signature that made me accept H4 on the
bee at 1.13x and 1.25x. What varies is not focus but *brightness*, smoothly and
monotonically from 60.5% to 103.5%. `pics/BAND-frames.png` confirms it by eye:
every frame is either a soft dark blur or clean white paper, and **not one
contains a crisp trichome fringe.** The bracket has no answer here.

**The merge's band edge exists in no source frame.** Merge peak gradient 1853
against at most 243 in any input — **7.6x more edge energy than the data
contains.** A per-pixel election can only emit values that some frame holds, so a
boundary sharper than every input is not selected, it is *manufactured* at the
seam where the winner index jumps. That is the hard scalloped edge.

This explains the null in 11.3 completely. **Both candidate fixes change how
frames are ranked, and at the band there is nothing to rank.** All 205 frames are
equally featureless; any statistic returns noise; the argmax is arbitrary; and the
arbitrary choice is biased toward the bright end because brightness rises
monotonically with frame index. Substituting a better discriminator cannot help
when the thing being discriminated is absent.

### 11.5 A correction to my own report

Section 2 established veiling misranking at `pale-wash`, an ROI **inside** the
subject, where a real texture peak at f40 exists and the election misses it by
~96 frames. That finding stands and section 4 fixes it.

The **band** is at d = +21 px, *outside* the silhouette, and it is a different
case: H4, no answer, nothing to elect. When the owner reassigned the band to my
lane I carried section 2's mechanism across to it without re-testing at the new
location. That was wrong. Section 4 was never aimed at the band and, measured, it
does nothing there.

`flower-bud` therefore carries **both** failure modes, at different distances from
the same silhouette — misranking inside, no-answer outside — which is why a single
remedy was never going to clear the whole image.

### 11.6 His pairing is confounded, though it does not change the verdict (MEASURED)

His inference rests on the two subjects differing in exactly one property. They
differ in at least three:

| | coffee-bean | flower-bud | ratio |
| --- | --- | --- | --- |
| subject/backdrop contrast | 2.91:1 | **12.48:1** | **4.29x** |
| subject share of frame | 59.6% | 21.7% | 2.74x |
| pixels at clip | 2.39% | 0.00% | — |

Contrast is not a nuisance variable here: it is the driver *both* candidate
mechanisms depend on, so the correlation is equally consistent with either and
cannot choose between them. And coffee-bean's silhouette covers 59.6% of its
frame with backdrop on two sides only, which is a thin basis for a far-field
reference. It remains a usable **negative control** — it has no ring to remove and
none of my arms gave it one — but it is not a controlled contrast to
`flower-bud`.

`couch-fibers-cpl` is worth one line: unimodal, p95/p5 = **2.30** against 15.90
and 17.96 for the other two. It is dense fine structure with **no silhouette at
all**, which is why it is a good do-no-harm subject and a poor discriminator. It
kills "fine density alone is sufficient to fool the measure", which H5 never quite
claimed, and leaves H5's actual conjunction untested by it.

### 11.7 The specification, corrected

**For the band, no focus statistic is the answer.** The remedy is the one the
owner's own H4 instruction names: *report it, do not fabricate it.*

- **Where:** `crates/strehl-core/src/merge.rs`, the election, not `focus.rs`.
- **Invariant:** where the through-focus response is flat to within the noise
  floor across the bracket, the merge must **abstain** rather than argmax. Measured
  flatness threshold from three independent ROIs on two subjects: a peak-to-floor
  ratio below **1.35x** is indistinguishable from no answer (band 1.32x, bee
  `blob` 1.34x, bee `fringe` 1.17x; a good ROI on the same subject reads 41.2x).
- **Behaviour on abstention:** emit a coverage/confidence plane, and fall back to
  the *near* end of the bracket rather than the far end. ARGUED on MEASURED
  values: at the band f025 sits at 60.5% of the far field against the merge's
  104.3%, so a near fallback cannot produce a bright ring — prominence goes to
  zero or negative by construction.
- **Target number:** `flower-bud` ring prominence from **12.47%** to **below
  1.0%**, measured by `src/ringprofile.py` with the mask taken from the shipped
  arm. Not 0.23%: that was coffee-bean's *far-field* wobble at 450 px and is not
  the right yardstick. At the matched 9-21 px distance coffee-bean reads 0.02%.
- **Guard:** `coffee-bean` must stay at 1.92% / 0.02% and its darkening at
  -39.4%; `flower-bud` darkening must stay at -40.4%, which is the other lane's
  term.

Section 4 stands unchanged for the subject **interior**. Section 10.10 stands as a
margin improvement. Neither addresses the band and I no longer claim they do.

### 11.8 The cost

Abstention with a near fallback trades a bright fabricated fringe for a **soft
honest one**. At the band the near frames are visibly blurred — f025 is a smooth
dark gradient with no resolved hairs. The image gets a silhouette that reads as
out of focus instead of one that reads as cut out and pasted. That is better, and
it is not free: the owner will see softness where he now sees a hard edge, and on
a subject whose entire visual interest is its trichome fringe that is a real loss.

The deeper cost is that **the capture cannot be fixed in software**. 205 frames
and not one resolves the fringe. If the fringe matters, it needs a bracket that
covers it — finer steps through the near end, or a different aperture. A coverage
output is what tells the photographer that *at capture time*, which is the only
point where it is still fixable.

### 11.9 Reproduction

```powershell
# the modified pin (built outside the repo; crates/ untouched)
cd C:\dev\strehl-out\pin-elect
& "$env:USERPROFILE\.cargo\bin\cargo.exe" build --release -p strehl-cli
$env:STREHL_FOCUS_STAT = "hp"   # mean | max | hp | hpmax
.\target\release\strehl.exe stack D:\personal\macro\flower-bud-alone-cpl `
    --out C:\dev\strehl-out\BUILD-ELECT\accept\fb-hp.tiff --demosaic

cd experiments\BUILD-ELECT\src
python ringprofile.py <arms...> --mask-from ...\fb-mean.tiff
python acceptlook.py     # pics/ACCEPT-fb-arms.png
python bandframes.py     # pics/BAND-frames.png
```

Pictures: `pics/ACCEPT-fb-arms.png` (the four-arm null),
`pics/BAND-frames.png` (why), `pics/RING-masks.png` (the coffee-bean mask),
`pics/COUCH-look.png`.

## 12. The winner field, looked at: seams, speckle, and a coherent collar

The owner supplied a free 1:1 linear election dump from BUILD-CHROMA
(`lavendar-index.tif` on the plane grid, plus its matching binned merge), a lead
(neighbour excursions reaching 191 frames), and a correction (nobody, including
him, had actually verified that those excursions form straight or scalloped
boundaries; BUILD-CHROMA retracted its only supporting crop because it was 6x
`np.repeat` and therefore blocky by construction). He asked for the falsification
if the excursions turned out to be isolated speckle.

This section answers that question, and in answering it finds the mechanism for
the band.

### 12.1 My first instrument said SEAMS and it was wrong

`seamshape.py` thresholded the field at a 50-frame neighbour jump, ran 8-connected
component morphology, and compared against three random spatial nulls of identical
pixel count. MEASURED:

| | px | comps | mean size | max size | px in comps >= 8 |
| --- | --- | --- | --- | --- | --- |
| measured | 1514179 (18.35%) | 4392 | 344.76 | 1117713 | 99.7% |
| random null x3 | 1514179 | ~605700 | 2.50 | ~54 | ~21.4% |

It printed `SEAMS: excursions are connected, far beyond chance`, at 137.92x the
null mean component size.

The picture (`pics/SEAM-shape.png`) contradicted it in three seconds. The subject
carries a **smooth, coherent, organic depth field**. The **backdrop** is
salt-and-pepper chaos, and that chaos is where essentially all the excursions
live. Two of the three largest components, cropped and shown at 1:1, are
multicoloured noise spanning index 0 to 298 inside a 180 px box, over a merge
region with no detail in it at all.

**The defect is mine and it is worth recording.** The null scattered pixels over
the whole frame while the real excursions are confined to one region. A confined
set percolates inside its own region, so the test was measuring *"these pixels are
clustered into a region"*, which is true and trivial, rather than *"these pixels
form curvilinear seams"*, which is the claim on trial. A null must be drawn from
the same region as the measurement, otherwise region membership is scored as
shape. This is the same class of error as the owner's far-field prominence test:
a detector that cannot see the thing it was built to see, returning a confident
verdict either way.

It was caught only because the script emits a picture next to its verdict. The
house rule earns its keep again: **a verdict line must never be the only output.**

### 12.2 Redone with a region-matched null

`seamwhere.py` segments subject from backdrop on local contrast (brightness
thresholding fails: a lavender head on a bright sweep is not cleanly bimodal),
then repeats the shape test with the null drawn from the same region. MEASURED:

| region | mean abs 4-neighbour diff | > 50-frame jumps | > 150-frame jumps | median index |
| --- | --- | --- | --- | --- |
| **subject** | **0.741 frames** | **1.00%** | 0.32% | 108 |
| backdrop | 15.094 frames | 27.38% | 9.68% | 219 |

**The backdrop is 20.4x rougher than the subject.** On the subject, where the
photograph is, the elected index changes by less than three quarters of a frame
per pixel step, out of 299.

So the owner's lead resolves cleanly, and against his own reading:

- **CONFIRMED:** excursions of up to 298 frames (the entire bracket) between
  adjacent pixels are real.
- **REFUTED:** they are not on the subject and they are not seams cutting through
  photographed detail. **97% of them are in the featureless backdrop**, where no
  frame contains any texture, every frame is an equally good answer, and the
  argmax is decided by sensor noise. BUILD-CHROMA's 191-frame figure is a
  measurement of the paper sweep.

This is H4, the null, holding over an entire region rather than at a single ROI:
where the data has no answer, the election returns noise. It also explains
BUILD-CHROMA's own caveat that roughness was only a 1.15x contributor to chroma.
Electing a random frame in a region where all frames are the same blank white
costs almost nothing in the image domain. **Excursion count does not imply
image-domain effect size, and here it demonstrably does not.**

On the subject there remain 28027 excursion pixels (1.00%), organised at 143x the
region-matched null. That set is real and structured, but it is one percent, it is
sparse, and it is not what makes these pictures unusable.

### 12.3 What the picture showed that no statistic had asked about

`pics/SEAM-where.png`, panel 3, shows the backdrop index alone. The far backdrop
is noise, as above. But **hugging the silhouette there is a solid, smooth,
coherent rind of extreme index with lobed and scalloped outer boundaries.** It is
not speckle, it is not noise, and no first-difference statistic could have
reported it, because it is smooth: a roughness metric scores it as the *best*
behaved part of the frame.

`seamcollar.py` profiles roughness and elected index against signed distance
outward from the silhouette. MEASURED, whole profile:

| d (px) | n | median index | roughness (frames) | luma (DN) |
| --- | --- | --- | --- | --- |
| 2 | 53793 | 222 | **1.04** | 9237 |
| 6 | 52027 | 218 | 1.26 | 9323 |
| 12 | 92773 | 212 | 1.95 | 9375 |
| 20 | 84660 | 198 | 3.08 | 9348 |
| 28 | 81037 | 194 | 4.06 | 9271 |
| 40 | 148134 | 196 | 6.14 | 9386 |
| 56 | 137627 | 205 | 8.74 | 10197 |
| 80 | 248816 | 227 | 12.18 | 10591 |
| 112 | 235514 | 232 | 15.06 | 10688 |
| 160 | 442774 | 226 | 16.13 | 11147 |
| 224 | 435820 | 224 | 16.57 | 11762 |
| 320 | 837456 | 222 | 16.76 | 11984 |
| 448 | 798879 | 218 | 17.07 | 12244 |
| 640 | 1233481 | 217 | 17.32 | 12861 |
| 984 | 512772 | 224 | 16.47 | 14160 |

Subject median index: **108**.

Two facts, both monotonic and neither previously reported:

1. **Roughness rises monotonically with distance, 1.04 -> 17.32 frames.** The
   near-silhouette collar is **9.2x smoother** than the far field. The election is
   at its most confident and coherent exactly where the artifact is.
2. **The backdrop elects ~212-222 at every distance, while the subject elects
   108.** The collar is rendered from frames **~104 away** from the subject's own
   focus, roughly a third of the bracket.

### 12.4 The mechanism

Put the two halves together, and §2 of this report supplies the missing link.

§2 MEASURED, inside the subject at `pale-wash`, that veiling glare from a
defocused silhouette scores as focus: the full focus measure peaked at f136 while
its high-frequency part peaked at f40. The same thing is happening in the collar,
and there it is unopposed.

- The paper sweep near the silhouette has **no texture of its own** in any frame.
  H4 holds: there is no correct answer available from the backdrop's own content.
- But it is not featureless. It carries the **veil**: a smooth luminance ramp cast
  by the defocused subject, whose steepness varies frame to frame as the subject's
  blur circle grows and shrinks.
- A box aggregate of gradient magnitude cannot tell that ramp from texture. It
  ranks frames by veil steepness and returns a **confident, low-noise, spatially
  coherent argmax** at index ~220: the frame in which the subject is most
  defocused and its veil is broadest.
- Far from the silhouette the veil is gone, nothing is left to rank, and the field
  collapses to noise at roughness 17.

**The collar's outer boundary is the handover contour between those two regimes**,
where veil-driven ranking loses to noise-driven ranking. That contour is set by
the local strength of the veil, which is set by the local shape of the silhouette:
lobes project more veil than concavities, and a trichome fringe projects more than
smooth skin. **A handover contour follows silhouette morphology, so it is lobed
and scalloped.**

This is the owner's original argument, vindicated in its class and corrected in
its mechanism. He said straight and scalloped boundaries do not occur in defocus
and must therefore come from the election. Correct. But the boundary is not a
blocky winner field, not a box-window plateau, not a tile grid, and not a
density-driven focus statistic. It is **a region boundary between two election
regimes**, and it is smooth on both sides of itself.

It also explains his own 52x separation without invoking H5 at all.
`coffee-bean`'s silhouette is smooth and convex, so its veil ramp is smooth and
monotone, so the handover contour is a near-circle and the collar is uniform and
invisible: 0.23%. `flower-bud`'s trichome fringe modulates the veil at the scale
of the fringe, so the handover contour is lobed at that scale and the collar reads
as poured liquid: 12.0%.

### 12.5 Why every fix tried so far failed

§10 and §11 tested four focus statistics: `mean`, `max`, `hp`, `hpmax`. All four
failed the ring test (12.47 / 13.89 / 12.44 / 12.26%) while the negative control
never moved and the veiling term never moved, so the arms were neither inert nor
random.

§12.4 says why, and the statement is now general. **All four rank the same set of
frames by the same evidence.** In the collar that evidence is entirely veil. An
order statistic reorders a ranking; it cannot decline to rank. `hp` is the closest
to correct because it removes the low-frequency ramp, but §11.4 MEASURED that at
the flower-bud band no frame resolves the fringe at all (peak gradient flat to
1.32x while brightness climbs 60.5% -> 103.5%), so once the ramp is removed there
is nothing underneath it and `hp` elects noise instead of veil. Noise and veil are
both wrong.

**The fix cannot be a better ranking rule. There is nothing there to rank.** It
has to be an abstention plus a source of an answer from somewhere that does have
one.

### 12.6 The specification, revised

Supersedes §4 and §11.7 for the backdrop collar. §4's high-pass remains correct
for `pale-wash`, which is inside the subject and does have a texture peak to find.

**File:** `crates/strehl-core/src/merge.rs`, in the winner-field stage, after the
per-frame focus responses exist and before the regulariser.

**Invariant.** A pixel may only be elected by argmax if its through-focus response
carries texture evidence. Define, per pixel, `dr = max_k(hp_k) / median_k(hp_k)`
on the **high-passed** focus response, where the high pass is §4's. If
`dr < TAU_ABSTAIN`, the pixel **abstains**: it is excluded from the argmax and
marked in a coverage plane.

**Then fill, do not guess.** Abstaining pixels take their index by nearest-labelled
propagation (a distance-transform fill, or one pass of the existing regulariser
restricted to confident pixels as sources). In the collar the nearest confident
source is the subject, so the collar renders from a frame near index 108, in which
the subject is sharp and its veil is at its narrowest.

**Target numbers, all pre-registered and all already measured on the baseline:**

| quantity | baseline | required |
| --- | --- | --- |
| `flower-bud` ring prominence | 12.47% | **< 1.0%**, toward `coffee-bean`'s 0.23% |
| `coffee-bean` ring prominence | 1.92% at d=155 | unchanged to within 0.2 points |
| backdrop collar median index (`lavendar`, d <= 24) | 212-222 | within 30 frames of the subject's 108 |
| collar roughness (d <= 24) | 1.04 frames | must not rise above ~3 |
| veiling darkening | -36.5% (`flower-bud`), -38.2% (`coffee-bean`) | unchanged to within 1 point |
| subject-region roughness (`lavendar`) | 0.741 frames | must not rise |

**Threshold.** `TAU_ABSTAIN` sits between the measured no-answer and has-answer
populations. MEASURED separations available to calibrate it: bee `blob` 1.34x and
`fringe` 1.17x versus `leg-good` **41.22x** (§10.6); flower-bud band peak gradient
flat to **1.32x** across six frames (§11.4). A value of **1.35x** separates every
measured pair in this report, with the nearest miss at 1.34 and the nearest hold
at 41.22. It must be calibrated per subject against the noise floor, not shipped
as a constant, because the gap is 1.34 to 41.22 on one subject and the low side is
close.

**Guard.** `couch-fibers-cpl` is dense fine structure with no silhouette and is
audited print-worthy. It must abstain on **< 1%** of subject pixels. If abstention
climbs on `couch-fibers`, the threshold is eating texture and the change is wrong.

**Coverage output.** The abstention plane is a product feature, not a debug
artifact. Where the bracket genuinely does not cover a surface, the correct
behaviour is to say so. §9 MEASURED honest coverage gaps at 2 of 3 bee defect ROIs
(texture flat to 1.13x and 1.25x across 299 frames). Those pixels have no answer
and the stacker should report that rather than fabricate one.

### 12.7 The cost

1. **The backdrop stops being independently focused.** Any genuinely resolved
   background at its own depth keeps its own index (it has texture evidence and
   never abstains), but a *weakly* textured background will be pulled toward the
   subject's depth. On a scene with a real, softly-textured backdrop this is a
   regression.
2. **Noise averaging is lost in the fill region.** A propagated index is one
   frame's noise, not an argmax wandering over many. Backdrop noise will rise.
   Unmeasured; see §12.8.
3. **A threshold that can be set wrong.** 1.35x has a 1.34x near-miss in the
   measurements already taken. Set too high it eats real fringe detail, which is
   the exact failure `couch-fibers` guards against.
4. **It does not restore the fringe.** §11.4 MEASURED that no frame in the
   flower-bud bracket resolves the trichomes. Abstention makes the band stop being
   a bright scalloped wash; it cannot make hairs appear that were never captured.
   The remaining honest product answer there is a denser bracket.

### 12.8 What §12 did not verify

- **Not rendered.** §12.6 is specified and its targets are measured on the
  baseline, but no arm implementing abstention has been built or run. Every number
  in the "required" column is a target, not a result. Marked ARGUED.
- The mechanism is measured on `lavendar-cpl` (roughness and index versus
  distance) and linked to `flower-bud` through §2, §11.4 and the owner's 52x
  separation. **The collar profile has not been repeated on `flower-bud` or
  `coffee-bean` directly**, because no index dump exists for them; it would need
  two renders with `--index-map`. That is the first thing I would do next.
- The subject segmentation is a local-contrast threshold at p70, tuned by eye
  against the picture. The 20.4x subject-versus-backdrop roughness ratio is large
  enough that the exact threshold cannot plausibly reverse it, but it was not
  swept.
- The 1.00% of excursion pixels that are on the subject and organised at 143x the
  null were not characterised. They are not the dominant defect, but they are real.
- Whether the regulariser straddle the owner proposed (radius 8 averaging across a
  large jump, landing at a frame where neither depth is in focus) occurs anywhere
  that matters. On the subject the field is smooth to 0.741 frames per step, so
  there is almost nothing to straddle there; in the backdrop it certainly happens,
  but the backdrop is featureless so the consequence is small. Not tested directly.

Pictures, in the order to look at them:

- `pics/SEAM-where.png` (panel 3 is the finding: the coherent lobed collar)
- `pics/SEAM-collar.png` (panel 3, and the monotonic roughness ramp)
- `pics/SEAM-shape.png` (the instrument that was wrong, and the picture that caught it)
## 13. Re-baselined onto BUILD-BLEND's multi-band merge

The owner stopped this lane mid-investigation: BUILD-BLEND landed a Laplacian
multi-band merge (`d4b8644`, `8585ee3`, `eb072d5`), it is going in as the default,
and optimising the election on the path being replaced is discarded work. The
instruction was to run the pre-registered acceptance test against the **blend**
arm and report the residual honestly, including "there is not one".

All measurements below are on linear 16-bit TIFFs from `C:\dev\strehl-out\BUILD-BLEND\bm\`.
No JPEG, no `--srgb`. Absolute DN is reported alongside every ratio.

### 13.1 The ring: the pre-registered target is met

One subject mask, computed once from the pinned gallery arm and borrowed by all
three, so that the coordinate origin cannot move when the artifact that draws it
is removed. MEASURED:

| arm | far field | veiling darkening at 0-2 px | ring |
| --- | --- | --- | --- |
| pin `1cacb61` (`accept/fb-mean.tiff`, the gallery baseline) | 19032 DN | -7684 DN = -40.4% | d=21 px, +2374 DN = **12.47%** |
| `bm/flower-bud-alone-cpl-ctrl.tif` | 62170 DN | -12034 DN = -19.4% | d=21 px, +3528 DN = **5.68%** |
| `bm/flower-bud-alone-cpl-blend.tif` | 61640 DN | -9649 DN = -15.7% | d=245 px, +231 DN = **0.37%** |

**Pre-registered bar: 12.0% -> <= 1%. The blend arm reads 0.37%.**

Read the rows, not the verdict. The control's profile turns over: it falls to
-39% at the silhouette, rises to a local maximum at d=21-37 px, falls back to a
trough at d=135 px, then climbs to the far field. That double turnover is the
ring sitting inside the veil. The blend arm's profile **does not turn over at
all** between d=1 and d=205: it rises monotonically from -37.55% to -0.00%. The
d=21 px ring is not reduced, it is **absent**. Its only remaining interior peak is
+231 DN at d=245 px, which is far-field wobble of the same character and
magnitude as `coffee-bean`'s clean 0.23% at d=450 px.

**Attribution, which is not what the side-by-sides say.** The control arm is not
the gallery baseline. On the common mask it already reads **5.68%** against the
pinned binary's **12.47%**, so something that landed between `1cacb61` and
BUILD-BLEND's control build - most plausibly BUILD-HALO's veiling work - had
already removed a bit over half the ring in relative terms before the blend ran.
The honest statement is **5.68% -> 0.37% is the blend**, and 12.47% -> 5.68% is
somebody else's. The blend's step is the larger and the decisive one, but it is
not 12.47% -> 0.37%.

A caveat against the DN column, in the spirit of tonight's rule. The pin and
BUILD-BLEND's build use different output scaling: far field 19032 DN against
62170 DN, a factor of 3.27. Absolute DN is therefore **not** comparable across
those two rows and the ratio is the safer statistic for that one comparison.
Within the ctrl-to-blend pair, which shares a binary and agrees on far field to
0.85%, DN is directly comparable and the ring falls **+3528 DN -> +231 DN**.

### 13.2 The negative control holds, at the distance that matters

`coffee-bean` is the free placebo: no ring to remove, so any arm that gives it one
is doing something other than what it claims. MEASURED, mask borrowed from the
pinned control:

| arm | darkening | peaks within 40 px of the silhouette | headline peak |
| --- | --- | --- | --- |
| pin `cb-shipped.tiff` | -39.4% | 0.02% at d=9, 0.21% at d=25 | 1.92% at d=155 |
| `flip/coffee-bean--pyramid.tiff` | -37.5% | 0.33% at d=37 | 1.44% at d=312 |
| `flip/coffee-bean--estimator.tiff` | -39.6% | 0.01% at d=9, 0.19% at d=25 | 2.68% at d=165 |

**At the distance where `flower-bud`'s ring lives (d <= 40 px) every arm is quiet,
at or below 0.33%.** No arm manufactures a near-silhouette ring on a smooth
convex subject. The larger far-field peaks at d=155-512 px are present in the
**pinned baseline too**, they move between arms, and section 11 already recorded
why they are untrustworthy: this mask covers 59.55% of the frame in 1994
components, so "distance from the silhouette" is poorly defined at large d.

**Incomplete, and I asked rather than guessed.** There is no `coffee-bean` control
from BUILD-BLEND's own binary on disk, so the rows above compare **across
binaries**, which section 13.1 has just shown is not a small effect. I have asked
BUILD-BLEND for a blend-off render from the same binary and for the semantics of
`--pyramid` versus `--estimator`; the filenames do not say and I did not assume.
The two differ substantially from each other (1.44% against 2.68%, darkening
-37.5% against -39.6%), so they are two blend variants rather than an arm and its
control, and `pyramid` is the better behaved of the two.

### 13.3 My assignment, looked at: the patches are gone

The ring is a scalar. My actual commission was the hard-edged wrong-depth patches,
and those have to be judged by eye.

`pics/BLEND-interior.png` shows the four largest **local gradient decreases**
inside `flower-bud`'s subject, eroded 60 px clear of the silhouette so the collar
cannot contribute. These are selected as the places where the blend loses the most
edge energy: the **least favourable** places to judge it, chosen adversarially.

In all four, the control holds the artifact. Column 3 is the textbook case: a
flat, white, hard-edged scalloped plateau with a razor boundary cutting straight
across plant material. Column 1 has a vertical hard boundary against a flat grey
plateau; column 4 has flat white lobes with hard edges; column 2 is a broad pale
wash. **In all four the blend holds plant** - dark tissue with resolved hairs and
trichomes and no seam anywhere.

`pics/BLEND-fb.png` shows the same thing at full frame and at 1:1: the control is
a cut-out sticker on a blotchy grey backdrop, the blend is a clean natural
silhouette on an even sweep.

**The defect this lane was commissioned to fix is not present in the blend arm.**

### 13.4 An estimator of mine that failed, and the control that caught it

The first do-no-harm pass reported **-19.1%** gradient energy on `flower-bud` and
**-23.1%** in the deep subject interior, and printed `REAL SOFTENING`. That was
wrong twice over, and both faults are mine.

**Fault one: selection bias.** The pixels were the top decile of the **control's
own** gradient. Selecting on one arm's extremes and then comparing arms is
regression to the mean: any change at all, including a pure denoise, lowers the
other arm in that set. `biascheck.py` runs the selection **both ways round**.
MEASURED:

| subject | select on ctrl | select on blend | symmetric | unselected |
| --- | --- | --- | --- | --- |
| `flower-bud` | -23.05% | **+5.00%** | -14.76% | -16.05% |
| `lavendar` | -10.17% | **+4.60%** | -3.97% | +0.17% |
| `couch-fibers` | -2.71% | **+8.37%** | +2.31% | +2.31% |

**The sign flips on all three.** The forward number was an artifact of selection.
This is the same shape as the +0.845 sigma upper-envelope bias that impeached a
headline number elsewhere on this project tonight, and it is worth stating as a
rule: *an A/B on a selected subset must be run with the selection taken from each
arm in turn, and a sign that does not survive reversal is not a finding.*

**Fault two: the metric was measuring brightness.** Gradient magnitude in DN
scales with level. At the four crops in section 13.3 the level collapses because a
spurious bright wash is being removed: **20710 DN -> 1417 DN** at one, **17009 DN
-> 3952 DN** at another. A region 14.6x darker cannot carry the same absolute edge
energy however sharp it is. The picture and the number disagreed, and the picture
was right.

### 13.5 The cost, stated with its uncertainty

Switching to level-invariant local Weber contrast (`|grad|` over the local mean
level) removes fault two. MEASURED on the deep interior:

| subject | select on ctrl | select on blend | symmetric | unselected | reversal |
| --- | --- | --- | --- | --- | --- |
| `flower-bud` | -33.35% | +75.75% | **+20.93%** | **-7.20%** | sign flips |
| `lavendar` | -32.00% | -12.00% | **-24.97%** | **-12.39%** | **sign survives** |
| `couch-fibers` | -8.38% | +1.15% | **-4.07%** | **-1.51%** | sign flips |

I am not going to pick the flattering number. What this table honestly supports:

- **`couch-fibers`, the do-no-harm subject, passes.** Absolute gradient +2.31% by
  two independent unbiased estimators that agree exactly; Weber contrast -1.5% to
  -4.1% with a sign that does not survive reversal. Dense fine structure is not
  wrecked. This was the guard that mattered most and it holds.
- **`lavendar` shows a real contrast reduction**, -12.4% to -25.0%, and it is the
  one number here that **survives its reversal control**. That is a genuine cost
  of band blending and it should be treated as one.
- **`flower-bud` is unmeasurable by this instrument.** Its estimators disagree in
  sign (+20.93% against -7.20%) because its deep interior contains both the
  artifact being removed and the plant being preserved, and no aggregate over that
  mixture means anything. The pictures in section 13.3 are the evidence for
  `flower-bud`, not this row.

Absolute levels, which no ratio shows (`flower-bud`, same binary):

| region | ctrl | blend | delta |
| --- | --- | --- | --- |
| deep interior | 13137 DN | 13723 DN | **+586 DN = +4.46%** |
| collar 0-40 px | 54225 DN | 59384 DN | **+5159 DN = +9.51%** |
| far backdrop > 400 px | 61964 DN | 61431 DN | **-533 DN = -0.86%** |

Two of those are worth another lane's attention. The blend **reaches into the
veiling term**: darkening -12034 DN -> -9649 DN, that is -19.4% -> -15.7%, on the
same binary. That quantity is BUILD-HALO's and is specified. And the blend
**darkens the whole far background by -533 DN**, which is small, barely moves any
ratio, and is exactly the kind of additive shift that is invisible in both an
error and a ratio.

### 13.6 Does this lane still have a defect to fix? No, with one thing surviving

**No.** The hard-edged wrong-depth patches are absent from the blend arm at 1:1 on
linear data at the four worst places I could find, and the ring is at 0.37%
against a pre-registered bar of 1%. Close the lane.

Section 12's mechanism explains why the cure worked, and it was written before
this test: the election's error in the collar is a **low-frequency** error - it
ranks veil steepness, which is a smooth ramp - committed by a **hard per-pixel
selection**. A Laplacian decomposition stops selecting the low bands per pixel and
starts blending them, which removes the mechanism rather than trimming its output.
That is why the ring nulls to 0.37% instead of merely shrinking.

**What survives, and it is not an artifact fix.** Section 11.4 MEASURED that **no
frame in `flower-bud`'s 205-frame bracket resolves the trichome fringe at all**:
peak gradient flat to 1.32x across the bracket while brightness climbs
monotonically 60.5% -> 103.5%. Section 9 MEASURED honest coverage gaps at 2 of 3
bee ROIs, texture flat to 1.13x and 1.25x across 299 frames. Where the data has no
answer, a blend produces something smooth and plausible instead of something
scalloped and wrong. That is a large improvement and not a recovery.

**"The artifact is gone" and "the detail is there" are different claims, and only
the first is supported.** The recommendation that survives this re-baseline is
therefore not a merge change at all: it is the **coverage output** from section
12.6 - an abstention plane that records where the bracket had no answer, so a
plausible reconstruction is never mistaken for a resolved one. That is cheap, it
is orthogonal to the merge path, and it is the honest half of section 12's
specification.

### 13.7 What section 13 did not verify

- **The `coffee-bean` negative control is cross-binary.** No same-binary control
  exists on disk; requested from BUILD-BLEND, not yet received. The near-field
  conclusion (<= 0.33% within 40 px in all arms) is robust to this because it
  holds in every arm including the baseline, but the far-field rows are not.
- **`lavendar`'s -12% to -25% contrast reduction was not looked at**, only
  measured. It survives its reversal control, which is more than any other cost
  number here, and it deserves the same 1:1 adversarial crops that section 13.3
  gave `flower-bud`. I ran out of lane before doing it.
- No claim is made about `bee-1-cpl` under the blend; not rendered.
- The section 12.6 abstention specification remains **unimplemented and
  unrendered**. Every target in it is still a target.
- The attribution split in 13.1 identifies BUILD-HALO's veiling work as the most
  plausible cause of 12.47% -> 5.68% by elimination and timing, not by bisection.
  It is ARGUED. Bisecting it would need a render per candidate SHA.

Pictures, in the order to look at them:

- `pics/BLEND-interior.png` - the four adversarially chosen crops; the control
  holds hard-edged plateaus, the blend holds plant
- `pics/BLEND-fb.png` - full frame and 1:1, cut-out sticker against clean silhouette
- `pics/BLEND-lavendar.png`
- `pics/BLEND-residual.png`
## 14. Section 13 measured on a tone curve. Corrected here.

An independent verifier was run against section 13 and found a defect that
invalidates three of its numbers. The defect is mine, it is the one this report
warns against in its own preamble, and I am recording it in full rather than
quietly restating the table.

### 14.1 The retraction

Section 13 states: *"All measurements below are on linear 16-bit TIFFs from
`C:\dev\strehl-out\BUILD-BLEND\bm\`. No JPEG, no `--srgb`."* **That is false.**
MEASURED, from the render logs beside the files:

| file | binary | colour | tone |
| --- | --- | --- | --- |
| `bm/flower-bud-alone-cpl-ctrl.tif` | `strehl.exe` | camera RGB -> **sRGB** | black 0.00985, white 0.35458 |
| `bm/flower-bud-alone-cpl-blend.tif` | **`blend-render.exe`** | camera RGB -> **sRGB** | black **0.00000**, white **0.36676** |

So section 13's control arm carries an sRGB transfer curve, and the two arms come
from **different executables with different black and white points**. Every DN
comparison in 13.4 and 13.5 crosses that difference. The project's standing rule
is that the display curve amplifies edge artifacts several-fold and that nothing
may be measured on an `--srgb` render; I wrote that rule into this report and then
broke it.

Worse, **a compliant pair was already on disk and I had read the directory.**
`flip/flower-bud-alone-cpl--estimator.tiff` and `--pyramid.tiff` are **one binary,
both arms linear**, differing only in the merge. Their logs say so in the first
line: `estimator` is *"regularised winner + noise-gated average (THE DEFAULT PATH,
an estimator)"* and `pyramid` is *"LAPLACIAN MULTI-BAND MERGE"*. Section 13.2
inferred from the filenames that these were "two blend variants rather than an arm
and its control". **They are exactly an arm and its control.** Section 13.7's first
bullet, *"No same-binary control exists on disk"*, is therefore not incomplete but
**false**, which is the failure mode that section named as the most serious
available to it.

The lesson is narrow and worth keeping: **a render's provenance lives in its log,
not in its filename.** I inferred from names in a directory whose logs state the
answer in their first line.

### 14.2 The corrected headline

Re-run on the compliant pair: one binary, both arms linear, one subject mask
borrowed from the control so the coordinate origin cannot move. MEASURED:

| arm | far field | darkening at 0-2 px | interior peaks (d px, prominence) |
| --- | --- | --- | --- |
| `flip/...--estimator` (control) | 19163 DN | -7731 DN = **-40.3%** | **(21, 12.65%)**, (87, 0.31%), (105, 0.10%) |
| `flip/...--pyramid` (blend) | 19050 DN | -6630 DN = **-34.8%** | (275, 1.24%), (295, 1.22%) |

The control's profile turns over twice, which is the ring sitting inside the veil:
-40.35% at d=1, up to **-13.12% at d=21**, back down to -25.59% at d=95, then up to
the far field. The blend's profile is **monotonic from d=1 to d=275**: -34.81%,
-22.98%, -13.83%, -8.24%, -6.57%, -5.36%, -4.99%, -4.48%, -4.07%, -3.52%, -2.98%,
-2.12%, -1.55%, -0.62%, -0.09%, +0.32%, +0.58%, +0.59%. **It has no interior local
maximum anywhere inside d=275 px.**

**The pre-registered bar was 12.0% -> <= 1%. On the correct instrument the control
reads 12.65% and the blend has no near-field ring at all.** The remaining 1.24% at
d=275 px is far-field wobble; the control carries far-field structure too.

The number **0.37%** from section 13.1 is withdrawn. It was a property of the sRGB
curve compressing a bright ring against a compressed far field.

### 14.3 The attribution was wrong, and wrong against BUILD-BLEND

Section 13.1 claimed the control arm was not the gallery baseline, that it "already
reads 5.68% against the pinned binary's 12.47%", and that something landing before
the blend "had already removed a bit over half the ring". **Refuted.**

On one binary with both arms linear, the control - which is the **default ship
path** - reads **12.65%**, against the pinned gallery baseline's **12.47%**. Those
agree to 0.18 points. **Nothing removed half the ring before the blend. The whole
of it is the blend.** The 12.47 -> 5.68 step I reported was the tone curve, and I
under-credited another lane by inventing a step that does not exist.

The same correction applies to section 13.1's DN caveat. It said the pin and
BUILD-BLEND's build "use different output scaling ... a factor of 3.27". They do
not: rendered linear, BUILD-BLEND's build gives **19163 DN** far field against the
pin's **19033 DN**, 0.7% apart. The 3.27x was the tone curve on one arm.

What survives, and is now cleaner because it is same-binary and linear: **the blend
moves the veiling term**, darkening **-40.3% -> -34.8%**, a 5.5-point change in a
quantity that belongs to BUILD-HALO and is specified. That should be routed.

### 14.4 The negative control IS moved, and this is the one finding against the blend

`coffee-bean` is the pre-registered placebo: it has no ring, so an arm that moves
its profile is doing something other than what it claims. On the same-binary
linear pair, mask borrowed from the control. MEASURED, interior peaks:

| arm | darkening | peaks at d <= 40 px | peaks at d = 41-100 px | headline |
| --- | --- | --- | --- | --- |
| `--estimator` (control) | -39.3% | 0.38% at d=25 | 0.17% at d=55, **0.07% at d=93** | 2.46% at d=165 |
| `--pyramid` (blend) | -37.2% | none | 0.61% at 51, 0.57% at 81, 0.72% at 89, **1.17% at d=93** | 1.63% at d=312 |

**At the distance where `flower-bud`'s ring lives (d <= 40 px) the placebo holds:
the blend introduces nothing.** But in the **47-93 px band the blend introduces
structure the control does not have**, rising to **1.17% against 0.07% at the same
distance, a factor of 16.7**. By the letter of the pre-registered rule, that is the
blend doing something other than what it claims, and it is the only measurement in
sections 13 or 14 that runs against it.

Two honest qualifications, neither of which disposes of it. This mask covers
**59.62% of the frame in 2115 components**, so distance from the silhouette is
poorly defined here and section 11 already recorded that. And the blend also moves
`coffee-bean`'s darkening, -39.3% -> -37.2%, consistent with 14.3. It should be
looked at rather than argued about, and I did not look at it.

### 14.5 What else section 13 got wrong

- **The deep-interior level change reverses sign on a compliant instrument.**
  Section 13.5 reports `flower-bud`'s deep interior at 13137 -> 13723 DN, **+4.46%**.
  The verifier measured 1649 -> 1454 DN, **-11.83%**, on the linear pair. The two
  `bm` arms differ in black point by 0.00985 of full scale = **645 linear DN**,
  against a deep interior sitting at 1649 DN: the black-point mismatch alone is 39%
  of the signal. **The +4.46% is not attributable to the merge.** This is exactly
  the additive bias the owner made a hard requirement tonight, manufactured by my
  render pair instead of caught by it. Withdrawn.
- **Section 13.1 mixes two masks in one paragraph.** The table uses the pin's mask;
  the prose beneath it ("-39% at the silhouette ... trough at d=135 px") comes from
  a run using the control arm's own mask. Both were MEASURED, presented as one
  profile. On the pin mask those rows read -19.36%, ring at d=21, trough at d=105.
- **Sections 13.4 and 13.5 stand as arithmetic and fall as physics.** The verifier
  independently reproduced the selection-bias reversal on all three subjects
  (`flower-bud` -25.43% forward against +8.31% reverse; `couch-fibers` unselected
  +2.31%, reproducing to the digit), so 13.4's self-correction is sound. But those
  numbers were computed across the sRGB, two-executable, two-black-point pair, so
  the **magnitudes** are not trustworthy. The `lavendar` cost survives in sign and
  rough size on independent re-derivation (-10.0% and -10.1% by two unbiased
  estimators) but its adjudication as *"the one number whose sign survives its
  reversal control"* does **not** reproduce: the verifier's reverse estimate is
  +1.5%, indistinguishable from zero. Treat `lavendar`'s contrast loss as real and
  around -10%, and treat its reversal survival as withdrawn.
- `couch-fibers` **is not damaged** on either instrument. That guard holds.

### 14.6 The conclusion does not change

**Close the lane.** Every correction above touches a number and none touches the
finding:

- The commissioned defect is gone on the **correct** instrument, and by a wider
  margin than section 13 claimed: **no interior local maximum at all** inside
  d=275 px, against a control with 12.65% at d=21.
- The verifier looked for somewhere the blend is visibly worse, choosing crops by
  its own criterion and level-matching to +/-15% so that "a bright wash was removed"
  could not explain the result, on both `flower-bud` and `lavendar`. **It found
  none.** At every site the control holds a hard-edged plateau and the blend holds
  plant, and it reproduced this on the linear pair as well, so section 13.3's
  picture claim does not depend on the tone curve.
- Section 12's mechanism is untouched: it was measured on a winner-field dump, not
  on these renders.

The open item handed back is 14.4, the placebo motion at 47-93 px on `coffee-bean`,
which is small, real, and unexamined by eye.

### 14.7 What section 14 did not verify

- **`lavendar` and `couch-fibers` were never re-measured on linear data.** Their
  cost numbers in 13.4 and 13.5 remain computed through the sRGB, two-binary pair.
  Sign and rough magnitude were independently reproduced; the magnitudes should not
  be cited until re-run on `flip/`.
- **14.4 was not looked at.** It is a profile, not a picture, which is the failure
  this report has committed twice.
- `flower-bud`'s Weber row is unmeasurable by that instrument on either render pair
  and stays that way.
- No `bee-1-cpl` render under the blend. The 12.6 abstention plane is still
  unimplemented and unrendered.
- The verifier's own numbers are its own; where 14.5 cites them they are marked as
  its measurements, not mine. I re-derived 14.2, 14.3 and 14.4 myself.
## 15. I tried to reverse 14.4 and got half of it. What the placebo motion is.

Section 14.4 reported that the blend moves `coffee-bean`, the pre-registered
placebo, and called it *"the one finding against the blend"*.  I then looked at
it as a picture -- which 14.7 admitted I had never done -- and talked myself into
withdrawing it.  Because the reversal ran in another lane's favour and I had
already under-credited that lane once in 13.1, I sent it to an independent
verifier before believing it, under the rule that an agent does not verify its
own work.

**The reversal is half right.**  The half that is right is right; the half that
is wrong was an exculpation that moved the violation rather than removing it,
and it rested on a statistic inflated three separate ways.  14.4 needs
**rewording, not withdrawal**.

### 15.1 Provenance, checked first this time

MEASURED, from `flip-render.ps1` and both render logs:

- one binary for both arms, `flip-render.ps1` line 15,
  `$BIN = "...\target-flip\release\strehl.exe"`;
- **no `--srgb` in either arm**; both logs `levels : black 512, white 15360`;
- both TIFFs carry `ImageDescription = "Linear camera-native RGB (sensor
  primaries), NO colour matrix, no transfer curve."`;
- the estimator finished writing at 03:10:19 and the pyramid started the same
  second, so no rebuild could intervene.

So 15 and 14 do not repeat 13's failure.  Two caveats survive and both are new:

**The binary cannot be hash-verified.** `strehl.exe` has mtime 04:55:56, after
every render in `flip/` (03:05-03:37).  Provenance rests on the logs and the
timing chain, not on a hash.

**The `flip/` A/B is not merge-only, and its harness says otherwise.**
`flip-render.ps1` states the arms *"differ in the merge and nothing else"*.  The
pyramid's own log contradicts it:

```
not applied : photometric gain, clip census, outlier rejection, halo correction,
              through-focus statistics
```

and the estimator additionally receives `--gate 2.0`, which the pyramid path
refuses.  **This is merge-only pipeline against full estimator pipeline, five
stages apart.**  Every difference in 14 and 15 is attributable to the merge
*plus* five disabled stages, and neither section can separate them.  That is a
limit on the instrument, not a defect in the blend.

### 15.2 What was right

**The stripe is not real scene content.  REFUTED, and this is the strongest
result in the section.** At all four inspected sites the control shows a thin
bright line hugging the bean silhouette followed by a darker gap; the blend
shows a monotone ramp; and **none of four source frames** (00016, 00046, 00076
which is sharp at these sites, 00106) shows any bright band -- every one ramps
monotonically from dark bean to bright paper.  It is not a paper seam, a shadow
or a specular gradient.  So the control's extra contrast there really is
invented, and the same is true on the subject: at three of six ground-truthed
`flower-bud` sites the control carries a hard-edged contour-banded plateau that
**no source frame has**, and the blend renders those places as continuous plant.

**The brightening is local, not a calibration difference.  CONFIRMED.** An affine
null fitted on the interior and far field alone gives `blend = 1.02255*ctl -
359.1 DN`.  There is a real global component -- **+2.3% gain and a -359 DN
offset, which is invisible in any ratio and is reported here in DN because of
that** -- but its residuals are interior +0.0, collar -175.0, **band +5044.6**,
near backdrop +2968.1, mid +382.2, far +0.0.  The affine part explains about 11%
of the band motion.  The rest is local.

### 15.3 What was wrong: the number was inflated three ways

I reported the band losing **30.05%** of local Weber contrast against 4.85% in
the deep interior, a 6x localisation, and read that as the artifact being
removed.  Each of the three following corrections is independently reproducible
with `python placebo.py` on the `flip/` pair; I re-implemented them myself rather
than copy the verifier's numbers, and land within about a point of it at every
step.

| statistic on the 47-93 band | change | what it still contains |
| --- | ---: | --- |
| naive Weber, as published in 14 | **-30.05%** | rising mean, veil ramp, clipping |
| direct mean local sd, in DN | -31.70% | veil ramp, clipping |
| saturation-excluded | -21.18% | veil ramp |
| **ramp-detrended and saturation-excluded** | **-11.24%** | structure |

against a deep interior that moves **-8.18%** on the same clean statistic.
**The 6x localisation is really 1.37x.**  My own 14.7 suspicion that a 9 px
window on a veiled backdrop measures the veil gradient rather than texture was
correct and accounts for roughly ten of the thirty points.

**An arithmetic error of mine, worth naming because it is a trap.** I converted
Weber back to absolute DN as `mean(sd/mean) x mean(mean)` and reported the band
as 1021 -> 805 DN.  `mean(sd/mean) x mean(mean)` is not `mean(sd)`.  Measured
directly on the same population it is **973.0 -> 664.6 DN**.  My levels were
5-14% wrong and my change was 10 points wrong -- **in the conservative
direction**, so it understated my own case rather than flattering it, which is
the only reason it did not become a fourth published error.

**And the thing I missed entirely: a fifth of the band is clipped.**
MEASURED, pixels with any channel `== 65535`:

| zone | n px | estimator | pyramid | ratio |
| --- | ---: | ---: | ---: | ---: |
| deep interior (d <= -60) | 13013252 | 0.0000% | 0.0000% | - |
| interior collar (-30..-5) | 2842602 | 0.0000% | 0.0000% | - |
| **the 14.4 band (47..93)** | 575576 | **0.0952%** | **20.4824%** | **215x** |
| near backdrop (1..20) | 549645 | 0.0619% | 1.6263% | 26.3x |
| mid backdrop (120..250) | 1522130 | 7.8767% | 20.7315% | 2.6x |
| far field (300..600) | 2795748 | 8.6106% | 14.6171% | 1.7x |

Frame-wide **1.8673% -> 4.6508%**.  In the band the blend's **p90 is 65522.0 and
p95 upward is pinned flat at 65535.0**, against a control p95 of 58387.7.  The
pyramid log's `not applied : ... clip census ...` names a probable cause.  I
argued for two sections about the contrast of a region a fifth of which has no
headroom left, and never counted it.

### 15.4 Why the reversal fails as an exculpation

I wrote that the placebo motion is "(a) the veil being reduced and (b) the
artifact being removed".  (b) survives 15.2.  **(a) is not a defence.**  The
owner's constraint is that the veiling darkening belongs to BUILD-HALO and must
not be moved.  MEASURED on the same-binary linear pair:

| subject | darkening at the silhouette, control -> blend |
| --- | --- |
| `coffee-bean` | -39.3% -> -37.2% (2.1 points) |
| `flower-bud-alone-cpl` | -40.3% -> -34.8% (5.5 points, 1101 DN) |

*"The blend moved the placebo because it reduced the veil"* relocates the
violation from the placebo rule to the veil rule.  It does not clear it.  ARGUED,
on MEASURED numbers, and it is the reason 14.4 keeps its finding.

### 15.5 Ground truth, from the source frames themselves

The strongest instrument in this section is not a merge comparison at all.  All
105 `coffee-bean` source frames were profiled, each using its own mask and its
own far field, so no registration is needed; validated against the borrowed-mask
run at -30.84% versus -30.88%.  MEASURED:

| zone | frame min | frame max | frame mean | control | blend |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1..20 | -35.18% | -27.08% | -31.59% | **-30.88%** | -25.57% |
| 21..46 | -26.78% | -15.52% | -20.23% | **-20.60%** | -13.39% |
| 47..93 | -16.36% | -11.94% | -13.55% | -18.19% | -9.26% |
| 120..250 | -7.03% | -5.70% | -6.40% | -4.35% | **-3.80%** |

**The control's near-backdrop level sits inside the 105-frame envelope at
d=1..46.  The blend's sits outside it at every distance measured, always too
bright.**

The counter-reading, which must be given: a merge that genuinely removed defocus
bleed *should* be brighter than every frame at small d, so "outside the
envelope" near the silhouette is not automatically wrong.  The discriminator is
focus-dependence.  At d=1..20 the deficit swings 8 points across the bracket and
is V-shaped with a plateau near -27.1% over frames 60-76 -- that is bleed, and it
is removable.  At **d=120..250 it is nearly focus-invariant, -5.70 to -7.03, a
1.3-point spread.  That is real shadow and cannot be bled away.**  There truth is
about -6.4%, the control is 2.05 points too bright and the blend is **2.60 points
too bright**.  On the one zone where ground truth is unambiguous, **both arms
wash out about a third of a real shadow and the blend is the worse of the two.**

### 15.6 One site where the blend genuinely over-smooths

Found from a **random** null, not selected on the arm difference, so it is not a
circular pick.  `flower-bud-alone-cpl` at (y=3728, x=4252), sigma=1 local
modulation in DN:

| | control | blend | sharpest source frame | bracket min/max |
| --- | ---: | ---: | ---: | --- |
| (3728,4252) | 28.11 | **5.84** | 13.12 | 7.84 / 13.12 |

**The blend is below the minimum over all 26 sampled frames**, while frame 00065
shows real mottled surface texture there, and the mean level drops 1839 -> 1050
DN.  Both arms are wrong at that site in opposite directions: the control invents
a banded plateau, the blend erases the texture.  At the other five ground-truthed
sites the blend was equal to or closer to truth than the control.

`couch-fibers-cpl` remains undamaged and this is now a second independent
failure to find damage there.  Unselected, absolute DN, subject interior:
sigma=1 **87.93 -> 96.26 (+9.48%)**, sigma=2 +4.64%, sigma=4 +2.40%, sigma=8
+2.12%; whole frame and backdrop all positive.  Selecting on the control gives
-3.97% *relative* but **+2.99% in absolute DN**, the apparent loss being entirely
the interior mean rising 5868 -> 6106 DN -- the same level trap as 13.5.
Reversed selection +4.59% DN, random null +8.48% DN.

### 15.7 Three defects in my own instruments, and they are fixed

All three were found by the verifier, all three are in code this report has been
citing, and all three are now corrected in
`experiments/BUILD-ELECT/src/`:

- **`annulus.py` measured spatial concentration on a 128 px smoothed field**,
  which destroys concentration by construction, so it could only ever report
  "diffuse".  Recomputed on the raw per-pixel difference the answer holds --
  top 1% carry 2.68% and top 25% carry 56.29%, against a uniform 1% and 25% --
  but **the published evidence for a correct conclusion was circular.**
- **The four crop sites in 14's pictures do not lie in the band they
  illustrate.**  Their signed distances are 21.0, 115.4, 24.7 and 23.9 px; the
  band is 47-93.  They were also chosen as the argmax of the difference they
  then report.  Both scripts now print each site's signed distance and label the
  selection circular in its own output.
- **`ringprofile.signed_distance` padded the wrong transform.**  `d_out` was
  padded, where padding adds no zeros and is a no-op; `d_in` was not, and it is
  the one that saturates -- on a border-touching blob a corner whose true
  distance is 1 came back as **12**.  Fixed, and the deep-interior population
  moved 13178401 -> 13013252 px as a result, so the bug was live.

And one correction to a caveat I published **against my own number**:
`subject_mask` keeps only the largest connected component, but returned and
printed the count *before* that reduction.  So 14.4's *"59.62% of the frame in
2115 connected components, so distance is an average over many unrelated
silhouettes"* is **false**: the returned mask has **one** component.  Distance on
`coffee-bean` is still awkward -- one blob covering 59.62% of the frame with a
convoluted boundary -- but the stated reason was wrong, and it was the reason I
used to discount my own finding.  Both the function and its callers now print
`kept of found`.

### 15.8 14.4, reworded

The sentence *"the blend introduces profile structure the control does not
have"* is not what the data say.  The blend's peaks at 0.61 / 0.57 / 0.72 /
1.17% are bin-to-bin wiggles riding a **9.35% monotone rise** across the band,
and the wiggle is a symptom of the 20.48% clipping, not new structure.  The
honest statement:

> **The placebo is moved, in absolute DN, in every zone.**  The motion is local,
> not a calibration difference: +5696 DN in the 47-93 px band against +872 DN in
> the far field, 6.53x, with only about 11% of it affine.  It is made of three
> things -- the veil being reduced by 2.1 points, which is out of lane; a real
> invented-contrast removal, worth about 11% of detrended local sd against 8% in
> the interior, so barely localised; and **a 215x increase in clipped pixels,
> reaching 20.48% of the band**.  The radial profile is about 17x noisier
> bin-to-bin in this band as a result.

### 15.9 The conclusion still does not change, and what to route

**Close the lane.**  The commissioned defect is gone and 15.2 shows it was
invented rather than removed: the silhouette-hugging ring goes from 12.65%
prominence at d=21 px to no interior peak below d=275, the polygonal plateaus
exist in no source frame, and `couch-fibers` is undamaged under two independent
attempts to damage it.

Three things leave this lane pointing elsewhere, none of them mine to fix:

1. **The pyramid arm clips.** 20.48% of the near-backdrop band at the container
   ceiling, `clip census` disabled in that path.  Sent to BUILD-BLEND ahead of
   it becoming the default.  This is the one I would not ship without looking at.
2. **The blend moves the veiling darkening**, 5.5 points on `flower-bud` and 2.1
   on `coffee-bean`.  BUILD-HALO's term.
3. **Both arms wash out about a third of a real, focus-invariant shadow** at
   d=120..250, and the blend is the worse of the two.  That is a new defect
   belonging to neither the election nor the blend specifically, and nobody owns
   it.

One adjudication for the owner rather than for me: the blend's largest surviving
interior peak on `flower-bud` is **1.24% at d=275 px**.  Read as *"the ring at
~21 px must fall below 1%"* it passes outright; read as *"no interior peak above
1%"* it sits just the wrong side of the pre-registered line.  The two readings
differ and the number is close enough that the choice matters.

### 15.10 What section 15 did not verify

- **The five disabled stages cannot be separated from the merge** on the `flip/`
  pair, so no number in 14 or 15 is attributable to the multi-band merge alone.
- **The producing binary is not hash-verified.**
- **Whether "brighter than every source frame" at small d is an error or correct
  bleed-free behaviour is unsettled.**  The envelope is MEASURED; the bleed
  reading is ARGUED.  Only d=120..250 is a clean discriminator and both arms
  fail it.
- Six sites on `flower-bud` and four on `coffee-bean` were ground-truthed
  against source frames; none on `couch-fibers`.  The zone statistics are
  whole-frame and unselected, but the picture-level truth check is a small
  sample.
- The source frames were decoded rawpy AHD at `half_size` while both merged arms
  are Malvar-He-Cutler, which inflates merged fine-scale numbers relative to the
  frames.  The bias runs *against* 15.6's finding, so "blend below the bracket
  minimum" is conservative; "control above every frame" is partly instrument.
- **No regression test covers any of this** -- not the placebo profile, not the
  clip census, not the veil darkening.  Every number in 14 and 15 is a one-off
  measurement by hand and nothing will catch a re-break.
- `lavendar` and `couch-fibers` still have no ring measurement on linear data,
  as 14.7 said.
- The 12.6 abstention plane is still unimplemented and unrendered.

---

## 16. I orphaned the shadow-washout finding. I own it now, and I am withdrawing it.

The owner assigned me a finding I had reported outside my brief: that both merge
arms wash out about a third of a real shadow on `coffee-bean` at d=120..250, and
that the deficit is **focus-invariant**, which is what ruled out the obvious
explanation that it is a focus-selection artifact.

**It does not survive, and neither did my first attempt to bury it.  The
withdrawal stands; the reason I originally gave for it was wrong and is
corrected below.**

I first wrote that the deficit is *focus-dependent* -- r = +0.654 on
`coffee-bean`, r = +0.982 on a second subject -- and therefore defocus bleed by
15.5's own discriminator.  **A verifier killed that, and it was right to.**
Bracket index predicts the deficit better than sharpness does (r = **+0.9887**
against +0.654), the "sharpest 10%" frames are just the *late* frames, and
removing the bracket trend collapses the effect from 1.43 points to **0.13** on
`coffee-bean` and **reverses its sign** on the ruler.  I had replaced an unsound
"it is shadow" with an equally unsound "it is bleed".

The real answer is that **nobody has measured this quantity yet, including me.**
MEASURED, independently, on the raw frames: scene content moves **~88 half-res
px = ~176 full-res px** between the ends of the `coffee-bean` bracket, and the
displacement **reverses sign across the frame** -- outward at both edges in the
early frames, inward in the late ones.  That is not translation, it is a
**magnification change: focus breathing**, which is exactly what racking focus on
a macro lens does.  The band in question is 130 full-res px wide.

So both instruments failed, in mirror image, and for the same underlying reason:

| | what it held fixed | what moved | consequence |
| --- | --- | --- | --- |
| **15.5** | the scene | the mask (per-frame, IoU to 56%) | measured different territory each frame |
| **16, as first written** | the pixel window | **the scene** (176 px of breathing) | measured different content each frame |

**Neither ever held scene content fixed, so neither could detect
focus-dependence in either direction.**  The finding is withdrawn for
under-determination, not because a competing mechanism was proven.  Section
15.5's table should be read as retracted for the d=120..250 row, and 16.4's
original bleed claim is retracted with it.  16.10 records the verification in
full.

### 16.1 Provenance, before any number

- **Binary** `C:\dev\strehl-out\BUILD-BLEND\target-flip\release\strehl.exe`,
  SHA-256 `DC72971E27EF654E18535E8162C6E6E55FDC7E1208EB21626A0EBDDEC7EA6FD9`.
  The `flip/` TIFFs it is compared against were produced *before* this file's
  mtime, so **for the `flip/` pair the binary is still not hash-verified** (15.1).
  Every render *I* made in this section was made by this hashed binary.
- **Argv diff, pasted rather than described.**  My two ladder arms differ in
  exactly two tokens, the merge mode and the output path, which is the minimum
  possible:

      ARGV A: stack <dir> --merge estimator --out <A>.tiff --demosaic
      ARGV B: stack <dir> --merge pyramid   --out <B>.tiff --demosaic

  For contrast, BUILD-BLEND's `placebo-render.ps1:14` that produced the `flip/`
  pair differs in **three**: it adds `--gate 2.0` to the estimator arm only.
- **Gate.**  Two different parameters with two different compiled defaults, and
  my first draft of this line conflated them.  The estimator arm's noise gate is
  **4.00** (`one-estimator.log:22`, `merge.rs:443 DEFAULT_GATE = 4.0`); the
  pyramid arm's band gate is **2.00** (`one-pyramid.log:27`, `pyramid.rs:944`).
  Neither is the gallery masters' `--pyramid-gate 4.5`.
- **Runtime banner, quoted not paraphrased**, from `one-pyramid.log`: `bands: 7
  Laplacian levels + 1 base`, `noise gate: 2.00`, `folded: 1 / 1 frames`, and
  `not applied: photometric gain, clip census, outlier rejection, halo
  correction, through-focus statistics`.
- Instrument: `experiments/BUILD-ELECT/src/shadowenv.py`, committed at
  `22a2069f`.  Logs `shadowenv-{cb,one,ruler}.log`, pictures
  `pics/SHADOWENV-{cb,one,ruler}.png`, all under `C:\dev\strehl-out\BUILD-ELECT\`.

### 16.2 The instrument, and what it does not share with the original

15.5's number rests on four soft parts: a brightness mask, a distance transform,
a radial median, and a far-field reference.  `shadowenv.py` shares none of them.
It is per-pixel, not radial; each image is normalised by its **own** unshadowed
reference, which is also the only way a rawpy decode and a strehl render can be
compared at all, since their DN scales differ; the distance transform only
*proposes* regions and the picture shows what it proposed.

It also brings one thing 15.5's construction cannot have: **one fixed mask for
every image**, taken from the merge, so the band is the same physical pixels in
every frame and in both merges.  15.5 gave each frame **its own** mask.  16.6
measures what that costs.

**Commissioning runs before any result and both nulls are printed above it.**

| check | `coffee-bean` | ruler | reading |
| --- | ---: | ---: | --- |
| PLANT, darken band x0.90 | error **-0.0000** pts | error **-0.0000** pts | PASS |
| NULL, two halves of the reference | **+22.399%** | **-6.717%** | **FAIL both** |

**The reference band is not flat.**  On `coffee-bean` two halves of the region
used as "unshadowed reference" differ by 22.4%.  That does not invalidate a
merge-versus-frames *comparison*, because the same non-flatness multiplies every
arm equally, but it does mean **no absolute depth taken against it is a physical
number.**

### 16.3 The truth value is not soft, it is under-determined

The owner asked whether -6.4% could be obtained a second, independent way.  It
cannot, and the reason is worse than imprecision.  MEASURED, identical pixels,
same 105 frames, the only difference being the central statistic:

| statistic | truth over 105 frames | estimator arm | pyramid arm |
| --- | ---: | ---: | ---: |
| band **mean** | **-3.69%** | -5.17%  (-1.47 pts) | -3.82%  (**-0.13** pts) |
| band **median** | **-0.30%** | -3.46%  (-3.16 pts) | +0.34%  (**+0.64** pts) |
| swing | **3.39 points** | | sign of the pyramid difference **flips** |

The effect being claimed was 2.6 points of loss.  **The instrument's own
choice between mean and median moves the answer by 3.39 points on the same
pixels, and flips the sign of the pyramid's difference from -0.13 to +0.64.**
A 2.6-point claim cannot be made on a quantity with a 3.4-point analysis
ambiguity.  Neither reading reproduces -6.4%.

On the single-frame ladder the same split is 2.93 points (-3.49% mean versus
-0.56% median) on **one** frame, so this is not sampling noise across the
bracket; it is the band's azimuthal non-uniformity, which the NULL had already
reported as 22.4%.

**Two corrections to this table, from verification.**  First, the swing is *not*
a clipping artifact -- on `DSC00068` the band holds **0.000%** of pixels at or
above 64000 DN (max 60448), and excluding saturation from both regions still
leaves a 3.01-point gap.  The cause is band heterogeneity: the band's 1st to
99th percentiles run **32351 to 59688 DN** about a mean of 48272, sd 8425 = 17%.
Second, and against me: **the pyramid arm's median is measured through the
container ceiling.**  On the full-res merge grid the pyramid band has **20.73%**
of pixels pinned at 65535, and its reference band 8.64%, against 7.88% and 2.93%
for the estimator.  The -0.13 -> +0.64 sign flip therefore **cannot be attributed
to the mean/median choice alone** and should not be offered as clean evidence.
The under-determination conclusion stands on the `coffee-bean` truth column,
which is unclipped.

### 16.4 The premise -- focus-invariance -- is unfalsifiable here, not false

**This section originally claimed the deficit is focus-dependent and therefore
defocus bleed.  That claim is RETRACTED.**  It is preserved here with its
refutation because the way it failed is the useful part.

15.5 argued the deficit was real shadow *because* it was focus-invariant across
the bracket at -5.70% to -7.03%, a 1.3-point spread.  With one fixed mask,
MEASURED:

| subject | frames | corr(band sharpness, depth) | sharpest 10% | softest 10% | difference |
| --- | ---: | ---: | ---: | ---: | ---: |
| `coffee-bean` | 105 | +0.654 | -3.03% | -4.46% | 1.43 pts |
| `highly-angled-ruler-mm-cpl` | 60 | +0.982 | -24.09% | -37.03% | 12.94 pts |

Those correlations reproduce exactly under independent code.  **They do not mean
what I said they meant.**  Three measurements kill the inference:

| test | `coffee-bean` | ruler |
| --- | ---: | ---: |
| corr(band **sharpness**, depth) | +0.654 | +0.982 |
| corr(**bracket index**, depth) | **+0.9887** | **+0.9914** |
| sharpest-vs-softest split, raw | +1.434 pts | +12.930 pts |
| the same split, **bracket trend removed** | **+0.133 pts** | **-1.045 pts** |

**Bracket position explains 97.75% of the depth variance; band sharpness
explains 42.7%.**  The "sharpest 10%" frames on `coffee-bean` have mean index
75.4 and the "softest" have mean index 25.5, so the split I read as a focus
split is a *position* split wearing a focus label.  Detrend the bracket and the
effect collapses to a fifth of a point -- and on the ruler it changes sign.

Two further checks, both against me:

- **Matched-sharpness pairs.**  60 `coffee-bean` frame pairs matched to within
  3.0 in band sharpness but separated by more than 40 in bracket index differ in
  depth by up to **1.90 points** -- more than the whole 1.43-point effect I
  attributed to focus.  `DSC00016` and `DSC00120` sit **5.3%** apart in
  sharpness and span **100%** of the depth range.
- **The mechanism I proposed is contradicted by my own frames.**  I argued that
  as a frame defocuses, the dark body spreads outward into the band and darkens
  it.  Band sharpness peaks at index 75 (271.2) and falls back to 195.8 by index
  104 -- the band re-blurs -- while depth over that same leg gets *shallower*,
  -3.03% to -2.58%.  Under my own mechanism it had to get deeper.

And on the ruler the correlation is **non-identifiable**: in that 60-frame even
stride, every focus proxy is monotone in bracket order, so focus and position are
the same variable and r = +0.982 distinguishes nothing.

The reason all of this happens is 16.0's measurement: **the scene is sliding
through my fixed window at ~176 full-res px across the bracket, monotonically,
because magnification changes with focus.**  Bracket index is the breathing
parameter.  A fixed pixel window on unregistered frames measures the breathing,
not the focus.

**Consequence for the truth value.**  I had written that against the sharpest
frames both arms come out *deeper* than truth.  That result does not survive
either, because it depends on which focus proxy defines "sharpest".  MEASURED,
same pixels, same 105 frames:

| sharpness proxy | corr with depth | sharpest-10% truth | pyramid arm reads as |
| --- | ---: | ---: | --- |
| band gradient (the one I used) | +0.654 | -3.03% | 0.79 pts **deeper** |
| far-field reference, d=600..1400 | +0.297 | -3.99% | 0.17 pts deeper |
| **subject interior, d <= -300** | **-0.437** | **-4.42%** | 0.60 pts **lifted** |
| whole frame | -0.439 | -4.26% | 0.44 pts lifted |

**The correlation does not even keep its sign across proxies, and the verdict
flips with it.**  "Truth = the sharpest frames" is not a defined quantity on this
data.  Choosing the proxy after seeing which answer it gives is precisely the
error this project has spent the night catching, and I committed it.

### 16.5 Generalisation: it does not, and the reason indicts the instrument

The owner suggested the ruler because "the only dark band below the rule is the
rule's own shadow".  I rendered it (299 frames, both arms, hashed binary above)
and looked at what the bands landed on -- `pics/SHADOWENV-ruler.png`.

**The d=120..250 band does not lie on the rule's shadow.**  It lies along the
edge of the bright sweep in the lower right.  The rule's own shadow is a
diagonal band deep in the mask interior, at negative d, and is never measured.

That is the general problem, and it applies to `coffee-bean` too, where the band
traces the bean's silhouette on one side and the boundary of a dark backdrop
gradient on the other (the mask is 59.62% of frame because a dark region of the
sweep joins the subject's connected component).  **The band is defined by a
brightness threshold, so it traces brightness contours.  A brightness contour is
exactly where a "depth below the far field" statistic will always find a
deficit, whether or not any shadow is present.**  The instrument locates the
threshold, not the shadow.

So: **it does not generalise, and the failure is not subject-specific bad luck.**

### 16.6 Why 15.5 got a different number: its mask slides through the bracket

15.5 profiled each frame "using its own mask and its own far field, so no
registration is needed".  `maskdrift.py`, MEASURED on five frames spanning the
`coffee-bean` bracket:

| frame | mask, % of frame | threshold, DN | band, px | IoU with mid-bracket band |
| --- | ---: | ---: | ---: | ---: |
| DSC00016 | 60.22% | 32153 | 670101 | **56.12%** |
| DSC00042 | 58.59% | 33059 | 690778 | 74.67% |
| DSC00068 | 57.24% | 30877 | 695399 | 100% |
| DSC00094 | 56.25% | 30232 | 710897 | 77.26% |
| DSC00120 | 55.23% | 29678 | 719088 | **60.81%** |

The mask shrinks monotonically by **4.99 points of frame** and its threshold
drifts **7.7%** first-to-last across the bracket -- **10.2%** max-to-min, and
unlike the area the threshold is **not monotone** (32153, 33059, 30877, ...).
That is the photometric drift the runtime banner already warns about for this
exact subject: `coffee-bean 11.70% -> 2.34 gate units`, under `STATUS: NO
per-frame gain term is fitted or applied.`

**At the ends of the bracket only 56% of "the band" is the same pixels as at the
middle.**  A per-frame mask makes the d=120..250 band a moving target, so the
1.3-point spread that 15.5 read as evidence of focus-invariance was a spread
measured over **different territory in every frame**.  It could not have detected
focus-dependence, because it never held the region fixed.

**Two corrections, one of them fatal to the way I used this section.**

First, scale.  `maskdrift.py:20` computes the band on the **half-res** rawpy
grid, so its `d=120..250` is physically `d=240..500` on the merge grid -- *not*
the band under discussion.  At the band actually in question (`d=60..125`
half-res) the end-of-bracket IoU is **27.26% and 34.55%**, not 56% and 61%.  The
criticism of 15.5 holds a fortiori; the published figures were for a wider ring.

Second, and this is the one that matters: **I used this table to convict 15.5 of
a fault whose mirror image is in my own instrument.**  `shadowenv.py` holds the
region fixed *in pixels* and never registers the frames to each other -- and
16.0 measures ~176 full-res px of scene motion across this very bracket.  15.5
held the scene and moved the mask; I held the window and let the scene move.
**Both measure different content in every frame.**  This does not rehabilitate
15.5's -6.4%; it removes my standing to have replaced it with a mechanism.

### 16.7 What is doing the lifting: a separation experiment, not a favourite

The owner asked for an A/B that discriminates between the hull clamp, the
pyramid reconstruction, the demosaic, black-level handling, and exposure.  There
is one experiment that separates all of them at once: **stack a single frame.**
With one frame there is no election and no combination, so anything that moves
the shadow is a per-frame stage.  Compared against a rawpy decode of the *same*
frame, in the *same* band, with the *same* fixed mask:

| arm | band mean depth | vs rawpy | band median depth | vs rawpy |
| --- | ---: | ---: | ---: | ---: |
| rawpy decode of DSC00068 | -3.49% | -- | -0.56% | -- |
| `--merge estimator`, 1 frame | -3.64% | **-0.14 pts** | -0.66% | **-0.10 pts** |
| `--merge pyramid`, 1 frame | -3.64% | **-0.14 pts** | -0.66% | **-0.10 pts** |

The two output TIFFs have different SHA-256s (`3AF3CF5C...` vs `1B99A15F...`),
and I originally offered that as proof the arms had not collapsed to one code
path.  **It proves nothing.**  MEASURED on the pixels: the two files are
**100.0000% identical -- 6 differing samples out of 98,898,048**, max |diff| 101
DN, means agreeing to six decimal places.  At the level this measurement
operates on, the arms *did* collapse.

That forces a much narrower exoneration list than I first wrote, because several
stages are **inert at n=1 by construction** rather than measured innocent:

| stage | status at n=1 | evidence |
| --- | --- | --- |
| hull clamp | **untested** -- output is forced | `pyramid.rs:2199` test `the_clamp_is_exact_on_a_single_frame`: with one frame the hull is the frame, so `[lo,hi]` is a point |
| Laplacian decompose/reconstruct | **untested** -- overwritten by the clamp | same test, `assert_eq!` per pixel |
| photometric normalisation | **inert** | `one-estimator.log:54` `gain span : 1.0000 (max/min across 1 frames)` |
| clipping census | **inert** | `one-estimator.log:80` `ever clipped : 0.0000% (3 of 8241504)` |
| 17x17 regulariser | **vacuous** | regularises a winner field with one candidate; `n_eff=1 100.00%` |

**What the experiment genuinely supports, and all it supports: the demosaic,
black-level handling, exposure, CA correction and the single-frame align
resample together land within 0.14 points of a rawpy AHD decode.  None of those
lifts a shadow.**  The five rows above are **not** exonerated and I withdraw the
claim that they were.

The section as first written was also internally inconsistent: it exonerated the
hull clamp and photometric normalisation and then said "whatever residual
difference exists must come from combining frames" -- those two stages only act
*when* frames are combined.

### 16.8 Two of my own instruments failed their commissioning and are reported dead

Reporting these rather than quietly dropping them, because a detector that has
never returned a known answer is not an instrument.

- **The backdrop surface fit is unusable.**  Its null mirrors the real geometry
  exactly -- fit an 800 px band, predict a 130 px band 350 px inside it, on
  shadow-free backdrop.  Held-out null by order on `coffee-bean`: -2.3%, -3.2%,
  +3.0%, -5.6%, +1.9%, against a 0.5% criterion.  **FAIL at every order.**  The
  fitted depth swings from -11.5% to +7.7% across orders and the sign of the
  merge-minus-truth difference is not stable, so by the rule printed above the
  table it was never a result.  A global polynomial cannot represent this
  backdrop.  On the ruler order 5 diverges to 1e15 outright.
- **The envelope test is dead by its own null.**  It counts pixels where the
  merge exceeds the per-pixel max over all frames -- light that was
  manufactured, not selected.  It reports 53.5% and 64.9% of the shadow band,
  but **57.8% and 55.8% of the shadow-free reference band**, so it is firing
  everywhere and separates nothing.  Frames are unregistered, which widens the
  envelope and should have made violations *harder*; it did not.  Any future use
  needs the frames registered first.

An earlier version of the fit null split the reference into top and bottom
halves.  That put the held-out set outside the fitted domain and the polynomials
diverged to 1e15.  **A null that tests the wrong extrapolation is not a null**,
and it read as a catastrophic failure of the estimator when it was a failure of
the null.

### 16.9 What section 16 does not settle

- **The rule's own shadow has still never been measured.**  I showed the band
  misses it; I did not then hand-place an ROI on it.  A hand-placed ROI is a
  different kind of soft -- selection by eye -- but it is the honest way to get
  a real cast shadow, and it is the obvious follow-up if anyone still wants the
  number.
- **The absolute depth of any shadow in this corpus remains unmeasured.**  16.3
  shows the mean/median ambiguity is 3.4 points; nothing here produces a
  physical value, only comparisons.
- **The ruler was measured on a 60-frame subsample of 299**, chosen by even
  stride.  `coffee-bean` used all 105.
- **Frames are never registered to each other, and they move a long way.**  This
  is 16's largest defect and it was found by verification, not by me.  My
  instrument registers the rawpy grid to the merge grid *once*, integer-only,
  with a flat peak (ncc 0.62125 against 0.62101 for the best non-adjacent rival
  on `coffee-bean`, an exact tie at zero shift on the ruler).  I then asserted
  regional means are insensitive to a 1-2 px offset.  **The actual inter-frame
  motion is two orders of magnitude larger.**  MEASURED by NCC on 500x500
  patches against the mid-bracket frame, half-res grid:

  | site | DSC00016 peak | ncc, peak vs zero shift | DSC00120 peak | ncc, peak vs zero shift |
  | --- | ---: | ---: | ---: | ---: |
  | far-left | (+4, **-48**) | 0.9870 vs 0.8949 | (-6, **+40**) | 0.9827 vs 0.9119 |
  | right-mid | (-6, **+52**) | 0.9513 vs 0.7933 | (-8, **-36**) | 0.9737 vs 0.7895 |

  ~88 half-res px = **~176 full-res px** between bracket ends, in a band 130
  full-res px wide.  The sign **reverses between left and right within a single
  frame** -- early frames push content outward at both edges, late frames pull it
  inward -- so it is a **magnification change of roughly 7 points across the
  bracket**, not a translation.  Focus breathing, which is what a macro lens does
  when you rack it.  **The correct experiment -- the depth series on properly
  registered frames -- has not been run by anyone, so the true focus-dependence
  of this band is unknown in both directions.**
- **15.5's producing script and log no longer exist**, in the tree or under
  `C:\dev\strehl-out\`; a search for `-7.03`, `-6.40%` and `-5.70` across every
  log there returns nothing.  So -6.4% cannot be re-derived and I cannot say
  which pixel grid it used.  That is one more reason it should not stand, and
  one reason the scale mismatch in 16.6 cannot be fully resolved.
- Source frames decode rawpy AHD `half_size` while the merges are
  Malvar-He-Cutler.  For smooth backdrop levels this is a small bias, but it is
  not zero and it is not characterised.
- **No regression test covers any of this.**  Same gap 15.10 recorded.
- Nothing here is independently verified.  A verifier was commissioned on 16
  before it was reported as settled.

### 16.10 The verification, and what it cost me

16 was written, then verified by an independent agent instructed to kill it.  It
returned **DEFECTS FOUND**, and the honest summary is that **the withdrawal
survived and my reasons for it did not.**  Recorded here rather than quietly
patched, because the pattern is more useful than the conclusion.

| claim | verdict | what changed |
| --- | --- | --- |
| deficit is focus-dependent, therefore bleed | **refuted** | bracket index beats sharpness, +0.9887 vs +0.654; detrended effect 1.43 -> **0.13** pts, sign reverses on the ruler |
| truth is under-determined, 3.4-pt mean/median swing | **holds** | reproduced at +3.40 pts; not clipping (0.000% saturated); pyramid sign-flip leg contaminated by 20.73% clipping |
| 15.5's mask slides | **holds** | every figure reproduced to the digit; but computed on the half-res band, so the numbers describe `d=240..500` |
| single-frame ladder exonerates 8 stages | **refuted** | outputs 100.0000% identical; 5 of the 8 stages are inert or forced at n=1 |
| the band does not lie on the rule's shadow | **holds** | confirmed from the pictures |

Two verifier claims I re-derived myself at the primary source before accepting
them, per the rule that a verifier's prescription can carry its own defects: the
`gates : 4.00` line in `one-estimator.log:22` against `merge.rs:443`, and the
6-of-98,898,048 pixel difference, which I recomputed with my own code.  The
breathing measurement in 16.9 is mine, run independently after the verifier
reported motion; my patch sites and search parameters differ from its, and the
displacements differ in detail while agreeing on the fact and the sign reversal.

**The lesson, and it is the same one that cost the orchestrator two numbers
tonight.**  I had a correlation of +0.654, a mechanism that explained it, and a
discriminator handed to me by the section I was retracting.  I did not check
whether a *third* variable predicted the outcome better than my candidate did --
and one did, at +0.9887, on data I had already collected.  A confound that sits
in your own array is not caught by adding more subjects; the ruler agreed with me
at +0.982 and was the *most* confounded of the two.  **Agreement between two
measurements that share a confound is not corroboration, it is the confound
speaking twice.**

---

## 17. The owner opened the picture and my arc statistic was backwards

He asked for a crop box so he could look at the d~275 px feature himself.  He
looked, saw a large grey aura hugging the silhouette in the **control** arm that
my statistic had scored as clean, measured a within-crop profile, and sent back
the opposite of my ordering.  **He is right.  15.9's and 16's "the control has
no arc there, the feature is introduced by the blend" is RETRACTED.**

Re-measured with a rebuilt instrument, one pinned pair, shared mask,
`arcprofile.py`:

| | CONTROL (estimator) | BLEND (pyramid) |
| --- | ---: | ---: |
| aura band d=100-500, mean | **-10.13%** | **+0.21%** |
| the same, absolute | **-1935 DN** | **+39 DN** |
| per-sector median, 19 sectors | **-5.95%** | +1.35% |
| worst single bin | **-25.48%** at d=112 | -0.87% |
| recovers to within 1% of far field | d=**488** px | d=**112** px |
| far-field level | 19100 DN | 19004 DN |
| null floor, same backdrop | -3.35% | -3.02% |

**The two arms differ in sign**, so no ratio between them is quoted.  The
control's worst bin is **7.6x** its own null floor; the blend's aura-band worst
is **0.29x** the floor, i.e. below it.  Every one of the control's 19 sectors is
negative.

### 17.1 Why the old statistic said the reverse -- two separate bugs

**Bug 1, structural blindness, and it is the larger one.**
`peaksite.prominence_near` scores a **local maximum** over its outward trough.
A dark aura is a **depression**, and one that recovers monotonically outward has
**no interior local maximum at all** -- the test `vals[i] >= vals[i-1] and
vals[i] > vals[i+1]` never fires, the function returns `None`, and the row
records prominence **0.00**.  The control's profile rises monotonically from
14233 DN at d=112 to 19183 DN at d=588.  **It was a bump detector pointed at a
hole.**  It then scored the blend's one genuine small bump (+0.83% at d=262) as
the larger defect.  The instrument did not measure the wrong amount of aura; it
was structurally incapable of representing an aura as a nonzero number.

**Bug 2, a null inside its own reference.**  `NULL_LO, NULL_HI = 700, 1050` lay
entirely inside `ringprofile.FAR_LO, FAR_HI = 600, 1400`.  Signal and null were
both normalised by the region the null was drawn from.

> **A defect broader than the gap between the signal window and the null window
> contaminates its own reference and reads as absent.**

The owner's generalisation, and it is the fourth instrument this week to fail by
resembling its own intended output.  Note the two bugs are independent: fixing
the null alone would not have helped, because bug 1 returns 0.00 for the control
whatever the reference is.  **I reported a 12.1x SIGNAL/NULL ratio as evidence
the blend introduced the feature.  It was evidence that the blend's residual is
localised enough to fit inside the window, and the control's is not.**

### 17.2 The rebuilt instrument, and what its commissioning caught

`arcprofile.py` replaces peak prominence with a **signed deviation from a far
field**, prints the profile at every radius above any summary, and separates
three things v1 conflated:

- the **edge transition** -- every subject dips at its own silhouette because
  defocus spreads a dark body outward.  Optics, present in both arms, not a
  defect.
- the **aura** -- a depression persisting well past the edge transition.
- the **rim** -- a positive excursion, reported with its own sign so a bright rim
  can never cancel a dark aura inside one number.

| check | result | reading |
| --- | --- | --- |
| NULL A, constant 20000 DN frame | worst **+0.0000%** | PASS, no feature manufactured |
| NULL B, real backdrop d=1500-2100 | -3.35% / -3.02% | the floor on real data, **outside** the reference and 3x beyond recovery |
| PLANT, d=50-250 x0.85 | expected -15.36%, got **-15.36%** | PASS |
| EDGE CAL, `coffee-bean` | recovers by d=262 / d=162 | the edge transition is ~150-250 px wide |

**Two of these failed on the first run and the failures were the useful part.**
The PLANT failed (-16.98% against an expected -22.08%) because my *expectation*
was computed from the frame's worst bin, which sits at d=12, **outside** the
planted band -- an error in the check, not the instrument.  And `coffee-bean`,
which I had queued as a null on the owner's description of it as a free negative
control, returned **-35.86%**.  That is not a null failing; it is
`coffee-bean` having an ordinary **edge transition**, which every subject has.
**It is a calibration, not a null, and calling it one would have been the same
category error as v1.**  The owner's "0.23%" for `coffee-bean` refers to a bright
*ring*; the two statistics measure different features and both are small there.

### 17.3 What survives from 15.9, and what the blend's residual actually is

**Survives:** the azimuthal-averaging point.  A profile mean over a feature
living in a few sectors reports a number that occurs at no azimuth.  Per-sector
reporting is right and the owner has kept it.

**Corrected:** the direction.  Per sector, `arcprofile.py` gives

- **CONTROL**: min **-12.97%** (sector 22, 330-345 deg), median -5.95%, max
  -2.17%.  **All 19 sectors negative** -- a dark aura the whole way round.
- **BLEND**: min -1.44%, median +1.35%, max **+7.69%** (sector 2, 30-45 deg) --
  a *localised bright* excursion, which is the feature I originally found and
  mislabelled.

So the blend's residual is real, is **positive**, and is **localised to a few
sectors** -- whole-frame +0.21% understates it exactly as 15.9 said azimuthal
averaging would.  Crops cut for the owner at exact 1:1, shared stretch:
`pics/AURA-sector2-blend-residual--*--1to1.png` (crop 4294, 3363, 1200, 900) and
`pics/AURA-sector22-control-worst--*--1to1.png` (crop 4579, 1546, 1200, 900).

### 17.4 What 17 does not settle

- **I have not opened the sector-2 crop myself and should not be the one to
  judge it.**  +7.69% in one sector is not small, and it is the blend's, not the
  control's.  It is the open item.
- The null floor is **-3.0 to -3.4%**, not zero, because the backdrop has a real
  large-scale roll of ~2% peak-to-peak that appears identically in both arms.
  Any aura claim below about 3% is inside that floor.
- The `flip/` pair is still **not hash-verified** (16.1): the binary's mtime
  postdates the renders.  Everything in 17 is measured on that pair, so it
  inherits that gap.
- `AURA_LO = 100` is set from the `coffee-bean` edge calibration.  A subject with
  a wider edge transition would need a different cutoff, and the statistic does
  not currently derive it per subject.
- Nothing here is independently verified; a verifier was commissioned on 17
  before it was reported.

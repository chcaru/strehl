# V-hull — independent verification of the four-link merge-backend chain

Verifier: V-hull (V-TONE / V-veiling / V-seam lane). Author of the chain: ORCH.
Nothing in this file was written by the author of the claims. My instruments are
in `C:\dev\strehl-out\V-hull\` (`h1`..`h13`), written from the claims rather than
from ORCH's scripts. Where I ran ORCH's own recipe to reproduce a number he
quoted, I say so on the line.

All measurements are on linear TIFFs read with `tifffile` and asserted `uint16`.
Arms are `ORCH-CLAMP/clean6/flower-bud-alone-cpl--{ctrl,blend}.tiff`, full
resolution 4688 x 7040 x 3.

## Headline, stated first because two implementers are acting on link 2

**Link 2 is REFUTED as a quality claim.** The pyramid does not remove a veil. It
overshoots past the real backdrop by up to **677 DN more than any of its own
input frames**, in every distance bin from 2 to 128 px. The near-silhouette
darkening it "removes" is present in **all five input frames I sampled** and is
therefore real scene content — lens flare around a dark subject on a bright
sweep — not an estimator artifact. The estimator reproduces that content to
within **85 DN**. The pyramid replaces it with a bright cut-out halo.

This is the *same* hull violation as link 4, in the opposite sign. Link 4 is
right, and it is the reason link 2 is wrong.

## A structural note that applies to links 1, 2 and 3

The two arms are produced by **two different binaries**:
`strehl.exe stack --gate 4 --demosaic` for `ctrl`, and
`examples/blend-render.exe --gate 4 --base-mean --camera-linear` for `blend`
(`clean6.ps1`). Every arm difference is therefore a program difference, not
purely a backend difference. Their far fields agree to **6.1 DN** under a shared
mask, which bounds any global level confound, so this does not overturn
anything below — but it is not a one-line backend swap and should not be
described as one.

---

# Link 1 — "the shipped estimator backend draws a halo"

## CONFIRMED WITH QUALIFICATION — the darkening is real, but it is not monotone, 61% of its stated size is the backdrop's own illumination gradient, and it is not drawn by the backend

### Evidence: the magnitude reproduces

| quantity | ORCH | mine | recipe |
|---|---:|---:|---|
| d=0..2 background deficit | -2269.0 / -2269.6 DN | **-2338.0 DN** | ORCH's exact raw `q=0.35` threshold, no largest-component step |
| d=0..2 background deficit | — | -2066.3 DN | my mask (same threshold, largest component only) |
| far-field reference | 19366.9 DN | 19203.6 DN | median at d>500 |

### Evidence: the profile is NOT monotone

Fine 2 px bins, estimator, ORCH's mask recipe, global far-field reference:

| d (px) | 4..6 | 6..8 | **8..10** | 10..12 | 12..14 | 14..16 | **16..18** | 18..20 | 24..26 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DN | -1385.6 | -1271.5 | **-1235.9** | -1302.3 | -1428.5 | -1553.2 | **-1582.9** | -1573.9 | -1485.2 |

The deficit shrinks to a local minimum of **-1235.9 DN at d=8..10 px**, then
**deepens by 347 DN to -1582.9 DN at d=16..18 px**, then decays. Four of the 31
successive bins inside 64 px get deeper. ORCH's own section 27.2 table shows the
same shape independently: -1801.8 (4..8) -> -1846.8 (8..16) -> -1866.1 (16..32).

Link 1's stated discriminator is *"Monotone decay from the edge is a veil;
ringing would depart, reach an extremum a few px out, and return."* **Two
independent instruments — his and mine — show departure, an interior extremum at
16..18 px, and return.** The premise the veil conclusion rests on is false in the
author's own data.

### Evidence: 61% of the magnitude is the backdrop, not the subject

The backdrop is not flat. Inside the *legitimate* far field (d>500 px, verified
0.00% subject):

| reference region | median DN | inside subject mask |
|---|---:|---:|
| corner 400x400 TL | 19076.8 | 0.00% |
| corner 400x400 TR | 19031.2 | 0.00% |
| corner 400x400 BR | **15737.6** | 0.00%, min distance to subject **1667 px** |
| far field p5..p95 spread | **3610.4 DN** | — |

**The backdrop's own p5-p95 spread of 3610.4 DN is 1.75x the entire claimed
d=0..2 veil signal of -2066.3 DN.** Fitting a cubic to the far field only (it
removes 98% of far-field variance, residual sd 139.7 DN) and measuring against
that local backdrop instead of a global median:

| d (px) | 0..2 | 2..4 | 4..8 | 16..24 | 32..48 | 128..200 |
|---|---:|---:|---:|---:|---:|---:|
| global far-field median | -2066.3 | -1633.8 | -1335.2 | -1557.7 | -1175.2 | -491.9 |
| **local fitted backdrop** | **-813.5** | -736.4 | -470.8 | -403.4 | -347.8 | -235.4 |

The reference choice moves the headline number by **1252.9 DN, 61% of it.**

Held-out validation of the backdrop model (fit on d>800, predict the unseen
500<d<800 shell): median residual **-106.3 DN**, sd 197.9 DN, against +10.1 DN
in-sample. **106.3 DN is the honest error bar on every "local" number here**, and
the near-field effects are 3-8x it.

### Evidence: the backend does not draw it

Each image gets its **own** mask, own distance map and own fitted backdrop, so
registration cannot confound this. Deficit vs own backdrop, DN:

| image | 2-4 | 4-8 | 8-16 | 16-32 | 32-64 | 64-128 |
|---|---:|---:|---:|---:|---:|---:|
| frame 000 | -927 | -919 | -870 | -816 | -678 | -478 |
| frame 051 | -685 | -677 | -637 | -590 | -493 | -391 |
| frame 102 | -477 | -468 | -456 | -441 | -396 | -357 |
| frame 153 | -446 | -445 | -448 | -451 | -419 | -378 |
| frame 204 | -443 | -438 | -442 | -479 | -459 | -418 |
| **ESTIMATOR merge** | -744 | -417 | -357 | -391 | -342 | -323 |
| estimator excess over input range | **0** | **21** | **85** | **50** | **55** | **34** |

**Every input frame carries the dark annulus.** It is optical — veiling glare
from a dark subject against a bright sweep — and the estimator reproduces it to
within **85 DN** of the range its own inputs span. The single frames' masks are
larger (37.5-38.6% against the merge's 32.8%), which pushes their bins *further*
from the true silhouette where flare is weaker, so this comparison understates
the frames' flare and is conservative.

**Verdict: the observation is confirmed; the attribution in the word "draws" is
refuted.** Removing this halo is a flare problem, not a merge-backend problem.

---

# Link 2 — "the pyramid backend removes it"

## REFUTED

### Evidence: descriptively the ratio reproduces, and more strongly than claimed

Shared mask applied unchanged to both arms (ORCH's paired design, which is sound):

| d (px) | 8..16 | 16..24 | 24..32 | 32..48 | 48..64 |
|---|---:|---:|---:|---:|---:|
| estimator DN | -1383.5 | -1557.7 | -1416.2 | -1175.2 | -886.2 |
| pyramid DN | -499.4 | -109.1 | -118.8 | -85.7 | -134.6 |
| **ratio** | **0.361** | **0.070** | **0.084** | **0.073** | **0.152** |

ORCH quotes 0.62 / 0.53 / 0.64. My ratios are *lower*, i.e. the pyramid removes
even more than he measured. If "removes it" were the whole question, link 2 would
be confirmed with room to spare.

### Evidence: it removes real content and overshoots the hull of its own inputs

Same registration-free construction as link 1, merges sharing the estimator's
mask, deficit vs own fitted backdrop in DN:

| d (px) | 2-4 | 4-8 | 8-16 | 16-32 | 32-64 | 64-128 | 128-200 | 200-300 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| input frames, min | -927 | -919 | -870 | -816 | -678 | -478 | -375 | -337 |
| input frames, max | -443 | -438 | -442 | -441 | -396 | -357 | -325 | -286 |
| ESTIMATOR merge | -744 | -417 | -357 | -391 | -342 | -323 | -337 | -308 |
| **PYRAMID merge** | **-72** | **-42** | **-7** | **+235** | **+195** | **+57** | **-108** | **-196** |
| estimator excess | 0 | 21 | 85 | 50 | 55 | 34 | 0 | 0 |
| **PYRAMID excess** | **371** | **396** | **434** | **677** | **591** | **414** | **217** | **90** |

**The pyramid emits background values up to 677 DN brighter than any of its 205
input frames, continuously from 2 px to 300 px from the silhouette.** The
estimator's largest excursion is 85 DN.

Two further local references, chosen independently, agree: per-sector
normalisation (36 x 10 degree sectors about the subject centroid, each sector
normalised to its own far field) gives the pyramid **+561.3 DN at d=12..16** and
positive from d=4 outward, while the estimator stays negative throughout.

### The pictures, which the standing rule says outrank the numbers

`HULL-est-pyr-frame102.png` — estimator, pyramid, and single frame 102, each
minus its own fitted backdrop, one shared +-900 DN stretch:

- **estimator**: flat grey backdrop, soft dark surround hugging the silhouette.
- **pyramid**: a wide, hard, bright halo encircling the bud and following every
  contour into the concavities — a cut-out sticker outline.
- **frame 102 (ground truth)**: flat grey backdrop, soft dark surround.

**The single frame resembles the estimator, not the pyramid.** Section 27.3
describes the cut-out sticker outline as the estimator's artifact. Under
flat-field correction it is on the pyramid arm.

`crop-top.png` shows why the mistake is easy to make: in the raw shared stretch
the pyramid's backdrop does look cleaner and the estimator's veil and contour
banding are plainly visible. The pyramid looks better because it has been pushed
*past* the truth, and against a near-white sweep an overshoot is much less
visible than a veil.

### What section 28.3 got wrong, and why

Section 28.3 killed the edge-overshoot hypothesis on the grounds that the
pyramid is brighter on **both** sides of the silhouette and therefore not
antisymmetric. That test used the **global far-field median**, which carries the
3610 DN backdrop gradient documented above. Under a local reference the pyramid
is at **+1.9 DN at d=0..2** rising to **+274.3 DN at d=24..32** and back to
**-169.4 DN by d=200..300** — a localised bright lobe outside, against exact-zero
crush inside. **The overshoot hypothesis was buried by the same uncorrected
backdrop gradient that inflated link 1 by 61%, and it should be exhumed.**

---

# Link 3 — "the pyramid clips mid-tones to exact zero"

## CONFIRMED — every number reproduces exactly; one characterisation does not

### Evidence: exact reproduction

Computed with my own reader, then re-run under ORCH's Rec.709 luma
(`0.2126R + 0.7152G + 0.0722B`, his `zeros.py`) once I found my mean-of-RGB
disagreed:

| quantity | ORCH | mine |
|---|---:|---:|
| exact-zero RGB, estimator | 0 | **0** |
| exact-zero RGB, pyramid | 122,416 (0.371%) | **122,416 (0.3709%)** |
| per-channel zeros R / G / B | 123,050 / 176,531 / 460,886 | **123,050 / 176,531 / 460,886** |
| luma<500, estimator / pyramid | 686 / 432,421 | **686 / 432,421** |
| median DN, estimator / pyramid | 18137.2 / 18550.5 | **18137.2 / 18550.5** |
| disagreement set >2000 DN | 721,189 (2.19%) | **721,189 (2.19%)** |
| medians in that set | 3920.7 / 878.0 | **3920.7 / 878.0** |
| gate-4 / gate-2 zeros | 122,416 / 121,297 | **122,416 / 121,297** |
| Jaccard, shared fraction | 0.9424 / 96.59% | **0.9424 / 96.59%** |

Blue leads by 3.74x. Gate-independence holds. Nothing here is in doubt.

### The one thing that does not survive: "one contiguous region ... not speckle"

| set | pixels | components | largest | comps for 90% | **bbox fill** |
|---|---:|---:|---:|---:|---:|
| exact-zero | 122,416 | **661** | 35.8% | 4 | **3.84%** |
| disagreement >2000 DN | 721,189 | **4,081** | 46.2% | 8 | **5.32%** |

The bbox quoted in 28.2 (`y 744..4687, x 1668..5104, centroid y 3169 x 3678`) is
the disagreement set's, and it reproduces exactly — but **a bounding box cannot
distinguish a contiguous blob from scattered speckle**, and these boxes are 95%
empty. The accurate statement is: a handful of large clusters carrying 90% of the
mass, embedded in thousands of small ones. That is not "one contiguous region",
and it is a better fit to link 4's mechanism than the original description was.

---

# Link 4 — "per-band convexity does not imply reconstruction convexity"

## CONFIRMED, and more severely than claimed — but one supporting argument is refuted and the harness is under-commissioned

### Evidence: the toy reproduces

My own 1-D implementation, written from the mathematical claim:

| exponent | mine: violating / 76,800 | mine: rate | mine: worst | ORCH: violating | ORCH: rate | ORCH: worst |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 0.000% | 0.000 | 0 | 0.00% | 0.000 |
| 1 | 0 | 0.000% | 0.000 | 0 | 0.00% | 0.000 |
| 2 | 0 | 0.000% | 0.000 | 1 | 0.00% | 0.336 |
| 4 | 8 | 0.010% | 0.387 | 2 | 0.00% | 0.054 |
| 8 | **63** | 0.082% | 0.797 | **72** | 0.09% | 0.752 |
| 16 | **497** | 0.647% | 1.896 | **511** | 0.67% | 2.924 |

### Defect 1: the harness has no positive control

`hullproof.py` prints two controls and calls the shared-weight one "the
load-bearing one". With one weighting `w` shared by every band, the output is
`sum_b sum_k w_k dec[k][b] = sum_k w_k frame_k`, a convex combination by
construction. **That control is a tautology; it cannot fail unless the plumbing
is broken.** It shows the instrument is quiet. It does not show the instrument
can respond. My harness carries both:

```
planted 10 px/trial at hull+0.05 x span -> caught 200/200 (PASS)
planted 10 px/trial at hull+0.20 x span -> caught 200/200 (PASS)
planted 10 px/trial at hull+1.00 x span -> caught 200/200 (PASS)
NULL 1 single-frame passthrough : 0 violations
NULL 2 one shared weighting     : 0 / 25,600 violations
NULL 3 per-pixel path, expo=0   : 0 / 10,240 violations
```

### Defect 2: `hullsweep.py` does not pair its arms

`rng = default_rng(7)` is drawn once and the exponent loop generates **fresh
random scenes for each exponent**, so every row is a different dataset. That is
why ORCH's worst-excursion column is non-monotone (0.336 at exponent 2, 0.054 at
exponent 4). Mine, on paired data, is monotone: 0.000, 0.000, 0.000, 0.387,
0.797, 1.896. The headline rate trend is large enough to survive this; the small
cells are noise.

### Defect 3: the extrapolation to 205 frames is refuted, in ORCH's own model

ORCH: *"The 0.140 and 0.09% rates in my toy are small. I have asserted, not
shown, that 205 frames and 7 bands make them large."* It is the reverse. At
exponent 8, global per-band weights:

| frames | bands | violating | rate | worst | median hull span |
|---:|---:|---:|---:|---:|---:|
| 8 | 6 | 24 | 0.117% | 0.612 | 0.597 |
| 8 | 7 | 36 | 0.176% | 0.634 | 0.552 |
| 16 | 7 | 3 | 0.015% | 0.173 | 0.655 |
| 50 | 7 | 2 | 0.010% | 0.089 | 0.705 |
| 100 | 7 | 0 | 0.000% | 0.000 | 0.796 |
| **205** | **7** | **0** | **0.000%** | **0.000** | **0.820** |

**The rate falls to zero as frames are added, because the hull span grows with
frame count** (0.597 -> 0.820). More observations make the hull harder to escape.
The stated inference is backwards.

### The correct argument, which lands much harder

The toy weights each band by `abs(band).mean()` — **one scalar per frame per
band, for the whole signal**. The real merge weights **per pixel**. Redoing the
identical test with per-pixel weights:

| frames | exponent | violating / 10,240 | rate | worst |
|---:|---:|---:|---:|---:|
| 8 | 4 | 2,564 | **25.04%** | 4.944 |
| 8 | 8 | 3,209 | **31.34%** | 5.425 |
| 50 | 8 | 1,790 | 17.48% | 9.519 |
| **205** | **8** | **1,186** | **11.58%** | 5.015 |

with the null intact (expo=0 -> 0.000%) and a clean monotone onset
(0.000%, 3.47%, 13.90%, 25.39%, 31.45% at exponents 0, 1, 2, 4, 8).
**Two to three orders of magnitude above the global-weight toy, and it survives
at 205 frames.** The mechanism is real and severe; the reason is spatial
weighting, not frame count or band count.

### The decisive evidence, which is in the real code and not in any toy

`ORCH-CLAMP/interv/renders/flower-bud-alone-cpl--{unclamped,clamped}.tiff`:

| arm | exact-zero px | luma<500 | median DN |
|---|---:|---:|---:|
| unclamped | **122,416 (0.3709%)** | 432,421 (1.310%) | 18550.5 |
| **clamped to the per-pixel hull** | **0 (0.0000%)** | **101 (0.000%)** | 18547.9 |

**Clamping the reconstruction to the per-pixel hull of the aligned inputs removes
100% of the exact zeros and 99.98% of the sub-500 DN pixels, and moves the frame
median by 2.6 DN (0.014%).** That is direct proof in the shipped code that the
zeros are hull violations, and it is far stronger than the toy that motivated it.
The prediction in 29.4 that the clamp "cannot cost anything real" is measured
here at 2.6 DN.

---

# The number that does not fit

**The pyramid's exact-zero pixels sit *inside* the subject while its hull
violations of +371 to +677 DN sit *outside* it, and both are removed by the same
clamp.** Link 3 and link 2 are one defect with two signs, and the chain treats
them as a benefit and a cost of the same backend. The trade in 28.4 — "no halo,
but 0.37-1.05% clipped" — is not a trade. Both arms of it are the same
unsupported excursion, and the clamped render already demonstrates that fixing
one fixes the other at a cost of 2.6 DN.

The consequence for the ship decision runs the other way from section 28.4's:
the pyramid's headline benefit was never a benefit, so `DEFAULT_MERGE_BACKEND`
staying on `Estimator` is right — but for a different reason than the clip, and
the clip is no longer the blocker, the overshoot is.

# What I could not verify

- I sampled **5 of 205** input frames for the hull comparison. The true 205-frame
  range is wider than the 5-frame range I measured, so the pyramid's excess of
  371-677 DN is an upper bound on a smaller true number. The sampled profile is
  smooth and ordered in `k`, which argues the range is well covered, but a full
  205-frame per-pixel min/max on this subject would settle it and I did not run
  one. **This is the single largest gap in this report.**
- I verified links 1-3 on `flower-bud-alone-cpl` only. The `dry-erase` ratios
  (0.32 / 0.28 / 0.16) and the four no-regression subjects are not
  independently re-derived here.
- The two arms come from two different binaries, bounded but not eliminated as a
  confound (far fields agree to 6.1 DN).
- Section 27.3's crops were tone-mapped through a window from the reference arm;
  mine are backdrop-subtracted. I have not reproduced his exact viewing pipeline,
  so I cannot say *why* his crops read the way they did, only what the arms
  contain.

# Corrections to my own work, recorded against my interest

My first placebo appeared to refute ORCH's: shifting the mask 640 px left the
d=0..2 deficit at **-1570.7 DN** against -2066.3, a collapse of only 24%, where
he reports -2269.6 -> -458.1. I nearly filed that as a defect. It was mine: a
640 px shift of a 32%-area mask **retains 58.5% overlap with the original**. At
genuine separation the deficit collapses as he says:

| shift (px) | overlap with real mask | d=0..2 deficit |
|---|---:|---:|
| 640, 640 | 58.5% | -1570.7 DN |
| 1200, 1200 | 41.1% | +0.5 DN |
| 2000, 2500 | 17.3% | -753.8 DN |
| 0, 3000 | 6.0% | +215.7 DN |
| real mask | 100% | **-2066.3 DN** |

Under his exact recipe the placebo collapses from -2338.0 DN to **+642.1 DN**.
**ORCH's placebo control is sound and his null control is sound.** The paired
mask design in `veilpair.py` — one mask and one distance transform from a named
reference arm, applied unchanged to every arm — is correct and I adopted it.

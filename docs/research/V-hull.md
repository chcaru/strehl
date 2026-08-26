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

---

# Part 2 — the clamped arm, and a retraction of my own link-2 verdict

Assignment: re-point the hull-excursion instrument at a **clamped** pyramid render.
Arms verified before use: clamped `458ecd00a5c8d5f3`, unclamped `f62f41da9e107bd0`,
both matching the quoted prefixes. Both logs show identical argv
`--gate 4 --base-mean --camera-linear --chunks 5`, 205 frames, alignment reference
102, and `colour : no characterisation; CAMERA-NATIVE RGB`. Colour space asserted
from the log and from the data, not from the flag alone.

## Line 1, because it is the answer to the question that was asked

**The clamp does not remove the excursion. It removes 0.000% of it in the
background beyond d=32 px.** Clamped and unclamped background profiles are
identical to within 1 DN from d=128 px outward. The cause survives the bound.

**But my previous verdict on link 2 was wrong and I retract it.** It rested on a
mask that was not on the silhouette. Corrected, link 2 is **CONFIRMED**: the
pyramid removes a real ring artifact that the estimator has and that no input
frame has. Two implementers acting on link 2 should continue.

## My own error, first

My Part 1 link-2 table quoted the pyramid as 371-677 DN outside its inputs' range
and concluded it "erases real optical flare". That used ORCH's `q=0.35` luminance
split as the silhouette. It is not the silhouette.

The subject is dark on a bright sweep and is surrounded by a wide veil that is
*also* below the 35th percentile. The threshold lands at **17063.9 DN** against a
background of 19075 DN, so the mask swallows the entire veil and stops at the
veil's outer edge. `MASK-overlay.png` shows it directly: the mask boundary stands
off the visible bud by a wide moat. **Every distance bin I reported in Part 1 was
measured from the outer edge of the halo, not from the bud.** ORCH's Section 27
and Section 28 use the same rule and inherit the same error.

Replacement rule, anchored on unambiguously dark bud pixels: `luma < frac x own
median`, largest component, holes filled, with `frac` swept over 0.30 / 0.42 /
0.55. Mask area 21.5% instead of 32.2%.

### Commissioning of the corrected instrument

```
PLANT   +50.0 DN at d=16..32 (361595 px) -> measured   +50.00 DN  err +0.00  neighbour move 0.00  PASS
PLANT  +300.0 DN at d=16..32 (361595 px) -> measured  +300.00 DN  err +0.00  neighbour move 0.00  PASS
PLANT +1500.0 DN at d=16..32 (361595 px) -> measured +1500.00 DN  err +0.00  neighbour move 0.00  PASS
NULL  (no plant)                         -> worst bin movement 0.000000 DN                        PASS
```

Three amplitudes recovered exactly, locality held, null exactly zero. The Part 1
instrument was never commissioned this way, which is how the mask error survived.

## Evidence: background residual vs own far field, DN, N = 13 input frames

Frame count raised from 5 to 13 by rendering frames 12, 64, 89, 128, 166, 192 on
the verified pin `DF209CE003E2E6B9`. Every excursion below is against a 13-frame
envelope.

| d (px) | 0-4 | 4-8 | 8-16 | 16-32 | 32-64 | 64-128 | 128-200 | 200-300 | 300-400 | 400-600 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| frames MIN (13) | -12329 | -12062 | -11664 | -10887 | -9353 | -6408 | -3634 | -1318 | -430 | -177 |
| frames MAX (13) | -10248 | -10077 | -8940 | -6566 | -2877 | -800 | -226 | -151 | -83 | 38 |
| ESTIMATOR | -10220 | -7754 | -5836 | -4040 | **-4051** | **-4582** | **-4079** | -1916 | -266 | 13 |
| PYR-UNCLAMPED | -9678 | -5209 | -2166 | -1043 | -498 | -106 | 142 | 335 | 289 | 144 |
| PYR-CLAMPED | -9716 | -5274 | -2295 | -1097 | -536 | -108 | **142** | **335** | **289** | **143** |

Far-field levels: estimator 19009.9 DN, unclamped 19003.2, clamped 19003.2,
frame 102 19010.2. **The two merges agree to 6.7 DN and the estimator matches the
alignment reference frame to 0.3 DN**, so nothing below is a global level artifact.

### Why a hull test is not valid near the silhouette

Inside about 32 px the residual is dominated by the subject's own edge falloff. A
sharper edge recovers faster, so an all-in-focus merge is *expected* to sit above
every single frame there. The sharpest frame f102 gives -8940 DN at d=8-16 and the
most defocused f204 gives -11664. Being outside the envelope in the bright
direction at small d is the signature of successful stacking, not a defect. **This
invalidates the near-field half of my Part 1 table as well as this one**, and I
restrict every level verdict below to d >= 128 px.

## 1. Clamped pyramid, bright excursion — SURVIVES THE CLAMP, UNCHANGED

Far field only, where no edge-sharpness argument applies:

| d (px) | 128-200 | 200-300 | 300-400 | 400-600 | worst |
|---|---:|---:|---:|---:|---:|
| EXCURSION estimator | -445 | -597 | 0 | 0 | **-597 DN** |
| EXCURSION pyramid unclamped | +368 | +486 | +372 | +106 | **+486 DN** |
| EXCURSION pyramid CLAMPED | +368 | +486 | +372 | +105 | **+486 DN** |

**The clamp changed the far-field excursion by 1 DN in one bin and 0 DN in the
other three.** The clamped pyramid is outside its inputs' range in **all four** far
bins.

Threshold sweep, mean residual at d >= 128 px:

| frac | estimator | unclamped | clamped |
|---|---:|---:|---:|
| 0.30 | -1786 DN | +208 DN | +201 DN |
| 0.42 | -1562 DN | +227 DN | +227 DN |
| 0.55 | -1433 DN | +249 DN | +249 DN |

Sign and ordering are stable across the sweep. The verdict does not depend on the
threshold.

### Why the clamp is nearly vacuous here — measured, not argued

Where the clamp actually fired, from a per-pixel diff of the two arms
(12.945% of output pixels overall; the log reports 8.590% / 10.007% / 10.009% /
10.945% per pre-demosaic plane):

| region | n px | fired % | median abs dDN |
|---|---:|---:|---:|
| background d>400 | 16,430,751 | **0.000%** | 0 |
| background d 128-400 | 3,790,799 | **0.000%** | 0 |
| background d 32-128 | 1,385,008 | **0.000%** | 0 |
| background d 16-32 | 254,047 | 0.468% | 59 |
| background d 4-16 | 344,211 | 5.105% | 229 |
| background d 0-4 | 161,757 | 6.481% | 305 |
| subject depth 0-16 | 708,808 | 10.599% | 232 |
| subject depth >16 | 9,927,958 | **41.981%** | 298 |

The clamp's entire action is inside the subject and within ~16 px of the
silhouette. The reason it cannot bite in the background is that the clamp bounds
the output to the per-pixel range of the **aligned inputs in absolute DN**, and the
bracket drifts in exposure: the 13 sampled frames' far-field levels span
**17464.1 to 21517.8 DN, a hull 4053.7 DN wide (23.2% drift)**. A +486 DN
excursion is **12.0%** of that width and passes untouched.

**Verdict: the clamp bounds the error without removing its cause. It is a
guardrail, not a fix, and it is not a guardrail at all in smooth background.**

## 2. Clamped pyramid, dark excursion — REMOVED

| quantity | unclamped | clamped |
|---|---:|---:|
| exact-zero RGB pixels | 122,416 (0.3709%) | **0 (0.0000%)** |
| luma < 500 DN | 432,421 (1.310%) | **101 (0.000%)** |
| frame median | 18550.5 DN | 18547.9 DN |

Confirmed against the hull rather than the zero count: the clamp fired on
**41.981%** of deep-subject pixels with a median correction of **298 DN**, which is
where those pixels were. Cost to the frame median: **2.6 DN, 0.014%**. Link 3's
defect is genuinely fixed, not merely floored.

## 3. Estimator vs clamped pyramid on identical tiles — level says one thing, shape says the other

| statistic | ESTIMATOR | PYR-CLAMPED | 13 input frames |
|---|---:|---:|---:|
| worst far-field level excursion | **-597 DN** | **+486 DN** | 0 by definition |
| far bins outside the envelope | 2 of 4 | **4 of 4** | - |
| descending steps in the profile | **2** | 2 | **0 in all 13** |
| departure from own monotone envelope | **542 DN** | **191 DN** | **0 DN in all 13** |

**On level the two arms are comparable and opposite: the estimator is too dark by
597 DN, the clamped pyramid too bright by 486 DN. Neither is faithful.**

On shape they are not comparable. **All 13 input frames are strictly monotone in
distance — zero descending steps, zero departure.** The estimator departs by
**542 DN**, dipping from -4040 at d=16-32 to -4582 at d=64-128 before recovering.
That is departure, an interior extremum, and return: **a ring, in the estimator, on
the discriminator ORCH himself specified.** The clamped pyramid's departure is
**191 DN, 2.8x smaller**, and sits at d=400-600 rather than at the silhouette.

The eye sees shape, not level, which is why the ring is the visible artifact and
the 486 DN lift is not.

## 4. The picture — ORCH is right, I was wrong, do not retract Section 32

`STRIP-A-hairy-silhouette.png`: frame 102, estimator, unclamped pyramid, clamped
pyramid, 560 px at 1:1, identical coordinates, one shared display curve
(lo 1486, hi 20618 DN), with a backdrop-subtracted row beneath at a shared
+-900 DN.

- **ESTIMATOR: a hard white halo traces every contour of the bud and reaches into
  the concavities between the trichomes**, with a dark smudge beyond it. It is the
  cut-out sticker outline of Section 27.3, and it is unmistakable at 1:1.
- **Both pyramid arms: no halo.** Background smooth, individual trichomes resolved.
- frame 102 is defocused in this region and shows no halo either.

My Part 1 statement that "the bright cut-out halo is on the pyramid" is **wrong and
withdrawn**. It came from comparing arms after subtracting a global cubic backdrop,
which converted the estimator's dark mid-field moat into an apparent bright rim on
the other arm. Section 32 stands.

Crop A was chosen by maximum silhouette-boundary density, which selects for edges.
`STRIP-B-neutral-5050.png` repeats it under a rule neutral to edges — the window
closest to 50/50 subject/background occupancy — and shows the same thing.

## 5. Section 33's flatcrop selection rule — the non-reproduction survives

ORCH asked whether `flatcrop.py` selecting tiles by flatness made it blind to a
noise penalty. Measured with **no tile selection at all**: every background pixel at
d > 400 px, noise as 1.4826 x MAD of the 5-point Laplacian over sqrt(20).

| arm | level DN | noise DN | vs estimator |
|---|---:|---:|---:|
| ESTIMATOR | 19049.2 | 22.62 | 1.000 |
| PYR-UNCLAMPED | 19055.6 | 22.78 | **1.007** |
| PYR-CLAMPED | 19055.6 | 22.78 | **1.007** |
| frame 102 (input) | 19033.4 | 72.14 | 3.190 |

**1.007x, not V-RIM's 1.21-1.58x.** Section 33's non-reproduction holds under a
rule that is neutral to both flatness and edge density. The suspicion was
reasonable and it is not borne out.

## 6. Link 4, confirmed again by the shipped code

The clamped render's own log prints `hull clamp : 8.590% 10.007% 10.009% 10.945%`
per plane. Against the two toy predictions for 205 frames and 7 bands:

| model | predicted violation rate at 205 frames |
|---|---:|
| ORCH's global per-band weights (`hullproof.py` design) | **0.000%** |
| my per-pixel per-band weights | **11.58%** |
| **the shipped merge, measured** | **8.590 - 10.945%** |

The per-pixel correction lands within a factor of 1.06 to 1.35 of the real code;
the global-weight toy is off by everything there is. Link 4's mechanism is
confirmed a third way, and the correction to its supporting argument is confirmed
with it.

## Verdicts, revised

| link | Part 1 verdict | **revised** |
|---|---|---|
| 1 — estimator draws a halo | CONFIRMED w/ QUALIFICATION | **CONFIRMED.** The ring is real, is in the estimator, is 542 DN, and is absent from all 13 inputs. My "not monotone, therefore not a veil" was right; the conclusion it supports is "ringing", not "no artifact". |
| 2 — pyramid removes it | REFUTED | **CONFIRMED — I retract the refutation.** It rested on a mask that was not on the silhouette. |
| 3 — pyramid clips to zero | CONFIRMED | **CONFIRMED, and fixed by the clamp** (122,416 -> 0 at 2.6 DN median cost). |
| 4 — per-band convexity | CONFIRMED, extrapolation refuted | **CONFIRMED, now by the shipped code** (8.6-10.9% measured vs 11.58% predicted). |

## The number that does not fit

**Both merge backends are outside their inputs' envelope in the far background, in
opposite directions, by comparable amounts: estimator -597 DN, clamped pyramid
+486 DN.** The frames' own envelope at d=200-300 is -1318 to -151 DN and neither
arm lands in it. A backend that is merely "not the estimator" has not been shown to
be faithful, only to be wrong in a less visible way. Whatever ships, the far-field
level needs its own test.

## What remains unverified

- **The clamp is uncommissioned as an intervention.** I verified the two binaries
  differ and that the diff is confined to where the log says, but I did not plant a
  sabotage into `interv.py`'s mutation to prove it would have caught a no-op edit.
  I am relying on ORCH's harness for that, which is the thing I am not supposed to
  do.
- One subject, `flower-bud-alone-cpl`. `dry-erase-marker-head-cpl` arms exist at
  `ORCH-CLAMP/interv/renders/` and are not measured here.
- The 13-frame envelope is 13 of 205. It is a lower bound on the true envelope, so
  every excursion quoted is an upper bound on the true excursion.
- The estimator arm still comes from a different binary (`strehl.exe`) than the two
  pyramid arms (`blend-render.exe`). The clamped-vs-unclamped comparison is clean
  one-line interventional; the estimator-vs-pyramid comparison is not.
- `--index-map` with `--n-eff-map` did not recur as `0xC0000409` in this session; I
  did not invoke that pair.

---

# Part 3 — the aligned merge, and BUILD-HULL's proposed invariant

Two questions: is the shipped *aligned* merge convex or is that undecidable from
outside `crates/`, and is the §11 invariant the right one. I confirm BUILD-HULL's
refutation of my own test independently first, because I should not attack its
proposal while accepting its correction on trust.

## 1. The arithmetic — confirmed, with the regime identified

`min` and `mean` do not commute. For a convex merge the true band-level bound is
`mean_B(merge) <= mean_B(max_k x_k)`, and what I tested was
`mean_B(merge) <= max_k mean_B(x_k)`, which is **strictly tighter** and therefore
admits false positives.

My first attempt to make it fire failed, and I record that: over 30 provably convex
random renders it fired **0 times**, with the true bound wider by 0.379 (low) and
1.099 (high) units. Random frames do not trip it. It needs the structure a focus
merge actually has — election correlated with local brightness, because near a
silhouette the sharpest frame is also the least veiled.

Provably convex merges (pointwise assertion passed on every row), 205 frames,
200,000 samples, election weight `(x - min_k x)^expo`:

| selection exponent | mean_B(merge) | max_k mean_B(x_k) | **excess my test reports** | true bound mean_B(max_k x_k) |
|---:|---:|---:|---:|---:|
| 0 | -0.0013 | 0.8510 | -0.8523 | 2.8590 |
| 1 | 0.3463 | 0.7374 | -0.3911 | 2.8282 |
| 2 | 0.6819 | 0.8714 | -0.1895 | 2.8893 |
| **4** | 1.1600 | 0.8696 | **+0.2904 FALSE POSITIVE** | 2.8993 |
| **8** | 1.8300 | 0.8592 | **+0.9708 FALSE POSITIVE** | 2.8668 |
| **16** | 2.5061 | 0.7849 | **+1.7212 FALSE POSITIVE** | 2.8704 |

**The shipped per-band selection exponent ramp is `2 3 4 5 8 8 8`.** Four of its
seven bands sit at exponent 4 or above, which is exactly the regime where my test
manufactures violations out of a convex merge, and the false excess grows
monotonically with the exponent. My positive control confirms the *pointwise* test
is fine: planted violations at +1.0, +50.0 and +300.0 above the hull were detected
500/500 each, and pointwise violations over 6,000,000 convex samples were **0**.

**BUILD-HULL is correct. My 371-677 DN is withdrawn.** That is now the third
independent reason it was wrong, and they are separable: the mask was not on the
silhouette (Part 2), near-field hull tests are invalid because a sharper edge
recovers faster (Part 2), and the statistic was not bounded by convexity at all
(here). Any one of the three is sufficient.

## 2. Can the shipped ALIGNED merge be decided from outside `crates/`? — NO

BUILD-HULL asserts this and proves it by reading. I tested it.

The only route that could work is to render one frame through the bracket's own
205-frame sidecar, giving an aligned per-frame sample. `STREHL_WARPMAP` names a
sidecar and `STREHL_ONLY_FRAME` selects a frame. Together:

```
STREHL_WARPMAP=...\flower-bud-alone-cpl-2701862c2b7e7f4e.warpmap.txt
STREHL_ONLY_FRAME=102  strehl stack D:\personal\macro\flower-bud-alone-cpl --out ... --demosaic
-> rc=1
Error: the sidecar named by STREHL_WARPMAP (...) was not fitted on this bracket
Caused by: this warp map was fitted on stack "flower-bud-alone-cpl"
  (digest 2da87e45b71aed22, 205 frames) but was applied to "flower-bud-alone-cpl"
  (digest 499972446858e9dd, 1 frames)
```

`ONLY_FRAME` reduces the bracket before `alignment_for` runs, so the digest and the
`map.len() == paths.len()` check both fail. This is deliberate — `merge_cmd.rs:1991`
says silently rendering a different registration "would make every control here
unfalsifiable" — and it is right to be. It also closes the only route.

`strehl stack --help` offers exactly two map outputs, `--index-map` and
`--n-eff-map`. There is no aligned-frame export, and no subset-of-bracket merge.

**Re-implementing the warp externally is not a route.** The gather is Catmull-Rom
with negative taps; any resampler I wrote that was not bit-identical would
manufacture edge-local excursions of its own, in precisely the near-silhouette
region under investigation. That confound is larger than the effect.

**Verdict: UNDECIDABLE from outside `crates/`. Convexity is proved on `ALIGN=0` and
unproved on the pipeline that ships.**

### What would have to exist inside for it to become decidable

The minimum is **not** the assertion. An in-crate assertion moves the claim from
unverifiable to self-certified, which is a different thing and a worse one if it is
mistaken for evidence. The minimum that restores external verifiability is an
env-gated writer that emits **the warped plane for frame k at merge time**, after
the gather and before accumulation. Two of those plus the merge output make the
aligned hull measurable by anyone, with no trust in the merge's own opinion of
itself. It is the same shape as `--index-map`, which already exists and is what
made my election work possible.

If the assertion ships instead, it must ship with a **commissioning test that plants
an out-of-hull value and requires the assertion to go red**, in the repository, run
in CI. Otherwise it is an uncommissioned pin: a green that means nothing.

## 3. Attacking the §11 proposal

### 3a. Is 1 DN the right tolerance? — yes, and it is not where the risk is

The accumulator is `f32` folded over 205 frames at levels around 20,000 DN. Worst
case relative error is about `205 * 2^-24 = 1.22e-5`, i.e. **0.24 DN**. A 1 DN
tolerance is ~4x that bound, and BUILD-HULL measured **exactly zero** violations at
**zero** tolerance across 49,477,152 samples, so 1 DN is slack, not fitting.

Against real defects: the violations the pyramid actually commits have a median
absolute correction of **298 DN** (measured in Part 2 from the clamped/unclamped
diff). That is **300x** the tolerance. Nothing that has gone wrong in this project
could hide under 1 DN. **The tolerance is the least interesting parameter in the
proposal and I would not spend more time on it.**

### 3b. Are the two exemptions band-mean-neutral, or a hole? — one is a hole

**MHC demosaic is not exempted, it is out of scope**, because the assertion sits
before it. That is clean as an assertion and it means something different from what
"exemption" suggests: **the assertion does not cover the pixels the user receives.**
0.171% of delivered samples are out of hull with excursions measured at -1150 to
+2074 DN. Net -0.026 DN is a global mean and a global mean is exactly the statistic
that cannot see a locally concentrated defect — the error class that has now bitten
this project four times. The gap between "what is asserted" and "what ships" should
be stated in the doc comment.

**The Catmull-Rom gather exemption is the hole, and it is the wrong hole to open.**
BUILD-HULL's §9 lists it as **not measured**, and argues it neutral "by partition of
unity". Partition of unity gives DC preservation on a *constant* field. It says
nothing about a field with an edge in it. The kernel's non-convexity comes from two
negative taps, so its excursions are **edge-local by construction** — and the
artifact under investigation is a **near-silhouette halo**, which is edge-local too.
**Exempting the warp gather exempts precisely the region the whole investigation is
about.** An unmeasured named exemption over the region of interest is not an
auditable exemption; it is the defect's hiding place. Measure it before exempting
it, or scope the exemption to a measured bound rather than to a stage.

### 3c. Does asserting over the ELECTED samples cover the failure that happened?

This is the question ORCH most wanted checked, and the answer has two parts.

**In the form stated, the worry does not land.** The exact-zero crush is a
*pyramid* defect, and `pyramid.rs:1187` already clamps **after** `collapse` — the
reconstruction, not the election — with `hull: Hull::InputRange` as the default at
`pyramid.rs:823`. That siting is correct. The estimator backend has no band
reconstruction, so for it "end of pass two on the accumulator output" *is* the
output. Neither backend has an invariant sited before its own reconstruction.

**A worse version does land, and BUILD-HULL states it against its own proposal**:

> "the hull invariant I proposed in §11 is blind to it. The merge elects frames in
> which the pixel is not backdrop at all, so the offending value is inside the hull
> by construction. A convexity assertion would have passed this bug silently, and
> shipping it alone would have been worse than useless because it would have looked
> like a guarantee."

That is the correct reading and I endorse it. The -4233 DN artifact is **inside the
hull**. An invariant cannot catch a defect that satisfies it. **§11 is a regression
guard for a property already measured at zero, not a detector for the defect that
motivated it.** Ship it as the former, never describe it as the latter, and put
§12.6 on the critical path instead.

**One thing §11 would genuinely improve and should be credited with**: the pyramid
currently repairs 8.590% / 10.007% / 10.009% / 10.945% of output pixels per plane
**silently, every run**, and only prints the rate. A ~10% silent repair rate is not
a guardrail firing at the margin, it is a structural property of the backend, and it
should be a warning rather than a statistic in a log tail.

### 3d. Runtime cost — measured, and it is not small

From the two interventional logs, one line apart, identical argv, same machine:

| arm | fold time | total | per frame |
|---|---:|---:|---:|
| `Hull::Unclamped` | 160.0 s | 162.0 s | 0.78 s |
| `Hull::InputRange` | **284.3 s** | **295.5 s** | 1.39 s |
| **cost** | **+124.3 s, +77.7%** | **+82.4%** | +78% |

Memory: the hull needs `lo` and `hi` at level-0 size per plane
(`pyramid.rs:883-887`), which for 4 planes of 3520x2344 in `f32` is **264 MB** on
top of the logged 5.2 GB plan.

**An assertion-only variant does not avoid this.** The dominant cost is maintaining
the per-pixel running min/max across the fold; the clamp itself is one `clamp` per
output sample. So the honest figure for "hull invariant on by default" is close to
**+78% merge time**, not a rounding error.

Caveat, stated because it could change the number: nine agents share this machine
and the two runs were 3 minutes apart, not interleaved. The comparison is
interventional in the source but not load-controlled. It should be re-timed on a
quiet machine before the default is decided on it.

## 4. The switch class — a third instance, already documented in-crate

I did not go looking, but the audit for an aligned-frame export surfaced one.
`merge_cmd.rs:3053-3054`:

> `// default loudly. The precedent not to repeat is STREHL_FIX_CA, a`
> `// byte-identical no-op under STREHL_ALIGN=0 that says nothing at all.`

So `STREHL_FIX_CA` under `STREHL_ALIGN=0` is a third member of the class, and the
codebase already knows it and names it a precedent not to repeat. That matters for
how the class is treated: it is not three coincidences, it is a **known failure mode
that has already been written down once and then re-committed twice**
(`STREHL_FIX_HALO` byte-identical on 109MSDCF; `EDGE_AWARE` throttled to
near-nothing). The fix is not vigilance, it is a rule: **a switch that reports
itself ON must be able to prove it changed something, or report OFF with a reason.**
`optics.rs:546-549` already implements exactly that discipline for `STREHL_FIX_CA`'s
*parsing* — refusing to guess, refusing a typo, refusing silently-off. The same
discipline is not applied to its *effect*.

## 5. Verdicts

| question | verdict |
|---|---|
| Is my Part-1 test a hull test? | **NO.** Fires on provably convex merges at exponent >= 4; shipped ramp is `2 3 4 5 8 8 8`. Withdrawn. |
| Is the ALIGN=0 merge convex? | Accepted from BUILD-HULL; I did not re-run it, and I say so in §6. |
| Is the shipped ALIGNED merge convex? | **UNDECIDABLE from outside `crates/`**, proved by a hard error, not by argument. |
| Is 1 DN the right tolerance? | **Yes**, ~4x the 0.24 DN `f32` bound, 300x below real defects. Not the risk. |
| Are the exemptions safe? | **Demosaic: out of scope, state the gap.** **Catmull-Rom: NO — unmeasured, and edge-local over exactly the region under investigation.** |
| Does §11 catch the failure that happened? | **No, and BUILD-HULL says so first.** Ship as a regression guard, never as a guarantee. §12.6 is the one that matters. |
| Cost on by default? | **+77.7% fold time, +264 MB.** Decidable, but must be decided explicitly and re-timed on a quiet machine. |

## 6. What remains unverified

- **I did not re-run BUILD-HULL's 0-of-49,477,152 measurement.** I verified its
  arithmetic and reproduced its false-positive mechanism, which is a different
  thing. Its convexity result on `ALIGN=0` is accepted, not independently
  confirmed, and it is the load-bearing input to everything above.
- The `+77.7%` timing is not load-controlled.
- I did not measure the Catmull-Rom gather's excursion, only argued why exempting
  it unmeasured is unsafe. That measurement needs to happen inside `crates/` for
  the same reason §2 gives.
- `dry-erase-marker-head-cpl` remains unmeasured in Parts 2 and 3.

# V-veiling — an independent attack on ORCH's veiling finding

**Verifier:** V-veiling. **Subject:** `docs/research/ORCH-veiling.md`, claims 1-3.
**Standing:** the author of a finding never verifies it. I wrote every instrument in
this report from scratch and did not read `spill.py`, `rim_diff_lin.py`,
`aura_source.py` or `polarity_test.py` until my own numbers were final.
**Pin:** `C:\dev\strehl-out\pin-859edac\target\release\strehl.exe`,
sha256 `DF209CE0...F97DC70F`, verified before use. All measurement on linear renders.
**Instruments:** `C:\dev\strehl-out\V-veiling\vv_core.py` and `r1`-`r12`.

## Verdict

| # | Claim | Verdict |
|---|---|---|
| 1 | The merge is worse than its own inputs near the silhouette | **CONFIRMED** — the effect is real, visible, and larger than a convex merge can produce |
| 2 | The mechanism is two-layer veiling averaged in by a sigma-calibrated gate | **REFUTED AS COMPLETE** — veiling inheritance accounts for at most 37% of the headline number |
| 3 | The polarity reverses on a bright subject | **CONFIRMED WITH QUALIFICATION** — reproduces as a statistic; a co-registered measurement finds no halo at all on the pencil |

The finding survives. **The mechanism does not.** BUILD-HALO should keep building, but
one of the three components I isolate is repaired by a flag that already exists.

## 1. Claim 1 re-derived independently

Own luminance (mean of RGB), own threshold, own morphology, own distance transform, own
binning. ORCH's table reproduces to 1-3% in every cell, so the arithmetic is sound and
the two instruments agree.

But ORCH's method transfers the **merge's** mask to **all** images, and the bracket is
not one geometry. Measured subject area gives a magnification drift of **227 px of
silhouette radius** end to end, against a defocus-blur residual of only **19 px** (the
residual about a straight line in *k* is U-shaped with its minimum at frame 102, which
is how the two are told apart). Transferring one mask across that is not safe.

Giving every image **its own** silhouette and **its own** distance map removes the
confound. Seven frames spanning the bracket, excess over each image's own far field
(d > 420 px), linear DN:

| image | 4-12 | 12-30 | 30-60 | 60-120 | **120-200** | 200-300 | 300-420 | far field |
|---|---|---|---|---|---|---|---|---|
| frame000 | -6891 | -6331 | -5361 | -3664 | -1500 | -423 | -69 | 17169 |
| frame025 | -6932 | -6214 | -4964 | -2865 | -958 | -211 | -73 | 17541 |
| frame051 | -6913 | -5905 | -4200 | -1649 | -476 | -138 | -78 | 17951 |
| frame102 | -6453 | -4218 | -1482 | -508 | **-213** | -155 | -98 | 18832 |
| frame153 | -7311 | -5749 | -3187 | -1385 | -514 | -220 | -147 | 19732 |
| frame179 | -7820 | -6733 | -4863 | -2191 | -922 | -276 | -173 | 20185 |
| frame204 | -8172 | -7349 | -5907 | -3523 | -1528 | -478 | -185 | 20630 |
| **MERGE** | -4546 | -3777 | -4290 | -4664 | **-4027** | -1591 | -268 | 18891 |

The veiling profile across the bracket is smooth and U-shaped in `|k - 102|` with its
maxima at the two ends, so **no unsampled frame can be more veiled than -1528**.

**Correcting the confound strengthens the claim rather than weakening it.** The merge is
outside the frame envelope in **four** bands (60-120, 120-200, 200-300, 300-420) against
three under the published method, and the headline ratio moves from 16x to **18.9x**.
Individual published cells are nonetheless wrong: frame204 at d=120-200 moves from -366
to **-1528**, a factor of 4.2. **ORCH's assertion that d >= 30 px is safe on a
featureless backdrop is refuted** at the level of the cells, though not of the verdict.

### The instrument is exonerated by a control

A true mean of the same seven frames — an honest convex combination — is reported by my
pipeline as **inside** the envelope in six of seven bands, and outside by **50 DN** in
the seventh. The merge is outside by **2499 DN**. The effect is 50x the instrument's
demonstrated bias floor.

### The picture

`C:\dev\strehl-out\V-veiling\D-merge-minus-f102.png`. `frame102-lin` accepted the
alignment sidecar and resolves to identity, so it is **co-registered with the merge** and
the plain difference is legitimate. It shows a thin bright rim hugging the silhouette,
then a broad dark band reaching ~300 px, on a flat field. The far field of that
difference is **+18 to +41 DN** on ~18800, so the normalisation is not inventing
anything.

### It is not radial, and it is not a subregion

A 2-D grid of distance-from-silhouette against radius-from-centre puts the darkening at
-2291 to -4328 DN across **every** radius inside the d = 60-200 shell and at +20 to +40
DN at d > 300 across every radius. It tracks the silhouette, not the optical axis.
Per-pixel on the co-registered pair, **98.1%** of background pixels at d = 60-120 and
**96.5%** at d = 120-200 have the merge darker than frame 102, 96.3% and 93.3% of them
by more than 1000 DN. The binned median is representative; a per-pixel formulation
agrees with it.

## 2. Claim 2 is refuted as a complete mechanism

`spill.py` pre-registered the falsification in its own docstring:

> If the aura is defocus spill ... **the merge should sit among them rather than outside
> them.** If the individual frames are all flat and only the merge dips, the merge is
> manufacturing it and defocus spill is not the cause.

The merge does not sit among them. ORCH's inference from that — *"so it is admitting
frames more veiled than any of the three"* — is the step that fails: with seven frames
spanning the bracket, **no frame is more veiled than -1528 and the merge is at -4027**.
A convex combination cannot leave the convex hull of its inputs. In **raw** linear DN,
with no normalisation of any kind, the merge reads 14864 at d = 120-200 while the
darkest frame in the bracket reads **15669**.

The merge is also outside the envelope on the **bright** side at d = 4-30 (raw 14344
against a frame maximum of 12458). Outside on both sides of the silhouette is a halo
signature, not a veil.

### Where the -4027 actually comes from

`--index-map` says which frame won each pixel. The election is strongly structured by
distance from the silhouette:

| band | median elected frame | % electing k < 40 | mean level of elected frames |
|---|---|---|---|
| 4-12 | 111 | 1.7% | 18940 |
| 60-120 | 50 | 36.4% | 17933 |
| **120-200** | **10** | **84.4%** | **17475** |
| 200-300 | 3 | 74.5% | 17750 |
| 300-420 | 98 | 27.4% | 18740 |
| far field | 114 | 19.5% | 18939 |

In ORCH's headline band the merge elects the **start of the bracket**; in the far field
it elects the **middle**. The photometric fit measures a **gain span of 1.2350 across
the 205 frames**, and the shipped merge prints `STATUS: NO per-frame gain term is fitted
or applied`. Two populations of frames 23.5% apart in level are being differenced and
the result attributed to veiling.

Three independent routes agree on the size of that component at d = 120-200:

| route | value |
|---|---|
| level of elected frames, band minus far field | **-1464 DN** |
| aura recovered by re-rendering with `--photometric on` | **+1415 DN** |
| far-field reference difference against frame000 | -1722 DN |

The first two agree to **3.4%**, and they were obtained from different artefacts — one
from the election map, one from a fresh render.

`--photometric on` removes **35.1%** of the aura at d = 120-200, **47.1%** at 200-300
and **41.3%** at 300-420, while touching d = 4-30 by only 2.3%. It returns d = 300-420
to inside the envelope. Composite: `aura-shipped-vs-photometric.png`.

### The decomposition

At d = 120-200 the -4027 DN is, exactly:

| component | DN | share | repaired by |
|---|---|---|---|
| genuine inherited veiling, at the level of the worst frame in the bracket | **-1500** | 37% | ORCH's signed envelope |
| exposure drift transferred by a spatially-varying election | **-1722** | 43% | `--photometric on`, which already exists |
| residual convexity violation — the merge below **every** input's raw value | **-805** | 20% | unidentified |

I do not know the cause of the -805 DN term. `stack --help` states the path "does not
yet deconvolve, reject outliers, or model occlusion", so the usual suspects are absent;
the alignment resampler is CatmullRom, which has negative lobes, but its footprint is a
few pixels and this term reaches 200 px. **It is a real convexity violation and it is
unexplained.** It is the smallest of the three and the only one with no known repair.

## 3. Claim 3 — the polarity reverses

The pencil table reproduces, and the merge is `OUTSIDE-dark` in 5 of 7 bands exactly as
published. But `pen-f149-lin` is the pencil merge's alignment reference and is therefore
**co-registered** with it, so the same confound-free difference is available there and
ORCH did not take it. It shows **no halo**: median `merge - f149` runs -139, -227, -176,
-85, +62, +50, +30 DN across the bands on a backdrop of ~3092 DN, changing sign at
d = 120. Against flower-bud's -4290 DN on 18891 that is 5.7% against 22.8%, and it is
flat to the eye (`D-pencil-merge-minus-f149.png`).

**This answers the loose end ORCH flagged as the most likely place the analysis is
wrong.** The near-silhouette darkening is *not* a polarity-independent effect of
comparable size: on the bright-subject case the merge tracks its own reference frame to
within a few percent. The published "merge darker than every frame on the pencil too"
rests entirely on comparisons against the two **mis-registered** end frames, on a
receding backdrop ORCH had already declared unclean. There is no second effect here; the
pencil simply shows almost nothing.

## 4. The remaining attacks, and what they did not overturn

**Far-field normalisation.** The `outside the range` verdict at d = 120-200 survives
every alternative reference, and strengthens under the ones furthest from the subject:

| reference | MERGE | darkest frame | verdict |
|---|---|---|---|
| d > 420 (published) | -4027 | -1528 | OUTSIDE-dark, 2.64x |
| d > 1000 | -3932 | -1472 | OUTSIDE-dark, 2.67x |
| four 400x400 corners | -2266 | -282 | OUTSIDE-dark, 8.02x |
| darkest quadrant far field | -2703 | -385 | OUTSIDE-dark, 7.02x |

This was the wrong attack. The normalisation's weakness is not *spatial*, it is
*photometric*, and no choice of region finds it.

**Mask threshold.** Sweeping 0.40 to 0.70 on flower-bud gives ratios of 16.8x, 18.2x,
18.9x, 16.9x — the verdict does not depend on the threshold. It collapses to 7.8x at
0.80 and 1.1x at 0.90, but for a legible reason: the mask grows from 21.8% to 29.8% of
the frame and swallows the aura it is supposed to be measuring. Not a threat.

**The invariant.** "Never worse than a single frame" is **not** an established project
invariant. `README.md:135` records it as a claim already retracted once, and facts 1129
and 1142 in `SYNTHESIS.md` state that the floor "is unestablished" and is "an intention
rather than a guarantee". ORCH's summary describes the finding as violating an
invariant. It is more accurate, and more useful, to say this is the **first direct
positive measurement** of that floor being broken — which is what facts 1129 and 1142
suspected from the singleton-exposure direction and could not show.

## 5. The number that does not fit

**The merge is 805 DN below the raw value of every frame in its own bracket**, after both
the photometric term and the inherited veiling are accounted for. Nothing in the
documented architecture produces that. A two-pass elect-then-average merge is convex by
construction and cannot do it. Until it is explained, an upper-envelope fix built on the
assumption that the truth is recoverable *from the samples* is building on a floor that
has a hole in it: at these pixels the output is not any sample, and no envelope over the
samples predicts it.

## 6. Incidental defect

`stack --index-map <p> --n-eff-map <p>` together on the 205-frame flower-bud stack exited
`-1073740791` (`0xC0000409`, stack buffer overrun) on first run. Each flag alone exited
0, and the pair succeeded on retry, so it is intermittent. Four agents share this
machine and the run was concurrent with others; I record it rather than diagnose it.

## What BUILD-HALO should take from this

1. The defect is real, visible, and worth the rewrite. Keep going.
2. **Turn `--photometric on` for depth-separated brackets before measuring anything.**
   It is 35-47% of the aura in the affected bands, it costs one flag, and any envelope
   arm measured without it will be credited with a win that a level fit already had.
3. The acceptance floor of -247 DN at d = 120-200 was measured with the merge's mask
   transferred to frames of a different magnification. Re-measure the floor with each
   frame's own silhouette; the correct comparator on that band is **-213 DN**.
4. Expect roughly 800 DN that no envelope over the samples can reach.

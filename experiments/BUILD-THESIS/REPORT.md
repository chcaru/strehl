# BUILD-THESIS: estimation vs selection, measured on resolved detail

Status: `MEASURED`. Not verified — I did not verify my own work and this needs
an independent pass. See *What I could not verify* at the end.

## The question

The README says the expected gain on resolved detail is `~1.2-1.8x` and that
the figure is `ARGUED`, not measured. This closes that gap by rendering six
subjects twice from one binary — the shipping default merge and the shipping
selection baseline `argmax-baseline` — and measuring resolved detail at
matched sites.

## The headline

**On these six subjects the shipped merge does not resolve more detail than
`argmax-baseline`, and `argmax-baseline` does not resolve more than the merge.
Every difference found is at or below what the same instrument reports for the
two arms' noise difference alone with no blur planted at all.**

The `~1.2-1.8x` figure is not observed. Neither is a loss. What the merge
delivers over selection on this corpus is **the same detail, quieter, without
inventing structure** — and the last of those three is the one the sharpness
statistics cannot see and the crops show plainly.

Equivalent Gaussian blur separating the arms, in pixels. `+` means the shipped
merge resolves finer; `-` means `argmax-baseline` does. `null` is what the same
statistic reports on the same tiles for the arms' *real* noise difference with
**zero blur planted** — the yardstick every number has to clear.

| subject | N | FOV | σ a/m | S1 | null | S2 | null | S3 | null | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `bee-3-cpl` | 299 | 0.9321 | 1.064 | −0.45 | 0.34 | +0.09 | 0.26 | −0.00 | 0.22 | nothing above the null |
| `bee-1-cpl` | 299 | 0.9236 | 1.078 | −0.44 | 0.35 | +0.04 | 0.23 | +0.47 | 0.22 | S3 only, +0.47 vs 0.22 |
| `leaf-2-cpl` | 182 | 0.9342 | 1.110 | −0.43 | 0.36 | −0.36 | 0.26 | +0.38 | 0.24 | S2 and S3 disagree in sign |
| `flowers-cpl` | 176 | 0.9367 | 1.625 | +0.49 | 0.45 | +0.26 | 1.33 | −2.06 | 1.23 | **S1 and S3 contradict** |
| `tweezers-cpl` | 100 | 0.9728 | 2.681 | −0.47 | 0.49 | −0.35 | 0.26 | +0.40 | 0.25 | S2 and S3 disagree in sign |
| `flat-on-ruler-cpl` | 79 | 0.9707 | 1.381 | −0.48 | 0.37 | −0.44 | 0.25 | −0.38 | 0.24 | **all three: argmax finer** |

Ratio form, and the same conclusion under a second site-selection rule that
neither arm can contaminate:

| subject | S1 mean | S1 min | S2 mean | S2 min | S3 mean | S3 min |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `bee-3-cpl` | 0.760 | 0.760 | 1.015 | 1.015 | 1.004 | 1.004 |
| `bee-1-cpl` | 0.794 | 0.794 | 1.014 | 1.014 | 1.102 | 1.102 |
| `leaf-2-cpl` | 0.768 | 0.788 | 0.995 | 0.999 | 1.017 | 1.020 |
| `flowers-cpl` | 1.617 | 1.561 | 0.965 | 0.915 | 0.631 | 0.555 |
| `tweezers-cpl` | 0.771 | 0.746 | 0.986 | 0.967 | 1.060 | 1.011 |
| `flat-on-ruler-cpl` | 0.812 | 0.807 | 0.927 | 0.931 | 0.956 | 0.962 |

### Per subject, in words

**`bee-3-cpl` (299 frames) — nothing.** This is where selection should lose
worst: at any pixel only one or two frames of 299 hold that depth in focus, so
there is almost nothing for an estimator to average. It is also where the merge
pays its largest handicap — the coverage rescale drops 6.8% of the field and
upsamples it back. All three statistics land inside the noise null. **The
deepest stack in the corpus produced the smallest detail difference of any
subject.** That is the opposite of the prediction the `~1.2-1.8x` figure rests
on, and it is the single most important line in this table.

**`bee-1-cpl` (299) — S3 only, marginally.** +0.47 px against a 0.22 px null.
S1 and S2 do not corroborate it. One statistic out of three, at twice its own
null, is a hint, not a result.

**`leaf-2-cpl` (182) — a tie with the statistics pointing opposite ways.**
S2 says −0.36, S3 says +0.38, both about 1.5x their nulls. This is the stack
the README's noise measurement used, so the detail number now sits beside it:
**0.1546x the noise of one frame, and no measurable detail difference either
way.** The crop is the clearest picture of the whole result — the same leaf
venation resolved to the same fineness in both arms, with visibly more grain in
the argmax arm.

**`flowers-cpl` (176) — the statistics contradict each other, and the reason is
a defect in the baseline, not in the tool.** S1 says the merge is 0.49 px
finer; S3 says it is 2.06 px softer. Look at the crop before believing either.
`argmax-baseline` renders the smooth out-of-focus ground as **hard-edged
patchwork** — large blotches where the argmax elected different frames in
neighbouring regions with nothing to choose between them. S3 measures
correlation length, so it scores those invented blotch edges as fine structure
and reports the merge as soft. **Both statistics are being fooled by invented
structure, in opposite directions.** I do not report a detail number for
`flowers-cpl`. What I report is that this subject is where the merge's real
advantage lives, and no sharpness statistic will ever credit it: the merge
renders defocused ground as defocused ground.

**`tweezers-cpl` (100) — a tie, on the subject with the largest noise gap.**
σ(argmax)/σ(merge) = 2.68, the largest in the set, and S1's whole −0.47 is
inside its 0.49 null. The crops are, to my eye at 1:1, indistinguishable in
detail.

**`flat-on-ruler-cpl` (79) — selection wins, and all three statistics agree.**
S1 −0.48 (null 0.37), S2 −0.44 (null 0.25), S3 −0.38 (null 0.24). Every one of
them exceeds its null and every one has the same sign, on every tile for S1 and
S2. High contrast, machined detail, shallow relief, the shallowest stack in the
set: at any pixel there is one unambiguously sharpest frame, selection finds
it, and the merge's coverage rescale then costs it about a third of a pixel.
**This is the honest result the brief anticipated, and it is the only
unambiguous win in the table.**

### Why the merge does not win where it was expected to

Two measured reasons, and neither is a defect in estimation as an idea.

1. **The merge pays a resampling tax the baseline never pays.** `stack` aligns
   and then scales the field of view so every frame covers every pixel — 0.9236
   to 0.9728 across these six, so up to 7.6% of the field discarded and
   upsampled back. Charging the baseline the same tax (the `argmax_geom` column
   in `measure-*.json`) moves S1 on the bees from 0.760 and 0.794 to **0.991
   and 0.996** — from an apparent 24% deficit to a dead heat. The merge is
   spending on coverage roughly what it might be gaining on estimation.

2. **The estimator degenerates to selection almost everywhere.** On
   `flat-on-ruler-cpl` the estimator arm reports `mean n_eff 1.142` with
   **86.07% of pixels at n_eff = 1**. Where n_eff is 1 the merge *is* selection,
   so it cannot beat selection. The README says this outright — "where one frame
   is unambiguously sharpest it degenerates to selection" — and the detail
   numbers are what that sentence looks like when it is measured.

## The binary

**sha256 `4c0c6022adf0a5e325275e7ffea010d54b6b17925fe947b03a0a816e72ff7840`**,
9 385 984 bytes, built from committed tree `b9b6921e` extracted with
`git archive` into `C:\dev\strehl-scratch-THESIS` and built there (the repo
root fails with `Access is denied` under tonight's concurrency).

**Both arms of every subject came from that one binary.** It is not asserted —
`render_arms.ps1` writes the hash into a provenance sidecar per arm and
`measure.py` refuses to run a subject whose two sidecars disagree.

Both arms are **linear, binned, camera-native RGB, 3520 x 2344**, one output
pixel per 2x2 CFA quad. `--srgb` was never passed to either arm and no statistic
touches a `.png`. The two arms are on the same geometry because
`argmax-baseline` only writes binned output and `stack` defaults to binned, so
neither arm was resampled to meet the other.

**Every number is green-plane only.** `stack` applies the lateral-CA correction
and `argmax-baseline` does not; CA correction moves R and B radially against G
and leaves G alone. Measuring green removes that confound outright rather than
arguing it is small.

## Commissioning: what I fed the statistics, and what died

Two statistics were **killed by their own commissioning before they could
vote**. Both would have produced confident-looking numbers.

* **P99(|grad|)/P75(|grad|), a gradient sparsity ratio.** Disqualified: it
  **rises on blur**, by 1.39x at σ = 0.8 px and **5.13x** on a synthetic chirp
  with ground-truth blur. Blur erases the body of a texture faster than its
  strongest edges, so the tail ratio grows as the image softens. It would have
  scored the softer arm as the sharper one.
* **Density of noise-significant Laplacian-of-Gaussian zero crossings.**
  Disqualified: it also **rises on blur**, 12.6x on the ground-truth chirp. Its
  significance threshold came from a median noise estimate taken from the image
  itself, and on a finely detailed image that estimate is dominated by real
  detail rather than noise. The more the image resolves, the higher its own bar
  goes. Self-calibration turned into self-defeat.

Three survived to be used, and one of those carries a stated bias.

| statistic | what it is | blur plant | noise null |
| --- | --- | --- | --- |
| **S1 `norm`** | mean \|laplacian\| / local RMS contrast — ORCH's, imported not copied | passes: 0.57x at σ0.8, 0.28x at σ1.5, 0.24x on ground truth | **FAILS**: +4.7% at 5% added noise, **+33%** at 15% |
| **S2 `f50`** | noise-floor-subtracted spectral half-energy frequency, cyc/px | passes: 0.81x, 0.62x, 0.67x | passes: ≤ +0.2% at every level, +0.00% on impulses |
| **S3 `acf`** | 1 / half-height correlation length of the detail field, 1/px | passes: 0.69x, 0.49x, 0.40x | passes: ≤ +0.1% at every level |

**S1's failure is not a footnote, it is a load-bearing fact.** `norm` rises on
noise, and `argmax-baseline` is the noisier arm — 1.253x single-frame noise
against the merge's 0.890x in the README, and 1.06x to 2.68x measured directly
here. So S1 leans toward selection for free. It is kept because it is ORCH's
validated instrument and is strongly blur-monotone, and because a statistic
biased *against* the hypothesis is worth more than one biased for it.

S2 and S3 are **contrast-invariant by construction** — multiply the image by
any constant and neither moves — so neither can be accused of dividing out the
very thing blur destroys, which is the failure mode ORCH's control exists to
catch. S3 is related to S2 by Wiener-Khinchin and I say so rather than selling
it as independence; the *estimators* differ and do not fail the same way. S2
subtracts a flat floor read off the top of the spectrum, S3 never estimates a
floor and instead extrapolates through a corner noise cannot reach.

### The plant that caught them and the null that did not move them

The **plant**: a real 800 px tile from a delivered render, Gaussian-blurred by
0.8 px, and a synthetic radial chirp at ground-truth blur 1.2 px. S2 fell to
0.81x and 0.67x; S3 to 0.69x and 0.40x. Both killed candidates *rose* on the
same plant — that is what the plant was for.

The **null**: the same tile plus white noise at 1%, 5% and 15% of tile σ, and
0.05% impulse noise chosen to match `argmax-baseline`'s own measured index
speckle rate on `flat-on-ruler-cpl` (0.049%). S2 moved by at most +0.2%; S3 by
at most +0.1%. S1 moved by +33%.

## Commissioning the chain, not just the statistics

Near-parity is also what a chain that has quietly gone inert reports. So the
whole pipeline — registration, site selection, native-pixel extraction,
inversion — was fed subjects whose answer was known before it ran:

| control | S1 | S2 | S3 |
| --- | ---: | ---: | ---: |
| identity (argmax arm **is** the merge arm) | **1.000** | **1.000** | **1.000** |
| argmax arm = merge blurred 0.8 px | 3.074x | 1.074x | 1.140x |
| argmax arm = merge blurred 1.5 px | 6.490x | 1.156x | 1.276x |

Identity returns exactly 1.000 on all three, on all six tiles, so the chain
does not invent a difference out of registration slop. The blurs are seen, and
seen monotonically.

That table also shows why raw ratios are unreadable: a plainly visible 0.8 px
blur moves S1 by 3.07x and S2 by 1.07x. So every statistic is converted to
**equivalent Gaussian blur in pixels** by blurring one arm's tile until its
statistic meets the other's. On the controls the inversion recovers the planted
blur exactly — 0.000, 0.800, 1.498/1.500 px on all three statistics — and on a
finer ladder it is exact from **0.20 px** upward and returns 0.000 below 0.10.
**The instrument resolves 0.2 px. The subject differences are 0.4 px against
0.2-0.5 px nulls.**

## The yardstick that decides the result

`limits.py` plants **no blur at all** and instead adds white noise to a merge
tile until its σ matches that subject's argmax arm, then asks the same
inversion what it sees:

| subject | σ ratio | S1 | S2 | S3 |
| --- | ---: | ---: | ---: | ---: |
| `bee-3-cpl` | 1.064 | −0.34 | −0.25 | −0.23 |
| `bee-1-cpl` | 1.078 | −0.35 | +0.23 | +0.20 |
| `leaf-2-cpl` | 1.110 | −0.36 | −0.26 | −0.24 |
| `flowers-cpl` | 1.625 | −0.45 | −1.50 | −1.32 |
| `tweezers-cpl` | 2.681 | −0.49 | +0.26 | −0.25 |
| `flat-on-ruler-cpl` | 1.381 | −0.37 | +0.25 | −0.25 |

**S1 reports −0.34 to −0.49 px for a pure noise difference with zero blur. The
S1 column in the headline table is −0.43 to −0.48 px on five of six subjects.
S1's entire apparent result is the arms' noise, restated in pixels.** It is not
a detail measurement at all, and reporting `0.77x` from it — which is what
ranking the arms on `norm` alone would have produced on five subjects — would
have been the same class of error as ranking 26 masters on raw \|laplacian\|
and concluding the merge fails on flowers.

## Site selection

Sites were chosen on the **mean of both arms**, never on one arm, then cut from
each arm's own native pixels at integer offsets. The registration locates the
site; it never resamples the thing being measured.

A single global affine cannot register these two arms, and **that is a property
of the baseline**: `stack` aligns every frame to one reference so its output has
one consistent geometry, while `argmax-baseline` does not align at all, so each
output pixel carries the geometry of whichever frame won there. Where the stack
drifted, neighbouring regions of the argmax render sit on different grids.
Global ECC therefore only gets within ~72 px and each site is then located by
normalised cross-correlation; median site match was **0.79 to 0.97** and one
site out of 36 was dropped as unmatchable.

The mean rule has a demonstrated hazard, found on `flowers-cpl`: the argmax
patchwork is the highest-\|laplacian\| thing in a very low-contrast frame and
nominated sites holding no real detail in either arm. So everything was
re-measured under a second rule — score sites on the **pixelwise minimum** of
the two arms' \|laplacian\|, so a site must carry detail in *both* arms to be
nominated, which no single arm's invented structure can achieve. **Every
conclusion is unchanged** (the two ratio tables above). The flowers
contradiction survives both rules, which is why it is reported as a
contradiction rather than explained away as a site artifact.

## Crops — see it, do not take my word

1:1, 512 px, native pixels, **one shared display stretch computed from both
arms together** so neither is flattered. These are for looking at; no number in
this report comes from a `.png`.

| what it shows | path |
| --- | --- |
| **The whole result in one frame.** Leaf venation resolved identically; argmax visibly grainier. | `C:\dev\strehl-out\BUILD-THESIS\crops\leaf-2-cpl-siteMIN\tile1-SIDEBYSIDE-merge-left-argmax-right.png` |
| **The baseline inventing structure.** Smooth defocused ground; merge renders a gradient, argmax renders hard-edged patchwork. This is what S3 scored as detail. | `C:\dev\strehl-out\BUILD-THESIS\crops\flowers-cpl\tile0-SIDEBYSIDE-merge-left-argmax-right.png` |
| Bee hair at 299 frames, plus argmax background blotching at top right | `C:\dev\strehl-out\BUILD-THESIS\crops\bee-3-cpl\tile0-SIDEBYSIDE-merge-left-argmax-right.png` |
| Bee hair, well-registered site — the two arms are hard to tell apart | `C:\dev\strehl-out\BUILD-THESIS\crops\bee-3-cpl\tile3-SIDEBYSIDE-merge-left-argmax-right.png` |
| Machined detail, the one subject where argmax measurably wins | `C:\dev\strehl-out\BUILD-THESIS\crops\flat-on-ruler-cpl\tile0-SIDEBYSIDE-merge-left-argmax-right.png` |
| Tweezers — indistinguishable at 1:1, and the numbers agree | `C:\dev\strehl-out\BUILD-THESIS\crops\tweezers-cpl\tile0-SIDEBYSIDE-merge-left-argmax-right.png` |
| Chain control: identity, must be and is pixel-identical | `C:\dev\strehl-out\BUILD-THESIS\crops\CTRL-identity\` |
| Chain control: a planted 0.8 px blur, for calibrating your eye | `C:\dev\strehl-out\BUILD-THESIS\crops\CTRL-blur0.8\` |

Every subject has six sites under both site rules; the table lists the ones
worth opening first.

## Measured vs assumed

**Measured.** The six renders and their per-arm provenance. The green-plane
detail statistics at 36 matched sites. The equivalent-blur conversion and its
0.2 px resolution floor. The per-subject noise-null yardstick. The per-arm noise
σ by a robust median estimator (σ ratios 1.06-2.68, which independently
corroborate the README's 1.253x / 0.890x). The commissioning of five candidate
statistics and the disqualification of two. The whole-chain identity and blur
controls. That the estimator degenerates to n_eff = 1 on 86.07% of
`flat-on-ruler-cpl` pixels. That every conclusion survives a second site rule.

**Assumed.**

* That `argmax_geom` — magnifying an argmax tile by 1/s through an OpenCV
  bicubic and back — costs about what the merge's own coverage rescale costs.
  The merge resamples each *input frame* once with CatmullRom; this resamples
  the *output* once with a Keys bicubic (a = −0.75 against CatmullRom's −0.5).
  It is an estimate of the tax, labelled as one. The bee result that the tax
  accounts for the entire S1 gap rests on it.
* That the six subjects span the corpus's difficulty range. They were chosen on
  ORCH's detail-per-contrast ranking to span deep-stack occlusion, the README's
  noise subject, high-contrast machined detail and the lowest-contrast subject,
  but six of 26 is a sample.
* That green-plane detail stands in for detail. Defensible on a CFA sensor
  where green is half the samples, but it is a stand-in.

**What I could not verify.**

* **I could not verify any of this myself, by rule.** Every number here needs an
  independent pass. The scripts are deterministic and seeded.
* **I could not measure the estimator arm on `leaf-2-cpl`.** `stack --merge
  estimator` rendered fine (182/182 frames placed, sane pixel statistics) but
  ECC registration against the argmax arm collapsed to 0.0815 and five of six
  sites failed the match threshold. Its numbers are in `measure-mean.json` and
  **should be ignored**. The estimator arm on `flat-on-ruler-cpl` registered
  normally and agrees with the pyramid arm (S1 0.822 vs 0.812, S2 0.964 vs
  0.927, S3 1.012 vs 0.956), so on that one subject the two merge backends give
  the same answer against selection. One subject is not a result about the
  estimator backend.
* **I could not put a number on the patchwork.** The `flowers-cpl` crop shows
  `argmax-baseline` inventing hard-edged structure in defocused ground, and it
  is the clearest quality difference in the entire set, but no sharpness
  statistic I commissioned measures it — two of them scored it as *detail*, in
  opposite directions. Measuring it needs a defect statistic, not a detail
  statistic, and I did not build one.
* **I could not separate estimation from alignment.** `argmax-baseline` does not
  align and the merge does. On a stack with real drift the merge's alignment is
  a genuine advantage and its coverage rescale a genuine cost, and this design
  cannot hold either fixed. Both arms are measured exactly as they ship, which
  is the honest comparison of the shipped tool but not a clean isolation of the
  estimator.

## Reproducing

```powershell
git archive b9b6921e | tar -x -C C:\dev\strehl-scratch-THESIS
cd C:\dev\strehl-scratch-THESIS; cargo build --release
cd <repo>
pwsh -NoProfile -Command "& '.\experiments\BUILD-THESIS\render_arms.ps1' -Subjects @('bee-3-cpl','bee-1-cpl','leaf-2-cpl','flowers-cpl','tweezers-cpl','flat-on-ruler-cpl')"
python experiments\BUILD-THESIS\commission.py C:\dev\strehl-out\BUILD-THESIS\renders\flat-on-ruler-cpl\merge.tif C:\dev\strehl-out\BUILD-THESIS\renders\flat-on-ruler-cpl\argmax.tif
python experiments\BUILD-THESIS\build_controls.py leaf-2-cpl
python experiments\BUILD-THESIS\measure.py CTRL-identity CTRL-blur0.8 CTRL-blur1.5
python experiments\BUILD-THESIS\measure.py bee-3-cpl bee-1-cpl leaf-2-cpl flowers-cpl tweezers-cpl flat-on-ruler-cpl
python experiments\BUILD-THESIS\measure.py --rule=min bee-3-cpl bee-1-cpl leaf-2-cpl flowers-cpl tweezers-cpl flat-on-ruler-cpl
python experiments\BUILD-THESIS\blureq.py C:\dev\strehl-out\BUILD-THESIS\measure-subjects.json
python experiments\BUILD-THESIS\limits.py
python experiments\BUILD-THESIS\summarize.py
```

`commission.py` exits non-zero — that is correct and is the S1 noise-null
failure documented above, not a broken run.

Data: `C:\dev\strehl-out\BUILD-THESIS\SUMMARY.json`, `measure-*.json`,
`blureq-*.json`, `limits.json`, `commission.json`, `renders\*\*.err`.

## What the README should say

The `~1.2-1.8x` detail figure is `ARGUED` and this measurement does not support
it. A replacement that is defensible on this evidence:

> On resolved detail, measured green-plane and camera-linear at 36 matched sites
> across six subjects from one binary, the shipped merge and `argmax-baseline`
> are **indistinguishable to within 0.5 px of equivalent Gaussian blur**, which
> is the size of the difference the same instrument reports for the two arms'
> noise gap alone. Selection wins outright on exactly one subject —
> `flat-on-ruler-cpl`, high contrast and shallow relief, where all three
> statistics agree at about 0.4 px. The merge's advantage on this corpus is
> **noise and the absence of invented structure, not fineness**.

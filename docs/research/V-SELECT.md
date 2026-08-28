# V-SELECT — does the shipped merge choose incoherently, and does that get worse with depth?

Lane V-SELECT. Companion to [`V-DRIFT.md`](V-DRIFT.md), which refuted alignment
*accumulation* as the cause of the depth-dependent quality collapse. This document
tests the hypothesis that replaced it.

Numbers quoted against commit `a9ed52cb`. Every merge here was produced by the
pinned binary at `C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe`,
SHA-256 prefix `44C2F2CD2E5B2894`, verified at the top of every run. Subjects are
`flower-bud-alone-cpl` (205 frames) and `bee-3-cpl` (299 frames). All merges
`--linear-srgb --demosaic`, shipped `pyramid` backend unless an arm says otherwise.

---

## Verdict

**The prediction as stated fails. The mechanism behind it is real but small, and
the two are not the same claim — which is the point of this document.**

The prediction under test was: *the merge's per-pixel frame choice should disagree
between two independent half-stacks at a rate far above what the scene justifies,
and that disagreement rate should rise with N.*

1. **REFUTED — the proposed signature.** The incoherent part of half-stack
   disagreement does not rise with N. As a fraction of delivered detail it
   *falls* — 0.86× on flower across N=35→205, 0.69× on bee across N=50→299. In
   absolute amplitude it is flat: 1.19× and 1.02× respectively. This holds on
   both subjects, both ladder designs, and both normalisations. **A fleet that
   validated the exponent fix by watching half-stack disagreement would have seen
   nothing, and concluded wrongly.**

2. **SUPPORTED, mildly — the mechanism.** The shipped weighting does become less
   decisive with depth, measured directly on the shipping backend. Against
   `--pyramid-select hard-max` on the same stack at the same N, which cancels the
   cloud-width confound (§7), headroom grows **1.13× on flower** (50.9 → 57.5
   across N=18→205) and **1.20× on bee** (55.5 → 66.5 across N=25→299). Both
   subjects, same direction, the direction dilution predicts.

   The raw confidence *level* moves the other way — 761.8→728.4 on flower,
   458.2→418.5 on bee — but that reading is confounded by the cloud widening with
   N, and §7 is the controlled one. The controlled reading is what stands.

3. **Its size was understated here, and I am correcting my own number.** §7
   measured headroom as a **whole-field mean**, and §12 shows that dilutes a
   region-confined effect **2.2×**. Resolved spatially, headroom in the flattest
   quartile — the support the 20–60 px plateau was convicted on — is the highest
   of any region on both subjects at both depths: **71.2 → 88.9** on flower and
   **88.9 → 97.3** on bee, against whole-field means of 50.9–66.5. That is **59%
   to 81% of the ~120-unit span** between argmax and `--pyramid-exponent 0.5`,
   not the 5.5–9.2% an earlier draft of this document claimed. **That claim is
   withdrawn.** The shipped merge hedges hard, and hardest exactly where the
   defect is.

   What does *not* change is the depth half. The flat quartile grows 1.25×
   (flower) and 1.09× (bee) — on bee, *slower* than the whole field. So the
   mechanism is large in level and modest in depth-growth, and it is the depth
   behaviour that the collapse to 0.180 / 0.060 needs explaining.

4. **The band and the support both had to be corrected first (§11).** Everything
   in §§3–4 was originally scored at 0.30–0.45 cyc/px — a period of 2.2–3.3 px —
   while the convicted plateau sits at 20–60 px, and on the 24 *most textured*
   tiles in the frame while the defect is flat-region mottle. Re-measured at
   0.02–0.08 cyc/px on the flat support, the refutation in (1) gets **stronger**
   (0.52× against 0.86×), and the leak calibration proved band-specific by a
   factor of **9.8×** — reusing it would have manufactured a result.

**But one thing does rise with depth steeply, and only on the collapse subject.**
The registration difference between two *independently solved halves* of
`bee-3-cpl` grows **1.93× to 2.15×** across every support tested, in the
convicted band, across N=50→299, with fitted shift 0.356→0.618 px. On
`flower-bud-alone-cpl` — where V-DRIFT §4 measured total corner drift at 0.715 px,
flat — the same quantity *falls*, on every support. This is not the accumulation
V-DRIFT refuted; it is solve-to-solve divergence, it behaves the way the collapse
behaves, it survived a content-blind support, and it is unowned. See §8 and §11.4.

**What this means for the fix in flight.** Nothing here says the
confidence-dependent exponent is a bad change; §12 says it targets a larger
effect than I first reported. It says two things about how to judge it. First, do
not validate it with a half-stack disagreement rate — that statistic is blind to
this, on every band and support tested. Second, measure any before/after **per
region, not as a whole-field mean**: a flat-region effect is diluted 2.2× by the
average, so a real improvement will look small and a regression at the borders
will look like nothing.

---

## What I measured versus what I assumed

**Measured.**
- Half-stack disagreement decomposed into a registration-explainable part and an
  incoherent remainder, on two subjects, at three depths each, on two ladder
  designs (§3, §4).
- The leak of a warp into the incoherent bin, calibrated on two plant families
  (§2), including the failed first calibration design.
- The shipped merge's per-pixel confidence, four depths per subject (§5).
- The confidence map's response to the pyramid's own selection knobs, both
  directions (§6).
- Headroom against `--pyramid-select hard-max` at both ends of each ladder (§7),
  which is the cloud-width-controlled reading and the one the verdict rests on.

**Assumed.**
- That two interleaved halves of a stack are exchangeable samples of the same
  scene. Checked, not assumed, via the `high_A/high_B` gate — and the check
  *rejected* the interleaved ladder's low-N rung on bee at 1.68× (§3).
- That the confidence map means what its CLI help says it means. Commissioned in
  §6, so this is measured for *direction and both-ways response* but assumed for
  *absolute interpretation*: I did not read `pyramid.rs` (build lane owns it).
- That `flower-bud-alone-cpl` exhibits the quality collapse. **It is not on
  record as doing so.** It was chosen because its alignment error is measured and
  tiny, making it the subject where alignment is excluded rather than argued.
  bee-3-cpl is the documented collapse subject and carries the result.

**Not measured.**
- The literal per-pixel frame-choice disagreement rate. It is not obtainable on
  the shipped backend at all — see §1.
- Any quality comparison against `enfuse` or `focus-stack`. Other lanes own that.
- Whether the incoherent level of ~1.0–1.5 is above "what the scene justifies".
  I have no reference merge, so I report the *trend with N*, which is what the
  prediction was about, and explicitly **refuse** the level claim (§4.3).

---

## 1. The literal prediction cannot be tested on the shipped merge

The prediction is about the merge's per-pixel frame choice. The tool has a flag
that reports exactly that, `--index-map`, "a 16-bit grayscale TIFF holding the
index of the frame that won pass one, per pixel". It is **refused under the
pyramid backend**, and the help says why:

> `--index-map` and `--n-eff-map` are both refused under `--merge pyramid`
> because the pyramid elects per band coefficient rather than per pixel, so no
> frame index and no frame count owns an output pixel.

This is not a missing feature. It is a statement that the quantity in the
prediction **does not exist** in the shipped merge. The pyramid elects per band
coefficient; there is no per-pixel winner to disagree about. Passing the flag
without `--merge estimator` silently gets you the estimator — the backend that
does not ship — so a harness testing the prediction the obvious way would measure
the wrong merge and never be told.

So the prediction has to be tested through what the merge *renders* (§3, §4) and
through the per-pixel trust artifact the pyramid *does* expose (§5).

---

## 2. Commissioning the half-difference decomposition

Two hypotheses predict that independently merged halves disagree, and they
predict different *shapes*. A registration difference between the halves is a
similarity warp, which to first order makes the half-difference a linear
combination of the half-sum's own gradients — **coherent**. A selection
difference renders the same pixel at a different focus, which is not a warp of
anything — **incoherent**.

So regress `D = A − B` onto the basis a similarity warp plus an exposure
difference spans, with `S = (A+B)/2`:

```
[ S, Sx, Sy, x*Sx + y*Sy, -y*Sx + x*Sy ]
  ^   ^^^^^^  ^^^^^^^^^^^  ^^^^^^^^^^^^^
gain  transl.    scale        rotation
```

`reg` is the fitted part's amplitude in the `high` band (0.30–0.45 cyc/px),
`sel` is the residual's, both as a ratio to `S`'s own amplitude in that band.
Partner tiles are located by integer-only NCC — sub-pixel resampling would add
blur to the quantity being measured — and the residual sub-pixel and scale
difference is left for the basis to absorb, which is what it is for.

### 2.1 The first commissioning design failed, and the failure set the method

The first ladder planted **integer** shifts of 1, 2 and 4 px. It reported:

| plant | total | reg | sel | sel/reg |
|---|---:|---:|---:|---:|
| shift 1 px | 1.5707 | 0.8670 | 0.9024 | 1.04 |
| shift 2 px | 2.7189 | 1.4400 | 2.8588 | 1.99 |
| shift 4 px | 1.9891 | 2.5427 | 3.0031 | 1.18 |

A pure registration error was landing **half its energy in the selection bin**.
The basis is a first-order Taylor model and the scoring band's period is only
2.2–3.3 px, so a 1 px shift is a third of a period — far outside the linear
regime. Had this been accepted, every `sel` in this document would have been
partly registration and the conclusion would have been unsupported.

The regime that matters is not 1–4 px: two halves of one stack register to a
fraction of a pixel. The ladder was rebuilt with **exact sub-pixel shifts by
Fourier phase ramp**, which adds no interpolation blur.

### 2.2 The commissioned instrument

Twelve 256 px sites on `d0.tif`. All values are band ratios; `fit shift` is the
translation the basis recovers, in px.

| plant | total | reg | sel | sel/reg | fit shift |
|---|---:|---:|---:|---:|---:|
| null (A vs A) | 0.00000 | 0.00000 | 0.00000 | – | 0.0000 |
| shift 0.05 px | 0.07146 | 0.04519 | 0.03260 | 0.721 | 0.0560 |
| shift 0.10 px | 0.14303 | 0.09036 | 0.06536 | 0.723 | 0.1120 |
| shift 0.20 px | 0.28700 | 0.18061 | 0.13205 | 0.731 | 0.2241 |
| shift 0.40 px | 0.58141 | 0.36015 | 0.27506 | 0.764 | 0.4493 |
| shift 0.80 px | 1.21924 | 0.70783 | 0.64444 | 0.910 | 0.9093 |
| blob-blur 0.1 | 0.47797 | 0.00187 | 0.47777 | 255.616 | 0.0021 |
| blob-blur 0.3 | 0.63930 | 0.00674 | 0.63919 | 94.816 | 0.0074 |
| blob-blur 0.6 | 1.10738 | 0.00876 | 1.10680 | 126.384 | 0.0062 |
| interp only (e=0) | 0.00000 | 0.00000 | 0.00000 | 0.000 | – |
| scale 0.2% | 0.13378 | 0.07962 | 0.10466 | 1.315 | – |
| scale 0.8% | 0.56473 | 0.31811 | 0.40865 | 1.285 | – |

The selection plant blurs a random fraction of the tile's area in blobs — same
scene, same geometry, locally different focus, at random locations, which is what
an incoherent choice does to an image. The scale plant exists because bee's halves
differ in coverage crop `k` by up to 1.4%; a *centred* scale change fits a
translation of zero, so the translation ladder cannot calibrate it. Its `e=0`
rung runs the identical bilinear path and reads **exactly 0.00000**, so the scale
leak is the scale and not the resampler.

Five checks, all PASS:

| check | result |
|---|---|
| null reads zero | 0.00e+00 total, 0.00e+00 select |
| shift ladder monotone in `reg`, above null | 0.0452 → 0.7078 |
| blob ladder monotone in `sel`, above null | 0.4778 → 1.1068 |
| fitted translation recovers planted dose | 13.7% worst case (want < 15%) |
| separation: blob's sel/reg vs shift's sel/reg | **129.7×** (want > 3×) |

The fourth check is the one that makes `shift_px` a measurement rather than a
reaction: the basis *recovers the planted translation*, not merely responds to it.

### 2.3 The leak is a calibration, not a caveat

Across the whole sub-pixel range the leak is a near-constant fraction of the
plant's own total (46%, 46%, 46%, 47%, 53%) and therefore proportional to `reg`:
sel/reg runs 0.72 → 0.91 for translation and 1.28–1.32 for scale. The worst ratio
over **both** families is **1.28**, and `halfmetric.py` subtracts `1.28 × reg`
from `sel` to form `sel_net`. Using the worst rather than the interpolated ratio
means the subtraction errs toward removing too much, so a surviving `sel_net`
understates the incoherent part rather than overstating it — the hostile
direction for the hypothesis this lane would otherwise be positioned to confirm.

---

## 3. The first ladder was confounded, and the gate caught it

The obvious depth ladder builds two halves by interleaving a subsampled set. That
locks the partner separation to the subsampling stride: at N=35 the two halves'
frames sit 6 apart in focus, at N=205 they sit 1 apart. A pixel can then disagree
for a reason that has nothing to do with the merge — at coarse sampling the
nearest in-focus frame available to half A is genuinely a different depth from the
one available to half B. That inflates the **low-N** end, which is the same
direction as a falling curve.

`flower-bud-alone-cpl`, interleaved ladder:

| set | N | half | sep | shift px | reg | sel_net | sel_abs | high_S | A/B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| n34 | 35 | 18 | 6 | 0.180 | 0.3875 | 1.5260 | 98.9 | 64.8 | 1.18 |
| n102 | 103 | 52 | 2 | 0.229 | 0.1967 | 1.4951 | 123.6 | 82.6 | 1.08 |
| n204 | 205 | 103 | 1 | 0.167 | 0.1304 | 1.3168 | 133.5 | 101.4 | 0.98 |

On `bee-3-cpl` the same design put the two halves' own high-band amplitudes at
**169.1 vs 100.5 — a ratio of 1.68** at the low-N rung. The halves were not
exchangeable samples of the same scene, so that row's disagreement is partly a
content difference and not a merge property. `halfmetric.py` now warns on any row
outside 0.80–1.25.

**This is why a fall on this ladder cannot refute the prediction**: the confound
inflates the low-N end and could mask a real rise. The ladder was replaced rather
than corrected.

---

## 4. The fixed-separation ladder — the primary result

For half-size M, take `A = src[0::S]` and `B = src[1::S]` with `S = len(src)//M`.
Both halves span the full depth, sample it with the same stride, are disjoint, and
**every partner pair is adjacent in focus at every M**. Focus-sampling separation
is held constant by construction; only the number of frames competing at each
pixel changes, which is exactly what the dilution prediction is about.

### 4.1 `flower-bud-alone-cpl` — the subject where alignment is excluded

| set | N | half | sep | kA | kB | shift px | reg | sel_net | sel_abs | high_S | A/B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| s12 | 35 | 18 | 1 | 0.9973 | 0.9970 | 0.259 | 0.2177 | 1.5294 | 112.1 | 73.3 | 1.15 |
| s4 | 103 | 52 | 1 | 0.9973 | 0.9972 | 0.173 | 0.1443 | 1.4357 | 128.0 | 89.1 | 1.02 |
| s2 | 205 | 103 | 1 | 0.9972 | 0.9973 | 0.167 | 0.1304 | 1.3168 | 133.5 | 101.4 | 0.98 |

Incoherent fraction **0.86×**, incoherent absolute **1.19×**, registration
**0.60×**, fitted inter-half shift **0.65×** (0.259 → 0.167 px), coherence-blind
single-half high-band amplitude **1.28×** (98.4 → 125.7).

### 4.2 `bee-3-cpl` — the documented collapse subject

| set | N | half | sep | kA | kB | shift px | reg | sel_net | sel_abs | high_S | A/B |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| s12 | 50 | 25 | 1 | 0.9217 | 0.9241 | 0.356 | 0.3176 | 1.3816 | 168.6 | 122.0 | 1.14 |
| s4 | 150 | 75 | 1 | 0.9277 | 0.9340 | 0.444 | 0.4579 | 1.2149 | 193.0 | 158.9 | 1.10 |
| s2 | 299 | 150 | 1 | 0.9228 | 0.9359 | 0.618 | 0.6044 | 0.9519 | 172.2 | 180.9 | 1.01 |

Incoherent fraction **0.69×**, incoherent absolute **1.02×**, registration
**1.90×**, fitted inter-half shift **1.74×** (0.356 → 0.618 px), coherence-blind
single-half high-band amplitude **1.37×** (169.2 → 231.9).

### 4.3 Reading these tables, including what they do not say

**The normalisation matters and both are reported, because on bee they disagree.**
`sel_net` is a ratio to the half-sum's own detail, and that denominator grows
1.48× on bee across the ladder. The falling *fraction* is therefore mostly the
denominator, and the honest statement is the absolute one: **1.02× — flat.** The
same discipline applied to flower gives 1.19×, a mild rise that tracks the 1.28×
rise in delivered detail.

**Neither reading supports the prediction.** The incoherent component does not
rise with N faster than the detail it accompanies, on either subject.

**REFUSED: the level claim.** `sel_net` sits at 1.0–1.5, meaning the incoherent
residual's high-band amplitude is comparable to the half-sum's own — larger than
the 60%-area blob plant reads (1.107). That looks alarming and I will not quote it
as evidence of a defect, because I have no reference for what two halves of a
stack *should* disagree by. Two halves contain different photon-noise
realisations and different focus samples; some incoherence is mandatory. The
prediction was explicitly about a rate "far above what the scene justifies", and
**I did not build the reference merge that would establish what the scene
justifies.** The trend with N is measured; the level is not interpretable.

---

## 5. The direct test: does the shipped merge stop committing as N grows?

`--confidence-map` is the per-pixel trust artifact the pyramid *does* produce.
Its CLI help states the polarity and the failure mode outright:

> how centrally the output sits inside the cloud of aligned observations, in
> milli-units. **Low is good** ... Electing a frame puts the output at an extreme
> of the observations and reads near 0. **Averaging frames that disagreed puts it
> dead centre and reads near 1000, which is what the veiled-detail failure looks
> like from the inside.**

Dilution — the winner's share falling toward an average as near-ties multiply
with N — predicts this **rises** with N. Coverage is held constant across the
ladder (`src[::S]`, whole depth, varying density), so only the count of competing
frames changes.

`flower-bud-alone-cpl`:

| N | k | mean | median | p90 | frac > 500 |
|---:|---:|---:|---:|---:|---:|
| 18 | 0.9973 | 761.8 | 889.0 | 1000.0 | 81.14% |
| 52 | 0.9973 | 746.2 | 923.0 | 1000.0 | 80.05% |
| 103 | 0.9972 | 737.3 | 893.0 | 990.0 | 80.32% |
| 205 | 0.9971 | 728.4 | 878.0 | 976.0 | 80.01% |

`bee-3-cpl`:

| N | k | mean | median | p90 | frac > 500 |
|---:|---:|---:|---:|---:|---:|
| 25 | 0.9217 | 458.2 | 400.0 | 960.0 | 42.81% |
| 75 | 0.9277 | 425.6 | 347.0 | 933.0 | 42.40% |
| 150 | 0.9228 | 417.7 | 347.0 | 933.0 | 41.48% |
| 299 | 0.9321 | 418.5 | 355.0 | 930.0 | 41.85% |

**It falls on both, then flattens.** Across an 11.4× change in N on flower the
mean moves −33.4 units, *toward* commitment. The hedged fraction is pinned within
1.1 points of constant on both subjects across the whole ladder.

**Do not read this as refuting dilution.** It is the uncontrolled reading.
Confidence is a centrality measure against a cloud that widens as N adds more
badly-defocused frames, and a wider cloud pushes *any* electing merge's reading
down without its behaviour having changed. §7 controls for that by differencing
two arms on the same stack, and the controlled answer is the opposite of this
one. This table is reported because it is what the instrument says before the
control, and because the gap between the two readings is the whole reason the
control exists.

Absolute levels are not comparable between subjects — flower's 728–762 against
bee's 418–458 is a scene difference, not a merge difference. Only within-subject
depth trends are read here, and only after §7.

---

## 6. Commissioning the confidence map, both ways

A flat curve is also what a dead instrument produces, so §5 is worthless until
the map is shown to respond to commitment in both directions. The pyramid exposes
the knobs that set exactly this, so the plant is the real mechanism rather than a
synthetic stand-in. One fixed N (52 frames of flower), so no depth is in play.

| arm | mean | median | frac > 500 |
|---|---:|---:|---:|
| `--pyramid-select hard-max` (argmax, one frame wins) | 691.3 | 885.0 | 74.46% |
| `--pyramid-exponent 4.0` (sharper, toward a winner) | 722.9 | 885.0 | 77.68% |
| **shipped default** | **746.2** | **923.0** | **80.05%** |
| `--pyramid-exponent 0.5` (flatter, toward an average) | 811.6 | 923.0 | 86.77% |

| check | result |
|---|---|
| exponent 4.0 below default | 722.9 < 746.2 PASS |
| exponent 0.5 above default | 811.6 > 746.2 PASS |
| hard-max below default | 691.3 < 746.2 PASS |
| both ways: one knob, opposite directions, opposite responses | 811.6 > 722.9 PASS |

The both-ways check is the one that matters. A statistic that only moved under
damage would pass a degradation-only test trivially; `--pyramid-exponent 0.5`
plants a deliberate move *toward* the averaging the dilution hypothesis is about,
and the map scores it as such.

**The calibration this provides.** The knob's full span here is 691.3 → 811.6, or
120.3 units. That is the scale against which every depth effect in this document
is measured: §7's headroom growth of 6.6 units (flower) and 11.0 (bee) is 5.5% and
9.2% of it. Without this span the headroom numbers would be bare differences with
no sense of whether they are large. For further scale, moving the exponent from
the default 1.0 to 4.0 costs 23.3 units, so the whole depth effect on flower is
about a quarter of what a 4× exponent change does at fixed N.

---

## 7. The cloud-width control

Confidence is a centrality measure against a cloud that is not a fixed yardstick.
As N grows the stack contributes more badly-defocused frames, the cloud widens,
and an output that elects one frame sits further out on a wider cloud — reading
lower — without the merge having changed behaviour. A falling curve could
therefore be an artifact, and §5 alone cannot exclude it.

The control is to read the *distance between two arms on the same stack at the
same N*, where cloud width cancels:

```
headroom(N) = confidence(shipped default) − confidence(hard-max)
```

Dilution requires headroom to **grow** with N: the shipped weighting's winner
share falls toward an average while argmax stays fully committed by construction.

| subject | N | default | hard-max | **headroom** | frac>500 default | frac>500 hard-max |
|---|---:|---:|---:|---:|---:|---:|
| flower | 18 | 761.8 | 710.8 | **+50.9** | 81.14% | 76.06% |
| flower | 205 | 728.4 | 670.9 | **+57.5** | 80.01% | 74.22% |
| bee | 25 | 458.2 | 402.7 | **+55.5** | 42.81% | 37.19% |
| bee | 299 | 418.5 | 352.0 | **+66.5** | 41.85% | 35.53% |

**Headroom grows on both subjects: 1.13× on flower, 1.20× on bee.** That is the
direction dilution predicts, on the controlled statistic, on both subjects
independently. The mechanism is real and this is the measurement that shows it.

Note that it points the *opposite* way to the raw levels in §5, and this is why
the control was necessary: both arms' absolute confidence falls with N (the cloud
widening), but the shipped weighting falls *less* than argmax does, so the gap
between them opens. Reading §5 alone would have refuted dilution incorrectly.

**The size, stated in the units the knobs provide — and superseded by §12.** §6
measures the pyramid's full commitment axis at ~120 units (`hard-max` 691.3 to
`--pyramid-exponent 0.5` 811.6, on flower at N=52). The whole-field depth effect
is +6.6 units on flower and +11.0 on bee, or 5.5% to 9.2% of that span.

**Do not quote those percentages as the mechanism's size.** They are the size of
the *depth growth* of a *whole-field mean*, and §12 shows that mean dilutes a
region-confined effect by 2.2×. Measured on the support where the defect was
convicted, headroom is 71–97 units, or 59–81% of the same span. The two readings
answer different questions and only the §12 one describes how hard the shipped
merge is hedging.

**A caveat I cannot close.** Headroom is measured against argmax *on the same
weighting family*. If the pyramid's per-band exponent ramp already behaves
differently at depth for reasons unrelated to near-tie multiplicity, this
statistic cannot tell that apart from dilution. Separating them needs the merge's
internal weights, which requires reading `pyramid.rs` — owned by the build lane
and out of scope here.

**Run discipline.** The first bee headroom run failed at N=299 with `decode failed
for ...DSC00023.ARW: The system cannot find the file specified` after the default
arm of the same N had already succeeded. Two concurrent instances of
`headroom.py` shared one scratch root and the first to finish removed the other's
frames mid-merge. The scratch root is now per-subject; the numbers above are from
the re-run. Recorded because a partial result there would have been a headroom
computed from arms measured on different frame sets.

---

## 8. What rises with depth, and it is not selection

One quantity in §4 rises with depth, and only on the collapse subject: the
**registration difference between two independently solved halves**.

| subject | fitted inter-half shift, shallow → deep | `reg` |
|---|---|---|
| `flower-bud-alone-cpl` (N=35 → 205) | 0.259 → 0.167 px (0.65×) | 0.60× |
| `bee-3-cpl` (N=50 → 299) | **0.356 → 0.618 px (1.74×)** | **1.90×** |

The coverage crops diverge in step: bee's half pair goes from `k` = 0.9217/0.9241
(0.0024 apart) to 0.9228/0.9359 (**0.0131 apart**, a 1.4% scale difference, ~33 px
across the frame). flower's stay within 0.0003 at every depth.

**This is not the hypothesis V-DRIFT refuted.** V-DRIFT killed *accumulation
along the chain* — error compounding frame to frame — and that refutation stands
on its own evidence (equidistant windows differing 2.92×, held-out/cycle-floor
flat at ~4.6×). What §4 shows is different: two independent solves of the same
deep stack land on measurably different geometry, and that divergence grows with
depth on bee while shrinking on flower. More frames should constrain a solve
*better*, so this is the opposite of the expected direction.

I am not claiming this causes the collapse. I am recording that it is the only
measured quantity here that behaves the way the collapse behaves — worse with
depth, on the subject where the collapse is documented, absent on the subject
where it is not — and that **nobody owns it**. It is a solver-stability question,
not a merge question, and it would not be fixed by the exponent change.

Two things must be checked before anyone acts on it, and I did not do either:
whether the divergence is a property of the solve or an artifact of the halves
being different frame sets, and whether 0.618 px of inter-half disagreement is
enough to matter at 0.30–0.45 cyc/px.

**Caveat on the scale leak at bee's deep rung.** The leak calibration was planted
at up to 0.8% scale; bee's deepest pair carries 1.4%. The sel/reg leak ratio was
flat across the planted range (1.315 at 0.2%, 1.285 at 0.8%), so extrapolation is
mild, but bee's deep rows are the extrapolated ones and the `reg` values there
are the numbers most exposed to it.

---

## 9. On the caveat that points the other way

The standing note is that if detail is merely incoherent rather than absent, it is
present in the delivered image, the 2.017 overstates the damage, and the published
noise figures are biased against us — because incoherent detail lands in the
half-difference and is counted as noise.

This lane's coherence-blind companion speaks to that directly. **One half's own
high-band amplitude rises with N on both subjects: 1.28× on flower, 1.37× on bee.**
That statistic contains no half-split at all, so no amount of agreement or
disagreement between halves can move it. A deep merge is not returning less
high-frequency content than a shallow one on these subjects.

That is not a quality claim and must not be read as one. V-DRIFT §8 measured the
hazard precisely: planted misregistration *raises* band amplitude 1.82×, because
ghosting adds high-frequency energy and stops noise cancelling. Rising high-band
amplitude is consistent with more real detail and equally consistent with more
ghosting — and §8 above shows bee's inter-half registration divergence growing
over the same range. **The two readings cannot be separated by this instrument**,
which is exactly why the number is offered as a coherence-blind companion and not
as evidence of quality.

---

## 10. What would change my mind

- **A reference merge.** Running `enfuse` or the `estimator` backend through the
  identical half-stack pipeline would establish what two halves *should* disagree
  by. If a reference merge's `sel_net` were far below strehl's at matched N, the
  level claim I refused in §4.3 would become quotable and the picture could
  change. This is the single most valuable follow-up and it is buildable with the
  V-SPEED enfuse pipeline.
- **A subject where the collapse and the incoherence rise together.** Two
  subjects is thin. `113MSDCF` and `119MSDCF` are the subjects with published
  scene ratios and neither was run here.
- **Reading `pyramid.rs`.** I tested the confidence map's *response*, not its
  definition, and I measured headroom against argmax within the same weighting
  family. If the pyramid's per-octave exponent ramp behaves differently at depth
  for reasons unrelated to near-tie multiplicity, §7 cannot separate that from
  dilution. The merge's internal weights would settle it; the build lane owns
  that file.
- **A headroom ladder with more than two rungs.** §7 has two points per subject,
  so it establishes a direction and a magnitude but not a shape. If headroom
  grows faster than linearly in N it would matter a great deal at 299 frames and
  I would not see it from two points.
- **A depth ladder past 299.** Every rise measured here is sub-linear; a
  mechanism that only bites past some N would not appear.

---

## 11. The instrument was measuring the wrong band and the wrong support

This section exists because the fleet reported that the falsification lane
self-caught a defect **its own self-test missed, because the test asserted only
the mean of a field whose defect was at the borders**, and asked every lane to
check its harness for that shape. Mine had it twice.

**Gap one: the wrong band.** Everything in §§3–4 was scored at
`tri.BANDS["high"]` = 0.30–0.45 cyc/px, a period of **2.2–3.3 px**. The defect
the fleet has convicted is a plateau at **20–60 px**, with L3 holding 54.3% of
plateau area and L4 36.5%. Those are different worlds: the convicted band is
roughly ten times coarser than the band I measured in, and `high` does not reach
it at all. `tri.BANDS["low"]` = 0.02–0.08 cyc/px (period 12.5–50 px) covers it.

**Gap two: the wrong support.** `pick_sites` ranks tiles by mid-band amplitude
**descending** and keeps the top 24. That is correct sampling for a sharpness
question and precisely wrong for this one: the convicted defect is *flat-region*
mottle, so an instrument that samples the 24 most textured tiles in the frame is
looking everywhere except where the defect was convicted.

Neither gap returns "no effect". Both return **no information**, and in this
document's output the two were indistinguishable.

### 11.1 The calibration does not transfer, and that is measurable

The leak ratio — how much apparent selection a pure registration error
manufactures — is a phase error, `2·pi·f·d`, so it scales with the scoring
frequency. Re-running `commission_half.py --band low`:

| band | period | separation | worst leak ratio |
|---|---|---:|---:|
| `high` 0.30–0.45 cyc/px | 2.2–3.3 px | 129.7× | **1.28** |
| `low` 0.02–0.08 cyc/px | 12.5–50 px | 214.7× | **0.13** |

A 9.8× fall for a ~10× fall in centre frequency, which is what the phase argument
predicts and is therefore a check on the calibration rather than just an output
of it. **Carrying 1.28 down to the low band would have subtracted about ten times
the real leak and could have manufactured a negative `sel_net` out of nothing.**
`leak_ratio()` now refuses to run on an uncalibrated band rather than borrowing
one.

### 11.2 Two supports fail commissioning, and are reported as failing

| band | support | null | monotone `reg` | monotone `sel` | dose recovery | separation |
|---|---|---|---|---|---:|---:|
| low | `detail` | PASS | PASS | PASS | **13.7% PASS** | 214.7× PASS |
| low | `flat` | PASS | PASS | PASS | **22.9% FAIL** | 175.4× PASS |
| low | `grid` | PASS | PASS | PASS | **19.6% FAIL** | 866.6× PASS |

Flat and content-blind tiles have weak gradients, so the `Sx, Sy` columns are
poorly conditioned and the fitted translation recovers its planted dose to only
20–23% against a 15% gate. **The consequence is scoped, not waved away:** no
pixel-valued inter-half shift is quoted from the `flat` or `grid` supports
anywhere in this document. The null, both monotonicity checks and the separation
all pass on all three supports, so the *band-ratio* decomposition and the
*direction* of its depth trend stand on all three; the absolute px figure does
not.

### 11.3 Re-measured, the refutation gets stronger

`sel_net`, N low rung → high rung, fixed-separation ladder, all at
0.02–0.08 cyc/px except the first row:

| subject | band | support | fraction | absolute |
|---|---|---|---:|---:|
| flower | high | detail | 0.86× | 1.19× |
| flower | low | detail | **0.52×** | 0.65× |
| flower | low | flat | **0.63×** | 0.55× |
| flower | low | grid | *saturated — REFUSED* | 1.40× |
| bee | high | detail | 0.69× | 1.02× |
| bee | low | detail | **0.52×** | 0.62× |
| bee | low | flat | **0.50×** | 0.41× |
| bee | low | grid | **0.48×** | 0.63× |

`flower` × `low` × `grid` is refused rather than read: its `sel_net` sits at
1.0035 → 1.0032, pinned against the half-sum's own amplitude, and its absolute
rise of 1.40× tracks `high_A`'s 1.40× exactly. A ratio that saturates is not a
measurement of the numerator. Flower's grid support samples mostly defocused
background where the low-band half-sum is 264–402 DN against 7712–9962 on the
detail support, so there is little signal to be a fraction of.

**Seven informative readings. Six fall, one is refused, none rises.** The
refutation is not an artifact of the band or the support: it is *stronger* in the
convicted band (0.52× against 0.86×) and it survives on the flat support where
the blotch actually lives (0.50× on the collapse subject, from the highest
starting level of any support, 0.3563). **Half-stack incoherence does not rise
with N, and the fleet should not use it to validate the exponent fix.**

### 11.4 What the re-measurement changed on the other side

`reg` — the inter-half registration divergence of §8 — reads **larger** in the
convicted band, and the subject asymmetry survives a content-blind support:

| subject | support | `reg` ratio, N low → high |
|---|---|---:|
| bee | detail | **2.15×** |
| bee | flat | **1.93×** |
| bee | grid | **2.07×** |
| flower | detail | 0.45× |
| flower | flat | 0.64× |
| flower | grid | 0.17× |

Rises on the collapse subject on every support; falls on the control subject on
every support. §8 was measured on the detail support at the high band and read
1.90×; in the convicted band on the convicted support it is 1.93–2.15×. This
finding did not weaken under scrutiny, it strengthened, and it remains unowned.

---

## 12. §7 understated the mechanism, because a whole-field mean was the wrong statistic

Applying the fleet's warning to §7 directly. Headroom there was a **mean over the
whole confidence map**. If the effect is concentrated in the flat regions where
blotch was convicted, a whole-field mean dilutes it — the exact failure the
falsification lane hit.

**Commissioning first, spatially, both ways.** `headmap.py --commission` plants a
known offset in one region and requires it to be seen *there* and not elsewhere,
in both signs, and it separately requires the whole-field mean to *fail* to see
it in full:

| check | result |
|---|---|
| +40 border plant moves border | +40.00 PASS |
| +40 border plant leaks to interior | +0.00 PASS |
| −40 border plant moves border | −40.00 PASS |
| −40 border plant leaks to interior | +0.00 PASS |
| +60 flat-quartile plant moves `q0_flat` | +60.00 PASS |
| +60 flat-quartile plant leaks to `q3_detail` | +0.00 PASS |
| whole-field mean sees a ±40 border-only plant | **±18.11** — diluted 2.2× |

The last row is not a pass in the ordinary sense; it is the quantified statement
of the defect being guarded against. A real effect confined to one region is
understated **2.2×** by the statistic §7 used. Commissioning also caught a live
bug in this script: the plant originally ringed *pixels* at 15% while the mask
ringed *blocks* at 15%, so straddling blocks took part of the plant and were then
scored as interior, reporting a 4.17-unit "leak" that was a misalignment between
the plant and the partition, not a property of the field.

**Headroom by region, in confidence units:**

| subject | N | whole | `q0_flat` | q1 | q2 | `q3_detail` | border | interior |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| flower | 18 | 50.93 | **71.18** | 42.39 | 35.55 | 54.41 | 19.23 | 77.15 |
| flower | 205 | 57.47 | **88.88** | 44.75 | 26.36 | 69.54 | 24.69 | 84.59 |
| bee | 25 | 55.51 | **88.94** | 40.22 | 53.24 | 39.51 | 44.85 | 64.33 |
| bee | 299 | 66.51 | **97.28** | 58.26 | 65.42 | 45.02 | 59.98 | 71.92 |
| flower ratio | | 1.13× | **1.25×** | 1.06× | 0.74× | 1.28× | 1.28× | 1.10× |
| bee ratio | | 1.20× | **1.09×** | 1.45× | 1.23× | 1.14× | 1.34× | 1.12× |

**The level is the finding, and it corrects me.** `q0_flat` — the flattest
quartile of the delivered image, the support the plateau was convicted on — has
the highest headroom of any region on both subjects at both depths: 71.2 and 88.9
on flower, 88.9 and 97.3 on bee, against whole-field means of 50.9–66.5. **§7
understated the shipped merge's excess hedging on the convicted support by
1.40–1.60×.**

Against §6's ~120-unit knob span, headroom in the flat quartile is **59% to 81%
of the entire distance between argmax and `--pyramid-exponent 0.5`**. My earlier
sentence — that the mechanism is "5.5% to 9.2%" of the available range — was
measured on the wrong support and is **withdrawn as a statement about the
mechanism's size**. It remains true only of the whole-field average.

**The depth growth is the part that does not change much.** `q0_flat` grows
1.25× on flower (+17.7 units) and 1.09× on bee (+8.3). On bee the flat quartile
grows *more slowly* than the whole field. So the corrected picture is:

- **in level**, the shipped weighting hedges hard, and hardest exactly where the
  defect is — a large effect that the exponent fix is well aimed at;
- **in depth-growth**, the effect remains modest on the convicted support, so
  depth is still not well explained by this mechanism alone.

That is a genuine split, and it is the honest reading: the fleet is fixing
something real and larger than I said, but the *depth* half of the story is still
not accounted for by it.

**One more thing the partition shows.** `border` grows fastest of any region on
both subjects — 1.28× on flower, 1.34× on bee — from the lowest level on flower
(19.2). Border geometry is where deep stacks lose coverage overlap, and it is the
same geometry that fooled the falsification lane. Nobody is looking at it.

---

## 13. Provenance under discipline 34: the merge did change, and the result survives

The orchestrator has ruled that anything measured at or before `9b05d0b7` is
stale by 13 commits. Every number in §§1–12 was measured on that pin
(`44C2F2CD2E5B2894`). This section tests whether that matters rather than
asserting either way.

**Reading the source said the change was default-off. Reading was wrong.**
`git diff 9b05d0b7..HEAD` over `pyramid.rs` and `merge.rs` is 438 insertions and
11 deletions, two of them in the election arithmetic: `Gate::tolerance()` moved
from the `FOCUS_NOISE_SD` constant to a per-instance `self.noise_sd`, and the
fold's `gain.beta(k)` became `beta_for(&self.gain, frame_beta, k)`. Both look
default-preserving in source — `Gate::new` still fills `FOCUS_NOISE_SD`, and
`beta_for` falls through to `gain.beta(k)` on `None`. **`binsame.py` renders the
same frames with both binaries and the outputs differ on every case tested**,
shallow and deep, merge and confidence map alike. A default-preserving change is
a claim about behaviour, and this one does not hold.

| case | N | merge | confidence map |
|---|---:|---|---|
| flower stride 12 | 18 | DIFFERS | DIFFERS |
| flower stride 2 | 103 | DIFFERS | DIFFERS |
| bee stride 12 | 25 | DIFFERS | DIFFERS |

### 13.1 How large, in the units of each claim

| case | mean conf pin | mean conf HEAD | delta | image RMS DN | low-band pin | low-band HEAD |
|---|---:|---:|---:|---:|---:|---:|
| flower N=18 | 761.8 | 765.3 | **+3.5** | 50.6 | 633.0 | 628.3 |
| flower N=103 | 737.3 | 747.2 | **+10.0** | 79.2 | 932.6 | 927.3 |
| bee N=25 | 458.2 | 459.1 | **+0.9** | 44.2 | 6225.0 | 6225.3 |

Two things follow and they point in opposite directions.

**The pin numbers reproduce exactly.** 761.8, 737.3 and 458.2 come back to the
printed digit against §5's table, re-rendered on a CPU-saturated host. The
measurements were right about the binary they were made on.

**But the binary shift is N-dependent and large in level terms.** +3.5 at N=18
against +10.0 at N=103 on the same subject. §7's whole-field depth effect on
flower was +6.6 units. **The binary change alone moves a single rung by more than
the entire depth effect §7 measured**, so any statistic read as an absolute
confidence *level* across depth is contaminated. Low-band amplitude, by contrast,
moves at most 0.74%.

### 13.2 What survives, and the reason is the differencing

`headroom_head.py` re-renders both arms with the HEAD binary:

| subject | N | default | hard-max | headroom HEAD | headroom pin | shift |
|---|---:|---:|---:|---:|---:|---:|
| flower | 18 | 765.3 | 714.0 | 51.31 | 50.93 | **+0.38** |
| bee | 25 | 459.1 | 403.4 | 55.69 | 55.51 | **+0.18** |

**The binary moves the level by up to 10.0 units and the headroom by 0.38.** Both
arms move together and the shift cancels in the difference — 0.7% and 0.3% of the
respective headrooms. The cloud-width control in §7 was built to cancel a *scene*
confound; it cancels a *binary* confound as well, which was not designed for and
is the reason this document did not have to be withdrawn.

| claim | statistic | binary sensitivity | standing |
|---|---|---|---|
| §11.3 refutation, 0.48–0.63× | low-band amplitude ratio | 0.74% | **STANDS** |
| §11.4 bee reg rises 1.93–2.15× | same family | 0.74% | **STANDS** |
| §4 high-band refutation | high-band ratio | not re-measured | **ASSUMED** |
| §7 and §12 headroom | differenced, same binary | 0.38 units | **STANDS** |
| §5 absolute confidence levels | absolute level | 10.0 units, N-dependent | **PERTURBED** |

§5's fall of 761.8 → 728.4 on flower is 33.4 units; a +3.5/+10.0 differential
across depth shrinks it by roughly a fifth without reversing it. §5 was already
the *uncontrolled* reading, reported only so that §7 had something to control,
and the verdict never rested on it. It is now doubly hedged — confounded by cloud
width and perturbed by the binary. **Do not quote §5 levels.**

**Not re-measured, and named as such.** The §4 high-band ladder and the §12
regional partition were not re-rendered on HEAD. §12 is a headroom difference and
inherits the cancellation argument above, but that is an inference from a
whole-field measurement, not a regional one. The full ladders are ~40 merges and
the differencing evidence did not justify the host time tonight.

---

## Reproducing

```powershell
cd projects\strehl\experiments\V-DRIFT
python commission_half.py              # decomposition, 5 checks + leak calibration
python commission_half.py --band low --site-mode detail   # the convicted band
python commission_conf.py             # confidence map, both ways, 4 checks
python headmap.py --commission        # spatial headroom, 8 checks, both signs
python halfstack.py  --subject flower  # interleaved ladder (confounded; see 3)
python offsetctl.py  --subject flower  # fixed-separation ladder (primary)
python halfmetric.py --subject flower --ladder s
python halfmetric.py --subject flower --ladder s --band low            # see 11
python halfmetric.py --subject bee --ladder s --band low --site-mode flat --ncc-floor 0.5
python conf.py       --subject flower --strides 12 4 2 1
python headroom.py   --subject flower --strides 12 1
python headmap.py                      # headroom by region (see 12)
python binsame.py                      # pin vs HEAD: same frames, both binaries
python bindelta.py                     # size of the pin/HEAD difference (see 13)
python headroom_head.py                # does headroom survive the binary change
python verify_select.py                # numeric check of this document
```

Add `--dir 'D:\personal\macro\bee-3-cpl' --subject bee` for the second subject.
Artifacts under `C:\dev\strehl-out\V-DRIFT\`: `half-*.jsonl`, `halfmetric-*.json`,
`conf-*.jsonl`, `head-*.jsonl`, `half-leak.json`, `commconf.json`, and the
rendered TIFFs under `half/`, `conf/` and `head/`. `D:\` is read-only and nothing
here writes to it.

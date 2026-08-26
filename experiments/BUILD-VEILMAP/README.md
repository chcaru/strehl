# BUILD-VEILMAP — how much of the corpus is bimodal?

The veil (ORCH-veiling §59.3) is lost *base*, not lost detail: `BaseBand::Mean`
(`crates/strehl-core/src/pyramid.rs:895`) averages all frames at every pixel,
so at an occluded pixel — where most frames show the defocused foreground — the
background's pedestal is dragged toward the occluder. The signature of such a
pixel is a **bimodal through-focus response**: two sharpness peaks at different
frames, from two depth layers sharing one pixel.

This experiment asks how much of the 26-subject corpus shows that signature, so
that the value of BUILD-BLEND's third base-band arm can be judged against the
corpus rather than against one claw on one bee.

**Headline (MEASURED).** At **96 master px blocks**, drift-tracked, with
topographic prominence, on the 24 of 26 subjects for which a drift model could
be fitted:

| | multi-peak fraction |
|---|---|
| `bee-1-cpl` | **0.324** |
| `bee-3-cpl` | **0.199** |
| `bee-2-cpl` | **0.117** |
| `foam` | 0.112 |
| `lavendar-cpl` | 0.088 |
| `dry-erase-marker-head-cpl` | 0.064 |
| `113MSDCF` | 0.061 |
| corpus median | **0.007** |
| 8 subjects | **0.000** |

**The veil is localised, not pervasive** — but where it is present it is not a
curiosity. It is a *subject class*: deep, hairy, self-occluding subjects run
10–32% bimodal; flat, smooth or shallow subjects run at zero.

---

## What was measured

For each subject, one decode pass produces a through-focus curve per block per
frame from the CFA green lattice `raw_image_visible[0::2, 1::2]`, response =
mean |Laplacian|, exactly as `V-VEILCLAW/probe.py` did — no demosaic, no tone
curve, no black subtraction. Every curve is then classified FLAT /
SINGLE-PEAK / MULTI-PEAK by `V-VEILCLAW/curve.py`'s `smooth(v, 7)` and
prominence-based `peaks(..., min_prom=0.10, min_sep=15)`, imported verbatim.

Two arms are computed in the **same** decode:

* `resp` — each block gathered at its own per-frame similarity (drift-tracked);
* `fixed` — the identical block gathered at fixed pixel coordinates (what
  V-VEILCLAW did, and what an uncontrolled measurement would report).

The difference between them *is* the drift control, and comes from one run
rather than two.

## The prominence caveat, quantified (MEASURED)

`curve.py::peaks` measures prominence against `v[:i].min()` and `v[i+1:].min()`
— the **global** minimum on each side, not the highest saddle between this peak
and the neighbouring higher one. Over a 299-frame bracket the response falls to
the noise floor at both ends, so every ripple on a broad shoulder is credited
with the whole descent to the far end. It overstates prominence, and it
overstates it in the direction that inflates the multi-peak count.

`classify.py::peaks_topo` implements the standard topographic definition
instead. **It matters, and at 48 px it roughly halves the answer:**

| block | `curve.peaks` (global min) | `peaks_topo` |
|---|---|---|
| 48 | 0.526 | **0.266** |
| 96 | 0.375 | **0.199** |
| 192 | 0.322 | **0.183** |
| 384 | 0.264 | **0.139** |

(`bee-3-cpl`, tracked arm.) Every number in this README is the topographic one.
Both are recorded per subject in `classify/*.json`. The claw still classifies
MULTI-PEAK under the corrected definition, at every block size where the
instrument is potent — see below.

---

## Controls, as observed output

### 1. Potency — PASS at 48/96/192 px, FAIL at 384 px

`potency.py` looks up the **grid cell containing** master point (2735, 2175) —
the claw — rather than a hand-placed box, because the grid is what produces the
headline number.

```
point  block    arm     det  class       peaks (frame index : prominence)
claw      48   resp    topo  MULTI-PEAK  f187:0.68  f267:0.60
claw      48  fixed    topo  MULTI-PEAK  f180:0.87  f289:0.66
claw      96   resp    topo  MULTI-PEAK  f186:0.53  f267:0.46
claw      96  fixed    topo  MULTI-PEAK  f181:0.65  f289:0.39
claw     192   resp    topo  MULTI-PEAK  f183:0.31  f269:0.36
claw     192  fixed    topo  MULTI-PEAK  f182:0.28  f266:0.13  f287:0.12
claw     384   resp    topo  SINGLE-PEAK f182:0.19
claw     384  fixed    topo  SINGLE-PEAK f182:0.12
```

The hand-placed box reproduces `V-VEILCLAW/README.md`'s commissioned result
**exactly** in the uncorrected arm — that README records `PROBE: TWO-PEAK
floor=84.2 f182 prom=0.45 f288 prom=0.29`, and `classify.py` prints:

```
  fixed claw  topo   MULTI-PEAK  floor=   84.3  f182 prom=0.45  f288 prom=0.28
  fixed ctl   topo   SINGLE-PEAK floor=   83.4  f244 prom=0.24
  fixed null  topo   FLAT        floor=  115.7
```

against V-VEILCLAW's `CONTROL: SINGLE-PEAK floor=83.3 f244 prom=0.24` and
`NULL: FLAT`. Three windows, three matching verdicts, prominences agreeing to
0.01. The response is the same instrument.

**384 px is beyond the instrument's potency and its numbers must not be used.**
That is not an instrument fault, it is the dilution the corpus already records
(occlusion bimodality is depleted at the 27 px selection window and wants
roughly 5 px): a 384 px block swamps one occlusion boundary with single-layer
surroundings. It is reported here because it bounds the block-size question
from above.

### 2. Null — PASS

The far-corner paper block classifies FLAT at every block size, in both arms,
under both prominence definitions (16 of 16 cells above). AGENTS rule 9's
flat-ROI control was run before any corpus number was believed.

### 3. Drift null — PASS, on four independent tests

This is the one that decides whether the headline means anything, because a
fixed block can show two peaks purely because ~13% magnification breathing swept
different objects through it. Four tests, three of which do not require knowing
the tracker's error magnitude:

**(a) A real flat subject.** `flat-on-ruler-cpl` — a flat target, minimal depth
layering, no occlusion boundaries — carries **4.70% breathing, 199 master px of
corner-to-corner drift** (`fitdrift.py` output), and yields:

```
flat-on-ruler-cpl   79    0.000/0.003     0.000/0.000     0.000/0.000     0.000/0.000
```

Zero multi-peak blocks at every block size, in **both** arms. Real breathing on
a real bracket, with the detector at its headline settings, manufactures
essentially nothing. `leaf-2-cpl` (9.97% breathing, 421 master px) gives
0.013/0.011 at 48 px and 0.000 at 96 px and above.

**(b) Drift-corrected against uncorrected, same decode.** If the number were
drift, removing the drift would move it. On the synthetic plant — where the
bimodality *is* entirely drift — correction cuts multi-peak by **8.5x** at
96 px (0.094 → 0.011) and **10.6x** at 48 px (0.624 → 0.059). On `bee-3-cpl`
the same correction moves it from 0.189 to 0.199, i.e. **not at all, and
slightly upward**. Whatever produces `bee-3-cpl`'s bimodality is insensitive to
the drift correction, and drift is not.

**(c) Radial organisation** (`radial.py`). Breathing is a scale about the
optical centre: its differential shift is exactly zero there and grows with
radius. Any drift artefact is therefore *forced* to be radially organised.
Occlusion has no reason to care where the optical centre is.

```
subject              arm    0.00-0.17  0.17-0.33  0.33-0.50  0.50-0.67  0.67-0.83  0.83-1.00   slope
PLANT-bee-3-cpl      fixed      0.000      0.051      0.084      0.297      0.160      0.242   +0.258
foam                 fixed      0.029      0.130      0.177      0.262      0.299      0.382   +0.401
foam                 resp       0.112      0.120      0.106      0.114      0.111      0.146   +0.016
bee-1-cpl            resp       0.262      0.589      0.578      0.384      0.362      0.222   -0.204
bee-3-cpl            resp       0.262      0.241      0.335      0.302      0.123      0.014   -0.197
bee-2-cpl            resp       0.141      0.139      0.166      0.201      0.079      0.000   -0.029
flat-on-ruler-cpl    resp       0.000      0.000      0.000      0.000      0.000      0.000    0.000
```

The pure-drift plant is exactly zero in the central bin and rises outward. All
three bees are **centre-weighted with negative slope** — the opposite of what
drift can produce. `foam` is the case that proves the correction works: its
uncorrected arm has the drift signature (+0.401, zero at the centre) and its
tracked arm is flat (+0.016), i.e. the tracker removed a real artefact.

The pictures say it more plainly than the table:
`maps/PLANT-bee-3-cpl-b48-fixed-plain.png` is a bullseye — a dark FLAT spot at
the optical centre saturating to solid red at the corners.
`maps/bee-3-cpl-b96-resp-plain.png` and `maps/bee-1-cpl-b96-resp-plain.png` are
pictures of a bee: FLAT paper outside the body, SINGLE-PEAK across the smooth
thorax, MULTI-PEAK along the legs, hairs and body edges.

**(d) A synthetic plant** (`plantdrift.py`). The all-in-focus master warped by
the measured `a_k, ty_k, tx_k` — real breathing, identical scene content at
every frame, no focus change, no occlusion, nothing for a curve to be bimodal
about. Any multi-peak is pure artefact:

```
 block    arm    det   blocks    flat  single   MULTI
    48   resp   topo    14162   0.897   0.044   0.059
    48  fixed   topo    14162   0.081   0.296   0.624
    96   resp   topo     3504   0.983   0.006   0.011
    96  fixed   topo     3504   0.514   0.392   0.094
   192   resp   topo      864   0.994   0.003   0.002
   192  fixed   topo      864   0.870   0.119   0.010
```

**Uncorrected, drift alone manufactures multi-peak in 62% of 48 px blocks.**
Tracked, the artefact floor is 5.9% at 48 px, **1.1% at 96 px**, 0.2% at 192 px.
Against that floor `bee-3-cpl`'s 0.199 and `bee-1-cpl`'s 0.324 at 96 px are
essentially all signal.

### 4. Block-size sensitivity (MEASURED)

`bee-3-cpl`, tracked, topographic:

| block (master px) | multi | plant floor | claw potency |
|---|---|---|---|
| 48 | 0.266 | 0.059 | MULTI ✓ |
| **96** | **0.199** | **0.011** | **MULTI ✓** |
| 192 | 0.183 | 0.002 | MULTI ✓ |
| 384 | 0.139 | 0.000 | **SINGLE ✗** |

The fraction is **monotone decreasing with block size but not steeply so** —
48 px gives 1.9x the 384 px value, not 10x. It is therefore not a size-driven
artefact. 96 px is chosen as the headline because it is where potency still
holds and the drift floor has already fallen to ~1%; 48 px buys more sensitivity
at 5x the floor.

The corpus records that occlusion bimodality wants roughly 5 px, so **all of
these block sizes understate the true rate** and the headline is a lower bound
(ARGUED — 5 px blocks were not measured here; the drift model's placement error
is far larger than 5 px, so they could not have been measured honestly).

---

## Full census (MEASURED)

Tracked / uncorrected, topographic prominence, all in-bounds blocks.
Complete machine-readable form in `summary.csv`; per-subject detail in
`classify/<subject>.json`; maps in `maps/<subject>-b<B>-<arm>-plain.png`.

```
subject                               n         b48             b96            b192            b384
bee-1-cpl                           299  0.415/0.367     0.324/0.294     0.292/0.296     0.289/0.299
foam                                100  0.298/0.433     0.112/0.223     0.037/0.041     0.000/0.000
bee-3-cpl                           299  0.266/0.256     0.199/0.189     0.183/0.171     0.139/0.139
bee-2-cpl                           299  0.211/0.212     0.117/0.111     0.074/0.076     0.025/0.025
dry-erase-marker-head-cpl           299  0.138/0.175     0.064/0.100     0.060/0.087     0.064/0.080
lavendar-cpl                        299  0.128/0.110     0.088/0.080     0.080/0.079     0.083/0.056
flower-bud-with-background-fern-cpl 299  0.126/0.119     0.043/0.052     0.053/0.044     0.069/0.065
couch-fibers-cpl                    299  0.107/0.083     0.026/0.026     0.010/0.010     0.005/0.000
coffee-bean                         105  0.104/0.109     0.047/0.055     0.037/0.051     0.075/0.080
113MSDCF                             63  0.058/0.055     0.061/0.057     0.057/0.047     0.028/0.023
pencil-flatter-angle-cpl            299  0.042/0.041     0.003/0.005     0.000/0.000     0.000/0.000
pencil-steep-angle-cpl              299  0.029/0.029     0.003/0.003     0.004/0.003     0.000/0.000
112MSDCF                             79  0.027/0.030     0.023/0.022     0.015/0.008     0.005/0.000
wrapped-text-1                      130  0.026/0.056     0.001/0.014     0.000/0.001     0.000/0.000
flower-bud-alone-cpl                205  0.021/0.020     0.010/0.007     0.007/0.007     0.000/0.000
wrapped-text-2                      120  0.021/0.077     0.003/0.036     0.000/0.006     0.000/0.000
leaf-2-cpl                          182  0.013/0.011     0.000/0.000     0.000/0.000     0.000/0.000
tweezers-cpl                        100  0.012/0.004     0.002/0.000     0.004/0.004     0.011/0.005
lead-1-cpl                          123  0.006/0.006     0.000/0.000     0.000/0.000     0.000/0.000
flowers-cpl                         176  0.004/0.010     0.000/0.005     0.000/0.002     0.000/0.000
flat-on-ruler-cpl                    79  0.000/0.003     0.000/0.000     0.000/0.000     0.000/0.000
109MSDCF                             22  0.000/0.000     0.000/0.000     0.000/0.000     0.000/0.000
119MSDCF                             33  0.000/0.000     0.000/0.000     0.000/0.000     0.000/0.000
coffee-bubbles                       19  0.000/0.000     0.000/0.000     0.000/0.000     0.000/0.000
PLANT-bee-3-cpl (drift only)        299  0.059/0.624     0.011/0.094     0.002/0.010     0.000/0.005
```

Not measured: **`flower-inner-edge-cpl`** and **`highly-angled-ruler-mm-cpl`**.
`fitdrift.py` could not obtain enough RANSAC inliers on any frame (2 or fewer
against a 3-parameter model) and **aborts rather than publish a drift model
fitted on nothing**. `highly-angled-ruler-mm-cpl` is the expected failure:
repeating millimetre ticks are the classic periodic-texture correspondence trap.
Both are UNVERIFIED, not zero.

### Shallow brackets are not comparable (MEASURED, and a caveat)

`109MSDCF` (22 frames), `119MSDCF` (33) and `coffee-bubbles` (19) return exactly
0.000 at every block size. `min_sep=15` on a 22-frame bracket makes bimodality
very nearly **structurally inexpressible** — two peaks must be 68% of the
bracket apart. Their zeros are an artefact of holding V-VEILCLAW's parameters
fixed, which was done deliberately so the claw remains the calibration. Read
those three rows as "not measurable at these settings", not as "no occlusion".
Thresholds were **not** re-tuned to improve them.

---

## Cross-reference to the merge (NOT DONE)

The base/detail mismatch census — counting bimodal blocks that also show the
claw's base/detail signature against the master — was not reached. It is the
obvious next step and would turn this screening statistic into a defect census.

---

## Is the drift confound controlled well enough to trust the headline?

**Yes at 96 px and above; no at 48 px without the floor subtracted; and no at
all for the uncorrected arm.** (MEASURED for the first two clauses, via the
plant and `flat-on-ruler-cpl`.)

Stated plainly, and with the part that argues against the number first:

* The drift model is **not uniformly good**. Held-out placement error on
  `bee-3-cpl` is a median 70 master px (uncorrected: 157), and the model
  reproduces AGENTS rule 6's two recorded f240 shifts to only 17.9 and 36.7
  master px. On `112MSDCF` the same instrument achieves a median **1.8 master
  px** (uncorrected 29.1) and on `flat-on-ruler-cpl` a smooth-vs-direct
  agreement of 1.1 master px. The quality is subject-dependent and `bee-3-cpl`
  — the headline subject — is among the worse ones, because it is deep, hairy
  and defocused nearly everywhere in most frames.
* A synthetic plant perturbed by a **smooth scale error of 14–20 master px**
  produces a 41% multi-peak floor at 96 px, which would swamp the headline.
  **I do not believe that number is a fair floor and I am reporting it anyway.**
  The perturbation I imposed is `sin(2πu)` — a scale wobble that sweeps content
  back and forth *exactly twice* across the bracket — which is a two-peak
  generator by construction. Its tell is in the output: the median peak
  separation is **149–152 frames**, precisely half the bracket, in every cell.
  Real `bee-3-cpl` blocks separate by a median of 38 frames and the claw by
  86–108. A fitted low-order polynomial's error does not oscillate twice, so
  this is an adversarial upper bound, not a floor. (ARGUED: I did not measure
  the true shape of my model's error, only its magnitude.)
* Against that, the three tests that need no assumption about the tracker's
  error all agree: a real flat-target bracket with 199 master px of drift
  yields **zero**; drift correction changes the plant 8.5x and `bee-3-cpl` not
  at all; and the multi-peak maps of the bees are centre-weighted and shaped
  like bees, while the pure-drift map is a bullseye centred on the optical axis.
  Drift artefact cannot be centre-weighted — it is zero at the centre by
  construction.

So the headline is trustworthy in **rank and order of magnitude** — bees at
10–32%, flat and shallow subjects at 0%, the corpus median at 0.7% — and
trustworthy in its qualitative verdict. The individual per-subject figures
carry a subject-dependent uncertainty from the tracker that I have bounded from
below (perfect-model plant) but not from above with a defensible error shape.
`lavendar-cpl` is the one subject I would treat with suspicion: its tracked
radial slope is still **+0.293**, the drift signature, so some of its 0.088 is
probably artefact.

**Verdict: the veil is localised to a subject class, not pervasive across the
corpus — and within that class it is severe.** Roughly a third of `bee-1-cpl`
and a fifth of `bee-3-cpl` is bimodal at 96 px, which is far too much to call an
edge case, and those are exactly the subjects the project holds up as
print-worthy. A fix that is off by default would not fire on the images that
most need it. (ARGUED: whether *every* bimodal block is actually veiled by the
merge was not measured — see "Cross-reference to the merge" above.)

---

## Files

| | |
|---|---|
| `veilcore.py` | response, summed-area block means, drift model, `TrackFitter` |
| `fitdrift.py` | sparse direct per-frame fits → one global smooth polynomial |
| `veilgrid.py` | one decode pass → tracked and untracked block response tensors |
| `classify.py` | FLAT/SINGLE/MULTI, `peaks_topo`, spatial maps |
| `potency.py` | claw/control/null read out of the grid |
| `plantdrift.py` | synthetic drift-only bracket |
| `radial.py` | multi-peak fraction against radius from the optical centre |
| `track.py` | ground-truth check + tracked-block contact sheet |
| `summary.py` | corpus table and `summary.csv` |
| `runall.py` | resumable parallel driver over all subjects |
| `whyfail.py`, `diag.py`, `look.py`, `dist_probe.py` | correspondence diagnostics |
| `bench.py`, `commission.py`, `placement.py` | commissioning probes |

Outputs (not in git): `C:\dev\strehl-out\BUILD-VEILMAP\` —
`drift/`, `tensors/`, `classify/`, `maps/` (200 PNGs), `track/`, `summary.csv`.

Reproduce: `python runall.py --workers 6`, then `python summary.py`,
`python potency.py`, `python radial.py --subjects ...`.

## Two things a verifier should attack first

1. **The `lapratio` gate's quantile fallback** (`veilcore.py`). The absolute
   band [0.30, 2.00] was calibrated on `bee-3-cpl` and does **not** transfer:
   on `leaf-2-cpl` at f045 the seed is already accurate to a median 1.9 lattice
   px — nearly every window is a correct match — yet the ratios run 1.9–10.4
   and the band rejects 17 of 20, because the master is a merge with its noise
   averaged down and a single raw frame is not. The fallback keeps the lowest
   within-frame quantile instead. It is doing real work on the smooth subjects
   and it is the least-verified component here.
2. **The per-subject numbers for subjects whose drift fit is weak.**
   `fitdrift.py` prints `WEAK:` and the held-out fractions for every subject;
   `bee-1-cpl` — the highest scorer in the corpus — fitted from only 7 directly
   fitted frames and has a held-out fraction of 0.125 within 16 master px. Its
   0.324 is the number I would most like an independent check on, even though
   its `fixed` arm agrees (0.294) and its radial slope is −0.204.

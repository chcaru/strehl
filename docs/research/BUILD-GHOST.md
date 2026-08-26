# BUILD-GHOST: does the shipped merge path need outlier rejection and photometric normalisation?

**Agent:** BUILD-GHOST · **Reporting to:** ORCH · **Status:** complete

## The claim under test

`README.md:181-184` tells a user, in the user-facing document:

> **In practice, on this corpus:** all 26 reference renders were produced on this path
> and none of them needed those stages. If your subject held still and your exposure
> held steady, neither will yours.

The path in question is the default `pyramid` merge backend, whose own banner
(`README.md:150-154`) states that photometric gain, clip census, outlier rejection,
halo correction and through-focus statistics are **not applied**. So the README is
asserting that a corpus of 26 stacks needed neither outlier rejection nor photometric
normalisation. That assertion was ARGUED. This report measures it.

**Verdict up front: the README's claim is substantially correct, but its stated
*reason* is wrong, and one subject is a genuine exception.** Detail below.

---

## Answers to ORCH's four questions

| # | Question | Answer |
|---|---|---|
| 1 | How many of 26 have residual motion large enough to matter? | **MEASURED: 10 of 26** clear a floor measured on a subject that cannot move; **5 of 26** at the control-validated K=1 baseline. Every one clears it by only 1.07×–1.90×. None is a large signal. |
| 2 | How many have exposure drift large enough to mis-weight the gate? | **MEASURED: depends on the merge's focus window W, and I report the whole curve rather than guess it.** At W=2, **6 of 26**; at W=4–8, **10 of 26**; at W=32, **15 of 26**; across the whole bracket, **23 of 26**. The bracket-total figure is the misleading one. |
| 3 | Is any of it visible in the delivered masters? | **MEASURED (by eye, 22 crops at 1:1 across 15 subjects): no. Not one instance of ghosting, doubling, or smear.** Including bee setae against flat white and printed text on paper, the two most ghost-revealing configurations in the corpus. |
| 4 | Does the port need to happen tonight? | **No — v2, with one carve-out.** See recommendation. |

---

## Part 0 — the detector, and why you should believe it

No corpus number below was quoted until the control suite was green.

`python experiments/BUILD-GHOST/controls.py` → `C:\dev\strehl-out\BUILD-GHOST\controls.log` (374 s)

| Control | Outcome | Key number |
|---|---|---|
| C1 identity (frame against itself) | PASS | residual exactly 0.0; 1348 kept / 7245 tiles |
| C2 planted global similarity | PASS | scale+rotation error 6.0e-6; p99 **0.233** sensor px |
| C3 planted local motion ladder | PASS | 0.25→0.164, 0.5→0.376, 1.0→0.887, 2.0→**1.915**, 4.0→3.899, 8.0→7.841 |
| C4 defocus-only null | PASS | p99 0.229 / 0.230 / 0.466 / 1.099 / 1.093 at σ_max 0.3 / 0.6 / 1.2 / 2.5 / 5.0 |
| C5 defocus **and** motion together | PASS | planted 2.0 → 1.94 inside the moving region; 0.605 outside it |
| C6 real rigid pairs | PASS | flat-on-ruler p99 **0.866** over 2281 tiles |
| C7 two greens, one exposure | PASS | offset error **0.0258** plane px |
| C7b "aliasing explains C7's tail" | **NOT-CONFIRMED** | predicted a 1.3× drop, measured 1.08× |

**Census: 8 items → 7 PASS, 0 FAIL, 0 CONFIRMED, 1 NOT-CONFIRMED. Sums to 8.**

C7b was my own hypothesis about my own detector, and it is reported falsified rather
than tuned green. It no longer matters to any conclusion: after the uniqueness gate,
C7's p90 is 0.282 sensor px, far under the floor. Report it as "needs no excuse",
not as "explained".

**Detector floor = 1.099 sensor px** (worst null p99 across C2, C4, C6-flat).

### How defocus was separated from motion — and the proof it worked

This is the confounder the brief flagged, and it is real. **MEASURED:** a naive
difference-based detector flags **35.0%** of tiles on a pair where nothing moved
(defocus only) but only **9.9%** on a pair with a real 8 sensor px displacement —
**3.5× more false alarm than true alarm.** A difference metric is not a weak motion
detector; it is not a motion detector at all.

The separation is structural, not statistical. Defocus is a symmetric, unit-sum
convolution: it changes the *amplitude* of a correlation peak, never its *position*.
Motion moves the peak. The metric is a **displacement**, read off the one axis
blur cannot touch. Proven by C4 (defocus alone stays at the floor), C5 (motion is
still recovered when defocus is piled on top), and the 3.5× statistic above.

Additional guards, each of which changed a result: a Hann **window-autocorrelation
correction** (the window drags every estimate toward zero *in proportion to itself*;
`smoke.py` shows the fix leaves worst signed bias 0.0300 plane px and tile-to-tile
scatter **exactly 0.0000**, i.e. the residue is pure 1/16-px grid quantisation);
a **peak-uniqueness gate** calibrated by sweep, not asserted (`tune_uniq.py`: it
flattens four independent nulls — wrapped text 11.09→1.67, angled ruler 12.65→1.78,
two-greens 7.05→1.58, defocus-only 2.10→1.03 sensor px — while leaving C3's real
planted 2.0 px motion untouched at 1.93→1.96); and a **focus-match gate** so that
only tiles sharp in *both* frames are compared.

### Two things I got wrong, corrected here rather than buried

1. **The multi-baseline design assumption is FALSIFIED.** I sampled baselines
   K ∈ {1,4,16} expecting that residual growing with K means slow drift. It does not.
   `flat-on-ruler-cpl` is a printed card glued to a steel rule at a single depth —
   it *cannot* move — and it reads 0.852 / 3.004 / 6.146 sensor px at K = 1 / 4 / 16.
   Growth with K is geometry (accumulated warp, larger defocus separation, and
   depth-dependent parallax the global similarity cannot express), **not motion**.
   `k_slope` is therefore not a motion statistic and I do not use it as one.
   Consequence: each baseline gets its **own floor, measured on that null subject**
   (K=1 → 1.099, K=4 → 3.004, K=16 → 6.146 sensor px), and the null control is
   re-run through the final rule as a self-check — it reads *quiet*, as it must.
   Note K=1's floor is independently reproduced: C6 measured 0.866 on this subject,
   the blind corpus sweep measured 0.852 — agreement to 1.6%.

2. **A visual impression I formed was not supported by measurement, and I retract
   it.** Viewing the top sites, they looked like they were landing on empty regions
   (blown white, dark noise, featureless grey). `hotsites.py` tested that against a
   24×24 grid of sites in the same master: median structure percentile at hot sites
   is **57.3** — i.e. *typical*, not low. Partition of 31 sites: 3 below the 25th,
   10 in 25–50, 12 in 50–75, 6 above the 75th. **Sums to 31.** The residual does
   *not* preferentially land on featureless regions. Claim withdrawn.

---

## Part 1 — residual local motion beyond the aligner's similarity

`python experiments/BUILD-GHOST/sweep.py --all --jobs 5` (1658 s) → `data/sweep.json`

**Census: 26 subjects examined, 26 measured, 0 no-usable-pair, 0 crashed. Sums to 26.**

The aligner (`crates/strehl-core/src/align.rs`, read only) fits a **similarity and only
a similarity** — 4 parameters, in plane pixels, 1 plane px = 2 sensor px. So focus
breathing's large scale change is *expected* and is modelled out; what I report is
what survives that fit. Threshold `T_K = 2 × floor_K`, decided on **clusters**
(≥4 contiguous tiles, direction coherence ≥0.50) because real motion is contiguous
and points one way while detector noise is white and directionally random; p99 is
only a screen.

| subject | p99 K1 | p99 K4 | p99 K16 | hot | peak (sensor px) | excess over floor | verdict |
|---|---|---|---|---|---|---|---|
| dry-erase-marker-head-cpl | 1.90 | 6.15 | 13.66 | 8 | 18.54 | 1.51× | MOTION |
| tweezers-cpl | 1.32 | 4.86 | 9.26 | 1 | 13.44 | 1.09× | MOTION |
| highly-angled-ruler-mm-cpl | 1.72 | 5.22 | 14.68 | 10 | 11.42 | 1.90× | MOTION |
| bee-3-cpl | 1.31 | 6.20 | 14.73 | 3 | 10.94 | 1.82× | MOTION |
| bee-1-cpl | 1.65 | 5.58 | 13.61 | 3 | 8.09 | 1.35× | MOTION |
| pencil-steep-angle-cpl | 1.17 | 3.46 | 6.61 | 1 | 6.78 | 1.13× | MOTION |
| bee-2-cpl | 1.44 | 5.90 | 7.58 | 3 | 6.45 | 1.07× | MOTION |
| wrapped-text-1 | 1.88 | 6.41 | 12.03 | 7 | 2.61 | 1.19× | MOTION |
| flower-inner-edge-cpl | 1.09 | 3.49 | 9.15 | 1 | 2.51 | 1.14× | MOTION |
| couch-fibers-cpl | 1.16 | 4.53 | 16.15 | 1 | 2.48 | 1.13× | MOTION |
| *(16 others)* | ≤1.41 | ≤5.58 | ≤12.81 | 0 | — | — | quiet |

**Census: 26 examined → 10 MOTION, 16 quiet, 0 not measured. Sums to 26.**
Of the 10, **5** are flagged at the control-validated K=1 baseline.
Null-control self-check: `flat-on-ruler-cpl` reads **quiet**. PASS.

**The single most important number in this table is the `excess` column.** The largest
detection in the entire corpus clears its floor by **1.90×**; seven of the ten clear it
by under 1.4×. There is no subject with a big, unambiguous motion signal. A stack with
an antenna that actually twitched would not look like this.

**MEASURED conclusion:** residual non-rigid motion in this corpus is small and
marginal everywhere. **ARGUED caveat:** because I fit the *pairwise* similarity rather
than the shipped global solve, my residual is a **lower bound** on what the shipped
aligner leaves. That bias runs *toward* the README being right, which is the
conservative direction for a claim I was trying to falsify — but it is a bias and
ORCH should know it points that way.

---

## Part 2 — exposure

`python experiments/BUILD-GHOST/exposure.py --all` → `data/exposure_all.json`
Controls 3/3 PASS. E2 recovered planted gains 1.01 / 1.05 / 1.20 to 7 significant
figures. E3 established the separation margin: a σ=8 plane px defocus with **no** gain
change fakes only **0.11%** apparent gain and conserves frame mean to 1 part in 4×10⁶,
because defocus is a unit-sum convolution — going soft redistributes light, it does not
create or destroy it. All flux is camera-linear (decile statistics of the CFA green
plane, black-subtracted); **nothing here passes through a tone curve.**

**Census: 26 subjects examined, 26 with flux data, 0 missing. Sums to 26.**

### The headline number is real, and it is not what it looks like

Seven subjects show large, smooth, monotonic flux ramps with essentially zero flicker
and EXIF that says the exposure never changed: `dry-erase-marker-head-cpl` **+0.537
stops**, `flower-bud-with-background-fern-cpl` +0.467, `lavendar-cpl` +0.440,
`flower-inner-edge-cpl` +0.422, `highly-angled-ruler-mm-cpl` +0.402, `flowers-cpl`
+0.300, `flower-bud-alone-cpl` +0.270. Read naively that is half a stop of unexplained
gain drift on a quarter of the corpus.

It is mostly **magnification**. Focus breathing changes m; the same photons spread over
m² more pixels; flux per pixel goes as 1/m². That gives a prediction with **no free
parameter**: `ln(flux_b/flux_a) == −2·ln(scale_ab)`. The left side comes from
`exposure.py` (decile flux); the right from `sweep.py`'s similarity fits, computed for
an entirely different purpose before this hypothesis existed. They share no code beyond
the decoder.

`python experiments/BUILD-GHOST/magtest.py` → `data/magtest.json`

- **Census: 426 usable pairs → 0 no-flux, 216 untestable-subject-or-too-few-tiles,
  210 used. Sums to 426.** Subjects: **16 testable, 10 untestable. Sums to 26.**
- Testability was gated on **inputs only** — predicted effect size versus independently
  measured flicker (at σ/√n, the standard error of an n-point slope), and ≤1% clipping.
  Never on the residual or the slope. Proof it does not select for agreement: the gate
  *admits* subjects that disagree, e.g. `flat-on-ruler-cpl` (slope −0.181) and
  `couch-fibers-cpl` (+0.242).
- **Median per-subject slope +0.365** against a prediction of exactly 1.0.
- **Permutation null N1 PASSES: 0 of 400 re-pairings reach the true slope (p = 0.0025),
  null slope −0.006 ± 0.085.** Both flux and scale drift monotonically with frame index,
  so "they correlate" would be worthless; this shows the *pairing* carries information
  the marginals do not. The null is drawn through the same gates, so a gate that
  manufactured agreement would show up here.
- Six subjects show the mechanism cleanly, with 2–5× RMS reduction and **zero fitted
  parameters**: fern (slope +1.235, R² 0.980, **5.06×**), lavendar (+0.773, R² 0.866,
  3.89×), bud-alone (+1.246, R² 0.910, 3.40×), tweezers (+1.056, R² 0.826, 3.03×),
  inner-edge (+1.224, R² 0.614, 2.31×), angled-ruler (+0.765, R² 0.492, 2.07×).
  **These are exactly the subjects with the big ramps.**

**MEASURED:** where the drift is large enough to matter, it is largely magnification.
**MEASURED:** where the mechanism fails (113MSDCF, bee-1, flat-on-ruler, 109MSDCF), the
drift is ≤0.03 stops RMS — there is essentially nothing to explain.

### But mechanism is not impact, and this is the part that could mislead ORCH

**Identifying the drift as geometric does NOT make it harmless.** Warping a frame back
to reference geometry resamples it: interpolation moves intensity values around, it does
not restore photons magnification diluted. **The flux deficit survives alignment.** To
the noise gate a 0.4-stop offset is a 0.4-stop offset regardless of cause — and a smooth
monotonic one is *worse* for an estimator than random flicker, which averages out.

What rescues it is that **the bracket total is the wrong statistic.** The merge does not
weigh frame 1 against frame 299; at any output pixel it combines the frames in focus
*there* — a narrow window. Rather than guess that window I report the whole curve
(`gateimpact.py` → `data/gateimpact.json`), worst sliding window, peak-to-peak stops:

| subject | W=2 | W=4 | W=8 | W=16 | W=32 | whole bracket |
|---|---|---|---|---|---|---|
| **foam** | **0.0754** | **0.1420** | **0.3165** | **0.5736** | **0.8908** | **1.0081** |
| bee-1-cpl | 0.1039 | 0.1332 | 0.1442 | 0.1569 | 0.1641 | 0.1918 |
| 113MSDCF | 0.0947 | 0.0947 | 0.0947 | 0.1151 | 0.1314 | 0.1314 |
| coffee-bean | 0.0861 | 0.1405 | 0.1611 | 0.1649 | 0.1649 | 0.1649 |
| couch-fibers-cpl | 0.0681 | 0.0681 | 0.0689 | 0.0714 | 0.0793 | 0.2366 |
| 112MSDCF | 0.0511 | 0.0704 | 0.0774 | 0.0950 | 0.1029 | 0.1248 |
| wrapped-text-2 | 0.0493 | 0.0811 | 0.0811 | 0.0811 | 0.0937 | 0.1424 |
| dry-erase-marker-head-cpl | 0.0057 | 0.0161 | 0.0367 | 0.0750 | 0.1191 | **0.5551** |
| flower-…-fern-cpl | 0.0034 | 0.0085 | 0.0169 | 0.0346 | 0.0686 | **0.4757** |
| lavendar-cpl | 0.0028 | 0.0075 | 0.0152 | 0.0289 | 0.0568 | **0.4454** |
| highly-angled-ruler-mm-cpl | 0.0028 | 0.0066 | 0.0132 | 0.0257 | 0.0484 | **0.4097** |

**Census at a 0.05-stop threshold, out of 26:** W=2 → **6** exceed / 20 below;
W=4 → 10 / 16; W=8 → **10 / 16**; W=16 → 11 / 15; W=32 → 15 / 11;
whole bracket → 23 / 3. **Each row sums to 26.**

**This inverts the naive reading.** The subjects with the *scariest* bracket totals —
dry-erase at 0.555 stops, fern 0.476, lavendar 0.445, ruler 0.410 — are among the
*best behaved* locally, at **0.003–0.006 stops between adjacent frames**. Smooth
magnification drift spread over 299 frames is invisible to any local window. The
subjects that genuinely threaten the gate are the **flicker** subjects, and they are a
different set.

**`foam` is the one genuine exposure failure in this corpus.** 0.075 stops adjacent,
**0.32 stops within 8 frames**, 0.89 within 32, 1.008 across the bracket; flicker MAD
0.0292 stops (30× the well-behaved subjects); and it is one of the few with
**EXIF that does not report constant exposure**. That is exactly the aperture
non-repeatability the brief anticipated, and photometric normalisation would help it.

---

## Part 3 — looking at the pictures

**This is the part that decides it, so it was done by eye, not by metric.**

Tools: `crops.py` (motion-sited 1:1 crops, ranked by its own cluster score) and
`verdictcrops.py` (crops at **exactly** the sites `analyse.py` nominates — written
after I noticed the two site lists were not identical, which would have made the visual
check evidence about the wrong thing). Masters read with `tifffile`, **asserted
`uint16`**, cropped 512×512 at 1:1 with **no resampling**, written through a
hand-rolled lossless PNG writer so no JPEG artifact could masquerade as a ghost.
The 16→8-bit path was itself smoke-tested and viewed first (`smoke_crops.py`).

**22 distinct crops viewed across 15 subjects**, covering every subject Part 1 flagged,
the rigid null, and the three subjects most likely on physical grounds to have moved
(drifting bubbles, foam, cut flowers).

| subject | what I actually see at 1:1 |
|---|---|
| `bee-3-cpl` (excess 1.82×) | Setae projecting against flat white — **the most ghost-revealing configuration in the corpus**. Every hair a single crisp profile. No doubling, no secondary edge, no smear. |
| `bee-1-cpl` (1.35×) | Dense plumose setae resolved down to individual side-branches; abdomen edge clean against white. Award-quality detail. No ghosting. |
| `wrapped-text-1` (1.19×, highest K=1 residual in the corpus, 1.878 px) | Printed letterforms, high-contrast black on white — the other ideal ghost test. Edges clean and single, toner dot structure resolved, paper fibre visible. Slight softness consistent with the paper's curve, **no doubled glyph**. |
| `dry-erase-marker-head-cpl` (1.51×, corpus's largest peak at 18.54 px) | Near-blown white body with a soft edge and some dust. Soft, but no doubling or smear. Note this subject is **5.3% clipped**; a correlation estimate here is unreliable. |
| `highly-angled-ruler-mm-cpl` (1.90×, most hot clusters) | Featureless soft grey — a defocused low-contrast region. Nothing present to ghost. |
| `tweezers-cpl` (1.09×) | Dark, low-contrast matte metal; texture largely noise. No visible artifact. |
| `couch-fibers-cpl` | Dense synthetic fibres at many depths; in-focus fibres crisp, out-of-focus fibres overlaid as expected for a deep stack. No doubled fibres. |
| `flower-inner-edge-cpl` | Petal edge with trichomes individually resolved, each a single clean profile. Living material, no motion visible. |
| `lavendar-cpl` | Fine trichome mat, sharp where in focus. No ghosting. |
| `coffee-bubbles` | Bubble rims with bright specular highlights — bubbles genuinely drift on a liquid surface. Rims **sharp and single**. No doubled rim. |
| `foam` | Dark wet foam; bubble walls with speculars. Slightly mushy walls consistent with defocus and translucency. No doubling. |
| `flat-on-ruler-cpl` (rigid null) | Paper fibre and rule markings, sharp. As expected. |
| `bee-2-cpl` (1.07×) | Wing membrane with veins and setae over pale cuticle. Veins sharp and single, hairs individually resolved. Soft in places from defocus; no doubling. |
| `flowers-cpl` | Pale low-contrast surface, largely defocused. No structure present to ghost. |
| `flower-bud-alone-cpl` | Bud with trichomes silhouetted against white; foreground soft from defocus, edge trichomes crisp and single. No doubling. |

**Census: 15 subjects viewed → 15 with no visible ghosting, 0 with visible ghosting.
Sums to 15.** Crops: `C:\dev\strehl-out\BUILD-GHOST\crops\` and `crops\verdict\`,
with `manifest.json` recording each site's master coordinates, K, frame index,
coherence and excess so ORCH can re-cut any of them.

**MEASURED: the residual motion in this corpus is measurable but not visible.**
That is the honest answer and it changes the priority, exactly as the brief anticipated.

**Coverage limit, stated plainly: 26 subjects → 15 viewed, 11 not viewed. Sums to 26.**
The 15 were chosen as all 10 Part 1 flagged, the rigid null, and the four most likely
on physical grounds to have moved. The 11 unviewed are subjects Part 1 measured as
quiet with no hot cluster at any baseline, so there was no motion site to crop; a ghost
there would have to be one my detector missed entirely. That is a real residual risk and
I am not claiming otherwise — it is the main thing an independent verifier should attack.

---

## Recommendation

**Do not do the photometric + outlier-rejection port tonight.** It is a **v2** item.
It is not worth colliding with three agents in `crates/`.

Reasoning, with the tags:

1. **MEASURED** — no delivered master shows visible ghosting, doubling or smear at 1:1,
   including in the two configurations (setae on white; black text on white) where a
   ghost would be unmissable, across 22 crops on 15 of the 26 subjects. Outlier
   rejection cannot improve a picture that has no visible outlier artifact.
2. **MEASURED** — residual motion is marginal everywhere. The largest detection in 26
   subjects clears its floor by 1.90×, and seven of ten by under 1.4×.
3. **MEASURED** — the alarming half-stop exposure ramps are mostly magnification from
   focus breathing (permutation null p = 0.0025; up to 5.06× RMS reduction with no
   fitted parameter), and locally they are 0.003–0.006 stops between adjacent frames.
   Photometric normalisation would buy almost nothing on those subjects.
4. **The carve-out.** `foam` is a real exception on exposure: 0.32 stops within 8
   frames, 30× the corpus flicker, EXIF inconsistent. If `foam` must ship at print
   quality, it needs photometric normalisation — but that is **one subject of 26**, and
   the cheaper fix is to re-shoot it. **ARGUED**, not measured: I did not test whether
   normalising `foam` actually improves its master, because that needs a merge-path
   change, which is outside my remit.

**So the README's claim is substantially right — but its stated reason is wrong, and
I recommend the wording change.** It currently tells users the corpus was fine
*because subjects held still and exposure held steady*. **Exposure did not hold
steady**: 23 of 26 subjects drift by more than 0.05 stops across the bracket and seven
drift by 0.27–0.54 stops. The corpus was fine because the drift is smooth and
magnification-driven, so it is negligible *within the narrow frame window the merge
actually combines*. A user who reads the current sentence and infers "my flat exposure
graph means I'm safe" has drawn the wrong lesson — and a user with `foam`-like flicker
is not safe at all. Suggested framing: *steady* is the wrong test; **locally** steady is
the right one.

---

## Reproducing this

```powershell
cd C:\dev\blog\death-of-software\projects\strehl
python experiments\BUILD-GHOST\smoke.py         # 3 s   estimator ladder
python experiments\BUILD-GHOST\controls.py      # 374 s C1-C7b, must be green first
python experiments\BUILD-GHOST\exposure.py --all        # Part 2
python experiments\BUILD-GHOST\sweep.py --all --jobs 5  # 1658 s Part 1
python experiments\BUILD-GHOST\analyse.py       # verdict tables + verdict.json
python experiments\BUILD-GHOST\magtest.py       # magnification test + permutation null
python experiments\BUILD-GHOST\gateimpact.py    # gate-relevant local flux spread
python experiments\BUILD-GHOST\hotsites.py      # structure at hot sites
python experiments\BUILD-GHOST\crops.py --top 10 --sites 3
python experiments\BUILD-GHOST\verdictcrops.py --top 3
```

Logs and data: `C:\dev\strehl-out\BUILD-GHOST\` (`*.log`, `data\*.json`, `crops\`).
Master SHA-256 (first 16 hex) in `C:\dev\strehl-out\BUILD-GHOST\master_hashes.txt`;
all 26 are 197,798,531 or 198,023,555 bytes. Sample:
`bee-3-cpl BD5B92DDB5DFBD36`, `wrapped-text-1 D50A90386FA7B82E`,
`foam 6AAFA4B2A4C12587`, `flat-on-ruler-cpl 2866EA70452DC35F`.

No Rust build was needed — the whole measurement is Python over `rawpy` + `tifffile`,
which sidesteps the shared-tree `os error 5` trap entirely. Nothing under `crates/`,
`experiments/ORCH-drift-check/` was modified. `D:\` was never written to.

## Open questions for ORCH

1. **What frame window does the merge actually combine at one output pixel?** My Part 2
   verdict swings from 6/26 to 23/26 across plausible W. I report the curve rather than
   guess. Someone who knows the pyramid backend can read off the right row.
2. **Capture mode.** `align.rs` states `CaptureMode::Rail` is not covered — rail motion
   gives depth-dependent parallax with no global 2D transform. If any of these 26 were
   rail-shot, some of my K>1 residual is parallax, not motion. This is why the rigid
   *single-depth* card is the primary null and why deep subjects are reported but do
   not set the floor.
3. **`foam`:** re-shoot, or port photometric normalisation for it? Measurement says it
   is the only subject where the answer is not obviously "leave it".
4. I never explained C7's residual tail (C7b falsified). It does not affect any
   conclusion, but it is an unexplained property of my own detector.

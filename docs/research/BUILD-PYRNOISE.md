# BUILD-PYRNOISE — the shipping pyramid backend's flat-ROI noise, measured externally

The README's section "The honest performance claim" calls its table "the whole
argument". Every `gate` row in that table is an **estimator** measurement:
`--gate` is an estimator-only flag and `--merge pyramid --gate 2` is refused
with rc=1. The pyramid — **the compiled-in default** — has no row, because the
pyramid backend refuses `--flat-roi`, `--detail-roi`, `--stats`, `--n-eff-map`
and five other estimator-only flags. The tool cannot measure its own default.

This report measures it from outside the tool.

**Headline.** On the 22-frame reference bracket, at the ROI and denominator the
existing table's column was measured on, the shipping pyramid reads **0.915x**
and the README-recommended `--pyramid-gate 4.5` reads **0.746x**, against a
single unstacked frame. Both beat one frame. Both beat argmax's 1.068x. The
same instrument reproduces the table's own gate-2.0 row to 0.2%.

**Two subjects of three produced no noise row at all**, and the reason is a
finding in its own right: on a deep focus sweep there is no region that is
stationary across the bracket, so the flat-ROI statistic silently measures
recovered structure instead of noise. §7.

---

## 0. Provenance

One binary for every arm. Cross-build comparison is void in this project, so
nothing here crosses a build.

| | |
| --- | --- |
| binary | `C:\dev\strehl-out\acceptance-pins\b9b6921e\target\release\strehl.exe` |
| sha256 | `CF33AE080F438C6473034EC5078D0AB4C0AA9B53421747A3F765008DDDF0D6E6` |
| size | 9,385,984 bytes |
| corpus | `D:\personal\macro\` (read-only) |
| renders | `C:\dev\strehl-out\BUILD-PYRNOISE\renders\<subject>\` |
| harness | `experiments/BUILD-PYRNOISE/` |

`render_arms.ps1` re-asserts that sha256 before every batch and aborts on
mismatch; the assertion line appears in each render log. Every arm's full
stderr is kept beside its TIFF as `<arm>.err`.

Renders are the default binned measurement grid: 3516x2344, 16-bit, linear
camera-native, no demosaic, no sRGB. All statistics are on the **green plane**
only, `G = (G1 + G2) / 2`.

### 0.1 Why green-only is safe here

`argmax-baseline` prints no chromatic-aberration line and `stack` does. That
asymmetry would be fatal if it touched green. It does not: rendering the same
subject with `--fix-ca off` and differencing (`ca_control.py`) gives

```
R: max|d| = 3561 DN, 98.58% of pixels moved
G: max|d| =    0 DN,  0.00% of pixels moved
B: max|d| = 3129 DN, 98.55% of pixels moved
```

CA correction is **green-bit-identical**. Measured, not assumed.

---

## 1. Which backend actually ran — the banner for every arm

An argv records what the caller said; only the banner records what the program
did. Passing an estimator-only flag without `--merge` silently selects the
estimator. Every line below is verbatim from that run's own stderr.

| arm | argv (subcommand `stack`, subject dir omitted) | banner line, verbatim |
| --- | --- | --- |
| `pyr_default` | `--merge pyramid` | `merge backend   : pyramid (--merge)` |
| `pyr_g4p5` | `--merge pyramid --pyramid-gate 4.5` | `merge backend   : pyramid (--merge)` |
| `est_g2` | `--merge estimator --gate 2` | `merge backend   : estimator (--merge)` |
| `argmax` | `argmax-baseline` | `strehl argmax-baseline -- naive per-pixel argmax (NOT THE DEFAULT; a negative control)` |
| `frameNNN` | `argmax-baseline` on a one-file dir | `strehl argmax-baseline -- naive per-pixel argmax (NOT THE DEFAULT; a negative control)` |
| `pyr_default_noalign` | `--merge pyramid`, `STREHL_ALIGN=0` | `merge backend   : pyramid (--merge)` |

The gate each run actually applied, also from the banner:

| arm | banner |
| --- | --- |
| `pyr_default` | `noise gate      : 2.00 x the modelled band-noise power.` |
| `pyr_g4p5` | `noise gate      : 4.50 x the modelled band-noise power.` |
| `est_g2` | `gates           : 2.00  (UNCALIBRATED -- question 90; ...)` |

and the path each took:

* `strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)`
* `strehl stack -- regularised winner + noise-gated average (--merge estimator; reachable, NOT the default)`

The pyramid's `2.00` and the estimator's `2.00` are **different quantities** —
a multiple of modelled band-noise power versus a multiple of the focus-response
SD. They are not comparable and are not compared here.

---

## 2. Alignment — how the confound was handled

Alignment is ON by default for both merge paths and OFF for `argmax-baseline`.
The banner says what it did:

```
alignment       : ON (sidecar), reference frame 11, 22 placed / 0 refused, 0.0 s
  coverage      : field of view scaled to 0.9870 so that EVERY frame covers
                  every pixel (1.3% of width dropped, then upsampled to keep
                  the output dimensions).
alignment       : OFF -- frames are combined unregistered.
```

So an aligned arm is magnified by 1/0.9870 = **1.013171** and catmull-rom
resampled. Three things were done about it.

**(a) The magnification was verified independently.** `geometry.py` fits a
similarity transform from a patch-NCC displacement field between arms:

| pair | fitted scale | residual |
| --- | --- | --- |
| `pyr_default_noalign` vs `argmax` | 1.000000, translation 0.00 px | **0.000 px** |
| `pyr_default` vs `argmax` | 1.010910 | — |

`STREHL_ALIGN=0` lands the merge on argmax's grid **exactly**, and the fitted
magnification agrees with the banner's to 0.22%. ROIs for aligned arms are
mapped through the banner's scale about the image centre.

**(b) The resampling's own noise reduction was measured.** Interpolation is a
low-pass; an aligned arm could win the noise column without its merge doing
anything. `resample_control()` magnifies a **single frame's** flat ROI by the
same factor — no merge to help — and reports the attenuation:

| subject | scale | raw sd | high-pass sd |
| --- | --- | --- | --- |
| 109MSDCF | 1.013171 | **0.9858x** | **0.8852x** |

This is the size of the confound, and it is a bound, not a correction: scipy's
cubic spline is sharper than catmull-rom, so the real attenuation is at least
this large. **It matters.** On the legacy raw-sd column it is small (1.4%), so
the headline rows below are essentially all merge. On the high-pass column it
is 11%, so a high-pass ratio of 0.885x or above is attributable to the
resampler alone and means nothing about the merge.

**(c) A matched-site family was rendered anyway.** `pyr_default_noalign`,
`pyr_g4p5_noalign`, `est_g2_noalign`, `argmax` and the single frames all sit on
the identical raw grid (0.000 px residual). Those arms are reported, but they
are **not the product**: unregistered stacking ghosts, and the ghosting reads
as noise (`pyr_default_noalign` = 1.055x where `pyr_default` = 0.971x). They
are a control, not a row.

**The published row is the ALIGNED arm**, because alignment is what the
shipping tool does, and because the existing table's rows are aligned estimator
runs too — which is what makes the tie-back in §5 valid.

---

## 3. Commissioning the noise instrument

Nothing below was believed before these ran. `commission.py`, full log in
`commission_109MSDCF.txt`.

| id | test | bar | result |
| --- | --- | --- | --- |
| C4 | **positive control** — plant noise of known sigma, require the statistic to read `sqrt(s0^2 + sa^2)` | 1.0% | **PASS**, worst error **0.157%** over +5 / +15 / +30 / +100% plants |
| C5 | **null** — arm against a bit-identical re-render | 1.000x | **PASS**, sha256 equal, ratio **1.000000x** |
| C3 | contrast null — x2 gain and +500 DN offset | — | **PASS**, exactly **0.0e+00** |
| C6 | sabotage potency — a statistic known to be bad must MOVE on these plants | must move | **PASS**, gradient energy moves **+101.570%** |
| C7 | rule-9 flat control | 5% | **PASS**, **-0.600%** under +15% planted noise |

C5 is the strongest form of the null available: `pyr_default_null.tif` is not
merely close to `pyr_default.tif`, it is **byte-identical**, sha256
`F4FDB145E882C3EC...`. The pyramid backend is deterministic.

C6 exists so that C1 (§4) cannot pass by being numb. The plants are shown to be
potent by a statistic that is *supposed* to move on them.

---

## 4. Commissioning a detail statistic — this FAILED, and detail is not reported

Two detail statistics were already killed in this project for *rising* on blur,
and a third for failing a noise null. So the bars were fixed first: a detail
statistic must move **< 3%** under planted noise and **> 15%** under a 1 px
Gaussian blur, and must be contrast-invariant.

On **109MSDCF alone**, `f50` with a band restriction — the power-weighted
median frequency computed over `f >= 0.05` c/px — passes three of four:

| id | test | bar | result |
| --- | --- | --- | --- |
| C1 | noise null | 3% | **PASS**, moves **<= 0.129%** up to +100% planted noise |
| C3 | contrast null | 0 | **PASS**, exactly **0.0e+00** |
| C2 | **blur null** | 15% | **FAIL — 2.03%** at sigma = 1.0 px (monotone, but far short) |

The bar was not lowered. `detail_bakeoff.py` ran eight candidates against the
unchanged bars, on **all three subjects** (`bakeoff_109MSDCF.txt`). The table
below reports each candidate's **worst** behaviour across the three, which is
the only defensible way to read it:

| candidate | worst move on noise | move on 1 px blur | contrast | discrimination |
| --- | --- | --- | --- | --- |
| `f50(f_lo=0.05)` | 16.07% | 2.03% | 0.0e+00 | 0.1x |
| `f50(f_lo=0.12)` | 7.73% | 6.93% | 0.0e+00 | 0.9x |
| `f50(f_lo=0.18)` | 10.47% | 3.48% | 0.0e+00 | 0.3x |
| `f50(f_lo=0.25)` | 37.23% | 1.91% | 0.0e+00 | 0.1x |
| `spectral_centroid` | 6.60% | 5.73% | 0.0e+00 | 0.9x |
| `acf_length` | 61.88% | 11.31% | 4.4e-16 | 0.2x |
| `hf_share` | 208.43% | 84.91% | 0.0e+00 | 0.4x |
| `grad_energy` (the sabotage arm) | 101.85% | 20.59% | **1.0e+00** | 0.2x |

**None passed.** Every candidate fails the noise bar, the blur bar, or both;
the sabotage arm additionally fails contrast invariance at 1.0, which is what
it is there to demonstrate. Plant potency is confirmed: the sabotage statistic
moves 101.8% on the same noise plants, so a pass on the noise bar would have
meant something.

The single most important line is the first one. On **109MSDCF alone** the
best candidate `f50(f_lo=0.05)` moved only **0.129%** under noise and looked
like a winner with a discrimination ratio of 10.9x. Extended to three subjects
its worst noise response is **16.07%** and its discrimination collapses to
0.1x. A detail statistic commissioned on one subject would have been believed
and would have been wrong — which is exactly how this project's previous three
detail statistics died.

The underlying cause is structural: the macro tile's radial spectrum falls as
roughly `f^-3.2`, so a power-weighted median sits near the low-frequency cut
and a 1 px blur — which acts at high frequency — barely moves it, while raising
`f_lo` to reach the blur trades away the noise immunity one-for-one.

The readings also **fail to replicate across tiles**. Converted to equivalent
Gaussian blur of the reference frame, on 109MSDCF's two disjoint detail tiles:

| arm | tile 1 | tile 2 |
| --- | --- | --- |
| `pyr_default` | 0.00 px | 1.18 px |
| `pyr_g4p5` | 0.00 px | 1.23 px |
| `est_g2` | 0.00 px | 1.11 px |
| `argmax` | 0.00 px | 2.88 px |
| `frame011` | 0.00 px | 2.36 px |

On tile 1 every arm sits at the instrument floor. On tile 2 the ordering is
plausible — the merges are sharper than both argmax and a single frame — but an
ordering that appears on one tile and not another is not a measurement.

**Therefore no detail number is claimed.** The brief permits this and it is the
honest outcome. What the pyramid's noise reduction costs in sharpness is
**not measured here**, and §8 says so.

> Because detail is unmeasured, the noise ratios below are **one half of a
> trade and are not a quality metric**. A plain mean wins this column outright
> at 0.534x while destroying detail. Any use of these numbers that omits that
> sentence misrepresents them.

---

## 5. The flat-ROI admission test — a new instrument, commissioned

> **PARTIALLY RETRACTED.** This test is **missing a photometric term and
> over-rejects.** A single unstacked frame carries the bracket's per-frame level
> drift; a merged arm does not, because the merge fits and removes it. So
> `temporal` is inflated by a term neither arm ever sees. On `leaf-2-cpl` the
> README claim's own ROI reads 1.494 here and **1.017 once a whole-plane
> per-frame gain is removed**, and across 400 windows the admissible count goes
> from 1 to 17. The test should be read as `temporal` **after** removing a
> whole-plane per-frame gain. Separately, §5.1's verdicts are **not applicable
> to arm-vs-arm ratios between two merges of the same bracket** at all: measured
> there, admission predicts the error at corr −0.002. The exclusions below were
> in the safe direction — no published row rests on the defect — but the stated
> reason for them is not established. Full measurement, controls and mechanism:
> [`BUILD-PYRNOISE-ADJUDICATION.md`](BUILD-PYRNOISE-ADJUDICATION.md) §3 and §4.

The flat-ROI protocol assumes the region carries noise and nothing else. That
assumption is never checked; the ROI is picked by a low-high-pass argmin and
trusted. On a deep focus sweep it is false, and falsifying it changes the
answer by more than the effect being measured.

The test (`admission.py`): two independent estimates of the same per-pixel
noise must agree across the single unstacked frames —

* **temporal**: sd across frames at a fixed pixel, averaged over pixels
* **spatial**: sd of `x - box9(x)` within one frame, averaged over frames

Ratio 1.00 for a stationary region; above 1 when the scene at that pixel
changes frame to frame. **Bar fixed before any subject was scored: 1.30.**

`commission_admission.py` (`commission_admission.txt`):

| id | test | requirement | result |
| --- | --- | --- | --- |
| A1 | synthetic null — pure Gaussian noise | ratio in [0.90, 1.15] | **PASS, 0.9883** |
| A4 | a real admissible ROI still passes | <= 1.30 | **PASS, 1.1171** |
| A2 | planted drift on a detailed ROI | must reject | **PASS**, rejects at **4 px** |
| A3 | planted frame-dependent structure | must reject | **PASS**, rejects at **50 DN = 1.23x the noise sd** |

The thresholds are reported as measured, not as hoped: A2 needs 4 px and A3
needs structure at 1.23x the noise sd. The test is **deliberately blind** to
translation of a *featureless* region — there is nothing there to move — so a
failure means non-stationary **content**, and this report does not claim to
separate focus breathing from drift.

Both bugs found while commissioning are recorded rather than hidden: the first
version of A3 cropped a bare tile, the high-pass estimator returned NaN, and
`NaN <= 1.30` evaluated False and printed as a rejection — a **fake pass**. The
fix asserts finiteness. The first version of A2 planted motion on a flat region,
where it is not potent, and correctly failed.

### 5.1 Verdicts

| subject | frames | chosen ROI | 5 flattest windows | admissible |
| --- | --- | --- | --- | --- |
| **109MSDCF** | 22 | **1.117** | 1.12, 1.10, 1.09, 1.08, 1.15 | **5 / 5 — PASS** |
| 109MSDCF at M2's historical ROI | 22 | **1.033** | — | **PASS** |
| leaf-2-cpl | 182 | 1.476 | 1.48, 1.55, 1.95, 2.05, 3.11 | **0 / 5 — FAIL** |
| tweezers-cpl | 100 | 4.590 | 4.59, 4.36, 4.54, 4.43, 4.61 | **0 / 5 — FAIL** |

Only 109MSDCF yields a publishable noise row. §7.

---

## 6. The measurement

Subject **109MSDCF**, the 22-frame reference bracket the existing table was
built on. ISO 160. Denominator **frame011** = `DSC00020.ARW`, which is also the
frame the aligner chose as its own reference and the frame M2 used.

ROIs were chosen on the **mean of the arms**, never on one arm, over 444
guarded 256x256 windows on a stride-64 grid; windows touching the 2nd or 99.5th
percentile of level are excluded, and a window must clear the border on **both**
grids so that magnification cannot map it into the aligned arm's extrapolated
edge.

### 6.1 The row for the README — M2's ROI, the table's own measurement

This is the ROI (`2272,1344,256,256`), denominator and statistic the existing
column was measured on: **legacy raw spatial sd ratio, green plane, camera
linear, against a single unstacked frame.** It passes admission at 1.033.

| arm | legacy raw sd | ratio | high-pass ratio |
| --- | --- | --- | --- |
| `frame011`, unstacked | 124.473 DN | **1.000x** | 1.000x |
| `argmax-baseline` | 132.916 DN | **1.068x** | 1.079x |
| `--merge estimator --gate 2` | 110.498 DN | **0.888x** | 0.820x |
| **`--merge pyramid` (default gate 2.0)** | 113.950 DN | **0.915x** | 0.780x |
| **`--merge pyramid --pyramid-gate 4.5`** | 92.911 DN | **0.746x** | 0.466x |

**The tie-back.** The README's table gives `0.890x` for the estimator at gate
2.0. This external instrument, which shares no code with the tool, reads
**0.888x** — a **0.2%** agreement. The instrument reproduces a known row.

The argmax row reads **1.068x**, not the table's **1.253x**. That is not a
discrepancy introduced here: M53 already re-measured today's binary at 1.068x
on this ROI. The table's 1.253x is M2's historical number from a different
pipeline. **The 1.253x in the README is stale**, and any row added beside it
should say so.

### 6.2 The independently re-chosen ROI, and robustness

The ROI chosen fresh on the mean of the arms lands at `(1416, 264)`. Reported
as the **median over the 5 flattest windows**, so no single window carries it:

| arm | aligned | legacy median | [min .. max] | high-pass median | [min .. max] |
| --- | --- | --- | --- | --- | --- |
| `frame011` | — | 1.000x | — | 1.000x | — |
| `argmax-baseline` | no | 1.013x | [0.924 .. 1.015] | 1.036x | [0.743 .. 1.039] |
| `--merge estimator --gate 2` | yes | 0.966x | [0.949 .. 0.973] | 0.689x | [0.670 .. 0.721] |
| **`--merge pyramid` default** | yes | **0.971x** | [0.965 .. 0.980] | **0.655x** | [0.639 .. 0.712] |
| **`--merge pyramid --pyramid-gate 4.5`** | yes | **0.961x** | [0.960 .. 0.966] | **0.390x** | [0.367 .. 0.628] |
| `--merge pyramid` default, `STREHL_ALIGN=0` | no | 1.055x | [1.035 .. 1.079] | 1.219x | [0.967 .. 1.228] |
| `--merge pyramid 4.5`, `STREHL_ALIGN=0` | no | 1.026x | [1.018 .. 1.040] | 0.431x | [0.402 .. 0.663] |
| `--merge estimator --gate 2`, `STREHL_ALIGN=0` | no | 0.983x | [0.927 .. 0.990] | 0.687x | [0.547 .. 0.706] |

The **ordering is identical to §6.1** — pyramid-4.5 best, pyramid-default and
estimator-gate-2 close behind, argmax worst and above 1.0 — so the conclusion
does not depend on which ROI was chosen. The **magnitudes differ** (0.971x here
versus 0.915x at M2's ROI) because the legacy raw sd includes scene structure,
which is identical across arms and dilutes every ratio toward 1.0; this window
has a smooth gradient (raw sd 172 DN at a high-pass energy of 19.9) and dilutes
harder. M53 documents the same compression. This is why §6.1 is the row to
publish: it is the one that is commensurable with the existing table.

Single-frame denominator distribution, since one frame is a free choice worth
1.60x in this corpus (fact 441): over all 22 frames the legacy raw sd is
median 170.554 DN, range 165.965–172.990 — a spread of only **1.042x** — and
frame011 sits at 172.459 DN, the high end. Choosing the denominator differently
moves the published ratios by at most about 4%, and in the direction that would
make the pyramid look *better*, not worse.

### 6.3 Reading the high-pass column

Against the §2(b) resample control, high-pass ratios of 0.885x or above are
attributable to interpolation alone. `pyr_default` at 0.655x and `pyr_g4p5` at
0.390x are well beyond it; `argmax` at 1.036x is worse than a single frame even
before the resampler is credited — but argmax is unaligned, so it gets no
resampler credit and its number is clean.

---

## 7. What could not be measured, and why

**Two of three subjects produced no noise row.** `leaf-2-cpl` (182 frames) and
`tweezers-cpl` (100 frames) were rendered in full — every arm, rc=0, banners
captured — and then **disqualified by the admission test at every one of the 5
flattest windows** (1.48–3.11 and 4.36–4.61 against a bar of 1.30).

This is not a harness failure. It is what the admission test exists to catch,
and the raw numbers show exactly why publishing them would have been wrong. On
`leaf-2-cpl` the legacy ratio for a single arm spans **0.775x to 3.224x** across
five adjacent windows of the same "flat" region — the statistic is not
measuring a property of the merge at all. It is measuring that a deep focus
sweep has no region that is stationary across the bracket: a patch that looks
smooth in each individual frame is smooth **for a different reason in each
frame** (it is out of focus in most of them), so the merged arm legitimately
contains structure the single frame does not, and the flat-ROI statistic scores
that recovered structure as noise. The arm that recovers the most real detail
loses hardest, which is exactly backwards.

The consequence for the corpus is larger than this report: **the flat-ROI noise
statistic underpinning the README's entire table is only valid on the shallow
22-frame bracket.** It was never checked on a deep sweep, and it does not
survive one. The existing table should be read as a statement about 109MSDCF.

Also not measured:

* **Detail cost.** §4. No detail statistic could be honestly commissioned, so
  what the pyramid's noise reduction costs in sharpness is unknown. The tile-2
  readings hint the merges are sharper than both argmax and a single frame, but
  that does not replicate on tile 1 and is not a claim.
* **Whether `--pyramid-gate 4.5`'s large win is free.** It reads 0.746x versus
  the default's 0.915x. A higher gate admits fewer frames into the fine bands,
  which reduces noise *and* can reduce recovered detail. Without a commissioned
  detail statistic the trade cannot be priced, and 0.746x must not be read as
  "better".
* **`n_eff` for the pyramid.** The backend does not compute it. The `n_eff`
  column of the README's table has no pyramid entry and this report cannot
  supply one; the pyramid's banner reports per-band averaged fractions
  (`averaged: 76.8% 0.2% 0.0% ... 100.0%`) which are a different quantity.
* **Anything below the single-frame spread.** The 22 frames span 1.042x on the
  legacy statistic, so differences smaller than roughly 4% are not resolved.

---

## 8. Verdict

**Does the shipping pyramid backend beat a single unstacked frame on noise?**
**Yes.** 0.915x at its default `--pyramid-gate 2.0`, on the 22-frame reference
bracket, at the table's own ROI and denominator. The independently re-chosen
ROI agrees in ordering at 0.971x. It is not a large win, but it is on the right
side of 1.0, and it is the first measurement of the shipping backend's noise
that exists.

**Does it beat argmax?** **Yes, decisively.** argmax reads 1.068x — worse than
not stacking, as the README already says of selection. The pyramid at its
default is 14% better than argmax; at `--pyramid-gate 4.5` it is 30% better.

**Does it beat the estimator the README's table describes?** At matched gates,
approximately a tie and slightly behind: pyramid-default 0.915x versus
estimator-gate-2 0.888x. At the configuration the README actually tells users to
run, the pyramid is **ahead of every estimator row in the table**: 0.746x beats
gate 4.0's 0.788x. The gates are different quantities and this is a comparison
of shipped configurations, not of gate values.

**At what cost in detail?** **Unmeasured**, and the report will not guess. Three
detail statistics have now failed commissioning in this project and a fourth
(`f50`) failed here. Until one survives, the noise column is half a trade.

**The one sentence that must travel with these numbers:** a plain mean wins this
column outright at 0.534x while destroying detail, so a lower flat-ROI noise
ratio is not evidence of a better stack.

---

## 9. Reproduction

```powershell
cd experiments/BUILD-PYRNOISE
./render_arms.ps1 -Subject 109MSDCF -SingleFrames all   # asserts the binary sha256
python commission.py                                     # C1..C7, the noise instrument
python commission_admission.py                           # A1..A4, the admission test
python detail_bakeoff.py                                 # the eight-candidate bake-off
python geometry.py                                       # alignment grid + magnification
python ca_control.py                                     # green-bit-identity of CA
python measure.py 109MSDCF leaf-2-cpl tweezers-cpl
```

Logs kept beside the scripts: `commission_admission.txt`, `bakeoff_109MSDCF.txt`,
`measured_final.txt`, `measured_109.txt`. Per-arm stderr and the machine-readable
`_measured.json` are under `C:\dev\strehl-out\BUILD-PYRNOISE\renders\<subject>\`.

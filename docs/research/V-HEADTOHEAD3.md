# V-HEADTOHEAD3 — tone-neutral competitive baseline

> **CORRECTION TO THE FIRST COMMITTED REPORT.**  Independent report
> verification found a second same-bracket Zerene PMax render that the author
> had seen in the file search but incorrectly grouped with inadmissible marker
> captures.  The original two-render census and “no fine-band winner” headline
> were false.  They are superseded below.
>
> **VERDICT: NOT ROBUST across comparator input development.**  On the same 63
> captures, strehl is unresolved against Zerene built from Lightroom
> `Sharpness=0` inputs at 0.20–0.30 cyc/px, but **trails** Zerene built from
> `Sharpness=40`, colour-NR 25 inputs: `R=0.3992
> [0.3381,0.4720]` at 0.20–0.25 and `R=0.2834
> [0.2178,0.3696]` at 0.25–0.30.  The latter changes from `0.9735` to `0.2834`
> across those two available PMax renders.  Every focus-stack-fork band
> remains unresolved.
>
> The checker agrees on both sharpened-Zerene fine-band trails, but only 16/18
> classes overall.  Coffee geometry also remains disagreed: 1.036 versus 1.044
> (0.772%, beyond the preregistered 0.5% bar).

Preregistration:
[`experiments/V-HEADTOHEAD3/PREREGISTRATION.md`](../../experiments/V-HEADTOHEAD3/PREREGISTRATION.md).
The first two amendments in that file predate outcome measurement.  The second is
substantive: synthetic commissioning proved that the original flat-spectrum
ratio subtraction amplified additive noise by 25,494×.  It was replaced,
before real outcomes, by a conservative same-direction flat veto.  A clearly
labelled post-outcome census correction adds the omitted comparator without
changing any band, threshold, ROI or verdict rule.

## 1. Why this measurement exists

The 17–27% detail deficit reported by
[`V-HEADTOHEAD.md`](V-HEADTOHEAD.md) is retracted.  The standing account in
[`V-HEADTOHEAD2.md`](V-HEADTOHEAD2.md), including its registration-sign
correction banner, shows that the old comparator tone curve explains 94.8%,
109.9%, and 267.1% of the apparent three-band deficit.  A curve fitted using
only 4×4 averages reproduced the disputed high-frequency power despite having
no information above 0.125 cyc/px.  Raw render power was therefore not an
admissible competitive statistic.

This lane asks the narrower defensible question: how much **ordinal rendered
structure** does each pipeline place in each spatial band after removing all
strictly monotone point-tone information?  It does not call that quantity MTF
or ground-truth fidelity.

## 2. Comparator renders and frozen provenance

Three usable render pairings exist:

| subject | strehl shipped master | comparator | bracket |
| --- | --- | --- | --- |
| `113MSDCF`, no input sharpening | `C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff` | `D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif` (Zerene PMax) | 63 frames |
| `113MSDCF`, sharpened inputs (post-registered) | same strehl master | `D:\edited\macro\test\2026-05-07-21.31.06 ZS PMax.tif` (Zerene PMax) | same 63 frames |
| `coffee-bean` | `C:\dev\strehl-out\DELIVER-V6\masters\coffee-bean.tiff` | `C:\dev\macro\out\coffee-bean\stack.tif` (focus-stack fork) | 105 frames |

No Helicon render was found under `C:\dev`, `D:\edited`, or
`D:\personal\macro`.  Extra Zerene *marker* files exist, but the two prior
head-to-head reports establish that those captures do not match a strehl
bracket, so they are inadmissible.

The two 113 TIFF input sets have identical filenames
`DSC00001`–`DSC00063` and matching embedded `OriginalDocumentID` values 63/63.
Their Lightroom XMP settings are uniform but different:

| Zerene input directory | `Sharpness` | `ColorNoiseReduction` | `Contrast2012` |
| --- | ---: | ---: | ---: |
| `D:\edited\macro\test2` | 0 | 0 | +100 |
| `D:\edited\macro\test` | 40 | 25 | +100 |

The full-file hash control read:

| file | bytes | SHA-256 |
| --- | ---: | --- |
| strehl `113MSDCF.tiff` | 197801290 | `4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F` |
| Zerene PMax, sharpening 0 | 196453660 | `B240FE4016E97EBB194497B2798A095C63C490C4FFF54018D48D34C7523719A0` |
| Zerene PMax, sharpening 40 | 196453660 | `4D490F71EF63DA33758A49BF583AD2166CD014A5401ED64EDB5E5EDCABB47A3E` |
| strehl `coffee-bean.tiff` | 197801290 | `F38CA50ED1A680FA4DBCDD8D0513BE538DD31634B4E89AC6A34885944790A2EC` |
| focus-stack fork | 393326272 | `8636C20D73CA0CB1F57DB89BF8553ABC166E0FBC517E5C62A07C74DEE509066E` |

The strehl masters are not moving-HEAD renders.  The retained DELIVER-V6
manifest and [`experiments/DELIVER-V6/BANK-33.md`](../../experiments/DELIVER-V6/BANK-33.md)
record:

```text
exe       C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe
SHA-256   2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7
commit    6af834dac08d6605aee7ea3ad75809fdf6313770
command   <exe> stack <absolute source directory> -o <absolute master> --srgb
env       private STREHL_CACHE_DIR; all other STREHL_* unset
```

This is consequently a **pipeline comparison**: raw-fed strehl versus
Lightroom-TIFF-fed comparators, measured on strehl's shipped `--srgb` master.
It is not a merge-algorithm isolation.

## 3. Statistic and tone-invariance theorem

Only each render's native green plane is used.  In each native ROI, pixel
values are replaced by average ranks

```text
q_j = (rank_j - (N+1)/2) / N .
```

After DC removal and a separable Hann window, `A_k` is FFT power in band `k`
divided by total power across the six admitted bands.  The bands in
cycles/strehl-pixel are:

```text
0.02–0.05  0.05–0.10  0.10–0.20
0.20–0.25  0.25–0.30  0.30–0.40
```

Measurement pixels are never resampled.  If scale `s` expands comparator
pixels onto the strehl grid, a 512-pixel strehl ROI is paired with
`round(512/s)` native comparator pixels and comparator band edges are
multiplied by `s`.

For any strictly increasing point map `phi`,
`x_a < x_b` if and only if `phi(x_a) < phi(x_b)`, while equal values remain
equal.  Thus the average ranks, registration ranks, ROI gates and partitions,
all `A_k`, and the paired geometric-mean ratio

```text
R_detail = exp(mean_i(log(A_strehl,i / A_comparator,i)))
```

are unchanged.  `R>1` favours strehl.  Percentile 95% intervals use 10,000
paired-ROI bootstrap draws, seed `20260902`.

No nontrivial statistic can remain invariant to an arbitrary *non-decreasing*
map that may collapse the image to a constant.  Clipping, newly created
quantisation ties, channel mixing, spatially varying tone and non-monotone
local contrast are exact exceptions.  Rail exclusion, tie census and plants
bound these exposures; they do not turn them into a theorem.

## 4. Commissioning

The investigator-favoured bias was declared as **strehl leads**.  Ordinal power
can be fooled in that direction by noise, sharpening, ringing or resampling,
and in the other direction by denoising, blur or rank ties.

The author's first synthetic run was not green: 15/16 controls passed while
all 9 then-present plants went RED.  That exact early count is not retained in
a committed log, so it is MEASURED but not independently reproducible.  The
failed flat subtraction itself remains executable and reads a 25,493.7 maximum
fine-band departure instead of the required ≤5%.  That failure caused the
preregistered amendment; it was not waived.

The final commissioned suite is:

| arm | controls | deliberate defect plants | decisive reading |
| --- | ---: | ---: | --- |
| operators and synthetic estimator | 22/22 GREEN | 15/15 RED | rank oracle exact; all six shifts exact |
| frozen hashes | 1/1 GREEN | 1/1 RED | one-nibble hash plant rejected |
| real-ROI tone/potency | 3/3 GREEN | 2/2 RED | ordinal move `0`; raw move `30.4%` |
| 113 full 96-ROI real tone curves | 3/3 GREEN | — | affine, gamma 3, logistic: every end-to-end delta `0` |
| coffee full 96-ROI real tone curves | 3/3 GREEN | — | independently run; every end-to-end delta `0` |
| sharpened-input Zerene real tone curve | 1/1 GREEN | — | gamma 3; every end-to-end delta `0` |
| **total** | **33/33 GREEN** | **18/18 RED** | every deliberate plant fired |

The registration fixture plants `(0,0)`, `(1,0)`, `(0,-1)`, `(2,3)`,
`(-3,2)`, and `(5,-5)`.  Every returned correction was exactly the negative
displacement and made the untouched source and corrected interior
byte-for-byte equal.  Wrong-sign and no-op implementations both went RED.

Other potency readings matter to interpretation:

* Gaussian sigma 0→2 removed 99.8% of combined ordinal 0.20–0.40 share, so
  the estimator can read fully present blur rather than saturating at a low
  structural ceiling.
* Unsharp masking raised combined 0.25–0.40 share by 49.3%.
* A down/up resample moved one band by 77.5%.
* A 12-bit quantisation changed unique/largest-tie occupancy from
  `65536 / 0.00153%` to `3167 / 0.0961%`; 1%/99% clipping produced a 1.001%
  largest tie.
* The author observed the fixed external 4×4 rank oracle catch a wrong
  expected-rank fixture in the independent checker before measurement.  That
  pre-fix output is not committed; the corrected checker is executable and
  passes its independent rank and registration predicates.

Independent verification ran all three real-pixel tone curves on the fork,
and gamma 3 was also run on the post-registered sharpened Zerene arm.  Every
run returned zero geometry-rank, ROI-decision, partition, per-ROI and
bootstrap-effect movement.

## 5. Geometry, registration and ROI populations

Scale is fitted on every eighth native green pixel **after ranking**, so the
fit itself cannot see strict point tone.  Registration resampling is used only
to find geometry; every reported spectrum reads native pixels.

| pair | author scale | prior scale | checker scale | preregistered agreement |
| --- | ---: | ---: | ---: | --- |
| 113/Zerene, sharpening 0 | 1.0020 | 1.0020 | 1.0020 | PASS, exact |
| 113/Zerene, sharpening 40 | 1.0030 | — | 1.0080 | PASS at 0.4985% |
| coffee/fork | 1.0360 | 1.0340 | 1.0440 | **FAIL**, author/checker differ 0.772% |

The author's coffee fit agrees with the prior independently reported 1.035063
to 0.09%, but that fact does not erase the new checker disagreement.  Both
fits have interior maxima.  Per the preregistration, the disagreement is
published rather than reconciled.

Real sign commissioning also passes:

| pair | no registration | wrong sign | corrected sign |
| --- | ---: | ---: | ---: |
| 113/Zerene, sharpening 0 | 0.4000 | 0.2918 | **0.6151** |
| 113/Zerene, sharpening 40 | 0.2799 | 0.2553 | **0.3451** |
| coffee/fork median rank correlation | 0.1894 | 0.1253 | **0.9530** |

The fixed 512-pixel grid produced:

| pair | candidates | eligible | detail (top half) | low-texture/flat (bottom quartile) | exclusions |
| --- | ---: | ---: | ---: | ---: | --- |
| 113/Zerene, sharpening 0 | 96 | 81 | 41 | 21 | 14 registration-null, 1 rail |
| 113/Zerene, sharpening 40 | 96 | 55 | 28 | 14 | 34 registration-null, 6 registration-gain, 1 rail |
| coffee/fork | 96 | 55 | 28 | 14 | 25 rail, 9 registration-null, 7 registration-gain |

The independent checker retains 81/41/21 on unsharpened 113, 56/28/14 on
sharpened 113, and 54/27/14 on coffee.  Exact ROI centres, cut values, reasons,
tie groups and quadrant estimates are printed in `RESULT_JSON`/`CHECK_JSON` by
the commands in §9.

## 6. Competitive result

The preregistered practical bar is 5%.  A provisional LEADS/TRAILS class needs
the corresponding 95% bound beyond 1.05 or `1/1.05`.  If the low-texture
interval resolves in the same direction, the result is downgraded to
UNRESOLVED (FLAT VETO).  All bands passed blur sensitivity; no leave-one-out
or quadrant reversal fired.

### 6.1 Strehl versus Zerene PMax, Lightroom sharpening 0 (`113MSDCF`)

| cyc/px | `R_detail` [95% CI] | `R_flat` [95% CI] | verdict |
| --- | --- | --- | --- |
| 0.02–0.05 | **1.0833 [1.0534, 1.1114]** | 0.7617 [0.7196, 0.8071] | **STREHL LEADS** |
| 0.05–0.10 | 0.9239 [0.9029, 0.9452] | 0.8518 [0.8058, 0.8998] | UNRESOLVED — flat veto |
| 0.10–0.20 | **0.8842 [0.8420, 0.9311]** | 1.1680 [1.1035, 1.2308] | **STREHL TRAILS** |
| 0.20–0.25 | 0.8721 [0.7817, 0.9745] | 2.3833 [2.1009, 2.6967] | UNRESOLVED |
| 0.25–0.30 | 0.9735 [0.8339, 1.1406] | 3.2530 [2.7675, 3.8098] | UNRESOLVED |
| 0.30–0.40 | 1.0264 [0.8564, 1.2305] | 3.1692 [2.6437, 3.7543] | UNRESOLVED |

On this development rung, strehl's resolved Zerene result changes sign with band: +8.3% ordinal
share at 0.02–0.05 and −11.6% at 0.10–0.20.  There is no resolved Zerene
fine-band deficit or lead above 0.20 cyc/px **on this rung**.

### 6.2 Strehl versus Zerene PMax, Lightroom sharpening 40 / colour NR 25

This arm was discovered by independent verification after the first report.
It uses the same 63 source identities and the unchanged preregistered
instrument.  Because the author and checker disagree on the 0.02–0.05 and
0.10–0.20 flat vetoes, those two final classes are NOT ROBUST; they agree on
both decisive fine-band trails.

| cyc/px | author `R_detail` [95% CI] | author `R_flat` [95% CI] | author / checker class |
| --- | --- | --- | --- |
| 0.02–0.05 | 1.2856 [1.2448, 1.3260] | 1.2243 [1.0395, 1.4271] | LEADS / FLAT VETO — **NOT ROBUST** |
| 0.05–0.10 | 0.9999 [0.9664, 1.0336] | 1.0285 [0.9386, 1.1221] | UNRESOLVED / UNRESOLVED |
| 0.10–0.20 | 0.7538 [0.7223, 0.7887] | 0.8478 [0.7552, 0.9620] | TRAILS / FLAT VETO — **NOT ROBUST** |
| 0.20–0.25 | **0.3992 [0.3381, 0.4720]** | 0.7395 [0.5011, 1.0546] | **TRAILS / TRAILS** |
| 0.25–0.30 | **0.2834 [0.2178, 0.3696]** | 0.6365 [0.3860, 1.0007] | **TRAILS / TRAILS** |
| 0.30–0.40 | 0.2018 [0.1461, 0.2797] | 0.4820 [0.2796, 0.7872] | FLAT VETO / FLAT VETO |

At 0.25–0.30, the two PMax outputs change `R_detail` from 0.9735
(unsharpened-input rung) to 0.2834 (sharpened/NR-input rung), a 70.9% ratio
change.  Point-tone invariance cannot and should not remove spatial sharpening
or denoising.  Exact Zerene run parameters are not retained, so the input XMP
is the documented difference rather than a complete causal isolation.  A
single app-level “strehl versus Zerene” number is unsupported by these files.

### 6.3 Strehl versus focus-stack fork (`coffee-bean`)

| cyc/px | `R_detail` [95% CI] | `R_flat` [95% CI] | verdict |
| --- | --- | --- | --- |
| 0.02–0.05 | 0.9466 [0.9369, 0.9563] | 0.8524 [0.7783, 0.9156] | UNRESOLVED |
| 0.05–0.10 | 0.9984 [0.9886, 1.0095] | 0.9211 [0.8702, 0.9662] | UNRESOLVED |
| 0.10–0.20 | 1.1302 [1.1061, 1.1560] | 1.1125 [1.0732, 1.1647] | UNRESOLVED — flat veto |
| 0.20–0.25 | 1.2975 [1.2426, 1.3568] | 1.2891 [1.2282, 1.3637] | UNRESOLVED — flat veto |
| 0.25–0.30 | 1.3915 [1.3034, 1.4850] | 1.3560 [1.2718, 1.4433] | UNRESOLVED — flat veto |
| 0.30–0.40 | 1.3710 [1.2099, 1.5342] | 1.4079 [1.2102, 1.6413] | UNRESOLVED — flat veto |

The tempting conclusion is that strehl leads the fork by 30–39% in the fine
bands.  The real flat control reads essentially the same 29–41% direction, and
the sharpening plant proves that ordinal share can rise without added faithful
detail.  Calling those rows wins would repeat the project's historical error
in a new statistic.  They are unresolved.

### 6.4 Independent checker

The checker reimplements ranks with `numpy.unique`, registration with
`skimage.phase_cross_correlation`, geometry with `skimage.resize`, the spectrum
with a weighted real FFT, and uses bootstrap seed `20260903`.  It imports no
author measurement module and carries no frozen outcome.

| pair | checker `R_detail` by ascending band | final-class agreement |
| --- | --- | ---: |
| 113/Zerene, sharpening 0 | 1.0832, 0.9240, 0.8843, 0.8722, 0.9737, 1.0268 | 6/6 |
| 113/Zerene, sharpening 40 | 1.2842, 0.9991, 0.7565, 0.3990, 0.2847, 0.2018 | 4/6 |
| coffee/fork | 0.9428, 0.9982, 1.1432, 1.3392, 1.4369, 1.3756 | 6/6 |

All 18 author/checker point ratios lie within the sum of their 95%
half-widths; the largest point-ratio difference is 3.3%.  Final-class
agreement is 16/18.  Class agreement on coffee does not repair its scale gate:
outcome class is robust to the two defensible geometry choices, while exact
coffee geometry remains not agreed.

### 6.5 Per-band standing across all available renders

| cyc/px | standing |
| --- | --- |
| 0.02–0.05 | **NOT ROBUST:** lead on unsharpened Zerene; checker disagreement on sharpened Zerene; fork unresolved |
| 0.05–0.10 | UNRESOLVED on all three renders |
| 0.10–0.20 | **NOT ROBUST:** trail on unsharpened Zerene; checker disagreement on sharpened Zerene; fork flat-vetoed |
| 0.20–0.25 | **NOT ROBUST across development:** unresolved on unsharpened Zerene, trail on sharpened Zerene, fork flat-vetoed |
| 0.25–0.30 | **NOT ROBUST across development:** unresolved on unsharpened Zerene, trail on sharpened Zerene, fork flat-vetoed |
| 0.30–0.40 | UNRESOLVED on all three renders |

## 7. What this does and does not establish

It establishes that point tone no longer determines the answer.  It also
establishes that the **available rendered pipeline is not stable across its
documented input-development rungs**: the same program family and same 63
capture identities move from unresolved to large, independently reproduced
strehl trails at 0.20–0.30 between the two PMax files.  Therefore the correct
competitive verdict is NOT ROBUST, not a single win or deficit.

The old 17–27% deficit remains retracted; this does not reinstate its raw-power
method or number.  The new 60.1% and 71.7% point trails against the sharpened
PMax render are results of a whole rendered pipeline, not causal estimates of
strehl's merge.  Raw development, demosaic, local contrast, denoising and
sharpening remain inside the compared pipelines.  The `--srgb` master's
demosaic and delivery tone also mean this is not the linear-resolution arm
that the earlier report preferred.

### What changes in Rust

**Nothing in `src/` or `crates/` changes.**  This lane was explicitly
read-only with respect to Rust, and its resolved deficits change with
comparator preprocessing rather than being causally attributable to a stacker module.
Changing merge, alignment or demosaic code from this evidence would be
overreach.  The concrete change is to competitive validation: future detail
claims must use the rank/native-grid instrument in
`experiments/V-HEADTOHEAD3/` (or a truth-referenced successor), never raw render
power across independently toned outputs.

### Could not verify

* Helicon performance: no usable Helicon render exists in the searched roots.
* A physical resolution/MTF winner, or whether extra ordinal structure is
  faithful detail rather than sharpening.
* Invariance to clipping, spatially varying/local tone, channel mixing, or
  quantisation-created ties; the theorem covers strictly increasing point maps.
* Coffee's exact scale within the preregistered author/checker tolerance.
* Current moving-HEAD strehl performance; the measured deliverable is pinned to
  `6af834dac08d`.
* An algorithm-only comparison on identically developed linear inputs.
* Exact comparator application settings beyond the retained output files and
  prior reports; neither comparator has a complete reproducible run manifest.

## 8. Proposed corpus facts

* **P1.** Three admissible render pairings survive: two Zerene PMax outputs
  from the same 63-frame `113MSDCF` identities but different Lightroom
  sharpening/NR rungs, plus the focus-stack fork on the 105-frame coffee-bean
  bracket; no usable Helicon render was found.
* **P2.** Average-rank native-grid band share is exactly invariant to strictly
  increasing point tone.  Affine, gamma-3 and logistic real end-to-end plants
  moved geometry ranks, ROI decisions, partitions and `R_detail` by zero; raw
  power moved 30.4%.
* **P3.** Registration returned the exact negative of six planted shifts.
  Corrected real median correlation was 0.6151, 0.3451 and 0.9530 versus
  wrong-sign 0.2918, 0.2553 and 0.1253.
* **P4.** Against unsharpened-input Zerene, strehl leads at 0.02–0.05
  (`1.0833 [1.0534,1.1114]`), trails at 0.10–0.20
  (`0.8842 [0.8420,0.9311]`), and is unresolved above 0.20.  Against
  sharpened-input Zerene it trails at 0.20–0.25 (`0.3992
  [0.3381,0.4720]`) and 0.25–0.30 (`0.2834 [0.2178,0.3696]`).
* **P5.** The checker agrees on 16/18 verdict classes, including both
  sharpened-Zerene fine trails.  Coffee geometry differs 1.036 versus 1.044
  (0.772%, FAIL); sharpened-Zerene geometry differs 1.003 versus 1.008
  (0.4985%, PASS).
* **P6.** No Rust change follows because no resolved result isolates a stacker
  module; this lane changes the admissible competitive instrument instead.
* **P7.** The app-level baseline is NOT ROBUST: at 0.25–0.30 the same scene's
  ratio changes from 0.9735 to 0.2834 across the Lightroom development ladder.

## 9. Reproduction commands

Run from
`C:\dev\blog\death-of-software\projects\strehl\experiments\V-HEADTOHEAD3`
with Python 3.12.10, NumPy 2.4.4, SciPy 1.17.1, tifffile 2026.5.2 and
scikit-image 0.26.0:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH=(Get-Location).Path
python -B commission.py
python -B commission.py --hashes
python -B commission.py --real
python -B tone-check.py 113
python -B tone-check.py 113-sharp --curves gamma3
python -B geometry.py
python -B measure.py 113
python -B measure.py 113-sharp
python -B measure.py cb
python -B check.py 113 113-sharp cb
```

No command invokes strehl or reads a `STREHL_*` variable; no capture directory
is written.  `measure.py` prints complete `RESULT_JSON`, including ROI centres
and diagnostics.  `check.py` independently prints `CHECK_JSON`.

Research commits through the independently verified instrument:

```text
5d85d8e12ae35dee46568d31e1a662a4b451ecf4  initial preregistration
11ed554e2a736789813074c642c536b967c3a16a  pre-outcome registration-gate amendment
48c81eebba999e8c2d76bc7460ded792408a8708  failed-control amendment
9f08a4fa5602055db4b764caf6bb35e914604b22  instrument and independent checker
fec4a572d140997cc7b7be673c9719c68fa7d2b3  close verifier-found gaps
403693a1ce9a673d2181b1f3ed4bb0ada6fd65bd  preserve NOT SENSITIVE precedence
a050d6861d5ab7655fe08a85c9fd1d3a29a2b1aa  first report (superseded census/headline)
55a53bccc9458b950f8176716836afe18378e9a9  disclose post-outcome comparator
3c108fac1cde4af7d92b2629e0d2f2abfcbadba0  add omitted Zerene arm
```

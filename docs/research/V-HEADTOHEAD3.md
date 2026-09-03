# V-HEADTOHEAD3 — tone-neutral competitive baseline

> **CORRECTION / EXHAUSTIVE CENSUS.**  Two independent verification passes
> broke the comparator census in the earlier committed reports.  The first
> found a second 113 Zerene render.  The second proved that three previously
> rejected Zerene marker renders match `119MSDCF`, and found three focus-stack
> marker renders.  The focus-stack filenames then caused one more wrong-subject
> assumption: the preregistered geometry gate rejected 113 (score 0.0802,
> 160.6 px residual), while the unchanged fit accepted 119 (score 0.9832,
> 1.33 px residual).  That correction was committed before reading those
> outcome spectra.  The two- and three-pair accounts at commits `a050d686` and
> `08a11d52` are superseded below.
>
> **VERDICT: NOT ROBUST across comparator development.**  Nine unique-byte
> pairings survive.  The six newly admitted 119 arms produce no resolved win
> or loss after the real flat-region veto.  The decisive instability remains
> on the same 63-frame 113 bracket: at 0.25–0.30 cyc/px, strehl is unresolved
> against PMax built from Lightroom `Sharpness=0` inputs,
> `R=0.9735 [0.8339,1.1406]`, but trails PMax built from `Sharpness=40`,
> colour-NR 25 inputs, `R=0.2834 [0.2178,0.3696]`.  Point tone cannot cause
> that change; spatial preprocessing can.

Preregistration:
[`experiments/V-HEADTOHEAD3/PREREGISTRATION.md`](../../experiments/V-HEADTOHEAD3/PREREGISTRATION.md).
The registration-gate and failed-flat-control amendments predate all real
outcomes.  Every later census/provenance correction is labelled post-outcome
and reuses the frozen bands, thresholds, ROI rules and verdict rules.

## 1. Question and scope

The 17–27% detail deficit in
[`V-HEADTOHEAD.md`](V-HEADTOHEAD.md) is retracted.  The standing correction in
[`V-HEADTOHEAD2.md`](V-HEADTOHEAD2.md) shows that comparator tone accounts for
94.8%, 109.9% and 267.1% of the old apparent three-band gap.  It also records
the repaired registration-sign defect.

This lane asks a narrower question: how much **detail-specific ordinal rendered
structure** does each complete pipeline place in each spatial band after
removing every strictly monotone point-tone degree of freedom?  It does not
call ordinal structure MTF, resolution truth, or faithful detail.

The strehl arm is the shipped `--srgb` DELIVER-V6 master from pinned commit
`6af834dac08d6605aee7ea3ad75809fdf6313770`.  The comparators consumed
Lightroom-developed TIFFs, while strehl consumed ARWs.  This is therefore a
pipeline comparison, not an isolation of merge algorithms.

## 2. Comparator census and provenance

Nine unique-byte render pairings are measured:

| ID | strehl master | comparator render | provenance |
| --- | --- | --- | --- |
| `113` | `113MSDCF.tiff` | `D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif` | Zerene PMax; 63/63 source identities; LR sharpening 0, colour NR 0, contrast +100 |
| `113-sharp` | same | `D:\edited\macro\test\2026-05-07-21.31.06 ZS PMax.tif` | Zerene PMax; same 63/63 identities; LR sharpening 40, colour NR 25, contrast +100 |
| `119-pmax` | `119MSDCF.tiff` | `D:\edited\macro\marker\2026-05-09-13.35.07 ZS PMax.tif` | Zerene PMax; 33/33 identities; LR contrast +50 |
| `119-pmax-udr` | same | `D:\edited\macro\marker\2026-05-09-13.40.00 ZS PMax UDR.tif` | Zerene PMax UDR; same 33 identities; LR contrast +50 |
| `119-pmax-udr-neutral` | same | `D:\edited\macro\marker2\2026-05-09-13.47.08 ZS PMax UDR.tif` | Zerene PMax UDR; same 33 identities; LR contrast 0 |
| `119-fork` | same | `C:\dev\macro\out\stack_test2_rec2020.tif` | focus-stack fork, float Rec.2020 marker render |
| `119-fork-defringed` | same | `C:\dev\macro\out\stack_test2_rec2020_defringed.tif` | postprocessed variant |
| `119-fork-u16` | same | `C:\dev\macro\out\stack_test2_rec2020_16bit.tif` | 16-bit variant |
| `cb` | `coffee-bean.tiff` | `C:\dev\macro\out\coffee-bean\stack.tif` | focus-stack fork; 105-frame bracket |

`C:\dev\macro\out\stack_v3.tif` is byte-identical to
`stack_test2_rec2020.tif` and is not double-counted.  The three marker-fork
inputs have been deleted.  The rendered target, strong 119 geometry fit, and
repository documentation are available, but their individual source
identities and exact invocation cannot be re-audited.  In contrast, the
Zerene 113 and 119 identity counts above come from embedded
`OriginalDocumentID` values.

No Helicon render was found under `C:\dev`, `D:\edited`, or
`D:\personal\macro`.  The twelve distinct frozen byte streams hash as follows:

| file | bytes | SHA-256 |
| --- | ---: | --- |
| strehl `113MSDCF.tiff` | 197801290 | `4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F` |
| 113 Zerene PMax, sharpening 0 | 196453660 | `B240FE4016E97EBB194497B2798A095C63C490C4FFF54018D48D34C7523719A0` |
| 113 Zerene PMax, sharpening 40 | 196453660 | `4D490F71EF63DA33758A49BF583AD2166CD014A5401ED64EDB5E5EDCABB47A3E` |
| strehl `119MSDCF.tiff` | 197801290 | `65AE95D15061EA455C239EC47CEC094A6461D1BD42A900A4139630499B162B9B` |
| 119 Zerene PMax | 196453640 | `B94C04421C8EB5FADD766E99A361F2C0BE4DE5425BECABAEB8D1FC1C82AA146B` |
| 119 Zerene PMax UDR, contrast +50 | 196453640 | `412E92611996DB808C60F522334881B9F4F108ED659F665560617FF19BA3A0EA` |
| 119 Zerene PMax UDR, contrast 0 | 196453640 | `91A23716F5D1DAAB1A25A09BC2407EC386840858A559C72D7C074B89FABD5F97` |
| marker fork, float | 392907466 | `2D1CCEC678F81173A231FBC7FD84E5457F361C57D32DFB06B24CBD82C1BBD6C2` |
| marker fork, defringed | 392897296 | `82E1606DDF2627B938588F8DD4D7D8480392680CBCFD7D20900C84A043AAAA3B` |
| marker fork, 16-bit | 196449104 | `930014DEAB9F4833ABD7F2D93880CECBA282C900C7FC29C13AA6155797404086` |
| strehl `coffee-bean.tiff` | 197801290 | `F38CA50ED1A680FA4DBCDD8D0513BE538DD31634B4E89AC6A34885944790A2EC` |
| coffee fork | 393326272 | `8636C20D73CA0CB1F57DB89BF8553ABC166E0FBC517E5C62A07C74DEE509066E` |

DELIVER-V6 records executable SHA-256
`2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7`
and command `strehl.exe stack <source> -o <master> --srgb`, with a private
`STREHL_CACHE_DIR` and all other `STREHL_*` variables unset.  This lane does
not rerender.

## 3. Tone-neutral statistic

Only native green pixels are measured.  In each native ROI, values become
average ranks

```text
q_j = (rank_j - (N+1)/2) / N .
```

After DC removal and a separable Hann window, `A_k` is FFT power in band `k`
divided by total power across the six bands:

```text
0.02–0.05  0.05–0.10  0.10–0.20
0.20–0.25  0.25–0.30  0.30–0.40 cycles/strehl-pixel.
```

Measurement pixels are never resampled.  If one comparator pixel spans `s`
strehl pixels, a 512-pixel strehl ROI is paired with
`round(512/s)` native comparator pixels, and comparator band edges are
multiplied by `s`.

For paired ROI `i`,

```text
d_ik = log(A_strehl,ik / A_comparator,ik)
R_detail,k = exp(mean_i(d_ik in the top texture half)).
```

The bottom texture quartile supplies `R_flat`.  A resolved same-direction flat
effect vetoes a provisional detail verdict.  `R>1` favours strehl.  Percentile
95% intervals use 10,000 paired bootstrap draws, seed `20260902`.

For any strictly increasing scalar point map `phi`, values retain exactly the
same ordering and ties.  Average ranks, registration ranks, ROI gates,
partitions, spectra, ratios and bootstrap draws are therefore identical.
This theorem does not cover clipping, newly created quantisation ties,
spatially varying/local tone, channel mixing, or non-monotone contrast.

## 4. Commissioning

The declared investigator-favoured direction was **strehl leads**.  The first
synthetic run did not pass: the preregistered flat-ratio subtraction amplified
an additive-noise confound by 25,493.7×.  Before real outcomes it was replaced
by the conservative same-direction veto.  The failed reading remains
executable.

| suite | controls | defect plants | decisive reading |
| --- | ---: | ---: | --- |
| synthetic operators/estimator | 22/22 GREEN | 15/15 RED | external rank oracle exact; all six shifts exact |
| frozen byte hashes | 1/1 GREEN | 1/1 RED | 12 distinct hashes; one-nibble plant rejected |
| real-ROI tone/potency | 3/3 GREEN | 2/2 RED | ordinal move 0; raw statistic moved 30.4% |
| 113 full-pipeline tone curves | 3/3 GREEN | — | affine, gamma 3, logistic: every delta 0 |
| coffee full-pipeline tone curves | 3/3 GREEN | — | affine, gamma 3, logistic: every delta 0 |
| 113-sharp gamma 3 | 1/1 GREEN | — | every delta 0 |
| 119-fork gamma 3 | 1/1 GREEN | — | every delta 0 |
| **total** | **34/34 GREEN** | **18/18 RED** | every deliberate plant fired |

The registration fixture planted `(0,0)`, `(1,0)`, `(0,-1)`, `(2,3)`,
`(-3,2)`, and `(5,-5)`.  Every recovered value was the exact negative
displacement and made the corrected interior equal an untouched source array.
Wrong-sign and no-op implementations went RED.

Additional potency:

* Gaussian sigma 0→2 removed 99.8% of combined ordinal 0.20–0.40 share.
* Unsharp masking raised 0.25–0.40 share by 49.3%.
* Down/up resampling moved one band by 77.5%.
* 12-bit quantisation changed unique/largest-tie occupancy from
  `65536 / 0.00153%` to `3167 / 0.0961%`; 1%/99% clipping produced a
  1.001% largest tie.
* The fixed external 4×4 oracle caught a wrong expected-rank fixture in the
  independent checker before outcomes.

## 5. Geometry, registration, and independent implementation

The author uses scipy ranks/zoom/full FFT and bootstrap seed `20260902`.
The independent checker uses `numpy.unique` ranks,
`skimage.phase_cross_correlation`, `skimage.resize`, a weighted real FFT, and
seed `20260903`.  It imports no author outcome implementation.

| pair | author/checker scale | relative difference | eligible author/checker | gate |
| --- | ---: | ---: | ---: | --- |
| 113 PMax, sharpening 0 | 1.002 / 1.002 | 0 | 81 / 81 | PASS |
| 113 PMax, sharpening 40 | 1.003 / 1.008 | 0.4985% | 55 / 56 | PASS |
| 119 PMax | 0.996 / 1.001 | 0.5020% | 96 / 94 | **FAIL** |
| 119 PMax UDR, contrast +50 | 0.996 / 1.003 | 0.7028% | 96 / 68 | **FAIL** |
| 119 PMax UDR, contrast 0 | 1.003 / 1.003 | 0 | 70 / 67 | PASS |
| 119 fork, float | 1.006 / 1.006 | 0 | 94 / 94 | PASS |
| 119 fork, defringed | 1.006 / 1.006 | 0 | 94 / 94 | PASS |
| 119 fork, 16-bit | 1.006 / 1.006 | 0 | 94 / 94 | PASS |
| coffee fork | 1.036 / 1.044 | 0.7722% | 55 / 54 | **FAIL** |

The three geometry failures are published, not reconciled.  They do not hide
a resolved win/loss: all affected 119 and coffee bands remain unresolved under
both implementations.  The marker PMax UDR 0.02–0.05 point estimates also
miss the independent numeric agreement gate: author `0.7981`, checker
`0.7064`, difference `0.0916` versus summed CI half-widths `0.0860`.
The other 53/54 point estimates pass that gate.

Author real-registration median correlations:

| pair | none | wrong sign | corrected |
| --- | ---: | ---: | ---: |
| 113 PMax, sharpening 0 | 0.4000 | 0.2918 | **0.6151** |
| 113 PMax, sharpening 40 | 0.2799 | 0.2553 | **0.3451** |
| 119 PMax | 0.4868 | 0.3026 | **0.8992** |
| 119 PMax UDR, contrast +50 | 0.4875 | 0.3038 | **0.9018** |
| 119 PMax UDR, contrast 0 | 0.8721 | 0.8371 | **0.9174** |
| 119 fork, float / 16-bit | 0.7563 | 0.6051 | **0.9397** |
| 119 fork, defringed | 0.7566 | 0.6051 | **0.9402** |
| coffee fork | 0.1894 | 0.1253 | **0.9530** |

Across all 54 band outcomes, author/checker final classes agree 50/54.  The
four differences are flat-veto versus non-veto, not opposing wins: two on
113-sharp (0.02–0.05 and 0.10–0.20), plus 0.05–0.10 on 119 PMax and PMax UDR.
All bands pass blur sensitivity.  No leave-one-out or spatial-quadrant reversal
fires.

## 6. Competitive results

The practical bar is 5%.  LEADS requires the lower detail CI above 1.05;
TRAILS requires the upper CI below `1/1.05`; a resolved same-direction
`R_flat` forces `UNRESOLVED (FLAT VETO)`.

### 6.1 113 Zerene PMax, Lightroom sharpening 0

| cyc/px | `R_detail` [95% CI] | `R_flat` [95% CI] | final |
| --- | --- | --- | --- |
| 0.02–0.05 | **1.0833 [1.0534,1.1114]** | 0.7617 [0.7196,0.8071] | **LEADS** |
| 0.05–0.10 | 0.9239 [0.9029,0.9452] | 0.8518 [0.8058,0.8998] | FLAT VETO |
| 0.10–0.20 | **0.8842 [0.8420,0.9311]** | 1.1680 [1.1035,1.2308] | **TRAILS** |
| 0.20–0.25 | 0.8721 [0.7817,0.9745] | 2.3833 [2.1009,2.6967] | UNRESOLVED |
| 0.25–0.30 | 0.9735 [0.8339,1.1406] | 3.2530 [2.7675,3.8098] | UNRESOLVED |
| 0.30–0.40 | 1.0264 [0.8564,1.2305] | 3.1692 [2.6437,3.7543] | UNRESOLVED |

### 6.2 113 Zerene PMax, sharpening 40 / colour NR 25

| cyc/px | `R_detail` [95% CI] | `R_flat` [95% CI] | author/checker |
| --- | --- | --- | --- |
| 0.02–0.05 | 1.2856 [1.2448,1.3260] | 1.2243 [1.0395,1.4271] | LEADS / FLAT VETO |
| 0.05–0.10 | 0.9999 [0.9664,1.0336] | 1.0285 [0.9386,1.1221] | UNRESOLVED / UNRESOLVED |
| 0.10–0.20 | 0.7538 [0.7223,0.7887] | 0.8478 [0.7552,0.9620] | TRAILS / FLAT VETO |
| 0.20–0.25 | **0.3992 [0.3381,0.4720]** | 0.7395 [0.5011,1.0546] | **TRAILS / TRAILS** |
| 0.25–0.30 | **0.2834 [0.2178,0.3696]** | 0.6365 [0.3860,1.0007] | **TRAILS / TRAILS** |
| 0.30–0.40 | 0.2018 [0.1461,0.2797] | 0.4820 [0.2796,0.7872] | FLAT VETO / FLAT VETO |

The development ladder changes 0.25–0.30 `R_detail` from 0.9735 to 0.2834,
a 70.9% ratio change.  Exact Zerene run settings are not retained, so the XMP
difference is documented association, not a complete causal isolation.

### 6.3 119 Zerene marker renders

Every final row is unresolved.  `FV` means the apparent direction is rejected
by the same-direction flat-region control.

| cyc/px | PMax +50 `R` [CI], final | PMax UDR +50 `R` [CI], final | PMax UDR neutral `R` [CI], final |
| --- | --- | --- | --- |
| 0.02–0.05 | 0.7968 [0.7515,0.8441], FV | 0.7981 [0.7531,0.8449], FV | 0.7272 [0.6878,0.7720], FV |
| 0.05–0.10 | 0.9162 [0.8803,0.9526], UNRESOLVED | 0.9246 [0.8901,0.9602], UNRESOLVED | 0.8770 [0.8458,0.9100], FV |
| 0.10–0.20 | 1.4347 [1.3231,1.5576], FV | 1.4118 [1.3079,1.5255], FV | 1.5159 [1.4254,1.6101], FV |
| 0.20–0.25 | 2.5970 [2.2121,3.0459], FV | 2.4998 [2.1542,2.8980], FV | 2.9329 [2.6416,3.2420], FV |
| 0.25–0.30 | 3.3410 [2.7925,3.9897], FV | 3.2527 [2.7396,3.8518], FV | 3.9086 [3.4846,4.3734], FV |
| 0.30–0.40 | 3.7050 [3.0575,4.4760], FV | 3.8254 [3.1871,4.5653], FV | 4.8142 [4.2779,5.3889], FV |

The checker additionally applies the flat veto to the first two arms at
0.05–0.10.  It never promotes a marker-Zerene row to a win or loss.

### 6.4 119 focus-stack marker renders

Float and 16-bit variants have identical ordinal outcomes.  Defringing changes
the point estimates only slightly.  All rows remain unresolved.

| cyc/px | float and 16-bit `R` [CI] | defringed `R` [CI] | final |
| --- | --- | --- | --- |
| 0.02–0.05 | 0.7506 [0.7036,0.7991] | 0.7497 [0.7029,0.7980] | FLAT VETO |
| 0.05–0.10 | 1.0616 [1.0321,1.0912] | 1.0638 [1.0340,1.0937] | UNRESOLVED |
| 0.10–0.20 | 1.7576 [1.6079,1.9273] | 1.7638 [1.6136,1.9329] | FLAT VETO |
| 0.20–0.25 | 2.5756 [2.2413,2.9770] | 2.5841 [2.2464,2.9877] | FLAT VETO |
| 0.25–0.30 | 2.7358 [2.3514,3.2235] | 2.7464 [2.3591,3.2409] | FLAT VETO |
| 0.30–0.40 | 2.2081 [1.9000,2.6200] | 2.2177 [1.9055,2.6353] | FLAT VETO |

The real flat estimates move in the same direction by similar or larger
amounts—for example, float `R_flat=3.7162 [2.4542,5.8176]` at 0.25–0.30.
Calling the nominal 2.74× detail value a win would relabel a general
processing/noise difference as detail.

### 6.5 Coffee focus-stack fork

| cyc/px | `R_detail` [95% CI] | `R_flat` [95% CI] | final |
| --- | --- | --- | --- |
| 0.02–0.05 | 0.9466 [0.9369,0.9563] | 0.8524 [0.7783,0.9156] | UNRESOLVED |
| 0.05–0.10 | 0.9984 [0.9886,1.0095] | 0.9211 [0.8702,0.9662] | UNRESOLVED |
| 0.10–0.20 | 1.1302 [1.1061,1.1560] | 1.1125 [1.0732,1.1647] | FLAT VETO |
| 0.20–0.25 | 1.2975 [1.2426,1.3568] | 1.2891 [1.2282,1.3637] | FLAT VETO |
| 0.25–0.30 | 1.3915 [1.3034,1.4850] | 1.3560 [1.2718,1.4433] | FLAT VETO |
| 0.30–0.40 | 1.3710 [1.2099,1.5342] | 1.4079 [1.2102,1.6413] | FLAT VETO |

### 6.6 Standing by band across all nine pairings

| cyc/px | standing |
| --- | --- |
| 0.02–0.05 | **NOT ROBUST:** strehl leads unsharpened 113 PMax; the sharpened 113 class disagrees author/checker; all seven other pairings are unresolved |
| 0.05–0.10 | **UNRESOLVED:** no pairing produces a win or loss; two 119 flat-veto labels disagree without changing that conclusion |
| 0.10–0.20 | **NOT ROBUST:** strehl trails unsharpened 113 PMax; sharpened 113 is TRAILS/FLAT-VETO across implementations; all seven others are flat-vetoed |
| 0.20–0.25 | **NOT ROBUST across 113 development:** unresolved against sharpening-0 PMax, trails sharpening-40 PMax; seven others unresolved/flat-vetoed |
| 0.25–0.30 | **NOT ROBUST across 113 development:** `0.9735 [0.8339,1.1406]` versus `0.2834 [0.2178,0.3696]`; seven others unresolved/flat-vetoed |
| 0.30–0.40 | **UNRESOLVED:** no pairing produces a retained win or loss |

## 7. Interpretation and Rust consequence

Point tone no longer determines the answer.  The real render corpus instead
shows that comparator development, sharpening, denoising, local processing,
and flat-region structure dominate several apparent high-band effects.  The
old 17–27% deficit remains retracted; the new sharp-PMax trails are
whole-pipeline associations, not proof that strehl's merge loses detail.

### What changes in Rust

**Nothing in `src/` or `crates/` changes.**  The lane was read-only with
respect to Rust, and no resolved result isolates alignment, merge, demosaic, or
delivery code.  Changing those modules from a result that flips with
comparator preprocessing would be overreach.  The actionable change is to
competitive validation: future claims must use this native-grid rank
instrument (or a truth-referenced successor) and matched input development,
not raw power across independently toned renders.

### Could not verify

* Helicon performance: no usable Helicon render exists in the searched roots.
* The exact source identities and invocation for the three retained marker
  focus-stack files; their source TIFF directory is gone.
* A physical MTF or truth-fidelity winner, or whether extra ordinal structure
  is detail rather than sharpening/ringing/noise.
* Exact geometry within the 0.5% author/checker bar for 119 PMax, 119 PMax UDR
  +50, or coffee.
* Invariance to clipping, local/spatial tone, channel mixing, or new ties.
* Exact comparator application settings beyond retained TIFFs/XMP and prior
  reports; no comparator has a complete reproducible run manifest.
* Moving-HEAD strehl; this measures pinned commit `6af834dac08d`.

## 8. Proposed corpus facts

* **P1.** Nine unique-byte pairings survive: five Zerene outputs and four
  focus-stack outputs; `stack_v3.tif` is an alias, and no Helicon render was
  found.
* **P2.** Native-grid average-rank band share is exactly invariant to strictly
  increasing point tone.  Eight full-pipeline real tone plants moved every
  outcome component by zero; raw power moved 30.4%.
* **P3.** Registration recovered the exact negative of all six planted shifts.
  Correct-sign real correlation exceeds both no-registration and wrong-sign
  correlation on every pairing.
* **P4.** On 113 sharpening-0 PMax, strehl leads 0.02–0.05 and trails
  0.10–0.20.  On sharpening-40 PMax, both implementations retain trails at
  0.20–0.25 and 0.25–0.30.
* **P5.** All six newly admitted 119 comparator renders are unresolved in all
  bands after the flat veto; their large nominal high-band ratios are not
  detail-specific.
* **P6.** Author/checker classes agree 50/54; no disagreement is an opposing
  win/loss.  Three geometry pairs and one point estimate fail the independent
  numeric gates.
* **P7.** The app-level baseline is NOT ROBUST: 113 0.25–0.30 changes from
  `0.9735` to `0.2834` across available Lightroom development rungs.
* **P8.** No Rust change follows because no result causally isolates a Rust
  stacker module.

## 9. Reproduction

From `experiments\V-HEADTOHEAD3`, with Python 3.12.10, NumPy 2.4.4,
SciPy 1.17.1, tifffile 2026.5.2, and scikit-image 0.26.0:

```powershell
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONPATH=(Get-Location).Path
python -B commission.py
python -B commission.py --hashes
python -B commission.py --real
python -B tone-check.py 113
python -B tone-check.py cb
python -B tone-check.py 113-sharp --curves gamma3
python -B tone-check.py 119-fork --curves gamma3
python -B geometry.py
python -B measure.py 113 113-sharp 119-pmax 119-pmax-udr 119-pmax-udr-neutral 119-fork 119-fork-defringed 119-fork-u16 cb
python -B check.py 113 113-sharp 119-pmax 119-pmax-udr 119-pmax-udr-neutral 119-fork 119-fork-defringed 119-fork-u16 cb
```

`measure.py` prints complete `RESULT_JSON`, including ROI centres and
diagnostics.  `check.py` prints independent `CHECK_JSON`.  No command invokes
strehl or writes a capture directory.

Research commits through the exhaustive pair table:

```text
5d85d8e12ae35dee46568d31e1a662a4b451ecf4  initial preregistration
11ed554e2a736789813074c642c536b967c3a16a  registration-gate amendment
48c81eebba999e8c2d76bc7460ded792408a8708  failed-control amendment
9f08a4fa5602055db4b764caf6bb35e914604b22  instrument and checker
fec4a572d140997cc7b7be673c9719c68fa7d2b3  verifier-found control fixes
403693a1ce9a673d2181b1f3ed4bb0ada6fd65bd  verdict-precedence fix
a050d6861d5ab7655fe08a85c9fd1d3a29a2b1aa  first report, superseded
55a53bccc9458b950f8176716836afe18378e9a9  disclose second 113 render
3c108fac1cde4af7d92b2629e0d2f2abfcbadba0  add second 113 arm
08a11d528202eb3d84b257f6f0427c5e8226a9ab  three-pair report, superseded
b31b8b858e2cf2956c7965c65affa6be014cad27  exhaustive-census disclosure
178267c9a38f40ca3cfe979ea2fa13a5230ccdd2  pre-outcome fork-subject correction
40b20bef0fe0cdaba7298573095806e580a7ed85  exhaustive pair tables
```

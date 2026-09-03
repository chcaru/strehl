# SCORECARD-BASELINE — first independent self-baseline

**Scorecard:** v1.1, SHA-256
`11a754a61837ebe70cd1d59b9ad224d9240cfd105747b1cc28fce78befc03baa`.
**Frozen source:** `4b60b1ba9f56abe92573451815e67f03725d19fa`.
**Frozen binary:** `strehl 0.0.0 (4b60b1ba9f56)`, SHA-256
`814eb719608cc0f085fbd49e7529eb6fa4e50031070f5f57af4fc2812cee4363`.
The pre-render freeze is commit `bc8f315a1d2a205633ca05e8b7ac21453da44f22`.

## Verdict

**UNMEASURED.** This lane produced real native-RAW diagnostics, but no quality
value is admitted as a v1.1 score. All eight rendered arms fail the scorecard's
pre-metric native-scale gate: an independently commissioned affine reader measures
`0.2901%`–`0.4619%` scale disagreement against `<=0.10%`. The shipping default's
`cover=scale` banners independently report the same mechanism. The required common
ProPhoto-TIFF input adapter is also absent.

## Score table

Comparator ratios remain **UNMEASURED — comparator lane** throughout.

| Axis | Absolute bar | This lane's reading | Verdict |
|---|---|---:|---|
| M1 | median licensed cutoff `0.25`; `S_25`; gain/width guard | invalid diagnostics: cutoff `0.15` on both bee lights; `S_25` `6.20e-5` / `6.34e-5`; geometry `0.2901%`–`0.3019%`; matching 1.6 s darks/flats `0/0` | **UNMEASURED** — geometry, FPN floor, bee eligibility, common-input arm |
| M2 | `eta <=1.10` | invalid diagnostic medians `1.8483` and `2.5156`; affine slopes `1.0630`–`1.0687` | **UNMEASURED** — geometry/transfer guards fail; M1 prerequisite absent |
| M3 | halo/veil percentiles, affected rate, width, coherence | no score run | **UNMEASURED** — arm failed §1.5 before metric; no admitted checker |
| M4 | `Q_flat`, failed-site rate | no score run | **UNMEASURED** — same |
| M5 | coverage, Wilson bound, failed run, FOV | no score run | **UNMEASURED** — same |
| M6 | high/low clipping `<=0.10%`, detail `>=0.90` | rail census proves high-arm `<10,000` even before alignment for salt `1,193`, battery `1,230`, angled ruler/grid `0`, fabric f/11 `82`; salt low arm only `15` | **UNMEASURED** — registered capture set is under-powered as written |
| M7 | DeltaE00 / seam / ICC | traceable tilted target candidates `0` | **UNMEASURED** — confirmed capture blocker |
| M8 | hull violations exactly `0.0000%` | no score run | **UNMEASURED** — no valid geometry/common-input arm or admitted external warp checker |
| M9 | false certification, coverage, interval calibration | matching bee dark/flat groups `0/0`; shipping default emits no licensed-band acuity/variance certificate | **UNMEASURED** |
| M10 | valid fraction, rank, errors, slope/null/confusion | no depth product; ruler record says only “approximately 10.26 deg” | **UNMEASURED** |
| M11 | absolute CPU/hybrid/cold/live bars | not timed | **UNMEASURED** — quiet window required; comparator terms belong to comparator lane |
| M12 | memory, scaling, worker hashes, modulo spread | not run | **UNMEASURED** — quiet window required |

No frequency above `0.25 cyc/native px` was inspected or reported.

## Commissioning

| Instrument | Planted defect RED | Untuned null GREEN |
|---|---:|---:|
| M1 target-locked repeat information | pre-sensor blur dropped cutoff by `0.080 cyc/px` | common pattern movement `0`; unsharp movement `0`; flat signal ratio `0.0607` |
| M2 residual efficiency / blur guard | added `0.25 sigma_1` raised eta by `0.2315`; blur lowered noise to `0.3265x` but widened the edge `3.4155x` | untouched temporal means eta `1.0035` |
| Translation reader | one-pixel mutation detected | exact `(-2,+3)` shift recovered |
| Post-score affine rejection audit | `0.300%` scale plant read `0.3031%` and failed | identity `0`; translation-only null `0.0084%` |
| Rail eligibility census | high- and low-rail threshold plants detected | two interior samples stayed green |

M3–M5 and M8 score checkers were not commissioned after the shared arm failed its
pre-metric gate. M9/M10 have no compatible product to check. M11/M12 await the
required quiet host.

## Captures and corpus facts

All **27 named capture paths exist**; none is missing. Score renders used only the
two registered ISO-100 bee repeats:
`DSC00328`–`00359` and `DSC00584`–`00615`, partitioned exactly into the frozen
8/12/12 and 16/16 arms. The rail census read foam, salt, battery, angled ruler,
all five grid captures, and all three fabric captures.

The current request tree is **4,096 files / 4,086 ARWs**, not 3,261 / 3,251.
The exact difference is a post-freeze `high-res-calibration-slide-cpl` addition
of **835 ARWs**. It was not substituted into this frozen scorecard.

No ColorChecker/colour-checker/grey-card target exists by directory or filename.

## Scorecard defects and largest gap

1. The contract says ProPhoto RGB D50, but M1's coefficients
   `0.2627/0.6780/0.0593` are Rec.2020/D65 luminance coefficients.
2. M1 does not define the “defocused source” denominator for its same-focus bee
   sentinel.
3. M2 specifies no aggregation functional for eta.
4. M5's “longest failed run along the focus-sweep direction” is undefined for
   non-planar flower/duck/pill tile maps.
5. The shipping default deliberately rescales every aligned render, conflicting
   with §1.5's native-scale gate.

The largest gap is therefore **scoreability, not a flattering or unflattering
quality number**: the default output geometry invalidates the arm before M1–M8,
and strehl cannot ingest the registered common TIFFs.

## Quiet-window request

Yes: reserve **90–120 minutes** for M11/M12. It must cover the N=33/105/299
worker matrix, N=96–99 modulo ladder, process-tree memory sampling, warm-up and
six alternating sweeps. The common-TIFF comparative arm remains blocked even
with a quiet host.

## Reproduction

```text
python commission.py
python freeze.py
python prepare.py
python render.py
python measure.py
python audit_geometry.py
python rail_preflight.py
python verify.py
```

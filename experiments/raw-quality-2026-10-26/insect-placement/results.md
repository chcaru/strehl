# Fixed thorax gap recipe closed without a geometric estimate

2026-10-26. **MEASURED by root's bounded execution; VERIFIED here from the saved complete receipts.** All eight nominated green profiles refuse in each of sources104,105,106: seven have insufficient fixed-window gap contrast and `A/G1/y` has no signed crossing in its fixed left window. This is not evidence of zero displacement or a correct global map. No numerical geometric estimate exists. The JSON `[0,0]` vectors are placeholders produced when every profile is unavailable, not measured null motion.

Close this fixed nomination/estimator recipe. No coordinate, window, threshold, source interval or fit-model change follows. No warp or full-photo intervention is admitted. The result does not establish that placement is irrelevant elsewhere or that all scale boundaries are unmeasurable.

Root ran `execute-placement.py` to invoke the frozen `run.py` controls, stage and measure modes under the existing owned-process controller. The actual numerical child was:

```text
Python312/python.exe -B -X faulthandler experiments/raw-quality-2026-10-26/insect-placement/run.py measure --cache outputs/raw-quality-2026-10-26/insect-placement-cache --out outputs/raw-quality-2026-10-26/insect-placement-observation
```

All three stages exited0. Numerical work was0.719seconds by the experiment timer; the process receipt records0.968seconds wall, no termination and no remaining owned processes, with four threads and4GiB/60second bounds. These are operational observations during other host work, not a speed benchmark. The invocation binds script SHA256 `7415a528546e5b1cb0c29b134889c2e6960dd21d407037f58eaa2f7febd05fab` and the unchanged map/order/nomination inputs.

Generated controls passed: the flat refused all edges; the physical-phase ramp and wrong-phase foil were live; known translation maximum center error was0.01490951native pixels; fixed-center symmetric defocus maximum center change was0.000000477pixels. The changed glint shifted A's apparent x-center by about−0.45/−0.48pixels in G1/G2 while leaving held B unchanged, and the actual common-motion gate rejected it. That is useful rejection power, not a guarantee that the nominated photograph contains the required opposed edges.

The staging receipt records exactly three unique originals, RawPy copying the512-square u16 patches inside each context, and one additional existing rawler-based decode of source105. The independent105 patch has zero differing sensels. Original hashes and modification times remained unchanged during the staged run. This reviewer read the receipts and caches only and did not reopen an original RAW.

Evidence: `outputs/raw-quality-2026-10-26/insect-placement-{controls,stage,measure}/` process/invocation records; `insect-placement-cache/cache.json`; `insect-placement-observation/{controls,result}.json`. The separate bounded all-phase postflight below is descriptive only and cannot reopen the failed placement recipe.

## Cached all-phase postflight: the nominated windows are not dark gaps

**MEASURED / visually inspected:** the failure is a nomination/shape mismatch at these fixed coordinates, not evidence that the structures live chiefly in red/blue while green has little contrast. I nominated the RGB contexts too approximately for the proposed centered dark-gap estimator. Actual green profiles have substantial structure, but the fixed center/shoulder windows have the wrong ordering for a dark gap. Lowering a positive contrast threshold would not turn negative shoulder-minus-center values into the required gap.

The approved read-only command was:

```text
python -B -X faulthandler experiments/raw-quality-2026-10-26/insect-placement/inspect-phases.py
```

It exited0; inner extraction/plot time was0.875seconds, below the10second allocation. It read only the three bound512-square u16 caches, the frozen script/map and existing display ICC. Before/after cache hashes agree. It did not read a RAW, fit an edge/motion, move a window, choose a new feature, estimate noise or alter the original observation. [Postflight result](phase-inspection-1/result.json) retains all48 R/G1/G2/B profiles across the three sources and exact input/script bindings.

All phase addresses are literal original-CFA sites relative to even cache origin `(4528,2544)`: R `(2x,2y)`, G1 `(2x+1,2y)`, G2 `(2x,2y+1)`, B `(2x+1,2y+1)`. The unchanged105→149→source transforms and the same three parallel traces/offsets/windows were used. No demosaiced color values entered these profiles. Source105 is shown below because it is the fixed gauge; the neighboring profiles remain in the result and no temporal matching was performed.

Each table entry is **left/right shoulder median minus center median, in original DN**. A centered dark gap requires both values positive; the original recipe further required each to exceed30DN. The one-dimensional profiles are diagnostic observations, not calibrated optical boundaries.

| Fixed profile | R | G1 | G2 | B |
| --- | --- | --- | --- | --- |
| A horizontal | −34.8 / −33.5 | −110.1 / −92.2 | −87.7 / −72.2 | −69.2 / −57.1 |
| A vertical | +34.8 / −6.3 | +651.4 / −43.3 | +364.0 / −69.7 | +151.5 / −43.7 |
| B horizontal | +82.3 / −157.7 | −170.3 / −887.8 | −185.3 / −948.3 | −310.2 / −560.0 |
| B vertical | −154.4 / −106.3 | −914.8 / −761.1 | −1004.0 / −859.3 | −586.5 / −514.3 |

In [feature A's shared-scale plot](phase-inspection-1/feature-A-all-phases.png), the horizontal profile rises from the fixed center onto a broad bright bead to its right; it is not a dark interval between two brighter outer shoulders. The vertical profile combines a nearby strong peak with a trough displaced from the nominated center. In [feature B's plot](phase-inspection-1/feature-B-all-phases.png), the center sits on a strong bright bead/glint: G1 center medians are921.4/944.6DN above black horizontally/vertically; G2 gives971.0/1033.3DN. Those are not low-contrast green observations. Red/blue follow broadly corresponding peak/valley geometry; they do not provide the missing centered gap at the frozen locations.

Direct source105 [R](phase-inspection-1/source105-R-physical-sensels.png), [G1](phase-inspection-1/source105-G1-physical-sensels.png), [G2](phase-inspection-1/source105-G2-physical-sensels.png) and [B](phase-inspection-1/source105-B-physical-sensels.png) sensel-array views were inspected after the plots were generated. They use one fixed black512/white15360/gain3.434/sRGB grayscale display and the same ICC, without per-phase normalization or white balance. Each256-square image displays one native phase at pitch2 over the512-square sensor footprint; it is not a demosaiced or reconstructed photograph. The shared-scale plots show original black-subtracted DN, not display values. Their channel amplitudes should not be interpreted as color accuracy or relative calibrated SNR.

**Consequence:** this postflight supplies no rationale for replacing the green guide with a joint-color guide. It diagnoses why these exact manually nominated windows failed. It also does not prove that a green-only guide is sufficient everywhere, that RAW contains no useful registration information, or that the global alignment is correct. The fixed placement recipe stays closed, with no feature relocation, polarity reversal, threshold reduction or new geometric estimate.

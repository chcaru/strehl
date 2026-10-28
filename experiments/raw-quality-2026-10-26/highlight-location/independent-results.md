# Independent stage1 location result

2026-10-27. **VERIFIED JSON/source review; no RAW, sensor-array rerun, fit or correction by this reviewer.** The observation establishes positive region-level overlap between exceptional final CFA values and final-MHC support in both frozen windows. It does not yet establish that those samples coincide with the pale contour, explain a halo, represent original saturation or are false reconstructed detail. Independent photographic co-location review is separate.

## Recorded execution and integrity

[Result](../../../outputs/raw-quality-2026-10-26/highlight-location-1/result.json) is `LOCATION_OBSERVATION_COMPLETE`, with all five accounting controls true and `quality_claim=false`. Root reports terminal exit0. The retained program argv is `experiments/raw-quality-2026-10-26/highlight-location/observe.py`; interpreter flags are not included in this JSON. Internal duration is0.203s during the concurrent complete299 green-phase trial, so this is operational timing only.

Executed script SHA-256 `1f3f70cc202292e5e32fa1e1f78baddb7c50144daebb1efbcb88e9ef45b56923` matches the independently reviewed source. The result records identical before/after hashes and metadata for its five inputs: sensor TIFF, sidecar, frozen witness manifest, demosaic source and script. It records zero original RAW reads. This is not a new content audit of all299 originals. I independently checked all eight saved phase/dependency map file hashes; none differs from the receipt. No pixel-count recomputation was commissioned here.

## Exact counts and gauge

Each core is384x384 delivered pixels; its read extent is388x388 including the two-pixel halo. Direct hits and possible output dependency sites are different quantities:

| Region | Strict DN threshold | Direct core R/G1/G2/B hits | Expanded CFA hits | Possible MHC RGB destination sites |
| --- | --- | --- | --- | --- |
| bright-wing-rim | >14848 | 0/8/16/0 =24 | 26 | 248 |
| bright-wing-rim | >15871 | 0/5/8/0 =13 | 13 | 149 |
| upper-occlusion | >14848 | 0/3/4/0 =7 | 7 | 37 |
| upper-occlusion | >15871 | 0/2/3/0 =5 | 5 | 30 |

Thus26 is the bright-wing expanded count, not its direct core count. Two working-white exceedances lie in the halo. All **core** exceedances are green; the JSON does not provide the halo's phase breakdown. Possible destination counts are unions of nonzero camera-RGB dependencies, not three-channel sample counts, positive contributions or artifact-pixel counts.

Bright-wing G1/G2 core maxima are18098.346/22000.094DN; upper-occlusion maxima are17717.594/18010.000DN. R and B core maxima remain below both thresholds. These are black-subtracted final-sensor values. Working-white14848 and nominal-container15871 remain numerical reference levels, not independently calibrated saturation thresholds.

The delivered windows remain `(4050,1810,384,384)` and `(3850,1300,384,384)`, with reference149 active offsets `(68,46)`. The inspected13-tap union and two-pixel expansion correctly address final MHC support in this gauge. Counts are internally consistent with nested thresholds and overlapping stencil support; that consistency does not independently verify optical meaning.

## Decision

**ARGUED:** do not close the region-level exceptional-value hypothesis as spatially absent: both windows have direct hits and possible dependencies. Equally, do not promote positive384-window overlap into a halo explanation. The regions contain genuine compact glints, colored scales and broad contours; the locator has not distinguished their roles. Negative signed taps and downstream development further prevent treating a support map as a map of bright contamination.

The appropriate next decision is the already assigned visual co-location review using unchanged complete/native views and these maps. A useful local relationship could motivate a separately scoped source-provenance observation; this result alone does not authorize one. No change to white levels, clipping, smoothing, admission or reconstruction follows. Original censoring, source MHC, Catmull overshoot, legitimate bright interpolation and merge behavior remain unseparated. Stage1 provides a bounded location fact, not image-quality progress.

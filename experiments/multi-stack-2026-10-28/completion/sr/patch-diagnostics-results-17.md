# Patch diagnosis and fixed-observation model result17

VERIFIED numerical nonperturbation. The diagnostic builds/runs use the exact
product16 support libraries and current core diagnostic source. Each ROI retains
all75 color-pair records and675 predefined patches. Ordinary training fits,
held measurements, graph/cycle decisions, consuming-pull bits and all output
arrays/TIFF pixels remain identical to16b. Zero RAW decodes; each arm takes
about3.6s and1.202GB private under concurrent work. The script, commands and
artifact comparisons are bound by sr-insect-global-summary-17.json.

The diagnostic runs the ordinary witnessed estimator first, then evaluates
descriptive probes. Those extra probes do not enter the certified original
footprints or alter eligibility. Fitted local probes are reconstructed from
the reported global fit; they are not claimed as a new exact fit trajectory.
The independent source/receipt review found no additive-API blocker.

## What the missing held measurements mean

ROI0 cross-pass held seed census,32 predefined sites per color:

| Color | NCC Ok | Low peak | Unsupported original-search footprint | Retained by original estimator |
| --- | --- | --- | --- | --- |
|Red|24|8|0|24|
|Green|16|8|8|0|
|Blue|16|16|0|14|

The original Green path can stop before returning observations because fewer
than four initial patches pass its support gate. This does not mean all Green
texture was absent. For110/400 specifically, held sites1 and3 have NCC Ok,
site5 has LowPeak, and site7 has an unsupported search footprint. Red has three
Ok/one LowPeak; Blue two/two. Surviving cross-pass displacement contradictions
remain; the extra count does not qualify the fit. Unsupported footprint can
mean finite crop/filter boundaries or invalid original taps; the current census
does not distinguish these causes, so it is not automatically labeled clipping.

ROI1 also exposes lack of local gradient information: each Red/Blue pair's
held patch at one fixed site fails that gate. Its missing all-color support is
not repaired by averaging more of the same geometrically unqualified samples.
Complete role/color/stage counts remain in sr-patch-census-roi0-17.json and
sr-patch-census-roi1-17.json; no rejected patch was removed from the census.

## Translation is not a general repair on these observations

DERIVED on fixed measured seed probes, not a new original-domain registrar.
The predeclared unit-weight residual-translation and residual-similarity models
use exactly the same train points and untouched held points. Algebra controls
run first, including scale/rotation misspecification, unobservable training
curvature, rank/count failures and independently computed absolute-sensor gauge.

| ROI/color | Four-held eligible pairs | Translation within0.15sensor at all four | Similarity within0.15sensor at all four |
| --- | --- | --- | --- |
|0 Red|17|2|6|
|0 Green|11|0|2|
|0 Blue|17|1|8|
|1 Red|0|0|0|
|1 Green|4|4|2|
|1 Blue|0|0|0|

The translation arm's median maximum errors in ROI0 are0.221/0.238/0.215sensor,
versus0.164/0.180/0.154 for similarity. ROI1 Green favors translation on its four
available pairs, but Red/Blue provide no four-held comparison. No model is
selected by these held outcomes and no product fitter/default changes. This
conditional one-pass analysis does not justify another full-image render on the
insect. It is separate from the engine's iterated fit/probe and global solve.

Exact commands:

```powershell
python experiments/multi-stack-2026-10-28/completion/sr/run-insect-global.py --binary outputs/multi-stack/completion/sr-patch-roi-build-17/roi-pilot.exe --tag 17 --patch-diagnostics
python experiments/multi-stack-2026-10-28/completion/sr/frozen-probe-model-ablation.py --out outputs/multi-stack/completion/sr-frozen-probe-controls-02.json
python experiments/multi-stack-2026-10-28/completion/sr/frozen-probe-model-ablation.py --source outputs/multi-stack/completion/sr-insect-global-17-rgb-roi0/local-registration-report.json --out outputs/multi-stack/completion/sr-frozen-probe-roi0-01.json
python experiments/multi-stack-2026-10-28/completion/sr/frozen-probe-model-ablation.py --source outputs/multi-stack/completion/sr-insect-global-17-rgb-roi1/local-registration-report.json --out outputs/multi-stack/completion/sr-frozen-probe-roi1-01.json
```

# Completion photographic review 01

VERIFIED visual observations, 2026-10-28, root/independent_review. Complete float masters and photographs were read, checked finite, and rendered with the fixed transforms below; complete-scene overviews are orientation only. All 84 witness images were inspected as native384-pixel slices, displayed in21 labeled boards with paste only and no resampling. This reviewer did not author the CLI guide selection or interleave/HDR orchestration, but did author fixes to core precision/attribution. Therefore this is an independent output-observer challenge, not a claim of wholly author-independent validation of those core modules. Root reviewed those fixes separately.

## Interleave: preserved photograph, benefit not demonstrated at pitch2

The 182-source combined result has no observed missing region, new broad seam or new color break. It does not show recognizable extra line separation, sharper QR boundaries, clearer fine grid or radial detail relative to either91-source half in these witnesses. The separate ordinary182 reference is visually similar. These are positive preservation/capability observations, not a demonstrated detail or noise gain.

The source is a single tilted chart sweep, divided into even and odd positions. The two halves are disjoint source bytes but are not independent repeated photographic acquisitions. Each91-frame half still densely spans the same range. ARGUED: this is a weak positive-benefit stimulus because it may not create an appreciable gap in focus coverage. Failure to see a benefit is not proof that interleaving cannot help, nor permission to leave that benefit unrealized.

The display was frozen solely from the odd-half master before candidate viewing. The independent display formula reproduced every odd-half photograph channel exactly, maximum u16 difference0. The display baseline/ICC and output hashes are retained under `outputs/multi-stack/completion/independent-photographs`. Nine centers were selected from the odd-half and dense-control locators before candidate pixels, then frozen in [interleave-rois-frozen.json](interleave-rois-frozen.json), SHA2562b866eeaf59a99448fcf50a01fd0203ae11125357ebf267722638e6bc45d7aaf.

| Native witness | Observation across halves and combined |
| --- | --- |
| flat-gray | Similar smooth field and small marks; no visual noise estimate |
| qr-grid | Same broad edge halos and square structure |
| qr-corner | Same nested-square boundary and halo, no added detail |
| fine-radial-labels | Same fine label/bar separation and unresolved central pattern |
| fine-bars | Same line boundaries, soft fine groups and small color fringes |
| bright-dots | Same round boundaries and chromatic rim |
| dark-dot-field | Same dot/defect structures and background texture |
| lower-radial | Same merged central spokes and persistent edge fringes |
| fine-grid | Same resolved/unresolved bar groups; no new reliable pattern |

The combined and both half controls use canvas[58,39,3400,2267] in plane pixels, delivering6800×4534. Ordinary182 is7032×4688 with a separate measured map and cover placement. Its broad landmarks were selected from its own control overview; normalized center correspondence is approximate. Its native crops are not registered pixel correspondences. No dense/candidate pixel difference or scale-confounded sharpness metric is used.

Root requested the next causal stimulus: pitch8 positions0,8,…176 and offset4 positions4,12,…180. [prepare-sparse-interleave.py](prepare-sparse-interleave.py) staged46 distinct, hash-verified existing copies into `outputs/multi-stack/completion/interleave-pitch8-inputs`,23 per pass, without opening original RAWs or decoding. The source preparation and each copied byte payload are bound. The first sparse single-half output must supply the next display/witness freeze before the combined output is viewed. Dense182 remains the union ceiling, with its separate gauge acknowledged.

## HDR precision: active weights, no additional visible benefit yet

The precision result preserves the earlier successful two-exposure result's chart structure and avoidance of the long-only blur/halos in QR, bar, dot and radial witnesses. It adds no clearly recognizable fine structure or visible noise benefit over equal-weight HDR or the best short-only control in these12 frozen witnesses. Several QR/bar boundaries remain mildly softer than the short-only rendering. No new large seam or color break is visible in the complete precision scene. These observations do not justify declaring an incremental photographic gain.

Exact serialized warpmap, canvas[26,17,3464,2310], ordered source/gain pairs and development reference pass1 match the previously reviewed equal HDR. Full dimensions are6928×4620. The old physical display remains fixed at black0, white4, contrast0.55, exposure gain1. The same earlier12 origins were reused without adjustment. The map equality check used the actual serialized map, not just matching dimensions. Existing source support and clipping qualifications in [the prior review](../../review/hdr-photographic-review.md) remain applicable; display gray/white alone is never clipping evidence.

All12 retained witnesses were reviewed against equal HDR, short2.5s and long6s: gray-ramp-middle; adverse-flare-p12; qr-white-black-grid; qr-corner-boundary; large-radial-star; fine-resolution-bars; bright-dot-field; low-contrast-dot-field; lower-radial-spokes; clipped-core; blue-clipped-core; clipped-boundary. The previously observed long-only blur/plateaus remain obvious at QRcorner, bars and bright dots. Equal and precision HDR are closely similar. The two clipped-core witnesses are mostly flat; a more uniform field is not proof of recovered fine detail. The low-contrast dots and gray field do not establish temporal sigma from their spatial texture.

MEASURED actual contribution receipts show that the precision option was exercised. At band0,334,547,156 group-pixel cases used precision versus10,832,880 missing-prediction cases. Those are accumulated group-pixel events, not unique final pixels. The frozen witness observer in [inspect-precision-contributions.py](inspect-precision-contributions.py) reads saved maps only. Its full bounded results are [precision-witness-contributions.json](precision-witness-contributions.json).

| Witness or scope | Median final normalized fixed-guide fraction, band0 | Implication |
| --- | ---: | --- |
| gray-ramp-middle |0.99934|Precision materially contributes here |
| qr-white-black-grid |0.99993|Precision contributes to this finest band; band2 median is0.00008 |
| low-contrast-dot-field |1.0|Active precision, without visually demonstrated new detail/noise gain |
| qr-corner-boundary |0|Repeat eligibility is absent at the median coefficient |
| fine-resolution-bars |0.00206|Most local finest-band output does not use precision |
| bright-dot-field |0.05070|Limited median precision contribution |
| all three clipped witnesses |0|No local repeat precision at the median; unchanged appearance is expected |

At band2, high-contrast QRcorner, bars, brightdots, lower spokes and all clipped witnesses have median fixed-guide fraction0. At band5 most witnesses are0, while low-contrast dots retain0.29538. These maps describe exact normalized band weights before collapse/demosaic/hull clamp. They do not measure final-pixel temporal variance or independence, and effective-source counts are not noise calibration. This closes the no-op-control ambiguity without turning active weights into a quality claim.

## SR ROI04 bounded inspection

The full192×192 native/candidate board at `outputs/multi-stack/completion/sr-roi-04/inspection/comparison-native-pixels.png` was viewed at native pixels. The earlier obvious purple channel pits do not recur visibly; no new large seam/color artifact is apparent. Both arms retain the same turquoise mottling, dark voids and bright cyan/white grains. No new recognizable resolved structure is established. Only2,265/36,864 pixels receive coherent all-channel replacement; the rest remain native exactly. Near-identical overall appearance is expected and cannot validate the assumed0.1 registration uncertainty. Actual measured registration, held-out original prediction and a complete photographic output remain required.

## Commands and retained evidence

All commands were run from the isolated multi-stack worktree with no engine/RAW decode. The helper forces numerical library workers to1 and processes full masters in128-row strips; native observations are384×384 copies. Successful commands returned exit0:

```text
python -X utf8 -X faulthandler experiments/multi-stack-2026-10-28/completion/review/prepare-completion-displays.py control
python -X utf8 -X faulthandler experiments/multi-stack-2026-10-28/completion/review/prepare-completion-displays.py dense-control
python -X utf8 -X faulthandler experiments/multi-stack-2026-10-28/completion/review/prepare-completion-displays.py interleave
python -X utf8 -X faulthandler experiments/multi-stack-2026-10-28/completion/review/prepare-completion-displays.py hdr
python -X utf8 -X faulthandler experiments/multi-stack-2026-10-28/completion/review/inspect-precision-contributions.py
python -X utf8 -X faulthandler experiments/multi-stack-2026-10-28/completion/review/prepare-sparse-interleave.py
```

[prepare-completion-displays.py](prepare-completion-displays.py) binds the original display helper. Per-arm readbacks retain full master/photo/display/ICC hashes, dimensions, source finite checks and exact crop pixel hashes. [native-comparison-layout.json](native-comparison-layout.json) binds all21 paste-only boards. An initial tool JavaScript syntax error while submitting the board assembly executed no command; the corrected one-shot Python assembly succeeded. No failed artifact is used in this review.

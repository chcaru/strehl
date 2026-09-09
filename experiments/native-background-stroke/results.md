# Background-stroke source result

2026-09-09. **MEASURED: stronger persistence in sensor coordinates.** Both green-phase contact sheets show a compact round dark feature at the same original sensor position in all five selected captures. Under the held reference-to-frame scene transform, the finite feature moves horizontally across the view. Its two-dimensional extent distinguishes this observation from the infinite-horizontal-line ambiguity. Root visually inspected both sheets; independent interpretation is in independent-results.md.

This is evidence of a captured sensor-coordinate-persistent feature. It supports, but does not prove, its contribution to the elongated output mark. A foreground-derived map can disagree with a background surface; this inspection alone does not establish physical dust, a calibrated attenuation, or a safe correction. The original generic hot-pixel null and unrelated right-border map dispute remain closed.

Command actually run from the repository:

~~~powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B experiments/native-background-stroke/run.py
~~~

Source revision: 7d886d2611740b33a3d2632fc95f5dca6c58472a. Exactly five original RAWs (indices 0,26,52,78,104), five corresponding supplementary TIFF patches, five secondary decodes, one controls job and one analysis job. All 12 bounded children completed normally, with no cleanup errors. Summed child CPU was 7.0625 seconds; summed child wall time was 7.609 seconds. This is diagnostic cost, not full-stack speed. Original listed input metadata remained unchanged. No RAW or primary photograph was modified.

## Decoder and coordinate admission

All 1459200 interior u16 sensels match exactly between rawpy 0.27.0 / LibRaw 0.22.1 and the existing M61 strehl-raw executable, including every four-phase digest. Secondary executable SHA256: ecf20e1b1e639fc3b86fe82d26a3e3ca02fd326549aa6353e80ad4480682d89d. The executable was held, not rebuilt; the current owning caller source is bound and its last source commit is 052697263a1eb35a05426b3ab2b454c62da25d06. Exact pixel agreement admits these patches independently of a fresh-build claim.

Metadata is not identical: rawpy reports visible width 7028 and white level 16383, versus strehl-raw active width 7032 and white level 15360. Both report black 512 and the compared active origin is zero. This diagnostic uses black-subtracted DN in a common interior rectangle, without white normalization. It does not establish full-image decoder equivalence or cross-decoder normalized-radiance identity.

The independent sampler controls passed 80 affine cases, with maximum error 0.000244140625 DN and zero storage-origin discrepancy. A missing delivered-crop origin fails by 56.5 DN. Both green phases distinguish planted scene-following versus sensor-fixed finite two-dimensional features; identity/wrong-direction controls fail as intended. Uniform and live infinite-horizontal fields refuse evidence. These controls prove arithmetic, not real alignment truth.

## Actual source views

![G1 sensor and scene views](C:/dev/blog/death-of-software/projects/strehl/experiments/native-background-stroke/run-1/contact-G1.png)

![G2 sensor and scene views](C:/dev/blog/death-of-software/projects/strehl/experiments/native-background-stroke/run-1/contact-G2.png)

All panels use the same linear display interval, 3890.8327 to 5264.0678 black-subtracted DN; none of the 20 views clips at either endpoint. Each sample spans two native pixels. Sensor views preserve original phase samples; scene views use phase-preserving bilinear interpolation, so grain sharpness is not a registration criterion. Supplementary Lightroom patches are retained but were not used to infer the RAW feature's cause.

The fixed broad rectangles fail as local attenuation measures: every stroke-minus-clean mean is positive even though the compact feature is visibly dark. Background shading and the 190-native-pixel vertical separation dominate these means. This is a useful negative result about the statistic, not evidence that the mark brightens the image. No spatial SD, temporal sigma, fitted gain or noise calibration is inferred.

| Original index | Gauge | Green phase | Stroke mean DN | Clean mean DN | Stroke minus clean DN |
|---|---|---|---:|---:|---:|
| 0 | sensor | G1 | 4888.894 | 4833.745 | +55.149 |
| 0 | sensor | G2 | 4879.633 | 4825.675 | +53.957 |
| 0 | scene | G1 | 4867.832 | 4814.040 | +53.793 |
| 0 | scene | G2 | 4858.854 | 4805.882 | +52.971 |
| 26 | sensor | G1 | 5045.193 | 4995.845 | +49.348 |
| 26 | sensor | G2 | 5036.629 | 4987.021 | +49.609 |
| 26 | scene | G1 | 5043.561 | 4989.758 | +53.802 |
| 26 | scene | G2 | 5035.199 | 4981.319 | +53.880 |
| 52 | sensor | G1 | 4654.609 | 4581.710 | +72.899 |
| 52 | sensor | G2 | 4646.276 | 4573.190 | +73.085 |
| 52 | scene | G1 | 4654.609 | 4581.710 | +72.899 |
| 52 | scene | G2 | 4646.276 | 4573.190 | +73.085 |
| 78 | sensor | G1 | 4566.807 | 4449.406 | +117.402 |
| 78 | sensor | G2 | 4558.495 | 4441.376 | +117.119 |
| 78 | scene | G1 | 4558.633 | 4444.779 | +113.853 |
| 78 | scene | G2 | 4550.823 | 4436.666 | +114.156 |
| 104 | sensor | G1 | 4480.758 | 4334.967 | +145.791 |
| 104 | sensor | G2 | 4472.221 | 4326.265 | +145.956 |
| 104 | scene | G1 | 4468.886 | 4321.991 | +146.895 |
| 104 | scene | G2 | 4460.343 | 4313.823 | +146.520 |

## Decision

Close this five-file diagnosis with the sensor-coordinate-persistence finding. No default changes and no enlarged source inspection follow automatically. The next decision is one targeted causal intervention or pipeline observation at this nominated feature; it must preserve a clean/real-detail control and must distinguish a local improvement from global SOTA quality. Existing source correction hooks are being assessed before adding any new mechanism. SOTA photographic quality and a fair competitive timing result remain unproven.

Rule48 follow-through: root also viewed all ten direct320x155 gray strips in run-1/unscaled-views, each with sensorleft andsceneright, onePNGpixelper phase-grid value, noresizing andthesame documentedDNtransform. This confirms the finite-feature persistence at native phase sampling; thelarge labelledcontacts are presentation/context. display-views.py holds the exact scriptcontents run through Python -I -B stdin; views.json binds everystrip. No newsourcepixels, fit or metric was computed.

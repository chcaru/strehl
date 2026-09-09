# Independent five-frame background diagnosis

2026-09-09. Root executed committed source `7d886d26`; this reviewer inspected saved controls, process/decoder/output records, and both complete G1/G2 contact sheets. No additional pixels, RAW decode, metric rerun or product execution by this reviewer.

**Conclusion: the nominated region contains a captured dark feature with clearly stronger sensor-coordinate persistence under the held map. Its physical origin and contribution to the long delivered stroke are not yet proven.** This finite population can close with a positive coordinate observation; it need not be enlarged to reach that conclusion.

## What the observations distinguish

In both green contact sheets, the compact dark feature retains its finite outline and location across all five sensor-coordinate panels. In the scene-sampled panels the whole feature, including its left and right ends, moves substantially from right to left. The original indices are the fixed 0,26,52,78,104. This is not the ambiguous infinite-horizontal-line case: a localized two-dimensional blob is visible before any diagnostic resampling or merge. It is therefore stronger evidence than apparent row-profile persistence or similarity of box averages.

This supports a feature already present in the captured RAW samples and fixed in sensor coordinates over these observations. It does not establish dust, a hot/dead pixel mechanism, or a calibration suitable for correction. The held map was fitted to the subject; background depth and optics can differ from the bean's geometry, so coordinate persistence is not a physical identification of which surface contains the mark. Both green phases agree in appearance, but they share the same five captures and are not independent photographic replications.

The current source observation also does not prove that this compact feature produces the longer native output stroke through the actual gather, focus weighting and collapse. Those production contributions were not observed here, and 100 source frames remain uninspected. The earlier refutation of generic hot-pixel/dust trails remains intact. The existing right-border dust map does not overlap this nominated left region; these results do not justify turning it on as a fix.

## Re-choice against misleading summaries

The frozen stroke-minus-clean averages are **positive in every frame, gauge and green phase**, spanning about +49.35 to +146.89 DN, even though a local dark blob is obvious. The broad boxes at different vertical positions include changing background shading, and the selected mark occupies only a small part of the lower box. The sign of their difference cannot diagnose attenuation or absence. In particular, those values must not be converted into a dust depth or a noise claim. The shared display range (3890.8 to 5264.1 black-subtracted DN) reveals both the feature and the broad brightness changes instead of fitting each panel independently.

This independently re-chooses finite two-dimensional location over the aggregate contrast statistic. It also separates location from appearance: focus, illumination, exposure, interpolation and local shading can change apparent depth or sharpness. The allocated primary interface did not supply exposure/ISO/aperture metadata; it would be unsupported to attribute the observed frame brightness changes to one of those causes. No spatial standard deviation is used as temporal noise, no private noise model is fitted, and no output-quality score is inferred.

## Controls, decoder identity and execution

The held controls passed unchanged: 80 affine comparisons, maximum error 0.000244140625 DN, zero discrepancy from rebasing the storage patch, and the live omitted-output-origin destroyer at 56.5 DN. Both scene-following green plants selected the correct gauge on every nonreference frame; their largest normalized squared residual was about 0.00004902 versus at least 1.4106 under identity and 1.2494 under the wrong direction. Sensor-fixed plants had zero sensor-view residual and lost under the scene and inverse views. Both phases refused uniform and live infinite-horizontal nulls. These are commissioned coordinate arithmetic controls, not independent truth for the real alignment.

All five 640x456 interior u16 patches match the secondary decoder exactly: 1,459,200 sensels, zero differing values, zero maximum difference, and all 20 per-phase hashes equal. Their explicit ROI headers use the same origin (112,1304) and dimensions. The primary copies were made inside LibRaw's context, and interpretation followed all five equality checks.

**Pixel/ROI identity does not mean all decoder metadata agree.** Every primary reports visible width 7028 and white level 16383; every secondary log reports active width 7032 and white level 15360. Both report black 512 and origin zero. The selected left-interior samples are exact despite the right-edge extent difference. This diagnostic subtracts the same black level and does not normalize by white, so the disagreement does not alter its views or signed DN contrasts. These receipts cannot justify cross-decoder normalized-radiance equality. Primary RGGB phase codes and all-channel black/WB metadata are recorded, rather than inferred from the full decoded padding.

All 12 bounded jobs exit zero, with terminal accounting, no error, cleanup error or forced termination. Summed child wall time is 7.609 seconds, owned CPU 7.0625 seconds, largest job commit 129,470,464 bytes. The run directory contains 35,312,434 retained bytes at review, below 64 MiB; the completion record confirms original metadata unchanged. No new alignment or whole-stack output was run.

## One next observation

Nominate this captured feature for **one compact observation of its real contribution through gather and collapse at the already frozen output stroke region**, with the observer disabled/enabled output hash placebo required by rule 26. Record which input locations and weights contribute there without changing them. That would connect the source feature to the delivered stroke, or reject that proposed link, before any corrective algorithm is chosen. Do not broaden this into a blind defect search or a speculative whole-stack setting sweep.

Evidence: [G1 contact sheet](run-1/contact-G1.png), [G2 contact sheet](run-1/contact-G2.png), [controls](run-1/controls/controls.json), [decoder comparison](run-1/decode-comparison.json), [descriptive result](run-1/result.json), [completion](run-1/completion.json). Independently checked record hashes: controls `cfdf8e9a67a5871724292dd22b8ee070d0efc4e236b73f134d09cc9da6835ba2`; decoder comparison `a334e7bd567728eb0ba8b57fd70b1fc27c0fb5343afe56c1ee64a80aba323b89`; result `956c9a40b01111f7e65fb6a84219b23f992183058d723bcb5b6fb2d75773d11a`.

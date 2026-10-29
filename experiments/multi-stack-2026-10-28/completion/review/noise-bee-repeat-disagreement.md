# Frozen pair disagreement diagnosis

**MEASURED:** global brightness drift is not the dominant explanation for this pair's discrepancy. No compatibility decision, gain, primary behavior or production source changed. All product/SR admission flags remain false.

## Exact replay and commands

The old `nb-guide-02` saved aggregate evidence and original-site unions but not per-point observations. Root authorized a serialization-only replay of identical targets [1,17], guides [0,3], eight patch/components and256points per scope. `nb-guide-b06` executable SHA256 is `52ed197beab5c08262d541c7546ad5b6144225147043f6c6be264b25c38047a5`; recursive source and product16 library hashes are archived in its build receipt and sources folder.

```powershell
python experiments/multi-stack-2026-10-28/completion/sr/build-roi.py --fingerprint target/release/.fingerprint/strehl-cli-63ce8e1d9f947ed6/lib-strehl_cli.json --out outputs/multi-stack/completion/nb-guide-b06 --source experiments/multi-stack-2026-10-28/completion/review/noise-bee-repeat-compatibility-real.rs --build-id product16-bee-original-points
python experiments/multi-stack-2026-10-28/run-command.py --receipt outputs/multi-stack/completion/noise-bee-compatibility-guide-run-03 --cwd . --env RAYON_NUM_THREADS=1 -- outputs/multi-stack/completion/nb-guide-b06/noise-bee-repeat-compatibility-real.exe outputs/multi-stack/completion/noise-bee-repeat-01/equal outputs/multi-stack/completion/noise-bee-repeat-01/source-cache outputs/multi-stack/completion/noise-bee-repeat-01/inputs/protocol.json outputs/multi-stack/completion/nb-guide-03
python experiments/multi-stack-2026-10-28/completion/review/noise-bee-repeat-disagreement.py --controls
python experiments/multi-stack-2026-10-28/completion/review/noise-bee-repeat-disagreement.py outputs/multi-stack/completion/nb-guide-03 --output outputs/multi-stack/completion/nb-guide-03/disagreement-02.json
```

**VERIFIED:** `nb-guide-03/equivalence.json` checks all eight old aggregate rows exactly equal after removing only the additive observation receipt; all eight footprint files remain byte-identical. Source identities match, four cache hits, zero RAW decodes. Four analyzer controls exercise offset, scalar gain, equal-mean AC attenuation and opposite texture. The attenuation foil proves a same-data affine fit can erase actual AC loss, so fitted diagnostics cannot authorize correction. The1.105s run sits at the runner's one-second polling floor; no timing or sampled-memory claim follows.

## Native identity decomposition

Identity is high+mid+low. Its plug-in noise denominator includes every covariance cross term. Shared noisy Q predictions and previously fitted geometry prevent calibrated real significance. Noisy X and Y cause errors-in-variables bias; same-data fits are optimistic.

| Patch | CFA | Mean Y-X DN | DC fraction of squared residual | Scalar fit reduction | Identity/noise | Low band/noise |
| --- | --- | --- | --- | --- | --- | --- |
| upper-forehead | R | -0.877 | 0.385% | 1.479% | 1.069 | 1.872 |
| upper-forehead | G1 | -0.678 | 0.092% | 0.013% | 1.392 | 3.620 |
| upper-forehead | B | 0.264 | 0.038% | 0.208% | 1.174 | 2.255 |
| upper-forehead | G2 | 0.860 | 0.190% | 0.969% | 1.446 | 3.283 |
| lower-body-hairs | R | -1.118 | 0.251% | 1.448% | 1.974 | 3.549 |
| lower-body-hairs | G1 | 1.133 | 0.093% | 0.173% | 2.203 | 4.059 |
| lower-body-hairs | B | -1.419 | 0.421% | 1.219% | 2.283 | 3.177 |
| lower-body-hairs | G2 | -1.970 | 0.270% | 0.442% | 2.881 | 6.080 |

A neutral gain from the median four-color log-mean ratio on forehead is0.9999388008 (Y-from-X); applying it to body changes native squared residuals by less than0.05%. Learning0.9988173245 on body worsens forehead G1/B/G2. These old validation patches are not relabeled as fresh calibration. Per-color signs differ and a scalar/common offset cannot explain the discrepancy.

A same-data spatial plane removes only0.18-1.03% of native discrepancy. Adding sparse gradients at32sensor spacing removes0.9-6.4%; this is not a consuming subpixel-placement estimate. Fractional source phases vary almost affinely across each patch. Circular spans and raw/detrended correlations are retained, but scene, phase alias, placement and illumination are not causally separable from these observations. Lower-body low-band disagreement remains3.18-6.08times predicted temporal noise despite near-unit amplitude transfer. Neither a changed physical PSF nor its absence is established.

## Deferred photometry contract

**ARGUED, not executed:** disjoint neutral photometry can address actual lighting drift, but this diagnosis gives little reason to expect compatibility here. Root deferred new photometry reads in favor of native-estimator unequal-variance controls.

If reopened, train only on the previously nominated right-thorax512sensor square at active fraction[0.774,0.556]. Retain all forehead/body validation points. Check complete original target, guide, filter and eligibility footprints for train/validation overlap. A bounded provisional subdivision is4x4patches of32quad pixels at local origins[16,80,144,208] per axis. Reuse the existing session-photometry zero-offset scalar recipe (10% trimmed means, median four-color log ratios) and explicit eligibility/limits. Its API currently calibrates passes using multiple pairs/rank span; it is not already a per-frame estimator, and no implicit relaxation is approved.

Anchor named X at gain1, or the explicit primary pass. Scale only Y, apply gain-squared variance, preserve raw-unit per-original expected signal and retain raw/normalized evidence. No additive offset, color gain, spatial fit or average-appearance centering. This is a new normalized-observation estimand, not primary protection or permission to erase intentional lighting differences. Retain reciprocal/errors-in-variables diagnostics and gain uncertainty; fitted gain couples output points.

Required actual fit-to-observer foils: neutral gain positive; differential Gaussian blur with equal DC; color-only blur/illumination; opposite equal-energy texture; same optical pattern with subpixel/CFA alias; stable common defocus; clipping/missing negative taps; footprint overlap. Freeze training and validation photons, geometry and noise. Keep existing5%amplitude and0.5loss limits and every unknown. Common defocus may support preserving its own PSF while averaging, never sharpness or SR. No new original read was launched for this deferred plan.

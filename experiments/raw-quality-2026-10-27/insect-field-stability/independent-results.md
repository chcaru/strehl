# Independent result: close the fixed per-step residual field

2026-10-27. **MEASURED / independently reviewed:** `REFUSED_FIXED_PER_STEP_HYPOTHESIS`. All12 primary held cells have their complete declared populations;10 fail the unchanged20percent MSE-reduction requirement. All six replication cells increase error relative to zero. This is a failure of the predeclared six-scalar stationarity hypothesis, not a missing-data refusal or proof that real geometry is correct. No alignment correction or photographic claim follows.

## Controls and producing path

The [complete control receipt](../../../outputs/raw-quality-2026-10-27/insect-field-controls-1/output/controls.json) passes every frozen check. Exact zero reports no affirmative evidence; noise-only fails every primary cell. The known stable field with shared-acquisition and independent-pair noise passes, and its recovered vector components are within0.001 of the declared values. The literal all88-row training means agree exactly, including the independent MAD-outlier flags. Thus this is neither a refuse-all scorer nor a survivor-only fit.

Held signal reversal, cyclically wrong-site coefficients and wrong-span coefficients all fail every primary cell through the actual scorer. A complete population containing a refused primary row fails its completeness gate. Physically omitting a row and sharing acquisition95 between intervals both raise the intended validation errors. The persistent-bias lookalike has exactly the stable positive's numeric observations and result, yet keeps physical attribution false. That passing foil is an explicit limit: even an affirmative real result could not identify optical movement rather than persistent matching bias.

This controls numerical/scoring logic and one fixed synthetic noise construction. It does not calibrate the real NCC errors, reproduce occlusion, validate a camera-noise model or demonstrate that ordinal step is physical depth. The actual target remains the saved summary's f64 measured-minus-final-similarity vector in each pair's guide coordinates; no new correspondence or common physical feature is inferred.

## Actual held prediction

The [actual receipt](../../../outputs/raw-quality-2026-10-27/insect-field-actual-1/output/receipt.json) retains all7,020 site/pair rows. Training uses88 span8 pairs per site inside acquisitions0–95. Primary held112–207 supplies95 span1 and88 span8 pairs; replication224–298 supplies74 and67. All are present and correlated. Every primary held MAD count is zero. The train/held/replication acquisitions are disjoint, while shared-source dependence within each population remains explicit.

Fitted `(x,y)` vectors, guide pixels per bracket step, are:

- Tile15: `(-0.253968,-0.043881)`.
- Tile41: `(0.020796,-0.035316)`.
- Tile56: `(0.072552,0.038842)`.

| Site | Held span1 | Held span8 | Replication span1 | Replication span8 |
| --- | ---: | ---: | ---: | ---: |
|15|−11.000|−5.894|−15.998|−0.626|
|41|0.331|0.340|−1.131|−1.569|
|56|−3.120|−1.211|−4.651|−1.224|

Entries are **fractional MSE reduction**, with required value at least0.20; negative means the prediction is worse than zero. These ratios are not displacement magnitudes. For example, tile15's held span1 vector MSE rises from0.005325 to0.063894 squared guide pixels. Tile41's two apparent successes do not replicate: span1 MSE rises0.002500→0.005328 and span8 rises0.067875→0.174383 in the replication interval.

The saved16-source blocks support that qualification without replacing the frozen headline population. Tile41's held span8 improvement turns negative in192–207; every replication span8 block is negative, including the explicit short288–298 block. No row-count p-value or IID confidence statement is warranted. Tile15's training mean includes15 later MAD outliers as required; tiles41/56 include none. Filtering those15 after this result would change the question and would not explain the replication failures at the other two sites.

Span32 remains adverse and incomplete in five of six cells: held valid counts51/57/0 of64 at sites15/41/56; replication0/43/0 of43. Tile41's partial held improvement cannot qualify a complete population, and its complete replication cell also worsens the null. No hard case or failed search was silently replaced.

## Decision and evidence boundary

**ARGUED recommendation:** close this exact stationary per-step measured-field hypothesis. Do not rescue it by keeping only tile41's first held interval, discarding MAD flags, shifting focus windows, changing spans or adding a temporal/radial basis under this allocation. The conditional footprint overlap remains useful instrument evidence; it does not change this prediction failure. Focus-dependent geometry, defocus-sensitive correlation, illumination and visibility remain possible causes, with no one cause identified here. A richer correction is not justified by this negative result.

Root's exact [control command](../../../outputs/raw-quality-2026-10-27/insect-field-controls-1/process.json) and [actual command](../../../outputs/raw-quality-2026-10-27/insect-field-actual-1/process.json) both exited0, with no cleanup errors. Controls took0.718s/24,784,896bytes peak job commitment; actual saved-data analysis2.328s/23,658,496bytes, one worker. The actual completion binds analyzer SHA256 `b0205a3ec0f258011be4068de04a60fe5af90ec64cf8ee36100cf886d496cec1`, unchanged source/input bindings and actual receipt SHA256 `8ea62a78e4547d2d540fb2e9d6846aa2e8f20c5a54322a8f113d6459d1810a97`. These are small saved-data job costs, not stacking-performance claims.

This review read retained results only. No threshold, source, fit, RAW data, crop or image was changed or executed. There is no new stack output and no demonstrated image-quality improvement; the photographic goal remains unresolved.

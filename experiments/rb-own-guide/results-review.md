# Independent R/B own-guide results review

**MEASURED: reject full photographic admission of this operator; preserve the demonstrated colour-detail headroom.** The fixed screen completed, but fails its flat-noise and developed-green guards. No rerun, retuning or full render was performed for this review.

The executed test exits0 in3.25seconds, one test passed, with peak job committed memory393,760,768bytes. All94 bound source hashes and the executed binary match. The returned screen explicitly records photographic_replay_admitted=false: test-process success is not quality success.

## Useful positive result

All four positive scene/ISO combinations exercise different own-colour weights, changed R/B output, recoverable focused-source detail, and harm from deliberately swapped guides. Improvement survives the matched-estimator green arm, which uses the same sixteen gathers and noise-floor construction. The result therefore cannot be dismissed as merely changing the canonical floor estimator.

| Scene / ISO | Own RGB error / canonical | Own RGB / matched green | Own chroma / canonical | Own developed G / canonical |
|---|---:|---:|---:|---:|
| Focus offset /100 |0.1901|0.1904|0.1868|1.9182|
| Focus offset /400 |0.2639|0.2645|0.2312|1.2622|
| Colour only /100 |0.4370|0.4275|0.4170|1.2386|
| Colour only /400 |0.4495|0.4329|0.4121|1.4213|

At ISO100 the offset R/B component recoveries rise from about0.595/0.595 to1.015/1.026; colour-only recoveries rise from0.571/0.426 to0.819/0.865. The latter focused-source witnesses recover0.824/0.879, so this is recovery of representable colour structure, not an unexercised or blank plant. Recovery above1 is overcontrast, not extra truthful detail; the independent absolute RGB/chroma errors and truth-capped component guards remain necessary.

## Why the complete operator fails

Flat RGB error rises to1.4650 and1.4561 times canonical at ISO100/400; chroma rises to1.5130 and1.4998. These exceed the frozen1.25 bars. Against matched-estimator green the RGB ratios remain1.3391/1.3336 and chroma1.3776/1.3780. Thus the colour-specific weighting adds flat error even after separating the floor-estimator change. This is a spatial truth error on a known constant generated field, not an empirical camera temporal-sigma or calibration estimate. It does not isolate noise-selection coupling, finite-probe uncertainty, or a particular floor threshold as the cause.

All four positive cases fail the developed-green guard despite much lower total RGB error. At ISO100 offset, green RMSE rises from0.00195238 to0.00374513 while total RGB falls from0.0194860 to0.00370383. Every original green CFA sample in the merged outputs is exact, and the same MHC development is used. This verifies cross-colour propagation into reconstructed green through the final demosaic path. It does **not** establish that better colour recovery itself causes noise, or partition green error between altered deterministic structure and noise. Keeping measured green sites exact is insufficient to keep delivered green accurate.

The genuine coloured-ray case also fails the green guard, narrowly:1.10845 against canonical's1.10 limit, while total RGB/chroma improve to0.84562/0.76848. Zero-offset neutral, all three crossing-depth windows, and clipped-glint adjacent/outside windows pass their frozen guards. Those local passes do not cancel either flat failure or the green failures. The clipped fixture contains9 original codes at16383; adjacent/outside near-unity errors provide nonregression evidence only, not restoration of clipped radiance or removal of the real photograph's fans.

## Mechanical scope and decision

Canonical-guide identity, terminal base, original input hull, source immutability, and G1/G2 bit equality pass in every arm. All five arms are byte-for-byte equal at the array/RGB-hash level with diagnostics on/off on ISO100 offset. Independent floor controls exercise the divide-by16 factor, green covariance cancellation/reinforcement, source-plane routing and invalid-input refusals. These are operator checks, not random-independence or sensor-noise calibration proof.

This is a substantial generated demonstration that colour-specific guidance can recover detail missed by green guidance, alongside a measured failure of this complete noise/merge/demosaic combination. Close this exact candidate for photographic replay and promotion. Retain its positive result as headroom for a separately specified intervention; do not weaken the current bars or claim the user's glints are explained by axial colour focus.

Screen SHA256 `5bae9a282349905a2d7dc391a55ced39e19f0eda9c6d24ec75706f96c3ed7cb3`; process `266437f1dd1e221a836229e91087cedf8e7e91637cfce7f93a3e2babeee9af20`; bindings `2a6477ef10e087b276566431afc93636fc02c299acedf4ab0120ed9f13ff391a`; completion `4f0620b5606db2dea305d866f5e27df6373a4789da4971d534072343ecc4ab3d`, all under `controls-1/`.

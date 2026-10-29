# Geometry-only low-pass checkpoint

Status: VERIFIED synthetic instrument controls; photographic registration pending. Core affine integration remains unregistered and uncompiled.

The existing raw-CFA local registration result remains the baseline: 72 color-pair measurements, no saved-placement certificate, and no all-RGB admitted source. The 0.15 anchor-sensor-pixel bound remains unchanged.

The optional instrument filters each original, unaligned same-color plane with an explicit finite separable Gaussian before local NCC. It does not filter the reconstruction inputs or delivered image. Sigma zero preserves the original diagnostic arm. Sigma 1.2 quad pixels is the proposed synthetic/photographic arm, to suppress the aliased .35/.12 cycle-per-sensor carrier in the known-truth control while retaining lower-frequency 2D structure. This does not undo aliasing and cannot prove optical resolution.

For independent injected original noise variance v and 1D taps g, the filtered variance is v*(sum(g*g))^2. The central-derivative variance is v*sum(g*g)*(sum(g*g)-sum(g[k]*g[k+2]))/2. This covariance term matters; using independent filtered-neighbor noise would misstate the information gate. No patch noise is fitted. Complete original support/clipping masks pass through every tap, and disjoint training/holdout margins include filter support.

Prepared controls:

- geometry-lowpass-controls.rs: flat/one-axis negatives first; 39 measured-trajectory RGB pairs with known high-frequency/colored-edge signal; raw alias foil versus the filtered objective; smooth low-pass positive; wrong-placement, clipping and spatial-motion negatives.
- local-lowpass-unit-tests.rs: independent impulse-energy covariance check, poisoned/missing tap footprint, invalid sigma refusal.
- affine-regression-controls.rs: six independent moment/operator controls already prepared, without any candidate/default integration.

Root schedules native tests and any cached photographic run. Source-only checks do not establish that these assertions pass. Production integration will use the tested post-normalization/WB/exposure and post-MHC camera-RGB writer seam, before matrix/highlight/tone; WB remains before MHC.

## Root-run results

VERIFIED: root ran the registered geometry-lowpass flat-first selection (3 passed), then all 12 geometry controls, and all 6 independent affine-moment controls. Receipts are outputs/multi-stack/completion/sr-lowpass-flat-controls-01/receipt.json, sr-lowpass-controls-01/receipt.json, and sr-affine-controls-01/receipt.json. The full commands are retained there; each uses --locked and --test-threads=1 with native exit0. No camera input was read by these tests.

MEASURED on the known high-bandwidth measured-trajectory plant: all 39 unfiltered color pairs failed the saved-placement certificate; the filtered maximum error was 0.087312 anchor sensor pixels under the unchanged 0.15 bound. This demonstrates that the previous raw instrument can be biased by CFA aliasing. It does not establish that any actual camera placement is accurate. The next frozen ROI command uses --registration-geometry-sigma-quad 1.2 with the same original cache, sealed focus census, source set and ROI, retaining the raw result in its original output directory.

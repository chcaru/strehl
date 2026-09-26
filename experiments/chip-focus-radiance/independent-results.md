# Independent direct-radiance observation review

Generated controls and complete photograph reviewed, 2026-09-25. The complete
candidate is rejected for protected native-detail loss despite reduced broad
coloured spread; see `photographic-review.md` for all 25 fixed native pairs.
The original chip-focus-front
two-band prediction gate remains failed; this is a separately authorized
observation using its narrower fine-band support, not a passed proxy gate.

MEASURED: build-1 failed on an ambiguous floating-point literal in the
independent oracle. An explicit f64 annotation repaired compilation without
changing its formula. Controls-1 then reported three passes and one instrument
failure: the wrong coordinate factor cancelled exactly at the first chosen
point. The correction reused both original positive points and retained that
first-point degeneracy. Missing-factor errors are now [0, 0.135], so the fixed
0.01 rejection bar detects the error at the second point. It does not detect
it at every point. No coordinate, operator, image stimulus or quality bar changed.

Fresh build-3 compiled and controls-2 passed all four tests (root job 0.344 s).
Independent SHA256 checks prove `identities.json`, `planar.json` and
`refusal.json` are byte-identical between controls-1 and controls-2. The repair
therefore did not move the successful numerical, image or noise measurements.

| Actual operator control | Measured result |
| --- | --- |
| 299 identical high-DN / negative sources | Maximum absolute error 0.0078125 DN; within the declared f32 accumulation bound |
| One supported source; uniform-weight mean | Exact expected output in both fixtures |
| Known planar focus, radiance MSE | 55,248.281 DN² versus uniform mean 951,982.574 DN² |
| Shifted front; erased detail | 1,331,480.080 / 1,339,927.645 DN²; both rejected by the same positive bar |
| Flat independent noise, MSE | Narrow average 88.206 DN²; average individual source 399.947 DN²; uniform mean 12.119 DN² |
| Refusal controls | Order, missing/duplicate source, nonfinite/invalid data, zero mass and finite-input sum overflow all refused |

The flat result is both a benefit and a cost: the narrow average reduces noise
relative to one source, but has about 7.28 times the uniform mean's MSE. The
structured positive demonstrates the known focus versus noise tradeoff on the
fixed local-blur sinusoid fixture. It does not establish native photograph
quality, occlusion ownership, sensor calibration or appropriate reconstruction
bandwidth. Its MSE gain must not be presented as a percentage improvement in
the user's chip photograph. These tests consume f32 planes at the actual new
accumulator boundary; actual RAW gather/CA/MHC transfer still belongs to the
full adapter and photographic review.

VERIFIED source review: the candidate consumes the current BandWorker's four
gathered planes once per source, applies one shared spatially fitted weight,
and reconstructs complete radiance including DC. The canonical comparator keeps
its existing fold/chunks and must match current delivered RGB16/ICC. Baseline
tone is pinned for both writes. The candidate deliberately bypasses pyramid
assembly and the input-range clamp; it must have finite positive mass everywhere
or produce no candidate. Earlier native-coherent-estimator also averaged full
radiance; the distinction here is the globally fitted front and nonuniform
schedule, not a novel arithmetic reconstruction class.

Root commands, with the bounded wrapper and retained bindings:

```text
python experiments/chip-focus-radiance/run.py build --out experiments/chip-focus-radiance/build-3
python experiments/chip-focus-radiance/run.py controls --build experiments/chip-focus-radiance/build-3 --out experiments/chip-focus-radiance/controls-2
```

The wrapper executes the four exact Rust tests under
`merge_cmd::chip_focus_radiance::independent_controls::` with one test thread.
The preserved first failure is `controls-1/process.log`; final records are in
`controls-2/output/`. Planar receipt SHA256:
`58e0c1c2ed4fa4c6f8a4eba7300f93e2d3d79a17d7a5e134e528bb72d5802562`.
Both the control receipt and completion explicitly deny native photographic
qualification. No width, iteration, source, plane or quality-bar tuning followed.

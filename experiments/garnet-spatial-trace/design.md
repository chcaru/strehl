# Garnet rectangular islands: test numerator overflow first

SOURCE REVIEW / DERIVED hypothesis, 2026-09-25. This note makes no new RAW,
GPU or numerical-run claim. Root independently found both hard rectangles in
the four cached merged CFA planes, before WB, demosaic and rendering; that
rejects a writer-only origin. The dormant writer-stage probe is not required
for this upstream diagnosis. Existing full-output photographic comparisons
remain the reference, and no fix is implemented here.

## A concrete unchecked arithmetic path

Actual current `pyramid.rs::select_weight` caps the general exponent at
`exp(80)`, about `5.54e34`, and stores f32 weights. That ensures a weight is
finite. `accumulate_level` nevertheless adds `weight * Laplacian_coefficient`
into a separate f32 numerator. A finite coefficient of 10,000 DN can make one
such product exceed f32's approximately `3.40e38` limit. Several smaller same-
sign products can also overflow while their weight sum stays finite.

The existing `a_large_band_energy_does_not_overflow_the_weight` and
`the_weight_sum_cannot_overflow_over_a_long_stack` tests check the weight and
denominator, not the weighted numerator. The newer
`assert_pedestal_accumulators_finite` explicitly checks only
`AdmissionMode::FloorPedestalV1`; the user's current `HardFloor` route does not
enter it. Finite cached output therefore does not clear this mechanism.

A negative-infinite resolved coefficient survives addition of finite bands.
The actual separable positive expand stencil spreads it across a rectangular
support. Away from borders, one band-2 coefficient reaches a 13x13 CFA-plane
rectangle (26x26 native sites); band 3 reaches 29x29 CFA sites (58x58 native).
The final `InputRange` clamp then replaces negative infinity with the finite
per-pixel lower input bound. That can yield an abrupt, ordinary-textured dark
rectangle. This is a specific prediction of the source, not proof that these
particular photographed rectangles followed that path. Opposite infinities
could instead make NaNs and have different downstream behavior.

GPU scheduling is not a matching square tiler: current code uses 64x1
invocations and full-width 256-row strips. Native MHC uses a local 5x5 stencil;
the writer runs complete rows and per-pixel development. Pyramid grids have
the right broad scales but scale resemblance by itself establishes nothing.
Gathered codes can exceed the original 14-bit container after MHC/Catmull
overshoot because the rounded gather quantizes into u16. A merged value above
15871 black-subtracted DN does not establish original RAW clipping or a decoder
defect. These alternatives are not categorically cleared by source inspection.

## Minimal actual-consumer observer

`core-observer.rs` is inactive unless `STREHL_GARNET_NUMERATOR_CENSUS=1`.
Root includes it as `pyramid::garnet_spatial_trace` under the existing
`native-correction-variance` feature and inserts four calls in actual `finish`:

```rust
let mut census = garnet_spatial_trace::start(self);
// after actual per-plane, per-level normalization/fallback:
garnet_spatial_trace::resolved(census.as_mut(), self, c, k, out);
// directly before and after the final existing InputRange clamp:
garnet_spatial_trace::pre_hull(census.as_mut(), self, c, &img);
garnet_spatial_trace::post_hull(census.as_mut(), self, c, &img);
```

Each call receives the existing arrays read-only. No weights, coefficients,
gather, normalization, fallback, collapse, bounds, chunk schedule or writer are
reimplemented. The observer prints `GARNET_NUMERATOR_CENSUS ` followed by JSON.
It records actual per-plane/band numerator, denominator, unweighted sum and
resolved-coefficient finite/nonfinite counts, then pre/post-hull image counts.
The first 64 offending global coordinates and f32 bits are retained per array.

For the exact full garnet domain/frame count, it additionally records complete
row-major run-length masks on CFA ROI `[2334,929,192,192]`, corresponding to
native output `[4668,1858,384,384]`. Nonfinite kinds are 1=positive infinity,
2=negative infinity, 3=NaN. No mask entries are silently truncated. Post-hull
masks state which bits changed and which formerly nonfinite sites now exactly
equal the stored input lower/upper bounds. Resolved-band windows use nominal
decimated coordinates and explicitly do not claim to be full filter support.
There is no need to retain another source image volume.

Root runs the existing full 183-frame garnet Current recipe with the same
canonical chunks/crop/warp/noise and actual writer. Require complete output
pixels against the historical Current, then observer-on/off whole-file identity
from the same fresh binary. A changed diagnostic render invalidates attribution.
The complete master and its untouched regions provide the observer control;
the native diagnostic panel is evidence about origin, not a substitute delivery
image or an improvement claim. Independent numerical controls exercise the
actual BandMerge and own any future regression assertion.

The hypothesis is rejected for this run if numerator/resolved/pre-hull arrays
are finite. If nonfinites occur elsewhere but their exact propagated mask misses
the islands, the arithmetic issue is real but does not explain these islands.
Only nonzero, matching masks followed by exact lower/upper-bound replacement
exercise the proposed chain. Record an empty or nonmatching mask as such; do
not count a passing observer test as confirmation of the defect.

If this specific mechanism is absent, the next single full-context diagnostic
would retain actual gathered CFA ROI values over all 183 sources plus actual
per-band fallback/denominator and pre/post-hull fields. Three smooth sampled
originals cannot exclude another source or a gather-stage defect. That larger
trace is deliberately deferred until this cheaper arithmetic question is answered.

Mechanical prior-art command run during the source review:

```powershell
& 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -I -B experiments/ORCH-drift-check/prior_art.py rectangular blocky patch pyramid clipping
```

It routes to BUILD-ELECT, V-DILUTE, M120, BUILD-SOFTGATE, M130,
BUILD-PYRNOISE and M194. Those broader patchwork/selection histories do not
replace the exact weighted-numerator and final-hull checks described here.

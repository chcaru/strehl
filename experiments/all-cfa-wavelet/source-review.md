# Independent source audit

**Decision: no blocking source defect found.** This admits the frozen generated
controls for root execution once their author declares them ready; it does not
admit a photograph or establish quality. No build, test, RAW read or numerical
measurement was performed by this reviewer.

Reviewed `implementation.rs` SHA256
`02993079671a30aa80d41238d388f0f16211514bfe1edbca3dbd0fb2462e21df`
and the five-line test-only CLI registration. The earlier checkpoint was
`34d9cc647102d338b8049cc60846b46c73e32752113df0166ea49e32cabc5452`.

**VERIFIED by source inspection:**

- Evidence sums four squared complex magnitudes, each scaled by normalized
  WB gain squared. It does not sum complex colour coefficients first.
- Original-DN planes are checked bitwise against `Frame::active_row` at the
  crop's original CFA sites. Noise uses explicit `[R,G1,G2,B]` enum mapping,
  avoiding the different `CfaPlane::ALL` order. Each supplied per-plane model
  is evaluated before WB squared; the baseline green-mean variance is only
  retained as diagnostic provenance.
- Complex LL is retained, packed and inverted in the correct nested order.
  Second-level kernels compose offsets `(j-3)+2*(k-3)` and complex products,
  coalescing all paths modulo the original axis length before squared norm.
  The separable two-dimensional variance then multiplies these effective
  axis energies against original independent-site variance. It never filters
  scalar LL variance recursively.
- Each direction/level has one denominator and one weight shared by all four
  complex colour coefficients. The deepest LL has no detail weight and uses
  the source mean; zero-weight detail also uses that mean. Reconstruction,
  input-range clamp and final camera-RGB/MHC route match the stated scope.
- Only the current source's transforms and cumulative fields are retained.
  The actual baseline uses two bands and the same original sources/crop.

The final amendment adds `compare_generated_with_diagnostics(..., bool)`;
the original entry passes true. The conditional controls only own-plane
positive-support/aggregate-zero witness computation. Evidence, production
weight calls, numerators, denominators and reconstruction are outside it.
Its output non-interference still requires the independently specified exact
on/off comparison on an exercised fixture; source reading cannot replace it.

**Pending numerical evidence:** the independent plan covers full-transform
impulse variance on a 12x16 field, including wrapped repeated paths and a wrong
scalar-recursion destroyer; odd crop phase; and the original-CFA noise hashes.
Its 56-native-pixel trim exceeds the derived 23-quad composed dependency plus
one quad of final MHC support. Controls were still being authored when this
review was recorded, so their final implementation and outcomes are not
certified here. Actual source truth recovery, aggregate-floor suppression of
weak colour, phase sensitivity and flat noise remain binding quality questions.
This identity-only calculation makes no fractional-gather covariance claim.

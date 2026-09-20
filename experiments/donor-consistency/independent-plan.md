# Independent donor-consistency controls

Fixed before execution. Root builds/runs; this reviewer owns controls only.
This is a labelled photographic counterfactual, not a general focus estimator
or a SOTA claim. Controls commission its actual coefficient consumer, not the
correctness of the photographic donor labels.

Use one compact asymmetric generated three-source/four-plane u16 fixture,
converted to black-subtracted f32 at consumption, plus literal scalar fields
where they make arithmetic observable. Exercise real BandMerge/finish and
public production Pyramid Gaussian/Laplacian/collapse operators. Inject one
fixed variance field; do not fit a noise model or interpret it as calibration.
Keep default SoftPower, mean base/fallback and InputRange with a small fixed
band count. Retain all original source arrays and assert unchanged hashes.

1. Check capsule geometry independently: endpoints, midpoint, radius16/20/24,
   segment reversal, zero-length disk, asymmetric signs and off-axis points.
   Radius16 is1, radius20 is0.5, radius24 is0. Literal f64 geometry versus the
   f32 implementation must agree within1e-4 in mask value. Use an odd native offset and a
   compact crop around the real fixed facet capsule. Evaluate the exact actual
   shared-quad coordinate (2*x+0.5,2*y+0.5) plus output-native offset. A second
   offset changes mask phase; it must match the analytic geometry, not be
   required to produce an identical field. No original photographs are read.
2. Build the expected Gaussian mask pyramid with public production
   `Pyramid::build_gaussian`; compare every stored mask at every attained
   level. Include a spatially varying fractional mask and two overlapping
   masks. Independently normalize an over-one sum while retaining relative
   membership; verify live overlap and nonbinary weights actually occur.
   Nonfinite, negative, above-one or wrong-sized inputs must be refused.
3. Obtain resolved baseline coefficients through the diagnostic seam and
   independently build each donor's Laplacian pyramid. Verify every AC value
   against `(1-sum m)*baseline + sum(m*donor)` using the same weights for all
   four deliberately different planes. Preserve every terminal-base f32 bit.
   The interpolation bypasses normalized baseline membership rather than
   multiplying its old source weights or allowing mean fallback to restore
   excluded donors. Check a live two-donor blend and its all-late-source arm.
4. Empty/off and all-zero masks must match actual baseline finish bit for bit.
   With mask1 everywhere, all AC coefficients must equal the selected donor,
   while the base remains baseline. Independently collapse that combination
   and apply the actual input sample min/max hull. Compare the returned image,
   and require it to differ from both ordinary finish and direct donor pixels
   somewhere so base preservation is not a vacuous equality.
5. Require the focused-versus-late placebo to change actual output, not just
   metadata. Verify all final samples finite and within the per-pixel bounds
   of original source planes. A fixed large-DC/separate-detail construction
   must cause pre-hull excursions and confirm that the clamp is exercised.
   A source with the wrong geometry/nonfinite samples or missing donor
   contribution must not silently substitute another source.

Use exact bits for off/zero, base retention and source hashes. Expected mask
Gaussian/normalized mask weights must agree within1e-6 (normalization may use reciprocal multiplication
instead of division); shared-plane routing is checked coefficient by coefficient.
This is separate from the pre-existing1e-4 tolerance for analytic native
capsule geometry evaluated against global-coordinate f32 arithmetic.
For independently accumulated f32 coefficient/collapse comparisons, use
absolute tolerance0.003DN (well below one stored u16 count); report the worst
error. A broken offset, plane-specific mask, replaced base, missing clamp,
Laplacian instead of Gaussian mask, or unchanged late arm must fail one of
these checks. These are mechanical controls, not image-quality thresholds.

Gaussian mask reduction and pyramid expansion can alter reconstructed pixels
outside the original fine-mask footprint. Do not assert unchanged output there.
The full photographic test must show the transition and nearby competing
structure, as well as core, rays and flat-noise cost, against the unchanged
baseline and identical-mask late69 arm. The earlier fixed labels and masks must
remain unchanged after seeing those outcomes.

## Controls-1 failure and diagnostic amendment

The fresh first build passed geometry (maximum analytic difference2.91566e-5)
but stopped at a combined all-ones image-error/clamp-participation assertion;
neither value was printed, so the log cannot identify which condition failed.
Keep its original fixture and both limits unchanged. Before build2, split those
assertions and print their actual values, source pin, reconstructed pin and
bounded pin. Add a separate constant-donor fixture: other sources are2000DN
brighter except at the same centre sample. Its actual resolved terminal base
must be more than1000DN above that common sample; zero donor AC then necessarily
creates a pre-hull excursion. Require the clamp to return exactly the common
input value and retain the0.003DN whole-image comparison. This strengthens and
diagnoses the mechanical control; it changes no photographic acceptance rule.

Root's linked-current-core diagnostic identified the failed choice before the
next full CLI build: the test merge helper omitted `FrameWorkspace::next_frame`
between sources, retaining the first source's cached pyramid. Actual BandWorker
already resets it. Correct the helper only and preserve the original fixture,
excursions>=4 and0.003DN limits. Independently build fresh pyramids for all three
original sources, assert their terminal bases differ by more than100DN, and
require the resolved baseline base to equal their arithmetic mean bit for bit.
This regression can reject the cache omission even when a duplicated finish
calculation agrees with its own incorrect single-source coefficients. Production
code is unchanged by this correction. Root retains the failed run and diagnostic
receipts and owns both the fast linked-core run and the final fresh CLI build.

# Independent source-gradient target screen

Frozen before execution, 2026-09-25. Root runs; source_trace authors the operator
and consumer; opal_headroom chooses these independent controls. This is a tiny
target screen, with no synthesis solver, RAW read, demosaic, TIFF or photograph.
The prior consistency-reconstruction, shared-source and source-prior failures
remain closed. The proposed delta is differentiating each source coefficient
before spatial fusion, with every actual canonical source weight held fixed.

Use public BandMerge::add_frame, canonical_fields and resolved_coefficients on
five pre-gathered four-plane inputs, 160x144 quad sites. Default MergeConfig
reaches four AC levels plus the terminal. At each AC level use the normalized
weight at the forward edge's origin: g=sum_i p_i(x) D L_i. Unsupported origins
use the unweighted mean of source gradients. The comparator is D C, where C is
the actual resolved canonical coefficient. Terminal target is held exactly.
Forward differences have zero stored last-column dx and last-row dy; those
missing edges never enter a score. No alternative orientation, edge averaging,
weight smoothing, noise estimate, coefficient scaling or fallback is tested.

Truth is the gradient of the actual public Pyramid::build on known noiseless
four-phase truth planes. Raw camera-DN units, actual R/G1/G2/B coordinates and
the earlier [1.7,1,1,2.3] WB division are retained. The inherited analytic
contact rectangle and near-fine/far-coarse formulas come from
band-source-agreement/independent-controls.rs; no RAW interpolation is simulated.
The noisy arm adds independent fixed 20-DN Gaussian draws per source, CFA
channel and site, after evaluating radiance. Guide=(G1+G2)/2 and its supplied
variance is exactly200 DN²; the noiseless arm supplies zero. This is white-noise
operator commissioning, not sensor calibration or gathered-noise validation.

Four tests, forced into flat-before-detail order, write four exact receipts:

1. `a_target_identities` -> arithmetic.json. Independent finite differences at
   odd/even extents and all borders, with missing-edge masks and wrong-sign/
   dropped-interior destroyers. Equal-source actual consumer and unsupported
   flat mean target identities are checked. Spatially constant unequal
   memberships [1/8,1/4,5/8] commute with finite differentiation on actual
   pyramids, checked as a TARGET identity only. No reconstructed-image identity
   is claimed. Absolute arithmetic tolerance is0.02 DN; dyadic finite-difference
   and missing-edge examples must be exact.
2. `b_flat_target_noise` -> flat.json. Literal radiance0.25, noiseless and one
   independently seeded noisy population. Noiseless targets must be zero. For
   every CFA plane and AC level, candidate gradient RMS must be <=1.05 baseline
   plus0.02 DN; no noise reduction claim follows from this target-only check.
3. `c_contact_join_screen` -> contact.json. Preserve the inherited rectangle
   [108,116]..[140,164], its coloured sinusoidal surround and blur law. Fixed
   whole interior [38,42]..[280,244] and contact interior [112,120]..[136,160]
   require the same per-plane/per-band1.05 RMS no-harm bar. Contact-detail
   template recovery at levels0/1 must retain98% of baseline, bounded to[0,1] for that score,
   with baseline recovery>=0.5. The spill window [142,118]..[164,162] at levels0/1
   is the only proposed positive. For each plane and those levels, baseline
   target error RMS must exceed0.2 DN, the join J=D C-g must exceed5% of that
   error RMS and have positive normalized alignment >0.2 with the baseline
   truth error. Only then is a spurious join exercised. Candidate spill error
   must be <=0.95 baseline. Both noiseless and noisy populations must qualify.
   Absence of this positive is a failed/unexercised hypothesis, never a reason
   to revise the region or stimulus.
4. `d_near_far_retention` -> depth.json. Retain the inherited0.10 and0.022
   native-cycle components focused at sources0/4, all five samples, and the
   same whole interior. Every plane/band keeps the1.05 RMS no-harm bar. At each
   band jointly regress against BOTH independently generated component-gradient
   templates, including their cross term and an intercept. Fine retention is
   judged at level0 and coarse retention at level2, per plane; both baseline
   recoveries must be>=0.5, candidate bounded recovery>=98% baseline. A fixed
   wrong-depth target using source0 alone must fail the far-retention or error
   criterion. An erased target and a truth target with half the far component
   must fail the same retention check, proving the scorer is not dominated by
   the other component. Noiseless and noisy populations both remain in scope.

Per-band scoring prevents fine-band amplitude from hiding coarse losses.
RMS can reward smoothing, so live component retention and erased/wrong-depth
destroyers are separate. Join alignment can be positive for useful contrast;
it is merely eligibility, and known-truth improvement plus detail protection
remain necessary. Finite differences are independently computed by the scorer,
not borrowed from the candidate. Full source arrays are tiny test fixtures;
the consumer itself streams and never introduces a native aligned volume.

Each receipt reports mechanical_pass and explicitly sets
canonical_consumer_qualified=false, photographic_quality_admitted=false.
Flat/contact/depth report scientific_pass; their conjunction is the only
target-screen qualification. Scientific failures are saved without panic;
instrument errors still fail tests. No target benefit licenses a reconstructed
image. Failure closes this fixed target construction without region, threshold,
derivative or stimulus rescue. No synthesis work is admitted by arithmetic alone.

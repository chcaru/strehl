# Concrete coefficient-domain repeat consumer

Status: ARGUED implementation design, 2026-10-28. This responds to the actual
candidate of two 299-frame same-settings bug-3 passes and the optional primary
stack request. It deliberately does not revive the rejected spectral recipe.
It needs production-path controls and full photographs before a quality claim.

## Consumer seam

Add a separate opt-in group entry point to BandMerge (or a dedicated sibling
sharing the ordinary band-weight function), leaving add_frame_with_gain unchanged.

    pub struct BandSource<'a> {
        pub source_id: SourceId,
        pub bracket_id: BracketId,
        pub size: LevelSize,
        pub cfa: [&'a [f32]; 4],       // already built Laplacian coefficients
        pub green: &'a [f32],        // same green luma as existing selection
        pub temporal_var: &'a [f32], // absolute coefficient variance, DN^2
        pub support: &'a [bool],     // genuine gathered footprint, no padding
    }

    pub struct GroupPolicy {
        pub primary: Option<BracketId>,
        pub agreement: AgreementPolicy,
    }

    impl RepeatGroupWorkspace {
        pub fn begin(&mut self, group: GroupIdentity, policy: GroupPolicy);
        pub fn add_source_band(&mut self, level: usize, source: BandSource);
        pub fn finish_into(&mut self, merge: &mut GroupBandMerge);
    }

Names are illustrative, not API requirements. A root-facing preparation helper
should build the source luma and four color bands once, then feed borrowed bands.
Do not collapse a grouped image and redecompose it. Separate per-source hull
updates use actual source level-0 values, not reconstructed grouped pixels.
No aligned-frame volume is retained.

Each group workspace keeps all levels of bounded sufficient statistics:

- coefficient sums (four CFA colors sharing weights);
- green mean, weight sum and sum(weight^2 * source variance);
- compatibility statistics and supported independent-source count;
- ordinary per-source merge numerator, denominator and fallback sums/count;
- the eligible primary contribution when requested;
- source provenance/acceptance diagnostic summaries.

Memory scales with output area and worker count, not total source count or K.
Source preparation and an accumulator live together; each decoded source is
dropped before the next. An initial implementation can cap active group workers
and report the added buffer cost explicitly.

## Exact role of per-band variance

For the first same-settings repeat implementation, equal weights are a good
deliberate choice. They avoid noisy inverse-variance weighting and use the real
candidate's equal exposure/ISO. With n independent supported observations:

    C_group = sum(C_i) / n
    V_group = sum(V_i) / (n*n)

All four color coefficients use the same membership/weights. The new path
computes green band energy as the ordinary smooth5(L_group^2), and the expected
noise energy as smooth5(V_group). The floor is gate times that absolute energy.
There is no synthetic effective PlaneNoise and no second beta multiplication.

A source's first implementation can set:

    V_i[k] = beta_i[k] * Gaussian(source_luma_variance)[k]

where beta_i is its existing actual-warp probe, falling back by the existing
per-band contract. This retains the current source model's spatial approximation;
it is not a claim of exact heterogeneous covariance. Validate its phase extremes
and use an explicit propagated-field path if that approximation fails.

At a fixed coefficient, sum(alpha_i^2 * V_i) follows from independent exposure
noise even though each source's neighboring coefficients are correlated.
Smoothing squared energy only requires the pointwise second moment for its mean.
The spatial covariance still affects gate tails and therefore must be covered
by actual-path flat-noise tests. Scene-derived membership conditions the noise;
the formula is a frozen-membership prediction, not automatically calibrated
conditional confidence.

HDR/unequal ISO is a separate extension. Normalize signal by c and source
variance by c^2; use fixed exposure-informed weights or a robust shared signal
guide for inverse-variance weights. Do not estimate each weight from the exact
noisy coefficient it multiplies. Keep mixed aperture and lighting outside repeat
mean eligibility until their own experiment passes.

## Compatibility, fallback and optional primary

Start with a conservative local agreement policy and no claim of universal
thresholds. Compare supported coefficient differences to the sum of injected
variances, aggregated over a fixed spatial neighborhood. Use the same membership
across CFA colors, with a color/low-frequency disagreement veto so equal green
cannot silently mix different lighting. Require the separately checked pairing
and geometric residual first. A coefficient gate cannot identify every
misregistration, texture alias or focus mismatch by itself.

A streaming weighted residual (Welford form) is a compatibility statistic, not a
new estimate of sensor noise. Never replace the injected variance with measured
scatter to make disagreeing samples pass. Two-pass equal-weight means can compare
one member to the other; K>2 should not privilege whichever arrives first.
Dilation of a disagreement veto must include the source/variance footprint.

The optional primary controls appearance/fallback, not whether every supporting
sample is forced into the result:

| State at a coefficient | Contribution |
| --- | --- |
| Group agrees; primary present or absent | Noise average as one focus observation. |
| Group disagrees; eligible primary member covers it | Original primary contribution and original variance; no claimed repeat gain. |
| Group disagrees; no preferred primary | Original ordinary source contributions; no hidden preference for the geometry anchor. |
| Primary missing/outside support; supporting group agrees | Supporting mean, with support provenance and coverage. |
| Primary missing/outside support; supporting samples disagree | Ordinary symmetric support contributions and unresolved diagnostic. |
| No valid covering source | No contribution; explicit coverage failure, never padded zeros. |

For the no-primary disagreement case, retain ordinary source contributions
while sources stream. The group finish step chooses these sufficient statistics
instead of the grouped contribution. This reproduces ordinary local election
semantics without saving source pyramids. The new path needs per-level per-pixel
fallback denominators: an accepted group is one observation, whereas a rejected
group may contribute several original observations. A global scalar frame count
cannot describe that mixture. Coverage is another reason for the same field.

Use binary, conservative agreement initially. Fractionally mixing grouped and
ordinary contributions reuses the same noise realizations twice; an effective
sample-count calculation must then account for that dependence.

Where a designated primary has no paired frame at that focus, do not fabricate
one by interpolating focus. It is absent. Keep geometric anchor selection and
primary preference distinct in persisted provenance and UI.

## Minimal producing-path tests

1. **Legacy/off:** existing single bracket and one-member session route execute
   the old consumer with exact output identity at fixed chunks/workers. A planted
   source change proves the byte check responds.
2. **Independent flat, first:** same mean and known injected noise through actual
   prepared bands, over deterministic independent seeds. Equal K=2 mean variance
   approaches 1/2 with uncertainty reported. Assert mean bias, including near
   black and highlights, before a sharpness number.
3. **Duplicate source:** two paths to the identical RAW cannot count as independent
   or claim noise gain. The identity/dedup branch reaches the same producing path.
4. **Warp-phase:** identity, integer and half/subpixel phases on a known textured
   and flat source. Compare modeled per-band second moments to fresh independent
   noise pushed through the actual source/warp/pyramid path. Deliberately reuse
   identity beta on the half-phase foil; it must be detected.
5. **Agreement positive and motion/focus negative:** identical sharp latent with
   independent noise averages; known 0.5-native-pixel error, half-step defocus,
   moving edge and color-only lighting change decline. With primary, exact source
   fallback where rejected; without primary, ordinary source contributions.
6. **No preferred source symmetry:** reverse bracket order and choose a different
   automatic geometric reference, re-expressing the same geometry. Statistics and
   output agree within the declared f32 reduction tolerance. Explicit primary
   selection is the only semantic asymmetry.
7. **Coverage:** primary is absent at some focus nodes and outside a support
   strip. Other valid samples fill supported areas; all-missing remains invalid.
   Poison synthetic padding with extreme values to prove it never enters fusion.
8. **Real photographs:** both full bug passes separately, ordinary pooled joint
   merge, grouped candidate with/without explicit primary; same development and
   complete source accounting. Review complete photographs, then fixed native
   hair/edge/specular/background witnesses independently.
9. **Exposure extension:** flat target at the real 1/2.5/6-second levels only after
   metadata and spatial lighting consistency pass. Use unclipped overlaps and
   an intentionally wrong exposure factor. Do not assume all three bracket
   frame indices or fine focus states match.

For accepted groups, expose actual independent contributor count and local
effective count, and distinguish rejection from absence. Do not label these
counts measured resolution or promise sqrt(K) across a completed photograph.
Report noise reduction where it was measured and local visual changes separately.

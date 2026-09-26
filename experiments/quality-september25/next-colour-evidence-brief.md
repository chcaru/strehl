# One next candidate: colour-difference source evidence

2026-09-25. **ARGUED, unimplemented.** Best distinct bounded candidate after
the current source-agreement trial: select coarse AC sources using colour
differences that reject an illuminant-coloured veil, then apply the **same
weights to all four unchanged CFA coefficients**. Do not remove a specular
component from the delivered radiance or estimate a new clean image.

**Prior-art delta.** Mechanical `prior_art.py` searches ran for `dichromatic
specular colour channel chromatic`, `chromatic opponent diffuse specular`, and
`nonlocal depth coherence source selection`; read the current proposal,
SYNTHESIS architecture, BUILD-CHROMA, M107, M-PHASE0-LCA, BUILD-HIGHLIGHT,
V-GREEN and the recent real-source trace closure. R/B own-guide and guarded
residual changed channels independently and failed photographic transfer;
green-match projected source tuples onto the existing green result. Shared-source
field and cross-scale prior borrowed green/finest ownership. This candidate
instead changes the shared within-band evidence. No prior inspected experiment
tests this exact intervention. The failed marigold profiles do not justify it.

**Physical hypothesis, not attribution.** A dielectric dichromatic model writes
colour as body colour plus illuminant-coloured reflection; projection
orthogonal to that illumination can suppress the latter in an evidence signal.
[Primary model](https://publications.ri.cmu.edu/using-a-color-reflection-model-to-separate-highlights-from-object-color),
[orthogonal projection formulation](https://arxiv.org/abs/1512.00237).
Manual WB supplies a proposed direction, not proof: minerals can be coloured,
metallic, translucent or iridescent, and optical colour errors can survive the
projection. This is not a claim that mineral glare is removable or achromatic.

**Smallest existing consumer seam.** Reuse
`rb-own-guide/core-bridge.rs::{fields_from_energy,add_fields}` and the full
adapter's canonical chunks/pinned writer. On co-sited camera-RGB samples from
the existing phase-packed gather, form WB-scaled differences `R-G` and `B-G`.
Do not subtract different CFA-site samples as if they were co-located. Build
their existing Laplacian bands; sum the two smoothed squared energies. Project
the existing original-source noise draws through exactly the same gather and
differences before squaring, retaining shared-green/MHC covariance. Use the
existing gate/exponent formula. At coarse AC sites with no admitted chromatic
source, retain canonical weights exactly; otherwise use the chromatic weights
for every CFA plane. Hold finest, terminal mean, bounds, geometry and tone.
One rule, no strength sweep; retain only one consumed source at a time.

**Minimal falsifiers before one photograph.** Reuse existing actual-consumer
fixtures and require: (1) a coloured textured surface behind a defocused
neutral bright feature improves RGB truth while retaining the true focused
highlight; assert the baseline actually has positive spill; (2) flat noise
first, neutral edges/white hairs, true coloured glints, warm-WB weak colour and
fine-near/coarse-far competing detail stay within inherited guards, scored
after final MHC; (3) a neutral veil added to a known coloured scene leaves the
projected evidence unchanged within independently bounded rounding error;
(4) Off/no-chroma fallback identity, fractional CFA phases and detail/colour
destroyers work. Failure closes this rule, without threshold rescue.

**One complete-image decision.** If those controls pass, compare complete
216-source ore102 against `outputs/quality-september25/ore-102`, with baseline
RGB16/ICC exact and its resolved tone pinned. Freeze the existing white-patch,
blue-grain and reflection targets plus whole-frame review. Require identifiable
surface separation/gradation with retained bright facets and blue grains;
darker whites, weaker chroma or smoother grain alone fail. This tests the
photographic hypothesis; it is not already supported by a real source witness.

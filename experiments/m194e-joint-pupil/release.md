# M194e prospective implementation release

Root, 2026-09-07, before any M194e implementation or generated data. M194d is
complete at `7c1cfdbd10e1c1db0186b5054c23deabae2a63fd`. The charter, both author
documents, independent mathematical design and consumer-scope audit were read
and reconciled. Implementation is authorized after the commit containing this
release, within the allocated experiment directory only.

Bound final designs:

| Document | SHA-256 |
| --- | --- |
| implementation-plan.md | dbac8c9ce4ff2d555bd49291de325e3f3494459b23b9cd83ec4ff180cf93f1a0 |
| implementation-preregister.md | 2196166ee9a36af8cc73e272e97d430d4478b2b8e05fc3af2215afc64de0e500 |
| independent-design.md | 5d98f9e949b77da629cc32e1cc3f35d2bcf9cb0b7fbdad28d58476e35509bf87 |

The author implements the polar/radial integral and numerical cell integration;
the independent reviewer implements Cartesian pupil chords, analytic clipped-cell
Fourier/moment integrals, and small direct cross-checks. Both share the declared
mathematical model, not their integration code. The independent analytic-cell
method has no numerical cell-resolution arm: its cell evidence is analytic
oracles and direct cross-checks; its remaining numerical integral is refined.
The author still reports separate pupil and cell refinement.

The fixed five64×48 frames, all pixels and edge band, retain max0.004 electrons
and RMS0.0008 electrons discrepancy budgets. Independent self-refinement must
be within0.0005 electrons. These are numerical engineering requirements on
float64 reference-generation arithmetic, not physical or production-output error
bounds. No passing subset, changed scene or loosened accuracy line is authorized.

**DERIVED resource audit, not a timing result:** root identified that the first
200m angular-node ceiling was smaller than a nominal cell-refinement count.
Before implementation it became600m, with full-visible/hidden points omitting
irrelevant angular splits. The independent resource audit includes actual cell
clipping: at most288 cut cells from the three parallel lines, at most4 triangles
per cut cell and2 otherwise, giving at most2,150,400 nominal refined point calls
and412,876,800 angular nodes under the conservative four-interval point rule.
This fits4m/600m before adaptation; angular refinement gives206,438,400 nodes.
Coincident lines and zero-area pieces must be deduplicated. This arithmetic
does not prove that adaptive refinement or the registered CPU/wall limits pass.
The own-process stop budgets remain live failure conditions.

Pupil error indicators are propagated with nonnegative native-area quadrature
weights, rather than counted once per point without weighting. Indicator
agreement is not proof of accuracy; independent arrays and powered analytic
controls are still required. Storage claims are confined to explicitly tracked
ndarray allocations/lifetimes, not total process RSS.

The float/model commission precedes CFA generation. A separate independent
conversion check follows actual CFA emission; no receipt needs to certify files
before they exist. Exact new child schemas and sources are bound in the designs.
The old M194b/M194d schema and product sources stay frozen. There is no product
bridge, new noisy quality matrix, parameter tuning, capture or SOTA/default
promotion in this release. Author and reviewer may execute their scoped controls
and bounded runs autonomously, retaining every initial failure and source state.

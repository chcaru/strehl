# Directional route: native test not found

**READ-ONLY FINDING:** no port or known-truth test of complex directional
wavelet fusion in the current native RAW consumer was located. Searches used
`prior_art.py complex wavelet directional consistency`, followed by targeted
SYNTHESIS, report, experiment and Rust-source searches. No build, RAW decode or
new experiment was run. This is a search result, not proof of absence.

The apparent precedents do not close it: M189b tests an anisotropic-sharpening
metric failure; M-PHASE0-XSPEC tests Fourier phase through focus; M79/G are
literature surveys; M162 explicitly has no fork-to-Strehl change set. Historical
fork results and the current external photograph change the whole pipeline.
Neither supplies this native, known-truth intervention. Phase-packed RGB and
green-match also preserve the original scalar Laplacian source evidence.

**VERIFIED source distinction:** the pinned MIT comparator uses a separable
six-tap complex Daubechies transform with H/V/D detail bands. It selects by
squared complex magnitude, retains the chosen coefficient's phase, then repairs
two-of-three directional donor disagreement. It has **no inter-frame phase
coherence acceptance test**. This is not automatically a six-orientation
dual-tree implementation. The exact batch-composite and neighbour behaviour is
recorded in `../fine-support-guidance/external-consistency-review.md`; copying
its hard selector would reintroduce the project's known noise-selection failure.

**One bounded next algorithm test, ARGUED and untested:** replace only the native
finest-band guide with directional soft consensus. Adapt that MIT forward
one-level transform to the actual gathered green guide. For each H/V/D band,
form its squared complex amplitude and the existing local energy smoothing;
propagate the same injected synthetic probe through this new operator to obtain
its directional floor. Apply the existing noise-aware weight function to each
direction, take the median of the three weights, and expand that half-size field
to band0 with the existing positive pyramid expansion. Use it as the shared
band0 source weight. Preserve all colour coefficients, bands1+, base and fallback. This is
two-direction support without a hard donor or a broad spatial pool; it is not a
claim to reproduce the comparator or to test phase coherence.

Reuse the existing `BandMerge` finest-weight seam and
`phase_packed_rgb::compare_generated`/fine-support generated adapter. Run only
the already available flat, compact-glint/depth-step and genuine coloured-ray
fixtures first. The transform's decimation phase and periodic boundary need
explicit interior support and shifted/impulse controls. No full image or new
simulator is needed for this decision.

**Strongest expected failure:** a genuine oriented edge can excite only one
direction and be suppressed by consensus. Its known-truth recovery is a binding
negative control. Conversely, a defocused fan that wins all three directions
survives unchanged; fixed source69 fan versus compact-source coefficients from
the existing six-point native diagnostic can expose that cheaply. If either
failure occurs, close this fixed rule without tuning. Complex arithmetic alone
is not evidence that physical glint fans become distinguishable.

## Decision: median rule closed before implementation

**DERIVED analytic falsifier, accepted 2026-09-19:** an ideal horizontal or
vertical grating can have nonzero detail in only one of H/V/D. The other two
directions then have zero excess weights, so their unconditional median is zero
and removes valid focused detail by construction. This is the oriented-detail
negative control above, already sufficient to reject the rule. Do not implement
or tune this proposed median gate. The finding that no native complex-wavelet
fusion test was located remains; actual complex-coefficient fusion is a separate
route and is not closed by this falsifier.

## Root decision before implementation

**DERIVED rejection of this median rule:** for an ideal horizontal or vertical
grating, two separable high-pass directions see constant input and have zero
signal. Taking the median of their zero excess weights and the one active
direction's positive weight returns zero. This is a constructed failure of the
proposed rule, not an uncertain empirical risk that warrants another render.
Do not implement or sweep the unconditional median consensus above.

The prior-work finding still stands. Root instead allocated a bounded actual
complex-coefficient fusion test with independent weights for H/V/D, preserving
single-direction signal. Its initial scope is identity geometry and one level,
with a matched one-level actual baseline and exact propagation of the supplied
independent identity-guide variance. No fractional or full RAW quality claim
follows. See `../complex-wavelet-merge/charter.md`.

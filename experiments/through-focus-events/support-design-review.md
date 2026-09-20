# Bounded decision on temporal-affinity support

**Do not implement an automatic compact-donor selector from this evidence yet.**
The dark association is a useful observed separation from this particular ridge,
but supplies neither an automatic compact seed nor a source ordering. Reading
the actual signed traces matters: core, column and fan all brighten strongly
toward the late sources; the competing ridge is nearly constant. Their signed
finest-Laplacian traces do not exhibit the same association. Joint DN cosine can
therefore find a shared late brightness evolution without finding the source
that removes that evolution. The facet relation also cancels across channels.

This does not repeat the old closures. Radius32 energy/floor pooling moved the
real nearby ridge toward the visibly softer source35, then the fixed generated
candidate destroyed its glint core. The shared-source-field Potts rule retained
roughly true core amplitude but raised RGB error and did not remove its fan.
Neither experiment tested whole-stack DN-affinity-gated pooling. However,
restricting a pool by affinity addresses **who may share evidence**, not **which
of their shared sources is focused**. Electing the largest local energy still
has the measured late-ray problem; electing smallest brightness or sharpest
temporal peak would introduce an unsupported focus rule. M27/M63 rule out the
tempting peak/width interpretation.

The cheapest distinct falsifier, if root chooses one despite this limitation,
is a small generated *threshold-free affinity-pool* counterfactual: every fixed
8x8-quad block is its own anchor; within the already used32-quad neighbourhood,
set self-weight1 and neighbour weight `max(0, signed-four-DN-change cosine)^2`.
Pool each source's existing finest energy and injected floor with those fixed
spatial weights, then retain the existing SoftPower source weighting, other
bands, mean base and hull. There is no compact seed election or hard donor:
the source distribution is automatic but must actually recover compact truth
to count as useful. The zero cutoff means orthogonal/anticorrelated, not a
threshold fitted between this photograph's0.12 and0.65. It is a support test,
not an ownership algorithm or a recommendation for a full render.

First decisive plant: two independently focused nearby surfaces, one containing
a compact core and physical expanding fan, the other a genuine thin ridge.
Give the two surfaces the same smooth late four-channel brightening while
keeping their focused-source indices different. Pair it with the identical
scene without that nuisance, a genuine coloured radial feature, and a flat/noise
null. A signed intensity descriptor can become arbitrarily alike as common
brightening dominates while correct donors remain different. Reject on lost
ridge/core truth or absent fan improvement; high affinity or prettier index
fields cannot pass. This is stronger than merely permuting a focus curve.

For a bounded small plant, keep the exact69x4 differences per block first.
Whole-image block state would be about125,137 blocks: exact70x4 f32 means use
140MB, two source energy/floor fields across70 use70MB, and fixed81-neighbour
weights about41MB. These are scalar analysis fields, not aligned CFA frames;
actual reconstruction needs a second streaming source pass. Compression could
reduce this, but truncating temporal descriptors before this falsifier creates
another unmeasured choice. No compute or quality benefit has been measured.

Recommendation now: save this narrowly specified falsifier; do not manufacture
an automatic compact-donor claim from the dark cosine separation or tune a
cosine threshold on it. The actual clipped-core setting further prevents a
Gaussian/flux-conservation interpretation. The independent photograph/source
witness should supply the missing source-direction evidence before another
whole-image source-selection program is opened.

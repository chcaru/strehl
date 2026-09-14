# Current quality work — 2026-09-14

The priority is visible quality on the owner's new stabilized RAW stacks.
No SOTA claim or new default quality promotion has been established in this work.

Three complete new stacks have been rendered: printer105, tiny checker150 and
chip299. Matched original/gathered/merged patches now use the same actual product
colour development. The observer's on/off/placebo outputs are byte-identical.

The quadratic alignment option improves independent synthetic placement tests
but shows no clear photographic improvement on the new printer. Several local
demosaic alternatives improve the chip's rail appearance while damaging known
coloured detail; those branches are closed. This completed work is committed at
`3a8eafa0e8a59d1819b851095290a10ee1d69dc9` (the preceding quadratic implementation
is `cbe7ed2a601c3a141757ea93b9c48a11fab04fa4`).

**Useful photographic result: local geometry correction before averaging.**
On the chip's fixed pale-circuit crop, the same eight RAW frames give more
distinct ladder segments and cleaner, tighter rail edges after a locally fitted
translation correction. Root and an independent reviewer agree. This is a
local comparison of eight-frame means, not a full 299-frame product improvement
or proof of newly resolved detail. The source MHC remains crisper in places.

The green-only fit uses disjoint training and validation areas. Its validation
error falls in every neighbouring frame; synthetic same-focus, unequal-blur,
blur-only and wrong-sign controls pass. One frame reaches the search bound and
is excluded from both image arms. Only geometry changes; fitted nuisance
brightness terms are not applied to the RAW values.

**Closed: the current joint inverse reconstruction family.** Nine saved RAW
patches have independently verified decoding and coordinate conventions. The
native 1x Lanczos inverse improves all twelve fixed signal tests against
single-frame MHC, but amplifies colour noise. On the actual photograph it adds
periodic colour stipple. Correcting local geometry improves its rail placement
but does not remove the stipple. A clipping-admission placebo does not cure it.
Four prescribed residual updates from the cleaner local mean also add colour
speckle without an identifiable new feature. No further kernel, iteration,
regularization or demosaic sweep is commissioned for this crop.

Under the locally corrected map, the estimated horizontal sampling geometry
for red and blue is more poorly conditioned than under the original map.
Green remains much better conditioned. These are matrices of estimated
positions, not independent measurements of true sampling diversity or proof
of its contribution to the reconstruction failure.

**Next decision: carry the local placement improvement into the actual merge
consumer, with spatially restricted scope.** A crop-local fit must not become
an unrestricted whole-image warp. Product integration and performance remain
unproved; no new default is promoted. Preserve RAW u16 storage, injected camera
noise, original saturation provenance and consumption-time sampling.

Detailed evidence: results.md, final-eight-frame-photographic-verdict.md,
local-green-translation-review.md, joint-backprojection-verdict.md,
mhc-catmull-sampler-controls-1.json and chip-corrected-sample-diversity-1.json.
All recent numerical/image work reuses small saved patches. Original captures
remain read only.

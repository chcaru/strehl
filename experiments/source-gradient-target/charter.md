# Source-gradient targets: necessary screen before a reconstruction

Root scope, September25. Test whether differentiating each source coefficient
before weighted combination supplies a more faithful target than differentiating
the already combined coefficient. The exact finite forward-difference identity
adds a source-membership derivative to the latter. That term can represent a
spurious join or legitimate scene contrast; removing it is not automatically
correct. The prior consistent-reconstruction trial held coefficient targets
unchanged and does not answer this target choice. The prior-art and limitations
are recorded in quality-september25/next-reconstruction.md.

Use the actual public core BandMerge and its existing feature-gated field and
resolved-coefficient accessors on tiny supplied CFA-plane fixtures. Hold all
canonical weights, noise inputs, pyramid filters and fallback rules. Accumulate
sum(w D L)/sum(w) per AC level, direction and channel, with the canonical mean
fallback where no weight is admitted. Compare against D of the actual resolved
canonical coefficient. Fixed finite forward differences have no wraparound.
Image arithmetic and sufficient statistics are f32; avoid an N-image volume.
Original RAW gathering, placement, CA, MHC and final development are explicitly
outside this small screen.

The independent reviewer freezes flat-first, known bright contact, two-depth
fine/coarse, genuine-colour and destroyer checks before execution. Compare to
the actual pyramid analysis of independently known truth. A smaller target
error must not conceal erased fine or far-depth structure. No whole-image,
SOTA or speed claim can follow. An unexercised benefit or harmful target closes
the fixed construction without derivative, threshold or source-subset sweeps.

No inverse solver is commissioned here. Spatially constant memberships imply
target equality g=D C, not equality of a hypothetical reconstructed image to
canonical collapse. The old A-transpose-A solver and its certificate do not
apply to a new gradient objective. Equal realizable source images are a valid
identity fixture; inconsistent coefficient targets are not.

source_trace owns operator/consumer; opal_headroom owns independent fixtures,
preregistration and decisions; root owns the small standalone build and runs.
This proceeds alongside the different fixed-front radiance-intercept screen.
No core/CLI hooks, production default change, full adapter or SYNTHESIS fold.

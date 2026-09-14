# Quality path after the September 14 RAW experiments

This is the current quality implementation queue, replacing the immediate
quality actions in 2026-09-sota-program.md and the older SOTA proposal. Read
the measured decision record in docs/research/SYNTHESIS.md before architectural
changes; this plan does not promote any experimental default.

The owner's priority is photographic quality on the A7C II macro captures.
The existing program has not established SOTA quality. Further speed-only work
is deferred; retain the already measured experimental GPU improvements.

The new capture regime is electronic shutter, IBIS off, a delayed tripod start,
manual white balance and polarized KL 1500 LCD lighting. The optical path is
the Sony 100mm Macro GM, Viltrox 2x teleconverter and X4 CPL. Use these captures
as the current development population, recording which originals each test
actually consumes. Camera metadata, sensor noise, clipping and colour headroom
remain part of the RAW model. Do not infer unmeasured optics from the gear name.

## What changes the direction

Committed evidence at `a0febf209ce9f38649e40fc39a6f7cf3abf4a243`, particularly
experiments/quality-september14/results.md, supports a narrower route than more
single-frame interpolation variants. Several alternatives clean up the chip's
rail appearance while destroying genuine coloured detail in independent tests.
A direct multi-frame CFA inverse preserves those test signals but adds colour
noise and periodic artifacts to the actual photograph. Even four prescribed
updates from a cleaner mean do not give a clear photographic benefit. Close
these tested variants for this crop; do not use more parameter sweeps to rescue them.

The useful intervention is local placement. With the same eight observations,
a translation fitted on one part of a green-only patch and checked on another
improves rail continuity and ladder separation in the mean. Blur-only and
wrong-sign controls can reject the fit. This does not yet show an improvement
in the complete product, new resolved detail, or validity on an entire frame.

## Immediate implementation question

Carry the correction through the actual gather, injected variance, band merge
and developer before building a general refinement system. The first adapter
reuses saved original CFA data and an explicitly cropped domain. Its available
context supports four Laplacian levels, so it cannot reproduce the seven-band
whole-image result. Require complete source support and exact invariance to
unsupported-buffer filler. Both image arms keep current lens colour correction,
the same frame membership and the same reference. See
experiments/quality-september14/local-placement-consumer-decision.md for the
pre-execution scope and stopping conditions.

That diagnostic is now positive: both reviewers see clearer ladder separation
and crossings through the actual consumer, with no obvious lost structure in
the selected native view. Complete source-support checks and black/white
unsupported-buffer invariance pass. The four-level/eight-frame limitation
remains. This justifies the next full-context placement test; it does not
justify a default change. Exact commands, costs and output hashes are in
experiments/quality-september14/results.md, final section.

If that diagnostic is useful, the next acceptance result must use full context
and the real merge on at least one other scene. A local fit may guide a spatial
correction only where supported; it must not overwrite a whole-image sidecar.
The runtime correction needs an unchanged-map fallback in ambiguous or
defocused regions. It must demonstrate that it does not convert blur or an
occlusion into motion. These are implementation requirements to test, not
claims that a suitable general algorithm has already shipped.

## What counts as progress

An image-quality change must retain or restore an identifiable feature in
matched native views, preserve genuine colour, and survive independent review.
Use known-scene truth and flat-noise controls alongside photographs. A lower
registration residual, stronger gradient or better synthetic score alone does
not justify promotion. A local crop improvement cannot establish a full-stack
or competitive SOTA result.

Keep subagent work bounded: one implementation, one independent choice review,
and photographic review when there is a new image. Reuse retained samples and
fixed settings. Each negative result closes its proposed intervention; it is
not a reason for another open-ended sweep. Once a product-level photographic
gain is established, measure its full-workflow cost and compare complete
outputs with the retained external baselines. Quality decides which changes
deserve optimization.

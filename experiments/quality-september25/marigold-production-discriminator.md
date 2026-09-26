# Bounded marigold production audit

READ / ARGUED, 2026-09-25. **No distinct supported defect found; stop this audit without a new experiment.** No build, RAW read, render or implementation change was made. The prior production audit already covers source inclusion, crop addressing, accumulator units and final development; those are not new leads.

The additional concrete hazard examined was stale source-plane pyramids: fresh focus weights accidentally applied to the previous frame’s cached coefficients could manufacture duplicated structure despite correct sources and geometry. The actual caller prevents this: `merge_cmd.rs::BandWorker::fold` invalidates the probe, loads the current planes, computes the current luma/variance, then calls `self.fws.next_frame()` before adding the frame. `pyramid.rs::FrameWorkspace::next_frame` (2819) clears `PlaneCache::valid`; `PlaneCache::ensure` rebuilds every source-plane pyramid. Chunk reset/absorb also has existing fresh-versus-recycled controls. No inconsistent production call site was found.

The cheap falsifier would be complementary source-coded frames through fresh versus reused workspaces, with an omitted-invalidation destroyer. Without a caller discrepancy, running it again would add coverage rather than explain the photograph. No new test is recommended.

The current quality proposal and source-pure, actual-contribution, local-placement, R/B-guidance and CA-before-MHC closures were checked by content. Pure sources retain different real hair groups while haze remains; unstable five-point profiles cannot attribute a lost hair; local placement failed held prediction. None establishes this cache hazard or another default inconsistency as the cause. The CA selector also explicitly matches the documented composed FE100GM+2× rig, so an unrelated-lens default is not a new lead.

Mechanical search run: `prior_art.py marigold chromatic alignment validity boundary source inclusion`; relevant returns include sampler-boundary-correction, M86/M103, BUILD-CHROMA and M194e. This narrow none-found result is not a correctness claim, a capture-limit claim, or justification for another blind fusion variant.

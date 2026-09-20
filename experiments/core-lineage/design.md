# Fixed original-RAW core lineage prototype

2026-09-19. Generated-only,3–16 original-u16 sources, each at most512native
pixels per axis; supplied fixed similarities, no CA. Author does not run.
Independent controls judge actual full-AC output, not topology appearance.
No source index, hand capsule, radius ranking or fitted blur model enters.

## Frozen arithmetic and geometry

For each active-local CFA plane, `C=I−G5(I)`, with separable binomial
`[1,4,6,4,1]/16`. Original-sample variance is injected through
`sum((delta−G5)^2 * V)` on the actual25 source samples, including the centre
cross-term. The field is `max(0,C_R/sigma_R,C_G1/sigma_G1,C_G2/sigma_G2,C_B/sigma_B)`.
Per-plane WB would cancel in this ratio. This is a nomination field, not a
calibrated maximum-of-four confidence. It is computed before any gather, so no
independence of interpolated samples is assumed and no new noise model is fit.

Build an8-connected descending component tree above5, batching equal values.
A leaf retains cells before its first merge; its peak and merge saddle define
the core at their midpoint. A branch needs peak>=8 and prominence>=3. Any
original code>=the frame's white level in any of the branch cells'5×5quad
four-plane contrast supports refuses it. Original analysis-edge contact also
refuses. These rules intentionally may refuse the real clipped glints.

Map labels only: active-local source quad centre is `(x+.25,y+.25)` in the
quad-coordinate map gauge. Apply the exact inverse similarity about
`(full_width/2,full_height/2)`, subtract output crop, and floor to a containing
reference quad cell. Odd decoded active offsets affect active-row addressing,
not map coordinates. Distinct source-branch aliases refuse; no image intensity
or covariance is interpolated for this analysis.

## Frozen lineage and consumer

Connect adjacent-frame branches only by mutual unique footprint overlap.
A split/merge invalidates connected tracks; ambiguous descendants stay invalid.
A missing correspondence ends a track. Require3 consecutive source nodes and
an intersection of mapped cores with at least2 cells, with both checkerboard
subsets represented. A one-cell persistent hot point therefore refuses.

At each actual baseline fold, reuse the retained finest energy/floor and the
production SoftPower function with the actual reached band count. Retain only
scalar weights at mapped core cells. Each core subset independently supplies
a per-source mean; their source sets above90% of their own maxima must overlap.
The whole-core source profile must vary by at least25% of its maximum over its
observed nodes. These are fixed heuristics, not calibrated focus probabilities.
The two subsets gate agreement, then their means are count-weighted in f32:
`(n0/n)*mean0 + (n1/n)*mean1`. Normalize this whole-core vector over sources.

Transport this shared four-plane vector only over the union of observed
branch footprints. Overlap with any other track, including a refused track,
is unknown. Use a3×3 occupancy fraction as an inward taper; outside the
retained support activation is exactly zero. No support expansion or fallback
to a nearest marker is permitted.

Use the existing `shared_source_field_diagnostic::Replay`: full-domain donor
AC, held baseline terminal mean, fixed `Bpre + sum(q*AC) − alpha*BAC` consumer
ordering as implemented there, original input hull, and bit-exact baseline at
zero activation. The actual implementation's parenthesization is authoritative:
`Bpre + (sum(q*AC) − alpha*BAC)`. All4planes share memberships. Original source
and actual gathered-plane hashes bind both passes. Off and forced-source modes
exist only for independent controls. No production defaults or old files change.

Retained state is one source analysis field/tree, previous branch footprints,
union/core/eligibility records and sparse per-core scalar evidence, followed by
the bounded generated scalar membership volume. No N aligned image/pyramid
volume is retained. Full-image cost/coverage and native CA are not admitted.
Any clipping, topology or detail failure remains a failure without a radius,
threshold, source-index, correspondence or parameter-family sweep.

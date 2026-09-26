# One common-guide pyramid falsifier

Prospective, September26. Generated-only; no photographic qualification or
default change. Root builds/runs; independent controls own quality decisions.
Original storage is u16 CFA, arithmetic f32, and each consumed source is released
before the next. No aligned-source volume, fitted optics or learned component.

The question is whether changing the spatial analysis/synthesis basis can reduce
cross-boundary mixing while holding the current Gaussian source decisions.
The canonical guide can contain false boundaries. A benefit on an oracle guide
does not admit the actual-guide arm. Current inverse, gradient-target, wavelet,
phase-packed and learned-guide failures remain failures.

## Fixed arithmetic and units

Use current `level_sizes`, including finite odd extents. At each restriction
site (2x,2y), multiply the existing 5x5 binomial product taps by
`c(a,b)=1/(1+(a-b)^2/(v(a)+v(b)))`, then normalize the row. Borders replicate.
The common coarse guide is restricted by that row. Expansion uses the existing
even [1,6,1]/8 or odd [1,1]/2 product support, multiplied by the same conductance
between its fine guide value and each coarse guide value, then normalized.
All sources and all four CFA channels share these immutable spatial rows.

Here `v(g)=0.25*(sqrt(V_G1(g))+sqrt(V_G2(g)))^2`; both V functions are the injected
`PlaneNoise::variance` on black-subtracted DN, clamping negative signal as that
API specifies. This is a conservative single-source mean-green envelope proxy,
**not a bound on the merged guide's variance**, edge probability, coefficient
variance or optimal scale. It is a fixed Cauchy-conductance heuristic. No
per-stage noise estimation and no octave variance reduction are introduced.

For each source form Gaussian levels with R, then
`L_k=G_k-E_k(G_{k+1})`; synthesize by the matching E and addition. Constant-guide
R/E equal the old Gaussian operators algebraically, with separately controlled
f32 ordering differences. Matching analysis/synthesis, common-source inputs,
and spatially constant shared memberships must reconstruct within independently
declared f32 bounds; no universal bit-exact cancellation claim is made.

Weights are copied unchanged from actual old Gaussian `BandWorker` fields.
Its injected variance/probed beta/floor calibrate **only that old decision path**.
No old floor is applied to new coefficients, and this empirical transfer does
not claim calibrated new-basis focus selection. Accumulate `w*(L/65536)` and w
in original order; divide and restore DN once. Zero total weight uses the mean
of the new coefficients. The terminal is the mean of the new terminal levels,
not the historical Gaussian base. Use the unchanged actual input hull and MHC.

## Actual consumer and fixed nuisance arms

Pass1 uses the actual rounded native gather, injected noise and canonical fold.
Save compact per-source hashes only, and accumulate temporal mean G. The actual
guide is (canonical G1+G2)/2 in black-subtracted DN. Pass2 recomputes each source
and all old fields, requiring source/gather/variance/beta/weight hash identity,
and streams the same four planes through each fixed transform/accumulator.
Canonical pass1/pass2 final CFA and MHC must be bit-identical. The baseline with
diagnostics disabled must remain identical too.

Arms: common-canonical, constant (canonical guide's scalar spatial mean),
displaced (guide[y-5,x+7], clamped), temporal-mean (independent nuisance), and
optional true (reviewer supplied sharp guide, diagnostic only). None selects
another arm based on its output. Flat noise runs first; then bright contact,
near-fine/far-coarse, genuine bright detail and weak colour protections. The
reviewer controls guide corruption, masks, failure bars and source order.

Pure API: `EdgePyramid::new(sizes,guide,noise)`, `reduce(k,x)`, `expand(k,x)`,
`analyze(x)`, `synthesize(bands)`; `EdgeMerge::new(sizes,count)` / `add(index,
planes,weights,transform)` / `finish(transform)`. Generated API:
`compare_generated(frames,transforms,crop,noise,cfg,true_guide,diagnostics)`.
Tiny fixtures allow N1..17, requested3/7AC, active extent<=2110. This is no
all488 cost or quality claim. No full adapter is commissioned here.

Precomputed coefficients cost `4*(25*sum(coarse_pixels)+9*sum(fine_pixels))`
bytes plus guides/metadata, about81.3 bytes per finest quad for many levels.
This is O(image), independent of source count, and must be included in any
later full-memory budget; simultaneous nuisance arms are generated-only.

Fattal's2009 edge-avoiding wavelets are prior conceptual work, not code or a
quality guarantee for this fixed normalized-stencil recipe. Only the official
[publication abstract](https://cris.huji.ac.il/en/publications/edge-avoiding-wavelets-and-their-applications/)
was read. SYNTHESIS architecture/noise/storage decisions and the closest
completed native failures were read before this implementation.

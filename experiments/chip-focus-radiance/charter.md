# One complete native focus-surface radiance observation

Root decision, 2026-09-25. This is a separately scoped development observation,
not admission through the failed chip-focus-front proxy gate. That gate remains
false. Its fine band nevertheless predicts all23 held sites and all7 named
witnesses within the registered bars; aggregate relative error is0.21669.
Coarse p90 and lower-colour fail. The independent reviewer supports a bounded
native observation on the narrower fine-band evidence. No revised fit, width,
schedule, response family or selection of sites is permitted.

The new reconstruction is a direct convex radiance average on a fitted spatial
focus surface. It replaces the entire frequency assembly, including DC, for
this one candidate. For output quad(qx,qy), evaluate the saved front at native
centre(2qx+.5,2qy+.5), in the delivered6500x4332 reference149 gauge. Use the
saved xy normalization, plane, monotone299-source schedule and fine-band width.
Each frame's weight is exp(-.5*((t[k]-z)/sigma_fine)^2), identical for all four
CFA planes. Accumulate gathered black-subtracted f32 CFA values and weights in
source order, divide once. No categorical winner, per-band source prior,
private noise calibration, sharpening or inverse filter. Inputs remain u16 RAW;
gather, CA, injected noise for the canonical comparator and current MHC/writer
are unchanged. The candidate's entire radiance/DC changes deliberately.

The Gaussian is an empirically useful focus proxy, not a calibrated PSF or an
inverse-variance estimator. Its width is not optimized for final reconstruction.
Whole-field extrapolation beyond the fixed sites, local relief within128pixel
patches, input-to-native CA/tone/sampling mismatch, defocus averaging and reduced
noise averaging are explicit risks. All299 frames remain represented by the
fixed soft weights; f32 underflow may give negligible distant weights zero.
Every pixel must have finite positive total mass; otherwise refuse the entire
candidate. No hand-chosen patch mask, favorable source subset or width sweep.

One native pass uses the actual BandWorker gather while producing the unchanged
complete canonical merge and the radiance candidate. Original identities,
reference map and crop are fixed to the current chip receipt. The complete
canonical RGB16 and ICC must match current production; pin its exact tone for
the candidate and prove the pinned baseline rewrite is identical. Retain both
full masters, complete views and the existing25 unresampled native comparisons
covering all7 named targets and fixed controls. A full-image gain, if any, must
be shown to the owner; an overview cannot decide native-detail quality.

Independent controls execute the actual new accumulator before RAW reads:
nonzero spatial slopes and unequal coordinate normalization with wrong-coordinate
destroyers; constant/source/mean cases and finite-range refusal; known spatial
focus with a wrong-front destroyer and a flat-noise control. Mechanical
correctness alone cannot establish photographic benefit. Root executes bounded
build, controls and at most one complete candidate; no default promotion.

Prior search executed: `prior_art.py planar focus surface radiance blend`.
It identifies B-algorithms-sota, BUILD-BLEND, M70, V-BLEND, A-prior-corpus,
E-plugin-architecture, M67, M69, BUILD-PLUGIN and M7, also ORCH-veiling and
F-camera-lens-optics. SYNTHESIS architecture/profile decisions remain binding.
M70's useful off-peak information and the current V-DILUTE closure rule out
equating few sources with quality. BUILD-BLEND/V-BLEND's historical noise and
seam findings are not evidence for the current photograph. ORCH-veiling shows
why smooth recorded blur can survive noise gates on another scene, not a chip
measurement. Current shared-source, source-prior, same-band-agreement and
consistent-reconstruction failures remain closed. This candidate uses a
spatially predictive fitted front to average complete source radiance, rather
than electing each frequency independently or reweighting those coefficients.
It is not claimed to be a new general architecture or unprecedented algorithm.
In particular, native-coherent-estimator/design.md and results-september25.md
already test complete-radiance averaging. Their legacy regularized Tenengrad
gate loses genuine far-coarse structure and the observation is refused. That
fixed estimator remains closed. The difference here is the independently
predicted global spatial front and nonuniform schedule, not coherence alone;
this one nominally planar chip cannot establish multilayer-scene performance.

Ownership: source_trace authors operator/adapter; trace_review independently
owns controls and photographic interpretation; root owns runner/execution and
decision. No N-frame aligned volume, original-file writes or SYNTHESIS fold.

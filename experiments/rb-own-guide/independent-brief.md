# Independent R/B own-guide choice brief

Preregistered design, 2026-09-19; no test or RAW execution. Author: new_captures; independent fixtures/review: full_context_placement; executor: root. Concrete controls await the author's API. One small fixed screen, no parameter sweep or inferred camera focus offset.

**Question:** can red/blue guides recover genuine colour detail that green guidance misses, without increasing colour noise or mixing real depths? M107 and BUILD-CHROMA establish measured colour-dependent focus responses, but BUILD-CHROMA rejects them as the explanation of its rainbow-speckle and pink-rim defects. BUILD-HIGHLIGHT distinguishes original code limits from displayed white. None licenses a fan-cause or camera-calibration claim here. Mechanical prior-art search: `python experiments/ORCH-drift-check/prior_art.py "own guide" "per-channel" "chromatic focus" "colour focus"`.

## Compare the right arms

Keep canonical SoftPower, exponent schedule, pyramid sizes, terminal mean base, input hull, actual rounded gather and injected original-u16 noise model. Candidate changes R/B AC weights only. Original G1/G2 collapsed arrays must be bit-identical; developed green can change through MHC and gets its own truth guard.

Report canonical baseline, matched-estimator green guidance, and R/B own guidance. The same sixteen original-noise gathers provide eight independent pairs for all guides. For coefficient differences, the expected energy floor is the existing spatial energy smoother applied to the eight-pair half-squared differences, then the held gate. Do not multiply a second scalar beta into a variance already transported through gather and Laplacian. The matched-green arm separates guide benefit from changing the floor estimator. An unchanged-guide placebo must explicitly retain the canonical guide **and** canonical floor/weights, with exact canonical output; merely using green with a new floor cannot be required to match.

## Fixed scene set and decisions

Five original-u16 sources, asymmetric active origin and crop, existing held fractional similarity and warm WB. Use ISO100; repeat flat and the two positive cases at ISO400 only. No scene-derived noise fit. Exact geometry, carrier amplitudes and scoring windows will be frozen in the control source before execution.

1. Flat first, then a neutral/coloured detail field with synthetic R/G/B best-focus centres `[1,2,3]`, and its zero-offset twin `[2,2,2]`. Those indices define stimuli, not an optical constant or algorithm input.
2. Independent R/B detail with constant green, including an actual focused R and B source in the five-frame sequence. Each affected colour must have a truth component recoverable by its focused source (at least 0.5); a blank or unrepresentable plant cannot qualify a win.
3. Real thin features crossing at distinct depths and a genuine coloured radial feature. Preserve both structures, not just their shared intersection or the visually stronger surface.
4. A source-clipped glint next to unsaturated real detail. Record the clipped-code support. Do not demand recovery of unknown clipped radiance; score the independent adjacent detail and outside-core colour error against known generated truth.

For **each** offset/colour-only positive, require actual changed R/B weights/output and at least 5% lower RGB **and** R-G/B-G truth RMSE than both canonical and matched-green references. Require true R/B component recovery to retain at least 90% of either reference's truth-capped component wherever that reference recovers at least 0.5. For zero-offset, radial and crossing scenes, RGB, developed-green and chroma RMSE must each be at most 1.10 times either reference; apply the component guard separately to each protected feature. Flat RGB/chroma RMSE must be at most 1.25 times either reference. The clipped scene applies the structured guards only to its declared unsaturated adjacent/outside regions, while core output must remain finite and within the actual input hull.

Commission error/component scores with exact truth, a half-amplitude detail destroyer and an added-colour/noise destroyer. A known-wrong guide must exercise harm on a positive scene: exchange R/B guide **and matching floor** while retaining original output-plane samples. This is an independent negative control, not a competing candidate. A no-change guide must exercise exact identity. Both original green CFA planes, input hashes and terminal base remain exact in every arm. A small independently enumerated coefficient/noise witness checks pair factor, plane routing and transported floor units; it does not calibrate the camera.

Lower RMSE alone can reward smoothing; a component score can reward overcontrast; both can miss local mixed-depth damage. Therefore all protected windows and the noise control are binding, and no gradient-energy or winner-map score admits the candidate. Passing this generated screen would justify only considering a bounded full-photograph test after resource review, not promotion or a SOTA claim.

# Bee observer commissioning freeze

This supplements, without replacing, the source/role/region protocol SHA256 `f2fc47d451314ef0bf4a188cdf52d147d17de4fd72b947f58069017f631fcae4`. No real assay Q/V or R/M value selects the operating point.

The new linear Q model has two validation residuals and a full2×2 covariance. Energy is `rᵀC⁻¹r/2`, with Q-only signal-dependent variance and exact Catmull original-tap squared norms. Four measured bee placement windows, the frozen eye-facets and dark-background positions, both1200DN/200DN original levels and all4CFA components are included with equal case/component/block weights. Synthetic originalu16 noise uses the saved injected camera profile; this commissions the observer, not camera calibration.

Training uses only flat plants and seeds96..111. The one scalar cutoff is `max(1.10, nearest-rank empirical99thpercentile)` over all supported32×32component blocks: sortNenergies ascending and take element `ceil(.99*N)−1`. Training mean energy must be0.90..1.10 separately for every level/component/window/domain, and the learned cutoff must be≤1.50; otherwise stop and diagnose the instrument. There is no threshold retry or clamp-down. Report mean, median,95th,99thandmax before reporting acceptance.

Freeze this threshold before heldout seeds112..127. Known flat and linear illumination plants must each accept≥95% in every level/component/window/domain stratum and overall. Report every adverse acceptance for temporal curvature, focus change, spatial shift, step, clipping; an adverse acceptance is a power limitation, not a reason to fit the threshold again. A zero-noise linear drift arm is for the risk-confounding foil, not the injected-noise calibration gate.

The threshold is an empirical operating point on these controls, not a1%false-positive guarantee for real data. Neighboring blocks share sampling/filter support, and acquisition seeds are replication units. Later real masks retain all predeclared regions/components and all candidate fallbacks. Complete source/guide/filter dependencies must remain valid; R/M do not select the mask or threshold.

The algebra controls already establish midpoint confounding and conservative two-state risk, but do not replace actual sampler/core controls. The descriptive midpoint reference is the average of timestamp-interpolated R_at_M3 and R_at_M4 (equivalently R interpolated at the averageMtime), not an unweightedR2/R5average when intervals differ.

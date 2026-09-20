# Independent shot-noise-prior source review

SOURCE-REVIEWED; no author/reviewer execution. No material blocker remains for the prescribed commissioning followed by two fixed fits and independent scoring.

The candidate uses the declared cancellation-safe difference `sqrt(2)*(S2-S1)/(sqrt(g*S2+c)+sqrt(g*S1+c))` on each RGB sheet. Its denominator remains in autograd: there is no detach, observed-signal substitution, private noise estimate, or latent radiance clamp. The vector norm, Huber transition at two, axis/sheet averages and coefficient are preserved. The inherited norm safeguard is converted by the original reference scale squared. Alpha TV, binary penalty and normalized radiance L2 retain their original expressions and coefficients.

This matches the old local gradient normalization at 2048 DN; it is not globally equivalent to the old penalty. The independent controls compare the actual f32 helper against a literal transformed-coordinate f64 oracle, test a live reference-scale edge and contrast derivative, and use distinct near/far images to exercise the sheet average. Crucially, the nonconstant common-brightness control requires a lower penalty and a negative brightness derivative, checked independently by finite differences. That exposes the expected incentive to brighten textured sheets. The constant-field check alone would not reveal it. The reported derivative excludes the separate data and L2 responses and must not be described as total-objective brightness behaviour.

The fitting state clones the same original160 sheet parameters and true alpha as visibility-1, verifies their hashes/configuration, and optimizes only near/far radiance. The likelihood, censoring, optics, supported interior, training-only facade and fixed 1000-iteration L-BFGS budget remain unchanged. The scorer also checks exact initial near/far/alpha/pinhole identity against the retained reference. No original-prior baseline is rerun or selected after observing results.

Flat is scored first with both original and paired RGB/chroma guards; signed per-channel bias and tails are descriptive additions. Layered retains the original truth and held-out checks plus paired core/ridge error and truth-capped component protection. Returned-state acceptance and raw-parameter stationarity remain separate. A changed objective value cannot establish a fit or image improvement across the two different priors. Final held predictions are generated after fitting and do not enter optimization.

The wrapper CLI matches both scripts, commissions before fitting, binds sources and retained reference files, and checks immutability between stages. Existing continuum-optics failure and unknown visibility remain unresolved. This is an experiment in regularity under injected noise and known visibility, not sensor calibration, a free-alpha solution, or real-photo admission.

Reviewed SHA256 bindings:

- `shot-noise-prior.py`: `adaf3118df4893186f37f844c449c8f79b77add297c7b5177fbe771986e77670`
- `shot-noise-prior-plan.md`: `0ccd1fdb0f426a3c3571b73ac3f7d81367f3c359ada5d696d7e19a91a12a10fe`
- `shot-noise-prior-controls.py`: `394ce6c39ad34b4ba40d24915430207c5eace4185fddb354a843113de1e65cbb`
- `shot-noise-prior-independent-plan.md`: `986ac355e3f8703c8ef686701c31bf6241513201976fefcef34d7325160f5c2b`
- `run-shot-noise-prior.py`: `a4e08d7da6f46a25e828fcd1ff4312485a1415c49cab5c3c895fa7b64720c1d2`

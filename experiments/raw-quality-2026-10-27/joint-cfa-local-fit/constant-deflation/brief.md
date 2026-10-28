# Exact constant-color elimination, fixed finite work

Root allocates one materially changed solver question after the original-CFA
band-residual flat fails visibly despite its normal-residual stop. The no-fit
budget finds substantial error at original samples and a known-constant
objective12.3times lower than the returned field. No original-A nullspace cause
is established. See ../band-residual/results.md and the saved budgets.

Use exactly the existing original-u16 fixtures, A/H/q, noise, geometry,64-step
bound and reference-cell delivery. No image prior, chroma coupling, clipping,
focus-parameter change or longer iteration rescue. Let C contain three constant
camera-color fields, U=B C using the actual weighted operator, and
P=I-U(UᵀU)^−1Uᵀ. Solve min||P(Bz-b)||², then restore
X=z+C(UᵀU)^−1Uᵀ(b-Bz). This algebra preserves the original objective/minimizers;
finite precision and finite-work outcomes must be checked. Preserve all finite
fields even on numerical/image refusal. Use f32 arithmetic and stable norms.
Zero-start projected CGLS minimizes the correction-coordinate norm; restoring
the constant can select a different member of an underdetermined minimizer
family. Do not claim identical minimum-norm X or only a harmless reparameterization.
Use the actual color-disjoint U columns and checked scalar Gram normalization,
not an unchecked generic inverse. Their observed supports must be orthogonal.

The stopping reference is the actual projected initial normal; also report the
reconstructed original objective, full normal and constant-direction normal.
Test literal B(C), P symmetry/idempotence/annihilation, projected adjoint and
objective equivalence. A wrong one-sided projection must fail. DC-offset
invariance applies only with identical frozen noise/weights/geometry; do not
recompute shot variance or focus weights for that control. Constant coefficients
must come from measurements, never known fixture truth. No test may supply
hidden depth, component amplitudes or truth as an initialization.

Prior reviewed: September14 Lanczos weak-first-difference reconstruction improved
noiseless controls but had chroma noise and a soft/stippled actual photograph;
residual updates amplified noise. Those results prohibit treating simple prior
or update recipes as established fixes. Current zero-start weighted convergence
does not establish faithful radiance. Research search and mechanical prior-art
check for`deflation projected constant` found no exact documented counterpart;
that limited search is not an absence claim. No change to the broader RAW
contract or independent photographic acceptance follows.

Ownership: cfa-residual prepares isolated implementation/API; photo-review
prepares independent projected mechanics and existing actual-baseline image
guards; integration-review audits algebra and stopping/reference choice; root
owns runner and all execution. No agent numerical jobs or builds.

First root checkpoint: mechanics plus one complete neutral-flat fit,120s/
480CPU seconds/4GiB/fourworkers. If the unchanged actual-baseline flat guards
fail, stop without the larger screen. If they pass, root may release the fixed
ten-candidate/four-foil inventory under300s/1200CPU seconds/4GiB only after a
measured cost projection. Flat color and different-depth/independent-color
preservation remain essential; a repaired neutral flat is not success. No full
photograph is released by this brief. GPU streaming cost, clipping/fallback and
whole insect/corpus evidence remain outstanding before photographic claims.

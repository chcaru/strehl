# Coupled quadratic NCC refinement

2026-09-14. Source implementation only; no accuracy or photographic gain is
claimed. The root owns builds/runs; a separate agent owns the controls and
consumer comparison. The existing separable peak refinement remains default.

Both production NCC paths already calculate a score grid and elect an integer
maximum. Their independent horizontal/vertical parabolas omit the mixed second
derivative. `quadratic_peak` derives the full 2x2 Hessian from the existing 3x3
stencil and solves one linear system for its stationary point. For an exact
quadratic the omitted term biases the old x offset by hxy/hxx times the true y
offset (and conversely). This is a derived mechanism, not a real-image finding.

All arithmetic is f32. Original source images, integer peak, NCC threshold,
contrast, matching support and warped-coordinate conversion remain unchanged.
The helper requires a unique integer maximum, finite local samples, a negative
definite Hessian and offsets strictly inside +/-0.5. Its Hessian is normalized by
its largest absolute entry before requiring determinant >1e-4. This is a fixed
engineering conditioning limit, not sensor-noise calibration. Any refusal uses
the original parabolic expressions and result bits. The old sinc experiment
still uses its original separable fallback even if a caller requests quadratic.

Failure inputs include nonquadratic peaks, varying defocus/depth mixtures,
nearly singular oblique ridges, repeated-pattern ambiguity and noisy curvature.
Correct recovery of a literal quadratic cannot validate those cases. The
independent fixed 48-row fixture calls both actual NCC paths, preserving the
previous experiment's continuous scene/noise and independent displacement truth.
Local errors do not establish full-stack placement or image quality. Root's
subsequent photographed comparison, if admitted, must inspect preserved fine
structures and a flat control using the same development settings.

The only CLI entry is `strehl align --peak-refinement quadratic --out <map>`.
An explicit output is required to avoid changing automatic cache semantics;
automatic merge alignment stays separable. The candidate is recorded in the
sidecar note. Diagnostic align submodes reject this flag instead of ignoring it.
An exhaustive live `AlignConfig` literal in the M103 probe inherits the new field
from its original base configuration; historical source snapshots are untouched.

Prior art checked with `python experiments/ORCH-drift-check/prior_art.py
"coupled quadratic" "2D quadratic" "cross curvature" "NCC peak"` (exit 0).
It surfaced M12 and M78. Additional scoped source search found no coupled
quadratic implementation. M103's endpoint/per-frame distinction, failed
metacalibration/cross-blur, the failed angular-spectrum candidate and the sinc
control failures were reviewed. This differs from sinc/Newton: nine existing
scores, no reconstructed 9x9 interpolant, no iteration or convergence criterion.

Verification pending: independently chosen literal/symmetry/refusal controls,
both current NCC consumer paths, original alignment regressions and CLI parsing.
No new RAW decode, numerical test, build or source write outside this repository
was performed by the implementation author.

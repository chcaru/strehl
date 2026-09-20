# Fixed R/B residual guard

Prospective generated experiment,2026-09-19. Preserve rb-own-guide at69f5d145 and
its rejected screen. Its guide-specific colour gains were accompanied by flat
noise and delivered-camera-green regressions; no full photograph is admitted.
Root executes; author never verifies. No parameter sweep, new RAW input or
production default change.

Reuse exactly the previous actual GPU rounded gather, original-u16 injected
noise, sixteen independent source draws, three R/meanG/B guide transforms,
spatial floor, SoftPower weights, mean fallback/base and InputRange hull. The
unsmoothed coefficient variance is now retained as V=sum8(La-Lb)^2/16.
For every R/B coefficient use T=L^2/V, with V=0 explicitly ineligible (also for
nonzero L). Negative/nonfinite variances or coefficients refuse. The threshold
is q=F(1,8).isf(.01/(2*N*nb*25)), where nb is actual reached AC-band count.
Only this scalar tail/quantile calculation uses f64. Convert q upward to f32
once; image arithmetic is the finite-checked f32 comparison L*L>q_f32*V.
An output band coefficient is activated if any source scalar exceedance lies
in its existing clamped5x5 energy support. No additional mask smoothing occurs.

In each R/B AC band the fixed expression is Ccanonical+A*(Cown-Ccanonical).
At A=0, return literal canonical bits, including signed zero. Terminal means
are canonical. Collapse on the full generated domain and apply the original
input hull; original G1/G2 planes remain exact canonical. Demosaic canonical and
new CFA reconstructions using the unchanged MHC/WB/range operation, then form
(Rnew,Gcanonical,Bnew) in normalized WB camera RGB. Any subsequent matrix/tone
is unchanged. This holds camera G, not final sRGB G after a mixing matrix.

The F law is exact only under an independent scalar Gaussian-linear null with
the stated variance. Observed-DN noise injection, u16 rounding, black clipping
and actual gather nonlinearities mean this experiment has no calibrated camera
false-alarm guarantee. The union bound does not require independent neighboring
taps, but this is only a local coefficient-support family, not native-output-pixel
or whole-image FWER: inverse-pyramid support propagates changes. Eight pairs
cannot establish empirical extreme-tail quantiles. No effective-DOF estimate
from independent smoothing taps, scalar-beta multiplier or private noise fit is
introduced.

The independent first falsifier is flat N5/N9 at ISO100/400, requiring each R/B
band's mask fraction<=.01 and output RGB/chroma error<=1.05 of both canonical
and matched-green references. Then retain the earlier truth scenes and component
guards. References include the old canonical/matched-green/own/identity/swapped
arms plus camera-green-only, separating green preservation from residual guarding.
All old arms share the same sixteen gathers; no extra source collection occurs.
Diagnostic-off repeats must preserve all output hashes. Root supplies independent
SciPy F quantiles; the independent helper checks /16, support, invalid variance,
exact-zero mixing and threshold inversion before the image screen.

This does not revive significance_scale: SYNTHESIS1908 reports its failed derived
strength and upstream singleton limitation. Nor does it revive M194h's cutoff:
that intervention repaired one selected site but restored a secondary defect and
worsened every fixed-window RGB MSE against its pedestal comparator. No Wiener
or PSF inversion from the retired M41 route is used. Failure closes this fixed
guard without threshold rescue.

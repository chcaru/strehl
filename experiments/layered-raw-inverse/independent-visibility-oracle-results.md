# Independent fixed-visibility results

MEASURED by root on2026-09-20; independently reviewed from retained scores and
optimizer receipts, without fitting, rendering or changing the model. Fixing
visibility resolves the fixed flat-image failure and improves the layered
reconstruction substantially, but the layered bright-prediction and paired
glint-retention requirements still fail. The whole diagnostic is not admitted.
Score SHA256: `1b419e0c0eb0223522a23d4de0642b454bb1ec93b4b2a09e0e5f8ebf7a021088`.
Root's exact command is in visibility-1/fit-process/invocation.json; fitting
took35.625s and independent scoring2.344s. These are operational costs.

The intervention was executed as specified: initial radiance parameters and
sheet arrays remained exact; independently exported alpha stayed byte-exact;
only near/far were optimizer parameters. Original sources and reference outputs
remained unchanged. Both fits were accepted finite returns. Flat used196
evaluations/184 iterations; layered1021/1000, within the fixed limits. All
observed fitting indices were the seven training indices. No truth radiance or
held-out observation entered the solve.

Flat separates immediate recomposition from fitting. Changing only the matte
reduces RGB/chroma error from the original checkpoint8.675/12.346 to
7.517/10.294DN, still failing the absolute bars. Radiance fitting then reaches
5.672/7.926DN, passing both the mean6.018/8.368 references and the free-alpha
long-run43.301/65.698 references. Both held views and all present CFA strata
pass, with global RMS1.002/1.010 supplied sigma. There are no bright or censored
held samples in this case, so those absent strata supply no corroboration.

This is causal evidence that removing spatial opacity freedom prevents the
observed flat failure under this bounded recipe; it is not evidence that a
camera must estimate the exact constant0.35. Both true flat sheets are identical,
so their underlying opacity is not uniquely identified by these observations.
The fixed-alpha fit has higher training NLL than free-alpha3.67851 versus
3.63922 while giving a much better delivered image. That directly reinforces
the earlier finding that improved training fit alone does not protect output.

Layered recomposition alone is not a sufficient explanation for its final
gain. With correct alpha and unchanged old sheets, whole RGB error initially
gets worse,235.11->266.93DN; glint-free ridge components are only0.688–0.813
and fail the original detail guard. After fitting, whole/core/ridge/crossing
errors are150.97/731.46/312.40/577.41DN, compared with
260.55/1117.53/519.13/912.66 for the matched free-alpha reference. All original
image truth bars pass. Ridge components recover0.954–0.982 and pass the paired
protection. Correct visibility therefore enables useful radiance refitting;
it is not just an oracle matte pasted onto an already correct pair of sheets.

Two explicit failures remain. Glint components are0.96153/0.95335/0.96398.
The free-alpha1.018/1.006/1.022 values are capped at truth1 before comparison,
so the required threshold is0.98. This failure is not an accidental punishment
for removing reference overshoot: the new result undershoots the protected
component by about3.6–4.7%. At the same time, its lower absolute RGB errors mean
the projection loss cannot be equated with an overall worse image. Keep both
observations and the predeclared rejection. Held focus0.25 also fails on41
bright samples,2.14781sigma versus1.75, despite global1.04728. Focus0.75 has no
bright samples; its1.22199 global pass does not resolve that defect. All held
samples are uncensored.

Neither fit is stationary at the declared1e-6 parameter-gradient bar. Flat
returns at7.24e-6 after184 iterations, exceeding that bar; raw-parameter
stationarity would not itself prove radiance-space stationarity. Its repeated
final objective values suggest limited
numerical progress, but do not establish the exact internal stop cause.
Layered reaches the1000-iteration limit at0.002852. Its last closures still
decrease total, with data/prior trading small changes. Thus the bounded success
on flat is valid, but no optimum-level claim follows; the residual bright
attenuation cannot yet be assigned uniquely to the prior.

Fixed-DN regularity is a plausible contributor, not a measured cause. Its
reference scale stays tied to2048DN while shot variance rises with radiance;
for an unsaturated scalar observation, likelihood precision then decreases
while the fixed image-gradient penalty does not. In a local scalar model this
can require a larger bright residual to balance the same prior force. The
actual coupled, censored, multi-frame inverse is more complicated, and a
nonstationary state can produce the same attenuation. Current results separate
opacity freedom from the remaining conditional-radiance problem; they do not
separate regularization bias from unfinished optimization, or justify changing
the injected noise model or tuning a prior to the bright subset.

Known visibility is useful but insufficient for this complete test. The next
automatic problem remains estimating and validating visibility from the RAW
stack; this oracle supplies no such estimator. Matched64-ray optical tests
still do not repair the separate64/1024 adequacy failure. No photographic,
canonical-merge, calibration or SOTA claim is supported by this result.

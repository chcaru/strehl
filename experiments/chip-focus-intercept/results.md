# Independent fixed-intercept screen result

MEASURED, 2026-09-25: **the frozen scientific screen failed.** All four
mechanical tests passed, but the two-depth protection did not retain 98% of
the far component. The registered result is closure of this fixed recipe under
that screen. No full observation, canonical-consumer qualification, production
change, width/degree sweep or threshold relaxation is authorized by this result.

The failure is informative rather than a numerical refusal. The near-fine
component improves from approximately 0.6192 to 0.7798 of its focused template,
while the far-coarse component falls from approximately 0.2250 to 0.2178,
retaining about 96.8% rather than the required 98%. Both components were live;
joint regression retains their covariance. Whole-image RMSE and the aggregate
template recovery improve slightly, so they would conceal this loss without
the separate-component protection. The far component is already poorly
recovered by the Gaussian; the reported loss is about 0.0071 of the focused
template, not 3.2% of the whole image or an established photographic defect.

| Independent check | Saved result and scope |
| --- | --- |
| Dense f64 oracle / exact quadratic | Maximum errors 0.004036 / 0.003906 DN; moment error 5.42e-7. Arithmetic commissioning only. |
| Support refusals | Rank-deficient, one-sided, negligible opposite mass, order/missing and invalid inputs refused. No fallback image. |
| Flat noise, executed first | Observed MSE 148.355 DN² versus propagated 148.020 DN² (ratio 1.002263). Gaussian MSE 88.206 DN². |
| Actual signed-weight propagation | Direct sum(h²) and moment expression agree within relative 5.73e-7. Maximum variance ratio to Gaussian 1.7662; maximum unit-source gain 0.3962. Frozen noise bars pass. |
| Unchanged nonquadratic sinusoid | MSE 9,980.357 versus Gaussian 55,248.281 DN², about 0.181 times its MSE. Wrong supported front 866,750.199 and erased detail 1,339,927.645 DN² both fail the same benefit bar. |
| Bright contact | Whole, interior, edge and outside protections all pass. Whole per-plane RMSE falls from 159–192 DN to 91–107 DN; no clean signed range excess. |
| Near-fine/far-coarse | Whole RMSE and noise/range bars pass, but separate far-template retention fails in every plane. Scientific refusal. |
| Signed overshoot destroyer | Bounded temporal input produces 502.121 DN above its maximum, exceeding the fixed 64-DN bar. The range check has power; this synthetic alignment with positive weights is not a physical scene. |

VERIFIED choices: the successful unchanged-Gaussian sinusoid and flat MSE values
exactly match the preceding radiance screen's saved values. No input tuning
produced the new positive. The wrong-front control reverses slopes while
preserving range, so it is numerically admitted and its failure is actual
wrong prediction rather than a support rejection. Noise increases as expected
for signed quadratic weights; no Gaussian-noise-parity claim is made. The
actual finite-sample propagation, not the asymptotic 27/16 value, was gated.
The two-depth failure is the originally named failure mode, not a new reason
invented after seeing the result. The pre-execution component and localized
contact protections were necessary to expose it.

ARGUED next-direction judgment, separate from the failed decision: there is
meaningful single-surface headroom here. The previous complete Gaussian chip
already reduced broad coloured spread while losing native detail; this fixed
intercept substantially recovers nonquadratic focused detail and improves the
known single-depth contact without clipping or exceeding the declared noise
policy. That makes one separately labeled exploratory chip observation more
informative than another synthetic family or bandwidth sweep. It is not
automatically admitted. Root would have to explicitly record a new, narrower
observational decision despite the preregistration's closure, leaving this
screen false and the canonical-consumer/detail gate unmet until evaluated.

The chip is only approximately a single surface. Its coarse proxy failed, and
small relief, unresolved multiple depths, calibration, front error and gather
error remain possible. The polynomial specifically addresses local averaging
bias; the prior photograph did not identify that bias as the cause of every
soft feature. A complete candidate could amplify noise, damage far details or
leave the blur unchanged. I support at most one unchanged-formula observation
with the same canonical comparator and Gaussian reference, exact current
gather/tone identity, explicit all-site refusal, and all 25 native protections.
I do not support a general route, repeating this screen with different bars,
or using the new image to select width/degree. If the fixed native image loses
detail or adds objectionable overshoot, close it without a rescue sweep.

Root executed the standalone build (13.25 s) and four controls (0.781 s):

```text
python experiments/chip-focus-intercept/run.py build --out experiments/chip-focus-intercept/build-1
python experiments/chip-focus-intercept/run.py controls --build experiments/chip-focus-intercept/build-1 --out experiments/chip-focus-intercept/controls-1
```

`controls-1/completion.json` records four passes, sources_unchanged=true,
scientific_screen_pass=false, canonical_consumer_qualified=false and
photographic_quality_admitted=false. All four test receipts remain unchanged.
Adversary SHA256:
`0bd2e2128b8f4efc7f0c2f2abbc777320a1aaaa2740e26a39318228b0686a8db`.
Planar SHA256:
`393652d271192528f9a1a4f61ad4e987649600687fbe8b976c001911f0994141`.
These timings and error ratios are generated-operator evidence, not native
stack speed, camera calibration, photographic percentages or SOTA evidence.

# Guarded R/B colour evidence: generated result

MEASURED by root, independently reviewed in results-review.md. Fresh release
build149.688s; fixed actual-consumer test3.953s. Commands:

```text
python -I -B experiments/rb-residual-guard/quantile-reference.py
python -I -B experiments/rb-residual-guard/run.py build --out experiments/rb-residual-guard/build-1
python -I -B -X faulthandler experiments/rb-residual-guard/run.py controls --build experiments/rb-residual-guard/build-1 --out experiments/rb-residual-guard/controls-1
```

The test completes successfully; frozen photographic admission remains
**false**. Screen SHA256:
9f064df49645fafc45b5c2cd16d379a5c1fe048a3b47549f7af8062783aea8ae.
All image-quality bars pass. The sole failure is ISO400/N5 red-band-2 mask
area20/1184=1.689%, above the frozen1% budget. There is one raw crossing,
in source4; its existing5x5 support expands to20 cells. Do not reinterpret
those cells as independent events or retrospectively change the bar.

Flat RGB-error ratios to canonical are1.00031,1.00153,1.00585,1.00511 for
ISO100/N5, ISO100/N9, ISO400/N5, ISO400/N9. Chroma ratios are1.00108,
1.00357,1.01160,1.00950. All remain within the strict1.05 limits and beat
the matched-noise green reference. On colour-offset/colour-only plants,
RGB-error ratios are0.16478/0.42425 at ISO100 and0.24958/0.43184 at ISO400;
they also pass the independent matched-green comparisons. Neutral,
crossed-depth thin features, radial structure and clipped-adjacent guards
pass. These are generated-scene errors, not photographic quality scores.

Canonical camera green is exact; final sRGB green need not be exact after
the mixing colour matrix. The green-copy-only arm retains much larger flat
error, so green copying alone does not explain the guarded result. Wrong
source/guide controls demonstrably destroy genuine signal. Original five
arms reproduce the committed own-guide experiment exactly. Probe routing,
independent scalar quantiles, zero/invalid variance refusal, literal-zero
residual, actual input hulls, canonical terminal means, original immutability
and observer-neutrality checks pass.

The F(1,8) scalar model assumes independent Gaussian coefficient draws.
Signal-dependent injection, integer rounding and nonlinear black clamps mean
this has not calibrated sensor tails. Local support multiplicity does not
give a full-image bound after reconstruction. The failed area diagnostic
stays visible alongside the image results.

The independent reviewer recommends one separately preregistered ISO100
observational full photograph after full-domain mechanics and resource
checks. Root accepts that recommendation in
../rb-residual-full/observational-plan.md. This does not change the generated
admission, production defaults or the program's unproven SOTA status.

# Independent sampling-isolation plan

Registered before new fits on 2026-09-25. This is a generated-only explanation
of an earlier failed instrument control, not permission to retry photographic
alignment, adjust the beta threshold or tune interpolation kernels.

First repeat the original pure-translation stimulus unchanged: original waves,
392-square grid, nonidentity A/B, known delta(0.43,-0.57), G2/top-bottom split,
phase guide, gain1.06/bias0.017, ordinary and joint model, optimizer limits and
all original refusal rules. Save both complete fit records and every scalar
admission component **before** checking the old beta-within0.03 requirement.
Keep a failed screen as failed even if the sampler diagnosis later succeeds.
The earlier run never saved its beta, so this is a newly measured value, not
recovery of an old missing number. No source patches or RAW files may be opened.

For the isolation layer, **hold motion at its known planted value**. A jointly
fitted translation could trade against interpolation blur and defeat the
purpose of this comparison. Joint motion remains only in the unchanged replay
above. Use identity geometry with exactly three prescribed phase offsets:
(0,0), (0.5,0.5) and (0.5,0). Reuse the same independent analytic waves,
photometric gain/bias and separated train/test grids. Omit the phase-only guide
from this layer and label it an interpolation unit control. Its absence is an
explicit simplification, not a repair of the original discriminator.

Compare exact evaluation of the continuous source with order1 sampling of its
point-sampled raster. Both source design columns use the same independently
defined **five-point discrete Laplacian**, including the source-pixel unit.
At an off-grid coordinate its exact counterpart is source(z+1)+source(z-1)+
source(z+i)+source(z-i)-4*source(z), evaluated from the analytic field. Do not
quietly use the continuous Fourier Laplacian in one arm and the discrete
stencil in the other. Gain, Laplacian coefficient and bias may be fitted on
training support; apply them unchanged on held-out support. No motion fitting,
phase search, source-frame search or nuisance refit on holdout is allowed.

Required falsifiable expectations: exact evaluation with zero physical blur
has beta within the original0.03-native-pixel-squared bar at all three phases.
Integer bilinear evaluation agrees with its exact-evaluation arm within that
same bar. Half/half bilinear has a negative beta outside the near-zero bar and
a larger absolute beta than the exact arm; otherwise the proposed numerical
confound is not demonstrated. Record every value before refusal. The Taylor
value near-0.125 is a low-frequency prediction, not an exact acceptance target
or a correction to subtract from later photographic estimates.

The half/integer phase is explicitly outside a scalar isotropic explanation:
its leading interpolation error acts along one axis. Report its fit and
held-out residual without pretending a scalar beta measures physical isotropic
defocus. Existing flat/rank and wrong-sign controls remain adverse evidence;
the new isolation does not silently re-admit those scenes. State conditioning
and sample counts so an exact beta from a degenerate design cannot pass.

A unit-layer positive shows that bilinear evaluation can create an apparent
blur coefficient. It does **not** establish how much of the original guided,
nonidentity failure it explains. The fixed normalized phase guide and sampling
lattice may contribute their own mismatch. A higher-order replacement would
be a separately declared, single conditional comparison on the original
stimulus; no saved-photo retry or kernel sweep follows this experiment alone.

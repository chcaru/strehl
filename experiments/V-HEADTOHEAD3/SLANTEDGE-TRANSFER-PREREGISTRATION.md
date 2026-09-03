# V-HEADTOHEAD3 — externally fixed USM transfer amendment

**Registered 2026-09-03 before applying the sibling lane's exact USM to any
real V-HEADTOHEAD3 render.**

## Prior and question

M-PHASE0-SLANTEDGE commits `1639efc4`, `e4b95d3c`, and `09977acc`
independently exercised the licensed V-HEADTOHEAD3 `Q25` statistic.  On its
frozen Gaussian-edge fixture, base `Q25` was `9.52160e-4`; identity,
sigma-0.75 blur, genuine sigma-1.20 improvement, and unclipped
radius-1/amount-0.5 USM read `1.000000`, `0.841501`, `0.977981`, and
`5.560744x`.  Affine/gamma-3/logistic read
`0.999963/1.000000/0.999966`; extra-noise median was `17.0056x`.

Thus `Q25` remains strongly point-tone invariant but is neither
sharpening-safe nor a calibrated resolution statistic on that plant.  This
amendment asks only whether the exact externally fixed USM produces enough
`Q25` gain on the already frozen real macro sites to account for the
PMax40/PMax0 `Q25` swing.  It cannot promote `Q25` back to resolution, MTF,
M1, M4, or M8.

The existing sigma-1/amount-1 sensitivity result is known
(`2.7920 [2.6438,2.9666]x` on PMax0), but its operator differs from the new
prior.  It will not substitute for this exact transfer.

## Bias

Bias is toward finding that real-render USM gain is large enough to explain
the apparent PMax40 advantage, and therefore toward retaining sharpening-0 as
the only honest development-matched descriptive comparator.  Evidence
against that bias is welcome.  The exact parameter, sites, band, transforms,
hashes, thresholds, and bootstrap seeds below are fixed before measurement.

## Frozen inputs

No site is selected, replaced, or relabelled:

* `sharpening_frozen.py`: 24 source-only detail sites, digest
  `B3A2F5279069A3CC85FB42F49F6FDA39397423D9A65565CAB88CCF8E627679F6`;
* strehl master:
  `4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F`;
* PMax0:
  `B240FE4016E97EBB194497B2798A095C63C490C4FFF54018D48D34C7523719A0`;
* PMax40:
  `4D490F71EF63DA33758A49BF583AD2166CD014A5401ED64EDB5E5EDCABB47A3E`.

PMax40 is locally registered to PMax0 exactly as in the frozen sharpening
arm.  Strehl is paired independently to PMax0 and PMax40 using separately
image-fitted scale and translation.  Measurement pixels remain native;
interpolation is permitted only for geometry/registration diagnostics.

## Externally fixed transform and statistic

The transform is exactly the sibling plant:

```text
low = scipy.ndimage.gaussian_filter(
    image_float64, sigma=1.0, mode="nearest", truncate=6.0)
USM05 = image_float64 + 0.5 * (image_float64 - low)
```

There is no clipping.  `Q25` is the existing average-rank, Hann-windowed
energy in `[0.20,0.25)` divided by fixed rank variance.  Nothing above 0.25
is read or reported.  Because the sibling battery refused `Q25`, every result
below is labelled **presentation sensitivity, not resolution**.

On the 24 fixed sites define geometric-mean paired quantities:

```text
T0   = Q25(USM05(PMax0)) / Q25(PMax0)
M40  = Q25(USM05(PMax0)) / Q25(PMax40)
TS   = Q25(USM05(strehl)) / Q25(strehl)
S40  = Q25(USM05(strehl)) / Q25(PMax40)
R0   = Q25(strehl) / Q25(PMax0)
O40  = Q25(PMax40) / Q25(PMax0)
```

`T0/5.560744` and `log(T0)/log(5.560744)` compare real and synthetic
magnitudes descriptively; neither is a calibration score.  Author intervals
use 10,000 paired-site bootstrap draws, PCG64 seed `20260906`; the independent
checker uses seed `20260919`.

Frozen interpretation:

* `REAL_TRANSFER_SUFFICIENT` if `LCB95(T0)>1.05` and `LCB95(M40)>1.0`;
* `REAL_TRANSFER_PARTIAL` if `LCB95(T0)>1.05` but `UCB95(M40)<1.0`;
* `NO_REAL_TRANSFER` if the complete `T0` interval lies in `[0.95,1.05]`;
* otherwise `UNRESOLVED`.

“Sufficient” means only that the information-free post-render operation can
equal or exceed the real `Q25` rung.  It does not prove that this operation
caused PMax40, because the two source developments differ in eleven fields.
`R0` is the requested sharpening-matched descriptive comparison, but it too
cannot be called resolution.

## Commissioning and stops

Before real pixels, author and independent implementations must:

1. recover an analytic radius-6 Gaussian impulse kernel and catch a changed
   amount or boundary;
2. show identity parity, a blur degradation, and an enabled USM improvement
   in `Q25`; disabled blur/USM mutants must go RED;
3. retain exact affine/gamma-3/logistic invariance and reject 0.28125;
4. recover a planted translation with the correction sign; wrong-sign and
   no-op mutants must go RED;
5. make a fixed external log-ratio bootstrap oracle and all four literal
   interpretation branches agree;
6. reject a changed input hash or site digest.

Stop without changing a threshold if either commission fails, an input/site
identity changes, either geometry has no interior optimum, author/checker
scales differ by more than 0.5%, fewer than 12 sites survive, or their point
estimates disagree outside the union of their 95% intervals.

## Product consequence

No Rust change may follow from `Q25`, which is now refused as a resolution
instrument.  A sufficient real transfer amends the competitive narrative:
PMax40 cannot evidence a stacking-resolution deficit, while PMax0 becomes the
only admissible development-matched descriptive arm.  It does not itself
establish a PMax0 tie or a physical strehl deficit.

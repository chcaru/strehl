# M164 common-transfer veto — preregistration

Status: frozen before any M164 measurement pixel was decoded.

## Question and one-sided decision

Given two registered, linearized rendered outputs `A` and `B` of one scene,
does a low-complexity common transfer predict the realized difference
`D = B - A` on spatial tiles that were not used to fit it?

The instrument is a **veto**, not a quality score:

- `INADMISSIBLE_COMMON_TRANSFER` means that M1, M2, and M9 comparisons between
  these two bytes must be refused.
- `NOT_VETOED` means only that this veto did not identify a common transfer.
  It does not say that either output is better.
- `IDENTITY_EQUIVALENT` does not fire. Identity is not evidence that a
  comparison is being gamed.
- malformed, non-finite, too-small, or unquantified inputs return
  `INSTRUMENT_INVALID`; they never produce a pass.

## Non-vacuity restriction

An unrestricted finite-image LSI test is tautological. If every DFT
coefficient of `A` is nonzero, then

```text
H[k] = FFT(B)[k] / FFT(A)[k]
```

defines a circular convolution taking `A` exactly to arbitrary `B`. Such a
test would fire on everything.

M164 therefore freezes two deliberately restricted, physically relevant
families:

1. **smooth zero-phase LSI**: scalar gain; every dihedral-symmetric local
   orbit through radius 3; and `G_sigma(A)-A` at sigma
   `0.20, 0.25, 0.30, 0.40, 0.60, 0.80, 1.00, 1.50, 2.00, 3.00 px`;
2. **period-2 resampling**: a separate full radius-2 linear kernel for each
   `(x mod 2, y mod 2)` phase.

The second family exists because a twofold down/up interpolation is linear but
polyphase rather than strictly shift invariant. The veto chooses the family
with the lower held-out residual. A non-fire outside these families is not a
certificate that no common transfer exists.

## Fitting and held-out statistic

Inputs are one linear-light scalar plane with a declared quantization step
`q`. M164 uses deterministic sample points at stride 3, excludes a 12-pixel
outer border, and partitions 64-by-64 macrotiles by checkerboard parity.
Each family is fit twice: even macrotiles train / odd test, then odd train /
even test. Columns are RMS-scaled on the training fold and solved by ridge
least squares with dimensionless ridge `1e-8`.

The model predicts `D`, not `B`. The scalar column is `A` itself, so a common
gain `g` appears as `(g-1)A`; it is not divided away. The constant column is a
nuisance black offset and does not count as a transfer by itself.

On the union of both held-out folds define:

```text
r_rel  = RMS(D - D_hat) / RMS(D)
r_abs  = RMS(D - D_hat) / q
r_tile = per-macrotile RMS(D - D_hat) / RMS(D)
r_fold = RMS(D_hat_even_fit - D_hat_odd_fit)
         / RMS((D_hat_even_fit + D_hat_odd_fit)/2)
```

Only tiles with `RMS(D) >= 2q` enter `r_tile`. A veto fires iff all frozen
conditions hold:

```text
RMS(D) / q                         >= 0.50
number of informative tiles       >= 8
r_rel                              <= 0.12
r_abs                              <= 0.75
q90(r_tile)                        <= 0.25
r_fold                             <= 0.20
```

These conjunctive bars intentionally recognize near-deterministic common
post-processing, not merely two images with similar spectra.

## Development stimulus

No holdout is opened. The texture source is twelve fixed 512-by-512 crops,
six from each already-burned DELIVER-V6 development master:

- `C:\dev\strehl-out\DELIVER-V6\masters\coffee-bean.tiff`
  (`F38CA50ED1A680FA4DBCDD8D0513BE538DD31634B4E89AC6A34885944790A2EC`);
- `C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff`
  (`4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F`).

For each 7032-by-4688 source, crop origins `(x,y)` are
`(512,512)`, `(2500,512)`, `(5000,512)`, `(512,2500)`,
`(2500,2500)`, `(5000,2500)`. Green is IEC-sRGB-decoded, winsorized at
the crop's 0.5th and 99.5th percentiles, mapped once to `[0.10,0.90]`,
and quantized to linear `u16`. The same resulting `A` feeds every arm.
These bytes are development stimuli, never scored axis outcomes.

## Frozen commissioning battery

All listed strengths are run on all twelve crops. “Reliable threshold” means
the weakest listed strength that fires on 12/12 crops and for which every
stronger listed strength also fires on 12/12.

1. **Identity:** exact `A` versus `A`; must fire 0/12.
2. **Movable null disturbance:** add a 32-LSB smooth local disk to `B`; the
   difference statistic must become nonzero while the common-transfer veto
   still fires 0/12.
3. **Gaussian blur:** sigma
   `0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.60, 0.80, 1.00, 1.50,
   2.00, 3.00 px`.
4. **Unsharp mask:** radius `1.00 px`, amount
   `0.001, 0.002, 0.005, 0.010, 0.020, 0.050, 0.100, 0.200,
   0.500, 1.000`.
5. **Scalar gain:** multiplicative delta
   `0.0001, 0.0002, 0.0005, 0.001, 0.002, 0.005, 0.010, 0.020`.
6. **Blur plus gain:** sigma `0.40, 0.80, 1.50 px`, each at gains
   `0.97` and `1.03`.
7. **Interpolation blur:** bilinear shift by `(d,d)` followed by the inverse
   shift, for `d = 0.05, 0.10, 0.20, 0.35, 0.50 px`; and one twofold
   box-down/bilinear-up polyphase resample.

The false-positive battery has 144 fixed-seed (`164`) legitimate differences,
48 each:

- independent heteroscedastic noise realizations of one latent scene;
- local resolved-detail changes under randomized soft masks, with no common
  global transfer;
- spatially varying blur/sharpen renders whose local sign and strength differ.

The observed rate and the exact Clopper-Pearson 95% upper bound will be
reported. No family may be silently removed after outcomes.

## Mandatory planted improvement

For every crop, form:

```text
A = G_0.80(S) + fresh noise A
B = G_0.40(S) + fresh noise B
```

at independent Gaussian noise sigma
`0, 0.25, 0.50, 1, 2, 4, 8, 16` linear-u16 LSB.
This is a pre-noise optical-resolution improvement, not a post-render USM.
Report every fire count. In the zero-noise limit an invertible blur difference
can itself be represented by a sharpening transfer; if the veto cannot
distinguish those cases, that is a required finding, not a threshold-tuning
opportunity.

## Verification and refusal discipline

The commissioning artifact records source hashes, crop hashes, every trial,
aggregate thresholds, and the exact source hash of the instrument. A separate
fail-closed verifier:

- returns `FAIL` rather than throwing on every exception;
- re-derives all aggregate counts from trials;
- checks input and source hashes;
- independently checks the scalar-gain algebra;
- proves both gate directions with source mutations;
- asserts every mutation anchor occurs exactly once before changing it.

No runtime measurement is part of this lane.

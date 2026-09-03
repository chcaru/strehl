# C2 build audit and correction preregistration

**Frozen before the new audit replay, before any corrected render, and before
any Rust implementation.**

Date: 2026-09-02. Lane: `M-PHASE0-LCA`.

The earlier `PREREGISTRATION.md` and report remain the record of the first
phase-0 census. This document governs the owner's new order to audit the prior
finding and, only if it survives, build a reversible prototype.

## 1. Claim identity

The dispatch calls C2 “lateral chromatic aberration,” but the authoritative
proposal's C2 is **longitudinal/axial chromatic z-diversity**: a difference in
R/G/B best-focus position along the bracket. The published 4.22–7.54% red and
3.51–7.13% blue numbers are the gradient energy forfeited by using the
green-selected focus epoch for those channels. They are not a measurement of
radial colour magnification.

This audit will not silently convert one aberration into the other:

* an axial effect moves the through-focus peak and may have a nonzero
  centre-field intercept;
* lateral CA is a radial scale/translation error, must be zero at the optical
  centre, and belongs to the existing spatial optics correction.

## 2. Bias and ways this can be wrong

**Declared bias direction:** the corpus, the owner's desire to stop phase 0,
and the request to change Rust all push toward a false GO. A clean replication
will therefore be treated as suspicious until the cancellation, tone, and
wrong-sign controls fire.

The result is wrong if any of these is true:

1. the published numbers cannot be reproduced from the named RAW stacks;
2. the peak checker and its controls share a defect that cancels;
3. the apparent payoff is an intensity/exposure remap rather than focus;
4. a retraction applies to the axial peak or payoff;
5. a radial scale effect is being mislabeled as an axial epoch shift;
6. the Rust correction changes the default path;
7. zero shift changes output, or the wrong sign improves the registered
   detail statistic.

## 3. Part 1: prior-finding audit

### 3.1 Frozen sources and targets

The legacy implementation is
`experiments/BUILD-CHROMA/src/{common,b0_validate,b1_curves,b2_analyse,b4_controls,b6_discriminate}.py`.
The four inputs are read-only:

| stack | published dR | published dB | published R forfeit | published B forfeit |
|---|---:|---:|---:|---:|
| `lavendar-cpl` | -0.8075 | -0.7185 | 4.22% | 3.51% |
| `coffee-bean` | -0.8100 | -0.4845 | 6.62% | 5.19% |
| `couch-fibers-cpl` | -0.8977 | -0.7124 | 7.36% | 7.06% |
| `bee-2-cpl` | -0.6601 | -0.7540 | 7.54% | 7.13% |

The audit will hash those sources and every RAW inventory. It will regenerate
all four legacy response caches under this lane's `out/`; the missing old
`C:\dev\strehl-out\BUILD-CHROMA` artifacts are not evidence.

### 3.2 Independent statistic

The audit checker will not import the legacy peak or loss checker. From the
regenerated response arrays it will independently:

1. fit the three samples around each discrete maximum with the closed-form
   linear-domain parabola;
2. form `kG=(kG1+kG2)/2`, `dR=kR-kG`, `dB=kB-kG`, and
   `null=kG1-kG2`;
3. reproduce the registered validity/prominence gate;
4. reduce sample points to tile medians before any uncertainty;
5. compute forfeit
   `1 - E_channel(kG)/E_channel(k_channel)`;
6. bootstrap tiles, never pixels or frames.

Legacy reproduction passes only if each dR/dB differs from the published value
by at most 0.05 frame and each forfeit differs by at most 0.25 percentage
point. Every accepted stack must retain negative dR and dB; G1-G2 must satisfy
the existing 0.125-frame null gate.

### 3.3 Commissioning and cancellation controls

Before trusting the audit checker:

* committed external response values and a separately committed predicate
  must recover fixed R/G1/G2/B peaks, signed offsets, and forfeit;
* planted vertex-sign, channel-order, frame-scale, G1-only-reference, and
  loss-sign defects must each go RED;
* a fully present one-frame plant is judged against what this estimator
  actually reads, not merely against the physical dose;
* the old synthetic Gaussian-blur arm is supporting evidence only. It does
  not satisfy the external-predicate requirement by itself;
* the real G1-G2 null and the existing real-data R↔G1 label-swap control are
  audited as data the checker did not generate.

Any untreated failure or plant that does not go RED files **STOP**.

### 3.4 Intensity/tone audit

The legacy measurement is CFA-native, black-subtracted linear RAW, with no
demosaic, colour matrix, white balance, output tone curve, or comparator
render. That provenance must be confirmed from code rather than inferred from
the report.

The replay additionally records, at the same fixed points, local variance and
the affine-invariant statistic

```text
N = Sobel gradient energy / max(local variance, floor).
```

Constant gain and offset plants must leave N's peak and forfeit unchanged to
machine precision. An unnormalised sabotage arm must move. On real data, the
normalised dR/dB must retain the registered negative sign on all accepted
stacks, and pooled normalised R/B forfeit must have a tile-bootstrap lower 95%
bound above zero. Gamma 0.8 and 1.2 are diagnostic on `lavendar-cpl`; each must
retain the sign and at least 75% of the untreated offset magnitude. Failure
means the published “recoverable detail” size is not trusted and files STOP.

### 3.5 Retraction and aberration-type gates

The audit will enumerate every `RETRACT`, `WITHDRAW`, and `AMEND` hit in the
BUILD-CHROMA/M107 dependency chain. Retractions of lateral transfer,
render-space blue harm, focus-dependent epsilon, or bootstrap width are not
silently applied to the axial result; conversely, any retraction of the axial
peak or green-election forfeit files STOP.

For at least `lavendar-cpl` and `coffee-bean`, a tile-bootstrap fit of dR on
field radius must have a negative centre intercept whose 95% interval excludes
zero. The absolute centre value must be at least half the fitted edge value.
That is the discriminator: lateral CA must vanish on axis.

### 3.6 Audit decision

Part 2 is unlocked only if all §§3.1–3.5 pass. The machine-readable audit will
file exactly `GO` or `STOP`. `STOP` ends the lane without touching Rust.

## 4. Part 2: off-by-default prototype

### 4.1 Implementation contract

Flag: **`STREHL_AXIAL_CA_SHIFT`**.

Accepted values are `off`, `0`, `-1`, and `+1`; unset is `off`. Invalid values
are errors. Nonzero is accepted only by the aligned pyramid backend.

For green election epoch `k`:

* `-1` supplies R and B values from epoch `k-1`, while G1/G2, selection luma,
  variance, weights, and denominator remain at `k`;
* `+1` supplies R and B from `k+1` and is the registered wrong-sign control;
* global endpoints clamp to their current R/B;
* an unavailable or alignment-refused neighbour falls back to current R/B and
  is counted;
* chunk workers receive a one-frame temporal halo, but halo green is never
  folded.

The unset/off/zero branch must call the pre-existing path without new
arithmetic or a changed accumulation order. No axial value is added to
`OpticalProfile`; its epsilon fields are spatial lateral-CA quantities.

### 4.2 Frozen real-stack experiment

Input: `D:\personal\macro\lavendar-cpl`, 299 frames. Published offsets
`dR=-0.8075`, `dB=-0.7185` make `-1` the nearest integer prototype.

One release binary and one alignment sidecar produce four camera-linear,
binned pyramid outputs:

1. flag unset;
2. explicit `0`;
3. corrected `-1`;
4. wrong sign `+1`.

All other `STREHL_*` variables, merge options, input order, worker count, and
output options are frozen in the run manifest.

### 4.3 Output statistic and bars

Non-overlapping 256×256 output tiles are selected only from default-green
low-band power, before treatment labels are read. For each channel:

```text
Q = mean FFT power at 0.20..0.35 cycles/pixel
    / mean FFT power at 0.05..0.15 cycles/pixel.
```

The primary delta is the paired tile median of `log(Q_arm/Q_default)`,
converted back to percent, with 10,000 fixed-seed tile bootstraps. This ratio
is invariant to channel gain and DC offset. Raw Sobel-gradient-energy change
is a secondary bridge to the published 4.22–7.54% R and 3.51–7.13% B ranges;
agreement or disagreement is reported without changing the primary metric.

Registered bars:

* unset and explicit zero TIFF SHA-256 must be identical;
* all green samples must be byte-identical across every arm;
* corrected R and B point estimates must be at least +1%, with lower 95%
  bounds above zero;
* wrong-sign R and B upper 95% bounds must be below zero;
* bottom-power flat tiles must stay within ±1%, with intervals containing
  zero;
* dimensions, clipping counts, metadata/provenance, and alignment sidecar are
  unchanged.

If zero is non-null or wrong-sign is not worse in both R and B, the metric is
void and the feature is rejected. There is no parameter tuning after any arm
is scored.

## 5. Product decision

The flag remains off by default regardless of measured gain. A passing
prototype is evidence for a calibrated fractional follow-up, not permission to
bake `-1` into a lens profile: focus-frame units vary with capture step width.
The final report must state the measured delta beside the corpus prediction
and name any discrepancy as the headline result.

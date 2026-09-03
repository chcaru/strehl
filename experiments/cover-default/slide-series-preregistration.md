# COVER slide-series amendment — depth, exposure, and step-width controls

Frozen before aligning, decoding, or rendering any member of the released
high-resolution calibration-slide unit. This amends the completed COVER audit;
it does not rewrite either earlier preregistration.

## Release and scope

Scorecard v1.3 commit `e91ba50e` classifies all six stacks beneath
`D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl`
as **DEVELOPMENT — NOT HOLDOUT** and registers them for flat-path identity,
`cover=scale`, and geometry diagnostics. The six stacks are one 657-frame
session unit. Reading any one therefore spends the whole unit for development.
They may not be used as independent repeat-pair/FRC evidence because IBIS was
on. `D:\personal\macro` remains strictly read-only.

No sharpness, SFR, gradient, band-power, acutance, visual-quality, or timing
statistic is admissible here. The only outcomes are serialized integer
identity and geometry derived from f64 sidecar placements.

| short name | relative directory | N | fixed reference index / sorted file |
| --- | --- | ---: | --- |
| flat-1s | `flat-sw4-cpl\flat-et1s-sw4-cpl` | 60 | 30 / `DSC00046.ARW` |
| flat-2p5s | `flat-sw4-cpl\flat-et2.5s-sw4-cpl` | 61 | 30 / `DSC00050.ARW` |
| flat-6s | `flat-sw4-cpl\flat-et6s-sw4-cpl` | 65 | 32 / `DSC00047.ARW` |
| tilted-sw10 | `tilted-sw10-cpl` | 92 | 46 / `DSC00062.ARW` |
| tilted-sw4 | `tilted-sw4-cpl` | 182 | 91 / `DSC00122.ARW` |
| all-axis-sw10 | `very-tilted-all-axis-sw10-cpl` | 197 | 98 / `DSC00102.ARW` |

The reference is always `floor(N/2)`, matching the merge's reference rule.
No reference may be changed after seeing a solve. The private output root is
`D:\strehl-out\cover-default-slide-v2`; no output is permitted under the
capture tree.

## Frozen alignment procedure

Use the already-proven COVER executable
`D:\strehl-out\cover-default\target\release\strehl.exe`, whose frozen SHA-256
is
`1AC423529D5AAD88B7141801E47DCD612FCA8061558578A88592DB715CE81A0F`
and whose source stamp is `4e5278870a5e`. This keeps the six new values on the
same implementation as the existing N=22 value. Before use, recheck that hash.

For each row, clear inherited `STREHL_*`, cap Cargo/Rayon/OMP/OpenBLAS/MKL/
NumExpr/BLIS/VecLib at eight threads, and run exactly:

```text
strehl.exe align <directory> --reference <fixed-index>
  --spans 1,2,4,8,16,32,64,96,128
  --threads 8 --resampler catmull-rom --out <private-sidecar>
```

The three non-flat directories (`tilted-sw10`, `tilted-sw4`, and
`all-axis-sw10`) additionally receive `--force-tilted`; it is an explicit
acknowledgement that a global similarity is only the model the product will
apply, not physical truth for a tilted plane. There is no retry with changed
spans, reference, kernel, limit, or acceptance threshold.

Before interpreting `k`, each sidecar must:

* identify exactly the sorted source file names, sizes, and count in its
  source stack;
* record the fixed reference and Catmull-Rom;
* contain exactly N placed transforms and zero refused transforms;
* give the reference transform as exact f64 identity;
* give the expected 3516x2344 plane geometry and finite placements.

A failed command or gate is `UNMEASURABLE`, not a value repaired by dropping
frames. Held-out and cycle errors are reported, but no post-result error
threshold changes membership: this audit asks what geometry the product's
registered model applies, not whether that model is physical truth.

Compute `k` from the serialized f64 transform bits with the independently
commissioned COVER geometry implementation, a 3-plane-pixel Catmull-Rom support
margin, and all four plane corners. Human-readable banners are only a
corroboration within `5e-5`. Report `k`, `1/k - 1`, the crop rectangle, and
placed/refused counts for every stack.

## Primary depth prediction

Treat the source's printed anchors as fixed decimal assertions:

```text
N=22:  k=0.9870
N=299: k=0.9321
```

The N=299 capture remains a performance holdout. It is not opened, listed,
hashed, decoded, aligned, or freshly measured; `0.9321` is explicitly a source
assertion. The N=22 diagnostic was already measured, but this registered
ordering uses the source's stated four-decimal anchor, as requested, rather
than silently substituting a more favourable full-precision endpoint.

If "`k` falls as the stack deepens" is true over these eight points, the
full-precision result must satisfy the strict chain:

```text
0.9870 > k60 > k61 > k65 > k92 > k182 > k197 > 0.9321
```

Equality fails. Any reversal fails. Consequently each approximately 60-frame
stack must lie strictly between both documented anchors. Report `ORDERED` only
if every inequality holds, `NOT_ORDERED` with every violating adjacent pair
otherwise, and `UNMEASURABLE` if an alignment gate prevents the test. Even
`ORDERED` establishes an observed cross-capture ordering, not causation by N:
reference gauge, pose, IBIS, exposure, focus range, step width, and tilt remain
possible causes.

## Exposure/SNR falsification control

The three flat-sw4 stacks share target, nominal geometry, ISO, aperture, focal
length, session, and step width, while exposure changes from 1 s through
2.5 s to 6 s. Register "essentially unchanged geometry" as:

```text
max(k60, k61, k65) - min(k60, k61, k65) <= 0.0010
```

Also require the span across the three integer Crop rectangles to be at most
two plane pixels independently for left, right, top, and bottom loss. These
are absolute tolerances fixed before the sidecars exist. Failure means the
measured cover geometry is exposure/solve-sensitive at a material level; it
must not be described as a purely geometric depth law.

For bit identity, render only each flat stack's fixed reference placement
through the *full stack's* covered map, once as Crop and once as Scale. Against
an external rawpy/LibRaw decode of that reference:

* every Crop R/G/B serialized sample must be exact: max 0 DN, RMS 0 DN,
  differing fraction 0, overall and per channel;
* each Scale candidate, compared with the unscaled external decode over the
  preregistered common sensor domain, must differ on more than 1% of samples.

The categorical pattern `Crop exact / Scale changed` must hold at 1 s, 2.5 s,
and 6 s. This is the SNR-invariance predicate for Q1. Scale's DN RMS is reported
but is not required to be exposure-invariant because changing exposure changes
the signal being interpolated.

## Step-width/density control

The primary ordering requires `k92 > k182`. To distinguish another capture
from the mere addition of constraints, form a deterministic 92-placement
subset of the N=182 sidecar:

```text
index(i) = floor(i * 181 / 91 + 0.5), for i=0..91
```

This includes both endpoints and reference index 91. Compute `k182->92` in the
same reference gauge. Removing constraints must give
`k182->92 >= k182`; violation is a geometry-harness failure.

The step-width/density control supports a depth/density interpretation only if

```text
abs(k182->92 - k92) <= 0.0010
```

Otherwise the N=92 versus N=182 comparison is materially capture/step-width
sensitive and cannot isolate frame count, even if its sign agrees with the
primary ordering. Report the full, subset, and cross-capture deltas rather than
averaging them into the primary verdict.

## Q1 candidate and external checker

After this file is committed, add a dedicated experimental Rust example that:

1. loads and identity-checks the full sidecar against the full sorted stack;
2. resolves Crop or Scale with production `cover_or_explain`;
3. extracts the sidecar's registered reference placement;
4. decodes only that reference and applies production
   `warp_frame_in_place`;
5. serializes camera-linear binned RGB16 with the production black, white, WB,
   green, clamp, and integer rules;
6. applies Crop only by integer output addressing, and performs no merge,
   selection, restoration, defect, CA, exposure, matrix, or display transfer.

The checker must be a separate Python implementation using rawpy/LibRaw. It may
not import the Rust candidate, strehl/rawler, the prior external checker, or a
candidate-produced expected array. It copies the mosaic and metadata inside
two independent rawpy contexts, fixes RGGB/black/usable-white/WB arithmetic
before comparison, independently derives the supported Crop rectangle from
the sidecar, and refuses rather than adapting any representation mismatch.

Commission before reading a real comparison:

* fixed literal RGGB encoder fixtures;
* candidate-side centre-green XOR `0x8000` detected as one 32768-DN change;
* XOR `0x0001` improves max and RMS toward zero;
* restoration returns every statistic to exact zero;
* a one-quad Crop-origin mutation differs on more than 1% and correcting only
  the origin improves every statistic;
* Scale is the real-render positive arm and must exceed 1% different.

Any nonzero external-to-Crop difference fails identity. No offset, gain,
channel permutation, crop, threshold, or overlap may be fitted after viewing a
candidate.

## Decision rule

Report the strict eight-point result, SNR control, step-width control, and
three external Q1 results separately. A control failure cannot be averaged
away by another pass.

No outcome in this amendment flips the product default. Crop already failed
the registered border gate at a 256 px safe inset and 64.6047% retained area.
This slide series can confirm or refute the documented depth and identity
claims; it cannot repair that independent shipping blocker.

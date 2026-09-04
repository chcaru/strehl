# COVER slide-series amendment — M8 source-hull comparison

Frozen before any full-stack Crop M8-R trace, Crop M8-O comparison, corrected
Scale rerun, observational-equivalence render, or result from this amendment
exists. This extends `slide-series-preregistration.md`; it changes none of that
file's geometry, reference-gauge, Q1, SNR, step-width, or default-decision
outcomes.

## Authority and prior disclosure

The authority is scorecard v1.4 commit
`64d9d675a48028fde617d0cb5048fc6ea49d7722`, M8 lines 719–788. Current
scorecard v1.7 retains the same computation, bars, and controls at lines
819–888. M8 is an invented-value/source-hull certificate. It is not a
resolution, sharpness, acuity, SFR, visual-quality, or SOTA statistic.

Commit `76b3d9cc8b5185735d6c19d4339ce74d29e333e2` already discloses
Scale-only diagnostic M8-R/M8-O results plus a one-frame Crop identity arm.
Those values are known before this amendment. They are not admitted as the
registered comparison because the checker, runner, plants, and results first
appeared together; M8-O was not commissioned; source/binary/run identity was
incomplete; no trace-on/off output hash was taken; M8-O coordinates lacked a
bound frame; and full-stack Crop was never run. This amendment is a
preregistered rerun, not a blind replication. Thresholds come only from the
scorecard and cannot move in response to either the old or new values.

## Capture and placement freeze

The six-stack calibration-slide session is already spent development evidence,
not a holdout. This amendment initially uses the flat 1 s stack and may
continue to the 2.5 s and 6 s stacks only under the stopping rule below.
`D:\personal\macro` remains strictly read-only. No holdout may be listed,
hashed, decoded, or rendered.

| case | source directory below `high-res-calibration-slide-cpl\flat-sw4-cpl` | N | reference | released sidecar | sidecar SHA-256 | Crop `(x,y,w,h)` |
| --- | --- | ---: | ---: | --- | --- | --- |
| flat-1s | `flat-et1s-sw4-cpl` | 60 | 30 | `flat-1s.warpmap.txt` | `862C6FD8E1956FDD53F527A12809B3079226334265EDADFF8AA1F0EA3B9B828C` | `25,17,3466,2310` |
| flat-2p5s | `flat-et2.5s-sw4-cpl` | 61 | 30 | `flat-2p5s.warpmap.txt` | `0C2CF172F7577189D2EE6F19F281D1A5BA821E7EC4A2F4D13F0BB12B87D4C638` | `23,16,3470,2312` |
| flat-6s | `flat-et6s-sw4-cpl` | 65 | 32 | `flat-6s.warpmap.txt` | `60A33EA0513E6408313EAA5698106FEC9B23FD6E8E325C246141C1905F2427F3` | `25,17,3466,2310` |

The source inventories must reproduce the sidecar FNV-1a identities and a
committed pre-run manifest of every ARW name, size, UTC timestamp, SHA-256, and
EXIF digest. Reuse these sidecars byte-for-byte. Do not align again, change a
reference, drop a frame, round a placement, disable the active per-channel CA
profile, or substitute identity for the full-stack reference. The strict
slide-series result remains `UNMEASURABLE_REFERENCE_NOT_BIT_IDENTITY`; M8 is a
separately labelled actual-product diagnostic that consumes each serialized
placement unchanged. Its one-frame identity null uses a separately generated,
exact-identity, copied-reference sidecar and disables CA.

## Product and trace freeze

Build uninstrumented and instrumented binaries from one committed source
archive, never the live dirty worktree. Before rendering, commit a run manifest
containing the archive commit, source-tree and lockfile hashes, tool hashes,
binary hashes, Rust/Python/NumPy/tifffile/rawpy/LibRaw versions, OS, complete
environment, input manifest hash, sidecar hashes, output contract, and exact
commands. Cap Cargo, Rayon, OMP, OpenBLAS, MKL, NumExpr, BLIS, and VecLib at
eight; use one pyramid worker so trace-state writes are serialized.

Every full arm is the ordinary pyramid product path with explicit full-resolution
gather, Catmull-Rom, released sidecar, camera-linear binned RGB16, cover mode,
defect correction off, restoration off, auto-exposure off, and default active
CA. The value-only hook runs immediately after `sample_checked` fills
`scratch.dst` and before inverse WB, pedestal restoration, raw-u16 rounding or
clamp, merge, output clamp, and serialization. It emits:

* exact effective f64 transform bits and CFA site;
* the immutable linear `R`, `G`, or `B` source plane used by that gather;
* the gathered `scratch.dst` f32 bits and finite/invalid pattern;
* frame path/index, geometry, range, and site gain.

It emits no support indices, hull, tolerance, contributor/election mask, or
pass flag. Duplicate frame/site traces hard-fail; no marker may silently hide a
second value. Retain content-hashed trace blocks until independent
adjudication finishes.

The same source/sidecar must produce byte-identical TIFFs from the
uninstrumented binary, instrumented binary with tracing off, and instrumented
binary with tracing on. Prove this first on the one-frame identity arm and then
on each measured full arm before opening its hull result. Any mismatch
invalidates that arm.

## M8-R primary

For each geometrically valid frame, full internal plane coordinate, and CFA
site `R/G1/G2/B`, independently reconstruct

```text
(sx,sy) = 2 * T_site(x + dx/2, y + dy/2)
```

from the emitted f64 transform. Reimplement Catmull-Rom validity, coordinate
clamping, floor, and the exact `[-1,0,1,2]^2` discrete support without calling
or importing Strehl. In the same white-balanced, black-subtracted source-plane
units as `scratch.dst`, set

```text
lo_k = min(support_16)
hi_k = max(support_16)
tau_R = 8 * ULP_f32(max(1, abs(lo_k), abs(hi_k)))
```

where the argument, next representable value toward positive infinity,
subtraction, and multiplication are binary32 operations. A violation is
`r_k < lo_k-tau_R` or `r_k > hi_k+tau_R`.

The scorecard census is every independently valid full-plane gather before
Crop addressing. Also report a delivered-window subset for Crop by mapping
local output `(u,v)` to full `(u+rect.x,v+rect.y)`. Scale's two domains are
identical. Neither denominator may use Strehl's coverage mask except as a
required zero-mismatch cross-check.

The bar is an integer count of exactly zero. A fraction formatted `0.0000%`
with any violation fails.

## M8-O final output

Read the actual camera-linear RGB16 TIFF. For Crop, require the frozen dimensions
and map every local coordinate to the frozen full-plane origin; do not infer or
fit an origin from pixels. Transform each valid source interval and `tau_R`
with the positive factor

```text
output_gain[channel] / frame_site_gain / (white - black)
```

For final R and B, take the minimum lower and maximum upper endpoint across all
valid frames. Production merges G1 and G2 independently and averages them only
at output, so freeze the final green interval as:

```text
lo_G = 0.5 * (min_k lo_k,G1 + min_j lo_j,G2)
hi_G = 0.5 * (max_k hi_k,G1 + max_j hi_j,G2)
```

This permits different G1/G2 contributor frames. The green tolerance is the
larger of the maximum transformed G1 and G2 `tau_R`; R/B use their maximum
transformed `tau_R`. Then add exactly `0.5/65535` for final serialization.
There is no tolerance for inverse WB, pedestal restoration, intermediate raw
rounding/clamp, merge, black clamp, final upper clamp, noise, or scene content.

For every endpoint and maximum tolerance, retain the lowest sorted frame index
on an exact tie. An M8-O violation record names the bound frame/site and
tolerance frame/site; green names both independently selected bound frames.
Final clamping can erase M8-O evidence, so M8-O cannot substitute for M8-R.
The M8-O bar is also an integer count of exactly zero.

## Complete coordinate evidence

For every M8-R violation, persist capture, mode, sidecar hash, frame index and
source hash, CFA site/channel, full-plane coordinate, Crop-local coordinate or
an outside-delivery marker, gathered value, lower/upper bound, tolerance,
direction, and signed excess. For every M8-O violation, persist capture, mode,
sidecar hash, local and full coordinates, RGB channel, encoded and normalized
value, lower/upper bound, direction, signed excess, bound witness frame/site(s),
and tolerance witness frame/site. Manifests remain below the private output
root and are indexed by relative path, row count, byte count, and SHA-256.
The committed result contains the complete index, never only an aggregate.

## Commissioning and falsification before real output

All controls run before a real trace:

1. A frozen fractional hard step must make Catmull-Rom violate M8-R in both
   directions; copy and fractional convex-bilinear fixtures must each give
   zero.
2. Literal samples at `lo-32*tau` and `hi+32*tau` must both fire. Replacing
   them with `±16*tau` is the improvement arm and must reduce maximum excess;
   restoration must return count, maximum, and manifests to exact zero.
3. Boundary, scale, rotation, translation, both-axis, CFA-site, wrong-kernel,
   wrong-transform-bit, wrong-source-plane, finite/NaN-validity, missing,
   duplicate, and concurrent-state plants must all be detected or refused.
4. M8-O fixtures must commission multiframe endpoint/tolerance witnesses,
   independent G1/G2 green extrema, intermediate lower/upper clamp, exact
   `0.5/65535` serialization boundaries, complete coordinates, and both
   violation directions. A `±32*tau` final plant, `±16*tau` improvement, and
   restoration must move in that order.
5. A wrong Crop origin and wrong Crop dimensions must fail; the exact origin
   must restore zero. A final-clamp fixture must make M8-R red while M8-O is
   green, proving that M8-O alone cannot acquit the resampler.
6. The copied-reference Crop/identity arm must have zero M8-R violations,
   zero exact-copy differences, and match two independent rawpy/LibRaw
   decodes.

Controls are read against these fixed predicates, not values computed by the
producer. A second verifier may import neither the primary checker nor Strehl
and must independently recover the fixture outcomes and real counts from the
retained value-only traces.

## Cell order, stopping, and interpretation

Run flat-1s Scale and Crop to completion first, including both censuses,
complete manifests, and output-transparency hashes.

* If Crop has any M8-R or M8-O violation, the exact-zero Crop hypothesis is
  refuted. Stop before 2.5 s and 6 s: one complete counterexample is decisive
  for a universal zero bar, and no cross-exposure pass may be claimed.
* If Crop is exact-zero on both censuses, run the 2.5 s pair, then the 6 s
  pair. A positive Crop pass requires exhaustive zero counts in all three
  stacks; there is no early positive stop.
* Always finish and persist every coordinate for a started cell. Never stop at
  the first violating pixel.

Classify each completed pair only as:

| Scale | Crop | category |
| --- | --- | --- |
| fail | pass | `IMPROVED_TO_PASS` |
| pass | pass | `BOTH_PASS` |
| fail | fail | `BOTH_FAIL` |
| pass | fail | `REGRESSED` |

A smaller nonzero fraction is not an improvement on this axis. Report M8-R and
M8-O separately, per mode, without averaging. A Scale failure plus Crop pass
would establish only that Crop satisfies this source-hull invariant while
Scale does not. It would not establish resolution, sharpness, overall quality,
SOTA, or permission to ignore Crop's independent 256 px pyramid-border
blocker. A null or negative result is final and equally admissible.

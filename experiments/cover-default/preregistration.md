# Cover-default decision preregistration

Frozen before this lane runs any comparison or border-profile command.  The
author has read the prior BUILD-CROP/M95/M104/M112 reports, so this is not a
blind registration.  It prevents those priors, or a pleasing new number, from
moving the predicates.

## Scope and evidence

This lane asks only questions with exact or geometric answers:

1. whether an identity placement is copied under `crop` and resampled under
   `scale`;
2. the fitted coverage factor `k` and its implied `1/k - 1`;
3. how far the pyramid transports black-fill boundary contamination into the
   emitted crop; and
4. whether those facts license changing the default.

No gradient, SFR, acutance, band-power, ordinal-detail, or visual sharpness
statistic is admissible here.

The scorecard classifies `109MSDCF`, `113MSDCF`, `coffee-bubbles`, and
`flat-on-ruler-cpl` as non-holdout diagnostic/development inputs.  Only those
captures may be decoded.  `D:\personal\macro` is read-only.  The 299-frame
`bee-1-cpl` capture is `HOLDOUT — PERFORMANCE` and will not be decoded or used
to make this decision.  Existing 299-frame claims may be audited as published
provenance, but they are not a fresh measured arm.

All Rust/Rayon and numerical-library thread counts are capped at 8.  Every
render clears inherited `STREHL_*`, pins `STREHL_WARPMAP` outside the capture
tree, and records all values it then sets.

## Harness commissioning

`audit.py commission` must pass before any result is read.

* **Known defect:** alter exactly one value of a fixed 64x48x3 integer array by
  +4096.  The comparator must report max absolute difference 4096, RMS
  `4096/sqrt(64*48*3)`, and differing fraction `1/(64*48*3)`.
* **Improvement arm:** reduce that defect to +1024, then restore it.  Max and
  RMS must move toward zero in that order and the restored arm must be exactly
  zero.  This prevents a non-negative statistic from passing only because it
  detects worsening.
* **Origin plant:** extract a fixed integer window from a larger array.  The
  correct origin must be exact; each one-pixel origin mutation must differ.
  Returning from the mutation to the true origin is a second improvement arm.
* **Border plant:** multiply a known outer 16-pixel ring by exactly 1.02.  The
  profile must localise the change to that ring and return safe inset 16 at a
  fixed 0.1% threshold.  A 1.0005 arm must improve the safe inset to the
  minimum admissible 8 pixels, and the unplanted arm must remain there.
* **Geometry plant:** for an identity similarity on 3516x2344 with a 3-pixel
  support margin, the independent bisection must equal the closed-form
  four-edge solution.  Reducing the externally specified margin to zero must
  improve `k` to exactly 1.

These truths come from the planted arrays and closed-form geometry, not from a
value computed by strehl.

## Q1 predicates

Use one copied frame from `109MSDCF`, an explicit one-frame sidecar, pyramid
backend, 7 bands, Catmull-Rom, full-resolution gather on, defect correction
off, lateral-CA correction off, and no display encoding.

* The alignment-off direct render, the aligned `STREHL_COVER=0` render at the
  crop window, and `--cover crop` must agree bit-for-bit: max=0 DN, RMS=0 DN,
  differing fraction=0.
* A deliberate one-pixel crop-origin mutation must differ, then the correct
  origin must improve all three statistics back to zero.
* `--cover scale` must report `k < 1` and differ from the direct render on more
  than 1% of serialized samples.  Its actual max, RMS, and differing fraction
  are reported without a quality interpretation.

Failure of either exact-copy predicate refutes the implementation claim and
stops the default decision.

## Q2 predicates

`k` is independently recomputed from serialized f64 placement bit patterns and
the four plane corners.  The port is admitted only if:

* its identity-map commission matches the closed form within `2e-15`; and
* on each freshly rendered diagnostic stack it agrees with strehl's four-place
  coverage banner within `5e-5`.

Report every available safe stack/prefix as `(frames, k, 1/k-1)`.  The
within-`113MSDCF` depth claim passes only if the preregistered 8, 16, 32, and
63-frame maps have non-increasing `k` and the 63-frame implied upsample exceeds
the 8-frame value.  The published `0.9870 @ 22` claim passes at the banner
precision.  The published `0.9321 @ 299` claim is reported as either reproduced
from admissible evidence, contradicted, or not freshly verified; it is never
silently substituted from prose.

## Q3 predicates

On `109MSDCF` and `flat-on-ruler-cpl`, render `--cover crop` at pyramid bands 2
and 7 from the same explicit sidecar.  Also render the corresponding scale
controls.  For each pair, in fixed annuli from the emitted border, compute

`E(d) = (mean_G(bands7,d) / mean_G(bands2,d)) / R_deep - 1`,

where `R_deep` is the same ratio over pixels at least 768 pixels from every
border.  Bands 2 is an external treatment arm, not a producer-reported mask;
its boundary reach is at most 8 pixels under the fixed filter support.

The **safe inset** is the smallest registered annulus boundary at or beyond
8 pixels for which `abs(E) <= 0.001` in that and every deeper annulus.  If no
such boundary exists, the safe inset is unbounded by the image.  The 7-band
profile is evidence only if its reach is greater than the 2-band/improved arm
and the commissioned 2% plant is recovered.

## Default decision

Changing the default is licensed only if all of the following hold:

1. Q1 exact copy passes and Scale measurably resamples.
2. The outer 0-16 crop ring is within 0.1% of the 2-band boundary-local control
   on every tested real stack.
3. The safe inset is at most 128 pixels (one default coarsest-band support) on
   every tested stack.
4. After that inset, every tested crop retains at least 80% of the original
   pixels.
5. Byte-freeze and golden fixtures either explicitly pin `scale` or are
   deliberately rebaselined with full invocation provenance.

Any failed item keeps `Scale` as default.  In particular, exact identity is
necessary but cannot overrule a contaminated delivered border.

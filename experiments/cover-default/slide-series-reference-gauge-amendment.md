# COVER slide-series preflight amendment — reference gauge

Frozen after the first real sidecar failed the exact-reference loader gate, but
before any slide-series `k`, crop rectangle, rescale magnitude, RAW decode,
candidate render, or external pixel comparison was exposed.

The original strict result is preserved: under
`slide-series-preregistration.md`, the six-point series is
`UNMEASURABLE`. This amendment licenses a separately labelled
**actual-product diagnostic**; it does not rewrite that outcome or classify
the observed difference as harmless roundoff.

## Preflight observation

The registered `flat-1s` solve placed all 60 frames, but serialized its
reference as:

```text
a.re 3fefffffffffffff
a.im 3be0000000000000
b.re bc80000000000000
b.im 3cb0000000000000
```

rather than exact `(1,+0,+0,+0)`. The geometry adjudicator stopped before
calling its cover solver and printed no `k`. No other sidecar reference bits
were inspected before freezing this amendment.

This is not permission to replace the transform with identity. Production
`cover_or_explain` consumes the serialized transform as written, so both the
coverage diagnostic and Q1 must do the same.

## No fitted admission bound

For a plane corner `z`, let

```text
d(z) = |((a - 1)*z + b)|
```

in plane pixels, using the serialized f64 values and the same
cancellation-resistant expression as the alignment source. Report the maximum
over all four centred `3516x2344` plane corners.

There is deliberately **no tolerance gate** on that displacement. Choosing one
after seeing the failed identity bits would make the diagnostic depend on a
post-result threshold. The actual-product arm instead asks what the shipping
coverage code does with the sidecar it really wrote. It admits any placed,
finite reference transform already admitted by the original all-placement
gate and keeps that transform unchanged. A visibly or numerically material
reference displacement is therefore an outcome to report, not a reason to
move a threshold.

Report for every map:

* the four exact reference f64 bit patterns;
* maximum reference-corner displacement;
* whether exact identity passed.

## Diagnostic execution

Add an explicit `measure-product` mode to the geometry adjudicator. It must
retain all other frozen gates and predicates, use every placement exactly as
serialized, and report both:

* `strict_preregistered_status = UNMEASURABLE_REFERENCE_NOT_BIT_IDENTITY`;
* the separately labelled actual-product ordering/SNR/step-width results.

The Rust reference renderer and external checker must use the actual reference
transform. They may not canonicalize, rebase, round, or overwrite it. Q1
therefore tests whether the real non-bit-identity placement still serializes as
an exact copy under Crop. Any nonzero external Crop difference remains a
failure, and a material reference displacement would make the documentation's
identity premise false even before pixels are compared.

No alignment is rerun and no spans, references, memberships, resampler,
sidecar, threshold, or source anchor changes. The 299-frame capture remains
untouched. The existing 256 px Crop-border blocker remains binding regardless
of the diagnostic result.

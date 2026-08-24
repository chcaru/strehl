# M82 — pre-registration amendment: matched bee ISO pair

**Frozen at 2026-08-24T00:24:59-07:00, before M82 runs ExifTool on the
current `bee-2-cpl` / `bee-3-cpl` directories, decodes their first frames for
cross-capture registration, or computes their cross-capture admission-map
agreement.**

This amendment does not alter the original five-stack bar, the wrapped-text
bar, the first bee amendment, or any result already committed from them. It
adds one first-class matched-content / different-ISO control. The original
M82 verdict stands independently.

## I0. Why this arm exists, and what is not blind

**ARGUED question.** `bee-2-cpl` (ISO 400) and `bee-3-cpl` (ISO 100) are
reported to hold subject, angle, focus start, aperture, and frame count fixed
while changing ISO and exposure. If that premise survives source checks, the
pair asks a narrower question than the bee triple: after solving each stack
for the same requested model-predicted sigma gain, does the merge admit the
same parts of the same focus sweep?

**MEASURED prior art, not new M82 evidence.** M61 fact 31 already records the
owner's confirmation that this is the one genuine matched pair in the bee /
wrapped-text group: same subject, angle, and depth. M61 fact 17 says framing
held but lighting stability remained circumstantial. M61 also already tested
conversion gain on this pair: fact 31's green gain ratio is 4.0486 against the
ISO ratio 4.000, a +1.22% difference. The claim that no prior milestone could
separate content from gain mode is therefore false at source. This amendment
tests the merge's spatial admission behaviour, which M61 did not.

**MEASURED existing M82 outputs, fully visible before this amendment.** No
threshold below may be represented as blind for these aggregates:

| request | `bee-2` gate / achieved gain | `bee-3` gate / achieved gain | gate ratio `bee-3/bee-2` |
| --- | --- | --- | ---: |
| 0.90 | 0.268920 / 0.9021 | 0.300538 / 0.9037 | 1.118× |
| 0.70 | 1.124448 / 0.6997 | 1.514691 / 0.6987 | 1.347× |
| 0.50 | 4.855507 / 0.5022 | 9.279772 / 0.5019 | 1.911× |

At the primary 0.70 request, M82 has also already seen the fixed detail ROI's
mean admitted count and singleton exposure: 1.202709 / 81.6422% for `bee-2`
and 1.157139 / 85.3031% for `bee-3`. Its even/odd half aggregates are likewise
visible: means 1.068222 / 1.064751 and singleton exposures 93.4948% / 93.8244%
for `bee-2`; means 1.046432 / 1.048534 and singleton exposures
95.5147% / 95.3312% for `bee-3`. The spatial maps, their cross-capture
agreement, and their even/odd spatial repeatability have not been computed.

The M57 prices are also already visible and both abstain at the primary
request: −0.02862 ± 0.03285 px and −0.01658 ± 0.04954 px, both below the
frozen 0.343 px null. This arm cannot turn those numerical centres into
sharpness evidence.

**ARGUED correction to the proposed inference.** Raw gate equality is not a
valid co-location test. M82's reported coordinate is
`mean_pixels(1 / sqrt(n_eff))`: the absolute sensor sigma cancels after the
admission count is known. Before admission, however, `FocusField` divides the
same DN-domain focus contrast by predicted sigma. On matched DN content the
lower-noise ISO-100 field should therefore be taller in sigma units and should
need a *larger*, not equal, raw gate to admit the same physical neighbours.
The already-visible gate mismatch cannot by itself diagnose a bad noise
model. Spatial admission agreement at matched outcome is the new observable.

## I1. EXIF identity and focus-schedule precondition

**ARGUED source method.** Run installed ExifTool 13.58 on all three current bee
directories with the requested command:

```
exiftool -T -ISO -FNumber -FocusDistance2 -r -ext ARW <dir>
```

Also run a filename-bearing census with `-FileName -ExposureTime` added, so
rows can be sorted and paired rather than relying on traversal order. Preserve
the raw stdout, stderr, executable path, version, command, and a reduced JSON.
ExifTool is executed only; its GPL source is not read or incorporated.

**ARGUED pass rule.** The matched-pair premise passes this precondition only if:

1. each of `bee-2-cpl` and `bee-3-cpl` yields exactly 299 readable rows;
2. ISO and f-number are internally constant at 400 / 5.6 and 100 / 5.6;
3. each has exactly nine distinct `FocusDistance2` values;
4. the filename-sorted 299-value focus-distance sequences are exactly equal,
   including the first value; and
5. `ISO × exposure_seconds` agrees within 1%.

The owner's values are predictions, not evidence. Any failed item downgrades
the pair to `EXIF PREMISE NOT ESTABLISHED`; all measurements are still
reported, but no matched-schedule inference is made. `bee-1-cpl` is censused
for context only and cannot rescue or fail this pair.

## I2. First-frame framing and content precondition

**ARGUED image method.** Decode filename-sorted frame 0 through rawpy. Build
black-subtracted averaged-green images
`0.5 * (max(G1-black, 0) + max(G2-black, 0))`. Crop the final two columns so
the green plane is divisible by four, then 4×4 block-average. Estimate the
translation that maps `bee-3` into `bee-2` by phase correlation on
Gaussian-high-passed (`sigma=2` blocks), Hann-windowed images, then refine by
direct Pearson correlation over the surrounding ±2 block shifts. No rotation,
scale, or non-rigid warp is fitted: a pair that needs one is not the promised
fixed framing.

At the selected translation, report:

- translation in green-plane pixels;
- raw-intensity Pearson correlation after overlap cropping;
- high-pass Pearson correlation;
- affine-photometric residual RMS divided by `bee-2`'s spatial SD; and
- the within-frame G1/G2 high-pass correlations as decode sanity checks.

**ARGUED framing bar.** Framing/content passes only if the absolute translation
is at most 16 green-plane pixels on each axis, raw correlation is at least
0.99, high-pass correlation is at least 0.90, affine residual is at most 0.15
spatial SD, and both G1/G2 sanity correlations are at least 0.95. These high
lines are appropriate because the claimed control holds content fixed; a
merely recognisable bee is insufficient.

**ARGUED destructive control.** Before accepting the real result, reverse the
order of a deterministic 8×8 tile partition of the `bee-3` block image and
run the identical registration and pass rule. Read back the mutated array and
require the framing bar to fail. Restore from the untouched decode and verify
its byte hash. If the mutation passes, the registration instrument is
non-discriminating and the pair is `FRAMING NOT ESTABLISHED`.

## I3. Shipped noise-profile source audit

**ARGUED audit, not a new fit.** Record the exact `CameraProfile` branches used
at ISO 100 and 400 and trace each to M48, M61, and M71. The audit must
distinguish an exact per-ISO measured row from a relation or multi-ISO fit.
It must not call a value “measured at this ISO” merely because a
measurement-backed formula returns a number there.

This source audit is a precondition on attribution, not on running the map:

- if both gain and read-noise terms at both ISOs have direct measurements
  consistent with the shipped prediction to 10%, call the denominator
  `MEASUREMENT-BACKED`;
- otherwise call it `APPROXIMATE` and do not attribute a map failure uniquely
  to content or to the noise model.

Known omissions such as PRNU, spatial correlation, and per-pixel sigma
structure remain limitations even if the scalar terms pass.

## I4. Spatial admission-map co-location arm

**ARGUED data and operator.** Reuse the exact committed gates above and the
frozen 512² detail ROI `(1824,544,512,512)`. Decode all 299 frames, reproduce
the shipped averaged-green focus field and 17×17 regularisation independently,
and retain the `n_eff` map rather than only its mean. Compare `bee-2` with
`bee-3` after applying I2's rounded green-plane translation and cropping a
32-pixel guard plus the shifted edge. The winner is always admitted, exactly
as shipped.

For each request report:

1. Spearman correlation of `log1p(n_eff)` maps;
2. exact-count agreement;
3. mean absolute count difference;
4. singleton-mask symmetric-difference fraction and Jaccard index; and
5. each map's mean, quantiles, and singleton exposure.

The committed primary request remains 0.70. Requests 0.90 and 0.50 are curve
context and cannot rescue it.

**ARGUED repeatability baseline.** Within each stack, independently elect and
count the filename-even and filename-odd halves at the same full-stack gate.
Compute the same spatial Spearman and singleton symmetric difference. This is
not an achieved-gain comparison; it is the available repeatability ceiling
for the spatial pattern, with equal-sized interleaved focus sweeps.

**ARGUED capability rule.** The map instrument is capable only if both
within-stack primary Spearman correlations are at least 0.50.

**ARGUED co-location bar, frozen before the maps exist.** At request 0.70:

- cross-ISO Spearman must be at least 0.50 and no more than 0.10 below the
  smaller of the two within-stack correlations; and
- cross-ISO singleton symmetric difference must be no more than 0.10 above
  the larger of the two within-stack differences.

Passing both gives `ADMISSION CO-LOCATED` on this pair. With a capable
instrument, failing either gives `ADMISSION NOT CO-LOCATED`. An incapable
instrument or failed I1/I2 precondition gives `NOT ESTABLISHED`, not a
numerical sign.

**ARGUED map mutation control.** Reverse the order of a deterministic 8×8 tile
partition of the `bee-3` primary count map, verify the changed bytes by hash,
and apply the same bar. The planted map must fail the bar and its Spearman
must fall at least 0.20 below the real cross-ISO value. Byte-restore and verify
the original hash. Failure of the plant makes the arm `NOT ESTABLISHED`.

The admission comparison itself must also expose a self-test pinned to
`gap <= tolerance`. Before measurement, a byte-level source mutation changes
that comparison to `gap >= tolerance`; read-back must see the planted bytes,
the self-test must exit nonzero, and restoration must reproduce the original
hash.

## I5. Decision and attribution

**ARGUED decision.** This arm can establish or refute admission-map
co-location on one matched ISO pair. It cannot establish the portable
sharpness price unless both already-frozen M57 price rows are readable; they
are not. Therefore even `ADMISSION CO-LOCATED` leaves M82's top-level
`NO SHIP / NOT ESTABLISHED` verdict unchanged.

If admission does not co-locate while I1/I2 pass, report the mismatch and the
profile audit separately. Do **not** call it uniquely a noise-model defect:
lighting stability, focus-actuator repeatability, missing spatial noise terms,
and the transferred ROI remain rival mechanisms. Conversely, successful
co-location is evidence that the current scalar noise denomination absorbs
the ISO change for this merge operator; it is not proof that the whole sensor
model is exact.


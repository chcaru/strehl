# M136 — M8-O representable-domain ruling

## Ruling

**VERIFIED — RULING:** Repairing M8-O is legitimate, not goalpost-moving, but
the repair should project the independently reconstructed source hull through
the mandatory output representation while retaining every coordinate in the
denominator, rather than delete rail coordinates from the census.

**VERIFIED — headline answers:**

| Question | Ruling |
|---|---|
| Meaning of `full_rail_below_hull` | The proposed reading is correct. It is an encoded `65535` sample already classified as a lower violation, with `lo > 1 + tolerance`. |
| Achievability as written | Impossible for the 977,684 bilinear coordinates while output remains the required `u16/65535` domain and the current unprojected hull is used. |
| Goalposts | Legitimate construct repair, provided the denominator is unchanged, unavoidable rails remain separately reported, in-range plants remain red, and M8-R remains mandatory. |
| Ownership of rails | Not current M6: its denominator requires another aligned input in `[0.20,0.95]`. Keep a mandatory M8-adjacent headroom census and, if it is to gate quality, specify a new prospective M6 headroom submetric. |
| Rail-only residue | Exactly `2413/74173536`, or approximately `0.0032531818356347471421613228739694976925463011497793%`. |
| Correct target | Still exactly zero, after the hull includes the actual deterministic intermediate quantizer and final representable-domain projection. |
| Contradiction | The 2,413 nonrail coordinates are not established genuine invention: all fit inside the omitted intermediate-`u16` quantization bound. |

## Scope and evidence

**VERIFIED:** This was a read-only reanalysis of the frozen M8 artifacts. No
stacking campaign or benchmark was run. `experiments/M136-m8o-bar/analyze.py`
hashes every source it reads before and after analysis and asserts equality;
the hashes and results are in `experiments/M136-m8o-bar/analysis.json`.

**VERIFIED:** The governing format and transfer are not optional:

> Each program must emit a native-size 16-bit linear TIFF. No output may be histogram
> matched, auto-exposed, white-balanced, sharpened, denoised, resized, or tone-mapped
> after stacking. Numerical metrics run in linear light before any display conversion.
(`docs/proposals/2026-09-sota-scorecard.md:175-177`)

**VERIFIED:** M8's stated construct is invented values, not headroom:

> **What it measures and why.** A merge or restoration stage can ring beyond any
> observed linear sample. The proposal explicitly requires a per-file hull census of
> `0.0000%` or coordinates for every exception
(`docs/proposals/2026-09-sota-scorecard.md:821-823`)

### Prior art and result versioning

**VERIFIED:** The retained rule-40 search is
`experiments/M136-m8o-bar/prior-art.txt`. It surfaced the pre-existing
`M8-overshoot.md` and `M-FLATNULL.md` as headline matches, and
`M133-blocker-audit.md`, `F-camera-lens-optics.md`, `REVIEW.md`,
`M8-COMPARATIVE.md`, `M101-defect.md`, and `ORCH-veiling.md` as mentions.
The rerun also finds this report because it was retained after drafting.

**VERIFIED:** M-FLATNULL had already isolated the same mechanism on its clean
inset:

> **Final verdict: the registered noise-rise failure was not observed, but M8-O
> is not commissioned as a general comparative invention/detail axis.** It is
> sensitive to a downstream unsharp mask, yet it reads materially nonzero on
> every flat-target arm. On the clean 6-second arm, 97.827% of inset violations
> are a representation false positive: the output is encoded at 65535 while the
> entire independently reconstructed normalized source hull lies above
> `1+tolerance`. The census is literally detecting an outside-hull value, but
> the cause is output clamping rather than invented detail.
(`docs/research/M-FLATNULL.md:3-10`)

**VERIFIED:** That report also imposed the correct governance boundary:

> **Do not use current M8-O as the surviving general comparative detail axis.**
> A rail-aware hull, pre-clamp output census, or frozen rail exclusion would be a
> new statistic, not a reinterpretation of this one; it requires a new
> preregistration and full commissioning. This lane made none of those changes.
(`docs/research/M-FLATNULL.md:178-181`)

**VERIFIED:** This ruling agrees. The recorded v1.7 M8-O result remains a FAIL
under the instrument that produced it; it must not be retroactively relabelled.
The replacement is a versioned successor definition whose formal result is
`UNMEASURED` until independently commissioned and run. Calling that successor
a legitimate repair concerns construct validity, not historical scorekeeping.

## 1. What `full_rail_below_hull` actually means

**VERIFIED:** The checker requires a `uint16` TIFF, converts each encoded code
to `O = encoded/65535`, adds the mapped M8-R tolerance and final half-code
tolerance, and marks a lower violation when `O < lo - tolerance`:

>     image = np.asarray(tifffile.imread(tiff_path))
>     expected = (meta["height"], meta["width"], 3)
>     if image.shape != expected or image.dtype != np.uint16:
>         raise ValueError(
>             f"{tiff_path}: expected uint16 {expected}, got {image.dtype} {image.shape}"
>         )
(`experiments/M8-overshoot/checker.py:550-555`)

>             encoded = np.asarray(image[y0:y1, :, channel], dtype=np.uint16)
>             values = encoded.astype(np.float64) / 65535.0
>             tolerance = tau + U16_QUANT_TOL
>             lower = bracketed & (values < lo - tolerance)
>             upper = bracketed & (values > hi + tolerance)
(`experiments/M8-overshoot/checker.py:577-581`)

**VERIFIED:** The violation manifest records direction `-1` for a lower
violation:

>     mask = lower | upper
>     yy, xx = np.nonzero(mask)
>     values = encoded.astype(np.float64) / 65535.0
>     out = np.empty(len(xx), dtype=O_VIOLATION_DTYPE)
>     out["y"] = yy + y0
>     out["x"] = xx
>     out["channel"] = channel
>     out["direction"] = np.where(upper[mask], 1, -1)
(`experiments/M8-overshoot/checker.py:528-535`)

**VERIFIED:** The attribution code then defines the field by requiring all
three predicates: maximum code, lower direction, and a lower hull endpoint
more than the complete tolerance above one:

>     encoded = rows["encoded"]
>     rail = (encoded == 0) | (encoded == 65535)
>     stats = {
>         "coordinates": len(rows),
>         "manifest_sha256": result["violations_sha256"],
>         "zero_rail": int(np.count_nonzero(encoded == 0)),
>         "full_rail": int(np.count_nonzero(encoded == 65535)),
>         "nonrail": int(np.count_nonzero(~rail)),
>         "full_rail_below_hull": int(
>             np.count_nonzero(
>                 (encoded == 65535)
>                 & (rows["direction"] < 0)
>                 & (rows["lo"] > 1.0 + rows["tolerance"])
>             )
>         ),
>     }
(`experiments/M8-overshoot/stage_attribution.py:181-196`)

**VERIFIED:** The frozen aggregate is exactly the one stated in the question:

>     "nonnegative_bilinear_m8_o_rail": {
>       "coordinates": 980097,
>       "full_rail": 977684,
>       "full_rail_below_hull": 977684,
>       "nonrail": 2413,
>       "zero_rail": 0
>     },
(`experiments/M8-overshoot/stage-attribution.json:70-76`)

**VERIFIED:** Therefore `full_rail_below_hull` does mean: the delivered sample
is the largest representable 16-bit value, yet even the lower edge of the
checker-allowed source hull is above that value. The sign is an output
*undershoot*, not an invented high overshoot. These rows are
`977684/980097 = 99.753799878991569...%` of the bilinear M8-O violations.

**VERIFIED — shipping nuance:** The Catmull-Rom arm has 938,063 full-rail
violations but only 938,062 in the impossible-below-hull class:

>     "shipping_catmull_m8_o_rail": {
>       "coordinates": 983648,
>       "full_rail": 938063,
>       "full_rail_below_hull": 938062,
>       "nonrail": 45585,
>       "zero_rail": 0
>     },
(`experiments/M8-overshoot/stage-attribution.json:111-117`)

**VERIFIED:** One Catmull full-rail row is therefore not excused by
representable-domain projection. Projection alone leaves 45,586 rows, not the
45,585 nonrail rows (`experiments/M136-m8o-bar/analysis.json:87-92`).

## 2. Achievability and the defect in the current construction

**VERIFIED — impossibility proof:** Let the serialized code be
`e in {0,...,65535}` and the checker's decoded value be `O=e/65535`.
Necessarily `O <= 1`. Every `full_rail_below_hull` row satisfies
`lo > 1+tolerance`, hence `lo-tolerance > 1`. Passing the lower comparison
would require `O >= lo-tolerance > 1`, contradicting `O <= 1`. This proof does
not depend on the merge, resampler, or choice of `e`; no admissible 16-bit
implementation can clear any of those 977,684 rows under the present
comparison.

**VERIFIED:** The scorecard currently asks the checker to compare the final
serialized value directly with the unprojected broad source hull:

> 4. **M8-O, final-output hull.** At the same linear coordinate and channel, define
>    `lo_O=min_k(lo_k)` and `hi_O=max_k(hi_k)` over every geometrically valid input
>    frame, never strehl's elected contributor list. Compare the actual final linear
>    output `O` to this interval. For a 16-bit serialized audit only, add exactly
>    `0.5/65535` quantisation tolerance to the largest contributing `tau_R`; no tone,
>    noise or scene-adaptive tolerance is allowed.
(`docs/proposals/2026-09-sota-scorecard.md:852-857`)

**VERIFIED:** The implementation likewise linearly scales `lo`, `hi`, and
`tau`, but does not compose the source interval with the producer's intervening
round/clamp or final `[0,1]` clamp:

>         lo_norm = np.asarray(lo * output_scale, dtype=np.float32)
>         hi_norm = np.asarray(hi * output_scale, dtype=np.float32)
>         tau_norm = np.asarray(tau * output_scale, dtype=np.float32)
>         lo_view = o_lo[b.channel, y0:y1]
>         hi_view = o_hi[b.channel, y0:y1]
>         tau_view = o_tau[b.channel, y0:y1]
>         np.minimum(lo_view, np.where(valid, lo_norm, np.float32(np.inf)), out=lo_view)
>         np.maximum(
>             hi_view, np.where(valid, hi_norm, np.float32(-np.inf)), out=hi_view
(`experiments/M8-overshoot/checker.py:409-417`)

**VERIFIED:** The source hull is not wrong in its own pre-serialization
linear domain. The category error is using that unbounded interval as though
it were already an interval in the bounded serialized output domain. The
correct final-output hull is the image of source support through every fixed,
monotone, samplewise representation transform on the audited path.

**VERIFIED:** A wider integer or floating format with an extended linear range
could represent these values and could clear the unprojected comparison, but
it is not admissible under the quoted 16-bit-TIFF contract. A scene-dependent
scale, shoulder, or tone map could fit them into `[0,1]`, but is expressly
forbidden and would also be policed by the unit-slope tone sentinel. A
different resampler cannot solve the contradiction: the contradiction is
already present in the zero-M8-R bilinear arm.

**VERIFIED:** Clamping the *checker hull* at the final serialization boundary
is legitimate only if M8-R remains a separate pre-clamp census. Clamping source
support before reconstructing M8-R would hide the very excursions M8-R exists
to expose and is not this ruling.

## 3. Legitimate repair versus moving the goalposts

### The case that it is goalpost-moving

**VERIFIED:** The change is proposed after a failure and changes 977,684 red
rows to representationally valid rail outcomes. That fact alone warrants a
presumption against the change.

**VERIFIED:** The scorecard itself warns that clamping can defeat M8-O:

> **Known defeat.** Final clamping can erase M8-O evidence; a broad all-frame hull can
> bracket a per-frame excursion; a producer-supplied contributor mask or hull can omit
> the disproof; and destructive clipping can force a zero rate.
(`docs/proposals/2026-09-sota-scorecard.md:877-880`)

**VERIFIED:** A literal “exclude rows when the observed output is at a rail”
rule also makes membership depend on the producer's output and changes the
denominator. That is avoidable and would create the appearance that clipping
removes evidence. It should not be adopted.

### The case that it is a legitimate repair

**VERIFIED:** M8's stated construct is support/invention. At an interval wholly
above one, `O=1` is the unique nearest representable value and cannot be an
invented high value. Rejecting it tests unavailable headroom, not invention.
The literal test is therefore not merely strict; it is false to its construct.

**VERIFIED:** A stronger legitimacy test than “what does a pass license?” is:

1. Does the revision correct a proved domain mismatch rather than use observed
   performance to choose a favorable threshold?
2. Does it keep the full population and a fixed, independently reconstructible
   rule?
3. Does every in-domain unsupported low/high plant remain red?
4. Does an off-rail output remain red when the whole hull lies beyond a rail?
5. Is the displaced information-loss phenomenon still measured and reported?
6. Do pre-clamp controls remain mandatory?

**VERIFIED:** Representable-domain projection passes that test. The small
deterministic commissioning in `analysis.json` found all four required green
cases green and all four required red cases red, including matching-rail green
and off-rail red:

>     "expected_green": 4,
>     "expected_red": 4,
>     "observed_green": 4,
>     "observed_red": 4,
>     "passed": true
(`experiments/M136-m8o-bar/analysis.json:161-165`)

**VERIFIED:** This is not a repair designed to make the shipping arm pass.
Even the conservative reanalysis that projects the hull and grants the known
intermediate quantizer leaves 31,148 Catmull-Rom M8-O violations, while the
bilinear arm leaves zero:

>     "denominator": 74173536,
>     "full_rail_below_hull": 938062,
>     "nonrail": 45585,
>     "projected_hull_violations": 45586,
>     "projected_plus_internal_quant_violations": 31148,
>     "violations": 983648
(`experiments/M136-m8o-bar/analysis.json:87-92`)

**VERIFIED — pass license before:** A literal pass would license both
“no delivered value outside the unprojected source hull” and the accidental
precondition “no tolerated source hull lies wholly beyond the mandatory output
domain.” The latter is a headroom/input-transfer claim over which a compliant
`u16` stacker has no per-coordinate remedy.

**VERIFIED — pass license after:** A repaired pass licenses: “every delivered
code lies within the final representable image of independently reconstructed
source support, after only declared deterministic representation transforms.”
It does **not** license absence of clipping, preservation of above-white
headroom, highlight detail, M8-R safety, or overall SOTA. Those remain separate
claims.

**VERIFIED — ruling:** The pass-license test reaches the right answer here,
but only together with the anti-gaming conditions above. The legitimate repair
is a codomain correction with an unchanged denominator and mandatory rail
disclosure, not deletion of inconvenient observations.

## 4. Where the rail excursions belong

**VERIFIED:** Current M6 is specifically a *recoverable-contributor* metric:

> 1. A high-rail pixel is recoverable when at least one common input is `>=0.98` and at
>    least one aligned input lies in `[0.20,0.95]`. A low-rail pixel is recoverable when
>    at least one input is `<=0.02` and another lies in `[0.05,0.80]`.
> 2. `clip_high` is the fraction of recoverable high pixels with output
>    `>=65534/65535`; `clip_low` is the mirrored fraction `<=1/65535`.
> 3. On recoverable-highlight tiles, compute M5’s `rho_best` against the independently
>    selected unsaturated source; report the median as highlight-detail retention.
(`docs/proposals/2026-09-sota-scorecard.md:762-768`)

**VERIFIED:** For a bilinear `full_rail_below_hull` row,
`lo_O=min_k(lo_k)>1+tolerance`. Therefore every geometrically valid mapped
source support is above one; in particular, there is no aligned contributor in
M6's `[0.20,0.95]` interval. These rows fail M6's population predicate and are
not in the current `clip_high` denominator.

**VERIFIED:** The present scorecard therefore does **not** double-count these
coordinates as M6 and M8 failures. It counts an output-domain/headroom
condition incorrectly as M8 invention and does not count it in M6.

**ASSUMED — governance recommendation:** Keep two mandatory, non-gating
diagnostics beside M8-O: high and low source-support intervals wholly beyond
the output domain, split into output-at-corresponding-rail and output-off-rail.
If headroom loss is to be a scored quality failure, add a prospectively
specified M6-H/output-transfer submetric. Do not silently fold it into current
M6, whose recoverability denominator and comparator requirements answer a
different question.

**ASSUMED — semantic placement:** “Output-domain headroom truncation” is the
least misleading name. It records real lost representational headroom without
calling the rail code invented. It is adjacent to M6 because it is clipping,
and adjacent to section 1.3 because the mandatory format causes it.

## 5. The 2,413-coordinate residue

**VERIFIED:** Keeping the original denominator, rail projection leaves exactly

`2413/74173536`

which is the irreducible exact fraction

`0.000032531818356347471421613228739694976925463011497793`

or

`0.0032531818356347471421613228739694976925463011497793%`.

The persisted calculation is:

>     "post_projection_residue_exact": "2413/74173536",
>     "post_projection_residue_fraction": 3.2531818356347474e-05,
>     "post_projection_residue_fraction_decimal": "0.000032531818356347471421613228739694976925463011497793",
>     "post_projection_residue_percent": 0.003253181835634747,
>     "post_projection_residue_percent_decimal": "0.0032531818356347471421613228739694976925463011497793"
(`experiments/M136-m8o-bar/analysis.json:174-178`)

**VERIFIED:** The current checker budgets only the mapped `tau_R` plus the
final half-code. It omits an earlier lossy conversion. After the M8-R trace,
the producer divides out the site gain, restores black, rounds, and clamps to
`u16`:

>                         // Undo the balance, restore the pedestal, then round and
>                         // clamp exactly as the shipped path does.
>                         (scratch.dst[lo + px] * inv + black)
>                             .round()
>                             .clamp(0.0, u16::MAX as f32) as u16
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs:2143-2147`)

**VERIFIED:** The merge path later reads that integer back and subtracts black:

>                 for (px, o) in dst.iter_mut().enumerate() {
>                     *o = (f32::from(frame.data[row + 2 * px]) - black).max(0.0);
>                 }
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/merge_cmd.rs:4779-4781`)

**VERIFIED:** It then applies output gain/range and performs the final
serialization:

>     let encode = |v: f32, gain: f32| -> u16 {
>         let v = (v * gain / range).min(1.0);
>         let v = if srgb { srgb_encode(v) } else { v };
>         (v * u16::MAX as f32 + 0.5) as u16
>     };
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/merge_cmd.rs:7365-7369`)

**VERIFIED:** Away from the intermediate clamp, the omitted round contributes
at most `0.5 * output_gain[channel] / sensor_range` in normalized output units.
Across the three bilinear arms this is about `6.045–6.125` output LSB for R,
`2.207` for G, and `3.356–3.444` for B. The 2,413 post-projection violations
are R `1,839`, G `0`, B `574`; none exceeds the corresponding omitted bound,
and all three bilinear arms become zero under projection plus that bound
(`experiments/M136-m8o-bar/analysis.json:3-46,366-577`).

**VERIFIED:** The one-frame bilinear arm is the cleaner diagnosis. It has zero
M8-R but 52,570 nonrail M8-O rows:

>     "m8_o": {
>       "clamping_caveat": "Final clamping can erase M8-O evidence; a zero M8-O count is not a pass without the pre-clamp M8-R census.",
>       "denominator": 24724512,
>       "fraction": 0.002126230034388545,
>       "lower_violations": 27286,
>       "max_abs_signed_excess_linear": 9.673507562264066e-05,
>       "max_abs_signed_excess_u16_lsb": 6.339533180929756,
>       "max_upper_signed_excess_linear": 9.597676976044744e-05,
>       "min_lower_signed_excess_linear": -9.673507562264066e-05,
>       "percent": 0.2126230034388545,
>       "quantisation_tolerance": 7.629510948348211e-06,
>       "tiff_sha256": "9682FF568F221E55D9D04C4FF11ED675DCF29D4EB620D83D8816BFD1D7937E16",
>       "unbracketed_samples": 0,
>       "upper_violations": 25284,
>       "violations": 52570
>     },
(`experiments/M8-overshoot/stage-attribution.json:649-664`)

**VERIFIED:** Every one of those 52,570 rows also clears under the known
intermediate half-step bound
(`experiments/M136-m8o-bar/analysis.json:814-887`). This independently
demonstrates that the post-gather residue is compatible with a representation
round trip even when the resampler itself is clean.

**VERIFIED — contradiction to the question's characterization:** The 2,413
rows may not honestly be called “genuine invention” on present evidence. They
are violations of the incomplete checker model, but all are bounded by a
known, deterministic quantizer omitted from that model.

**ASSUMED — remaining causal precision:** The quantization bound proves that
none of the 2,413 requires an invention explanation; it does not replay the
exact intermediate integer at each coordinate. The exact trace needed for
that attribution was not retained. A replacement checker should model the
round/clamp exactly rather than turn the half-step into a permanent generic
tolerance.

**VERIFIED:** The corrected target should remain exactly zero. Once all fixed
representation operations are included, each nonempty source interval has a
nonempty image in `[0,1]`, and some `u16` code lies within one half-code of a
point in that image. Thus zero is mathematically achievable without a
statistical allowance. The existing bilinear evidence reaches zero under the
conservative complete bound; an official result remains unmeasured until the
replacement checker is independently commissioned and run.

## 6. Replacement bar text

**ASSUMED — recommended normative text:** This is the replacement I recommend
applying. It preserves M8-R unchanged.

```text
M8-O — final serialized source-support certificate

Population and coordinate domain. For every scored capture, evaluate every
(capture, x, y, channel) coordinate in the native-size final linear 16-bit TIFF,
for channel in {R,G,B}, at the output sample centre, for which at least one input
frame is geometrically valid under the frozen placement. The denominator N is
the number of those coordinates. Coordinates at either rail, and coordinates
whose source-support interval lies wholly outside [0,1], remain in N.

Source intervals. For each valid frame k, independently reconstruct the exact
discrete source support used by the registered resampler and let
I_k = [lo_k - tau_R,k, hi_k + tau_R,k], with tau_R,k defined exactly as in M8-R.

Output-domain image. Let F_k,c be the fixed, declared, per-channel monotone
numeric map actually traversed from the M8-R trace domain to the linear value
immediately before final-u16 serialization. F_k,c must include every
representation-only operation on that path: inverse site gain, pedestal
restore/removal, intermediate rounding and container clamping, fixed output
gain and range normalization, and the final saturation to [0,1]. It must not
include a producer-chosen contributor mask, merge/restoration decision,
scene-adaptive transform, tone map, or noise allowance. Evaluate interval
images with the recorded arithmetic order and outward rounding:

    J_k = F_k,c(I_k)
    L = min_k inf(J_k)
    H = max_k sup(J_k).

For the frozen native-RAW path, before the final-u16 quantizer:

    F_k,c(z) =
      clamp_[0,1](
        max(clamp_[0,65535](round(z / g_k,c + b_k)) - b_k, 0)
        * G_c / R_k)

where g_k,c is the recorded site gain, b_k the recorded black level, G_c the
recorded final output gain, and R_k the recorded sensor range. A checker that
lacks any required transform parameter or rounding rule reports UNMEASURED.

Comparison and tolerance. Read encoded code e as O=e/65535. The only tolerance
outside the interval construction is q=0.5/65535 for final serialization.
Count one M8-O violation exactly when O < L-q or O > H+q. No temporal-noise,
scene-adaptive, or empirical tolerance is allowed.

Success. Report violation count V, denominator N, exact fraction V/N, percent,
maximum signed excess, and every violating coordinate. M8-O passes iff V=0
(exactly 0.0000%). M8-R and the crop/reference identity arm remain separately
mandatory at zero.

Rail disclosure. Also compute the same broad hull before only the final [0,1]
saturation. Separately report counts and fractions over N for (a) high
unrepresentable support, whose tolerated lower bound is >1+q, and (b) low
unrepresentable support, whose tolerated upper bound is <-q. Split each count
by output at the corresponding rail versus output off that rail. These
coordinates are not M8-O violations when the output is at the corresponding
rail; an off-rail output remains an M8-O violation under the projected hull.
The rail counts are mandatory disclosures and do not by themselves establish
highlight/shadow retention.

Controls. In addition to the existing M8 controls, commission the revised
checker with: an in-range copy null; an in-range convex-bilinear null; planted
in-range high and low excursions; a wholly-above-one hull at code 65535 and
off rail; and a wholly-below-zero hull at code 0 and off rail. Required results
are respectively green, green, red/red, green/red, and green/red.
```

**VERIFIED:** This text leaves the denominator at `74,173,536` for the frozen
three-stack census. It changes classification, not population: the 977,684
matching high-rail coordinates remain visible in the mandatory rail report,
while an output even one full code off the required projected rail remains
red.

## Could not determine

**VERIFIED — could not determine:** The exact historical ambient value of
`STREHL_HULL` for the stage-attribution run cannot be reconstructed from its
provenance. The driver clears and records several `STREHL_*` variables but
neither clears nor records `STREHL_HULL`
(`experiments/M8-overshoot/stage-attribution.ps1:138-155,201-216`). The frozen
source says an unset value defaults to `InputRange`
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-core/src/pyramid.rs:759-775`),
but the run record does not prove it was unset.

**VERIFIED — could not determine:** The frozen M8 artifacts do not retain the
post-inverse-gain intermediate `u16` sample or all parameters needed to replay
that integer conversion coordinate by coordinate. Therefore the known
half-step bounds account for all 2,413 aggregate and all 52,570 one-frame
residuals, but exact row-by-row causal identity remains unproved.

**VERIFIED — could not determine:** No independently commissioned
implementation of the replacement M8-O definition has yet read the full
corpus. This report establishes that the old bar is partly impossible, that
the replacement is well-posed and retains its target sensitivity, and that the
existing bilinear residue fits known representation error. It does not promote
M8-O to an official PASS.

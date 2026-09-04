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
| M134 corroboration | Confirms the proof and all per-capture counts; it increases confidence but does not change the ruling. |
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
(`docs/proposals/2026-09-sota-scorecard.md`, "Each program must emit a native-size 16-bit linear TIFF." clause)

**VERIFIED:** M8's stated construct is invented values, not headroom:

> **What it measures and why.** A merge or restoration stage can ring beyond any
> observed linear sample. The proposal explicitly requires a per-file hull census of
> `0.0000%` or coordinates for every exception
(`docs/proposals/2026-09-sota-scorecard.md`, "A merge or restoration stage can ring beyond any" clause)

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
(`docs/research/M-FLATNULL.md`, "Final verdict: the registered noise-rise failure was not observed" clause)

**VERIFIED:** That report also imposed the correct governance boundary:

> **Do not use current M8-O as the surviving general comparative detail axis.**
> A rail-aware hull, pre-clamp output census, or frozen rail exclusion would be a
> new statistic, not a reinterpretation of this one; it requires a new
> preregistration and full commissioning. This lane made none of those changes.
(`docs/research/M-FLATNULL.md`, "Do not use current M8-O as the surviving general comparative detail axis." clause)

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
(`experiments/M8-overshoot/checker.py`, "expected uint16 {expected}, got {image.dtype} {image.shape}" clause)

>             encoded = np.asarray(image[y0:y1, :, channel], dtype=np.uint16)
>             values = encoded.astype(np.float64) / 65535.0
>             tolerance = tau + U16_QUANT_TOL
>             lower = bracketed & (values < lo - tolerance)
>             upper = bracketed & (values > hi + tolerance)
(`experiments/M8-overshoot/checker.py`, "lower = bracketed & (values < lo - tolerance)" clause)

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
(`experiments/M8-overshoot/checker.py`, "out = np.empty(len(xx), dtype=O_VIOLATION_DTYPE)" clause)

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
(`experiments/M8-overshoot/stage_attribution.py`, "rail = (encoded == 0) | (encoded == 65535)" clause)

**VERIFIED:** The frozen aggregate is exactly the one stated in the question:

>     "nonnegative_bilinear_m8_o_rail": {
>       "coordinates": 980097,
>       "full_rail": 977684,
>       "full_rail_below_hull": 977684,
>       "nonrail": 2413,
>       "zero_rail": 0
>     },
(`experiments/M8-overshoot/stage-attribution.json`, "1.3213567167675544" clause)

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
(`experiments/M8-overshoot/stage-attribution.json`, "1.326144138524015" clause)

**VERIFIED:** One Catmull full-rail row is therefore not excused by
representable-domain projection. Projection alone leaves 45,586 rows, not the
45,585 nonrail rows
(`experiments/M136-m8o-bar/analysis.json`, "31148" clause).

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
(`docs/proposals/2026-09-sota-scorecard.md`, "M8-O, final-output hull." clause)

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
(`experiments/M8-overshoot/checker.py`, "lo_norm = np.asarray(lo * output_scale, dtype=np.float32)" clause)

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

### Independent M134 corroboration

**VERIFIED — no change to the ruling:** I read
`experiments/M134-kernel-frontier/phase4-results.json` and its generating
script rather than accepting the supplied summary. M134 states the same
set-theoretic proof:

>   "proof": {
>     "accepted_lower_condition": "value >= lo - tolerance",
>     "consequence": "at least one such geometrically valid census sample makes an exact 0.0000% M8-O bar impossible without changing the output representation, normalization, or census treatment of saturation",
>     "empty_intersection_when": "lo - tolerance > 1",
>     "representable_output_interval": "[0, 1]"
>   },
(`experiments/M134-kernel-frontier/phase4-results.json`, "empty_intersection_when" clause)

**VERIFIED:** Its protocol, source hashes, tolerance, and verdict are:

>   "protocol": "M134 M8-O representability v1",
>   "source": {
>     "analysis_script_sha256": "7161136DBC100FA852E82BCAADA5335A226B9FAFDF0F815DC23F1E9CCBB2D144",
>     "frozen_stage_attribution": "experiments/M8-overshoot/stage-attribution.json",
>     "frozen_stage_attribution_sha256": "E0BFCEDA067F614EFEFAD60DFE27FD6803A085DBE2976AB19A1116B37207C792"
>   },
>   "u16_quantisation_tolerance": 7.629510948348211e-06,
>   "verdict": "UNACHIEVABLE AS WRITTEN under the current normalized u16 output: when lo > 1 + tolerance, every representable value is below the source hull"
(`experiments/M134-kernel-frontier/phase4-results.json`, "UNACHIEVABLE AS WRITTEN under the current normalized u16 output" clause)

**VERIFIED:** I independently hashed `phase4.py`, the frozen stage-attribution
artifact, and the companion checker; all equal the recorded hashes. I also
compared every M134 bilinear per-capture denominator, violation count, rail
classification, and nonrail count with M136's separate reclassification; all
match (`experiments/M136-m8o-bar/analysis.json`, "m134_corroboration" clause).

**VERIFIED:** The per-capture split is exactly:

| Capture | Unrepresentable/full-rail-below-hull | Nonrail | Fraction of all valid output coordinates |
|---|---:|---:|---:|
| `flat-et1s` | `0` | `1,409` | `0` (`experiments/M134-kernel-frontier/phase4-results.json`, "B348E5BE9D9C7527BFD1ABE812B77B4EA41FA6B92F0A7BCE2B8001E18A506AA8" clause) |
| `flat-et2.5s` | `0` | `671` | `0` (`experiments/M134-kernel-frontier/phase4-results.json`, "FE150A22D9148FD9D7A7154B21F8095CE584F8EB32269A834887DF857A20FB5E" clause) |
| `flat-et6s` | `977,684` | `333` | `0.03954310604795759` (`experiments/M134-kernel-frontier/phase4-results.json`, "DB4C1E9411F06B7126A67308A5B2E8C64DA94A5B40B17B2BDDDC1496F0C912E3" clause) |

**VERIFIED:** This strongly corroborates saturation attribution, but the
mechanism does not depend on a natural-experiment inference: M134 directly
counts `lo > 1 + tau + 0.5/65535`. Such a coordinate has an empty intersection
between its accepted interval and `[0,1]`, regardless of why its exposure
produced that hull.

**VERIFIED — correction to the supplied characterization:** Exposure time is
not the only recorded difference among the three arms. They contain 60, 61,
and 65 frames and use cover scales `0.9862`, `0.9870`, and `0.9859`,
respectively:

>     "flat-et1s": {
>       "cover_scale": 0.9862,
>       "frames": 60,
(`experiments/M8-overshoot/results.json`, "1B559A76D7ADC33262B5EEFB59E56462D70E62B375E665D6E9B56BC328D1B48E" clause)

>     "flat-et2.5s": {
>       "cover_scale": 0.987,
>       "frames": 61,
(`experiments/M8-overshoot/results.json`, "D7A1A1046BB3F6C14CB41DB825401A6A571FF1C9DD2FA116BED08331C6F52066" clause)

>     "flat-et6s": {
>       "cover_scale": 0.9859,
>       "frames": 65,
(`experiments/M8-overshoot/results.json`, "7884DD2B809361CE8B0B57FA291B7C1A68DFBEDD71CA8A076F4271CD32AA76BD" clause)

**VERIFIED:** The split is therefore corroborative rather than a controlled
“only exposure differs” experiment. This qualification does not weaken the
per-coordinate impossibility proof.

**VERIFIED — independence qualification:** The companion record truthfully
reports `forbidden_strehl_imports: []`, `independent: true`, and names
independent coordinate, support, and tolerance functions
(`experiments/M134-kernel-frontier/out/independence.json`, "forbidden_strehl_imports" clause).
However, `phase4.py` itself computes this particular representability census
from the frozen M8 checker's saved `o-lo.npy` and `o-tau.npy` arrays:

> def count_unrepresentable_hulls(state: Path) -> dict:
>     lo = np.load(state / "o-lo.npy", mmap_mode="r")
>     tau = np.load(state / "o-tau.npy", mmap_mode="r")
>     if lo.shape != tau.shape:
>         raise RuntimeError(f"{state}: lo/tau shape mismatch")
>     valid = 0
>     above = 0
>     for channel in range(lo.shape[0]):
>         for y0 in range(0, lo.shape[1], 64):
>             y1 = min(lo.shape[1], y0 + 64)
>             l = np.asarray(lo[channel, y0:y1], dtype=np.float64)
>             t = np.asarray(tau[channel, y0:y1], dtype=np.float64)
>             finite = np.isfinite(l)
>             valid += int(np.count_nonzero(finite))
>             above += int(
>                 np.count_nonzero(finite & (l > 1.0 + t + U16_QUANT_TOL))
>             )
(`experiments/M134-kernel-frontier/phase4.py`, "def count_unrepresentable_hulls(state: Path) -> dict:" clause)

**VERIFIED:** M134 is thus an independent analysis and proof over the same
frozen evidence, not a wholly independent raw-to-hull reconstruction for the
phase-4 count. That is still valuable convergence, but it is not independent
data and should not be described as such.

## 3. Legitimate repair versus moving the goalposts

### The case that it is goalpost-moving

**VERIFIED:** The change is proposed after a failure and changes 977,684 red
rows to representationally valid rail outcomes. That fact alone warrants a
presumption against the change.

**VERIFIED:** The scorecard itself warns that clamping can defeat M8-O:

> **Known defeat.** Final clamping can erase M8-O evidence; a broad all-frame hull can
> bracket a per-frame excursion; a producer-supplied contributor mask or hull can omit
> the disproof; and destructive clipping can force a zero rate.
(`docs/proposals/2026-09-sota-scorecard.md`, "Known defeat.** Final clamping can erase M8-O evidence" clause)

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
(`experiments/M136-m8o-bar/analysis.json`, "expected_green" clause)

**VERIFIED — ruling on the specific M134-style proposal:** “Count nonrail and
rail-pinned overshoots, but exclude unavoidable rail-pinned undershoots” has
the right intent but is not precise enough to govern. It misclassifies by
output category:

1. nonrail rows are not automatically invention — all 2,413 bilinear nonrail
   rows fit a known omitted intermediate-quantizer bound;
2. rail rows are not automatically representability exceptions — one shipping
   Catmull full-rail row is not `full_rail_below_hull`;
3. excluding rows changes the population and invites outcome-conditioned
   accounting.

**VERIFIED:** The principled version is source-defined, not label-defined:
retain every coordinate and compare its output with the exact representable
image of its independently reconstructed source interval. This produces the
desired dispositions without a special amnesty: matching unavoidable rail
passes, off-rail output fails, in-domain low/high invention fails, and a rail
on the wrong side of an in-domain hull fails.

**VERIFIED — defects the successor must still catch:**

1. every pre-clamp resampler undershoot or overshoot outside exact discrete
   support, through unchanged M8-R;
2. every final in-range value below or above the representable source hull;
3. a high-rail output when the projected source hull ends below one, and a
   zero-rail output when the projected source hull begins above zero;
4. any off-rail output when the whole source hull lies beyond the corresponding
   rail, because the nearest supported representable value is that rail;
5. post-gather merge, reconstruction, sharpening, or restoration excursions
   that survive into the deliverable;
6. either-sign planted defects, while exact copy and convex-bilinear controls
   remain green;
7. omitted valid frames or producer-selected contributor masks, by retaining
   the all-geometrically-valid-frame hull and independent coordinate list.

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
(`experiments/M136-m8o-bar/analysis.json`, "31148" clause)

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
(`docs/proposals/2026-09-sota-scorecard.md`, "A high-rail pixel is recoverable when at least one common input is" clause)

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
(`experiments/M136-m8o-bar/analysis.json`, "2413/74173536" clause)

**VERIFIED:** The current checker budgets only the mapped `tau_R` plus the
final half-code. It omits an earlier lossy conversion. After the M8-R trace,
the producer divides out the site gain, restores black, rounds, and clamps to
`u16`:

>                         // Undo the balance, restore the pedestal, then round and
>                         // clamp exactly as the shipped path does.
>                         (scratch.dst[lo + px] * inv + black)
>                             .round()
>                             .clamp(0.0, u16::MAX as f32) as u16
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/align_cmd.rs`, "Undo the balance, restore the pedestal, then round and" clause)

**VERIFIED:** The merge path later reads that integer back and subtracts black:

>                 for (px, o) in dst.iter_mut().enumerate() {
>                     *o = (f32::from(frame.data[row + 2 * px]) - black).max(0.0);
>                 }
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/merge_cmd.rs`, "f32::from(frame.data[row + 2 * px]) - black" clause)

**VERIFIED:** It then applies output gain/range and performs the final
serialization:

>     let encode = |v: f32, gain: f32| -> u16 {
>         let v = (v * gain / range).min(1.0);
>         let v = if srgb { srgb_encode(v) } else { v };
>         (v * u16::MAX as f32 + 0.5) as u16
>     };
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-cli/src/merge_cmd.rs`, "let encode = |v: f32, gain: f32| -> u16 {" clause)

**VERIFIED:** Away from the intermediate clamp, the omitted round contributes
at most `0.5 * output_gain[channel] / sensor_range` in normalized output units.
Across the three bilinear arms this is about `6.045–6.125` output LSB for R,
`2.207` for G, and `3.356–3.444` for B. The 2,413 post-projection violations
are R `1,839`, G `0`, B `574`; none exceeds the corresponding omitted bound,
and all three bilinear arms become zero under projection plus that bound
(`experiments/M136-m8o-bar/analysis.json`, "omitted_internal_half_step" clause).

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
(`experiments/M8-overshoot/stage-attribution.json`, "9682FF568F221E55D9D04C4FF11ED675DCF29D4EB620D83D8816BFD1D7937E16" clause)

**VERIFIED:** Every one of those 52,570 rows also clears under the known
intermediate half-step bound
(`experiments/M136-m8o-bar/analysis.json`, "999.7215616330504" clause). This independently
demonstrates that the post-gather residue is compatible with a representation
round trip even when the resampler itself is clean.

**VERIFIED — contradiction to the question's characterization:** The 2,413
rows may not honestly be called “genuine invention” on present evidence. They
are violations of the incomplete checker model, but all are bounded by a
known, deterministic quantizer omitted from that model.

**VERIFIED — shipping disposition:** The 2,413 are from the bilinear
counterfactual, not the shipping Catmull-Rom kernel, so they do not themselves
decide whether shipping passes a repaired bar. Shipping does not pass
trivially: projection plus the complete conservative quantization bound still
leaves 31,148 Catmull-Rom M8-O violations
(`experiments/M136-m8o-bar/analysis.json`, "31148" clause), and its separate M8-R result
remains `63,191,176/6,131,678,976`
(`experiments/M8-overshoot/results.json`, "63191176" clause). The formal result under the
exact new M8-O definition is nevertheless `UNMEASURED` until that checker is
commissioned; the 31,148 count is a diagnostic lower than the old count, not a
promoted score.

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
For cover=crop, (x,y) names the compact TIFF coordinate and maps to full-plane
(x+x0,y+y0), where (x0,y0) is the crop origin independently reconstructed from
the frozen placements. The reconstructed crop rectangle must agree with the
recorded producer rectangle and TIFF dimensions. Any TIFF coordinate lacking a
reconstructed valid contributor, or any missing/duplicate expected frame-site
trace, makes the result UNMEASURED rather than shrinking N.

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

F_k,c must be applied to each frame interval before the min/max reduction.
Applying a projection or an empirical internal-quantizer allowance to old
aggregate lo/hi/tau arrays is not this metric.

For a candidate whose audited native-RAW path matches the frozen path, define:

    u_k,c(z) =
      u16(clamp_[0,65535](round_f32_ties_away_from_zero(z / g_k,c + b_k)))

    P_k,c(z) = max(f32(u_k,c(z)) - b_k, 0) * G_c / R_k

    F_k,c(z) = clamp_[0,1](P_k,c(z))

where g_k,c is the recorded site gain, b_k the recorded black level, G_c the
recorded final output gain, and R_k the recorded sensor range. A checker that
lacks any required transform parameter, scalar type, operation order, rounding
rule or clamp rule reports UNMEASURED. If the candidate path differs, its exact
fixed monotone representation path must be declared prospectively and the
checker recommissioned before any target result is read.

Comparison and tolerance. Read encoded code e as O=e/65535. The only tolerance
outside the interval construction is q=0.5/65535=1/131070 for final
serialization.
Count one M8-O violation exactly when O < L-q or O > H+q. No temporal-noise,
scene-adaptive, or empirical tolerance is allowed.

Success. Report violation count V, denominator N, exact fraction V/N, percent,
maximum signed excess, and every violating coordinate. M8-O passes iff V=0
(exactly 0.0000%, decided from the integer count rather than a rounded
percentage). M8-R and the crop/reference identity arm remain separately
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
are respectively green, green, red/red, green/red, and green/red. Also require
an exact intermediate-u16 quantizer-boundary green/red pair, a nonzero-origin
crop-coordinate green/red pair, and fail-closed tests for missing black level,
crop origin, frame-site trace, or arithmetic metadata.
```

**VERIFIED:** This text leaves the denominator at `74,173,536` for the frozen
three-stack census. It changes classification, not population: the 977,684
matching high-rail coordinates remain visible in the mandatory rail report,
while an output even one full code off the required projected rail remains
red.

**ASSUMED — finality:** With the added crop-coordinate and per-frame-transform
clauses, this is the final M136 bar text. It is kernel-agnostic: a future arm is
scored by its frozen output and independently reconstructed support, not by a
kernel-specific exception. The exact candidate arithmetic remains a measured
input to `F_k,c`; changing that fixed path requires prospective versioning and
recommissioning, not an after-the-result tolerance.

### 6.1 Scorecard amendment packet

**VERIFIED — exact current text and unique anchor:** Replace the following
current M8-O definition, identified by the unique single-line anchor
`M8-O, final-output hull.`:

```text
4. **M8-O, final-output hull.** At the same linear coordinate and channel, define
   `lo_O=min_k(lo_k)` and `hi_O=max_k(hi_k)` over every geometrically valid input
   frame, never strehl's elected contributor list. Compare the actual final linear
   output `O` to this interval. For a 16-bit serialized audit only, add exactly
   `0.5/65535` quantisation tolerance to the largest contributing `tau_R`; no tone,
   noise or scene-adaptive tolerance is allowed.
```

(`docs/proposals/2026-09-sota-scorecard.md`, "M8-O, final-output hull." clause)

**ASSUMED — exact replacement:** Substitute the complete normative text in the
fenced block under section 6 above, beginning with the unique line
`M8-O — final serialized source-support certificate` and ending with the unique
line `crop origin, frame-site trace, or arithmetic metadata.` No text outside
those two inclusive anchors is part of the replacement. Retain M8-R unchanged
and retain the existing exact-zero M8-O success sentence.

**VERIFIED — plan licence:** The governing plan requires the render manifest to
carry:

> the acuity summary, the per-axis scorecard verdicts, **and the
> hull certificate** — the out-of-hull census result (0.0000% or the exceptions, with
> coordinates) stamped per render, which in the current era is a differentiator worth
> stating plainly: *this file provably contains no invented values*.

(`docs/proposals/2026-08-sota-path.md`, "hull certificate** — the out-of-hull census result (0.0000% or the exceptions, with" clause)

The plan later narrows the licence: the hull census “can establish invention;
it cannot name the inventor”
(`docs/proposals/2026-08-sota-path.md`, "and is stated here in the only form the evidence supports: **it can establish" clause).
The replacement implements that existing zero-invention certificate in the
actual serialized codomain; it does not create a new claim.

**VERIFIED — falsifiable conditions:**

1. `DENOMINATOR_UNCHANGED := N == count(all registered eligible capture,x,y,channel coordinates before output-value classification)`; deleting one rail or out-of-domain-support coordinate must make the check fail.
2. `RAILS_REPORTED := high_at_rail + high_off_rail == count(pre-final lower bound > 1+q) AND low_at_rail + low_off_rail == count(pre-final upper bound < -q)`; deleting or reclassifying one such coordinate must make the check fail.
3. `IN_RANGE_PLANTS_RED := planted_high_violations == 1 AND planted_low_violations == 1 AND their directions are +1 and -1`; clamping, excluding, or accepting either plant must make commissioning fail.
4. `M8_R_MANDATORY := combined_pass == (M8_O.V == 0 AND M8_R.V == 0 AND crop_identity.V == 0)`; changing an otherwise-green fixture to `M8_R.V=1` must force `combined_pass=false`.

**VERIFIED — status boundary:** M8 still reads **FAIL** on M8-R at
`1.030569%`; this ruling neither changes that result nor promotes M8-O to PASS.

**VERIFIED — 2,413-row boundary:** The stated reading is correct in substance,
but the technical defect is specificity/construct validity rather than
sensitivity: those rows fit omitted deterministic representation error, so
they do not establish invention and do not establish that the product invents
less.

**ASSUMED — shared cause with M135:** Both failures registered an exact bar
before proving that the statistic identified the intended construct over its
admissible domain: M135's normalization erased the relevant operator family,
while M8-O compared a bounded output with unprojected support and made valid
coordinates impossible to pass.

## 7. Preregistered clamped-Catmull M8-O measurement

The machine-readable companion is
`experiments/M136-m8o-bar/clamped-m8o-preregistration.json`. Its status is
`PREREGISTERED_NOT_EXECUTED`; no number in this section is a clamped M8-O
result.

### 7.1 The clamp and M8-O are only partly orthogonal

**VERIFIED:** The narrow reasoning is correct. A zero-margin Catmull-Rom clamp
changes the gathered value but not the exact 4x4 source support, the fixed
output container, or the set-theoretic fact that an interval wholly above one
has no intersection with an unsaturated normalized-`u16` value. In the existing
matched Scale renders, all nine aggregate files — `o-lo.npy`, `o-hi.npy`, and
`o-tau.npy` for three captures — are byte-identical between shipping Catmull-Rom
and clamped Catmull-Rom. The clamped arm simultaneously has zero M8-R
violations over `6,131,678,976` gathered samples
(`experiments/M136-m8o-bar/analysis.json`, "clamped_artifact_inventory" clause).

**VERIFIED — numerical correction:** The old clamped-Catmull support hull is
the shipping Catmull hull, not the bilinear hull. Its unchanged old Scale-domain
unrepresentable population is therefore `938,062`, not bilinear's `977,684`:

>     "aggregate_unrepresentable_hulls": {
>       "high": 938062,
>       "low": 0,
>       "valid": 74173536
>     },
(`experiments/M136-m8o-bar/analysis.json`, "aggregate_unrepresentable_hulls" clause)

**VERIFIED — important qualification:** The clamp is not orthogonal to M8-O as
a whole. It changes the gathered values supplied to the merge, so it may change
the final nonrail, wrong-rail, reconstruction, and quantizer-sensitive residue.
M8-R zero therefore does not imply M8-O zero. That final residue is the
measurement being preregistered.

**INHERITED — crop qualification:** The clamp alone leaves the old
representability mechanism untouched, but the forthcoming run changes from
the old Scale output domain to M130's compact Crop domain. M130 describes Crop
as evaluating warps in full-plane coordinates and then writing the compact
covered rectangle directly:

> `strehl stack --merge pyramid --cover crop` now evaluates each warp in the
> original full-plane coordinate system, then extracts the common covered
> rectangle before luma, variance, the measured gate floor, pyramid construction,
> local-energy weighting, accumulation, confidence, and collapse. The compact
> collapsed plane is written directly. There is no writer-time second crop.
(`docs/research/M130-crop-early.md`, "strehl stack --merge pyramid --cover crop" clause)

**VERIFIED:** Consequently, neither `977,684` nor any other old Scale-domain
rail count is preregistered as the expected Crop count. The mechanism persists;
the new population and count must be measured.

### 7.2 What exists, and why it cannot decide the new bar

**VERIFIED:** M134 left three clamped TIFFs and three state directories:

| Capture | Existing TIFF/state | M8-R | Existing aggregate hulls |
|---|---|---:|---|
| `flat-et1s` | `experiments/M134-kernel-frontier/out/clamped-flat-et1s.{tiff,provenance.json}` and `clamped-flat-et1s-state/` | `0 / 1,977,960,960` | `o-lo.npy`, `o-hi.npy`, `o-tau.npy` |
| `flat-et2.5s` | corresponding `clamped-flat-et2.5s*` paths | `0 / 2,010,926,976` | same three arrays |
| `flat-et6s` | corresponding `clamped-flat-et6s*` paths | `0 / 2,142,791,040` | same three arrays |

The persisted inventory records `has_m8_o_json=false`,
`has_m8_o_violations=false`, `retained_trace_blocks=0`, trace protocol `2`,
no black level, no output-crop origin, and `cover=scale` for every capture
(`experiments/M136-m8o-bar/analysis.json`, "clamped_artifact_inventory" clause).

**VERIFIED:** That absence follows the runner, not merely the filenames. After
each target render M134 invokes only `finalize-r`:

>     Invoke-Checked $Binary $arguments $log
>     Invoke-Checked "python" @("-B", $Checker, "finalize-r", "--state", $state) (
>         Join-Path $Out "$name-r.log"
>     )
(`experiments/M134-kernel-frontier/run.ps1`, "name-r.log" clause)

**VERIFIED:** The v2 trace serializes sensor range and site gain, but no black
level:

>     w.write_all(&frame.levels.range().to_le_bytes())?;
>     w.write_all(&site_gain.to_le_bytes())?;
>     let frame_path = frame.path.to_string_lossy();
(`experiments/M134-kernel-frontier/m8_trace.rs`, "frame.levels.range().to_le_bytes()" clause)

It deletes each block after the old checker consumes it:

>     if !status.success() {
>         bail!(
>             "independent M8 checker failed on {}; block retained",
>             block.display()
>         );
>     }
>     OpenOptions::new()
>         .write(true)
>         .create_new(true)
>         .open(&marker)
>         .with_context(|| format!("creating unique M8 seen marker {}", marker.display()))?;
>     fs::remove_file(&block)
>         .with_context(|| format!("removing consumed M8 block {}", block.display()))?;
(`experiments/M134-kernel-frontier/m8_trace.rs`, "removing consumed M8 block" clause)

**VERIFIED:** The old aggregate arrays cannot be repaired after the fact. The
v2 checker first reduces each frame using the linear scale
`output_gain/site_gain/value_range`:

>     output_scale = np.float32(output_gain / b.site_gain / b.value_range)
(`experiments/M134-kernel-frontier/checker.py`, "output_scale = np.float32(output_gain / b.site_gain / b.value_range)" clause)

It then takes aggregate minima/maxima
(`experiments/M134-kernel-frontier/checker.py`, "np.minimum(lo_view, np.where(valid, lo_norm, np.float32(np.inf)), out=lo_view)" clause). The exact
successor instead must apply each frame's additive black restore, discrete
round/clamp, black removal, gain/range normalization, and final saturation
*before* reducing across frames. Frame identity and the nonlinear operation
have already been discarded, so no transformation of aggregate
`o-lo/o-hi/o-tau` can recover the registered statistic.

**VERIFIED — answer on reuse:** The retained files are sufficient to run the
old, impossible, unprojected M8-O comparison against the old Scale TIFFs. They
are also sufficient for the conservative half-step diagnostic already reported
in section 5. They are not sufficient for an exact section-6 score.

**ASSUMED — theoretical but irrelevant alternative:** One could avoid a new
trace for the *old* TIFFs only by building and commissioning an independent
RAW decoder that reproduces every source plane, black level, gain, placement,
rounding operation, and crop mapping. That would reconstruct the missing
evidence rather than use the existing state. It would still not score the
post-M130 output the owner has requested.

**INHERITED — governing disposition:** A fresh post-M130 clamped render is
required because Crop changes the output domain and bytes. The result must use
the TIFF and trace produced by the same frozen candidate binary; mixing a new
hull with the old M134 TIFF, or vice versa, is `UNMEASURED`.

### 7.3 Required instrument and evidence contract

**ASSUMED — required implementation:** Before any target run, an implementation
lane must add, under `experiments/M136-m8o-bar/`, `m8_trace_v3.rs`,
`checker_m136.py`, `fixture_m136.py`, `verifier_m136.py`, and
`run-clamped-m8o.ps1`. These files do not exist at preregistration time; their
interfaces and verdict rule are fixed here, while their hashes must be frozen
after commissioning and before target output is read
(`experiments/M136-m8o-bar/absence-audit.txt`, "Result: all absent." clause).

Trace v3 must provide, for every expected frame/CFA-site block:

1. protocol version and kernel identity;
2. frame path, input order and source-file SHA-256;
3. full reference geometry and compact output geometry;
4. full-plane Crop origin `(x0,y0)`;
5. CFA site/channel, placement coefficients and transform centre;
6. source-plane dimensions and values;
7. the actual gathered `f32` plane for M8-R;
8. per-frame black level, sensor range and per-channel site gain;
9. the final per-channel output gain; and
10. the scalar types, operation order, rounding mode and clamp semantics of the
    candidate path.

**ASSUMED — independence boundary:** The producer may supply values and fixed
representation parameters. It may not supply a source hull, valid-contributor
mask, crop verdict, or pass flag. The checker independently reconstructs the
Crop rectangle, sample coordinates, geometric validity, exact 4x4 support,
`tau_R`, interval transform, hull reduction and verdict. A producer rectangle
may be recorded only as a cross-check; disagreement is `UNMEASURED`.

**ASSUMED — streaming evidence:** Trace blocks may be deleted only after both
the primary checker and the independent verifier have consumed them
successfully and their block hash has been recorded. The two implementations
must not import Strehl's sampler, hull, contributor, Crop or serialization
code. This prevents another “independent analysis of shared derived arrays”
from being mistaken for an independent reconstruction.

Each capture state must retain:

- complete expected/consumed frame-site manifests and block hashes;
- M8-R totals and every M8-R violation;
- pre-final-saturation and projected aggregate lower/upper arrays;
- a valid-contributor-count array;
- extremising frame identities for aggregate lower and upper bounds;
- final M8-O totals and every M8-O violation;
- the mandatory high/low, at-rail/off-rail disclosure; and
- command, environment, dependency, source, patch, binary, map, TIFF, checker,
  verifier, fixture and runner hashes.

### 7.4 Executable procedure

The exact decision contract is also frozen in
`experiments/M136-m8o-bar/clamped-m8o-preregistration.json`.

1. **Wait for and name the candidate.** Set `$Commit` to the exact commit that
   contains M130 Crop and will be evaluated. Refuse an uncommitted worktree.
   Create a clean source archive below
   `experiments\M136-m8o-bar\out\source-snapshot`; never build or edit the shared
   `crates\` tree. If `clamped-catmull` is not yet production code, apply only
   the recorded zero-margin M134-equivalent clamp plus trace-v3 instrumentation
   to that private snapshot. Record every changed file and before/after hash.

   ```powershell
   Set-Location C:\dev\blog\death-of-software\projects\strehl
   $Commit = '<full post-M130 commit>'
   powershell -NoProfile -ExecutionPolicy Bypass -File `
     .\experiments\M136-m8o-bar\run-clamped-m8o.ps1 `
     -Mode Prepare -SourceCommit $Commit
   ```

   `Prepare` must fail unless `git rev-parse "$Commit^{commit}"` succeeds, the
   private snapshot is clean, `--cover crop` and `clamped-catmull` are present,
   the clamp is raw Catmull-Rom followed once by an exact zero-margin 4x4
   source-support clamp, and the trace format satisfies section 7.3.

2. **Repeat the rule-40 search before freezing the instrument.** Compare the
   new output with
   `experiments/M136-m8o-bar/prior-art-clamped-m8o.txt`; inspect every new
   headline match or prior refusal before proceeding.

   ```powershell
   python .\experiments\ORCH-drift-check\prior_art.py `
     clamped catmull m8-o projected output hull
   ```

3. **Commission before any target TIFF is read.**

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File `
     .\experiments\M136-m8o-bar\run-clamped-m8o.ps1 `
     -Mode Commission -SourceCommit $Commit
   ```

   The M8-R fixture must reproduce exactly: ordinary Catmull hard step
   `28/252` (`14` low, `14` high); zero-margin clamped hard step `0/252`;
   widened-clamp sabotage `28/252` (`14` low, `14` high); copy and bilinear
   nulls zero; and the explicit high/low plant exactly two violations, one of
   each sign.

   The M8-O fixture must produce zero for in-range copy, convex bilinear,
   exact intermediate-quantizer round trip, correct high rail for support
   wholly above one, correct low rail for support wholly below zero, and a
   nonzero-origin Crop identity. It must produce exactly the registered planted
   coordinates for in-range high, in-range low, above-one at code `65534`,
   below-zero at code `1`, one-code-beyond-quantizer, and wrong-Crop-origin
   defects. Trace v2, missing black, missing Crop origin, and missing or
   duplicate frame-site records must each yield `UNMEASURED`, never a partial
   denominator. The exact scalar inputs and expected counts for these cases,
   including the `g=2`, `b=512`, `G=2`, `R=16384`, `z=1001` intermediate
   quantizer pair, are frozen in the machine-readable preregistration.

   Finally, alter only a copy of a commissioned-null TIFF at one registered
   high and one registered low coordinate. The final reader must find both
   coordinates and signs. The instrument author may not certify these controls;
   the independent verifier must do so.

4. **Freeze the instrument before the target run.** Write
   `instrument-freeze.json` containing the preregistration hash, source commit,
   source archive and patch hashes, binary hash, and hashes of the runner,
   trace hook, primary checker, independent verifier and fixture. Record tool
   versions. Any later hash change invalidates the freeze and requires complete
   recommissioning before a result may be read.

5. **Fingerprint each read-only input and placement before rendering.** Use
   `Get-ChildItem -Force -Recurse -File`; record file count, bytes, paths,
   timestamps and SHA-256 content hashes. Copy the three registered clamped
   warp maps into M136 output and verify these source hashes:
   `C817271C015FB2703CE802AC53B9925E17953574D1D39D10D23597DEDAB5E6F2`,
   `0035A701259E5AAA6F61910C7F79B2E1A30BBDEF09A827C258C6919E55ED467F`,
   and `6D855863804B27506003F5ECE4967AA6136A19EDEF33B2CE8E3A567B0FD4D767`.
   `D:\personal\macro` remains read-only.

6. **Render and consume all three target captures.** The runner must clear
   inherited `STREHL_*` variables, then set the exact environment in the
   preregistration. For each of `flat-et1s`, `flat-et2.5s`, and `flat-et6s`,
   it must execute the equivalent of:

   ```powershell
   & $Binary stack $Input --out $Tiff --merge pyramid --cover crop `
     --resampler clamped-catmull --fix-ca off
   ```

   The same invocation must emit the trace consumed by both checkers. No
   output path may leave `experiments\M136-m8o-bar\out\`.

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File `
     .\experiments\M136-m8o-bar\run-clamped-m8o.ps1 `
     -Mode Census -Capture All -SourceCommit $Commit
   ```

7. **Finalize both censuses without changing the instrument.** Apply `F_k,c`
   to each frame interval before reduction, map compact TIFF coordinates
   through the independently reconstructed Crop origin, compare each final code
   by section 6, and emit per-capture plus aggregate JSON. Required statistics
   are:

   - output width, height, full-plane Crop origin, frame count and exact `N`;
   - M8-R denominator, low/high counts, fraction and maximum signed excess;
   - M8-O `V`, low/high counts, exact `V/N`, decimal fraction and percent;
   - maximum positive, minimum negative and maximum-absolute excess in linear
     units and output-code LSB;
   - counts per capture and channel;
   - every violating coordinate with `e`, `O`, `L`, `H`, `q`, sign, excess and
     the frames establishing `L` and `H`;
   - high/low unrepresentable support, each split output-at-rail/off-rail; and
   - zero unbracketed coordinates, zero coverage mismatches and a complete
     frame-site manifest.

8. **Have the independent verifier adjudicate the frozen outputs.**

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File `
     .\experiments\M136-m8o-bar\run-clamped-m8o.ps1 `
     -Mode Verify -SourceCommit $Commit
   ```

   The verifier must independently recompute support, Crop mapping, transformed
   intervals and final classifications from the same value traces, not import
   the primary checker or compare only its saved hull arrays. It must confirm
   exact per-capture and aggregate counts, every violation row, controls and
   hashes.

9. **Re-fingerprint inputs, hash every output, then summarize.** Any input
   mutation, source/hash drift, incomplete trace, checker disagreement or
   unaccounted output is `UNMEASURED`.

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File `
     .\experiments\M136-m8o-bar\run-clamped-m8o.ps1 `
     -Mode Summarize -SourceCommit $Commit
   ```

### 7.5 Decision rule fixed before the number exists

**ASSUMED — preregistered M8-O rule:** Once and only once every commissioning,
completeness, independence and provenance gate above passes, the clamped arm
passes this M8-O experiment iff every capture has `V=0` and aggregate `V=0`.
Any aggregate `V>=1` is a FAIL. A result of `40` is therefore unambiguously a
FAIL, not a near-pass.

**ASSUMED — no nonzero floor:** This is a deterministic exhaustive census, not
a sample estimate. There is no sampling error to price. Source reconstruction
error remains `tau_R`; the exact intermediate container is inside `F_k,c`; and
the final serializer has exactly `q=1/131070`. A new nonzero allowance would
need an independently proved omitted deterministic operation, prospective
versioning, and full recommissioning before looking at a new target result. The
observed clamped residue itself can never license such a floor.

**ASSUMED — disposition of nonzero results:** If `V=40`, diagnose all forty.
If they are producer defects, repair the candidate and rerun it as a new
candidate. If they prove the frozen checker omitted a deterministic
representation operation, retain this protocol's result as `UNMEASURED`,
version the instrument prospectively, and recommission. Do not convert forty
red coordinates into a tolerance after seeing them.

**ASSUMED — combined M8 gate:** A commissioned M8-O zero is necessary but not
sufficient. The same candidate must also have M8-R zero and crop/reference
identity zero. Conversely, failure of commissioning or missing evidence is
`UNMEASURED`, not a candidate PASS or FAIL. A zero on these three development
stacks commissions the candidate mechanism; the scorecard's eventual M8 pass
still requires the same frozen checker on every scored quality capture.

## Could not determine

**ASSUMED — could not independently determine:** The statement that M134 was
dispatched without knowledge of M136 is accepted from the owner's message.
Neither `phase4-results.json` nor its provenance records cross-lane awareness,
so the artifacts cannot prove cognitive blindness. They do prove distinct
scripts and matching conclusions over the same frozen M8 evidence.

**VERIFIED — could not determine:** The per-capture split cannot isolate the
causal effect of exposure time because frame count and cover scale also vary.
This does not affect the direct empty-intersection proof; it limits only the
claim that the split itself is a one-variable natural experiment.

**VERIFIED — could not determine:** The exact historical ambient value of
`STREHL_HULL` for the stage-attribution run cannot be reconstructed from its
provenance. The driver clears and records several `STREHL_*` variables but
neither clears nor records `STREHL_HULL`
(`experiments/M8-overshoot/stage-attribution.ps1`, "Remove-Item Env:STREHL_ALIGN,Env:STREHL_FIX_CA,Env:STREHL_COVER,Env:STREHL_RESAMPLER" clause). The frozen
source says an unset value defaults to `InputRange`
(`experiments/M8-overshoot/out/source-snapshot/crates/strehl-core/src/pyramid.rs`, "Err(_) => Hull::InputRange," clause),
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

**VERIFIED — could not determine:** No post-M130 clamped-Catmull M8-O artifact
exists in the searched repository. The exact Crop denominator, rail-disclosure
counts and violation count therefore cannot be predicted from the old Scale
states. The filename, state-directory and content searches are retained in
`experiments/M136-m8o-bar/absence-audit.txt`.

**ASSUMED — could not determine:** The exact commit that will contain the
accepted M130 implementation, and whether `clamped-catmull` will be production
code or an experiment-only patch at that commit, are not fixed here. The
protocol treats both as explicit frozen inputs and refuses to mix either with a
different binary or source snapshot.

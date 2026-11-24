# Plan X1, engine side: `strehl survey` (2026-11-24)

Author-run, not independently reviewed. Plan:
[`docs/proposals/2026-11-subject-highlights-and-detail-plan.md`](../../../../docs/proposals/2026-11-subject-highlights-and-detail-plan.md)
sections 4 (S2, S4) and 5 (X1, X2). Capture format: [../tiers.md](../tiers.md).

Labels: MEASURED (a command below produced the number), VERIFIED (checked against an
independent result), DERIVED, ARGUED, UNVERIFIED.

## What was built

`strehl survey <folder> [--json <file>] [--print-json] [--subject <json>] [--count 13]
[--no-register] [--decodes 4]` in `crates/strehl-cli/src/survey-cmd.rs` (tests in
`survey-cmd-tests.rs`; `lib.rs` only registers it). Read-only over the capture; `--json`
(or `--out`) is refused inside it.

1. **Shots.** Member 1 of every recorded group with a durable file, a focus target and a
   timed shutter. The shutter and ISO come from the `capture_buffered` event's `exposure`
   (plan X3), else its `capture_intent`, else the camera status the intent recorded. A
   position with two shutters is a pair: longest and shortest. The short shot's partner is
   the long shot at that focus taken nearest it in the journal. The long shutter is the
   pairs' most common long one. The dense cluster is the longest run of single-shutter
   positions no further apart than twice the closest two. With fewer than 5 positions in
   it, every long position is used.
2. **Subject.** `subject_cmd::run_evidence`, `quiet` and `select` (the `strehl subject`
   path) run on up to 13 long frames spread evenly in focus. Alternatively the subject comes
   from `--subject` (a `strehl subject` JSON, a host `Subject` with `rate_ppm`, or a manifest
   with `plan.subject`), or from the survey manifest's `plan.subject`. A given outline gets
   its depth from the same evidence (`select`'s cut and depth rule over the given raster).
   The outline is mapped to each position by its magnification rate about the centre.
3. **Step.** `focus-step`'s tile measure (64 px tiles, green Laplacian energy, half-height
   width, width / 7) is repeated in this file over tiles with at least half their area in the
   subject. `focus-step --subject` was not in this base, so the code is duplicated until that
   lands.
4. **Body.** Long frames of the pairs, subject sites, per colour (RGGB from the active
   origin, greens pooled), as shares of black..white. Highlights are set aside first. A
   confirmed short site above twice the body's 99th percentile, scaled by the pair's
   measured ratio and clear of the short frame's noise by 6 sigma, removes the long sites
   within 2 px of it.
5. **Census.** Short frames, subject sites, short value / measured ratio / (white -
   black). `p999` and `p9999` cover every subject site. `max`, `top` and the highlight count
   cover only sites the long frame confirms: the long frame's brightest sample within 2 px
   must reach half of what the short site predicts, or be pinned. Highlights are confirmed
   sites more than a stop above their colour's body p99.9 by 6 sigma of the injected noise
   model.
6. **Ratio.** Per pair, from 8 px cell means per colour where the long mean is 5 to 70 %
   of the range with no pinned sample, and the short mean is at least 10 of its standard
   errors. The value is the median of the cell ratios. The shutter codes are never used for
   it. They are reported as `commanded`, on the camera's third-stop series 2^(k/3) s (1/60
   is 1/64 s, 1.3 is 1.26 s; DERIVED in the results note's Q3), and as `commanded_marked`.
7. **Advice (X2).** This is effective-seconds arithmetic from the long shutter. The highlight
   pass puts the base at body top 0.8 and the short group at top × 2 at 0.8, each snapped to
   the nearest offered code. Protect is the longest offered code at which top × 2 is at most
   1. Accept is the base code, with the expected pinned subject sites per plane. Above the
   long shutter that count comes from the long frame. Below it, it comes from the confirmed
   short sites. `suggested` is `highlight_pass` when there are highlights and the top exceeds
   twice the body top. The offered codes come from the manifest's
   `initial_status.properties.ShutterSpeed.allowed`, or `camera.properties...` as a fallback.

Every pooled statistic is a sum of per-frame integer histograms, so the output does not
depend on the journal's order.

### JSON keys

Top level: `subject` (as `strehl subject` writes it, the given object, or `null`), `scope`
(`"subject"` or `"frame"`), `depth`, `step`, `body`, `ratio`, `census`, `advice`, `shutters`,
`levels`, `positions` and `summary`.

- `depth`: `first_focus`, `last_focus`, `core_first_focus`, `core_last_focus`,
  `first_plane`, `last_plane`, and `suggested_start` / `suggested_end` (half a sharp width
  added each side; `null` without a width).
- `step`: `width`, `width_p10`, `width_p90`, `suggested_step`, `edge_step`, `tiles`,
  `tiles_considered`, `positions`, `spacing` and `source`.
- `body`: `r`, `g` and `b` (each `p50`, `p99`, `p999`), plus `top`, `sites` and
  `set_aside_sites`.
- `ratio`: `commanded`, `commanded_marked`, `measured` (the median over the pairs) and
  `per_position`. Each `per_position` entry has `focus`, `long_code`, `short_code`,
  `commanded`, `commanded_marked`, `measured`, `per_colour`, `cells` and
  `off_commanded_pct`.
- `census`: `r`, `g` and `b` (each `p999`, `p9999`, `max`), `top`, `margin_stops` (1),
  `highlight_sites`, `highlights`, `pinned_short_sites`, `unconfirmed_sites`,
  `pinned_long_per_position` and `per_position`. Each `pinned_long_per_position` entry has
  `focus`, `pinned` and `predicted`. Each `per_position` entry has `focus`, `max [r,g,b]`
  and `highlight_sites`.
- `advice`: `highlight_pass` (`base_s`, `base_code`, `base_code_s`, `short_s`,
  `short_code`, `short_code_s`), `protect` (`s`, `code`, `code_s`), `accept` (`s`, `code`,
  `code_s`, `pinned_sites_per_plane`), `suggested` and `from_s`. The `*_s` values are ideal
  effective seconds; `*_code_s` is the chosen code as marked.
- `shutters`: `long_code`, `long_s`, `long_effective_s`, `short_code`, `short_s`,
  `short_effective_s`, `iso` and `offered`.
- `positions`: `pairs`, `long`, `dense`, `subject_frames`, `skipped_groups` and `notes`.

[evidence/weevil-b.json](evidence/weevil-b.json) is a complete example.

## Fixtures

No real two-shutter survey existed. Fixtures were assembled in scratch
(`C:/w/shd-census-out/fixtures`, deleted afterwards) by `make-specs.py` and
`make-fixture.py`. Each one copies member 1 of the source groups from the read-only
`D:/StrehlCaptures` runs and writes a positions-run manifest, a plan X3 journal (`tier`,
`exposure`) and durable receipts with the original SHA-256. The specs, which list the
source runs, are in [specs/](specs/).

| Fixture | Pairs (long / short) | Other long positions |
| --- | --- | --- |
| weevil-a | 1/4 s ("owner shutter, first") / 1/60 s at 24972, 25182, 25462 | the rig sweep, 24 positions 2 units apart |
| weevil-b | as weevil-a | 12 positions spread over the owner's weevil stack, plus 24 consecutive stack planes 7 units apart (dense) |
| weevil-a-shuffled | weevil-a with the journal's groups permuted (seed 7) | |
| weevil-last | 1/4 s ("owner shutter, last") / 1/60 s | as weevil-a |
| weevil-13 | 1.3 s / 1/4 s (first) | none |
| pronotum-1s, pronotum-quarter | tonight's ladder at 62000: 1 s / 1/15 s, 1/4 s / 1/60 s | none |

Engine: `target/release/strehl.exe` built from this branch (base `6dcb52098` plus these
files). Private `STREHL_CACHE_DIR`, 4 decodes at once. Runs take 1 to 3 s each. The commands
are in `run-all.ps1`, and the reports in [evidence/](evidence/).

## Gates

**Ratio within the light's 5 % of the commanded.** MEASURED, partly met.

| Pair | Measured | Against commanded (third-stop) |
| --- | --- | --- |
| weevil 24972, 1/60 / 1/4 | 0.06235 | -0.2 % |
| weevil 25182 | 0.06207 | -0.7 % |
| weevil 25462 | 0.05799 | **-7.2 %** |
| pronotum 1/15 / 1 s | 0.06131 | -1.9 % |
| pronotum 1/60 / 1/4 | 0.06118 | -2.1 % |
| weevil-13 24972, 25182, 25462 (1/4 / 1.3) | 0.1995, 0.1969, 0.2123 | +0.5, -0.8, **+7.0 %** |

The two misses share one frame: the 1/4 s "first" exposure at 25462. As the long frame it
reads 7 % bright (the ratio is low), and as the short frame against 1.3 s it reads 7 %
bright (the ratio is high). That one frame was brighter, which points to the light rather
than the method. MEASURED. The prototype's independent four-shot measure at 25462 gave
0.0582 (results note, `evidence/ladder.txt`), against 0.0580 here. With the "last" 1/4 s
rung as the long frame the three pairs read +6.0, +4.6 and -1.4 %, so the light moved over
the ladder (the results note's repeated 1/4 s read 0.945). Within a level band the
measurement is flat: green cell ratios in 0.05 to 0.20 of full scale agree within 1.3 %
(diagnostic run, since removed). The marked codes (1/60 against 1/4 = 0.0667) would put
every weevil pair 6 to 13 % off. The camera exposes on its third-stop series. DERIVED.

**Census places the weevil's glints at 1.3 to 5.2 times the 1/4 s full scale.** MEASURED,
met within about 10 %.

| Position | Census max (G), engine full scale | Same in the prototype's full scale (16383 - 512) | Prototype largest |
| --- | --- | --- | --- |
| 24972 | 2.39 | 2.24 | 2.5 |
| 25182 | 5.72 | 5.35 | 5.2 |
| 25462 | 3.99 | 3.73 | 3.7 |

- The engine's levels for these A7CR frames are black 512 and white 15360. The prototype
  used 16383. Converted, the per-position maxima agree with the prototype's within -10 to
  +3 %. The prototype took the mean of two members at a site in four-shot groups; this
  census uses one sample from member 1.
- Self-check: the short frames predict how many subject sites pin in the long frame.
  - At 1/4 s, 82 / 90 / 163 predicted against 78 / 99 / 157 observed.
  - At 1.3 s, predicted from 1/4 s, 9,897 / 7,810 / 12,326 against 9,819 / 7,769 / 12,283
    (within 1 %).

**A fixture without highlights reports none.** MEASURED, met after two fixes. The input
was weevil-b with `--subject` set to a backdrop box
([evidence/backdrop-subject.json](evidence/backdrop-subject.json)), a near-black region at
p99.9 0.0007. Final: 0 highlight sites, `suggested: accept`, 0 pinned at the accept code.
The 5,233 short sites above the body are reported as `unconfirmed_sites`.

The gate failed twice on the way, on this same input:

1. With the bare rule (sites above twice p99 or p99.9), 4.06 M of 4.06 M sites were set
   aside and 7,811 counted as highlights.
2. Adding the noise guard alone left 3,405 highlights. The short frame's backdrop p99.9 sits
   at about 10 DN above black, 7.5 times the profile's 1.33 DN temporal read noise. Fixed
   pattern and hot pixels have tails that a temporal model does not hold, and they do not
   scale with exposure.

The long-frame confirmation removes them.

The unit tests reproduce both failures:

- `dark_body_has_no_highlights`;
- `fixed_pattern_is_not_radiance`, which fails with the confirmation turned off (`CONFIRM
  = 0` placebo, run and restored).

**Stable to reordering.** MEASURED, met. weevil-a and weevil-a-shuffled give byte-identical
JSON (SHA-256 `87727027...06AD`).

**Unit tests.** MEASURED, 11 pass (`cargo test --locked -p strehl-cli --lib survey_cmd`,
Compiling seen). They cover:

- shutter codes and the third-stop series;
- a ratio measured against a dimmed short frame;
- a glint census with its advice;
- no highlights, a dark body, and fixed pattern;
- order-free pooling;
- classification (retakes, the nearest-in-time partner, long-only positions outside the
  cluster);
- spread;
- outline mapping and `rate_ppm`;
- the step over a tile mask.

## Weevil numbers (weevil-b, MEASURED)

- **Subject:** 36.0 % of the frame, from 13 long frames. Sharp from 24594 to 25714 (the
  core runs 24706 to 25602).
- **Step:** 24 dense positions 7 apart, 653 of 5,271 subject tiles. Width 46.6 units (10th
  to 90th percentile 32.3 to 58.2); step 6, edge 12. `strehl focus-step` on the owner's whole
  stack (199 planes, all tiles) gives 44.1 (33.8 to 58.1), step 6.
  [evidence/focus-step-weevil.txt](evidence/focus-step-weevil.txt). The weevil-a sweep, 2
  units apart over 48 units, cannot measure it: 6 tiles, and the report says so.
- **Body at 1/4 s:** p99.9 is R 0.068, G 0.181 and B 0.073. The medians are 0.009, 0.025
  and 0.011.
- **Census:** top 5.72 (G); p99.99 is 0.135, 0.405 and 0.186; 4,757 highlight sites; none
  pinned in the 1/60 s frames.
- **Advice:**
  - highlight pass: base 1 s (ideal 1.10 s) with a short group at 1/60 (ideal 1/57 s);
  - protect: 1/50 (ideal 1/46 s);
  - accept: 1 s, with about 4,700 pinned subject sites a plane (member 1 only).

  The plan's table gave 1 to 1.3 s, about 1/25 s and 12,000 to 20,600 sites at 1.3 s.
  The weevil-13 fixture observes 7,800 to 12,300 at 1.3 s for member 1, which is consistent.

## Findings for the integrator

- **A7CR white (MEASURED, [evidence/top-values-pronotum-1s.txt](evidence/top-values-pronotum-1s.txt)).**
  The engine reports white 15360 for the A7CR, but the RAW data reaches 16383. The 1 s
  pronotum frame has 1,036 sites at 16383 and 234 between 15360 and 16382. "Pinned"
  (white - 2) therefore counts some unclipped sites on this body, and full-scale units here
  are 7 % larger than the prototype's. Settle this before X4 and X5 define pinned.
- **Prediction off at 1 s on the pronotum (UNVERIFIED cause).** 1,488 sites were predicted
  to pin against 1,018 observed, while the weevil agrees within 10 %. Possible causes: noise
  scatter across a steep tail near pin (the body p99.9 is 0.51), or the white question above.
- **Retakes at a pair's focus.** A dense or retake shot at a sparse position's focus used to
  replace the pair's long frame: in a first fixture the sweep's 25182 moved the ratio by
  +3.3 %. The pair now takes the long shot nearest its short one.
- **Light.** About 7 % frame to frame on this rig (MEASURED above). A per-pair measured ratio
  is required. The census uses each pair's own ratio; a failed measurement falls back to the
  commanded one, with a note.

## What remains

- A real Calibrate survey from the rig (the owner is capturing). The gates above ran on
  assembled fixtures.
- Switch the step to `focus-step --subject` when it lands, and remove the copy.
- Depth is limited to the planes surveyed. The live sweep's loose range (X1 step 1) is not
  read here.
- The desktop side of X2: showing the three choices with noise and time.
- The white-level question above.

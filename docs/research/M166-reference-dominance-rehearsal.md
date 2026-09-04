**REHEARSAL SPECIFIED: 1,092 frames**

# M166 — exact-configuration reference-dominance rehearsal

Status: **PHYSICAL PROTOCOL SPECIFIED; CAPTURE RELEASE REMAINS BLOCKED UNTIL
THE PRODUCTION DOMINANCE MANIFEST IS FROZEN**

## 0. Ruling

**INFERRED BY READING.** The minimum exact-configuration development rehearsal
is one uninterrupted `1,092`-frame sitting on a deliberately non-holdout
target. It mirrors the complete corrected `900`-frame M1 package and adds the
two existing `96`-frame physical control arms. One throwaway histogram frame
makes `1,093` shutter releases. The two M147 magnification-preflight frames
remain outside the sitting.

**VERIFIED BY RUNNING.** The accounting is:

```text
converter-on package                                  320
TC0 package                                           772
                                                     ----
registered rehearsal                                1,092

corrected M1-only score                               900
rehearsal-only sharp and blur controls            +   192
                                                     ----
registered rehearsal                                1,092
```

**INFERRED BY READING.** The combined score contains another `315`
converter-on frames for M5/M9. They neither enter the M1 reference nor the M1
scored-path witness, so replaying them is not part of the minimum M1
admissibility rehearsal. Their omission is allowed only while the frozen
temperature, geometry, illumination, focus, and common-mode gates prove that
the M1 package begins in the same admitted physical state. A full-dress
endurance rehearsal that also repeats those unrelated inputs would be
`1,407` frames; it is not the minimum requested here.

**INFERRED BY READING.** The `1,147` score total in
`M166-reference-information-dominance-physical.md` is superseded. M164's later
frozen witness contract says that `S_1` and `S_2` must each represent one
complete independently acquired scored-path input set. A convenient
fixed-focus burst is inadmissible when the renderer receives a focus stack.
The earlier `96`-frame three-strip TC0 witness therefore cannot be the
dominance witness.

**VERIFIED BY RUNNING.** Replace that `96`-frame block with two complete,
candidate-excluded copies of both registered focus-stack budgets:

```text
TC0-DOM-sw4-A    55
TC0-DOM-sw4-B    55
TC0-DOM-sw10-A   27
TC0-DOM-sw10-B   27
                  --
                 164
```

**VERIFIED BY RUNNING.** The correction is `+68` frames, so the combined score
is `1,215`, not `1,147`.

**INFERRED BY READING.** The accepted `1.32x` TC0 target, hard `1.33x`
maximum, four
converter-on reference strips, and held-out A/B/V calibration design do not
move.

**INFERRED BY READING.** The physical `S_1/S_2` witness costs exactly `164`
registered frames in each rehearsal or score. It must be acquired in the same
uninterrupted subject/session as its matching reference, calibrations, and
scored inputs. A separate witness sitting cannot bound the session-common
terms and is inadmissible.

**INFERRED BY READING.** This report specifies the physical half only. It
adopts the estimator, common-mode charging, simultaneous inference, and
`S_1/S_2` requirements in `M164-reference-dominance.md`; it does not replace
or reinterpret them.

## 1. Zero-frame release gate

**INFERRED BY READING.** The owner must not start the `1,092`-frame rehearsal
from the current repository state. M164's report still says “production
margins unfrozen.” Before the first registered exposure, the registrar must
provide one versioned, hash-bound production manifest containing:

1. the complete licensed cell family;
2. positive `delta_I,k` and `delta_H,k` for every licensed cell;
3. `epsilon_common`, power floors, rank and conditioning bars;
4. the frozen scalar or vector reduction for the complete `S` input;
5. calibration, target, resampler, geometry, software, seed, and checker
   hashes; and
6. a fail-closed reader that emits the M164 family verdict and persistent
   reasons for every refusal.

**INFERRED BY READING.** Missing values may not default to M164's
commissioning-only `0.08`.

**INFERRED BY READING.** The following must also be frozen before the
acceptance rehearsal:

- the final `10 x 8` target artwork class, guards, 33-level tone strip,
  matched featureless sentinels in every reference-strip/field class, and
  fiducials;
- the complete input-only site and focus-selection rule;
- the M165 A/B/V calibration contract and validation thresholds;
- every candidate and comparator binary, setting and native-output adapter;
- the camera sheet, block order, target placement, environment tolerances,
  and frame manifest; and
- the physical blur offset and sharp-control selection rule.

**Exact STOP.** A missing or mutable item above blocks the rehearsal at zero
frames. The two-frame M147 preflight may still be completed; it establishes
scale and field only.

## 2. What “exact configuration” binds

### 2.1 Fixed across rehearsal and score

**INFERRED BY READING.** “Exact” binds all facts that can change the optical,
sampling, noise, calibration, or execution law:

- the same Sony A7C II body, Sony FE 100 mm F2.8 Macro GM OSS, exact Viltrox
  2x converter, support, rail, target carrier, lighting, diffusers,
  polarizers, external power arrangement, recording media class, firmware,
  and RAW mode;
- M mode, ISO 100, `1 s`, marked f/5.6, fixed white balance, EFCS, 14-bit RAW,
  body stabilization off, lens OSS off, and all automatic image corrections
  off;
- converter-on maximum-reproduction reference state and converter-off TC0
  target `1.32x`, never above `1.33x`;
- measured sampling-ratio lower bound at least `2.0`, full target plus guards
  in the common field, and all registered carriers no higher than
  `0.25 cyc/native scored px`;
- ten columns on one iso-depth line and the eight-row depth axis at
  `1.00 degrees +/- 0.02 degrees`;
- four reference strips covering rows `1-2`, `3-4`, `5-6`, and `7-8`;
- complete `sw4` (`55`) and `sw10` (`27`) passes, bracket direction, interval,
  node count, focus-reset approach, start/end witnesses, and acquisition
  order;
- A/B/V calibration class definitions, frame counts, diffuser changes,
  temperature witness, settling-frame exclusions, and no-shared-master
  lineage;
- the target eligibility, mapping, tone, clipping, power, rank, condition,
  matched featureless/flat/dark common-mode, and focus gates;
- the production dominance manifest and all extraction, bootstrap, checker,
  renderer, comparator, and manifest-schema hashes; and
- the same continuous-power, no-disturbance, no-outcome-directed-adjustment
  sitting rule.

### 2.2 Facts allowed to differ

**INFERRED BY READING.** Only independent realization facts may differ:

- the development panel and concealed target seed versus the holdout panel
  and its independent concealed seed;
- session identifier, timestamp, RAW hashes, shot/read noise, and fitted
  calibration-map values;
- measured focus coordinates, pose residuals, illumination and temperature,
  but only inside the already frozen tolerances; and
- the physical calibration frames, references, witnesses, candidate inputs,
  and maps, all of which must be fresh and session-local; and
- unrelated M5/M9 converter-on input blocks, which are omitted from the
  minimum M1 rehearsal because they enter neither `R` nor `S`. Their presence
  in the combined score is admissible only when all M1 start-state,
  temperature, geometry, illumination, focus, calibration, drift, and
  common-mode gates remain inside their frozen tolerances.

**INFERRED BY READING.** Changing hardware, firmware, artwork construction, exposure, lighting,
polarization, target tilt, magnification target, strip count, bracket schedule,
calibration class, reduction, threshold, software, or order after reading a
rehearsal result invalidates exact-configuration transfer. The changed
configuration needs a complete new rehearsal on a fresh development panel and
sitting.

## 3. Non-holdout construction

**INFERRED BY READING.** Before capture, label one independently seeded rigid
stochastic panel `D-REHEARSAL-01 — DEVELOPMENT; NEVER SCORE`. It must use the
same frozen fabrication class as the holdout panel, but it must be a different
separately framed physical panel with an independently generated concealed
code. The holdout panel remains covered, outside every field of view, and
unread.

**INFERRED BY READING.** The complete rehearsal unit is:

```text
development subject D-REHEARSAL-01
+ its one uninterrupted capture sitting
+ every calibration, reference, S witness, candidate input and control frame
  from that sitting.
```

**INFERRED BY READING.** No RAW, calibration map, reference, selected site, rendered output, or fitted
quantity from that unit may enter a score or comparator qualification. The
development candidate/comparator renders are allowed to be read because the
entire unit is intentionally burned.

**INFERRED BY READING.** If a failure is repaired, the failed sitting is not
promoted to a pass by rerunning selected blocks. A manifest/provenance mistake
or a pre-outcome mechanical eligibility failure may be corrected and followed
by a complete fresh sitting on the same permanently burned D panel. Any change
chosen from a cell, dominance, control-sign, power, or target-content result
requires a fresh independently seeded D2 panel as well as a fresh sitting.
This prevents result-directed target or cell tuning from masquerading as
independent validation.

### 3.1 Why this is not the scored session under another name

**INFERRED BY READING.** The physical protocol is deliberately almost the
same, but the statistical role is different:

- the rehearsal is a development unit whose results may diagnose and change
  the apparatus;
- the score is an independently seeded subject/session selected only after
  all such changes are frozen;
- the rehearsal includes `192` physical-control frames that the score does
  not contain; and
- a rehearsal pass only licenses an attempt. The score must independently
  pass the same eligibility and dominance families.

**INFERRED BY READING.** Reading a rehearsal result burns only its predeclared development unit.
Reading a score and then changing placement, focus, exposure, cells, margins,
or software burns the holdout. That development/holdout separation, not a
different camera setting, is the principled distinction.

## 4. Exact physical capture

### 4.1 Registered frame table

**VERIFIED BY RUNNING.**

| Order | Block | Optical state | Rows / focus role | Frames |
|---:|---|---|---|---:|
| 1 | `TR-FLAT-A`, `TR-DARK-A`, `TR-FLAT-B`, `TR-DARK-B` | converter on | frozen A/B calibration classes | `128` |
| 2 | `TR-S01-A/B` | converter on | rows `1-2`, `16+16` | `32` |
| 3 | `TR-S02-A/B` | converter on | rows `3-4`, `16+16` | `32` |
| 4 | `TR-S03-A/B` | converter on | rows `5-6`, `16+16` | `32` |
| 5 | `TR-S04-A/B` | converter on | rows `7-8`, `16+16` | `32` |
| 6 | `TR-FLAT-V`, `TR-DARK-V` | converter on | held-out calibration validation | `64` |
|  | **converter-on subtotal** |  |  | **`320`** |
| 7 | `TC0-FLAT-A`, `TC0-DARK-A`, `TC0-FLAT-B`, `TC0-DARK-B` | converter off | frozen A/B calibration classes | `128` |
| 8 | `TC0-DOM-sw4-A/B` | converter off | complete all-row `55+55` S inputs | `110` |
| 9 | `TC0-DOM-sw10-A/B` | converter off | complete all-row `27+27` S inputs | `54` |
| 10 | candidate `TC0-sw4-A/B`, `TC0-sw10-A/B` | converter off | complete all-row candidate inputs | `164` |
| 11 | candidate reset/start/end witnesses | converter off | frozen positions and return direction | `60` |
| 12 | `TC0-SHARP` near/middle/far | converter off | rows `1-3`, `4-6`, `7-8`; `32` each | `96` |
| 13 | `TC0-BLUR` near/middle/far | converter off | same groups; frozen offset; `32` each | `96` |
| 14 | `TC0-FLAT-V`, `TC0-DARK-V` | converter off | held-out calibration validation | `64` |
|  | **TC0 subtotal** |  |  | **`772`** |
|  | **registered rehearsal** |  |  | **`1,092`** |

**VERIFIED BY RUNNING.** One histogram/setup frame precedes block 1 and is
never registered. **INFERRED BY READING.** The two-frame M147 preflight is a
separate release gate.

### 4.2 Reference strips

**INFERRED BY READING.** For each reference strip, turn Focus Bracket off and
focus at the fiducial-derived centre of its assigned row pair. Take the
`A` repeat (`16` RAWs), move focus away, return from the registered direction,
and take the `B` repeat (`16` RAWs). The A and B halves use disjoint
calibration masters. A guarded site may belong to exactly one strip and may
not cross a focus seam.

**INFERRED BY READING.** The four-strip layout is eligible only when both edge rows in every row pair
clear focus, geometry, power, rank, and common-mode gates in both repeats.

### 4.3 Complete scored-path physical witness

**INFERRED BY READING.** The dominance witness is not a set of fixed-focus
strips. It is two complete, source-disjoint copies of each acquisition budget
the renderer receives:

- one `55`-frame `sw4-A` pass and one independently reset `55`-frame
  `sw4-B` pass; and
- one `27`-frame `sw10-A` pass and one independently reset `27`-frame
  `sw10-B` pass.

Use the exact scored bracket direction, interval, endpoint, exposure, focus
approach, optical state, and target pose. The A and B witness passes use their
corresponding disjoint TC0 A/B calibration masters. The `164` witness RAWs
are excluded by manifest from every candidate and comparator input. They are
reduced only by the frozen candidate-blind pre-render witness path.

**INFERRED BY READING.** The separate candidate input block remains necessary. Feeding a
`TC0-DOM-*` RAW to a candidate invalidates the dominance lineage.

### 4.4 Order and uninterrupted sitting

**INFERRED BY READING.** Capture the table literally from top to bottom.
Remain continuously powered. Do not move the target, camera support, lights,
polarizers, or carrier between blocks. The only intended optical transition
is one converter removal followed by axial movement to the accepted `1.32x`
TC0 placement. Do not reinstall the converter.

**INFERRED BY READING.** The A/B calibration sources precede their subject package; V remains unfitted
and temporally closes that optical-state package. Whole focus passes are
sequential; no per-node exposure interleaving is required or requested.

**INFERRED BY READING.** The protocol fits one sitting by construction: it is one continuous ordered
capture with no teardown. Sufficient external power and recording capacity
for `1,093` releases must be installed before the histogram frame. A power
cycle, card-induced disturbance, target movement, or unregistered pause makes
the sitting ineligible.

**INFERRED BY READING.** No absolute duration is asserted under the host timing
quarantine.

## 5. Full pass/refusal predicate

### 5.1 Licensed population

**INFERRED BY READING.** The physical manifest must contain every tuple in the
frozen production cell family across:

- all four reference strips;
- both registered scored acquisition modes, `sw4` and `sw10`;
- every registered channel;
- all four registered frequency bands;
- all four registered orientations; and
- every frozen subject-region/field partition.

**INFERRED BY READING.** The exact tuple count is the manifest's count. It may not be inferred after
capture because M164 leaves the production channel and region expansion to
the frozen implementation. All 64 required guarded physical sites must remain
available to the cluster population. No cell or site may be deleted after
viewing a result.

### 5.2 Cell eligibility

**INFERRED BY READING.** A licensed cell is ineligible, and therefore cannot
contribute a passing family, if any of the following occurs:

1. wrong or missing hardware, setting, frame, hash, role, order, target,
   calibration class, or provenance;
2. fewer than 64 common guarded sites, duplicated target content, a site
   crossing a strip seam, failed fiducial/plane/scale mapping, or carrier
   frequency outside the frozen band;
3. clipping, failed tone inversion, nonpositive target power, a shared-objective
   null/near-null, insufficient support, or failed local shift-invariance /
   cross-cell-leakage model;
4. reference-strip or focus-stack endpoint, node, coverage, reset, focus,
   geometry, or A/B agreement failure;
5. source overlap between `S_1` and `S_2`, shared A/B calibration-master
   estimation, incomplete `55`- or `27`-frame input budget, candidate contact
   with an `S` RAW, or failed split/autocovariance sufficiency check;
6. failed A/B map or held-out V residual, failed temperature/focus
   portability, or common-mode fraction above the frozen bound;
7. nonpositive common-mode-charged signal or noise, failed rank or
   conditioning bar, invalid bootstrap draw, or zero bootstrap standard
   error; or
8. either simultaneous information-margin or transfer-margin lower bound is
   not strictly positive.

### 5.3 Family result

**INFERRED BY READING.** The rehearsal passes only when:

1. every physical eligibility gate above passes;
2. the M164 common-mode family passes simultaneously;
3. every licensed cell in both scored acquisition modes has a strictly
   positive simultaneous lower bound for its frozen information margin;
4. every licensed cell in both scored acquisition modes has a strictly
   positive simultaneous lower bound for its frozen transfer margin;
5. the fixed-focus blur control clears its registered degradation direction,
   `Q95 < 0.90`;
6. the fixed-focus sharp control clears its registered improvement direction,
   `Q05 > 1.10`; and
7. every manifest, checker, source, output, and verdict hash is sealed.

**INFERRED BY READING.** A missing, invalid, weak, null, or merely partial result is overall
`UNMEASURED`, never `PASS`. A strong strip, band, channel, orientation, field,
or focus density cannot compensate for another. Cell-family narrowing is
lawful only before an untouched validation rehearsal and before the holdout
is opened.

**INFERRED BY READING.** A rehearsal pass cannot guarantee that the
independent scored session passes. Different shot noise, focus realization,
panel instance, temperature, and drift may still produce a score refusal.
The gap is closed by running the same frozen eligibility and dominance gates
on the score: if the score does not independently pass, M1 is `UNMEASURED`.
The rehearsal transfers permission to try, not its numerical result.

## 6. What each failure tells the owner

**INFERRED BY READING.** Every recoverable action below is a development-only
repair. After a repair, freeze it and repeat all `1,092` registered frames in
a fresh sitting; never patch selected blocks into a pass. The same D panel is
permitted only for a pre-outcome mechanical or provenance correction. A
repair informed by cell values, dominance, control sign, power, or target
content requires an independently seeded D2 panel. Permit one
diagnosis-and-repair cycle for a classified setup, focus, exposure, or
calibration fault. If the same cell-local failure recurs on the independent
validation panel after its prerequisite gates pass, classify it by the
persistent optical signature below rather than authorizing another
outcome-directed adjustment.

| Failure signature | Immediate action | Mechanism implicated | Disposition |
|---|---|---|---|
| M147 ratio, common field, packing, tilt, roll/yaw, fiducial or carrier mapping fails | Re-aim, reframe or correct the prescribed axial placement on a setup panel; preserve target `1.32x` and hard `1.33x` | placement / geometry, not dominance | recoverable if a frozen feasible placement exists |
| Reference edge rows, A/B returns, or bracket peaks fail while exposure and target power pass | Correct tilt-axis alignment, strip focus centres, reset approach or focus schedule on development data | **focus error** | recoverable only before a fresh full rehearsal |
| A focus-correct, high-SNR reference repeatedly loses transfer in the same field/orientation cells | Do not add good cells or average; repeat on an independent development panel, then stop the current rig if the pattern persists | **Viltrox aberration / field behavior** | rig-condemning for the frozen family after independent confirmation |
| Transfer clears but information fails broadly because reference noise remains high after valid flats/darks and unclipped exposure | First correct illumination uniformity and histogram on development while retaining the frozen `1 s` exposure; if the protocol itself must change, re-freeze it before fresh validation | **Viltrox transmission loss / reference noise** | recoverable lighting defect first; then rig-condemning at the frozen exposure budget |
| Scored path is stably as strong as or stronger than the focused reference across field, while converter calibration and common mode pass | Do not assume diffraction superiority; require the formal lane's registered optical diagnosis or a different reference path | **bare-lens pupil behavior**, or no physical reference advantage | current rig cannot license those cells |
| Apparent information/transfer improves while featureless, flat or dark common-mode UCB fails | Correct vibration, illumination drift, thermal stabilization, diffuser handling, calibration order or map lineage | calibration/common-mode contamination | recoverable only with fresh A/B/V sources and a full new rehearsal |
| Information and transfer fail only at strip edges and move when focus moves | Re-focus/re-aim the affected strip layout; do not change score cells based on the observed sign | **focus error** | recoverable before fresh validation |
| Information fails while transfer passes and reference photon statistics worsen monotonically, independent of focus | Verify flat/dark/exposure first; if valid and repeatable, stop | **Viltrox transmission loss** | rig-condemning at current frame/exposure budget |
| Transfer fails by orientation/field while information, focus, geometry and calibration remain stable | Repeat once on an independent panel to separate target defect; if persistent, stop | **Viltrox aberration** or **bare-lens pupil behavior** | rig-condemning for affected frozen cells |
| Both paths have a null/near-null or the target lacks licensed power | Replace the development target only if the defect is fabrication/power; otherwise the shared objective cannot identify that cell | shared-objective null or target defect | target-recoverable or claim-family/rig-condemning; never compensable |
| Sharp/blur controls have wrong or impotent signs | Stop capture; return the instrument/control selection to software commissioning before another physical session | instrument or control definition, not owner technique | no score until a fresh rehearsal passes |
| Missing/overlapping RAW, candidate contact with `S`, shared A/B master, power interruption or changed setting | Preserve files for diagnosis but declare the sitting ineligible | protocol/provenance | fresh complete sitting required |

**INFERRED BY READING.** No failure authorizes a relaxed margin, more favorable aggregation, post-result
cell deletion, extra reference exposure, or additional reference frames. Such
a change is a new protocol requiring formal re-freeze and fresh independent
development validation.

## 7. Frame budget

**VERIFIED BY RUNNING.**

| Session | Registered frames | Extra setup releases | Comparison |
|---|---:|---:|---|
| stale prior score | `1,147` | `1` | superseded |
| corrected combined score | `1,215` | `1` | `+68` from complete `S_1/S_2` |
| M1-only corrected score | `900` | `1` | excludes the existing `315`-frame combined M5/M9 block |
| **minimum exact M1 rehearsal** | **`1,092`** | **`1`** | M1-only score plus `192` controls |
| optional full-dress combined rehearsal | `1,407` | `1` | also replays the unrelated `315` M5/M9 frames |

**VERIFIED BY RUNNING.** The operative minimum rehearsal number is `1,092`, which is `55` fewer
registered frames than the stale `1,147` score estimate and `123` fewer than
the corrected `1,215` combined score. **INFERRED BY READING.** It fits one sitting only if the rig,
power, media, thermal state, and target lock survive all `1,093` releases.
That survival is itself part of what the rehearsal tests. The `1,407` option
is an endurance dress rehearsal, not a requirement of the M1 admission gate.

## 8. Paste-ready owner-facing capture text

**INFERRED BY READING — PASTE-READY TEXT FOLLOWS.**

> ### Exact-configuration M1 rehearsal — STOP before the holdout
>
> This is a development rehearsal. Use the separately labelled development
> panel, never the sealed holdout panel. Nothing photographed or rendered in
> this rehearsal may later be used as a scored or comparator input.
>
> 1. **STOP unless the capture sheet is released.** Before taking the first
>    registered frame, confirm that the final target artwork, all licensed
>    cells, both positive dominance margins, the common-mode limit, power and
>    conditioning limits, calibration rules, candidate/comparator versions,
>    frame manifest and fail-closed checker are versioned and hash-frozen.
>    Commissioning defaults are not permission to shoot.
>
> 2. **Use the development subject.** Mount
>    `D-REHEARSAL-01 — DEVELOPMENT; NEVER SCORE`. Keep the sealed holdout panel
>    covered and outside the field of view. The development panel must be a
>    different physical instance with an independent concealed pattern seed,
>    but the same frozen construction, guards, tone strip, sentinels and
>    fiducials. Every reference-strip and field class must contain its frozen
>    matched featureless control.
>
> 3. **Match the scored rig exactly.** Use the registered Sony A7C II body,
>    Sony 100 mm macro lens, exact Viltrox 2x converter, support, lights,
>    diffusers and polarizers. Use M mode, ISO 100, 1 s, marked f/5.6, fixed
>    white balance, EFCS and 14-bit RAW. Turn body stabilization and lens OSS
>    off. Turn automatic corrections, HDR, DRO and noise reduction off.
>    Provide continuous external power and enough recording space for 1,093
>    releases. A power cycle or physical disturbance is STOP.
>
> 4. **Set and verify geometry.** Put the ten-column direction on one
>    iso-depth line. Set the eight-row depth direction to
>    `1.00 degrees +/- 0.02 degrees`. With the converter fitted, use maximum
>    reproduction. After converter removal, target `1.32x` and never exceed
>    `1.33x`. The frozen scale checker must retain a simultaneous lower bound
>    of at least `2.0`, with the full target and guards in the common field.
>    Failed scale, field, packing, tilt or fiducials are STOP.
>
> 5. **Take one histogram frame.** Correct clipping or photon starvation now.
>    Do not register this frame. Once registered capture starts, do not change
>    exposure or illumination.
>
> 6. **Capture converter-on calibration — 128 frames.** Take
>    `TR-FLAT-A`, `TR-DARK-A`, `TR-FLAT-B` and `TR-DARK-B`, 32 each. Move or
>    rotate the diffuser between A and B. Keep the camera continuously powered
>    and record the physical body and temperature witness.
>
> 7. **Capture four converter-on reference strips — 128 frames.** Use
>    `TR-S01` for rows `1-2`, `TR-S02` for rows `3-4`, `TR-S03` for rows
>    `5-6`, and `TR-S04` for rows `7-8`. Focus Bracket must be off. At each
>    strip take 16 A frames, move focus away, return from the registered
>    direction, and take 16 B frames. A guarded site may belong to only one
>    strip. A seam, failed edge row or failed focus return is STOP.
>
> 8. **Close converter-on calibration — 64 frames.** Take `TR-FLAT-V` and
>    `TR-DARK-V`, 32 each. V is held out and may fit neither A nor B map.
>
> 9. **Remove the converter once.** Do not move the target or support.
>     Move the camera axially to the accepted `1.32x` TC0 placement and run
>     the live scale/field check. Any valid ratio below `2.0`, placement above
>     `1.33x`, lost guard or failed geometry is STOP. Do not reinstall the
>     converter in this sitting.
>
> 10. **Capture TC0 calibration — 128 frames.** Take `TC0-FLAT-A`,
>     `TC0-DARK-A`, `TC0-FLAT-B` and `TC0-DARK-B`, 32 each, with the same
>     lineage, diffuser and temperature rules.
>
> 11. **Capture the candidate-excluded physical witness — 164 frames.**
>     Take complete `TC0-DOM-sw4-A` and `TC0-DOM-sw4-B` passes, 55 frames
>     each, and complete `TC0-DOM-sw10-A` and `TC0-DOM-sw10-B` passes,
>     27 frames each. These are complete focus stacks, not fixed-focus strips.
>     Use the scored bracket direction, interval, reset approach, endpoints
>     and exposure. A and B use disjoint calibration masters. Mark every
>     `TC0-DOM-*` RAW as forbidden to candidate and comparator manifests.
>
> 12. **Capture the candidate input block — 224 frames.** Reset by the
>     registered approach, then take the separate candidate
>     `TC0-sw4-A/B` and `TC0-sw10-A/B` stacks, 164 frames total, plus the 60
>     reset/start/end witnesses. Do not substitute any `TC0-DOM-*` frame.
>
> 13. **Capture the physical controls — 192 frames.** Use the frozen
>     input-only selection rule. Take 32 sharp-control frames at each of the
>     near, middle and far positions, then 32 frames at the preregistered blur
>     offset for each position. Do not choose focus after looking at an M1
>     result.
>
> 14. **Close TC0 calibration — 64 frames.** Take `TC0-FLAT-V` and
>     `TC0-DARK-V`, 32 each. V is held out and fits neither A nor B.
>
> 15. **Hash and seal all 1,092 registered RAWs before rendering.** Record the
>     one histogram frame separately. Preserve folder names, counts, order,
>     settings, body identity, temperature witnesses and calibration lineage.
>     Missing, duplicate, overlapping or candidate-touched witness input is
>     STOP.
>
> 16. **Run the frozen reader.** Every licensed cell in every reference strip,
>     channel, frequency, orientation, field region and both focus densities
>     must clear the simultaneous information and transfer bounds. All
>     common-mode, calibration, geometry, focus, power, rank, conditioning,
>     and tone gates must also pass. The blur control must have
>     `Q95 < 0.90`; the sharp control must have `Q05 > 1.10`. One missing,
>     invalid, null, weak or failed cell makes the complete rehearsal
>     `UNMEASURED`; no good cell compensates.
>
> 17. **After any failure, stop.** A setup, focus, exposure or calibration
>     problem may be diagnosed on this development unit, but after any repair
>     the complete rehearsal must be repeated in a fresh sitting. The same
>     development panel may be reused only for a pre-outcome mechanical or
>     provenance correction. If a cell value, dominance result, control sign,
>     power result or target content informed the repair, use a fresh
>     independently seeded development panel. Do not repair selected folders
>     and call the old sitting a pass. A repeated focus-correct transfer failure
>     condemns the current optical configuration for those cells; a repeated
>     transfer-pass/information-fail pattern implicates converter transmission
>     and reference noise. Do not change a threshold, drop a cell or spend the
>     holdout to rescue a failure.
>
> 18. **A pass licenses only the holdout attempt.** The scored session is a
>     fresh `1,215`-frame sitting on the sealed independent holdout panel. It
>     omits the 192 rehearsal-only physical controls and must independently
>     pass every frozen eligibility and dominance gate. A failed score remains
>     `UNMEASURED`. The combined score's additional 315 converter-on focus
>     frames for the other scored checks are not part of this minimum detail
>     rehearsal because they enter neither the reference nor the scored-path
>     physical witness. Their presence is allowed only while every frozen
>     detail-axis temperature, geometry, focus, calibration, drift and
>     common-mode gate still passes.

## 9. Verification and limits

**VERIFIED BY RUNNING.** The deterministic accounting artifact is:

```text
experiments/M166-reference-dominance-rehearsal/analysis.json
```

**VERIFIED BY RUNNING.** The independent fail-closed arithmetic verifier
reports:

```text
PASS: 11/11 checks
```

**VERIFIED BY RUNNING.** It verifies the `164`-frame complete witness, `+68` score correction,
`1,215` corrected combined score, `900` corrected M1-only score, `320/772`
optical-state subtotals, `1,092` minimum rehearsal, and `1,407` optional
full-dress rehearsal.

**INFERRED BY READING.** This report does not claim the rig will pass. It
specifies the minimum complete physical attempt under the current frame
budgets. The production dominance margins and several manifest bars remain
unfrozen, so the owner-facing zero-frame STOP is active until the formal lane
publishes and hashes them.

**INFERRED BY READING.** Controlling sources are:

- `docs/research/M164-reference-dominance.md`, §§2–5, for the estimator,
  no-compensation family, production-margin contract, and complete-input
  `S_1/S_2` witness;
- `docs/research/M164-m1-staged-capture.md`, §§2–5, for A/B/V lineages,
  candidate input budgets, physical controls, staging, and refusal rules;
- `docs/research/M166-reference-information-dominance-physical.md`, §§2–5,
  for the accepted `1.32x` placement, four-strip reference geometry, and
  optical-risk interpretation; and
- `docs/research/M135-detail-instrument.md`, target and physical-control
  sections, for development/holdout separation and target eligibility.

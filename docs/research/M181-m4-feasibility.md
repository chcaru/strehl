# M181 — retained-M4 feasibility from captures already on disk

## Verdict

**VERIFIED BY RUNNING. `M4_RETAINED_BLOCKED_CAPTURE`.** The existing scored
flat captures supply only `55/84` medication sites, `123/83` bee sites, and
`0/83` foam sites under the exact hash-pinned M152 input-only census. The fixed
mix therefore selects only `55 + 83 + 0 = 138` of the required `250` flat
sites. The bee surplus cannot replace either short capture.
`experiments/M181-m4-feasibility/out/flat-probe.json` records the rerun.

**VERIFIED BY RUNNING.** The result is mixed rather than purely photographic.
An already-burned, separate development-flat capture exists:
`D:\personal\macro\flat-fields\flat-fields`, files `DSC00103.ARW` through
`DSC00122.ARW`, supplies all `1,768` M152 raw-green candidates at ISO 100,
marked f/5.6, 200 mm, 1/125 s. It clears the `>=100` raw-site development
floor. Final M166 transfer eligibility is still unmeasured because its RGB
plant-margin test can only be run on common TIFFs, and no real campaign common
TIFF exists.

**VERIFIED BY RUNNING.** The new high-resolution slide capture does not change
the scored-capture verdict. Its three fronto-parallel runs return zero eligible
raw flat sites at 1 s, 2.5 s, and 6 s. They reach zero after 36/60, 13/61, and
8/65 decoded frames respectively.

**VERIFIED BY RUNNING.** Every one of the `9,886` allowed ARWs reports the
ILCE-7CM2, `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`, and 200 mm. M181
found no bare-lens contradiction to M147 in the allowed corpus. The prohibited
holdout was not opened, so M147 remains the source for the larger all-archive
denominator.

**VERIFIED BY RUNNING.** Computational blockers remain after capture. A tracked
source search found no implementation containing either the normative
`M4-TRANSFER-V1` domain separator or the normative random seed
`15240420260904`. There is no M4 matrix/plant materializer or `Q,g,r` scorer.
M165 can convert one RAW to a common TIFF, but it refuses a real conversion
without a matching frozen pattern map, and the shipping `strehl stack` path
still does not perform full common-track RGB registration, noise modelling,
stack output, and directory orchestration.

## 1. Scope and holdout discipline

**VERIFIED BY RUNNING.** The inventory walker descended
`D:\personal\macro` read-only and pruned
`D:\personal\macro\requests\7-aperture-pairs` before opening that child
directory. The prohibited subtree was never enumerated, decoded, rendered, or
measured. The allowed inventory contains `63` ARW-bearing directories and
`9,886` ARWs. See
`experiments/M181-m4-feasibility/out/inventory.json`.

**VERIFIED BY RUNNING.** ExifTool then read the model, lens, focal length, and
stabilization tags from all `9,886` explicitly enumerated allowed files. The
population is exactly:

```text
Model:              ILCE-7CM2 x 9,886
LensModel:          FE 100mm F2.8 Macro GM OSS + 2X Teleconverter x 9,886
FocalLength:        200 mm x 9,886
ImageStabilization: On x 9,886
unexpected frames:  0
```

The machine-readable result is
`experiments/M181-m4-feasibility/out/rig-audit.json`. Paths were supplied to
ExifTool from the already-pruned allowlist; ExifTool was never asked to recurse
the capture root.

**INFERRED BY READING.** Converter-on is not an M4 disqualifier. M166 freezes
the named medication, bee, and foam populations and contains no bare-lens
eligibility condition. The universal converter state matters to shared
common-input calibration, but it does not remove an otherwise eligible M4
site.

**INFERRED BY READING.** M181 reused M152's canonical implementation rather
than recreating the statistic. Before import, the runner requires these exact
SHA-256 values:

- `census_common.py`:
  `3e36a18d8c7b675f224f4fbe694ef2d16297e3e038df18e61cdb4dead219a680`;
- `census-definition.json`:
  `b2e872a6a8214d4fbe379287f52fc57b8f5e61f292aab4c30e96b11d49325879`;
- `m4-freeze.json`:
  `a92b49bd2dc0a661b3319f96e54c7514994292f17f5a0ac0bab0d12cf7cb8d5c`;
- M152 noise-calibration content:
  `47eaf0235c0492ffeabcd0098581f52f22a8d4b8a7241f743c61754476f06566`.

## 2. The authoritative retained bar

### 2.1 Population and flat-power predicate

**INFERRED BY READING.** M166 says literally
(`docs/research/M166-bar-definition-repairs.md:196-199`):

> The scored population is exactly 250 output-blind 128-by-128 native-pixel flat
> tiles: medication pill 84, bee background 83, and foam 83, with no
> cross-capture substitution. Site order is M152's frozen order.

**INFERRED BY READING.** M166 defines
(`docs/research/M166-bar-definition-repairs.md:213-240`):

> `B99_i` is the nearest-rank p99 of that band RMS over:
>
> - 1,000 blends of all source frames with
>   `numpy.random.Generator(PCG64(15240420260904))` and independent
>   `Dirichlet(1,...,1)` weights in generated order;
> - every one-hot source frame; and
> - the uniform source mean.
>
> `Q_i = band_rms(candidate_G_i) / max(B99_i, noise_floor(ISO_i))`.
>
> A missing/invalid output tile has `Q_i=+inf`. Each of the three captures'
> nearest-rank median and the pooled 250-site nearest-rank median must be
> `<=1.00`; any invalid tile is also an immediate candidate failure.

**INFERRED BY READING.** The normalized linear floors are exactly
`1.26102285354196e-5` at ISO 50 or 100 and
`3.72061790502189e-5` at ISO 1000
(`docs/research/M166-bar-definition-repairs.md:228-236`).

### 2.2 Input-only flat-site eligibility

**INFERRED BY READING.** M166 adopts M152's population. M152 says literally
(`docs/research/M152-site-census.md:119-127`):

> Flat candidates are a fixed non-overlapping 128x128-native-pixel grid with a
> 128 px outer margin. A site survives only if **every input frame** passes all
> of:
>
> - its Hann-windowed orthonormal-FFT RMS in `1/60` through `1/20`
>   cycles/native pixel is strictly below the independent temporal-noise p99;
> - low-rail fraction is at most 1%;
> - high-rail fraction is at most 0.1%; and
> - median signal is at least ten temporal sigmas above black.

**INFERRED BY READING.** No failed site may be replaced from another capture.
The flat quotas are independently mandatory
(`docs/research/M152-site-census.md:133-148`).

### 2.3 Transfer eligibility and predicate

**INFERRED BY READING.** The transfer plant is the exact signed integer field
(`docs/research/M166-bar-definition-repairs.md:246-260`):

```text
phase(site,j) =
  2*pi*uint64_be(SHA256("M4-TRANSFER-V1|"+site_id+"|"+j)[0:8])/2^64

P_i(x,y) =
  round_ties_even(
    256*cos(2*pi*(4x+3y)/128+phase(i,0))
    + 256*cos(2*pi*(-3x+4y)/128+phase(i,1)))
```

**INFERRED BY READING.** M166's final site eligibility rule is literal
(`docs/research/M166-bar-definition-repairs.md:256-263`):

> A flat site is eligible only if adding `P_i` to R, G, and B of every source
> common TIFF cannot leave `[0,65535]`; this margin check is input-only and
> occurs before outputs.

**INFERRED BY READING.** For each retained site and each RGB channel,

```text
g = <D,P>/<P,P>
r = ||D-gP||_2/||P||_2
```

and M166 requires literally
(`docs/research/M166-bar-definition-repairs.md:265-273`):

> Every site and channel must have `0.995<=g<=1.005` and `r<=0.005`.
> `<P,P>=0`, any non-finite value, changed output geometry, or a missing twin is
> a candidate failure.

**VERIFIED BY RUNNING.** The denominator arithmetic is `84+83+83=250`
flat-power values and `250*3=750` non-deletable site/channel transfer results:
`252` medication, `249` bee, and `249` foam channel results.

## 3. What each named absence really is

| Named item | Kind | Present today? | Exact producer or missing work | Evidence |
| --- | --- | --- | --- | --- |
| Eligible medication/foam tiles | Capture content, selected computationally | **No** | M152 `census_flat_capture` is the producer of the eligibility census. Existing medication is `55/84`; foam is `0/83`. | **VERIFIED BY RUNNING.** M181 reran the hash-pinned producer. |
| Separate development flat | Capture content | **Yes as a raw-eligible development candidate** | Existing `flat-fields\flat-fields` 1/125-s 20-frame burst supplies `1,768/100` M152 raw sites. M166's later RGB plant-margin test awaits common TIFFs. | **VERIFIED BY RUNNING.** |
| Materialized Dirichlet matrices | Computed artifact | **No** | No producer exists. It must instantiate one PCG64 generator, draw three little-endian binary64 matrices in medication/bee/foam order, and hash the stored bytes before candidate output opens. | **VERIFIED BY RUNNING** tracked-source search; **INFERRED BY READING** for the required algorithm. |
| Materialized transfer plants | Computed artifact | **No** | No producer exists. It must derive concealed phases, materialize exact integer arrays, perform the all-frame/all-channel common-TIFF rail test, and hash the stored bytes. | **VERIFIED BY RUNNING** tracked-source search; **INFERRED BY READING** for the required algorithm. |
| Base/planted common-input renders | Computed artifacts with a capture prerequisite | **No** | `experiments/M165-common-input/converter.py:2080-2168` produces one common TIFF per RAW, but refuses without a frozen matching pattern map. `strehl-common-input` only proves parsing/pre-merge identity and exercises one frame. Full common-RGB stack rendering/orchestration is not implemented. | **INFERRED BY READING.** |

**VERIFIED BY RUNNING.** The tracked implementation search was:

```powershell
git grep -n -- M4-TRANSFER-V1 -- '*.py' '*.rs' '*.ps1' '*.js' '*.ts'
git grep -n -- 15240420260904 -- '*.py' '*.rs' '*.ps1' '*.js' '*.ts'
```

Both returned no tracked implementation match. The seed and transfer domain
separator occur only in prose/freeze artifacts.

**INFERRED BY READING — DECONFLICTION WITH M152.** M152's reported `15/15`
checks, `6/6` killed mutation arms, and `3,000/3,000` charged sites are real,
but they belong to the **M3 side-max commissioning battery**, not retained M4.
The producer loads `manifest["m3"]["sufficiency"]["selected_sites"]`, applies
one-dimensional rim/veil profile plants, and writes schema
`m152-m3-side-max-commission-v2`
(`experiments/M152-site-census/commission_m3_side_max.py:99,161,922,936`).
The M152 report likewise labels the result “reduction-level” M3 commissioning
(`docs/research/M152-site-census.md:407-444`).

**VERIFIED BY RUNNING.** M152 contains no tracked implementation match for
`M4-TRANSFER-V1`. Its only code-adjacent occurrence of seed
`15240420260904` is the declarative `m4-freeze.json`; no M152 source consumes
that seed to materialize matrices. Therefore M152 directly confirms that
plants are computational artifacts, but it is **not** the exact producer of
M4's two-carrier integer plants, Dirichlet matrices, common-TIFF twins, or
`Q,g,r` result. This is a scope distinction, not a contradiction in the bar.

**INFERRED BY READING.** A fifth computational absence is implicit: there is
no checker that consumes the materialized inputs and renders to report the four
capture/pooled `Q` medians plus all `750` `(g,r)` outcomes. OWNER-ACTIONS
already says M4 “also needs a scorer that does not yet exist”
(`docs/OWNER-ACTIONS.md:1293`).

**INFERRED BY READING.** M165 is not blocked merely on orchestration. Its
converter explicitly raises `PATTERN_MAP_REQUIRED` without a frozen matching
dark/flat map (`experiments/M165-common-input/converter.py:2080-2100`), and
M165 records that no eligible real calibration capture, real map, or campaign
common TIFF exists (`docs/research/M165-common-input.md:25-28`). Its current
calibration contract is six 32-frame groups per optical state, `192` frames per
state and `384` across converter-on and TC0
(`docs/research/M165-common-input.md:709-725`). Those are shared common-track
capture prerequisites, not members of M4's 250-site denominator.

**INFERRED BY READING.** M165's residual integration statement is explicit:
the adapter reaches the generic merge core, but shipping `strehl stack` remains
CFA-native; common-track RGB registration, noise modelling, output, and
directory orchestration remain separate work
(`docs/research/M165-common-input.md:793-797`).

## 4. Capture inventory

### 4.1 High-resolution calibration slide

**VERIFIED BY RUNNING.** Exact recursive enumeration of only
`D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl`
found `657` files, all ARW, in exactly six directories: three flat and three
angled. ExifTool read all `657` headers.

| Run | Geometry | Frames | Step width | Exposure | ISO | Aperture |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `flat-et1s-sw4-cpl` | fronto-parallel | 60 | 4 | 1 s | 100 | f/5.6 |
| `flat-et2.5s-sw4-cpl` | fronto-parallel | 61 | 4 | 2.5 s | 100 | f/5.6 |
| `flat-et6s-sw4-cpl` | fronto-parallel | 65 | 4 | 6 s | 100 | f/5.6 |
| `tilted-sw4-cpl` | tilted | 182 | 4 | 1 s | 100 | f/5.6 |
| `tilted-sw10-cpl` | tilted | 92 | 10 | 1 s | 100 | f/5.6 |
| `very-tilted-all-axis-sw10-cpl` | very tilted on all axes | 197 | 10 | 1 s | 100 | f/5.6 |

**VERIFIED BY RUNNING.** Every header reports ILCE-7CM2, the FE 100 mm F2.8
Macro GM OSS plus 2x teleconverter, 200 mm, and image stabilization on. The
three “flat” runs are geometrically flat views of a patterned slide, not
featureless illumination fields.

### 4.2 Scored flat captures already named by M166

| Capture | Geometry | Frames | Step width | Exposure | ISO | Aperture | M152 raw sites |
| --- | --- | ---: | --- | --- | ---: | ---: | ---: |
| `medication-pill-cpl` | pill with flat/background regions | 146 | not recoverable from path or Sony EXIF | 0.2 s | 50 | f/5.6 | 55 |
| `bee-1-cpl` | bee with background regions | 299 | not recoverable from path or Sony EXIF | 70 at 1/3 s; 166 at 0.4 s; 63 at 0.5 s | 100 | f/5.6 | 123 |
| `foam` | fronto-parallel textured foam | 100 | not recoverable from path or Sony EXIF | 74 at 1.6 s; 26 at 2 s | 1000 | f/8 | 0 |

**VERIFIED BY RUNNING.** All three report 200 mm and image stabilization on.
Medication and bee were evaluated over all 146 and 299 frames. Foam exhausted
all 1,768 grid candidates after three frames, so the exact implementation
short-circuited.

### 4.3 Other relevant allowed flats and controls

| Capture | Geometry | Frames | Step width | Exposure / ISO / aperture | Disposition |
| --- | --- | ---: | --- | --- | --- |
| `coffee-bubbles` | fronto-parallel development category | 19 | fixed focus; N/A | 2.5 s, ISO 1000, f/8 | 0 raw sites |
| `flat-fields\flat-fields` | paper illumination field, infinity focus | 18 uninterrupted 20-frame bursts, 360 total | fixed focus; N/A | ISO 100, f/5.6; 1/250 through 1/5 s | 12 bursts have at least one raw site; 11 have at least 100 |
| `flat-fields\subject-focus-sweep-no-cpl` | fronto-parallel paper sweep | 62 | not recoverable | 0.2 s, ISO 100, f/5.6 | 0 raw sites |
| `flat-fields\subject-focus-sweep-with-cpl` | fronto-parallel paper sweep | 62 | not recoverable | 0.2 s, ISO 100, f/5.6 | 0 raw sites |
| `requests\10-paper-iso-var` | fixed-focus paper control | 110 | fixed focus; N/A | 1/8 or 1/2 s, ISO 50-640, f/5.6 | sampled homogeneous ISO groups returned 0 |

**INFERRED BY READING.** The 360-frame flat-field directory is physically
eighteen 20-frame captures: nine exposure settings in a first pass followed by
the same nine in a second pass. `docs/captures-needed.md:1257-1279` records the
owner's two-pass acquisition order, and `docs/research/BUILD-DEFECT.md:13`
independently describes “18 captures x 20 frames.”

**VERIFIED BY RUNNING.** The first pass produced:

| Exposure | Eligible raw sites |
| ---: | ---: |
| 1/250 s | 1,768 |
| 1/125 s | 1,768 |
| 1/60 s | 1,750 |
| 1/30 s | 1,537 |
| 1/20 s | 1,152 |
| 1/13 s | 398 |
| 1/10 s | 29 |
| 1/8 s | 0 |
| 1/5 s | 0 |

**VERIFIED BY RUNNING.** The second pass produced
`1,764, 1,752, 1,606, 1,220, 576, 0, 0, 0, 0` in the same exposure order.
At the long exposures, high-rail failure, not insufficient signal, removes the
population.

**INFERRED BY READING.** These flat-field captures are not registered holdouts
and were already decoded and published by M71, so they cannot be protected
scoring evidence. That makes them suitable for an explicitly registered
development role, subject to the still-unrun common-TIFF plant-margin check.

## 5. Eligibility result

**VERIFIED BY RUNNING.** The exact scored reduction is:

```text
medication: eligible 55, quota 84, shortfall 29
bee:        eligible 123, quota 83, selected 83, shortfall 0
foam:       eligible 0, quota 83, shortfall 83
selected scored flats: 138 / 250
```

**VERIFIED BY RUNNING.** Every medication rejection and every foam rejection is
first attributed to `band_at_or_above_temporal_p99`; neither capture loses a
candidate first to the low rail, high rail, or ten-sigma signal checks. A
different exposure alone is therefore not an evidenced repair for these old
scenes. The repair needs genuinely broad ground with less 20–60-pixel
structure in every frame.

**VERIFIED BY RUNNING.** The high-resolution slide flats are not substitutes:

```text
1 s:   0 / 1,768, all removed by band power
2.5 s: 0 / 1,768, all removed by band power
6 s:   0 / 1,768, 1,730 removed by band power and 38 by high rail
```

**VERIFIED BY RUNNING.** A separate development capture is now available at
the raw-site stage. M181 designates the existing 20-frame 1/125-s burst
`DSC00103.ARW` through `DSC00122.ARW`: `1,768/1,768` raw sites survive, versus
the required `100`. It is source-disjoint from medication, bee, and foam and
was already burned by prior flat-field analysis.

**INFERRED BY READING.** This does not yet prove `1,768` final transfer-eligible
sites. M166 adds the all-RGB, all-common-TIFF `[0,65535]` plant-margin test
after common conversion. The accurate state is therefore:

```text
development capture present:                         YES
M152 raw-green development population >=100:        YES
M166 RGB transfer-margin eligible population >=100: UNMEASURED_NO_COMMON_TIFF
```

## 6. Exact missing capture and proposed shot

**INFERRED BY READING.** Under the retained `84/83/83` population, genuine new
camera work is unavoidable:

1. one fresh protected medication-pill flat/background capture that
   independently supplies at least `84` eligible sites;
2. one fresh protected foam flat/background capture that independently
   supplies at least `83` eligible sites.

**INFERRED BY READING.**
The existing 55 medication sites cannot be concatenated with a new capture,
and the bee surplus cannot cross-fill either quota. The existing flat-field
burst is development-burned and has the wrong semantic role. The slide flats
have zero sites.

**INFERRED BY READING.** No authoritative exact camera sheet currently exists.
M177 explicitly records the missing fields as “Exact frames per capture,
focus-bracket count, optical state, and frozen choice between the two
population versions” (`docs/research/M177-capture-programme.md:108`). M152 and
M166 freeze the acceptance predicate and quotas, not aperture, ISO, bracket
width, frame count, or exposure time. Therefore any numerical shot sheet is a
new protocol that the orchestrator must ratify before capture, not a fact
recoverable from the bar.

**INFERRED BY READING.** A conservative executable M181 proposal, based on the
successful paper-flat exposure and the delivered 60-frame SW4 precedent, is:

- **Medication protected session:** Sony A7C II, FE 100 mm Macro GM plus 2x
  teleconverter and CPL, 200 mm, marked f/5.6, ISO 100, 1/125 s, in-camera
  focus bracket step width 4, exactly 60 frames, body IBIS and lens OSS off.
  Place one pill centrally against a broad matte white-paper field; keep the
  pill and support inside the central quarter so at least 100 non-overlapping
  background tiles remain.
- **Foam protected session:** the identical optical/exposure/bracket settings,
  but a small foam specimen against a separate broad matte field. Keep the
  specimen and support inside the central quarter.
- Use constant diffuse illumination, one uninterrupted bracket per subject,
  and one exposure at each focus node. Before any candidate output is opened,
  run the M152 input-only census and require at least `100` raw sites from each
  capture, deliberately exceeding the hard `84` and `83` quotas to leave
  margin for the later RGB plant-rail veto.

**INFERRED BY READING.** This proposal is intentionally not called frozen. The
1/125-s evidence is strong: two existing 20-frame paper bursts at that setting
yield `1,768` and `1,752` raw sites. The 60-frame/SW4 choice is only a
conservative operational bridge from an existing delivered bracket and must
be approved as a new population version. If the root will not ratify it, the
correct owner instruction is **do not shoot yet; first freeze the M4 capture
sheet**.

**INFERRED BY READING.** No new development flat should be requested now.
Reserve the existing 1/125-s flat-field burst for M4 development. Ask for a new
development capture only if the future common-TIFF RGB plant-margin check
leaves fewer than 100 eligible sites.

## 7. Remaining computational work and cost

**INFERRED BY READING.** After capture, the shortest complete implementation
sequence is:

1. census the two protected captures input-only and freeze a new population
   manifest before opening candidate output;
2. implement and commission the Dirichlet matrix materializer;
3. implement and commission the plant materializer plus RGB rail gate;
4. produce matching real M165 maps/common TIFFs;
5. implement the full common-RGB stack adapter/orchestrator;
6. render three base and three planted candidate stacks with identical
   binary/settings;
7. implement and commission the `Q,g,r` scorer and exhaustive denominator
   report.

**INFERRED BY READING.** The M4-specific matrix/plant/scorer work is about
`2-3` focused engineering days. Completing and commissioning the missing
common-RGB stack/orchestration path is another `3-5` days. This excludes the
shared M165 calibration capture and any licensed comparator work needed by
full M4 rather than the retained component.

**VERIFIED BY RUNNING.** At the old `146+299+100=545` frame counts, one
uncompressed RGB16 common-input copy is about `100.34 GiB`; retaining both base
and planted source twins is about `200.68 GiB`, before outputs and manifests.
The M181 raw census itself took `378.231 s` on this host.

**INFERRED BY READING.** A future retained-M4 run should budget several hours
of conversion/rendering and at least `250 GiB` of working storage, but a
defensible wall-clock cannot be quoted until the common-track renderer exists.

## 8. Is the scorecard verdict stale?

**VERIFIED BY RUNNING.** The overall
`UNMEASURED_CAPTURE_INADEQUATE` verdict is **not stale**. Medication and foam
still fail their independent scored quotas, so the retained component cannot
be measured from captures already on disk.

**VERIFIED BY RUNNING.** One reason printed under that verdict **is stale**:
“a separate development flat” is no longer absent in the capture sense.
`flat-fields\flat-fields` was captured on 2026-08-23, before M166's
2026-09-04 commit, and its 1/125-s development burst has `1,768` M152
raw-eligible sites. The high-resolution slide set was not overlooked by M152;
all three flat runs were explicitly measured and returned zero.

**INFERRED BY READING.** The success-bar row around scorecard line 809 remains
numerically correct and needs no change. The explanatory paragraph and two
readiness rows should stop claiming that the development capture itself is
absent. M181 did not edit the scorecard. Exact replacement text follows.

Replace the paragraph beginning **“Definition and current state of the
retained component”** with:

```markdown
**Definition and current state of the retained component.** The retained component is
now exact, but it is `UNMEASURED_CAPTURE_INADEQUATE`. The scored flat population
still waits on a fresh medication capture supplying at least 84 eligible sites and a
fresh foam capture supplying at least 83; the existing captures supply 55 and 0,
while bee supplies 123 against its quota of 83, so only 138/250 sites can be
selected. A separate burned development-flat candidate now exists:
`flat-fields\flat-fields`, whose 1/125-s 20-frame burst supplies 1,768 M152
raw-eligible tiles; final RGB transfer-margin eligibility awaits common TIFFs.
Materialized Dirichlet matrices and transfer plants, matching pattern-map/common
TIFF inputs, a common-track stack orchestrator/scorer, and base/planted renders
remain absent. None may be replaced by an empty denominator or waived limb.
```

Replace the M4 row in §3.1 with:

```markdown
| M4 | **RETAINED COMPONENT DEFINED; `UNMEASURED_CAPTURE_INADEQUATE`; full M4 (a)(b)(d)** | The retained flat-power/transfer bar is exact, but scored medication and foam remain short at 55/84 and 0/83 raw-eligible tiles, so only 138/250 flat sites can be selected. A separate burned development-flat candidate exists (`flat-fields\flat-fields`, 1,768 M152 raw-eligible tiles in the 1/125-s 20-frame burst), but its RGB transfer-margin eligibility awaits common TIFFs. Materialized Dirichlet matrices/plants, matching pattern-map/common TIFF inputs, a common-track stack orchestrator/scorer, and base/planted renders remain absent. The full disclosure's edge/comparator remainder is still blocked. |
```

Replace the M4 row in the comparison table with:

```markdown
| M4 | Artifact rate | **UNMEASURED_CAPTURE_INADEQUATE** | **UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | M166 defines the retained flat-power/transfer component, but scored medication and foam remain short at 55/84 and 0/83 raw-eligible tiles, so only 138/250 flat sites can be selected. A separate burned development-flat candidate exists (`flat-fields\flat-fields`, 1,768 M152 raw-eligible tiles in the 1/125-s 20-frame burst), but its RGB transfer-margin eligibility awaits common TIFFs. Materialized matrices/plants, matching pattern-map/common TIFF inputs, a common-track stack orchestrator/scorer, and base/planted renders remain absent. Full M4 remains a mandatory disclosure. |
```

## 9. Reproduction and commissioning

**VERIFIED BY RUNNING.** Reproduction commands:

```powershell
python experiments\M181-m4-feasibility\probe_flats.py inventory
python experiments\M181-m4-feasibility\probe_flats.py rig
python experiments\M181-m4-feasibility\probe_flats.py probe
python experiments\M152-site-census\test_census.py
python experiments\M181-m4-feasibility\verify.py
python experiments\M181-m4-feasibility\commission_verify.py
```

**VERIFIED BY RUNNING.** Results:

- M152 targeted tests: `16` passed;
- M181 verifier: `6/6` checks green;
- commissioning: `6/6` exact planted defects killed;
- inert arm: `1/1` remained green;
- commissioning verdict: `COMMISSIONED`.

**INFERRED BY READING.** Every mutation targets one verifier class:
source-freeze mismatch, prohibited-path injection, inventory denominator
mismatch, a planted 100-mm rig population, probe partition mismatch, and
stored-verdict mismatch. Each mutation uses an anchor required to resolve
exactly once. The inert arm changes only unconsumed notes.

**VERIFIED BY RUNNING.** Evidence hashes:

| Artifact | SHA-256 |
| --- | --- |
| `probe_flats.py` | `f4548c73828a0190300fe2aea2cf3069bc080f460f5ff595904cf17da6b79acf` |
| `verify.py` | `c6e214901c0f1b5f96c81d219a235ebac87d37a29b8455db3e9d21d279051066` |
| `commission_verify.py` | `933ec47b633104313b19bdd7f7d814a2c7571269b7c2525ba3a0458a50f7baa9` |
| `out/inventory.json` | `cb2320647448825520c301d223fdd3f02d77eeed1bd018df7e1b01d66f0a151e` |
| `out/rig-audit.json` | `9427dade51b76c022b9b31cf78742b4a96de8e7fee5f867e14204651d10b9c25` |
| `out/flat-probe.json` | `f0833fd14f8fe09324c20c0571d701c7a01aa4993b64782ac12f80146f7aed38` |
| `out/commission.json` | `99eaa36ed8c1166d5737b287c86b5d42546c4a15d7af02d9aff49e34ab806627` |

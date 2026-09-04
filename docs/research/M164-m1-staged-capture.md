# M164 follow-up — staged physical path to an admissible M1

Status: **DESIGN PROPOSAL — BLOCKED ON M165 PATTERN-MAP CONTRACT; DO NOT
SHOOT FROM THIS FILE**

This report replaces the monolithic owner-facing interpretation of the
`2 + 768 + 891 = 1,661` exposure plan in
`docs/research/M164-m1-admissibility.md`. It does not edit the scorecard,
owner actions, or capture request.

## 0. Ruling and correction

**ARGUED.** M164 remains an admissibility gate, not a detail score. An
admissible M1 still needs the independent physical truth architecture
described in `docs/research/M135-detail-instrument.md`: positive
truth-referenced information, non-compensating truth-transfer and unexplained
structure witnesses, independent calibration, physical blur and improvement
controls, and a frozen numerical decision rule. Nothing in this staging plan
revives an output-only statistic.

**DERIVED — first correction to M164's earlier count.** The `891`-frame
scored session is a combined M1/M5/M9 request. It is not the smallest
presently specified M1-only sitting. Before M165's finding, M1's named roles
were:

| M1 scored role | Frames |
|---|---:|
| converter-on fixed-focus reference, near/middle/far | `96` |
| converter-on flat A/B and dark A/B | `128` |
| converter-off `sw4-A/B` and `sw10-A/B` | `164` |
| converter-off reset/start/end witnesses | `60` |
| converter-off flat A/B and dark A/B | `128` |
| **pre-M165 M1-only scored sitting** | **`576`** |

The converter-on focus ladders and their `60` witnesses account for the
remaining `315 = 891 - 576` frames. They serve M5/M9, not the inverted M1
truth comparison. Omitting those blocks defers M5/M9; it does not remove an
M1 acquisition role.

**CROSS-LANE CORRECTION.** Those rows contained generic A/B flat and dark
photons, but they did not define an M165-admissible deterministic-pattern map:
no map estimator, capture-match rule, dedicated held-out validation source, or
manifest binding had been frozen. They were therefore functionally missing
from the common-input contract even though `256` calibration frames appeared
in each rehearsal/score budget.

M165 requires disjoint estimation and held-out validation. The conservative
base package proposed here is:

| Pattern-map role | Frames |
|---|---:|
| `FLAT-A`, independent map-A source | `32` |
| `DARK-A`, independent map-A source | `32` |
| `FLAT-B`, independent map-B source | `32` |
| `DARK-B`, independent map-B source | `32` |
| `FLAT-V`, used only for held-out validation | `32` |
| `DARK-V`, used only for held-out validation | `32` |
| **one dark class plus one flat class** | **`192`** |

The `A` and `B` maps preserve M135's disjoint output/reference lineages. `V`
is never fitted and tests both maps. The `32`-frame block size is inherited
from the current capture contract; it is a **proposed floor**, not an M165
measurement. M165 explicitly left the required count open pending a frozen
held-out residual-precision rule. Stage 0M below must commission that rule
before the owner is asked for these frames.

If M165 admits one dark-temperature class and one focus-valid flat class for
each optical state (converter-on and TC0), the corrected path is:

```text
2-frame geometry preflight
+ 896-frame non-holdout physical/pattern-map rehearsal
+ 704-frame sealed M1-only score
= 1,602 registered/setup exposures
```

The scored request already requires one unregistered histogram exposure, so
the known shutter-release floor is `1,603`. Setup retries are not hidden in
that number: each extra M147 pair adds two releases, and any invalidated
development stage must be counted again.

That `1,602` is a **conditional floor**, not yet an executable total. It
assumes, in each sitting, two dark classes (converter-on and TC0) and two flat
classes (converter-on and TC0), and that each flat-gain correction is valid
across its complete registered focus schedule. Each additional independently
matched dark-temperature class adds `96`; each additional flat-focus class
adds `96`. No repository evidence yet licenses the two-plus-two assumption.

## 1. Existing-corpus exhaustion before any new-frame request

### 1.1 Holdout ruling first

The authoritative files were read in the required order:

| Artifact | SHA-256 |
|---|---|
| `experiments/M141-capture-inventory/holdout-register.json` | `804102b54cba607bd500e595e636142d2d8b80f0ad053e43f56f1df9bfd31488` |
| `experiments/M141-capture-inventory/capture-manifest.json` | `e2849d543cb126ab95ad342f2a3a1a96f4b6f5658548025007f593ddd5764b03` |
| `experiments/M141-capture-inventory/capture-stacks.csv` | `ae0ac8b283b0009f56535ba868c312f9faf77d223b567d8ef1fbdc682818b66a` |

**VERIFIED FROM THE REGISTER.** The `68` stack directories divide into:

- `11` directories in two burned development units: the five-stack
  `calibration-grid-2026-09-01` session and six-stack
  `high-res-calibration-slide-2026-09-02` session;
- `6` explicit `NOT HOLDOUT` control/historical rows;
- `16` clean registered holdout rows; and
- `35` `INDETERMINATE — DO NOT ASSUME CLEAN` rows.

Only the burned and explicit-not-holdout material was considered available for
development use. No clean or indeterminate RAW was decoded, rendered, or
scored for this audit. The source trees remained read-only.

The slide path is not merely nominally burned: before this amendment the
repository already contained `61` files referring to it, including released
geometry and M8 work. The register's whole-session ruling therefore controls
all six members.

### 1.2 Cross-cutting geometric result

**VERIFIED FROM M141 METADATA.** All `10,509` inventoried ARWs report:

- camera `ILCE-7CM2`;
- focal length `200 mm`;
- lens protocol string
  `FE 100mm F2.8 Macro GM OSS + 2X Teleconverter`; and
- `ImageStabilization: On`.

Physical reproduction ratio is recoverable from metadata for `0` stacks.
Thus no existing capture proves the required bare-lens TC0 state, accepted
`M_work`, or stabilization-off geometry.

M1's reference requirement is not “more focus-bracket frames.” It is a
fixed-focus near/middle/far atlas of the **same physical patch** at
independently measured subject sampling satisfying
`LCB95(M_reference/M_scored) >= 2.0`, stronger object-space transfer in every
licensed cell, different sensor footprints, and disjoint matched
calibration. A dense `sw1`/`sw4` stack at the same lateral sampling cannot be
promoted into that reference, and a merge of it would be circular truth.

### 1.3 Candidate-family rulings

| Existing family | Holdout status | M1 truth-reference ruling | Development value that remains |
|---|---|---|---|
| `requests\misc-diagnostic\high-res-calibration-slide-cpl` — six stacks, `657` frames | **BURNED — DEVELOPMENT OK** | **NO.** All six are converter-on, 200 mm, stabilization-on. The `flat-*` name describes a fronto-parallel patterned slide, not a uniform illumination flat. The three tilted stacks are focus brackets, not fixed-focus reference halves; there is no same-session TC0 partner, no measured `>=2x` ratio, no disjoint matching pattern map, and no full stochastic target/sentinel/tone contract. | Reference-resampler, registration, focus-density, flat-path/null and failure-branch commissioning already use it. It cannot demonstrate the final native-geometry success path. |
| `requests\30-calibration-grid` — five stacks, `242` frames | **BURNED — DEVELOPMENT OK** | **NO.** It is a predictable periodic grid, converter-on and stabilization-on. The apparent `55`-frame sw4 and `27`-frame sw10 matches are not bare-lens A/B pairs and have no higher-sampling fixed-focus atlas. | Step-width, coverage, registration and rejection-path development only. |
| `requests\6-11-extended-dark-frames` — `506` frames | **NOT HOLDOUT** | **NOT A TRUTH CANDIDATE; NOT SCORE CALIBRATION.** Its only ISO-100/1-s segment has `22` frames, not a `32`-frame A/B/V group, and it was not acquired at the future session's sensor temperature. It is converter-on/stabilization-on and has no paired matching flat. | Dark-estimator and temperature-sensitivity development, without frame credit to rehearsal or score. |
| `flat-fields\flat-fields` plus its with/without-CPL focus sweeps | **INDETERMINATE — DO NOT TOUCH** | **NO USE AUTHORIZED.** Metadata alone shows converter-on, stabilization-on data. The uniform-flat directory stops at `0.2 s`, not the required `1 s`; its focus is infinity. The two subject sweeps are `0.2 s`, not flat fields or a higher-sampling reference. | None unless the orchestrator later classifies the whole subject/session. No pixels were read here. |
| `requests\10-paper-iso-var` | **NOT HOLDOUT** | **NO.** Textured printer paper is a scene/noise control, not a spatially uniform flat or an independently oversampled reference; its exposures are `0.125/0.5 s`. | Noise and flat-null development already allowed; no M1 frame credit. |
| `requests\19-razor-edge` | one f/5.6 horizontal stack **NOT HOLDOUT**; the other five **INDETERMINATE** | **NO.** All are converter-on, stabilization-on, deterministic edges at `2.5/3.2 s`, with no same-session TC0/reference pair or M165 map. | The explicit control row may support edge-algorithm development. Indeterminate siblings remain untouched. |
| `requests\7-aperture-pairs` and `requests\8-tilted-planar` | mixed clean registered holdout and indeterminate rows | **DO NOT TOUCH.** Metadata already rules them out: converter-on, stabilization-on, no fixed high-sampling atlas, no measured magnification ratio, and no TC0 partner. | Preserve their existing holdout roles. |
| clean natural-subject rows (`bee-1`, fabric, rulers, duck tape, chia, flower/fern, pill, foam, battery, salt) | **CLEAN REGISTERED HOLDOUT** | **DO NOT TOUCH.** None has a registered same-subject higher-sampling fixed-focus reference or bare-lens counterpart; all report stabilization on. | Preserve for their registered axes. |
| explicit historical/development scenes (`coffee-bean`, `113MSDCF`, `coffee-bubbles`) | **NOT HOLDOUT** | **NO.** They are single optical-state stacks with no independently sampled same-session truth, no required repeats/calibration, and incompatible capture settings. | Renderer/veto development only. |
| remaining general stacks | **INDETERMINATE — DO NOT ASSUME CLEAN** | **DO NOT TOUCH.** Their metadata shares the converter-on/stabilization-on disqualifiers, so no pixel inspection is needed to reject them as M1 truth. | None without an explicit holdout ruling. |
| rendered files under `D:\edited\macro` | not raw capture candidates | **NO.** A rendered output cannot become the external physical truth or sensor pattern calibration for another rendered output. | Historical output diagnostics only. |

### 1.4 Existing-data subtraction

M141 already evaluated the two predecessor capture designs block by block:

- committed `603`-frame design: `0/24` blocks satisfied, `0` existing frames
  creditable;
- live `448`-frame inverted block: `0/21` blocks satisfied, `0` existing
  frames creditable.

The new M165 blocks also receive zero credit. The `22` matching-setting darks
are too few and not temperature-matched to a future session; the available
uniform-flat metadata is wrong-exposure, wrong-focus, stabilization-on and
indeterminate; the slide's “flat” runs are patterned focus brackets rather
than diffuser flats.

**DERIVED.** Existing captures reduce software-development work, but they
replace **zero physical frames** in the exact rehearsal or sealed score:

| Route | Before corpus subtraction | Existing eligible frames | After subtraction |
|---|---:|---:|---:|
| conditional M1-only path | `1,602` | `0` | **`1,602`** |
| conditional combined M1/M5/M9 path | `1,917` | `0` | **`1,917`** |

Both totals remain conditional on M165 freezing the focus/temperature class
count. This is not a claim that the corpus is useless. It has already paid for
synthetic/real development of M147 geometry, reference resampling, focus
coverage, failure paths and M165's no-map refusal. Those are zero-frame
software prerequisites, not interchangeable photons in the registered
physical protocol.

### 1.5 Stage 0 judgement

**JUDGEMENT — Stage 0 cannot be reduced to zero new frames.** It requires one
real converter-on and one physically unmoved converter-off image of the same
coplanar grid. Every inventoried RAW reports the converter-on protocol
identity, and no existing stack has a measured bare-lens reproduction ratio.
Synthetic resampling and the burned slide have already commissioned the code,
but neither tests the real optical-state change. Stage 0 therefore remains
two fresh frames, with an optional second pair only if M147 prescribes a new
placement.

## 2. Release conditions before asking for Stage 1

**PROPOSAL.** The two-frame M147 preflight may proceed under its existing
owner ask. No later physical stage should be released until all of these
zero-frame conditions are true:

1. Every stage has a non-interactive, fail-closed checker that writes a
   persistent verdict. Missing inputs, malformed manifests, failed provenance,
   and numerical exceptions must return a typed failure and nonzero exit.
2. M165's pattern-map estimator, held-out residual statistic and acceptance
   threshold are implemented, commissioned, versioned and hash-frozen. The
   accepted map cardinality across optical state and focus is explicit.
3. The M165 schema/validator can bind the independently recorded physical body
   identity, temperature witness, focus state or focus-interpolation domain,
   and held-out validation hashes/result. The current files do not yet enforce
   all four facts; see Stage 0M.
4. The M1 extraction code, site population, frequency cells, tone inverse,
   geometry rules, calibration lineage, reference-side resamplers, M164 gate,
   physical-control selection algorithm, and synthetic battery are versioned
   and hash-bound.
5. The target contract is reconciled. “Any stable irregular patch” is not by
   itself enough for the full claim. The selected one-use target must either
   pass M135's complete 64-site/nonduplication/power/sentinel/tone eligibility
   contract, or the concealed-code development/holdout panels must be used.
   A narrower natural-target statement requires an explicit scope ruling; it
   may not be substituted silently.
6. Common-input conversion and every required comparator binary, license,
   version, setting, native-size output adapter, and hash are executable on
   development data. The target specimen/seed is chosen only after that
   freeze.
7. The owner-facing bench sheet fixes the exact optical state and input-only
   selection rule for the two `96`-frame physical controls. This proposal
   assumes converter-off fixed-focus controls at accepted `M_work`: one
   input-selected sharp position and one preregistered focus offset, each at
   near/middle/far. The orchestrator must ratify that assumption.
8. The camera, target, light, and support can remain powered, warmed, and
   physically locked while development-stage results are read. If not,
   the physical stages cannot lawfully be spliced across changed setups; after
   the desktop gates pass, the full rehearsal must instead be one development
   sitting.

The final numerical M1 margins may use arm-blind power information from the
rehearsal, but every margin, reduction, uncertainty rule, executable, and hash
must be frozen before the sealed score starts.

## 3. Staged capture with falsification gates

The original physical rehearsal remains `768` frames. M165 adds one dedicated
`FLAT-V/DARK-V` validation pair per optical state, `2 x 64 = 128`, making the
conditional two-optical-state rehearsal `896`. The rig remains locked between
physical stages. A pause for analysis is allowed only while the camera,
target, illumination, polarizers, roll/yaw, and environment remain unchanged.
A disturbance that breaks cross-state geometry restarts the optical-state
package.

### Stage 0M — zero-frame M165 contract gate

**Why it precedes capture.** The actual pattern-map photons do **not** belong
before Stage 0: `M_work` and the focus schedule are not yet accepted, flats
must match them, and dark temperature is not reusable across a later warmed
session. What belongs before Stage 0 is the map contract and reader.

Before any calibration exposure, freeze:

1. the estimator and exact residual statistic;
2. the held-out pass/fail threshold and minimum usable count;
3. whether A/B require two maps or the scorecard's singular “one map” is
   intended campaign-wide;
4. the definition and number of focus-calibration classes, or a validated
   focus interpolation/invariance rule;
5. a temperature witness, tolerance and interpolation/refusal rule; and
6. the manifest fields that bind all of those facts.

**Exact STOP.** If those six items cannot be expressed and validated before
the first calibration frame, do not ask the owner to capture Stage 1. M165's
converter must continue to return `PATTERN_MAP_REQUIRED`.

**Manifest gap to route.** `m165-common-input-manifest-v2` hashes and embeds
the `m165-sensor-pattern-map-v1` manifest, but the current pattern validator
compares one EXIF-derived `capture_match` object exactly. On this body,
serial, focus distance and camera temperature may be `null`. The template has
no required held-out-validation hashes/result, external physical-body
identifier, external temperature witness, or declared focus interpolation
domain. Extra JSON could be hash-bound but would currently be ignored by the
validator. M165 or the registrar must extend and commission that contract;
M164 must not invent a parallel manifest.

There is also a cardinality ambiguity to resolve. M135 requires A and B not to
share a calibration master because common estimation error can masquerade as
repeatable detail. The scorecard and M165 describe “one frozen
deterministic-pattern map,” while M165's per-source manifest can technically
point different sources at different map hashes. The registrar must state
whether “one” means one frozen method or literally one shared fitted map. A
literal shared map conflicts with M135's lineage defense unless an independent
argument and blank-residual gate bound its shared estimation error.

This plan adopts, rather than duplicates, M165's frozen converter:
rawpy `0.27.0`, LibRaw `0.22.1`, executable-bundle SHA-256
`09987d67aee229b6075001748bcd20f17b0cf47e0e42f238a9fc8940595fd95d`,
and the `m165-common-input-manifest-v2` output envelope. Any M165 amendment
must preserve or deliberately supersede that freeze and record the new hash.

### Proposed pattern-map capture unit

This is the exact capture unit to commission, not a change to M165's file
format:

| Group | Count | Required physical match | Role |
|---|---:|---|---|
| `DARK-A` | `32` | same recorded body, sensor fingerprint, ISO 100, `1 s`, RAW mode and registered temperature class; lens capped/light sealed | map-A offset estimate |
| `FLAT-A` | `32` | same body, ISO 100, `1 s`, lens, converter state, focal length, marked f/5.6 and registered focus class/schedule | map-A gain estimate |
| `DARK-B` | `32` | same dark conditions, disjoint exposures | map-B offset estimate |
| `FLAT-B` | `32` | same flat conditions, diffuser moved/rotated, disjoint exposures | map-B gain estimate |
| `DARK-V` | `32` | same dark conditions, temporally bracketing the subject block, never fitted | held-out offset/temperature validation |
| `FLAT-V` | `32` | same flat conditions, exercising the registered focus-portability challenge, never fitted | held-out gain/focus validation |

The first two frames of every dark group remain registered but are excluded as
settling frames, matching the existing protocol. No frame may cross
rehearsal/score, optical state, or admitted calibration class. Every original
ARW path, size and SHA-256 must be bound through M165's manifest chain.

The `32` count is deliberate but provisional: the current calibration analysis
estimates about `0.084%` relative RMS for a 32-frame flat master at `10000 DN`
and about `0.16 DN` model floor for the 30 usable darks after settling
(`docs/research/M-FRC-VIABILITY.md`, §1.4). Those numbers support trying the
existing block size; they do not commission M165's as-yet-unwritten residual
bar. Stage 0M must retain the right answer—more frames or STOP—if its power
calculation rejects `32`.

### Stage 0 — two-frame shared-optic kill test

**Capture and cost.** The live M147 request: one converter-on RAW at maximum
reproduction and one physically unmoved converter-off RAW near the intended
working magnification. Owner cost is the already stated approximately five
minutes. M147's measured full-resolution analysis runtime is `25.40 s`; that
is compute time, not a capture-duration promise.

**What it buys.** It field-commissions the sampling-ratio estimator at a real
optical-state change. Combined with the predeclared target field and carrier
bounds, it tests the feasible working-magnification set:

```text
F = M_work values for which
    LCB95(M_reference / M_work) >= 2.0,
    the complete target and guards remain in the common field,
    all licensed carriers map to <= 0.25 cyc/native scored px,
    and M147's local geometry gates are satisfied.
```

**Exact STOP.** Stop the current shared-prime inversion if `F` is empty. A
valid M147 reading below `2.0` at the lowest otherwise eligible `M_work`, or
incompatible field/frequency constraints that make every ratio-clearing
setting ineligible, is a design falsification rather than a request for more
score frames.

An input-quality refusal such as `NO_COHERENT_GRID` means correct the two-frame
capture and rerun Stage 0; it is not evidence that M1 works or that the optical
design is impossible. If `F` is nonempty but the first TC0 placement is
outside it, allow one tool-prescribed two-frame verification at the selected
setting. A second **valid numerical** failure at the lowest eligible setting,
or an empty feasible set, is design STOP. Repeated quality refusal blocks the
bench procedure for diagnosis but is not misreported as an optical
falsification. No 96-frame block begins on a provisional lens label or EXIF
magnification.

### Stage 1 — converter-on pattern-map sources, 128 frames

**Capture.** With the converter on at maximum reproduction, acquire
`FLAT-A`, `DARK-A`, `FLAT-B`, and `DARK-B`, `32` frames each. These are
estimation sources for independent A/B maps, not generic calibration:

- darks: the same recorded physical ILCE-7CM2 body, ISO 100, `1 s`, RAW mode
  and warmed sensor state as the reference; no power cycle;
- flats: the same body, ISO 100, `1 s`, Sony FE 100 mm F2.8 Macro GM,
  marked f/5.6, 2x Viltrox fitted, maximum-reproduction state, and the frozen
  focus class/schedule from Stage 0M; and
- every file: separate folder, role, capture-order record and SHA-256.

The illumination must be spatially uniform and unresolved at licensed
frequencies. Move or rotate the diffuser between A and B. Retain but exclude
the first two settling darks. The physical order must put dark samples near
the reference block; a distant calibration sitting is not temperature
matching.

**GO/NO-GO.** The frozen estimator must produce finite positive A/B maps with
the registered shape, sensor fingerprint and source provenance. A/B source
sets must be disjoint and must not include subject RAWs. Clipped/textured
flats, light-leaked darks, wrong metadata, wrong body identity, failed
temperature witness, or map-estimator failure is STOP before the reference
atlas. This is only a provisional map gate; dedicated held-out validation
arrives in Stage 2.

### Stage 2 — reference plus held-out map validation, 160 frames

**Capture.** Without changing the optical state or target geometry:

- shoot three fixed-focus `32`-frame reference bursts at near, middle and far,
  with Focus Bracket off (`96`); and
- acquire `FLAT-V` and `DARK-V`, `32` each (`64`), never used to fit either
  map.

The V dark must temporally bracket the reference with the Stage 1 darks; the V
flat must exercise the frozen focus-matching or focus-portability rule rather
than repeat a convenient unmatched setting.

**What it buys.**

- common-field and atlas-strip coverage;
- at least 64 unique guarded candidate sites;
- reference-side power in all 16 registered cells;
- two independently corrected reference halves;
- clipping, rail, bit-depth, fiducial, focus-seam, and 33-level tone-witness
  eligibility;
- held-out flat/dark residuals for both A and B maps; and
- evidence that temperature/focus matching survived the complete
  converter-on package.

**GO/NO-GO.** Proceed only if every scored site belongs to one registered
reference strip, all required cells have measurable reference power, at least
64 sites survive, the tone strip is monotone and unclipped, each burst is
stable, and both maps pass the frozen V residual and temperature/focus match
gates. Any population, power, clipping, tone, atlas, residual, body,
temperature, focus, or geometry failure is STOP before converter removal.

### Stage 3 — TC0 pattern-map sources, 128 frames

**Capture.** After the live M147 ratio passes, remove the converter and move
the camera axially only. At accepted `M_work`, acquire TC0 `FLAT-A`,
`DARK-A`, `FLAT-B`, and `DARK-B`, `32` each, under the same matching rules as
Stage 1 except that the converter is absent and the frozen TC0 focus
class/schedule applies.

**GO/NO-GO.** Require finite, positive, disjoint, correctly shaped provisional
TC0 A/B maps and matching body/ISO/exposure/aperture/optic/focus/temperature
witnesses. Failure is STOP before the focus ladders.

### Stage 4 — exact converter-off focus rehearsal, 224 frames

**Capture.** Remaining converter-off at the accepted Stage 3 geometry,
preserve the target and four or more fiducials, and shoot:

- `164` frames: complete `sw4-A/B` (`2 x 55`) and `sw10-A/B`
  (`2 x 27`) passes; and
- `60` frames: TC0 reset/start/end fixed-focus witnesses.

Use the score's exact direction, interval, exposure, stabilization state,
reset approach, and `M_work`.

**What it buys.**

- actual `sw4`/`sw10` gap-free coverage at `M_work`;
- 64-site interior focus peaks in both complete A/B passes;
- G0–G3 fixed-focus, reset, endpoint, node, geometry, and spectral
  repeatability;
- native geometry and reference-to-TC0 mapping;
- provisional per-cell reference-transfer superiority; and
- the input-only focus geometry needed by the preregistered control-selection
  algorithm.

**GO/NO-GO.** Proceed only if the live M147 check still passes, every G0–G3
predicate passes, no A/B re-indexing is needed, both widths have gap-free
coverage and interior peaks at at least 64 common sites, and the reference
maps legally to TC0. A failed width, endpoint, node, map, or site floor is
STOP. If `M_work`, target, camera pose, or optical mapping changes, restart
Stage 1; do not reuse a no-longer-matched reference.

After this stage, run the frozen **input-only** rule to select and register the
sharp-control focus positions and blur offset. Do not inspect a desired M1
sign and then choose the frames that produced it.

### Stage 5 — physical controls plus held-out TC0 map validation, 256 frames

**Capture.** Before disturbing the target, shoot:

- `96` converter-off fixed-focus sharp-control frames, near/middle/far; and
- `96` converter-off fixed-focus focus-offset blur-control frames,
  near/middle/far.

Then shoot TC0 `FLAT-V` and `DARK-V`, `32` frames each, never used for map
fitting. Their dark timing and flat focus schedule must provide the
preregistered held-out challenge for the Stage 3 maps. This completes the
conditional two-optical-state `896`-frame rehearsal:

```text
128 + 160 + 128 + 224 + 256 = 896.
```

**What it buys.**

- the mandatory physical pre-noise degradation and improvement directions;
- calibrated truth-relative `J_TR`, transfer, and unexplained-structure
  behavior end to end;
- separate output/reference and A/B calibration lineages plus dedicated
  held-out pattern-map validation;
- sensor-footprint decorrelation and the blank-residual `<= 0.05` gate;
- PCHIP tone, clipping, rank, condition, site-count, resampler, null, and M164
  interaction on real captures; and
- arm-blind variance information for freezing the final numerical M1 bar.

**GO/NO-GO.** The physical blur arm must satisfy its registered
`Q95 < 0.90` direction, and the genuine optical improvement must satisfy
`Q05 > 1.10`, with no compensating transfer, flat, provenance, tone, or
unexplained-structure failure. Every reference cell must be stronger than the
scored path; the 64-site/rank/conditioning/power gates and independent
lineages must survive. Any wrong sign, impotent control, transfer failure,
correlated blank residual, rank failure, or underpowered frozen margin is
STOP. It sends the design back to the instrument, target, optics, or sample
size. It does not license a relaxed bar.

Only after Stage 5 passes may the registrar freeze the exact M1 statistic,
population, aggregation, margins, uncertainty, comparator relation, binaries,
settings, seeds, and hashes.

### Stage 6 — sealed M1-only score, 704 frames

**Capture.** Use a fresh target instance/panel and independent calibration in
one uninterrupted holdout sitting:

1. converter-on reference near/middle/far, `96`;
2. converter-on flat/dark A/B/V pattern-map groups, `192`;
3. converter-off TC0 `sw4-A/B` and `sw10-A/B`, `164`;
4. converter-off TC0 reset/start/end witnesses, `60`; and
5. converter-off TC0 flat/dark A/B/V pattern-map groups, `192`.

The optical order and all settings mirror the accepted rehearsal. The score
does not contain physical-control frames.

**GO/NO-GO.** The sitting is eligible only if every frozen input, provenance,
geometry, tone, reference, calibration, M164, rank, population, and
lineage gate passes. A failed gate returns `UNMEASURED`; no threshold, site,
focus offset, mapping, resampler, or comparator setting may be changed after
any member is read.

The full `704` may yield a valid but wide-interval M1 tuple. It qualifies a
comparator, and thereby helps M2/M3/M11, only if the future frozen M1 success
and comparator-retention predicates actually pass.

## 4. What the original 768 frames and M165's added 128 de-risk

**ARGUED.** The rehearsal is not ceremonial. Its blocks exercise distinct
physical branches that synthetic plants and the burned IBIS-on archive do not
cover:

| Rehearsal block | Frames | What becomes unknowable or uncommissioned if cut |
|---|---:|---|
| reference atlas | `96` | same-site truth coverage, two fresh `16`-frame halves, near/mid/far strip coverage, reference power |
| converter-on A/B map sources | `128` | independent half calibration, reference flat/null, fixed-pattern and exposure compatibility |
| converter-on held-out map validation | `64` | whether either fitted map actually removes rather than adds pattern under matched temperature/focus |
| TC0 A/B ladders | `164` | exact `sw4`/`sw10` depth coverage, complete independent output repeats, node population |
| TC0 witnesses | `60` | reset, endpoint, fixed-focus stability and G0–G3 eligibility |
| TC0 A/B map sources | `128` | independent A/B output calibration and output/reference lineage separation |
| TC0 held-out map validation | `64` | independent evidence that the TC0 correction transfers across its registered condition |
| physical sharp control | `96` | proof the instrument can recognize a real pre-noise improvement rather than only reject defects |
| physical blur control | `96` | proof the truth channel decreases under a real pre-noise degradation at the frozen offset |

Skipping the rehearsal moves every unexercised physical branch into the
holdout. The first needed code, target, mapping, focus-offset, tolerance, or
sample-size change would then burn the full scored sitting. Cutting only the
controls recreates the exact failure mode the commissioning standard forbids:
a blind instrument can pass a battery containing only defects.

The original `768` is not proved globally minimal. It is the smallest complete
M135 physical rehearsal previously specified: all named frame counts and
A/B/reference roles are inherited from the score design, and there is no
measured physical power result authorizing fewer repeats, fewer calibration
lineages, one step width, or fewer than 64 sites. M165 does not make any of
those `768` frames optional. It adds the two dedicated `64`-frame validation
blocks, so the current conditional total is `896`.

A smaller rehearsal is possible only as a separately preregistered redesign
with its own power and commissioning evidence. Simply deleting frames or
quietly using A/B as each other's only validation is not an uncertainty trade.

### Why it cannot be folded into the sealed session

The physical controls and reference behavior must be read to decide whether
the instrument, offsets, mappings, margins, and target are acceptable. Reading
them against the scored session's reference spends the subject-plus-session
holdout. If anything then changes, the score is already burned. If they are
not read, the instrument remains physically uncommissioned. Therefore:

```text
rehearsal read -> freeze -> independent sealed score
```

is load-bearing. Controls may not be added to the scored manifest and called
free validation.

## 5. Weakest presently admissible M1 capture

**ARGUED.** The smallest scored sitting under the unchanged current M1 design
was `576` frames before M165's held-out pattern-map requirement was integrated.
The `448` frames named as the “inverted block” in M135 rely on `128`
converter-on A/B calibration frames already present in the wider M1/M5/M9
session. A standalone M1 sitting restores those `128`, then M165 adds one
`64`-frame V block in each optical state:

```text
448 inverted block
+ 128 converter-on A/B calibration
+ 64 converter-on held-out map validation
+ 64 TC0 held-out map validation
= 704 M1-only scored frames.
```

Below `704`, the omitted roles are not merely a source of wider confidence
intervals:

- one output pass cannot separate repeatable information from one realization;
- one reference half cannot expose reference noise or agreement;
- shared or missing flat/dark masters destroy acquisition lineage;
- one step width does not meet the registered stress population;
- missing witnesses leave reset, endpoint and node matching unqualified; and
- missing V sources leave the deterministic-pattern map unvalidated.

Thus the current proposal is **all-or-nothing below 704 with respect to
acquisition eligibility**, conditional on one dark-temperature class and one
focus-valid flat class per optical state. A future M165 residual-power study
might justify fewer validation frames or require more; no repository evidence
presently does either. Conversely, all `704` frames do not guarantee a
positive or qualifying result; they only make an admissible reading possible.

### 5.1 Judgement on over-capture

**JUDGEMENT.** Over-capturing is sound when it means more independently named
frames at the **same matched condition**, with their roles and inclusion order
frozen in advance. The added V groups are the useful form of over-capture:
they test the map on photons not used to fit it and provide a rejection
reserve without cherry-picking.

Over-capturing a loose range of temperatures or focus positions and pooling it
afterward is not sound. It can average away the fixed pattern, mix different
flat fields, or make a mismatched map look stable. Wider-condition captures
must be labelled as interpolation/portability challenges and may enter a map
only under a preregistered rule that passes held-out validation.

Long extra dark sequences can themselves warm the sensor. Darks should
therefore bracket each optical-state subject block in the same continuously
powered session rather than be appended as one long tail. More frames are
useful only until the frozen residual-precision target is met; they are not a
substitute for matching.

## 6. Ways the capture can still be unusable

The table distinguishes an instruction that can prevent waste from a result
that must remain a typed refusal. Items marked **ADD** are not yet safely
resolved in the owner-owned request.

| Waste mode | Preventive instruction before owner capture | Required consequence |
|---|---|---|
| No admitted numeric M1 bar when score begins | **ADD:** after Stage 5, freeze the exact `J_TR/F_TR/U_TR` implementation, site/band population, reduction, margins, uncertainty, comparator rule, seeds, settings and hashes | Do not release Stage 6 |
| Current capture request still carries a STOP banner | Replace it only after `M_work`, target contract, control optical state/offset, stage readers, block order and failure actions are reconciled | Do not infer permission from this report |
| Stage data are acquired before their reader exists | Require a dry-run-passing, persistent, fail-closed checker for every stage before that stage is released | Missing checker is STOP at zero frames |
| Common-input or comparator adapter is unavailable | Freeze and hash every required renderer, license, setting and native-size linear output path on development data before choosing the target | Do not spend physical capture on an unrunnable comparator |
| A directory or stack named `flat` is assumed to be a calibration flat | Require a spatially uniform diffuse/integrating-field capture and run M165's flat sentinels; the burned slide's `flat-*` name means fronto-parallel target orientation only | Patterned-target focus frames receive no calibration role |
| A denser focus bracket is assumed to provide higher-sampling truth | Require a fixed-focus independently sampled atlas with measured `LCB95(M_reference/M_scored) >= 2.0` and different sensor footprints | Dense `sw1`/`sw4` z-sampling at one lateral scale receives no truth role |
| Clean or indeterminate old captures are opened to save development frames | Read the authoritative whole-session holdout register before any outcome-producing access; use only burned or explicit-not-holdout units for development | Treat any unauthorized read as burning the whole subject/session; never backfill capture credit |
| Old darks or flats are reused because nominal ISO/exposure matches | Require same physical body and session, dark temperature within the frozen tolerance, and flats matching lens/converter/aperture/focus domain; bind exact sources in `m165-common-input-manifest-v2` | Unmatched legacy calibration receives zero score credit |
| **No frozen M165 deterministic-pattern map** | For every admitted optical-state package, acquire named `32`-frame `FLAT-A/DARK-A`, `FLAT-B/DARK-B`, and held-out `FLAT-V/DARK-V` blocks; split further wherever focus or temperature creates another class; freeze the estimator, map, source hashes and validation result into the M165 chain | Converter returns `PATTERN_MAP_REQUIRED`; M1/M9 are `UNMEASURED` |
| Pattern-map body or temperature is only assumed | Record the physical body identifier externally and bracket each optical-state subject block with same-body, ISO-100, 1-second darks under continuous power; freeze a temperature witness/tolerance before shooting | Missing or out-of-range witness is refusal |
| Flat does not match lens/aperture/focus | Match body, lens, converter state, marked f/5.6, exposure and the registered focus class/schedule; never substitute a convenient generic flat | `PATTERN_MAP_CAMERA_MISMATCH` or physical calibration refusal |
| One map is applied across a focus sweep without proof | Stage 0M must freeze and commission the number of flat-focus classes or an interpolation/invariance rule with held-out focus challenges | Add `96` flat frames per additional class or STOP |
| M165 manifest cannot enforce the physical match | Route a schema/validator amendment for external body ID, temperature witness, focus domain and held-out validation; keep using `m165-common-input-manifest-v2`, not a parallel M164 format | Do not release calibration capture |
| The `$0` patch supports only a narrower target-conditional claim | Require all M135 target-eligibility gates; otherwise fabricate independent concealed development/holdout panels | `TARGET_INELIGIBLE`; no silent scope reduction |
| Target/seed is known while renderers are still tunable | Freeze binaries and settings first; then choose the one-use specimen/orientation or generate concealed seeds; keep holdout panel sealed | Any post-target tuning invalidates the target |
| Printed target is scaled, screened, sharpened or repeated | Supply final-size artwork; disable fit-to-page/RIP enhancement; verify physical carrier mapping and uniqueness before capture | Reject the panel |
| Target lacks 64 guarded common sites or all 16 cells | Stage 2 census from input-only geometry; require the complete site/power floor before proceeding | Redesign target/framing |
| Carrier maps above `0.25 cyc/native scored px` | Generate physical cell dimensions from accepted `M_work`; verify mapping from measured pixels, not nominal print dpi | Refuse affected target/cells; full contract fails |
| Target, tone strip and fiducials are not coplanar | Mount all on one rigid plane and verify plane residual from input-only fiducials | Restart with a coplanar target |
| Natural specimen dries, shifts or changes | Use a rigid inert one-use target for the score; if a natural patch is used in rehearsal, lock and monitor it | Any visible/metric scene change invalidates pairing |
| Reference field or near/mid/far atlas misses sites | Stage 2 map must assign every retained site to exactly one well-focused strip with guards away from seams | Reframe or redesign atlas |
| EXIF `200 mm` or the lens protocol string is treated as proof of magnification | Measure the physical grid pitch at both optical states and use M147's bootstrap lower bound; lens labels and nominal teleconverter factors are provenance only | No ratio decision without `LCB95(M_reference/M_scored)` |
| Reference sampling ratio is below `2.0` | Stage 0 plus a live ratio check before the first TC0 scored frame; use unrounded M147 lower bound | STOP; never substitute lens labels |
| No `M_work` satisfies ratio, field and frequency simultaneously | Compute the feasible set after Stage 0 | Abandon the current shared-prime inversion |
| Converter-on transfer is not stronger in every licensed cell | Measure it in the complete rehearsal with adequate target power and both calibrated reference halves | Refuse the failed cell; if every registered cell is required, no M1 score |
| Shared base-lens zero is mistaken for object truth | State the claim as reference-path-conditional and report only frequencies whose reference transfer qualifies | Never claim detail outside the qualified reference passband |
| IBIS or lens OSS is enabled | Bench checklist and recorded state: body SteadyShot OFF, lens OSS OFF before every stage and after every power/state change | Entire affected stage is unusable |
| Wrong exposure or automatic processing is enabled | M mode, ISO 100, `1 s`, marked f/5.6, fixed WB, camera-linear 14-bit RAW, EFCS; NR/DRO/HDR/lens corrections and auto review off | Metadata/settings mismatch is refusal |
| Clipping, photon starvation or invalid tone range | Take the one throwaway histogram frame before the registered score; verify rails and all 33 levels before frame 1; adjust only before the session | Once score starts, stop and reshoot rather than retune |
| Lighting flicker, warm-up drift or moved polarizers | Flicker-free source warmed at least 15 minutes; lock source and polarizers; record illumination witnesses | Drift beyond frozen eligibility invalidates the stage |
| Sensor/camera thermal state changes between subjects and calibration | **ADD:** commission a pre-warm and input-only thermal-stability check in rehearsal; keep camera powered, bracket subject blocks with darks, and timestamp every block | No numeric stability threshold is currently frozen, so Stage 6 remains blocked until one is |
| Stage-analysis pause changes the physical setup | Keep rig, camera, target, lighting and environment locked and powered while a verdict is read | If continuity cannot be maintained, restart Stage 1 or shoot the full rehearsal as one sitting |
| Focus reset approaches from the wrong direction | Record one reset method/direction; use it for P0/P1, every A/B pass and every control; issue no extra AF command | Failed G1/reset gate is STOP |
| Focus motion has not settled | Preserve the registered 3-second bracket interval and at least 3 seconds after manual focus motion | Failed G0/G3 is STOP |
| Wrong bracket count, width or direction | Exact `55/27`, widths `4/10`, complete A then B passes, order `0 -> +`; verify folder counts before changing state | Never fill missing frames or re-index after capture |
| `sw4`/`sw10` has gaps or endpoint peaks at `M_work` | Stage 4 image-derived coverage and 64-site interior-peak check; EXIF `FocusPosition2` is not evidence | Change design on development data; do not score |
| A/B nodes do not represent the same focus positions | Apply G2 `< 0.10` fixed-focus log-ratio plus G3's unique zero-lag maximum and `< 0.10 px` geometry gates to same-index curves | No result-time shift or node re-indexing |
| Fixed-focus bursts, resets or endpoints are unstable | Apply G0 `<= 0.033 px` and G1 `< 0.10 px` gates exactly as registered | Failed burst/state is unusable |
| Converter is removed too early or reinstalled | Finish converter-on reference and calibration first; log owner-confirmed 2x Viltrox identity; remove once, then remain TC0 | Mixed state/order invalidates lineage |
| Camera is reframed by yaw, roll or target movement | Keep target fixed; move camera axially only; retain at least four common fiducials and input-only geometry residuals | Failed native mapping is refusal |
| Focus Bracket remains on for the truth atlas | Explicitly turn it OFF and store near/mid/far bursts separately | A merged/bracket truth reference is circular and unusable |
| Reference exposure differs from its calibration | Lock exposure across reference and converter-on masters; record settings at every block | Exposure mismatch invalidates reference calibration |
| A/B or optical states share calibration | Six separate `32`-frame flat/dark A/B/V groups in each base optical-state package, plus any extra registered focus/temperature classes; no fitted source crosses A/B, optical state, rehearsal/score, or session; V is fit to neither | Missing lineage returns `UNMEASURED` |
| Flats contain paper/diffuser texture or repeated illumination pattern | Use a true diffuse/integrating field or adequate defocus; move/rotate diffuser between A, B and V | Failed flat sentinel is refusal |
| Darks are cold, light-leaked or at wrong exposure | Warm camera, cap/light-seal correctly, keep scored exposure, retain but exclude first two settling darks | Recapture development stage; scored mismatch burns sitting |
| Reference and output share correlated sensor structure | Enforce different sensor footprints after scale change, independent masters, and blank-residual correlation `<= 0.05` | Correlation failure is nonnumeric refusal |
| Physical blur/improvement controls are post-selected | Freeze an input-only focus-position/offset rule after Stage 4; register before Stage 5; never choose by the desired M1 sign | Control arm is invalid |
| Only degradation is commissioned | Keep all `96` genuine-improvement frames and require the registered positive direction | Wrong/absent improvement kills the instrument |
| Control arm uses the truth reference as the “improvement” | Use a separate converter-off fresh-noise optical capture; the reference remains truth only | Circular arm is invalid |
| Rehearsal and score reuse target, reference or calibration | Use independent one-use development and holdout target instances/panels, exposures, flats and darks | Shared lineage burns admission |
| Battery, card or power cycle interrupts the scored sitting | **ADD:** use the power method proven across the full rehearsal; pre-verify card capacity for all RAWs plus reserve; no card/battery swap, sleep, firmware update or power cycle | Any interruption makes the whole subject/session ineligible |
| Files are missing, duplicated, mislabelled or silently corrupted | Empty dedicated destination/card, literal block folders, expected-count manifest, SHA-256 on ingest, and fail-closed role binding | Never infer a missing role from timestamps |
| Score is previewed, rendered or tuned before sealing | After the one histogram setup frame, disable auto review; permit only frozen input/provenance gates; hash and seal the complete sitting before any comparator output | Any quality/outcome read burns the entire subject/session |
| A participant applies USM, denoise/blur, deconvolution, resize or internal postfilter | Freeze neutral output settings and native dimensions; run M164 before M1; prohibit unilateral postfilters on the common-merge track | M164 fire means that pair is inadmissible, not worse |
| Product-internal sharpening is mixed with genuine merge differences and evades M164 | Keep truth-relative non-compensating `F_TR/U_TR`; do not treat `NOT_VETOED` as structural sharpening safety | Failed truth witness is refusal |
| Exact score duration exceeds setup stability | Measure the complete order and transition time during Stages 1–5; do not promise 45 or 60 minutes until rehearsed | If stable uninterrupted execution is not demonstrated, do not release Stage 6 |
| Stage 6 is split or resumed after interruption | Declare one subject plus one uninterrupted sitting as the holdout unit; provision power/storage before frame 1 | Discard the entire sitting for M1 |
| A failed score gate is repaired after looking | Freeze all remediation policy beforehand; a failed eligibility gate returns `UNMEASURED` | Any changed code/threshold requires a fresh holdout |

## 7. Revised totals and stopping losses

| Last completed gate | Newly exposed frames | Cumulative registered/setup exposures |
|---|---:|---:|
| Stage 0 | `2` | `2` |
| Stage 1 | `128` | `130` |
| Stage 2 | `160` | `290` |
| Stage 3 | `128` | `418` |
| Stage 4 | `224` | `642` |
| Stage 5 — full rehearsal accepted | `256` | `898` |
| Stage 6 — M1-only score | `704` | **`1,602`** |

If M147 requires its one allowed placement verification, add `2`. The score's
known throwaway histogram release makes the base physical release floor
`1,603`; any additional setup test frames must be named by the final capture
request rather than silently omitted.

The current request also calls for a live ratio decision after converter
removal but does not say whether it consumes a new RAW or a live-view/input
frame. If it needs another shutter release, add it explicitly; it is not
silently included in `1,603`.

If the owner elects to preserve the combined M1/M5/M9 holdout, its original
`891` frames also need the two `64`-frame V blocks. Stage 6 becomes `1,019`
and the conditional registered total is:

```text
2 + 896 + 1,019 = 1,917
```

These totals assume exactly two dark-temperature classes and two flat-focus
classes per sitting: converter-on and TC0. The general count is:

```text
rehearsal = 512 non-calibration frames
            + 96 * D_rehearsal + 96 * F_rehearsal
M1 score  = 320 non-calibration frames
            + 96 * D_score + 96 * F_score
total     = 2 + rehearsal + M1 score
```

Every additional focus class adds `96` flat frames; every additional
temperature class adds `96` dark frames. If both split, the increment is
`192`. Until Stage 0M freezes all four class counts, `1,602` is a conditional
floor rather than an owner-ready total.

The M1-only route still defers `315` converter-on M5/M9 focus/witness frames.
That unbundles other axes without weakening M1.

## 8. Final recommendation

**PROPOSAL.** Treat the existing-corpus audit as complete for capture-credit
purposes: do not open clean or indeterminate stacks in search of a shortcut,
and budget zero old frames against the physical protocol. First route the
Stage 0M manifest/estimator gaps to M165; no calibration capture is executable
until they are closed. Then execute the two-fresh-frame M147 preflight. If the
feasible working-magnification set is nonempty, expose only one development
stage at a time while the rig remains locked. Do not release the next block
until the previous verdict is on disk and accepted. After the conditional
`896`-frame rehearsal passes, freeze the M1 bar and choose between:

- **M1-first:** `704` sealed frames, conditional `1,602`
  registered/setup exposures total; or
- **combined M1/M5/M9:** `1,019` sealed frames, conditional `1,917` total.

Given M1's comparator-qualification dependencies, the M1-first path is the
smallest unchanged-scope route to any admissible M1 reading. It is not a
promise of a qualifying result. Neither number is owner-ready until M165
freezes the dark/flat class counts and match tolerances.

## 9. Governing sources

- `docs/research/M147-preflight.md`, §§0–2: two-frame field gate, exact
  `LCB95 >= 2.0` rule, typed quality refusals, and measured `25.40 s` runtime.
- `docs/research/M135-detail-instrument.md`, §§6.4–6.6 and 8: target,
  reference, calibration, control, site, lineage, and frame-count contract.
- `docs/proposals/2026-09-truth-referenced-detail.md`, §§0, 3, 5 and 6.1:
  inverted reference design, non-compensating certificate, decision shape,
  and why the sealed reference is not commissioning data.
- `docs/capture-requests/2026-09-319-frame-session.md`, stop banner, block
  table, control clause, literal order, and G0–G3 clauses: current operational
  constraints. This file remains owner/orchestrator-controlled and unsafe to
  shoot from.
- `docs/proposals/2026-09-sota-scorecard.md`, M1: current `UNMEASURED` state,
  missing admitted bar, required fresh input roles, and mandatory controls.
- `docs/research/M165-common-input.md`, “Pattern-map finding and required
  capture”: fatal missing-map ruling, exact matching dimensions, disjoint
  estimation/validation requirement, and explicit refusal to invent a frame
  count before residual precision is registered.
- `docs/research/M-FRC-VIABILITY.md`, §1.4: existing 32-frame calibration-unit
  precision estimates and the reason 16-frame per-pixel masters were not
  accepted as sufficient evidence.
- `experiments/M165-common-input/pattern-map-manifest-template.json` and
  `converter.py:887-1002,1080-1139`: current map schema, exact
  `capture_match` behavior, source disjointness, array/hash checks, and the
  metadata fields that are `null` on the development body.
- `experiments/M141-capture-inventory/holdout-register.json`: whole-subject/
  uninterrupted-session holdout rulings used before any suitability work.
- `experiments/M141-capture-inventory/capture-manifest.json` and
  `capture-stacks.csv`: `68`-stack/`10,509`-RAW metadata inventory, universal
  converter-on/stabilization-on findings, and absent measured magnification.
- `experiments/M141-capture-inventory/capture-design-coverage.json`: verified
  zero-frame coverage of the predecessor `603`-frame and live `448`-frame
  designs.
- `docs/research/M141-capture-inventory.md`: four-way slide characterization,
  holdout analysis and human-readable block-by-block coverage rationale.

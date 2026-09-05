# M165 — common linear input, pattern-map gate, consumer receipts, and Strehl byte identity

## Verdict

**Stage 0M is closed in software. The Stage 0C exact-byte boundary and retained
fork byte-admission arm are commissioned, but the color-semantic contract is
now `PROPHOTO_DISPROVED`. The real competitive package remains `UNMEASURED`.**

M165 now provides:

- a frozen LibRaw common-merge converter;
- a deterministic uncompressed RGB16 TIFF writer and frozen embedded
  linearized-ProPhoto D50 profile;
- a strict Strehl TIFF adapter and pre-merge byte-identity verifier;
- a frozen A/B dark/flat estimator with a never-fitted V validation block;
- enforceable two-class-per-sitting cardinality;
- external physical-body, temperature, focus-schedule, and flat-field-state
  provenance;
- a frozen, fail-closed consumer-boundary gate that independently hashes and
  parses one in-memory read of every TIFF, validates consumer-side receipts,
  and partitions every input and consumer/input pair into counted outcomes;
- a source-pinned, host-locally bit-reproducible rebuild of the retained
  `focus-stack` fork plus a locked one-read consumer adapter; and
- a fail-closed ProPhoto semantics gate that separates the embedded profile
  declaration, producer pixel semantics, and each consumer's interpretation.

**VERIFIED BY RUNNING.** The embedded 548-byte ICC is a valid linear,
ProPhoto/ROMM-primaries, D50 profile. LibRaw output color `4` uses a
`prophoto_rgb` matrix within `0.000216269` maximum absolute coefficient error
of an independently derived Bradford D50-adapted sRGB-to-ProPhoto transform,
while it is `0.286834150` from the unadapted transform. LittleCMS also rendered
the frozen LibRaw-generated gamma-1 profile and the M165 profile identically
for all ten witness patches. The producer is therefore D50-compatible at the
tested operational boundary; exact ICC byte identity is not claimed. The
required retained fork independently ignores the embedded ICC and treats
16-bit input under its sRGB-OETF/output-space contract. That required-consumer
divergence alone forces `PROPHOTO_DISPROVED`; exact-byte identity remains true
but is not color-semantic identity.

No eligible real calibration capture exists. Therefore no real pattern map, no
campaign common-merge TIFF, and no campaign consumer-identity result exists.
Per the live `docs/proposals/2026-09-sota-scorecard.md` §1.2, M1 remains
`UNMEASURED`; M9 remains `DEFINITION_BLOCKED_M1_TRUTH` and additionally lacks
the same calibration input. Stage 0M closes the zero-frame
design/implementation gate; it does not manufacture the missing photons.

The class count is now frozen at **two dark-temperature classes and two
flat-focus classes per sitting**: one of each for `converter-on`, and one of each
for `tc0`. Each optical state has independent A and B fitted maps plus a shared,
never-fitted V block, so one sitting produces four fitted maps. M164's `1,602`
registered-frame M1-only total (`1,603` including its known histogram release)
and `1,917` combined M1/M5/M9 total are no longer conditional on M165 class
counts. They are **not globally owner-final** because M164 records other open
release conditions and an unresolved possible live-ratio shutter release.

## Next gate — Stage 0C consumer-boundary admission

**INFERRED BY READING.** Stage 0M froze and commissioned the zero-frame map,
manifest, refusal, and identity machinery. It did not qualify a consumer
campaign. The immediate next gate is **Stage 0C**, a new M165 term that does not
rename or remove Stage 0M: freeze every required consumer runtime bundle and
setting, then require one independently generated receipt for every
consumer/input pair on development common TIFFs. This must precede a real
subject. M164 §2 release condition 6 requires comparator binaries, licences,
settings, and common-input execution to be frozen on development data before
target selection, while its Stages 1 and 2 must first produce and validate the
matching converter-on calibration. A real-subject end-to-end campaign is the
gate after those prerequisites, not a substitute for them.

The assignment's proposed roster needed correction against the live scorecard.
The required common-merge consumers are:

1. strehl;
2. licensed Zerene PMax;
3. licensed Zerene DMap; and
4. a fresh rebuild of the retained fork source, commit-pinned and
   executable-hash frozen. Its exact-byte admission arm is satisfied on
   development input by the rebuild documented below; its color-semantic arm
   is disproved below.

Helicon is additional **when obtainable**. Its absence is counted and reported
but is not fatal. Omitting the required fork while treating Helicon as required
would enforce the wrong contract.

**VERIFIED BY RUNNING.** `consumer_gate.py` now enforces Stage 0C. For each
input it:

- reads the converter manifest and TIFF into memory once;
- hashes the whole TIFF with SHA-256 over `[0,file_size)`;
- parses those same TIFF bytes and hashes the concatenation of every strip byte
  range in scan order as the pixel payload;
- checks dimensions, ICC, converter/source/map provenance, and both converter
  hashes;
- checks that an independently produced consumer attestation belongs to the
  named consumer, input path, invocation, and outputs, then checks its hashes
  against those bytes;
- binds the complete consumer executable bundle, settings, invocation, output,
  campaign, and registry; and
- reports exhaustive `PASS`, `FAIL`, `MISSING`, `BLOCKED`, and
  `OPTIONAL_ABSENT` counts whose sums must equal their denominators.

The gate bundle SHA-256 is
`62127f6218a2f0b9fc3482a8b44138c237935ef763d0129ff7dfc87d0898d98f`;
the gate source SHA-256 is
`5ce6a625aa834e182d4823d902a377ef0ba4afa9d1012ddab06b3bbc23c1219e`.
The committed freeze file SHA-256 is
`339026c99c444abf2f30a676b1eaba18cc41e459a27947ce448d66e5d8950175`.

This gate does not turn an externally supplied receipt into proof by assertion.
It reopens neither a path for hashing nor parsing: one cache owns every artifact
read. The receipt producer independently performs the same one-read hash and
parse, and the consumer attestation supplies the third comparison. Strehl's
attestation is its Rust identity report. The rebuilt fork now emits the
standard attestation from a locked handoff. No Zerene or Helicon attestation is
claimed here.

The operational sequence is:

```text
python consumer_gate.py freeze --out consumer-gate-freeze-v1.json
python consumer_gate.py record --campaign CAMPAIGN --registry REGISTRY \
  --freeze FREEZE --consumer-id ID --input-id INPUT \
  --attestation ATTESTATION --invocation-json INVOCATION \
  --output OUTPUT --out RECEIPT
python consumer_gate.py verify --campaign CAMPAIGN --registry REGISTRY \
  --freeze FREEZE --receipts RECEIPTS_DIRECTORY --out VERDICT
```

## Governing contract re-read

The live source was re-read rather than relying on the assignment summary:

- `docs/proposals/2026-09-sota-scorecard.md` §1.2 defines common-merge as the
  sole publication track and requires one frozen matching deterministic-pattern
  correction before M1 can be measured; M9 is separately definition-blocked
  and also lacks that calibration input.
- `docs/research/M164-m1-staged-capture.md` §2, Stage 0M, and *Proposed
  pattern-map capture unit* define the zero-frame release gate and the six
  `DARK-A/FLAT-A/DARK-B/FLAT-B/DARK-V/FLAT-V` groups.
- M164's current file hash is recorded in
  `experiments/M165-common-input/out/independent-hash-audit.json`; M165 did not
  edit it or any proposal/capture-request/status file.

## What already existed and was reused

1. **A partial LibRaw audit and manifest vocabulary.**
   `docs/research/SCORECARD-BASELINE.md`,
   `experiments/SCORECARD-BASELINE/out/INPUT-MANIFEST.json`, and
   `experiments/M153-m11-harness/{staged-input-manifest-template.json,
   adapter-identity-template.json}` already established explicit development
   settings, separate file/payload hashes, and the absence of matching maps.
2. **The Strehl merge boundary.** `strehl_raw::decode` and the existing generic
   `strehl_core::pyramid::BandMerge` supplied the internal boundary. M165 added
   a strict RGB TIFF adapter rather than replacing the merge core.
3. **A measured flat normalizer.** M71's 61-plane-pixel, three-pass reflected
   box surface was reused. M71 measured green PRNU at `0.3096%`, spectrally
   white, and at least `91.4%` stable in variance across a much larger
   focus/filter/shutter change (`docs/research/M71-flat-fields.md`, P1, P3,
   P4). M71 also showed why infinity-focus vignetting must not be imported into
   macro captures.
4. **Calibration-count evidence.** `docs/research/M-FRC-VIABILITY.md` §1.4
   predicts `0.084%` relative RMS for a 32-frame, 10000-DN flat master and
   about `0.16 DN` for 30 usable darks after the two-frame settling discard.
   Its §7 also shows why A and B may not share a fitted master.
5. **The residual correlation bar.** M135 requires disjoint A/B calibration,
   no sharing across optical states, and blank-residual correlation `<=0.05`
   (`docs/research/M135-detail-instrument.md` §3 and §6).
6. **Temperature evidence.** M4 records the 6–7 °C dark-current doubling rule
   (`M4-fpn-measured.md:633`); M101 measures a `15.4 e-/s` thermal component
   (`M101-defect.md` §4.2); M71 measures approximately `0.224103 DN/e-` from
   its two green gains.
7. **No reusable real map.** M71 retained flat-analysis arrays, but no paired
   1-second dark offset plus matching flat gain map. The M2/M16 audits likewise
   contain no eligible map. The census remains in
   `out/pattern-map-audit.json`.
8. **Comparator provenance.** M162 established that the archived fork result
   used Lightroom-developed TIFFs and has no producing executable. M165 reused
   the comparator-agnostic registry and first-class consumer executable hash,
   then rebuilt the nearest retained source revision without claiming it was
   the archived producer. None of this changes the Strehl byte-identity method.

## Implemented artifacts

| Artifact | Purpose |
|---|---|
| `converter.py` | Converter `1.2.0`; v2 pattern-map and v3 common-input validation; physical body, temperature, focus schedule, held-out result, and source-context enforcement. |
| `pattern_map_estimator.py` | Streaming dark/flat estimator, deterministic NPZ writer, A/B fit, V-block validator, sitting/cardinality validator, and synthetic commissioning. |
| `pattern-map-settings-v1.json` | Exact class counts, tolerances, estimator, statistics, thresholds, and refusal policy. |
| `pattern-map-estimator-freeze-v1.json` | Hash freeze for estimator source, converter source, settings, Python, NumPy, rawpy/LibRaw, and ExifTool. |
| `pattern-map-sitting-template.json` | Exactly two optical-state classes and four fitted maps per sitting. |
| `pattern-map-capture-template.json` | Six disjoint 32-frame groups, sensor fingerprint, physical records, and class definitions. |
| `physical-body-witness-template.json` | Owner-assigned body ID bound to a private contemporaneous evidence hash. |
| `capture-record-template.json` | Power, shutter, stabilization, lens/converter, aperture, and dark light-seal record. |
| `flat-field-record-template.json` | Three independently named A/B/V diffuser states; B and V require a move or rotation. |
| `temperature-probe-calibration-template.json` | Probe identity, reference, timestamp, and uncertainty. |
| `temperature-log-template.json` | Strictly time-ordered external contact-probe samples. |
| `focus-schedule-template.json` | Hash-frozen normalized subject schedule, direction, reset method, fit point, and validation endpoints. |
| `source-capture-context-template.json` | Per-ARW binding to the body/capture/temperature/focus artifacts and exact schedule position. |
| `pattern-map-manifest-template.json` | A or B map, fitted sources, excluded darks, V sources/result, estimator freeze, and all class identities. |
| `commissioning/pattern-map-estimator/commission.json` | Stage 0M algorithm and schema/refusal commissioning evidence. |
| `out/pattern-map-determinism.json` | Byte-stable repeat of the commissioning report and both generated NPZ maps. |
| `out/stage0m-class-derivation.json` | Machine-readable class/tolerance arithmetic and M164 count consequence. |
| `consumer_gate.py` | Stage 0C one-read TIFF/hash/parser, receipt recorder, exhaustive campaign verifier, and fail-closed CLI. |
| `consumer-gate-freeze-v1.json` | Frozen Stage 0C script, Python runtime, schemas, and bundle hash. |
| `consumer-campaign-template.json` | Frozen input-set and registry binding. |
| `consumer-boundary-receipt-template.json` | Per-consumer/per-input independent hash, byte-range, attestation, invocation, and output contract. |
| `consumer-receipt-template.json` | Explicitly marked `SUPERSEDED_UNENFORCED`; the old placeholder is not accepted by Stage 0C. |
| `consumer-registry-template.json` | Extended in place with complete runtime bundles and registered attestation schemas; still comparator-agnostic. |
| `consumer_fixture.py` | Commissioning-only independently reading consumer; never a comparator result. |
| `commission_consumer_gate.py` | Reproducible Stage 0C clean, mutation, restoration, missing-receipt, and malformed-input battery. |
| `commissioning/consumer-gate/commission.json` | Stage 0C commissioning report. |
| `audit_consumer_readiness.py` / `out/consumer-readiness.json` | Pre-rebuild machine consumer partition and precise blockers. |
| `experiments/M165-fork-rebuild/freeze_fork_source.py` / `source-pin.json` | Raw-Git-object source freeze for the selected retained fork revision. |
| `experiments/M165-fork-rebuild/build_fork.py` / `build-freeze.json` | Two-clean-path reproducible Windows build, toolchain/dependency lock, runtime bundle, and pre-render executable freeze. |
| `experiments/M165-fork-rebuild/fork_consumer.py` | Independent TIFF parser, one-read SHA-256, Win32 read-only locked handoff, actual fork invocation, and fail-closed standard attestation. |
| `experiments/M165-fork-rebuild/commission_fork_arm.py` / `commissioning/commission.json` | Truthful full-roster admission plus isolated clean/RED/repair commissioning of the real fork arm. |

## Stage 0M closure

| M164 requirement | Closure |
|---|---|
| Estimator and exact residual statistic | Implemented and source-hash frozen. |
| Held-out threshold and minimum count | 32 acquired per group; first two darks excluded; 30 dark and 32 flat usable; exact RMS/coherence bars frozen below. |
| One-map ambiguity | “One” means one immutable fitted map per `(session, optical state, A/B lineage, temperature class, focus class)`. A literal campaign-wide map is forbidden. |
| Focus classes or interpolation | One exact schedule-domain class per optical state; no interpolation; middle-fit and held-out near/far endpoint challenge. |
| Temperature witness/tolerance | Calibrated external contact probe, fixed mount, first `DARK-A` sample as center, age `<=10 s`, delta `<=0.5 °C`, no interpolation. |
| Manifest binding | Sitting, capture, body, bench state, flat-field state, temperature calibration/log, focus schedule, source hashes, estimator freeze, map bytes, and held-out result are all hashed and validated. |

The gate is satisfiable with zero new frames because it freezes the method and
schemas, not a fitted map. Real map production remains impossible until the
registered captures exist.

### Cardinality

The enforced sitting manifest accepts exactly:

- one `converter-on` temperature class;
- one `tc0` temperature class;
- one `converter-on` focus-schedule class;
- one `tc0` focus-schedule class; and
- A and B fitted maps in each optical state.

Class IDs are canonical:

```text
{session_id}:{optical_state_id}:temperature
{session_id}:{optical_state_id}:focus
```

No fitted source may cross A/B, optical state, or sitting. The V sources are
shared only as never-fitted validation data. A tolerance miss is a typed STOP
and recapture of that optical-state package, not permission to add a post-hoc
class. This is what makes the count genuinely frozen rather than advisory.

### Dark-temperature class and tolerance

**Frozen count: two per sitting, one per optical state.**

The reason is lineage, not an assertion that removing the converter changes
dark current. M135 forbids sharing calibration across optical states, and the
converter-on and TC0 packages occur at different times. Within each optical
state, A, B, V, and subject frames must remain inside one class while the body
stays continuously powered.

The class center is the external sample referenced by `DARK-A` capture index
zero. Every registered frame must have a probe sample no older than `10 s` and
within `+/-0.5 °C`; interpolation is forbidden. The probe calibration
uncertainty must be `<=0.2 °C`.

The tolerance is conservative but not magic. A half-degree change under a
6–7 °C doubling law changes dark current by `5.076%` to `5.946%`. Applying
that to M101's `15.4 e-/s` thermal component and M71's mean green gain gives a
derived 1-second change of `0.1752` to `0.2052 DN`, below the frozen
`0.30 DN` held-out dark RMS bar. The external body reading is only a proxy for
sensor temperature; passing `DARK-V` is therefore load-bearing.

### Flat-focus class and tolerance

**Frozen count: two per sitting, one exact schedule-domain class per optical
state.**

The map estimates high-frequency sensor-space gain only. Each flat is divided
by its own per-CFA-plane 61-pixel triple-reflected-box smooth field, so the
low-frequency optical field is retained rather than turned into a forbidden
lens/vignetting correction. `FLAT-A` and `FLAT-B` are fitted at normalized
schedule position `0.5 +/- 0.05`. `FLAT-V` contains 16 frames within `0.05` of
the near endpoint and 16 within `0.05` of the far endpoint. Subject sources
must name an exact entry in the hashed `[0,1]` schedule; interpolation is
forbidden. Sony `FocusPosition2` is corroboration only because its reported
steps are too coarse to define the macro axis.

One class per optical state is justified by M71's measured lower bound that
`91.4%` of PRNU variance survives a much larger focus/filter/shutter change.
Combining that lower bound with `0.3096%` PRNU gives a conservative derived
upper bound of `0.0908%` RMS for the unstable component, below the `0.15%`
held-out all-position bar. This is only prior justification for trying one
class. The real near/far V block can still reject it.

### Estimator and held-out statistic

For each A or B lineage:

1. discard dark capture indices zero and one;
2. subtract LibRaw's per-CFA black level and arithmetic-mean the remaining 30
   darks into `offset_dn`;
3. subtract black plus that offset from each of 32 flats;
4. divide each CFA plane by its own 61-plane-pixel, three-pass reflected-box
   smooth field;
5. arithmetic-mean the normalized flats and invert the mean into `gain`; and
6. write `gain` and `offset_dn` as deterministic uncompressed float32 NPY
   members inside an NPZ.

Application is:

```text
corrected = black + clip((raw - black - offset_dn) * gain, 0, white - black)
```

Validation never fits V. After the two dark settling exclusions, capture-index
parity creates 15/15 dark halves. Flat parity creates 16/16 halves, including
8/8 at each focus endpoint. Map A corrects the even half and map B the odd
half. The exact frozen checks are:

- RMS of half the sum of the two split dark means: `<=0.30 DN`;
- the analogous normalized flat RMS over all positions: `<=0.0015`;
- normalized flat RMS at each endpoint: `<=0.0025`; and
- maximum positive real cross-power coherence: `<=0.05` in every admitted one
  of 12 Hann-windowed radial rings over complete 128-plane-pixel CFA tiles,
  from `0.015625` through `0.5` cycles per plane pixel, with at least 128
  modes.

The RMS includes finite temporal/master noise; it is not mislabeled as a pure
common-mode estimate. The ring statistic supplies the cross-lineage
common-pattern test. The settings file spells out both formulas, and the
estimator source hash freezes their implementation.

## Frozen estimator and commissioning

`pattern-map-estimator-freeze-v1.json` records:

- estimator `m165-dark-flat-map` `1.0.0`;
- rawpy `0.27.0`, LibRaw `0.22.1`, NumPy `2.4.4`, Python `3.12.10`, and
  ExifTool `13.58`;
- estimator source SHA-256
  `9b22970ac16624c58c550e1211dec499b172c3ca43c5af2a2ecaa8e27a5755ae`;
- settings SHA-256
  `a9fbd14556316550dd50a9eb3c18797c46a4674035aed7fffabd174df920e715`;
- executable-bundle SHA-256
  `7bc94f2d11976e512cb72face86fbf9deb6bf355592781b2c6aa64c203c37b73`.

The commissioning report SHA-256 is
`b37a73db16dcfcaf4c7f9992d78d12ac7635c8f8937ed3e8eacb134168f3b7f9`
and its status is `PASS`.

| Arm | Dark common RMS | Flat common RMS | Maximum dark / flat ring coherence | Verdict |
|---|---:|---:|---:|---|
| Clean movable null | `0.189963 DN` | `0.083101%` | `0.038127 / 0.023444` | PASS |
| Same null plus real fixed offset/gain disturbance, no correction | `1.812823 DN` | `0.622051%` | `0.999214 / 0.976905` | FAIL |
| Planted wrong-sign correction | `3.612643 DN` | `1.237138%` | above the frozen bars | FAIL |
| Estimated A/B correction | `0.232911 DN` | `0.101646%` | `0.018499 / 0.026701` | PASS |

The clean endpoint flat RMS values were `0.117664%` near and `0.117520%` far.
After estimated correction they were `0.131389%` and `0.131216%`; both passed
the `0.25%` endpoint bar. The improvement is real relative to the disturbed
uncorrected arm: dark RMS fell `1.812823 -> 0.232911 DN` and flat RMS fell
`0.622051% -> 0.101646%`.

The contract battery also passed:

- valid capture and two-class sitting manifests;
- exact `2` dark / `2` flat classes and `4` fitted maps;
- rejection of a missing class and a source shared across optical states;
- rejection of body mismatch, `+0.6 °C` temperature mismatch, focus mismatch,
  wrong group count, and a flat B state without a diffuser move;
- valid map/source-context matching;
- rejection of map/body, map/temperature, and map/focus-schedule mismatch;
- rejection of a failed held-out result; and
- malformed JSON returning exit `1` with a persistent `status=FAIL` record.

A second complete run produced byte-identical report and map artifacts:

- report
  `b37a73db16dcfcaf4c7f9992d78d12ac7635c8f8937ed3e8eacb134168f3b7f9`;
- synthetic map A
  `15a9bd1b8a9fe1edb9fc5bcb2763a0a6877c478dbdcea9154761c1ff2e7a4a9c`;
- synthetic map B
  `e4959eaedb02260cdbc43e8011a5ba876fe7a5a01a1f2915e7646208fcd74ce6`.

The NPZ fixtures are ignored generated artifacts; the committed report,
settings, source, freeze, and determinism record reproduce and bind them.

## Held-out construction

**Use dedicated V blocks from the same continuously powered sitting. Do not use
a separate validation sitting.**

The V frames need their own blocks because they must never contribute to either
fit. They should remain in the same sitting because the map is explicitly keyed
to session, optical state, temperature class, and focus schedule. A separate
sitting would add an uncontrolled thermal/session change and validate a
different estimand. M164's Stage 2 and Stage 5 construction is therefore right:
dedicated same-sitting V blocks, with moved/rotated diffuser state and temporal
bracketing, are independent validation without breaking the match.

## Converter and TIFF contract

The amended converter is `m165-libraw-common-linear` `1.2.0`. Its frozen bundle
SHA-256 is
`cfb71ae59c321366467cbfa915c10e2071a7ce13e3fd6a1eb23a5b00bcd699fc`;
the converter source SHA-256 is
`a515a39895c3d1d27adebaecc07fab529f3aa7b3c1ef0dcb12cf417b5367a481`;
settings SHA-256 is
`dcce8eda23287d19aaf9992782f8d3f845726773edcae67de53a9d4e962d930a`;
ICC SHA-256 remains
`16c8cad1299737e912d72ad83e959a9f879519a5fd2aaddb82ce103ebeca08ef`.

The v3 common-input manifest requires the v2 map plus a per-source capture
context. It checks the actual body witness/capture record/temperature
calibration/log/focus schedule artifacts, not merely free-form IDs. It also
requires the map's exact source cardinality, A/B lineage, sitting class,
sensor fingerprint, deterministic NPZ hash/types/shape/range, estimator
freeze, and passing V result before altering RAW pixels.

The measured output contract remains:

| Property | Measured result |
|---|---|
| 16-bit | `BitsPerSample=[16,16,16]`, unsigned |
| Linear | ICC RGB TRCs all `1.0`; LibRaw `gamma=(1,1)` |
| Embedded profile | ICC RGB/XYZ matrix, D50 media/header white, and gamma-1 TRCs independently parsed |
| Producer/profile match | **D50-compatible; exact ICC byte identity not claimed:** LibRaw's matrix matches independent Bradford D50 adaptation and both gamma-1 profiles render the witness patches identically |
| Uncompressed | TIFF `Compression=1` |
| Native dimensions | burned one-frame probe produced `[4688,7028,3]` from a `7028 x 4688` active image |
| Development tags | strict allowlist; an unlisted tag is a Rust test refusal |

The one-frame development probe remains
`DEVELOPMENT_ONLY_NONCONTRACT`, applied no map, emitted no TIFF, and used only
the burned calibration-slide source. Its output byte hash remained
`27dbd01c5fcfd15ebbf89b059faca9e015b6aaea06b75ae30210cbea3c4179cf`.

## ProPhoto semantics audit

### Exact assumption under test

**INFERRED BY READING.** The current producer assumes that LibRaw's
`ColorSpace.ProPhoto` output is linear, D50-adapted ProPhoto RGB and that the
hard-coded ICC operationally describes those samples. The operative source is:

```python
(b"bXYZ", icc_xyz(0.0313534, 0.0000857, 0.8252100)),
(b"gXYZ", icc_xyz(0.1351917, 0.7118741, 0.0000000)),
(b"rXYZ", icc_xyz(0.7976749, 0.2880402, 0.0000000)),
(b"wtpt", icc_xyz(0.9642200, 1.0000000, 0.8252100)),
```

and:

```python
"output_color": rawpy.ColorSpace.ProPhoto,
"output_bps": 16,
"gamma": (1.0, 1.0),
```

The TIFF writer stores unsigned, interleaved, uncompressed RGB16 and embeds
those exact profile bytes in TIFF tag `34675`. The profile is therefore
embedded, not merely assumed. It is ICC v2.1, display class `mntr`, RGB data
space, XYZ PCS, with gamma-1 TRCs. Because standard ROMM/ProPhoto uses its
piecewise approximately 1.8 encoding curve, the accurate name for the M165
artifact is a **custom linearized ProPhoto/ROMM-primaries profile**, not the
standard encoded ProPhoto representation.

### Independent profile witness

**VERIFIED BY RUNNING.** Pillow 12.2.0 with LittleCMS 2.18 independently
accepted the profile and measured:

| Field | Result |
|---|---|
| Description | `M165 Linear ProPhoto RGB D50 v1` |
| Version / class / spaces | `2.1` / `mntr` / `RGB` -> `XYZ` |
| White chromaticity | `(0.34566868, 0.35849635)`, within `0.00005` of registry D50 |
| Red primary | `(0.73469847, 0.26530153)` |
| Green primary | `(0.15960225, 0.84039775)` |
| Blue primary | `(0.03660361, 0.00010687)` |
| RGB TRCs | `1.0`, `1.0`, `1.0` |

The independent `colour-science` 0.4.7 ROMM/ProPhoto dataset supplied the
published primaries `R(.7347,.2653)`, `G(.1596,.8404)`,
`B(.0366,.0001)` and D50 `(.3457,.3585)`. Ten known RGB patches transformed
through LittleCMS agreed with independent `colour-science` linear-ProPhoto to
sRGB calculations within zero 8-bit codes in this battery. Neutral code
`128` mapped to sRGB code `188`; treating the same code as standard nonlinear
ROMM mapped it to `146`, a 42-code separation. The embedded profile declaration
is therefore **PROVED** and the probe distinguishes linear from standard
encoded ROMM.

**VERIFIED BY RUNNING.** The audited development common TIFF was read once
into immutable memory; SHA-256 and parsing used those same bytes:

| Covered bytes | SHA-256 |
|---|---|
| Whole TIFF `[0,75040)` | `b2872db41b4b8fa0f02b504f7f7440e142c8701f92031b56939768688b82442b` |
| Embedded ICC `[764,1312)` | `16c8cad1299737e912d72ad83e959a9f879519a5fd2aaddb82ce103ebeca08ef` |
| Uncompressed pixel strip `[1312,75040)` | `fb66e83a8ff7c310fee1de0a201895761b0f6840ac4de51affff3c63999f2f15` |

The strip hash also equalled the independently decoded RGB16 byte hash.

### Producer semantic compatibility

**VERIFIED BY RUNNING.** rawpy `0.27.0` reported LibRaw `0.22.1`; constructing
its actual parameters with `ColorSpace.ProPhoto`, 16 bits, and gamma `(1,1)`
produced `output_color=4`. A separate LibRaw 0.22.1 `dcraw_emu` development
decode with `-o 4 -6 -W -g 1 1 -T` emitted a 496-byte ICC with SHA-256
`a1792592ee42de0e22b292797094cecbdd120bea07d2dd00a82ebdb7aa2cfbe4`.
LittleCMS parsed it as:

```text
ProPhoto D65 gamma 1 toe slope 1
media white XYZ = (0.9504547119, 1.0, 1.0890502930)
```

The generated profile is not byte-identical to M165's profile. Its media white
is D65 while M165's is D50, and the maximum colorant XYZ delta is
`0.000183106`. That difference is profile metadata, not by itself evidence
that LibRaw's pixel values are D65-relative.

**VERIFIED BY RUNNING** and **INFERRED BY READING.** The primary pixel-space
witness is LibRaw 0.22.1's exact `colorconst.cpp`, SHA-256
`cad6b9a6661400e70de73fe0c0f9eae501ed58d98c8ecad7afae54275798609b`.
Its `prophoto_rgb` matrix differs from independent `colour-science` Bradford
D50 adaptation by `0.000216269`, versus `0.286834150` without chromatic
adaptation. Independently, LittleCMS produced zero differing 8-bit codes
between the LibRaw-generated and M165 gamma-1 profiles for the ten frozen
patches. The defensible producer result is therefore
`D50_COMPATIBLE_EXACT_PROFILE_BYTE_IDENTITY_NOT_CLAIMED`. LibRaw's D65
`pwhite` and description remain recorded, but are not used as pixel-space
proof.

### Consumer interpretations

| Required consumer | Evidence basis | Result |
|---|---|---|
| Strehl | **VERIFIED BY RUNNING** byte boundary; **INFERRED BY READING** adapter source | `HONORS_FROZEN_SAMPLE_SEMANTICS`: requires the ICC hash and presents exact unscaled `u16` values to merge |
| Retained fork | **VERIFIED BY RUNNING** and **INFERRED BY READING** pinned source | `DIVERGES`: no ProPhoto mode; 16-bit input bypasses conversion under assumed output-space semantics, default sRGB |
| Zerene PMax | **INFERRED BY READING** vendor documentation | `PROPHOTO_UNPROVABLE_WITHOUT_LICENSED_CONTROLLED_RUN_OR_VENDOR_STATEMENT_ON_INTERNAL_PIXEL_PIPELINE` |
| Zerene DMap | **INFERRED BY READING** vendor documentation | same |

**VERIFIED BY RUNNING.** The exact frozen fork executable consumed ten
synthetic RGB16 cases spanning gamma-1 versus gamma-1.8 ICCs and all five
advertised input-color modes. Every decoded output had SHA-256
`14323867654d3781278c6713fa4a5213858ce3f14d6b0627cdc138fbcfedabad`
and no ICC tag. The null is movable: changing the actual pixel payload changed
both input and fork output to
`b64c1a930a0ce101abfdd4f0263c0d7961cfa508a58d350dc29ac742d1b7789a`.
The probe is therefore responsive to pixels while specifically insensitive to
ICC transfer semantics.

The verifier read each 74,480-byte fixture once, hashed and parsed those same
immutable bytes, and held a Win32 `CreateFileW` handle with `FILE_SHARE_READ`
through every child exit. The consumer's two expected path opens per run were
therefore allowed while replacement or mutation was denied; file identity,
size, and last-write metadata remained unchanged. For the gamma-1 fixture,
SHA-256 over whole-file `[0,74480)` was
`7d54c57cf5f5fc4da41a504c653b00606fad4ab01ab32ab9fb7f21fa5c746d26`;
the uncompressed RGB16 payload and every fork output decoded to
`14323867654d3781278c6713fa4a5213858ce3f14d6b0627cdc138fbcfedabad`.

The semantic consequence is measurable: common-input code `32768` means
linear `0.50000763`, while the fork's documented sRGB-OETF interpretation
decodes to `0.21404820`, a `0.28595943` linear-light difference.

**INFERRED BY READING.** Zerene's vendor page says embedded profiles are read
for screen display, can be copied to output, and explicitly mentions both
ProPhoto RGB and linear profiles. It contains no PMax or DMap pipeline
statement. That does not establish whether either stack method transforms
through the embedded TRC before computation. A licensed controlled run or a
vendor statement on the internal pixel pipeline remains required.

The required-consumer partition is exhaustive:

```text
1 HONORS_FROZEN_SAMPLE_SEMANTICS
+ 1 DIVERGES
+ 2 PROPHOTO_UNPROVABLE_WITHOUT_LICENSED_CONTROLLED_RUN_OR_VENDOR_STATEMENT_ON_INTERNAL_PIXEL_PIPELINE
= 4 required consumers
```

### Commissioning and verdict

**VERIFIED BY RUNNING.** The baseline completed with
`68 PASS + 0 RED = 68`. A unique full-line mutation changed only the expected
linear neutral from `188` to `180`; the gate returned exit `1` with exactly
`67 PASS + 1 RED = 68` and
`PROFILE_NUMERIC_NEUTRAL_MISMATCH`. The unrelated `TIFF_STORAGE` arm remained
`1 PASS + 0 RED = 1`. Exact byte restoration was the planted improvement and
returned to `68 PASS + 0 RED = 68`; the repaired reference hash equalled the
baseline hash.

The gate read 39 verifier path artifacts once each at most, while Git blobs
were read once directly from their pinned object IDs and the fork input paths
remained locked through consumer exit. Two complete same-input baseline runs
produced byte-identical result JSON at SHA-256
`94032be73acdfde6ef30f26f7987d168312c7874cb36524912cda2ea8932fb81`.
Its committed evidence lives in
`experiments/M165-prophoto-semantics/`. The gate source SHA-256 is
`92972001d402b1973ecd4c347acb26b1e301ee4a71b731c5c1447ecd5c0da1eb`;
the commission result is
`b38ec7fa4594f93a3cffa40f294b8d3a3277be44d8be157f293aaac8018d6f24`;
and the deterministic freeze manifest is
`24211d045e48621387727db3037f6e665e5b990bcd1b0c85c9cb5f4bb9121db7`.

**FORMAL VERDICT: `PROPHOTO_DISPROVED`.** The file contains a valid embedded
linearized-ProPhoto D50 ICC and the current LibRaw producer is operationally
D50-compatible under the independent matrix and patch witnesses. The required
retained fork nevertheless interprets the 16-bit values under incompatible
sRGB-OETF/output-space semantics and omits the ICC. Zerene's internal
interpretation remains separately unproved. This is an input-contract result,
not a quality comparison.

## Strehl byte identity

The current 7 x 5 synthetic TIFF has:

- whole-file SHA-256
  `a1ec6e639bda27d204fdb27dc5dbb9ed5afdee834ac9acad0595a2fdd181fe66`;
- TIFF pixel-payload SHA-256
  `17258eb77d5692e323acb659ddc1787b275fabf71cd170e503c5d9cb65c5977b`;
- Rust-decoded internal `u16` SHA-256: the same; and
- bytes reconstructed from the exact `f32` RGB plane allocations passed to
  `BandMerge::add_frame`: the same.

`core_merge_exercised=true` proves the allocations entered the real generic
merge core. The original Stage 0M commissioned verifier binary SHA-256 is
`846bc33be7b64ea36260918311e7ab2cdce629de4a0aeb1df23373f9ec60a7f5`.
The comparator registry remains arbitrary-length with a first-class executable
hash for every consumer, including the rebuilt fork below.

Identity sensitivity remains commissioned:

- flipping one inert TIFF bit preserved the payload hash, changed the whole
  file hash to
  `5ad1294276ec56a0bc0a7e07f3b210d6d9a91f8471267e16f6e2cb6f50a794f4`,
  and failed;
- changing one pixel sample from `1000` to `1001` changed the payload hash to
  `f229a267899a682ab9b4fffd8533c1429aa893d6f236224ee7d1f5cd43abbd68`
  and failed; and
- restoring the bytes passed.

**STREHL BYTE IDENTITY IMPACT: NONE.** Stage 0M adds the provenance required to
admit a map. It does not change the byte-identity boundary or its result.
Campaign identity remains **NOT YET TESTABLE** until real maps and TIFFs exist.

## Stage 0C commissioning and present readiness

### Commissioning

**VERIFIED BY RUNNING — machinery only, not comparator evidence.** The
commissioning campaign used two generated common TIFFs:

| Input | Dimensions | Whole-file SHA-256 | Pixel-payload SHA-256 |
|---|---:|---|---|
| `input-a` | `7 x 5` | `c7683da77256d3fdc7acd1d1a8b38cb3b9fcc9ce948bc51d1347289e94e08456` | `4b9edeedbf0820c6d51313d37c5239cba7aca948e234d23c6820b3c5a0325084` |
| `input-b` | `9 x 6` | `64101a62a97e70774354d35bba84ade56056f0b7c5460ce20a55f1e13d5b3774` | `d5efeea996096a824c18a59ca63af451090d92dbbf340a4cc4f2bfb0bbb06cba` |

The actual Strehl verifier consumed both inputs and exercised the generic merge
core. Its commissioning executable SHA-256 was
`abbcdcedd58400c45db49284654a0f6815b3c0ffadc0d64282cadb388fc9fa42`;
its source SHA-256 was
`0abf5917357365ba83028f82c0a2855917ad45071d95d3ec2d404702de1ef31f`.
The other three required-consumer slots were explicitly named `*-fixture` and
used the commissioning-only independent reader. They commission the receipt
gate and make no claim about Zerene or the fork.

The clean matrix contained two inputs, four required consumers, and one
unavailable optional consumer:

- required pairs: `8 PASS + 0 FAIL + 0 MISSING + 0 BLOCKED = 8`;
- optional pairs: `0 PASS + 0 FAIL + 0 MISSING + 0 BLOCKED +
  2 OPTIONAL_ABSENT = 2`;
- all pairs: `8 + 2 = 10`; and
- inputs: `2 PASS = 2`.

Every partition reported `partition_balanced=true`, and the read audit reported
`maximum_reads_per_artifact=1`.

The planted degradation replaced exactly one unique full line in the
PMax-fixture receipt:

```text
"input_file_sha256": "c7683da77256d3fdc7acd1d1a8b38cb3b9fcc9ce948bc51d1347289e94e08456",
->
"input_file_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
```

The mutation helper first proved that an absent anchor hard-errors. The actual
mutation then made the gate `FAIL`, partitioning the required matrix as
`7 PASS + 1 FAIL = 8` and the inputs as `1 PASS + 1 FAIL = 2`. Restoring the
exact original receipt bytes returned `8 PASS = 8` and `2 PASS = 2`. Removing
one receipt separately produced `7 PASS + 1 MISSING = 8`, and malformed
campaign JSON exited `1` with a persisted `FAIL / JSON_INVALID` report.
A cross-consumer substitution that pointed the DMap receipt at the PMax
attestation failed as `ATTESTATION_CONSUMER_MISMATCH`, with
`7 PASS + 1 FAIL = 8` required pairs.
A separate registry with every required consumer deliberately blocked produced
`8 BLOCKED = 8` required pairs and `2 BLOCKED = 2` inputs.

The Stage 0C commission report SHA-256 is
`576d4e198131371be579abda2752d86cbfa0677c42bec845d6f35a4345b426c4`.

### Pre-rebuild consumer readiness (superseded snapshot)

**VERIFIED BY RUNNING.** Before the fork rebuild, the machine audit partitioned
all four required modes:

| Required consumer | Outcome | Direct evidence |
|---|---|---|
| strehl | `READY_FOR_SYNTHETIC_IDENTITY_ONLY` | Current adapter binary, source, and existing identity report were present and hashed. |
| Zerene PMax | `BLOCKED_LICENSE_EXPIRED` | Installed build `1.04T2026-05-04-0750`; retained log says trial expiry `2026-06-06`, which precedes this audit. |
| Zerene DMap | `BLOCKED_LICENSE_EXPIRED` | Same installed runtime and expired licence; it is a separately required mode. |
| retained-source fork | `BLOCKED_NO_REPRODUCIBLE_BINARY` | See the reading-derived ruling below. |

The partition is
`1 READY_FOR_SYNTHETIC_IDENTITY_ONLY + 2 BLOCKED_LICENSE_EXPIRED +
1 BLOCKED_NO_REPRODUCIBLE_BINARY = 4`. The installed Zerene launcher SHA-256 is
`aeb428ca38df27b61b1031ec34064382dd9ea3ff929a17505e180000d75b1efd`;
the application JAR SHA-256 is
`e138ce88bedf2cfab7ef78aa2398a57ca4944ec09571c285a0a11c10bcb4e549`.
Those hashes identify the blocked installation; they do not make it licensed
or frozen for scoring.

The persisted readiness report SHA-256 is
`843481fb3097ff431967aa6f7cd90c17ccfebecac9f8d1b1f2dee286f6f74de8`.

**INFERRED BY READING.** M162 established that the archived fork has no
admissible producer binary. The exact unblock was a fresh build of retained commit
`4bc7f95e448cf20ee2bdd758403ec43e2612a1c6`, with source tree, toolchain,
dependency lock, compiler flags, settings, invocation, and final executable
SHA-256 frozen before rendering. That rebuild is now complete below; this
earlier audit remains useful only as the before-state.

**VERIFIED BY RUNNING, TARGETED PATH PROBE.** No Helicon executable was found
at the four documented Windows installation paths. **INFERRED BY READING.**
M132's broader machine audit also found none. Under the live scorecard Helicon
is optional when unobtainable, so this is `OPTIONAL_ABSENT`, not a required-arm
blocker.

**INFERRED BY READING.** The precise owner ask for Zerene is: after written
permission to publish the black-box comparison, buy Prosumer for `$189` plus
tax if this remains eligible personal/unfunded use; otherwise buy Professional
for `$289` plus tax. Do not buy Helicon to clear Stage 0C.

**PRE-REBUILD STAGE 0C VERDICT: BLOCKED.** This snapshot predates the fork
work below.

### Fresh retained-source fork arm

#### Revision selection

**VERIFIED BY RUNNING.** The selected revision is
`4bc7f95e448cf20ee2bdd758403ec43e2612a1c6`, the root and earliest retained
`focus-stack` source commit in `C:\dev\macro`. Its commit time is
`2026-05-10T19:56:59-07:00`. The archived best-run log at
`C:\dev\macro\out\coffee-bean\stack.log` has SHA-256
`cfc2837ca87219f0150e14e2151d3f89fe81ade9920f5dbfc082cfb6369ab283`
and last-write time `2026-05-10T23:45:16.3564650Z`; the selected commit is
approximately three hours twelve minutes later. The next retained revision,
`412d1b5226f69b186a6e8b8ef91b4befa3c55664`, changes 27 `focus-stack`
files by 1,582 insertions and 154 deletions.

**INFERRED FROM THAT EVIDENCE.** `4bc7f95e...` is the nearest and
least-confounded retained source snapshot, so it is the best-supported rebuild
target. It is **not** claimed to be the archived producer. The machine-readable
selection evidence is `experiments/M165-fork-rebuild/revision-selection.json`.

#### Source and executable freeze

**VERIFIED BY RUNNING.** `freeze_fork_source.py` read Git objects directly,
not the mutable external worktree. The frozen `focus-stack` subtree is Git
SHA-1 `543b825e325f959ed15c10032d2b8156f11070cc`, containing 103 files and
14,961,176 bytes. Its canonical per-blob manifest SHA-256 is
`494d3abb49ccec3f23d7c37676acd806111f973f12c0cf416ae45999359d1196`;
`source-pin.json` itself is
`f883a1c80d83fec83f3ada3381b9cc07acfe4d8b2e2cb2a0b7b07915f1bb7577`.
Regenerating the pin with the same frozen timestamp reproduced that file byte
for byte.

`build_fork.py` extracted those exact blobs into two clean, different source
and build paths. Both builds emitted the same 271,360-byte executable:

```text
SHA-256 691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac
byte differences between clean builds: 0
```

The formal verdict is
`BIT_REPRODUCIBLE_TWO_CLEAN_PATHS_SAME_HOST`. Cross-host reproducibility was
not tested. The executable hash covers `[0,file_size)`. It was frozen at
`2026-09-04T19:40:58.497473+00:00` before any image render; the only
pre-freeze executions were `--version`. The version banner binds the selected
commit and reports OpenCV `4.13.0`.

The frozen toolchain is MSVC `19.44.35226.0`, linker/NMake
`14.44.35226.0`, VC tools `14.44.35207`, CMake `3.31.6-msvc6`, and Windows
SDK `10.0.26100.0`. The decisive flags are `/Brepro`,
`/experimental:deterministic`, a commit-valued `GIT_VERSION`, and
`/pathmap:<source>=C:\m165\focus-stack`, with `/Brepro` on executable and
static linkers. The bundle includes the executable, OpenCV, and four MSVC
runtime DLLs; its canonical SHA-256 is
`4b9d4c310a16294bcc46ee5b947aec02cbdba9887787af017018071dd9455150`.
`build-freeze.json` binds every tool/dependency byte hash and has SHA-256
`ccc80840ba2f7971cc5e78df7422d0840032e843d57c9757597783532859a5a2`.

The reproducer is:

```text
python experiments\M165-fork-rebuild\freeze_fork_source.py ^
  --repo C:\dev\macro ^
  --commit 4bc7f95e448cf20ee2bdd758403ec43e2612a1c6 ^
  --frozen-utc 2026-09-04T19:25:44.711441+00:00 ^
  --out experiments\M165-fork-rebuild\source-pin.json

python experiments\M165-fork-rebuild\build_fork.py ^
  --repo C:\dev\macro ^
  --commit 4bc7f95e448cf20ee2bdd758403ec43e2612a1c6 ^
  --source-pin experiments\M165-fork-rebuild\source-pin.json ^
  --vcvars "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" ^
  --opencv-build C:\dev\macro\deps\opencv\build ^
  --work experiments\M165-fork-rebuild\work\repro ^
  --bin experiments\M165-fork-rebuild\bin ^
  --frozen-utc 2026-09-04T19:40:58.497473+00:00 ^
  --out experiments\M165-fork-rebuild\build-freeze.json
```

#### Real fork consumer admission

**VERIFIED BY RUNNING — development input only, not a quality comparison.**
The rebuilt executable consumed one generated 128 x 96 common TIFF twice, as
required by its two-input CLI, and returned exit `0` with a 7,020-byte output
whose SHA-256 is
`68139558bb33a795d1fb7a5aaf007bf56b70f22c360b55a23542052d85cc4fed`.
The input measured 75,040 bytes, `BitsPerSample=[16,16,16]`,
`Compression=1`, and contained the frozen linear ProPhoto D50 ICC.

`fork_consumer.py` is independent of the Stage 0C TIFF parser. It opened the
input once with Win32 `CreateFileW`, `GENERIC_READ`, and `FILE_SHARE_READ`;
hashed and parsed the same in-memory bytes; held that handle through child
exit; and verified unchanged volume/file identity, size, and last-write
metadata before and after consumption. Converter manifest, locked adapter, and
Stage 0C gate independently agreed:

| Range | SHA-256 |
|---|---|
| Whole TIFF `[0,75040)` | `b2872db41b4b8fa0f02b504f7f7440e142c8701f92031b56939768688b82442b` |
| Pixel payload strip `[1312,75040)` | `fb66e83a8ff7c310fee1de0a201895761b0f6840ac4de51affff3c63999f2f15` |

The truthful five-consumer registry counted every result:

- required: `2 PASS + 0 FAIL + 0 MISSING + 2 BLOCKED = 4`;
- optional: `1 OPTIONAL_ABSENT = 1`;
- all consumer/input pairs: `2 PASS + 2 BLOCKED + 1 OPTIONAL_ABSENT = 5`;
- input: `1 BLOCKED = 1`, because both Zerene modes remain unavailable.

Both passing required pairs are real: Strehl and the rebuilt fork. Both blocked
pairs are licensed Zerene PMax and DMap. The full roster therefore correctly
remains `FAIL/BLOCKED`, rather than turning a partial prerequisite into a
scorecard pass. The roster uses an M165-local frozen copy of the Strehl
verifier, SHA-256
`8e807de32b63859fe0a00fa81a791b08b70cbbca57bd1ee5195eaab0bd811a2b`,
rather than the concurrently mutable Cargo target path. Its gate artifact
SHA-256 is
`f44625bd8bb8ed53960b9dc6d1a37385510fba9c577030ec81cf2a98d554ce2f`.

The isolated fork-arm null passed `1 PASS = 1`. The mutation helper first
hard-failed on an absent anchor, then replaced the unique full line

```text
"input_file_sha256": "b2872db41b4b8fa0f02b504f7f7440e142c8701f92031b56939768688b82442b",
->
"input_file_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
```

and the gate went RED as `RECEIPT_INPUT_HASH_MISMATCH`,
`0 PASS + 1 FAIL = 1`. Restoring the exact original receipt bytes returned
`1 PASS = 1`; the baseline and repaired gate files are byte-identical with
SHA-256
`d8f16887750c71e53c819c269bdada18810103a5f8d524e9ca98f4bbedae3e69`.
Supplying the adapter a wrong executable hash separately exited `1`, persisted
`FAIL / EXECUTABLE_HASH_MISMATCH`, and created no output. The complete
commission report is `PASS`, SHA-256
`e22a787fa3276dd6def780aa13734ac1a597c3ca7063249825a4b221697c28ca`.

**STREHL BYTE IDENTITY IMPACT: NONE.** The fork is an additional registered
consumer; it does not change Strehl's already commissioned internal boundary.

**CURRENT REAL STAGE 0C VERDICT: BLOCKED.** The fork executable and exact-byte
admission blocker is closed. Remaining prerequisites are a corrected and
re-frozen fork consumer path that honors the frozen color semantics, licensed
Zerene PMax and DMap, and an eligible calibrated campaign capture. The producer
D50-semantic question is closed as compatible by the audit above.

**Color-semantic result.** The pinned fork has no ProPhoto input mode.
Its 16-bit integer TIFF path passes decoded samples through without input-color
conversion and does not interpret the embedded ICC. Exact file-byte admission
is proven; color-semantic equivalence is **disproved**, not merely unproved.
This is inferred directly from the pinned `src/colormgmt.cc` and verified by
the 11-run semantic battery above:
`parse_input_colorspace` admits only auto/none/linear-Rec.2020/linear-sRGB/sRGB,
and `normalise_loaded_image` returns `CV_16U` input unchanged.

## Capture requirement and totals

For each optical state in each sitting, acquire exactly:

| Group | Acquired | Used |
|---|---:|---:|
| `DARK-A` | 32 | 30 after settling |
| `FLAT-A` | 32 | 32 |
| `DARK-B` | 32 | 30 after settling |
| `FLAT-B` | 32 | 32 |
| `DARK-V` | 32 | 30 after settling, never fitted |
| `FLAT-V` | 32 | 32, never fitted |

That is 192 calibration frames per optical state and 384 across the two
required optical states. M164 distributes those blocks across its stages; M165
does not alter its arithmetic.

If either optical-state package cannot remain inside the frozen temperature
class or its near/far V block rejects focus portability, the result is STOP /
`UNMEASURED`. Adding a third class after seeing the failure is forbidden.

## Validation

- Pattern-map commissioning: **PASS**.
- Stage 0M manifest/refusal battery: **PASS**.
- Deterministic estimator repeat: **PASS**.
- `python -m py_compile` for converter and estimator: **PASS**.
- `cargo test -p strehl-raw common_tiff -- --nocapture`: **4 passed**.
- `cargo build -p strehl-cli --bin strehl-common-input`: **PASS**.
- Common-input TIFF commissioning: **PASS**.
- Missing-map render: exit `1`, `PATTERN_MAP_REQUIRED`, no TIFF created.
- Blocked fork registry: exit `1`, `CONSUMER_REGISTRY_NOT_FROZEN`.
- Independent .NET/Python/Rust hash audit: **PASS**.
- Stage 0C consumer-boundary commissioning: **PASS**.
- Stage 0C clean partition: `2/2` inputs and `8/8` required
  consumer/input pairs passed; `2/2` optional pairs were counted
  `OPTIONAL_ABSENT`.
- Stage 0C unique-line hash mutation: **FAIL as required**, exactly one
  required pair and one input failed.
- Stage 0C receipt restoration: **PASS**.
- Stage 0C missing receipt: **FAIL as required**, exactly one required pair and
  one input were counted `MISSING`.
- Stage 0C cross-consumer attestation substitution: **FAIL as required** with
  `ATTESTATION_CONSUMER_MISMATCH`.
- Stage 0C blocked-registry probe: **FAIL as required**, `8/8` required pairs
  and `2/2` inputs were counted `BLOCKED`.
- Stage 0C malformed campaign: exit `1`, persisted `FAIL / JSON_INVALID`.
- Stage 0C receipt-record CLI reproduced the library-generated receipt byte for
  byte.
- Pre-rebuild consumer-readiness audit: exit `1`, persisted `BLOCKED`, required
  consumer partition balanced `4/4`.
- Fork source pin regeneration: **byte-identical PASS**.
- Fork two-clean-path build: **PASS**, zero differing executable bytes.
- Frozen fork executable: 271,360 bytes, SHA-256
  `691eada94d451fdc06baaddb7edee86ee85472d8aff4fa915dab468ef8f609ac`.
- Fork locked-handoff consumer run: exit `0`; converter, adapter, and gate
  whole-file and payload hashes all agreed.
- Truthful current development roster: `2 PASS + 2 BLOCKED = 4` required
  pairs; `1 OPTIONAL_ABSENT = 1`; every partition balanced.
- Fork-arm unique-line receipt mutation: **FAIL as required** with
  `RECEIPT_INPUT_HASH_MISMATCH`, exactly `1/1` pair failed.
- Fork-arm exact repair: **PASS**, exactly `1/1` pair passed.
- Fork adapter wrong-executable-hash probe: exit `1`, persisted
  `FAIL / EXECUTABLE_HASH_MISMATCH`, no output.
- ProPhoto semantic-gate baseline: `68 PASS + 0 RED = 68`; formal evidence
  verdict `PROPHOTO_DISPROVED`.
- ProPhoto unique-line mutation: exit `1`,
  `PROFILE_NUMERIC_NEUTRAL_MISMATCH`, exactly `67 PASS + 1 RED = 68`;
  unrelated `TIFF_STORAGE` stayed green.
- ProPhoto exact repair/planted improvement: `68 PASS + 0 RED = 68`.
- Fork semantic battery: ten ICC/mode variants produced one decoded pixel
  hash and no ICC; a distinct pixel input produced a distinct output hash.
- Fork semantic handoff: one verifier read per fixture; locked child opens;
  identity/size/last-write metadata unchanged through every consumer exit.
- ProPhoto one-read audit: 39 verifier path artifacts, maximum read count one.
- ProPhoto repeatability: two full commissioning reruns produced byte-identical
  baseline, degraded, improvement, commission, and freeze artifacts.

**Blocked on compute: NO.** No bulk decode was launched. Real RAW work was
limited to one-frame burned-development probing. Under the standing host
policy, deterministic fitting/rendering may proceed under load when inputs
exist; absolute timing remains quarantined. The present blockers are fork
color semantics, missing physical inputs, and licensed Zerene modes, not host
scheduling.

## Residual doubt

1. The thresholds are frozen from prior measured noise/PRNU evidence and
   synthetic commissioning; a real 33 MP V block may still reject them.
2. External body temperature is a proxy, not a sensor-junction measurement.
   The held-out dark residual is intentionally the final authority.
3. One focus class per optical state is a tested design, not a guaranteed
   physical fact. A failed endpoint V block requires a newly preregistered
   multi-class design and new captures.
4. No eligible pattern-map photons exist, so no real map or common TIFF has
   passed this chain.
5. The adapter reaches the generic merge core, but the shipping `strehl stack`
   command remains a CFA-native path; common-track RGB registration, noise
   modelling, output, and directory orchestration remain separate integration
   work.
6. The fork executable is reproducible across two clean paths on this host;
   cross-host bit reproducibility is not yet measured.
7. The producer is D50-compatible at the tested operational boundary, but the
   M165 and LibRaw-generated ICC files are not byte-identical. The generated
   profile's D65 metadata is recorded and is not treated as pixel-space proof.
8. The pinned fork's 16-bit input path ignores the embedded ProPhoto ICC. The
   byte contract passes, but color-semantic equivalence is disproved.
9. The Stage 0C standard attestation now has a real fork locked-handoff result,
   but no Zerene or Helicon receipt. The gate refuses their absence; it does
   not infer consumption from an output file.
10. Zerene documentation proves profile-aware display/output handling, not
    PMax or DMap's internal stack math. That semantic claim still requires a
    licensed controlled run or a vendor statement.

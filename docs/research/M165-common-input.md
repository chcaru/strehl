# M165 — common linear input, pattern-map gate, and Strehl byte identity

## Verdict

**Stage 0M is closed in software. The competitive package is still
`UNMEASURED`.**

M165 now provides:

- a frozen LibRaw common-merge converter;
- a deterministic uncompressed linear ProPhoto D50 TIFF writer;
- a strict Strehl TIFF adapter and pre-merge byte-identity verifier;
- a frozen A/B dark/flat estimator with a never-fitted V validation block;
- enforceable two-class-per-sitting cardinality;
- external physical-body, temperature, focus-schedule, and flat-field-state
  provenance; and
- fail-closed synthetic commissioning for the estimator and every new refusal
  boundary.

No eligible real calibration capture exists. Therefore no real pattern map, no
campaign common-merge TIFF, and no campaign Strehl byte-identity result exists.
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
   used Lightroom-developed TIFFs and has no producing executable. M165 retained
   the comparator-agnostic registry and first-class consumer executable hash;
   none of the Stage 0M work changes the Strehl byte-identity method.

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
| ProPhoto D50 | ICC RGB/XYZ matrix and D50 media/header white inspected |
| Uncompressed | TIFF `Compression=1` |
| Native dimensions | burned one-frame probe produced `[4688,7028,3]` from a `7028 x 4688` active image |
| Development tags | strict allowlist; an unlisted tag is a Rust test refusal |

The one-frame development probe remains
`DEVELOPMENT_ONLY_NONCONTRACT`, applied no map, emitted no TIFF, and used only
the burned calibration-slide source. Its output byte hash remained
`27dbd01c5fcfd15ebbf89b059faca9e015b6aaea06b75ae30210cbea3c4179cf`.

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
merge core. The commissioned verifier binary SHA-256 is
`846bc33be7b64ea36260918311e7ab2cdce629de4a0aeb1df23373f9ec60a7f5`.
The comparator registry remains arbitrary-length with a first-class executable
hash for every consumer, including a future rebuilt fork.

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

**Blocked on compute: NO.** No bulk decode was launched. The only real RAW work
was the previously authorized one-frame burned-development probe. Fitting real
full-resolution maps and rendering a campaign will require both new
calibration captures and a released quiet compute window.

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
6. The fork still lacks a rebuilt, hashed executable and therefore remains a
   blocked common-merge consumer.

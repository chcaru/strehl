RECONCILED: rehearsal 1,092, scored 1,215, total 2,307

# M166 — capture reconciliation and merged staircase

Status: **CURRENT FULL-PROGRAM COUNT RECONCILED; CAPTURE RELEASE REMAINS
BLOCKED AT ZERO REHEARSAL FRAMES**

## 0. Ruling

**INFERRED BY READING.** M164 and M166 describe the same physical program only
up to the M1-only boundary. They are genuinely different asks after that
boundary:

- M164's `704`-frame sealed block is an earlier **M1-only** score design.
- M166's `1,215`-frame sealed block is the current **combined M1/M5/M9** score
  design after the reference, complete-input dominance witness, and held-out
  calibration corrections.

**VERIFIED BY RUNNING.** Commit ancestry and commit dates place M164's
pattern-map integration at `cdae4723` before M166's successive corrections at
`a195bc63`, `ff99afc8`, and `fd1f46cf`. The current branch contains those
commits in that order.

**INFERRED BY READING.** The controlling plan requires a capture session that
supplies the missing capture and truth-instrument inputs together; it does not
authorize silently dropping the M5/M9 roles from the owner-facing program.
Therefore the current owner ask is M166's combined path:

```text
two-frame scale/field preflight, outside both sittings       2
exact-configuration development rehearsal                1,092
fresh sealed combined M1/M5/M9 scored sitting            1,215
                                                        -----
two-sitting registered capture total                     2,307
owner program including the preflight                     2,309
```

**INFERRED BY READING.** The `2,307` total excludes the two preflight frames.
The preflight is a kill gate, not rehearsal or scored evidence. One
unregistered histogram/setup release per sitting and any refused or repeated
preflight attempt are also outside these registered-frame totals.

**INFERRED BY READING.** There is no remaining owner decision between a
`704`-frame M1-only score and a `1,215`-frame combined score unless the
orchestrator deliberately reopens program scope and chooses to defer M5/M9.
That would be a named **scope reduction**, not an arithmetic variant of the
current ask. No M164 ruling is needed to reconcile the current full-program
budget.

**INFERRED BY READING.** A separate M164 ruling is still required before the
two dominance-witness stages can use an interim optical futility stop:

> Will the production M164 manifest issue a hash-bound best-case impossibility
> certificate after a complete `TC0-DOM-sw4-A/B` or
> `TC0-DOM-sw10-A/B` block?

Until M164 answers yes and commissions that certificate, those stages may
stop only on hard eligibility failures. They may never stop on an analyst's
unfavorable interim margin.

## 1. Containment, block by block

### 1.1 M164's `704` is not a literal subset of M166's `1,215`

**INFERRED BY READING.** It is tempting to write `704 < 1,215` and call the
former a subset. That is wrong at file level because M164's reference role was
a `96`-frame three-strip design, while M166 replaces it with four different
`32`-frame strips. Containment is by **role after supersession**, not by
reusing all `704` RAWs.

| M164 M1-only role | M164 frames | Current M166 treatment | Current frames | Relation |
|---|---:|---|---:|---|
| converter-on three-strip fixed-focus reference | `96` | `TR-S01` through `TR-S04`, four strips at `32` each | `128` | **replaced**, not retained; `+32` net |
| converter-on `FLAT-A/DARK-A/FLAT-B/DARK-B` | `128` | same named A/B converter-on calibration role | `128` | retained by role |
| converter-on `FLAT-V/DARK-V` | `64` | same held-out converter-on validation role | `64` | retained by role |
| TC0 candidate `sw4-A/B` and `sw10-A/B` | `164` | same candidate input role, `55+55+27+27` | `164` | retained by role |
| TC0 candidate reset/start/end witnesses | `60` | same G0–G3 execution-witness role | `60` | retained by role |
| TC0 `FLAT-A/DARK-A/FLAT-B/DARK-B` | `128` | same named A/B TC0 calibration role | `128` | retained by role |
| TC0 `FLAT-V/DARK-V` | `64` | same held-out TC0 validation role | `64` | retained by role |
| **M164 M1-only score** | **`704`** | superseded M1-role package after the four-strip replacement | **`736`** | `704 - 96 + 128 = 736` |

**VERIFIED BY RUNNING.** The named current M1 roles above sum to `736`.

### 1.2 What M166 adds beyond the superseded M1-only package

**INFERRED BY READING.** The current complete-input and combined-score
contracts add these named roles beyond the superseded M1-only package:

| Added current role | Frames | Why it is not already in M164's `704` |
|---|---:|---|
| candidate-excluded `TC0-DOM-sw4-A/B` | `110` | two complete `55`-frame scored-path witness stacks; these RAWs are forbidden to candidate and comparator manifests |
| candidate-excluded `TC0-DOM-sw10-A/B` | `54` | two complete `27`-frame scored-path witness stacks; same exclusion |
| converter-on M5/M9 focus ladders and their witnesses | `315` | combined-score roles that M164 deliberately removed from its M1-only branch |
| **added beyond current M1-role package** | **`479`** | `110 + 54 + 315` |

**VERIFIED BY RUNNING.** `736 + 110 + 54 + 315 = 1,215`.

**INFERRED BY READING.** The two `164`-frame blocks are distinct:

- candidate **input**:
  `TC0-sw4-A/B + TC0-sw10-A/B = 55 + 55 + 27 + 27`;
- candidate-**excluded dominance witness**:
  `TC0-DOM-sw4-A/B + TC0-DOM-sw10-A/B = 55 + 55 + 27 + 27`.

Equal budgets do not make those RAWs interchangeable.

### 1.3 Equivalent derivation from the live combined base

**VERIFIED BY RUNNING.**

```text
base combined M1/M5/M9 score                         891
remove superseded three-strip converter-on reference -96
install four-strip converter-on reference            +128
add candidate-excluded TC0-DOM sw4/sw10 A/B          +164
add held-out V calibration in both optical states    +128
                                                     ----
current combined M1/M5/M9 score                     1,215
```

**INFERRED BY READING.** The final `+128` is four new `32`-frame groups:
`TR-FLAT-V`, `TR-DARK-V`, `TC0-FLAT-V`, and `TC0-DARK-V`. It is not either
of the two A/B calibration packages already inside the base score.

## 2. Why `896` became `1,092`

**INFERRED BY READING.** Yes: M164's `896` is the direct predecessor of the
current `1,092` exact-configuration rehearsal. The update is not a generic
scope expansion and it is not caused by the physical controls. Both designs
already contain the same `192` control frames:

- `TC0-SHARP` near/middle/far: `96`;
- `TC0-BLUR` near/middle/far: `96`.

The exact change is:

| Changed rehearsal role | M164 | M166 | Delta |
|---|---:|---:|---:|
| converter-on reference layout | three `32`-frame strips = `96` | four `32`-frame strips = `128` | `+32` |
| candidate-excluded complete scored-path dominance witness | absent | `TC0-DOM-sw4-A/B` `110` plus `TC0-DOM-sw10-A/B` `54` | `+164` |
| all other A/B/V calibration, candidate-input, fixed-witness, and physical-control roles | `800` | `800` | `0` |
| **rehearsal** | **`896`** | **`1,092`** | **`+196`** |

**VERIFIED BY RUNNING.**

```text
896 - 96 + 128 + 164 = 1,092
```

**INFERRED BY READING.** M164's Stage 4 used the candidate
`TC0-sw4/sw10` stacks themselves as provisional reference-transfer evidence.
M166 applies M164's later complete-input lineage rule literally: the
dominance witness must be a second, complete, source-disjoint set excluded
from candidate and comparator inputs. That new witness is the `164`-frame
addition.

## 3. Owner budget

**VERIFIED BY RUNNING.**

| Item | Registered frames | Scope |
|---|---:|---|
| development rehearsal | **`1,092`** | exact M1 configuration, including candidate execution and both physical controls |
| scored sitting | **`1,215`** | fresh, sealed, combined M1/M5/M9 score |
| two sittings together | **`2,307`** | no RAW, map, reference, site, render, fitted value, or subject/session is shared |
| scale/field preflight | **`2`** | separate kill gate before either sitting |
| **owner program including preflight** | **`2,309`** | excludes setup histogram releases and retries |

**INFERRED BY READING.** If the owner or orchestrator intentionally changes
the program to **M1-first and defers M5/M9**, the score must be re-derived from
the current M166 package, not restored to M164's stale `704`. The named
current M1-role package is `736`, and M166's complete candidate-excluded
dominance witness adds `164`, giving a current M1-only score of `900`. That
conditional branch would be:

```text
named decision: defer the 315-frame M5/M9 converter-on package
rehearsal                                               1,092
current M1-only scored sitting                            900
two sittings                                            1,992
plus the two-frame preflight                                2
owner program                                           1,994
```

**INFERRED BY READING.** The full-program branch is current because the
owner-facing capture request is explicitly the combined M1/M5/M9 scored
session and the controlling plan treats capture as the joint missing-capture
and truth-instrument input. The M1-first branch is disclosed only so no one
mistakes a future scope decision for a counting correction.

## 4. Merged staircase

**INFERRED BY READING.** Every cumulative number below starts at the two-frame
preflight. The rehearsal remains one continuously powered, uninterrupted
development sitting even though the manifest may place registered analysis
holds between complete blocks. If the rig cannot remain locked and inside
the frozen stability tolerances while a checker runs, do not stage it: stop
or capture the full ordered rehearsal without interim reads.

| Stage | New frames | Cumulative owner frames | What the stage can conclude | Allowed action |
|---|---:|---:|---|---|
| **0M — frozen contract and checker** | `0` | `0` | Missing or mutable production manifest, target, cell family, margins, reduction, settings, software, hashes, seed, block order, or fail-closed reader means the program is not executable. The current M164 record is `BLOCKED`. | **Stop-and-refuse only.** It cannot pass the optics or score anything. |
| **0 — two-frame scale/field kill test** | `2` | `2` | A valid empty feasible set, or a valid sampling/field/frequency failure at the lowest eligible placement, kills the present optical design before either sitting. A quality refusal calls for a fresh pair, not an optical verdict. | **Stop-and-refuse, or continue.** Never accept M1 from these frames. |
| **1 — converter-on A/B calibration** | `128` | `130` | Wrong body/settings/count/lineage, clipped or textured flats, light-leaked darks, temperature mismatch, or failed disjoint A/B maps. | **Stop-and-refuse, or continue.** No interim `PASS`. |
| **2a — `TR-S01` rows 1–2** | `32` | `162` | Failed row coverage, focus return, guard, tone, fiducial, geometry, or required reference power for rows 1–2. | **Stop-and-refuse, or continue.** No interim `PASS`. |
| **2b — `TR-S02` rows 3–4** | `32` | `194` | The same frozen strip predicate for rows 3–4. | **Stop-and-refuse, or continue.** No interim `PASS`. |
| **2c — `TR-S03` rows 5–6** | `32` | `226` | The same frozen strip predicate for rows 5–6. | **Stop-and-refuse, or continue.** No interim `PASS`. |
| **2d — `TR-S04` rows 7–8** | `32` | `258` | The same frozen strip predicate for rows 7–8. | **Stop-and-refuse, or continue.** No interim `PASS`. |
| **2e — converter-on held-out V closure** | `64` | `322` | Either converter-on map fails held-out flat/dark transfer, focus/temperature portability, or reference common-mode. | **Stop-and-refuse, or continue.** No interim `PASS`. |
| **3 — live TC0 placement plus TC0 A/B calibration** | `128` | `450` | Failed live scale/field placement or wrong, overlapping, non-finite, mismatched TC0 A/B map sources. The live scale check adds no registered frame unless its final protocol explicitly says otherwise. | **Stop-and-refuse, or continue.** No interim `PASS`. |
| **4a — `TC0-DOM-sw4-A/B` complete witness** | `110` | `560` | Missing node, incomplete `55+55` budget, failed focus/coverage/geometry/lineage, candidate contact, or—only if M164 commissions it—a machine-issued proof that a completed sw4 cell cannot recover under any admissible remainder. | **Stop-and-refuse, or continue.** Without the M164 certificate, margin inspection is forbidden; hard eligibility failures only. |
| **4b — `TC0-DOM-sw10-A/B` complete witness** | `54` | `614` | The same checks for the complete `27+27` sw10 witness; one required failed licensed cell is enough. | **Stop-and-refuse, or continue.** Same certificate restriction; no interim `PASS`. |
| **5 — exact candidate package and G0–G3 witnesses** | `224` | `838` | Missing/duplicate frames, interruption, failed reset/start/end stability, endpoint/node/profile/coverage failure, or any free M5 exit count below `133` for sw4, sw10, or their physical-coordinate intersection. | **Stop-and-refuse, or continue.** This stage may declare the future score not worth shooting; it cannot accept the family. |
| **6a — sharp physical control** | `96` | `934` | The complete frozen positive control has `Q05 <= 1.10`, wrong sign, or is ineligible; the instrument has not demonstrated response to genuine optical improvement. | **Stop-and-refuse, or continue.** No interim `PASS`. |
| **6b — blur physical control** | `96` | `1,030` | The complete frozen degradation control has `Q95 >= 0.90`, wrong sign, or is ineligible; the instrument has not demonstrated response to physical blur. | **Stop-and-refuse, or continue.** No interim `PASS`. |
| **6c — TC0 held-out V closure and final family** | `64` | `1,094` | TC0 map/common-mode/drift closure and the complete frozen eligibility, information, transfer, power, rank, conditioning, and control family. This is the first and only rehearsal acceptance look. | **May finally refuse or pass the rehearsal.** A pass licenses only a fresh score attempt. |
| **7 — fresh sealed combined M1/M5/M9 score** | `1,215` | **`2,309`** | The registered score and every frozen eligibility/dominance requirement on an independent holdout subject/session. A failed gate returns `UNMEASURED`; nothing may be patched after reading. | **One sealed final score only.** No staged acceptance and no post-result repair. |

**VERIFIED BY RUNNING.** The rehearsal increments in stages 1–6c sum to
`1,092`; adding Stage 0 gives cumulative `1,094`; adding the sealed score gives
`2,309`.

**INFERRED BY READING.** Early refusal does not add an acceptance event, so it
does not inflate the final false-admission probability. Early acceptance would
add an acceptance opportunity and is therefore prohibited. The only
rehearsal `PASS` is after all `1,092` registered rehearsal frames and the only
score is after all `1,215` fresh holdout frames.

## 5. Paste-ready replacement for the owner document

**INFERRED BY READING — PASTE-READY OWNER-FACING TEXT FOLLOWS.**

> **The capture budget is now reconciled.** Budget **1,092 registered frames
> for the development rehearsal** and **1,215 registered frames for the fresh
> sealed M1/M5/M9 scored sitting**: **2,307 registered frames across the two
> sittings**. Ask 2a's two-frame scale/field preflight is separate, so the
> complete owner program is **2,309 frames including that preflight**. These
> totals exclude one unregistered histogram/setup release per sitting and any
> refused or repeated preflight pair.
>
> M164's `896`-frame rehearsal and `704`-frame sealed score were an earlier
> M1-only design. They are not an alternative current total. The rehearsal
> grew by `196`: replace its three-strip `96`-frame reference with four
> `32`-frame strips (`+32` net), and add a separate candidate-excluded
> `TC0-DOM-sw4-A/B` plus `TC0-DOM-sw10-A/B` complete-input witness
> (`55+55+27+27 = 164`). The two `96`-frame physical controls were already in
> the `896`; they did not cause this increase.
>
> The old `704`-frame score is not literally contained unchanged in the new
> score because its `96`-frame reference was replaced. Its roles become a
> `736`-frame current M1 package; the candidate-excluded dominance witness adds
> `164`, making the current M1-only package `900`; and the combined M5/M9
> converter-on package adds `315`, making the current scored sitting
> **`1,215`**. Choosing `900` instead would mean deliberately deferring M5/M9,
> not correcting the arithmetic. The current request preserves the combined
> M1/M5/M9 holdout.
>
> ### One staircase, with the two-frame off-ramp preserved
>
> Nothing after a stage is released until its complete frozen check is on
> disk. Every interim look is **fail-only**: it may stop and refuse, but it may
> never produce an early `PASS`. The only rehearsal acceptance look is after
> all `1,092` rehearsal frames. This preserves the statistical gate while
> avoiding later frames after an irreversible failure.
>
> | stage | new frames | cumulative including Ask 2a | what it can conclude |
> |---|---:|---:|---|
> | **0M — frozen contract and checker** | `0` | `0` | Missing or mutable manifest, target, cell family, margins, reduction, settings, hashes, seed, block order, or reader is **STOP**. The rehearsal is currently blocked here. |
> | **0 — your two-frame kill test** | `2` | `2` | A valid empty feasible set or valid sampling/field/frequency failure cancels the whole design before either sitting. A refused pair is repeated; it is not an optical verdict. |
> | **1 — converter-on A/B calibration** | `128` | `130` | Wrong settings, provenance, flats, darks, temperature, or A/B maps is **STOP**. |
> | **2a–2d — four reference strips** | `32` each | `162`, `194`, `226`, `258` | After each complete strip, failed rows, focus return, guards, tone, geometry, or reference power is **STOP**. |
> | **2e — converter-on held-out V closure** | `64` | `322` | Failed held-out map transfer, focus/temperature portability, or common-mode is **STOP**. |
> | **3 — live TC0 placement and TC0 A/B calibration** | `128` | `450` | Failed scale/field placement or TC0 calibration is **STOP**. |
> | **4a — `TC0-DOM-sw4-A/B`** | `110` | `560` | Incomplete `55+55`, failed nodes, coverage, focus, geometry, exclusion, or lineage is **STOP**. |
> | **4b — `TC0-DOM-sw10-A/B`** | `54` | `614` | The same for complete `27+27` sw10 witness stacks. No informal interim margin may condemn or accept the rig. |
> | **5 — exact candidate package plus G0–G3 witnesses** | `224` | `838` | Missing/duplicate frames, interruption, failed focus-program gates, or fewer than `133` eligible sw4, sw10, or common tiles is **STOP**. |
> | **6a — sharp control** | `96` | `934` | `Q05 <= 1.10`, wrong sign, or invalid control is **STOP**. |
> | **6b — blur control** | `96` | `1,030` | `Q95 >= 0.90`, wrong sign, or invalid control is **STOP**. |
> | **6c — TC0 held-out V closure and final rehearsal family** | `64` | `1,094` | This is the first and only point that may say the complete rehearsal passed. A pass licenses a score attempt; it is not a score. |
> | **7 — fresh sealed M1/M5/M9 score** | `1,215` | **`2,309`** | One independent uninterrupted holdout sitting. A failed gate is `UNMEASURED`; do not patch it after reading. |
>
> At the two dominance-witness rows, an early optical futility stop is allowed
> only if M164 first publishes and commissions a hash-bound machine
> certificate proving a completed required cell cannot recover under any
> admissible remainder. Until then, those rows stop only on hard eligibility
> failures. They never permit early acceptance.
>
> **The two-frame off-ramp remains the most valuable one.** Shoot Ask 2a when
> instructed. If it validly kills the feasible optical design, stop there:
> neither the `1,092`-frame rehearsal nor the `1,215`-frame score is spent.
> Passing Ask 2a establishes scale and field only. Do not start the rehearsal
> until the zero-frame manifest gate is explicitly released.

## 6. Verification

**VERIFIED BY RUNNING.** The existing M166 source-accounting suites were rerun
before this reconciliation:

```text
M166 reference-dominance analysis: PASS
M166 reference-dominance verifier: PASS 11/11
M166 reference-dominance report verifier: PASS 27/27
M166 rehearsal-cost analysis: PASS
M166 rehearsal-cost verifier: PASS 20/20
M166 rehearsal-cost commissioning: 20/20 planted defects caught
```

**VERIFIED BY RUNNING.** The reconciliation verifier and its commissioned
negative controls are under
`experiments/M166-capture-reconciliation/`. Every check is planted with the
exact defect it targets using a string anchor required to occur exactly once;
a missing anchor hard-errors rather than silently producing a green run.

```text
reconciliation verifier: PASS 25/25
reconciliation commissioning: 25/25 planted defects caught
missing- and duplicate-anchor guards: fired
```

**INFERRED BY READING.** Sources: the controlling
`docs/proposals/2026-08-sota-path.md`; M164's staged M1 proposal and blocked
production manifest; M166's exact rehearsal and staged-cost reports; the
combined scored-session capture request; and the owner document whose
conflicting totals this report replaces.

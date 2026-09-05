CAPTURE PROGRAMME: at least 3,716 specified frames in at least 6 sittings; minimum viable nominally 2 frames; 686 frames sequenced out pending detail-candidate admission. **INFERRED BY READING.**

# M177 — one capture programme

## 0. Decision

**INFERRED BY READING.** Do **not** treat the headline as permission to shoot.
Ask 2a is the only released capture on a sound owner sheet.  M173 adjudicated
the earlier prose `NOT SOUND`, commit `3b00845d` folded its exact replacement
into OWNER-ACTIONS, and commit `4a5d5eef` lifted the temporary M171 hold.  A
numerical preflight PASS still does not release either long sitting.  The M166
rehearsal and score remain stopped at zero frames; M167, M2 and the
replacement-slide ask are sequenced later; and four further asks are not yet
countable.  This document arbitrates shutter priority; it does not remove any
source protocol's STOP.
Sources: `docs/OWNER-ACTIONS.md:8-11,907-1019`;
`docs/research/M173-ask2a-audit.md:7-15,293-324`;
`docs/research/M166-capture-reconciliation.md:1-39`;
`docs/research/M167-detail-battery.md:518-522`.

**VERIFIED BY RUNNING.** Commit `2a0a39b4` is an ancestor of the current
branch, and its committed reconciliation is the controlling M166 accounting
source.  M177 uses its `896-96+128+164` rehearsal bridge and `900+315`
combined-score bridge rather than reconstructing a competing campaign total.

**VERIFIED BY RUNNING.** `CHECK[core-three] 1,092 + 1,215 + 686 = 2,993`.
The three requests named in the brief do total 2,993 frames.

**VERIFIED BY RUNNING.** `CHECK[landed-campaigns] 2 + 1,092 + 1,215 + 686 = 2,995`.
This is the complete newly reconciled M166/M167 envelope including Ask 2a.

**VERIFIED BY RUNNING.** `CHECK[specified-floor] 2 + 1,092 + 1,215 + 686 + 64 + 657 = 3,716`.
The audit found three further sized obligations: Ask 2a, the M2 two-light
replacement, and the deferred replacement-slide sitting.  Four other current
asks omit a frame count, so 3,716 is a floor, not a finite grand total.

**VERIFIED BY RUNNING.** `CHECK[score-path] 2 + 1,092 + 1,215 = 2,309`.
This is the complete currently specified M1/M5/M9 path, including the
two-frame scale/field preflight but excluding setup histogram releases and
retries (`docs/research/M166-capture-reconciliation.md:30-39,163-167`).

**VERIFIED BY RUNNING.** `CHECK[after-m167-defer] 3,716 - 686 = 3,030`.
Sequencing M167 later leaves a 3,030-frame specified queue.  This is a
dependency decision, not a claim that calibration work has no eventual value,
and it does not make the remaining unsized obligations disappear.

## 1. Consolidated ledger

**INFERRED BY READING.** The ledger distinguishes a *sized obligation* from a
*released sitting*.  “Axes advanced” means that the photographs supply or
clear an input named by that axis; “newly scoreable now” is stricter and is
zero throughout.  M169 proves that removing the comparator overreach alone
makes zero axes newly scoreable, because other blockers remain conjunctive
(`docs/research/M169-ratification-stakes.md:228-242`).

| Rank | Request and state | Source | Re-derived frames | What the photographs license | Axes advanced / newly scoreable now | Evidence |
|---:|---|---|---:|---|---|---|
| 1 | **Ask 2a scale/field preflight — RELEASED** | `docs/OWNER-ACTIONS.md:8-11,907-1019`; `docs/research/M173-ask2a-audit.md:293-324` | nominal accepted attempt `1 + 1 = 2`; fresh pairs after refusal are outside the floor | A real converter-on/converter-off sampling-ratio and common-field kill gate; no score and no dominance result | M1/M5/M9 path: `3`; now: `0` | **INFERRED BY READING.** |
| 2 | **M166 development rehearsal — STOP** | `docs/research/M166-capture-reconciliation.md:125-155` | `896-96+128+164 = 1,092` | Exact-configuration physical commissioning, the candidate execution path, both physical directions, and permission to attempt the score | M1/M5/M9 path: `3`; now: `0` | **VERIFIED BY RUNNING.** |
| 3 | **M166 sealed combined score — STOP** | `docs/research/M166-capture-reconciliation.md:85-122,163-181` | current M1-only `900` + M5/M9 `315` = `1,215` | Fresh holdout inputs for the combined M1/M5/M9 adjudication; it cannot borrow a rehearsal RAW or result | M1/M5/M9: `3`; now: `0` | **VERIFIED BY RUNNING.** |
| 4 | **M2 replacement two-light unit — DEFER** | `docs/research/M146-unlock-audit.md:23,74-79,159-160` | `2 x 32 = 64` | Replaces the ineligible second-light unit for a future M2 instrument; the present M2 statistic is void | M2 input: `1`; now: `0` | **VERIFIED BY RUNNING.** |
| 5 | **Ask 5 fresh slide equivalent — DEFER** | `docs/OWNER-ACTIONS.md:1329-1368` | `182+92+186+197 = 657`; the `186` is `65+61+60` | A stated lower bound for a future scoring holdout; the same section says the four-stack design lacks independent repeat lineages, so it licenses no score as written | Detail-holdout path: M1/M5/M9; now: `0` | **VERIFIED BY RUNNING.** |
| 6 | **M167 physical false-rate battery — SEQUENCE OUT, CONTINGENT** | `docs/research/M167-detail-battery.md:518-620` | `96+110+54+60+110+128+128 = 686` | Panel- and intervention-conditioned flat, USM, blur, and—only with an admitted reference reader—physical-improvement rates for a frozen candidate | Scorecard axes: `0`; now: `0` | **VERIFIED BY RUNNING.** |

**VERIFIED BY RUNNING.** `CHECK[rehearsal] 896 - 96 + 128 + 164 = 1,092`.
This verifies the committed M166 bridge from the predecessor rehearsal: replace
the three-strip reference and add the source-disjoint dominance witness
(`docs/research/M166-capture-reconciliation.md:125-155`).

**VERIFIED BY RUNNING.** `CHECK[score] 900 + 315 = 1,215`.
The reconciled current M1-only score is 900; the registered converter-on
M5/M9 package adds 315
(`docs/research/M166-capture-reconciliation.md:163-181,251-254`).

**VERIFIED BY RUNNING.** `CHECK[m167] 96 + 110 + 54 + 60 + 110 + 128 + 128 = 686`.
This recomputes M167 from its seven acquisition rows
(`docs/research/M167-detail-battery.md:551-560`).

**VERIFIED BY RUNNING.** `CHECK[m2] 2 x 32 = 64`.
M146 requires two fixed-focus ISO-100 bee blocks, thirty-two frames under each
light (`docs/research/M146-unlock-audit.md:74-79`).

**VERIFIED BY RUNNING.** `CHECK[ask5] 182 + 92 + (65 + 61 + 60) + 197 = 657`.
Ask 5 prints the four semantic groups as `182+92+186+197`; the allowed-disk
survey resolves its flat group into three physical runs
(`docs/OWNER-ACTIONS.md:1329-1355`;
`docs/research/M167-detail-battery.md:460-471`).

**INFERRED BY READING.** The 657 is only a countable predecessor-shaped floor,
not a final scoring recipe.  Ask 5 requests the “same four stacks” at
`docs/OWNER-ACTIONS.md:1351-1354`, then states at `:1361-1368` that those four
stacks lack the independent repeat lineages needed to score.  Its promised
folded shot list must resolve that contradiction and may increase the total.

### 1.1 Current but unsized asks

**INFERRED BY READING.** These are genuine missing-photon statements, but none
is an executable capture sheet.  They are excluded from 3,716 rather than
assigned invented frame counts.

| Request | Source | What is specified | Missing before it can enter a sitting | Axis advanced / newly scoreable now | Evidence |
|---|---|---|---|---|---|
| M4 flat population | `docs/research/M152-site-census.md:269-289`; `docs/OWNER-ACTIONS.md:1147-1215` | Fresh medication and foam protected backgrounds plus a separate development flat; the alternative population version uses one protected flat plus development | Exact frames per capture, focus-bracket count, optical state, and frozen choice between the two population versions | M4: `1` / `0` | **INFERRED BY READING.** |
| M10 metrology ruler | `docs/research/M154-m10-angle.md:320-326`; `docs/OWNER-ACTIONS.md:1218-1287` | One fresh uninterrupted ruler stack with independently measured pose | Exact bracket width/count and a released M10 product/checker | M10: `1` / `0` | **INFERRED BY READING.** |
| M6 highlight/shadow population | `docs/research/M160-amendment6-reachability.md:101-104` | Controlled stacks for foam, salt, ISO-100 battery, highly angled ruler, and bright grid/fabric populations | Exact stack counts, bracket settings, exposure ladder, and one owner-facing order | M6: `1` / `0` | **INFERRED BY READING.** |
| M7 colour population | `docs/research/M144-reference-uncertainty.md:270-285`; `docs/research/M160-amendment6-reachability.md:96-100` | A tilted traceable patch target plus a textured colour-seam coupon | Target/certificate acceptance, exact frames, exposure, bracket settings, and released comparator path | M7: `1` / `0` | **INFERRED BY READING.** |

### 1.2 Requests found but not outstanding

**INFERRED BY READING.** The superseded node-coincidence request is historical,
not additive: its twenty-four fixed witnesses and 407-frame total belong to a
dead protocol (`docs/capture-requests/2026-09-node-coincidence-gate.md:1-20`;
`docs/capture-requests/2026-09-319-frame-session.md:198-208`).

**INFERRED BY READING.** `docs/research/OWNER-QUESTIONS.md:9-15` still calls
daylight flat fields outstanding, but `docs/captures-needed.md:1257-1279`
records them delivered.  The focus-rail request is explicitly deferred for
lack of hardware.  Neither enters this programme.

**INFERRED BY READING.** The plan's D10 tether exercise is explicitly deferred
and expressly does not move the resolution claim
(`docs/proposals/2026-08-sota-path.md:2591-2604`).  It is not an outstanding
capture sitting.

## 2. Existing imagery before new photons

**VERIFIED BY RUNNING.** The audit enumerated only
`D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl`
with `Get-ChildItem -LiteralPath ... -Recurse -Force -File`.  It did not
enumerate `D:\personal\macro`, its `requests` parent, or any sibling.  The
forbidden quality holdout was never listed, opened, decoded, or statted.

**VERIFIED BY RUNNING.** `CHECK[survey] 65 + 61 + 60 + 182 + 92 + 197 = 657`.
All 657 files are ARWs and there are no other files in that allowed subtree.

| Relative run | ARWs | Exposure | FocusPosition2 population | Evidence |
|---|---:|---:|---|---|
| `flat-sw4-cpl/flat-et6s-sw4-cpl` | `65` | `6 s` | `57 x 65` | **VERIFIED BY RUNNING.** |
| `flat-sw4-cpl/flat-et2.5s-sw4-cpl` | `61` | `2.5 s` | `57 x 61` | **VERIFIED BY RUNNING.** |
| `flat-sw4-cpl/flat-et1s-sw4-cpl` | `60` | `1 s` | `57 x 60` | **VERIFIED BY RUNNING.** |
| `tilted-sw4-cpl` | `182` | `1 s` | `57 x 76, 58 x 80, 59 x 26` | **VERIFIED BY RUNNING.** |
| `tilted-sw10-cpl` | `92` | `1 s` | `57 x 38, 58 x 40, 59 x 14` | **VERIFIED BY RUNNING.** |
| `very-tilted-all-axis-sw10-cpl` | `197` | `1 s` | `56 x 10, 57 x 40, 58 x 40, 59 x 41, 60 x 40, 61 x 26` | **VERIFIED BY RUNNING.** |

**VERIFIED BY RUNNING.** ExifTool read all 657 headers from that exact allowed
subtree.  Every header reports Sony A7C II, the Sony 100 mm macro plus 2x
teleconverter, 200 mm, ISO 100, marked f/5.6, 7168 by 5120 pixels, and
stabilisation on.  Each of the six condition directories is one contiguous
camera-filename sequence and contains no A/B lineage in its filenames.
`CHECK[survey-groups] 6 runs; 657 headers; stabilisation-on = 657`.

**VERIFIED BY RUNNING.** ExifTool extracted one embedded preview from the
fronto-parallel “flat” run directly into memory; a local-luminance census found
strong high-frequency structure rather than a featureless field.  No preview
or other file was written to `D:\`.

**INFERRED BY READING.** The name “flat” means fronto-parallel here, not
featureless: the subject is a patterned slide.  The whole session is burned
development, has no corresponding-node A/B repeat passes, and cannot become a
physical false-rate sample or scoring holdout
(`docs/research/M167-detail-battery.md:473-493`;
`docs/research/M164-m1-staged-capture.md:137-155`).

**INFERRED BY READING.** Existing-corpus disposition by request:

| Request | Existing substitute? | Why | Evidence |
|---|---|---|---|
| Ask 2a | **No** | The archive has no real converter-off pair or accepted physical `M_work` | `docs/research/M173-ask2a-audit.md:14-16,242-246` — **INFERRED BY READING.** |
| M166 rehearsal and score | **No** | Existing eligible credit is zero: converter-on, stabilisation-on, wrong session/lineage, no bare-lens pair, and no matched fresh calibration | `docs/research/M164-m1-staged-capture.md:119-191` — **INFERRED BY READING.** |
| M167 | **No for rates; yes for pruning only** | The 657 frames are burned, stabilised, single-pass, patterned, and lack A/B lineages and a uniform null | `docs/research/M167-detail-battery.md:455-493` — **INFERRED BY READING.** |
| M2 | **No** | The required second-light block already fails the frozen non-translation gate; the slide's exposure ladder is bracketed development, not two fixed-focus light blocks | `docs/research/M146-unlock-audit.md:23,98-108,150-160` — **INFERRED BY READING.** |
| M4 | **No** | Existing scored flats supply only 138 of the required 250 selected sites, and every development flat tested supplies zero eligible sites | `docs/research/M152-site-census.md:15-27,238-289` — **INFERRED BY READING.** |
| M10 | **No** | The old ruler unit is burned and its angle has no qualifying uncertainty | `docs/research/M154-m10-angle.md:38-70,320-326` — **INFERRED BY READING.** |
| Ask 5 | **No** | Its 657-frame predecessor was deliberately spent on development; moreover, the stated four-stack replacement still lacks the repeat lineages that its own scoring paragraph requires | `docs/OWNER-ACTIONS.md:1329-1368` — **INFERRED BY READING.** |
| M6/M7 | **No** | Their current registered populations or traceable target are absent | `docs/research/M160-amendment6-reachability.md:96-104` — **INFERRED BY READING.** |

## 3. Deduplication ruling

**INFERRED BY READING.** A RAW is reusable only when both consumers require
the same subject/session class, optical state, exposure and stabilisation
state, focus programme and order, calibration lineage, manifest admissibility,
and holdout/development role.  Equal frame budgets are not evidence of any of
those properties.

### 3.1 Legitimate reuse

| Frames | Consumers | Property that makes reuse valid | Evidence |
|---:|---|---|---|
| M166 candidate `164` | M1 candidate execution and the rehearsal's input-only M5 exit gate | Both consumers explicitly read the same converter-off candidate `TC0-sw4/sw10-A/B` inputs; the M5 gate is input-only and adds no score or manifest role | `docs/research/M166-rehearsal-cost.md:130-151` — **INFERRED BY READING.** |
| M166 scored converter-on `315` | M5 and M9 | The combined request registers one same-session converter-on focus/witness package for both axes | `docs/research/M166-capture-reconciliation.md:88-100,168-181` — **INFERRED BY READING.** |
| M167 detailed renders | M167 USM and blur arms | Those interventions are post-render transforms of already frozen A/B renders and require no extra exposure | `docs/research/M167-detail-battery.md:583-601` — **INFERRED BY READING.** |

**INFERRED BY READING.** There is **no legitimate cross-request RAW merge** in
the current frozen texts.  The reuse above is internal to a request.

### 3.2 Rejected merges

| Tempting merge | Why it only looks shared | Property that forbids it | Evidence |
|---|---|---|---|
| M166 dominance `164` with M166 candidate `164` | Both are `55+55+27+27` | DOM RAWs are candidate-excluded witnesses; candidate RAWs are renderer inputs. One set in both roles makes the witness identical to what it is meant to test | `docs/research/M166-rehearsal-cost.md:102-127` — **INFERRED BY READING.** |
| M166 rehearsal with M166 score | Roles and budgets are analogous | Development and sealed holdout must use independent subject/session, RAW, calibration, site, render, and fitted-value lineages | `docs/research/M166-capture-reconciliation.md:163-167`; `docs/research/M166-rehearsal-cost.md:126-129` — **INFERRED BY READING.** |
| M167 `TEST-*` with either M166 candidate or M166 DOM stacks | Every package totals `164 = 55+55+27+27`, uses widths 4/10, and is converter-off | M167 fixes `M_test <= 1.30x`, ABBA order, and intervention-rate candidate inputs; M166 fixes the accepted `1.32x` placement and literal order, while its DOM copy is candidate-excluded. Magnification, order, role, session, target, manifest, and calibration lineage all differ | `docs/research/M167-detail-battery.md:529-566`; `docs/research/M166-reference-dominance-rehearsal.md:242-296` — **INFERRED BY READING.** |
| M167 reference bursts with M166 reference strips | Both are converter-on fixed-focus groups | M167 requires three near/middle/far zones with a `21/21/22` site allocation; M166 requires four row-pair strips, disjoint A/B halves, and a different target contract | `docs/research/M167-detail-battery.md:527-557`; `docs/research/M166-reference-dominance-rehearsal.md:130-141,272-289` — **INFERRED BY READING.** |
| M167 calibration with M166 calibration | Names and `128`-frame budgets recur | Calibration is session-, optical-state-, focus-, temperature-, and lineage-local. The two protocols cannot currently be one literal uninterrupted order | `docs/research/M166-reference-dominance-rehearsal.md:117-166,290-303`; `docs/research/M167-detail-battery.md:544-577` — **INFERRED BY READING.** |
| M167 `NULL-sw4-A/B` with any flat masters | Both use a diffuser-like field | Null stacks are focus-bracket evidence for a no-scene rate; flats are fixed-focus calibration maps and must not become scored null observations | `docs/research/M167-detail-battery.md:555-557` — **INFERRED BY READING.** |
| M2 light blocks with any `32`-frame burst | The group size recurs | M2 requires one bee subject under two registered lights and fixed focus; reference, calibration, and control bursts have different subjects and estimands | `docs/research/M146-unlock-audit.md:74-90` — **INFERRED BY READING.** |
| M4 protected flat with M4 development flat | Both need featureless background | Reading the development arm commissions the checker and burns that session; the protected arm must remain unread until score | `docs/research/M152-site-census.md:269-289` — **INFERRED BY READING.** |
| Burned 657-frame slide with Ask 5 | The requested replacement intentionally mirrors it | The original is development-burned; scoring requires a fresh untouched session | `docs/OWNER-ACTIONS.md:1329-1359` — **INFERRED BY READING.** |

**INFERRED BY READING.** M167's “do not duplicate if the rehearsal will supply
the same blocks” sentence is conditional, not a finding of identity
(`docs/research/M167-detail-battery.md:518-522`).  The current M166 and M167
specifications fail that condition on magnification, target partition, order,
and session-local calibration.  A future registrar may harmonise them before
either is shot; M177 may not silently do so after the fact.

**VERIFIED BY RUNNING.** The committed source does **not** support the shorthand
that M166 DOM is converter-on.  M166 registers both `TC0-DOM` blocks as
**converter off** (`docs/research/M166-reference-dominance-rehearsal.md:242-243`),
just as M167 removes the converter for `TEST-*`
(`docs/research/M167-detail-battery.md:552-553`).  They still cannot be shared:
M166's accepted `1.32x` state conflicts with M167's `M_test <= 1.30x`, and the
candidate-excluded dominance role conflicts with M167's candidate test role.
No 164-frame merge is credited.

## 4. Ranking by shutter value

**INFERRED BY READING.** `CHECK[axes-zero] comparator relaxation -> 0 of 12 newly scoreable`.
M169's exact result is zero, not “a blocker disappeared, therefore an axis can
run” (`docs/research/M169-ratification-stakes.md:228-242`).  The same
discipline applies below: every row advances zero axis verdicts *now*, even
when it clears a useful capture input.  That zero is not the ranking rule:
dependency order is.  A long-pole instrument step is deferred only while its
inputs or candidate do not yet exist, never because its eventual reach is
large.

| Order | Block | Value per frame | What it unblocks | Axis verdicts that move on capture alone | Decision | Evidence |
|---:|---|---|---|---:|---|---|
| 1 | Ask 2a, nominally `2` | Three capture paths tested by one accepted pair | It can kill or preserve the entire M1/M5/M9 optical design before a long sitting | `0` | **Shoot first; wait for explicit release after any numerical PASS** | `docs/OWNER-ACTIONS.md:907-1019`; `docs/research/M173-ask2a-audit.md:284-324` — **INFERRED BY READING.** |
| 2 | M166 rehearsal, `1,092` | Three-axis score attempt gated by one development sitting | Real reference/witness/calibration inputs for production G1–G8, physical controls, candidate execution, and eventual score permission | `0` | **Next only after every zero-frame release gate** | `docs/research/M166-rehearsal-cost.md:1-40,412-477`; `experiments/M171-reference-admission/PREREGISTRATION.md:14-21` — **INFERRED BY READING.** |
| 3 | M166 score, `1,215` | Three registered axes receive one sealed input unit | M1/M5/M9 score inputs, conditional on rehearsal, real-reference admission, detail-instrument admission, and all other prerequisites | `0` | **Only after those admissions PASS** | `docs/research/M166-capture-reconciliation.md:203-228`; `docs/research/M171-reference-admission.md:3-9` — **INFERRED BY READING.** |
| 4 | M2 replacement, `64` | One future-axis capture limb at low frame cost | The failed two-light geometry/input limb, but not the missing instrument | `0` | **Defer until an M2 instrument exists** | `docs/research/M146-unlock-audit.md:150-160`; `docs/research/M167-detail-battery.md:118-186` — **INFERRED BY READING.** |
| 5 | M4/M10/M6/M7 unsized asks | Value per frame cannot be calculated | Each clears one named capture or truth limb | `0` | **Return for exact sheets; do not improvise** | Sources in §1.1 — **INFERRED BY READING.** |
| 6 | Ask 5, at least `657` | Future detail holdout, but only after commissioning | A replacement for a deliberately spent development unit; the registered exact list is still missing | `0` | **Defer** | `docs/OWNER-ACTIONS.md:1329-1368` — **INFERRED BY READING.** |
| 7 | M167, `686` | Value becomes decision-relevant only after a candidate exists | Conditional error-rate calibration for a frozen candidate; it is not a prerequisite of M171 reference admission | `0` | **Sequence out now; restore immediately after candidate admission or contrary dependency proof** | `docs/research/M167-detail-battery.md:497-525`; `experiments/M171-reference-admission/PREREGISTRATION.md:14-21` — **INFERRED BY READING.** |

### 4.1 Verified critical path to blocker `(a)`

**INFERRED BY READING.** The proposed order “score, then G1–G8, then admit an
instrument” is reversed.  The 1,215-frame sitting is a sealed score, not
commissioning material.  Real reference and instrument admission must succeed
on non-holdout evidence before the score is exposed
(`docs/research/M166-capture-reconciliation.md:200-228`;
`docs/research/M171-reference-admission.md:3-9`).

| Order | Required event | Registered frame cost | What must be true before the next event | Evidence |
|---:|---|---:|---|---|
| 0 | Execute the repaired, released Ask 2a and obtain one accepted pair | nominally `2`; every refused/repositioned attempt is another complete pair outside the floor | Numerical scale/field/frequency feasibility is accepted; a console result alone is not a session release | `docs/OWNER-ACTIONS.md:907-1019`; `docs/research/M173-ask2a-audit.md:284-324` — **INFERRED BY READING.** |
| 1 | Freeze the production route | `0` registered frames; engineering, procurement and fabrication are unsized | Complete production manifest/cells/margins; target and support; admitted comparator licence and pinned binaries; geometry, calibration, resampler, seed, checker and candidate/detail contract are frozen | `docs/research/M164-dominance-manifest.md:64-110,162-175,302-326` — **INFERRED BY READING.** |
| 2 | Capture the M166 exact-configuration rehearsal | `1,092` | The non-holdout reference, complete scored-path witnesses, disjoint calibration, candidate inputs and physical controls arrive intact | `docs/research/M166-capture-reconciliation.md:125-167`; `docs/research/M166-reference-dominance-rehearsal.md:230-302` — **INFERRED BY READING.** |
| 3 | Instantiate and run production M171 G1–G8 on the real rehearsal | `0` new registered frames if the planned M166 evidence and external calibration provenance suffice | All eight gates pass; the reference is admitted only in its supported reduction subspace | `docs/research/M171-reference-admission.md:3-32,72-85`; `experiments/M171-reference-admission/PREREGISTRATION.md:14-21,107-220` — **INFERRED BY READING.** |
| 4 | Build, freeze, commission and independently admit the detail instrument | `0` currently registered owner frames; engineering is unsized | The candidate passes P1–P7 and A1–A6, including an evaluator-controlled OS-strength A6 sandbox; the current harness cannot emit real-candidate admission without it | `docs/research/M167-detail-battery.md:274-307,414-435`; `docs/proposals/2026-09-truth-referenced-detail.md:1210-1242,1291-1308,1377-1417` — **INFERRED BY READING.** |
| 5 | Clear blocker `(a)` for the admitted instrument, then capture the sealed M166 score | `1,215` | The rehearsal and admissions passed; the independent holdout remains sealed and unpatched | `docs/research/M166-capture-reconciliation.md:200-228` — **INFERRED BY READING.** |
| 6 | Run admitted instruments and axis-specific checkers | `0` additional frames in this M166 path; other axes retain their own sized or unsized asks | M1/M5/M9 can receive reads; reaching up to `12 of 12` measurable still requires every other blocker and axis-specific prerequisite, and is not twelve PASSes | `docs/proposals/2026-08-sota-path.md:164-170,2254-2292`; `docs/STATUS.md:3668-3690` — **INFERRED BY READING.** |

**INFERRED BY READING.** The route table's leverage claim is preserved, not
dismissed: if blockers `(b)`, `(c)`, `(d)` and the axis-specific prerequisites
are already clear, adding a working admitted detail instrument can raise the
measurement ceiling from `4 of 12` to `12 of 12`.  That is reachability, not a
claim of twelve passing results (`docs/STATUS.md:3668-3690`).

**VERIFIED BY RUNNING.** `CHECK[critical-path] 2 + 1,092 + 1,215 = 2,309 registered frames`.
The arithmetic is complete; the path is not.  Ask 2a retries, failed-rehearsal
replacement sittings, and any production calibration that cannot be supplied
by already frozen provenance remain outside or unsized.

**INFERRED BY READING.** Owner frames alone cannot clear blocker `(a)`.
M171 commissioned synthetic logic only; production still needs a sealed
calibration manifest, a versioned ruling on the `0.5` versus `0.25`
noise estimands, and independent known-input provenance.  `DIGITAL_K` remains
uncommissioned.  The candidate also needs implementation, preregistration,
independent audit/admission and the absent A6 sandbox
(`docs/research/M171-reference-admission.md:7-16,62-85`;
`experiments/M171-reference-admission/PREREGISTRATION.md:29-52`;
`docs/research/M167-detail-battery.md:302-307,414-435`).

**INFERRED BY READING.** M171 expressly requests no new magnification,
optical-state or calibration exposure for its present gate
(`experiments/M171-reference-admission/PREREGISTRATION.md:14-21`).  Therefore
M167's 686-frame battery is **not** an admission prerequisite.  If production
G4 or another gate later proves that existing known-input provenance is
insufficient, the additional physical calibration is an unsized new request;
it must not be silently equated with M167.

## 5. Executable sitting envelopes

**INFERRED BY READING.** “Setup changes” below counts deliberate optical,
subject, lighting, or calibration-state transitions, not elapsed time.  Every
converter-on block is batched before one removal; none reinstalls the converter
inside a sitting.

### Sitting 0 — repaired and released Ask 2a preflight

**VERIFIED BY RUNNING.** Current OWNER-ACTIONS contains M173's exact target,
RAW mode, exposure, manual-focus/axial-motion, two-frame retake, three-outcome
adjudication and corrected-denominator requirements
(`docs/OWNER-ACTIONS.md:907-1019`;
`docs/research/M173-ask2a-audit.md:293-324`).

| Field | Programme | Evidence |
|---|---|---|
| Subject | Flat, square high-resolution slide; same central grid intersection in both frames | `docs/OWNER-ACTIONS.md:919-927` — **INFERRED BY READING.** |
| Optical configuration | Frame A: Sony A7C II + Sony 100 mm GM + fully seated 2x Viltrox at maximum reproduction. Frame B: converter removed, bare lens aimed near `1.32x` and never above `1.33x`; axial camera motion only | `docs/OWNER-ACTIONS.md:928-952` — **INFERRED BY READING.** |
| Focus programme | Focus Bracket off; one critically focused ARW in each optical state | `docs/OWNER-ACTIONS.md:928-953` — **INFERRED BY READING.** |
| Frames / stacks | `2` fixed frames; `0` bracket stacks | `docs/OWNER-ACTIONS.md:914-959` — **INFERRED BY READING.** |
| Setup changes | `1` converter removal and `1` axial reframe; target, roll, yaw, light, polariser, and centre remain fixed | `docs/OWNER-ACTIONS.md:939-953` — **INFERRED BY READING.** |

### Sitting 1 — M166 exact development rehearsal

| Field | Programme | Evidence |
|---|---|---|
| Subject | `D-REHEARSAL-01 — DEVELOPMENT; NEVER SCORE`, an independently seeded rigid panel from the frozen holdout construction class | `docs/research/M166-reference-dominance-rehearsal.md:176-205` — **INFERRED BY READING.** |
| Common camera state | Sony A7C II + Sony 100 mm GM; RAW, ISO 100, marked f/5.6, `1 s`, fixed WB, EFCS; IBIS and OSS off | `docs/research/M166-reference-dominance-rehearsal.md:117-145` — **INFERRED BY READING.** |
| Converter-on batch | `128` A/B calibration + four fixed `32`-frame row-pair strips + `64` held-out V calibration = `320` | `docs/research/M166-reference-dominance-rehearsal.md:242-260` — **INFERRED BY READING.** |
| Converter-off bracket batch | DOM: two width-4 x `55` plus two width-10 x `27`; candidate: a second two width-4 x `55` plus two width-10 x `27` | `docs/research/M166-reference-dominance-rehearsal.md:261-270,279-289` — **INFERRED BY READING.** |
| Converter-off fixed batch | `128` A/B calibration + `60` witnesses + three `32`-frame sharp groups + three `32`-frame blur groups + `64` V closure = `444` | `docs/research/M166-reference-dominance-rehearsal.md:261-276` — **INFERRED BY READING.** |
| Frames / stacks | `1,092` registered = `328` bracket + `764` fixed; `8` complete bracket stacks | `docs/research/M166-reference-dominance-rehearsal.md:242-278` — **VERIFIED BY RUNNING.** |
| Setup changes | `1` converter removal; calibration target/dark/diffuser changes stay inside each optical-state batch; four strip focuses, ten witness bursts, and six control focuses are registered changes | `docs/research/M166-reference-dominance-rehearsal.md:280-303` — **INFERRED BY READING.** |

**VERIFIED BY RUNNING.** `CHECK[rehearsal-structure] bracket 164 + 164 = 328; fixed 1,092 - 328 = 764; stacks 4 + 4 = 8`.

### Sitting 2 — M166 sealed combined score

| Field | Programme | Evidence |
|---|---|---|
| Subject | Fresh sealed holdout panel from the same frozen construction class; no rehearsal lineage | `docs/research/M166-reference-dominance-rehearsal.md:149-166,176-205` — **INFERRED BY READING.** |
| Common camera state | Same body/lens/settings as Sitting 1; uninterrupted, stabilisation off | `docs/research/M166-reference-dominance-rehearsal.md:117-166` — **INFERRED BY READING.** |
| Converter-on bracket batch | Two width-4 x `55`, two width-10 x `27`, and one width-1 x `91` = `255` in `5` stacks | `docs/capture-requests/2026-09-319-frame-session.md:352-392,468-516` — **INFERRED BY READING.** |
| Converter-on fixed batch | `60` witnesses + `128` A/B calibration + four reference strips x `32` + `64` V calibration = `380` | `docs/capture-requests/2026-09-319-frame-session.md:352-392`; `docs/research/M166-rehearsal-cost.md:87-127` — **INFERRED BY READING.** |
| Converter-off bracket batch | Candidate and candidate-excluded DOM each contain two width-4 x `55` and two width-10 x `27` = `328` in `8` stacks | `docs/research/M166-rehearsal-cost.md:102-124` — **INFERRED BY READING.** |
| Converter-off fixed batch | `60` witnesses + `128` A/B calibration + `64` V closure = `252` | `docs/capture-requests/2026-09-319-frame-session.md:376-392`; `docs/research/M166-rehearsal-cost.md:114-124` — **INFERRED BY READING.** |
| Frames / stacks | `1,215` registered = `583` bracket + `632` fixed; `13` complete bracket stacks | Sources above — **VERIFIED BY RUNNING.** |
| Setup changes | `1` converter removal and axial reframe; no converter reinstall; calibration-state changes remain within their optical batch | `docs/capture-requests/2026-09-319-frame-session.md:550-586,766-785` — **INFERRED BY READING.** |

**VERIFIED BY RUNNING.** `CHECK[score-structure] bracket 255 + 164 + 164 = 583; fixed 1,215 - 583 = 632; stacks 5 + 4 + 4 = 13`.

### Sitting 3 — M167 physical false-rate battery, contingently deferred

| Field | Programme | Evidence |
|---|---|---|
| Subjects | Tilted grid plus coplanar matte nonperiodic patch; separate texture-free opal/integrating null covering the same site footprint | `docs/research/M167-detail-battery.md:527-542` — **INFERRED BY READING.** |
| Common camera state | Sony A7C II + Sony 100 mm GM; RAW, ISO 100, marked f/5.6, `1 s`, fixed WB, EFCS; IBIS/OSS off | `docs/research/M167-detail-battery.md:544-549` — **INFERRED BY READING.** |
| Converter-on batch | At `M_ref >= 2.70x`: three fixed-focus groups x `32` plus four calibration groups x `32` = `224` | `docs/research/M167-detail-battery.md:551,556` — **INFERRED BY READING.** |
| Converter-off detailed batch | At `M_test <= 1.30x`: ABBA order, two width-4 x `55`, two width-10 x `27`, plus ten witness bursts x `6` = `224` | `docs/research/M167-detail-battery.md:552-554,564-566` — **INFERRED BY READING.** |
| Converter-off null/calibration batch | Two null width-4 x `55` plus four fixed calibration groups x `32` = `238` | `docs/research/M167-detail-battery.md:555-557` — **INFERRED BY READING.** |
| Frames / stacks | `686` registered = `274` bracket + `412` fixed; `6` complete bracket stacks | `docs/research/M167-detail-battery.md:551-560` — **VERIFIED BY RUNNING.** |
| Setup changes | `1` converter removal, `1` detailed-to-null subject substitution, and no converter reinstall | `docs/research/M167-detail-battery.md:551-577` — **INFERRED BY READING.** |

**VERIFIED BY RUNNING.** `CHECK[m167-structure] bracket 110 + 54 + 110 = 274`.

**VERIFIED BY RUNNING.** The preceding source arithmetic confirms that M167's
three bracket rows total `274`, not `328`.  They comprise `2+2+2 = 6` stacks,
while the remaining `412` frames are fixed bursts and calibration.  This is
not a source defect: M167 gives the correct 686 total and six-stack count but
does not print a bracket-frame subtotal.  This report uses `274` bracket and
`412` fixed for all decisions.

### Sitting 4 — M2 replacement two-light unit, deferred

| Field | Programme | Evidence |
|---|---|---|
| Subject | Same fixed-focus bee scene under two registered illuminations | `docs/research/M146-unlock-audit.md:74-79` — **INFERRED BY READING.** |
| Optical/focus configuration | Exact registered M2 state must be reissued; source fixes ISO 100 and fixed focus but does not publish a complete owner sheet | `docs/research/M146-unlock-audit.md:69-97` — **INFERRED BY READING.** |
| Frames / stacks | Two fixed bursts x `32` = `64`; `0` focus-bracket stacks | `docs/research/M146-unlock-audit.md:74-79` — **VERIFIED BY RUNNING.** |
| Setup changes | `1` illumination change; no focus-node or exposure interleave | `docs/research/M146-unlock-audit.md:74-90` — **INFERRED BY READING.** |

### Sitting 5 — Ask 5 replacement slide, deferred envelope only

| Field | Programme | Evidence |
|---|---|---|
| Subject | Fresh equivalent of the allowed high-resolution calibration-slide session | `docs/OWNER-ACTIONS.md:1329-1355` — **INFERRED BY READING.** |
| Optical configuration | Same Sony rig and converter-on slide geometry as the predecessor; a new exact sheet must explicitly turn IBIS/OSS off before release | `docs/OWNER-ACTIONS.md:1351-1359`; `docs/research/M167-detail-battery.md:473-493` — **INFERRED BY READING.** |
| Focus programme | Width-4 tilted `182`; width-10 tilted `92`; three flat width-4 passes `65/61/60`; very-tilted width-10 `197` | `docs/OWNER-ACTIONS.md:1331-1333`; `docs/research/M167-detail-battery.md:460-471` — **INFERRED BY READING.** |
| Frames / stacks | `657` frames in `6` physical bracket runs | Sources above — **VERIFIED BY RUNNING.** |
| Setup changes | Converter remains installed; at least `3` pose/exposure-family transitions separate the four semantic groups | Sources above — **INFERRED BY READING.** |

**INFERRED BY READING.** Sitting 5 is not executable from this envelope.
Ask 5 explicitly says to wait for the commissioned instrument and a folded
exact shot list, and its four-stack description lacks the independent repeat
lineages its closing paragraph requires
(`docs/OWNER-ACTIONS.md:1351-1368`).

## 6. Minimum and sequencing

**INFERRED BY READING.** If the owner can perform only **one capture action**,
shoot Sitting 0, the repaired and released nominal two-frame Ask 2a pair.  It
tests the three-axis optical route before either long sitting, and no archive
frame can substitute.

**INFERRED BY READING.** If “one sitting” means one *major sitting after a
passed preflight and explicit release*, choose the 1,092-frame rehearsal, never
the score.  A score without its accepted rehearsal is ineligible, while the
rehearsal can stop the score from consuming a holdout.

**VERIFIED BY RUNNING.** `CHECK[budget-300] 300 - 2 = 298`.
With a 300-frame ceiling, take one accepted two-frame preflight and leave 298
shutter releases unused.  No M166 stage may be banked across sittings, M167
needs its whole calibrated session for the stated rates, and the other
requests are deferred or unsized.  A refused preflight consumes a fresh pair
outside the nominal floor.

**INFERRED BY READING.** Sequence all 686 M167 frames out of the owner queue
**for now**.  The reason is contingent sequencing: M167 calibrates conditional
rates for a frozen candidate and reader, while no real detail candidate is
currently admitted and M171 does not require this battery to admit the
reference.  Restore the battery to the queue immediately when a detail
candidate is admitted, or immediately if M167 demonstrates that these frames
are a prerequisite of admission rather than post-admission calibration
(`docs/research/M167-detail-battery.md:497-525`;
`experiments/M171-reference-admission/PREREGISTRATION.md:14-21`).

**INFERRED BY READING.** Do not cut inside a released M166 sitting.  In
particular, the rejected `676`, `868`, `900`, and `928` rehearsal variants
delete estimator, candidate-execution, or physical-direction evidence
(`docs/research/M166-rehearsal-cost.md:156-174,362-385`).

## 7. Physical impossibilities

**INFERRED BY READING.** The active M166 and M167 protocols are physically
shootable on the registered rig because both use complete sequential A and B
passes.  Fixed-focus bursts repeat at one focus with Focus Bracket off; they
are not interleaved bracket exposures.

**INFERRED BY READING.** The superseded 383-frame paired-node proposal is
impossible on the Sony A7C II.  In-camera Focus Bracket fires once and advances;
it cannot take A and B—or two exposure settings—at one node before moving
(`docs/capture-requests/2026-09-319-frame-session.md:185-220`).

**INFERRED BY READING.** The achievable substitute is one complete automated
pass for A followed by a separately reset complete pass for B, with
corresponding nodes compared only after both passes finish.  If two exposure
settings are required, shoot one complete ladder per exposure setting.  Never
split odd/even files from one finer bracket; that produces different focus
nodes, not repeated observations
(`docs/capture-requests/2026-09-319-frame-session.md:682-704`;
`docs/research/M167-detail-battery.md:564-570`).

**INFERRED BY READING.** A teleconverter change is likewise a block boundary,
not a node operation.  Finish every converter-on block, remove it once, move
axially to the registered bare-lens state, then finish every converter-off
block.  M166 and M167 are grouped that way.

**INFERRED BY READING.** The M4, M6, M7, M10, M2, and Ask 5 descriptions are
not physically impossible; they are *specification-incomplete*.  They need an
exact released sheet before the owner can execute them without inventing
counts or settings.

## 8. Route-only source repairs

**INFERRED BY READING.** M177 owns none of the following files and did not edit
them.  The orchestrator should apply or reject these exact replacements.

**INFERRED BY READING.** In
`docs/proposals/2026-08-sota-path.md:2310-2312`, replace the stale 603-frame
critical-path item with:

```text
3. **`(a)`+`(c)` -- the current capture and admission programme.** After
   M173's corrected Ask 2a yields an accepted two-frame scale/field preflight,
   freeze the production manifest, target, licence, binaries, calibration,
   resampler, seed, checker and detail-candidate contract. Then acquire the
   1,092-frame exact-configuration development rehearsal. Before exposing a
   holdout, run production M171 G1-G8 on its real reference and independently
   commission/admit the detail instrument, including the A6 capability
   sandbox. Only a clean rehearsal and admitted instrument license the fresh
   1,215-frame combined M1/M5/M9 score. The registered capture floor is 2,309
   frames including one accepted preflight pair; retries, engineering,
   procurement and any newly required calibration remain outside or unsized.
```

**INFERRED BY READING.** In
`docs/research/OWNER-QUESTIONS.md:11-14`, replace stale C1 with:

```text
| C1 | **Flat fields.** The daylight PRNU/PTC set was delivered on
2026-08-23; this historical request is closed. M4's newer protected and
development flat-population asks are separate and live in OWNER-ACTIONS Ask
2c. | **Delivered; do not reshoot under this old recipe.** |
```

**INFERRED BY READING.** Immediately below the headings for Ask 2c and Ask 2d
in `docs/OWNER-ACTIONS.md:1147,1218`, insert:

```text
> **PLANNING NEED, NOT A CAPTURE SHEET.** Do not shoot from this section until
> the exact frame count, focus-bracket programme, optical state, exposure,
> file manifest, and input-only arrival check are frozen in one released
> request.
```

**INFERRED BY READING.** In `docs/OWNER-ACTIONS.md:1351-1354`, replace the
internally insufficient “same four stacks” prescription with:

```text
**What I need back, and when.** A fresh scoring sitting on the same slide and
rig, but not merely a repetition of the four development stacks. The exact
released list must add the independent sw4/sw10 A/B repeat lineages,
start/end/reset witnesses, and matching calibration required by the admitted
instrument. The predecessor's 657 frames are therefore a lower bound, not the
final scoring-session total.
```

## 9. Verification

**VERIFIED BY RUNNING.** `experiments/M177-capture-programme/verify.py`
re-derives the M166, M167, M2, Ask 5, grand-total, stack-structure, and
sequencing arithmetic from the cited source text; repeats the exact-subtree 657-file
inventory and ExifTool header census; checks the no-merge and physical-rig
clauses; verifies the contingent M167 sequencing and blocker-`(a)` ordering;
and never enumerates the forbidden sibling.

**VERIFIED BY RUNNING.** `CHECK[commission] planted defects caught = 20; missed = 0; inert edits passed = 1 of 1`.
The commissioned mutations cover report arithmetic, source arithmetic,
cross-role deduplication, the M166/M167 optical-state distinction, M167
configuration, Ask 2a's complete repair and non-release outcome, permanent-
versus-contingent refusal, critical-path ordering and reachability
prerequisites, the zero-axis statement, and the whole-pass substitute.  An
appended non-semantic comment is the inert edit.

**VERIFIED BY RUNNING.** An independent read-only verifier reran both modes,
recomputed every core sum separately, repeated the exact-subtree file and
header census, and audited the source claims.  Its verdict was `VERIFIED`, with
no defects or gaps.

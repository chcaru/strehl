STAGED RELEASE: 128 frames

# M166 — rehearsal cost and staged release

Status: **NO SUCCESSFUL-PATH REDUCTION; FAIL-ONLY STAGING ADMISSIBLE**

## 0. Ruling

**INFERRED BY READING — CURRENT-CONTRACT RULING.** No registered frame may be
deleted from the current rehearsal while preserving both its complete release
gate and the requirement that an omitted role must not create a new way for
the rehearsal to pass while the scored sitting fails.
The successful path remains exactly `1,092` registered frames.

**VERIFIED BY RUNNING.** The useful decomposition is:

```text
M164 dominance kernel                                  676
exact scored-input execution and focus witnesses     +224
physical sharp and blur controls                     +192
                                                      ----
successful rehearsal                                1,092
```

**INFERRED BY READING.** Only the first `676` frames enter or validate the
M164 information/transfer calculation itself. The other `416` frames are not
arithmetic padding: `224` supply and exercise the actual M1 candidate input
package plus its focus-return gates, and `192` are the two physical direction
controls required to commission the detail instrument before a holdout is
spent.

**INFERRED BY READING.** An estimator-only `676`-frame sitting would retain
M164's nominal family calculation, but it would not be the same rehearsal
gate. It could license the holdout without ever exercising the candidate input
package or proving that the physical instrument responds in both required
directions. Under the question's no-new-false-license rule, that reduction is
inadmissible and is discarded.

**INFERRED BY READING.** M164's complete-input requirement is correct. The
`164`-frame `S_1/S_2` witness remains the minimum complete pair for the two
registered focus budgets; this report does not replace it, weaken it, or build
the production manifest.

**INFERRED BY READING — SCOPE OF “COULD FAIL.”** No finite rehearsal can make
an independent future sitting deterministic. Shot noise, focus realization,
temperature and drift can make a correctly rehearsed score refuse. The
admissible interpretation is therefore: a cut may not introduce a *new
systematic or untested failure branch* that the full rehearsal would have
observed. Requiring literal zero probability of an independent score refusal
would make every rehearsal, including `1,092`, inadmissible.

## 1. What every block buys

**VERIFIED BY RUNNING.** The ten roles below sum to `1,092`. The first five
plus the final TC0 validation block sum to the `676`-frame M164 kernel.

| Block | Frames | Class | What it buys | Specific failure admitted if cut | Basis |
|---|---:|---|---|---|---|
| converter-on `FLAT-A/DARK-A/FLAT-B/DARK-B` | `128` | predicate calibration/control | disjoint correction for `R_1/R_2`; reference flat/dark common-mode inputs | shared or uncorrected sensor structure can inflate reference repeatability and make `Q_R` look like scene signal | **INFERRED BY READING** |
| four converter-on reference strips | `128` | predicate subject evidence | `R_1/R_2` over all eight rows and every licensed cell, with `16+16` fresh frames per strip | an omitted row pair, focus seam, field/orientation loss or low-power reference cell is never observed | **INFERRED BY READING** |
| converter-on `FLAT-V/DARK-V` | `64` | held-out predicate control | independent validation that both fitted reference maps transfer at the registered focus and temperature | an overfit or correlated A/B map can manufacture repeatable reference structure without an untouched check | **INFERRED BY READING** |
| TC0 `FLAT-A/DARK-A/FLAT-B/DARK-B` | `128` | predicate calibration/control | disjoint correction for the complete `S_1/S_2` acquisitions | shared TC0 map error can inflate apparent scored signal or deflate its half-difference noise | **INFERRED BY READING** |
| `TC0-DOM-sw4-A/B` and `TC0-DOM-sw10-A/B` | `164` | predicate subject evidence | two complete, source-disjoint scored-path input sets at both registered focus densities | a convenient frame or incomplete width understates the information available to the renderer; a missing width leaves licensed cells unmeasured | **INFERRED BY READING** |
| separate candidate `sw4-A/B` and `sw10-A/B` stacks | `164` | M1 candidate baseline; scored-session-only acquisition | supplies the candidate-rendered `Y_1/Y_2` baseline that the candidate-excluded DOM witness cannot replace, and proves that package under the frozen order, power, media, thermal and motor load | candidate rendering/adapter/settings are never exercised on their lawful inputs, and an intermittent second-package failure first appears in the holdout | **INFERRED BY READING** |
| candidate reset/start/end fixed-focus witnesses | `60` | execution control | G0-G3 stability, reset, endpoint and spectral-profile evidence for the focus program used by the score | a geometrically plausible ladder with unstable bursts, wrong return, or endpoint/profile mismatch remains eligible | **INFERRED BY READING** |
| near/middle/far sharp control | `96` | positive physical control | proves the physical instrument recognizes a genuine pre-noise optical improvement, `Q05 > 1.10` | a one-sided instrument that only rejects degradation, or reverses the positive direction, can be released | **INFERRED BY READING** |
| near/middle/far blur control | `96` | negative physical control | proves the truth channel falls under the frozen pre-noise focus offset, `Q95 < 0.90` | a blind instrument can pass all ordinary data because no physical degradation ever challenges it | **INFERRED BY READING** |
| TC0 `FLAT-V/DARK-V` | `64` | held-out predicate control and temporal closure | validates both TC0 maps after the complete TC0 package and supplies the final flat/dark common-mode bound | drift, map non-portability or repeatable contamination accumulated during the package can masquerade as dominance | **INFERRED BY READING** |

**INFERRED BY READING.** The matched featureless sentinels are embedded in the
registered target frames and add no separate count. The histogram frame is a
setup release, not a registered frame. The two M147 scale/field frames remain
outside the rehearsal.

**INFERRED BY READING.** The `315` converter-on M5/M9 frames in the combined
score are the example of a block that exists only for other scored axes and
is safely absent here. They enter neither M164 path and do not commission the
M1 instrument. No further score-only block has the same property: the
`224`-frame TC0 candidate package is the M1 score input and its eligibility
control.

## 2. Candidate savings, tested and rejected

**VERIFIED BY RUNNING.** These are the apparent smaller totals. None preserves
the current release gate.

| Proposed sitting | Frames | Nominal saving | What disappears | Ruling | Basis |
|---|---:|---:|---|---|---|
| omit TC0 held-out validation | `1,028` | `64` | final TC0 map/common-mode and temporal-closure test | **reject** — M164's charged quantities are not licensed | **INFERRED BY READING** |
| omit either physical direction control | `996` | `96` | one side of physical response commissioning | **reject** — a blind or sign-reversed instrument can pass | **INFERRED BY READING** |
| omit the separate candidate stacks, retain their fixed witnesses | `928` | `164` | second complete execution of the two scored focus programs | **reject** — intermittent execution/endurance detection is weaker | **INFERRED BY READING** |
| omit both physical controls | `900` | `192` | physical positive and degradation directions | **reject** — M164 alpha is unchanged, but the M1 instrument is uncommissioned | **INFERRED BY READING** |
| omit the complete candidate package | `868` | `224` | candidate stacks and G0-G3 fixed-focus witnesses | **reject** — the rehearsal no longer tests the score's M1 input acquisition | **INFERRED BY READING** |
| retain only the M164 kernel | `676` | `416` | all scored-input execution evidence and both physical controls | **reject** — this is an estimator qualification, not an exact-configuration holdout release | **INFERRED BY READING** |

**INFERRED BY READING.** Deleting frames *inside* the `676`-frame kernel is
also inadmissible. Removing an A or B half destroys the split-repeat
signal/noise construction; removing a strip or focus density deletes licensed
cells; removing a V class deletes held-out calibration evidence. Merely using
fewer frames per retained role changes the sampling distribution and has no
commissioned equal-power result.

## 3. Detection-power trade

### 3.1 Direct M164 evidence

**INFERRED BY READING.** M164 fixes a one-sided familywise alpha of `0.05`,
split `0.025`/`0.025` between common mode and dominance. Keeping the same
alpha after reducing frames would not keep the same power. Under an
independent equal-variance approximation, reducing a `16`-frame reference
half to `m` frames multiplies its averaging standard error by
`sqrt(16/m)`; reducing a `32`-frame calibration group to `m` multiplies the
master-noise term by approximately `sqrt(32/m)` (and the dark usable-count
term starts from `30`, after two settling exclusions). The real checker uses
clustered sites and simultaneous max-`t`, so those square-root expressions
are direction checks, not a replacement power calculation.

**INFERRED BY READING.** No physical effect-size distribution or validated
power curve in the current sources proves that any smaller repeat count keeps
the required lower confidence bounds. The exact power loss is therefore
unknown, not zero. A smaller direct kernel would need a separately
preregistered and independently validated sample-size design; it cannot be
declared equivalent from arithmetic.

### 3.2 Candidate-package insurance

**INFERRED BY READING.** The separate candidate stacks do not enter the M164
formula. They are the lawful candidate-rendered baseline for the wider M1
instrument and add an opportunity to expose an intermittent failure of the
same two in-camera focus programs under the score-like sequence. A
deterministic candidate adapter, settings or rendering failure is completely
invisible if this block is deleted. For the separate intermittent-execution
risk, if one complete four-stack package has independent failure probability
`p`, one package detects the defect with probability `p`; two packages detect
at least one failure with probability:

```text
1 - (1 - p)^2 = 2p - p^2.
```

**INFERRED BY READING.** Removing the duplicate package loses
`p(1-p)` detection probability. Equivalently, a reduced rehearsal can pass
one package and have the next package fail with probability `(1-p)p` under
that model. The repository has no estimate of `p`, and no evidence licenses
independence; with correlated or state-dependent faults the risk is even less
identifiable. The only defensible statement is that the detection opportunity
strictly decreases for `0 < p < 1`.

**INFERRED BY READING.** The full rehearsal still cannot guarantee the
independent score package. More rehearsal passes update confidence in an
unknown failure rate; they do not make the next sitting deterministic. This
is the unavoidable independent-session risk, not permission to remove an
existing observation while claiming equal detection power.

### 3.3 Physical controls and held-out validation

**INFERRED BY READING.** Omitting a physical intervention changes detection
probability for defects visible only under that intervention from the
full-block value to exactly zero. Omitting `SHARP` makes a positive-direction
failure invisible; omitting `BLUR` makes blindness to pre-noise degradation
invisible. Omitting either V pair makes map overfit, temperature/focus
non-portability and flat/dark common mode unbounded rather than merely less
precise. No numeric false-release probability is available because those
physical distributions have not yet been measured.

## 4. Staged release is admissible

**INFERRED BY READING — ANSWER: YES.** The successful path remains one
development subject plus one uninterrupted, continuously powered sitting, but
the manifest may preregister analysis holds between complete blocks. A hold
is admissible only when it is logged, the target and rig remain locked, no
setting changes, and all frozen temperature/illumination/geometry tolerances
continue to pass. If the apparatus cannot remain stable while the checker
runs, staging is not admissible and the owner must either capture the full
ordered sitting or stop.

**INFERRED BY READING.** Ordering by diagnostic power is sound only inside the
physical constraints. Converter-on evidence must precede the one converter
removal; A/B map sources must precede the subject data they calibrate; V must
close its optical-state package; and the candidate package must retain the
same order relative to the score-like blocks. Diagnostic convenience may not
reorder those facts.

**VERIFIED BY RUNNING.** The following release schedule preserves the current
`1,092`-frame successful path while limiting stopping loss:

| Release | New frames | Cumulative | Frames avoided by abort | Abort predicate | Main signature exposed | Basis |
|---|---:|---:|---:|---|---|---|
| zero-frame gate | `0` | `0` | `1,092` | missing/mutable production manifest, target, checker, hashes or settings | software/provenance, not optics | **INFERRED BY READING** |
| TR A/B calibration | `128` | `128` | `964` | wrong body/settings/count/lineage; clipped or textured flat; light-leaked dark; non-finite, nonpositive or mismatched A/B map | calibration or exposure defect | **INFERRED BY READING** |
| `TR-S01` | `32` | `160` | `932` | either row, focus return, guard, tone, geometry or required reference power fails | focus/placement at rows `1-2` | **INFERRED BY READING** |
| `TR-S02` | `32` | `192` | `900` | same frozen strip predicate | focus/placement at rows `3-4` | **INFERRED BY READING** |
| `TR-S03` | `32` | `224` | `868` | same frozen strip predicate | focus/placement at rows `5-6` | **INFERRED BY READING** |
| `TR-S04` | `32` | `256` | `836` | same frozen strip predicate | focus/placement at rows `7-8` | **INFERRED BY READING** |
| TR V validation | `64` | `320` | `772` | either reference map fails held-out flat/dark, temperature/focus portability or reference common-mode | calibration contamination versus real reference power | **INFERRED BY READING** |
| TC0 A/B calibration after the live scale/field check | `128` | `448` | `644` | live geometry or either provisional TC0 map fails the frozen predicate | placement/calibration before long TC0 blocks | **INFERRED BY READING** |
| `TC0-DOM-sw4-A/B` | `110` | `558` | `534` | incomplete budget, failed node/coverage/focus/lineage, or a manifest-issued best-case impossibility certificate for any sw4 cell | focus error; severe Viltrox/TC0 transfer or information reversal | **INFERRED BY READING** |
| `TC0-DOM-sw10-A/B` | `54` | `612` | `480` | same predicate for sw10; one weak licensed cell is enough | width-specific focus/reduction defect versus persistent optical failure | **INFERRED BY READING** |
| exact candidate package plus fixed witnesses | `224` | `836` | `256` | missing/duplicate frame, interruption, or any G0-G3 reset, endpoint, stability, spectral-profile or node failure | score-input execution rather than reference optics | **INFERRED BY READING** |
| sharp control | `96` | `932` | `160` | complete frozen control has `Q05 <= 1.10` or an eligibility refusal | absent/reversed positive response | **INFERRED BY READING** |
| blur control | `96` | `1,028` | `64` | complete frozen control has `Q95 >= 0.90` or an eligibility refusal | blindness to physical degradation | **INFERRED BY READING** |
| TC0 V plus final family | `64` | `1,092` | `0` | either TC0 map/common-mode closure fails, or any final licensed cell/control/eligibility bound fails | separates calibration/drift from the final optical verdict | **INFERRED BY READING** |

**INFERRED BY READING.** The first statistically complete release is `128`
frames because all four converter-on A/B map-source groups are needed to
instantiate the two disjoint calibration lineages. Individual `32`-frame
folders still receive immediate count, metadata, clipping and handling
checks, but calling one such folder a formal stage would not produce a
complete gate.

### 4.1 Optical diagnosis during staging

**INFERRED BY READING.** A reference strip that fails at its edge rows, or a
failure that moves with the strip focus, is a focus/placement failure and can
stop before converter removal. A field/orientation transfer loss that
persists across both complete TC0 widths after focus, power and calibration
eligibility pass implicates Viltrox aberration or bare-lens pupil behavior.
A broad information loss with transfer retained is consistent with Viltrox
transmission/reference-noise loss, but it is not final until TC0 V excludes
map and common-mode contamination.

**INFERRED BY READING.** The M164 production checker may support an interim
*fail-only* certificate after each complete DOM width: it must prove that,
even under the most favorable admissible common-mode charge and uncertainty
penalty, at least one already complete cell cannot obtain a positive final
lower bound. That certificate must be defined and hash-bound by M164 before
capture. This lane does not supply it. If M164 supplies no such certificate,
the owner may abort only on hard eligibility failures at `558`/`612`; no one
may inspect an informal margin and call the rig condemned.

## 5. Multiple looks and optional stopping

**INFERRED BY READING.** Re-running the max-`t` family after partial blocks,
continuing when the numbers look promising, or accepting as soon as one look
passes would create a multiple-looks problem. The fixed `0.05` familywise
contract does not pay for repeated acceptance opportunities. A lawful design
would need preregistered group-sequential alpha spending or an anytime-valid
confidence process and fresh commissioning; neither exists.

**INFERRED BY READING.** The schedule above avoids that problem:

1. each provenance, calibration, strip, G0-G3 or physical-control component is
   evaluated once, after its complete frozen block;
2. an early result can only stop and refuse; it can never license the score;
3. an interim optical stop is allowed only under a machine-issued logical
   impossibility certificate, not a noisy unfavorable estimate; and
4. No interim look may produce `PASS`; the complete frozen family is accepted or refused exactly once, after all `1,092` frames.

**INFERRED BY READING.** Because early refusal does not add an acceptance
event, it cannot inflate the final false-admission probability. A generic
futility boundary could reduce power by stopping a sitting that would later
pass; that is why only final-component failures and logically irreversible
conditions are allowed. Under those restrictions the set of possible passing
datasets is unchanged, so staged release preserves the original gate.

## 6. Non-holdout construction

**INFERRED BY READING.**
`D-REHEARSAL-01 — DEVELOPMENT; NEVER SCORE` remains the only subject class admitted to every rehearsal stage.
It is one rigid stochastic development panel from the frozen construction
class, with a concealed seed independent of the sealed holdout panel and of
every scored or comparator subject.

**INFERRED BY READING.** Stages do not become separate statistical units.
They remain one development subject plus one uninterrupted capture session.
No RAW, calibration map, selected site, render or fitted quantity from that
unit may enter a scored or comparator manifest.

**INFERRED BY READING.** An abort burns the development session. A purely
pre-outcome mechanical or provenance correction may be followed by a complete
fresh sitting on the already burned development panel. Any repair informed by
a cell value, dominance margin, control sign, power result or target content
requires a fresh independently seeded `D2` panel and a fresh sitting. Staging
does not borrow a holdout and does not change that rule.

## 7. Why the full version was specified

**INFERRED BY READING.** The earlier report answered a broader question:
what is the minimum *exact M1 release rehearsal* under the then-current score
design? It mirrored the `900`-frame M1 score package and added the `192`
physical controls that cannot lawfully be read in the holdout. That is why it
returned `1,092`.

**INFERRED BY READING.** The present cost challenge forced a useful separation
that the earlier report did not print prominently:

```text
676  direct M164 kernel
224  exact M1 scored-input execution
192  physical instrument controls
```

**INFERRED BY READING.** That separation does not authorize `676`, `868`,
`900` or `928`. Each smaller number deletes a branch named in the release
predicate, and the current evidence supplies no equal-power substitute. The
reasoning change is therefore not “those frames were unnecessary.” It is:
**the successful-path total was right, but treating all `1,092` as one
all-or-nothing owner commitment was unnecessarily expensive on a failing
configuration.** Fail-only staged release captures the saving that is
actually supported.

## 8. Paste-ready owner-facing replacement text

**INFERRED BY READING — PASTE-READY TEXT FOLLOWS.**

> ### Development rehearsal — one clean pass still needs 1,092 registered frames
>
> The rehearsal cannot be shortened without dropping a test that protects the
> scored sitting. What changes is the release: you will shoot it in blocks and
> stop as soon as a complete block proves the sitting cannot pass. A passing
> rehearsal still contains all `1,092` registered frames.
>
> 1. **STOP until I release the frozen capture sheet and checker.** The target,
>    margins, cell list, settings, block order, software and hashes must all be
>    final. The two-frame scale/field preflight remains allowed; it does not
>    release this rehearsal.
>
> 2. **Use only the development panel.** Mount
>    `D-REHEARSAL-01 — DEVELOPMENT; NEVER SCORE`. Keep the sealed holdout
>    covered and outside the field of view. Nothing from this rehearsal may
>    later become a scored or comparator input.
>
> 3. **Prepare for the full sitting before frame 1.** Use the registered Sony
>    body, Sony 100 mm macro, exact Viltrox, support, light, diffusers,
>    polarizers, external power, recording media and camera settings. Take the
>    one unregistered histogram frame. Once registered capture starts, do not
>    power-cycle, disturb the rig, change exposure or make an unlogged pause.
>
> 4. **First release — 128 frames.** With the converter fitted, capture
>    `TR-FLAT-A`, `TR-DARK-A`, `TR-FLAT-B` and `TR-DARK-B`, `32` each. Run the
>    released checker while the rig remains locked and powered. Wrong
>    settings, count, body, lineage, clipping, flat texture, dark light leak,
>    temperature mismatch or failed A/B map is **STOP**. Do not take a
>    reference strip after that failure.
>
> 5. **Reference release — 192 more frames.** Capture `TR-S01` through
>    `TR-S04`, `32` frames per strip, checking each strip before the next.
>    Then capture `TR-FLAT-V` and `TR-DARK-V`, `32` each. A failed row, guard,
>    focus return, tone, fiducial, geometry, power cell, held-out map or
>    common-mode check is **STOP before converter removal**.
>
> 6. **Converter-off calibration — 128 more frames.** Remove the converter
>    once, move axially to the accepted `1.32x` placement, never exceed
>    `1.33x`, and pass the live scale/field check. Capture
>    `TC0-FLAT-A`, `TC0-DARK-A`, `TC0-FLAT-B` and `TC0-DARK-B`, `32` each.
>    Failed scale, field, map, body, temperature, focus class or lineage is
>    **STOP**.
>
> 7. **Dominance witness — 164 more frames.** Capture complete
>    `TC0-DOM-sw4-A/B` stacks, `55+55`, check them, then complete
>    `TC0-DOM-sw10-A/B`, `27+27`, and check them. These RAWs never enter a
>    candidate or comparator. Missing nodes, failed focus coverage, source
>    overlap, failed geometry or a checker-certified impossible licensed cell
>    is **STOP**. No provisional number may produce an early pass.
>
> 8. **Exact candidate package — 224 more frames.** Capture the separate
>    candidate `sw4-A/B` and `sw10-A/B` stacks plus all `60` registered
>    reset/start/end witnesses in the frozen order. Any interruption, missing
>    frame or failed stability, reset, endpoint, spectral-profile or node gate
>    is **STOP**.
>
> 9. **Physical controls — 192 more frames.** Capture the `96` sharp-control
>    frames and run its frozen check; `Q05` must be strictly above `1.10`.
>    Then capture the `96` blur-control frames; `Q95` must be strictly below
>    `0.90`. A wrong, weak or invalid sign is **STOP**. Do not change the focus
>    choice or blur offset after seeing a result.
>
> 10. **Close TC0 and decide — 64 final frames.** Capture `TC0-FLAT-V` and
>     `TC0-DARK-V`, `32` each. Hash all `1,092` registered RAWs and run the
>     complete frozen checker once. Any failed calibration, common-mode,
>     geometry, focus, power, rank, conditioning, control or licensed
>     information/transfer cell makes the rehearsal **STOP / UNMEASURED**.
>
> 11. **Do not patch a failed sitting.** Preserve it for diagnosis, but do not
>     replace one folder and call the old session a pass. A repair informed by
>     an optical value, cell, control sign, power result or target content
>     requires a fresh independently seeded development panel and a complete
>     new sitting.
>
> 12. **A pass buys permission, not a score.** Only a clean `1,092`-frame
>     rehearsal licenses the fresh `1,215`-frame holdout sitting. The holdout
>     must independently pass. The staged checks reduce frames wasted on a
>     failed rig; they do not reduce the evidence required for a pass.

## 9. Verification and limits

**VERIFIED BY RUNNING.** Deterministic accounting is recorded in:

```text
experiments\M166-rehearsal-cost\analysis.json
```

**VERIFIED BY RUNNING.** The fail-closed report verifier reports:

```text
PASS: 12/12 checks
```

**VERIFIED BY RUNNING.** Every verifier check was then exercised by an
in-memory planted defect whose anchor was required to occur exactly once:

```text
COMMISSIONED: 12/12 planted defects caught; missing-anchor guard fired
```

**INFERRED BY READING.** The accounting and staging conclusions use
`M164-reference-dominance.md` for the estimator/family and complete-input
contract, `M164-m1-staged-capture.md` for staged physical holds and control
roles, `M166-reference-dominance-rehearsal.md` for the corrected block list,
and `M135-detail-instrument.md` for the mandatory physical direction controls.

**INFERRED BY READING.** The exact interim best-case impossibility certificate
is a production-manifest responsibility. Until M164 publishes and hashes one,
the `558`/`612` checkpoints may stop only on hard eligibility failures, not on
an analyst's reading of an interim dominance margin.

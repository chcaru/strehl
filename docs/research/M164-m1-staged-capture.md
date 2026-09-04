# M164 follow-up — staged physical path to an admissible M1

Status: **DESIGN PROPOSAL — NOT A CAPTURE REQUEST; DO NOT SHOOT FROM THIS FILE**

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

**DERIVED — correction to M164's earlier count.** The `891`-frame scored
session is a combined M1/M5/M9 request. It is not the smallest presently
specified M1-only sitting. M1 needs:

| M1 scored role | Frames |
|---|---:|
| converter-on fixed-focus reference, near/middle/far | `96` |
| converter-on flat A/B and dark A/B | `128` |
| converter-off `sw4-A/B` and `sw10-A/B` | `164` |
| converter-off reset/start/end witnesses | `60` |
| converter-off flat A/B and dark A/B | `128` |
| **M1-only scored sitting** | **`576`** |

The converter-on focus ladders and their `60` witnesses account for the
remaining `315 = 891 - 576` frames. They serve M5/M9, not the inverted M1
truth comparison. Omitting those blocks defers M5/M9; it does not remove an
M1 acquisition role.

The shortest currently specified unchanged-scope path is therefore:

```text
2-frame geometry preflight
+ 768-frame non-holdout physical rehearsal
+ 576-frame sealed M1-only score
= 1,346 registered/setup exposures
```

The scored request already requires one unregistered histogram exposure, so
the known shutter-release floor is `1,347`. Setup retries are not hidden in
that number: each extra M147 pair adds two releases, and any invalidated
development stage must be counted again.

This is a minimum **under the current acquisition contract**, not a theorem
that no future redesigned instrument could use fewer frames.

## 1. Release conditions before asking for Stage 1

**PROPOSAL.** The two-frame M147 preflight may proceed under its existing
owner ask. No later physical stage should be released until all of these
zero-frame conditions are true:

1. Every stage has a non-interactive, fail-closed checker that writes a
   persistent verdict. Missing inputs, malformed manifests, failed provenance,
   and numerical exceptions must return a typed failure and nonzero exit.
2. The M1 extraction code, site population, frequency cells, tone inverse,
   geometry rules, calibration lineage, reference-side resamplers, M164 gate,
   physical-control selection algorithm, and synthetic battery are versioned
   and hash-bound.
3. The target contract is reconciled. “Any stable irregular patch” is not by
   itself enough for the full claim. The selected one-use target must either
   pass M135's complete 64-site/nonduplication/power/sentinel/tone eligibility
   contract, or the concealed-code development/holdout panels must be used.
   A narrower natural-target statement requires an explicit scope ruling; it
   may not be substituted silently.
4. Common-input conversion and every required comparator binary, license,
   version, setting, native-size output adapter, and hash are executable on
   development data. The target specimen/seed is chosen only after that
   freeze.
5. The owner-facing bench sheet fixes the exact optical state and input-only
   selection rule for the two `96`-frame physical controls. This proposal
   assumes converter-off fixed-focus controls at accepted `M_work`: one
   input-selected sharp position and one preregistered focus offset, each at
   near/middle/far. The orchestrator must ratify that assumption.
6. The camera, target, light, and support can remain powered, warmed, and
   physically locked while development-stage results are read. If not,
   Stages 1–4 cannot lawfully be spliced across changed setups; after the
   desktop gates pass, the full `768` must instead be one development sitting.

The final numerical M1 margins may use arm-blind power information from the
rehearsal, but every margin, reduction, uncertainty rule, executable, and hash
must be frozen before the sealed score starts.

## 2. Staged capture with falsification gates

Stages 1–4 partition the existing `768`-frame rehearsal; they do not add a
second rehearsal. The rig remains locked between them. A pause for analysis is
allowed only while the camera, target, illumination, polarizers, roll/yaw, and
environment remain unchanged. A disturbance that breaks cross-state geometry
restarts Stage 1.

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

### Stage 1 — reference/target screen, 96 frames

**Capture.** With the converter on at maximum reproduction, shoot three
fixed-focus `32`-frame reference bursts at near, middle, and far. Focus
bracketing is off. This is the development target/panel, never the holdout
target.

**What it buys.**

- common-field and atlas-strip coverage;
- at least 64 unique guarded candidate sites;
- reference-side power in all 16 registered cells;
- provisional odd/even half agreement and burst stability;
- clipping, rail, bit-depth, fiducial, focus-seam, and 33-level tone-witness
  eligibility; and
- a cheap test of whether the proposed target is physically resolvable at all.

**GO/NO-GO.** Proceed only if every scored site belongs to one registered
reference strip, all required cells have measurable reference power, at least
64 sites survive the input-only guards, the tone strip is monotone and
unclipped, and each burst is stable. Any failed population, power, clipping,
tone, atlas, or geometry condition is STOP and sends the design back to the
target, framing, or reference optics. Stage 1 cannot prove calibration
independence; it can only reject a bad reference before another `672` rehearsal
frames are exposed.

### Stage 2 — reference calibration and split qualification, 128 frames

**Capture.** Still converter-on and without disturbing the target or optical
state, shoot independent `32`-frame flat A, flat B, dark A, and dark B groups.
Move or rotate the diffuser between flats. Retain but exclude the first two
settling darks as the current protocol requires.

**What it buys.**

- independent calibration for the two `16`-frame reference halves;
- converter-on flat/null behavior;
- reference split SNR and repeatability;
- a first check for fixed-pattern and calibration-lineage leakage; and
- proof that the reference exposure and calibration are compatible.

**GO/NO-GO.** Proceed only if both reference halves remain eligible under
their separate masters, flats are featureless at licensed scales, darks match
the warmed exposure state, no rail/precision gate fails, and the reference
split has adequate power. Shared, textured, clipped, exposure-mismatched, or
unstable calibration is STOP. Do not “fix” it by letting both halves use one
master.

### Stage 3 — exact converter-off focus rehearsal, 224 frames

**Capture.** After the live M147 ratio passes, remove the converter, move the
camera axially only, preserve the target and four or more fiducials, and shoot:

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

### Stage 4 — physical controls plus TC0 calibration, 320 frames

**Capture.** Before disturbing the target, shoot:

- `96` converter-off fixed-focus sharp-control frames, near/middle/far; and
- `96` converter-off fixed-focus focus-offset blur-control frames,
  near/middle/far.

Then shoot independent TC0 flat A/B and dark A/B groups, `4 x 32 = 128`
frames. This completes the `768`-frame rehearsal:

```text
96 + 128 + 224 + 96 + 96 + 128 = 768.
```

**What it buys.**

- the mandatory physical pre-noise degradation and improvement directions;
- calibrated truth-relative `J_TR`, transfer, and unexplained-structure
  behavior end to end;
- separate output/reference and A/B calibration lineages;
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

Only after Stage 4 passes may the registrar freeze the exact M1 statistic,
population, aggregation, margins, uncertainty, comparator relation, binaries,
settings, seeds, and hashes.

### Stage 5 — sealed M1-only score, 576 frames

**Capture.** Use a fresh target instance/panel and independent calibration in
one uninterrupted holdout sitting:

1. converter-on reference near/middle/far, `96`;
2. converter-on flat/dark A/B, `128`;
3. converter-off TC0 `sw4-A/B` and `sw10-A/B`, `164`;
4. converter-off TC0 reset/start/end witnesses, `60`; and
5. converter-off TC0 flat/dark A/B, `128`.

The optical order and all settings mirror the accepted rehearsal. The score
does not contain physical-control frames.

**GO/NO-GO.** The sitting is eligible only if every frozen input, provenance,
geometry, tone, reference, calibration, M164, rank, population, and
lineage gate passes. A failed gate returns `UNMEASURED`; no threshold, site,
focus offset, mapping, resampler, or comparator setting may be changed after
any member is read.

The full `576` may yield a valid but wide-interval M1 tuple. It qualifies a
comparator, and thereby helps M2/M3/M11, only if the future frozen M1 success
and comparator-retention predicates actually pass.

## 3. What the 768-frame rehearsal de-risks

**ARGUED.** The rehearsal is not ceremonial. Its blocks exercise distinct
physical branches that synthetic plants and the burned IBIS-on archive do not
cover:

| Rehearsal block | Frames | What becomes unknowable or uncommissioned if cut |
|---|---:|---|
| reference atlas | `96` | same-site truth coverage, two fresh `16`-frame halves, near/mid/far strip coverage, reference power |
| converter-on calibration | `128` | independent half calibration, reference flat/null, fixed-pattern and exposure compatibility |
| TC0 A/B ladders | `164` | exact `sw4`/`sw10` depth coverage, complete independent output repeats, node population |
| TC0 witnesses | `60` | reset, endpoint, fixed-focus stability and G0–G3 eligibility |
| TC0 calibration | `128` | independent A/B output calibration and output/reference lineage separation |
| physical sharp control | `96` | proof the instrument can recognize a real pre-noise improvement rather than only reject defects |
| physical blur control | `96` | proof the truth channel decreases under a real pre-noise degradation at the frozen offset |

Skipping the rehearsal moves every unexercised physical branch into the
holdout. The first needed code, target, mapping, focus-offset, tolerance, or
sample-size change would then burn the full scored sitting. Cutting only the
controls recreates the exact failure mode the commissioning standard forbids:
a blind instrument can pass a battery containing only defects.

The `768` is not proved globally minimal. It is the smallest complete
exact-configuration rehearsal currently specified: all named frame counts and
A/B/reference roles are inherited from the score design, and there is no
measured physical power result authorizing fewer repeats, fewer calibration
lineages, one step width, or fewer than 64 sites. A smaller rehearsal is
possible only as a separately preregistered redesign with its own power and
commissioning evidence; simply deleting frames is not an uncertainty trade.

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

## 4. Weakest presently admissible M1 capture

**ARGUED.** The smallest scored sitting under the unchanged current M1 design
is `576` frames after the complete accepted rehearsal. The `448` frames named
as the “inverted block” in M135 rely on `128` converter-on calibration frames
already present in the wider M1/M5/M9 session. A standalone M1 sitting must
restore those `128`, yielding `448 + 128 = 576`.

Below `576`, the omitted roles are not merely a source of wider confidence
intervals:

- one output pass cannot separate repeatable information from one realization;
- one reference half cannot expose reference noise or agreement;
- shared or missing flat/dark masters destroy acquisition lineage;
- one step width does not meet the registered stress population;
- missing witnesses leave reset, endpoint and node matching unqualified; and
- fewer control/rehearsal roles leave the physical instrument uncommissioned.

Thus the current design is **all-or-nothing below 576 with respect to
acquisition eligibility**. A future power-backed redesign might find a lower
count, but no repository evidence presently licenses one. Conversely, all
`576` frames do not guarantee a positive or qualifying result; they only make
an admissible reading possible.

## 5. Ways the capture can still be unusable

The table distinguishes an instruction that can prevent waste from a result
that must remain a typed refusal. Items marked **ADD** are not yet safely
resolved in the owner-owned request.

| Waste mode | Preventive instruction before owner capture | Required consequence |
|---|---|---|
| No admitted numeric M1 bar when score begins | **ADD:** after Stage 4, freeze the exact `J_TR/F_TR/U_TR` implementation, site/band population, reduction, margins, uncertainty, comparator rule, seeds, settings and hashes | Do not release Stage 5 |
| Current capture request still carries a STOP banner | Replace it only after `M_work`, target contract, control optical state/offset, stage readers, block order and failure actions are reconciled | Do not infer permission from this report |
| Stage data are acquired before their reader exists | Require a dry-run-passing, persistent, fail-closed checker for every stage before that stage is released | Missing checker is STOP at zero frames |
| Common-input or comparator adapter is unavailable | Freeze and hash every required renderer, license, setting and native-size linear output path on development data before choosing the target | Do not spend physical capture on an unrunnable comparator |
| The `$0` patch supports only a narrower target-conditional claim | Require all M135 target-eligibility gates; otherwise fabricate independent concealed development/holdout panels | `TARGET_INELIGIBLE`; no silent scope reduction |
| Target/seed is known while renderers are still tunable | Freeze binaries and settings first; then choose the one-use specimen/orientation or generate concealed seeds; keep holdout panel sealed | Any post-target tuning invalidates the target |
| Printed target is scaled, screened, sharpened or repeated | Supply final-size artwork; disable fit-to-page/RIP enhancement; verify physical carrier mapping and uniqueness before capture | Reject the panel |
| Target lacks 64 guarded common sites or all 16 cells | Stage 1 census from input-only geometry; require the complete site/power floor before proceeding | Redesign target/framing |
| Carrier maps above `0.25 cyc/native scored px` | Generate physical cell dimensions from accepted `M_work`; verify mapping from measured pixels, not nominal print dpi | Refuse affected target/cells; full contract fails |
| Target, tone strip and fiducials are not coplanar | Mount all on one rigid plane and verify plane residual from input-only fiducials | Restart with a coplanar target |
| Natural specimen dries, shifts or changes | Use a rigid inert one-use target for the score; if a natural patch is used in rehearsal, lock and monitor it | Any visible/metric scene change invalidates pairing |
| Reference field or near/mid/far atlas misses sites | Stage 1 map must assign every retained site to exactly one well-focused strip with guards away from seams | Reframe or redesign atlas |
| Reference sampling ratio is below `2.0` | Stage 0 plus a live ratio check before the first TC0 scored frame; use unrounded M147 lower bound | STOP; never substitute lens labels |
| No `M_work` satisfies ratio, field and frequency simultaneously | Compute the feasible set after Stage 0 | Abandon the current shared-prime inversion |
| Converter-on transfer is not stronger in every licensed cell | Measure it in the complete rehearsal with adequate target power and both calibrated reference halves | Refuse the failed cell; if every registered cell is required, no M1 score |
| Shared base-lens zero is mistaken for object truth | State the claim as reference-path-conditional and report only frequencies whose reference transfer qualifies | Never claim detail outside the qualified reference passband |
| IBIS or lens OSS is enabled | Bench checklist and recorded state: body SteadyShot OFF, lens OSS OFF before every stage and after every power/state change | Entire affected stage is unusable |
| Wrong exposure or automatic processing is enabled | M mode, ISO 100, `1 s`, marked f/5.6, fixed WB, camera-linear 14-bit RAW, EFCS; NR/DRO/HDR/lens corrections and auto review off | Metadata/settings mismatch is refusal |
| Clipping, photon starvation or invalid tone range | Take the one throwaway histogram frame before the registered score; verify rails and all 33 levels before frame 1; adjust only before the session | Once score starts, stop and reshoot rather than retune |
| Lighting flicker, warm-up drift or moved polarizers | Flicker-free source warmed at least 15 minutes; lock source and polarizers; record illumination witnesses | Drift beyond frozen eligibility invalidates the stage |
| Sensor/camera thermal state changes between subjects and calibration | **ADD:** commission a pre-warm and input-only thermal-stability check in rehearsal; keep camera powered and timestamp blocks; capture darks at the matched warmed state | No numeric stability threshold is currently frozen, so Stage 5 remains blocked until one is |
| Stage-analysis pause changes the physical setup | Keep rig, camera, target, lighting and environment locked and powered while a verdict is read | If continuity cannot be maintained, restart Stage 1 or shoot the full rehearsal as one sitting |
| Focus reset approaches from the wrong direction | Record one reset method/direction; use it for P0/P1, every A/B pass and every control; issue no extra AF command | Failed G1/reset gate is STOP |
| Focus motion has not settled | Preserve the registered 3-second bracket interval and at least 3 seconds after manual focus motion | Failed G0/G3 is STOP |
| Wrong bracket count, width or direction | Exact `55/27`, widths `4/10`, complete A then B passes, order `0 -> +`; verify folder counts before changing state | Never fill missing frames or re-index after capture |
| `sw4`/`sw10` has gaps or endpoint peaks at `M_work` | Stage 3 image-derived coverage and 64-site interior-peak check; EXIF `FocusPosition2` is not evidence | Change design on development data; do not score |
| A/B nodes do not represent the same focus positions | Apply G2 `< 0.10` fixed-focus log-ratio plus G3's unique zero-lag maximum and `< 0.10 px` geometry gates to same-index curves | No result-time shift or node re-indexing |
| Fixed-focus bursts, resets or endpoints are unstable | Apply G0 `<= 0.033 px` and G1 `< 0.10 px` gates exactly as registered | Failed burst/state is unusable |
| Converter is removed too early or reinstalled | Finish converter-on reference and calibration first; log owner-confirmed 2x Viltrox identity; remove once, then remain TC0 | Mixed state/order invalidates lineage |
| Camera is reframed by yaw, roll or target movement | Keep target fixed; move camera axially only; retain at least four common fiducials and input-only geometry residuals | Failed native mapping is refusal |
| Focus Bracket remains on for the truth atlas | Explicitly turn it OFF and store near/mid/far bursts separately | A merged/bracket truth reference is circular and unusable |
| Reference exposure differs from its calibration | Lock exposure across reference and converter-on masters; record settings at every block | Exposure mismatch invalidates reference calibration |
| A/B or optical states share calibration | Four separate `32`-frame flat/dark groups per optical state; no master crosses A/B, optical state, rehearsal/score, or session | Missing lineage returns `UNMEASURED` |
| Flats contain paper/diffuser texture or A/B flats repeat the same pattern | Use a true diffuse/integrating field or adequate defocus; move/rotate diffuser between A and B | Failed flat sentinel is refusal |
| Darks are cold, light-leaked or at wrong exposure | Warm camera, cap/light-seal correctly, keep scored exposure, retain but exclude first two settling darks | Recapture development stage; scored mismatch burns sitting |
| Reference and output share correlated sensor structure | Enforce different sensor footprints after scale change, independent masters, and blank-residual correlation `<= 0.05` | Correlation failure is nonnumeric refusal |
| Physical blur/improvement controls are post-selected | Freeze an input-only focus-position/offset rule after Stage 3; register before Stage 4; never choose by the desired M1 sign | Control arm is invalid |
| Only degradation is commissioned | Keep all `96` genuine-improvement frames and require the registered positive direction | Wrong/absent improvement kills the instrument |
| Control arm uses the truth reference as the “improvement” | Use a separate converter-off fresh-noise optical capture; the reference remains truth only | Circular arm is invalid |
| Rehearsal and score reuse target, reference or calibration | Use independent one-use development and holdout target instances/panels, exposures, flats and darks | Shared lineage burns admission |
| Battery, card or power cycle interrupts the scored sitting | **ADD:** use the power method proven across the full rehearsal; pre-verify card capacity for all RAWs plus reserve; no card/battery swap, sleep, firmware update or power cycle | Any interruption makes the whole subject/session ineligible |
| Files are missing, duplicated, mislabelled or silently corrupted | Empty dedicated destination/card, literal block folders, expected-count manifest, SHA-256 on ingest, and fail-closed role binding | Never infer a missing role from timestamps |
| Score is previewed, rendered or tuned before sealing | After the one histogram setup frame, disable auto review; permit only frozen input/provenance gates; hash and seal the complete sitting before any comparator output | Any quality/outcome read burns the entire subject/session |
| A participant applies USM, denoise/blur, deconvolution, resize or internal postfilter | Freeze neutral output settings and native dimensions; run M164 before M1; prohibit unilateral postfilters on the common-merge track | M164 fire means that pair is inadmissible, not worse |
| Product-internal sharpening is mixed with genuine merge differences and evades M164 | Keep truth-relative non-compensating `F_TR/U_TR`; do not treat `NOT_VETOED` as structural sharpening safety | Failed truth witness is refusal |
| Exact score duration exceeds setup stability | Measure the complete order and transition time during Stages 1–4; do not promise 45 or 60 minutes until rehearsed | If stable uninterrupted execution is not demonstrated, do not release Stage 5 |
| Stage 5 is split or resumed after interruption | Declare one subject plus one uninterrupted sitting as the holdout unit; provision power/storage before frame 1 | Discard the entire sitting for M1 |
| A failed score gate is repaired after looking | Freeze all remediation policy beforehand; a failed eligibility gate returns `UNMEASURED` | Any changed code/threshold requires a fresh holdout |

## 6. Revised totals and stopping losses

| Last completed gate | Newly exposed frames | Cumulative registered/setup exposures |
|---|---:|---:|
| Stage 0 | `2` | `2` |
| Stage 1 | `96` | `98` |
| Stage 2 | `128` | `226` |
| Stage 3 | `224` | `450` |
| Stage 4 — full rehearsal accepted | `320` | `770` |
| Stage 5 — M1-only score | `576` | **`1,346`** |

If M147 requires its one allowed placement verification, add `2`. The score's
known throwaway histogram release makes the base physical release floor
`1,347`; any additional setup test frames must be named by the final capture
request rather than silently omitted.

The current request also calls for a live ratio decision after converter
removal but does not say whether it consumes a new RAW or a live-view/input
frame. If it needs another shutter release, add it explicitly; it is not
silently included in `1,347`.

If the owner elects to preserve the combined M1/M5/M9 holdout instead, Stage 5
remains `891` and the original registered total remains:

```text
2 + 768 + 891 = 1,661
```

The staging reduces how many frames are lost before a failure is discovered.
Only the M1-only unbundling changes the final total, by deferring `315`
converter-on M5/M9 focus/witness frames. It does not weaken M1.

## 7. Final recommendation

**PROPOSAL.** Execute the two-frame M147 preflight first. If the feasible
working-magnification set is nonempty, implement and dry-run the four
development-stage checkers, then expose only one rehearsal stage at a time
while the rig remains locked. Do not release the next block until the previous
verdict is on disk and accepted. After the complete `768` passes, freeze the
M1 bar and choose between:

- **M1-first:** `576` sealed frames, `1,346` registered/setup exposures total;
  or
- **combined M1/M5/M9:** `891` sealed frames, `1,661` total.

Given M1's comparator-qualification dependencies, the M1-first path is the
smallest unchanged-scope route to any admissible M1 reading. It is not a
promise of a qualifying result.

## 8. Governing sources

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

# M166 — adversarial audit of the truth-reference capture

Status: **COMPLETE**

## 0. Verdict

**INFERRED — VERDICT: `SOUND WITH REPAIRS`.** The central instrument is not
fatally circular. An independently exposed reference plus the
non-compensating `TRD = (J_TR, F_TR)` certificate closes the specific
post-render-sharpening attack for a deliberately narrow estimand: information
recoverable through the qualified reference path. A pure full-rank linear
postfilter cannot raise `J_TR`, and any transfer movement can only veto or
demote through `F_TR`.

**VERIFIED BY RUNNING.** A finite two-world witness reproduces identical
reference and output observations to maximum error
`1.24e-16` and `2.78e-17` while changing latent object and reference transfer.
It proves that the atlas does **not** identify unconstrained object truth
`X`; it identifies the reference-path latent `GX`.

**INFERRED.** That surviving scope is scientifically usable, but the capture
is not ready as written. Five repairs are capture-blocking:

1. make the claim scope or independently known target explicit;
2. replace the hard-coded three-strip atlas with a measured strip count and
   repeatable focus-position protocol;
3. add a real reference-error independence test rather than treating
   odd/even exposure splitting as sufficient;
4. freeze the covariance dimensions and physical micro-site population before
   artwork or capture; and
5. solve magnification, panel packing, per-strip scale, and stability as one
   feasible-set gate.

**INFERRED.** If the program insists on *object truth* rather than the stated
`GX` reference-path claim and declines an independently certified target or
reference OTF, the verdict for that broader claim is `FATALLY FLAWED`.

## 1. Evidence boundary

**VERIFIED BY READING.** The governing design was read from
`docs/proposals/2026-09-truth-referenced-detail.md`, especially §§0.1,
2.2–2.4, 3.1, 4–7, and 10.

**VERIFIED BY READING.** The target, estimator, and claim-scope contracts were
read from `docs/research/M135-detail-instrument.md`, especially §§3.3, 4,
6.1, 6.4, and 6.6.

**VERIFIED BY READING.** The staged fail-closed capture was read from
`docs/research/M164-m1-staged-capture.md`, especially §§2–6.

**VERIFIED BY READING.** The scale gate and its unclosed real-optics
uncertainty were read from `docs/research/M147-preflight.md`, especially §§0–4.

**VERIFIED BY READING.** The macro DoF equation and the fact that reported
`f/5.6` already includes the teleconverter penalty were read from
`docs/research/F-camera-lens-optics.md` §4.

**VERIFIED BY RUNNING.** The deterministic calculations are in
`experiments/M166-truth-reference-capture-audit/analysis.json`; the fail-closed
checker reports `14/14` in `verification.json`.

**VERIFIED BY RUNNING.** This audit decoded no RAW, opened no request-7
holdout image, rendered no output, and performed no timing measurement.

## 2. Threat 1 — does the atlas identify truth?

### 2.1 What it identifies

**VERIFIED BY READING.** The proposal's split-reference model is:

```text
R_1 = G X + e_1
R_2 = G X + e_2
Y   = H X + n
```

**INFERRED.** Under zero cross-error covariance, its cross-transfer estimator
has expectation:

```text
E[Y R*] / E[R_1 R_2*] = H / G.
```

**INFERRED.** The unknown scene power cancels. Gate 3 can therefore determine
whether the scored path is attenuated relative to the reference path without
knowing the absolute transfer `G`. My initial urgent alert saying that gate 3
could not self-measure `G` was too strong; it need not measure `G` separately
to estimate `H/G`.

**VERIFIED BY READING.** The proposal already calls the atlas a “qualified
proxy,” requires reference-transfer superiority in every licensed band, and
limits the result to the shared-prime reference passband. M135 §3.3 likewise
says the result measures information about `GX`, not unconstrained object
truth.

### 2.2 The surviving gauge ambiguity

**INFERRED.** For any invertible transfer `K`, the two worlds

```text
world A: X,      G,        Y_i = K H_i X, R = G X
world B: X'=KX,  G'=G K^-1, Y_i = H_i X',  R = G' X'
```

produce identical reference pixels, identical output pixels, and identical
ratios `H_i K/G = H_i/G'`.

**VERIFIED BY RUNNING.** The M166 witness uses `G=0.8`, `K=1.2`, and output
transfers `0.35` and `0.50`. Both worlds produce the same observations while
the output/reference ratios remain `0.525` and `0.750`, so the relative
reference-superiority gate passes in both.

**INFERRED.** This construction kills an *absolute-object* interpretation,
because `X` and `G` are not separately identified. It does not kill the
declared `GX` interpretation: `G'X' = GX`, so the scoped truth is identical in
the two worlds.

### 2.3 Why the original sharpening attack is nevertheless closed

**VERIFIED BY READING.** `J_TR` is exactly invariant to a registered
nonsingular linear operator applied after output noise. `F_TR` reports
attenuation, overshoot, phase, and unexplained repeatable structure separately
and may never create a win.

**INFERRED.** With a fixed physical reference, post-render sharpening changes
`Y` but not `R`. It cannot raise `J_TR`; if it moves transfer toward the
reference, that movement still cannot compensate for the absent information
gain. If it overshoots, `F_TR` worsens.

**INFERRED.** This is a healthy discriminating structure: genuine
pre-noise improvement can raise `J_TR`, while a pure post-noise invertible
filter cannot.

### 2.4 Required scope repair

**VERIFIED BY READING.** The current `$0` stochastic-patch route in M135 §6.6
does not provide a known latent input. It supports a target-conditional,
reference-path statement. M135 §6.4's independently seeded panel is the
stronger target route, and proposal §3.3 is the separate known-physical-target
alternative.

**INFERRED — REPAIR.** The score and owner protocol must choose one of two
contracts before capture:

- **reference-path contract:** state every result as information about `GX`,
  exclude shared/reference optical zeros and aberrations from object-truth
  language, and never call the stochastic patch a known input; or
- **object-truth contract:** use a traceable, concealed, two-dimensional
  nonperiodic target whose realized geometry/transfer is independently bounded,
  or independently calibrate the reference OTF in every licensed cell.

**INFERRED.** A design file alone is not a complete physical truth witness if
the printer, emulsion, mask, or mounting transfer is unknown. The realized
artifact needs independent fabrication metrology or the claim remains
reference-path-conditional.

## 3. Threat 2 — the `2.0x` sampling requirement

### 3.1 Sampling sufficiency

**VERIFIED BY RUNNING.** Deriving pitch from `35.9 mm / 7008 px` gives
`5.1227169 um`. At the conservative scale ratio
`2.7015 / 1.33 = 2.0312030`, the maximum licensed
`0.25 cyc/scored px` mode maps to `0.1230798 cyc/reference px`, or
`8.1248` reference pixels per cycle.

**INFERRED.** As a lateral-sampling condition, `2.0x` is enough for the
licensed band. The licensed mode is far below reference Nyquist, and there is
no information-theoretic cliff at exactly `2.0x`.

**VERIFIED BY READING.** The proposal does not treat sampling ratio as optical
proof. It separately requires split-reference SNR, reference power, and
superior object-space transfer.

**INFERRED.** That separation is healthy. “Empty magnification” can pass gate
1 but must fail gate 3 or gate 7.

### 3.2 The `1.54%` operational margin

**VERIFIED BY RUNNING.** The conservative point ratio exceeds `2.0` by
`1.536%` of the achieved ratio (`1.560%` relative to the threshold).
M147's nominal synthetic plant returned point `2.0329159` and lower bound
`2.0126457`, leaving only `0.6323%` lower-bound headroom.

**VERIFIED BY READING.** M147 explicitly says the converter-change systematic
is unbound until the real two-frame pair is measured. It fails closed whenever
the unrounded lower bound is below `2.0`.

**INFERRED.** Measurement uncertainty therefore cannot silently turn a miss
into a pass. The remaining risk is wasted capture from manual placement or
from assuming that the maximum-reproduction ratio applies to all three
reference focus states.

### 3.3 Scale and target packing form one narrow feasible set

**VERIFIED BY READING.** M135's engineered panel specifies a `10 x 8` layout.
Each site has a `128 px` interior plus a `64 px` guard on every side, so each
cell spans at least `256` scored pixels.

**VERIFIED BY RUNNING.** Eight guarded rows occupy:

| scored magnification | nominal eight-row height |
|---:|---:|
| `1.30x` | `8.07025 mm` |
| `1.32x` | `7.94797 mm` |
| `1.33x` | `7.88821 mm` |

**VERIFIED BY RUNNING.** Ignoring fabrication and placement allowance, the
minimum magnification that fits those eight rows inside `8 mm` is
`1.31142x`. At `1.32x`, only about `52 um` of total nominal vertical room
remains.

**INFERRED.** Lowering scored magnification is not an unlimited way to buy
sampling margin. Below about `1.311x`, the registered panel geometry no longer
fits before adding manufacturing tolerance, seam clearance, or border
allowance.

**INFERRED — REPAIR.** Stage 0 must solve and persist one joint feasible set
over:

```text
sampling LCB
AND per-strip reference magnification
AND full target/guard/fiducial/tone-strip field
AND fabrication tolerance
AND licensed carrier mapping.
```

**INFERRED — REPAIR.** The bench sheet must aim at the interior of that
measured feasible set, not at the `1.33x` ceiling. The actual ratio must be
checked again from the scored target before the first long TC0 bracket.

## 4. Threat 3 — odd/even reference “independence”

### 4.1 What is independent

**VERIFIED BY READING.** Odd and even frames are separate physical exposures,
so photon and ordinary read-noise draws can be conditionally independent.
Using disjoint A/B flat and dark fits also removes shared map-estimation noise
that one common fitted master would introduce.

**INFERRED.** The two halves are not independent physical references. They
share subject, objective, teleconverter, sensor, illumination, vibration
environment, focus state, thermal history, and any stable or cadence-locked
residual.

### 4.2 Constructive common-error failure

**INFERRED.** If

```text
R_1 = GX + C + e_1
R_2 = GX + C + e_2,
```

then the split denominator contains:

```text
E[R_1 R_2*] = |G|^2 P_X + P_C.
```

**INFERRED.** Reference-half agreement rewards the common term `C`; it cannot
detect it. Disjoint fitted masters also do not remove a physical residual
common to both halves.

**VERIFIED BY RUNNING.** In the registered scalar witness
`G=0.8`, `H=0.4`, scene power `1`, and common-reference-error power `0.2`,
the estimated `H/G` changes from `0.5` to `0.380952`, a `-23.81%` bias.
Allowing half of that common term to leak into the output raises squared
correlation by `7.87%`.

**INFERRED.** The witness is not a claim that this camera has that exact
error. It demonstrates that odd/even splitting plus half agreement does not
establish the zero cross-error premise used by the estimator.

### 4.3 Required independence repair

**INFERRED — REPAIR.** Retain the 32 exposures per focus position, but record
their full order and require all of:

1. the preregistered odd/even split;
2. a non-degenerate temporal split such as first/last or blocked `ABBA`;
3. agreement of `J_TR`, `H/G`, and every `F_TR` component across those
   partitions;
4. per-cell reference-half residual cross-power on matched featureless
   sentinels; and
5. alignment/translation estimates whose noise is not fitted jointly across
   the two halves.

**INFERRED — REPAIR.** The null must be per licensed cell and tonal stratum.
A single frame-wide correlation can average a bad band or field region below
its threshold.

**VERIFIED BY READING.** M135's flat/detail ratios, M164's held-out A/B/V
maps, different sensor footprints, and the `<=0.05` blank-residual gate are
strong existing defenses. The repair makes their required independence claim
match the estimator rather than replacing them.

## 5. Threat 4 — diffraction and information superiority

### 5.1 Diffraction-only result

**VERIFIED BY RUNNING.** At `1.33x`, the licensed
`0.25 cyc/scored px` endpoint is `64.907 cyc/mm` in object space.
Using the proposal's Airy ranges gives diffraction-only object-space cutoff
ranges:

| path | cutoff range |
|---|---:|
| converter-on reference | `286.38–368.58 cyc/mm` |
| bare-lens scored state | `184.71–228.04 cyc/mm` |

**INFERRED.** Diffraction alone does not make the reference empty at the
licensed endpoint, and it predicts a real advantage.

**VERIFIED BY READING.** The Viltrox aberration and bare-lens pupil
magnification remain unmeasured. The proposal correctly refuses to promote
the diffraction calculation into proof.

### 5.2 What gate 1 cannot establish

**INFERRED.** More pixels per millimetre do not establish more independent
subject information. Defocus, teleconverter aberration, flare, phase error,
or a reference-specific ghost can all consume the sampling advantage.

**INFERRED.** A magnitude-only “reference stronger” test is also insufficient
for an object-truth claim. A repeatable converter-specific halo can coexist
with high magnitude transfer and become part of `GX`.

**INFERRED — REPAIR.** Freeze gate 3 as a per-strip, per-cell
errors-in-variables transfer test using both reference halves and
input-selected converter-off sharp controls. It must report magnitude,
phase, unexplained structure, uncertainty, and a nonzero power floor.
Selection may use only input geometry/focus evidence.

**INFERRED — REPAIR.** For the sealed sitting, either re-evaluate transfer
sufficiency from the raw input focus peaks and the sealed reference, or prove
in rehearsal that the frozen transfer qualification lawfully carries across
the registered optical/focus/temperature class. Rehearsal success alone must
not silently certify a changed class.

**INFERRED.** If the claim remains `GX`-conditional, a qualified
reference-specific aberration narrows the claim but does not make the
statistic circular. If the claim says object truth, that aberration requires
the independently known target/OTF repair in §2.4.

## 6. Threat 5 — three fixed-focus strips

### 6.1 Constructive coverage calculation

**VERIFIED BY READING.** The owner protocol says to tilt the target roughly
`1 degree`; it does not freeze the tilt axis or tolerance. The reference
count is hard-coded to near, middle, and far.

**VERIFIED BY RUNNING.** A `1 degree` tilt produces depth spans of:

| active direction | depth span |
|---|---:|
| `8 mm` short axis | `139.62 um` |
| `12 mm` long axis | `209.43 um` |
| `12 x 8 mm` diagonal | `251.70 um` |

**VERIFIED BY RUNNING.** Applying the repository's macro DoF equation at
`m=2.7015`, reported `f/5.6`, measured bellows factor
`2.412–3.064`, and a permissive two-sensor-pixel circle of confusion gives
only `37.92–48.18 um` total DoF per fixed-focus burst.

**VERIFIED BY RUNNING.** Three ideal, non-overlapping strips therefore cover
only `113.77–144.53 um`. Across the short axis, the required count is
`3–4`; across the long axis it is `5–6`; across the diagonal it is `6–7`.

**INFERRED.** Three strips are not guaranteed even under the most favorable
short-axis interpretation. At the favorable DoF endpoint they leave less than
`5 um` total slack before overlap or seam guards; at the other endpoint they
miss the short-axis depth range outright.

**INFERRED.** The exact transfer-based usable focus width may be narrower than
the two-pixel DoF surrogate, so this calculation is a permissive warning, not
a pessimistic bound.

### 6.2 Required focus repair

**INFERRED — REPAIR.** Do not freeze the atlas at three bursts. Before the
sealed capture:

1. measure the target plane and tilt axis from fiducials;
2. acquire a low-cost converter-on single-frame focus census on the
   development panel;
3. define each strip's usable support by the actual per-cell transfer/focus
   gate, not by “thirds”;
4. choose and freeze enough strip centers that every retained site belongs
   wholly to one support with the registered seam/guard margin; and
5. increase the reference frame count before holdout if more than three
   strips are required.

**INFERRED — REPAIR.** The score panel must use the rehearsed plane
orientation and mechanically referenced strip offsets. If the lens focus ring
is used instead, magnification and geometry must be measured separately for
every strip.

**VERIFIED BY READING.** `FocusPosition2` is too coarse to recover the needed
macro focus state. It cannot serve as the strip-position witness.

**INFERRED — REPAIR.** The strongest rig procedure is to lock the lens at the
registered reference magnification and translate the camera on a measured
axial stage for each strip. That keeps the lens state fixed and makes the
focus offsets externally recordable. If the available support cannot do
that repeatably, the focus protocol needs another independently measurable
actuator before capture.

**INFERRED — REPAIR.** Apply the `LCB95 >= 2.0` sampling gate separately to
every retained reference strip. A single maximum-reproduction preflight does
not prove the ratio after focus breathing at middle and far settings.

## 7. Threat 6 — this Sony/Viltrox rig

**VERIFIED BY READING.** The A7C II cannot interleave A/B exposures at each
focus-bracket node. The staged design uses complete A and B sweeps, so it does
not require an impossible camera operation.

**VERIFIED BY READING.** Fixed-focus bursts with Focus Bracket disabled are
physically compatible with the body. The reference atlas does not ask the
camera to merge or bracket those frames.

**VERIFIED BY READING.** Existing corpus evidence proves focus bracketing with
the communicating Viltrox fitted, but no existing capture proves the exact
bare-lens `M_work` schedule. M164 correctly places the bare-lens width and
node tests in the non-holdout rehearsal.

**INFERRED.** Removing the converter once, remounting the prime, and moving
the camera axially is physically possible. It can disturb roll, yaw,
polarizer angle, dust, illumination, or sensor footprint, but the design's
fiducial, map, held-out-flat, and geometry refusals can detect rather than
normalize those changes away.

**VERIFIED BY READING.** The staged design already fails closed on wrong
aperture/exposure, IBIS/OSS, clipping, focus-node mismatch, missing map
lineage, geometry residual, or interrupted setup. These are healthy controls,
not unresolved logical defects.

## 8. Additional threats

### 8.1 A natural patch does not supply independent coded sites

**VERIFIED BY READING.** The estimator requires at least 64 independent
macro-sites. The `$0` route permits ordinary stochastic material and tests
nonduplication and power.

**INFERRED.** Nonduplication is not statistical independence. One natural
fiber field can have long-range texture, repeated manufacturing structure,
or one global nuisance shared by all 64 sites. A site bootstrap can then
understate uncertainty.

**INFERRED — REPAIR.** Use independently seeded development and holdout code
panels for the full M1 claim. If a natural patch is retained, freeze a
correlation-length/effective-sample-size rule and state the result as
one-specimen conditional; do not call 64 spatial crops 64 independent
physical subjects.

### 8.2 The rank contract is not yet a physical target contract

**VERIFIED BY READING.** Proposal §6 requires
`n / max(p,q) >= 1.5`, no regularization, and enough disjoint micro-sites.
M135's artwork specifies 64 macro-sites but does not fix `p`, `q`, the number
of micro-sites, or their independent code construction.

**VERIFIED BY RUNNING.** If each macro-site supplies one covariance row,
`n=64` allows `max(p,q) <= 42`; dimension `43` already fails. A complete
`128 x 128` output interior has dimension `16,384` and would require at least
`24,576` rows under the stated ratio.

**INFERRED.** The proposal may choose a much smaller theorem-bearing support
and enough independently coded micro-sites, so this is not an impossibility
proof. It is a zero-frame definition blocker: the photons cannot be repaired
after the panel is made.

**INFERRED — REPAIR.** Freeze `p`, `q`, support shape, postfilter support,
micro-site size/count/code independence, clustering level, condition-number
bar, and exact target packing. Run the full rank path on synthetic artwork
before releasing fabrication or Stage 1.

### 8.3 Shared geometry fitting can re-couple the halves

**VERIFIED BY READING.** The proposal allows analytic translation correction
before each reference mean and requires frozen reference-side geometry.

**INFERRED.** If one noisy fit jointly estimates translations or a local warp
from all 32 reference frames, its estimation error is shared by `R_1` and
`R_2`. Disjoint flat/dark maps do not remove that coupling.

**INFERRED — REPAIR.** Estimate half-specific frame translations from
input-only fiducials, or estimate a common deterministic geometry from a
separate calibration source and propagate its uncertainty. Never improve a
joint reference alignment by maximizing the scored texture correlation.

### 8.4 Session stability remains undefined

**VERIFIED BY READING.** M164 already identifies missing numerical
temperature and uninterrupted-stability thresholds as release blockers.
The reference is captured before converter removal; scored brackets and
calibration follow later in the same long sitting.

**INFERRED.** “Same session” is not itself a stability measurement. A slow
focus, illumination, sensor-temperature, or polarizer drift can be common
inside odd/even halves while differing between reference and scored states.

**INFERRED — REPAIR.** Before Stage 6, freeze input-only thresholds for tone
strip drift, fiducial geometry, dark-temperature witness, reference-focus
stability, and held-out flat/dark residuals. Record those witnesses around
the relevant blocks and refuse the full sitting when any class changes.

## 9. Exact pre-capture repair set

**INFERRED — REPAIR 1: claim and target.** Choose `GX`-conditional scope
explicitly, or require an independently certified concealed target/OTF for
object truth. For the full M1 claim, replace the generic natural patch with
independently seeded development and holdout panels carrying matched
featureless sentinels and the frozen micro-site population.

**INFERRED — REPAIR 2: estimator-to-artwork closure.** Freeze and dry-run
`p`, `q`, support, rank, conditioning, micro-sites, clusters, bands, guards,
and every refusal before fabrication. Missing rank evidence is a zero-frame
STOP.

**INFERRED — REPAIR 3: joint scale/field gate.** Solve `M_work` jointly with
panel packing and fabrication tolerance. Require M147's real-optics field
commissioning, then remeasure the ratio on the actual score target and for
every reference strip.

**INFERRED — REPAIR 4: variable atlas.** Replace “near/middle/far =
three” with an input-only measured strip-cover algorithm and a variable
registered strip count. Freeze the score-panel tilt axis/tolerance and a
repeatable mechanical focus-position method.

**INFERRED — REPAIR 5: reference error.** Keep disjoint A/B/V calibration,
but add alternate temporal partitions, per-cell matched-blank cross-power,
half-specific alignment, and partition-sensitivity limits.

**INFERRED — REPAIR 6: information superiority.** Freeze the per-cell
errors-in-variables transfer, phase, residual, SNR, and power gates. Exercise
them with the rehearsal's physical sharp/blur controls and bind how sealed
input frames re-establish the accepted optical class.

**INFERRED — REPAIR 7: stability.** Freeze thermal, illumination, focus,
geometry, and calibration-continuity thresholds and prove the complete
physical sequence in rehearsal. A failed witness returns `UNMEASURED`; it is
never repaired from the sealed result.

## 10. What survives the attack

**INFERRED.** The atlas is not merely a second output of the same merger. It
has fresh exposures, higher subject sampling, disjoint calibration, a
different sensor footprint, and no access by the tested algorithm.

**INFERRED.** `J_TR` plus veto-only `F_TR` has the right loose-direction
closure: a constant output has no usable rank/information, post-render blur
ties on information and loses transfer, post-render sharpening cannot gain
information, and pre-noise blur loses information.

**VERIFIED BY READING.** M164's stage order is genuinely fail-closed:
scale/field can stop at two frames; atlas coverage can stop before converter
removal; physical controls precede the sealed score; failed gates return
`UNMEASURED`.

**INFERRED.** Those properties make the design repairable rather than
fatally flawed. They do not make the current three-strip, odd/even,
not-yet-dimensioned protocol safe to shoot.

## 11. Final ruling

**INFERRED — `SOUND WITH REPAIRS`.** Preserve the reference-path
`TRD` architecture and the M164 staged STOP semantics. Do not authorize the
owner capture until Repairs 1–7 are frozen and executable. The two
load-bearing corrections are: the result is about qualified `GX`, not known
absolute `X`; and the number and placement of fixed-focus reference strips
must be measured rather than assumed to be three.

# M164 follow-up — what the transfer veto does and does not unlock for M1

Status: **DESIGN RULING; REAL-PAIR JOB PREPARED BUT NOT RUN**

> **COUNT CORRECTION / STAGED FOLLOW-UP.** Section 3.2 below correctly
> decomposes the then-current `891`-frame combined M1/M5/M9 session, but it
> incorrectly presents that bundle as the minimum M1 claim-bearing sitting.
> A standalone M1 sitting restores the `128` converter-on calibration frames
> used by the `96`-frame reference and omits `315` converter-on M5/M9
> focus/witness frames: `96 + 128 + 164 + 60 + 128 = 576` before M165.
> M165 subsequently made a held-out deterministic-pattern-map calibration
> mandatory. The conservative staged proposal adds one `32`-flat/`32`-dark
> validation block per optical state, making the conditional M1-only score
> `704` and the full path `1,602`. Those numbers remain blocked on M165's
> focus/temperature matching and manifest rules. The staged plan and complete
> waste-mode audit supersede the owner-count conclusion here; see
> `docs/research/M164-m1-staged-capture.md`.

## 0. Ruling first

**ARGUED — YES, BUT ONLY AS A NECESSARY GATE.** M164 changes M1 by making one
previously legal ambiguity rejectable: when one rendered output is explained
by the other through M164's frozen common-transfer families, the comparison is
refused before a detail statistic is read. It therefore removes pure common
blur, unsharp masking, scalar gain and registered resampling as legal ways to
win an output-to-output comparison.

It does **not** supply the positive quantity M1 needs. M164 does not measure
scene information, identify which output is closer to the subject, or
distinguish cosmetic sharpening from a truth-improving common sharpening. Its
own truth-improving USM control fired `12/12`; that is correct behavior for a
veto and proof that it cannot be the M1 score
(`docs/research/M164-transfer-veto.md`, §§8.2 and 9).

The result is therefore:

```text
M164 closes one admissibility failure mode.
M164 does not turn an output-only detail proxy into truth.
```

M1 remains `UNMEASURED`. M166's stricter bar audit also remains correct: the
scorecard currently contains no admitted statistic, population, aggregation
rule or numerical success predicate, so the bar is `UNDETERMINED`, not merely
waiting for pixels (`docs/research/M166-bar-achievability.md`, “M1 — no
admitted bar”).

## 1. The exact mechanism by which M164 helps

The withdrawn output-only instruments had two separate problems:

1. they could not distinguish scene detail from presentation; and
2. some were exactly or empirically blind to a common post-render transfer.

M164 closes only the second. It predicts `D = B - A` on held-out spatial
macrotiles from a frozen low-complexity transfer family. A common scalar is
not normalized away: for `B = gA`, the fitted signal is `(g-1)A`. The
commissioned instrument detects scalar delta `0.00018`, Gaussian blur at
sigma `0.27 px`, radius-1 USM at amount `0.0035`, resampling at `0.001 px`,
and blur-plus-gain in `72/72`, while firing on `0/144` registered legitimate
differences and `0/96` fresh-noise optical improvements
(`docs/research/M164-transfer-veto.md`, §§3, 5, 7 and 8).

That is useful in two places:

- **Protocol enforcement.** A participant may not apply unilateral output
  sharpening, denoising/blur, deconvolution or resizing and then ask an
  output-only M1 statistic to compare the result. If the final pair is
  consistent with a registered common transfer, the question is declared
  unanswerable.
- **Defense in depth beside truth.** A future truth-referenced M1 can use M164
  as an output-pair refusal before its positive truth coordinate is read.

The limitation is equally important. `NOT_VETOED` excludes only the two
registered M164 families. Internal sharpening mixed with spatially varying
merge differences may not look like one common filter. M164 is therefore not
a structural sharpening proof for an otherwise unsafe statistic.

## 2. What is still required beyond M164

An admissible M1 still needs all of the following.

### 2.1 An external physical reference

The positive coordinate must consume information not present in either
rendered output: a separately exposed, higher-subject-sampling image of the
same physical patch. The current best design is a fixed-focus near/middle/far
reference atlas, not another stacker output. A dense merge from the same
capture is circular because it can share blur, registration error,
hallucination and tone with the candidate
(`docs/proposals/2026-09-truth-referenced-detail.md`, §§0 and 3).

The reference is a qualified proxy, not perfect ground truth. It is admitted
only if its measured subject sampling is at least `2.0x`, its object-space
transfer is stronger in every registered cell, its split halves agree, and
its calibration/noise lineage is independent.

### 2.2 A positive information coordinate and non-compensating witnesses

The surviving architecture is not one scalar. It combines:

```text
J_TR + truth-relative transfer T_TR/F_TR + U_TR
```

- `J_TR` is truth-referenced recoverable information. Its realized-sample
  covariance construction is exactly invariant to a nonsingular linear
  transform of the complete output feature vector.
- the truth-relative transfer coordinate (`T_TR` in M135; expanded as the
  `F_TR` vector in the later proposal) reports attenuation, overshoot, phase
  and residual departures from the independent reference. It may veto or
  worsen a result; it may never create a win.
- `U_TR` exposes repeatable output structure absent from the reference.
- A matched featureless sentinel must pass on every run.

The coordinates cannot be averaged into a weighted score. M135's synthetic
battery commissioned this architecture, including the identity, pre-noise
blur, genuine optical improvement, USM, post-render blur, added noise,
hallucination, clipping, quantization, flat and missing-lineage arms
(`docs/research/M135-detail-instrument.md`, §§4.4–4.7 and 7–8).

M164 does not replace `F_TR`. M164 compares outputs to each other; `F_TR`
compares each output's transfer to independent physical truth. The latter is
what distinguishes a sharper optical capture made before fresh sensor noise
from a post-render sharpening of already noisy pixels.

### 2.3 Independent tone, geometry and lineage

The instrument also needs:

- the already successful independent 33-step PCHIP tone witness;
- native-output geometry, with only the oversampled reference resampled;
- two complete scored-output repeats and two independently calibrated
  reference halves;
- disjoint flat/dark masters across optical state and A/B lineage;
- a different sensor footprint after the physical scale change;
- blank-residual correlation `<=0.05`;
- at least 64 guarded, nonduplicated, nonperiodic sites with adequate power
  in every licensed frequency/orientation cell; and
- typed refusal on missing provenance, clipping, low bit depth, failed rank,
  conditioning, geometry, transfer or flat-null gates.

These are acquisition facts. No statistic computed from two final TIFFs can
reconstruct them after the fact
(`docs/research/M135-detail-instrument.md`, §§4.7, 6.1–6.4 and 8).

### 2.4 A real M1 success bar

The registrar must still freeze, before holdout rendering:

- the exact site and band population;
- the reduction across sites, repeats, bands and comparators;
- a strictly positive information margin `delta_J`;
- noninferiority allowances `delta_F_j` for every non-compensating transfer
  component;
- uncertainty and multiplicity treatment; and
- the status rule for mixed or refused bands.

The current truth-reference proposal gives the correct shape:

```text
lower_95(Delta J) > delta_J
AND
upper_95(Delta F_j) <= delta_F_j for every component j
AND
every provenance, geometry, rank, tone, clipping and reference gate passes.
```

It intentionally leaves the numerical margins for preregistered physical
power work. M135's `0.98` values are Phase-1 preservation gates, not an M1
superiority bar; its `1.02` superiority value is explicitly an unratified
planning proposal (`docs/proposals/2026-09-truth-referenced-detail.md`, §5;
`docs/research/M135-detail-instrument.md`, §§6.3 and 8.1).

## 3. Minimum owner capture

### 3.1 The live two-frame ask is only a preflight

The two frames and five minutes do **not** supply M1 truth. They are:

1. one flat calibration-slide RAW with the converter fitted at maximum
   reproduction; and
2. one RAW of the physically unmoved slide with the converter removed near
   `1.32x`.

They field-commission M147's sampling-ratio gate and decide whether
`LCB95(M_reference/M_scored) >= 2.0`. They contain neither a same-subject
reference atlas nor independent A/B scored repeats, and cannot produce an M1
value (`docs/research/M147-preflight.md`, §§0, 4 and 6).

### 3.2 Minimum claim-bearing data versus minimum defensible program

**ARGUED — CORRECTED.** The registered **891-frame uninterrupted scored
session** is the combined M1/M5/M9 design. Within it, M1's inverted block adds
**448 frames**:

- `96` converter-on fixed-focus reference frames: near, middle and far,
  `32` each;
- `164` converter-off scored focus frames: independent `sw4-A/B` (`2 x 55`)
  and `sw10-A/B` (`2 x 27`);
- `60` converter-off reset/start/end fixed-focus witnesses; and
- `128` converter-off calibration frames: flat A/B and dark A/B,
  `32` each.

The 448-frame block replaces a superseded block inside the wider session and
relies on the bundle's existing `128` converter-on calibration frames. It is
therefore not a standalone 448-frame score session. A standalone M1 sitting
needs those `128` frames but not the bundle's `315` converter-on M5/M9
focus/witness frames:

```text
96 reference + 128 reference calibration
+ 164 TC0 focus + 60 TC0 witnesses + 128 TC0 calibration
= 576 M1-only scored frames.
```

This unbundles other axes; it does not remove an M1 role. M165 then requires
held-out validation of the pattern map. The conservative staged proposal adds
one `32`-flat/`32`-dark V block per optical state, raising the conditional
standalone score to `704`
(`docs/proposals/2026-09-truth-referenced-detail.md`, §0).

**ARGUED.** The minimum **defensible owner program before admission** is
larger. Under the provisional assumption that one focus-valid pattern-map
class covers each optical state, the M1-only route is **896 non-holdout
rehearsal frames plus 704 sealed scored frames = 1,600 frames**, after the
two-frame preflight. Including that preflight, the conditional floor is
**1,602 registered/setup exposures**. Preserving the combined M1/M5/M9 score
instead gives a conditional `1,917`. Each extra flat-focus class adds `96`
frames; each extra dark-temperature class adds `96`, and splitting both adds
`192` to the affected sitting. The rehearsal must be read to bind the physical
blur and genuine-improvement controls, reference transfer, target eligibility,
pattern-map residual, registration, calibration independence and physical
allowances. It cannot share a subject/session, reference or calibration with
the score. Combining rehearsal and score would burn the holdout before the
physical instrument was frozen
(`docs/research/M135-detail-instrument.md`, §§6.4 and 8;
`docs/research/M164-m1-staged-capture.md`).

### 3.3 Subject and conditions

For the full M1 claim without weakening its meaning, use separate
development and sealed-score instances of a rigid, coplanar,
concealed-seed random-code target with:

- at least 64 unique guarded coded sites spanning all 16 registered
  frequency/orientation cells;
- matched featureless sentinels;
- four or more input-only fiducials;
- a coplanar 33-level neutral tone strip; and
- no repeated/public pattern available to a renderer.

The `$0` rehearsal may first test a one-use stochastic material already on
hand. It is not assumed to qualify; failure of nonduplication, carrier power,
flat sentinels or transfer requires the coded artifact rather than relaxed
gates.

Use the existing Sony A7C II, FE 100 mm macro and Viltrox 2x:

- converter on, measured maximum reproduction, fixed-focus near/mid/far
  reference bursts;
- then converter off without moving the target, axial reframe only;
- scored state target `1.32x`, hard maximum `1.33x`, marked `f/5.6`;
- ISO 100, 1 s, fixed white balance and lighting, 14-bit lossless-compressed
  RAW, EFCS, IBIS off and OSS off;
- independent complete `sw4` and `sw10` A/B brackets;
- independent flat/dark lineages for reference halves, scored A/B, rehearsal
  and score; and
- at least 64 common sites surviving focus, guard, clipping, registration and
  reference-power gates.

Three reference focus positions are necessary because the subject is tilted
and the higher-magnification depth of field cannot truthfully cover the whole
plane in one exposure. Two full repeats at both step widths are required by
the existing scorecard contract; splitting one sweep does not create an
independent capture.

## 4. Audit of withdrawn candidates

No withdrawn output-only candidate becomes admissible by placing M164 in
front of it.

| candidate | ruling after M164 | reason |
|---|---|---|
| `f_licensed` | **NOT REVIVABLE** | It is pinned at `0.15 cyc/px` for base, physical blur, genuine improvement and USM. A veto cannot give a blind statistic a positive detail coordinate. |
| native `S_25` + PCHIP + M164 | **NOT REVIVABLE** | PCHIP can remove the tone defect and M164 can reject a pure registered postfilter, but native `S_25` still lacks quantitative calibration, moves over `0.004972x–10.381863x` under noise and `1.42205/1.18548/1/0.65802` across angle, and its expanded USM arm is `1.028294x`. A restricted non-fire is not structural sharpening safety for a merge-plus-filter difference. |
| tone-hardened `S_25` | **NOT REVIVABLE** | PCHIP tone movement is at most `0.0141%`, but the repaired statistic reverses physical optics: blur `1.268326x`, genuine improvement `0.923468x`, with noise also in the wrong direction. M164 cannot repair a positive coordinate whose physical sign is wrong. |
| licensed `Q25` | **NOT REVIVABLE** | USM scores `5.560744x`, genuine improvement has the wrong sign, and noise moves it about `17x`. |

The measured candidate values are from
`docs/research/M-PHASE0-SLANTEDGE.md`, “Survivor follow-up” and “S25
hardening build.” The independent PCHIP witness is reusable; the candidates
are not.

## 5. Recommended route

**PROPOSAL.** Admit no revived `S_25`, `f_licensed` or `Q25` bar. Finish the
already commissioned M135 architecture:

```text
M164 output-pair admissibility gate
AND
truth-referenced J_TR information superiority
AND
noninferior F_TR transfer components in every licensed cell
AND
U_TR / matched-flat / lineage / tone / geometry gates
```

Freeze the exact physical population and numerical `delta_J`/`delta_F`
decision before the sealed session. Commission the complete physical path on
the separate 768-frame rehearsal. Only then bind the instrument and read the
891-frame holdout.

This route does not relax M1. It makes explicit that “more recoverable scene
information” is the positive claim, while output transfer, unexplained
structure and common postfiltering are non-compensating vetoes.

## 6. Prepared historical real-pair job

**NOT RUN.** The quiet-host release has not been given.

The prepared runner is
`experiments/M164-transfer-veto/realpair.py`. It is closed over exactly:

- `cb`: DELIVER-V6 versus the focus-stack fork — `BURNED-OK`;
- `113`: DELIVER-V6 versus Zerene PMax0 — `BURNED-OK`; and
- `113-sharp`: DELIVER-V6 versus Zerene PMax40 — `BURNED-OK`.

It contains no `119MSDCF` pair. The absent SHIP-V2 pairs remain permanently
unadjudicable.

The runner:

- forces one thread and is expected to take the previously reported
  `5–10 minutes`;
- writes `RUNNING` before input work and atomically replaces it with `PASS`
  or `FAIL`;
- exits nonzero on a missing file, byte/hash/ICC mismatch, unexpected TIFF
  layout, invalid geometry, inadequate site coverage, failed adapter control
  or invalid M164 result;
- copies both `D:\edited\macro` comparators into the lane-owned staging
  directory before TIFF decoding;
- verifies the exact archived hashes;
- inverts the DELIVER-V6 render using its embedded tone metadata and maps
  sRGB, Adobe RGB and Rec.2020 values to common linear luminance;
- estimates a robust comparator-to-strehl similarity transform, refines local
  translation, and maps only the strehl arm into each comparator-native
  512-pixel site;
- repeats each direction under bilinear and cubic geometry adapters;
- requires at least eight of twelve fixed sites; and
- calls a pair inadmissible only if every eligible site fires in one
  direction under both adapters. Mixed sites are reported as
  `MIXED_SITE_EVIDENCE`, not rounded into a veto.

The per-pair artifact contains fire counts and min/median/max
`difference_rms_lsb`, `kernel_effect_rms_lsb`, `residual_rms_lsb`,
`residual_over_difference`, `tile_q90` and `fold_disagreement`, in both
directions and for both adapters. Each pair also runs identity, movable-null,
blur, USM and resampling controls after preprocessing. Adapter-to-adapter
fires are recorded as sensitivity diagnostics and cannot by themselves veto
the real pair.

**VERIFIED WITHOUT REAL-PAIR PIXELS.** The synthetic runner self-test passes.
It checks the exact three-pair whitelist, the pinned M164 source hash, identity,
movable-null, blur, sharpening, resampling and registration-sign paths. This
does not predict any real-pair result.

Prepared single command:

```powershell
$env:OPENBLAS_NUM_THREADS='1'; $env:OMP_NUM_THREADS='1'; $env:MKL_NUM_THREADS='1'; $env:PYTHONDONTWRITEBYTECODE='1'; & 'C:\Users\chris\AppData\Local\Programs\Python\Python312\python.exe' -B 'C:\dev\blog\death-of-software\projects\strehl\experiments\M164-transfer-veto\realpair.py' --output 'C:\dev\blog\death-of-software\projects\strehl\experiments\M164-transfer-veto\out\realpair-verdict.json' --stage-dir 'C:\dev\blog\death-of-software\projects\strehl\experiments\M164-transfer-veto\out\realpair-stage'
```

No real pair, quality metric or holdout was opened by this follow-up.

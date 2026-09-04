# Truth-referenced detail: capture decision and conditional instrument

Status: Proposal

Decision: **CAPTURE REQUIRED; CONDITIONAL GO for commissioning; NO-GO for any
score or SOTA claim**

Owner: lane-TRUTH

Scope: M1 detail only. This document designs an instrument and its capture. It
does not take a claim-bearing reading, revise the scorecard, or open the sealed
holdout.

**MEASURED.** **Revision 1:** D8/M115's primary numbers reproduce, and the
later transfer audit and current scorecard reject the same-capture product
form (`docs/research/M-PHASE0-SPLIT.md:73-103,252-280`;
`docs/proposals/2026-09-sota-scorecard.md:1119-1124`).

**ARGUED.** D8 is adjudicated as the incumbent, but its blur response and
sharpening invariance belong to different statistics. The capture decision is
unchanged (`docs/proposals/2026-08-sota-path.md:1694-1746`).

**MEASURED.** **Revision 2:** the commissioned M8 source-hull checker reports
Strehl at M8-R `1.030569%` and M8-O `1.326144%`, with an exact zero identity
arm (`docs/research/M8-overshoot.md:21-62`).

**DERIVED.** M8 does not supply the missing detail coordinate. Moderate
sharpening can remain inside a broad all-frame hull, and projection back into
that hull extends the attack to stronger sharpening. M8 remains strong
one-way artifact evidence; the capture decision is unchanged.

**MEASURED.** **Revision 3:** the owner's converter is a communicating 2x
Viltrox, not Sony's incompatible SEL20TC. The composed rig was measured at
maximum reproduction `2.7198 +/- 0.0051` with a widened interval
`[2.7015, 2.7381]` (`docs/research/SYNTHESIS.md:1705-1711`;
`docs/research/M84b-ruler-metrology.md:48-53,271-280,550-556`).

**DERIVED.** Main 1.30x gives at least
`2.7015 / 1.30 = 2.078x` reference/main sampling at the measured maximum.
Nominal 1.4x would give only `1.929x` at the conservative reference bound.

**ARGUED.** Pin the main sweep's near-focus reset to **1.30x effective
reproduction with that same converter installed**. The 160-frame counts and
block structure are unchanged.

## 0. Decision first

**ARGUED.** Yes, a truth-referenced M1 instrument requires additional physical
data in the incoming session. The current main sweeps, fixed-focus witnesses,
flats and darks do not contain an independently sampled image of the same
nonperiodic subject. Without one, every available candidate must infer detail
from a degraded output, another realization of the same degradation, or a
merge made by the system under test. Those are exactly the families that have
failed or remain uncommissioned.

**MEASURED.** M115 really measured
`0.9938-0.9974` planted-blur recovery, at most `0.54%` movement under
information-free output filters, an `8.2514x` naive-gradient response, and an
exact power identity (`docs/research/M115-deconv-headroom.md:82-107,129-137`).
The first result is the response of absolute `P_sig`; the second is the
invariance of normalized `R_SNR`. They are not one statistic with both
properties. The current scorecard explicitly drops the same-capture split
channel, and the later transfer audit reproduced the numbers before killing
the product form
(`docs/proposals/2026-09-sota-scorecard.md:1119-1124`;
`docs/research/M-PHASE0-SPLIT.md:1-16,73-103,252-280`).

**ARGUED.** D8 therefore does not remove the external-reference requirement.
Its confirmed numbers do not supply one statistic that is both
sharpening-safe and blur-sensitive, and its same-capture product status is
already closed.

**DERIVED.** M8 does not remove the requirement either. The scorecard defines
M8 as source-support evidence rather than a resolution statistic and names
final clamping as a defeat
(`docs/proposals/2026-09-sota-scorecard.md:833-879`). A clean hull census
therefore cannot certify that a rise in a separate detail proxy came from
resolved scene structure.

**ARGUED.** The main capture setting is now part of the truth-reference
contract: set the **near-focus reset to 1.30x effective reproduction**,
measured from pixels per known grid period, with the existing 2x Viltrox left
installed. Do not remove the converter for the main sweep. The reference uses
the same optical train at its maximum available reproduction, targeted at
`>=2.70x`. If the measured reference/main ratio is below `2.0x`, the reference
is conditional or refused under section 0.1 rather than relabelled after the
fact.

**ARGUED.** Add **160 frames** after all main sweeps and their fixed-focus
witnesses:

| Block | Frames | Operator instruction |
|---|---:|---|
| `TR-REF-NEAR` | 32 | Same patch, maximum available reproduction (`>=2.70x` target), fixed-focus intersection in the near third |
| `TR-REF-MID` | 32 | Same patch and framing, fixed-focus intersection in the middle third |
| `TR-REF-FAR` | 32 | Same patch and framing, fixed-focus intersection in the far third |
| `TR-FLAT-C` | 32 | Reference-only flat, third diffuser position/orientation |
| `TR-DARK-C` | 32 | Reference-only dark, matching the fixed reference exposure |
| **Total added** | **160** | 96 subject frames plus 64 calibration frames |

**MEASURED.** The FE 100 mm F2.8 Macro GM reaches 1.4x natively and a true 2x
converter gives the nominal 2.8x ceiling. The owner's Viltrox communicates
`200 mm`, `f/5.6`, and `MaxApertureValue = 5.6`
(`docs/research/F-camera-lens-optics.md:12-13`;
`docs/research/SYNTHESIS.md:1705`;
`docs/capture-requests/2026-09-319-frame-session.md:223-229`).

**DERIVED.** The current request's f/5.6 is therefore the combined path wide
open and must not be doubled again as f/11.

**ARGUED.** The subject blocks must be shot as follows:

1. Finish every main sweep and fixed-focus witness first. Do not touch the
   target, target tilt, lighting, polarizers, camera roll, or camera yaw.
2. Only then make the axial camera move needed to reach the rig's maximum
   available reproduction, targeted at `>=2.70x`, and reframe the **same
   nonperiodic patch**. Keep at least four surrounding grid or fiducial
   intersections in the frame. Fill as much of the sensor as possible with
   the patch rather than with the periodic grid.
3. Turn focus bracketing off. Set one manual focus position for the near third,
   approach it from the same focus direction every time, lock it, and take 32
   lossless-compressed 14-bit RAWs without moving focus. Repeat independently
   for the middle and far thirds. Each setting needs only a narrow in-focus
   strip through its named third; gaps between strips are expected and are not
   scored. These are three fixed-focus bursts, not one bracket and not an
   interleaved protocol.
4. Use ISO 100, f/5.6, fixed white balance, EFCS, IBIS off, OSS off, the same
   warmed flicker-free light and the same crossed-polarizer state as the main
   blocks. Begin with 1 s. If the axial move changes transmission enough to
   make that exposure unsuitable, select one replacement shutter time before
   the first reference burst, use it unchanged for all 96 reference subject
   frames, and use the same time for `TR-FLAT-C` and `TR-DARK-C`. Do not
   auto-expose the three focus positions separately.
5. After the 96 subject frames, shoot 32 reference-only flats with a diffuser
   position or orientation not used by flat A or B, then 32 warmed darks at the
   reference exposure. Discard the first two darks operationally in the same
   way as the main calibration groups, but retain every RAW in the manifest.
6. Record the reference focus positions, shutter time, lens-reported focus
   state if available, camera-to-stage move, and four fiducial coordinates.
   Do not report "2.8x" from the lens name alone: the analysis must measure the
   actual reference/main subject-sampling ratio from pixels per common grid
   period. Absolute grid pitch is not needed for that ratio.

**MEASURED.** The main request already requires a coplanar nonperiodic patch
beside the grid because a periodic target can carry its own answer
(`docs/capture-requests/2026-09-319-frame-session.md:71-101`). It also requires
IBIS and OSS off, ISO 100, 1 s, f/5.6, fixed white balance and 14-bit
lossless-compressed RAW (`docs/capture-requests/2026-09-319-frame-session.md:220-237`).

**MEASURED.** The A7C II focus bracket drives a complete ladder rather than
allowing two exposures to be interleaved at one focus node. The existing
request therefore added separate fixed-focus witnesses around the independent
sweeps (`docs/STATUS.md:1946-1973`;
`docs/capture-requests/2026-09-319-frame-session.md:138-173`). The reference
protocol above does not require an impossible interleave.

**ARGUED.** Thirty-two frames per focus position are required because they
provide two independently calibrated 16-frame reference halves. The halves
are needed to measure reference noise, shared calibration leakage and transfer
uncertainty without asking the output being scored to validate its own truth.
Three focus positions are required because the target is tilted and depth of
field is smaller at the higher reproduction ratio. A scored site may come from
one fixed-focus average only; no site may cross a seam and no focus-stacking
algorithm may construct the reference.

### 0.1 Reference eligibility and the fallback decision

**ARGUED.** The desired reference/main subject-sampling ratio is at least
`2.0x`. A ratio at or below `1.25x` is an automatic no-go. A ratio between
`1.25x` and `2.0x` is only conditionally usable if a later registrar freezes
and the commissioning battery clears reference-MTF, split-reference SNR and
resampling-uncertainty bars before holdout rendering.

**DERIVED.** At the measured conservative reference bound, main 1.30x gives
`2.078x`; main 1.40x gives `1.929x`. The main target is therefore 1.30x, not
the lens's nominal native maximum.

**ARGUED.** This is a deliberate trade: it reduces the spatial stress on the
other axes, but it remains above unity reproduction and preserves the only
independently sampled M1 route available in this session.

**ARGUED.** Those are proposed capture-eligibility thresholds, not active M1
score bars. The scorecard registrar must ratify or replace them before the
holdout is opened. Sampling ratio alone is not enough: the reference optic
must also show superior object-space transfer in every licensed band. A
higher pixel count with worse reference defocus or aberration is not truth.

**DERIVED.** At the measured maximum and reported f/5.6 wide open, the
composed path has
`N_eff = 13.5-17.2`, image-space diffraction cutoff `106-135 cy/mm`, and
nonzero MTF through the sensor's `97.7 cy/mm` Nyquist
(`docs/research/M84b-ruler-metrology.md:48-53`;
`docs/research/M85-output-correctness.md:366-378`).

**DERIVED.** The two-stop converter loss is already present in the reported
f/5.6; applying another factor of two would double-count it.

**DERIVED.** Under the explicit same-pupil approximation, using the same
converter at 1.30x and 2.7198x gives a reference/main object-space
diffraction-cutoff ratio of `1.35-1.45x` over the measured
`p = 1.31-1.94` interval:

```text
f_c,object = m / (lambda N (1 + m/p)).
```

The reference therefore has a predicted diffraction-transfer advantage, not
a 2.0x optical-resolution advantage. The `2.0x` figure is sampling.

**DERIVED.** Holding object-space frequency fixed at the structure represented
by the top licensed main-image frequency, `0.25 cyc/main px`, the same
circular-aperture model predicts reference/main diffraction-MTF
`1.143-1.155x` there and a strict reference advantage at every positive lower
frequency (`docs/proposals/2026-09-sota-scorecard.md:103-106`). The model and
its MTF equation are independently recorded at
`docs/research/M85-output-correctness.md:366-378`. This is still a
diffraction-only prediction.

**ARGUED.** Converter aberrations and the change in pupil behaviour with
focus remain unmeasured. Keeping the same Viltrox installed in both captures
removes the bare-lens-versus-converter substitution but does not prove equal
aberrations. The reference remains a qualified proxy and must pass the frozen
reference-transfer gate after capture. Failure leaves M1 `UNMEASURED`; it
does not retroactively make the 160 frames claim-bearing.

**ARGUED.** If the main setup is already at the rig's maximum available
reproduction, this rig cannot create a higher-sampling truth reference. The
session then needs one of these replacements:

1. a different optical path that gives at least 2x more subject pixels per
   millimetre while keeping the same patch and fiducials; or
2. a traceable, nonperiodic chrome-on-glass or photomask target with a native
   design map, features spanning the licensed main-sensor band, and at least
   256 independent guarded cells, captured with the same A/B repeat,
   fixed-focus and calibration discipline.

**ARGUED.** The existing periodic grid is not that replacement. It is useful
for geometry and scale, but it is predictable. The current capture request
withdrew a certified target under the previous relative-only M1 design
(`docs/capture-requests/2026-09-319-frame-session.md:71-84`). This proposal
changes the premise: if no oversampled same-subject reference is available,
known physical truth becomes necessary.

**ARGUED.** If neither replacement can be shot, the honest result is:
**no admissible truth-referenced detail reading can be taken from this
session**. Preserve the main session for the other axes, but leave M1
`UNMEASURED`.

## 1. Verified starting point

**MEASURED.** The scorecard remains `0/12 MEASURED`; M1 has neither an admitted
statistic nor a numeric bar and blocks several quality claims
(`docs/proposals/2026-09-sota-scorecard.md:473-505,544-577`).

**MEASURED.** The six candidates in the original brief, plus the already
prescribed D8 incumbent, do not supply the missing instrument:

| Candidate | Deciding observation | Result |
|---|---|---|
| `Q25` slant-edge | USM/base `5.560744x`; genuine sigma-1.20 improvement `0.977981x` | Rewards fake sharpening and gives real improvement the wrong sign |
| Three slanted-edge implementations | approximately `+9.9%` after USM | Presentation-sharpness diagnostics only |
| native `S_25` | USM/base `1.028294x` after the 64-site expansion | Outside the unchanged 1% arm |
| candidate 1 | USM/base `1.095732x`, UCB95 `1.129895` | Bounded finite reader rewards accessibility |
| FRC | exact common-filter cancellation | Immune to USM and blind to blur |
| candidate 2 | not run after the ordered FRC stop | Uncommissioned, not empirically dead |
| D8 / M115 split stack | `P_sig` recovers blur; `R_SNR` resists output filters | The response and invariance are in different channels; same-capture product form later killed |

**MEASURED.** The slanted-edge values and sign reversals are recorded in
`docs/research/M-PHASE0-SLANTEDGE.md:202-212,251-278`. Candidate 1's finite
128-moment, ridge-logistic estimator returned `1.095732x` under unclipped USM
even though the population estimand obeys data processing
(`docs/research/M-CAND1.md:38-55`). FRC's exact finite-sample cancellation and
its blur blindness are derived and demonstrated in
`docs/research/M-FRC-VIABILITY.md:215-285`.

**MEASURED.** Candidate 2 is a full-rank, unregularized, full-covariance
Hotelling construction with an ordered arm sequence and exact congruence
conditions (`experiments/M-CAND2/PREREGISTRATION.md:21-94`). It is
uncommissioned because the previous lane stopped when FRC failed, and its
registered clipping arm had no rail hits
(`docs/research/M-CAND2.md:20-45`). This proposal reuses candidate 2's exact
linear-equivariance lesson; it does not present the same algebra as an
independent discovery.

**MEASURED.** Earlier internal truth-reference work is also a warning, not a
free pass. A truth-referenced `0.30-0.40` wedge preferred Hamilton-Adams by
9.7%, while later real-capture evidence found no useful detail and additional
maze artifacts (`docs/research/BUILD-SHARP.md:3945-3955`). M57 likewise found
that a ground-truth oracle FSC at one frequency remained blind to a common
linear filter (`docs/research/M57-detail-metric-from-first-principles.md:98-125`).

### 1.1 D8 incumbent audit

**MEASURED.** The governing proposal describes D8 as two interleaved,
disjoint half-stack renders, each re-deriving its own data-dependent weights,
and cites M115 as its commissioned basis
(`docs/proposals/2026-08-sota-path.md:1694-1746`). The primary M115 source
supports the quoted numbers:

| D8 statement | Primary M115 result | Adjudication |
|---|---|---|
| Planted blur recovered at `0.9938-0.9974` | `P_sig` fell monotonically under sigma `0.5-2.0`; eight log-attenuation recovery ratios were in that range | **CONFIRMED**, for absolute `P_sig` (`docs/research/M115-deconv-headroom.md:82-95`) |
| Gain/filter invariance to `0.54%` | Normalized `R_SNR` ratios were `1.0000`, `0.9986`, `0.9980`, `0.9946` | **CONFIRMED**, for `R_SNR` (`docs/research/M115-deconv-headroom.md:96-107`) |
| Naive metric moved `8.25x` | The inverse-taper arm moved naive gradient energy `8.2514x` | **CONFIRMED** (`docs/research/M115-deconv-headroom.md:96-107`) |
| `(P(A)+P(B))/2 = P_sig + P_noise` | Reported as `1.0000` on every arm and both stacks | **CONFIRMED**, but algebraic bookkeeping rather than an independent validity control (`docs/research/M115-deconv-headroom.md:129-137`; `docs/research/M-PHASE0-SPLIT.md:83-91`) |

**MEASURED.** The blur and filter arms are also different interventions. C2
Fourier-blurs every already captured frame in the cube, including its recorded
sensor noise, before the split render. C3 applies the same frequency gain to
both completed half outputs
(`experiments/M115-deconv-headroom/src/s03_instrument.py:163-190,208-242`;
`experiments/M115-deconv-headroom/src/m115lib.py:477-493`).

**DERIVED.** C2 is therefore a calibration of the absolute cross-power channel
under a common post-acquisition blur. It is not a genuine
optical-improvement arm in which the optics change before new photon/read
noise is drawn.

**MEASURED.** For half outputs `A` and `B`, M115 defines
(`docs/research/M115-deconv-headroom.md:47-60`;
`experiments/M115-deconv-headroom/src/m115lib.py:440-457`):

```text
P_sig   = Re <A conj(B)>
P_noise = P(A - B) / 2
SNR     = P_sig / P_noise.
```

**DERIVED.** At one Fourier mode `k`, under a common linear filter `H`,

```text
P_sig^H(k)   = |H(k)|^2 P_sig(k)
P_noise^H(k) = |H(k)|^2 P_noise(k)
SNR^H(k)     = SNR(k).
```

**DERIVED.** The suspected mechanism is correct: the normalization protects
`R_SNR` from post-sharpening because signal and noise scale together at each
frequency. For M115's finite radial bin `b`, however,

```text
P_sig^H(b)   = sum_k in b w_k |H(k)|^2 P_sig(k)
P_noise^H(b) = sum_k in b w_k |H(k)|^2 P_noise(k).
```

**DERIVED.** The ratio is exactly invariant for a flat gain and approximately
invariant when `H` and the per-mode SNR vary little inside the bin. Otherwise
it can move because the filter reweights modes and because the Hann window
and finite binning are not an exact per-mode quotient. M115's `0.54%` is that
measured finite implementation, not an exact theorem for every aggregate
(`experiments/M115-deconv-headroom/src/m115lib.py:151-200`;
`experiments/M115-deconv-headroom/src/s03_instrument.py:208-242`). This
qualification does not rescue the detail claim: `R_SNR` has no guaranteed
ordering under common blur. Its residual can have either sign according to
the pre-existing SNR spectrum, rather than reporting the absolute transfer
loss. Conversely, unnormalized `P_sig` recovers that transfer but scales up
under the same USM or gain. Reading C2 and C3 together does not create a
scalar that owns both properties; it exposes the boundary between the two
channels.

**DERIVED.** The power identity has no additional discriminatory content:

```text
P(A - B) / 2
  = (P(A) + P(B)) / 2 - Re <A conj(B)>,
```

**DERIVED.** Substituting the definitions therefore yields equality
identically. It can catch an implementation arithmetic error, but it cannot
detect a wrong latent, common-mode structure, a gameable tuner or a false
interpretation.

**ARGUED.** A non-compensating pair `(R_SNR, P_sig)` would be stronger than
D8's scalar tuning objective: `R_SNR` could be the sole promotion gate while
`P_sig` could only veto or demote, never create a win. Post-USM `P_sig` alone
would then earn nothing, while post-blur loss of `P_sig` could make an arm
worse. It would still not be an admissible M1 instrument. Any deterministic
structure common to both halves but absent from the scene - fixed pattern,
registration residue or algorithmic hallucination - enters `P_sig` as if it
were truth and can also raise `R_SNR`. Without an independent reference, the
pair cannot tell repeatable scene structure from a repeatable mistake.

### 1.2 Independence, confounds and the density floor

**ARGUED.** Alternate **frames** are separate exposures. Their photon and read
noise are temporally independent, and they must not be conflated with a
same-frame pixel or CFA split. This document calls D8's construction a
**same-capture interleaved frame split**. Its rejection is not based on shared
shot/read noise
(`experiments/M115-deconv-headroom/src/m115lib.py:407-438`).

**MEASURED.** M115 itself states the remaining direction of failure:
`P_sig` is fooled upward by anything common to both halves that is not scene,
especially fixed-pattern non-uniformity; unequal half latents bias it downward
(`experiments/M115-deconv-headroom/src/m115lib.py:440-453`). Its flat null
failed the registered `0.25` bar on two arms. The reported fixed-pattern floor
was `0.073%` and `0.050%` after scaling from the flat corpus to two detail
ROIs, not a universal absence proof
(`docs/research/M115-deconv-headroom.md:109-137`).

**MEASURED.** Quantization is another common-mode path. M115 measured
cross-half rounding-error correlation `r=+0.5109`; matched 8-bit narrowing
raised `P_noise` `3.937x` while independent dither of identical power raised it
`63.311x`, a `16x` under-report
(`docs/research/M115-deconv-headroom.md:318-337`). No D8-derived measurement
may see quantized intermediates.

**MEASURED.** The later D8 audit loaded M115's historical source blobs and
reproduced blur recovery `0.9938215871-0.9973982082`, maximum filter movement
`0.537785%`, and identity
`0.999999999987-1.000000000000`. It still returned the historical split-null
failure, a common-mode adversary at FRC `0.972099`, no plant that transferred
to a data-dependent tuner, and a final `KILL - STOP/REMOVE RUST`
(`docs/research/M-PHASE0-SPLIT.md:73-103,252-280`). The current scorecard
therefore uses repeated exposures only and requires an independent repeated
bracket, sensor-pattern subtraction, a non-degenerate partition and a
transferring tuner plant before D8 can reopen
(`docs/proposals/2026-09-sota-scorecard.md:1119-1124`).

**ARGUED.** The density floor is not a universal frame count. M27 measured one
105-frame `coffee-bean` bracket: its 53-frame decimation had `0.01%`
under-resolved pixels, while 27 frames had `37.46%` and 14 had `69.06%`.
M27 explicitly says this was one unaligned subject and that no genuinely
under-sampled real stack was tested
(`docs/research/M27-coverage-gap-measured.md:78-129,156-176`). Applied only as
a warning, not as a transferred bar:

| Incoming block | Odd/even halves | Effective step width | D8 status |
|---|---:|---:|---|
| `sw1`, 91 frames | 46 / 45 | 2 | **CONDITIONAL DIAGNOSTIC** only after an input-only density gate; current capture contract says never feed this reference block to a stacker |
| `sw4`, 55 frames | 28 / 27 | 8 | **NO-GO for odd/even under the current scorecard**; density is also unproven, so use the full `sw4-A` and `sw4-B` repeated brackets if testing the gold form |
| `sw10`, 27 frames | 14 / 13 | 20 | **NO-GO for odd/even under the current scorecard**; retain the full A/B pair only as the registered sparse-step stress |

**MEASURED.** Those counts follow the current request's `91/55/27` ladder,
which marks `sw1` as checker-only and says never to feed it to a stacker; `sw4`
and `sw10` each have full A/B repeats
(`docs/capture-requests/2026-09-319-frame-session.md:116-136`).

**ARGUED.** A repeated bracket is the stronger D8 form because it avoids
halving the z-density and independently re-runs the camera exposures. It does
not by itself create optical truth. Repeated exposures on one sensor still
share stable sensor structure, and a repeat-pair SNR remains invariant to a
flat common gain; per-mode normalization cancels common blur, while finite
band aggregation only reweights the existing SNR spectrum. The
independent-repeat follow-on reached the same limit: even after its geometry
controls, repeated exposures could not prove that stable sensor structure did
not inflate scene-pair FRC
(`docs/research/M-PHASE0-SPLIT2.md:145-158`).

### 1.3 D8 reopening arms

**ARGUED.** D8 is the incumbent to beat, but it is currently a killed offline
instrument. Any reopening dies unless all of these pre-results conditions are
met:

| Arm | Required result | Death |
|---|---|---|
| Historical reproduction | Reproduce M115 C2, C3 and arithmetic identity from frozen source | Any mismatch; identity success alone has no validity weight |
| Information-free USM | The complete non-compensating verdict cannot improve under the registered unclipped USM | `P_sig` or finite-bin SNR creates a win |
| Common blur | The complete verdict ranks the blurred output below its unblurred source | Normalized SNR turns blindness into a tie or `P_sig` is allowed to compensate |
| Genuine optical improvement | A separately captured optical improvement made before fresh photon/read noise scores better | C2's post-acquisition cube blur is substituted, the sign is wrong, or the verdict refuses |
| Nonlinear tone | Gamma-3 and the registered logistic transform do not raise the verdict | Either transform creates a win |
| Clipping | Registered clipping does not raise the verdict, and rail-hit counts are reported | Clipping creates a win or the rail-hit arm is impotent |
| Independent realisations | Full repeated brackets, separately calibrated, pass node and geometry gates | Odd/even is used below its density floor or failed A/B geometry is pooled |
| Common-mode adversary | Fixed pattern and deterministic A/B structure absent from an independent reference do not raise the result | Common structure scores as detail |
| Quantization | Every statistic consumes linear floating intermediates and a potent narrowing arm is refused | Difference noise under-reports the narrowing |
| Partition | A non-degenerate balanced alternate partition agrees with the registered one | A label swap is counted as a sensitivity test |
| Tuner transfer | Tuning occurs on data disjoint from the pair that grades it, and a plant changes the actual data-dependent optimum | Self-tuning leakage or a fixed common-filter surrogate passes |
| Density | Each half independently passes a frozen input-only coverage gate | Halving produces under-resolved focus peaks |

**MEASURED.** These extend rather than replace D8's original port criterion
that the Rust implementation reproduce M115's checks or die
(`docs/proposals/2026-08-sota-path.md:1741-1746`). The later audit established
that reproduction is necessary but not sufficient
(`docs/STATUS.md:156-198`).

**ARGUED.** `TRD=(J_TR,F_TR)` is designed to beat D8 at the exact missing
boundary. Its information component retains structural post-filter
protection, while its transfer and common-residual components are referenced
to a separately sampled physical image that neither half-stack nor the
algorithm produced. D8 can remain an offline diagnostic or a future M2-style
matched-contrast efficiency channel. It cannot replace independent truth for
M1.

### 1.4 M8 source-hull frontier audit

**MEASURED.** M8 is a commissioned and independent source-hull instrument.
Its checker imports no Strehl code, passed positive and negative plants, and
reported an exact `0 / 32,919,152` real copy/reference arm. Strehl nevertheless
failed at aggregate M8-R `63,191,176 / 6,131,678,976` (`1.030569%`) and M8-O
`983,648 / 74,173,536` (`1.326144%`)
(`docs/research/M8-overshoot.md:21-62`).

**MEASURED.** The two censuses answer narrower questions. M8-R checks each
pre-merge resampler result against that frame's exact local source support.
M8-O checks the final output against the broader hull over every valid frame.
The scorecard explicitly calls this "sharpening-independent source support,
not a resolution statistic" and records that a broad hull or final clamp can
hide the excursion (`docs/proposals/2026-09-sota-scorecard.md:833-879`).

**DERIVED.** The proposed frontier therefore lacks unique directions in both
senses. Post-merge sharpening need not move M8-R and can remain inside M8-O;
conversely, a pre-merge resampler excursion can move M8-R without any
sharpening. Motion on the M8 axis is neither necessary nor sufficient for the
mechanism the frontier assigns to it.

**DERIVED.** Let the final all-frame source hull at pixel `i` be
`[lo_i, hi_i]`, and let `U(y)` be any sharpened version of output `y`. The
attack

```text
z_i = min(hi_i, max(lo_i, U(y)_i))
```

**DERIVED.** This attack has zero M8-O violations by construction. It does not
undo sharpening values that already lie inside the hull, and clipping only
the excursions can retain much of the edge steepening. If `U` is applied
after merge, M8-R is unchanged; a hull-constrained merge or direct
source-value selector can also avoid a resampler excursion entirely.

**DERIVED.** A six-sample construction is sufficient to kill the proposed
frontier. Take two source observations with equal-and-opposite perturbations
around their mean:

```text
A = [0.10, 0.20, 0.40, 0.60, 0.80, 0.90]
B = [0.00, 0.15, 0.35, 0.65, 0.85, 1.00]
y = (A + B) / 2
  = [0.05, 0.175, 0.375, 0.625, 0.825, 0.95].
```

**DERIVED.** Apply strength-1 USM with the three-tap blur `[1, 2, 1] / 4` and
endpoint replication. Without any clamp, the result is

```text
u = [0.01875, 0.15625, 0.36250, 0.63750, 0.84375, 0.98125].
```

**DERIVED.** Every output sample is already inside
`[min(A_i,B_i), max(A_i,B_i)]`, so M8-O is zero while squared gradient energy
rises `1.142536x` and total variation rises `1.069444x`. Identity placement
can keep M8-R zero as well (`docs/research/M8-overshoot.md:37-43`). The
construction uses only the two same-coordinate samples; M8-O's actual
all-frame 4x4-support hull is at least as broad
(`experiments/M8-overshoot/checker.py:252-278,409-420`).

**DERIVED.** The clamp extends the attack rather than creating it. At
strength 2, project the oversharpened result back into the same hull:

```text
z_i = min(hi_i, max(lo_i, U_2(y)_i))
z   = [0.00, 0.15, 0.35, 0.65, 0.85, 1.00].
```

**DERIVED.** M8-O remains zero, while squared gradient energy rises
`1.237410x` and total variation rises `1.111111x`. This is sharpening moving
up a conventional high-frequency detail proxy at constant zero overshoot.

**ARGUED.** Clipping is therefore not a secondary caveat; it is an exact
projection attack on the proposed two-dimensional separator. More generally,
M8 constrains amplitude provenance, not spatial choice, phase or information.
A selector can choose `lo_i` or `hi_i` according to an edge or checkerboard
rule and synthesize high-frequency structure entirely from observed values.
Constrained deconvolution and monotone local-contrast operators can have the
same opening.

**ARGUED.** The frontier is **NO-GO as an M1 instrument**. An M8 failure is
strong evidence that a source-hull invariant was violated and remains useful
as an independent veto or artifact coordinate. A clean or unchanged M8 result
cannot establish absence of sharpening, cannot make any of the six dead
statistics admissible, and cannot replace independent truth. There is no
reason to re-scope lane-TRUTH away from `TRD`.

## 2. What truth-referencing does and does not solve

### 2.1 A direct fidelity scalar still fails failure mode A

**DERIVED.** Let the physical truth be `x`, the delivered image be
`y = Hx + n`, and a deterministic post-render sharpening operator be `U`.
A squared-error fidelity score compares

```text
E_base = ||Hx + n - x||^2
E_usm  = ||U(Hx + n) - x||^2.
```

There is no ordering theorem that forces `E_usm >= E_base`. If `H` is a blur
and `U` partially approximates its inverse, the bias term
`||(UH - I)x||^2` can shrink by more than the transformed-noise term grows.
The sharpening contains no new scene information, yet the fidelity estimate
improves. SSIM, PSNR, learned perceptual distances and other single-image
fidelity scores have the same logical opening unless a separate proof closes
it.

**ARGUED.** This is the truth-reference version of candidate 1's accessibility
failure. Candidate 1 made information easier for a bounded reader. A direct
fidelity score can make a blurred image easier to match to the reference. The
reference changes what "correct" means, but it does not make every finite
estimator immune to a helpful-looking inverse filter.

**MEASURED.** This repository has already seen a truth-referenced band score
select an algorithm later rejected for artifacts
(`docs/research/BUILD-SHARP.md:3945-3955`). Truth reference is therefore
necessary for the proposed transfer test, but direct fidelity alone is not
sufficient.

### 2.2 The information component escapes failure mode A only structurally

**DERIVED.** For each independent site, let `x_s` be a fixed vector of
reference-side truth features and let `y_s` be the complete linear output
pixel vector for the registered observation support. With centered sample
covariance matrices

```text
S_xx = X'X / (n - 1)
S_yy = Y'Y / (n - 1)
S_xy = X'Y / (n - 1),
```

define squared canonical correlations as the eigenvalues of

```text
K = S_xx^-1 S_xy S_yy^-1 S_yx
```

and define the truth-referenced canonical information functional

```text
J_raw = -0.5 * sum_i log2(1 - rho_i^2).
```

This is a second-order Gaussian information functional, not a claim that the
natural scene is exactly Gaussian and not a learned ideal observer.

**ARGUED.** Finite-sample canonical correlation is upward biased. The reported
information component is therefore

```text
J_TR = J_raw - median_pi J_raw(X_pi, Y),
```

using a registrar-frozen set of block-respecting truth-label permutations
`pi`, shared across algorithms and arms. The correction is not floored at
zero. Each permuted term obeys the same congruence identity as the observed
term, so null correction does not reopen the USM accessibility defect.

**DERIVED.** If a nonsingular linear post-filter `A` is applied to every output
vector, then

```text
S_yy' = A S_yy A'
S_xy' = S_xy A'
```

and therefore

```text
S_xy' S_yy'^-1 S_yx'
  = S_xy A' (A S_yy A')^-1 A S_yx
  = S_xy S_yy^-1 S_yx.
```

Every `rho_i` and `J_TR` is identical on the finite sample. A full-rank USM
cannot buy accessibility because there is no fitted classifier, selected
moment set, capacity limit, ridge penalty or arm-specific optimization to
tighten. The equality is in the computed statistic, not merely in a population
estimand.

**ARGUED.** That protection is conditional and deliberately brittle. The
instrument must refuse rather than add covariance shrinkage, diagonal loading,
PCA truncation, selected moments, outcome-chosen bands, learned embeddings or
any other non-equivariant capacity limit. For the theorem-bearing USM arm, site
extraction happens first and the arm applies an explicitly registered square,
full-rank operator to the complete `y_s` vector with a fixed boundary rule; no
post-filter crop is allowed. A crop from a globally filtered image is not
automatically covered, because outside-support pixels enter the crop. If the
rank and sample-size gates cannot be met without regularization, `J_TR` does
not exist for that run.

**ARGUED.** The battery therefore contains two USM arms. The site-local square
operator tests the exact finite-sample theorem. A second full-frame USM,
followed by the ordinary site extractor and with all scored sites far from the
frame boundary, tests the real rendering path empirically against the frozen
1% recommendation. Failure of either arm kills the candidate. The exact proof
must not be quoted as if it covered an unexamined crop or boundary mode.

**MEASURED.** Candidate 1 failed specifically because its implemented
128-moment map and finite ridge-logistic optimization were not equivariant,
whereas candidate 2 preregistered a full-rank, unregularized covariance
estimator (`docs/research/M-CAND1.md:38-55`;
`experiments/M-CAND2/PREREGISTRATION.md:21-50`). Those are the repository
precedents for the prohibition above.

### 2.3 The same proof reproduces failure mode B

**DERIVED.** The congruence proof does not know that `A` is a sharpening
filter. If a common post-render blur is nonsingular on the finite support, it
also leaves `J_TR` unchanged. Truth-referencing has not repealed the
invariance/blindness tradeoff. It has only made a second, non-normalized
comparison to truth possible.

**DERIVED.** In a scalar stationary mode with pre-noise optical transfer `h`,
truth power `S_x` and independent noise power `N`,

```text
rho^2 = |h|^2 S_x / (|h|^2 S_x + N)
J_raw = 0.5 log2(1 + |h|^2 S_x / N).
```

A genuine optical improvement made **before** sensor noise raises `|h|` and
raises the raw functional. A physical blur made before noise lowers both in
this stationary mode. The reported null-corrected statistic is admitted only
if the frozen optical-direction arms preserve those orderings. A common
post-render filter multiplies signal and already-present noise together and
cancels. This is the desired distinction between registered truth
recoverability and presentation, but it means `J_TR` alone cannot satisfy the
blur arm.

### 2.4 The required escape is a non-compensating certificate

**ARGUED.** The proposed instrument is not one scalar. It is the joint
certificate

```text
TRD = (J_TR, F_TR)
```

where higher `J_TR` means more recoverable truth-referenced information and
`F_TR` is a vector of transfer departures from the independent reference.
`F_TR` may veto or make a result worse. It may never create a detail win.

**DERIVED.** Split the reference burst into independently calibrated halves
`R_1` and `R_2`. For each frozen frequency mode `k` and output repeat `Y`,
estimate the output-to-truth transfer with a cross-fitted ratio

```text
h_hat_k =
    sum_s Y_s,k * conj((R_1,s,k + R_2,s,k) / 2)
    -------------------------------------------------
    sum_s R_1,s,k * conj(R_2,s,k).
```

The denominator removes additive reference-noise power in expectation, but
the finite-sample ratio is not itself unbiased. The final estimator must
preserve the split labels, report its ratio bias in the reference uncertainty,
and never reuse one noisy reference as both truth and noise estimate. A later
implementation audit may replace the displayed ratio with an algebraically
equivalent errors-in-variables cross-fit, but not with a self-normalized
output-only correlation.

**ARGUED.** For each preregistered band below `0.25 cyc/native output px`,
`F_TR` reports, separately and without compensation:

```text
attenuation_b = weighted departure of |h_hat| below 1
overshoot_b   = weighted departure of |h_hat| above 1
phase_b       = weighted departure of arg(h_hat) from 0
residual_b    = deterministic output energy not explained by the reference,
                after independently estimated temporal and reference noise
```

No average over these four components or over bands is claim-bearing. The
reference-power weights and bands are fixed before holdout rendering.

**DERIVED.** A frequency-wise common residual can be estimated without
rewarding temporal noise by combining the two main repeats:

```text
C_YY,k       = Re sum_s Y_A,s,k * conj(Y_B,s,k)
C_RR,k       = Re sum_s R_1,s,k * conj(R_2,s,k)
C_YR,k       = (1/4) sum_s [
                   Y_A,s,k * conj(R_1,s,k) +
                   Y_A,s,k * conj(R_2,s,k) +
                   Y_B,s,k * conj(R_1,s,k) +
                   Y_B,s,k * conj(R_2,s,k)]
residual_k   = C_YY,k - |C_YR,k|^2 / C_RR,k.
```

The estimate may be negative from finite-sample variation and is never
clipped into success. A deterministic texture shared by A and B but absent
from the independent reference raises `C_YY` without the corresponding
truth cross-term and is therefore exposed by the residual component. Any mode
whose `C_RR` is nonpositive, phase-inconsistent between reference halves, or
not significantly above its reference-noise uncertainty is refused.

**DERIVED.** Relative to truth:

| Input to the instrument | `J_TR` | `F_TR` | Joint ordering |
|---|---|---|---|
| `Y = X` | maximum for the given noise | all transfer departures zero | truth |
| `Y = B X`, nonidentity low-pass blur | invariant if blur is post-noise; lower if pre-noise | nonzero attenuation and/or phase departure | below truth |
| `Y = U X`, nonidentity USM | invariant if USM is post-noise | nonzero overshoot and/or phase departure | below truth |
| sharper optics before noise | higher | attenuation no worse and normally lower | eligible to be better |
| USM applied to an already blurred output | unchanged | may improve or worsen | never better, because `J_TR` did not rise |

**DERIVED.** The last row is important. A sharpening filter can legitimately
move a biased transfer closer to one. The design does not deny that. It denies
the filter a detail win because transfer fidelity is veto-only and the
information component is exactly unchanged. This is the precise reason the
pair escapes failure mode A without pretending that every fidelity number is
sharpening-monotone.

**DERIVED.** Blur and over-sharpening both rank below truth because
`|b_k - 1| > 0` for any nonidentity blur transfer `b_k` in a licensed mode and
`|u_k - 1| > 0` for any nonidentity sharpening transfer `u_k`. They lie on
opposite sides of one and cannot cancel because attenuation and overshoot are
reported separately. This closes failure mode B for the joint certificate,
not for `J_TR` by itself.

### 2.5 Why no claim-bearing scalar is proposed

**ARGUED.** A weighted scalar such as `J_TR - lambda F_TR` reopens the problem.
For any finite `lambda`, a sufficiently large apparent fidelity improvement
can compensate for zero registered information gain, or an information gain
can hide an arbitrarily bad artifact component. Choosing `lambda` from
observed results would also be outcome-dependent tuning.

**MEASURED.** The scorecard already forbids a composite headline score and
requires joint tuples with no compensation
(`docs/proposals/2026-09-sota-scorecard.md:108-113,1125-1130`). M57 separately
concluded that the defensible stacker claim is two-dimensional rather than a
one-number detail claim (`docs/research/M57-detail-metric-from-first-principles.md:91-94,629-637`).

**ARGUED.** The defensible conclusion is therefore narrower than "no scalar
can exist" as a theorem. It is: **no single scalar is presently justified
against both observed failure modes without adding a model-specific
compensation rule that this program has already ruled inadmissible.** The
joint certificate is the candidate that remains.

## 3. What counts as truth

### 3.1 Higher-magnification same-subject reference: recommended

**ARGUED.** The reference is a higher-subject-sampling, fixed-focus RAW atlas
of the exact patch in the scored main sweeps. It is not a rendered JPEG, not a
focus-stack output, not a deconvolution, and not a synthetic target inferred
from the candidate output.

**ARGUED.** Each 32-frame focus burst is dark/flat corrected with the
reference-only `C` masters and split 16/16. Frames may receive analytic
translation correction before a straight linear mean. Near, middle and far
sites are assigned by a geometry-frozen strip map. Each scored site must lie
fully inside one strip and one focus burst; seam pixels and feathering are
excluded. The atlas is therefore a set of fixed-focus averages, not a fourth
stacker.

**ARGUED.** "Independent" means:

- the reference has more measured subject samples per millimetre;
- it is captured in separate exposures after the main blocks;
- it is made without the algorithm under test or any comparator merger;
- its two 16-frame halves and calibration master are disjoint from main A and
  B;
- its geometry is estimated without looking at a candidate's score; and
- the algorithm under test never receives the reference.

Using the same subject and lighting is intentional and is not a dependence
defect. Sharing a flat master, output merger, selected score sites or
score-driven registration would be.

**ARGUED.** The higher-magnification image is a qualified proxy for optical
truth, not perfect ground truth. It licenses only modes for which all of these
later-frozen gates pass:

1. measured reference/main subject-sampling ratio from common fiducials;
2. split-reference signal-to-noise;
3. reference focus and transfer sufficiency at the licensed subject
   frequencies;
4. no clipping or nonlinear RAW transfer;
5. reference-half agreement;
6. geometry and resampler sensitivity; and
7. enough nonperiodic reference power in every claim-bearing band.

A failed gate produces `UNMEASURED`, not a lower score.

### 3.2 Dense focus stack: useful, but not optical truth

**ARGUED.** The 91-frame `sw1` pass may answer one narrower question:
"Does a sparse sweep converge toward the output produced by the same merger
from a denser depth sampling?" It may support depth-sampling adequacy for a
fixed algorithm and fixed rendering contract.

**ARGUED.** It may not license:

- absolute optical detail;
- a comparison between mergers;
- sharpening safety;
- artifact freedom;
- truth fidelity; or
- a SOTA claim.

The dense merge is generated by the same possibly flawed operation as the
sparse merge, so shared blur, hallucination, registration defects and tone can
agree perfectly. Treating it as truth would move the circularity one level
up, not remove it.

**MEASURED.** The incoming request contains a density ladder and independent
repeat passes, but the current scorecard explicitly says the existing burned
grid and development-only high-resolution slide may commission an instrument
and may not supply its scored value
(`docs/proposals/2026-09-sota-scorecard.md:278-285,337-355,551-552`;
`docs/capture-requests/2026-09-319-frame-session.md:104-133`).

### 3.3 Known physical target: valid alternate, not the current grid

**ARGUED.** A certified physical target can replace the higher-magnification
atlas only when its **two-dimensional, nonperiodic geometry** is independently
known at substantially finer sampling than the main sensor. A suitable object
is a random binary microdot or pseudorandom chrome photomask with a traceable
design file, fiducials, features spanning the licensed band and enough
guard-separated cells for cluster inference.

**ARGUED.** A USAF chart, Siemens star or regular microscope grid may help
calibrate geometry and transfer, but none alone is sufficient for a
natural-detail claim. Repetition makes the answer guessable, sparse bars
under-sample artifact behavior, and radial/edge summaries can reward
presentation sharpening.

## 4. Registration and resampling contract

**MEASURED.** Registration is a first-order threat in this repository. A prior
nontranslation residual missed the `0.10 px` gate at `0.107703`; an independent
implementation reproduced `0.105202`, and the battery found wrong-sign and
local-warp failures (`docs/research/M-PHASE0-SPLIT2.md:1-18,148-170`).
A prior down/up resampling path moved one claim band by `77.5%`
(`docs/research/V-HEADTOHEAD3.md:442-453`).

**ARGUED.** The native candidate/comparator output is never resampled. The
common-grid procedure is:

1. Decode and linearize RAW through the frozen product path. Keep the output
   on its native pixel grid.
2. Estimate reference-to-main geometry from grid/fiducial coordinates and
   low-frequency input copies that are disjoint from scored sites. No output
   detail statistic participates.
3. Freeze one reference-side geometry for each of the near, middle and far
   fixed-focus bursts, including any measured focus breathing. Reuse that
   three-map set for all algorithms and all kill arms.
4. Apply scale, rotation, optical-distortion mapping and pixel-footprint
   integration to the **oversampled reference only**.
5. Remove candidate translation analytically. In spectral calculations use a
   unit-modulus Fourier phase ramp; in pixel calculations shift the
   reference-side footprint integrals. Never interpolate the candidate.
6. Restrict every claim mode to `<=0.25 cyc/native output px`, with the
   antialias transition entirely on the reference side.
7. Fit no local warp to improve a score. If the frozen physical mapping leaves
   excessive local residual, refuse the site or the run.

**MEASURED.** The scorecard requires native-output work, analytic translation
handling, scale disagreement `<=0.10%`, rotation `<=0.02 degrees`, and
nontranslation residual `<=0.10 native output px RMS`
(`docs/proposals/2026-09-sota-scorecard.md:225-235`). The head-to-head
verification likewise states that output pixels are never resampled
(`docs/research/V-HEADTOHEAD3.md:296-304,401-404`).

**ARGUED.** Reference resampling is unavoidable because the point of the
capture is a different subject-sampling grid. It is admissible only as a
frozen measurement operator. Before any holdout rendering, the registrar must
freeze:

- the reference pixel-footprint model;
- the antialias filter and support;
- the optical-distortion model;
- two alternate reference-side kernels used only as a sensitivity arm; and
- a maximum allowed change in `J_TR` and every `F_TR` component between them.

If that uncertainty consumes the decision margin, the result is
`UNMEASURED`. The instrument may not select whichever kernel favors Strehl.

## 5. Exact decision relation

**ARGUED.** The claim-bearing result is a paired comparison of Strehl to each
comparator, reported by independent repeat and by band. Let
`Delta J = J_TR(strehl) - J_TR(comparator)` and let each
`Delta F_j = F_TR,j(strehl) - F_TR,j(comparator)`, where lower fidelity
departure is better.

**ARGUED.** The only result allowed to say **BETTER DETAIL** is:

```text
lower_95(Delta J) > delta_J
AND
upper_95(Delta F_j) <= delta_F_j for every fidelity component j
AND
every provenance, geometry, rank, tone, clipping and reference gate passes.
```

`delta_J` is a strictly positive information margin. Each `delta_F_j` is a
noninferiority allowance set from reference repeat uncertainty, geometry
uncertainty and arm-blind development power. No fidelity improvement may
substitute for `Delta J <= delta_J`.

**ARGUED.** Other outcomes are:

| Outcome | Rule |
|---|---|
| `WORSE` | information is significantly lower, or a fidelity component is significantly worse without a qualifying information gain |
| `EQUIVALENT` | information and all fidelity components lie inside their frozen equivalence regions |
| `MIXED` | information rises but any fidelity component regresses, or components disagree across bands |
| `UNMEASURED` | any input, reference, rank, transfer, geometry, tone, clipping, power or provenance gate fails |

**ARGUED.** `MIXED` and `UNMEASURED` do not satisfy M1 and cannot be rounded
into a win. Results are reported for Strehl versus Zerene and Strehl versus
Helicon separately. There is no average-comparator victory.

## 6. Estimator and sample contract

**ARGUED.** The commissioning implementation must use all of the following:

- at least 64 independent macro-sites, with uncertainty resampled at the
  macro-site level;
- enough disjoint micro-sites inside those macro-sites to meet a preregistered
  `n / max(p, q) >= 1.5` full-rank covariance gate for output dimension `p`
  and truth dimension `q`;
- a complete linear green or luminance output support window with a frozen
  site-local boundary rule for theorem-bearing filter arms;
- a fixed reference feature basis using only modes at or below
  `0.25 cyc/native output px`;
- no ridge, shrinkage, pseudo-inverse, PCA, learned embedding, selected
  moment, score-driven feature deletion or outcome-driven band choice;
- separate A and B readings before any summary;
- reference halves 1 and 2 retained through the calculation;
- cluster bootstrap or an independently justified cluster interval, with
  seeds and site manifest frozen; and
- exact refusal on covariance rank failure or an inadmissible condition
  number, rather than a regularized number.

**ARGUED.** The reference basis may reduce the truth dimension because it
defines the licensed task. The output observation may not be reduced in a way
that destroys full-rank post-filter equivariance. The implementation must
demonstrate algebraically and with a finite random matrix self-test that its
actual centering, support, channel transform and covariance code preserve
`J_TR(Y) == J_TR(AY)` before any image arm is run.

**ARGUED.** The congruence guarantee covers nonsingular **linear** output
operators only. `J_TR` is still a finite second-order reader and can change
under an arbitrary nonlinear remapping. Gamma, logistic tone, clipping and
quantization therefore do not receive a theorem: the linear-output provenance
gate and their dedicated kill arms must refuse them. A learned hallucinating
restorer outside the frozen comparator envelope is also out of scope and
produces `UNMEASURED`, not an information claim.

**ARGUED.** The A and B main passes are not pooled as if they were twice as
many independent subjects. Each pass produces a complete paired comparison.
Agreement is a reproducibility gate; the subject and uninterrupted session
remain the holdout unit.

### 6.1 Commissioning data before the holdout

**ARGUED.** The sealed same-session reference is not commissioning data. The
implementation must reach a frozen, auditable state before those RAWs are
rendered:

| Commissioning need | Allowed development source |
|---|---|
| Congruence, null bias, blur/improvement direction, USM, tone, clipping and hallucination plants | Synthetic forward models with complete latent truth and frozen seeds |
| Reference split, transfer ratio, residual and reference-side resampler code | Existing development-only high-resolution slide plus synthetic pixel-footprint plants |
| Wrong-sign, fractional shift, scale, rotation and local-warp refusal | Existing phase-0 registration development captures and planted transforms |
| Rank, conditioning, site count and cluster interval | Existing development images with truth labels permuted, plus arm-blind power simulation |
| End-to-end physical rehearsal | Prefer a disposable-subject rehearsal using the same reference protocol; if omitted, all unexercised physical-reference branches remain automatic holdout refusal conditions |

**MEASURED.** The scorecard permits the burned grid and development-only
high-resolution slide to commission a new instrument but bars them from its
scored value (`docs/proposals/2026-09-sota-scorecard.md:551-552`). Their known
IBIS geometry defect makes them useful for failure and rejection paths, not
evidence that the final native-geometry success path will pass
(`docs/capture-requests/2026-09-319-frame-session.md:36-55`).

**ARGUED.** A disposable-subject rehearsal is strongly preferred because it
is the only way to exercise the full cross-magnification success path without
spending the holdout. It need not use the irreplaceable subject and does not
supply any M1 score. If no such rehearsal is made, the first unseen physical
condition that requires a code, mapping or threshold change burns the
holdout; the lane may only refuse and reshoot.

## 7. Ordered commissioning battery

**ARGUED.** The following arms and death conditions are frozen conceptually
by this proposal. A later scorecard registrar must freeze numerical
tolerances, powers, nuisance values and exact seeds on development data before
the sealed session is rendered. Arm order is binding: stop at the first death
and do not use later arms to rehabilitate the statistic.

| Order | Arm | Required result | Candidate dies if |
|---:|---|---|---|
| 0 | Provenance and potency | Every transform changes the intended samples; hashes and lineage are complete | The arm is a no-op, touches the wrong stage, or uses scored data to choose a parameter |
| 1 | Identity and permutation nulls | Identity is equivalent; shuffled truth gives no detail evidence | Null is significant, negative estimates are clipped into success, or the shuffled reference scores |
| 2 | Finite-matrix congruence self-test | `J_TR(Y) == J_TR(AY)` to numerical tolerance for random full-rank `A` | Actual code is not equivariant |
| 3a | Site-local information-free USM after all noise | Exact finite-sample `J_TR` equality; the joint verdict is never `BETTER` | Equality fails or fidelity alone promotes the arm |
| 3b | Full-frame information-free USM after all noise | Empirical `J_TR` equivalence on ordinary extracted sites | Recommended one-sided UCB for the ratio exceeds `1.01` |
| 3c | Identity-placed hull-safe/projected USM and source-endpoint selector | Both M8 censuses remain zero, but the joint truth-referenced verdict is never `BETTER` | In-hull sharpening, hull projection or selection among observed extrema creates a valid detail win |
| 4 | Common post-render Gaussian blur | `J_TR` remains equivalent and `F_TR` ranks blur below truth | Blur is called better/equivalent to truth or the fidelity channel is blind |
| 5 | Truth-sided filter pair | Exact truth beats both a low-pass copy and an over-sharpened copy | Either side is not worse than truth |
| 6 | Pre-sensor blur ladder | `J_TR` decreases monotonically and attenuation worsens | Any blur rung rises, or the effect is underpowered |
| 7 | Genuine optical improvement | `J_TR` rises and no fidelity component regresses | The sigma-1.20 improvement does not beat its blurrier control |
| 8 | Gamma-3 and logistic tone | Transfer sentinel refuses the run before a claim number | Either nonlinear arm produces a higher valid detail result |
| 9 | Clipping and quantization | A potent arm lowers the result or is refused | The arm raises a valid result; a rail-free "clipping" arm is invalid |
| 10 | Added independent noise | `J_TR` falls; fidelity cannot rescue it | Noise raises information or creates a win |
| 11 | Common-mode A/B plant absent from reference | No information gain; residual fidelity worsens | A repeated hallucination or FPN pattern is rewarded |
| 12 | Flat/no-target ROI | No detail evidence and no transferable truth band | A flat produces a positive claim |
| 13 | Shared-master and reference-leakage plants | Deliberate sharing is detected or worsens the result | Shared calibration correlation raises the certificate |
| 14 | Geometry plants | Integer/no-op, fractional shift, wrong sign, scale, rotation and local warp behave as preregistered | Wrong sign passes, candidate pixels are resampled, or local warp is fitted away |
| 15 | Reference-resampler pair | Both frozen reference-side kernels agree inside the uncertainty allowance | Kernel choice changes the verdict |
| 16 | Rank/regularization sentinel | Rank failure refuses; hidden ridge and PCA are detected | Any regularized fallback emits a claim number |
| 17 | Edge-angle and orientation ladder | No orientation creates a win from the same transfer | Result depends materially on edge angle |
| 18 | Dense-stack pseudo-truth trap | Lineage gate rejects a merger-produced reference for optical M1 | A dense merge is accepted as physical truth |
| 19 | Reference corruption | Blurred, sharpened, misfocused and wrong-strip references fail eligibility or widen uncertainty | A compromised reference silently changes the winner |

**MEASURED.** These arms incorporate the current scorecard's mandatory null,
pre-sensor blur, genuine improvement, USM, gamma, logistic, noise, edge-angle,
common-mode, flat and 64-site controls
(`docs/proposals/2026-09-sota-scorecard.md:563-577`). The `1.01` USM
recommendation preserves the scale used to kill candidate 1, but it is not an
active M1 bar until the registrar ratifies it in a later scorecard revision.

**MEASURED.** A clipping arm must prove it reached a rail. Candidate 2's
registered clipping arm had `0/2,088,960` rail hits and therefore did not test
clipping (`docs/research/M-CAND2.md:20-32`). Tone stability also cannot
substitute for optical-direction arms: `Q25` was nearly invariant to affine,
gamma and logistic tone and still rewarded USM and reversed genuine optical
improvement (`docs/research/M-PHASE0-SLANTEDGE.md:202-212`).

**DERIVED.** Arm 3c carries the M8 frontier attack into commissioning without
making M8 part of the M1 promotion rule. It must be potent enough to raise a
registered high-frequency proxy while both M8 censuses remain zero; `TRD`
must still refuse or demote it.

## 8. Leakage firewall and authority

**ARGUED.** Roles are separated as follows:

| Role | May do | May not do |
|---|---|---|
| lane-TRUTH | Define the estimand, capture, algebra, arm families and death semantics | Render the holdout, choose result-favouring nuisance values, set the final numeric bar, or take the claim reading |
| scorecard registrar | Freeze dimensions, bands, minimum effects, uncertainty allowances, arm values and status rules in a numbered pre-results revision | Run the claim-bearing analysis or revise a bar after seeing it |
| implementation auditor | Re-derive the finite estimator and inspect code/data lineage independently of the stacker | Tune the production stacker from reference outcomes |
| measurement lane | Run the frozen battery and comparator analysis on the sealed session | Change code, sites, bars, reference mapping or exclusions after unsealing |
| independent verifier | Re-run from RAW, re-choose preregistered nuisance branches and adjudicate discrepancies | Know or optimize for the desired winner |

**MEASURED.** The current scorecard says challenge outcomes and numeric
admission bars must be frozen in a later revision before score data are read
(`docs/proposals/2026-09-sota-scorecard.md:568-577`). It also bars the current
session from development and treats subject plus uninterrupted session as the
holdout unit (`docs/proposals/2026-09-sota-scorecard.md:276-295`;
`docs/capture-requests/2026-09-319-frame-session.md:36-55`).

**ARGUED.** Existing captures, synthetic forward models and a separately
declared development reference may commission the code. The incoming
high-magnification reference is part of the sealed holdout. It may be checked
for file integrity, EXIF, gross clipping and manifest completeness on arrival,
but no detail output, site selection, band choice, geometry tuning or
threshold choice may be made from it.

## 9. Prior art and scope

**MEASURED.** The repository prior-art tool passed its three commissioning
checks and was searched for `truth reference sharpening detail` during this
design. Its relevant matches included M46, M55b, M57, V-bestframe, M39, M80,
M95, BUILD-DEMOSAIC and BUILD-SHARP. Their disposition is not "superseded":

| Prior work | Result retained here | Why it is not the present instrument |
|---|---|---|
| M46 / M55b / M57 | A detail candidate needs a conjunctive, executable battery; output-only cross-power families have severe noise, gain and monotonicity limits | None had an independently sampled same-subject truth atlas and the accepted one-number result did not survive later verification (`docs/research/M46-detail-metric-measured.md:29-55`; `docs/research/M55-acceptance-spec.md:1-35`; `docs/research/M55-sigpow-verification.md:1-15`; `docs/research/M57-detail-metric-from-first-principles.md:29-81`) |
| V-bestframe | Native-grid, no-resample comparison and cross-repeat covariance can separate signal from temporal noise | It compares a merge to input frames from the same degraded capture and explicitly found raw band energy ranking noise (`docs/research/V-bestframe.md:1-31,55-100`) |
| M39 / M80 | Noise corrections need flat/no-target controls and must not clamp noise into detail | M39 measured a flat credited with `+35.5%` detail; M80 repaired a selector invariant by returning `NO TARGET`, not by forcing a number (`docs/research/M39-verify-detail-metric.md:1-35`; `docs/research/M80-invariant-repair.md:1-20`) |
| M95 / BUILD-DEMOSAIC | Known truth can separate scene-correlated transfer from fabricated output and can reveal defects invisible to power statistics | Both are synthetic or demosaic-specific truth instruments, not a same-subject focus-stack score (`docs/research/M95-demosaic.md:1-75`; `docs/research/BUILD-DEMOSAIC.md:1-75`) |
| BUILD-SHARP | Correct-band truth reference is necessary but can still select an artifact-bearing method | Its wedge is the direct warning against a fidelity-only promotion rule (`docs/research/BUILD-SHARP.md:3945-3955`) |
| D8 / M115 / M-PHASE0-SPLIT | Split cross-power separates temporally independent noise, and matched-contrast SNR is resistant to common output filters | `P_sig` and `R_SNR` own different properties; common-mode structure and tuner transfer killed the product form (`docs/research/M115-deconv-headroom.md:47-137`; `docs/research/M-PHASE0-SPLIT.md:1-103,252-280`) |

**ARGUED.** This proposal claims no novelty for canonical correlation, task
information, NEQ, split-reference transfer, truth/residual decomposition or
non-compensating scorecards. Its contribution is the specific conjunction,
capture lineage and refusal boundary required by the current M1 deadlock.

**MEASURED.** The project's DOI ledger resolved the relevant data-processing,
ideal-observer, Fisher-information, task-NEQ, FRC and Gaussian-copula
references on 2026-09-03
(`docs/proposals/2026-09-detail-instrument-investigation.md:376-395`).
The most relevant external foundations are:

- Cover and Thomas, data processing,
  [DOI 10.1002/047174882X](https://doi.org/10.1002/047174882X);
- Barrett, objective task image quality,
  [DOI 10.1364/JOSAA.7.001266](https://doi.org/10.1364/JOSAA.7.001266);
- Barrett et al., Fisher information and task performance,
  [DOI 10.1364/JOSAA.12.000834](https://doi.org/10.1364/JOSAA.12.000834);
- Wagner and Brown, task-based NEQ,
  [DOI 10.1088/0031-9155/30/6/001](https://doi.org/10.1088/0031-9155/30/6/001);
  and
- Nieuwenhuizen et al., FRC resolution measurement,
  [DOI 10.1038/nmeth.2448](https://doi.org/10.1038/nmeth.2448).

**ARGUED.** The name "information" in `J_TR` is scoped to its explicitly
declared Gaussian canonical functional. A successful commissioning would
license a comparative statement about recoverable, truth-referenced linear
information in the registered band and capture regime. It would not establish
general mutual information, perceptual quality, artifact freedom outside
`F_TR`, or universal optical resolution.

## 10. Final ruling

**ARGUED.** Truth-referencing does not by itself solve the detail problem. A
direct fidelity statistic can reward information-free sharpening, and a
structurally post-filter-invariant information statistic is blind to
post-render blur. The hypothesis survives only as a **joint,
non-compensating certificate**:

```text
more recoverable truth information
AND
no regression in transfer fidelity to independent physical truth.
```

**ARGUED.** M8 does not simplify that conjunction into an output-only
frontier. It can veto a source-hull violation, but a zero or unchanged M8
reading cannot turn a sharpening-sensitive detail proxy into evidence of
resolved truth.

**ARGUED.** That certificate has a structural answer to both known failure
modes, an independently sampled reference, a native-output geometry contract
and arms that can kill it. It is therefore worth commissioning. It is not yet
an admitted M1 instrument.

**ARGUED.** The operational decision is:

- **GO:** shoot the 160-frame higher-magnification reference block in the same
  session, with the main sweeps pinned to 1.30x effective reproduction and the
  same 2x Viltrox installed throughout, then seal it with the main holdout;
- **CONDITIONAL GO:** commission `TRD = (J_TR, F_TR)` on development data under
  the ordered battery, then require a registrar revision and independent
  implementation audit;
- **NO-GO:** do not use D8's same-capture split, the dense stack, current grid,
  development-only high-resolution slide, direct MSE/PSNR/SSIM, learned
  perceptual score, FRC, a detail-proxy/M8 frontier or any weighted
  information/fidelity scalar as the M1 truth instrument; D8 may remain an
  offline matched-contrast diagnostic and M8 remains an independent
  one-way artifact gate; and
- **CURRENT STATUS:** M1 remains `UNMEASURED`, and no detail-qualified SOTA
  claim is licensed.

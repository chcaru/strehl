# M-FRC-VIABILITY — repeat-pair FRC adjudication

**Status: revised after the SPLIT2 primary-source clarification and a lightweight
64-site power-planning probe.**

**Verdict:** **GO to commission repeat-pair FRC now on synthetic and existing
development data; NO-GO to admit the current Hann-tiled estimator as M1 before
that battery passes.** The new session is scored holdout, not commissioning
material. The arithmetic is commissioned, the historical sharpening result
stands, and FRC is responsive to controlled pre-noise detail changes. It is not
a complete resolution instrument by itself: common post-noise filtering is an
ideal null, the implemented windowed estimator has signed residuals, and shared
fixed pattern remains a structural confound.

The repository request was amended while this adjudication was in progress. The
current bench sheet is **407 frames**, not 319: it now includes 64-site framing,
32-flat/32-dark A and B calibration groups, settling language, and 24 witness
frames (`docs/capture-requests/2026-09-319-frame-session.md:1-38,110-216`).
Do not shoot the superseded 319-frame sheet.

The current 407-frame acquisition supplies the necessary pixels. One pre-shot
analysis defect remains: its frozen witness gate explicitly cannot detect a
focus-ladder offset that leaves the rig undisplaced, although the bench sheet
describes the witnesses as proving node coincidence
(`docs/capture-requests/2026-09-node-coincidence-gate.md:37-54`). Add a frozen,
input-only focus-support/ladder-phase predicate before the holdout is read. No
additional frames or per-node interleaving are required.

Claims below are labelled **MEASURED**, **DERIVED**, **EXPLORATORY**, or
**ARGUED**. No RAW was opened. The only new computation was a lightweight
synthetic probe using SPLIT2's committed FRC implementation.

## 1. Deadline adjudication: shoot 407 frames, freeze one missing input gate

The amended request gets the acquisition design right: body SteadyShot and lens
OSS are off; exposure is fixed; the irregular patch is coplanar with the grid;
`sw4` and `sw10` each have two complete same-direction passes; the patch must
support 64 sites; calibration is split A/B; and settling is explicit
(`docs/capture-requests/2026-09-319-frame-session.md:110-216,218-255`).

### 1.1 The A/B passes are independent in the FRC sense

**MEASURED:** this sensor's temporal noise is independent exposure-to-exposure
to within 1%; ten-frame means on real ISO-100 darks reached sqrt(N) on all four
planes (`docs/research/M62-sqrt-n.md:483-509`). Separate A and B sweeps therefore
supply independent photon/read-noise realizations.

Whole sweeps do not have to alternate at every focus node to satisfy FRC.
Independence means that A and B are separately acquired inputs to separately
run render pipelines while the latent subject and intended focus support remain
fixed. The existing repeated-exposure capture passed its focus-stability proxy;
SPLIT2 stopped on spatially varying registration, not on evidence of a focus
change (`docs/research/M-PHASE0-SPLIT2.md:39-87`).

The approximately 1 EV difference in SPLIT2 is also easy to misstate. Its
protocol **never paired the two light levels**: A and B were formed within each
32-frame fixed-light block, and the second light block was an independent
robustness replication. It failed geometry on its own
(`docs/research/M-PHASE0-SPLIT2.md:124-155`;
`experiments/M-PHASE0-SPLIT2/AMENDMENT-1.md:46-75`). The incoming fixed
exposure is still correct, but it is not repairing a within-pair 1 EV mismatch.

The 24 witness frames are useful for displacement and stability, but the current
frozen gate says plainly that they do **not** certify a focus-ladder offset that
does not move the rig (`docs/capture-requests/2026-09-node-coincidence-gate.md:17-54`).
That limitation matters because the bench sheet currently calls them proof that
the two ladders coincide.

**Required pre-shot analysis amendment:** freeze an input-only focus-support
gate on development data. At minimum it must compare A/B per-site through-focus
response curves and reject a systematic frame-index/peak-position offset; the
witness bursts can additionally compare the spatial focus profile on the
tilted target. The existing scalar high/mid spectral proxy is already
commissioned to reject a sigma-1 focus blur, but no cross-pass ladder-phase bar
is currently registered (`experiments/M-PHASE0-SPLIT2/frc.py:418-459`;
`docs/research/M-PHASE0-SPLIT2.md:39-57`). Freeze that bar before any new RAW is
read. The current frames contain the needed observations, so this changes the
gate, not the shoot.

### 1.2 Frame count and site count

The 55/27 counts are plausible depth-sampling counts. Ring statistics pool many
Fourier coefficients, while uncertainty resamples independent physical sites.
The scorecard requires at least 64 independent sharpening sites with an
unchanged bar as sample size grows
(`docs/proposals/2026-09-sota-scorecard.md:559-583`).

The current request now requires at least 64 guarded, non-overlapping eligible
sites, approximately an 8 by 8 lattice at a 256-pixel tile, with per-site
subject cross-power and an interior focus peak
(`docs/capture-requests/2026-09-319-frame-session.md:174-191,299-310`). That is
the right capture-side requirement. The site manifest still must be frozen
input-only before a render exists.

### 1.3 Registration is achievable without spatial resampling, but remains a gate

SPLIT2's arithmetic was not broken: it matched an independent direct DFT to
`1.60e-15` relative error. Its bright block passed the registered local-geometry
bar at `0.064031` native-pixel RMS; the second block failed at `0.107703`,
independently reproduced at `0.105202`
(`docs/research/M-PHASE0-SPLIT2.md:1-13,70-87,89-123`). Stabilization was on.
Turning both stabilization systems off is the direct capture-side correction.

The new witness gate freezes an integer-alignment rule, a within-burst floor
`<=0.033`, and a per-pair between-burst bar `<0.10` native-pixel local RMS
(`docs/capture-requests/2026-09-node-coincidence-gate.md:78-125`). M88b measured
exact removal of a 3-pixel integer shift, while one 0.37-pixel resample left
`2.3987 um` of bias (`docs/research/M88b-merge-sharpness.md:74-84`).

Those witness predicates are a useful input-only geometry sentinel. The final
A/B scene windows must independently pass the same no-resampling geometry
contract; witnesses cannot license a locally warped render pair.

### 1.4 The amended calibration count is conservative and sufficient to test

The current request now carries 32 flats and 32 darks **for each arm**, moves
the diffuser between flat groups, matches dark exposure and temperature, and
discards the first two darks in each group
(`docs/capture-requests/2026-09-319-frame-session.md:126-133,193-216`). This
directly fixes the shared-master defect.

The repository's “16 frames is sufficient” statement concerns precision of a
global PRNU standard-deviation estimate over millions of pixels; it does not
prove that a 16-frame per-pixel master has enough ring-resolved sensitivity for
M1 (`docs/captures-needed.md:1428-1451`). I therefore retract the earlier claim
that doubling calibration to 32/32 per arm was unnecessary.

At a `10000 DN` flat level, the measured shot/read model predicts a 32-frame
flat master at about `0.084%` relative RMS. After the required two-frame dark
discard, a 30-frame master has a read-noise-model floor of about `0.16 DN`;
the actual 1-second temporal dark variance is unmeasured and must be estimated
from these frames. Disjoint A/B masters have zero expected estimation-error
covariance under unbiased calibration, and the extra frames provide room for a
frozen split/cross-fit ring-null test. They improve power; they do not by
themselves prove the residual is zero.

### 1.5 Subject, tilt, exposure, and timing

The stable, fine, irregular coplanar patch and roughly 1-degree tilt provide the
right nonperiodic spatial-frequency and through-focus content
(`docs/capture-requests/2026-09-319-frame-session.md:82-108,236-255`). The
arrival check must use cross-power attributable to the subject, not
single-frame power that noise or FPN can satisfy, and must reject clipped,
photon-starved, or endpoint-focused sites. The fixed ISO 100, 1 s, f/5.6
exposure and identical reset do not break pairing.

**Deadline answer:** the superseded 319-frame sheet should not be shot. The
current **407-frame acquisition is physically sufficient and needs no more
frames**. Before capture data are read, amend the frozen input contract with a
focus-support/ladder-phase predicate; the existing witness gate proves
displacement/registration only and must not be described as proving identical
focus nodes.

## 2. Source claims verified

1. The governing proposal does prescribe two detail instruments: “D1: FRC +
   slant-edge” (`docs/proposals/2026-08-sota-path.md:192-197`).
2. The split prototype records amount-1.5 unsharp changing the crossing
   `0.222192 -> 0.220543`, while naive acuity rose `1.838176x`
   (`docs/research/M-PHASE0-SPLIT.md:166-193`).
3. The microscopy survey does carry the standing **ARGUED** recommendation that
   FRC needs two independent realizations and cannot reward independent invented
   noise (`docs/research/G-edof-deconvolution.md:609-612`).
4. Same-frame split FRC is withdrawn: the common-mode adversary reads
   `0.972099`, and later work withdrew the real crossing
   (`docs/research/M-PHASE0-SPLIT.md:35-51,89-101`).
5. Repeat-pair FRC is currently blocked on physical capture geometry
   (`docs/STATUS.md:923-930`), and the latest diagnosis adds data-dependent
   registration and stable FPN to the blockers (`docs/STATUS.md:1423-1448`).
6. SPLIT2's commissioned implementation matches a separately written direct DFT
   to `1.5968e-15` relative error, passes the independent-noise null, and
   deliberately fails the shared-pattern adversary
   (`docs/research/M-PHASE0-SPLIT2.md:89-123`).

The G-edof recommendation is historically real but too broad. The decision
record later corrected it: FRC rejects **independent** noise amplification, not
common-mode amplification, and same-frame FRC scored a catastrophically noisy
arm at `0.970` (`docs/research/SYNTHESIS.md:1001`).

## 3. Does the M-PHASE0-SPLIT sharpening result stand?

**Yes, narrowly; it did not fall with the real split-frame use.**

The withdrawal removes the Rust product path and the interpretation of the
real `0.400367` crossing, while explicitly retaining the offline code,
measurements, and controls (`docs/research/M-PHASE0-SPLIT.md:1-16,154-164`).
The sharpening arm is a synthetic shared-signal/independent-noise commissioning
control, not a statistic computed from the invalid real split.

The exact historical test used one 256 by 256 field divided into sixteen 64 by
64 tiles, then applied a periodic 3 by 3 **box** unsharp at amount 1.5—not an
isotropic Gaussian (`experiments/M-PHASE0-PIPE/out/source-prototype/crates/strehl-core/src/split.rs:473-486,549,620-657`).
SPLIT2 separately records the same sign: naive acuity rose `1.832679x`, while
the crossing moved `0.223792 -> 0.223037` (`-0.000754`) and the maximum ring
movement was `0.011247`. The tile's ring spacing was `1/64 = 0.015625`
cycles/quad-pixel (`docs/research/M-PHASE0-SPLIT2.md:89-123`;
`experiments/M-PHASE0-SPLIT2/out/commission.json:1630-1668`).

But it is **not scorecard-admissible M1 evidence**:

- it has 16 synthetic tiles, not 64 independent physical sites;
- it has no frozen equivalence-power calculation or minimum detectable effect;
- it covers one unclipped box-USM operation, not the windowing, clipping, tone,
  anisotropy, or adaptive-processing boundary;
- its first per-ring `5e-4` requirement failed at `0.010859` and was amended,
  before real pixels but after seeing the synthetic control
  (`experiments/M-PHASE0-SPLIT/PREREGISTRATION.md:124-141`); and
- the current scorecard explicitly says no admissible sharpening-safe detail
  statistic exists and requires both structural protection and the complete
  battery (`docs/proposals/2026-09-sota-scorecard.md:497-583`).

The accurate program statement is therefore:

> Among statistics that retained a measured detail response, FRC is the only
> repository candidate whose sharpening result stayed in the safe direction:
> amount 1.5 raised naive acuity 83.3% while the FRC crossing moved down. The
> blind `f_licensed` statistic also stayed pinned, so “only statistic” without
> that qualification would be false. The FRC result survives the split-frame
> withdrawal, but no FRC implementation has survived the registered 64-site
> admission battery or supplied the implementation-level structural proof.

## 4. Ring-cancellation algebra

For one ring/bin \(R\), the repository's standard form is

\[
\operatorname{FRC}_R(A,B)=
\frac{\operatorname{Re}\sum_{q\in R}A_qB_q^*}
{\sqrt{\left(\sum_{q\in R}|A_q|^2\right)
             \left(\sum_{q\in R}|B_q|^2\right)}}.
\]

Apply the same linear shift-invariant filter \(H_q\) to both realizations. Then

\[
\operatorname{FRC}'_R=
\frac{\operatorname{Re}\sum |H_q|^2 A_qB_q^*}
{\sqrt{\left(\sum |H_q|^2|A_q|^2\right)
             \left(\sum |H_q|^2|B_q|^2\right)}}.
\]

**DERIVED theorem:** if \(|H_q|^2=c_R>0\) for every coefficient actually
included in the bin, cancellation is exact on that finite sample. \(H\) need
not be real or zero-phase; a common complex phase also disappears. Any fixed
ring weights likewise cancel. If \(c_R=0\), the ring is undefined, not
invariant. Noise independence plays no role in this identity; it is required
only when interpreting the resulting correlation as repeatable scene
information.

The proposed isotropic-Gaussian USM theorem is therefore correct only for exact
equal-radius rings, periodic convolution, and the standard homogeneous
normalization. It is **not an exact identity for the repository estimator**,
which removes means, multiplies by a Hann window, and rounds Fourier radii into
finite-width bins (`experiments/M-PHASE0-SPLIT/PREREGISTRATION.md:31-55`).
The measured `0.010859` maximum ring movement is direct evidence of that
non-identity (`experiments/M-PHASE0-SPLIT/PREREGISTRATION.md:124-141`).

### Exact stopping points

1. **Finite-width ring bins.** Even a perfectly radial \(H(|q|)\) varies across
   a bin. It then reweights modes instead of factoring out.
2. **Anisotropic sharpening.** Direction-dependent gain varies within a ring.
   It can raise FRC: for two modes \(A=(1,1)\), \(B=(1,-1)\), base FRC is zero;
   common gains `(2,1)` make it `(4-1)/(4+1)=0.6`.
3. **Actual discrete Gaussian/box kernels.** A separable finite kernel is not
   exactly radial on the square Fourier lattice, especially near the licensed
   upper band. The cited test is explicitly a 3 by 3 box.
4. **Windowing, cropping, and boundaries.** In general
   \(W(h*x)\ne h*(Wx)\). Spatial filtering before evaluator apodization becomes
   convolution between Fourier modes. Reflect/nearest/zero boundaries are also
   not circular convolution.
5. **Clipping and quantization.** They are nonlinear and can create repeatable
   harmonics from shared scene structure. The sign is unrestricted.
6. **Gamma, logistic tone, and local contrast.** Pointwise nonlinearity mixes
   frequencies; monotonicity does not preserve Fourier correlation.
7. **Spatially adaptive, edge-aware, or data-dependent sharpening.** These are
   not one common diagonal \(H_q\). Independently fitted filters, masks, and
   deconvolution supports can differ between A and B.
8. **Geometry.** A residual translation contributes phase varying with
   direction; scale, rotation, local warp, and different crops move content
   between coefficients. Integer pre-cropping is safe; resampling is not.
9. **Different normalization.** Epsilon floors, noise-bias subtraction,
   regularization, per-ring whitening, mask corrections, channel mixing, or
   averaging already-normalized tile FRCs need their own proof. A phase-only
   per-coefficient statistic has a different invariance and is not this FRC.
10. **Threshold/censor logic.** Exact per-ring invariance would preserve a
    crossing, but small non-invariant ring movements can change interpolation,
    consecutive-ring confirmation, or censor class near the threshold.

Thus the algebra is stronger than an empirical non-rejection **inside its
boundary**, but that boundary excludes several operations real stackers ship.

### 4.1 Quantifying the implemented windowing residual

**EXPLORATORY, not admission evidence:** I ran SPLIT2's committed
mean-subtract/Hann/ring/classifier code on 64 independently generated sites,
with all bars absent and no RAW opened. Each 256-sample site was cropped from
the centre of a 512-sample support after filtering, specifically to keep a tile
boundary from masquerading as the windowing effect. The primary paired probe
uses 3,000 fixed-seed site-bootstrap draws; the fresh-noise and independent
postfilter replication use 5,000. The complete generator, seeds, arms, and
results are committed as exploratory—not admission—artifacts
(`experiments/M-FRC-VIABILITY/power_probe.py:20-289`;
`experiments/M-FRC-VIABILITY/out/power-probe.json:1-301`).

For the historical 3 by 3 box USM at amount 1.5, the 256-sample crossing moved
`0.23391273 -> 0.23385783`, or `-0.00005490`, with bootstrap interval
`[-0.00026482,-0.00002513]`; the maximum usable-ring movement was `0.00142420`.
Repeating at the historical 64-sample tile size gave `-0.00051282`,
`[-0.00077156,-0.00030666]`, and maximum ring movement `0.00840328`.
This reproduces SPLIT2's safe sign and shows why a sub-ring crossing movement
can still be statistically resolved: interpolation and pooled coefficients
provide information below one ring spacing.

The residual is not sign-protected. On the same 256-sample design, a common
post-noise Gaussian blur with sigma 2 moved the crossing **up** by `+0.00028558`
with interval `[+0.00020855,+0.00135282]`. A second independent 64-site seed
read `+0.00067685`, interval `[+0.00033230,+0.00088900]`. This is the finite
Hann/bin manifestation of M88b's wrong-signed low-pass response, not an
arithmetic error.

There is no useful distribution-free small-error bound for the current
estimator. The Hann operator has zeros, the crop/filter commutator is
content-dependent, and FRC's denominator can approach zero on a ring; a small
operator perturbation can therefore produce an arbitrarily large normalized
change on a low-power ring. The historical USM result is strong empirical
evidence for that exact arm, but it cannot substitute for the scorecard's
implementation-level structural argument.

## 5. Responsiveness: not generically blind, not yet powered for the claim

`BUILD-SHARP` calls the paired edge instrument “18,644x more responsive than
ring FRC” (`docs/research/BUILD-SHARP.md:166-173`) and points to M88b's direct
plant. A Gaussian low-pass from sigma 0 to 2 pixels changed FRC@0.25 from
`0.9742` to `0.9756`—an increase of only `0.0015`, in the wrong
direction—while 10–90 edge rise widened from `14.258` to `41.619 um`
(`docs/research/M88b-merge-sharpness.md:45-59`).

The published “18,644x” is not a statistical-power ratio: it divides
micrometres by a dimensionless FRC change and supplies no FRC sampling floor.
Normalized to their own baselines, the table is about **+191.9% edge width
versus +0.1507% FRC**. More importantly, this is a **post-noise output filter**.
For ideal FRC, any common nonzero linear transfer scales repeatable signal and
independent noise together and is intentionally a null. M88b therefore proves a
real limitation—FRC cannot stand alone as a presentation-resolution
instrument—but it does not measure FRC's response to the scorecard's required
**pre-sensor** blur and optical-improvement arms.

Pre-noise transfer is different: it attenuates or strengthens the latent signal
before fresh downstream noise, so repeat correlation should move. SPLIT2's
`0.991000 / 0.004115` low/high positive control proves dynamic range exists but
does not establish a minimum detectable effect
(`docs/research/M-PHASE0-SPLIT2.md:89-123`).

**EXPLORATORY 64-site power bracket:** using the same 256-sample padded fixture
as §4.1 and holding each site's A/B noise realization fixed across a planted
arm:

- pre-noise Gaussian sigma `0.1` moved the crossing `-0.00022397`, interval
  `[-0.00109610,-0.00016679]`. At the base crossing this is about a `1.1%`
  latent-amplitude attenuation;
- a pre-noise sigma-1 unsharp of amount `0.05` moved it `+0.00131969`, interval
  `[+0.00051075,+0.00522157]`, about a `3.3%` latent-amplitude gain there; and
- sigma `0.2` and `0.3` blur moved it `-0.00089646` and `-0.00202194`.

Thus a 64-site windowed crossing is not intrinsically too coarse: on a paired
deterministic commissioning fixture it resolves effects far below one
`1/256 = 0.00390625` ring.

That is the favorable case. In a separate planning draw where every optical
arm received fresh A/B noise, sigma `0.2` was unresolved and sigma `0.3` was
the first tested blur whose 95% site-bootstrap interval excluded zero. Around
the crossing, sigma `0.3` is approximately a 10% latent-amplitude loss. None of
the tested improvement arms through amount `0.2` supplied a stable MDE in that
single draw. This is not a registered power study, but it answers the practical
question honestly: **64 sites plausibly resolve a few-percent deterministic
paired change; the current evidence does not show that 64 physical sites resolve
a roughly 5% comparator difference under fresh capture noise.**

No universal site count can be inferred before the real site's variance and
effective repeat noise are known. The first admissible commissioning step must
freeze an arm-blind power curve and a minimum effect before any challenge arm
runs. The existing harness's response to 1-2 pixel misregistration
(`0.9477 -> 0.6663 -> 0.2049`) is nuisance sensitivity, not detail power
(`docs/research/M46-detail-metric-measured.md:187-205`).

**Responsiveness ruling:** FRC is safe-by-null for common invertible postfilters,
but it is responsive to pre-noise information transfer. BUILD-SHARP does not
kill that estimand. It does prove FRC must be paired with a separate
presentation/transfer instrument and that the current windowed crossing cannot
claim exact common-filter invariance.

## 6. What blocks repeat-pair FRC today

The existing repeat set is **data-blocked, not arithmetic-broken**. SPLIT2
verified the FRC implementation against an independent DFT to `1.60e-15`, then
correctly stopped because stabilization-on motion left the second fixed-light
block at `0.107703` native-pixel local RMS against `0.10`, independently
reproduced at `0.105202`. It retained no real FRC
(`docs/research/M-PHASE0-SPLIT2.md:1-13,70-123`). The approximately 1 EV change
was between two robustness blocks and was never used inside one pair
(`docs/research/M-PHASE0-SPLIT2.md:124-155`).

The remaining blocker after geometry is interpretation: stable DSNU, PRNU,
dark structure, dust, or calibration-master error is correlated at identical
sensor coordinates, while the temporal ABBA null cancels it. FRC correctly
reports correlation but cannot label it scene rather than fixed pattern. The
program diagnosis therefore names spatially varying geometry, data-dependent
registration, and stable sensor structure as the three blockers
(`docs/STATUS.md:1423-1448`).

Unblocking the eventual score requires the incoming stabilization-off matched
sweeps; input-only site selection and integer-crop registration that pass the
frozen geometry gate; and disjoint A/B calibration whose held-out ring
correlation passes a frozen null. The current 407-frame session supplies those
inputs, but it is sealed holdout. Commissioning, power selection, and all
numerical bars must be finished on synthetic and existing development data
before any holdout render.

## 7. Shared fixed-pattern noise and calibration count

The current body calibration is:

- black `512.10 DN`, gain `0.2232 DN/e-`, read noise `0.887 DN`;
- DSNU `0.389 DN`;
- PRNU `0.286%` of signal
  (`docs/research/V-LINEAR2.md:778-787`).

At ISO 100, the independent dark analysis similarly measures DSNU
`0.3833 DN`, temporal sigma `1.0073 DN`, and dark-frame fixed fraction
`0.12647` (`docs/research/M48b-fpn-rho-measured.md:55-82`). Its spectrum is
near-white to Nyquist, with only about 14% high-frequency roll-off
(`docs/research/M48b-fpn-rho-measured.md:236-268`). It therefore reaches the
same rings FRC would call detail.

For black-subtracted signal \(S\) DN, a variance-domain approximation before
calibration is

\[
F(S)=0.389^2+(0.00286S)^2,\qquad
T(S)=0.2232S+0.887^2,
\]

and a no-scene repeat floor after a merge with effective count \(n_\mathrm{eff}\)
is approximately

\[
\rho_\mathrm{repeat}(S)=\frac{F(S)}{F(S)+T(S)/n_\mathrm{eff}}.
\]

Illustratively, at \(n_\mathrm{eff}=9\), this is about `0.25` at `S=1000 DN`
and `0.62` at `S=5000 DN`; at \(n_\mathrm{eff}=55\), about `0.67` and `0.91`.
These are not ring-specific predictions—the PRNU spectrum is not yet measured
well enough for that—but they show why averaging makes shared pattern more,
not less, dominant. They also omit any additional 1 s dark-current
nonuniformity: the calibration darks that produced the constants above were
1/100 s, while the repository separately warns that dark-current defects do not
transfer across a 100x exposure change
(`docs/captures-needed.md:1598-1619`). The requested matched 1 s darks are
therefore necessary.

A single shared 32-frame master is also unsafe. Master-estimation noise becomes
one fixed map subtracted/divided into both outputs. Assuming a `10000 DN` flat,
32 flat and 32 dark frames, the resulting common-master floor is approximately:

| subject signal | `n_eff=9` | `n_eff=55` |
| ---: | ---: | ---: |
| `1000 DN` | `0.028` | `0.151` |
| `5000 DN` | `0.123` | `0.462` |
| `10000 DN` | `0.220` | `0.632` |

The 1/7 FRC threshold is `0.1429`, so a shared calibration master can itself
hold bright/high-`n_eff` rings above threshold.

With **independent** A/B masters, calibration-estimation errors have zero
expected cross-covariance; they add variance and reduce sensitivity but do not
inflate FRC in expectation. The residual expected correlation is therefore
zero **only under** stable DSNU/PRNU, independent flat texture, correct
normalization, and independent calibration noise. Existing scalar measurements
cannot guarantee the ring-resolved residual. It must be measured on held-out
corrected flats/darks at the same sensor coordinates. Fitting or subtracting a
common map from the repeat pair itself is forbidden because it manufactures
the desired answer (`docs/proposals/2026-09-detail-instrument-investigation.md:286-294`).

SPLIT2's independent-noise commissioning read mean `|FRC| = 0.029622` on 16
tiles (`docs/research/M-PHASE0-SPLIT2.md:89-123`). A simple sqrt(site-count)
projection is about `0.0148` at 64 sites, not a registered bar but a useful
expectation for finite-sample scatter around the zero-bias calibration null.
Any coherent ring floor above its frozen interval is residual shared pattern
and must stop the scene measurement.

**Conclusion:** the amended 32-flat/32-dark **per-arm** capture is the
defensible design. After the dark settling discard, each arm still has 30
darks, and both calibration groups have enough observations to split or
cross-fit a residual ring-null without forcing the final master down to an
unproven 16 frames. This count makes the test possible; only the measured
held-out residual can establish adequacy.

## 8. Recommendation and mandatory commissioning battery

### Recommendation

**GO to stand it up and commission it now on synthetic and existing development
data.** The arithmetic is independently verified, the null works, the
common-mode adversary works, the amount-1.5 USM evidence survives withdrawal,
and the reproducible 64-site planning probe shows pre-noise dynamic range. This
is enough to justify the experiment. The 407-frame session remains sealed until
the estimator, bars, and independent implementation audit are frozen.

**NO-GO to pre-admit the current Hann-tiled crossing as M1.** Three decisions
remain open and must be allowed to kill it:

1. whether a frozen 64-site design has power for the approximately few-percent
   comparator differences the program needs, in both defect and improvement
   directions;
2. whether independent 32-frame calibration groups drive every held-out
   fixed-pattern ring below a frozen null; and
3. whether the implemented estimator can supply the required structural
   sharpening argument. The ideal ring-cancellation theorem is not that
   argument once crop/Hann/binning intervene, and the low-pass probes show the
   residual is signed.

If admitted, FRC's defensible meaning is **repeatable scene-information
bandwidth under independent acquisition noise**. It is not a standalone visual
resolution or transfer statistic because a common invertible postfilter is an
ideal null. The original SOTA path itself prescribed “FRC + slant-edge,” not
FRC alone (`docs/proposals/2026-08-sota-path.md:192-197,1525-1534`). A separate
sharpening-safe presentation/transfer instrument is still needed for that
two-instrument claim.

### Battery, frozen before any holdout render

Every arm uses at least **64 independent guarded sites**, physical whenever the
arm is capture-derived. Numerical bars, tile size, ring bins, crossing rule,
censoring, and a fixed-seed
hierarchical bootstrap are frozen before the first challenge arm. Bars do not
move when site count grows. Power is calculated on development data without
reading any arm outcome.

1. **Arithmetic, identity, and untuned null.** Retain the direct-DFT agreement;
   independent-noise pairs must stay within the frozen zero interval, identical
   inputs must equal one, and zero/near-zero-power rings must refuse.
2. **Planted defect.** Attenuate target transfer **before fresh independent
   downstream noise** over a frozen ladder. The statistic must decrease
   monotonically and clear the arm-blind minimum effect.
3. **Planted improvement.** Increase pre-noise target transfer over a matched
   ladder with no low-frequency cue. The statistic must increase and clear its
   frozen minimum. Passing degradation while missing improvement is blindness,
   not safety.
4. **Power replication.** Repeat 2-3 with fresh arm noise and with common random
   numbers. Report the physical-site MDE separately from the paired
   deterministic-plant MDE. The registered decision uses the former.
5. **Structural USM gate first.** Run radius-1 amount-0.5 unclipped-float USM
   before any other challenge, then the historical amount-1.5 box and Gaussian
   forms. Supply either an implementation-level finite-sample proof or a
   pre-registered bound that covers crop, window, bins, and thresholding.
   Empirical non-rejection without that argument is RED.
6. **Boundary/adversarial sharpening.** Run anisotropic USM, boundary-phase and
   narrow-ring fixtures, clipping, quantization, gamma-3, logistic tone, and a
   spatially adaptive sharpener. Any upward claim-bearing result outside the
   frozen equivalence bar, or failure to refuse an out-of-scope nonlinear arm,
   kills the version.
7. **Common post-filter sentinel.** Apply Gaussian low-pass after noise to both
   repeats. Report FRC beside an independent transfer statistic that proves the
   degradation. If FRC is proposed as the sole resolution statistic, its null
   here is a kill; if it is the repeat-information component, this is a
   declared limitation and the companion instrument must catch the blur.
8. **FPN/PRNU plant.** Inject common fields at the measured `0.389 DN` DSNU and
   `0.286%` PRNU, plus dark-current defects and a deliberately shared master.
   Uncorrected/shared-master pairs must go RED.
9. **Real calibration sentinel.** Commission the correction and its ring bars
   on development calibration, then apply the frozen input-only sentinel to the
   holdout's disjoint per-arm flat/dark groups. Report every ring through
   `0.25 cyc/native px`; no pooled crossing may hide one common-mode red band.
10. **Geometry.** Integer shifts must recover exactly. Fractional translation,
    scale, rotation, local warp, crop mismatch, and focus-support mismatch must
    refuse before FRC. No spatial resampling.
11. **Noise, exposure, and content.** Added independent shot/read noise must
    lower FRC monotonically; scalar gain is a null; illumination drift,
    clipping, saturation, flat/no-target sites, and periodic-answer-only sites
    must refuse or provide no detail evidence.
12. **Hallucination and leakage.** A common deterministic pattern absent from
    the independent target must go RED. Site selection, registration,
    calibration, tuning, windows, bins, thresholds, and censor logic are frozen
    on development data, with the existing one-sided lineage perturbation
    retained.

**Decision rule:** if the geometry or calibration gates fail, the capture
cannot support repeat-pair FRC. If either directional power arm fails, FRC is
too blind. If the registered USM arm improves or the structural proof remains
idealized rather than implementation-level, the estimator is not admissible.
Only a complete GREEN licenses FRC as one component of M1; it never licenses
FRC alone as the proposal's full “FRC + slant-edge” detail claim.

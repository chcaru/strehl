# M-FRC-VIABILITY — repeat-pair FRC adjudication

**Status: complete.**

**Verdict:** **NO-GO as M1's detail instrument.** Repeat-pair FRC remains useful
as a secondary repeatability/coherence sentinel, but it is structurally blind to
an arbitrary-strength common linear post-filter, including blur. The incoming
capture is also **not sufficient exactly as written**: its acquisition protocol
does not guarantee matched focus nodes, enough independent eligible sites, or
independent flat/dark calibration residuals.

Claims below are labelled **MEASURED**, **DERIVED**, or **ARGUED**. No RAW was
opened and no heavy computation was run.

## 1. Deadline adjudication: do not shoot the request unchanged

The request gets the central mechanical correction right: it explicitly turns
both body SteadyShot and lens OSS off, holds exposure fixed, uses a coplanar
nonperiodic patch, and asks for two 55-frame `sw4` and two 27-frame `sw10`
passes (`docs/capture-requests/2026-09-319-frame-session.md:56-98,102-127`).
Those are necessary. They are not sufficient.

### 1.1 Independence of A and B

**MEASURED positive:** this sensor's temporal noise is independent from exposure
to exposure to within 1%; ten-frame means on real ISO-100 darks reached
sqrt(N) on all four planes (`docs/research/M62-sqrt-n.md:483-509`). Thus two
separate RAW exposures can supply independent photon/read noise.

**MEASURED negative:** two captures did not decorrelate the observed “flat”
reading. The earlier two-capture FRC was `+0.7310`, higher than the
within-capture value `+0.6569`
(`docs/research/M46-detail-metric-measured.md:135-162`). Its attribution
entirely to FPN was later scoped: that ROI contained real scene structure and
the fitted FPN amplitude was refuted, although the shared-pattern mechanism
survived (`docs/research/SYNTHESIS.md:1167-1170`). Independently, calibration
later measured real sensor-fixed DSNU and PRNU (§7).

**ARGUED capture defect:** two complete focus sweeps started from an “identical
near-focus reset” do not guarantee the same focus motor states, magnification,
or sparse-sweep phase (`docs/capture-requests/2026-09-319-frame-session.md:126-127`).
That is especially consequential for `sw10`: a fractional focus-node offset can
make A and B resolve different material even when both captures are otherwise
perfect. It is a latent mismatch, not independent noise.

**Required change:** at each focus node, expose A and B back-to-back before
advancing focus, then form the two stacks from alternate exposures. If the body
cannot do that, add a separately frozen focus-repeatability gate and enough
fixed-focus witnesses to prove the A/B node ladders coincide. Approach every
reset from the same direction and specify a post-focus-move settling delay; “1 s
interval” is not itself a settling specification.

### 1.2 Frame count is not site count

The 55/27 counts are plausible depth-sampling counts, but they provide one
output pair per step-width condition. They do not provide the independent
replicates used for uncertainty. The registered sharpening admission floor is
at least 64 independent sites, with the bar frozen as sample size grows
(`docs/proposals/2026-09-sota-scorecard.md:513-521`).

That literal 64-site rule currently governs commissioning, not a scored M1
whose computation and bar do not yet exist. But this session is an
irreplaceable holdout; letting it contain fewer than 64 eligible sites would
needlessly risk making the eventual scored instrument underpowered.

The request merely asks whether the patch has power somewhere out to
`0.25 cyc/native px` (`docs/capture-requests/2026-09-319-frame-session.md:149-156`).
A small patch could therefore pass and still leave fewer than 64 usable sites.

**Required change:** require at least 64 guarded, non-overlapping patch sites at
the eventual frozen tile size, and require each retained site—not the frame
average—to have independently repeatable scene power through the licensed band.
For a 256-native-pixel tile this means at least an 8 by 8 usable lattice
(2048 by 2048 pixels before additional guards). Freeze the input-only site
manifest before any render exists. The patch must also stay within the region
whose focus peak is interior to both A/B sweeps.

### 1.3 Registration

Turning stabilization off directly addresses the observed failure: the existing
repeat capture's second light block had nontranslation RMS `0.107703`, reproduced
independently as `0.105202`, over the `0.10` bar
(`docs/STATUS.md:765-824`). The scorecard forbids resizing and spatial
resampling and otherwise permits only tightly gated geometry
(`docs/proposals/2026-09-sota-scorecard.md:214-228`).

For this lane, use the stricter sibling-lane rule: register corresponding
windows by an **integer-only shift**. M88b measured that integer registration
removes a 3-pixel displacement exactly, while a 0.37-pixel resampling leaves a
`2.3987 um` bias; repeated interpolation changes the sign and magnitude of the
edge result (`docs/research/M88b-merge-sharpness.md:74-84`).

**Required change:** no output-derived subpixel warp. Use input-only/disjoint
landmarks, apply at most an integer crop shift, and refuse any pair with
fractional translation, scale, rotation, or local residual outside its frozen
gate. Per-node A/B exposure is the cheapest way to make that refusal rare.

### 1.4 Flats and darks

The counts might be salvageable; the specification is not. It says only
“flats 32” and “darks 32” (`docs/capture-requests/2026-09-319-frame-session.md:84-98`).
It does not say:

- that A and B receive independently estimated calibration maps;
- how the 32 frames are partitioned;
- that flats are spatially uniform, unsaturated, and sufficiently defocused or
  moved to suppress target texture;
- that darks are temperature- and exposure-matched, with settling frames
  discarded; or
- how residual same-coordinate correlation is validated.

Those omissions are load-bearing. The existing flat campaign showed that paper
fibre texture is exactly confounded with PRNU unless defocus or another
independent lever removes it (`docs/captures-needed.md:1276-1310`). The
repository's corrected flat prescription says 16 frames per level are enough
for PRNU precision, provided smooth-field normalization and temporal-floor
subtraction are done correctly (`docs/captures-needed.md:1428-1451`).

**Minimum amendment retaining 319 frames:** preassign 16 flats and 16 darks to
calibration A and the other 16+16 to calibration B; acquire the two flat groups
with independently moved/rotated diffuser texture; never apply one estimated
master to both outputs. This has no independent validation reserve.

**Recommended amendment:** 32 flats + 32 darks **per realization** (64+64
total; 383 session frames), allowing independent masters and split-half
residual validation. Darks should be 1 s, ISO 100, at the warmed session
temperature, with the first two frames in each group discarded. Flats should
remain at the same RAW exposure settings, land safely below saturation at high
signal, and use an integrating/defocused field rather than resolved paper.

### 1.5 Subject, tilt, exposure, and timing

The coplanar fine irregular patch and roughly 1-degree tilt are the right
stimulus shape (`docs/capture-requests/2026-09-319-frame-session.md:56-82,120-127`).
The arrival check must, however, measure **cross-power attributable to the
subject**, not raw single-frame power that sensor pattern or noise can satisfy.
It must run per site, reject clipping, and verify an interior through-focus peak
in both A and B. With crossed polarizers, take a pre-session test exposure to
ensure the 1 s setting is neither clipped nor photon-starved. Specify a real
settling interval after each focus move.

**Deadline answer:** **NO, not exactly as specified.** The minimum text changes
are paired exposures at each focus node (or an equivalent proved node-repeat
gate), 64 eligible guarded sites, independent A/B calibration partitions with a
real flat protocol, and explicit focus settling.

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
SPLIT2 separately records the same sign: crossing movement `-0.000754` while
naive acuity rose `1.832679x`
(`docs/research/M-PHASE0-SPLIT2.md:89-108`).

But it is **not scorecard-admissible M1 evidence**:

- it has 16 synthetic tiles, not 64 independent physical sites;
- it is one common-linear transformation, the exact class FRC is structurally
  blind to;
- its first per-ring `5e-4` requirement failed at `0.010859` and was amended,
  before real pixels but after seeing the synthetic control
  (`experiments/M-PHASE0-SPLIT/PREREGISTRATION.md:124-141`); and
- the current scorecard explicitly says no admissible sharpening-safe detail
  statistic exists and requires both structural protection and the complete
  battery (`docs/proposals/2026-09-sota-scorecard.md:469-521`).

The accurate program statement is therefore:

> One FRC implementation survived two synthetic, identical common-linear
> sharpening controls, including amount 1.5. No admissible detail statistic has
> survived the registered 64-site battery.

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

## 5. Responsiveness: safe by blindness

`BUILD-SHARP` calls the paired edge instrument “18,644x more responsive than
ring FRC” (`docs/research/BUILD-SHARP.md:166-173`) and points to M88b's direct
plant. A Gaussian low-pass from sigma 0 to 2 pixels changed FRC@0.25 from
`0.9742` to `0.9756`—an increase of only `0.0015`, in the wrong
direction—while 10–90 edge rise widened from `14.258` to `41.619 um`
(`docs/research/M88b-merge-sharpness.md:45-59`).

The published “18,644x” is not a statistical-power ratio: it divides micrometres
by a dimensionless FRC change and supplies no FRC sampling floor. Normalized to
their own baselines, the same table is about **+191.9% edge width versus
+0.1507% FRC**, still roughly 1,274x apart and still wrong-signed. The
qualitative conclusion is decisive even though the headline ratio is
dimensionally invalid.

**Smallest detectable effect:**

- for a common nonzero linear post-filter applied after noise, **no finite blur
  magnitude is identifiable**. It is in the exact null space under the theorem;
  more sites only estimate the same null more precisely;
- for pre-noise optical transfer changes, FRC can respond because the signal is
  attenuated before fresh downstream noise. No repeat-pair site-variance curve
  or minimum detectable effect exists in the repository, and v1.6 deliberately
  has no active M1 numeric bar
  (`docs/proposals/2026-09-sota-scorecard.md:497-521`);
- the existing harness has power against large misregistration—FRC at
  `f_sig` fell `0.9477 -> 0.6663 -> 0.2049` over 0, 1, and 2 pixels—but that is
  nuisance sensitivity, not detail sensitivity
  (`docs/research/M46-detail-metric-measured.md:187-205`).

The 64-site floor is therefore necessary but cannot rescue the structural
blind spot. FRC can reject **uncorrelated** inventions. It cannot penalize
deterministic blur, deterministic ringing/hallucination, shared sensor pattern,
or any sharper/noisier versus softer/cleaner trade that leaves normalized
coherence unchanged. That kills it as a sole resolution/detail comparator.

## 6. What blocks repeat-pair FRC today

The existing fixed-focus repeat set is genuine, but stabilization was on and
introduced 1–2 quad-pixel motion; after unitary translation correction, one
light block still failed the local nontranslation gate at `0.107703`, reproduced
at `0.105202`, so the lane correctly retained no real FRC
(`docs/research/M-PHASE0-SPLIT2.md:1-13,39-87,124-155`). The later program
diagnosis names the complete blocker set: spatially varying geometry,
data-dependent registration, and stable sensor structure that its ABBA null
cancels rather than tests (`docs/STATUS.md:1423-1448`). Unblocking therefore
requires a stabilization-off matched acquisition, registration chosen from
disjoint/input-only data with integer-only application, and independently
estimated sensor calibration whose held-out residual correlation passes a
frozen gate. The incoming capture addresses only the first of those completely.

## 7. Shared fixed-pattern noise and the 32+32 question

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

Conclusion: 32+32 is numerically plausible only as predeclared 16+16
independent masters, with no validation reserve. As written, it is inadequate.
The recommended 32+32 **per realization** is the defensible capture.

## 8. Recommendation and mandatory commissioning battery

### Recommendation

**NO-GO:** do not stand up repeat-pair FRC as M1's replacement detail
instrument or as a claim-bearing resolution crossing.

**Conditional GO:** retain it as a secondary repeatability/coherence channel
that answers, “which output Fourier content repeats across independent
noise realizations?” It may help reject uncorrelated noise or unstable
selection. It cannot answer, “which output preserves more resolution?” Until a
separate sharpening-safe transfer/detail instrument exists, it cannot restore
the proposal's two-instrument D1 claim.

### Battery, frozen before any holdout render

Every arm uses at least **64 independent guarded physical sites**, 10,000
fixed-seed hierarchical bootstrap draws by capture then site, and bars selected
by an arm-blind power calculation. Bars never move as sites are added.

1. **Identity and untuned null:** independent-noise pairs read zero within the
   frozen equivalence bar; identical inputs read one; zero-power rings refuse.
2. **Planted defect:** attenuate the target OTF **before fresh independent
   noise** at several known strengths. FRC must decrease by the frozen minimum
   effect with correct ordering.
3. **Planted improvement:** improve the pre-noise OTF/target modulation before
   fresh independent noise. FRC must increase by the independently powered
   minimum. A metric that passes only the defect arm is blind and fails.
4. **Common post-filter sentinel:** apply Gaussian blur after noise to both
   realizations. Record the predicted FRC null beside a transfer metric that
   proves the images degraded. This arm is the explicit limitation, not a pass
   as a resolution instrument.
5. **Sharpening/tone boundary:** radius-1 amount-0.5 float USM first, then the
   amount-1.5 historical arm, anisotropic USM, gamma-3, logistic tone, USM plus
   clipping, quantization, and a spatially adaptive sharpener. Any upward
   claim-bearing result or failure to refuse kills the frozen version.
6. **FPN/PRNU:** inject common fields at measured `0.389 DN` DSNU and `0.286%`
   PRNU; include a deliberately shared-master plant. The instrument must refuse
   uncorrected pairs, and independent calibration must remove the held-out
   cross-ring floor below a frozen bar.
7. **Real calibration sentinel:** cross-fit independent flat/dark masters and
   score held-out corrected frames at identical sensor coordinates. Report
   every ring through `0.25 cyc/native px`; no aggregate may hide one red band.
8. **Geometry:** integer shifts must recover exactly. Fractional translation,
   scale, rotation, local warp, crop mismatch, and focus-node mismatch must
   refuse before FRC. No spatial resampling.
9. **Noise and exposure:** added independent shot/read noise must lower FRC
   monotonically; scalar gain is a null; spatial illumination drift, clipping,
   and saturation must refuse.
10. **Content and anti-answer controls:** flat/no-target sites provide no detail;
    periodic-only targets cannot qualify; deterministic hallucination and
    common checker patterns must not be mistaken for independent reference
    information.
11. **Lineage/leakage:** site selection, registration, calibration, windows,
    bins, thresholds, and censor logic are frozen from development data. The
    319/383-frame session remains sealed until the complete battery passes.

If the capture protocol is amended, the incoming session can fuel this
secondary channel. It cannot cure FRC's structural blindness, so it does not
change the primary **NO-GO**.

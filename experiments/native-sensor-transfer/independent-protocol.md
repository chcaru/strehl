# Native sensor transfer: independent protocol

Status: SOURCE-ONLY prospective protocol. Draft1 is preserved as
independent-protocol-draft-1.md (32176B/SHA256
33896928666bb0ec8cbd42d7f40e730afc71b0cb684219c250cab2472daa2082); its
162-decode observer proposal is superseded before execution by the fixed table below. No RAW/image was opened, no synthetic
array/control, decoder, producer, compiler or checker was executed in preparing
this file. Root release and independent source-choice review remain mandatory.
This document fixes the independent choices before those operations; it is not
an execution grant or an assertion that the premises will hold.

## Question and limits

Compare the frozen supplied sensor noise model with temporal observations at
one actual native Crop consumer. The strongest available conclusion is a local,
conditional transfer diagnostic. Five paper repetitions cannot establish a new
photon-transfer curve, physical stationarity, a calibrated confidence interval
for an entire sensor, or a quality/SOTA improvement. Calibration parameters are
never fitted to this data. There is no registration, illumination correction,
frame rejection, site selection from residuals, or second capture selection.
A failed paper premise does not erase an interpretable dark diagnostic.

The independently re-chosen primary paper statistic uses two disjoint frame
contrasts and a fifth frame only for signal prediction. The all-five variance
is retained as sensitivity, not called an independent replication. The same
files, actual consumed arrays, and all refusal prefixes remain visible.
No scalar green covariance patch or automatic gain correction follows a result.

## Fixed source population and coordinate gauge

Exactly the charter's 27 originals, in numeric filename order:

* Paper: requests/10-paper-iso-var/DSC00235.ARW through DSC00239.ARW, five.
* Dark: requests/6-11-extended-dark-frames/DSC00872.ARW through DSC00893.ARW,
  twenty-two. Both paths are rooted at D:/personal/macro.

Recorded ISO160, exposure1/8 second and f/5.6 are inherited capture metadata,
not proof of identical temperature, illumination, release mode or sensor state.
The blocks were recorded about2h39m apart. Do not subtract dark from paper or
use this dark block to refit the paper read floor. Root's metadata-only inventory
reports27 present files,926855168 encoded bytes, maximum38825984 bytes; these are
not yet decoder observations or permission to read payloads.

Root selected ONE128x128 CFA-plane Crop, quad origin(x,y)=(1694,1108), within
inherited native active quad geometry3516x2344. Its relative sensor rectangle
is x=[3388,3644), y=[2216,2472). The inherited native active sensor rectangle is
(0,0,7032,4688), inside7168x5120 decoded storage. Actual matching metadata on all
27 files is a release-time predicate, not assumed because an earlier file had
that geometry. No origin/width adjustment after decoding is permitted.

Local plane coordinate(u,v) maps to full decoded photosite
(active_x+2*(1694+u)+dx, active_y+2*(1108+v)+dy). Output/plane order is explicitly
R,G1,G2,B, with offsets(0,0),(1,0),(0,1),(1,1). Do not confuse this order with
CfaPlane enum storage. Preserve all four planes at every selected site. Native
code units are u16 before subtraction and f32 afterward; no WB/exposure/white
normalization is introduced in the independent sensor statistics.

All128x128 sites are retained; there is no residual-based crop or bad-pixel mask.
For independent within-plane covariance use exactly offsets(1,0),(0,1),(1,1),
(1,-1), with valid overlap only, all four planes. Retain all six same-quad
cross-plane pairs. These finite neighbours do not establish a complete sensor
covariance field. The same-quad G1/G2 pair alone must not be called a distinct
physical green mechanism; M72 already answered that choice negatively.

## Same-file independent decode domain

Use rawpy/LibRaw public API once per original, isolated and bounded by the later
root ledger. Do not read decoder implementation source. Authenticate exact
original bytes/identity and decode that same file snapshot with source stability
before/after. Within the live RawPy context, copy only the fixed256x256 sensor
rectangle from raw_image, not raw_image_visible. Record full buffer shape,
visible rectangle/margins, native active rectangle, CFA letters at the actual
sensor origins, black levels, generic white, camera-channel whites and WB.
Require full raw buffer7168x5120, top_margin=left_margin=0 and flip=0. The
independent copy is literally raw_image[2216:2472,3388:3644]. A different
orientation, raw origin, active origin or buffer size refuses; never translate
by a convenient visible margin. Native ISO/camera fields and held capture metadata
are separate evidence: rawpy does not supply an independent ISO/camera metadata
parser here. No new metadata-decode campaign is introduced. Copy the ROI into owned contiguous u16 storage before closing;
no LibRaw view survives close. Full ROI and256 individual row hashes must exactly
match the producer's pre-transform u16 ROI, on every original. No tolerant pixel
comparison, common prefix, visible-domain substitution or extra cropped columns.
The old rawler7032 versus rawpy7028 visible width remains explicitly reported.
This comparison establishes decoder agreement on consumed addresses, not the
physical validity of every declared active photosite.

For used CFA channel indices require all four independently exposed black levels
to equal the producer scalar, and present positive integer camera-channel white
levels to be uniform and equal its scalar. Retain generic white independently;
do not choose whichever white happens to match. Historical generic16383 versus
camera15360 is a known policy distinction, not a new observed result. Missing or
mixed used-channel metadata refuses this association. Camera/ISO/geometry/levels
must match the frozen constructor contract; fallback provenance does not qualify.

Reuse the admitted sensor-domain/lifetime and white-authority conventions from
M193c. New independent source may factor only ordinary file/decoder ownership;
it must not import the producer's extraction, pyramid or estimator functions.
No additional no-data imported-runtime capture is proposed. Record actual public
module versions/file identities and supplied runtime authority with its stated
scope; do not claim complete DLL/cache/runtime closure.

## Actual consumer configuration and observations

Keep configured MergeConfig.bands=7, the actual production default. Source
level_sizes stops before a dimension below8: actual sizes128,64,32,16,8 give
four Laplacians plus base. exponent_at uses actualnb=4. This is current opt-in
Crop behaviour, not the full-native seven-Laplacian consumer. Keep gate2,
exponent2,sharpen_per_octave1.4,SoftPower,HardFloor,BaseMean,mean_coarse0,
InputRange hull and Mean fallback; pin the entire config and all environment-
derived defaults in the producer contract. No policy comparison or altered gate.

The actual constructor is profile::noise_model_for -> by_model ->
CameraProfile::noise_model, not noise_model_for_with. A7C2 frozen inputs are
base_iso100,gain_divisor436.8,read_noise_e_low4.20,second_base_iso400;
at ISO160 gain is the actual f32 evaluation160/436.8. The same PlaneNoise is
copied four ways, Profile provenance, PRNU absent. Retain every actual f32 bit,
levels and constructor/source identity. Do not apply measured-gain corrections,
PRNU, dark subtraction, or an automatic1/12 DN^2 quantization term. The empirical
read floor was fitted in DN and another quantization term can double-count it.

Two routes are served sequentially by each current decoded Frame: no-map and
placed-identity. A bounded temporary Frame clone feeds the unchanged actual
fold; it is dropped before the next original. This is not a retained aligned
stack. Root's prospective reduced witness schedule is:

| Invocation | Feature/observer | Originals | Decodes | Actual folds |
| --- | --- | --- | ---: | ---: |
| primary-paper | feature-on/on | all5 paper | 5 | 10 |
| primary-dark | feature-on/on | all22 dark | 22 | 44 |
| paper-off | feature-on/off | same5 paper | 5 | 10 |
| paper-placebo | feature-on/placebo | same5 paper | 5 | 10 |
| dark-prefix-on | feature-on/on | first2 dark, DSC00872..873 | 2 | 4 |
| dark-prefix-off | feature-on/off | same2 dark | 2 | 4 |
| dark-prefix-placebo | feature-on/placebo | same2 dark | 2 | 4 |
| paper-feature-off | feature-off | same5 paper | 5 | 10 |
| dark-prefix-feature-off | feature-off | same2 dark | 2 | 4 |

Total50 native original decodes,100 actual folds,50 real fullres warps and50
probe synthetic warps, plus27 independent original decodes. Preparation/prologue
must reuse its first decoded frame explicitly or account for an additional
actual decode before release; no invisible metadata decode is allowed. The
producer's final exact call table must match this table before any run. The
primary-paper on result supplies the paper triplet; the22-dark result does not
supply a two-dark output. The dark-prefix on is therefore its own invocation.
Paper5 and dark-prefix2 output hashes witness observer and feature insertion on
these exact native inputs/counts. They do NOT prove whole22-dark output neutrality.
No primary off/on result is relabelled as a fresh invocation. Private probe
synthesis is additional resource work, not a new original decode or sensor draw.

No-map does not enter the warp or measured-floor probe and must retain an empty
per-frame beta prefix. Placed-identity supplies a literal placed Similarity with
unit scale/zero rotation/zero translation to the existing native route; it still
executes its actual gather and floor probe. Default fullres gather internally
uses MHC/WB and may compose channel-specific CA from actual frame context.
Do not disable those paths merely to make the arms equal. Retain actual gather
mode, nominal map, effective channel transforms, CA context, defect choice and
all relevant switches. Root permits a cfg(test+feature) read-only callback at
the existing actual resolved t_site, with no extra lookup, transform arithmetic
or per-pixel logging; this is the actual-map witness, not a second resolution. Neither arm introduces an RGB input adapter. Root
scope-amendment-2 resolves the original wording: internal native reconstruction
is preserved; a new external RGB-input path is excluded.

The observer must read actual operands at the shared production seams, without
building an otherwise unused PlaneCache coefficient. Retain per original:
pre-transform ROI u16; actual post-gather/pre-clamp ROI u16 (linked to the same
observed source bytes in no-map); four consumed clamped planes; actual green luma; actual
injected variance; actual level L_k and Gaussian V_k; E_k=smooth5(L_k^2);
selected beta and its white/measured source; actual exponent/significance;
weight; bypass labels; and four final collapsed planes. The floor and above-floor
classification are DERIVED from recorded actual E,V,beta,gate operands using the
source operation order. They are not direct scalar observations from inside the
weight closure. There is no new per-pixel logger merely to change that label.
At each level keep full arrays (or lossless fixed coverage with identical scope),
not selected favourable coefficients. Actual coefficient coverage limited by a
production cache-read path must be identified; do not fabricate an observation.

The specified paper5 and dark-prefix2 observer triplets MUST give identical bytes
for each route's final collapsed-plane serialization: exactly four128x128 f32
planes in R,G1,G2,B order, little-endian bits,262144 bytes per route output.
After each of the18 finished routes, invoke the EXISTING write_merged once:
camera-native linear, Exposure::None, restore None, demosaic true and actual
levels/WB. Retain that whole TIFF too; no new writer, refold or redecode. Require
whole TIFF byte identity within the same declared witness populations as f32.
The floating-point equality remains mandatory because output quantization could
hide an observer perturbation. This is output-path preservation, not a TIFF
sharpness/noise/quality metric. Feature-off comparisons preserve actual truthful
source/build identities while the existing measurement writer remains in scope.
Placebo allocates/touches the same retained shapes without reading merge state.
Within each triplet and corresponding feature-off comparison, require actual
input/config identities, distinct truthful feature/source identities and counters.
The primary22-dark diagnostic carries the bounded observer-witness limitation.
There is NO required no-map/placed-identity output equality. A difference can
come from current gather/CA or beta, rather than sensor calibration. Before
reusing a no-map sensor prediction for placed-identity green, require exact
per-frame consumed-green equality plus a source-supported transform association;
otherwise label its physical prediction NOT_IDENTIFIED and retain actual temporal
observations/native normalization. Do not silently assert identity or fit a warp.

## Crop support, phase and floor prediction

Independent filtering uses the fixed binomial[1,4,6,4,1]/16, replicate boundaries,
reduce centres2*x, expand even[1,6,1]/8 and odd[1,1]/2, horizontal then vertical.
Never smooth across the temporal axis. Preserve real-arithmetic comparison and
actual f32 operands separately; a floating discrepancy is not sensor noise.

For G_k, radius is2*(2^k-1). At coefficient q, L_k radius is
(6*2^k-2) for evenq and(5*2^k-2) for oddq. For E_k's complete smooth5 support,
radii become(8*2^k-2) and(7*2^k-2), about source centre2^k*q, independently per
axis. They follow by composing the actual reduce/expand stencils; boundary
repeated taps refer to the SAME original variable and must be combined before
squaring weights for variance. They are not independent draws.

The E full-support safe index intervals are inclusive5..121,7..57,7..25,7..9
for k0..3. Their2D counts are13689,2601,361,9. These are source-derived expected
counts, not measurements. Partition each band into eight disjoint strata:
full-support versus boundary-dependent, each crossed with(x%2,y%2) in
(0,0),(1,0),(0,1),(1,1). Retain all strata, including small or empty ones.
Boundary coefficients are valid crop-consumer observations; they do not inherit
interior white beta. k3's nine supported coefficients are not meaningful spatial
replication and receive no pooled or scalar inferential confidence claim.

The probe's measurable cap min(4,sizes.len()-2)=3 means k3 is NOT attempted.
Its hypothetical trimmed12x12 population would also miss the minimum256, but
that is not the reached cause. k0..2 trimmed sizes96,48,24 contain9216,2304,576. With scaling/debug disabled and this
geometry, source expectation is a finite3-value beta prefix and white fallback
for k3. Retain actual prefix/NaNs/fallback and counts; unexpected behaviour stops
that association rather than substituting a desired beta. Historical0.5% probe
precision on a different domain is NOT the tolerance for this tiny crop.

Pyramid measurement has three different scales:
(a) temporal Var(L_k), (b) smooth5(temporal Var(L_k)), the noise term on E's scale,
(c) actual native beta_k*V_k, with floor=gate*(c). E itself contains scene energy
and is never used as a temporal variance. Report smooth5((mean_t L_k)^2) separately
with the finite-repeat noise contamination stated; do not subtract it into a
quality result. Base is averaged, not a gated fifth observation. mean_coarse and
significance bypasses remain explicit; actual gate exercise needs actual positive
and zero weights, with zero-underflow distinguished from threshold rejection,
not a theoretical threshold.

## Temporal estimators and independent prediction

Let X_t(s) be the same actual scalar site/plane/luma/band across the fixed T
frames. Retain arithmetic in binary64 for independent statistics. For all frames,
S2=sum_t(X_t-mean X)^2/(T-1). Temporal df/site is4 for paper and21 for dark under
independent repetitions. It is never4*16384 or21*16384. Fixed-pattern offsets
cancel from these same-site contrasts; time-dependent illumination does not.

Primary paper contrasts are d0=X0-X1,d1=X2-X3; Q=(d0^2+d1^2)/4. Prediction
uses frame4 only. Dark uses11 disjoint contrasts d_j=X_(2j)-X_(2j+1), j0..10,
Q=sum d_j^2/22. Do not subtract the mean of the pair contrasts: that removes
another degree of freedom and changes the defined target. Pairwise covariance
is C_ab=sum d_ja*d_jb/(2J); retain variance/covariance units before any rho.
Zero variance makes rho unavailable, not a fabricated zero. Retain each pair
component d_j^2/2 and its contribution to every pooled number. All-T centred
covariance is a second explicitly labelled sensitivity estimate.

Reconstruct and assert the green identities independently for both signed
preclamp G=(G1+G2)/2 and actual per-site-clamped G:
Var(G)=(Var(G1)+Var(G2)+2Cov(G1,G2))/4. These algebraic identities are association
checks, not independent calibration validation. The six cross-plane covariances
and four neighbour offsets keep a green-only explanation from being selected by
omitting the alternatives. Use actual overlapping site sets for BOTH endpoints;
never pair different crop extents and call the covariance changed.

Paper signal witness is Sref_p(s)=f64(raw_frame4_p(s))-actual_black, using the
independent owned u16 decode. With no paper clipping/nearblack refusal, the frozen
prediction per photosite is q_p=g_p*Sref_p+(RN_p*g_p)^2. It has no fitted parameter.
For green use qG=(qG1+qG2)/4: separate signal witnesses for the two photosites,
not the producer's current noisy luma. Record qG versus actual native var_t at
EVERY frame; native luma_variance evaluates green_luma_sigma at that frame's
consumed luma, then sqrt/square in f32. Its data coupling is part of the subject,
not a substitute for this disjoint signal prediction.

For dark signed preclamp codes compare with frozen r_p^2=(RN_p*g_p)^2. The
comparison is conditional on negligible dark signal and the old profile's
relevance to this separate capture state. Retain observed mean/black offset,
variance and covariance; do not use them to change r, black or q. For clamped
dark planes/luma/bands report the actual nonlinear transfer Q_after/Q_before,
clamp fractions and native q/beta/floor. Do NOT call applying the unclamped
sensor law to max(raw-black,0) a valid physical prediction. A Gaussian clipping
formula would add a distribution/mean assumption; it is not silently introduced.

For no-map paper, independently compose the finite linear Laplacian operator H
from literal stencils. Exact diagonal-model prediction at a band site is
B_k=sum_s H_k(s)^2*qG(s). On E's scale use smooth5(B_k), not a Gaussian reduction
of variance. Shared boundary addresses are coalesced BEFORE squaring. This is
conditional on spatially independent photosites: it intentionally does not fit
observed covariance into the predictor. Save separately:

1. Q(L_k), smooth5(Q(L_k)), and each pair's contribution;
2. B_k and smooth5(B_k), from independent frame4 qG;
3. beta_white*GaussianReduce_k(qG), and actual per-frame selected-beta*V_k;
4. native E, floor, weight and threshold side, with source-only and observed
   predicates separately labelled.

Compare(1)/(2) for the diagonal sensor-transfer diagnostic;(2)/(3)'s independently
predicted term for finite-crop/white-scalar approximation; and actual(3) versus
its disjoint prediction for current-input coupling. Do not attribute a mismatch
to gain until these different stages are distinguished. The measured finite
neighbour field is diagnostic context, not enough to reconstruct full HCovH'.
For dark, analogous B from r^2 is a PRECLAMP counterfactual only. For placed
identity, green prediction eligibility is as specified above; an ineligible
arm still retains(1) and actual(3)/(4), labelled no independent physical predictor.

Use the eight fixed support/phase strata per band. At level0 also report exactly
sixteen32x32 spatial blocks, row-major, and the complete crop. For each pooled
variance take the mean of site variances, then square-root only if an RMS sigma
is needed. Never mean site sigmas, spatially demean image texture into a temporal
estimate, or replace the full crop with a favourable quantile. Retain block min,
max and all sixteen values; their range is dispersion, not a confidence interval.
Per-band strata need no additional data-driven subdivision.

Fixed scalar uncertainty witnesses are local(64,64) for each of the four signed
photosite planes and green luma, plus source-centred band coordinates(64,64),
(32,32),(16,16) for k0,k1,k2. No boundary or k3 inferential witness. These8 sites
per block/eligible route are selected independently of values. Give pointwise
95% conditional Gaussian intervals for variance:
[J*Q/chi2_(J,.975), J*Q/chi2_(J,.025)], with J=2 or11.
The all-T version uses df=T-1. No multiple-site or family-wide PASS follows a
pointwise interval. Quantized ISO160 codes, temporal dependence, drift and clamp
invalidate unconditional chi-square coverage; clamped values receive no such
coverage claim. No interval for smooth squared energy is called chi-square.
Use a pinned standard-library/numerical inverse-CDF implementation only after
root reviews the checker, with fixed reference-quantile controls; no simulation-
estimated quantile or post-hoc interval choice.

Frame4 is independent of the primary paper contrasts, but is a noisy signal
witness. Preserve this uncertainty term instead of treating qG as known truth.
Conditionally under the diagonal frozen model,
Var(q_p)=g_p^2*q_p and Var(qG)=(gG1^2*qG1+gG2^2*qG2)/16.
For any linear functional a of q, use sum a_s^2 Var(q_s) as the model-conditional
reference variance and (sum |a_s|*sqrt(Var(q_s)))^2 as the fully correlated upper
bound; report both assumptions. This is plug-in uncertainty under the hypothesis,
not a newly calibrated confidence statement. Profile parameter uncertainty is
unavailable and explicitly unquantified. A ratio/interval overlap cannot establish
an unconditional physical-model PASS. No engineering band is invented after data.

## Paper nuisance premises: fixed input-only screens

Screens consume only independently decoded no-map input green arrays; they do
not read the supplied noise model, predicted variance, temporal variance result,
selected weights or output image. Every one of five frames remains in the saved
record. A triggered screen stops paper physical-transfer interpretation, while
dark interpretation and exact implementation checks remain available.

A. Domain/headroom: all four paper planes in all5 frames must be within
[black+64,white-64], inclusive. This is a prospective nearblack/saturation guard,
not an assurance of linear sensor response. Count all violations, never mask
individual sites. Dark is exempt and instead reports raw/clamped domains.

B. Illumination/offset: use green means over the fixed central96x96 rectangle
[16,112)^2 and its four48x48 quadrants. Compare each frame0..3 with frame4.
Trigger if any absolute mean change exceeds8 DN OR exceeds0.5% of the absolute
frame4 mean above black (both criteria are retained; either triggers). These
are fixed effect-size screens, not model-derived sigma tests. Even a non-trigger
cannot exclude smaller nuisance, and shot noise may trigger an honest refusal.

C. Gross motion/structure: within the same central96x96 reference rectangle,
compare frame0..3 to frame4 at each of exactly nine source offsets(dx,dy) in
{-1,0,1}^2. For scoring only, remove each patch's scalar mean; DO NOT modify any
array used for variance/prediction. Score mean squared differences of disjoint
4x4 box means (24x24 values) at each fixed offset. Require frame4's centred4x4-
box-mean RMS>=8 DN, otherwise classify motion premise UNRESOLVED_LOW_TEXTURE.
Trigger gross-motion/structure refusal if any nonzero offset improves the zero
score by more than25% AND more than4 DN^2. Retain all36 comparison vectors and
the zero scores; no chosen transform is applied. Ties do not prove stationarity.
Subpixel motion, focus changes, periodic texture and joint noise can evade or
trigger this screen. Non-trigger is only NOT_DETECTED_AT_FIXED_SCREEN, never
motion-free ground truth. The fixed sample remains useful as conditional evidence;
without independent physical stationarity truth it cannot become calibration.

D. No after-the-fact nuisance removal: no framewise gain/offset fit is applied,
no defect/PRNU/row/column subtraction is inferred from these controls, and no
correlation-selected sites replace the crop. Dark temporal drift is reported via
all11 pair components,22 frame means and all22-versus-pair sensitivity. It is
not paper illumination and need not share the paper screen disposition.

## Fixed prospective independent control groups

These are source definitions for a later finite release, not executed evidence.
Twenty ordered result groups, each retaining all listed variants before aggregate
status. Synthetic/helper portions execute before the independent RAW decode;
actual output/exercise portions of17/18 complete only when those saved producer
arrays are read and associated. They cannot prove producer neutrality before the
producer has run. Metadata provenance20 is checked before scientific reads.
The exact per-group phases are source-fixed, with no repeat of successful portions.
Every negative calls the SAME predicate used in the saved-data path, records its
specific refusal/changed value, and is followed by restoration. Never accept an
unrelated exception as a successful negative. Fixture construction is independent
of the producer. Root/producer integration must preserve these20 groups rather
than adding an unreviewed campaign. Existing completed M193c controls are cited
as prior conventions, not relabelled as new execution.

01 domain-owned: literal uint16 full buffer12x16,500+31*y+3*x, ROI(4,2,8,6),
   distinct visible origin; inside-context copy versus poisoned close. Actual
   owned oracle bytes/rows/CFA must match; late/borrowed copy must refuse.
02 domain-address: actual ROI shifted by2 columns (same shape) must reject
   full/row bytes; restoredROI passes. This powers address, not just metadata.
03 white-authority: primary12000, camera[12000]*4, generic16383 positive;
   generic12000/camera[11000]*4, mixed/absent camera and malformed bool refuse;
   restored camera positive. Existing policy, no fitting to actual15360.
04 temporal-pair: signed values[-4,4,-4,4,0]+1000 at every site give primary
   paper Q32 and all5 S2=16 exactly. Mean-centred-pair result0 must reject;
   missing-factor-two Q64 must reject; restore32. This deliberately demonstrates
   that the two estimators need not agree on a finite deterministic witness.
05 temporal-dark:22 literal values alternating-4,+4, plus1000: pairQ32 and
   all22 S2=352/21. WrongT divisor and one omitted pair must reject exact
   population/value association, then restore. No Gaussian claim for this plant.
06 covariance: both green sequences equal group04 residuals: pair covariance32,
   greenQ32 and zero-covariance diagonal16; opposite green sequence yields
   greenQ0/covariance-32. All four-plane/neighbor finite pair addresses retained.
   These independently known inputs power sign and covariance omission.
07 signal-separation: add+16 DN to all four paper frame4 photosites only. Primary
   pairQ is unchanged. Each photosite q_p changes by16*g_p; qG changes by
   (16*gG1+16*gG2)/4, equal8*g for the frozen equal-gain greens. Native luma
   signal changes by16 DN but its variance prediction changes by8*g, not16*g.
   An all5-derived prediction must fail the separate-source association. Restore.
08 noise-scale: three declared variants within this group: multiply the saved
   gain by4 with RN unchanged, multiply saved RN by4 with gain unchanged, and
   independently replace the correctly computed whole q by4*q. The first two
   must reject immutable source/operand identity; neither is claimed to scale
   total q by4 because the read term squares. Only the third, literal q-scale
   destroyer must change a fixed positive measured/q ratio to exactly one-quarter
   within the fixed binary64 bound, without altering measured samples. Restore
   each original. A plant using its own noise constant validates transfer
   arithmetic, not physical gain calibration.
09 clamp: preblack residuals[-4,4,-4,4,0] and black512 produce pairedQ32 before
   and8 after site clamp; a before/after-domain swap must reject. No use of the
   dark sensor-law predictor as a calibrated postclamp law; restore labels/data.
10 support-boundary: independent impulse and constant1 witnesses on128^2;
   replicate boundary's repeated addresses coalesced before squared-H prediction.
   An implementation treating copies as independent must disagree at the fixed
   corner; full-support/phase membership and restore required. Actual H must
   annihilate the constant at every Laplacian coefficient within float bound.
11 phase-filter: five literal fields1000+20*t+(t+1)*(3*x+7*y+((13*x+29*y)%17)),
   t0..4, on128^2; the nonconstant temporal amplitudes power temporal smoothing;
   wrong expand even/odd phase, dropped end tap and smoothing temporal axis each
   reject the actual independent transform association, then restore. Retain
   independently constructed scalar stencil operands at corner and(64,64).
12 energy-domain: actual E for a noiseless structured sequence repeated5times
   is nonzero at an exercised site while temporalQ=0. Substituting E as temporal
   variance must fail; smooth5(Q) remains0. This is a flat-temporal null, not a
   photographic quality assertion.
13 headroom: literal all-plane1000 plus group04 residuals with black512/white12000
   passes; one sample black+63 and one white-63 separately trigger exactly the
   domain screen, restoration passes. Dark does not inherit this paper premise.
14 illumination: fixed textured baseline allframesidentical, then frame0+32 DN,
   then frame0 scaled by1.02 with exact declared integer rounding. Each actual
   input-only mean screen must trigger; restored baseline must not. Literal
   thresholds remain fixed, and prediction/noise-model mutations leave screen
   outputs unchanged.
15 motion: baseline field1000+20*x+30*y+200*((x//8+3*(y//8))%2), identical5frames,
   fixed source shift(+1,0) in frame0 and restored baseline. Actual nine-shift
   score must exercise RMS>=8 and reject shifted structure; no repair follows.
   All-constant baseline must return low-texture unresolved, not stationarity.
16 white-beta-fallback: actual saved per-frame prefix/white source metadata is
   checked against requested7/actual4, expected prefix3. A carried previousframe
   beta on no-map, fabricated measuredk3 or wrong selected beta must reject;
   original/restored routing passes. The numeric beta precision is not assumed.
17 same-path-observer: actual separately executed off/on/placebo plane bytes
   and whole existing-writer TIFF bytes of the18 fixed route outputs must match
   within each declared witness, with
   source/input/config/arm
   association. An actual saved byte mutation must reject exact output equality,
   restore passes. Real native triplet evidence is mandatory, not a synthetic
   equality assertion. Comparing different route arms cannot satisfy this group.
18 gate-exercise: fixed actual native E/V/beta/floor/weight data must demonstrate
   any claimed zero/positive weight class and its exact sites. Flip a retained
   above-floor classification with operands unchanged; actual consumer predicate
   rejects, restore. If actual data lack either class, report NOT_EXERCISED;
   do not force a global rejection of unrelated decode/dark measurements. The
   seven fixed weight-branch witnesses and two weight mutations/restorations
   are enumerated in independent-checker-design.md; correct p2 underflow is not
   a threshold rejection or an association error.
19 uncertainty-scope: fixed positive scalar variance, independent analytic df2
   quantiles and six primary NIST table references for df4/11/21 (.025,.975),
   with0.0005001 table-rounding allowance as frozen in the companion design;
   wrongdf=2*16384 must reject. Its fixed omitted-half-recurrence/faulted-df4
   variants must reject those SAME external references and restore. A smoothed-energy or clamped
   value cannot be labelled an admitted Gaussian scalar interval. Restorelabels.
20 provenance-prefix: wrongsource/filehash/size/CFA-order and missingoneof27,
   wrongarm/observer or altered released terminal disposition must each fail the same
   saved-authority predicates; restored exact references pass. Every visited
   refusal stays retained and unvisited rows are explicit. Successful children
   do not retroactively complete a failed parent.

Groups10/11 require independently written sparse/rational stencil arithmetic;
no import of core/pyramid, original checker or producer helpers as oracle.
The fixed operator tolerance, serializer shapes and quantile construction are
specified in independent-checker-design.md and must be source-reviewed with the
concrete checker before any controls execute. They
are not permission for a trial RAW read to select tolerance. If a requested hook
cannot supply its stated actual operand without perturbation, stop that consumer
claim and resolve the concrete source issue before root release.

## Completion, refusal and dispatch

Keep separate outcome fields for transport/decoder agreement, source/extraction
association, observer neutrality, exact consumer arithmetic, paper premise,
dark raw-domain diagnostic, clamp transfer, per-route predictor eligibility,
actual gate exercise, and conditional statistical comparison. COMPLETE_SAVED_LOCAL
TRANSFER_DIAGNOSTIC never means model-valid, stationary, calibration-correct or
quality-improved. Ratio direction is explicit: high temporal/predicted ratio can
mean underestimated noise, covariance or nuisance; low ratio can mean clamp,
smoothing, misaddressing or overprediction. No single direction identifies gain.

If exact associations fail, stop their downstream interpretation and preserve
prefixes. If paper headroom/drift/motion is refused/unresolved, no physical paper
claim follows; dark and exact implementation observations can still complete.
If comparisons are interpretable and compatible under named assumptions, close
this bounded diagnostic without another capture, parameter fit or policy update.
If a stage-specific disagreement is retained, identify its actual consumer and
uncertainty; any later causal intervention needs a new independently reviewed
question. Statistical imprecision is an allowed final result. Already-answered
sensor-wide green covariance is not reopened by this local crop.

## Source-only ledger and prior work

This lane is limited to64MiB aggregate source/report reads,4MiB new retained
source/docs,60CPU seconds and120 active-process-wall seconds. No payload or
scientific execution is charged to this source grant because none is authorized.
Future raw/observer/independent-read costs must be separately released by root;
the77 proposed original decodes and probe work are not silently included here.

Read: charter (9945B/5f2e183d...), RAW priority review committed59202e51;
owned merge_cmd.rs extract_planes/BandWorker/load_frame; owned noise.rs,
profile.rs constructor; pyramid.rs reduce/expand/level_sizes/luma_variance/
add_frame_with_gain/smooth5; gatefloor.rs measure/run/pooled sample eligibility;
owned strehl-raw/lib.rs metadata/decode boundary; align_cmd.rs native dispatch;
M1-decode-measured; M72-green-plane-correlation amended headline and estimator
limits; M193c sensor-domain-reader-preregister and sensor-white-reader-preregister.
SYNTHESIS consumer/history query was targeted source text, not a new fold.

Root's one recorded prior_art query was sensor noise / temporal variance /
pyramid / green luma; do not rerun it. Named findings: BUILD-PYRNOISE,
BUILD-SOFTGATE, M194-production-truth, M130-crop-early, V-DILUTE and V-REVIEW-aura.
Priority review carries M48/M61/M68 corrected gains, M71/M90 PRNU, M72 materiality
withdrawal, M92/M92b and M135/M189 limitations. This protocol claims no absence
of prior art outside that bounded search and does not restore withdrawn claims.

Source navigation used rg for exact symbols/paths and bounded Get-Content slices.
Two wildcard path searches hit Windows invalid-name errors before reading their
requested experiment paths; corrected literal paths were used. Some broad filename
and SYNTHESIS query output was truncated, so unread tail content is not cited as
reviewed. No candidate ran. Full source-file lengths, rather than just displayed
slices, are conservatively charged; the read population is below16MiB including
repeated own-source reads, within the64MiB lane. Hold hashes and exact source-only
command receipts belong to root's source freeze; no files in the old200-source
closure, live crates, captures, SYNTHESIS or program proposal were edited.

Final interface source read also covered source/implementation-contract.md and
source/core-hook.rs (8092B/a2d71b5c...), matching original/prepared u16 ROI,
actual L/V/E/W and five-level coefficient observations without cache preparation.
This is an interface read, not a completed independent review of the whole
unapplied producer patch/adapter. Scope amendments1/2 were read explicitly.

Prospective root writer/map refinement before source hold:18 actual existing
write_merged calls and their TIFF artifacts are additional to the f32 outputs.
Decode/fold/warp/probe counts stay50/100/50/50. The map callback observes actual
resolved t_site at the existing resolution seam. No candidate or data ran between
the earlier draft and this refinement. Producer later ledger must price the18
writer calls/artifacts; no resource charge is silently removed or expanded.

Additional fixed startup accounting: each of the9 fresh native processes calls
the memoized BandGain::measure for actualnb4 once, using32 synthetic white fields
of256x256. Total9 initializations/288 compact synthetic pyramids are separate
from50 real full-native warps and50 probe synthetic full-native warps. They are
existing startup work, not new sensor draws, scientific arms or a rerun claiming
to commission the historical gain calibration. Root must charge their CPU/memory.

Methodology hold leaves full producer/independent-reader implementation review,
source freeze, fresh builds, private controls and all RAW/data execution OPEN.
No candidate was executed to select these tolerances or repair these pre-data
control expectations. The NIST public reference was read in two bounded HTML
views for the fixed CDF/quantile control; no external implementation was opened.

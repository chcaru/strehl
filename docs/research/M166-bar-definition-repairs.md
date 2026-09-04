# M166 — Definition repairs for M3, retained M4, M9, and M11

**Status:** proposal for lane M160 to apply; not a scorecard edit and not a
measurement result.

This proposal was prepared against
`docs/proposals/2026-09-sota-scorecard.md` SHA-256
`7128f9bbc9cdab2012a5c0829dbb54683eafe3886854bc54e7375af8bfd72f87`.
The owner's `docs/proposals/2026-08-sota-path.md` remains authoritative where
the two disagree.

The test for every definition below is operational: two implementations given
the same hash-bound inputs must select the same population, produce the same
numerators and denominators, and return the same state. These are proposed
definitions, not permission to score absent evidence.

## 0. Conventions shared by the four repairs

1. `PASS` and `FAIL` describe a candidate only after every required
   input/reference/comparator exists and passes its own admission checks. A
   missing required capture, truth producer, comparator, manifest, or
   commissioning artifact is `UNMEASURED_<reason>`, never a candidate pass or
   fail.
2. Missing, cropped, malformed, non-finite, rail-clipped where clipping is
   forbidden, or hash-mismatched **candidate** data are charged as the
   candidate-worst value stated below. They are never deleted from a frozen
   population. Malformed frozen evidence invalidates the campaign instead.
3. All thresholds are applied to unrounded IEEE-754 binary64 values and are
   inclusive. Reports may print decimals but must also retain hexadecimal
   binary64 values or exact integer numerator/denominator pairs. Non-finite
   values never compare as passing.
4. A nearest-rank quantile of `N>0` values is sorted ascending and takes the
   one-based element at `ceil(qN)`; there is no interpolation. An empty
   population is `UNMEASURED_EMPTY_POPULATION`.
5. Stable order is ascending UTF-8 byte order of the frozen `site_id`,
   `cell_id`, product ID, and mode ID as applicable. This is also the tie-break
   order.
6. The one-sided 95% Wilson limits use
   `z=1.6448536269514722`. The upper limit is

   `((p+z²/(2n)) + z*sqrt(p(1-p)/n+z²/(4n²))) / (1+z²/n)`;

   the lower limit changes the `+` before the square-root term to `-`.
7. Every result binds the scorecard hash, input and output byte hashes,
   checker hash, complete settings hash, product and mode IDs, population
   manifest hash, representation, and every excluded/invalid row with reason.

## 1. M3 — occlusion halo and broad veil

### 1.1 What the current wording permits

“Paired p99” currently permits incompatible reductions. For 500 sites, let
five sites have `(h_e,v_e)=(0.06,0)`, five different sites have
`(0,0.06)`, and the remaining 490 have `(0,0)`. Nearest-rank separate
percentiles give `max(p99(h_e),p99(v_e))=0`; nearest-rank p99 of the paired
site severity `a_e=max(h_e,v_e)` gives `0.06`. Both are plausible readings of
the current phrase.

The scalar image representation is also unstated. A linear-ProPhoto pixel
`(R,G,B)=(1,0,0)` is `0` under a green-only profile and `0.2880402` under
ProPhoto luminance. Therefore even the profile samples are not unique before
the halo formula is reached. Per-capture versus pooled bars, source-profile
choice, output geometry, percentile convention, and comparator selection are
likewise not fully bound.

### 1.2 Proposed normative population and representation

Adopt the following existing artifacts by content hash:

- M152 census manifest
  `experiments/M152-site-census/out/census-manifest.json`,
  SHA-256
  `35d5058afc1f310923ba2a3e5bf0cd3b91b3eb2df0e8d4868c22099de7bcd38d`;
- M161 checker definition
  `experiments/M161-m3-ratification/m3-checker-definition-v2.json`,
  SHA-256
  `578022e6eeefecce60a00191024e9ffd4dc3c621410b398709b3f92b987b67ca`;
- M161 scorer `m3_checker_v2.py`, SHA-256
  `05d291c8c24712d46666e9ed398f39cb982fa3b4c918a7e0cfcdee200dec2eda`.

The frozen population is exactly 500 sites: duck tape 133, chia 133,
flower/fern 132, and horizontal-razor control 102. No output-dependent
selection or replacement is allowed.

For scoring, decode every common input and product output as unsigned 16-bit
linear ProPhoto RGB D50. Normalize each code by `65535` and form the binary64
scalar

`Y = 0.2880402*R + 0.7118741*G + 0.0000857*B`.

The adapter must provide, before scoring, one hash-bound common-coordinate to
output-coordinate similarity transform per product/capture. It is derived
from input-only landmarks, never from the scored output. Its independently
held-out landmark residual must meet all M161 limits: absolute scale
disagreement `<=0.1%`, absolute rotation disagreement `<=0.02 degrees`, and
non-translation residual RMS `<=0.1 output px`. Failure is
`UNMEASURED_WARP_INADEQUATE`, not a deleted site.

At each frozen site, use the manifest centre and renormalize its stored
dark-to-bright normal once in binary64 by `n=n_raw/hypot(nx,ny)`. For signed
native-pixel offsets `s=-400,-399,...,400`, bilinearly sample each source `Y`
image at `centre+s*n`; sample the output at the transformed coordinate. Pixel
centres have integer coordinates, bilinear interpolation uses the four
enclosing centres, and an exact integer coordinate has its integer pixel
value. Any required sample outside the image charges that output site invalid.
The 128-by-128 `rho_edge` patches are axis-aligned and use coordinates
`centre+(j-63.5,i-63.5)` for `i,j=0,...,127`, sampled by the same rule.

The M152 discovery source named by `source_file` is both
`normalization_source` and `far_reference_source`. `sharp_source` is the
source having the smallest finite 10–90 width under the M161 definition; ties
take the earliest source-frame ordinal. All source frames, not only those
three, form the pointwise source hull. These choices are made from sources
alone and are shared bit-for-bit by the candidate and all comparators.

### 1.3 Proposed exact statistic and bars

For each site, use the M161 v2 formulas:

- `h_e` is the maximum output excess outside the all-source pointwise hull on
  `2<=|s|<=32`, divided by the discovery source's narrow step measured from
  `[-64,-48]` and `[48,64]`;
- `v_e` is the greater of the negative-side and positive-side arithmetic mean
  absolute residual from the discovery source on `16<=|s|<=200`, divided by
  that source's broad step measured from `[-400,-320]` and `[320,400]`;
- `a_e=max(h_e,v_e)`;
- width is output 10–90 width divided by the sharp-source 10–90 width on
  `[-32,32]`;
- `rho_edge` is M161's complex cross-spectrum coherence on the 128-pixel patch
  in `[0.15,0.25] cyc/native px`.

A malformed output site is `(h_e,v_e,width,rho)=(+inf,+inf,+inf,0)`.
A site is affected iff `a_e>0.05`.

The candidate must satisfy **all** of the following both on each of the four
capture populations and on the pooled 500 sites:

- nearest-rank median `h_e<=0.01`;
- nearest-rank median `v_e<=0.01`;
- nearest-rank p99 `h_e<=0.05`;
- nearest-rank p99 `v_e<=0.05`;
- `max(a_e)<=0.05`;
- affected point rate `<=0.01`;
- nearest-rank median width ratio in `[0.95,1.05]`;
- nearest-rank median `rho_edge>=0.90`.

The one-sided 95% Wilson upper bound on affected rate is computed **only on
the pooled 500 sites** and must be `<=0.02`; applying that confidence bar to
the 102-site razor control would make even `0/102` exceed 2%. Per-capture
point bars remain mandatory.

For the comparator clause, form `p99(a_e)` on identical frozen sites with no
deletion. For each capture and for the pooled population independently, the
reference is the lowest value among every available mode that has passed the
admitted M1 qualification on those same output bytes. This per-scope envelope
is deliberately no easier than choosing one favourable global mode. Ties use
product ID then mode ID. Required modes are licensed Zerene PMax, licensed
Zerene DMap, and the fresh best-known-source fork rebuild; each obtainable
Helicon A/B/C mode also enters. Strehl's value must be `<=` that reference in
every scope. If any required comparator product is absent, or no mode has an
admitted M1 qualification, this clause and therefore M3 are
`UNMEASURED_COMPARATOR_QUALIFICATION`.

### 1.4 Loose-direction closure

A constant output has no finite 10–90 crossing and zero coherence, so it
fails. A blur large enough to collapse edge transfer is rejected by the
`1.05` width ceiling; coherence alone is not credited as transfer magnitude.
A one-sided veil cannot be diluted by the opposite side, and one or a few
severe sites cannot hide below p99 because the literal maximum is mandatory.
No favourable capture or comparator can compensate for another because every
capture and the pooled population pass independently.

**Repair direction:** freeze representation/profile construction and adopt
M161 v2's side maximum plus literal observed maximum.

## 2. Retained M4 — same-output flat-band power

### 2.1 What the current wording permits

The current retained component names `median Q_flat<=1.00` but does not bind
the scored flat population, `B99`, `noise_floor`, channel, or aggregation.
For a site with output band RMS `1.1e-5` and `B99=1.0e-5`, choosing
`noise_floor=0` gives `Q_flat=1.10` while choosing `noise_floor=2.0e-5`
gives `0.55`. Both are allowed by the current text. More seriously, a
constant output has numerator zero and passes every such ratio.

### 2.2 Proposed exact flat-power limb

Adopt M152's population and randomization freeze
`experiments/M152-site-census/m4-freeze.json`, SHA-256
`a92b49bd2dc0a661b3319f96e54c7514994292f17f5a0ac0bab0d12cf7cb8d5c`.
The canonical window, mask, Parseval weighting, and band-RMS implementation is
`experiments/M152-site-census/census_common.py`, SHA-256
`3e36a18d8c7b675f224f4fbe694ef2d16297e3e038df18e61cdb4dead219a680`.
The scored population is exactly 250 output-blind 128-by-128 native-pixel flat
tiles: medication pill 84, bee background 83, and foam 83, with no
cross-capture substitution. Site order is M152's frozen order.
The unplanted/base output is the exact same output byte stream and settings
used by the retained M4 component in the joint M1/M2/M8 quality bundle.

For every source common TIFF and candidate output, use the decoded linear
ProPhoto green channel `G/65535`. For each tile:

1. subtract its arithmetic mean;
2. multiply by a separable 128-point Hann window normalized to mean-square
   one;
3. take an orthonormal real 2-D FFT;
4. sum squared magnitude, with exact real-FFT Parseval weights, over radial
   frequency `1/60<=f<=1/20 cyc/native px`;
5. divide that energy by `128*128` and take the square root.

`B99_i` is the nearest-rank p99 of that band RMS over:

- 1,000 blends of all source frames with
  `numpy.random.Generator(PCG64(15240420260904))` and independent
  `Dirichlet(1,...,1)` weights in generated order;
- every one-hot source frame; and
- the uniform source mean.

Instantiate the generator once. In fixed capture order medication, bee, foam,
draw one `1000 by N_frames` matrix per capture; every site in that capture
uses the same matrix. Before any candidate output is opened, materialize those
matrices as little-endian binary64 arrays and bind their SHA-256 values in the
campaign manifest. Those arrays, rather than a later library's
reimplementation of `Dirichlet`, are the normative random input.

The ISO floor is interpreted in the same normalized linear units and is
exactly:

- ISO 50 or 100: `1.26102285354196e-5`;
- ISO 1000: `3.72061790502189e-5`.

For tile `i`,

`Q_i = band_rms(candidate_G_i) / max(B99_i, noise_floor(ISO_i))`.

A missing/invalid output tile has `Q_i=+inf`. Each of the three captures'
nearest-rank median and the pooled 250-site nearest-rank median must be
`<=1.00`; any invalid tile is also an immediate candidate failure.

### 2.3 Mandatory paired transfer veto

Flat power alone is not admissible. After the candidate binary, settings,
common-input manifests, and flat sites are hash-frozen, derive two phases per
site from SHA-256:

`phase(site,j) = 2*pi*uint64_be(SHA256("M4-TRANSFER-V1|"+site_id+"|"+j)[0:8])/2^64`.

For local tile coordinates `x,y=0,...,127`, form the exact signed integer-code
plant

`P_i(x,y)=round_ties_even(256*cos(2*pi*(4x+3y)/128+phase(i,0)) + 256*cos(2*pi*(-3x+4y)/128+phase(i,1)))`.

Both carriers have radial frequency `5/128 cyc/native px`, within the scored
20–60 px band. A flat site is eligible only if adding `P_i` to R, G, and B of
every source common TIFF cannot leave `[0,65535]`; this margin check is
input-only and occurs before outputs. Add the same `P_i` to every frame and
all three channels at all selected non-overlapping sites, producing one
hash-bound planted twin stack per capture. Render the base and planted stacks
with the identical candidate binary and settings. Materialize and hash the
integer plants before rendering; their stored bytes, not a platform's later
`cos` implementation, are normative.

For each site and each RGB channel, let `P` be the decoded planted-minus-base
input tile and `D` the planted-minus-base output tile, both divided by 65535
and with their tile means removed. Compute

`g=<D,P>/<P,P>` and `r=||D-gP||_2/||P||_2`.

Every site and channel must have `0.995<=g<=1.005` and `r<=0.005`.
`<P,P>=0`, any non-finite value, changed output geometry, or a missing twin is
a candidate failure. The phases stay concealed until all candidate and
comparator hashes/settings are frozen.

A constructive clean implementation exists: at each flat tile choose any
registered convex source blend whose measured band RMS is at or below its
`B99` (such a member exists by construction) and use weights summing exactly
to one. Its base has `Q<=1`; because the plant is identical in every source,
the same linear blend gives `D=P`, hence `g=1` and `r=0`.

### 2.4 Loose-direction closure

A constant output still obtains `Q=0`, but its planted-minus-base output is
zero, so `g=0` and the retained component fails. A blur that materially
attenuates or distorts the 25.6-pixel carriers fails gain or residual. Because
the plant is applied to the actual scored flat stacks at the actual scored
sites, this is not a separate easy synthetic scene. The transfer veto can
only reject; it cannot rescue `Q_flat>1`.

**Repair direction:** bind M152's denominator and population, then make an
in-band paired transfer control a non-compensating veto.

## 3. M9 — acuity, uncertainty, and `n_eff` certificate

### 3.1 What is and is not presently definable

M9 has no admitted producer of `truth_valid`. With 500 claimed cells, a
manifest labelling all 500 truth-valid yields false-certification `0%` and
true coverage `100%`; the same bytes with all 500 labelled truth-invalid
yield false-certification `100%` and true coverage `0%`. The current text
does not choose between those manifests.

The D8/FRC channel cannot fill this hole: common post-noise blur or sharpening
leaves that statistic invariant, so it cannot establish delivered acuity.
M9 therefore remains **DEFINITION BLOCKED** until M1 admits an independent,
higher-sampling, candidate-specific acuity-truth predicate. No threshold
invented inside M9 may substitute for it.

The following is the exact downstream contract M160 can adopt now; its first
input is intentionally unresolved rather than papered over.

### 3.2 Required truth and product contracts

Before any candidate output is opened, the truth producer must freeze a
sampling manifest of exactly 1,000 independently located physical
`(site,band)` cells: 100 independently source-positive cells and 100
independently source-negative controls in each of `[0,.05)`, `[.05,.10)`,
`[.10,.15)`, `[.15,.20)`, and `[.20,.25] cyc/native px`. A physical site
can occupy one band only.

After the output is frozen but while blinded to the candidate certificate,
the independent truth producer appends, without changing the population, the
candidate-specific `truth_valid` result, truth amplitude, truth variance,
and independently calibrated single-frame variance. Every row also contains
stable `cell_id`, capture and repeat IDs, integer output coordinate, and band.
Source-negative controls must remain truth-invalid. At least 500 cells must be
independently truth-valid or the candidate fails
`INSUFFICIENT_DELIVERED_ACUITY`; the population is not resampled to
manufacture that count. M1 must define the physical target, higher-sampling
reference, candidate-preservation statistic, threshold, and uncertainty by
which those fields are admitted.

The candidate must emit hash-bound, native-grid arrays with one plane per band:

- `valid`: unsigned byte, only `0` or `1`;
- signed band-amplitude estimate: IEEE binary32;
- one-sigma uncertainty in the same amplitude units: IEEE binary32;
- `n_eff`: IEEE binary32.

The output also contains the rendered colour-output hash to which the
certificate applies. Shape mismatch, a missing plane/cell, any other validity
code, or non-finite/negative sigma or non-finite/non-positive `n_eff` at a
claimed cell is a candidate failure. No resampling of certificate planes is
allowed; the truth manifest names native integer coordinates. Validity must be
monotone in frequency: if band `k` is invalid, every higher band is invalid.
The highest valid band is the shipped acuity value.

For a cell, `claim_i` is exactly `valid_i==1`. Let `C` be claimed cells,
`T+` truth-valid cells, and `T-` truth-invalid cells:

- false-certification point rate is
  `|C intersect T-|/|C|`; an empty `C` is `+inf`;
- true-coverage point rate is `|C intersect T+|/|T+|`;
- at least 500 cells must be claimed;
- false-certification point rate and its one-sided 95% Wilson upper bound must
  both be `<=0.01`;
- true coverage and its one-sided 95% Wilson lower bound must both be
  `>=0.90`.

For every claimed truth-valid primary-repeat cell, define

`e_i=estimate_i-truth_amplitude_i`,

`v_i=sigma_i^2+truth_variance_i`, and

`h_i=1.959963984540054*sqrt(v_i)`.

Coverage is `|e_i|<=h_i`; the point coverage must lie in `[0.93,0.97]`.

The product's `n_eff` has one operational meaning. Compute
`n*_i=single_frame_variance_i/sigma_i^2` in binary64 and round it once,
ties-to-even, to binary32. The emitted `n_eff` bit pattern must equal that
binary32 value. Zero sigma or overflow is invalid, not infinite effective
sample size. Every claimed cell must also have `n_eff>=1.0`; a certificate
wider than its independently calibrated single-frame uncertainty is not a
valid stacked-acuity claim.

### 3.3 Exact repeat/decile calibration

The corpus must provide two independently captured, identically configured
repeat outputs at sweep width 4 and two at sweep width 10 for every
truth-valid claimed cell. Run every calculation and bar in §§3.2–3.3
separately for sw4 and sw10; a pooled-across-width result is diagnostic only
and both widths must pass. Let one width's repeat amplitudes and predicted
variances be `(a_i1,s_i1^2)` and `(a_i2,s_i2^2)`. Define

`d_i=(a_i1-a_i2)/sqrt(2)` and
`p_i=(s_i1^2+s_i2^2)/2`.

Sort cells by `(p_i,cell_id)`. Decile `j=0,...,9` is the half-open index range
`[floor(jN/10), floor((j+1)N/10))`; ties are never kept together and no decile
may be empty. In each decile,

`V_emp=sum((d_i-mean(d))^2)/(n_j-1)`,

`V_pred=mean(p_i)`, and `R_j=V_emp/V_pred`.

At least nine of ten `R_j` must be in `[0.90,1.10]`. The pooled ratio, computed
by the same sample-variance and arithmetic-mean formulas over all `N`, must
also be in `[0.90,1.10]`. Two or more failing deciles, a failing pooled ratio,
or any invalid term sets the required
`material_predicted_vs_empirical_disagreement=true` and fails M9.

The model/CRLB channel supplies `sigma` and the single-frame variance; the
independent repeat channel supplies `V_emp`. The required single-image
decorrelation channel remains a separately published diagnostic/control and
may veto a broken implementation, but it may not produce or override
`truth_valid`.

### 3.4 Loose-direction closure

Universal refusal has zero true coverage and fewer than 500 claims. Universal
validity fails on the 500 truth-invalid cells. A constant or blurred output
cannot supply the required 500 candidate-specific independently truth-valid
cells and calibrated amplitude intervals. Arbitrarily wide intervals fail the
`n_eff>=1` floor and the upper coverage bound; arbitrarily narrow or
fabricated uncertainty fails coverage and repeat variance. Fabricated
`n_eff` fails the exact variance identity.

**Repair direction:** admit independent acuity truth first, then bind the
certificate to balanced truth-negative/positive cells and independent repeat
calibration.

## 4. M11 — comparative and product-native timing

### 4.1 What the current wording permits

Comparator aggregation is unstated. Suppose comparator A takes `(10,100)` s,
comparator B `(20,10)` s, and Strehl `(6,6)` s on two captures. A
per-capture fastest envelope gives `20/12=1.667x` and fails; selecting the
single comparator with the fastest total gives `30/12=2.50x` and passes.

The live epoch is also outcome-changing. If frame 100's shutter closes at
`t=0`, its file becomes available at `t=3`, and the master closes at `t=11`,
the owner's last-shutter clock reads `11 s` and fails while a file-availability
clock reads `8 s` and passes.

### 4.2 Exact timing campaign

Use three frozen common-input cells:

- `C33`: the first 33 ordered frames of `bee-1-cpl`;
- `C105`: all 105 ordered frames of `coffee-bean`;
- `C299`: all 299 ordered frames of `bee-1-cpl`.

Every program receives identical ordered uncompressed 16-bit linear ProPhoto
RGB D50 TIFF bytes on the same volume, native dimensions, ICC, crop, and output
contract. Candidate CPU, hybrid, and baseline settings are each invariant
across `C33/C105/C299`; comparator mode identity/settings are invariant across
every capture on which that mode is evaluated.

For an ordinary invocation, read QPC immediately before creating the root
process. Stop only after a Windows Job Object reports zero live root or
descendant processes; the output TIFF and invocation manifest have both been
closed and flushed; and both have been reopened, structurally validated, and
SHA-256 hashed. Decode/load, registration, merge, colour, write, asynchronous
children, validation, and hashing are inside the boundary.

Store start/stop as integer QPC ticks plus the integer QPC frequency; subtract
ticks before converting to binary64 seconds. Root and every descendant image
path and file hash are retained. Requiring only root-process exit is invalid.

Each cell has one unscored warm-up and six scored sweeps. Odd sweeps use the
frozen forward setting order; even sweeps use its exact reverse. A failed
condition or member invalidates the entire paired sweep and campaign; no
selective rerun or outlier deletion is allowed. Report all six values and
minimum, median, maximum, range, MAD, scaled MAD, sample standard deviation,
and relative range. The score uses the minimum valid wall time.

Preflight requires a fixed power plan and a hash-bound thermal probe. A
predeclared allowlist contains only OS display processes plus the timed Job
Object; observing any other GPU-using process invalidates the campaign. Over
a 60-second preflight,
`CPU_busy=(DeltaKernel-DeltaIdle+DeltaUser)/(DeltaKernel+DeltaUser)` from
Windows `GetSystemTimes` must be `<=0.15`. During a run,
`external_busy=max(0,total_nonidle_CPU_time-JobObject_CPU_time) /
(logical_processor_count*wall_time)` must be `<=0.10`. CPU, thermal, throttle,
and GPU-process telemetry is sampled every 10 ms; the campaign manifest
predeclares the allowed start-temperature interval and requires no hardware
throttle flag. Input byte hashes are checked before and after every
invocation. A missing telemetry sample or condition miss invalidates the
campaign.

### 4.3 Comparative statistic, qualification, and ties

For each capture `c`, let `S_c` be Strehl's minimum 16-worker wall time.
For every quality-qualified comparator mode `m`, let `T_mc` be its minimum.
Define

`T_c=min_m T_mc`, `R_c=T_c/S_c`, and
`R_pool=sum_c T_c/sum_c S_c`.

The fastest-mode tie is product ID then mode ID. Strehl must have `R_c>=2.00`
for **each** of `C33`, `C105`, and `C299`, and `R_pool>=2.00`. The
per-capture envelope is intentional: no slow capture or favourable global
mode can hide a miss.

A comparator mode qualifies only when one binary/settings fingerprint passes
the common-input transfer/geometry contract, M1, M2, M3, M8, and retained M4
on their frozen quality-corpus outputs; every reading is taken from the
corresponding hash-bound output bytes and no timing-cell setting may differ.
The timing outputs must independently pass the common output contract and all
quality controls applicable to their captures. Required arms are licensed
Zerene PMax, licensed Zerene DMap, and the fresh best-known-source fork
rebuild; every obtainable Helicon A/B/C arm also enters. Missing required
arms, an unbound fresh fork, or absent admitted M1 makes M11
`UNMEASURED_COMPARATOR_QUALIFICATION`. It is not permission to time an
unqualified mode.

For the retained cross-worker component, scored repetition 1 is the
predeclared canonical output. At each N, the complete TIFF file SHA-256 **and**
the canonical decoded-pixel SHA-256 must each be identical across worker
counts 1/2/4/8/16. TIFF metadata must therefore be deterministic; invocation
manifests are not part of the compared TIFF. There is no cross-N identity
requirement.

### 4.4 Exact product-native disclosures

These do not rescue or fail the common-merge publication verdict, but each
receives a separate `PASS`, `FAIL`, or `UNMEASURED`:

- CPU: `min(wall)/N<=0.15 s/frame` at each N=33/105/299, workers fixed at 16.
- Hybrid: `min(wall)/N<=0.06 s/frame` at each N under one frozen hybrid mode.
  An absent backend is `UNMEASURED_NOT_IMPLEMENTED`, not a pass.
- Default baseline: `min(candidate_warm)/min(baseline_warm)<=2.00` at each N;
  only the build hash may differ.
- Cold: six predeclared pairs at each N for both candidate CPU-16 and the
  frozen hybrid mode. Each pair begins with an actual reboot identified by a
  unique boot-ID receipt, runs cold, then runs a warm mate with identical
  inputs/settings and fresh private output/temp paths. Every
  `cold_j-warm_j<=20.0 s`; “equivalent reset” is not admissible.
- Live first 100: use the frozen shipping-default product mode and a new signed
  acquisition trace containing monotonic shutter-close and durable
  file-close/availability timestamps for every frame. Prestart the frozen
  stacker, reveal each hash-verified file only at its recorded availability
  offset, and prohibit pre-availability access. The epoch is **shutter close
  of frame 100**, as required by the owner plan, not file-100 availability.
  After one unscored warm-up, all six scored replays must be valid and
  `max(finalized_output_time-shutter_close_100)<=10.0 s`.

### 4.5 Loose-direction closure

A no-op, constant output, or low-quality fast mode cannot enter the timing
denominator because the identical binary/settings fingerprint must qualify on
hash-bound quality outputs and the timed outputs must pass their applicable
controls. Returning before a child or asynchronous write finishes cannot
shorten the measured interval. Worker-specific cheap outputs fail full-file
and pixel identity. Capture-wise and pooled 2x bars prevent averaging one slow
case away.

**Repair direction:** freeze one end-to-end clock, a per-capture fastest
qualified envelope, exact output identity, and a real last-shutter live trace.

## 5. No-softening check

- M3 retains every M161 numeric bar and adds per-capture application plus the
  literal maximum.
- Retained M4 keeps pooled `median Q_flat<=1.00` and adds per-capture medians
  plus a transfer veto.
- M9 retains false-certification Wilson UCB95 `<=1%`, true coverage `>=90%`,
  nominal coverage `[93%,97%]`, and the 9-of-10 decile bar; it adds the
  truth-population balance, a true-coverage Wilson lower bound, and
  `n_eff>=1`.
- M11 retains every 2x, CPU, hybrid, cold, live, baseline, and worker-identity
  threshold; it adds per-capture comparative bars and uses the owner's earlier
  last-shutter epoch.

## 6. M10 one-line ruling

**M10 remains ill-defined:** M163 closes the uncertainty-blindness defect with
five useful vetoes, but it does not freeze the target-valid predicate, stored
depth/invalid encoding, flat-null p95 reduction, or layer-confusion/boundary
population; execution also still lacks the depth-plus-sigma product and fresh
metrology truth.

## 7. Dependencies that definitions cannot manufacture

| bar | exact missing thing | resulting state |
|---|---|---|
| M3 comparator limb | admitted M1 qualification; required common-input Zerene PMax/DMap and fresh fork outputs; committed/commissioned profile-package builder and input-only warp evidence | `UNMEASURED_COMPARATOR_QUALIFICATION` |
| retained M4 | at least 29 additional eligible medication flat tiles; at least 83 eligible foam tiles; a separate >=100-tile development flat; materialized Dirichlet matrices and transfer plants; base/planted common-input renders | `UNMEASURED_CAPTURE_INADEQUATE` |
| M9 | commissioned independent higher-sampling M1 acuity-truth producer; exactly balanced source-positive/control manifest; fresh dense checker-only material; two matched sw4 and two matched sw10 IBIS-off repeats; independent repeat truth; dark/FPN calibration; acuity/sigma/`n_eff` product | `DEFINITION_BLOCKED_M1_TRUTH` |
| M11 | admitted M1 and repaired M2 qualification; required licensed comparator common-input outputs; fresh hash-bound fork build; frozen baseline and hybrid modes; committed/commissioned timing harness; actual acquisition timing trace; reboot receipts; quiet-host release | `UNMEASURED_COMPARATOR_QUALIFICATION` or the specific missing product-native disclosure state |

None of those absences may be converted into a default value, an empty
denominator, a waived limb, or a candidate failure.

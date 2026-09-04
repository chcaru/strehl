# M161 — feasibility and instrument-validity audit of the five remaining publication axes

Status: **COMPLETE — no new impossible bar; three named licensing paths are void**

| Axis | Verdict | Bar feasibility | Instrument validity | Minimal repair / remaining work |
|---|---|---|---|---|
| M2 — noise | **INSTRUMENT VOID** | The registered numerical pass set is nonempty; no output-format contradiction exists. | The flat-ROI residual rewards a unit-DC low-pass operation on the candidate. It cannot distinguish noise reduction by averaging from noise reduction bought by blur, although the axis is explicitly “at matched information.” | Add a same-output, independent, non-compensating transfer/information veto local to M2. This **does not lower the bar**; it closes a false-positive route. Relabelling the present result as only “lower flat-ROI band residual” would lower the claim. |
| M3 — occlusion halo / veil | **SOUND BUT UNMEASURED** | The pass set is nonempty, the mandatory representation does not exclude it, and the existing capture census supplies 1,233 full-reach eligible edges. | The repaired per-side maximum sees the one-sided veil that defeated the old reduction; source-hull excess sees both rim signs; the width guard sees blur. Normalized coherence cannot by itself certify transfer magnitude, but it is not the sole blur guard. | Ratify the scorecard’s numerical completion of the owner’s literal `[bar]`, formally recommission the amended checker including a real external-warp null, and run candidate/comparator outputs. The side-maximum repair **tightens**, rather than lowers, the prior scorecard bar. |
| M9 — certified acuity / `n_eff` | **INSTRUMENT VOID** | An exact, independently truthful certificate can satisfy every numerical limb; neither `u16` image serialization nor the coverage denominators make the pass set empty. | D8’s named empirical acuity channel is normalized coherence and is exactly invariant to a common nonzero post-noise transfer. Blur and unsharp mask are therefore both invisible. D2’s model channel cannot independently validate itself. | Replace D8 as an acuity licence with independent truth plus a non-compensating transfer veto; retain independent repeat-variance calibration for `n_eff`. This **does not lower the bar**. |
| M10 — physical depth | **INSTRUMENT VOID** | An exact depth map passes the value bars, and a fresh metrology-backed ruler can physically supply the required truth. The burned old ruler prevents a score, not existence. | The registered verdict never consumes the required `sigma_z` / uncertainty product. Replacing every reported uncertainty by zero, infinity, or random values leaves every M10 pass/fail quantity unchanged. | Add independent uncertainty calibration and require the depth-plus-uncertainty product. This **does not lower the bar**; it restores a product the plan already requires. |
| M11 — speed | **SOUND BUT UNMEASURED** | The absolute, relative, cold, and live-latency targets have a jointly nonempty physical budget; measured decode and storage rates create no lower-bound contradiction. | The two-arm harness times the whole process tree through closed, flushed, hashed deliverables and responds to planted delay and asynchronous child work. No harmful normalization survives the absolute-time limbs. | Run the formal one-second control and real campaign after bindings exist. Reconcile scorecard drift: the fork is required, Helicon is optional, and hybrid speed is not an owner-publication prerequisite. Removing mandatory hybrid **lowers the scorecard**, but only to restore the owner’s unchanged CPU bar. |

## 0. Scope, authority, and method

This is a read-only document audit. I decoded no RAW, opened no protected output,
ran no stack, and ran no benchmark.

The owner’s authoritative claim is the block in
`docs/proposals/2026-08-sota-path.md` located by the unique single-line anchor:

`The end-state sentence the project should be able to print, each clause with its`

The block is:

> On [subjects], strehl resolves detail at or beyond the best shipping comparator
> (D1: FRC + slant-edge, licensed Zerene PMax *and* DMap), at strictly lower noise
> (existing flat-ROI instrument), with zero invented structure (hull census, stamped
> per file), no occlusion veil above [bar] (halo instrument at full reach), while
> emitting per-pixel certified acuity, n_eff, and depth in physical units that no
> comparator emits at all (D2/D8/A5/C5), in [X] s per frame on CPU (existing harness).

That quotation was checked at the plan itself, not at a summary. For every wrapped
quotation below, comparison is by stripping a blockquote marker from each source line
first and then collapsing whitespace. No locator in this report depends on a line
number.

The common admissibility constraints used below are:

1. The competitive input is the same hashed, uncompressed, native-size, 16-bit linear
   ProPhoto RGB D50 TIFF for every arm.
2. The delivered image is a native-size 16-bit linear TIFF. No histogram match,
   exposure or white-balance change, sharpening, denoising, resize, or tone map may be
   applied after stacking.
3. The neutral-ramp transfer, native-scale geometry, retained-field, and identical-site
   gates remain in force.
4. Strehl uses its shipping default without subject-specific overrides.
5. The plan’s comparator set wins over stale scorecard text: licensed Zerene PMax and
   DMap plus the fork at its frozen best-known build; Helicon only if obtainable.
6. Protected captures remain protected; a missing or burned capture makes an axis
   unmeasured, not mathematically impossible.

The output and transfer clauses are in
`docs/proposals/2026-09-sota-scorecard.md`, at the unique headings
`### 1.2 One common linear input` and
`### 1.3 Output transfer and the tone sentinel`.
Comparator authority is in the plan at the unique heading
`### D1. The scorecard, built once, first`. The later scorecard amendment correctly
states the required set, but M160 found fourteen still-operative contradictions. Those
stale clauses are reported where they affect an axis; they are not treated as owner
requirements.

“Feasible” here means that the accepted set is not empty under those constraints. It
does not mean strehl presently reaches the set. “Instrument valid” means that changing
the claimed quantity in the prohibited direction must change at least one mandatory
component of the full instrument tuple.

## 1. M2 — noise efficiency at matched information

### Bar, exactly as written

The owner’s bar is:

> at strictly lower noise
> (existing flat-ROI instrument)

The operational scorecard completion, under the unique heading
`### M2 — noise efficiency at matched information`, is:

> `eta <=1.10` and `UCB95(sigma_strehl / min(sigma_comparator)) <=0.950`.

### (a) Bar feasibility — satisfiable

There is no M8-like empty intersection with the representable output domain.
For an ideal unbiased 16-frame mean `O` and an independent held-out 16-frame mean `R`,
each has variance `sigma_1^2/16`, so

```text
sd(O - R) = sigma_1 * sqrt(2/16) = sigma_ideal
eta = 1
```

before robust-estimator sampling error. The absolute `eta <=1.10` limb therefore has
an ordinary pass point. A candidate residual below 95% of a nonzero pinned-comparator
residual satisfies the comparative limb; nothing in `u16`, the tone sentinel, native
scale, or the no-post-stack-processing rule forbids that output.

The current captures cannot produce the registered score. M146, at the unique
single-line anchor
`` `(c)` is genuinely present. The already-frozen input-only audit found the bright ``,
records the second mandatory light block at `0.107703 px`, independently
`0.105202 px`, against the frozen `0.10 px` geometry limit. That requires a
replacement capture. It is a missing admissible input, not a proof that the pass set
is empty.

The plan’s historical `4.5x`, `0.746x`, and `9.9x` statements do not establish the
comparative bar. They are against the fork or one unstacked frame, not licensed
Zerene, and `docs/research/BUILD-PYRNOISE.md`, at the unique heading
`## 8. Verdict`, says:

> **At what cost in detail?** **Unmeasured**, and the report will not guess.

It immediately gives the decisive control:

> **The one sentence that must travel with these numbers:** a plain mean wins this
> column outright at 0.534x while destroying detail, so a lower flat-ROI noise
> ratio is not evidence of a better stack.

Thus the archived values are not a present M2 score even though the numerical bar is
not impossible.

### (b) Instrument validity — void for the claimed construct

The scorecard defines, on low-structure ROIs,

```text
sigma_res = 1.4826 * MAD(BP(O - R))
eta       = sigma_res / sigma_ideal.
```

Write a locally flat latent signal as `S=c`, candidate noise as `n_O`, and held-out
noise as `n_R`. Let the candidate merge have unit DC but scalar response `k`, with
`0 <= |k| < 1`, throughout the scored band. This can arise from admitting defocused
frames or otherwise smoothing inside the merge; it need not be forbidden
post-stacking processing. In the scored band,

```text
BP(K(S + n_O) - (S + n_R)) = BP(k n_O - n_R)

Var = |k|^2 Var(BP(n_O)) + Var(BP(n_R))
```

for independent halves. Reducing `|k|` therefore improves both `sigma_res` and `eta`
while deleting transfer wherever the scene is not flat. The neutral ramp constrains
gain and tone; it does not constrain spatial transfer. Native dimensions and the
no-resize rule do not constrain it either.

This is not merely a hypothetical concern. The M2 card’s unique paragraph beginning
`**Known defeat.** Blur, denoising, black crush` names blur and denoising as ways to
lower the statistic, and the existing plain-mean control demonstrates the direction.
The registered M2 inputs are fixed-focus repeats, so an indiscriminate temporal mean
looks ideal there while the same rule can average mutually defocused frames on the
focus brackets the product exists to merge. The named flat-ROI instrument observes
residual amplitude, not whether the reduction came from statistically efficient
same-focus averaging or information loss on the actual workload.

The plan amendment says the noise instrument remains live and M2 is not intrinsically
dependent on M1. That can remain true only if M2 receives its own local,
non-compensating information guard. It need not inherit the whole M1 programme.

**Minimal repair:** qualify each candidate and comparator mode on the same output with
an independent transfer/information veto that blur must fail and noise cannot
compensate—for example, a truth-referenced transfer bound or independently sharp
source-width bound—then apply the noise ratio only among qualified modes. Keep the
noise and transfer values as a tuple. This makes passing harder and **does not lower
the bar**.

The alternative is to retain the current instrument and rename the licensed statement
to “lower `0.15–0.35 cyc/px` flat-ROI residual under this protocol.” That is honest,
but it is a narrower claim and **does lower the publication bar**.

## 2. M3 — occlusion halo and broad veil

### Bar, exactly as written

The owner’s bar is:

> no occlusion veil above [bar] (halo instrument at full reach)

The literal `[bar]` remains in the authoritative plan. The scorecard’s proposed
completion, under the unique heading
`### M3 — occlusion halo and broad veil`, is:

> **Success.** **SCORECARD ADDITION:** median `h_e` and `v_e <=0.01`; p99 of each
> `<=0.05`; affected-edge point rate `<=1%` and Wilson UCB95 `<=2%`; median edge-width
> ratio in `[0.95,1.05]`; median `rho_edge>=0.90`; strehl’s paired p99 is no greater
> than the best comparator’s.

The verdict below audits that registered completion. The owner still must adopt a
number before the literal end-state sentence can be printed.

### (a) Bar feasibility — satisfiable

Every absolute component has an ordinary joint pass point: a source-coherent ideal
boundary has `h_e=v_e=0`, affected rate zero, width ratio one, and `rho_edge=1`.
The comparative limb allows equality, so zero tied with a zero comparator remains a
pass. All quantities are normalized dimensionless residuals or widths; the
`u16/65535` image domain creates no unreachable value.

The physical capture requirement is also satisfiable from the present archive.
`docs/research/M152-site-census.md`, at the unique single-line anchor
`**M3 has enough existing input capture. M4 does not.**`, reports:

> | M3 | 1,233 broad-eligible edges; 221 duck tape, 399 chia, 511 flower/fern, 102 razor; every site has 400 native-pixel reach; every capture exceeds 50; exactly 500 sites frozen for scoring | **SUFFICIENT — no new M3 photons** |

This is an input-only census, not a score.

### (b) Instrument validity — the repaired tuple discriminates the claimed defect

The original broad-veil reduction was invalid. It averaged both sides of an edge, so a
6% one-sided 200-pixel veil read only `0.027243`; no site crossed the 5% affected
threshold. M152 records this under the unique heading:

`### Commissioning failure: the registered broad veil is not admissible`

The scorecard now uses

```text
v_e = max(v_e_neg, v_e_pos)
```

instead. M152’s already-recorded side-maximum diagnostic detected 100% of the planted
one-sided sites at approximately `0.0545`. The scorecard amendment also proves
pointwise that `max(a,b) >= (a+b)/2`, so this repair cannot make an old output easier
to pass.

The full tuple closes the relevant invariances:

- `h_e` is excess outside the externally warped source interval and detects both
  overshoot signs;
- side-max `v_e` detects a unilateral broad pedestal rather than diluting it with the
  clean side;
- the 10–90% width ratio responds to common spatial blur;
- `rho_edge` is normalized coherence, so a nonzero per-cell transfer magnitude
  cancels between its numerator and denominator; the independent width ratio, rather
  than `rho_edge`, carries the anti-blur duty;
- affine gain cancellation from step normalization is appropriate because the
  claimed veil is a fraction of the independently measured source step, while the
  tone sentinel separately fixes delivered gain.

No common transform that introduces the target halo/veil while leaving all mandatory
members of this tuple unchanged was identified. The instrument is therefore
construct-valid as a tuple, unlike its old whole-band-mean version.

M3 remains unmeasured because no registered common-input candidate/comparator outputs
or external-warp profile package has been scored, and M152 could not commission a real
external-warp null. The amended checker should be formally rerun before a score.

**Governance repair:** replace the owner’s `[bar]` with an adopted threshold or state
that the scorecard addition is the owner-approved completion. This does not change the
mathematics. The side-maximum change **raises the measured defect value or leaves it
equal**, so it does not lower the bar.

## 3. M9 — certified acuity and effective sample count

### Bar, exactly as written

The owner’s compound output bar contains:

> emitting per-pixel certified acuity, n_eff, and depth in physical units that no
> comparator emits at all (D2/D8/A5/C5)

For M9, the scorecard completion under the unique heading
`### M9 — acuity and effective-sample certificate calibration` is:

> **Success.** **SCORECARD ADDITION:** false-certification Wilson UCB95 `<=1%`;
> true-band coverage `>=90%`; nominal 95% coverage in `[93%,97%]`; empirical/predicted
> variance ratio in `[0.90,1.10]` for at least 90% of deciles.

### (a) Bar feasibility — satisfiable

An exact independent truth certificate provides a direct pass construction:

- zero false certifications;
- 100% true-band coverage;
- calibrated intervals with 95% empirical coverage; and
- empirical/predicted variance ratio one in every decile.

At the registered minimum of 500 claimed-valid cells, zero false certifications also
places the one-sided Wilson upper bound below 1%. The certificate can live in the
manifest or a measurement sidecar; the required 16-bit linear image representation
does not quantize the certificate into an empty accepted set.

The required independent depth-stack truth captures do not yet exist, so strehl has no
score. That is absence of evidence, not a feasibility contradiction.

### (b) Instrument validity — the named empirical acuity channel is exactly blind

The owner names D2 and D8. D8’s per-tile FRC is normalized coherence between two noisy
half renders. M135 gives the exact result under the unique heading
`## 3. The precise impossibility result`. For a common nonzero scalar transfer `K_k`
at Fourier cell `k`,

```text
rho_k(KY1, KY2)
  = |K|^2 cov(Y1, Y2)
    / sqrt(|K|^2 var(Y1) |K|^2 var(Y2))
  = rho_k(Y1, Y2).
```

Therefore post-noise blur and post-noise unsharp mask are both invisible to FRC,
normalized split SNR, magnitude-squared coherence, and their canonical-correlation
extensions. The plan’s D8 statement that a tile whose halves agree to a frequency has
“measured that resolution” is false: agreement measures repeatability under the shared
transfer, not delivered acuity.

D2 does not rescue it. D2 derives a CRLB from the same admitted weights and noise model
that generate the certificate. The scorecard itself, under the unique paragraph
beginning `8. **D2’s CRLB channel cannot certify itself.**`, correctly says that
independent repeated exposures and external fixed-pattern treatment are required.
Those controls can validate `n_eff` and variance. They do not make D8 transfer-sensitive.

The scorecard avoids an immediate false pass by substituting a future M1 truth for D8,
but no such instrument is presently bound. It also does not require the surviving
single-image decorrelation channel or the plan’s explicit model/empirical disagreement
flag; M158 records that narrower false-green route as finding 10. Thus the scorecard is
a sketch of a replacement, not a current licence.

The source locator for that drift finding is the unique M158 table row beginning
`| 10 | M9 can pass on claimed-band and variance calibration without the surviving`.

**Minimal repair:** remove normalized D8/FRC from the acuity-licensing role. Use an
independently captured, higher-sampling truth reference with a non-compensating
transfer veto, such as M135’s `J_TR` plus `T_TR`/`U_TR` architecture, at the tile-band
level. Validate `n_eff` separately against held-out repeat variance and external FPN
calibration, and retain the coverage bar so universal refusal fails. This **does not
lower the bar**; it replaces a blind witness.

D8 may remain as a repeatability or noise-efficiency diagnostic. Calling that
“certified acuity” would lower the claim and is not an acceptable repair.

## 4. M10 — depth in physical units

### Bar, exactly as written

The owner’s M10 portion is:

> depth in physical units that no comparator emits at all (D2/D8/A5/C5)

The scorecard completion under the unique heading
`### M10 — physical depth product` is:

> **Success.** **SCORECARD ADDITION:** valid target pixels `>=99%`; rank correlation
> `>=0.99`; median absolute error `<=0.5` focus step; p95 `<=1.0` step; ruler slope error
> `<=5%`; flat-null p95 range `<=0.5` step; synthetic layer confusion `<=1%`.

### (a) Bar feasibility — satisfiable

An exact truth map has 100% valid pixels, rank correlation one, zero absolute error,
slope ratio one, zero flat-null range, and zero layer confusion. The accepted set is
therefore explicitly nonempty. The allowed one fitted origin is a physical gauge
choice, not an escape from scale.

A fresh ruler can meet the truth requirement. M154, at the unique heading
`## What M10 requires`, derives that the independent angle must be known to roughly
`-0.245/+0.257 deg` around the nominal setup to keep the truth contribution within
2.5% slope error. That is ordinary metrology, not an impossible tolerance.

The three existing ruler stacks cannot score. Their session was burned before
registration, and the only angle record says “about” 10 cm against “about” 1.81 cm
without instrument, endpoints, repeatability, camera-relative frame, or uncertainty.
M154’s unique heading `## Verdict` therefore correctly says `M10 remains UNMEASURED`.
A fresh unit repairs the evidence; it is not a change to the bar.

The image-output `u16` contract creates no M8-like contradiction. The plan explicitly
calls for a separate depth product, and its unique single-line anchor is:

`Products, in increasing ambition: depth + uncertainty TIFF (no stacker emits this);`

### (b) Instrument validity — exactly invariant to the required uncertainty product

The value-map sub-instrument is well structured. Spearman rank alone is invariant to
every strictly increasing remapping and therefore cannot establish physical units, but
the absolute physical errors and unfitted ruler-slope ratio break that invariance. The
flat and hidden non-planar controls prevent a hard-coded plane from licensing the
product.

The full M10 instrument nevertheless omits one of the owner’s required outputs. The
plan states, at the unique anchors:

`A5's z(x,y) ± σ_z *is* C5's deliverable once the breathing ruler converts index to`

and

`Products, in increasing ambition: depth + uncertainty TIFF (no stacker emits this);`

The M10 card likewise says the map is useful only if “ordering, scale, and uncertainty”
survive external truth. But neither the exact computation nor the success clause reads
`sigma_z`, interval coverage, standardized residuals, or any uncertainty field.

Formally, let the delivered product be `(z_hat, sigma_z)`, and let `V` be the complete
registered M10 verdict. As written,

```text
V(z_hat, sigma_z) = V(z_hat, sigma_z')
```

for every replacement uncertainty map `sigma_z'`, including all-zero, infinite, random,
or spatially permuted maps. This is the requested invariance/blindness identity. The
instrument cannot distinguish calibrated uncertainty from fabricated uncertainty,
although uncertainty is part of the named A5/C5 product.

M158 already records this scope loss as finding 11: the scorecard can pass depth-value
accuracy without calibrating `sigma_z` or requiring the depth-plus-uncertainty TIFF.
That finding was labelled nonblocking in the drift audit; for the full plan product it
is instrument-voiding.

The source locator is the unique M158 table row beginning
``| 11 | M10 can pass on depth-value accuracy without calibrating `sigma_z` ``.

**Minimal repair:** require the depth-plus-uncertainty product and score it against
independent physical/repeat truth. At minimum, report nominal interval coverage,
standardized residual calibration by predicted-uncertainty decile, and a proper score
or width guard so all-infinite intervals cannot pass. Keep every existing depth-value
bar. This adds a missing veto and **does not lower the bar**.

If the owner deliberately drops uncertainty and claims only a physical depth value
map, the current value checker can be sound. That would narrow the plan’s A5/C5 product
and therefore **would lower the claim**.

## 5. M11 — wall-clock throughput

### Bar, exactly as written

The owner’s end-state bar is:

> in [X] s per frame on CPU (existing harness).

The plan later supplies concrete D15 targets. The scorecard reproduces them under the
unique heading `### M11 — wall-clock throughput`:

> **Success.** **PROPOSAL BARS:** warm common-input strehl throughput `>=2.00x` the
> best comparator; native-RAW CPU-only at 16 workers `<=0.15 s/frame`; hybrid
> `<=0.06 s/frame`; cold `<=warm+20 s`; first-100 streaming master closed and readable
> `<=10 s` after `DSC00100.ARW` becomes available.
> **SCORECARD FREEZE OF D5'S “ROUGHLY 2x”:**
> candidate/default-baseline warm-wall ratio `<=2.00`. The baseline build/hash and its
> complete settings are frozen before the candidate is timed.

One scope correction is mandatory. M158 finding 7 shows that the plan makes GPU/hybrid
optional while CPU is the reference and the printable claim. The hybrid target remains
valuable engineering evidence, but its absence cannot veto the owner’s publication
sentence.

The source locator is the unique M158 table row beginning
``| 7 | M11 requires an unconditional `<=0.06 s/frame` hybrid result ``.

### (a) Bar feasibility — satisfiable

No pair of timing limbs demands mutually exclusive work:

- At N=299, `0.15 s/frame` allows 44.85 seconds.
- `docs/research/M-PHASE0-DECODE2.md`, at the unique single-line anchor
  `**Verdict: PASS.** The shipped black-box decoder delivers **381.0 decimal`, measures
  1,416.1 MB/s of allocated output at 16 threads. The measured decode is below the
  CPU budget rather than above it.
- `docs/research/M-PHASE0-NVME2.md`, at the unique heading
  `## 4. D15 decision and Rust consequence`, measures cold storage at only 11.41% of
  projected decode time. Storage is not a lower-bound contradiction.
- The plan’s own D12 traffic estimate is roughly 4 GB per frame and its D14 whole-fold
  estimate is 2.5–4 seconds for 299 frames. The unique source headings are
  `#### D12. The fold kernels — SIMD and fusion, behind the freeze` and
  `#### D14. The GPU, decided the corpus's way — wgpu-only, whole-fold, after decode`.
  Together with decode/fold overlap, these values leave a nonempty physical budget
  for both the CPU target and the optional hybrid target.
- A streaming fold may process frames while the camera is still exposing. The
  ten-second live bar starts after frame 100 becomes available, so it does not require
  processing all 100 frames from a cold start inside ten seconds.
- The candidate/default ratio has the baseline itself at ratio one as a trivial
  timing pass point; the quality and absolute-speed limbs prevent that observation
  from being mistaken for a complete M11 pass.

This is not a claim that the current implementation reaches the targets. It establishes
that the mandatory input, output, and hardware constraints do not create a lower bound
above them. Unlike M8-O, no accepted-time interval is empty.

The comparator ratio must use the plan’s actual set and matched output. Stale scorecard
requirements that every mode pass all twelve axes, that Helicon be present, or that the
fork be omitted are governance blockers, not physical speed constraints.

### (b) Instrument validity — valid timing instrument, no score yet

`docs/research/M153-m11-harness.md`, at the unique headings
`### Two required arms` and `### Timing boundary and telemetry`, implements the
claimed quantities rather than a kernel proxy:

- one common-TIFF comparative arm and one native-RAW product arm;
- process launch through all descendants exiting;
- closed and flushed TIFF plus manifest;
- dimensions, representation, ICC, whole-file hash, and pixel-payload hash;
- alternating sweeps with a fixed six-observation minimum-per-setting rule; and
- separate warm, cold, stage, CPU, busy-fraction, GPU, and I/O records.

At the unique heading `### Planted effect`, its synthetic planted delay recovered
`0.081854167 s` from an `0.080000 s` plant. The unique line beginning
`The asynchronous-child plant delayed the child writer by 0.075 s.` records that the
harness kept timing for `0.1302698 s` after root exit. Thus the harness is not
invariant to ordinary omitted delay or asynchronous output work.

The relative speed ratio is intentionally invariant to a common multiplicative clock
change. That is a nuisance cancellation, not blindness to the claim: the CPU,
hybrid, cold, live, and baseline limbs are absolute times and do not divide the change
away. A candidate can no more hide a one-second delay from the full tuple than from
the planted control.

M11 remains unmeasured. M153’s unique heading
`## Current verdict and remaining dependencies` lists the absent common-input adapter,
commercial bindings, baseline/hybrid settings, live and cold contracts, probe
bindings, formal one-second control, and real campaign. Those are required before a
score, but none shows the timer cannot discriminate runtime.

The current harness also preserves scorecard policy that the plan does not authorize:
all-quality/M1 qualification and stale comparator wiring. Before the real run:

1. include the fork at its frozen best-known build;
2. make Helicon optional;
3. qualify matched output against the owner-required claim rather than all twelve
   scorecard axes; and
4. keep the hybrid result as an engineering disclosure, not an owner-publication veto.

Items 1–3 restore the plan and do not lower its bar. Item 4 lowers the current
scorecard requirement, but only because that requirement hardened an optional plan
branch into a mandatory one.

## 6. Programme consequence

There is **no new `IMPOSSIBLE` bar** among M2, M3, M9, M10, and M11.

There are three instrument failures:

1. **M2:** the flat-ROI statistic cannot license “noise efficiency at matched
   information” without a local transfer veto.
2. **M9:** the named D8 empirical acuity channel is exactly invariant to the common
   post-noise blur it must detect.
3. **M10:** the verdict is exactly invariant to arbitrary replacement of the required
   uncertainty map.

M3’s amended full tuple and M11’s timing core are sound but have no score. The next
scientifically useful work is therefore not another M2, M9, or M10 scoring campaign.
It is to repair those three licensing instruments first, while completing M3’s formal
recommissioning and M11’s policy bindings.

# Native refinement: present obstruction and one useful boundary comparison

2026-10-27. SOURCE-VERIFIED / DERIVED / ARGUED; no numerical work, RAW read,
model import, build or implementation. **Do not release a baseline-initialized
version of the failed inverse as the next quality intervention.** No currently
specified original-CFA refinement is demonstrated to preserve the usable
baseline while correcting its insect fidelity. This is not an optical ceiling
or a rejection of all inverse reconstruction.

## Why a usable initialization is insufficient

The [complete level-balanced checkpoints](../direct-cfa-level-balanced/photographic-review.md)
are rejected: all three complete images and thirty witnesses lose useful hair,
scale, surface and color information. The earlier full64-step inverse is also
photographically rejected. Those outcomes do not identify every cause, the
unobserved optimum, or what a different initialization would do.

The model still compares every admitted source band with a measurement of one
sharp latent RGB field. Its A contains physical sensel integration and geometry,
but no through-focus PSF or visibility. A residual can therefore represent
legitimate defocus, changed occlusion or specular radiance, rather than detail
missing from the final image. A better initialization does not distinguish
these quantities. A baseline-centered ridge adds an explicit image prior;
freezing a robust residual gate around the baseline can instead reject the
genuinely missing feature it was meant to recover. No such trust strength or
admission model is justified by the present evidence. Another residual census
or extra CG is not recommended under this decision.

Initialization itself must be honest. The saved RGB32 linear TIFF is *after*
native highlight clipping/chroma roll-off, so inverse-matrix conversion is not
a global recovery of camera RGB. Use the actual pre-WB signed sensor master
and the existing output MHC if a camera-RGB baseline is ever required; retain
the exact writer clipping/WB boundary. That creates a demosaiced initialization,
not new sensor observations. The upstream legacy gather already performed
per-source MHC/remosaic, so importing its result cannot retroactively satisfy
the demosaic-once contract. See the [quantity audit](../../raw-quality-2026-10-26/insect-consumer-spread/quantity-audit.md)
and [native-contract audit](../cfa-probe-cost-audit/native-contract-note.md).

The actual prior negatives matter. Retained
`C:/dev/blog/death-of-software/projects/strehl/experiments/coherent-detail-transfer/results.md`
rejects complete printer105/vitamin70/marigold488 correction
`C+expand(reduce(P-C))`: it brought back trails/branches with texture rather than
combining the benefits. [Guarded R/B residuals](../../rb-residual-full/results.md)
made the complete vitamin photograph's magenta/cyan tails stronger without a
compensating structural gain. The original-checkout
`experiments/native-cfa-kernel/results.md` rejects both positive direct-sensel
full299 chip reconstructions for softened rails, contacts and scratches. These
are specific operator failures, not proof that preserving a baseline is wrong.
They do prevent relabeling generic residual injection or positive accumulation
as a fresh supported solution.

## Shared vector confidence is substantially answered already

**SOURCE-VERIFIED:** `dual-tree-cfa/implementation.rs` and the executed GPU
server use one common confidence, not separate phase elections. For each
complex direction/level/site:

```text
E = S5(sum_p WB_relative[p]^2 * (real_p^2 + imag_p^2))
F = 2*S5(sum_p WB_relative[p]^2 * propagated_probe_power_p)
w = select_weight(max(E-F,0),F,exponent)
```

The same w multiplies real and imaginary coefficients of all four physical
phases. WB scales both signal and noise power. This scalar ratio of summed
powers is not full cross-phase covariance whitening, and the four physical
offsets do not become co-sited merely by summing their powers. Nevertheless,
independent R/B source voting is not what that candidate implemented. Its
[complete teal-veil rejection](../dual-tree-cfa-gpu/photographic-observation/photographic-review.md)
does not establish whether the cause is source support, phase sampling,
complex synthesis, boundary behavior or the MHC/remosaic interface.

The proposed common noise-normalized color cue was also tested in
[insect-color](../../raw-quality-2026-10-26/insect-color/independent-results.md):
`sum(E_R/V_R,E_meanG/V_meanG,E_B/V_B)`, one shared weight applied to all four
CFA planes in the ordinary Laplacian consumer. It passed flats and substantially
improved cofocused red/blue detail. But in the different-source adverse it
reduced retained blue recovery0.521 to0.407 while improving red. It was rejected
before the full photograph; this is a generated component-loss result, not an
actual-weevil failure or a proof that every chromatic guide is bad.

Full covariance whitening has not been established by that marginal-variance
test. It could change sensitivity, but it cannot solve the elementary shared
scalar conflict: coincident same-orientation red and blue structures requiring
different sources must receive the same normalized source distribution. A more
accurate scalar confidence can still sacrifice one. Independent channel weights
introduce the different coupling already exposed by R/B-own-guide and the
guarded full vitamin result. No new common-confidence recipe is selected here.

## The existing twelve-plane boundary comparison has two full negatives

Correction to the initial memo: BUILD-DEMOSAIC is not the closest precedent.
[Phase-packed RGB](../../phase-packed-rgb/results.md) already completed all70
vitamin-C sources, and [phase-packed chip](../../phase-packed-chip/full-results.md)
already transferred the unchanged consumer to all299 chip sources. Neither
produced a meaningful photographic improvement. Vitamin's colored fans remain;
chip's colored rims, stipple and contact bloom remain, without an additional
resolved line or opening. The independent [chip review](../../phase-packed-chip/full-results-review.md)
confirms that bounded null. These are separate complete photographic negatives,
not merely failed metrics or proposed implementations. The current weevil107
has not received this specific comparison.

The recorded paired jobs were57.906s/8,207,220,736bytes for vitamin and
256.703s/7,301,345,280bytes for chip. They include both arms, have documented
concurrent work, and are not current-weevil speed predictions. Chip preserved
the exact previous RGB16 baseline, all299 active-u16 hashes and beta values,
known-four collapsed planes, admission fractions and75/75/75/74 arithmetic
chunks. Its unchanged generated screen has worst flat-chroma ratio1.078951:
inside the historical1.25 bar, but not a1.05 pass. That penalty must travel too.

**SOURCE-VERIFIED:** the actual [implementation](../../phase-packed-rgb/implementation.rs),
[full-source helpers](../../phase-packed-rgb/full-stack.rs),
[independent controls](../../phase-packed-rgb/independent-controls.rs) and
[chip wrapper](../../phase-packed-chip/implementation.rs) make the intervention
precise. The baseline's four actual gathered planes, green guide, injected
variance and measured beta are reused. Eight additional colors are gathered
at the four physical Bayer offsets using the same per-source WB, MHC,
color-specific Catmull pull and **Rounded consumed-value convention**. Twelve
planes enter the same ordinary seven-band quad-grid merge, including existing
fallback and per-plane input hull; the output interleaves each site's RGB
triple instead of applying final MHC. The source actively compares known-four
values and admission after chunk absorption and collapse. It does not let the
extra colors change focus selection.

In particular, this exact predecessor does **not** remove source
re-quantization: `consumed_fullres_value(..., Rounded)` is also applied to the
missing eight colors. Its controls explicitly compare against rounded,
u16-clamped, black-subtracted/nonnegative oracle values. The claim it can test
is retaining missing-color estimates through fusion and omitting final MHC,
not eliminating every intermediate rounding or obtaining new original-sensel
information. Each source temporarily materializes MHC RGB, then releases it;
there is no aligned-frame volume. This is an explicitly **non-native
per-source-MHC RGB-fusion diagnostic**, not the requested native endpoint.

## A weevil transfer is bounded and feasible, with weak prior support

**ARGUED:** reuse the existing implementation rather than create another
once-RGB operator. A new capture-binding wrapper can follow the chip cost/full
adapter and the already-verified weevil replay bindings in
[green-phase full-adapter](../../raw-quality-2026-10-26/green-phase-guide/full-adapter.rs).
This is a different photographic target, not a materially new algorithm.
Fine hairs, small scale boundaries and colored junctions are a reasonable
interface-sensitive witness, but no evidence yet establishes that final MHC
causes their present softness. Two full prior nulls make useful gain uncertain.

The minimal adaptation, only if root separately selects it, is:

1. Bind all299 original identities/order, current CA-off map/reference149,
   native crop(68,46,6896,4596), exact first-source WB/matrix and retained
   DisplayBaseline bits. Require `STREHL_FIX_CA=off` and profileNone for both
   actual baseline and extra-color pull. The chip's `STREHL_CA_BEFORE_MHC=off`
   only disables that historical stage and **does not** disable ordinary CA;
   copying it alone would compare a different optical treatment. Match the
   held current CPU/gather/probe environment, not the chip's old GPU requirement.
2. Reuse `full_source_supported`, `gather_full_source(first_slot=4)`,
   `chunk_plan` and `absorb_chunk`; retain canonical75/75/75/74 grouping even
   when twelve-plane memory planning would choose fewer chunks. Preflight all
   twelve pulls at the exact existing crop. Refuse missing support instead of
   silently adding an inset. Keep one original source at a time and reuse
   its actual baseline guide/variance/beta without another estimator.
3. In one source149 cost/checkpoint, exercise the real gather and twelve-plane
   synthesis. Verify known-four full-source pulls against the actual current
   consumer; retain the commissioned all-twelve phase/CA/support oracle and
   writer controls. A single source is not an RGB identity null: omitting
   final MHC is the intervention. Known-four/hull identity and direct-writer
   parity are the meaningful mechanical nulls. Measure current memory/time;
   historical paired costs are context only.
4. On one complete paired replay, require known-four and admissions bit-exact
   and the canonical RGB16 **and developed-linear payloads** identical to the
   retained current master before interpreting the candidate. Reuse the exact
   native developer; the old helper emits RGB16 only, so exporting the same
   pre-developer f32 camera-RGB and developed-linear payloads is a small writer
   adapter addition, not a changed signal path. Do not call those camera-RGB
   values untouched signed original measurements: source rounding and clipping
   have already happened. Bind original bytes/metadata before and after.

The previous controls are meaningful: flats run first, fractional color and
varying-focus truth exercise selection, all twelve color/site pulls have an
independent oracle, missing-blue support refuses, unequal chunks preserve
known-four values, and both actual writers match held development. They do
not prove weak-green/cross-depth safety in every insect feature or current
seven-band photographic success. Reuse them without a new sweep; preserve
their flat penalty and both complete negative results in the new receipt.

Then present the complete weevil JPEG, full RGB16 and float masters plus all
ten existing native witnesses against current CA-off and complete HeliconB4/B8.
Useful evidence would be cleaner existing hair/scale separation or junction
color without veil, false fringe, missing weak color or harder glints. A color
texture change alone is not recovered structure. Bug2 and flat60 remain later
transfer/adverse requirements before any generalization. This comparison does
not model occlusion, remove physical glare, repair the source MHC or satisfy
the native endpoint, even if the insect photograph improves.

Decision: no further global inverse continuation or duplicate shared-color
guide is justified here. An unchanged twelve-plane **diagnostic transfer** is
implementation-ready with the listed binding/writer work, but its two full
photographic negatives rule out portraying it as an untried promising native
architecture. If strictly native candidates are the only permitted next step,
this lane has no supported implementation-ready replacement today. No quality
gain or new numerical result is claimed.

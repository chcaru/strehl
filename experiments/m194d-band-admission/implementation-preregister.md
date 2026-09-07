# M194d implementation preregistration

2026-09-07. **Prospective; no product edit, build, candidate render or candidate
score has run.** Root review is required before implementation. This registers
one experiment against committed M194c
`04128e041dabc0bdb86c64526cd8155dd0a0fd07`, not a Phase-1/SOTA acceptance gate.

## Frozen question and arm

Does replacing exact below-floor rejection with a positive continuous baseline
weight reduce the known sparse flat-field selection behavior without losing
the independently rendered detail/color in the fixed known-scene matrix?

The only treatment is `AdmissionMode::FloorPedestalV1`:

```text
F = gate * beta_k * max(V_k,0)
q = max(E_k-F,0)
a = q/max(F,1 DN²)
w = exp(clamp(p_k*ln(hypot(a,1)/64), -80, 80))
```

All finite frames, including q=0, receive that weight. This heuristic has no
calibrated error probability. It changes neither the source noise/model nor
the measured-floor sequence. The comparator is `AdmissionMode::HardFloor`,
whose arithmetic and defaults must remain unchanged. Gate2, the existing
exponent/ramp, bands3, measured floor, mean base, existing hull, WB, model,
resampler and all postprocessing stay fixed. No parameter or seed search.

The companion `implementation-plan.md` names prior refusals, dimensional
limits, exact integration paths and runtime option. It is part of this
preregistration. The positive-baseline choice is newly proposed; its
relationship to the existing significance `hypot` is disclosed, not novel.

## Before-output implementation controls

Run component controls before any scored production output. A broken fixture
must be recorded as an instrument failure, corrected prospectively, and rerun
under a new source binding. Do not change the candidate in response to output.

| Control | Input that must make the check fail; expected discrimination |
|---|---|
| Near-zero singleton continuity | Nine frames, one interior checkerboard luma of amplitude8, others zero; choose the common test variance from its analytic band0 energy64 so its floor is64/(1+2^-10). Legacy has one positive weight and selects it. Candidate's normalized share must be close to1/9, not1. Check independent algebra and actual BandMerge output, not just helper weights. Reintroducing the q<=0 early return must fail. This arranged component energy is not noise-calibration evidence. |
| Actual lifecycle | Call FrameWorkspace::next_frame before every add. Distinct contributing frame values must change the result. Omitting the reset is a negative control that must fail the ordinary live-source assertion, preserving the M194c lesson. |
| Equal below-floor behavior | At q=0, equal weights must reach the actual num/den normalization; coefficient output agrees with the independently calculated all-frame mean within declared f32 rounding. Different F values with every q=0 still have equal candidate weights. A caller that zeroes them before accumulation or supplies a hard selector must be detected by the singleton test, not credited by the equal-mean placebo alone. |
| High-contrast preference | With the same fixed gate/p/model machinery, a clearly above-floor checkerboard competes with below-floor frames. The candidate must strongly favor the high-signal coefficient, approach the legacy ratio at high normalized excess, and differ from the arithmetic-mean destroyer. Use a separately preregistered high amplitude128 with the first fixture's variance; do not tune amplitude after seeing output. |
| Heterogeneous floors | Equal energy with two declared finite noise floors must follow the formula's ordered weights; zero-excess frames retain equal baseline weights. This confirms implementation of floor normalization, not its quality or physical correctness. A swapped/missing floor must fail. |
| Numeric guard | Scalar inputs include exact threshold, just below/above, finite small/large floors and powers1,2,3.92,8. Check finite positive weights, nondecreasing low-signal order, high-signal asymptote before clamp and explicit saturation when clamped. Tiny differences can round to equal weights; do not require impossible strict f32 monotonicity. Inject NaN/Inf or incompatible configuration and require a clear error/panic rather than a silently finite weight. Check actual component accumulators/output finite separately. Helper finiteness is not an arbitrary-N accumulator proof. |
| Numeric accumulation refusal | Three finite component frames, a10000-DN zero-DC checkerboard at background20000, p8, one band, floor1DN². The capped weight is finite but its product with the band coefficient exceeds f32. Candidate must refuse explicitly during accumulation, before hull/write, instead of returning a plausible clamped image. Test a separately arranged overflowing absorb and nonfinite reconstruction guard. A finite-weight-only guard must fail these controls. No lower log cap, f64 accumulator or changed weight law is introduced to rescue this case. |
| Default and option | MergeConfig::default and the original M194b options resolve HardFloor before any override. Missing/misspelled test-local option, plan/operator mismatch, supplied-mode/actual-config disagreement and altered external hashes refuse. Mixed-mode absorb refuses. Same config/manifest repeated is a valid placebo. An additional original-entry plane/noise-off/full9 render must retain actual M194c TIFF bytes; do not count the explicit forty-off matrix as unselected-default execution. |
| Actual production source | Changing a real consumed CFA site, model or interior curved placement changes a powered output. Equivalent padding/origin/odd-tail representations and unused poison remain byte-identical; source decode counts remain one per supplied frame unless an explicitly commissioned observer rereads them. |
| Constant and single input | Constant source output is preserved; N=1 is equivalent mathematically. Actual off/on TIFF identity for single4 is checked rather than assumed, because weighted float arithmetic may round differently. Any difference is reported, not hidden by the mathematical identity. |
| Bounded state | No new per-frame-retained arrays, reference fields or second decode pass. Inspect allocation sites and exercise different N using the real source/fold; record decode counts and retained input-array count. No RSS/M12 claim follows. |

The exact near-zero component output tolerance is fixed before its first run
from the f32 arithmetic scale: at the3000-DN background, at most0.002 DN
absolute difference from the independently computed candidate coefficient in
an interior block. A separate asserted difference of at least1 DN between
legacy and candidate proves that tolerance cannot absorb the intended effect.
The high-amplitude control must have normalized preferred share above0.99
and be closer to its selected checkerboard than to the nine-frame mean.
Component p=2 is used for the exact analytic band0 plant with one Laplacian
band; the production three-band schedule is a separate integration check.
These are software plant checks, not measured quality requirements.

The numeric contract is explicit refusal, not a promise for arbitrary finite
inputs. Candidate-only finite-state checks run after each fold/absorb and before
final hull projection; invalid energy/floor values refuse as well. No failure
may be hidden by an image clamp. The actual fixed matrix must complete with
finite intermediates and outputs. HardFloor is unchanged; finding an inherited
large-range limitation does not authorize repairing its arithmetic in this task.

## Fixed delivered-output matrix and provenance

Use exactly the20 manifests already made by M194b: flat and plane each have
noise-off plus seeds701,709,719,727,733,739,743,751; color and color-null each
have noise-off. Render full9 and original single4 for each:40 outputs per
mode,80 new TIFFs in total. No new producer execution, source-noise draws,
capture reads, sealed data, or representative timing run.

The original-entry default control is one additional unscored render of the
existing plane/noise-off/full9 case, separate from the80-output mode matrix.
Other powered component/layout controls are also unscored and cannot add
input-noise replicates to that matrix.

All40 new HardFloor outputs must match the saved M194c candidate2 whole-TIFF
hashes and decoded pixels. Match build stamp where the actual output tag
requires it; record actual source separately. A same-source repeated output
is a placebo, not an independent noise repeat. A failed byte control blocks
an operator attribution until explained and repaired without altering data.

The prospective root controller must bind the exact new driver/runner/scorer
sources and source closure including external Rust includes. It must retain
visible `Compiling` evidence, command/feature/config data, original Cargo
artifact path/hash/size, identical copied executable hash, input/plan/receipt
hashes and source hashes before and after the batch. No ignored new fields or
hardcoded original SoftPower label can stand in for the operator value.

Current baseline source SHA-256 values read before this plan:

| File | SHA-256 |
|---|---|
| core `pyramid.rs` | `7b6376e68a1a6488f958b85e65cfdc57dfe8b8826d4612d8429d08f8743632ac` |
| CLI `merge_cmd.rs` | `693d0539b09302f77bdafd27b30356560f4cc2740d7414cc1c163b7bf1b5335f` |
| `known-scene-benchmark.rs` | `4ac1d2e82aef7ca4428b7e3fd276f691a50d4be8e0e2152ad00be00de8db2034` |
| M138 corrected contract | `46dff3cdeeeea6054b38185518b39964d00ac35880503273f7d6184dced5005e` |

The M138 contract remains draft. No M143/Phase-1 freeze is inferred from the
existence of a report or commit. The new local fixture receipt is not a
general external geometry/authenticity adapter.

## Outcome evidence and decisive falsifiers

Root and independent reviewers own the final comparison specification before
output. The following are mandatory and cannot be dropped by that specification:

- Preserve native Crop(9,7,142,106), output284x212, canonical offset(18,14)
  and fixed native ROI x[64,256),y[64,176),21504 pixels. No output registration,
  gain fitting, per-arm exclusions, new best-frame choice or target changes.
- Read actual TIFFs and retain **both** ideal-latent and optical-observation
  targets. Report every noise-off/noisy per-channel error and plane wave
  amplitude; color and achromatic null remain mandatory. More blur can lower
  noisy error, and greater edge/noise power can mimic detail, so neither alone
  can support a favorable quality finding.
- Flat temporal noise comes first. Use all eight fixed repeats, per channel,
  with whole-repeat paired uncertainty. Do not compare temporal sigma to
  spatial SD or claim independent pixels. Shared plant/model coefficients
  validate the operator, not the physical camera calibration.
- Preserve sparse truth-error tails alongside averages: signed extrema, whole
  ROI maximum absolute error and p99/p99.9 absolute error using NumPy linear
  quantiles, as fixed in root's comparison preregistration. Keep canonical
  coordinates with row-major first-tie convention, maximum increase/decrease
  in absolute truth error and largest output movement with signed truth-error
  change. These have no added threshold/exceedance-count acceptance rule.
  Candidate-minus-baseline movement
  and candidate truth error are distinct arrays and must be reported separately.
- Include the already observed red sample at native(142,170), flat709/full9:
  M194c moved it from2997.01448 to3101.46139 DN around3000-DN truth. Its
  prospective M194d behavior is now a fixed diagnostic, with selection history
  disclosed. It is not an independent held-out site. Report all other sites
  and repeats so improving this one cannot conceal a worse tail elsewhere.
- Lower noise with material loss to either truth target, noise-off plane waves,
  or analytic color is a tradeoff/failure, not a noise win promoted to quality.
  Worse temporal variance or sparse truth-error tails falsifies the intended
  flat-field benefit. No pooled winner can cancel an adverse channel/target.
- Kish width, winner concentration, positive weights, hull membership, or
  denominator continuity cannot accept this candidate. No width prefilter,
  inherited0.90 threshold, physical M135 claim, PHASE1_GO or SOTA score is used.

A clear structural defect, failed live-control or unbound evidence yields
`INSTRUMENT_INVALID`. A valid measured tradeoff or failure is retained as such
and ends this fixed candidate; it does not trigger a hidden retuning. A fully
favorable matrix would support only further bounded testing on these known
software scenes. It cannot promote a default, generalize to occlusion/deep
stacks, calibrate sensors, or close the scorecard.

## Author/independent boundary

Implementation_audit owns this plan and the later scoped code/author checks.
Directional_detail independently challenges the operator and re-chooses
component/layout controls; roadmap_audit independently specifies/checks the
comparison. Root owns the controller, final interpretation, schedule and commit.
No process termination, shared host lock, protected-data access, or source
mutation is authorized by this design document.

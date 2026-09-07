# Prospective quality design: target and support review

2026-09-07, implementation_audit. **Source inspection and derived prerequisites
only.** No geometry population, radiance, noise, product render or quality score
was run for this review. It reviews `next-quality-design.md` at
`e0832e307589e2439c8e6204136f7f3fdf47328b9dcbb35a55948bcee80bde35`;
it does not register the later experiment or change the released M194g source.

## Required correction: distinguish three different supports

The proposed `abs(h)>8` detail mask does **not** establish that the background
endpoint's MHC observation uses only background. With identity placement,
`h=x-.15*y-142`, the source unit-cell half-width in height is
`H=(abs(n_x)+abs(n_y))/2=.575`. Foreground visibility has pupil radius
`R_f=abs(d_f)*norm(n)` regardless of which layer is in focus. Endpoint0 has
`d_f=-6`, `d_b=0`; endpoint4 has `d_f=0`, `d_b=6`.

The actual union of nonzero MHC taps in `demosaic.rs` (`F_G/F_H/F_V/F_X`,
`demosaic_malvar_row`) is contained in the radius2 diamond, not merely an
unspecified five-by-five square. Its symmetric support in direction n is
`D=2*max(abs(n_x),abs(n_y))=2`. Thus, conditional on the declared identity
gather and single-input preservation, sufficient strict all-RGB conditions are:

- Endpoint0 background: `h < -(H + 6*sqrt(1.0225) + D)`, approximately `-8.6421`.
- Endpoint4 foreground: `h > H + D = 2.575`.

Equality stays outside the fully-visible mask. A simpler symmetric mask
`abs(h) > H + max_frame(R_f) + D` is conservative for all five source-frame
MHC observations; it must still distinguish foreground and background signs.
An axis-aligned square bound `D=2*(abs(n_x)+abs(n_y))=2.3` is also conservative
but unnecessarily discards more sites. Do not choose between them from output
errors. Per-channel/parity support can be narrower; freeze that only if its
extra complexity serves the consumer.

**Concrete prospective destroyer:** native `(150,110)` lies inside the proposed
window and has `h=-8.5`, passing the old background `abs(h)>8` rule. At this R
site, both missing-channel MHC stencils have a nonzero `(+2,0)` tap. The source
cell at that tap has maximum foreground-intersection height
`-8.5+2+.575+6*sqrt(1.0225)>0`. It is not fully background-visible. This proves
the old mask's logical insufficiency without evaluating radiance. A corrected
mask must reject this site, and admit genuinely farther background companions.

For nonidentity future inputs, use the actual source-coordinate dependencies,
not the identity scalar threshold. For each nonzero delivered-channel tap delta,
derive the source site's real-affine height h_delta, its transformed unit-cell
support H_delta and foreground pupil radius R_delta; require every
`h_delta-H_delta-R_delta>0` for foreground or every
`h_delta+H_delta+R_delta<0` for background. Add actual resampler dependencies if
the pull is noninteger. Exact-real support does not by itself prove equality
with rounded production evaluation; the separately commissioned numerical and
actual input-to-writer checks remain necessary near representable tangencies.

There are two additional prerequisites before reducing the actual endpoint
path to one source mosaic plus final MHC. `warp_frame_in_place_fullres` first
demosaics, samples and remosaics even an identity map. At exact integer identity
with CA disabled the selected CFA channel is its measured sample; the future
adapter must preserve the existing live identity/padding/coordinate controls.
Also bind the actual single-input `Hull::InputRange` (or tighter bound): the
final input hull has `lo==hi` at each CFA site and removes pyramid reconstruction
dependence there. If that mode or identity preservation changes, do not reuse
the simplified support proof. The actual TIFF remains an observation including
quantization and MHC, not continuous-layer truth.

The **74-native output-border guard** is a different statement. It bounds local
three-band dependencies conditional on fixed beta; it does not prove a
multi-frame output is unaffected by the depth boundary. To conservatively
exclude opposite-layer contributions from that whole local route would add
`74*(abs(n_x)+abs(n_y))=85.1` in mask-height support before source cell/pupil
support. The proposed central window cannot provide such a pure-layer region.
Its outside-band masks can be called input-defined surface detail diagnostics,
but not an isolation of boundary-free merge behavior. Global measured beta also
prevents this local guard from proving whole-domain invariance.

## Ideal target and endpoint observations

K=0 removes pupil displacement, not within-cell occlusion. The independent
target must integrate `A(q)*F(q)+(1-A(q))*B(q)` over each unit cell, including
both polygon portions. A centre mask or independently averaged alpha and
background remains a live destroyer. The previously commissioned clipping and
first-moment controls can support this new target only with its fixed larger
coordinates and final source bindings.

One clear unquantized ideal RGB definition at every native centre is
`T_c(z)=.25*c_c*WB_f32,c*S_K0(z)` in post-WB DN, with each represented f32 WB
coefficient used explicitly. This makes it clear that a same-centre ideal RGB
field is supplied for all three channels, whereas a real CFA measured only one.
Actual TIFF decoding is `code*14848/65535`, with no second black subtraction.
Input ties-to-even and final TIFF half-up quantization belong to the observed
path, not silently to this ideal. Include their possible discrepancy in the
instrument commission. Do not apply MHC to the ideal and continue calling that
the same target: an independently named K0 pipeline observation is another
reference and would require a separately registered output if desired.

Endpoint0/4 TIFFs are correctly kept separate. Their finite-sampling, MHC and
quantization error can remain even on the corrected full-layer masks. Comparing
both modes against the same two observations is informative, but matching a
blurred or aliased observation cannot erase an ideal-target loss. No splice,
per-pixel minimum or output-derived mask should enter the common reference.

## Noise and eight-repeat quantities

The draft correctly puts `c*S` **before** the Poisson draw. Before rounding,
the raw-DN variance is `.25^2*(c*S+4^2)`; applying c after Poisson gives the
wrong shot term `.25^2*c^2*S`. This distinguishes the live wrong-law plant on
red and blue even though green cannot see it. After declared WB, multiplication
by `WB_f32,c^2` also applies to variance. These are properties of the supplied
software law, not sensor-calibration evidence. Dark controls must separately
observe signed electron/read fluctuations, encoded values below black, and
the product's later black-subtraction clamp; those are different boundaries.

Eight separately keyed repeats permit per-site unbiased sample variance with
denominator7. Pair the two modes on each identical CFA bundle. Aggregate fixed
site variances without calling spatial scatter temporal noise; uncertainty must
resample/delete whole repeats, preserving spatial correlation and paired modes.
The noisy MSE is the mean of eight per-repeat squared errors to a common target.
For each pixel, `mean(error)^2-sample_variance/8` is the corresponding unbiased
squared-bias estimator, and may be negative. Its sum with sample variance equals
the per-repeat MSE algebraically, so that equality is an arithmetic consistency
check, not independent evidence. Repeat-mean minus each mode's own noise-off
output measures noise-dependent algorithm bias, not ranking fidelity.

The two-wave detail readout needs a fixed design matrix containing an intercept
and both sine/cosine pairs, explicit native-to-canonical coordinates and a
condition/rank guard. Finite masked windows do not make these columns orthogonal.
Use the identical readout on independently generated target values; a fitted
gain/phase must not subsequently be removed from the error. Retain the flat,
phase-shift, blur and extra-wave controls before production scoring, including
an amplitude-increase destroyer so manufactured contrast is not credited.

The proposed 90 CFA files and 36 paired-mode TIFFs plus two endpoint TIFFs are
consistent: two scenes, nine bundles, five original frames; two modes per
bundle. None of these counts grants a quality pass. The corrected optical masks,
actual common output domain, effective bands/measured floor and both targets
must be frozen before any of the 38 intended images is scored.

## Inspection record

Read-only `Get-Content`, `rg`/`rg --files` and `Get-FileHash` inspected the draft,
M194e support audit, frozen model, `align_cmd::warp_frame_in_place_fullres`,
`merge_cmd::load_frame/extract_planes`, actual MHC tap constants and
`BandMerge::finish`/`hull_default`. A few initial guessed source filenames were
absent; the searches were corrected to actual paths and no result was inferred
from those errors. No executable model/product command was run for this review.

Inspected source pins: demosaic
`425d6889485011cf6f2aaf57b0b873f15fd6ee3250853f3ba5f6540b496b3810`;
align_cmd `b3de7738151a6bc0500c66dd916f9fcb20cdb9be0bf698ad00425d3ebb397c69`;
pyramid
`848b485271abc48ee496ee69d70a1e01f45074bfbccde7a7ca076ded90f77d9e`.

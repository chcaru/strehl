# V-HEADTOHEAD3 preregistration — tone-neutral competitive baseline

Frozen at 2026-09-02T21:35:35-07:00, before computing an outcome spectrum
from any of the four renders below.  File dimensions, types, byte counts and
hashes were inspected first for admissibility and provenance; no detail
statistic or registration was measured.

Amended at 2026-09-02T21:38-07:00, still before reading outcome pixels: the
fixed 0.30 real-ROI correlation gate was replaced by an empirical shift-null
gate.  The already-read prior report states that the admissible fork pair
reaches only 0.0664 correlation at the corrected sign, so the fixed gate would
have made the requested comparison impossible by construction.  No other term
changed.

## Question and scope

On the two same-bracket comparator renders that still exist, does strehl carry
more or less **detail-specific ordinal spatial structure** in each admitted
frequency band?  This is a pipeline comparison, not an algorithm-only
comparison: the comparators consumed Lightroom-developed TIFFs, while strehl
consumed the ARWs.  The strehl arm is the shipped `--srgb` master from pinned
commit `6af834dac08d6605aee7ea3ad75809fdf6313770`.

The earlier 17–27% fine-detail deficit is not a prior.  It is retracted in
`docs/research/V-HEADTOHEAD.md`; `docs/research/V-HEADTOHEAD2.md` shows that a
tone curve accounts for 94.8%, 109.9% and 267.1% of its corrected three-band
gap.  That report also corrects a registration-sign defect.  Mechanical prior
art commissioning and searches were run before this document; no committed
report already answers the tone-neutral question.  The user dispatch allocates
the `V-HEADTOHEAD3` stem; the central AGENTS.md ledger is outside this lane's
write permission.

Two admissible pairings exist:

| ID | strehl | comparator | same source bracket |
| --- | --- | --- | --- |
| `113` | `C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff`, SHA-256 `4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F`, 197801290 B | `D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif`, SHA-256 `B240FE4016E97EBB194497B2798A095C63C490C4FFF54018D48D34C7523719A0`, 196453660 B, Zerene PMax | 63 ARWs / 63 input TIFFs |
| `cb` | `C:\dev\strehl-out\DELIVER-V6\masters\coffee-bean.tiff`, SHA-256 `F38CA50ED1A680FA4DBCDD8D0513BE538DD31634B4E89AC6A34885944790A2EC`, 197801290 B | `C:\dev\macro\out\coffee-bean\stack.tif`, SHA-256 `8636C20D73CA0CB1F57DB89BF8553ABC166E0FBC517E5C62A07C74DEE509066E`, 393326272 B, focus-stack fork | 105 ARWs / 105 input TIFFs |

The executable checker must hash the byte streams itself.  Its RED plant
changes one independently frozen nibble and must be rejected; the
preregistration text is not used as the checker's oracle.

The frozen strehl executable is
`C:\dev\strehl-out\DELIVER-V6\bin\strehl.exe`, SHA-256
`2A7BCD7B098D3523AB54491784436EB5F69A358ECFBEC5155108EC552D0712B7`,
9859584 B.  DELIVER-V6 records the complete invocation as
`strehl.exe stack <absolute ARW directory> -o <absolute master> --srgb`,
private `STREHL_CACHE_DIR`, and all other `STREHL_*` unset.  This lane does not
rerender.  No Helicon output was found in `C:\dev`, `D:\edited`, or
`D:\personal\macro`; extra Zerene marker renders are inadmissible because the
prior reports establish that their captures do not match a strehl bracket.

## Declared bias and failure directions

My expected and investigator-favoured direction is **strehl leads**, because
that would close the retracted deficit cleanly.  I will therefore treat
strehl-leading values as the direction requiring the most aggressive
confound checks.

Ordinal band share can be fooled upward by noise, spatial sharpening, ringing,
demosaic texture, resampling, or clipping-created boundaries; it can be fooled
downward by denoising, blur, a demosaic low-pass, or rank ties.  It measures
rendered ordinal structure, not MTF or truth fidelity.  Registration failure
can move either way.  The low-texture difference-in-differences control below
removes a common noise/processing floor but cannot distinguish faithful detail
from scene-dependent sharpening.  Those limitations will constrain the nouns
used in the verdict.

## Geometry and registration

Only the green plane is read.  Geometry is estimated from every eighth native
pixel after replacing each sampled plane by its global mid-rank field.
Consequently a strictly increasing pointwise remap cannot change the geometry
input.  A scale sweep zooms comparator ranks for registration only, finds an
interior correlation maximum, then refines to 0.001.  Its scale `s` means one
comparator pixel spans `s` strehl pixels.  Translation and local residual
integer corrections are found by rank phase correlation.

Measurement pixels are never resampled.  A 512×512 strehl ROI is paired with
the nearest native comparator crop of side `round(512/s)`.  Comparator band
edges are multiplied by `s`, so both spectra describe the same scene
frequencies.  Candidate strehl centres are a fixed 512-pixel grid, at least
384 pixels from each edge.  A pair is admissible only when both crops are in
bounds, its registered rank correlation exceeds the 99.9th percentile of 64
fixed, non-overlapping toroidal-shift correlations for that ROI, registration
improves correlation by at least 0.02 over no correction, and neither crop has
more than 1.0% of samples at a container rail.  This null-calibrated gate is
used instead of a fixed correlation threshold because the prior corpus already
records only 0.0664 correlation for the fork pair even at the repaired sign;
silently choosing 0.30 would preclude measuring that available comparator.
All exclusions and coverage are reported.

`integer_shift(reference, moving)` must return the **correction** `(-dy,-dx)`
when the moving image was planted at displacement `(dy,dx)`.  It is
commissioned on `(0,0), (1,0), (0,-1), (2,3), (-3,2), (5,-5)`, with equality
after correction checked directly against the untouched source array.  A
wrong-sign implementation and a no-op implementation must each go RED.
Synthetic scale plants at 0.970 and 1.035 must recover within 0.003 and have an
interior maximum; a forced endpoint range must go RED.

## Tone-invariant statistic

For each native ROI with `N` samples, let `r_j` be its average rank among the
ROI values and define

`q_j = (r_j - (N+1)/2) / N`.

After mean removal and a separable Hann window, let `P_k` be summed squared FFT
magnitude in radial band `k`.  The ordinal band share is

`A_k = P_k / sum(P_b for all registered bands b)`.

The predeclared scene bands, in cycles per strehl pixel, are:

`[0.02,0.05)`, `[0.05,0.10)`, `[0.10,0.20)`, `[0.20,0.25)`,
`[0.25,0.30)`, and `[0.30,0.40)`.

`[0.40,0.48)` is excluded before measurement because demosaic, Nyquist and
noise confounds dominate there in the prior corpus.  Bands that fail the blur
reach control below are reported but labelled NOT SENSITIVE.

For paired ROI `i`, `d_ik = ln(A_strehl/A_comparator)`.  Texture is defined
symmetrically as the geometric mean of the arms' total ordinal share from
0.02–0.20 cyc/px.  Among admissible ROIs, the bottom quartile is the real
low-texture/flat control, the top half is the detail stratum, and the middle
quartile is unused.  The primary effect is

`theta_k = mean(d_ik in detail) - mean(d_ik in low-texture)`,

with `R_adj = exp(theta_k)`.  The unadjusted `R_detail` and the flat-control
`R_flat` are also mandatory.  This subtraction prevents a general
high-frequency/noise advantage from being called detail-specific structure.

Uncertainty is a two-stratum paired bootstrap (10,000 replicates, PCG64 seed
`20260902`), independently resampling ROI pairs within detail and
low-texture strata.  The percentile 95% interval is preregistered; a
leave-one-ROI-out range and four spatial-quadrant estimates are robustness
diagnostics, not alternate headline estimators.

### Invariance theorem and exception

For any strictly increasing pointwise scalar map `phi`,
`x_a < x_b iff phi(x_a) < phi(x_b)` and equality is also preserved.  Average
ranks, `q`, every subsequent FFT quantity, the ROI strata, and rank-based
registration are therefore exactly unchanged.  This is algebra, but it is
still commissioned on real pixels.  No nontrivial image statistic can be
invariant to an arbitrary non-decreasing map that is allowed to collapse the
whole image to a constant.  Clipping, quantisation that creates new ties,
spatially varying maps, channel mixing, and non-monotone local contrast are
explicit exceptions; rail exclusion, tie census, and adversarial plants bound
rather than wish away those cases.

## Commissioning, RED plants, and fixed predicates

Before real outcome measurement, the instrument must pass all of these:

1. **External rank oracle:** a fixed 4×4 array and ranks written independently
   of the implementation must match exactly.  Permuting two expected ranks
   must go RED.
2. **Tone invariance:** identity versus affine, gamma 3.0, and a strong
   strictly increasing logistic S-curve must move every `A_k` and `R_adj` by at
   most `1e-10`, first on synthetic data and then on an actual ROI.  Raw
   intensity band share must move by at least 5% under one of the same curves
   (potency).  Replacing rank share with raw share must go RED.
3. **Non-monotone destroyer:** solarisation must move at least one ordinal band
   by 5%; a constant/blind statistic must go RED on this potency check.
4. **Registration sign:** all six shifts above recover the exact correction
   and make the corrected interior equal the untouched source.  Wrong sign and
   no correction each go RED.
5. **Scale:** both known scales recover within 0.003.  A range with the true
   scale outside it must go RED as “no interior maximum.”
6. **Blur reach:** on fixed-seed 1/f texture plus edges, Gaussian sigma
   `0,0.5,1,2` must monotonically reduce the combined 0.20–0.40 ordinal share
   by at least 15% from sigma 0 to 2.  A disabled blur plant must go RED.
   Per-band absolute change must be at least 5% for that band to be SENSITIVE.
7. **Flat/noise placebo:** identical constant-plus-fixed-noise arms must read
   `R_adj=1` to `1e-10`.  Adding the same independent fine noise process to
   comparator detail and comparator flat must move unadjusted fine share but
   leave the adjusted effect within 5%; omitting the flat subtraction must go
   RED.
8. **Tie/clipping exposure:** a 12-bit quantisation and a 1%/99% clip are
   measured.  They are not expected to be invariant; failure to detect a
   changed tie census must go RED.  Real-arm largest tie groups and rail
   fractions are published.

Every control has an input that can fail it.  A commissioning run is accepted
only if every positive control is GREEN and every listed sabotage is observed
RED.  The checker records control counts and readings; exceptions are not
silently waived.

## Verdict rules

For a SENSITIVE band:

* **LEADS:** lower 95% bound of `R_adj` is above `1.05`;
* **TRAILS:** upper 95% bound is below `1/1.05 = 0.952381`;
* **UNRESOLVED:** otherwise.

The 5% region is a practical-equivalence guard against declaring tiny
rank-spectrum shifts.  A class is additionally downgraded to UNRESOLVED if
fewer than 12 detail or 6 low-texture ROIs survive, if the leave-one-out class
can reverse, or if two or more spatial quadrants have opposite signed point
effects.  A band that fails blur reach is NOT SENSITIVE.  If the two subjects'
same-band classes oppose, the cross-subject conclusion is NOT ROBUST rather
than averaged.  Results are stated as ordinal rendered structure; the
sharpening/noise plants decide how strongly they can be interpreted as
faithful detail.

The author code and an independent implementation must agree on geometry scale
within 0.5%, per-band class, and `R_adj` within the sum of their bootstrap
half-widths.  Disagreement is published, not reconciled.

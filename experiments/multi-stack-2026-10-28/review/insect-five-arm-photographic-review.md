# Independent complete insect comparison: five native arms

2026-10-28, root/independent_review. VERIFIED complete fixed-display overview inspection and all nine frozen native384crops for each of: insect-only-106-4, insect-only-107-4, insect-pooled-4, insect-repeat-4 and insect-primary-6. Unchanged legacy106/107 complete overviews and contextual native crops were reviewed earlier. Full masters/photographs are retained; this reviewer ran no RAW or engine job.

## Binding and controls

The original witness selection preceded candidate viewing; geometry-only mapping is frozen in roi-mapped-frozen.json. All five native arms have identical saved warpmap text, exact coefficient rows, reference149 and canvas[38,26,3440,2292]. Every inspected crop is384x384native pixels with no spatial resampling. Both insect passes have identical actual WB[1.5986328125,1,2.708984375], so the HDR WB confound does not apply here.

The source count is299for each only-pass arm and598for pooled/repeat/primary. The full-session completion records still describe598session inputs for research only-pass controls; render receipts correctly identify299consumed frames. Each frame's luma/color beta, samples/realizations, gain, coverage, original clipping count, path and pass exactly match that frame's repeat4 receipt. The pooled recipe differs from repeat only in grouping_enabled=false. Primary and only-pass recipes are otherwise identical. This checks actual producing settings, not just arm filenames.

MEASURED binding command, exit0:

    python -X faulthandler -I experiments/multi-stack-2026-10-28/review/bind-insect-five-arm-review.py

insect-five-arm-review-binding.json records all complete-master, complete-display and crop-receipt hashes, and the source/operator checks. primary-insect-geometry-check.json records the exact primary/only107geometry comparison. All five use transform SHA256 c6adc8f592bb83a49df8909b3475ad3a933e431260913f632efae0f42e7dcc3a, frozen from baseline106 only.

Root prepared repeat/pooled/only106displays. This reviewer prepared only107andprimary using the existing independently commissioned helper, no auto-tone or retuning:

    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/prepare-review.py render --master outputs/multi-stack/insect-only-107-4/master.tiff --destination experiments/multi-stack-2026-10-28/review/full-displays/insect-only-107-4 --label insect-only-107-4 --transform outputs/multi-stack/independent-review/fixed-transform.json
    python -X faulthandler -I experiments/multi-stack-2026-10-28/challenge/prepare-review.py render --master outputs/multi-stack/insect-primary-6/master.tiff --destination experiments/multi-stack-2026-10-28/review/full-displays/insect-primary-6 --label insect-primary-6 --transform outputs/multi-stack/independent-review/fixed-transform.json

Both exited0, cwd the isolated worktree, OMP/OpenBLAS/MKL worker counts1. The helper checked every master sample finite and produced the complete fixed display. copy-frozen-native-crops.py verified each complete PNG, transform, ICC, exact map/canvas and pixel readback. Optional second argument supplies the independent review display directory. Native crops were viewed with detail=original. These preparation times are not engine benchmarks.

## Findings across the five arms

No gross missing anatomy, new tiled seam, broken framing or broad hue discontinuity was apparent in the complete outputs. This is complete-scene orientation evidence, not a claim of native detail quality. At the nine native witnesses:

- Dark background: faint colored tracks are less conspicuous than legacy106 in native outputs, including native-only106. Repeat versus pooled differences are subtle. Therefore this cannot be credited to averaging alone, and it is not temporal-noise evidence.
- Cyan scales and bright glint: changed highlight-dot shapes already occur in native-only106 versus legacy106. Adding107changes local dot intensities/shapes further. No confidently resolved additional boundary detail from repeat grouping was established.
- Dark wing band: native-only106and107have visibly different local dark/bright fine structure. Pooled/repeat/primary retain a granular blend; primary changes some local contrast, but a coherent improvement is not established.
- Upper leg and antenna hairs: filaments remain in every arm, with double/colored fringes retained. Pooled/repeat are extremely similar; primary does not clearly remove the fringes or establish extra resolved tips.
- Wing-leg occlusion: the bright underlying blue/green leg and textured lobe track pass107, both legacy and native. Native-only106remains darker there. Pooled, repeat and primary106all retain the pass107-like region. This is not newly invented anatomy, but it is a substantial appearance difference to keep visible in the result assessment.
- Blue/cyan surface: no broad hue break, but fine edge/texture differences remain. Repeat versus pooled does not show a clear photographic improvement in this witness.
- Face edge: curved dark boundary remains continuous. Local bright texture differs; no large new seam or clearly resolved-detail gain appears.

ARGUED from these inspected witnesses: no clear fine-detail or deghosting benefit from repeat averaging has been established. This is not evidence that the implementation is a no-op or that no scene could benefit. The producing-path counters confirm actual averaging: repeat480groups versus pooled598singletons, with889,604,344averaged finest-level group coefficients versus0. All nine RGB8native crops differ (mean absolute code deltas0.0214-0.3883, sparse maxima16-26). Those mechanics and code differences are not quality scores.

Explicit primary is also active: the finest-level40,130,780ordinary fallback coefficients in automatic repeat become40,130,780primary fallback coefficients with primary106, while its averaged count is unchanged. The primary does not globally restore106's occlusion appearance because the documented policy applies to supported matched-group disagreements; unmatched observations and other bands can still carry107content. Do not describe primary as preserving every pixel or removing all motion/occlusion differences.

## Conclusion and remaining limits

The complete campaign establishes functioning opt-in multi-pass outputs, meaningful control paths and a bounded optional-primary policy. It does not establish a net photographic quality improvement over ordinary stacking or a repeat-averaging improvement on this insect scene. Existing ordinary one-pass equivalence is separately established by the retained whole-output regression receipts. Nothing here justifies changing that mainline default.

Native-only versus legacy comparisons still confound geometry, gather/resampling, scale and reconstruction changes; frozen landmark mapping is not pixel registration. The two real capture passes can differ in focus, occlusion and reflectance. No gradient-energy/FRC/noise-standard-deviation surrogate was used as a quality verdict. Additional adverse regions may be documented later, explicitly post hoc, but the original witness freeze should remain intact.

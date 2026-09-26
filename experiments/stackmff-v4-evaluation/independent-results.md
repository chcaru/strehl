# Independent result: fixed StackMFF V4 pilot

**MEASURED / visually reviewed — reject this three-source result for newly
introduced selection seams.** Do not proceed to a 488-source or full-image
route from this observation. No tuning, postprocessing or alternate crop was
performed by this reviewer.

I viewed the existing complete marigold baseline for orientation, then the
entire 384-pixel baseline, candidate and donor 112/152/320 PNGs at native scale. The candidate
does retain the shorter, brighter lower-right tips visible in 112 and the long,
slanted upper-right strands visible in 152. That is a real distinction from
substituting either single source. However, it introduces conspicuous irregular
brightness/color islands across the upper half, through the left-central
smooth petal and beside the fan on the right. The individual source images
have smooth transitions there. These new boundaries are visible well inside
the two-pixel MHC border, and the saved source map shows corresponding changes
of source ownership. The resulting patchwork is not acceptable contact
cleanup. No quantitative noise or sharpening claim is made from these views.

The complete 488-source baseline contains additional fine loops and intermediate-focus
detail missing from both focused pilot donors. I do **not** attribute those
absences in the candidate to a learned-selection failure: this three-source input lacks
that information. The negative decision rests on damage introduced while
combining the supplied sources. The pilot also lacks full-image network
context, so this does not establish that every context or every learned
method must fail. It closes the frozen model/ROI trial and supplies no complete
stack improvement claim.

Execution fidelity passed. The model loaded all 439 checkpoint state entries
strictly, with finite values and the constructor restored after suppressing
discarded ImageNet initialization. Mixed-map reconstruction detected both
source-swap and index-shift destroyers. Duplicate and constant inputs preserved
their selected grayscale and RGB16 values. The fixed reverse order has zero
remapped-index, grayscale or RGB disagreement. The finite-logit observer covered
all four prescribed forwards; the fifth primary call with it removed produced
identical grayscale, indices and RGB16 hashes. These checks establish the
implemented comparator, not photographic quality.

I independently read the saved candidate TIFF and, separately for each original
source index, compared its masked RGB16 pixels with the corresponding saved
donor TIFF. Every selected vector matches at the same address. The saved ICC
and complete candidate-array hash also match the receipt. All five inspected
PNG arrays equal the same prescribed quantization of their RGB16 TIFFs. Thus the visible
islands are not a PNG display conversion or misindexed reconstruction artifact.
The explicit RGB16-to-float grayscale adaptation remains distinct from the
official 8-bit loader; no resize or extra tone operation was used.

Root executed `pilot.py run --upstream
experiments/stackmff-v4-evaluation/upstream-2 --out
experiments/stackmff-v4-evaluation/pilot-1` under the bounded wrapper; exact
command/environment are in `job-1/invocation.json`. The job completed in 4.625s
with 126,810,112 peak CUDA allocated bytes. This includes the small pilot and
controls, not a full-stack speed measurement. Attention memory/context for 488
sources was not exercised.

Receipt SHA-256:
`c9028266644b721845927149310595827377c25a57b8b537302726f481b435a6`.
Candidate TIFF SHA-256:
`bd5167c8cb347e195379b6614de5dcac5e19118c504f8d33218733be8fdbedab`.
The retained TIFF covers the entire 384-pixel pilot region, not a complete stack output.

# Fixed prepared-TIFF comparison

Independent protocol review, 2026-09-19. No Helicon execution by this reviewer.
Use installed Helicon Focus **8.3.11**, not an unqualified latest-version claim.
Run two fixed methods once each, with the same complete ascending manifest of
70 files DSC00094.tiff through DSC00163.tiff from
`experiments/quality-september19/vitamin-c-comparator-2/developed/`.
No preview-driven tuning, parameter sweep, retouching or output blending.

## Vendor-supported choices

The official v8 guide describes B as depth-map based and requiring consecutive
focus order; C uses a pyramid and can increase contrast/glare. Its comparison
table favours B for glare and C for complex overlapping detail. Radius applies
only to A/B. Smoothing affects B's depth map and C's combination of sharp areas.
The guide documents `-mp:1` for B, `-mp:2` for C, `-rp`, `-sp`, `-sort:asc`,
`-i` for a newline-delimited input manifest, and `-tif:u` for uncompressed TIFF.
It does not establish radius8/smoothing4 as optimal for this stack.
[Helicon Focus 8 User Guide](https://www.heliconsoft.com/focus/help/english/HeliconFocus.html).

Fix B to `-mp:1 -rp:8 -sp:4 -sort:asc`; fix C to
`-mp:2 -sp:4 -sort:asc`. Omit radius for C; if retained for runner consistency,
record it as inactive. Both runs use `-silent -noprogress -tif:u`, an explicit
manifest and unique output paths. Preserve the consecutive capture sequence;
do not choose a reverse order after inspecting results.

The guide describes alignment limits between consecutive images, optional
brightness equalization, interpolation and automatic edge cropping. It does
not supply complete numerical defaults or all CLI interpolation mappings.
[Helicon Focus 8 preferences](https://www.heliconsoft.com/focus/help/english/HeliconFocus.html).

Keep the installed alignment settings unchanged between B/C. Capture their
values, brightness adjustment, interpolation, automatic crop, depth feathering,
and GPU setting if accessible. Otherwise mark each as unknown application
state; do not manufacture explicit values from guesses or turn alignment off.
The comparison remains useful but cannot establish reproducibility across a
fresh installation. Bind the executable, input manifest, input hashes, actual
command, logs, output dimensions/bit depth/profile and output hashes. Retain
both outputs whatever their result. Check full-resolution output and visible
trial overlays independently; the two-frame TIFF witness is compatibility
evidence, not a full-stack quality verdict.

## What the comparison measures

The retained development receipt says RGB16 7032x4688 and an ICC profile matching
the Strehl baseline. Development tone is [0.09042,0.914606,0.55], reconstructed
from a six-decimal description rather than exact original f32 values. The
retained provenance explicitly places tone before external stacking. Helicon
and the fork receive identical prepared TIFFs; Strehl merges CFA before final
development. Thus this compares complete available workflows on the same
captures. It cannot isolate merge algorithms, RAW information use, demosaicing,
alignment, or brightness normalization. The failed RAW loader witness does not
show that Helicon lacks RAW support. Do not include development-free timings
in a RAW-to-output speed comparison. No causal, speed or SOTA headline follows.

Inspect actual output ICC metadata before generating views. Use one documented
colour-managed display path; never apply a second tone curve or independently
normalize each result. If an output profile is absent or cannot be established,
qualify colour judgements rather than silently assigning a profile.

## Frozen visual comparison

Compare complete overviews for missing content, alignment distortions and broad
colour/contrast changes. Then inspect native samples, flat region first, in the
five regions already frozen in
`experiments/quality-september19/vitamin-c-review-1/regions.json`:

| Region | Strehl output x,y,w,h | Question |
| --- | --- | --- |
| pale-background | 400,1150,384,384 | Noise, blotches, false texture or tonal seams? |
| facet-edges | 2500,2700,384,384 | Are glint fans reduced while real facet boundaries remain distinct? |
| fine-crystals | 4200,1700,384,384 | Genuine small structures/colour retained, or merely more contrast? |
| bright-facet | 1150,3850,384,384 | Highlight shape, transitions and chromatic fringes? |
| dark-inclusion | 3050,1850,384,384 | Extended bright artifacts versus nearby genuine structure? |

These are scene locations, not universal output coordinates. Strehl's native
crop adds (56,38) to recover its reference-active coordinates. Helicon/fork may
use another alignment reference, scale and crop. Establish and retain a
coordinate receipt from fixed surrounding structural landmarks before detail
judgement. Show unresampled native crops centred on the same scene location;
report any scale mismatch. A geometrically registered overview may aid
navigation but is not evidence of native resolution. Do not reuse identical
pixel coordinates or a guessed translation when the landmarks disagree.

Judge B, C, current Strehl and the existing fork separately. State mixed
outcomes per region; a smooth background does not excuse erased features, and
stronger gradients do not establish detail. Use the retained focused-source
views to distinguish real structures from spread artifacts, with their own
coordinate provenance. No photographic ground-truth error or new aggregate
score is introduced. A useful outcome is a concrete visible failure that a
subsequent Strehl intervention must improve, including whichever comparator
handles it better. It is not a universal product ranking.

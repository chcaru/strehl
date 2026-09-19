# September 19 quality work

The complete 299-frame chip now retains a **modest visible local improvement**
from measured source-coordinate correction. Both reviewers identify cleaner
existing rail cores and crossings. The correction reaches the actual RAW
consumer with full context and seven bands; it is no longer only an eight-frame
cropped experiment. Strong chromatic stipple remains. See
`../full-context-placement/results.md` and its native comparison.

**The first new-scene transfer is photographically null.** On star sand, fitting
the fixed porous-grain region reduces held-out guide error in every one of eight
neighbouring frames, but both reviewers cannot identify a clearer pore, ridge
or retained feature in the full 259-frame output. No obvious seam or additional
stipple appears in the frozen views. A lower alignment residual is therefore
not accepted as a photographic benefit.

## New captures actually used

`new-captures-1/report.md` records the two new stacks: 259 star-sand RAWs and
70 crystallized-vitamin-C RAWs. Both were inventoried and six embedded previews
were viewed; only star sand was RAW-decoded/rendered. Selected metadata records
ISO 100, 1 second, f/5.6, 200 mm, manual 3000 K WB and stabilization off.
The metadata inspected does not independently establish electronic shutter.
Before/after file listings include hidden/system entries and are identical.
This is not a full-file content-hash audit.

Star-sand baseline alignment/render: 61.765 / 80.531 wall seconds using the
retained accelerated binary. The subsequent controlled full-context pair uses
one fresh binary and pinned identical tone: baseline 88.750 seconds, candidate
88.454 seconds. These single observations do not establish comparative speed.

The selected porous-grain ROI is fixed in `star-inspection-1/receipt.json`.
Nine original u16 patches (ordinals 125–133, reference 129) use exact global-map
bits and full-sensor coordinates. The reference patch matches a second decoder
at every sensel. The unchanged green-only registrar uses disjoint fit/validation
areas; all eight nonreference fits converge, avoid the ±4-pixel bound, and have
held-out error ratios 0.870–0.946. Nuisance intensity fits are not applied to RAW
values. These ratios can be fooled by blur/photometry and are not quality scores.

## Controlled full-star output

`star-full-context-placement` retains configuration, provenance, full baseline
and candidate TIFFs, exact commands, process bounds and native crops. The
source support is [594,1424,392,392] in the active native sensor; its full-weight
328×328 core is [472,1352,328,328] in the cropped output. Only the nine configured
frames participate in the local intervention; reference 129 is exactly zero.
All 259 frames contribute to both complete renders. The image observer is off.

The registered comparison changes 247,420 output pixels; the largest change in
the frozen core is 1028/65535. The far control has 171 changed pixels, each by
at most one 16-bit output level. These counts establish a live intervention,
not better detail. Both independent and root native inspection are null for
an identifiable feature benefit. See the photographic review in
`star-full-context-placement/comparison-1`.

Commands run with installed Python 3.12 `-I -B` from the repository root:

```
python -I -B experiments/quality-september19/star-baseline.py
python -I -B experiments/quality-september19/star-inspection-1/inspect-star.py
python -I -B experiments/quality-september19/star-local-green-translation.py
python -I -B -X faulthandler experiments/quality-september19/star-porous-translation-run.py
python -I -B experiments/quality-september19/star-full-context-placement.py configure
python -I -B experiments/quality-september19/star-full-context-placement.py baseline --build experiments/full-context-placement/build-3
python -I -B experiments/quality-september19/star-full-context-placement.py candidate --build experiments/full-context-placement/build-3
python -I -B experiments/quality-september19/star-full-context-compare.py
```

Exact expanded invocations, executables, source hashes and child-process
accounting accompany each run. Original captures remain read only.

## Decision

Keep the supported chip correction as an experimental capability; do not
promote general automatic local refinement from these two photographs. Defer
the proposed multi-region extension: a second-scene visible gain is absent.
The matched comparison now resolves an important confound in that null result:
the corrected frame neighbourhood is not visibly detail-bearing for this ROI.
Frames 125, 129 and 133 are all softer than the merged photograph, with 125 the
least diffuse of those three. Neither reviewer identifies a source feature
missing from the merge. This cannot establish a capture limit or refute local
correction at the genuinely focused frames. A bounded locator across the stack
must nominate focused originals for native review before any further transfer
render. The metric nominates frames only; it is not a quality verdict.

The existing observer captures unwarped source, gathered and merged values with
the same development. Its complete output is byte-identical to the saved
baseline: all 90,370,560 RGB16 samples match, as does TIFF SHA256
`5fc6c3ab8e2bcb64ee9d1383586f0c3763d6dbc709968a218bf36b9d654420ae`.
All three merged patch interiors equal the corresponding complete-output slice.
An intentionally wrong +2-pixel location differs. Evidence and commands are in
`star-matched-source-1`, produced by `star-matched-source-run.py`.

SOTA image quality, competitive quality ranking, whole-image improvement and
per-pixel calibrated noise after local refinement remain unestablished.

## Focused-window repeat and final decision

A single bounded pass over all 259 originals nominated local anchor 120 and
retained original-u16 frames 116–124. The unchanged locator's flat/noise/blur
controls run first and explicitly demonstrate that noise can win its score.
Both reviewers then inspected five native product-developed nominees and
confirmed that frames 116–120 carry pore detail missing from the earlier
125–133 neighbourhood. Different parts of the sloping surface favour different
frames; 120 is a defensible local anchor, not a universal sharpest frame.

The small ordered-MHC adapter reproduces all three existing actual-star CFA to
camera-RGB fixtures bit for bit before use. The held product developer also
reproduces its baseline TIFF exactly. The nominated anchor's second RAW decode
has zero differing sensels. The bounded scan costs 133.438 wall / 133.141 CPU
seconds and peaks at 182,222,848 committed bytes. These are operational costs.
See `star-focus-locator-1/report.md` and its reproducible helper.

`star-focused-fit.py` reuses the unchanged green registrar and its limits.
Original-map bits are checked against every retained float transform. The
local anchor's guide is sampled in the original global-reference-129 grid;
there is no reanchoring of the image or composition of pairwise corrections.
An independent synthetic test uses a nonidentity anchor and odd patch origins.
Known source shifts recover within 0.000134 native pixels, with wrong-sign,
doubled-displacement and wrong-anchor placebos rejected. The wrong-anchor
placebo can still improve its own residual, so residual reduction alone cannot
validate these coordinates. Map binding and anchor sampling are essential.

All eight actual nonreference fits converge off bounds, with held-out error
ratios 0.832–0.927 and shifts under 0.5 native pixels in length. Intensity
nuisance fits are not applied. The new full-stack candidate
uses all 259 originals and the held baseline executable/development, requiring
no production rebuild. Its single operational render time is 81.156 seconds.

**MEASURED BY NATIVE INSPECTION: the focused-window repeat is also null for an
identifiable photographic gain.** Root and the independent reviewer inspect
the same core, four transitions and distant control. No newly separated pore,
restored rim or clearer ridge can be identified; no obvious new seam or clear
regression appears. Changed coloured bright points are not evidence of restored
detail. The candidate changes all core pixels, so an inert intervention is
excluded; numerical difference still is not image quality. The complete TIFF
and native views remain in `star-focused-render-1` and `star-focused-comparison-1`.

This closes this specific bounded local-translation intervention for this star
ROI after testing a genuinely detail-bearing neighbourhood. Keep the modest
full-context chip gain and the tested optional consumer. Defer the four-region
extension and automatic promotion; do not spend another search-bound, focus
window or taper sweep on this result. Broader alignment methods are not refuted.
Competitive quality and the persistent colour artifacts remain unresolved.

Additional commands actually run:

```
python -I -B experiments/quality-september19/star-matched-source-run.py
python -I -B experiments/quality-september19/star-focus-locator.py
python -I -B experiments/quality-september19/star-focused-fit-review-1/controls.py
python -I -B experiments/quality-september19/star-focused-fit.py --samples experiments/quality-september19/star-focus-locator-1 --anchor 120 --out experiments/quality-september19/star-focused-fit-1
python -I -B experiments/quality-september19/star-focused-replay.py experiments/quality-september19/star-focused-fit-1/placement.json --out experiments/quality-september19/star-focused-render-1
python -I -B experiments/quality-september19/star-full-context-compare.py --candidate experiments/quality-september19/star-focused-render-1/output/replay.tiff --out experiments/quality-september19/star-focused-comparison-1
```

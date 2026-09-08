# Next registration diagnostic: fixed coarse representation

ARGUED decision, not an execution release. Run one fixed factor-8 representation
experiment against the cached 23 native outcomes, beginning with a powered coarse
positive. No native-pair rerun, graph solve or blur-equalisation sweep. Alternatives
below are conditional. This memo used saved records, owned source, the decision
record and primary publications; no image, RAW or numerical helper was executed.

## What the existing evidence distinguishes

The [independent actual audit](C:/dev/blog/death-of-software/projects/strehl/experiments/m193c-output-grid/independent-direct-pair-1-read.md)
establishes 23 completed refusals: 15 pairs have too few mutual landmarks and
eight have no majority consensus. All nine feature extractions and seven controls
passed. Original 0 retained 503 features; the other eight each hit 1,024. There
are zero accepted edges. This is failure of this registration instrument on these
inputs, not proof that the images lack shared geometry. The historical ordered
65-to-104 call still has only 22 mutual landmarks.

The [owned reference pipeline](C:/dev/blog/death-of-software/projects/strehl/experiments/M193-cover-overlap/reference.py)
projects RGB numerically to luminance, stretches each image between its own 1st
and 99th percentiles, requests 2,048 SIFT candidates and retains the strongest
1,024. Mutual matching uses a squared-distance ratio of 0.64. Reaching the feature
cap does not establish useful spatial support.

Zeno's separate coordinate-only investigation reports repeated sites across the
alternating calibration/holdout split: nine near-identity matches on late pairs
occupy only two or three reference sites. Some identical source locations match
reference locations hundreds of pixels apart; a deterministic geometric map
cannot satisfy both within 2 pixels. Feature coverage also changes sharply
between upper and lower image regions. These observations motivate a distribution
test; they do not identify an optical cause. SIFT deliberately permits multiple
orientations at one location and scale, so descriptor multiplicity is not spatial
replication. That mechanism is plausible here, not proved by coordinates alone.
[Lowe's original paper](https://www.cs.ubc.ca/~lowe/papers/ijcv04.pdf)

The [decision record](C:/dev/blog/death-of-software/projects/strehl/docs/research/SYNTHESIS.md)
already rejects residual-as-truth and endpoint-as-per-frame placement. It also
withdraws the old causal defocus attribution confounded by a bilinear plant
(fact 174). [M78](C:/dev/blog/death-of-software/projects/strehl/docs/research/M78-blur-equalised-edges.md)
already tried Gaussian cross-blur: conservation improved from 3.260389 to
1.073795 while its best paired held-out error worsened from 7.241426 to 7.266073
plane pixels. Blur equalisation is therefore a previously failed prediction,
not the cheapest untested repair.

## 1. First experiment: exact rotation positive, then fixed factor-8 inputs

Keep the decoder, CameraLinear input, luminance rule, stretch, SIFT parameters,
candidate cap, descriptor matcher and fitting thresholds fixed. Change only a
registered 8-by-8 area average before the existing analysis projection/stretch:
7032 by 4688 becomes 879 by 586. Declare the averaging and rounding exactly;
do not silently substitute nearest-neighbour resize, display gamma or a tuned
blur width. OpenCV ranks retained SIFT features by local contrast; independent
scale-space research finds both blur assumptions and aliasing affect keypoint
stability. These support the hypothesis, not a prediction of success here.
[OpenCV SIFT](https://docs.opencv.org/4.13.0/d7/d60/classcv_1_1SIFT.html),
[Rey-Otero, Morel and Delbracio](https://arxiv.org/abs/1511.08478)

Coordinate units are load-bearing. Convert each coarse Q8 location before fitting
or scoring: `q_native = 8*q_small + 7*128`. The last term places it at the centre
of its native block. Keep the 2-pixel/1-pixel native bars: these are 0.25/0.125
coarse pixels. Keep 12 calibration plus 12 holdout matches and both majority
requirements. Raising tolerances in small-image pixels would change the question.

Use root/Zeno's proposed one exact nonidentity control: repeat each pixel of the
held 384-by-288 positive fixture into an 8-by-8 block, then rotate by 90 degrees
without interpolation. Native source-to-reference is
`(x_r,y_r)=(3071-y_s,x_s)`. Area8 recovers the original/rotated coarse fixtures.
Omitting both centre offsets changes translation from 3071 to 3064: a 7-native-
pixel error. A +2-native-pixel map destroyer is below one coarse pixel but must
fail the independent known-map corner oracle in native pixels. The registrar is
not called on this mutated map. Require the correct map to pass first; current
SIFT localisation at these tighter coarse tolerances is unmeasured. The positive
tests coarse matching and coordinate transport, not real defocus robustness.
Use bounded fixture lifetimes; do not add a large full-resolution SIFT replay.

If it passes, extract the nine coarse inputs once and repeat the exact 23 ordered
calls, retaining the historical 65-to-104 direction. Use cached native records.
Record locations, unique-site counts, mutual counts, native errors and refusals.
Do not change matching or its alternating split in this first arm: site counts
are descriptive, not independently held-out support. Coarse success implicates
representation/candidate selection, not defocus alone. Refusal does not prove
absent shared geometry. A returned transform is direct support, not placement
accuracy; spatial qualification remains separate.

## 2. Conditional: spatially balanced candidates and site-separated holdout

If the positive works but real matches remain sparse, duplicated or confined,
test one fixed alternative selection on the same bounded SIFT candidate pool:
4-by-4 cells, at most 64 strongest candidates per cell, no borrowing or padding.
Keep the overall 1,024 ceiling and report empty cells. This isolates the global
top-response selection from increasing feature count or changing descriptors.

Group repeated locations before assigning calibration/holdout and keep each group
wholly on one side; additionally use fixed spatially separated holdout regions.
Declare the grouping distance prospectively. A duplicate-orientation fixture must
not manufacture independent support, and a compact cluster must not qualify as
distributed coverage. This is an additional diagnostic qualification, not a
retroactive rewrite of the old 24-descriptor threshold. Native geometric bars
remain fixed. More matches or low training residual alone cannot pass it.

## 3. Fallback: a few landmark-free local translation probes

If descriptor selection remains ambiguous, use fixed disjoint tiles from two
prospectively chosen real pairs with explicitly windowed phase
correlation. Commission known nonwrapped shifts first, including a symmetric-blur
companion; flat and mismatched-tile negatives must refuse. Keep any calibration
tiles separate from evaluation tiles. This asks whether local translation support
survives outside SIFT, not whether a global registration graph can be solved.

OpenCV phase correlation estimates translation; its response measures peak
concentration, not geometric accuracy. Whole-image rotation/scale and spatially
varying defocus violate the simple translation/convolution setting. Published
blur-invariant Fourier registration assumes centrally symmetric blur; that
assumption is unqualified for this stack. A positive tile result can challenge
the descriptor explanation; failure cannot prove absent scene correspondence.
[OpenCV phase correlation](https://docs.opencv.org/4.13.0/d7/df3/group__imgproc__motion.html),
[Ojansivu's institutional thesis](https://oulurepo.oulu.fi/handle/10024/35209)

Freeze inputs/controls and remaining budget before release. Retain prior costs
and refusals; write no TIFFs/snapshots and stop on a failed positive. No quality GO
follows. Papers do not license copied code; existing OpenCV 4.13 is Apache-2.0.
No excluded GPL/LGPL source was consulted.
[OpenCV licence](https://opencv.org/license/)

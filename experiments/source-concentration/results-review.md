# Independent decision on the radial control

**Reject this fixed concentration rule at its preregistered screen. The radial
failure is a genuine missed-positive limitation, not a harness error.** No real
TIFF scan is admitted, and no threshold or fixture adjustment is justified by
this result. It does not show an incorrect accepted source assignment: the
rule explicitly refuses a genuine focused feature that the frozen control
required it to identify.

VERIFIED from `controls-1/output/controls.json`: groups1–6 and8 passed, with no
harness exceptions. Group7 failed in both source orders. There is exactly one
radial seed, at(145,145), correctly associated with the planted centre(144,144).
Every frame is measured with finite nonsingular covariance and no support,
centroid, competing-identity or display-ceiling refusal. The eligible interval
is13–27. Thus this is neither a missing-feature fixture nor a boundary/clipping
failure.

MEASURED values at the relevant original source indices:

| Index | Eligible | Contrast peak | Component mass | Radius |
| --- | --- | ---: | ---: | ---: |
|15|yes|0.159793|11.387392|3.862717|
|17|yes|0.192869|11.301928|3.802673|
|20, true focus|yes|0.258506|11.558767|3.871309|
|23|yes|0.192869|11.301928|3.802673|
|25|yes|0.159793|11.387392|3.862717|

The actual decision is `separated-tied-intervals`: equal minimum radii occur at
17 and23, rather than at true focus20. The reverse-order result reindexes these
same observations; it is a label-order control, not independent replication.
Changing tie handling alone cannot make this frozen rule pass. At true focus,
both required five-frame neighbours are eligible but have radius *below* the
focus radius, whereas the rule requires at least1.25 times it. At either measured
minimum, one five-frame neighbour is peak-ineligible. These statements follow
directly from the retained records and current decision code; no altered rule
was executed.

DERIVED fixture validity: `thin_light` and `radial_scene` construct a fixed
three-direction extended feature, at angles0,60 and120 degrees. Each direction
has intrinsic Gaussian axes8 and1; convolution with an isotropic Gaussian of
sigma`.7 + .19*abs(index-20)` produces axes`sqrt(64+sigma²)` and
`sqrt(1+sigma²)`. Amplitude is inversely proportional to their product, preserving
the analytic feature's integral. The same positive colour factors are used at
every index, with constant background and no clipping or noise. Minimum blur
is uniquely at20. This is genuine extended radial detail becoming sharper,
not a disappearing spot, brightness transfer, changing object, or a point
renamed radial.

For the complete continuous feature, equal angular weights give covariance
`(32.5 + sigma²) I`, which increases with blur. The implemented statistic instead
measures the source-pixel component of positive contrast above10% of that
frame's peak after fixed background filtering. Its selected pixels and their
weights change with blur: the component contains189 pixels at focus and221
at17/23. The resulting covariance radius need not preserve the full feature's
blur ordering, and here it does not. The data establish that failure of the
combined statistic. They do not independently isolate how much comes from
relative thresholding, Gaussian background subtraction or discrete sampling.
The radius is also largely set by the genuine extended structure; it is not
automatically a measure of the thin directions' focus.

The fixed discriminator works on the supplied compact-glint positive and
avoids the supplied null, identity and damage controls, but that is insufficient
under the explicit true-radial guard. Preserve this conservative rejection
without claiming a general inability to use source morphology, calibrated
noise behaviour, or image-quality improvement.

Executed command, by root:
`python -X faulthandler experiments/source-concentration/independent-controls.py --output experiments/source-concentration/controls-1/output`.
It exited1 as required by the failed gate. Result SHA256:
`67d886f988f3f12b4f8809b37bbef90c9bc6908dea17e84397284065dddf2143`.
The result binds unchanged helper, plan and implementation hashes. This review
used source inspection and retained results only; no rerun or new metric was
introduced.

Separate research-utility decision: the failed screen does not make an
unmodified, bounded, read-only scan intrinsically uninterpretable. If root
authorizes that distinct failure-characterization scope, it may establish
whether this selective rule makes any plausible real nominations or mostly
refuses, while preserving the failed gate and every seed/refusal. It does not
constitute screen admission, a validated focus estimator or permission to
change images. Export tone/clipping and component breakup remain confounders.
The current receipt stores only footprint bounding rectangles: these can reject
core/fan association but cannot prove that both points belong to one connected
component. Unfamiliar nominated frames need native-image and neighbour review
before even a descriptive correctness claim. No such scan is performed or
claimed in this review.

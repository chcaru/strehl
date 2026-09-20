# Independent attribution decision

**The remaining dark-fan signal is principally carried by retained coarse
baseline AC in this decomposition. The prescribed donor partly cancels it;
the clamp is not creating the mean residual at the frozen fan location.** This
justifies one distinct reconstruction-order counterfactual with the same
donors and native masks. It does not reverse the photographic rejection or
establish that a replacement operator will work.

## Accounting and neutrality

VERIFIED: `full-on-2/neutrality.json` binds exact RGB16 equality for baseline,
candidate and late outputs against both the same-build observer-off run and
the original `full-1` triplet. Same-build off/on TIFF hashes also match. The
observer therefore describes the photographs already reviewed, including the
wrong-donor control. The fresh three-control run passed; its separate-collapse,
signed-cancellation and false expanded-mask-product controls are retained in
`controls-3/process.log`.

MEASURED: the frozen analyzer independently passed all window identities.
Maximum mixed reconstruction error was0.0038681DN against the0.02DN limit;
maximum hull closure error was0.0001221DN against0.003DN. All36 shared baseline,
terminal-base and retained-AC artifacts are byte-identical between candidate
and late arms. I inspected both windows at both fixed signed map scales and
read the raw means as well as the local-reference contrasts and individual
bands. No location, scale, donor or mask was changed.

Executed analysis command:
`python -X faulthandler experiments/donor-consistency/attribution-analysis.py --input experiments/donor-consistency/full-on-2/attribution --output experiments/donor-consistency/attribution-analysis-1`.
The output manifest binds the frozen helper and plan, observer receipt and all
derived artifacts. `accounting.json` SHA256:
`a86f8adce41f0c4aefdf0ad9c96be1a527ecaa2c55aee5c4a523de16ae9d4e84`.

## What the signed terms show

At the frozen dark fan `(3102,2203)`, raw3x3-quad means are:

| Component, source DN | R | G1 | G2 | B |
| --- | ---: | ---: | ---: | ---: |
| Retained baseline AC |1082.42|1890.19|1850.55|856.40|
| Candidate donor AC |-309.38|-307.49|-468.50|-289.09|
| Late donor AC |1215.88|1531.26|1661.68|822.93|
| Shared terminal base |2081.49|4053.95|4054.88|1964.83|
| Candidate hull correction |0|0|0|0|
| Candidate post-hull |2854.53|5636.65|5436.92|2532.14|
| Baseline post-hull |3010.86|5634.65|5631.75|2745.73|

The retained level0 and1 contributions are exactly zero at this mean. The
positive remainder is concentrated in levels4–6: for G1 these contribute
599.21,654.29 and540.45DN respectively; level3 adds99.32 and level2 is-3.08.
Thus the residual is not explained by an unexercised native mask or by the
focused donor adding a net positive fan at this location. Donor33 supplies a
negative contribution, especially at level2, but its cancellation does not
remove the retained coarse field. Late69 supplies a large positive contribution
instead. The common-scale maps show the same distinction across the nearby
feature, rather than only in one averaged value.

The conclusion survives the independently chosen local reference: dark-fan
retained contrast is[1200.25,2013.22,2021.21,918.34]DN and donor contrast is
[-322.61,-326.86,-488.34,-298.15]DN. The base contributes only
[42.06,68.62,68.37,42.38]DN of this local contrast. Its large absolute DC level
must not be mistaken for evidence that the terminal base creates this tail.
Also, the negative dark-fan hull terms in the contrast table come from the
reference's positive clamp correction: the fan's own correction has zero mean.
This is precisely why raw values were retained. These statements concern the
fixed neighbourhood, not the absence of clamp activity elsewhere in the window.

At the dark core, the focused donor likewise supplies negative AC against a
positive retained remainder. At the nearby donor25 structure, the candidate's
positive green donor contribution contrasts with the late donor's negative
contribution, consistent with the retained photographic detail witness. Neither
is an independently known desired-radiance measurement.

The facet provides an important limit on interpretation. Although the earlier
photographic review found narrower prominent extensions, its frozen fan's G1
post-hull mean rises from3460.22 to3705.01DN. Negative fine baseline AC has been
removed while positive coarse AC remains, and the candidate donor cancels only
part of it. A rule equating lower intensity at this one point with better
photographic quality would therefore misdescribe even the partial facet gain.
The signed maps also show donor contributions with both signs; they are not
images of an isolated source and cannot be read as source-ownership fractions.

## Next consumer question

ARGUED: test whether **reconstructing each prescribed donor's complete AC first,
then mixing those AC images at output quads using the same native masks and
shared terminal base**, eliminates this retained coarse contamination while
preserving the compact cores, nearby donor25 structure and transition quality.
This changes the order of spatial mixing and reconstruction, not the radius,
donor labels, band count or evidence thresholds. The new path must be separately
commissioned: all-ones must deliver coherent donor AC plus the baseline base,
off/zero must retain exact identity, all four planes must share membership, and
the same input hull and late control must remain visible.

The current observer demonstrates accounting for the retained signal, not a
proof that all retained contrast is unwanted. Fixed donors may still be locally
misregistered or contain unwanted structure, and a spatial AC transition may
introduce seams or noise costs. A new counterfactual must answer those concerns
in the same photographs. Automatic donor assignment remains premature; this
is a local, externally labelled reconstruction diagnostic, not a SOTA result.

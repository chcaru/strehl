# Independent signed reconstruction accounting

Fixed before observer output is inspected. This follows the photographic
rejection in `results-review.md`; it does not reopen the recipe or introduce a
quality score. Root executes the analyzer after the observer controls and full
off/on/retained-triplet pixel identity checks. No original RAW is read.

Command (new output directory required):

`python -X faulthandler experiments/donor-consistency/attribution-analysis.py --input <run>/attribution --output <new-analysis-directory>`

First bind the receipt and every little-endian f32 artifact by SHA256. Require
the declared four CFA planes `[R,G1,G2,B]`, exact frozen windows, all seven AC
levels, finite values and complete fields. Independently add the already
full-context-expanded fields in f64. Baseline AC plus terminal base must recover
baseline pre-hull, and retained AC plus donor AC plus base must recover each
arm's pre-hull, within the previously fixed 0.02 source-DN absolute tolerance.
Pre-hull plus signed hull correction must recover post-hull within 0.003 DN.
The receipt's full-domain error summaries are retained separately from these
independent window checks. Baseline fields, terminal base and retained AC must
be byte-identical between candidate and late arms. A missing band, altered
sign, wrong plane/shape or changed shared field can fail this accounting.

Use the frozen output-native points: facet core `(2624,2906)`, facet fan
`(2602,2945)`, dark core `(3080,2150)`, dark fan `(3102,2203)`, and nearby structure
`(3240,2070)`. Independently selected local level references are facet
`(2548,2920)` and dark `(3180,2220)`, chosen from the existing photographs before
attribution. They are neither calibrated flat areas nor noise estimates.
Map each point to its containing quad with integer floor division by two;
subtract the receipt's quad crop origin, then take a fixed 3x3-quad mean in
each CFA plane. This is not a native RGB pixel measurement. Retain raw signed
means, each band's contribution, their sums, and the same means at the local
reference. Report point-minus-reference using the same linear extraction.

For both fixed 192x192-quad windows, show baseline AC sum, retained AC sum,
candidate donor AC sum, late donor AC sum, candidate hull correction and late
hull correction. Use all four planes, nearest display and the same diverging
scales of plus/minus64 and plus/minus512 source DN. Do not independently stretch
panels, rectify signs, or treat colour-map brightness as photographic quality.
The numeric output preserves values outside those fixed display ranges. The
actual developed photographs remain the evidence of appearance.

Interpret signed contributions, including the shared terminal base and any
cancellation, before attributing a residual. Retained contrast with little donor
contrast supports retained-baseline accounting in this representation; donor
contrast leaves a source/support explanation live; a hull contribution identifies
an additional clamp effect. More than one may matter, and no forced winner is
required. Comparing raw means as well as local-reference differences guards
against a reference subtraction manufacturing an apparent owner. A fixed local
reference can still contain genuine scene structure; it is not independent
truth about the desired radiance.

Do not form ownership percentages from absolute component energies. Opposite
signed terms can cancel, and removing one term is not the same as reconstructing
a new physically valid image. In particular, use the observed expansion of
masked coefficients, never expanded-mask times expanded-image: those operators
do not commute. Band accounting before MHC, white balance and tone cannot by
itself quantify the displayed coloured tail, prove a physical point-spread
function, or show that a revised reconstruction will improve the photograph.
It can justify a narrowly specified next counterfactual, or leave the cause mixed.

The analyzer writes new JSON, Markdown and diagnostic maps only. It does not
modify observer fields, outputs, donors, masks or thresholds, and does not
render a new merged photograph.

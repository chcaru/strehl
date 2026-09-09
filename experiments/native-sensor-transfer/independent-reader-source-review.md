# Native sensor transfer: independent reader source review

SOURCE REVIEW IN PROGRESS, 2026-09-09. This is a review of concrete reader,
decoder, numerical and control code under held methodology
`a257cba972948564fd6041dc535d5e34f2ea6679`. **No source hold or execution
clearance is issued by this initial note.** The author is correcting drafts;
exact final pins and disposition will be appended after rereading those changes.

I previously recommended the RAW priority and contributed Crop/protocol choices.
I did not author these four Python modules or their controls. I independently
read their concrete arithmetic and call sites against the held methodology and
owned native source. I did not import a candidate, allocate scientific arrays,
decode RAW, run controls, simulate, build or execute a product. The producer
integration at `c9f6bb1e` was root's separately recorded source action.

## Concrete corrections sent before data

Two integration mismatches would refuse an otherwise normal released run.
The adapter constructs its output root by joining CARGO_MANIFEST_DIR with
`../../experiments/native-sensor-transfer`, and serializes those unresolved
parent components into artifact references. The reader deliberately rejects
parent components. I requested canonicalizing that existing experiment root
before fresh output creation, retaining the reader's exact path policy.
Separately, the runner's inherited clean environment removes all four numerical
thread variables while the reader requires them to equal one. I requested
setting and retaining those four variables for controls/verify children.
Neither finding came from a failed data run.

The reader authenticates supplied references but also needs their exact roles:
frame JSON, original/prepared ROI, trace, collapsed payload and TIFF paths must
match the fixed invocation/frame/route names before reading. A copied file with
the same contents at another location cannot discharge the intended role.
The stage result path must be fixed, rather than allowing the supplied result's
parent to define the stage output. Historical source-map comparison must also
match the runner's declared interface: authenticate each historical release and
runner, and preserve equality of the actual compiled closure. An unrelated
checker-source change is not evidence that a previously built executable has
changed; neither may it relax the compiled source association.

Several scientific interpretation/output gaps were present in the drafts:

- The required `smooth5((mean_t L_k)^2)` scene-energy diagnostic was absent.
  Retain it separately, with finite-repeat contamination; do not subtract it
  into a quality result.
- Placed-route green eligibility was reused as a block-level conditional label
  while all four prepared photosite ratios were printed against the original
  sensor predictor. Prepared R/B need explicit NOT_IDENTIFIED/nonphysical
  comparator scope. Green identity does not license those channels.
- Dark B is a signed PRECLAMP counterfactual. Eligibility of that predictor
  cannot label actual postclamp Q/B a valid physical normalization. Keep the
  signed comparison and the actual clamp-transfer ratio separate.
- Recomputed exponent/selected-beta products must remain DERIVED. In particular,
  a binary64 product of recorded beta and V is not a directly observed f32
  closure value. The actual f32 floor/weight relation is checked separately.
- The required 22 dark frame means were absent; the mean image's pooled summary
  is a different quantity. Retain ordered same-crop means without subtracting
  them or applying the paper illumination screen to dark.

Root independently found an unregistered normalized-WB refusal at 2^-20 and
commissioned descriptive independent WB instead. I found the same gate could
survive indirectly in saved output validation: the native writer supports
Frame::wb_gains=None and unity fallback, so an unconditional coefficient divide
is not the full source contract. Also, the decoder must enforce positivity and
equality on USED CFA white channels as held, without turning an unused fourth
metadata slot into a new scientific refusal. Original buffer/code/black/white
and consumed-green associations retain their registered authority.

The control review challenged actual wiring and retained evidence, not merely
formula agreement. Group18 needed every named branch, clamp side and operand
retained/asserted, plus the promised threshold-side metadata fault. Group19
called the correct external NIST predicate but discarded its expected/actual
quantiles and reached-fault values from the retained row. Group11 needed the
promised independently constructed scalar stencil operands at the corner and
(64,64). Group10's partition check needed fixed phase/support membership and
counts, rather than total area alone. Group07's alleged all-five substitution
was only a changed-reference comparison; it must exercise the fixed frame4
source/role predicate or carry a narrower source-only association claim.

The spatially constant group06 neighbour witness can establish covariance sign
and overlap population, but cannot reject a wrong same-sized neighbour address.
That limitation must be explicit unless a prospective within-scope control
amendment supplies address variation. No new real input, ROI, estimator,
parameter sweep or fitted calibration is requested by these findings.

## Choices supported by the source pass

The owned rawpy ROI copy occurs inside its context, at the fixed raw-buffer
address; the visible-image view is not substituted. Local CFA letters and
used-channel levels are checked separately from same-file row/whole-code hashes.
ISO/camera fields are native plus inherited capture authority; this decoder
does not independently establish them through rawpy.

The independent binary32 filter spells the native five serial multiply/add
taps, replicated boundaries, horizontal-then-vertical order and the two expand
phases. It filters individual spatial planes and retains the native
sqrt-then-square variance path. Exact bits apply to these associations. The
separate binary64 diagonal prediction coalesces original addresses and uses
the difference of two separable operators; it is not the producer's measured
white beta. Negative diagonal results are refused rather than clipped away.

Paper uses two disjoint pair differences and frame4 as the separate signal
witness; dark uses eleven pair differences. The all-T centered estimate stays
a sensitivity comparison. Green covariance identities are association checks,
not physical calibration. Cross-plane and neighbour alternatives use matching
overlap extents. Site count is never promoted to temporal degrees of freedom.

The implementation distinguishes threshold rejection from correctly rounded
p1/p2 underflow. Exact p1/p2 bits and the separately bounded log/exp branch
remain distinct. Quantiles use the held integer/half-integer recurrence,
external NIST cells for df4/11/21, and the analytic df2 reference; an inverse
check against the same CDF is only consistency. No unconditional Gaussian
coverage is claimed for quantized/clamped data or for smoothed energy.

Retaining detached full pair-Q and every pair-component map while publishing
means/all-T variance as complete-crop, sixteen-block and fixed-site summaries
is consistent with the sensitivity wording. It must be explicitly described;
the full original/native arrays remain pinned. This is a retention choice,
not permission to discard sites or choose favourable spatial subsets.

## Pending source hold and bounded review scope

The complete four-module reader and controls, final runner interface, source
associations, normal publication capacity and all requested corrections still
need one cohesive final read. Source flags must support the declared f32 order
before execution; an eventual mismatch cannot justify a wider tolerance.
I read only the runner portions needed for the interface; root separately owns
its full review and process/resource release. No additional process framework
or runtime inventory was commissioned here.

This source-review stage is allocated 64 MiB source/report reads, 4 MiB new
retention, 60 CPU seconds and 120 active process-wall seconds. Read operations
were not measured as one whole process family, so exact cumulative CPU is
unknown. The finite lane stays charged. Review publication and source metadata
reads are not candidate controls or numerical evidence. All findings above are
pre-data source findings; none is an observed sensor, merge-quality or SOTA
result.

## Cohesive source disposition, 2026-09-09

**ACCEPTABLE FOR ROOT'S SEPARATE RELEASE, subject to the exact source and
attempt associations below.** This supersedes the initial pending disposition;
the initial text is preserved. It is not an executed control or scientific
result. All numerical/module corrections were read at these actual byte pins:

| File | Bytes | SHA256 |
| --- | ---: | --- |
| independent-read.py | 81461 | 9975b8abc8a7f8212d7a1a54f03a08d7008903ff1e3b1e978bdc8c69704744b6 |
| independent-numerics.py | 24837 | 27e2b9a5141929c4a5fcd20ec4a3592de5efd742d6d5be512c8ddbb71168dc87 |
| independent-decode.py | 10002 | 62d7e938e65973937002bac23edc70fc13b5ae9cbcf7d1867d5b1edd859e44dc |
| independent-controls.py | 27869 | 4643d51c1b893f00800711e3705b2af8d4436062dea6d86ea7bf7c7c0dc85b5e |
| independent-implementation-notes.md | 10499 | b56b32628bd9172fbf8df83c27f6b0d85add33631513f733f45bba0e5f6f07bf |

The four-module sources agree on the fixed twenty groups, 175 private variants,
and pending groups17/18. Saved verification authenticates those rows instead of
rerunning them, then adds sixteen observer and six weight/threshold variants:
197 in total, with final group17/group18 lengths17/19. The actual-mode paths
are source-bound fixed loops; these counts have not been observed at runtime.
The on/off/placebo/feature-off witness remains paper-five and dark-first-two,
for both routes and both output formats. It does not establish neutrality on
the other twenty dark frames or on arbitrary stacks.

The requested corrections are present. Actual E/V/W and coefficients remain
separate from DERIVED scalar context. Scene energy, ordered dark frame means,
used-channel levels, descriptive WB and the writer's optional-WB branch are
retained. Physical interpretation is separately scoped for prepared R/B and
signed-versus-clamped dark comparisons. An ineligible paper or transformed
green comparison remains visible with NOT_IDENTIFIED premises; it cannot turn
into a calibration pass. The frame4 role fault reaches the prediction's own
role predicate. Phase counts/boundary membership, explicit scalar stencil
terms, seven branch/literal witnesses, threshold-side faults and external
quantile/fault values are retained. Group06 now explicitly admits its constant
field cannot reject a same-shaped neighbour-address error. This is the honest
power limit of that registered witness, not independent spatial-address proof.

All saved native frame/ROI/trace/output roles are fixed before content use.
The reader binds actual Cargo log messages to the fresh exact bin, main.rs,
manifest, feature vector and target directory; copied executable bytes and
actual compiled closure remain associated. Historical build maps retain their
own runner/release identity, while current nonbuild maps must agree. The reader
does not imply hermetic compiler, dependency/DLL or runtime-source verification.
Root separately reviewed runner33684 bytes,
e000e5dfa15b54b7f88040c9f5d7dea3eaa92b62e120be5dd8b73d4d2cdfacd4,
including compiler configuration/override handling and numerical thread settings.
My review of that runner is limited to the shared interface. The canonical-root
producer correction was accepted separately; producer-source-review.md remains
unchanged at16581 bytes/3ca62160d06edde1cec8a7a1dfe03fd0b7151dfce3d5cbb7b0dc64373423cda3.

### Finite normal publication check

The independently re-counted detached arrays total55,697,408 bytes when all
predictions are available. The actual fixed per-role JSON/stdout caps bring
the logical write ceiling to67,100,672 bytes, 8,192 below64MiB. These are source
shape/cap deductions; no arrays or reports from the future experiment were read.

One independently written standard-library literal metadata serialization was
run, with no candidate imports/functions, numerical arrays or data. It used
all6,336 dark block summaries,704 per-frame comparator rows,512-backslash
FileRefs, wide finite values and a64KiB reservation for remaining fixed fields.
It yielded paper block661,160 bytes and dark block1,894,992 bytes against the
1,966,080-byte slot. The latter margin is71,088 bytes. Primitive serialized
widths were110 bytes per summary,124 per block summary,128 per ratio and1,191
per detached array reference. The64KiB remainder covers nuisance rows, scalar
interval/reference-uncertainty rows, current-luma comparisons, model/reference
metadata and framing. This is a conservative normal fixed-schema construction,
not an arbitrary-input maximum or a measured result from the reader.

The smaller return shapes were source-read: frame checks contain58 full on rows
(1,856 band/stratum rows),28 off/placebo rows and14 feature-off rows. Their map
records are limited to288 across the on/placebo routes, and only the fixed
source path and resolved profile representation are copied. No trace arrays
are embedded. Independent decode metadata contains27 single256-row hash vectors
(about464KiB before its small per-frame metadata), rather than duplicate vectors.
The eighteen output rows retain refs/settings/container extents, not pixels.
The final128KiB record contains compact groups, refs, stage/runtime/accounting
summaries and no source map or per-frame arrays. These shapes support the
declared2MiB/1MiB/128KiB/128KiB normal slots; each actual encoding remains the
admission check. This is not a claim that any possible metadata/error string
fits a successful publication.

Publication phase now starts before failed-prefix publication, so a reserved
tail is usable after the work-phase reserve triggers. Each write and final
stdout is charged before publication; hard time/read/write caps still apply.
An OS/write failure, exhausted hard cap or failing prefix publication can
prevent terminal JSON. Retained prefix files plus actual raw process exit/log
then remain authoritative. Process-local samples are explicitly prepublication;
they are not complete process-family CPU totals. No wall-to-CPU conversion or
refund is claimed. The allocated source-review lane remains charged; only the
literal metadata command above was separately observed to exit0 (tool wall0.4s,
not certified complete CPU).

Root has since reported the first build-on refusal and commissioned an
attempt-only recovery. That outcome is outside this reader's numerical review.
The main pin above still names build-on attempt1. A final release must use the
separately reviewed attempt2 association delta and preserve the failed attempt;
this note does not authorize relabelling attempt1 as complete. No numerical,
decoder, control population, tolerance or retention change is needed for that
operational association. Its exact amended pin will be appended after the
source-only reversal check.

### Accepted attempt association delta

The final reader is81550 bytes, SHA256
945f1fc58c275a5b4af74335d66ee24a8f675d39ea7b566a6744ca58395eb809.
I read the complete four-expression diff and independently reversed those
substitutions in memory: byte equality with the preserved81461-byte draft was
exact. The four changes bind the build-on result directory, Cargo target argv,
copied executable and original executable containment to attempt2; build-off
stays attempt1. No numerical/control/decoder/retention logic changes.
Implementation notes now11809 bytes,
9080c29213ae5e1501995ce4ce38c0d4abb71d360be6a590eb9b508a89ab11bb,
with the earlier10499-byte note followed by the attempt amendment.

This delta is ACCEPTABLE for the separately released attempt2 bundle. Root's
runner recovery and actual failed-build diagnosis are separate reviews; they
are not independently established by this source-only reader check. The
three other module pins in the table remain final. An own-source readback
also verified the original8574-byte review prefix remained byte-identical.
No candidate, decoder, controls or product execution occurred in this lane.

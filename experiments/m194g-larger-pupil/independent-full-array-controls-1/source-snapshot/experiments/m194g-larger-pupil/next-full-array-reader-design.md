# Prospective complete expected-array reader

2026-09-07. Root design for the next consumer, before any full M194g array run.
This is implementation preparation, not an execution release or a new accuracy
bar. The component reader must first admit both complete fresh component
batches, including the normalized-reference amendment and current-source
private controls. No successful subset supplies that authority.

## Fixed population and comparison

Consume three complete author results (`primary`, `angle-refined`,
`cell-refined`) and two complete independent reference results (`primary`,
`refined`). Each contains original indices0–4 exactly once and in the declared
order, with the five registered focus values. Re-derive their exact scene,
frame, dimensions320×240 and identity placement from the externally pinned
fixture, not a producer's proposed comparison inputs. The reference index is2.
This is25 complete scalar arrays, including15 author arrays; there is no
row/case/image exclusion, replacement or selected successful arm.

For every original frame, compare each author arm against the refined
reference, separately over the whole frame and the fixed native-centre band
`abs(x - 0.15*y - 142) <= 8`. Require maximum absolute discrepancy<=0.004e
and RMS<=0.0008e in each comparison. The band comes from the fixed scene
equation; it is not selected from the errors or producer branch maps. Assert
that both the band and its complement are nonempty. These are30 per-frame
author/reference comparisons, not one pooled number that can dilute a failure.

Also require, on every whole frame, author primary versus angle-refined and
versus cell-refined maximum<=0.001e, and reference primary versus refined
maximum<=0.0005e. These are10 author and5 reference refinement comparisons.
Report both signed extremes and the location of each absolute maximum, with
native coordinates and original frame index. A finite pointwise numerical
comparison tests agreement on this population; shared model errors or a
different untested scene can defeat it. It does not establish physical optics,
real-capture truth, preserved detail or product quality.

Also report per-frame counts and descriptive discrepancies separately for
the author's actual fallback-selected population and the broader independent
reference-boundary population, as already required by the preregistration.
Retain their distinct mask definitions and provenance. These summaries do not
add acceptance bars, select the whole/band population or require the two
branch maps to agree; an empty descriptive subset is reported as empty.

## Actual bytes, complete semantics and authority

Bind the actual externally pinned component authority, render execution
releases, source closures, terminal results, frame inputs, array refs and
runtime/command receipts. Reopen each array through a bounded NPY reader,
validating its header before allocation, exact little-endian dtype, shape,
payload extent, finite values and SHA256. Reject extra bytes, duplicated
identities/paths, missing frames, boolean integer aliases, unknown schema
fields, changed phases/placements and false completed-cell counts even when
the outer manifest is coherently rehashed. The exact interpreter arguments
and unchanged source/input bytes must match their prospective releases.

Author frame packages retain scalar, branch, sorted numerical indices and
four diagnostic columns. Reuse the independently commissioned semantic
checks where their contract applies; do not invoke the author's frame reader.
Validate all76800 sites, complete numerical coverage and per-frame work
budgets. Full-frame work is not the component-batch budget: keep the existing
author per-frame16000000-point/2400000000-node and full-arm1800CPU/3600wall
limits. Do not reuse the component author's cumulative-work validator without
its explicit full-arm mode. Reference full-arm counts
must remain cumulative across all five frames. A producer's wider analytic
selector need not agree with the author's branch map; compare every scalar.

Read arrays a bounded number at a time, with an explicit32MiB live named-array
ceiling and120CPU/240wall-second reader allowance through final persistence.
These are proposed engineering caps, not measured throughput or RSS. Keep the
first refusal and do not increase a cap from its observed runtime. Preserve
original and secondary finalization errors distinctly.

The successful output must supply a versioned, closed authority record for the
noise emitter containing the admitted primary scalar refs, original indices,
focus values, fixture identity and complete comparison provenance. Choose and
freeze its exact field schema and path-root convention before implementing the
emitter consumer. No noise generation or production output belongs to this
reader. Failed/incomplete comparisons must not emit a success authority.

## Powered consumer controls, before full-array admission

Use the actual comparison and file-reading functions on clearly labeled
private fixtures. Keep max and RMS failures separate: one changed sample must
fail the maximum; distributed changes below the maximum must fail RMS; a
failure in one arm or frame must survive aggregation with unchanged companions.
Exercise both a band and complement change, exact-limit acceptance, just-over
refusal, missing/duplicate frame substitution, nonfinite values, rehashed
metadata/NPY corruption and a changed diagnostic with unchanged scalar. Give
each a reopened unmodified/restored companion. Private array construction is
not optical generation and confers no full-image authority.

The complete real results must then pass these independently authored
consumers without source edits, row substitutions or threshold changes. The
independent verifier must re-choose at least the private fixture aspect ratio,
failure location and metadata mutation rather than merely repeat the
producer's own examples. Freeze final sources and exact commands before the
first control/full-reader execution, and retain the deciding records.

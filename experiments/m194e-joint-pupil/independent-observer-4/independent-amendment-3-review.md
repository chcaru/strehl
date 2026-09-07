# Independent review: global cell-error allocation

2026-09-07. Prospective review of `numerical-amendment-3.md`, author SHA
`e1e79088ff4c147be0b6a96410e4cc03913ad954da63c59e567f06648009fe43`.
No candidate allocation implementation or admitted full run exists. The
current model, scene, maps/rules/orders, maximum depths, independent references
and whole-cell/full-image limits remain fixed.

## Evidence and the actual consumer

The separate `independent-allocation-audit.md` derives why proportional leaf
budgets imply, but are not implied by, the aggregate consumer limits.
`independent-allocation-read.py` independently reconstructs the complete
508-node diagnostic tree, child-midpoint geometry, prefix-free complete
frontiers, leafwise absolute differences and separate pupil sums. Result SHA
`d780d645dc3ed313c98e60fe058c5812af091e61e3f32017261aefbeff86e8a0`
is `DIAGNOSTIC_VERIFIED_NOT_ADMITTED`.

The original34-leaf terminal partition retains its depth6 local failure yet
has aggregate8.856774755455326e-5 and high-pupil1.4623755733033123e-6,
both below unchanged whole-cell limits. Its high value differs from the frozen
whole-cell reference by9.09e-12 electrons. Reconstructing the diagnostic global
priority sequence yields18 leaves after14 splits, aggregate.0006571524094194218
and high-pupil1.4623755233115732e-6. Initial roots instead fail at.02088286.
This establishes an avoidable proportional-allocation refusal on this cell;
it does not admit that diagnostic or predict every other cell.

## Exact rule and necessary invariants

The proposed consumer is appropriate: E=sum(abs(high-low)+pl+ph), with the
separate P=sum(ph), using canonical-path math.fsum. Require E≤the existing
cell tolerance and P≤the existing pupil tolerance. Keep E+P as the reported
final indicator. Neither a signed global low/high difference nor dropping a
repeated high-pupil term is the same contract. All components/totals must be
finite, and error components nonnegative.

Evaluate all initial roots and both children of a selected leaf before the
next acceptance check. The active set is a complete prefix-free partition,
with no parent counted with descendants and no capped leaf omitted. The
integer binary-coverage test and area check are complementary: neither alone
proves spatial coverage. Retain the original geometric bisection and verify
that the two children are its actual partition; a duplicated half-triangle
can have correct total area and valid path labels while leaving a hole.

Choose the largest cell indicator among eligible leaves only, with immutable
root/binary-path ties. A capped large leaf can remain while another eligible
leaf is usefully refined. Refuse only when the aggregate remains unacceptable
and no permitted refinement exists, or an existing work/finite/geometry limit
fails. No monotonic decrease of the indicator is guaranteed when a parent is
replaced by children; an initially increased sum is not itself a failure.
Finiteness follows from the depth/resource caps, not a presumed decrease.

Use canonical recomputation, not incremental subtract/add sums. Stable-path
storage permutations must yield the same choices, totals and result. The root
indices remain those of the original deterministic cell triangulation; this
does not propose reordering that geometry. Eight initial roots and depth6 give
at most512 live leaves; 24,576 bytes describes their coordinate arrays alone,
not Python overhead or measured RSS. All retained arrays still need the actual
monitor and unchanged resource guards.

## Independently chosen powered component controls

These are synthetic quadrature-record controls of the actual aggregate/queue
helpers, not optical scenes or new truth data. Use the unchanged primary
tolerances. Valid root/child geometry and paths accompany each record, and
each rejection has an unchanged valid companion. Finite low/high values can
be offset by10000 so the records do not rely on negative radiance.

- Opposite signed deltas+0.0006 and-0.0006 produce zero signed total but
  E=.0012 and must not pass. Halving both deltas gives E=.0006 and must pass.
- A leaf of area1/16 with error.0001 and the complementary area15/16 with
  error.00005 is globally valid despite the first exceeding its proportional
  share. A local-only refusal on that active frontier is a failing control.
- D=.0004,pl=.0002,ph=.0002 yields E=.0008: omitting either pupil term would
  falsely pass. Separately D=0,pl=0,ph=.0003 passes the cell bar but fails the
  pupil bar; it must refine or refuse. The valid companion ph=.0002 passes.
- A depth6 leaf with error.0007 must remain in the total while an eligible
  .0001 leaf can split into two .00001 leaves. The new sum.00072 is valid.
  Refusing immediately on the capped leaf is wrong. If all leaves are capped
  and E remains.0008, refusal is required.
- An eligible .001 parent may produce two .0007 children, increasing the
  aggregate. Refining one child into two .00001 leaves then permits.00072.
  Do not assume each individual split improves the estimator.
- Equal-priority leaves with distinct fixed paths must select the canonical
  path. Shuffle storage order while preserving paths and require identical
  split traces and fsum results. This tests policy independently of the
  author's actual failed-cell sequence.

Inject negative/NaN/infinite error terms; omitted roots or children; duplicate
paths; a parent retained with descendants; biased area; duplicated spatial
half-triangles with nominally valid paths; and work/depth exhaustion. Require
the real helper's relevant refusal, not a stand-alone test of a copied guard.
Changes to initial geometry/data or expected results cannot be used to rescue
an unexpectedly unpowered case. Exact callback/API names may be bound once
the author's reviewed implementation interface is released.

## Actual-model, observer and historical controls

The actual new allocator must return both previously refused cells within
the original indicator and independent whole-cell limits. Re-run the same31
analytic and336 textured API cases and the independently powered19×11
observer/traversal population. Require both scalar and indicator byte identity
for off/count/placebo and the tracing observer.

The new six allocation counters describe accepted cells only. Before any
completion and after `new_frame`, all are zero. Count mode must record actual
terminal leaves/depth extrema and any local proportional over-allocation;
off/placebo retain zero allocation fields, while placebo still exercises its
hook. Independently match the counts to the observed accepted frontiers where
the helper API exposes them. A constant first completed cell followed by a
refined cell must not leave minimum/maximum depth as guessed defaults. Do not
use the local-overallocation diagnostic as an image-quality or acceptance bar.

Preserve the archived a59e local allocator's actual (31,7) refusal. Earlier
no-tangency-map ablations failed under the local allocator; the global allocator
may change their disposition. Record that new result without requiring the
obsolete refusal and without withdrawing the old evidence. The independent
fractional-moment/area/Fourier component controls still power the triangle maps.
They do not prove those maps remain necessary for every globally admitted cell.

Rebind the new source/schema/control closure and regenerate all15 complete
frames. No successful earlier frame or diagnostic can substitute. Keep whole
and fixed-edge max.004e/RMS.0008e, separate author refinements and independent
reference refinement. A new failure remains a real outcome, not permission
to relax a bar. No CFA authority is issued until the complete comparison passes.

**No design blocker remains.** This is a justified numerical allocation change
with independent falsifiers, not an optical calibration, product-quality,
performance, default-promotion or SOTA claim. Implementation waits for the
preregistered release; original failed methods remain failed.

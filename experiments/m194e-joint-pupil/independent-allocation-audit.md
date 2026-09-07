# Independent cell-error allocation audit

2026-09-07. **DERIVED from the actual consumer and current numerical code.**
This is an assessment before a third method proposal, not an implementation
or claim that either refused campaign passed. No scene, reference, precision
bar, Gauss order, adaptive depth or numerical source is changed here.

The second complete run stops at frame3/cell(31,7), after255 cells in the
actual tile8 traversal. Its frozen independent whole-cell value is
15172.35081699726 electrons, with primary/refined difference1.82e-12 and
refined numerical indicator4.99122e-7 electrons. The a59e author trace's
depth6 leaf uses the intended vertex map, so this is not evidence of a missed
predicate. Its cell-order difference3.44317e-6 exceeds its allocated
3.17450e-6; weighted pupil indicators remain approximately1.30e-14.
The leaf's true error has not been independently certified.

For leaf i, write A_i for its native area, D_i=|Q_high,i-Q_low,i| and P_low,i,
P_high,i for its area-weighted pupil indicators. The current implementation
accepts a leaf only when:

`D_i + P_low,i + P_high,i <= cell_tolerance * A_i`.

Because the disjoint retained triangles cover one native unit cell,
sum A_i=1, this is sufficient to satisfy the actual `render_cell` check:

`sum_i(D_i + P_low,i + P_high,i) <= cell_tolerance`.

The converse is false. A difficult small leaf may exceed its area-proportional
share while other leaves consume much less than theirs. Thus the proportional
condition is a numerical budget-allocation strategy, not an additional
definition of whole-cell accuracy. The separate consumer pupil check remains
`sum_i P_high,i <= pupil_tolerance`; the returned total indicator adds that
high pupil quantity to the cell indicator. These quantities and their existing
values must remain explicit under any replacement allocation strategy.

A diagnosis must finish the complete cell partition, retaining locally
over-budget depth6 leaves and their status alongside every other leaf. Report
the sums above, covered area, actual whole-cell high value, its difference
from the frozen reference, number/depth/area of local failures and all work
counters. A signed total difference `|sum Q_high - sum Q_low|` is inadmissible
as a replacement for `sum |Q_high-Q_low|`: cancellation can make it small when
individual regions disagree. No omitted difficult leaf or selected subset may
support the allocation hypothesis.

If that diagnostic meets the existing aggregate bars while the proportional
allocation refuses, it would establish an avoidable allocation refusal on this
cell. It would not retroactively pass the original implementation or prove
every other intended cell can meet the budget. If the aggregate also fails,
there is no such conclusion; a new allocator would still need to reduce the
actual aggregate within the fixed caps or refuse honestly.

A prospective alternative may maintain the complete current leaf partition,
refine a deterministically chosen large-indicator leaf only while an aggregate
bar remains exceeded, and retain depth6 as an absolute per-branch cap. Choosing
the largest current indicator is an algorithmic allocation policy, not a truth
fit. Its tie ordering, treatment of capped leaves and termination/refusal must
be registered before implementation. It must refuse if no permitted refinement
can establish both bars within the existing work/time/storage ceilings.
No leaf may disappear merely because it cannot be refined further.

This approach still needs actual array/lifetime bounds for its active leaf
records; theoretical finiteness is not measured RSS. Low/high estimates remain
heuristic indicators rather than a rigorous universal error bound. Preserve
all independently chosen analytic/map/null/observer controls, separate angle
and cell refinements, and the unchanged complete fifteen-array comparisons
against the frozen independent reference. Those measurements remain the
decisive numerical admission, with no physical-optics or camera-capture claim.

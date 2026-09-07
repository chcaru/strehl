# M194g phase-1 next action after the CPU refusal

2026-09-07. Independent design recommendation only. No profiling, full count,
source change or numerical execution was performed for this note. The original
`preflight-1` remains `UNCOMMISSIONED_COST` under release `0e125df2`.

## Recommendation

First use one bounded profile of the existing small private population to
identify whether a simple counter implementation change is worth making.
Do not begin an open optimization campaign. The profile should decide between
one narrow bookkeeping optimization and a prospective counter-only time-budget
amendment. A second full count should wait for that choice, its independent
controls, and a new release.

The deciding failure is specifically the counter's CPU ceiling. It is not a
cell-integral error, point/node/storage crossing, missing-input problem or
failure of the optical model. Raising a counter-only engineering time budget
can therefore be defensible, provided it is a new prospective experiment with
the original refusal preserved. It cannot make run 1 pass retroactively.
Conversely, optimizing this diagnostic has value only if a small change saves
substantial unnecessary interpreter work without changing what is counted.

Source inspection offers concrete hypotheses but has not ranked them by
measured cost. `Budget.check` was called 8,067,657 times; the Python point loop
charges nominal nodes and serializes an ordered record for each point.
`point_cuts` constructs dictionaries and cut lists, and `_stream` builds
binary payloads. Exact-selector arithmetic, the frozen rule helpers, output
progress writes, or those bookkeeping operations could dominate. The count
of calls alone does not establish which does.

## Small diagnostic, with a stopping point

Reuse the already registered 9×6, five-frame, three-arm private model from
`independent-preflight-controls-design.md`. Its actual 810 cells include all
three branches, both defocus signs and zero defocus; its unchanged source
record has 167,040 nominal points. This avoids choosing a new flattering
benchmark or executing another part of the intended population.

Register a fixed off/count/placebo diagnostic schedule before execution:
plain execution, a standard function-call profiler enabled around the actual
counter, and the same profiler construction with collection disabled. Give
each fresh process a non-resetting 10 CPU / 20 wall second diagnostic ceiling,
including fixture/loader setup, with the unchanged point/node/storage bounds.
This is a proposed resource limit, not a runtime prediction. Keep the original
partial output if the instrumented run crosses it; do not expand it on the fly.

The enabled profile is for attribution, not a product-speed or profiler-free
timing estimate. Retain its full function table and fixed inputs rather than
only selected hot functions. Compare all actual cell/frame/branch/work counts
and the ordered geometry stream digest across off/count/placebo. Preserve
timing, observer and storage records separately; their values need not be
byte-identical. The output/count invariant must fail under the existing
omitted-point or changed-cut positive control. No radiance entry point is
permitted, and the existing recording traps must remain live.

After this one diagnostic, choose one of two outcomes:

- If it identifies a specific redundant operation with a small implementation
  remedy, register that one counter-local change. Keep the old loader/model,
  selector predicates, inverse-then-dot heights, roots, low/high rules, mass
  checks, signed cuts, stream ordering and bytes unchanged. For example,
  avoiding repeated encoding of an immutable arm prefix is semantically much
  narrower than replacing per-point cut geometry with an inferred count.
  This example is not a claim that prefix encoding is the measured bottleneck.
- If cost is spread across required work, or the proposed rewrite would
  replace geometric operations, amend the counter-only elapsed budget
  prospectively instead. Choose a finite resource allowance because the
  program is willing to spend it, not because it is fitted to make a subset
  look complete. A 180 CPU / 240 wall second allowance is a bounded option,
  not a guarantee that the full population will finish. The root may select
  a different declared allowance before release; no optical/error/work bar
  should change with it.

One minor cleanup followed by repeated full-run timing failures would not be
an economical route. If the profile provides no useful attribution under its
cap, retain that result and decide the resource allowance rather than adding
new profiling axes.

## Conditions on either next full count

The 320×240 fixture, five original frame indices, three arms, 1,152,000-cell
coverage requirement, strict per-frame 8-million-point/1.2-billion-node limits,
32 MiB tracked-array scope and all no-radiance restrictions remain unchanged.
Keep one clock across all fifteen traversals and enforce it at least per cell
and low/high rule batch, including analytic-only cells. A batching optimization
must preserve the strict work-ceiling refusal and cannot overcharge, undercount
or hide work by resetting counters. The existing equality/just-below, missing
coverage, low/high/mass, source and original-error-retention controls are the
economical regression set; no new certificate framework is needed.

If the implementation changes, compare the original frozen revision with the
candidate on the same complete small inputs and exact count/stream payload,
then independently rerun affected controls on the new source. A profiler
number alone cannot authorize a changed counter. If only the time allowance
changes, validate the changed limit at its real boundary with injected clocks,
the unchanged work limits, and the intended input/release hash bindings. Do
not rerun unrelated optical or CFA controls whose sources have not changed.

Any apparent speedup on small fixtures is only a diagnostic observation.
Do not extrapolate from 821,287/1,152,000 cells: the remaining cell-refined
population uses higher cell-rule orders, so equal cell counts do not imply
equal work. The completed primary/angle rows also cannot substitute for its
as-yet uncounted angular partitions. An eventual complete cost PASS would
still admit only the next separately reviewed numerical phase, not radiance
accuracy, physical optics, CFA emission, production quality or SOTA status.

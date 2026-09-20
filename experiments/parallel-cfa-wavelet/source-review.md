# Independent source review

2026-09-19. full_context_placement; no build/test/RAW execution. **No numerical
or full-adapter blocker found for the frozen controls and separately scoped
cost trial.** Correctness, preservation and resource results remain pending.

The transform changes only scheduling of disjoint output rows or paired
low/high rows. Each output retains the serial tap sequence and f32 expression
order, stage order, cyclic addressing and complete packing. Sources, planes
and probe members remain sequential. No reduction tree, scattering addition,
source-volume collection or concurrent full transform workspaces were added.
The independent nested serial oracle includes the old transform source
unchanged; exact output comparisons under one/four threads can reject a
schedule/index/tap change rather than merely round-tripping the new code.

`scaled_add` rescales all four complex numerators and their common denominator
by old_max/new_max before inserting a larger weight. Otherwise it adds
weight/current_max. The finite normalized mathematical weights are unchanged;
f32 association necessarily changes. Weight0 leaves scaled state untouched.
The actual fold still updates unweighted means independently and uses the
same den>0 versus mean/count reconstruction branch, including terminal DC.
Input/state and accumulator finiteness are checked. This avoids the previously
unchecked finite exp80-weight times large-DN product, while leaving no claim
that arbitrary unbounded f32 inputs can never overflow a sum. Physical u16
source/full-transform bounds and the fixed70-frame ceiling are relevant.

Energy, WB-squared sums, support smoothing, supplied variance, exponent, weight
statistics, fallback, input hull and developer are unchanged. Probe code is
included from the old file, retaining sixteen source draws/eight pairs and
its headroom refusal. The copied full mechanical control changes only the
candidate-preservation comparison: the old operator must still reproduce its
historical hashes; new baseline, source/variance evidence and weights remain
exact, while candidate CFA/RGB differences receive explicit tight bounds.
The original boundary quality tests are included unchanged, with their failed
fractional weak-red bar and required benefit intact.

The full adapter diff adds one zero-initialized coefficient-scale field and
passes it to that same fold, plus module/env/progress labels. It preserves
canonical18,18,18,16 baseline absorption, full crop/CA/WB/tone, exact baseline
RGB16 guard, source35 cost scope, one-source known4/RGB equality, and original
read-only checks. The scale field adds67,108,864 bytes at4096²; it does not
multiply source workspaces. Actual process memory/time remain unmeasured.

The root preservation checker binds the old controls2 JSON hash, requires
the same twelve cases, baseline/evidence (except probe timing), decisions and
false admission, then applies2e-6 absolute candidate score and2e-4 RGB-ratio
continuity bounds. The full runner requires the same executable/source binding
and successful numerical/full-control completion before cost; full additionally
requires the root's explicit cost feasibility decision. These are execution
repairs under observational scope, not a replacement quality gate. Root was
notified of one log-marker mismatch after build binding: the copied full test
emits `PARALLEL_CFA_FULL_MECHANICAL`, while the frozen runner expects its old
prefix. Root will preserve the driver/source binding and, only if numerical
tests and continuity succeed but that final marker assertion fails, record
the wrapper-only failure and use a separately bound completion helper that
checks the actual new record. That is bookkeeping, not numerical acceptance.

Reviewed/frozen bindings:

| File | SHA256 |
| --- | --- |
| implementation.rs | 5f1bea55b13b1fc05166351dfdf37d4ea289c2df56bb0b2b091734507149a042 |
| transform.rs | f9218cee4cb841505a99c490dfbc93ced07d70dcc21a9cf129e7b9b0bcafc1c3 |
| full-stack.rs | 815b4b1d705811513aece4f92840aa812e5ff5e9853dcec5bca8515dafd84ed9 |
| independent-controls.rs | 1698535c374481f90d66cddf2dcc2d27607a0281299017a81fd35ddd4c369e3a |
| independent-full-controls.rs | 7548752d4092d7422294f4a072ff293d5989a35612c4efdca6e7e3941b7ecde9 |
| independent-plan.md | 06752c47825663fb573411f9d98a4c9c8f766942741b1c0e093c074401aac966 |
| preserved-screen.py | 3a369682fd18796cbb8951dff417fcc34367c6f4ad2af93b2cf8ab4443c8f0d0 |
| full-run.py | 02d14cc297f4485d533bfcb2fc5952263cf61aeb5012ef150e5680d136c7a9c8 |

The root-owned build binding is authoritative for the unchanged runner and any
separate completion receipt. This review was written in parallel with that build and changes no
compiled source or frozen control plan.

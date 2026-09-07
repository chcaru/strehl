# Independent review of the proposed numerical release

2026-09-07. **DERIVED design review; no numerical execution or release.**
Reviewed root's `next-numerical-release.md`, committed at `01d4e52b`, SHA256
`2565a27f1b72b5625738c2b232b0a58b14ef735f0d64ed8d50d41c07646d987c`,
against the fixed 150-case catalog, independent reference plan and M194g
preregistration. The resource split and sparse-payload choice are coherent.
The observer population can exercise its required branches. The implementation
registration should fix the small details below before execution; none calls
for a different scene, threshold, numerical method or larger population.

## Budget and coverage meaning

The author component allowance is one non-resetting batch: 600 process-CPU
seconds, 1200 wall seconds, 16 million point evaluations and 2.4 billion angular
nodes. Cache construction, all four observer traversals, faults and restored
companions consume it. A point means the frozen Meter's individual sampled
point, not one invocation on a batch of points. Analytic cell evaluation and
cache-only work still consume the clock, even when they consume no frozen
pupil points. Check time before final success as well as throughout traversal.
This is separate from the subsequent per-frame work limits and per-five-frame
arm time limits. The independent reference has its own 30-million-evaluation
component batch; neither process borrows the other's unused allowance.

The 32 MiB allowance is tracked explicit storage, not measured RSS. A scalar
frame, branch frame, sparse indices and diagnostic rows may coexist, together
with bounded scratch, while one frame is written or compared. Do not retain
all 15 observer frames in memory to establish equality. Count simultaneous
owned buffers, including copies made during sorting or serialization; a view
does not create a second backing allocation. Resource exhaustion remains an
uncommissioned result, not permission to omit a control.

For clarity, freeze the observer grid as integer centres x=0..8, y=0..5,
with native linear index 9*y+x, and name the arms primary, angle-refined and
cell-refined. Each execution covers all five frames in all three arms:
810 cells, hence 3240 cells across the four executions. Reversal applies to
the entire 54-cell sequence within each frame; frame/arm order stays fixed.
Use the actual proposed hybrid (analytic-enabled) consumer. The separate
150-case controls already require enabled/disabled component comparisons.

## The observer scene is powered, by geometry

The specified inverse is q0=(x/2-3/8, y/2+1/8). Thus
`h=x/2+y/8-75/32`, `H=5/16`, and `R=abs(dF)*sqrt(17)/8`.
The signed defocus arrays are dF=(-1,-.5,0,.5,1) and dB=(0,.5,1,1.5,2).
At every frame, (0,0) is strictly background, (8,5) strictly foreground and
(4,3) numerical: their heights are -75/32, 73/32 and 1/32, respectively.
The largest R+H is below 1, while abs(1/32)<H. These are independently
derived branch witnesses, not results from running the selector.

The intended textured fields have nonzero wave vectors and amplitudes. At
frame 0's foreground witness the selected defocus is -1, so actual wave and
nonzero-argument transfer work is possible. Assert that the real branch and
transfer paths reach those cases; the existence of a configured wave alone
does not show that its cached factor was consumed. The zero-defocus cases
must also be reached. This does not require a magnitude-discrepancy claim
for a numerically tiny transfer.

## Concrete consumer and power details to freeze

1. Give the u8 branch codes explicit distinct values. Assert the three
   independent witness coordinates above through the actual output reader.
   Exact schema/source bindings must include the two textured field records;
   they cannot silently resolve to the private counter's old constants.
2. Record a nonzero actual count-hook call total, nonzero placebo-hook total,
   and populated count collection. Off/placebo must perform no collection.
   Count cache misses/hits or actual transfer-consumption witnesses separately
   from persisted numerical payloads. A mode string or unused callback flag
   cannot satisfy this condition. Byte equality is required for corresponding
   same-arm scalar/branch/sorted diagnostic payloads, not across refinement
   arms or mode-dependent receipts.
3. Fix the scalar fault at frame 2 primary, native (4,3): add exactly 1 electron
   to that one finite stored scalar. Fix coverage power by replacing (4,3)
   with (5,3), creating one omission and one duplicate. The actual comparison
   or coverage consumer must refuse, and a literal reopened unchanged
   companion must pass. No fault need depend on a rounded nextafter changing
   an arithmetic result downstream.
4. Add one direct sparse-diagnostic fault at that same numerical site:
   increase its stored `cell_quadrature_delta_e` by .01 while leaving scalar
   and branch arrays untouched. The actual same-method payload comparator
   must reject it. Also reject a numerical branch with no sparse row, an
   extra row on an analytic site, a duplicate/unsorted index and an invalid
   branch code. Exercise the semantic reader/equality path, not solely an
   outer file-hash mismatch. Otherwise the currently named scalar and
   coverage mutations could leave a skipped diagnostic comparison undetected.
5. Preserve the four named fallback fields directly from the actual receipt;
   require finite nonnegative indicators. In the frozen implementation,
   `value_error_indicator_e = cell_indicator_e +
   weighted_high_pupil_indicator_e`; it is not another independent error
   estimate. `cell_quadrature_delta_e` is the sum of absolute low/high leaf
   differences, not a signed sum. Mapping those columns or checking that
   identity is serialization evidence, not independent precision evidence.
   Analytic sites correctly have no adaptive-indicator row. Complete external
   scalar comparisons remain their accuracy test.

The byte-equality checks may compare successive persisted frames with bounded
scratch; they do not require mode-dependent logs or JSON timing fields to
match. A JSON-normalized, re-opened valid input plus changed-field refusal
addresses the previous tuple/list boundary defect on the consuming path.
Do not count input normalization alone as model or payload verification.

No observer or reference was run for this review. Full-cost admission and an
explicit phase-2 release still precede implementation; frozen component source
and commands precede execution. The .004/.0008 electron external bars, complete
populations, retained old failures and separate all-array release remain intact.

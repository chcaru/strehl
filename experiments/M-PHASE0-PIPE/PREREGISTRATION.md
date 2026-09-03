# M-PHASE0-PIPE — preregistration

**Registered:** 2026-09-02, before this lane decoded a capture, timed a fold,
or implemented the queue. Reconnaissance was limited to the proposal,
architecture, prior reports, source, capture metadata, and machine state.

**Owned paths:** `experiments/M-PHASE0-PIPE/`,
`docs/research/M-PHASE0-PIPE.md`, the decode/fold scheduling seam in
`crates/strehl-cli/src/merge_cmd.rs`, its new queue helper, and the
`RENDER_ENV` registry in `crates/strehl-cli/tests/byte-freeze.rs`.
`docs/STATUS.md` is explicitly excluded.

**Read-only inputs:** name-sorted ARWs in
`D:\personal\macro\112MSDCF` and `D:\personal\macro\bee-3-cpl`. All sidecars,
renders, logs, build products, and records go below
`experiments/M-PHASE0-PIPE/out/`.

## 1. What D13 actually says

The authoritative proposal's D13 assertion is not merely “fold scales usefully
past eight workers.” It is:

> Pyramid folding continues scaling beyond eight workers on an idle 16-core
> machine sufficiently to justify worker-count-independent reduction and
> memory redesign.

The proposal records useful 1→8 scaling, says 8→16 was not measured, and asks
for an idle 1→32 sweep plus a fine-N ladder. It supplies **no numeric D13
go/no-go threshold**. Its numerical CPU, memory, byte-invariance, and
staircase end-state bars appear later in D15 and require D9's unimplemented
fixed reduction lattice. This lane will not attribute a newly chosen threshold
to D13 or claim that a speed-only worker override meets those end-state bars.

This lane operationalises “sufficiently” before measuring:

* **D13 TRUE:** chosen 8→16 fold speedup is at least **1.20x on both real
  stacks**.
* **D13 FALSE:** the TRUE condition is not met. The curve is still reported;
  no post-hoc gray band will turn a miss into a pass.
* **Fold saturation:** the first power-of-two worker setting whose next
  doubling improves chosen fold time by **less than 1.10x on both stacks**.
* W=32 characterises SMT and queue starvation; it is not substituted for
  D13's sixteen-physical-core bar.

The 1.20x bar asks a substantial reduction/memory redesign to buy at least a
substantial gain. A lower bar would bias toward surgery. Background contention
can only make scaling look worse in aggregate, but variation correlated with
worker setting can move either ratio; alternating sweeps and load rejection
target that failure.

## 2. D13 protocol and controls

The committed baseline binary is built from an archived committed source tree,
not the live shared working tree. Its SHA-256, source commit, full command,
relevant environment, input file list, and output hash are recorded.

Primary curve, on each input stack:

* first 64 name-sorted ARWs;
* `STREHL_PYRAMID_WORKERS=1,2,4,8,16,32`;
* one ascending and one descending sweep;
* one fixed `STREHL_WARPMAP` below this lane's `out/`;
* warm/page-cached fold capability, with alignment served from that sidecar;
* chosen time = the smaller valid fold time at each setting, per rule 16.

The fine-N arm uses `bee-3-cpl`, W=4, N=29..36, ascending then descending.
It reports total and per-frame fold time. A staircase is called present only
if the chosen N=33 time is at least 5% above N=32 and the N=33 increment is the
largest adjacent increment in the ladder. This descriptive arm does not change
the D13 verdict.

Valid runs require rc=0, the expected folded/total frame counts, a complete
TIFF, a full-file SHA-256, expected nonempty geometry, and nonzero pixel count
and sum from an independent TIFF reader. Repeated runs at one worker setting
must have one output hash. Hashes across worker settings are expected to differ
because the override changes floating-point reduction order.

### Commissioning, before accepted timing

The same wall-timing function used by the curve is run on identical four-frame
renders with and without an independently requested **2,000 ms sleep inside
the timed interval**. Commissioning passes only if the planted-minus-baseline
wall delta is 1,750–2,500 ms. The binary's parsed fold time must also be
positive and no greater than wall time. This proves the wall timer detects a
known slowdown; it does not falsely claim that the external sleep commissions
the binary's internal `Instant`.

The rendered TIFF is fully hashed and decoded. Zero pixels, zero nonzero
pixels, zero pixel sum, a truncated TIFF, a folded-count mismatch, or an empty
output must be rejected. Thus neither the process nor its output can be an
optimised-away no-op. Capture trees are manifested with
`Get-ChildItem -Force` metadata before and after; any difference invalidates
the campaign.

## 3. Load and resource validity

Each run records wall time, child CPU seconds, system busy fraction from
`GetSystemTimes`, external busy fraction after subtracting the child's CPU
time, peak working set, and available memory. Before launch, a five-second
probe must be at most 15% busy. During-run external busy above 10% marks the
arm contended and excludes it from the chosen curve; it remains in the record.
If a full quiet curve cannot be obtained, D13 is INCONCLUSIVE notwithstanding
the numerical rule above, and all attempts are reported.

W=16 and W=32 are skipped rather than invited to page when available physical
memory is below the harness's printed estimate plus 4 GiB. A resource skip is
not evidence against scaling. Concurrent CPU, RAM, thermal, or D: activity
biases times slow. Warm cache biases cold end-to-end speed fast, deliberately:
the estimand is fold scheduling after storage was separately shown nonbinding.
The per-setting minimum biases toward quiet-machine capability, not typical
latency.

## 4. Queue implementation and acceptance

The candidate switch is `STREHL_DECODE_FOLD_QUEUE=on`; unset, blank, and
explicit `off` select the unchanged path. Any other value must fail clearly.

The candidate uses a **zero-capacity rendezvous channel per existing fold
chunk**. A producer decodes the next frame while that chunk's consumer folds
the current frame. It must preserve worker count, chunk boundaries,
frame-within-chunk order, part order, and `BandMerge::absorb` order. At most
one additional decoded frame per active chunk may be live; the binary prints
that bound. A shared work-stealing frame queue is rejected because it would
change which floating accumulator receives a frame. An unbounded or
decode-all queue is rejected because live memory would grow with frame count.

Hard correctness gates:

* unset, explicit `off`, and `on` produce identical whole-file SHA-256 at a
  fixed worker count on the same real stack and flags;
* the existing tests and release build pass from fresh compilation;
* queue tests prove order, exactly-once consumption, overlap, bounded
  decode-ahead, and producer/consumer error propagation;
* queued peak working set remains finite and is reported against the printed
  analytic bound;
* the mode is named in the run banner, so an inert flag cannot pass by hash.

Any byte mismatch, hang, lost/duplicated frame, unbounded-live-frame failure,
or build/test failure rejects the implementation. A checker recomputing its
own answer is not used: final hashes are independently re-read with
PowerShell `Get-FileHash`, and an independent verifier chooses a holdout run.

## 5. Speed protocol and retention bar

After correctness, both 64-frame real stacks run five accepted alternating
off/on pairs at the unchanged default worker plan, fixed sidecars, and warm
cache. Every run is retained. Capability is best-of-5; medians are also
reported. During-run external busy must be at most 10%, or the pair is
contended and rerun when quieter.

The queue earns retention only if, on **both** stacks:

* off-best / on-best is at least **1.05x**;
* queued median is no more than 2% slower than off median;
* output hashes are identical.

Less than 1.03x on either stack is a negative result. The 1.03–1.05 interval
is too small to earn this complexity and is also removed rather than marketed.
This bar is intentionally stricter than noise: a 3% opt-in scheduling gain is
not worth another concurrency path. Best-of-N can flatter capability through
selection; publishing every run, medians, and load beside minima exposes that
bias.

# Peak RSS — resolving a direct conflict between two committed documents

**Status: tiebreak measurement, run by the orchestrator because two subagents disagreed and neither
could adjudicate its own number.** `M2-baseline-skeleton.md` and `M2-verification.md` state peak RSS
figures that differ by **2.2x**, and `SYNTHESIS.md` fact 22 had adopted one of them together with a
conclusion that this measurement shows is **backwards**.

| Source | Claim | Verdict |
| --- | --- | --- |
| `M2-baseline-skeleton.md` (original) | 4.12-4.20 GB at N=22 | **Right about the magnitude**, wrong about the mechanism |
| `M2-verification.md` §3 | 1.81-1.94 GB at N=22, over 9 runs | **Correct number, wrong configuration** — it is the reduced-thread figure |
| `SYNTHESIS.md` fact 22 (as committed) | 1.81-1.94 GB, "holds with **more** headroom than published" | **Refuted.** The headroom conclusion is inverted |

## 1. The measurement

Machine: Ryzen 9 9950X3D, 32 logical processors, 64 GB. `strehl.exe` built `--release`.
Method: `Start-Process -PassThru`, poll `PeakWorkingSet64` every 15 ms until exit, then read once
more after exit. Same method both subagents used, so the method is not the disagreement.

**N = 22** (`C:\dev\macro\test\109MSDCF`), varying only `RAYON_NUM_THREADS`:

| `RAYON_NUM_THREADS` | Peak RSS | Planner's prediction |
| --- | --- | --- |
| 1 | **833.1 MB** | 3.53 GB |
| 3 | **1686.2 / 1599.2 MB** | 3.53 GB |
| default (32) | **3892.7 / 4193.8 / 3928.1 MB** | 3.53 GB |

**Status: MEASURED**, n=6 runs across 3 configurations.

## 2. What this settles

**Both subagents measured correctly and neither was reproducible from the other**, because peak RSS
is a function of *live concurrency*, not of the plan:

    peak RSS ~ min(chunks, rayon pool size) x per-worker bytes

The verifier reported `RAYON_NUM_THREADS=3` in its own §2 as a determinism control, and my 3-thread
figure (1599-1686 MB) brackets its 1.81-1.94 GB. The skeleton agent's 833 MB at 1 thread reproduces
**exactly**. So the two documents were measuring two different configurations and each labelled its
result as *the* peak.

**The default-configuration figure is ~4.0 GB at N=22, not 1.9 GB.** Anything quoting 1.81-1.94 GB
as the peak is quoting a reduced-thread run.

## 3. The part that actually matters — it does not saturate where the plan says

Run on **105 real, distinct frames** (`C:\dev\macro\test\coffee-bean`), default threads — not a
synthetic corpus of copied files:

```
workers         : 18 chunks of <= 6 frames (20 allowed by the 6144 MB budget, 32 by CPU)
working set     : 321 MB/worker, 5.77 GB peak (DERIVED, O(workers) not O(frames))
```

**Measured peak: 6825.2 MB = 6.665 GiB = 7.157 decimal GB.** Status: MEASURED, n=1 at this N.

So the planner under-predicts by **1.24x** at N=105 and by **1.13x** at N=22 — and the error grows
with worker count, because it is per-worker. Modelled per-worker is `px*(14+12+4) + frame_bytes` =
**321 MB**; measured per-worker is **364 MB** (11 workers) and **379 MB** (18 workers). The omitted
term is the decoder's own scratch, which `rawler` allocates on top of the frame buffer we account
for.

**Against `SYNTHESIS.md` §3.2's 8 GB ratchet, N=105 is already at 89%**, and the skeleton agent
measured **7,616 MiB at N=220** on a synthetic corpus, which is 7.99 decimal GB — i.e. at or over.

## 4. Two decisions this forces, neither of which an agent should take alone

1. **The ratchet's units are undefined and at 7% margin they decide the verdict.** §3.2 says "8 GB".
   7,616 MiB is 7.44 GiB (passes) *or* 7.99 decimal GB (fails). **Pin the unit.**
2. **`MEMORY_BUDGET_BYTES` is the wrong lever.** It is 6 GiB and it sizes the worker pool via
   `by_memory = MEMORY_BUDGET_BYTES / per_worker_bytes`. Because `per_worker_bytes` under-counts by
   13-24%, the planner **licenses more workers than the budget can actually pay for**. The fix is to
   model decoder scratch in `per_worker_bytes`, not to lower the constant — but doing so **reduces
   parallelism** (N=105 would drop from 18 workers to ~14), which is a real speed cost on a project
   whose goal is SOTA speed. That trade belongs to the owner.

**Not fitted here on purpose.** Two points is not enough to decompose fixed overhead from
per-worker cost; a naive linear fit gives a *negative* intercept, which is unphysical and is a sign
the relationship is not clean. A proper scratch model needs a worker-count sweep, not a fudge
factor.

## 5. What was changed now

Only the tool's honesty. `WorkerPlan::describe` printed its under-count as `"{:.2} GB peak
(DERIVED, O(workers) not O(frames))"`. It now prints `">= {:.2} GB peak (LOWER BOUND -- excludes
decoder scratch; measured peak runs 1.13-1.24x this)"`. **The ratchet, the budget constant and the
worker sizing are untouched** — see §4.

## 6. How to quote this

- **Do** quote: ~4.0 GB at N=22 and 7.16 decimal GB at N=105, both at default thread count.
- **Do not** quote 1.81-1.94 GB as a peak without saying `RAYON_NUM_THREADS=3`.
- **Do not** quote "O(workers) not O(frames)" as though it implies a small constant. It is true and
  it is still the right architecture, but the constant is ~379 MB per worker and the pool goes to 20.
- **Do not** quote the N=220 figure as equivalent to the others: it is a synthetic corpus of copied
  ARWs, so decode-path behaviour may not represent 220 distinct exposures.

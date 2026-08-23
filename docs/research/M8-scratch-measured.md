# M8 — decoder scratch, measured

**Status: the scratch is MEASURED. The under-count is NOT what it was believed to be.**
Measured on the owner's own three real focus-bracket stacks plus three real dark-frame folders,
with a harness null, a known-size positive control, a real-data null, a cross-instrument control,
a run-to-run repeat budget, and a held-out stack that was never fitted. `rawler` was measured
strictly as a black box (`AGENTS.md`: its source is link-freely, do-not-read). Nothing under
`C:\dev\macro` or `D:\macro-dark-frames` was written to. No synthetic frames were used anywhere in
this measurement.

Every claim below carries a label: **MEASURED**, **VERIFIED**, **DERIVED**, **ARGUED** or
**UNVERIFIED**. An unlabelled number in this project is a defect (SYNTHESIS §5).

Code: `experiments/m8-scratch/`. Every number here comes from a command quoted in §11.

> **NOT yet independently reproduced.** SYNTHESIS §5 says the author never verifies their own work,
> and this report has not had that pass. Three legs are set up for whoever does it, in the order
> that makes a failure most informative:
>
> | Leg | What it should produce |
> | --- | --- |
> | `.\run-m8.ps1 -Stage selftest` then `-Stage null` | 13/13 harness controls pass; a real-data null of ≤24 KiB; `read-not-decode` recovering real ARW sizes at 1.002–1.004×. If these do not hold, stop — nothing downstream is interpretable. |
> | `.\run-m8.ps1 -Stage floor` | 320.2 / 430.3 / 540.4 / 540.3 / 650.4 / 650.4 MiB at chunks 1/2/3/4/6/8, sd ≤ 0.1 MiB. This is the most falsifiable claim in the report: a 110.04 MiB step landing exactly on ⌈log₂ chunks⌉, predicted from geometry before it was measured. |
> | `.\run-m8.ps1 -Stage holdout` + `python m8_analyse.py all` | Mean out-of-sample error 8.39%, max 17.47% on `119MSDCF`. **Deliberately a stack that appears in no fit.** |
>
> The §6.1 floor result is the one to attack first. It is dead-reproducible (sd 0.06 MiB), it is
> derived independently from the M1 geometry (`px × 14` = 110.04 MiB), and it carries the claim that
> most of M2's "missing" memory was never decoder scratch at all. If it survives, the rest follows;
> if it falls, §6.3, §8 and §10.2 all fall with it.

---

## 0. The verdict in one paragraph

`M2-rss-resolved.md` found the worker-sizing model under-counting by 13–24% and attributed the gap
to decoder scratch. **The decoder scratch is real and is now measured — 39.4 MiB of private commit
per concurrent decode, proportional to compressed file size — but it is not where most of the
missing memory went.** Sweeping the real stacker across 14 thread counts, 12 frame counts and 3
stacks (82 fitted runs, plus 10 held-out runs on a stack never fitted) resolves peak RSS into three
terms, two of which the shipped model omits entirely: a **15 MiB process floor**, **342.8 ± 5.4 MiB
per live worker**, and **110.04 MiB × ⌈log₂ chunks⌉ of `Selection` partials waiting in rayon's
reduce tree**. That third term is not scratch at all — it is the stacker's own reduce, and at 18
chunks it is 550 MiB, larger than the entire scratch contribution. The per-worker excess over the
buffer model is **37.0 ± 5.4 MiB** of working set and **7.7 ± 6.6 MiB** of private commit, the
latter consistent with zero: at the peak instant most workers are folding, not decoding, so the
per-decode scratch does not all coincide. Allocator retention was **separated from scratch and
bounded**: it settles at ≈2 MiB of resting commit and adds at most 4.15 MiB to peak commit, all
within the first 40 decodes, after which the kernel peak is flat to the resolution of the counter,
whereas scratch scales linearly with concurrency to R² = 0.99998. Out-of-sample on the held-out
stack the model predicts peak RSS to **8.4% mean / 17.5% max**, against a MEASURED run-to-run
scheduling spread of up to 7.3%. If the honest model were adopted the worker cap would fall from
20 to **16**, which changes the plan at N=105 (18 → 15 chunks) and N=220 (20 → 16) and leaves N=22
**unchanged at 11**. **This is a recommendation, not a change**: the default sizing is untouched,
and the honest model ships behind `--memory-model m8`, off by default. Two SYNTHESIS items move on
the way past: fact 22 is refined (concurrent decodes are **not** bounded by `min(chunks, pool)`,
because the decoder is itself rayon-parallel), and **§3.2.1 assertion 1 fails at its own specified
pair** — at a pinned pool, `N = 4 × pool` exceeds `N = 2 × pool` by 16–20% on unregressed code, so
that gate would go red today. §10 names both and proposes a restatement.

---

## 1. The headline numbers

All figures MiB = 2²⁰ B unless the row says decimal MB. Every stacker run had
`RAYON_NUM_THREADS` pinned.

| Quantity | Value | Label | Where |
| --- | --- | --- | --- |
| Decoder scratch, **isolated, private commit** | **39.36 ± 0.11 MiB** per concurrent decode on `coffee-bean` (37.8 MiB mean file); **32.34 ± 0.06 MiB** on `dark-ISO50` (31.6 MiB mean file) | MEASURED | §4.2 |
| Decoder scratch, **isolated, working set** | 74.8 MiB per concurrent decode at 32 threads, 8.2 MiB at 1 | MEASURED | §4.2 |
| Is it constant, file-proportional or pixel-proportional? | **File-size proportional**, slope **1.0093 ± 0.0147** (dimensionless), intercept 0.685 ± 0.530 MiB — consistent with zero | MEASURED | §4.1 |
| Pixel-proportional vs constant | **Cannot be separated.** `active_px` = 32,966,016 on every file available | UNVERIFIED | §4.1, §9 |
| Extra cost of the decoder's own thread pool | +1.51 ± 0.04 MiB per doubling of `RAYON_NUM_THREADS` | MEASURED | §4.1 |
| Allocator retention, resting | settles at **≈2 MiB per process** by decode ~10; ±8 MiB reuse oscillation that **sums to +0.8 MiB over 104 decodes** | MEASURED | §5 |
| Allocator retention, peak commit | **+4.15 MiB total**, all in the first ~40 decodes, then **exactly flat (+0.000 MiB)** to decode 104 | MEASURED | §5 |
| Scratch vs retention | **Separated.** Scratch scales with concurrency (R² = 0.99998 over k=0..32); retention does not scale and is bounded | MEASURED | §5 |
| Process floor | **14.4 MiB** (320.2 MiB at N=1 minus 305.79 MiB of buffers), sd 0.06 over 3 runs | MEASURED | §6.1 |
| Reduce-tree term | **110.04 MiB × ⌈log₂ chunks⌉**, matching `px × 14` = one `Selection` to **0.1%** | MEASURED | §6.1 |
| Per-worker peak working set | **342.8 ± 5.4 MiB** (359.4 decimal MB) | MEASURED | §6.3 |
| — of which the shipped buffer model accounts for | 305.79 MiB (320.6 decimal MB) | DERIVED | §2 |
| — **in-situ excess (the "scratch" the planner is missing)** | **37.0 ± 5.4 MiB working set; 7.7 ± 6.6 MiB private commit** | MEASURED | §6.3 |
| Model ratio to the shipped model | **1.121×** working set, **1.025×** private commit | MEASURED | §6.3 |
| Out-of-sample error, held-out stack `119MSDCF` | mean **8.4%**, max 17.5%, bias +0.6% (n=10) | MEASURED | §7 |
| Run-to-run spread at a fixed condition | pooled 1.5%, **max 7.3%** | MEASURED | §6.2 |
| Honest worker cap at the unchanged 6 GiB budget | **16** (unchanged by ±1σ on the slope) | DERIVED | §8 |
| Corrected chunks: N=22 / N=105 / N=220 | **11 / 15 / 16** (now 11 / 18 / 20) | DERIVED | §8 |

### 1.1 Two numbers in `M2-rss-resolved.md` are in conflicting units

`WorkerPlan::describe()` printed `321 MB` **decimal** (`per_worker_bytes / 1e6`). The `364`/`379`
figures M2 set beside it were `PeakWorkingSet64 / 1MB` from PowerShell, which is **MiB**. The
buffer model is 320,645,440 B = **305.79 MiB = 320.6 decimal MB**. M2's *ratios* (1.13–1.24×) are
unaffected because both sides were divided consistently; the *absolute* gap those two printed
numbers appear to show is not the real gap. **VERIFIED** by recomputing both from the same
constant. This report states units on every figure, and `describe()` now labels its own.

---

## 2. What the model claims, and what it is made of

`WorkerPlan::new` sizes the pool as `min(MEMORY_BUDGET_BYTES / per_worker_bytes, num_cpus, frames)`
with `per_worker_bytes = px × (14 + 12 + 4) + frame_bytes`. On the A7C II, `px` = 3516 × 2344 =
8,241,504 and `frame_bytes` = 7168 × 5120 × 2 = 73,400,320 B (**DERIVED** from the M1 geometry;
**MEASURED** exactly by the decoder — see §3.3).

| Term | Bytes | MiB | What it is |
| --- | --- | --- | --- |
| `Selection`, `px × 14` | 115,381,056 | 110.04 | f32 focus + 4 × u16 channel + u16 winner index |
| `FocusField`, `px × 12` | 98,898,048 | 94.32 | three f32 planes |
| `luma`, `px × 4` | 32,966,016 | 31.44 | one f32 plane |
| frame | 73,400,320 | 70.00 | the decoded, zero-padded CFA buffer |
| **total** | **320,645,440** | **305.79** | = 320.6 decimal MB |

**6 GiB / 305.79 MiB = 20 workers.** That is the number this measurement is about.

---

## 3. Why you should believe the instrument

### 3.1 The harness self-tests (MEASURED — 13/13 pass)

`m8-scratch selftest`, all with `RAYON_NUM_THREADS=1`:

| Test | Result | What it buys |
| --- | --- | --- |
| **S1 idle drift (the harness null)** | +32 KiB ws, +16 KiB commit over 2 s | The floor of the instrument. Every number below is thousands of times this. |
| **S2 known allocation** (the positive control) | 64 / 256 / 1024 / 2048 MiB recovered at ws **0.9999–1.0000×**, commit 1.0020–1.0026× | The harness detects an allocation of known size, to 0.01% on working set. |
| **S3 committed but untouched** | 1024 MiB planted → commit **+1075.9 MiB**, working set **+4 KiB** | The two instruments are **not** measuring the same thing, and the harness proves it rather than assuming it. This one result explains §6.1. |
| **S4 transient spikes** | 12/12 caught, lifetimes 647 µs to 100.6 ms | A peak that exists for under a millisecond is still seen. Sampling cannot miss the decode. |
| **S5 phase attribution** | commit attributed to the planting phase, 0 to the others | Phase boundaries are real. |
| **S6 kernel peak ≥ largest planted** | 2151.7 MiB ws / 2152.4 MiB commit ≥ 2048 MiB | The kernel counter brackets the run. |

### 3.2 The null on real data, not on synthetics (MEASURED)

SYNTHESIS §5 item 9: a synthetic null is not a null. So the null was run on the real corpus.

- **Idle holding a real file list, no decode:** +24 KiB ws, +16 KiB commit over 2 s.
- **k = 0 in the concurrency sweep** — same process, same real file list, no decode: 4 MiB ws,
  1 MiB commit.
- **Idle again after 8 real reads:** **0 ws, 0 commit.** No ratcheting from merely touching the
  corpus.

### 3.3 The positive control on real files (MEASURED)

`read-not-decode` reads a real ARW into memory without decoding it. Across 8 files the recovered
size / actual file size is **1.0023–1.0038×**. So the harness recovers a real, known quantity from
real data, not just a planted `Vec`.

Independently: `hold_commit − base` divided by `frame_bytes` over 660 isolated decodes is
**1.00273×**. The decoded frame buffer is accounted for **exactly**, so everything else the decode
costs is scratch by construction rather than by assumption.

### 3.4 Cross-instrument control (MEASURED)

The stacker is measured from outside (a PowerShell poller reading `PeakWorkingSet64` /
`PeakPagedMemorySize64`), while the harness reads its own counters from inside. At k = 1, 4, 12, 24
the two agree **digit for digit** (e.g. `179150848 == 179150848`). External stacker numbers are
therefore the same quantity as internal harness numbers.

### 3.5 Fact 22's own numbers, reproduced (VERIFIED)

SYNTHESIS fact 22 states the same binary on `109MSDCF` (N=22) peaks at 833 MB at 1 thread, ~1.6 GB
at 3, ~4.0 GB at 32.

| Threads | Fact 22 | M8 re-measurement | n |
| --- | --- | --- | --- |
| 1 | 833 MB | **833.2 MiB**, sd 0.1 | 4 |
| 3 | ~1.6 GB | 1679 MiB | 1 |
| 32 | ~4.0 GB | **4121.7 MiB**, sd 141.0 | 5 |

Fact 22 is confirmed, and §10.1 refines it.

---

## 4. The decoder in isolation

660 steady-state decodes (`idx > 0`), across **six real corpora** — three focus-bracket stacks and
three dark-frame folders from the same body, chosen because they are real sensor data with the same
pixel count and 16% smaller files. That size difference is the lever arm that separates "constant
per decode" from "tracks file size" without leaving real data.

### 4.1 Scratch is proportional to compressed file size (MEASURED)

x is file size in MiB, y is `scratch_commit` in MiB, so the slope is dimensionless.

| Threads | model | intercept a (MiB) | slope b | resid sd | R² |
| --- | --- | --- | --- | --- | --- |
| 1 | constant | 36.962 ± 0.167 | — | 2.477 | 0.000 |
| 1 | proportional | — | 1.0283 ± 0.0010 | 0.523 | **0.955** |
| 1 | **affine** | **0.685 ± 0.530** | **1.0093 ± 0.0147** | 0.523 | **0.956** |
| 4 | affine | 5.787 ± 0.912 | 0.9525 ± 0.0253 | 0.899 | 0.867 |
| 32 | affine | 19.829 ± 3.258 | 0.6871 ± 0.0905 | 3.212 | 0.209 |

At one thread the answer is unambiguous: **the intercept is consistent with zero and the slope is
consistent with 1**. The decoder's private commit above its output buffer is, to within 1 MiB, the
size of the compressed file. A constant model has R² = 0 against the same data.

Pooling all three pools and adding a thread term:

```
scratch_commit(MiB) = 5.24 ± 1.16  +  0.883 ± 0.032 × file(MiB)  +  1.512 ± 0.037 × log2(threads)
R² = 0.784   (without the thread term, R² = 0.248)
```

**Leave-one-corpus-out validation** (fit without a corpus, predict it): at 1 and 4 threads, mean
error −1.7% to +2.0%, max 10.3%. At 32 threads it degrades badly (coffee-bean mean +8.7%, max
26.8%) — the constant term is genuinely pool-dependent and the fit is not portable there.

**The decoder is internally parallel, and this is MEASURED not assumed**: a single isolated decode
takes **240.4 ms at `RAYON_NUM_THREADS=1`, 85.3 ms at 4, and 53.6 ms at 32** (n=220 each). A 4.5×
speedup from an environment variable the caller sets is decisive without reading a line of
`rawler`. Its scratch grows with that pool: 36.96 → 40.02 → 44.53 MiB commit.

### 4.2 The concurrency sweep — the constrained fit M2 could not do (MEASURED)

`peak = a + b·k` over **17 swept values of k** (0…32), fresh process per point, kernel-maintained
peaks. This is the measurement M2 declined to fit to two points.

| Corpus | Threads | mean file | commit slope b | b − frame_bytes | a | R² |
| --- | --- | --- | --- | --- | --- | --- |
| coffee-bean | 1 | 37.79 MiB | 109.36 MiB | **39.36 MiB** | +9.64 MiB | 0.999984 |
| coffee-bean | 32 | 37.79 MiB | 109.61 MiB | **39.61 MiB** | +34.91 MiB | 0.999874 |
| dark-ISO50 | 1 | 31.59 MiB | 102.34 MiB | **32.34 MiB** | +9.10 MiB | 0.999995 |
| dark-ISO50 | 32 | 31.59 MiB | 102.88 MiB | **32.88 MiB** | +33.41 MiB | 0.999901 |

**Every intercept is positive.** M2's warning is answered: a swept fit is physical where a two-point
fit was not.

The scratch difference between the two corpora is **7.02 MiB** (39.36 − 32.34); their file-size
difference is **6.20 MiB**. Ratio **1.13**, against the isolated slope of 1.009 ± 0.015 — the same
conclusion reached by a completely different route on different data. **Scratch tracks file size.**

Working set behaves differently and the difference is informative: 78.2 MiB/decode at 1 thread but
**144.8 MiB/decode at 32**. The ARW appears both as a private copy and as file-backed pages, and
how many of those pages stay resident is a function of the pool. Private commit is stable across
pools; working set is not.

---

## 5. Scratch versus allocator retention — separated (MEASURED)

These are different things with different consequences, and the brief was right to demand they be
told apart. The discriminator: decode N frames **sequentially, one ever live**, in one process.
True scratch cannot accumulate there; anything that grows is the allocator holding on.

138 sequential decodes per condition, coffee-bean (105) and 119MSDCF (33):

| Condition | resting commit above decode 1 | kernel peak commit |
| --- | --- | --- |
| coffee-bean, 1 thread | +0.01 MiB at decode 10, **+0.01 at decode 100** | 118.58 → **120.39 MiB, then +0.000 from decode 40 to 104** |
| coffee-bean, 32 threads | +1.45 MiB at decode 10, **+1.92 at decode 100** | 130.86 → **135.01 MiB, then +0.000 from decode 40 to 104** |
| 119MSDCF, 1 thread | +0.02 at decode 10, **+0.01 at decode 32** | 117.49 → 117.95 MiB |
| 119MSDCF, 32 threads | +1.76 at decode 10, **+1.86 at decode 32** | 130.52 → 132.96 MiB |

**It plateaus, and the plateau is exact.** Retention rises during roughly the first 40 decodes and
then stops: on both coffee-bean conditions the kernel peak commit over decodes 40 through 104 has a
range of **0.000 MiB** — not "approximately flat", identical. Total lifetime growth is +1.81 MiB at
one thread and **+4.15 MiB at 32**.

The remaining movement in resting commit is an **oscillation, not a trend**. At 32 threads the 51
steps larger than 0.5 MiB are matched ±8 to ±9 MiB pairs — a buffer freed and re-taken — and over
104 decodes **they sum to +0.80 MiB**. A single excursion reaches +10.87 MiB and comes straight back.

An OLS slope over the raw series reports 73 KB/decode at 32 threads, which is an artefact of the
early rise plus that oscillation; over the plateau region growth is **zero to the resolution of the
counter**.

**The separation, stated plainly:**

| | True decoder scratch | Allocator retention |
| --- | --- | --- |
| Scales with concurrency? | **Yes.** Linear in k, R² = 0.99998 over k = 0…32 | **No.** Measured with exactly one decode live |
| Scales with number of decodes? | No | Rises, then **plateaus** by ~40 decodes |
| Size | **39.4 MiB per concurrent decode** | **≈2 MiB resting, ≤4.15 MiB peak, per process, total** |
| Consequence for the planner | Multiplies by the worker count | A one-off, smaller than the measurement noise |

Retention is therefore real, bounded, and **not** a term the worker-sizing model needs. This is the
part of M2's hypothesis ("plus possibly allocator retention") that can now be dismissed with a
number rather than a shrug.

---

## 6. The real stacker

82 fitted runs across `109MSDCF` (22 frames), `coffee-bean` (105) and the small-N floor sweep;
**14 thread counts** from 1 to 32 and **12 frame counts** from 1 to 105; 4 repeats at 8 conditions.
`119MSDCF` was held out entirely (§7).

### 6.1 The floor sweep, and the term nobody was looking for (MEASURED)

One thread, tiny N. `live` = 1 throughout, so anything above one worker's buffers is not
per-worker. Three repeats each; the spread is 0.06 MiB.

| chunks | ⌈log₂ chunks⌉ | peak working set | step |
| --- | --- | --- | --- |
| 1 | 0 | **320.2 MiB** | — |
| 2 | 1 | 430.3 MiB | **+110.1** |
| 3 | 2 | 540.4 MiB | **+110.1** |
| 4 | 2 | 540.3 MiB | −0.0 |
| 6 | 3 | 650.4 MiB | **+110.0** |
| 8 | 3 | 650.4 MiB | +0.1 |

Two results, both exact:

1. **The process floor is 14.4 MiB.** 320.2 − 305.79 = 14.4. One worker's buffers account for
   95.5% of the whole process at N=1. The runtime, the prologue frame and the TIFF epilogue
   together cost 14 MiB.
2. **The steps are one `Selection` each, and they land on ⌈log₂ chunks⌉.** `px × 14` = 110.04 MiB;
   the measured step is 110.0–110.1 MiB, agreeing to **0.1%**. This is rayon's binary reduce
   holding one partial alive per level of the tree. It is **not decoder scratch** — it is the
   stacker's own `reduce_with`, and at the 18 chunks a 105-frame stack plans it is **550 MiB**.

**This term is absent from `per_worker_bytes` entirely.** It is larger than the scratch term the
measurement was commissioned to find.

That the floor is only 14.4 MiB — when an isolated decode costs 74.8 MiB of working set — is
explained by self-test S3: `Selection::new` and `FocusField::new` allocate pages that are not
touched until the fold. At one live worker the peak is reached during the **fold**, when the
decoder's scratch is already gone, not during the decode. Scratch only becomes resident when
enough workers overlap that some are decoding while others fold. **ARGUED** from S3 plus the floor
data; the phase-resolved confirmation inside the stacker was not done (§9).

### 6.2 Run-to-run spread (MEASURED) — the uncertainty M2 had no way to state

Peak RSS is scheduling-dependent. Four repeats per condition:

| Stack | N | threads | n | mean | sd | rel |
| --- | --- | --- | --- | --- | --- | --- |
| 109MSDCF | 22 | 1 | 4 | 833.2 MiB | 0.1 | **0.01%** |
| 109MSDCF | 22 | 6 | 4 | 2333.3 | 35.8 | 1.54% |
| 109MSDCF | 22 | 32 | 4 | 4121.7 | 141.0 | 3.42% |
| coffee-bean | 20 | 32 | 4 | 5065.7 | 117.9 | 2.33% |
| coffee-bean | 40 | 32 | 4 | 7360.8 | 356.6 | **4.85%** |
| coffee-bean | 60 | 32 | 4 | 7621.2 | 74.9 | 0.98% |
| coffee-bean | 105 | 8 | 4 | 3858.4 | 279.6 | **7.25%** |
| coffee-bean | 105 | 32 | 4 | 6900.6 | 9.5 | 0.14% |

Pooled 1.47%, worst 7.25%. **No model of this quantity can be expected to do better than ~7%**, and
any reported error below that is not resolving anything.

### 6.3 The fit (MEASURED)

Excluded from the headline fit: 8 of 82 runs where `chunk_len == 1` with many chunks. A worker that
decodes exactly one frame is only briefly at its own high-water mark, so the concurrency window
never fills — MEASURED, §10.2. `live` = min(chunks, `RAYON_NUM_THREADS`).

Target **peak working set**, n = 74:

| model | R² | resid sd | a (MiB) | b (MiB) | c (MiB) |
| --- | --- | --- | --- | --- | --- |
| a + b·live | 0.97755 | 385.9 | 356.5 ± 69.2 | 356.6 ± 6.4 | — |
| a + b·live + c·chunks | 0.98954 | 265.2 | **−136.8 ± 72.5** | 312.4 ± 6.6 | 67.9 ± 7.5 |
| a + b·live + c·threads | 0.97931 | 373.0 | 336.1 ± 67.5 | 389.3 ± 14.7 | −19.7 ± 8.0 |
| a + b·live + c·⌈log₂ chunks⌉ | 0.98639 | 302.6 | **−293.6 ± 110.1** | 327.9 ± 6.5 | 228.0 ± 33.6 |
| **a + b·live + (px×14)·⌈log₂ chunks⌉** | **0.98402** | **325.5** | **+42.8 ± 58.4** | **342.8 ± 5.4** | pinned at 110.04 |

**Two of the free-form models produce a negative intercept.** M2 refused to publish a model with a
negative intercept and was right to; the same refusal applies here even though these fits have 74
points rather than 2. The adopted model pins the reduce-tree coefficient to the value **measured
independently in §6.1 and derived independently from geometry**, and its intercept is positive.

Robustness check: pinning the floor *as well*, at the directly measured 14.4 MiB, leaves one free
parameter and gives **b = 344.8 ± 3.5 MiB**, R² = 0.98397 — the same answer with tighter
conditioning. The two-parameter form is quoted as the headline because it does not assume the
N=1 floor generalises.

**Adopted:**

```
peak_ws  ≈  a  +  live × (buffers + scratch)  +  ⌈log2 chunks⌉ × Selection
         =  42.8  +  live × (305.79 + 37.0)   +  ⌈log2 chunks⌉ × 110.04     MiB
```

The fitted intercept, 42.8 ± 58.4 MiB, is consistent within 0.5σ with the 14.4 MiB floor measured
directly in §6.1 — the two independent routes to the floor agree, which is the check that matters;
neither is precise. The pinned-floor variant (a ≡ 14.4, b = 344.8 ± 3.5) is the tighter estimator of
b and is quoted as the robustness check, not the headline.

| | per-worker b | excess over the 305.79 MiB buffer model | ratio |
| --- | --- | --- | --- |
| **peak working set** | **342.8 ± 5.4 MiB** | **+37.0 ± 5.4 MiB** | **1.121×** |
| peak private commit | 313.5 ± 6.6 MiB | +7.7 ± 6.6 MiB | 1.025× |

**The private-commit excess is consistent with zero at 1.2σ.** The buffer model is very nearly right
about *private commit per worker*; it is working set that it under-counts, and the difference
between the two — 29.3 MiB, about 0.8 × the file size — is file-backed pages, matching the isolated
measurement where working set exceeded commit by 0.94 × the file size (§4.2).

The in-situ working-set excess (37.0 MiB) is about **half** the isolated per-decode working-set
scratch (74.8 MiB at 32 threads). Read literally that says roughly half the live workers are inside
a decode at the peak instant — **ARGUED**, consistent, not independently confirmed.

### 6.4 What a no-intercept `peak / workers` says now

M2's method, applied to the repeated runs:

| Stack | live | peak_ws / live | range over 5 repeats |
| --- | --- | --- | --- |
| 109MSDCF N=22 | 11 | 355.5 – 381.5 MiB | 372.8 – 400.0 decimal MB |
| coffee-bean N=105 | 18 | 378.7 – 384.0 MiB | 397.1 – 402.6 decimal MB |

M2's 364 and 379 MiB sit inside these ranges. The quantity was not wrong; it was **not a per-worker
constant**, because it silently absorbed the floor and the whole reduce tree.

---

## 7. Out-of-sample validation (MEASURED)

`119MSDCF` — 33 frames, f/5.6, ISO 50, a different aperture, ISO and frame count — was **never in
any fit**. Predictions come from the §6.3 coefficients, unchanged.

| threads | chunks | live | rep | predicted | observed | error |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 17 | 2 | 1 | 1278.5 MiB | 1430.2 MiB | −10.61% |
| 2 | 17 | 2 | 2 | 1278.5 | 1421.2 | −10.04% |
| 5 | 17 | 5 | 1 | 2306.8 | 2795.2 | −17.47% |
| 5 | 17 | 5 | 2 | 2306.8 | 2326.7 | −0.85% |
| 9 | 17 | 9 | 1 | 3677.9 | 3443.6 | +6.80% |
| 9 | 17 | 9 | 2 | 3677.9 | 3396.1 | +8.30% |
| 17 | 17 | 17 | 1 | 6420.0 | 5844.8 | +9.84% |
| 32 | 17 | 17 | 1 | 6420.0 | 5941.1 | +8.06% |
| 17 | 17 | 17 | 2 | 6420.0 | 5914.6 | +8.54% |
| 32 | 17 | 17 | 2 | 6420.0 | 6209.6 | +3.39% |

**Mean |error| 8.39%, max 17.47%, bias +0.60%.** The two worst rows are the same condition measured
twice, and they differ from each other by 20% — that is the scheduling spread of §6.2, not model
error.

The plain `a + b·live` model, fitted on identical data, gives **11.97% mean / 25.21% max** on the
same held-out runs. Pinning the reduce term to its independently measured value makes the model
**better out of sample**, not merely better fitting.

Private commit, same holdout: **4.71% mean, 22.10% max, bias −2.02%**.

**End-to-end check on the shipped binary** (MEASURED, after the code change in §8.2), real 105-frame
stack, `RAYON_NUM_THREADS=32`, run twice on separate occasions:

| `--memory-model` | chunks | printed prediction | actual peak ws | error |
| --- | --- | --- | --- | --- |
| `buffers` (default) | 18 | 7.06 decimal GB | 6909 MiB = 7.24 GB (earlier run 6902 MiB) | **−2.5%** |
| `m8` | 15 | 5.87 decimal GB | 5762 MiB = 6.04 GB (earlier run 5768 MiB) | **−2.8%** |

The two occasions differ by 0.1%, so this check is reproducible, and both errors are well inside the
8.4% out-of-sample band. Note the sign: the model **under**-predicts here by ~2.5%, whereas on the
holdout its bias was +0.6%. At 18 chunks with `chunk_len` 6 the overlap is fuller than anything in
the fit set, and the model does not have a term for that.

---

## 8. The recommendation (DERIVED — for the owner to accept or reject)

`MEMORY_BUDGET_BYTES` is **unchanged at 6 GiB**, as instructed. The question is only how many
workers that budget honestly buys.

Solving `predicted_peak(W) ≤ 6144 MiB` with the §6.3 model gives **W = 16** (5968 MiB). At W = 17
the model predicts **6421 MiB**, over budget. The cap is **16 at b = 342.8 and still 16 at
b = 342.8 ± 5.4**.

| N | now: workers / chunks / len | M8: workers / chunks / len | predicted peak now | predicted peak M8 |
| --- | --- | --- | --- | --- |
| 22 | 20 / **11** / 2 | 16 / **11** / 2 | 4253 MiB | 4253 MiB |
| 33 | 20 / 17 / 2 | 16 / 11 / 3 | 6420 | 4253 |
| 105 | 20 / **18** / 6 | 16 / **15** / 7 | 6763 | **5624** |
| 220 | 20 / **20** / 11 | 16 / **16** / 14 | 7448 | **5967** |

- **N=22 does not change.** 22 frames over 16 workers is `chunk_len = 2`, giving 11 chunks — the
  same 11 the current model produces. The stack M2 measured is unaffected.
- **N=105 drops 18 → 15 chunks.** MEASURED end-to-end: actual peak falls from 6909 MiB to
  **5762 MiB**, a 16.6% reduction, landing under the 6 GiB budget for the first time.
- **N=220 drops 20 → 16 chunks**, predicted 5967 MiB.
- The M8 plan never asks for *more* workers than the current one. Adopting it cannot increase peak
  memory.

Cost: at N=105 the M8 plan does the same work with 15 workers instead of 18. On a 32-core machine
that is spare capacity, not lost throughput — MEASURED wall clock **3.826 s** (18 chunks) vs
**3.935 s** (15 chunks), a 2.8% difference against a 2–5% run-to-run spread. Summed decode time
across workers actually *fell*, 31.0 s → 26.9 s, so the wider plan was paying for contention.
**ARGUED** from two runs; not a throughput study.

### 8.1 What is *not* recommended

- **Lowering `MEMORY_BUDGET_BYTES`** — ruled out by the owner and the measurement agrees: it treats
  the symptom and makes the model less truthful.
- **Adding a flat fudge factor to `per_worker_bytes`** — it would not represent the reduce tree,
  which is O(log chunks) and not per-worker at all, and it would over-charge small stacks.

### 8.2 What was actually changed in `crates/**` (additive, default unchanged)

- `MemoryModel { Buffers (default), M8 }` and a `--memory-model` flag. **`Buffers` is the default
  and produces byte-identical plans to before**, asserted by
  `the_default_memory_model_is_unchanged_by_m8`.
- `PROCESS_FLOOR_BYTES` (15,099,494) and `DECODER_SCRATCH_BYTES` (38,797,312), both carrying the
  measurement they came from in a comment.
- `reduce_levels()` and `m8_peak_bytes()`.
- `describe()` now prints the honest prediction **on every run, under both models**, and labels the
  buffer sum as a lower bound rather than as the answer.

Tests: 58 → **65**, all green, plus `cargo fmt --all -- --check` and
`cargo clippy --workspace --all-targets -- -D warnings`.

**Negative-controlled** (`experiments/m8-scratch/negative-control.ps1`, MEASURED): six deliberate
regressions — zeroing `DECODER_SCRATCH_BYTES`, inflating `PROCESS_FLOOR_BYTES` 10×, an off-by-one
in `reduce_levels`, swapping the two models in both directions, and softening the `describe()`
lower-bound wording — each made the specific test meant to catch it go red, and the suite returned
to 65 green after restoring from a byte copy. Restore was from a copy, never `git checkout --`, and
every write bumped the file mtime so cargo could not skip the rebuild.

---

## 9. What is still not verified

1. **Pixel-count proportionality is untestable on this corpus.** `active_px` is 32,966,016 on every
   file available — one body, one geometry. A model that is constant-per-decode and a model that is
   proportional to pixel count are **indistinguishable here**, and §4.1's finding that scratch tracks
   *file size* does not settle which of the other two also contributes. **UNVERIFIED.** Resolving it
   needs a second camera or a crop mode.
2. **The `conc` harness is not the stacker.** It spawns std threads that each call
   `strehl_raw::decode`; the stacker nests decode inside rayon workers, and §4.1 showed decode is
   itself rayon-parallel. The two are not identical dynamics. The §6 stacker fit is the number to
   quote for the planner; the §4 sweep is the number to quote for the decoder.
3. **The claim that the peak is reached during the fold at low concurrency is ARGUED**, from
   self-test S3 plus the floor sweep. A phase-resolved sampler inside the stacker would settle it.
   It would also explain the model's one systematic bias: at `live = 1` it over-predicts by 5.7% to
   11.6%. That is the safe direction for a budget, and it is asserted as a known limitation by
   `the_m8_model_over_predicts_at_a_single_live_worker`, but it is not accuracy.
4. **The 16-worker cap is derived on one machine.** 32 logical processors, 64 GB, Windows. The
   floor, the buffer sizes and the reduce tree are machine-independent; the scratch term embeds this
   machine's allocator and file cache. **UNVERIFIED elsewhere.**
5. **Whether 37.0 MiB/worker is "decoder scratch" or something else the decode does** cannot be
   settled from outside the decoder, and `rawler`'s source is do-not-read. What is measured is the
   marginal cost of a live worker above its own buffers. That it agrees with the independently
   measured isolated scratch is strong, not conclusive.
6. **No N > 105 was measured on real files.** N=220 in §8 is a model extrapolation, explicitly
   labelled DERIVED. M2 reached N=220 with a synthetic corpus; this report does not, and does not
   quote a synthetic number anywhere.
7. **Only working set was optimised against.** If the real constraint is commit rather than
   residency, the honest per-worker figure is 313.5 ± 6.6 MiB and the cap would be higher.

---

## 10. Contradictions with SYNTHESIS, named

### 10.1 Fact 22 is refined, not refuted

Fact 22 says peak RSS tracks live concurrency, `min(chunks, rayon pool)`, not the plan. The
direction is confirmed (§3.5), but the formula is not exact:

- **In 8 of 108 runs the binary's own `peak_live` counter exceeded `min(chunks, threads)`** — by up
  to +3 (`coffee-bean` N=105 at 10 threads reported **13** concurrent decodes). Never below, always
  above. **MEASURED.**
- Cause, **ARGUED**: `strehl_raw::decode` is internally rayon-parallel (MEASURED, §4.1: 240 ms → 54
  ms from `RAYON_NUM_THREADS` alone). A worker blocked inside a nested rayon join can steal another
  chunk and begin a second decode, so decodes in flight are not bounded by the pool size.
- Fact 22 also does not mention that **the decoder's own pool costs memory**: scratch rises 36.96 →
  44.53 MiB commit from 1 to 32 threads, +1.51 MiB per doubling. Pinning the pool changes not only
  how many decodes overlap but how much each one costs.
- Fact 22's own summary — "**~379 MB measured** against **321 MB modelled**" — inherits M2's units
  mix (§1.1): 379 is MiB, 321 is decimal MB. It is also `peak_ws / live`, which §6.4 shows is not a
  per-worker constant at all: at the very condition fact 22 quotes it ranges over 378.7–384.0 MiB
  across five repeats, and at N=22 over 355.5–381.5 MiB, because it silently absorbs the process
  floor and every level of the reduce tree. The per-worker constant is **342.8 ± 5.4 MiB** (§6.3).
  **VERIFIED.**

### 10.2 SYNTHESIS §3.2.1 assertion 1 is FALSE **at its own specified pair**

§3.2.1 specifies the ratchet as three assertions and calls the first "the real test":

> With `RAYON_NUM_THREADS` **pinned**, peak RSS at `N = 4 × pool` must not exceed peak RSS at
> `N = 2 × pool` by more than a small tolerance.

That is a precise, testable claim, so M8 tested exactly it — the assertion's own pair, not a
convenient one. Two pools, two repeats each, `RAYON_NUM_THREADS` pinned:

| pool | N = 2×pool | N = 4×pool | **ratio** | chunks | chunk_len |
| --- | --- | --- | --- | --- | --- |
| 4 | 1598.9 MiB | 1912.1 MiB | **1.196** | 8 → 16 | 1 → 1 |
| 8 | 2832.6 MiB | 3297.3 MiB | **1.164** | 16 → 16 | 1 → 2 |

**+16% to +20% is not "a small tolerance" for a gate whose whole purpose is to catch a regression.**
As written, assertion 1 fails on unregressed code. It would have to be given a ≥20% tolerance to go
green today, at which point it can no longer detect the kind of regression it exists to detect.
**MEASURED.**

Pushing further along the same axis makes the trend unmistakable:

| threads | N | peak ws | ratio vs baseline | chunks | chunk_len |
| --- | --- | --- | --- | --- | --- |
| 4 | 8 | 1598.9 MiB | — | 8 | 1 |
| 4 | 12 | 1790.5 | 1.120 | 12 | 1 |
| 4 | 16 | 1912.1 | 1.196 | 16 | 1 |
| 4 | 32 | 2392.7 | **1.496** | 16 | 2 |
| 8 | 16 | 2832.6 | — | 16 | 1 |
| 8 | 32 | 3297.3 | 1.164 | 16 | 2 |
| 8 | 64 | 3611.9 | **1.275** | 16 | 4 |

Two mechanisms, both measured, and neither is a leak:

1. **`chunks` grows with N** until it saturates at `workers`, and the reduce tree costs
   110.04 MiB per level (§6.1). That is O(log N) growth the ratchet does not account for.
2. **`chunk_len` 1 → 2 fills the concurrency window.** At `chunks` = 16 and threads = 4, N=16
   (`chunk_len` 1) peaks at 1912 MiB and N=32 (`chunk_len` 2) at 2393 MiB — same chunks, same pool,
   **+25%**. A worker that decodes one frame is at its high-water mark only briefly, so the pool
   never actually fills. This is the same effect that made 8 of 82 fit runs unusable (§6.3).

**The ratchet's intent does hold; only its formula fails.** Once `chunks` has saturated *and*
`chunk_len ≥ 2`, growth in N is nearly flat: at 32 threads with `chunks` = 20 on both sides,
N=40 → 7260.9 MiB and N=60 → 7614.9 MiB, a ratio of **1.049** for a 50% increase in frames. The
system is O(workers), not O(N).

**Proposed restatement**, so the gate tests the property rather than an artefact of it:

> With `RAYON_NUM_THREADS` pinned, compare two N values that produce the **same `chunks` and both
> have `chunk_len ≥ 2`**. Peak RSS must not grow by more than a small tolerance. Record `chunks` and
> `chunk_len` alongside the number; if they differ between the two sides, the comparison is invalid
> and the gate must fail loudly rather than pass.

At 32 threads, N=40 vs N=60 satisfies this and gives 1.049 — a defensible tolerance.

### 10.3 Assertion 2 is M8's stated target, and `peak_rss / live_workers` is the wrong estimator

§3.2.1 assertion 2 asks for `peak_rss / live_workers` at a pinned thread count, ratcheted as its own
number, and says "it is the honest target of M8". M8's answer is that **the ratio is not a
constant**, because it silently absorbs the process floor and the entire reduce tree (§6.4): at the
same pinned condition it ranges over 355.5–384.0 MiB depending only on how many reduce levels the
plan happens to have. Ratcheting it would be ratcheting `chunks` as much as per-worker cost.

The quantity assertion 2 actually wants is the **fitted slope**, **342.8 ± 5.4 MiB per live worker**
(§6.3), which is what regresses when someone adds a buffer and does not move when `chunks` changes.
It is now available to CI as `m8_peak_bytes()` and is asserted by
`the_m8_model_reproduces_the_measured_full_overlap_peaks`. **ARGUED** — the restatement is a
recommendation for the owner; M8 did not edit SYNTHESIS.

### 10.4 The GiB-vs-decimal unit decision is load-bearing on real data, not just on the synthetic run

§3.2.1 decided that `8 GB` means **8 GiB = 8192 MiB**, and justified it on the N=220 synthetic run
(7616 MiB: fails as decimal, passes as GiB with 576 MiB of margin). M8 supplies the **real-file**
analogue, which the decision did not have:

| Real run (MEASURED, 32 threads, n=5) | peak ws | vs 8 GiB = 8192 MiB | vs 8 decimal GB = 7629 MiB |
| --- | --- | --- | --- |
| `coffee-bean`, N=60 | **7681 MiB** (max of 5) | passes, 511 MiB margin (6.2%) | **fails** |
| `coffee-bean`, N=40 | 7665 MiB (max of 5) | passes, 527 MiB margin | **fails** |
| `coffee-bean`, N=105 | 6911 MiB (max of 5) | passes, 1281 MiB margin | passes |

So the unit choice flips the verdict on a **60-frame stack of the owner's own files**, not only on a
synthetic corpus. The decision as taken is what keeps these green. **VERIFIED** against the
§3.2.1 constant.

It also shows how little headroom the current plan leaves: 6.2% at N=60, which is **inside** the
4.85% run-to-run spread measured at N=40 (§6.2) plus its own. The M8 plan predicts 5967 MiB at
N=220, a 27% margin. Reported as context for §8, not acted on.

---

## 11. Reproducing it

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cd C:\dev\blog\death-of-software\projects\strehl\experiments\m8-scratch
cargo build --release

# controls first; nothing downstream of a failed control is worth reading
.\run-m8.ps1 -Stage selftest         # §3.1  13 harness controls              (~30 s)
.\run-m8.ps1 -Stage null             # §3.2  real-data null + §3.3 positive   (~1 min)
.\run-m8.ps1 -Stage crossinstrument  # §3.4  poller vs the child's counters   (~1 min)

# the decoder as a black box
.\run-m8.ps1 -Stage single           # §4.1  660 isolated decodes, 6 corpora  (~6 min)
.\run-m8.ps1 -Stage seq              # §5    retention, one decode ever live  (~3 min)
.\run-m8.ps1 -Stage conc             # §4.2  the swept fit, k = 0..32         (~12 min)

# the real stacker, RAYON_NUM_THREADS pinned on every run
.\run-m8.ps1 -Stage floor            # §6.1  the floor and the reduce tree    (~1 min)
.\run-m8.ps1 -Stage stack            # §6.3  threads swept, then N swept      (~4 min)
.\run-m8.ps1 -Stage reps             # §6.2  4 repeats, the uncertainty bar   (~5 min)
.\run-m8.ps1 -Stage shape            # §10.2 SYNTHESIS 3.2.1 assertion 1      (~2 min)
.\run-m8.ps1 -Stage holdout          # §7    119MSDCF, never fitted           (~1 min)

python m8_analyse.py all > data\analysis.txt    # every number in §1 and §4-§8

# §8.2 the negative control on the shipped tests (~4 min)
.\negative-control.ps1

# §8.2 gates
cd ..\..
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace                          # 65 pass

# §7 end-to-end, both models on the real 105-frame stack
$env:RAYON_NUM_THREADS = '32'
.\target\release\strehl.exe stack C:\dev\macro\test\coffee-bean -o out.tif
.\target\release\strehl.exe stack C:\dev\macro\test\coffee-bean -o out.tif --memory-model m8
```

`data/*.csv` are committed, so `m8_analyse.py` reproduces every fit without re-measuring.

### 11.1 Read-only verification (VERIFIED)

`AGENTS.md` makes `C:\dev\macro` and `D:\macro-dark-frames` strictly read-only. Checked after the
run, against a cutoff before this measurement began:

```powershell
$start = Get-Date '2026-08-22 17:00:00'
foreach ($root in 'C:\dev\macro','D:\macro-dark-frames') {
  $f = Get-ChildItem $root -Recurse -Force -File
  "{0}: files={1}  written/created after cutoff = {2}" -f $root, $f.Count,
    ($f | Where-Object { $_.LastWriteTime -gt $start -or $_.CreationTime -gt $start }).Count
}
```

Result: `C:\dev\macro` 18,530 files, **0** written or created after the cutoff;
`D:\macro-dark-frames` 242 files, **0**. `D:\macro-dark-frames` was populated at 14:46–14:50, before
this session's first artifact at 17:51, and contains 242 `.ARW` and nothing else. Only
`LastAccessTime` moved, which is what reading does. **Nothing was written to either corpus.**

---

## 12. How to quote this result

> Decoder scratch is **39.36 ± 0.11 MiB of private commit per concurrent decode** on 37.8 MiB ARWs
> and **32.34 ± 0.06 MiB** on 31.6 MiB ARWs — i.e. **proportional to compressed file size**
> (slope 1.009 ± 0.015, intercept consistent with zero), plus 1.51 ± 0.04 MiB
> per doubling of the decoder's own thread pool (MEASURED, M8, real ARWs from six corpora, k swept
> 0…32, R² = 0.99998). Allocator retention is a **separate and bounded** quantity: ≈2 MiB of resting
> commit per process and ≤4.15 MiB of peak, all within the first 40 decodes, not scaling with
> concurrency (MEASURED). **In situ
> the stacker's per-worker peak working set is 342.8 ± 5.4 MiB**, which is 1.121× the 305.79 MiB
> buffer model; the missing 37.0 ± 5.4 MiB is scratch and file-backed pages. Two further terms the
> buffer model omits entirely are a **14.4 MiB process floor** and **110.04 MiB × ⌈log₂ chunks⌉ of
> `Selection` partials in rayon's reduce tree** — the latter is 550 MiB at 18 chunks and is not
> scratch at all. Out-of-sample error on a stack never fitted: **8.4% mean, 17.5% max**, against a
> run-to-run spread of up to 7.3%. Whether scratch is additionally pixel-proportional is
> **UNVERIFIED**: one body, one geometry.

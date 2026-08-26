# What the shipping default merge costs, end to end

**BUILD-SPEED**, measured 2026-08-26 on the reference rig.

The README's headline number — 299 frames of 33 MP ARW in 51.6 s — was measured
on `--merge estimator`. That is not the default any more. The default is
`--merge pyramid`, and its end-to-end time had never been measured. This report
measures it.

Everything below is MEASURED unless the line says ARGUED. Every wall-clock
figure carries the machine's busy fraction beside it, because the single largest
term in every timing on this box turned out to be *other agents*, not the
stacker.

---

## 1. Provenance

| | |
|---|---|
| commit | `b9b6921edc7ecec95443509b0778b4ed48404871` |
| tree | `git archive b9b6921e \| tar -x -C C:\dev\strehl-out\BUILD-SPEED\tree-b9b6921e` |
| build | `cargo build --release -p strehl-cli` with `CARGO_TARGET_DIR=C:\dev\strehl-out\BUILD-SPEED\cargo-target` (cargo/rustc 1.98.0; `Compiling strehl-cli` observed, per rule 33) |
| binary | `C:\dev\strehl-out\BUILD-SPEED\cargo-target\release\strehl.exe`, 9,385,984 bytes |
| binary sha256 | `88782BBC9F55F684E043FAC5CF0C44C1FEFF6B2B25727A9BA9E19D26E3722916` |
| host | AMD Ryzen 9 9950X3D, 16C/32T, 64 GB |
| workload | `D:\personal\macro\bee-3-cpl` — 299 Sony ARW, 33 MP, **11,308,236,800 bytes** (11,308.2 MB) |
| environment | `STREHL_CACHE_DIR=C:\dev\strehl-out\BUILD-SPEED\warpcache`; `STREHL_ALIGN`, `STREHL_WARPMAP`, `STREHL_MERGE`, `STREHL_PHOTOMETRIC`, `STREHL_FIX_CA`, `STREHL_PYRAMID_WORKERS`, `RAYON_NUM_THREADS` all **unset** |

`STREHL_CACHE_DIR` is set for isolation only. Since M97 the warp sidecar lives
under `cache_root()` rather than in the capture directory, so pointing it at my
own directory keeps a dozen concurrent agents from sharing (or poisoning) my
registration cache. It does not change the picture: §5 shows the cold run, which
*solved* the registration, and the warm runs, which *loaded* it, produce
byte-identical output.

The timed command is the one a user gets, with no merge flag:

```
strehl stack D:\personal\macro\bee-3-cpl --out <PATH> --srgb --auto-exposure
```

`--srgb --auto-exposure` matches the command the 51.6 s figure was taken with
(`experiments/ORCH-drift-check/retime.py`) so the two are comparable. No
`--merge` and no `--pyramid-gate`, so the backend and the noise gate are whatever
the binary compiles in: the binary reports `merge backend : pyramid` and
`noise gate : 2.00 x the modelled band-noise power`.

---

## 2. The headline

**299 frames, full resolution, default path, warm, best of 3** — the same
methodology as the 51.6 s figure (warm cache, minimum of three).

| condition | best of 3 | throughput | per frame | peak WS |
|---|---|---|---|---|
| box **60–80 % busy** | **116.88 s** | 96.8 MB/s | 0.3909 s | 5.71 GB |
| box **99–100 % busy** | **233.91 s** | 48.3 MB/s | 0.7823 s | 5.69 GB |
| **cold** (empty warp cache, 99 % busy) | **327.42 s** | 34.5 MB/s | 1.0951 s | 9.34 GB |

The cold run is a single run by construction — a cache is only cold once.
It decomposes as 73.4 s registration solve + 250.6 s fold + 1.9 s collapse and
write, and it is the only run in this report that exceeds 6 GB resident.

Two warm numbers are quoted rather than one because both were measured, on the
same binary, from the same directory, producing **the same output bytes**, and
they differ by 2.05x. Picking one and calling it "the" number would be a choice,
not a measurement. §3 is the evidence for why they differ.

### Stage breakdown

Printed by the binary itself; no instrumentation was added (`crates/` is
read-only for this agent). Best warm run, 63 % busy:

```
frames          : 299 from D:\personal\macro\bee-3-cpl (first decode 0.17 s)
alignment       : ON (sidecar), reference frame 149, 299 placed / 0 refused, 0.0 s
held-out err    : 13.353 px  resampler: CatmullRom
memory plan     : 4 workers x 1328 MB = 5.2 GB against a 6144 MB budget
folded          : 299 / 299 frames in 115.1 s (0.385 s per frame, 4 workers)
collapse+write  : 1.2 s
total           : 116.8 s
```

**The fold is 98.5 % of the run.** Decode, registration lookup, collapse and the
198 MB TIFF write together account for 1.8 s of 116.9 s. Any future work on the
default path that is not the fold is rounding error.

The pyramid backend does not print MB/s (that line belongs to the estimator
path), so throughput here is computed by the harness over the true RAW byte
count.

---

## 3. The number is dominated by machine load, and that is measured

Twelve warm 299-frame runs, two gate settings, identical inputs, byte-identical
outputs within each arm. `machine busy %` is sampled with `GetSystemTimes`
across the child's lifetime; `cpu s` is the child's own `GetProcessTimes`.

| gate | busy % | wall s | fold s | cpu s | threads | peak WS GB | MB/s |
|---|---|---|---|---|---|---|---|
| 2.00 | 63 | **116.88** | 115.1 | 509.6 | 4.36 | 5.64 | 96.8 |
| 2.00 | 60 | 125.35 | 124.0 | 560.8 | 4.47 | 5.70 | 90.2 |
| 2.00 | 80 | 141.26 | 139.4 | 579.6 | 4.10 | 5.71 | 80.1 |
| 2.00 | 99 | 233.91 | 230.8 | 863.3 | 3.69 | 5.64 | 48.3 |
| 2.00 | 100 | 238.78 | 235.3 | 829.8 | 3.48 | 5.68 | 47.4 |
| 2.00 | 99 | 240.16 | 237.3 | 874.5 | 3.64 | 5.69 | 47.1 |
| 4.50 | 90 | 165.64 | 163.0 | 681.1 | 4.11 | 5.71 | 68.3 |
| 4.50 | 93 | 193.10 | 190.8 | 730.8 | 3.78 | 5.64 | 58.6 |
| 4.50 | 93 | 209.38 | 205.3 | 790.3 | 3.77 | 5.78 | 54.0 |
| 4.50 | 98 | 229.68 | 226.5 | 895.5 | 3.90 | 5.75 | 49.2 |
| 4.50 | 98 | 230.15 | 227.0 | 887.4 | 3.86 | 5.70 | 49.1 |
| 4.50 | 98 | 231.21 | 228.1 | 904.5 | 3.91 | 5.64 | 48.9 |

`wall = -82.6 + 312.6 x busy_fraction`, R² 0.88 (n=12). The observed range is
**116.88 s at 63 % busy to 240.16 s at 99 % busy, a factor of 2.05 on identical
work.**

The child's own CPU-seconds move too — 510 to 904, a factor of 1.77 — so
**CPU-seconds are not a load-invariant measure of the work either.** A thread
that stalls on a contended memory bus still accrues CPU time. There is no
software-side quantity in this experiment that is invariant to the box's load
except the output bytes and the resident set.

Three consequences, stated plainly:

1. Every wall-clock figure in this report is an **upper bound** on what the
   default costs on an idle 9950X3D.
2. The gate 2.00 and gate 4.50 arms **cannot be ordered** by these data. Gate
   4.50's best (165.64 s at 90 % busy) is worse than gate 2.00's best (116.88 s
   at 63 % busy), but at matched saturation they are 233.91 s and 229.68 s —
   2 % apart, inside the spread. ARGUED: the noise gate does not measurably
   change fold cost.
3. Anyone re-measuring this must report the busy fraction or the number cannot
   be compared.

### An independent anchor for the idle case

`C:\dev\strehl-out\SHIP-V1\_render.log` records `bee-3-cpl` rendering in
**102.2 s** on 2026-08-26 at 04:05. That log's timer is a `Stopwatch` around
`Start-Process`/`WaitForExit` on the `strehl stack` process
(`scripts/finalpass.ps1:370-377`) — the same quantity I measure. And §5 shows my
`--pyramid-gate 4.5` output is **byte-identical** to the master that log line
describes, which pins the two to the same code path and the same worker count
(worker count changes the reduction order and therefore the bytes).

So: 102.2 s on a quiet box at 4 a.m., 165.6 s at 90 % busy, 229.7 s at 98 %
busy, for bit-identical output. ARGUED: the idle-box cost of the default path on
this workload is **near 102 s**, and the 116.88 s I could observe directly is
about 14 % above it.

---

## 4. Scaling in frame count

Ladder on the same subject with `--limit`, walked **up then down** and taking
the per-setting minimum (rule 16). Rule 16 earned its keep: N=20 read 24.00 s on
the up-sweep and 18.95 s on the down-sweep, 21 % apart. All rungs taken at
95–100 % busy, so they are internally comparable and belong to the saturated
regime.

| N | best wall s | best fold s | ceil(N/4) | fold / chunk | wall / N |
|---|---|---|---|---|---|
| 20 | 18.95 | 16.40 | 5 | 3.280 | 0.9477 |
| 40 | 35.30 | 32.30 | 10 | 3.230 | 0.8824 |
| 80 | 59.27 | 56.30 | 20 | 2.815 | 0.7408 |
| 150 | 110.45 | 107.90 | 38 | 2.839 | 0.7363 |
| 299 | 233.91 | 230.80 | 75 | 3.077 | 0.7823 |

**`wall = 1.11 s + 0.7679 s x N`, R² = 0.9976**, residuals `+2.48, +3.47, -3.28,
-5.85, +3.18` s. Largest residual is 5.85 s.

**The intercept is 1.1 s.** There is no meaningful fixed cost: no index build, no
whole-stack pass, nothing that a user pays before the first frame is folded. A
20-frame stack costs 20/299 of a 299-frame stack plus about a second.

The linear fit is real but it is not the mechanism. Fitting instead against the
**chunk length** `ceil(N/4)` gives `wall = 1.11 + 3.056 x chunks`, R² = 0.9971 —
statistically indistinguishable over one decade of N. The code says which is
true: `band_workers()` (`crates/strehl-cli/src/merge_cmd.rs:4205`) sizes the
fold pool from a **memory budget and deliberately ignores core count**, so the
pool is 4 workers wide at 33 MP regardless of the host, and the fold runs
`ceil(N/4)` sequential rounds. ARGUED: the true shape is a **staircase** — flat
within a group of four frames, stepping every fourth — and a ladder this coarse
cannot resolve the steps. The `fold / chunk` column is the per-round cost and it
is flat to ±8 % across a 15x range of N, which is what a staircase predicts.

Registration solve, measured separately (cache miss, one per rung):

| N | 20 | 40 | 80 | 150 | 299 |
|---|---|---|---|---|---|
| solve s | 3.3 | 5.8 | 13.7 | 26.0 | 73.4 |

`solve ~ N^1.144`, R² 0.99 — **superlinear**, and it is paid once per stack
because the result is cached. At 299 frames it is 73.4 s, which is 24 % of a
cold run and 0 % of every subsequent one.

### A second subject

`D:\personal\macro\119MSDCF`, 33 frames, 1,268.5 MB, default path, warm, 99–100 %
busy: 33.16 / 35.07 / 38.33 s, **best 33.16 s**, 38.3 MB/s, 1.0048 s/frame,
fold 30.5 s, peak WS 5.71 GB.

(The brief named `C:\dev\macro\test\` for this; that directory does not exist on
this machine, so a second subject from `D:\personal\macro\` was used instead.)

Per-frame cost is 1.00 s here against 0.78 s on bee-3-cpl at the same load. Both
are 33 MP. ARGUED: with `ceil(33/4) = 9` rounds for 33 frames the last round is
one frame wide and three of four workers idle through it — the staircase
penalises frame counts just above a multiple of four, and 33 is the worst case.

---

## 5. Validity controls — every timed run produced a correct master

A fast run that produced a bad picture is not fast. Controls run by
`experiments/BUILD-SPEED/validate_master.py`, which has a `--selftest` that
plants a constant image, an all-zero image and a float32 image and requires a
RED verdict on each (**ran: SELFTEST GREEN, 4/4 correct**), so it is known to be
able to fail.

**Exit codes.** All 28 harness-timed runs `rc=0`, plus 8 worker-sweep runs and 2
estimator runs timed outside the harness — 38 invocations, no non-zero exit, no
fallback, no partial write.

**Structure**, on the warm 299-frame default master:

```
shape        [4688, 7032, 3]      dtype  uint16      bytes 197,798,531
min 0   max 65535   mean 41991.6   std 19005.2
frac_zero 1.01e-07   frac_saturated 2.50e-04
not constant, not all-zero
VERDICT PASS
```

7032 x 4688, 16-bit, 3-channel, exactly the geometry the README claims.

**Degeneracy.** `std` 19005 on a 0–65535 range, 1 zero pixel in 10 million and
0.025 % saturated: neither clipped flat nor empty.

**Detail, with a flat-region control (rule 9).** Both ROIs were chosen on the
*reference* master, never on the arm under test, so the arm cannot pick its own
ground. Against `C:\dev\strehl-out\SHIP-V1\bee-3-cpl.tiff`:

| | detail ROI (1200,2400,400,400) | flat ROI (400,1200,400,400) |
|---|---|---|
| ratio mine / shipped | **0.9945** | **7.83** |

The detail statistic is in family — 0.55 % apart. The flat statistic is not:
**my default-gate render carries 7.8x the gradient energy of the shipped master
in a region that should be featureless.** Correlation over the green channel is
0.999929, mean |diff| 146.4 DN, max |diff| 17186.

**Determinism.** Independent of cache state and of machine load:

| output | sha256 (first 16) |
|---|---|
| `bee-3-cpl-cold.tif` (solved registration, 99 % busy) | `B7CE9E0D6D477501` |
| `bee-3-cpl-warm.tif` (sidecar, 99 % busy) | `B7CE9E0D6D477501` |
| `bee-3-cpl-warm2.tif` (sidecar, 63 % busy) | `B7CE9E0D6D477501` |
| `bee-3-cpl-gate45.tif` (98 % busy) | `BD5B92DDB5DFBD36` |
| `bee-3-cpl-gate45b.tif` (90 % busy) | `BD5B92DDB5DFBD36` |
| **`SHIP-V1\bee-3-cpl.tiff` (shipped master)** | **`BD5B92DDB5DFBD36`** |

Six default-gate runs produced one hash. Six gate-4.5 runs produced one hash.
The warp cache is a pure speed cache with no effect on the picture.

### Does my master match the shipped one? Not at the default. Exactly, at 4.5.

**`--pyramid-gate 4.5` reproduces `SHIP-V1\bee-3-cpl.tiff` byte for byte**
(`BD5B92DD...0B65`, 197,798,531 bytes, `diff_max_abs 0`, `corr_green 1.000000`,
all three detail ratios exactly 1). The exposure line agrees too: my run printed
`+1.53 stops (gain 2.888x)` and `_render.log` recorded `+1.53 stops (gain
2.888x)` for bee-3-cpl.

**The compiled default is `noise gate : 2.00`, and it does not.** So:

> The gallery masters were rendered at a noise gate of 4.5. The shipping default
> is 2.0. A user running the default gets a **visibly noisier flat field** than
> the pictures they were shown — 7.8x the gradient energy in a featureless
> region — while resolving the same detail.

That is the same class of gap I was sent to close on the timing side: a shipped
artifact that the default path does not reproduce. It is reported here, not
fixed here; `crates/` is read-only for this agent and the choice between "change
the default" and "change the gallery" is not mine.

---

## 6. Peak memory: O(workers), confirmed

Peak working set, single post-exit `K32GetProcessMemoryInfo` query (no polling,
so it cannot perturb the timing), fold-only runs:

| N | 20 | 40 | 80 | 150 | 299 |
|---|---|---|---|---|---|
| peak WS GB | 5.59–5.70 | 5.63–5.77 | 5.64–5.70 | 5.70 | 5.64–5.78 |

**Across a 14.9x range of frame count the peak resident set moves by 3.2 %.**
That is flat, and flat in N is the signature of O(workers). It agrees with the
binary's own plan line — `4 workers x 1328 MB = 5.2 GB against a 6144 MB budget`
— and with the architecture's claim.

The two runs that exceeded 6 GB are the two that included the **registration
solve**: 9.34 GB at N=299 and 10.47 GB at N=150. The solve is the memory-heavy
stage, it is not monotone in N, and it is skipped entirely once the sidecar
exists. ARGUED: peak memory for a repeat run of any size is ~5.7 GB; peak memory
for a first run is set by the solve and was observed up to 10.5 GB.

---

## 7. Where the time goes, and the one number that could move it

The fold is 98.5 % of the run and it runs **4 frames at a time on a 32-thread
CPU**. Sweeping `STREHL_PYRAMID_WORKERS` on a 40-frame limit, two passes in
opposite order, per-setting minimum (rule 16):

| workers | best wall s | best fold s | threads used | vs default |
|---|---|---|---|---|
| 1 | 59.02 | 57.4 | 1.21 | 0.29x |
| 2 | 29.55 | 28.2 | 2.36 | 0.58x |
| **4 (shipped default)** | **17.28** | **16.0** | **4.32** | **1.00x** |
| 8 | 13.41 | 12.1 | 7.37 | 1.29x |

Doubling workers from 1 to 2 to 4 nearly halves the time each step (2.00x,
1.71x); 4 to 8 buys 1.29x. **The shipped 4-worker cap leaves roughly 29 % on the
table on this 16-core box.**

The cap is not an oversight. `band_workers()` derives the pool from
`MEMORY_BUDGET_BYTES / per_worker_bytes` and ignores core count on purpose:
float addition is not associative, so a host-dependent worker count would make
the shipped merge produce **different bytes on different machines** and break
the byte-freeze. `STREHL_PYRAMID_WORKERS` overrides it, and outputs produced
that way are not byte-comparable with the shipped masters — which is why the
sweep above is a speed-only experiment and its outputs were not validated as
masters.

ARGUED: a memory budget that scaled with installed RAM, or an explicitly
documented "reproducible" vs "fast" mode, is worth about 1.3x on this class of
machine. Not attempted here.

---

## 8. `--merge estimator` exit code — a second observation

The README states the estimator "currently exits rc=1 out of the box". On this
build it does not. Two invocations, both at commit `b9b6921e` with binary
`88782BBC...2916`:

| command | rc | wall | output |
|---|---|---|---|
| `strehl stack D:\personal\macro\bee-3-cpl --merge estimator --out X --srgb --auto-exposure` | **0** | 320.88 s | 7032 x 4688 16-bit sRGB |
| `strehl stack D:\personal\macro\bee-3-cpl --merge estimator --out X` | **0** | 225.08 s | 3516 x 2344 16-bit linear camera-native (binned) |

Both wrote a master and returned zero. The `U3 the eroded low-detail region
keeps only 0 px` error the README quotes **does still exist** in the tree
(`crates/strehl-cli/src/photometric.rs:371`), but the estimator's own output now
reports `--- photometric normalisation (M99, OPT-IN) ---` and `STATUS: NO
per-frame gain term is fitted or applied`. ARGUED: the photometric stage became
opt-in, so U3 can only fire when `--photometric on` is passed, and the README's
"out of the box" claim is stale at this commit rather than wrong when written.

This does not restore the estimator as a speed claim: at 320.88 s under load it
is *slower* than the pyramid default (229.68 s at comparable load), on the same
frames through the same binary. The 51.6 s figure is not reproduced here and was
not the target of this experiment.

---

## 9. Reproducing this

```powershell
$env:STREHL_CACHE_DIR = 'C:\dev\strehl-out\BUILD-SPEED\warpcache'
python experiments\BUILD-SPEED\timeit_stack.py `
    --exe C:\dev\strehl-out\BUILD-SPEED\cargo-target\release\strehl.exe `
    --dir D:\personal\macro\bee-3-cpl `
    --out C:\dev\strehl-out\BUILD-SPEED\out\bee-3-cpl-warm.tif `
    --reps 3 --label WARM-299-default-pyramid --keep `
    "--flag=--srgb" "--flag=--auto-exposure"

python experiments\BUILD-SPEED\validate_master.py `
    --img C:\dev\strehl-out\BUILD-SPEED\out\bee-3-cpl-warm.tif `
    --ref C:\dev\strehl-out\SHIP-V1\bee-3-cpl.tiff
python experiments\BUILD-SPEED\validate_master.py --selftest

python experiments\BUILD-SPEED\scaling_fit.py   --jsonl C:\dev\strehl-out\BUILD-SPEED\timings.jsonl
python experiments\BUILD-SPEED\load_response.py --jsonl C:\dev\strehl-out\BUILD-SPEED\timings.jsonl
powershell -File experiments\BUILD-SPEED\ladder.ps1
powershell -File experiments\BUILD-SPEED\worker_sweep.ps1
```

Raw record of all 28 harness-timed runs, one JSON object per run with the full
argv, the environment, the binary hash, the parsed stage lines, the busy
fraction, the child's CPU-seconds and the peak working set:
`C:\dev\strehl-out\BUILD-SPEED\timings.jsonl`.

---

## 10. What I did not measure

* **An idle box.** Every run competed with a dozen agents. The best observation
  is 116.88 s at 63 % busy; SHIP-V1's log anchors the idle case near 102 s. The
  true idle number is bounded above by 116.88 s and is not measured here.
* **A cold run at low load.** The single cold run was taken at 99 % busy. Cold
  cost decomposes as warm + solve; ARGUED, a cold run at 63 % busy would land
  near 117 + ~40 = ~157 s, but the solve was not re-measured at low load.
* **The steps of the staircase.** N was sampled at 20/40/80/150/299, which
  cannot resolve a 4-frame period. The staircase is argued from the code and
  from the flat per-round cost, not observed directly.
* **Other subjects at scale.** Two subjects, 299 and 33 frames. Frame-count
  scaling is characterised on one subject only.
* **Whether the gate explains the flat-ROI gap.** Gate 4.5 reproduces the
  shipped master exactly and gate 2.0 does not, which localises the difference
  to the gate setting; the *mechanism* (a higher gate averages more frames per
  band, lowering noise) is the README's explanation, not a measurement of mine.


---

## 9. Speed — the first timing comparison this project has

*Added after the quality sections at the owner's request. The project's stated
goal is state of the art on speed **and** quality, and until now there was no
measured comparator number for speed anywhere in the repository. Everything
below is on the same 105-frame `coffee-bean` bracket, the same machine, the
same night. Harness: `experiments/V-HEADTOHEAD2/timing2.ps1`. Arithmetic:
`timing_derive.py`, so no derived number here was typed by hand. Raw:
`logs/timing2.csv`, `logs/timing-*.txt`.*

### 9.0 The result in one table

105 frames. strehl reads 7032×4688 CFA (**32.97 MP/frame**) and writes 7032×4688
16-bit RGB. The fork reads 7168×5120 float32 TIFF (**36.70 MP/frame**) and
writes 7008×4672 float32 after its crop (32.74 MP). Memory is **GiB** throughout
(PowerShell's `1GB` is 2^30).

| | wall (s) | s/frame | peak working set | CPU (s) | how it was got |
|---|---:|---:|---:|---:|---|
| **strehl**, end to end, alignment **solved** | **36.72 / 38.39 / 38.40** | **0.366** | 7.6 GiB | 593 | MEASURED, 3 reps |
| **strehl**, end to end, alignment **cached** | 28.29 / 38.42 / 46.62 | 0.269 best | 7.3 GiB | 327 | MEASURED, 3 reps |
| **`focus-stack` fork**, merged TIFF | **1604.15 / 1320.64** | **13.93** | **47.4 GiB** | **6840** | MEASURED, 2 reps |
| **Zerene Stacker PMax** | — | — | — | — | **UNTIMEABLE** (§9.6) |

Throughput, DERIVED: strehl **90.2 MP/s** of output; the fork **2.35 MP/s**.

**strehl is between 36.0× and 41.8× faster than the fork on this stack**, under
every pairing of the measured reps (best:best 36.0×, median:median 38.1×,
worst:worst 41.8×). It burns **11.5× less CPU** and **6.2× less peak memory**
doing it, and it reads the camera's RAW files while the fork reads a 9.9×
larger set of TIFFs that something else had to develop first.

That is the headline, and the rest of this section is the reasons not to trust
it further than it deserves.

### 9.1 The harness's first job was catching its own author

`timing.ps1` (v1, kept in place, unused) unset `STREHL_WARPMAP` and I believed
that made the run end to end. It did not. Both of its strehl runs printed, in
their own logs:

```
alignment       : ON (sidecar), reference frame 52, 105 placed / 0 refused, 0.0 s
```

**Alignment cost zero.** `strehl stack` discovers a *cached* sidecar under
`$STREHL_CACHE_DIR`, defaulting to `%LOCALAPPDATA%\strehl\warpmaps`
(`align_cmd.rs:1176`), and one was sitting there from earlier work. The fork
solves its alignment on every run. Publishing that number would have credited
strehl with a stage it had skipped — measured below at **45% of its
end-to-end CPU**.

Nothing clever caught this. strehl printed the fact and I read it. So v2 does
three things:

1. points `STREHL_CACHE_DIR` at a private directory and **wipes it before every
   SOLVE rep**, and
2. **asserts the mode strehl reports** and throws if it is wrong —

```powershell
function AssertAlign($stem, $want) {
  $line = (Select-String -Path "$logs\$stem.out","$logs\$stem.err" -Pattern '^alignment ' | Select-Object -First 1).Line
  if (-not $line) { throw "$stem : strehl printed no alignment line -- cannot certify the arm" }
  if ($line -notmatch [regex]::Escape($want)) { throw "$stem : expected alignment '$want' but strehl reported: $line" }
}
```

so a silent regression to the cache fails the run instead of flattering it —
and 3. keeps **both** arms, because they answer different questions: SOLVE is
what compares to the fork, CACHED is what the owner's own workflow costs on a
re-render.

The assertion is not decoration. It fired six times in the run that produced
the table, once per rep, and every line it accepted is in the logs:

```
STREHL-SOLVE   rep 1     36.72 s  exit 0  peakWS   7.34 GB  cpu   592.9 s  freeRAM 39.6 -> 45.4 GB
    alignment       : ON (solved), reference frame 52, 105 placed / 0 refused, 10.5 s
...
STREHL-CACHED  rep 1     28.29 s  exit 0  peakWS   7.21 GB  cpu   327.1 s  freeRAM 45.6 -> 50.5 GB
    alignment       : ON (sidecar), reference frame 52, 105 placed / 0 refused, 0.0 s
```

v1 also timed through a PowerShell pipeline, which gave no access to peak
memory or CPU time. v2 uses `Start-Process` and samples `PeakWorkingSet64` every
2 s while the process is alive — necessary, because reading it *after* exit
returns zero: the probe run of the fork reported `peak WS = 0.00 GB` post-exit
while a live sample of the same process read `50,770,456,576` bytes.

**Units.** PowerShell's `1GB` literal is 2^30, so every memory figure printed by
the harness is **GiB**. The machine reports 61.6 GiB visible to Windows.

### 9.2 What the reps actually say, including the ugly one

```
arm            n  wall s: min      med      max  spread  s/frame(med)    CPU s  thr-eq peak GiB
-----------------------------------------------------------------------------------------------
STREHL-SOLVE   3        36.72    38.39    38.40    1.05        0.3656    592.9    15.5     7.64
STREHL-CACHED  3        28.29    38.42    46.62    1.65        0.3659    327.1     8.3     7.34
FORK-MERGE     2      1320.64  1462.39  1604.15    1.21       13.9276   6839.6     4.7    47.37
```

**The CACHED arm's 1.65× spread is contention, not variance in the thing being
measured, and it is visible in strehl's own stage line.** Its three reps folded
105 frames at 0.24, 0.34 and 0.42 s/frame for identical work in the same order
they ran; three other agents were working in this tree at the time (stated in my
brief, and consistent with the 108 processes holding CPU time that the harness
counted at launch). The SOLVE arm ran earlier and is tight (1.05×). I am
reporting the CACHED spread rather than dropping the outlier, and I would not
defend any CACHED number to better than "about 28 s when the machine is free."

The fork's two reps differ by 1.21× (1604 s and 1321 s). Its parallel
efficiency is **4.7 of 32 logical processors (15%)** against strehl's **15.5
(48%)**, which is the signature of a memory-bound run rather than a compute
bound one. Sampled during the two runs, its working set ran between **26.4 and
45.7 GiB** and peaked at **47.4 GiB**, while free RAM fell to **0.3 GiB** in rep
1 and **1.7 GiB** in rep 2 at the moments I sampled. **Even the fork's *faster*
rep loses by 36×: strehl wins by 36.0× at the pairing most favourable to the
fork, 38.1× at the medians and 41.8× at the pairing least favourable to it.**

### 9.3 The fork's default configuration does not complete at all

The first fork run in this lane used the flags that produce the artefact
V-HEADTOHEAD2 measures — `--output-colorspace=linear-rec2020
--output-bitdepth=32` — and nothing else. At those settings the fork's
`--hdr-preserve` resolves to `auto` → **on**, which its own `--help` prices at
"~3.6 GB extra peak RAM per 32 MP frame". It ran for **521.52 s** and died:

```
Task Grayscale aligned_DSC00020.tif on thread 4 failed with exception:
OpenCV(4.13.0) ... alloc.cpp:73: error: (-4:Insufficient memory) Failed to
allocate 146800640 bytes in function 'cv::OutOfMemoryError'

Error exit due to failed steps
```

at task 716 of 860, exit code 1, on a machine with 61.6 GiB and ~40 GiB free at
launch. 146,800,640 bytes is exactly one 7168×5120 float32 plane.

So the timed fork runs use `--hdr-preserve=off`, which the fork documents as the
legacy path for "bit-identity regression against pre-Phase-4 builds" — the
closest reachable match to the build that actually produced the comparator.

**I cannot claim that is the cheaper configuration, and I am not going to.** The
run that died had reached task 716/860 in 521 s; the `off` run that completed
was still at 771/860 at ~640 s, so on the only comparison available the
*defaulted* configuration was progressing at least as fast right up to the point
where it ran out of memory. What is established is narrower and enough:
**the fork's default configuration on this stack does not complete on this
machine**, and the configuration that does takes 1320–1604 s. The failed run's
log is kept at `logs/timing-fork-hdrauto-OOM.txt`.

### 9.4 The fork binary on disk is not the fork binary that made the comparator

Stated because it bounds what this comparison means.

| | comparator run | timed here |
|---|---|---|
| binary date | ≤ 2026-05-10 | **2026-05-17 03:01:25** |
| tasks in the graph | **772** | **860** |
| self-reported wall | merged TIFF at **93.739 s**, all three artefacts at **143.458 s** | 1320.64 / 1604.15 s |
| accelerator | `OpenCL device: NVIDIA Corporation NVIDIA GeForce RTX 5090` | same binary family, same machine |

The archived log (`C:\dev\macro\out\coffee-bean\stack.log`, 2026-05-10) shows
the fork stacking these same 105 frames — 105 `Starting task: Load` lines from
`D:\edited\macro\coffee-bean` — in **93.7 s to the merged TIFF**. Seven days and
~88 extra pipeline tasks later — Phase 12.x per-frame denoise, FBDD, lateral CA,
axial defringe, a noise model — the same command takes **1320–1604 s**. I did
not measure the intermediate builds and cannot attribute the 14.1–17.1×
regression to any one of them.

**Is that archived log the run that produced the artefact V-HEADTOHEAD2
measured?** Probably, and it is worth saying how far "probably" goes, because
the log's mtime is 16:45:16 and `stack.tif`'s is 20:01:58 — three hours later.
The log itself recommends a post-run `embed_icc.py` step, which would rewrite
the file and move its mtime. `check_icc.py` asks the file:

```
bytes         : 393,326,272
geometry      : 7008 x 4672, 3 samples, 32 bits
ICC profile   : PRESENT, 472 bytes
VERDICT       : consistent with the archived log being this file's run, followed
                by the embed_icc.py step the log itself recommends
```

A plain fork write does not embed a profile — that is the entire point of the
tip in the log. So the mtime gap has an innocent explanation and the artefact
is **consistent with** this log. Consistent with is not proof of, and I did not
find a way to make it proof.

**Both numbers are true and they answer different questions.** Against
*today's* fork, strehl is 36–42× faster. Against the *May* fork that produced
the artefact this document measures quality on, strehl at 38.39 s is **2.4×
faster to a comparable merged output** (93.739 s → 38.39 s), and **3.7× faster
against the fork's full 143.458 s three-artefact scope, which is not a like
comparison and is stated only because that is the number the archive contains**.
**The 2.4× is the figure I would defend in public**, because it compares
strehl's merged TIFF against the fork's merged TIFF, and because it is the one
that does not depend on a performance regression in somebody else's tree.

### 9.5 What is included, what is not, and which way the omissions cut

Included in every number: process start, library load, decode, alignment, focus,
merge, colour, file write, flush.

**Not included, and not normalised away:**

- **strehl reads 105 ARW = 3.88 GB. The fork reads 105 TIFF = 38.42 GB —
  9.9× the bytes — and those TIFFs are Lightroom developments of those same
  105 ARW.** That development is work the fork's route requires and strehl's
  does not; it happened before either process started and is timed by neither.
  Every fork number here is therefore an **under-count** of its route, and the
  36–42× is a **lower bound**.
- The fork *can* read ARW directly (it has a whole `--raw-*` flag family). It
  was not timed that way, because the comparator artefact this project measured
  was made from the TIFFs. A fork-reads-RAW timing is a real missing arm and is
  listed in §9.9.
- **Scope:** strehl writes one merged TIFF (7032×4688, 16-bit, 197.8 MB). The
  fork here writes one merged TIFF (7008×4672, float32, 392.9 MB) and no
  depthmap or 3D view — though it computes a depth map internally regardless;
  its own progress lines say `Construct depthmap layer N` in a run that never
  asked for one. In the archived run the two extra artefacts cost 49.7 s on top
  of the 93.7 s merge.
- **strehl's output is half the bytes** (16-bit vs float32), which flatters
  strehl's write stage. Its write is 0.3–0.7 s of a 38 s run, so this is worth
  well under 1% and cannot move the conclusion.

### 9.6 Zerene Stacker PMax: UNTIMEABLE, with the reason

Not estimated. Attempted, and the attempt is logged.

Zerene *does* ship a batch CLI. Launched exactly as its own recorded launch
command does it, with `-noSplashScreen -exitOnBatchScriptCompletion
-runMinimized -batchScript` and a batch script pointed at the same 105-frame
directory (`experiments/V-HEADTOHEAD2/zerene-probe.zbs`), it printed:

```
0.398: license 83ced522295099724b84c81abbb79f3199726fd7 expires on Sat Jun 06 20:13:34 PDT 2026
0.401: Using default license key
0.401: License category = EXPIREDLICENSE
...
0.799: hard expiration date = null
0.825: Desktop class found
```

and then **stopped**. 300.5 s of wall clock, **9 s of CPU**, no further log
line, no output file, still alive when I killed it. Its batch entry point is
`com.zerenesystems.stacker.gui.MainFrame` — a GUI class — and it stalls in GUI
initialisation before it ever reaches the batch script.

Three independent reasons, any one sufficient:

1. **`License category = EXPIREDLICENSE`** (expired 2026-06-06; today
   2026-08-27). Whatever it did run would not be the licensed product's
   behaviour.
2. **It never reached the work.** 9 CPU-seconds in 300 wall-seconds is a
   process blocked, not a process stacking.
3. **Its real workflow has a human in it.** The archived interactive session
   log records `FileDialog 'visible' for 5900 milliseconds`, the output path
   chosen from a file chooser at t=80.609 s when the stack had finished at
   t=47.058 s — **33.5 s of a person** — and a **2,242-second gap** between the
   end of one stacking operation (t=47.058) and the start of the next
   (t=2289.220) that is lunch, not computation.

**What can honestly be said about Zerene's speed**, clearly labelled: Zerene's
*own* log, from an interactive session run by the repository owner on
2026-05-09 while the licence was valid, reports for a 33-frame stack of the same
camera at the same resolution:

```
 1508: 47.058: Time for makeStackedResult(method=1) = 26.912
```

**26.912 s for align + PMax on 33 frames = 0.8155 s/frame** (MEASURED by
Zerene, DERIVED per frame). strehl's end-to-end 0.3656 s/frame is **2.23×
faster than that**. Four caveats, all of which matter:

- different subject (`marker2`, 33 frames, not `coffee-bean`, 105);
- that number **excludes** Zerene's own image load and its save (196.5 MB
  written at t=82.015 s) and every second of the human;
- it excludes the Lightroom export that produced its 12.08 GB of input;
- and it is Zerene's internal clock, not a stopwatch around a process.

So: **strehl is faster than Zerene by a factor of about two on the only
comparable number that exists, and I would state that as "roughly twice", not
as 2.23×.**

### 9.7 Against the owner's own corpus figure

The calibration point given to me: 4,825 frames at ~33 MP in 16.2 minutes =
**0.2015 s/frame** (MEASURED, this session, whole corpus). My end-to-end SOLVE
arm is **0.3656 s/frame — 1.81× slower**; my best CACHED rep is 0.2694 s/frame,
1.34× slower. The gap is explained, not waved at:

- these runs carry `--linear-srgb --demosaic`, which is the mode V-HEADTOHEAD2
  measures quality in. It writes **7032×4688** with every CFA site demosaiced,
  against the default binned **3516×2344** — 4× the output pixels;
- the SOLVE arm re-solves alignment from scratch every rep (45% of its CPU),
  which a corpus render doing many subjects will not repeat per subject;
- three other agents were on the machine, and the CACHED arm's own reps show
  what that costs (0.24 → 0.42 s/frame for identical work).

I did not reproduce the corpus figure and am not disputing it; the two are
consistent once the mode is accounted for.

### 9.8 The missing GPU path is not the speed gap it looks like

The fork ran on `NVIDIA GeForce RTX 5090` via OpenCL, per line 1 of its own log.
strehl is CPU/rayon only. strehl still won by 36–42×.

`docs/research/M7-gpu-focus-measured.md` §0–§1 measured why that is not a
paradox: GPU-accelerating the focus measure is **173×** on that stage
(MEASURED), but the whole focus+merge stage is **0.40% of a cold pipeline and
0.57% of a warm one** (DERIVED there), and the fusion prize inside it is
0.14–0.20%. The pipeline is decode and alignment. My stage breakdown says the
same thing from the other end — of a 38.39 s SOLVE run, alignment is 10.5–12.8 s
and the fold (decode + warp + focus + merge, interleaved) is 23.2–25.3 s, with
0.3–0.7 s of write.

**So the honest speed claim does not need a GPU, and saying so is not a
rationalisation — it is a number that was measured before this comparison
existed and that predicted this outcome.**

### 9.9 What the timing could not determine

- **Cold cache.** Windows has no supported script-level way to drop the page
  cache, so nothing here is a certified cold run. What I have is one *observed*
  eviction: in the v1 harness a strehl run took 26.71 s, the fork then streamed
  38.42 GB through the page cache, and the next identical strehl run took
  46.68 s — **1.75×**, with the same alignment path and the same output. That is
  a real cold/warm bound on strehl (its input is 3.88 GB and does cache);
  it is one observation, not a series. A certified cold measurement needs a
  reboot between reps, or `EmptyStandbyList`, and I did neither.
- **The fork reading RAW.** Its `--raw-*` path would remove the Lightroom step
  from its route and make the comparison symmetric in input. One run,
  `--lr-match=on`, would settle whether the 9.9× byte asymmetry is doing any of
  the work. I did not run it because the fork costs ~25 minutes per rep and the
  quality comparator was built from TIFFs.
- **Zerene end to end, at all.** Needs a valid licence and a batch mode that
  does not stall in GUI init. If the owner renews, the same
  `zerene-probe.zbs` plus a stopwatch settles it in one run.
- **Attribution of the fork's 14–17× regression** between 2026-05-10 and
  2026-05-17. Not my tree, not measured, deliberately not blamed on a commit
  range — this document's own §4.1 standard is that attribution requires
  isolating the variable.
- **Whether the fork's peak of 47.4 GiB is inherent or a leak.** strehl's merge
  prints `memory plan : 4 workers x 1328 MB = 5.2 GB ... CONSTANT in the frame
  count`, and its measured peak (7.2–7.6 GiB) is consistent with that plus
  decode and output buffers. The fork's peak scaled with the stack. I measured
  the peaks; I did not measure their slope in frame count, which is the
  experiment that would turn "6.2× more memory" into "O(n) versus O(1)".

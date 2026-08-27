# V-SPEED — the missing third axis: strehl against the open-source field, memory card to finished image

*Lane V-SPEED. Every number below was produced by code in
`experiments/V-SPEED/` and is quoted from a JSONL record or a console capture
under `C:\dev\strehl-out\V-SPEED\`. Quoted against commit `3f2de81a`.
No comparator source was read; the GPL binaries were executed, never
inspected. Nine other agents were running on this machine throughout, several
CPU-saturating, and that fact is not an aside — it is the dominant error term
and it shapes every estimator chosen below.*

---

## 0. The verdict, first

**The end-to-end comparison is constructible, it is not rigged, and strehl
wins it by a wide margin that grows with stack depth.**

Start artifact: a directory of Sony `.ARW` files. End artifact: one merged
image on disk. Same start, same end, all three arms.

| comparator | subject | frames | paired median | conservative | **floor** |
|---|---|---:|---:|---:|---:|
| `align_image_stack` + `enfuse --hard-mask` | coffee-bean | 105 | **22.58×** | 14.66× | **5.70×** |
| `focus-stack` | coffee-bean | 105 | **4.21×** | 2.73× | **2.11×** |
| `align_image_stack` + `enfuse --hard-mask` | 109MSDCF | 22 | **12.13×** | 8.89× | **3.60×** |
| `focus-stack` | 109MSDCF | 22 | **3.41×** | 2.22× | **1.74×** |

All four numbers are "strehl is N× faster". The three columns are three
framings of decreasing generosity to strehl:

- **paired median** — median over warm rounds of (comparator pipeline total ÷
  strehl total) *within the same round*. Drift-robust: both arms saw the same
  machine load in the same minutes.
- **conservative** — the comparator's *fastest* warm round against strehl's
  *slowest* warm round. Every scrap of noise handed to the comparator.
- **floor** — the comparator's **merge stage alone**, fastest warm round, with
  RAW conversion and alignment charged at **zero**, against strehl's slowest
  warm round. This is the number that survives if you reject my converter, my
  aligner, and the entire end-to-end framing. It is a strict lower bound.

**Even at the floor, where the comparators are given their input pre-decoded
and pre-aligned for free and strehl is charged for doing both itself, strehl is
still 5.70× faster than enfuse and 2.11× faster than focus-stack on 105
frames.** That is the claim I would defend in public.

Three things stand behind the table.

**1. The "not directly constructible" objection was right about the
measurement that was available and wrong to stop there.**
`docs/research/ORCH-veiling.md` §127 argued that timing strehl's
decode+align+merge against the comparators' merge-of-pre-aligned-TIFFs would be
rigged. That is correct and it remains correct. But the conclusion drawn —
"not measured" — treated the comparators' missing stages as unbuildable.
They are not unbuildable, they are *unbuilt*, and building them is exactly what
a user of enfuse has to do. `enfuse` cannot read RAW and does not align.
`focus-stack` cannot read RAW; it does align. So RAW→TIFF conversion is not an
extra bolted on to flatter strehl — **it is the cost of using enfuse**, paid by
every person who has ever focus-stacked a Sony file with it. Charging it is the
honest choice; omitting it is the rigged one, in the comparator's favour.
See §2.

**2. The timer is commissioned; the *workload* is the noisy part, not the
clock.** A planted 5.00 s delay pushed the production `time_stage()` by
**+5.02 s** (spread 0.34 s) while the null arm moved **−0.01 s** (spread
0.22 s). But two earlier commissioning designs *failed*, and the failures are
the finding: on this loaded box the same `strehl stack` over the same 22 frames
ranged **8.02–18.57 s, a factor of 2.3**, purely from other agents' load. The
instrument resolves 0.02 s; the subject wobbles by 10 s. Everything downstream
— warm minima, paired ratios, an explicit drift guard — is a response to that.
See §3.

**3. The advantage grows with depth, and it is the deep case that matters.**
Per-frame, strehl goes 0.564 s → 0.273 s from 22 to 105 frames (fixed overhead
amortising). The enfuse pipeline goes the *other way*, 6.686 s → 7.772 s per
frame. So the gap widens from 12.13× to 22.58×. Macro stacks in this
repository's own source tree run to 299 frames. See §7.

**No comparator is REFUSED.** Both `enfuse` and `focus-stack` yielded a fair
end-to-end measurement. Zerene Stacker remains unavailable (expired licence,
`docs/research/V-LINEAR.md` §1) and is out of scope for this lane — that is an
absence of a comparator, not a refusal to measure one.

---

## 1. What was measured, and on what

**Machine.** AMD Ryzen 9 9950X3D, 16 cores / 32 logical threads, 61.5 GB RAM,
NVIDIA RTX 5090 present. Windows. **No arm used the GPU** — see §6.

**Binaries.** Identified by SHA-256, never by path or size. Four builds in this
tree share the byte size 9,568,768, so size is not an identifier.

| role | path | SHA-256 | self-reported version |
|---|---|---|---|
| subject | `C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe` | `44C2F2CD2E5B289491AB81C23A9A6EBB1BC4B095192981647F7F541FCB59F490` | pinned build `9b05d0b7` |
| aligner | `C:\dev\strehl-out\V-LINEAR2\hugin\Hugin\bin\align_image_stack.exe` | `361133980DB4FDCB083B8687B3780F7820823E45AE349B424A8CFC51D598CD55` | Hugin 2025.0.1 |
| merger | `C:\dev\strehl-out\V-LINEAR2\hugin\Hugin\bin\enfuse.exe` | `919B1BB1E6E48AC5D673B92C489450A74C48735341B5F6F25EFA0153221FF7B9` | `enfuse 4.3-993fd4822e8d` |
| merger | `C:\dev\strehl-out\V-LINEAR2\fs15\focus-stack\focus-stack.exe` | `E256176D70BEC54BB51A448B2ADC452E7F49D21BC5042B40689A3257BBFDEE9E` | `1.3-42-g0cd289e`, built Jan 11 2026, OpenCV 4.12.0 |

`runner.py` hashes all four at startup and **hard-exits** if strehl's digest
does not begin `44C2F2CD2E5B2894`. Every timing in this document was produced
by a process that passed that gate.

> Note on naming: the directory is `fs15` and `V-LINEAR2.md` calls this binary
> "focus-stack 1.5", but the binary's own `--version` says `1.3-42-g0cd289e`.
> Quote the hash, not the name.

**Exact invocations.** All flags, verbatim.

```
strehl       strehl.exe stack <dir> --out <f> --srgb --auto-exposure
develop      rawpy/LibRaw postprocess(output_bps=16, use_camera_wb=True), 16 worker
             processes, uncompressed TIFF via tifffile
align        align_image_stack.exe -m -C --use-given-order -a al_ <tifs>   (cwd = aligned dir)
enfuse       enfuse.exe --exposure-weight=0 --saturation-weight=0 --contrast-weight=1 \
                        --hard-mask --output=<f> al_*.tif
focus-stack  focus-stack.exe --output=<f> <tifs>
```

`--use-given-order` is not optional and not a tuning choice:
`align_image_stack` sorts by exposure value by default, which on a
constant-exposure focus stack is arbitrary order (`V-LINEAR2.md` §2). Omitting
it makes the comparator worse, not better.

`focus-stack` runs at all defaults — threads = ncpu+1, alignment internally
downsampled to ≤2048 px, batchsize 8. Those defaults are cheaper than what
strehl does; see §8.

**Subjects.** Two, of deliberately different depth, because per-frame cost and
fixed overhead separate only across depth.

| subject | frames | source | role |
|---|---:|---|---|
| `109MSDCF` | 22 | `D:\personal\macro\109MSDCF` | shallow |
| `coffee-bean` | 105 | `D:\personal\macro\coffee-bean` | deep |
| `112MSDCF` | 79 | `D:\personal\macro\112MSDCF` | cold-read probe only (§4) |

`D:\` was read-only throughout; all outputs went to `C:\dev\strehl-out\V-SPEED\`.

---

## 2. Why end-to-end is the honest framing

The objection this lane was asked to re-examine: *strehl takes a RAW directory,
enfuse takes TIFFs, therefore the comparison cannot be built.*

Restated as a question about what a user pays, it dissolves. A person with a
memory card full of `.ARW` files and a desire for one sharp image must, using
enfuse, do all of this:

1. decode 105 RAW files to TIFF (enfuse cannot read RAW),
2. align them (enfuse does not align),
3. merge them.

Using strehl they run one command. The stages in (1) and (2) are not overhead
invented to pad the comparator's number. They are the comparator's actual
requirements, and any measurement that omits them is measuring a pipeline
nobody can run.

The genuinely rigged comparisons are the two asymmetric ones, and this lane
produced neither:

- ✗ strehl's whole pipeline vs enfuse's merge step alone — charges strehl for
  work the comparator is excused;
- ✗ strehl's merge step alone vs enfuse's whole pipeline — the mirror image.

Both ends match here: `.ARW` directory in, one image file out.

**The conversion tool is the one real degree of freedom, and it is handled by
bounding rather than by argument.** I used `rawpy`/LibRaw at 16 worker
processes, not strehl's own decoder, because a person using enfuse does not
have strehl. (`V-LINEAR2` deliberately used strehl's decoder for its *quality*
comparison so that demosaic and white balance would cancel; that rationale is
about bit-identity and does not transfer to speed.) Someone could object that a
faster converter exists. The **floor** column answers that objection without
arguing it: set conversion *and* alignment to zero seconds — free, instant,
better than any converter that will ever exist — and strehl still wins by
5.70× and 2.11× on 105 frames.

**Measured, not assumed:** that `enfuse` cannot read `.ARW`. It was fed one and
refused. `focus-stack` likewise.

---

## 3. Commissioning the timer — three designs, two failures, one pass

Rule: a timer that cannot see a planted 5 s cannot see a real 5 s.

### 3.1 The clock itself — PASS at ±0.007 s

First attempt (`clockcheck.py`, absolute): time a child that sleeps T seconds.
**FAILED** — +0.48 s error at T = 1 s with a 0.91–1.30 s spread. Diagnosis: that
is Python interpreter startup under nine-agent load, not clock error. Any
absolute timing of a short child on this box is meaningless.

Rewritten as **differential + minimum** — t(T) − t(0), minimum over 5 repeats:

| planted | measured | error |
|---:|---:|---:|
| 1.000 s | 1.0059 s | **+0.0059 s** |
| 5.000 s | 5.0071 s | **+0.0071 s** |

**PASS.** The clock is good to ±0.007 s.

### 3.2 Block design — FAILED

A 2×2 plant/no-plant across blocks on the real `strehl` and `focus-stack`
stages returned deltas of **+2.78 s** and **+8.26 s** against a 5.00 s plant,
with 4–11 s within-arm spreads. A block design cannot resolve a 5 s plant
against 4–11 s of between-block machine drift.

### 3.3 Paired design on a real workload — FAILED, and the failure is the finding

`commission_paired.py` with 6 plant/no-plant *pairs* on `strehl` plus a null
arm: PLANT median **+6.13 s**, NULL median **+1.62 s** against expectations of
+5.00 and 0.00. Still not clean. The reason is visible in the raw data:

> **The same `strehl stack` command, on the same 22 frames, on the same
> machine, ranged 8.02 s to 18.57 s — a factor of 2.3 — purely from other
> agents' load.**

This arm is retained in `commission_paired.py` deliberately *because it
failed*. It is the measurement of the box's noise floor and it is the single
most important calibration number in this document.

### 3.4 Paired design on a deterministic synthetic stage — PASS

Isolating the harness from the workload: a deterministic synthetic stage
(`SYNTH_S = 10.0`) run through the **production `time_stage()`**, same code
path as every reported number, 6 pairs.

| arm | expected | measured median | spread |
|---|---:|---:|---:|
| PLANT | +5.00 s | **+5.02 s** | 0.34 s |
| NULL | 0.00 s | **−0.01 s** | 0.22 s |

**PASS.** The harness sees a planted 5 s as 5.02 s. `commission_paired.py`
hard-errors with `PLANT DID NOT ARM` if the plant fails to take effect, so a
silently disarmed plant cannot masquerade as a pass.

**Verdict: timings are reportable.** The instrument resolves 0.02 s. The
resolution of the *experiment* is set by the workload's load-driven variance,
which is why §5 reports minima, medians, maxima and spread for everything, and
why §7 reports a paired ratio and a drift guard rather than a single number.

---

## 4. Cache policy and interleaving policy

**Cache policy.** No cache purging was performed — this is a shared machine and
purging would have disrupted nine other agents. Instead the cold state is
*reported*, not hidden:

- **Round 0 of every subject is cold and is reported in its own column.** It is
  excluded from all warm statistics and from every ratio.
- **Warm = rounds 1..N**, back to back on a file cache warmed by round 0.

**One known asymmetry, measured and corrected for.** `develop` runs first in
every round, so it warms the `.ARW` files before strehl ever touches them.
strehl therefore never got a genuinely cold RAW read, and its round-0 number is
biased in its own favour. `coldprobe.py` quantifies the bias on `112MSDCF`
(79 frames), a subject no other run in this lane had touched:

| run | state | wall | s/frame |
|---:|---|---:|---:|
| 0 | cold | 28.89 s | 0.366 |
| 1 | warm | 24.82 s | 0.314 |
| 2 | warm | 25.48 s | 0.323 |

**Cold penalty +4.07 s, +16.4%.** Applying it to strehl's deep warm median
(28.70 s → 33.41 s cold-equivalent) moves the deep end-to-end ratios from
28.44× to **24.43×** against enfuse and from 4.52× to **3.88×** against
focus-stack. It cannot change any conclusion. Note that the comparator pipelines already carry *their* cold
penalty honestly, in `develop`'s round-0 number (44.08 s cold vs 27.57 s warm
minimum on the deep subject).

**Interleaving policy.** Rounds are interleaved, never blocked. Within a round
the consumers run A,B,C and **the order alternates by round** (AGENTS rule 16):

```
round even:  develop, strehl, align, enfuse, focus-stack
round odd:   develop, focus-stack, align, enfuse, strehl
```

`develop` is always first because both comparator pipelines depend on its
output. Alternating the consumer order means a monotone drift over a round
cannot systematically favour whichever arm happens to run early.

**`develop` is charged to both comparators.** It is literally the same
invocation producing the same TIFFs; neither comparator can read RAW. It is not
double-counted within a round — it runs once and its cost is added to both
comparator totals.

---

## 5. The full breakdown — arm × stage × subject

Every cell is wall-clock seconds. `s/frame` is the warm median ÷ frame count.
`spread` is (warm max − warm min) ÷ warm median.

### 5.1 `109MSDCF` — 22 frames, 5 rounds (0 cold, 1–4 warm)

| stage | cold | warm min | warm median | warm max | spread | s/frame |
|---|---:|---:|---:|---:|---:|---:|
| develop (RAW→TIFF) | 6.39 | 6.57 | 6.85 | 7.84 | 18.6% | 0.311 |
| **strehl** (whole pipeline) | 8.21 | 7.83 | 12.41 | 15.03 | 58.0% | 0.564 |
| align_image_stack | 118.85 | 72.75 | 85.63 | 93.35 | 24.1% | 3.892 |
| enfuse (merge only) | 64.45 | 54.06 | 54.74 | 70.68 | 30.4% | 2.488 |
| focus-stack (merge+align) | 28.89 | 26.21 | 29.98 | 46.11 | 66.4% | 1.363 |

| pipeline total | cold | warm min | warm median | warm max | spread | s/frame |
|---|---:|---:|---:|---:|---:|---:|
| **strehl** | 8.21 | 7.83 | 12.41 | 15.03 | 58.0% | **0.564** |
| develop + align + enfuse | 189.70 | 133.64 | 147.09 | 171.88 | 26.0% | **6.686** |
| develop + focus-stack | 35.28 | 33.34 | 36.55 | 53.95 | 56.4% | **1.662** |

### 5.2 `coffee-bean` — 105 frames, 4 rounds (0 cold, 1–3 warm)

| stage | cold | warm min | warm median | warm max | spread | s/frame |
|---|---:|---:|---:|---:|---:|---:|
| develop (RAW→TIFF) | 44.08 | 27.57 | 30.88 | 32.52 | 16.0% | 0.294 |
| **strehl** (whole pipeline) | 39.41 | 28.34 | 28.70 | 44.20 | 55.3% | 0.273 |
| align_image_stack | 548.96 | 368.68 | 399.92 | 511.02 | 35.6% | 3.809 |
| enfuse (merge only) | 284.17 | 251.76 | 272.56 | 433.91 | 66.8% | 2.596 |
| focus-stack (merge+align) | 106.88 | 93.18 | 98.89 | 115.23 | 22.3% | 0.942 |

| pipeline total | cold | warm min | warm median | warm max | spread | s/frame |
|---|---:|---:|---:|---:|---:|---:|
| **strehl** | 39.41 | 28.34 | 28.70 | 44.20 | 55.3% | **0.273** |
| develop + align + enfuse | 877.22 | 648.00 | 816.10 | 864.71 | 26.6% | **7.772** |
| develop + focus-stack | 150.96 | 120.74 | 129.77 | 147.74 | 20.8% | **1.236** |

### 5.3 Where the enfuse pipeline's time actually goes

The pipeline median is the median of per-round *totals*, so the exact
decomposition is taken from the round that produced it (round 1, total
816.10 s) rather than from stage-wise medians that would not sum:

| stage | seconds | share of pipeline |
|---|---:|---:|
| align_image_stack | 511.02 | **62.6%** |
| enfuse merge | 272.56 | 33.4% |
| RAW→TIFF develop | 30.88 → 32.52 | **4.0%** |
| **total** | **816.10** | 100% |

Across all three warm rounds the conversion share is 3.6%, 4.0%, 4.3%.

**Conversion is ~4% of the enfuse pipeline.** This is the single most useful
number for anyone who suspects the framing is rigged by the conversion charge.
Delete the conversion stage entirely — hand the comparator its TIFFs free — and
the enfuse pipeline is still **783.58 s** against strehl's 28.70 s, a 27.3×
gap. **The comparison does not rest on the converter choice — alignment does,
and alignment is a stage enfuse genuinely does not have.**

### 5.4 Raw per-round data

`109MSDCF`, seconds:

| round | dir | develop | strehl | align | enfuse | focus-stack |
|---:|---|---:|---:|---:|---:|---:|
| 0 (cold) | fwd | 6.39 | 8.21 | 118.85 | 64.45 | 28.89 |
| 1 | rev | 6.57 | 7.83 | 72.75 | 54.32 | 30.91 |
| 2 | fwd | 6.57 | 11.05 | 80.01 | 55.17 | 29.06 |
| 3 | rev | 7.84 | 15.03 | 93.35 | 70.68 | 46.11 |
| 4 | fwd | 7.13 | 13.76 | 91.25 | 54.06 | 26.21 |

`coffee-bean`, seconds:

| round | dir | develop | strehl | align | enfuse | focus-stack |
|---:|---|---:|---:|---:|---:|---:|
| 0 (cold) | fwd | 44.08 | 39.41 | 548.96 | 284.17 | 106.88 |
| 1 | rev | 32.52 | 28.34 | 511.02 | 272.56 | 115.23 |
| 2 | fwd | 27.57 | 28.70 | 368.68 | 251.76 | 93.18 |
| 3 | rev | 30.88 | 44.20 | 399.92 | 433.91 | 98.89 |

---

## 6. Parallelism and GPU — nobody is handicapped, nobody used the GPU

Brief item 7: do not tune our arm and not theirs. Nothing was tuned. Every arm
ran at its own defaults with no thread flag given to anyone. `parallelism.py`
measures actual core occupancy via Win32 `GetProcessTimes` (CPU seconds ÷ wall
seconds) on `109MSDCF`, 22 frames, 32 logical processors:

| arm | wall s | CPU s | mean cores busy | of 32 |
|---|---:|---:|---:|---:|
| strehl | 8.83 | 88.39 | **10.01** | 31% |
| enfuse | 52.69 | 368.98 | **7.00** | 22% |
| focus-stack | 29.06 | 219.58 | **7.56** | 24% |
| align_image_stack | 77.16 | 415.36 | **5.38** | 17% |

All four are genuinely multi-threaded and all four sit in the same band. strehl
is the most parallel of the four but not by a factor that could explain a 4×
or 22× result, and no arm is anywhere near saturating the machine — which is
itself a consequence of nine other agents holding cores.

`develop` is excluded from that table: it is a Python parent spawning 16 worker
*processes*, and `GetProcessTimes` on the parent does not cover descendants, so
its occupancy reading would be a meaningless ~0. Its configuration is stated
instead: **16 worker processes**, wall 0.294–0.311 s/frame. Its core occupancy
is **not measured** (§9).

**GPU: none of the three used it.**

- `focus-stack --opencv-version` prints 85 lines of OpenCV 4.12.0 build
  configuration containing **zero** occurrences of `OpenCL` (case-insensitive)
  and no CUDA entry. `Parallel framework: Concurrency`. Its default
  `--no-opencl=false` therefore has nothing to enable.
- `strehl stack --help` contains **zero** matches for `gpu`, `cuda`, `opencl`,
  `thread` or `rayon` — no GPU path and no thread knob is exposed.
- `enfuse` and `align_image_stack` are CPU-only.

The RTX 5090 in this machine did no work in any arm. This is a fair fight on
the CPU, and it also means the result would not change on a machine without a
discrete GPU.

---

## 7. The ratios — each naming comparator, subject and frame count

Veiling §127: *a performance ratio names its comparator, its subject, and its
frame count, or it is not a measurement, it is a mood.*

### 7.1 Primary estimator: per-round paired ratios

For each warm round, (comparator pipeline total ÷ strehl total) computed
**within that round**, so both arms saw the same machine load in the same
minutes. This is the estimator that survives the drift problem of §3.3.

| subject | frames | comparator | per-round | **median** | min | max |
|---|---:|---|---|---:|---:|---:|
| coffee-bean | 105 | align+enfuse | 28.80×, 22.58×, 19.56× | **22.58×** | 19.56× | 28.80× |
| coffee-bean | 105 | focus-stack | 5.21×, 4.21×, 2.94× | **4.21×** | 2.94× | 5.21× |
| 109MSDCF | 22 | align+enfuse | 17.06×, 12.83×, 11.44×, 11.08× | **12.13×** | 11.08× | 17.06× |
| 109MSDCF | 22 | focus-stack | 4.78×, 3.23×, 3.59×, 2.42× | **3.41×** | 2.42× | 4.78× |

Stated in full, the four headline claims:

> **strehl is 22.58× faster than Hugin `align_image_stack` +
> `enfuse --hard-mask` on `coffee-bean`, 105 frames, RAW directory to merged
> image, per-round paired median over 3 warm rounds (range 19.56–28.80×).**
>
> **strehl is 4.21× faster than `focus-stack` 1.3-42 on `coffee-bean`,
> 105 frames, RAW directory to merged image, per-round paired median over
> 3 warm rounds (range 2.94–5.21×).**
>
> **strehl is 12.13× faster than Hugin `align_image_stack` +
> `enfuse --hard-mask` on `109MSDCF`, 22 frames, RAW directory to merged image,
> per-round paired median over 4 warm rounds (range 11.08–17.06×).**
>
> **strehl is 3.41× faster than `focus-stack` 1.3-42 on `109MSDCF`, 22 frames,
> RAW directory to merged image, per-round paired median over 4 warm rounds
> (range 2.42–4.78×).**

### 7.2 Conservative and floor framings

| subject | frames | comparator | end-to-end (median/median) | conservative | floor |
|---|---:|---|---:|---:|---:|
| coffee-bean | 105 | align+enfuse | 28.44× | 14.66× | **5.70×** |
| coffee-bean | 105 | focus-stack | 4.52× | 2.73× | **2.11×** |
| 109MSDCF | 22 | align+enfuse | 11.86× | 8.89× | **3.60×** |
| 109MSDCF | 22 | focus-stack | 2.95× | 2.22× | **1.74×** |

- *end-to-end*: comparator warm median ÷ strehl warm median.
- *conservative*: comparator's fastest warm round ÷ strehl's slowest warm round.
- *floor*: comparator's **merge stage alone**, fastest warm, ÷ strehl's slowest
  warm. Conversion free, alignment free.

The floor row is the one to quote when the framing itself is under attack. It
concedes every disputed point in advance and still shows a win.

### 7.3 The drift guard — and one INCONCLUSIVE

An unpaired guard, deliberately harsh: require the arm-to-arm gap to exceed
3× the worst within-arm spread, or declare the comparison inconclusive.

| subject | comparator | gap | worst spread | ratio | verdict |
|---|---|---:|---:|---:|---|
| coffee-bean | align+enfuse | 787.4 s | 216.7 s | 3.6× | **OK** |
| coffee-bean | focus-stack | 101.1 s | 27.0 s | 3.7× | **OK** |
| 109MSDCF | align+enfuse | 134.7 s | 38.2 s | 3.5× | **OK** |
| 109MSDCF | focus-stack | **24.1 s** | **20.6 s** | **1.2×** | **INCONCLUSIVE** |

**Reported without softening: on the shallow subject, strehl versus
`focus-stack` does not clear the unpaired guard.** The 24.1 s gap is comparable
to the 20.6 s worst within-arm spread. The paired estimator does clear it — all
four warm rounds put strehl ahead, minimum 2.42× — and the paired estimator is
the better one here precisely because it cancels the between-round drift the
guard is detecting. But the two disagree about confidence, and the honest
statement is both:

> On 22 frames against `focus-stack`, strehl was faster in every one of four
> warm rounds (2.42×, 3.23×, 3.59×, 4.78×), but the run-to-run spread on this
> loaded machine rivals the arm-to-arm gap. **The shallow focus-stack ratio
> should not be quoted without that spread.** The deep case (105 frames,
> gap/spread 3.7×) is the one to lead with.

### 7.4 Depth dependence

| subject | frames | strehl s/frame | enfuse pipeline s/frame | focus-stack pipeline s/frame |
|---|---:|---:|---:|---:|
| 109MSDCF | 22 | 0.564 | 6.686 | 1.662 |
| coffee-bean | 105 | **0.273** | **7.772** | **1.236** |

strehl's per-frame cost **halves** from 22 to 105 frames as fixed overhead
amortises. The enfuse pipeline's per-frame cost **rises** by 16%, because
`align_image_stack` aligns pairwise in sequence and its cost per frame does not
improve with more frames to spread it over. That divergence is why the gap
widens with depth (12.13× → 22.58×), and it is the finding with the most
practical consequence: **the deeper the stack, the bigger the advantage**, and
this repository's own source directories contain 299-frame stacks.

---

## 8. Output artifacts — real, and not flattering to strehl on cost

Speed measured at a quality the user would reject is not a win, so each arm's
end artifact was confirmed to be a plausible merged image. **No quality
comparison was attempted** — that belongs to V-LINEAR2 and V-HEADTOHEAD2 and
duplicating it here would be worthless.

`artifacts.py`, round 2 of each subject:

| subject | arm | dimensions | dtype | bytes | min/max | sd | verdict |
|---|---|---|---|---:|---|---:|---|
| coffee-bean | strehl | 7032×4688×3 | uint16 | 197,801,285 | 0 / 64443 | 20055 | **REAL** |
| coffee-bean | enfuse | 7028×4688×4 | uint16 | 262,335,944 | 4690 / 65535 | 19690 | **REAL** |
| coffee-bean | focus-stack | 7028×4688×3 | **uint8** | 54,076,824 | 16 / 255 | 72.7 | **REAL** |
| 109MSDCF | strehl | 7032×4688×3 | uint16 | 197,801,285 | 0 / 65535 | 20287 | **REAL** |
| 109MSDCF | enfuse | 7028×4688×4 | uint16 | 256,961,756 | 0 / 65535 | 18162 | **REAL** |
| 109MSDCF | focus-stack | 6960×4641×3 | **uint8** | 62,090,984 | 0 / 255 | 73.9 | **REAL** |

Each is full-resolution, non-blank, and has tens of thousands of distinct
levels (uint8 arms have 233 and 256 of a possible 256). All six pass.

**Two facts here run against strehl and must be stated:**

1. **`focus-stack` writes 8-bit output.** strehl and enfuse write 16-bit. An
   8-bit write is roughly half the output work. The `focus-stack` timings are
   therefore *flattered* relative to strehl's, and its 4.21× / 3.41× deficits
   would widen if it produced a 16-bit file. (Fed *linear* TIFFs the shipped
   binary produced an 8-bit output with max = 48/255 — near black — which is
   why the primary arm uses sRGB develops.)
2. **`focus-stack` aligns at ≤2048 px by default**, a downsampled alignment,
   while strehl aligns at full sensor resolution. Again this is cheaper work,
   and again it flatters the comparator's timing.

Both were left at their defaults deliberately. Changing them would be tuning
the comparator, and the brief forbids tuning either side. The honest note is
that the comparator's defaults do *less* work than strehl and it is still
slower.

---

## 9. Measured versus assumed

**Measured — a command was run and its output is on disk:**

- Wall-clock for every stage of every arm on both subjects, 9 rounds total
  (`timings-deep.jsonl`, `timings-shallow.jsonl`).
- Timer commissioning: clock ±0.007 s; planted 5.00 s seen as +5.02 s; null
  −0.01 s (`commission-paired.jsonl`).
- The box's noise floor: strehl 8.02–18.57 s on identical work.
- SHA-256 of all four binaries; strehl's verified against the required prefix.
- Self-reported versions of enfuse and focus-stack.
- Core occupancy of strehl, enfuse, focus-stack and align_image_stack
  (`parallelism.log`).
- Absence of OpenCL and CUDA in focus-stack's OpenCV build (85 lines, 0 matches).
- Absence of any GPU/thread flag in `strehl stack --help` (0 matches).
- Cold vs warm RAW read cost for strehl: +4.07 s / +16.4% on 79 frames
  (`coldprobe.log`).
- Output dimensions, dtype, byte size and non-degeneracy for all six artifacts.
- That `enfuse` and `focus-stack` reject `.ARW` input.

**Assumed — stated, not demonstrated:**

- That `rawpy`/LibRaw at 16 workers is a *representative* RAW→TIFF converter
  for an enfuse user. A faster one may exist. **Bounded, not assumed away**:
  conversion is 3.8% of the enfuse pipeline (§5.3) and the floor framing sets it
  to zero.
- That `align_image_stack -m -C --use-given-order` is the alignment a
  competent enfuse user would run. Taken from `V-LINEAR2.md` §2.
- That the enfuse flag set (`--exposure-weight=0 --saturation-weight=0
  --contrast-weight=1 --hard-mask`) is the standard focus-stacking recipe.
- That `focus-stack`'s defaults are what its users run.
- That `112MSDCF` was genuinely cold for the §4 probe. No other run in this
  lane touched it, but nine other agents share this machine and I cannot prove
  none of them read it.
- That the outputs are of *acceptable* quality. Only their plausibility was
  checked; quality is other lanes' work.

**Not measured, and owed:**

- `develop`'s core occupancy (Win32 `GetProcessTimes` does not cover child
  processes; its 16-worker configuration is stated instead).
- Sensitivity of the comparator timings to sRGB vs linear develop mode. A
  single linear smoke round on `109MSDCF` gave develop 8.16 s, align 88.10 s,
  enfuse 94.08 s, focus-stack 36.52 s — all within the sRGB spreads except
  enfuse, which was slower on linear. Not enough rounds to call.
- Any comparison on a 299-frame stack, where §7.4 predicts the gap is widest.
- Zerene Stacker, unavailable (expired licence).

---

## 10. What this means for how the project states its speed claim

1. **The speed axis is no longer unmeasured.** Veiling §127's "no comparator
   against the field" is discharged. The 3.67×-on-105-frames predecessor-fork
   figure is a *different measurement against a different subject* and should
   never be quoted in the same breath as these; it compares strehl to its own
   ancestor, not to the field.

2. **State it as a floor plus a range, never as a single number.** The
   defensible public form is:

   > *End to end from a RAW directory to a merged image on a 105-frame stack,
   > strehl is **22.6× faster than Hugin align_image_stack + enfuse** and
   > **4.2× faster than focus-stack**. Even charging those tools nothing at all
   > for RAW conversion and alignment — comparing their merge step alone
   > against strehl's entire pipeline at its slowest — strehl is still 5.7× and
   > 2.1× faster.*

   The second sentence is what makes the first one safe.

3. **Lead with the deep subject.** It is the stronger case, it is the real
   macro use case, and it is the one that clears the drift guard against both
   comparators.

4. **Do not quote the shallow focus-stack ratio bare.** It is the weakest
   result in this document and the unpaired guard calls it inconclusive (§7.3).

5. **The remeasure hazard is real and should be priced in.** These numbers were
   taken on a machine with nine competing agents. Within-arm spreads reached
   66.8%. A quiet machine would very likely produce *larger* ratios, since
   contention noise is one-sided and strehl's arm is the shortest and therefore
   the most sensitive in relative terms. But that is a prediction, not a
   measurement, and it should be labelled as such until someone re-runs this on
   an idle box.

6. **Folding these facts into `SYNTHESIS.md` is owed and is outside this lane's
   edit scope.**

---

## 11. Facts

- **P1.** `enfuse 4.3-993fd4822e8d` cannot read `.ARW`; `focus-stack
  1.3-42-g0cd289e` cannot read `.ARW`. RAW→TIFF conversion is a mandatory stage
  of both pipelines, not an optional extra. *(Measured: both rejected a `.ARW`
  input.)*
- **P2.** `enfuse` performs no alignment. `align_image_stack` is a mandatory
  stage of the enfuse pipeline. `focus-stack` aligns internally.
- **P3.** The end-to-end framing — `.ARW` directory in, one image file out — is
  symmetric at both ends and is therefore not rigged. The asymmetric framings
  (either side's whole pipeline against the other's merge step) are, and neither
  was produced.
- **P4.** Timer commissioned: planted 5.00 s measured as **+5.02 s** (spread
  0.34 s), null arm **−0.01 s** (spread 0.22 s), through the production
  `time_stage()`. Clock differential accuracy ±0.007 s.
- **P5.** Two commissioning designs failed before one passed. A block design
  returned +2.78 s and +8.26 s against a 5.00 s plant; a paired design on the
  real `strehl` workload returned +6.13 s (plant) and +1.62 s (null).
- **P6.** The box's noise floor: **the same `strehl stack` on the same 22 frames
  ranged 8.02–18.57 s**, a factor of 2.3, under nine-agent load. This, not the
  clock, is the resolution limit of the experiment.
- **P7.** `coffee-bean`, 105 frames, warm medians: strehl **28.70 s**;
  develop+align+enfuse **816.10 s**; develop+focus-stack **129.77 s**.
- **P8.** `109MSDCF`, 22 frames, warm medians: strehl **12.41 s**;
  develop+align+enfuse **147.09 s**; develop+focus-stack **36.55 s**.
- **P9.** Per-round paired medians: **22.58×** vs enfuse and **4.21×** vs
  focus-stack on 105 frames; **12.13×** and **3.41×** on 22 frames.
- **P10.** Floor ratios, comparator merge stage alone against strehl's slowest
  warm round: **5.70×** vs enfuse and **2.11×** vs focus-stack on 105 frames;
  **3.60×** and **1.74×** on 22 frames.
- **P11.** RAW→TIFF conversion is **4.0%** of the enfuse pipeline in the median
  warm round on 105 frames (3.6–4.3% across warm rounds). `align_image_stack`
  alone is **62.6%**. Charging the comparator nothing at all for conversion
  still leaves it at 783.58 s against strehl's 28.70 s. The result does not
  turn on the converter choice.
- **P12.** strehl's advantage **grows with stack depth**: 12.13× → 22.58× vs
  enfuse and 3.41× → 4.21× vs focus-stack, from 22 to 105 frames. strehl's
  per-frame cost falls 0.564 → 0.273 s; the enfuse pipeline's *rises*
  6.686 → 7.772 s.
- **P13.** **No arm used the GPU.** focus-stack's OpenCV 4.12.0 build reports no
  OpenCL and no CUDA across 85 lines of build configuration; `strehl stack
  --help` exposes no GPU or thread flag.
- **P14.** Mean cores busy of 32, on 22 frames: strehl 10.01, focus-stack 7.56,
  enfuse 7.00, align_image_stack 5.38. All arms multi-threaded, none tuned,
  none saturating.
- **P15.** strehl's true cold-RAW penalty is **+4.07 s / +16.4%** on 79 frames.
  Correcting for it moves the deep end-to-end ratios 28.44× → **24.43×** vs
  enfuse and 4.52× → **3.88×** vs focus-stack, and changes no conclusion.
- **P16.** `focus-stack` writes **8-bit** output and aligns at **≤2048 px** by
  default, both cheaper than what strehl does. Its timings are flattered
  relative to strehl's, and it is still slower.
- **P17.** On 22 frames against `focus-stack` the unpaired drift guard is
  **INCONCLUSIVE** (gap 24.1 s, worst within-arm spread 20.6 s). The paired
  estimator puts strehl ahead in all four warm rounds, minimum 2.42×. Quote
  both or neither.
- **P18.** All six output artifacts are full-resolution, non-blank, and
  multi-level: **REAL**. No quality comparison was attempted.
- **P19.** No comparator was **REFUSED**. Zerene Stacker is unavailable
  (expired licence, `V-LINEAR.md` §1), which is an absent comparator, not a
  refused one.
- **P20.** The predecessor-fork figure of 3.67× on 105 frames is a comparison
  against strehl's own ancestor and is not commensurable with any ratio in this
  document.
- **P21.** Every stage row, pipeline-total row and paired-ratio row in §5 and
  §7.1 is re-derivable from the raw JSONL: `verify.py` recomputes all 20 rows
  from `timings-*.jsonl` and matches them verbatim against this document,
  **20/20 GREEN**. The checker is itself commissioned — a planted defect
  (paired median 22.58× → 31.41×) drives it **RED**, and it hard-errors with
  `MUTATION TARGET NOT FOUND` if the plant fails to arm.

---

## 12. Verifying this document

`verify.py` is the guard against the failure mode where a number is correct in
the console log and wrong in the prose. It recomputes each table row from
`C:\dev\strehl-out\V-SPEED\timings-*.jsonl` and requires the row to appear in
this file **exactly once, verbatim**. Whole-row matching is deliberate: a
presence test for a short token like `4.21` is satisfied by any duplicate of
that value anywhere in the document, so it can pass on a decoy while the
canonical site is wrong.

```
python verify.py               # 20/20 re-derived rows matched  GREEN
python verify.py --commission  # clean GREEN, planted defect RED -> COMMISSIONING PASS
```

**What it does not cover, stated plainly:** the §3 commissioning numbers, the
§6 parallelism table, the §4 cold probe and the §8 artifact table are quoted
from their own logs (`commission-paired.jsonl`, `parallelism.log`,
`coldprobe.log`, `artifacts.log`) and are not re-derived by `verify.py`.

---

## 13. Reproducing this

```
cd experiments/V-SPEED
python clockcheck.py                                     # clock, differential+minimum
python commission_paired.py synthetic                    # timer commissioning of record
python runner.py deep    coffee-bean "D:\personal\macro\coffee-bean" 4 srgb
python runner.py shallow 109MSDCF    "D:\personal\macro\109MSDCF"    5 srgb
python report.py deep shallow                            # tables and ratios
python parallelism.py 109MSDCF "D:\personal\macro\109MSDCF"
python coldprobe.py 112MSDCF "D:\personal\macro\112MSDCF" 3
python artifacts.py "C:\dev\strehl-out\V-SPEED\coffee-bean\out\r2-*.tif" \
                    "C:\dev\strehl-out\V-SPEED\109MSDCF\out\r2-*.tif"
python verify.py --commission                            # this document vs the raw JSONL
```

`runner.py` will refuse to run if the strehl binary's SHA-256 does not begin
`44C2F2CD2E5B2894`. Logs and JSONL land under `C:\dev\strehl-out\V-SPEED\`.
`D:\` is read-only and nothing in this lane writes to it.

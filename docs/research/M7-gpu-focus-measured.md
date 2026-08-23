# M7 — the GPU focus volume, measured, and the price of the fusion prize

**Status:** measured, 2026. All GPU numbers on an RTX 5090 (32 GB, sm_120) via `wgpu`
30.0.1 / Vulkan. All CPU numbers on a Ryzen 9 9950X3D (32 logical processors), 64 GB RAM.
Code: `experiments/m7-gpu-focus/`. Raw captured output: `experiments/m7-gpu-focus/results-*.txt`.

Every claim below is labelled **MEASURED** (I ran it and read the number),
**VERIFIED** (an assertion in the self-test suite passes), **DERIVED** (arithmetic on
measured inputs), **ARGUED** (reasoning, not measurement), or **UNVERIFIED** (stated but
not established here).

---

## 0. The verdict in one paragraph

The ring-difference focus measure and the merge, for a 22-frame A7C II stack already
resident in VRAM, take **4.115 ms** on the GPU (MEASURED, median of 30 warm reps,
±0.005 ms). The same work with the focus field round-tripped through memory — which is
what an *unconstrained* plugin that simply emits a focus field would cost — takes
**5.568 ms**. **The fusion prize is therefore 1.453 ms** (MEASURED), which is **0.14% of
a cold 22-frame pipeline and 0.20% of a warm one** (DERIVED, against M1's decode and
fact 15's alignment). Even the most permissive plugin model — materialise the entire
focus volume in VRAM, merge it afterwards — costs only 1.684 ms more than fusion, and
even *two* focus measures unfused cost 3.606 ms more than two fused, still under 0.4% of
the pipeline. **The fusion prize does not justify constraining contributors to spliceable
WGSL.** What the measurement *does* justify is a much weaker constraint: run on the GPU
at all. The GPU-versus-CPU gap is 173× (wall clock, 22 frames, MEASURED) and *that* is
where the two orders of magnitude live. Fact 21 is not wrong, but it cannot bear the
weight placed on it: it is per-frame *CPU time under 32-way concurrency*, not wall clock,
and it was never a bound on a GPU design. **SYNTHESIS risk 10 is confirmed: the
contribution format was being constrained by a measurement that does not apply to it.**

---

## 1. The headline numbers

22 frames, `C:\dev\macro\test\109MSDCF`, f/11, ISO 160. Active area 7032×4688, green
plane 3516×2344, packed 62.88 MiB/frame, 1.351 GiB resident for the stack. Median warm
GPU time over 30 reps; cold is the first run after pipeline creation. All MEASURED.

| | Variant | Dispatches/frame | GPU ms | Wall ms | Cold ms |
| --- | --- | ---: | ---: | ---: | ---: |
| **A** | **fused** (focus measured in registers, merged in the same invocation) | 1 | **4.115** | 4.352 | 4.124 |
| F | fused, raw fp32 divide instead of `div_rn` | 1 | 4.113 | 4.321 | 4.113 |
| **B** | **unfused** (focus → memory → merge reads it back) | 2 | **5.568** | 5.946 | 5.574 |
| **C** | **volume** (all 22 focus fields resident, merged afterwards) | 2 | **5.799** | 6.348 | 5.801 |
| D | fused2 (two measures, radii 1/3 and 2/5, combined + merged in one kernel) | 1 | 4.926 | 5.192 | 4.914 |
| E | unfused2 (the same two measures as two plugin passes + a merge) | 3 | 8.531 | 9.260 | 8.879 |

Distributions for variant A: min 4.104, median 4.115, mean 4.114 ± 0.005, p95 4.121, max
4.127 ms, n = 30. It is a very quiet measurement; the spread is 0.5%.

| Quantity | Value | Label |
| --- | ---: | --- |
| **Fusion prize, one measure** (B − A) | **1.453 ms** (26.1% of the unfused path) | MEASURED |
| Fusion prize vs the full volume (C − A) | 1.684 ms | MEASURED |
| **Fusion prize, two measures** (E − D) | **3.606 ms** (42.3% of the unfused path) | MEASURED |
| Price of numerical exactness (A − F) | **0.003 ms** (0.07%) | MEASURED |
| GPU focus volume, per frame | 0.187 ms | DERIVED |
| CPU focus+fold, 22 frames, single thread | 1415.7 ms (64.3 ms/frame) | MEASURED |
| CPU focus+fold, 22 frames, 32 threads, buffers pre-allocated | 710.2 ms | MEASURED |
| Speedup, GPU fused vs best parallel CPU | **173×** | DERIVED |

**As a fraction of the pipeline** (DERIVED; decode from M1 at 29.7 ms/frame cold /
15.2 ms/frame warm, upload at the best rate `wgpu` gives, alignment from fact 15 at the
14.5 ms/frame midpoint):

| Stage, 22 frames | Cold | Warm |
| --- | ---: | ---: |
| Decode | 653 ms | 334 ms |
| Host→device upload (1.351 GiB) | 60 ms | 60 ms |
| Alignment (fact 15, 13–16 ms/frame) | 286–352 ms | 286–352 ms |
| **Focus + merge, fused (variant A)** | **4.1 ms** | **4.1 ms** |
| **Total** | **≈1036 ms** | **≈717 ms** |
| **Whole focus+merge stage as a fraction** | **0.40%** | **0.57%** |
| **Fusion prize (B − A) as a fraction** | **0.14%** | **0.20%** |
| Fusion prize vs full volume (C − A) | 0.16% | 0.23% |
| Fusion prize, two measures (E − D) | 0.34% | 0.50% |

---

## 2. Why you should believe the timings: the controls

SYNTHESIS §5 requires a null and a positive control before a timing number means
anything. Both are here, and both are run *inside the same process and the same
allocation* as the headline, so they cannot be reconciliation artefacts across runs.
All MEASURED, `results-controls.txt`, n = 50.

### 2.1 The null — what a dispatch costs when it does nothing

One dispatch of the full 110 × 293 = 32,230-workgroup grid, whose kernel reads its
invocation id and returns:

```
gpu  ms: n=50  min 0.019  med 0.020  mean 0.020 ± 0.001  p95 0.022  max 0.023
wall ms: n=50  min 0.066  med 0.102  mean 0.122 ± 0.089  p95 0.222  max 0.592
```

**0.0201 ms per dispatch** is the floor. A self-test (group 7) asserts the null kernel
leaves the selection buffer bit-identical, so it really is doing nothing (VERIFIED). For
variant A this floor accounts for 22 × 0.0201 = 0.44 ms, i.e. **11% of the 4.115 ms
headline is dispatch overhead, not work.** That matters for the interpretation: a large
part of the "prize" in the two-measure case is *dispatch count*, not bandwidth.

### 2.2 The positive control — bandwidth of known cost

Three of them, because the obvious one is wrong and saying why is the point.

| Control | Payload | GPU ms (median) | Rate |
| --- | --- | ---: | ---: |
| **READ** — every word of 22 frames read once, 22 *distinct* buffers | 1.351 GiB | 1.129 | **1284.6 GB/s** |
| COPY — the same words read and written | 2.702 GiB moved | 1.771 | 1638.4 GB/s |
| D2D — 16 × `copy_buffer_to_buffer` of 62.88 MiB | 0.982 GiB | 1.935 | 545.2 GB/s one-way, 1090.4 GB/s r+w |

**The COPY control is discarded as a reference and this is deliberate.** Its destination
is a single 62.88 MiB buffer, which fits inside the 5090's 96 MiB L2, so the write half
may never reach DRAM; 1638 GB/s is an L2-inflated number. Its read half (1.351 GiB across
22 distinct buffers) cannot be cached and puts a DRAM-traffic *floor* of 819.2 GB/s under
it. **The READ control is the reference used everywhere below**: its 1.351 GiB working
set across 22 separate allocations is 14× L2 and cannot be captured.

The READ control is also the positive control in the strict sense — its cost is
*predictable*. Predicted from the D2D rate, it should take 1.330 ms; it took 1.129 ms.
The two independent bandwidth measurements agree to 15%, and the faster one is the
compute path, which is expected (the copy engine is not the fastest way to move memory on
this part).

Against fact 10's MEASURED-LOCALLY 1503 GB/s device-to-device: fact 10's number counts
read + write, so the comparable figure here is the COPY control's 1638 GB/s (L2-inflated,
above it) or the READ control doubled. **The READ control at 1284.6 GB/s is 85% of fact
10's 1503 GB/s.** Fact 10 survives; a compute-shader read stream reaches 85% of what
whatever tool produced fact 10 reached. No contradiction (DERIVED).

### 2.3 The host→device control, and an unexpected finding

Two paths, because the first one is bad and it would be dishonest to quote only it.

```
(a) queue.write_buffer, 22 frames      : 249.3 ms median -> 5.8 GB/s
(b) mapped staging buffer:
      host memcpy into the mapping     :  54.0 ms  (25 GB/s class)
      copy_buffer_to_buffer after it   :   5.8 ms  -> 250.3 GB/s
      end to end                       :  59.8 ms -> 24.3 GB/s
```

250 GB/s for the buffer-to-buffer copy is **impossible over PCIe 5.0 x16** (~63 GB/s
theoretical). The only consistent reading is that the `MAP_WRITE | COPY_SRC` buffer
`wgpu` handed back is **device-local host-visible memory (ReBAR)**: the host `memcpy` at
~25 GB/s *is* the PCIe transfer, and the copy that follows is device-to-device. **The
honest end-to-end `wgpu` H2D rate on this machine is 24.3 GB/s** (MEASURED), against fact
10's 56.9 GB/s. That is a 2.3× shortfall, and it is an **API ceiling, not a hardware one**
(ARGUED): `wgpu` exposes no pinned-host-allocation + async-copy-engine path, which is how
CUDA reaches 56.9 GB/s. `queue.write_buffer` is 4× worse still and should not be used for
bulk uploads.

This does not affect any conclusion below — upload is 60 ms against a ~1000 ms pipeline
either way — but it is a real constraint on any `wgpu`-based design and it should be in
the corpus.

### 2.4 Nothing spilled to system RAM

The Windows/WDDM silent-spill hazard is real and a previous measurement on this machine
lost a day to it. Two independent checks:

- `nvidia-smi` total VRAM before/after allocation, reported on every run. 22 frames:
  2396 → 6108 MiB (delta 3712 MiB against a 2295 MiB model, the excess being the
  6.45 GiB-class staging buffer and allocator granularity). 105 frames: 2400 →
  19296 MiB (delta 16896 MiB against a 10123 MiB model plus a 6447 MiB staging buffer =
  16570 MiB — agreement to 2%). No delta came in *under* the model, which is the spill
  signature.
- **The decisive one:** the achieved rates are 705–1429 GB/s. A buffer that had spilled
  to system RAM would be read across PCIe at ≤63 GB/s. **The measurement is 11–23× faster
  than PCIe. Nothing spilled** (DERIVED). This argument is stronger than the
  `nvidia-smi` delta and does not depend on it.

`nvidia-smi --query-compute-apps` returns nothing for a Vulkan process on Windows/WDDM,
so per-process attribution is unavailable; only the total delta is (MEASURED — the code
tries and reports `None`).

---

## 3. Why you should believe the kernel: numerical verification

**A fast wrong kernel is worthless.** The port was verified before it was timed.

### 3.1 The tolerance required, and why

The focus field is not an output. It is fed to an argmax over frames. **The only
difference that can matter is one that changes a winner index.** So the tolerance is
stated at two levels:

1. *Field level:* the GPU must be **no further from f64 truth than the CPU is**. This is
   the right test, not "GPU ≈ CPU": the CPU reference is itself an fp32 computation with
   its own error, and a GPU that merely reproduced the CPU's errors would be no better.
2. *Merge level:* the fraction of pixels whose winner changes, and the top-2 focus margin
   at those pixels — because a winner flip where the top two candidates are separated by
   1e-8 is a tie, not an error.

### 3.2 The exactness argument the kernel rests on (VERIFIED)

Green luma is `L = (G1 + G2) / 2` with `G1, G2` integers in `[0, 14848]` (white 15360
minus black 512). Every `L` is therefore a multiple of 0.5 and at most 14848. A
7-element box sum is at most 103,936; the separable second pass sums seven of those, at
most 727,552. Every multiple of 0.5 up to 2²³ × 0.5 = 4,194,304 is exactly representable
in f32. **Every partial box sum in this kernel is exact, regardless of the order the
threads accumulate in.** Self-test group 1 checks this empirically over 200,000 random
49-element draws: worst |f32 − f64| = **0e0** (VERIFIED). This is why the GPU's completely
different summation order — separable, in shared memory, across a 38×14 tile — is not a
source of error at all.

### 3.3 The one real numerical defect, and its diagnosis

The first version of the kernel gave a **non-zero focus value on a perfectly flat plane**,
where the ring difference is identically zero. The error was 1.1403739e-5. Multiplied by
the plane's `sigma` (21.4088) that is 2.44140625e-4 — **exactly 1 ULP of 4000**, the
plane's luma value.

Diagnosis: **the Vulkan specification permits 2.5 ULP of error in fp32 `OpFDiv`**, while
the CPU reference divides `f64 sum / f64 count` and rounds once. In a *difference of two
nearly-equal means* the cancellation is catastrophic: a 1-ULP absolute error in a ~4000
DN mean becomes a ~5.4e-5 *relative* error in the ring.

The fix is the classical division-residual refinement, applied at all four division sites:

```wgsl
fn div_rn(p: f32, d: f32) -> f32 {
    let q0 = p / d;
    let r  = fma(-d, q0, p);   // exact residual, by Sterbenz + the FMA
    return q0 + r / d;         // one Newton step: correctly rounded in practice
}
```

Result (MEASURED, self-test group 3, and the reason `m_fast` exists at all):

| | raw fp32 divide | `div_rn` |
| --- | ---: | ---: |
| bit-identical to CPU (synthetic) | 32.59% | **78.30%** |
| max abs difference | 4.005e-5 | **1.526e-5** |
| flat plane → 0 | no | **yes, exactly** |

**And it costs nothing: variant F (raw divide) is 4.113 ms against variant A's 4.115 ms,
a 0.07% difference and well inside the run-to-run spread** (MEASURED). Exactness is free
here precisely because the kernel is bandwidth-bound — see §4.

### 3.4 Agreement on real frames (MEASURED)

22 frames of `109MSDCF`, 181,313,088 plane pixels (`results-verify.txt`):

```
overall: 71.951236% of 181313088 plane pixels bit-identical
         worst relative GPU-CPU difference 2.373e-7   (i.e. ~2 ULP of f32)
worst absolute error against the f64 reference: GPU 1.341e-5, CPU 1.341e-5
per frame: GPU RMS vs f64 truth 3.0489e-6 ... CPU RMS vs f64 truth 3.0489e-6
```

**The GPU is exactly as close to f64 truth as the CPU is**, frame by frame, to five
significant figures — in three of 22 frames the GPU is marginally *closer*. The residual
28% of pixels differ by ≤ 2 ULP. Tolerance criterion 1 is met.

At the merge level, which is the level that matters:

```
winner index : 1 of 8241504 differ (0.000012%)
winning quad : 1 of 8241504 differ (0.000012%)
emitted green: 1 of 8241504 pixels differ, largest difference 9.0 DN
top-2 focus margin at the disagreeing pixel: 0.000  (6.62e-8 of the median focus, 0.9000)
```

**One pixel in 8.24 million**, and at that pixel the top two candidate frames are
separated by 6.6e-8 of a typical focus value — it is a numerical tie, and which frame
wins is arbitrary in both implementations. The emitted green differs by 9 DN out of a
14848 DN range at that single pixel. Tolerance criterion 2 is met.

Cross-check on a different stack, ISO and aperture (`119MSDCF`, f/5.6, ISO 50, 6 frames,
`results-verify-119.txt`): 82.77% bit-identical, GPU and CPU RMS vs truth identical to
five figures, and **0 of 8,241,504 winner indices differ, largest emitted green
difference 0.0 DN.**

### 3.5 The rest of the self-test suite (VERIFIED, all 18 assertions pass)

`results-selftest.txt`. The ones that are load-bearing:

- **flat plane → exactly zero focus everywhere, borders included.** The border is where a
  clamped box filter is easiest to get wrong; the divisor must be the *clamped* count.
- **fused and unfused produce bit-identical focus and identical winner maps** (0 differing
  pixels). This is what licenses treating fusion as an implementation detail rather than a
  different answer — and therefore what licenses reading B − A as a pure cost difference.
- **every tie goes to the lower frame index** (768/768), matching `Selection::beats`.
- **GPU fused merge == CPU `Selection::fold`** on synthetic data, 0 differing pixels.
- the two ranking properties `focus.rs` asserts (sharper edge scores higher; the same
  contrast scores lower at a higher signal level) re-asserted on the GPU.
- the **diagnosis check** of §3.3, which fails if the `div_rn` story is wrong.

Two of these tests were themselves defective when first written, and finding that out was
part of the work. The tie-break test used a sentinel value that the generator could
legitimately produce. The "sharper frame wins" test used a linear ramp — and a symmetric
box mean of a linear function equals its centre value, so the ring difference is
identically zero in the interior and *every* interior pixel tied. The 39.06% pass rate
that resulted matched the border-band fraction exactly, which is how it was caught.

---

## 4. Bandwidth-bound or compute-bound? The arithmetic

**MEASURED conclusion: bandwidth-bound, at 84% of the measured DRAM read ceiling.**
Here is the arithmetic, built entirely from the two controls that `measure` re-runs
*inline*, in the same process and the same allocation as the headline (null 0.0193 ms,
read 1285.0 GB/s — within 0.03% of the standalone control battery's 1284.6 GB/s in §2.2,
which is a useful cross-run reproducibility check in its own right).

**Halo amplification (DERIVED).** A workgroup of 32×8 threads produces a 32×8 plane tile.
With `OUTER_RADIUS = 3` it must load a 38×14 plane tile — 532 plane pixels — to produce
256 outputs. Each plane pixel costs two 32-bit words (the packed CFA quad). So the
kernel's L1-request traffic is **532/256 = 2.078×** the minimum:

```
tile loads      : 532 px x 8 B x 32230 workgroups = 130.8 MiB/frame x 22 =  2.811 GiB
selection reads : 2 x 31.44 MiB/frame                          x 22 =  1.351 GiB
                                                              total =  4.161 GiB
```

At the READ control's 1285.0 GB/s that is **3.477 ms**. Add the null control's dispatch
floor, 22 × 0.0193 = **0.425 ms**. **Predicted 3.902 ms. Measured 4.115 ms. Ratio 1.055.**

A model built from two independent controls predicts the headline to **5.5%** without a
single fitted parameter.

**And it predicts the prize too.** The prize is nothing but one extra round trip of the
focus field through memory: 2 × 31.44 MiB × 22 = 1.351 GiB, which at 1285.0 GB/s is
1.128 ms, plus 22 extra dispatches at the null floor = 0.425 ms, **predicted 1.553 ms
against a measured 1.453 ms (ratio 0.935)**. The fusion prize is *exactly* what the
bandwidth model says it should be. There is no hidden compute prize inside it.

**Achieved rate:** 4.161 GiB in 4.115 ms = **1085.7 GB/s**, i.e. **84% of the measured
1285.0 GB/s ceiling**. Compute-bound kernels do not sit at 84% of DRAM bandwidth.
Confirming evidence: making the arithmetic *more* expensive (variant F → A adds an FMA
and a second divide at four sites per pixel) costs 0.07%, which is within noise. The
arithmetic is free; the memory is everything.

### 4.1 It scales, and the model degrades in a specific, benign way

| Stack | Frames | A fused | B unfused | Prize | A ms/frame | Prize ms/frame | model ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `109MSDCF` f/11 | 22 | 4.115 | 5.568 | 1.453 | 0.1870 | 0.0660 | 1.055 |
| `119MSDCF` f/5.6 | 33 | 5.994 | 8.163 | 2.170 | 0.1816 | 0.0658 | 1.023 |
| `coffee-bean` f/8 | 105 | 14.908 | 19.139 | 4.232 | 0.1420 | 0.0403 | 0.801 |

All MEASURED (`results-measure-{109,119,coffee}.txt`). At 22 and 33 frames the prize per
frame is identical to three figures (0.0660 vs 0.0658 ms) and the model is accurate to
5%. At 105 frames the kernel goes *faster* than the DRAM model allows — 1430.5 GB/s of
modelled traffic against a 1285.8 GB/s ceiling, i.e. 111% — which can only mean part of
the traffic is being served from L2. The plausible candidate is the selection state
(4 arrays × 31.44 MiB), which is touched by *every* dispatch, unlike the frame buffers
which are touched once each; across 105 consecutive dispatches it has far more
opportunity to stay resident (ARGUED, not isolated). The relevant point for this report
is the direction: **at 105 frames the prize per frame falls to 0.0403 ms, so the deeper
the stack the *smaller* the fusion prize gets relative to everything else.** The 22-frame
number quoted in §1 is the *most favourable* case for fusion.

VRAM at 105 frames: 10,123 MiB modelled, 16,896 MiB delta including the 6.45 GiB staging
buffer, sustained rate 1430 GB/s. No spill (§2.4).

---

## 5. The primary result: what is the fusion prize actually worth?

### 5.1 The three plugin models, priced

| Plugin model | What the contributor supplies | Cost, 22 frames | Prize over fusion |
| --- | --- | ---: | ---: |
| **Fused** | WGSL that can be *spliced into* the merge kernel: a snippet operating on registers/shared memory, with the framework's tiling, halo and shared-memory layout imposed on it. | 4.115 ms | — |
| **Unfused / streaming** | Any compute kernel that writes an f32 focus field. The framework merges. | 5.568 ms | 1.453 ms |
| **Volume** | The same, but the framework keeps every field resident, so the plugin may do multi-pass work, cross-frame work, or anything else. | 5.799 ms | 1.684 ms |

**MEASURED. The most permissive plugin model there is — materialise the entire focus
volume — costs 1.684 ms more than the most restrictive one, on a pipeline whose other
stages cost about a second.**

### 5.2 Against the rest of the pipeline

For 22 frames (DERIVED from MEASURED inputs; sources in the table in §1):

```
decode        653 ms cold / 334 ms warm     (M1: 1.78 s / 0.91 s for 60 frames;
                                             re-measured here at 26.6-30.3 ms/frame)
upload         60 ms                        (§2.3, the best rate wgpu offers)
alignment     286-352 ms                    (fact 15: 13-16 ms/frame)
focus+merge     4.1 ms                      (this work)
--------------------------------------------------------------
total       ~1036 ms cold / ~717 ms warm

fusion prize  1.453 ms  =  0.14% cold, 0.20% warm
whole stage   4.115 ms  =  0.40% cold, 0.57% warm
```

At 105 frames the fusion prize is **0.090%** of the pipeline.

**The entire focus-and-merge stage is under half a percent of the pipeline. The part of
it that fusion recovers is one seventh of that.**

Even in the most fusion-favourable scenario measured — two focus measures, where fusion
saves 3.606 ms because it removes a whole extra kernel launch per frame *and* a whole
extra round trip — the prize is **0.34% of a cold pipeline**. And that scenario is itself
an argument *against* the constraint, not for it: multiple independent focus measures is
exactly the case a plugin system exists to enable, and it is exactly the case where
splicing several contributors' WGSL into one kernel is hardest to do safely (shared-memory
budget, register pressure, halo negotiation between measures with different radii).

### 5.3 The verdict on constraining contributors to WGSL

**Constraining third-party focus measures to spliceable WGSL is not justified by the
fusion prize.** (ARGUED, from MEASURED premises.)

The reasoning, laid out so it can be attacked:

1. The prize is **0.14–0.20%** of pipeline wall time for one measure, **0.34–0.50%** for
   two, and it *shrinks* with stack depth (§4.1). It is smaller than the run-to-run
   variance of the decode stage.
2. The prize is **entirely explained** by one extra memory round trip plus one extra
   dispatch (§4). There is no compute synergy being lost — no shared intermediate that
   fusion reuses, no algebraic simplification across the boundary. It is a pure I/O cost
   and it is priced at 1.128 ms of bandwidth plus 0.425 ms of launch overhead.
3. The constraint it buys is severe. Splicing means the contributor inherits the
   framework's tile size, halo width, shared-memory layout and register budget, cannot
   use multiple passes, cannot use a different data layout, cannot use a different
   precision, and cannot be tested independently of the merge. `INNER_RADIUS`/
   `OUTER_RADIUS` are already coupled to the merge's regulariser width by fact 25; a
   spliced interface would harden that accidental coupling into the ABI.
4. There is a defensible constraint hiding behind the indefensible one. The number that
   *is* two orders of magnitude is GPU versus CPU: **173× on wall clock** (§6). So the
   contribution rule that the measurement supports is **"your focus measure must run on
   the GPU and emit an f32 focus field"** — not "your focus measure must be a WGSL
   fragment we can paste into our kernel." The first buys 99.4% of the available win.
   The second buys the remaining 0.6% at the cost of the plugin model.

This bears directly on SYNTHESIS §3.4.1's blocking interface items. **B-items that assume
a spliced/fused contribution format should be re-opened**: the measurement that motivated
them does not support them.

Where fusion *is* still worth doing: as an **internal optimisation for the built-in
measure**, invisible to the interface. Self-test group 6 establishes that fused and
unfused give bit-identical results (VERIFIED), so the framework can fuse its own default
measure and fall back to the streaming path for plugins, with no behavioural difference
and no interface commitment. That is the design this measurement recommends.

---

## 6. Fact 21, and whether it survives

**Fact 21 (MEASURED) — "ring-difference focus measurement plus fold costs 196.8 ms/frame
against decode's 267.6 ms/frame."**

It survives *as a statement about the CPU implementation*, and it is superseded as a
constraint on the GPU design. Specifically:

1. **It is not wall-clock time per frame.** Measured here, the same work single-threaded
   is **64.3 ms/frame** (median 66.4, min 49.5, max 86.7; MEASURED) — 3.1× faster than
   196.8. Run 22-wide on 32 logical processors it takes **710.2 ms of wall clock for the
   whole 22-frame stack**, i.e. 32.3 ms/frame amortised, while consuming **16,961 ms of
   summed worker CPU time — 771 ms/frame**. Fact 21's 196.8 ms/frame sits between those
   two quantities and matches neither cleanly; it is a per-frame CPU-time figure measured
   under concurrency, which is the natural output of a profiler that sums thread time.
   That is a legitimate number for *"how much CPU does this stage consume"*. It is not a
   latency, and **it cannot be compared against a GPU kernel time**, which is what risk 10
   is about.
2. **The `196.8 / 267.6 = 74%` ratio is the load-bearing part and it is intact.** M2 §3
   defect 6 established that ratio. Nothing here contradicts it: on the CPU, focus+fold
   really is comparable in cost to decode. That is exactly why the stage was worth moving
   to the GPU.
3. **What does not follow is the architecture conclusion.** "Focus is 74% of decode on the
   CPU" does not imply "the GPU focus volume is expensive enough that fusing it with the
   merge is worth constraining an interface for." The GPU number is **4.115 ms for 22
   frames**, which is **0.6% of the CPU's 710 ms wall clock** and **0.4% of the pipeline**.
   Once the stage is on the GPU, its cost is not a design pressure at all.

**Explicit statement of conflict, as SYNTHESIS §5 requires:** this report does not
contradict fact 21's number, but it **contradicts the inference drawn from it in
SYNTHESIS §3.4 / risk 10**. Risk 10's own wording — *"the GPU contribution format is
being constrained by a CPU measurement"* — is confirmed. **Question 11 is answered: the
fusion prize is 1.45 ms out of ~1036 ms, and the answer is no.**

One caveat on my CPU numbers, stated because it is a weakness: this machine had
substantial concurrent load during the measurement (33% CPU from unrelated processes,
another agent building in the same repository). The single-thread per-frame distribution
was correspondingly wide (49.5–86.7 ms) and the 5-rep parallel figure varied 710–880 ms.
**All my CPU numbers should be read as upper bounds on CPU time.** They are quoted here
only as context; **no conclusion in this report depends on them.** The fusion prize is
GPU-versus-GPU, measured in the same process, seconds apart, with a spread of 0.5%.

---

## 7. What is still not verified

An honest list. None of these change the verdict, and all of them are stated so the next
person knows where to push.

1. **The residual ~28% of non-bit-identical pixels is not fully attributed.** §3.3 fixes
   the division; what is left is ≤ 2 ULP and the GPU is exactly as close to f64 truth as
   the CPU is, so it does not matter for the merge. But I did not isolate whether the
   remainder comes from Vulkan's 3-ULP `sqrt` or from the driver contracting
   `gain * s + rd2` into an FMA (naga emits no `NoContraction` decoration). **UNVERIFIED.**
2. **Alignment is not measured here.** The pipeline fractions use fact 15's 13–16 ms/frame
   as given. If alignment turns out to be much cheaper on the GPU too, every fraction in
   §5.2 grows — but so does decode's share, and the ordering does not change: the fusion
   prize would still be ~0.2% of a decode-dominated pipeline. **The verdict is not
   sensitive to this** (ARGUED).
3. **Decode is not re-measured against M1 rigorously.** I observed 26.6–30.3 ms/frame for
   22 frames with `rayon` across files, consistent with M1's cold 29.7 ms/frame. That is a
   consistency check, not a measurement. **UNVERIFIED as an independent decode number.**
4. **The prize is measured for *this* focus measure.** A contributor's measure with a
   larger radius, more passes, or a different access pattern would have a different
   unfused cost. What generalises is the *mechanism* — the prize is one round trip of an
   f32 field plus one dispatch, and both terms are computable in advance from the field
   size (§4). A measure that produced a much larger intermediate would have a
   proportionally larger prize. **The mechanism is MEASURED; its generalisation is
   ARGUED.**
5. **No multi-GPU, no other vendor, no other driver.** Every number is one RTX 5090 on one
   driver via Vulkan. The bandwidth *model* should transfer; the constants will not.
6. **`wgpu`'s H2D ceiling of 24.3 GB/s is a measurement of `wgpu`, not of the hardware.**
   I did not attempt a native-Vulkan or CUDA-interop upload path, so I cannot say how much
   of the 2.3× gap to fact 10 is recoverable. **UNVERIFIED.**
7. **L2 behaviour at 105 frames is observed but not explained** (§4.1). The kernel exceeds
   the DRAM read ceiling, so something is being cached; I attribute it to the selection
   state but did not prove that. **ARGUED.**
8. **`wgpu` inter-pass barriers were established by reading `wgpu-core` 30.0.1 sources**
   (`src/track/mod.rs:341` `skip_barrier`, and `wgpu-hal`
   `src/vulkan/adapter.rs:3239`, which puts only `INCLUSIVE | MAP_WRITE` in the ordered
   mask, so a `STORAGE_READ_WRITE` transition always emits a real barrier). This means the
   unfused variants really do pay for a memory dependency between passes and are not being
   silently overlapped. It is a **VERIFIED** reading of the source, not a measurement of
   the driver's emitted command stream.
9. **The CPU baseline is contended** (§6). Upper bound only.
10. **No timing was collected with the GPU in a fixed clock state.** Clocks were left in
    the default dynamic mode. The 0.5% spread on 30 reps suggests this is not a
    significant source of error, but it was not controlled.

---

## 8. How to quote this result

> The ring-difference focus measure plus merge, fused into a single `wgpu` compute pass,
> costs **4.115 ms for a 22-frame A7C II stack resident in VRAM** (MEASURED, RTX 5090,
> median of 30, ±0.005 ms; M7). It is **bandwidth-bound at 84% of the measured 1285 GB/s
> DRAM read ceiling**, and a model built from a null and a read control predicts it to
> 5.5% with no fitted parameters. Running the focus measure as a **separate pass that
> writes a focus field to memory costs 5.568 ms** — so the **fusion prize is 1.453 ms,
> which is 0.14% of a cold 22-frame pipeline** and falls to 0.09% at 105 frames (MEASURED,
> M7). **That is not enough to justify constraining plugin authors to spliceable WGSL.**
> The defensible constraint is "run on the GPU and emit an f32 focus field", which is
> worth 173× against the CPU and costs the plugin model nothing.

---

## 9. Reproducing it

`cargo` is not on PATH in a fresh PowerShell.

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;$env:PATH"
cd projects\strehl\experiments\m7-gpu-focus
cargo build --release

# 0. 18 assertions, 7 groups, no camera data needed.                      (~25 s)
.\target\release\m7-gpu-focus.exe selftest

# 1. Null, D2D, read, copy and both H2D controls. Section 2.               (~60 s)
.\target\release\m7-gpu-focus.exe controls "C:\dev\macro\test\109MSDCF" --limit 22

# 2. Numerical verification against the CPU reference and f64 truth. Section 3.
.\target\release\m7-gpu-focus.exe verify "C:\dev\macro\test\109MSDCF" --limit 22
.\target\release\m7-gpu-focus.exe verify "C:\dev\macro\test\119MSDCF" --limit 6

# 3. The headline table, the fusion prize and the bandwidth model. Sections 1, 4, 5.
.\target\release\m7-gpu-focus.exe measure "C:\dev\macro\test\109MSDCF" --limit 22 --reps 30

# 4. Scale checks. Section 4.1.
.\target\release\m7-gpu-focus.exe measure "C:\dev\macro\test\119MSDCF"    --limit 33  --reps 20
.\target\release\m7-gpu-focus.exe measure "C:\dev\macro\test\coffee-bean" --limit 105 --reps 20

# 5. The CPU baseline alone. Section 6.
.\target\release\m7-gpu-focus.exe cpu "C:\dev\macro\test\109MSDCF" --limit 22
```

Captured output for every command is in `experiments/m7-gpu-focus/results-*.txt`.

**Provenance of the CPU reference.** `experiments/m7-gpu-focus/src/cpu.rs` is a
behavioural copy of the relevant parts of `crates/strehl-core` — `PlaneGeometry`, `Noise`,
`box_mean`, `FocusField`, `green_luma`, `Selection` — taken from commit
**`037d966e03f7931d6b2311585dc3147ee1d9233b`**. It is a *copy*, not a dependency, so that
concurrent edits to `crates/strehl-core/src/focus.rs` cannot silently move this
measurement's baseline. Nothing under `crates/` was modified.

**Read-only discipline.** `C:\dev\macro` and `D:\macro-dark-frames` were opened for
reading only; the experiment writes exclusively inside
`experiments/m7-gpu-focus/`. Verified after the fact by comparing recursive file counts
and latest write times under `C:\dev\macro`.

**Rule 7.** The decoder in `src/decode.rs` packs the **active area only** (7032×4688 out
of the 7168×5120 padded buffer) before anything is measured, so the zero padding is not
present in either the CPU or the GPU path. There is no padding in the measured buffers to
accidentally treat as image data.

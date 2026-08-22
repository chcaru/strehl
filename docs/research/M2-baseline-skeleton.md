# M2 — Walking skeleton: the naive argmax baseline (MEASURED)

Date: this session. Machine: Ryzen 9 9950X3D / 64 GB / RTX 5090, Windows 11.
Tool: `strehl stack` (Rust 1.98.0 MSVC, `--release`), `rawler` 0.7.2, `tiff` 0.11.3.
Corpus: `C:\dev\macro\test\109MSDCF` — 22 ARW, 836,440,064 bytes, in-camera focus
bracket, ISO 160, macro of overlapping acrylic paint strokes on paper.

This is SYNTHESIS §8 step 0. It implements the **per-pixel argmax selector** —
the exact defect this project exists to remove — because until it exists there is
nothing to measure against. Every claim below is labelled.

> **This document has been independently verified and revised.** A second agent
> re-derived every headline number from the raw files without trusting this text
> (`M2-verification.md`). The headline reproduced digit-for-digit and its cause
> was *proven* by controls this author had failed to run. **Eight supporting
> claims were wrong and are corrected in place** — see §5 for the full list and
> the retractions. Nothing here quietly changed: every correction says what it
> replaced.
>
> **Do not quote from any earlier revision of this file.** In particular the
> "1.13x hard floor" is retracted outright (§3.2.3).

---

## 1. What was built

`strehl stack <DIR> --out <PATH> [--limit N] [--srgb] [--index-map <PATH>] [--flat-roi X,Y,W,H]`

Per CFA plane at 3516 x 2344 (active 7032 x 4688 halved):

1. `L = (G1 + G2) / 2`, black-subtracted.
2. `raw = |mean(L, 3x3) - mean(L, 7x7)|` — difference-of-box-means bandpass,
   separable running sums, borders clamped to the plane.
3. `focus = raw / max(sigma, 1e-3)` where `sigma` comes from the injected
   `NoiseModel` at that pixel's signal level.
4. Per-pixel argmax over frames. First frame wins ties. No smoothing, no top-k,
   no regularisation.
5. Output: 16-bit RGB TIFF, `R` = R, `G` = (G1+G2)/2, `B` = B, all from the
   winning frame — **binned from one real 2x2 quad, not demosaiced.**

**Status: VERIFIED.** `cargo fmt --check`, `cargo clippy --all-targets -- -D
warnings` and `cargo build --release` all exit 0; `cargo test` is 58 passed /
0 failed (was 11 before this milestone, 52 at first publication — §5 explains
the six added after verification found the headline had no regression test).

### 1.1 What it is not

- **Not demosaiced.** Each output pixel is one physical quad. There is no
  interpolation, so no demosaic artifact contaminates the baseline. The cost is
  half linear resolution.
- **Not colour-managed.** White balance is applied as a green-normalised
  per-channel gain; no camera-to-sRGB matrix. Output is camera RGB. Colours are
  plausible but not colorimetric. `--srgb` applies only the transfer curve, for
  looking at — not for measuring.
- **Not aligned.** Frames are used as decoded. M3 measures the inter-frame
  motion in this bracket as a 4-parameter similarity with **-1.835% total scale
  drift and no measurable rotation**, i.e. up to ~39 px of displacement at the
  plane corner between frame 0 and frame 21. The skeleton does not compensate
  for that, by design — exposing it is part of the baseline's job. §3.2.3 and
  §3.2.4 test whether it contaminates the headline measurement (it does not —
  drift's measured contribution is *negative*).

---

## 2. Throughput (MEASURED)

Three consecutive runs, all 22 frames, warm-ish page cache (see §2.1):

| Run | Wall | ms/frame | MB/s | Peak RSS |
| --- | --- | --- | --- | --- |
| 1 | 1.049 s | 47.7 | 797.3 | 4,194 MB |
| 2 | 1.065 s | 48.4 | 785.5 | 4,182 MB |
| 3 | 1.101 s | 50.0 | 759.6 | 4,195 MB |

Work summed across workers, run 1: decode 5.554 s (252.5 ms/frame), focus+fold
4.131 s (187.8 ms/frame). Against 1.049 s wall that is **9.2x effective
parallel overlap**. Output write: 0.14 s for 66 MB of TIFF.

**Focus+fold costs ~74% of decode** — 73.2%, 74.4% and 79.6% across the three
runs — which is **42% of total CPU**. The bandpass is not free, and it is the
cheapest focus measure anyone would consider. Any focus-measure bake-off that
assumes measurement is negligible next to decode is wrong on this hardware.

> **CORRECTED.** This document originally said "focus+fold is 41% of decode".
> That was "% of total CPU" mislabelled as "% of decode", and it understated the
> cost of the focus measure by a factor of ~1.8. Found by the independent
> verification; re-measured here. `SYNTHESIS.md` fact 21 carries the corrected
> figure.

### 2.1 The cache caveat

**Status: UNVERIFIED as a cold number.** M1's headline 1245 MB/s was a true cold
parallel read. These runs are not cold: the files had been read earlier in the
session, and a concurrent read-only benchmark was decoding the same ARWs. The
first run of the session (20 of 22 files never read) also gave 835.5 MB/s, so
~800 MB/s is the best estimate, but it is **below** M1's 1245 MB/s cold-parallel
decode-only figure — which is expected, since this pipeline also does the focus
computation and the fold, and it caps concurrency at 11 workers rather than
letting rayon use all 32 threads.

### 2.2 Memory: the streaming bound holds, with far less headroom than published

**Status: MEASURED.** Peak working set polled externally from the OS
(`Start-Process -PassThru`, `PeakWorkingSet64` sampled every 10-20 ms until
exit). The frame count is varied with `--limit` over a 220-file scratch corpus
built by replicating the 22 ARWs, so every frame is the same size and geometry.

| Frames | chunks (`WorkerPlan`) | in-flight peak (instrumented) | peak RSS |
| --- | --- | --- | --- |
| 22 | 11 | 11 | 4,192 MB |
| 44 | 15 | 15 | 5,440 MB |
| 100 | 20 | 20 | 7,614 MB |
| 200 | 20 | 20 | 7,615 MB |
| 220 | 20 | 20 | 7,616 MB |

**The architectural claim is confirmed exactly.** Peak RSS stops growing at
N=100 and is flat to N=220 — three more frames per chunk cost nothing, because
each worker still holds one frame at a time. Memory is O(workers), never O(N).

**The headroom claim was wrong, and wrong in the unsafe direction.** The
worker count is `min(budget / per_worker, cpus, frames)` = `min(20, 32, N)`, so
it saturates at **20**, not at the 11 this stack happens to use. At saturation
the real peak is **7,616 MiB against SYNTHESIS §3.2's 8 GB ratchet.** Read as
binary that is 576 MiB of headroom — **7%, not the 3.8 GB this document
originally claimed.** Read as decimal it is 7.99 GB against 8.0 GB, i.e. none at
all. **The ratchet does not currently say which it means, and at this margin it
has to.**

> **CORRECTED, twice over.** The original text said "the same binary at 200
> frames still holds 11 in flight" and "the 8 GB ratchet survives with 3.8 GB of
> headroom … at any N". Both were false: 11 is an artifact of N=22, and the
> ratchet survives at large N with 5% margin. The independent verification
> caught the first from the arithmetic and measured 15 at N=44; the second is
> new here, from running to N=220.

**This is a live defect in the tool, not only in the document.**
`MEMORY_BUDGET_BYTES` is 6 GB and `per_worker_bytes` is 321 MB, so the plan
*believes* 20 workers cost 6.4 GB. They actually cost 7.6 GB: `per_worker_bytes`
counts this crate's own buffers but not `rawler`'s internal decode scratch or
allocator retention, so the budget under-predicts real RSS by **27%**. A machine
with a larger budget, or a decoder that scratches harder, breaches the ratchet
silently. The fix is to make `per_worker_bytes` account for decode scratch
rather than to lower the constant, but that is a change to an
irreversible-decision ratchet and is left for the owner rather than made here.

### 2.2.1 Peak RSS depends on thread count, which is why two honest measurements disagreed

The independent verification measured **1.81–1.94 GB** at 22 frames over 9 runs.
Re-measured here with the same method, 8 runs give **4,182–4,199 MB**. Both are
reproducible; they are measuring different configurations.

Peak RSS tracks the number of frames *concurrently in flight*, and that is
`min(chunks, rayon threads)` — so restricting rayon restricts memory:

| `RAYON_NUM_THREADS` | in-flight peak | peak working set | peak private |
| --- | --- | --- | --- |
| 1 | 1 | 833 MB | 795 MB |
| 3 | 3 | 1,703 MB | 1,594 MB |
| default (32) | 11 | 4,196 MB | 3,816 MB |

**Status: MEASURED for the table, ARGUED for the explanation.** The verification
also ran the determinism check at `RAYON_NUM_THREADS=3`, and 1.81–1.94 GB is
within noise of this machine's 1.70 GB at 3 threads while being 2.3x below its
default-thread figure. The most economical explanation is that the RSS runs
inherited that environment variable. Working set and private bytes agree to 9%,
so neither figure is inflated by file-backed pages.

The verification's proposed *mechanism* — "fewer than 11 chunks ever fold
concurrently, so the 11-in-flight peak precedes the accumulator allocations" —
is refuted: the in-flight counter is instrumented around the decode and the
explicit `drop`, and if only decode buffers were resident at the peak, 11 frames
would cost 11 x 73.4 MB = 808 MB rather than the observed 4.2 GB. The observed
~380 MB per in-flight frame is close to the 321 MB `WorkerPlan` predicts for a
frame *plus* its accumulators.

None of this rescues the original 3.8 GB headroom claim, which §2.2 retracts on
stronger grounds than the verification used.

### 2.3 Determinism

**Status: VERIFIED.** Two runs — one on all 32 threads, one restricted to 4
logical CPUs — produced **byte-identical** output and index maps (SHA-256
`3C9A08EA…` and `7C1247B6…`). Rayon's `reduce_with` combines partials in
work-stealing order, so changing the core count genuinely changes the reduction
tree; identical output across both is real evidence the reduce is
order-independent. Independently reproduced: the verification obtained both
digests from a fresh build, and again at `RAYON_NUM_THREADS=3`.

Partition-boundary associativity is covered by
`stack::tests::absorb_is_associative_over_every_contiguous_partition`, which
checks every contiguous 2-way cut in both reduction directions plus one 3-way
split. **It does not check every partition** — the name previously said it did.
Contiguous is what `par_chunks` actually produces, so it tests the cases that
can occur, and the name now says so.

---

## 3. The argmax defect, measured on our own data

This is the point of the milestone.

### 3.1 Index-map speckle: 34.381% (MEASURED)

Fraction of plane pixels whose winning frame index differs by more than 2 from
the median of their 3x3 neighbourhood: **34.381%**.

**This number is meaningless without its nulls, and was originally published
without them.** Against an implied null of 0% it sounds damning. The correct
no-information null is a winner map drawn i.i.d. from the *observed* winner
histogram, which does not know where anything is:

| Winner map | speckle |
| --- | --- |
| **real argmax — this baseline** | **34.381%** (34.385% excluding borders) |
| null: winners drawn i.i.d. from the observed winner histogram | 53.496% |
| null: uniform-random winners | 66.174% |
| argmax of a 17x17-regularised focus field | 0.868% |

Read correctly, 34.4% against a no-information null of 53.5% says the winner map
carries *some* spatial information and is nowhere near a depth map.

Looked at directly, the index map is unambiguous: coherent, smoothly banded
structure along the paint ridges where there is real contrast, and **full-range
salt-and-pepper** everywhere the surface is smooth.

**It is an upper bound on selector instability and nothing more.** It cannot
separate "argmax elected a noise spike" from "no frame is in focus here, so the
depth error is harmless". One partial defence exists: by 64x64 contrast decile
the figure is 38.6% in the flattest decile but still **21.7% in the busiest**,
with 8 of 10 deciles at 33–39%, so it is not purely a featureless-region
artifact. That is as far as it goes.

The nulls, the decile breakdown and the regularised figure are from the
independent verification (MEASURED); the 34.381% is this tool's own output.

#### 3.1.1 A blind spot in the metric itself (MEASURED)

Covered by `stack::tests::alternating_columns_saturate_the_metric_but_a_
checkerboard_hides_from_it`. The 3x3 median makes the statistic **blind to a
checkerboard winner map** — the centre pixel's own value occupies the four
diagonals plus the centre, 5 of 9, and therefore *is* the median. Alternating
**columns** saturate the metric at ~100%; the higher-frequency checkerboard
scores 0% in the interior. The test proves it by scaling: the stripe count grows
with area (`w*h - h`) and the checkerboard count grows with perimeter
(`w + h - 2`, exactly half the border), which is only possible if the
checkerboard interior contributes nothing at any size.

So 34.381% is an upper bound on instability in general but **understates it in
the specific highest-frequency mode**. Recorded because it is a property of the
statistic, not a bug.

### 3.2 Flat-ROI noise penalty: 1.253x (MEASURED)

ROI `2272,1344,256,256` in plane coordinates, 65,536 px.

| Quantity | Value |
| --- | --- |
| Stacked green, **spatial** sd | **35.328 DN** |
| Single middle frame (11), same ROI, **spatial** sd | **28.201 DN** |
| **Ratio** | **1.253x** |
| Distinct winning frames inside the ROI | 22 of 22 |

**The stack is 25.3% noisier than one unstacked frame.** Stacking 22 exposures
of the same scene made the flat regions measurably worse than not stacking at
all. Every one of the 22 frames wins somewhere inside a 256 x 256 patch of
featureless paper.

Independently reproduced digit-for-digit from the raw files by a second agent
that did not use this code, and reproduced again here after the §5 refactor —
both output digests are unchanged.

**How the ROI was chosen.** The green channel was box-downsampled 16x to
suppress per-pixel noise, and 256 x 256 blocks were ranked by the residual
standard deviation of the downsampled block — i.e. by *scene structure*,
deliberately not by stacked noise, which would have biased the ratio downward.
`2272,1344` is the flattest block available closest to the plane centre.
Independently checked: an unrelated flatness search ranks it **51st of 26,724**
blocks, and **no** block is simultaneously flatter and closer to the plane
centre. It was not cherry-picked.

**The control frame is the conservative choice, not a flattering one.**
Per-frame spatial sd in this ROI across all 22 frames: min 22.852 (frame 21),
median 25.347, max 29.560 (frame 10). **Frame 11 at 28.201 is the 4th-noisiest
of 22**, because single-frame sd here tracks how in-focus the paper fibre is and
frame 11 sits near the focus peak. Against the min / median / max the ratio
would have been 1.546x / 1.394x / 1.195x.

#### 3.2.1 The model prediction is a different physical quantity (CORRECTED)

This document originally tabulated the noise model's **19.267 DN** next to the
measured **28.201 DN** with no comment, leaving a 1.46x gap that reads as a
model failure. It is not one. The two are not the same quantity:

- **19.267 DN is a *temporal* per-sample sigma** — the spread you would see at
  one fixed pixel across repeated exposures.
- **28.201 DN is a *spatial* sd** over 65,536 different pixels, and it contains
  noise **plus** whatever scene structure the ROI still has.

Matched properly they agree to **1.01x**: an Immerkaer 3x3-Laplacian high-pass
of frame 11 over the same ROI gives **19.473 DN** against the model's 19.267.
Validated synthetically — inject a true sigma of 19.267 plus 20.4 DN of smooth
structure and the high-pass estimator recovers 19.288 while the spatial sd rises
to 28.103, matching the observed 28.201. **The noise model is fine and the
sigma is fine; the ROI simply is not flat enough for the two to be equal.**

This is the same spatial-versus-temporal conflation that got the prior corpus's
1.10x claim retracted, committed again here by an author who had read the
retraction. It is now `AGENTS.md` rule 10. The tool's `--flat-roi` output now
prints the distinction inline so the next reader cannot make it.

#### 3.2.2 Structure correction: ~1.48x (MEASURED / DERIVED)

**This 1.253x is a lower bound.** No region of a real macro photograph is
perfectly flat, and residual scene structure is common to both measurements, so
it inflates both sigmas and drags the ratio toward 1.0.

The residual structure in this ROI is **~20.4 DN**, about half the ROI's
variance, obtained as ROI variance minus Immerkaer high-pass variance on frame
11. Removing it in quadrature from both sides gives **1.48x at `2272,1344`** and
**1.49x at `2352,1408`**.

> **CORRECTED.** The original figure was 10.93 DN, from a 16x box downsample.
> A 16x downsample cannot see pixel-scale paper fibre, which the 1:1 crop shows
> plainly; it was about **2x low**. The consequence is that the honest corrected
> ratio is 1.48x, not the 1.29–1.31x published — **the result is stronger than
> was claimed**, and 1.48x is exactly this document's own originally-discarded
> "correction B".

**~1.48x is the honest figure**, and it sits between two biased estimators for a
known reason: argmax's excess is **spatially correlated over 3–7 px, not white**
(the ring-difference measure has `INNER_RADIUS 1` / `OUTER_RADIUS 3` support), so
a high-pass view *understates* argmax damage while raw spatial sd *overstates*
the ratio through shared structure.

#### 3.2.3 What causes it: the merge rule, proven by controls (MEASURED)

Everything above is merely *consistent* with "argmax amplifies noise". None of
it isolates argmax as the cause, because the ROI has structure and the frames
are unaligned. The decisive experiment is to change **only the merge rule** and
keep the frames, the ROI, the drift and the structure identical:

| Merge rule | sigma (DN) | vs frame 11 |
| --- | --- | --- |
| single frame 11 (no stacking) | 28.201 | 1.000x |
| **argmax — this baseline** | **35.328** | **1.253x** |
| **unweighted mean of 22** | **15.050** | **0.534x** |
| median of 22 | 15.304 | 0.543x |
| **placebo** — the same winner map shifted by half a ROI: identical frame histogram, identical drift and defocus mixing, blind only to *this pixel's own noise* | **27.673** | **0.981x** |
| placebo — uniform-random frame per pixel | 26.411 | 0.937x |
| regularised — argmax of a 17x17-smoothed focus field | 30.305 | 1.075x |

Three steps:

1. **The mean lands at 0.534x.** Drift and scene structure by themselves push
   the ratio well **below** 1.0. They cannot be what pushes argmax above it.
2. **The placebo gives 0.981x.** A selector with argmax's exact frame-usage
   statistics, mixing the same defocus and the same misregistration, but
   decoupled from the pixel's own noise, is harmless. The noise-correlated
   excess is `sqrt(35.328² - 27.673²)` = **21.96 DN**.
3. Therefore **the 1.253x is caused by selection being coupled to per-pixel
   noise**, which is exactly the thesis.

Second flat ROI `2352,1408` reproduces it: argmax 1.263x, mean 0.506x.

**An N-sweep kills the drift hypothesis outright.** Centred on frame 11, drift
~0.771 px/step:

| N | total drift | argmax | mean |
| --- | --- | --- | --- |
| 3 | 1.5 px | **1.131x** | 0.820x |
| 5 | 3.1 px | 1.183x | 0.751x |
| 7 | 4.6 px | 1.213x | 0.703x |
| 11 | 7.7 px | 1.241x | 0.639x |
| 22 | 16.2 px | 1.253x | 0.534x |

Argmax is already above 1.0 at **N=3 with 1.5 px of total drift** and grows
monotonically in N — as argmax-over-N-noisy-statistics theory predicts, and as a
drift explanation does not.

**Status: MEASURED**, from the independent verification. These controls were not
run when this document was first written, which was its central weakness: it
asserted a cause it had not isolated.

> **RETRACTED — the "1.13x hard floor".** This document previously offered a
> worst-case-drift floor of 1.13x as its challenge-proof fallback, computed as
> `sqrt(excess² - (sqrt(2) x structure)²)` with structure = 10.93 DN. That
> argument consumes the structure figure §3.2.2 corrects. With the true 20.4 DN,
> `sqrt(2) x 20.4 = 28.9 DN` exceeds the observed excess of 21.3 DN and the
> identical argument yields **no floor at all** — it degenerates to 1.0. **Do
> not quote 1.13x.** The conclusion is not weakened, because the controls above
> defend it far better than the floor ever did: they do not bound drift's
> contribution, they *measure* it, and it is negative.

#### 3.2.4 The ratio does not track scale drift (MEASURED)

The scene's only genuinely flat regions are paper, and all of them sit 880+ px
from the plane centre; the centre itself is the dark paint crossing, which is
the busiest part of the frame. So "flat" and "central" could not both be
satisfied, and the question of whether drift was driving the number had to be
answered by measurement. Five ROIs, same size, spanning the available radii:

| ROI | radius | drift 0→21 | structure | raw ratio | structure-corrected |
| --- | --- | --- | --- | --- | --- |
| `1648,928` | 284 px | 5.2 px | 36.75 DN | 1.053x | 1.113x |
| `1824,1344` | 536 px | 9.8 px | 33.35 DN | 1.091x | 1.263x |
| **`2272,1344`** | **881 px** | **16.2 px** | **10.93 DN*** | **1.253x** | **1.292x*** |
| `2352,1408` | 982 px | 18.0 px | 10.44 DN | 1.263x | 1.303x |
| `2368,1408` | 996 px | 18.3 px | 10.50 DN | 1.265x | 1.305x |

Three independent reasons the trend is structure, not drift:

1. **Across the three flat ROIs, drift varies by 13% (16.2 → 18.3 px) and the
   ratio varies by 1% (1.253 → 1.265).** If drift set the number it would track
   drift. It does not.
2. **The low-drift ROIs are not flat.** Their raw ratios are lower because they
   carry 3x more scene structure, which is common to numerator and denominator
   and pulls the ratio toward 1.0. Correcting each for its *own* structure
   collapses the spread from 1.053–1.265 for every ROI that is actually flat.
3. **The N-sweep in §3.2.3 settles it directly**: at N=3 the total drift is
   1.5 px and the ratio is already 1.131x. Drift at that magnitude cannot
   produce it, and the plain mean over the *same* frames goes down, not up.

**Status: MEASURED for the table, ARGUED for the interpretation.** \* The
`structure` column is the 16x-downsample estimate this document originally used
and §3.2.2 shows to be ~2x low, so the last column is **not to be quoted** —
only the *relative* ordering across ROIs survives, which is all reasons 1 and 2
need. Reason 3, and not this table, is what answers the drift objection.

### 3.3 Against the prior corpus

The prior corpus put the argmax noise penalty at **1.82x** in flat areas. We
measure **1.253x raw, ~1.48x structure-corrected**.

**Status: ARGUED.** Same sign, same order of magnitude, smaller number. Three
plausible reasons, none of which rescue argmax: our stack is 22 frames rather
than a larger one (fewer frames to draw a spike from — the penalty grows with N,
since argmax over more samples reaches further into the tail, and §3.2.3's
N-sweep measures exactly that growth); our ROI is mid-tone paper rather than a
bright highlight; and our focus measure is noise-normalised, which is already a
partial mitigation that a plain gradient measure would not have. **The direction
is confirmed on our own sensor, with our own files: per-pixel argmax makes flat
regions worse than not stacking.** That was the central empirical claim the
project is built on and it is no longer borrowed.

### 3.4 Winner distribution (MEASURED)

Unimodal, peaking at frame 9 (9.57%), tapering to ~2% at both ends. The bracket
is well-centred on the subject and every frame contributes. This is the shape a
working focus bracket should produce, and it is the control that says the
speckle in §3.1 is a *selector* defect rather than a broken bracket or a broken
focus measure.

### 3.5 Regularising the selector helps, and is not enough (MEASURED)

Not planned, and load-bearing. Argmax of a **17x17-smoothed focus field**, on
the same frames and the same ROI:

| | speckle | flat-ROI ratio |
| --- | --- | --- |
| raw argmax (this baseline) | 34.381% | 1.253x |
| **regularised argmax** | **0.868%** | **1.075x** |
| unweighted mean | — | 0.534x |

`SYNTHESIS.md` §1.1(a) argued from review, not measurement, that the merge
reference must come from a regularised focus field rather than a raw per-band
argmax. That argument is now measured: regularisation removes 97% of the speckle
and more than half the noise excess.

**But 1.075x is still above 1.0.** A regularised selector is still a selector.
Only averaging goes below a single frame. **Both halves of the architecture are
required and neither alone suffices**: a regularised reference to stop the
selector electing noise, *and* a noise-gated estimator that averages wherever
the frames agree within the noise floor. A better selector is not enough.

This is `SYNTHESIS.md` fact 23. **Status: MEASURED**, from the independent
verification; not reproduced by this tool, which deliberately implements no
regulariser.

---

## 4. What this establishes for the design

**Status: ARGUED throughout this section.**

1. **The plumbing is real.** RAW files in, a correct photograph out, on the
   owner's own hardware and files, in ~1 s for 22 frames. Nothing in the
   end-to-end path is hypothetical any more.
2. **The baseline artifact now exists and is named.** `out\baseline-argmax.tif`
   with a fixed random-free procedure and byte-reproducible output. Every future
   quality claim is measured against it. Without this, "better" was unfalsifiable.
3. **The defect reproduces on our data at the predicted sign and order.** This
   is the strongest argument available for the whole thesis, because it is no
   longer a citation.
4. **The merge stage is the target, not the focus measure.** The focus measure
   here is crude and the winner distribution (§3.4) is nonetheless correct. What
   is broken is the *decision rule*, not the *evidence*. Improving the focus
   measure alone cannot fix §3.2 — a better measure still gets argmaxed, and
   §3.5 measures that directly: regularising the focus field leaves 1.075x.
5. **Focus computation costs ~74% of decode**, 42% of total CPU. Budget it. It
   is not free.
6. **A regularised selector is necessary and not sufficient** (§3.5). The
   architecture needs both a regularised reference and an averaging estimator.

---

## 5. Corrections and the tests that were missing

This document was independently re-derived from the raw files by a second agent
told not to trust it (`M2-verification.md`). **The headline survived
digit-for-digit and its cause was proven by controls this author had not run.
Five supporting numbers did not survive**, two of them wrong in the direction
that loses an argument. All are corrected above, in place, with the retraction
stated rather than the text quietly swapped:

| # | Was | Is | Where |
| --- | --- | --- | --- |
| 1 | residual structure 10.9 DN | **~20.4 DN**; corrected ratio **1.48x**, not 1.29–1.31x | §3.2.2 |
| 2 | "hard floor of 1.13x" | **retracted — no floor**; replaced by the mean/placebo controls | §3.2.3 |
| 3 | 19.267 vs 28.201 tabulated together | **different quantities**; matched properly they agree to 1.01x | §3.2.1 |
| 4 | peak RSS 4.12–4.20 GB, 3.8 GB headroom | **7,616 MiB at saturation, 576 MiB headroom**; RSS tracks thread count | §2.2, §2.2.1 |
| 5 | "still 11 in flight at 200 frames" | **15 at N=44, 20 at N>=100**, measured to N=220 | §2.2 |
| 6 | "focus+fold is 41% of decode" | **~74% of decode**, 42% of total CPU | §2 |
| 7 | 34.4% speckle, no null | no-information null is **53.5%**; upper bound only | §3.1 |
| 8 | test named "every partition" | renamed to **every contiguous partition** | §2.3 |

**The real defect was in the tests, not the arithmetic.** The 52 tests were all
synthetic unit tests of the library; **the headline number's own code path had
none**. `roi_green` and the ratio computation had zero coverage, and
`speckle_fraction`'s three tests did not pin its border convention. Fixed:

- The ratio computation is split out of the reporting into `flat_roi_stats`, so
  it can be called from a test rather than only from `main`.
- `a_single_frame_stack_has_a_flat_roi_ratio_of_exactly_one` — the identity
  check. The two sides of the ratio are produced by different code walking
  different data structures; stacking one frame must give exactly 1.000.
- `the_flat_roi_ratio_is_the_ratio_of_the_two_sigmas` — a winner 3x noisier
  reports exactly 3.000, with no sampling slack.
- `roi_green_is_hand_computable_and_never_reads_the_padding` — hand-computed
  interior and corner ROIs against a frame whose buffer is larger than its
  active area and whose active origin is not (0,0), with everything outside
  filled with a poison value.
- `roi_green_and_mean_and_sigma_recover_an_injected_noise_level` — a known
  injected sigma is recovered to 2%, and the G1/G2 average is shown to drop it
  by exactly sqrt(2).
- `the_border_convention_is_clamped_with_an_upper_median` and
  `alternating_columns_saturate_the_metric_but_a_checkerboard_hides_from_it` —
  §3.1.1.

**All six new tests were mutation-tested**, and one initially failed to earn its
place. Injected defects: wrong CFA offset in `roi_green` (caught, 2 tests);
transposed ROI walk in `flat_roi_stats` (caught); dropped black subtraction on
one side of the ratio (caught, 2 tests); `>` to `>=` on the speckle tolerance
(caught by an existing test); **lower median instead of upper (NOT caught)** —
the first border test fixed how *many* pixels speckle but not which, and the
count is identical under either convention. It was strengthened with an
asymmetric pattern that only the upper median satisfies, and now catches it.

Test count: 52 → 58. `cargo fmt --check`, `cargo clippy --all-targets -- -D
warnings` and `cargo test` are clean, and both published SHA-256 digests
reproduce unchanged after the refactor.

---

## What this does NOT show

- **No alignment, and the index map shows it.** M3 measures -1.835% scale drift
  across this bracket, up to ~39 px at the plane corner. Some of the §3.1
  speckle at large radius is therefore misregistration being selected rather
  than noise being selected, and the two are not separated here. §3.2.3 shows
  the *flat-ROI ratio* is not drift-driven — it measures drift's contribution as
  *negative* — but no equivalent control exists for the speckle percentage.
  **Treat 34.381% as an upper bound on selector instability**, bounded below by
  the 53.5% no-information null and blind to checkerboard modes entirely
  (§3.1.1). Re-measuring speckle after M3's alignment lands is the obvious
  follow-up.
- **`MEMORY_BUDGET_BYTES` under-predicts real RSS by 27%** (§2.2). Peak RSS is
  now measured to N=220 and the O(workers) bound is confirmed, but the tool's
  own budget arithmetic does not model the decoder's scratch, so the 8 GB
  ratchet is defended by 576 MiB rather than by the budget — and by nothing at
  all if the ratchet is read as decimal GB. Unfixed, deliberately — it is a
  change to an irreversible-decision ratchet, and the ratchet needs its units
  pinned down first.
- **The two RSS measurements have not been reconciled by the other party**
  (§2.2.1). The thread-count explanation is this author's, and is ARGUED.
  `SYNTHESIS.md` fact 22 currently carries the 1.81–1.94 GB figure and the "more
  headroom than published" reading, both of which §2.2 contradicts.
- **The noise model is `Provenance::Profile`, not calibrated.** The gain
  (ISO/436.8) is derived from white-level consistency, not a photon-transfer
  measurement, and read noise is a table entry. It is adequate for *ranking*
  focus across frames at a fixed pixel, which is all the skeleton consumes.
  M4 has since measured read noise and the dual-gain switch on dark frames, but
  the gain remains DERIVED and a photon-transfer curve still needs the flat
  fields requested in `captures-needed.md` §4.
- **The sigma normalisation in the focus measure is a proxy**, and is documented
  as such in `focus.rs`. The true variance of `(inner - outer)` is not the
  variance of a single pixel — the boxes average and they overlap. Only the
  cross-frame ranking at a fixed pixel is consumed, so the proxy is adequate
  here; the focus-measure bake-off must do it properly.
- **Argmax's excess is spatially correlated, not white**, over 3–7 px — the
  ring-difference measure's own support. High-pass views therefore understate
  argmax damage and raw spatial sd overstates the ratio through shared
  structure. ~1.48x is the honest figure between them, and it is a *range*
  narrowed by two biased estimators, not a directly measured quantity.
- **Single scene, single ISO, single camera, one 22-frame stack.** The mechanism
  is general and the N-sweep behaves as theory predicts; the specific numbers
  are not claimed to generalise.
- **No claim that this output is good.** It is deliberately the honest worst
  case. It is 25.3% noisier than doing nothing, in the places where doing
  nothing would have been fine.

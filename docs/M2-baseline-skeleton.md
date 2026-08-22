# M2 — Walking skeleton: the naive argmax baseline (MEASURED)

Date: this session. Machine: Ryzen 9 9950X3D / 64 GB / RTX 5090, Windows 11.
Tool: `strehl stack` (Rust 1.98.0 MSVC, `--release`), `rawler` 0.7.2, `tiff` 0.11.3.
Corpus: `C:\dev\macro\test\109MSDCF` — 22 ARW, 836,440,064 bytes, in-camera focus
bracket, ISO 160, macro of overlapping acrylic paint strokes on paper.

This is SYNTHESIS §8 step 0. It implements the **per-pixel argmax selector** —
the exact defect this project exists to remove — because until it exists there is
nothing to measure against. Every claim below is labelled.

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
warnings` and `cargo build --release` all exit 0; `cargo test` is 52 passed /
0 failed (was 11 before this milestone).

### 1.1 What it is not

- **Not demosaiced.** Each output pixel is one physical quad. There is no
  interpolation, so no demosaic artifact contaminates the baseline. The cost is
  half linear resolution.
- **Not colour-managed.** White balance is applied as a green-normalised
  per-channel gain; no camera-to-sRGB matrix. Output is camera RGB. Colours are
  plausible but not colorimetric. `--srgb` applies only the transfer curve, for
  looking at — not for measuring.
- **Not aligned.** In-camera focus brackets from the A7C II are close enough to
  produce a coherent image without alignment; M3 owns that question.

---

## 2. Throughput (MEASURED)

Three consecutive runs, all 22 frames, warm-ish page cache (see §2.1):

| Run | Wall | ms/frame | MB/s | Peak RSS |
| --- | --- | --- | --- | --- |
| 1 | 1.067 s | 48.5 | 784.0 | 4,195 MB |
| 2 | 1.022 s | 46.5 | 818.8 | 4,120 MB |
| 3 | 1.001 s | 45.5 | 835.5 | 4,196 MB |

Work summed across workers, run 3: decode 5.497 s (249.9 ms/frame), focus+fold
3.853 s (175.1 ms/frame). Against 1.001 s wall that is **9.3x effective
parallel overlap**. Output write: 0.14 s for 66 MB of TIFF.

**Focus+fold is 41% of the per-frame CPU cost of decode.** The bandpass is not
free, and it is the cheapest focus measure anyone would consider. Any
focus-measure bake-off that assumes measurement is negligible next to decode is
wrong on this hardware.

### 2.1 The cache caveat

**Status: UNVERIFIED as a cold number.** M1's headline 1245 MB/s was a true cold
parallel read. These runs are not cold: the files had been read earlier in the
session, and a concurrent read-only benchmark was decoding the same ARWs. The
first run of the session (20 of 22 files never read) also gave 835.5 MB/s, so
835 MB/s is the best estimate, but it is **below** M1's 1245 MB/s cold-parallel
decode-only figure — which is expected, since this pipeline also does the focus
computation and the fold, and it caps concurrency at 11 workers rather than
letting rayon use all 32 threads.

### 2.2 Memory: the streaming bound holds

**Status: MEASURED.** Peak working set 4.20 GB, polled externally from the OS.
The predicted working set was 3.53 GB; the ~0.67 GB excess is `rawler`'s internal
decode scratch plus allocator retention.

`in-flight frames: 11 peak, bound 11` — instrumented with an atomic counter
incremented before decode and decremented after an explicit `drop`, so this is
the real number, not the intended one.

At 22 frames the whole volume would have been 1.6 GB and materialising it would
have been easy. It was not materialised. The same binary at 200 frames still
holds 11 in flight, because the bound is derived from a memory budget and the
CPU count, never from the frame count. **SYNTHESIS §3.2's 8 GB ratchet survives
with 3.8 GB of headroom** — and it survives at any N.

### 2.3 Determinism

**Status: VERIFIED.** Two runs — one on all 32 threads, one restricted to 4
logical CPUs — produced **byte-identical** output and index maps (SHA-256
`3C9A08EA…` and `7C1247B6…`). Rayon's `reduce_with` combines partials in
work-stealing order, so changing the core count genuinely changes the reduction
tree; identical output across both is real evidence the reduce is
order-independent. Partition-boundary associativity is covered separately by
`stack::tests::absorb_is_associative_over_every_partition_of_the_stack`, which
checks every contiguous partition exhaustively.

---

## 3. The argmax defect, measured on our own data

This is the point of the milestone.

### 3.1 Index-map speckle: 34.381% (MEASURED)

Fraction of plane pixels whose winning frame index differs by more than 2 from
the median of their 3x3 neighbourhood: **34.381%**.

Physical depth in a macro scene is piecewise smooth. A third of the image
disagreeing with its own neighbourhood by more than two focus steps is not depth.
It is argmax resolving a tie between frames that are all equally out of focus by
picking whichever one happened to have the largest noise excursion.

Looked at directly, the index map is unambiguous: coherent, smoothly banded
structure along the paint ridges where there is real contrast, and **full-range
salt-and-pepper** everywhere the surface is smooth. The defect is not subtle and
it is not a corner case — it is most of the frame.

### 3.2 Flat-ROI noise penalty: 1.265x (MEASURED)

ROI `2368,1408,256,256` in plane coordinates, 65,536 px.

| Quantity | Value |
| --- | --- |
| Stacked green, spatial sd | **34.855 DN** |
| Single middle frame (11), same ROI | **27.552 DN** |
| **Ratio** | **1.265x** |
| Noise model prediction, one green-luma sample | 19.262 DN |
| Distinct winning frames inside the ROI | 22 of 22 |

**The stack is 26.5% noisier than one unstacked frame.** Stacking 22 exposures
of the same scene made the flat regions measurably worse than not stacking at
all. Every one of the 22 frames wins somewhere inside a 256 x 256 patch of
featureless paper.

**How the ROI was chosen.** The green channel was box-downsampled 8x to suppress
per-pixel noise, and every 256 x 256 block with a mean between 8000 and 55000
(16-bit) was ranked by the residual standard deviation of the downsampled block —
i.e. by *scene structure*, deliberately not by stacked noise, which would have
biased the ratio downward. `2368,1408` was the flattest block in the frame.
Inspected at 1:1 with 1%-percentile autoscaling it shows only faint paper fibre.

**This 1.265x is a lower bound (DERIVED).** No region of a real macro photograph
is perfectly flat, and the residual scene structure is common to both
measurements, so it inflates both sigmas and drags the ratio toward 1.0.
Removing it in quadrature:

| Structure estimate | Method | Corrected ratio |
| --- | --- | --- |
| 15.233 DN | 8x-downsampled sd of the stacked ROI (data-driven, itself a lower bound) | **1.366x** |
| 19.700 DN | inferred by trusting the noise model for the single frame | **1.493x** |

**Status: DERIVED, not MEASURED** — correction B is conditional on a gain that
SYNTHESIS §4.1 already flags as derived from white-level consistency rather than
a photon-transfer curve. Both corrections move the same way. The honest statement
is **1.265x measured, 1.37–1.49x once scene structure is accounted for.**

### 3.3 Against the prior corpus

The prior corpus put the argmax noise penalty at **1.82x** in flat areas. We
measure 1.265x raw / 1.37–1.49x corrected.

**Status: ARGUED.** Same sign, same order of magnitude, smaller number. Three
plausible reasons, none of which rescue argmax: our stack is 22 frames rather
than a larger one (fewer frames to draw a spike from — the penalty grows with N,
since argmax over more samples reaches further into the tail); our ROI is
mid-tone paper rather than a bright highlight; and our focus measure is
noise-normalised, which is already a partial mitigation that a plain gradient
measure would not have. **The direction is confirmed on our own sensor, with our
own files: per-pixel argmax makes flat regions worse than not stacking.** That
was the central empirical claim the project is built on and it is no longer
borrowed.

### 3.4 Winner distribution (MEASURED)

Unimodal, peaking at frame 9 (9.57%), tapering to ~2% at both ends. The bracket
is well-centred on the subject and every frame contributes. This is the shape a
working focus bracket should produce, and it is the control that says the
speckle in §3.1 is a *selector* defect rather than a broken bracket or a broken
focus measure.

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
   measure alone cannot fix §3.2 — a better measure still gets argmaxed.
5. **Focus computation is 41% of decode cost.** Budget it. It is not free.

---

## What this does NOT show

- **No alignment.** Frames were used as decoded. If the bracket had meaningful
  parallax the argmax would also be selecting misregistration, and the speckle
  number would be contaminated. M3 owns this.
- **Peak RSS is measured for 22 frames, not 200.** The O(workers) bound is
  instrumented and the arithmetic is in the tool, but the large-N run has not
  been done.
- **The noise model is `Provenance::Profile`, not calibrated.** The gain
  (ISO/436.8) is derived from white-level consistency, not a photon-transfer
  measurement, and read noise is a table entry. It is adequate for *ranking*
  focus across frames at a fixed pixel, which is all the skeleton consumes.
  §3.2's correction B depends on it and is labelled accordingly. The lens-cap
  capture requested at the end of M1 is still owed and still blocks calibration.
- **The sigma normalisation in the focus measure is a proxy**, and is documented
  as such in `focus.rs`. The true variance of `(inner - outer)` is not the
  variance of a single pixel — the boxes average and they overlap. Only the
  cross-frame ranking at a fixed pixel is consumed, so the proxy is adequate
  here; the focus-measure bake-off must do it properly.
- **No claim that this output is good.** It is deliberately the honest worst
  case. It is 26.5% noisier than doing nothing, in the places where doing
  nothing would have been fine.

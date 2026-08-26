# BUILD-HULL: the out-of-hull instrument for the real merge

Answers one question for a rendered stack: **does the output contain samples whose
value lies outside the range of the aligned input samples available at that sample?**

Findings are in [`docs/research/BUILD-HULL.md`](../../docs/research/BUILD-HULL.md);
section 15 covers the aligned/warped measurement these scripts produce.

## Why the hull is honest

The hull is built from frames rendered **by strehl itself**, each under a one-frame
`STREHL_WARPMAP` sidecar carrying that frame's own placement copied verbatim from the
real 205-frame solve. Every frame therefore passes through strehl's own gather and its
own Catmull-Rom kernel onto the reference grid the merge lands on. Comparing against
unwarped frames would manufacture violations everywhere; that is structurally not what
this does, and `coreg.py` measures the result rather than asserting it.

## The theorem the per-band test rests on

For **any** linear operator `L`, a convex combination with one weight vector shared
across bands satisfies `L(O) = sum_k w_k L(F_k)`, which lies inside
`[min_k L(F_k), max_k L(F_k)]` necessarily. So a per-band violation under *my* Laplacian
proves the weights are not shared across bands. The decomposition does not need to match
`pyramid.rs`; it only needs to be linear.

It follows that the per-band result attributes the excursion to a **spatial frequency**,
not to a `pyramid.rs` array index. It cannot do the latter and does not claim to.

## Files

| file | role |
|---|---|
| `warpframes.py` | synthesises one-frame warpmap sidecars and renders co-registered warped frames |
| `coreg.py` | measures frame-vs-merge registration by high-pass NCC; refuses to report a number unless a planted shift is recovered |
| `bfold.py` | folds the frame basis once into cached whole-image and per-band hulls |
| `bhull2.py` | hull scoring, five-outcome partition, hull-span units, shared helpers |
| `btest.py` | scores every merge arm; per channel, whole-frame and bbox; arm partition sums |
| `octave.py` | decimated octave pyramid matched to the merge's `7 levels + base, coarsest 28x19` |
| `footprint.py` | upsamples each octave's violation to full res and subtracts the null arm |
| `commission_bands.py` | synthetic commissioning, including the shared/independent x fixed/data-dependent 2x2 |
| `plantcheck.py` | predicts the planted count from the hull alone, then requires exact equality |
| `bandattrib.py` | magnitude-by-band attribution for the non-decimated decomposition |
| `clamptest.py` | scores clamped vs unclamped arms against one hull; carries the build control |
| `builddiff.py` | isolates what changed between two binaries on a path with no hull code |
| `pairprice.py` | prices the clamp from a matched one-build pair, with a determinism null |

## Which hull is which

Two different objects, and section 16.4 of the report turns on not confusing them:

- **What the clamp enforces** (`pyramid.rs:1189`) is the hull of the **CFA quad planes,
  before demosaic**. `BAND_PLANES = 4`; the merge runs on R, G1, G2, B.
- **What these scripts measure** is the hull of **demosaiced RGB**.

For green, `G = 0.5*(G1+G2)` and `min_k(G1_k+G2_k) >= min_k G1_k + min_k G2_k`, so the
clamp's constraint transported into the RGB domain is *strictly weaker* than the hull here.
A correctly clamped render can sit outside this hull without leaving its own. Do not read a
non-zero rate on a clamped arm as a failure of the clamp.

## Commissioning, which must pass before any number is trusted

- `commission_bands.py` must print **GREEN**: shared weights leak `0`, single-frame
  passthrough leaks `0`, `sum(bands) - frame` is `0.000e+00`, a plant is recovered.
- `plantcheck.py` must print **GREEN**: the planted ABOVE count predicted from the hull
  equals the measured count exactly, with zero leakage outside the plant box and the
  BELOW count unchanged.
- The real-pipeline null (`--pyramid-exponent 1e-6 --pyramid-sharpen 1.0`) must read
  ~zero. It reads 0.0002% whole-image and exactly 0 in the base octave.

A detector reporting zero violations is indistinguishable from a detector that is not
looking, so none of these are optional.

## Conventions

- 16-bit TIFFs are read with `tifffile` and asserted `uint16`; never `PIL`.
- Never measure on an `--srgb` or JPEG file; the tone curve amplifies differences ~4x.
- Every partition is asserted to sum, so a skipped region cannot read as a clean one.
- Arms are reported as requested / scored / missing for the same reason.

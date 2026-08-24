# M113 pre-registration — independent verification of fact 1420

Written before any number in `out/` was read. Author: M113-kernel-verify.
Subject under test: SYNTHESIS fact 1420 (`lanczos3 -0.0663 dex` vs
`catmull-rom -0.2006 dex`, gain `+0.1343 dex`, "9.4x the rescale fix",
"4 of 4 controls passing", C4 `0.6466` vs `0.4488`).

Rule 24 binds: verification must **re-choose**, not re-compute. I therefore do
not re-run `x3_kernel.py`. Every choice point below is set to a different
defensible value from M95's.

## Choice points, and where I differ from M95

| choice | M95 (`x3_kernel.py`) | M113 |
| --- | --- | --- |
| statistic | `band_ratio` = log10(P[0.30-0.48] / P[0.02-0.10]), unreferenced | **reference-based error against a Fourier-exact shift**, plus a **round-trip** error whose truth is the input itself |
| tile selection | 40 sharpest by gradient (data-dependent) | **fixed geometric lattice**, every non-overlapping 256 px tile whose centre lies inside the central half of the frame; no selection on content, no selection on result |
| kernel set | 4 kernels | **9-kernel monotone ringiness ladder** ending past Lanczos-3, so the metric can be driven off the end |
| data | `single-noalign.tif` only | that file **and** a synthetic exactly-band-limited plant where the Fourier shift is provably the truth |
| end-to-end arm | 3 renders, `--limit` 1 frame | **two full 299-frame renders**, one solve, only the sidecar `resampler` line differing |

## Bars, registered before the numbers

- **B1 (metric validity).** Rank the 9-kernel ladder by `band_ratio` and by
  RMS-vs-truth. If `band_ratio` keeps improving monotonically past the kernel
  that minimises RMS-vs-truth, then `band_ratio` **is rewarding ringing** beyond
  the accuracy optimum and fact 1420's dex figure is not a quality figure.
  - **FAIL-INPUT THAT EXISTS (rule 20):** a truncated-sinc kernel at radius 16.
    It has the widest passband of anything here and rings hardest. If the metric
    were accuracy-tracking, it must NOT be ranked best.
- **B2 (where Lanczos-3 sits).** Report the argmin of RMS-vs-truth. Lanczos-3 is
  vindicated only if it is at, or on the correct side of, that argmin.
- **B3 (reproduction).** Re-derive the Catmull-Rom -> Lanczos-3 dex gain
  end-to-end through the shipped binary on the full 299-frame `bee-3-cpl`,
  reference 149, one solve. Registered as reproducing if it lands inside
  `[+0.08, +0.16]` dex, which brackets both published values (`+0.1160` real
  warps, `+0.1343` synthetic).
- **B4 (ringing on real occluding edges).** On the two full renders, measure
  under/overshoot at hair silhouettes in DN and as a fraction of local range.
  Registered as materially ringing if Lanczos-3's p99.9 overshoot exceeds
  Catmull-Rom's by more than 3x on hair ROIs, or if it drives pixels below the
  local neighbourhood minimum by more than 1% of the local range at p99.9.
- **B5 (controls in `m95-lanczos.rs`).** For each of C1..C4, name an input that
  makes it fail and check such an input exists. A control with no such input is
  arithmetic, not evidence.

## Controls this harness must pass before any arm is read

- **N1 null.** Shift of (0,0): every interpolating kernel must read ~0 on all
  three statistics. An instrument that charges for nothing cannot price a kernel.
- **N2 response.** A planted Fourier-exact Gaussian blur of sigma = 0.25 px must
  move all three statistics in the *worse* direction.
- **N3 the falsifier for B1.** A planted pure **passband boost** (a zero-phase
  gain > 1 in 0.30-0.48 cyc/px, which is ringing and nothing else). `band_ratio`
  must read it as an IMPROVEMENT while RMS-vs-truth reads it as WORSE. If N3
  does not separate, B1 has no power and I must say so.
- **N4 loader.** The Fourier shift by an exact integer must equal `np.roll`
  to floating-point noise.

## What would make me report "confirmed"

Lanczos-3 at or before the RMS-vs-truth argmin, an end-to-end reproduction
inside B3's band, and B4 not firing on hair ROIs.

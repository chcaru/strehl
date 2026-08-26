"""Is the pyramid merge's flat-tile acuity loss NOISE REDUCTION or BLUR?

acuitymap.py showed the loss is monotone in reference-tile sharpness: -20% in
the flattest quintile, -1.3% in the sharpest. Two mechanisms produce that and
they have OPPOSITE consequences:

  NOISE REDUCTION  the merge averages where no frame wins (its noise gate says
                   exactly this). Removing white noise scales the whole
                   high-frequency plateau down by roughly a constant factor.
                   Nothing is lost. accept.py's `acuity` counts noise as detail.

  BLUR             a low-pass rolls off monotonically toward Nyquist and takes
                   real detail with it.

Discriminator: the radially-averaged power spectral ratio test/ref over the
flattest tiles.
  flat in frequency        -> noise reduction
  monotone falling to 0    -> blur

Controls:
  1. NULL  ref-vs-ref must give ratio 1.0000 at every frequency.
  2. The SHARPEST quintile is run as a contrast: if the flat-tile ratio is a
     genuine noise effect it should be much closer to 1 there, since those
     tiles are signal-dominated.

Usage:
  python spectralratio.py <dir> <subject> --ref ctrl --test blend
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import tifffile


def green(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    assert a.dtype == np.uint16, f"{path.name}: expected uint16, got {a.dtype}"
    return a[:, :, 1].astype(np.float32)


def abs_lap(g):
    lap = np.zeros_like(g)
    lap[1:-1, 1:-1] = (
        4.0 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    )
    return np.abs(lap)


def radial_psd(tile: np.ndarray, nbin: int = 24):
    """Radially averaged power spectrum of one square tile, Hann-windowed."""
    t = tile - tile.mean()
    n = t.shape[0]
    w = np.hanning(n)
    t = t * w[:, None] * w[None, :]
    F = np.fft.fftshift(np.fft.fft2(t))
    P = (F.real**2 + F.imag**2)
    c = n // 2
    y, x = np.ogrid[:n, :n]
    r = np.sqrt((y - c) ** 2 + (x - c) ** 2)
    rmax = c
    idx = np.clip((r / rmax * nbin).astype(int), 0, nbin - 1)
    out = np.zeros(nbin)
    for b in range(nbin):
        m = idx == b
        out[b] = P[m].mean() if m.any() else np.nan
    return out


def collect(g, tiles, t, nbin):
    acc = np.zeros(nbin)
    n = 0
    for (iy, ix) in tiles:
        sub = g[iy * t : (iy + 1) * t, ix * t : (ix + 1) * t]
        if sub.shape != (t, t):
            continue
        acc += radial_psd(sub, nbin)
        n += 1
    return acc / max(n, 1), n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("subject")
    ap.add_argument("--ref", default="ctrl")
    ap.add_argument("--test", default="blend")
    ap.add_argument("--tile", type=int, default=128)
    ap.add_argument("--nbin", type=int, default=24)
    a = ap.parse_args()

    d = Path(a.dir)
    gr = green(d / f"{a.subject}--{a.ref}.tiff")
    gt = green(d / f"{a.subject}--{a.test}.tiff")
    assert gr.shape == gt.shape

    t, nbin = a.tile, a.nbin
    h, w = gr.shape
    ny, nx = h // t, w // t

    # rank tiles by REFERENCE sharpness only
    ar = abs_lap(gr)
    thr = np.percentile(gr, 20.0)
    lit = gr > thr
    score = []
    for iy in range(ny):
        for ix in range(nx):
            sl = (slice(iy * t, (iy + 1) * t), slice(ix * t, (ix + 1) * t))
            m = lit[sl]
            if m.sum() >= t * t * 0.9:  # near-fully-lit tiles only
                score.append((float(ar[sl][m].mean()), iy, ix))
    score.sort()
    k = max(len(score) // 5, 1)
    flat = [(iy, ix) for _, iy, ix in score[:k]]
    sharp = [(iy, ix) for _, iy, ix in score[-k:]]

    print(f"subject : {a.subject}   {gr.shape}  tile={t}  bins={nbin}")
    print(f"tiles   : {len(score)} fully-lit; quintile size {k}")

    freq = (np.arange(nbin) + 0.5) / nbin  # fraction of Nyquist

    for label, tiles in (("FLATTEST quintile", flat), ("SHARPEST quintile", sharp)):
        pr, n1 = collect(gr, tiles, t, nbin)
        pt, n2 = collect(gt, tiles, t, nbin)
        pn, _ = collect(gr, tiles, t, nbin)

        null = np.nanmax(np.abs(pn / pr - 1.0))
        print(f"\n=== {label}  ({n1} tiles) ===")
        print(f"  NULL ref-vs-ref max |ratio-1| = {null:.2e}", end="  ")
        if null > 1e-9:
            print("** INSTRUMENT BROKEN **")
            return 3
        print("OK")
        with np.errstate(invalid="ignore", divide="ignore"):
            amp = np.sqrt(pt / pr)  # amplitude ratio = MTF-like
        print(f"  {'f/Nyq':>7}{'amp ratio':>12}")
        for b in range(0, nbin, 2):
            print(f"  {freq[b]:7.2f}{amp[b]:12.4f}")
        hi = amp[nbin // 2 :]
        lo = amp[: nbin // 2]
        print(f"  low-half mean {np.nanmean(lo):.4f}   high-half mean {np.nanmean(hi):.4f}")
        print(f"  amp at 0.5*Nyq {amp[nbin//2]:.4f}   at ~Nyq {amp[-1]:.4f}")
        slope = np.nanmean(hi) - np.nanmean(lo)
        verdict = (
            "FALLING toward Nyquist -> consistent with BLUR"
            if slope < -0.05
            else "FLAT across frequency -> consistent with NOISE REDUCTION"
            if abs(slope) <= 0.05
            else "RISING toward Nyquist -> sharpening"
        )
        print(f"  high-minus-low {slope:+.4f}  =>  {verdict}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

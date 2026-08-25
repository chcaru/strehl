"""Wiener deconvolution of the merged render, against a SELF-MEASURED PSF.

Why this is not a repeat of the section 4 negative
--------------------------------------------------
Section 4 built the same estimator with `H` set to the phase-averaged MTF of
our own RESAMPLING KERNEL. That kernel is nearly perfect -- Catmull-Rom holds
0.625 at Nyquist -- so there was almost nothing to invert, the calibrated noise
capped the gain at 1.096x, and caps of 1.4/1.7/2.5 gave byte-identical output.
The negative was real but its scope was narrow: it said the RESAMPLER is not
costing us contrast.

It said nothing about the optics, which is where the blur actually is. Section 1
measured the system on a printed ruler at a 30.44 um 10-90 rise against a 14.11
um diffraction limit, and measured the f/11:f/5.6 edge-width ratio at 1.025x
where diffraction predicts 1.964x. Blur that does not improve on stopping down
is aberration, not diffraction, and it is 60.1% of the total blur variance.
That is the term this script targets.

What is self-calibrated, and what is assumed
--------------------------------------------
* The PSF width is MEASURED from the merged image's own edges, by the same
  10-90 ESF instrument used in section 1 (M88b), on integer-registered profiles.
  No lens model is loaded.
* The noise level is MEASURED from the merged image's own flat regions. This is
  the honest sigma for this estimator, because it is the noise actually present
  in the thing being deconvolved -- the merge averages 166.8 of 299 frames per
  pixel (corpus fact 1685), so the residual noise is far below a single frame's
  and a per-frame noise model would badly over-estimate it and throttle the
  filter for no reason.
* The PSF is assumed Gaussian and SPATIALLY INVARIANT. Both are approximations
  and the second is deliberate: corpus fact 1682 proves that the merge already
  manufactures structure through the SPATIAL VARIATION of its weights, exceeding
  the convex-weighting bound of 1.284 by 3.4x. A spatially varying restoration
  filter has exactly that failure mode. A single global filter cannot invent a
  patch boundary, so it is the safe thing to try first.

Ringing is the failure mode, and no high-pass statistic may adjudicate it --
corpus fact 1359 records a Laplacian metric scoring a visible selection artefact
2.73x ABOVE the correct render. Judgement is by eye on flat regions adjacent to
hard edges, with `couch-fibers-cpl` as the do-no-harm guard.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

try:
    import tifffile
except ImportError:  # pragma: no cover
    raise SystemExit("tifffile is required: PIL silently returns 8-bit for 16-bit RGB TIFFs")


def read16(path: Path) -> np.ndarray:
    """Read a 16-bit TIFF. Never use PIL here -- it silently downcasts to 8-bit."""
    a = tifffile.imread(str(path))
    if a.dtype != np.uint16:
        raise SystemExit(f"{path}: expected uint16, got {a.dtype}")
    return a


def luma(rgb: np.ndarray) -> np.ndarray:
    """Linear-sRGB luminance. The renders are --linear-srgb, so no curve to undo."""
    f = rgb.astype(np.float64) / 65535.0
    return 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]


# ---------------------------------------------------------------- noise ------

def noise_sigma(y: np.ndarray, tiles: int = 24, tile: int = 96) -> float:
    """Robust noise SD, from the quietest tiles of the image itself.

    Uses the standard Laplacian-MAD estimator, but takes the MEDIAN over the
    quietest tiles rather than the whole image, because a global MAD on a
    detailed macro frame is dominated by real structure and would over-estimate
    sigma -- which in this estimator means silently throttling the filter.

    The 6/sqrt(2) normalisation is for the {{1,-2,1},{-2,4,-2},{1,-2,1}} kernel
    applied to i.i.d. noise; 1.4826 converts MAD to a Gaussian-equivalent SD.
    """
    k = np.array([[1, -2, 1], [-2, 4, -2], [1, -2, 1]], dtype=np.float64)
    h, w = y.shape
    # Valid-region convolution without scipy.
    lap = sum(k[i, j] * y[i:h - 2 + i, j:w - 2 + j]
              for i in range(3) for j in range(3))
    sds = []
    for yy in range(0, lap.shape[0] - tile, tile):
        for xx in range(0, lap.shape[1] - tile, tile):
            t = lap[yy:yy + tile, xx:xx + tile]
            sds.append(1.4826 * np.median(np.abs(t - np.median(t))) / 6.0 * np.sqrt(2))
    sds = np.sort(np.array(sds))
    return float(np.median(sds[:max(tiles, 1)]))


# ------------------------------------------------------------ power spec ----

def radial_power(y: np.ndarray, n: int = 1024) -> tuple[np.ndarray, np.ndarray]:
    """Radially averaged power spectrum of a central n x n window, in c/px."""
    h, w = y.shape
    n = min(n, h, w)
    cy, cx = h // 2, w // 2
    p = y[cy - n // 2:cy + n // 2, cx - n // 2:cx + n // 2].astype(np.float64)
    p = p - p.mean()
    win = np.hanning(n)
    p = p * win[:, None] * win[None, :]
    P = np.abs(np.fft.fftshift(np.fft.fft2(p))) ** 2 / (n * n)
    fy = np.fft.fftshift(np.fft.fftfreq(n))
    r = np.hypot(fy[:, None], fy[None, :])
    nb = n // 2
    edges = np.linspace(0, 0.5, nb + 1)
    idx = np.clip(np.digitize(r.ravel(), edges) - 1, 0, nb - 1)
    tot = np.bincount(idx, weights=P.ravel(), minlength=nb)
    cnt = np.bincount(idx, minlength=nb)
    return 0.5 * (edges[:-1] + edges[1:]), tot / np.maximum(cnt, 1)


# ---------------------------------------------------------------- filter ----

def wiener(y: np.ndarray, sigma_px: float, nsr: np.ndarray,
           freqs: np.ndarray) -> np.ndarray:
    """G = H / (H^2 + sigma^2/S), with H a Gaussian OTF of width sigma_px.

    `nsr` is sigma^2/S(f) sampled at `freqs` (cycles/px) and is interpolated
    onto the 2-D frequency grid. Keeping the noise-to-signal ratio frequency
    dependent is the whole point: it is what makes the filter back off exactly
    where the image has no signal left to recover, instead of at a hand-set cap.
    """
    h, w = y.shape
    fy = np.fft.fftfreq(h)
    fx = np.fft.fftfreq(w)
    r = np.hypot(fy[:, None], fx[None, :])
    H = np.exp(-2.0 * np.pi ** 2 * sigma_px ** 2 * r ** 2)
    N = np.interp(r, freqs, nsr)
    G = H / (H * H + N)
    return np.real(np.fft.ifft2(np.fft.fft2(y) * G)), G, H, r


def noise_spectrum(freqs: np.ndarray, P: np.ndarray, dead_from: float
                   ) -> tuple[np.ndarray, float]:
    """Measure the NOISE power spectrum from the image's own dead band.

    A scalar noise SD is the wrong object here, and using one is what made the
    first attempt ring. The Laplacian-MAD estimator assumes WHITE noise, but the
    noise in a merged frame is strongly CORRELATED -- it is an average of ~167
    frames resampled through a Catmull-Rom kernel, both of which suppress high
    frequencies. Correlated noise therefore has far less power at high frequency
    than white noise of the same SD, so a scalar sigma taken from a high-pass
    operator under-reports the noise at the mid frequencies the filter actually
    amplifies, and the Wiener denominator lets the gain run away. Measured: a
    scalar sigma permitted 29.4x gain and the picture was destroyed.

    The fix needs no model and no extra data. The optics have already zeroed the
    signal above a known frequency -- section 1 measured a 30.44 um system rise,
    which puts the MTF below 1e-3 by 0.25 c/px -- so in that band EVERY bit of
    measured power is noise. Fit the noise there and extrapolate down.

    A power law is fitted rather than a constant precisely because the noise is
    NOT white; a constant fit would be the same mistake in a new place. Returns
    the noise power at `freqs`, and the fitted exponent so it can be reported:
    an exponent near zero would mean the noise really was white and would make
    this whole correction a no-op, which is a claim worth being able to check.
    """
    m = (freqs >= dead_from) & (P > 0)
    if m.sum() < 8:
        raise SystemExit("dead band too small to fit a noise spectrum")
    lf, lp = np.log(freqs[m]), np.log(P[m])
    slope, intercept = np.polyfit(lf, lp, 1)
    N = np.exp(intercept) * np.power(np.maximum(freqs, 1e-6), slope)
    return N, float(slope)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("tif")
    p.add_argument("--sigma", type=float, required=True,
                   help="PSF Gaussian sigma in PIXELS of this image")
    p.add_argument("--out", required=True)
    p.add_argument("--boost", type=float, default=1.0,
                   help="multiply the calibrated noise power by this; 1.0 is calibrated")
    p.add_argument("--dead-from", type=float, default=0.28,
                   help="frequency above which the optics guarantee no signal")
    p.add_argument("--json")
    a = p.parse_args()

    rgb = read16(Path(a.tif))
    y = luma(rgb)
    sd = noise_sigma(y)
    freqs, S = radial_power(y)
    N, slope = noise_spectrum(freqs, S, a.dead_from)
    Ssig = np.maximum(S - N, N * 1e-3)
    nsr = (N * a.boost) / Ssig

    out, G, H, r = wiener(y, a.sigma, nsr, freqs)
    # Report the filter's actual behaviour across the band, not just its peak:
    # a max gain says nothing about WHERE the gain is, and gain at frequencies
    # the optics have already zeroed is gain applied to nothing but noise.
    band = [0.05, 0.10, 0.15, 0.20, 0.25, 0.35, 0.50]
    prof = []
    for f in band:
        m = (r >= f - 0.005) & (r < f + 0.005)
        mtf = float(np.exp(-2 * np.pi ** 2 * a.sigma ** 2 * f * f))
        prof.append(dict(f=f, mtf=round(mtf, 5),
                         gain=round(float(G[m].mean()) if m.any() else float("nan"), 4),
                         restored_mtf=round(mtf * (float(G[m].mean()) if m.any() else 0), 4)))
    stats = dict(tif=a.tif, sigma_px=a.sigma, noise_sd_scalar=sd, boost=a.boost,
                 noise_exponent=slope, dead_from=a.dead_from,
                 max_gain=float(G.max()), profile=prof)
    print(json.dumps(stats, indent=2))

    # Apply the same per-pixel gain to each channel so colour is untouched.
    ratio = np.divide(out, y, out=np.ones_like(y), where=np.abs(y) > 1e-6)
    ratio = np.clip(ratio, 0.0, 8.0)
    res = np.clip(rgb.astype(np.float64) * ratio[..., None], 0, 65535).astype(np.uint16)
    tifffile.imwrite(a.out, res)
    print(f"wrote {a.out}")
    if a.json:
        Path(a.json).write_text(json.dumps(stats, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

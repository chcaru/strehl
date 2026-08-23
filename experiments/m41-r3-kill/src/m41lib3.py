"""M41 -- FRC diagnostics and repair candidates.  NEW FILE, adds nothing to
m41lib.py and m41lib2.py, which have both produced results that are reported in
docs/research/M41-r3-kill-measured.md and are therefore frozen (rule 15).

Why this exists.  m41lib.frc_cross has no way to say "the curve never crossed
the threshold inside the sampled band".  Its fallback is

    return float(ff[-1])

and `ff[-1]` is a CONSTANT of the ring grid, not a measurement:

    n = 512, nbin = 64  ->  edges = linspace(0, 256, 65), width 4 px
                        ->  last ring centre = 254 px
                        ->  ff[-1] = 254 / 512 = 0.49609375  ->  "0.4961"

Every "0.4961 cyc/px" in out/a2_run.log, out/a6_run.log and out/a8_frc_power.log
is that fallback.  It is a RIGHT-CENSORED reading meaning ">= 0.4961", and two
censored readings cannot be divided to make a ratio.  The functions here return
the censoring flag alongside the number so a caller cannot lose it.

Rule 20 for everything in this file: the input that makes a crossing statistic
FAIL to be informative is a curve that stays above the threshold everywhere.
Such an input exists and is the common case on this data -- that is the finding.
"""
import numpy as np
import m41lib as L


def ring_grid(n, nbin):
    """The frequency grid m41lib.frc produces, computed without any image.
    Returns (freqs, last) where `last` is the value frc_cross falls back to."""
    rmax = n // 2
    edges = np.linspace(0, rmax, nbin + 1)
    ff = 0.5 * (edges[:-1] + edges[1:]) / n
    return ff, float(ff[-1])


def cross(ff, fr, thr=1.0 / 7.0, consecutive=2):
    """m41lib.frc_cross's rule, but returning (freq, censored).

    censored=True means the curve never fell below `thr` for `consecutive`
    adjacent rings inside the sampled band, so the returned frequency is
    ff[-1] -- a LOWER BOUND on the crossing, not the crossing.
    """
    nb = len(fr)
    for i in range(nb - consecutive + 1):
        if all(fr[i + j] < thr for j in range(consecutive)):
            if i == 0:
                return float(ff[0]), False
            f0, f1 = ff[i - 1], ff[i]
            r0, r1 = fr[i - 1], fr[i]
            if r0 == r1:
                return float(f1), False
            return float(f0 + (r0 - thr) * (f1 - f0) / (r0 - r1)), False
    return float(ff[-1]), True


def frc_pred(latent, sigma, nbin=64):
    """Analytic split-half FRC expectation for a known latent and known white
    noise sd: per ring, FRC = SNR/(1+SNR) with SNR the ring-mean signal power
    over the ring-mean noise power.  This is the truth channel for the planted
    ladder -- it uses the KNOWN latent and the KNOWN sigma and never looks at
    the noisy realisation, so it is not circular.

    It is validated against the measured independent-noise split in a11; if the
    two disagree the prediction is reported as failed, not quietly used.
    """
    n = latent.shape[0]
    w = np.outer(np.hanning(n), np.hanning(n))
    S = np.abs(np.fft.fftshift(np.fft.fft2((latent - latent.mean()) * w))) ** 2
    npow = sigma * sigma * float((w * w).sum())      # white noise through the window
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - n // 2) ** 2 + (xx - n // 2) ** 2)
    edges = np.linspace(0, n // 2, nbin + 1)
    ff, fr = [], []
    for i in range(nbin):
        m = (rr >= edges[i]) & (rr < edges[i + 1])
        if m.sum() < 8:
            continue
        snr = float(S[m].mean()) / npow
        fr.append(snr / (1.0 + snr))
        ff.append(0.5 * (edges[i] + edges[i + 1]) / n)
    return np.array(ff), np.array(fr)


def gauss_blur(img, sb):
    """Gaussian blur of KNOWN sd `sb` px, applied in the Fourier domain so the
    planted MTF is exactly exp(-2 pi^2 sb^2 f^2) with no kernel truncation."""
    if sb <= 0:
        return img.astype(np.float32)
    n = img.shape[0]
    FY = np.broadcast_to(np.fft.fftfreq(n)[:, None], (n, n // 2 + 1))
    FX = np.broadcast_to(np.fft.rfftfreq(n)[None, :], (n, n // 2 + 1))
    H = np.exp(-2.0 * (np.pi ** 2) * (sb ** 2) * (FX * FX + FY * FY))
    return np.fft.irfft2(np.fft.rfft2(img) * H, s=(n, n)).astype(np.float32)


def mean_grad(a):
    """mean |grad|.  Rule 18: this rises when a merge MANUFACTURES detail exactly
    as when it preserves it, so it is admissible against collapse only.  Rule 23:
    `a` must already be 2-D; sobel is never handed a cube here."""
    from scipy.ndimage import sobel
    assert a.ndim == 2, "rule 23: pass a 2-D plane, never a (frames, y, x) cube"
    gx = sobel(a, axis=1)
    gy = sobel(a, axis=0)
    return float(np.sqrt(gx * gx + gy * gy).mean())


def p_ratio(a, fc=L.F_SIG):
    lo, hi = L.band_power(a, fc)
    return hi / max(lo, 1e-30)

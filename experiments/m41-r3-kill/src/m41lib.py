"""M41 step 2 -- the six pre-registered merge arms, plus controls.

Executes section 8 of docs/research/G-edof-deconvolution.md.
Kill condition was committed in PREREGISTRATION.md (commit f809772) BEFORE this
script was run.

Arms
  A  regularised winner field + noise-gated average  (shipped-equivalent proxy)
  B  plain per-pixel argmax on the fine focus field  (the naive baseline)
  C  plain mean of all frames
  D  guarded focus-axis regularised inverse filter, H_k = defocus (x) diffraction
  D' ablation: D with no diffraction term
  E  ablation: D unguarded (sigma^2/S = 0)

Rules honoured
  4   no merge reference is a raw per-band argmax; arm B is a LABELLED baseline,
      never a reference for another arm's score
  7   raw_image_visible only
  9   the flat-ROI control is computed for every arm, in the same pass
  10  every sigma reported here is a SPATIAL sd and is labelled as such; it is
      never compared to a temporal sigma
  18  metric fooling direction is printed next to each metric
  23  sobel is only ever called on an already-extracted 2-D plane
Read-only corpora are never written.
"""
import os, sys, glob, json, argparse, time
import numpy as np
import rawpy, exifread
from scipy.ndimage import uniform_filter, sobel
from scipy.special import j1

BLACK = 512
F_SIG = 0.2762            # fact 27, MEASURED optical cutoff, cyc/px, green plane
FINE_W = 5                # FINE_WINDOW_RADIUS = 2
COARSE_W = 27             # WINDOW_RADIUS = 13
REG_W = 17                # REGULARISER_RADIUS = 8
GATE = 0.5                # "frames within 50% of PEAK HEIGHT" (merge_cmd.rs)
TILE = 128
STEP = 64
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")


def iso_of(p):
    with open(p, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    for k in ("EXIF ISOSpeedRatings", "Image ISOSpeedRatings"):
        if k in t:
            return int(str(t[k]).split(",")[0].strip("[] "))
    return None


def load_cube(files, roi, pad):
    x, y, w, h = roi
    x0, y0 = x - pad, y - pad
    x1, y1 = x + w + pad, y + h + pad
    out = np.empty((len(files), y1 - y0, x1 - x0), np.float32)
    for i, f in enumerate(files):
        with rawpy.imread(f) as r:
            v = r.raw_image_visible
            g1 = v[2 * y0:2 * y1:2, 2 * x0 + 1:2 * x1 + 1:2].astype(np.float32)
            g2 = v[2 * y0 + 1:2 * y1 + 1:2, 2 * x0:2 * x1:2].astype(np.float32)
        out[i] = 0.5 * (g1 + g2) - BLACK
    return out


def focus_fields(cube, g, rn_e):
    """Returns (fine, coarse, reg) noise-normalised Tenengrad fields.
    Rule 23: sobel is applied plane by plane, never to the (n,y,x) cube."""
    n = cube.shape[0]
    fine = np.empty_like(cube); coarse = np.empty_like(cube); reg = np.empty_like(cube)
    for k in range(n):
        p = cube[k]                                    # 2-D plane, extracted first
        gx = sobel(p, axis=1); gy = sobel(p, axis=0)
        e = gx * gx + gy * gy
        m = uniform_filter(p, COARSE_W)
        nvar = 0.5 * (g * np.maximum(m, 0.0) + (rn_e * g) ** 2)   # quad plane: /2
        fine[k] = uniform_filter(e, FINE_W) - 24.0 * nvar
        coarse[k] = uniform_filter(e, COARSE_W) - 24.0 * nvar
        reg[k] = uniform_filter(coarse[k], REG_W)
    np.maximum(fine, 0.0, out=fine); np.maximum(coarse, 0.0, out=coarse)
    np.maximum(reg, 0.0, out=reg)
    return fine, coarse, reg


# ---------------------------------------------------------------- arms A,B,C
def arm_B(cube, fine):
    w = np.argmax(fine, axis=0)
    return np.take_along_axis(cube, w[None], 0)[0], w


def arm_A(cube, coarse, reg):
    w = np.argmax(reg, axis=0)
    peak = np.take_along_axis(coarse, w[None], 0)[0]
    acc = coarse >= (GATE * peak)[None]
    acc[w, np.arange(cube.shape[1])[:, None], np.arange(cube.shape[2])[None]] = True
    n = acc.sum(0).astype(np.float32)
    s = (cube * acc).sum(0)
    return s / np.maximum(n, 1.0), w, n


def arm_C(cube):
    return cube.mean(0)


# ---------------------------------------------------------------- OTF models
def otf_defocus(r, fx, fy):
    """Geometric pillbox of radius r (quad px). H = 2 J1(2 pi r f)/(2 pi r f).
    Goes negative -- the contrast reversals are real and are kept."""
    f = np.sqrt(fx * fx + fy * fy)
    if r <= 1e-6:
        return np.ones_like(f)
    a = 2.0 * np.pi * r * f
    out = np.ones_like(f)
    nz = a > 1e-8
    out[nz] = 2.0 * j1(a[nz]) / a[nz]
    return out


def otf_diffraction(fx, fy, fc=F_SIG):
    """Incoherent circular-aperture OTF with the MEASURED cutoff fc (fact 27)."""
    f = np.sqrt(fx * fx + fy * fy)
    nu = np.clip(f / fc, 0.0, 1.0)
    h = (2.0 / np.pi) * (np.arccos(nu) - nu * np.sqrt(np.maximum(1.0 - nu * nu, 0.0)))
    h[f >= fc] = 0.0
    return h


# ------------------------------------------------- self-calibration of s
def calibrate_s(cube, coarse, g, rn_e, use_diff=True):
    """The reviewer's claim (survey section 5): the width of the through-focus
    response curve IS the local PSF scale sampled by the operator.  Measure the
    FWHM of the measured curve in frames, then solve for the blur growth per
    frame s (quad px/frame) that reproduces that FWHM under the forward model.
    Returns (s, fwhm_measured_frames, fwhm_modelled_frames)."""
    n = cube.shape[0]
    curve = coarse.reshape(n, -1).mean(1)
    kstar = int(np.argmax(curve))
    c = curve - curve.min()
    half = 0.5 * c.max()
    above = np.where(c >= half)[0]
    fwhm_meas = float(above[-1] - above[0] + 1)

    # measured spectrum of the sharpest frame, used as |F|^2 in the model
    p = cube[kstar] - cube[kstar].mean()
    h, w = p.shape
    win = np.hanning(h)[:, None] * np.hanning(w)[None, :]
    P = np.abs(np.fft.rfft2(p * win)) ** 2
    P /= P.sum()
    FY = np.broadcast_to(np.fft.fftfreq(h)[:, None], P.shape).copy()
    FX = np.broadcast_to(np.fft.rfftfreq(w)[None, :], P.shape).copy()
    grad2 = (2.0 * np.pi) ** 2 * (FX * FX + FY * FY)
    hd = otf_diffraction(FX, FY) if use_diff else np.ones_like(FX)

    def modelled_fwhm(s):
        resp = []
        for dk in range(0, n):
            H = otf_defocus(abs(dk) * s, FX, FY) * hd
            resp.append(float((P * grad2 * H * H).sum()))
        resp = np.array(resp)
        r = resp - resp.min()
        hh = 0.5 * r.max()
        idx = np.where(r >= hh)[0]
        # symmetric curve -> full width is 2*half-width-at-half-max - 1
        return 2.0 * (idx[-1] + 1) - 1.0

    lo, hi = 0.02, 8.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if modelled_fwhm(mid) > fwhm_meas:
            lo = mid
        else:
            hi = mid
    s = 0.5 * (lo + hi)
    return s, fwhm_meas, modelled_fwhm(s)


# ---------------------------------------------------------------- arm D family
def arm_wiener(cube, reg, g, rn_e, s, use_diff=True, guarded=True, order=None):
    n, H, W = cube.shape
    acc = np.zeros((H, W), np.float64)
    wacc = np.zeros((H, W), np.float64)
    win1 = np.hanning(TILE)
    win = np.outer(win1, win1)
    fy = np.fft.fftfreq(TILE)[:, None]
    fx = np.fft.rfftfreq(TILE)[None, :]
    FX = np.broadcast_to(fx, (TILE, TILE // 2 + 1)).copy()
    FY = np.broadcast_to(fy, (TILE, TILE // 2 + 1)).copy()
    f2 = np.maximum(FX * FX + FY * FY, (1.0 / TILE) ** 2)
    hd = otf_diffraction(FX, FY) if use_diff else np.ones_like(FX)
    idx = np.arange(n) if order is None else order
    ys = list(range(0, H - TILE + 1, STEP))
    xs = list(range(0, W - TILE + 1, STEP))
    if ys[-1] != H - TILE: ys.append(H - TILE)
    if xs[-1] != W - TILE: xs.append(W - TILE)
    for y in ys:
        for x in xs:
            tile = cube[:, y:y + TILE, x:x + TILE]
            rtile = reg[:, y:y + TILE, x:x + TILE].reshape(n, -1).mean(1)
            kstar = int(np.argmax(rtile))
            mean = float(tile[kstar].mean())
            sig2 = 0.5 * (g * max(mean, 0.0) + (rn_e * g) ** 2)
            var_sig = max(float(tile[kstar].var()) - sig2, 1e-3)
            # fixed 1/f^2 prior, normalised so its total power = measured signal power
            Sf = 1.0 / f2
            Sf = Sf * (var_sig / Sf.mean())
            num = np.zeros((TILE, TILE // 2 + 1), np.complex128)
            den = np.zeros((TILE, TILE // 2 + 1), np.float64)
            for k in range(n):
                dk = abs(idx[k] - idx[kstar])
                Hk = otf_defocus(dk * s, FX, FY) * hd
                Y = np.fft.rfft2((tile[k] - mean) * win)
                num += Hk * Y
                den += Hk * Hk
            if guarded:
                den = den + sig2 / Sf
            else:
                den = den + 1e-6
            L = np.fft.irfft2(num / den, s=(TILE, TILE)) + mean
            acc[y:y + TILE, x:x + TILE] += L * win
            wacc[y:y + TILE, x:x + TILE] += win
    return (acc / np.maximum(wacc, 1e-9)).astype(np.float32)


# ---------------------------------------------------------------- metrics
def frc(a, b, nbin=64):
    """Fourier ring correlation.  Rule 18: FRC CANNOT be fooled upward by noise
    amplification -- amplified noise is uncorrelated between the two halves and
    pushes FRC DOWN.  It CAN be fooled upward by anything correlated between the
    halves, e.g. a shared blur; so a blurrier merge can hold FRC high at low f."""
    n = a.shape[0]
    w1 = np.hanning(n)
    w = np.outer(w1, w1)
    A = np.fft.fftshift(np.fft.fft2((a - a.mean()) * w))
    B = np.fft.fftshift(np.fft.fft2((b - b.mean()) * w))
    cy, cx = n // 2, n // 2
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    rmax = n // 2
    edges = np.linspace(0, rmax, nbin + 1)
    fr, ff, cnt = [], [], []
    for i in range(nbin):
        m = (rr >= edges[i]) & (rr < edges[i + 1])
        if m.sum() < 8:
            continue
        num = np.real(np.sum(A[m] * np.conj(B[m])))
        den = np.sqrt(np.sum(np.abs(A[m]) ** 2) * np.sum(np.abs(B[m]) ** 2))
        fr.append(num / max(den, 1e-30))
        ff.append(0.5 * (edges[i] + edges[i + 1]) / n)   # cyc/px
        cnt.append(int(m.sum()))
    return np.array(ff), np.array(fr), np.array(cnt)


def frc_cross(ff, fr, thr=1.0 / 7.0):
    """First frequency at which FRC drops below the 1/7 threshold and stays
    below for two consecutive bins (guards against a single noisy bin)."""
    for i in range(len(fr) - 1):
        if fr[i] < thr and fr[i + 1] < thr:
            if i == 0:
                return float(ff[0])
            f0, f1 = ff[i - 1], ff[i]
            r0, r1 = fr[i - 1], fr[i]
            if r0 == r1:
                return float(f1)
            return float(f0 + (r0 - thr) * (f1 - f0) / (r0 - r1))
    return float(ff[-1])


def hp_sd(a, w=9):
    return float((a - uniform_filter(a, w)).std())


def band_power(a, fc=F_SIG):
    n = a.shape[0]
    w1 = np.hanning(n); w = np.outer(w1, w1)
    A = np.abs(np.fft.fftshift(np.fft.fft2((a - a.mean()) * w))) ** 2
    cy = cx = n // 2
    yy, xx = np.mgrid[0:n, 0:n]
    rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2) / n
    return float(A[rr < fc].sum()), float(A[(rr >= fc) & (rr < 0.5)].sum())

"""M113-ca: an inter-channel displacement estimator that is NOT phase correlation.

FAILURE MODES DELIBERATELY NOT SHARED WITH ORCH's ESTIMATOR
  ORCH: FFT, spectral whitening X/|X|, correlation-surface argmax, parabolic
        3-point sub-pixel fit, Hann window, periodic wraparound.
  THIS: pure spatial domain. No FFT in the estimator. No argmax. No peak fit.
        A 4-parameter linear least squares per window.

MODEL. Within a window, red is green displaced by s = (sx, sy) plus a per-window
photometric gain and offset -- the gain matters because R and G carry different
scene contrast, and failing to fit it is what killed ca_radial.py's proxy:

    R[x] = a * G[x - s] + b

Linearising G[x - s] ~= G[x] - s.grad G gives design columns [G, Gx, Gy, 1] with
coefficients [a, cx, cy, b], and the CORRECTION to the current s is -(cx/a, cy/a).

SIGN. The first version of this file accumulated +cx/a and warped G by +s. Both
signs were wrong, and because the two errors were in the update AND in the warp
the iteration DIVERGED rather than merely inverting: it returned +3.13 px on data
whose true displacement is -0.15 px, and a plant slope of -3.10 instead of +1.00.
Written out here because discipline 774 says read the sign off the control -- and
that is exactly what caught it. `selftest()` is that control, and it runs on a
synthetic image with a known planted shift, so it cannot pass by accident.
"""
import numpy as np

def _grad(g):
    gx = np.zeros_like(g); gy = np.zeros_like(g)
    gx[:, 1:-1] = 0.5 * (g[:, 2:] - g[:, :-2])
    gy[1:-1, :] = 0.5 * (g[2:, :] - g[:-2, :])
    return gx, gy

def fshift2(t, dx, dy):
    """Exact band-limited translation: new[y,x] = old[y-dy, x-dx]."""
    H, W = t.shape
    kx = np.fft.rfftfreq(W); ky = np.fft.fftfreq(H)
    ph = np.exp(-2j * np.pi * (kx[None, :] * dx + ky[:, None] * dy))
    return np.fft.irfft2(np.fft.rfft2(t) * ph, s=(H, W))

def lk_shift(r_tile, g_tile, pad, win, iters=6, tol=1e-4, max_step=2.0):
    """Displacement of r relative to g (r content sits at g's position + s).

    Returns (sx, sy, cond); cond is the normalised smallest singular value of the
    design matrix, so a window with no edges reports unsolvable rather than
    returning a confident zero.
    """
    sx = sy = 0.0
    sl = (slice(pad, pad + win), slice(pad, pad + win))
    r = r_tile[sl].astype(np.float64)
    cond = 0.0
    for _ in range(iters):
        gs = fshift2(g_tile, sx, sy) if (sx or sy) else g_tile
        g = gs[sl].astype(np.float64)
        gx, gy = _grad(g)
        m = np.ones_like(g, dtype=bool)
        m[:2, :] = m[-2:, :] = m[:, :2] = m[:, -2:] = False
        A = np.stack([g[m], gx[m], gy[m], np.ones(int(m.sum()))], axis=1)
        y = r[m]
        s = np.sqrt((A * A).mean(axis=0)); s[s == 0] = 1.0
        An = A / s
        try:
            sv = np.linalg.svd(An, compute_uv=False)
            cond = float(sv[-1] / sv[0])
            coef, *_ = np.linalg.lstsq(An, y, rcond=None)
        except np.linalg.LinAlgError:
            return float("nan"), float("nan"), 0.0
        coef = coef / s
        a, cx, cy = coef[0], coef[1], coef[2]
        if not np.isfinite(a) or abs(a) < 1e-6:
            return float("nan"), float("nan"), cond
        dsx, dsy = -cx / a, -cy / a
        if not (np.isfinite(dsx) and np.isfinite(dsy)):
            return float("nan"), float("nan"), cond
        n = float(np.hypot(dsx, dsy))
        if n > max_step:
            dsx, dsy = dsx * max_step / n, dsy * max_step / n
        sx += dsx; sy += dsy
        if abs(dsx) < tol and abs(dsy) < tol:
            break
    return sx, sy, cond

def radial_tangential(dx, dy, wx, wy, cx, cy):
    rx, ry = wx - cx, wy - cy
    n = float(np.hypot(rx, ry))
    if n < 1e-6:
        return 0.0, 0.0
    ux, uy = rx / n, ry / n
    return dx * ux + dy * uy, -dx * uy + dy * ux

def selftest(verbose=True):
    """Plant a known shift into a synthetic band-limited image and recover it.

    Synthetic, so the ground truth is exact and independent of any photograph.
    A DIFFERENT photometric gain and offset are planted too, because the whole
    point of the 4-parameter fit is that those must not leak into the shift.
    """
    rng = np.random.default_rng(7)
    N = 256
    base = rng.normal(size=(N, N))
    f = np.fft.fftfreq(N)
    rad = np.hypot(f[:, None], f[None, :])
    base = np.real(np.fft.ifft2(np.fft.fft2(base) * np.exp(-(rad / 0.12) ** 2)))
    base = 1000.0 + 300.0 * base / base.std()
    ok = True
    rows = []
    for planted in (0.0, 0.05, 0.1, 0.155, 0.25, 0.5, 1.0, -0.155, -0.5, -1.0):
        r_t = fshift2(base, planted, 0.0) * 0.7 + 120.0     # gain 0.7, offset 120
        sx, sy, cond = lk_shift(r_t, base, 64, 128)
        err = sx - planted
        rows.append((planted, sx, err))
        if abs(err) > 0.01:
            ok = False
        if verbose:
            print("   planted %+.3f  recovered %+.4f  err %+.4f  (sy %+.4f)"
                  % (planted, sx, err, sy))
    if verbose:
        print("   SELFTEST %s (bar: every |err| <= 0.010 px, gain 0.7 offset 120 planted)"
              % ("PASS" if ok else "FAIL"))
    return ok, rows
"""ORCH: measure lateral CA as what it physically IS -- a radial displacement between
colour channels, in pixels -- and validate the estimator with a blur-free planted shift.

WHY THIS FILE EXISTS. The first attempt (ca_radial.py + ca_control.py) scored lateral CA
by the anti-correlation of the (R-G) and (B-G) residuals at edge pixels. That metric
FAILED its positive control:

  * it reads -0.778 at the optical centre, where lateral CA is zero BY CONSTRUCTION,
    so its absolute value is dominated by scene hue structure, not misregistration;
  * planting MORE lateral CA moved it in the wrong direction and non-monotonically,
    because the bilinear plant blurred R and B while leaving G sharp -- the plant
    changed sharpness, and the metric answered about sharpness.

Both defects have the same root: the statistic was a proxy. This file measures the
quantity itself.

METHOD. Per window, estimate the sub-pixel translation of R against G and of B against G
by phase correlation on GRADIENT MAGNITUDE (edges register across channels even when the
colours differ), then project that translation onto the radial direction from the optical
centre. Lateral CA is by definition radial, so the radial component is signal and the
tangential component is a built-in noise gauge: a valid estimate must have
|tangential| << |radial| in the aggregate, and if it does not, the estimator is
picking up scene structure rather than channel misregistration.

CONTROL. The plant is an INTEGER pixel roll of one channel. An integer shift moves the
data without resampling it, so it cannot change sharpness -- which is precisely the
confound that killed the previous attempt. The estimator must recover the planted shift
in pixels, with the correct sign, at +/-1 and +/-2 px, and the sign convention is read
off the control rather than assumed.
"""

import json
import os

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

import importlib.util

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("ca_radial", os.path.join(_here, "ca_radial.py"))
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)
load_tiff_u16 = _m.load_tiff_u16
grad_mag = _m.grad_mag

R1 = r"C:\dev\strehl-out\M114-ca-verify\r1"
OUT = r"C:\dev\strehl-out\ORCH-ca-radial"

WIN = 128
MIN_EDGE_ENERGY = 60.0
MIN_PEAK = 0.06          # phase-correlation peak sharpness; below this the shift is noise
MAX_SHIFT = 6.0          # px; a larger estimate is a mis-lock, not a fringe
SUPPORT_HI = 0.788

RINGS = [0.045, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.83, 0.93]

_HANN = np.outer(np.hanning(WIN), np.hanning(WIN)).astype(np.float32)


def _prep(ch):
    g = grad_mag(ch.astype(np.float32))
    g = g - g.mean()
    return g * _HANN


def shift_of(b, a):
    """Sub-pixel translation of b relative to a, by phase correlation. Returns
    (dy, dx, peak). Sign convention is established empirically by the control."""
    A = np.fft.rfft2(_prep(a))
    B = np.fft.rfft2(_prep(b))
    X = A * np.conj(B)
    X /= (np.abs(X) + 1e-9)
    c = np.fft.irfft2(X, s=(WIN, WIN))
    idx = int(np.argmax(c))
    py, px = idx // WIN, idx % WIN
    peak = float(c[py, px])

    def sub(v0, v1, v2):
        d = v0 - 2.0 * v1 + v2
        return 0.0 if abs(d) < 1e-12 else 0.5 * (v0 - v2) / d

    dy = sub(c[(py - 1) % WIN, px], c[py, px], c[(py + 1) % WIN, px])
    dx = sub(c[py, (px - 1) % WIN], c[py, px], c[py, (px + 1) % WIN])
    fy = py + dy
    fx = px + dx
    if fy > WIN / 2:
        fy -= WIN
    if fx > WIN / 2:
        fx -= WIN
    # Sign convention is NOT assumed. The integer-roll control in control() measured
    # recovered = -planted + 0.045 px, i.e. this construction returns the negative of
    # the displacement of b relative to a. Negate here so the returned value is the
    # displacement of b, and let the control re-verify it on every run.
    return -fy, -fx, peak


def radial_tangential(dy, dx, wx, wy, cx, cy):
    rx, ry = wx - cx, wy - cy
    n = float(np.hypot(rx, ry))
    if n < 1e-6:
        return 0.0, 0.0
    ux, uy = rx / n, ry / n
    return dx * ux + dy * uy, -dx * uy + dy * ux


def windows_on_ring(off, r, cx, cy, half_diag, W, H, n_ang=240):
    out = []
    for k in range(n_ang):
        th = 2.0 * np.pi * k / n_ang
        px = cx + r * half_diag * np.cos(th)
        py = cy + r * half_diag * np.sin(th)
        x0 = int(round(px - WIN / 2.0))
        y0 = int(round(py - WIN / 2.0))
        if x0 < 4 or y0 < 4 or x0 + WIN > W - 4 or y0 + WIN > H - 4:
            continue
        g = np.asarray(off[y0:y0 + WIN, x0:x0 + WIN, 1]).astype(np.float32)
        if float(grad_mag(g).mean()) < MIN_EDGE_ENERGY:
            continue
        out.append((x0, y0))
    return out


def measure(img, wins, cx, cy):
    """Median radial and |tangential| channel displacement, in px, over a ring."""
    rad_r, rad_b, tan = [], [], []
    for (x0, y0) in wins:
        w = np.asarray(img[y0:y0 + WIN, x0:x0 + WIN, :])
        g = w[..., 1]
        wx, wy = x0 + WIN / 2.0, y0 + WIN / 2.0
        for ch, acc in ((0, rad_r), (2, rad_b)):
            dy, dx, pk = shift_of(w[..., ch], g)
            if pk < MIN_PEAK or abs(dy) > MAX_SHIFT or abs(dx) > MAX_SHIFT:
                continue
            rr, tt = radial_tangential(dy, dx, wx, wy, cx, cy)
            acc.append(rr)
            tan.append(abs(tt))
    f = lambda v: float(np.median(v)) if v else float("nan")
    return f(rad_r), f(rad_b), f(tan), len(rad_r), len(rad_b)


def control(off, cx, cy, half_diag, W, H):
    print("=" * 84)
    print("POSITIVE CONTROL -- integer pixel roll of R (no resampling, so no blur change)")
    print("=" * 84)
    wins = windows_on_ring(off, 0.50, cx, cy, half_diag, W, H, n_ang=90)[:40]
    print("r=0.50 ring, %d windows\n" % len(wins))
    print("%-14s %14s %14s %10s" % ("planted dx", "recovered dx", "error", "n"))
    rows = []
    for planted in (-2, -1, 0, 1, 2):
        got = []
        for (x0, y0) in wins:
            w = np.asarray(off[y0:y0 + WIN, x0:x0 + WIN, :]).astype(np.float32)
            # Integer roll sourced from the full image so the window stays full of
            # real data rather than wrapped edge content.
            r_shift = np.asarray(off[y0:y0 + WIN, x0 - planted:x0 - planted + WIN, 0]).astype(np.float32)
            dy, dx, pk = shift_of(r_shift, w[..., 1])
            if pk < MIN_PEAK or abs(dx) > MAX_SHIFT:
                continue
            got.append(dx)
        med = float(np.median(got)) if got else float("nan")
        rows.append((planted, med, len(got)))
        print("%-14d %14.3f %14.3f %10d" % (planted, med, med - planted, len(got)))
    print()
    errs = [abs(m - p) for p, m, n in rows if n > 0 and np.isfinite(m)]
    ok = bool(errs) and max(errs) <= 0.25
    print("PASS BAR: every planted shift recovered to within 0.25 px, correct sign.")
    print("RESULT  : max |error| = %.3f px  ->  %s" % (max(errs) if errs else float("nan"),
                                                       "PASS" if ok else "FAIL"))
    print()
    return ok


def main():
    off, W, H = load_tiff_u16(os.path.join(R1, "off.tif"))
    on, _, _ = load_tiff_u16(os.path.join(R1, "on.tif"))
    cx, cy = W / 2.0, H / 2.0
    half_diag = float(np.hypot(cx, cy))
    os.makedirs(OUT, exist_ok=True)

    if not control(off, cx, cy, half_diag, W, H):
        print("Estimator not validated -- refusing to print the radial table.")
        return

    print("=" * 84)
    print("LATERAL CA AS RADIAL CHANNEL DISPLACEMENT (px). CA fit support r = 0.208..%.3f"
          % SUPPORT_HI)
    print("=" * 84)
    print("%-7s %-8s %5s %9s %9s %9s %9s %9s"
          % ("r", "support", "n", "R off", "R on", "B off", "B on", "|tan| off"))
    rows = []
    for r in RINGS:
        wins = windows_on_ring(off, r, cx, cy, half_diag, W, H)
        if len(wins) < 5:
            print("%-7.3f  (only %d usable windows -- skipped)" % (r, len(wins)))
            continue
        ro, bo, to, nro, nbo = measure(off, wins, cx, cy)
        rn, bn, tn, nrn, nbn = measure(on, wins, cx, cy)
        side = "INSIDE" if r <= SUPPORT_HI else "OUTSIDE"
        rows.append(dict(r=r, side=side, n=len(wins), R_off=ro, R_on=rn,
                         B_off=bo, B_on=bn, tan_off=to, tan_on=tn))
        print("%-7.3f %-8s %5d %9.3f %9.3f %9.3f %9.3f %9.3f"
              % (r, side, len(wins), ro, rn, bo, bn, to))
    print("=" * 84)
    print("|tan| is the TANGENTIAL displacement, which lateral CA cannot produce. It is")
    print("the estimator's own noise floor: a radial number smaller than it is not signal.")
    with open(os.path.join(OUT, "ca_shift.json"), "w") as fh:
        json.dump(rows, fh, indent=2)
    print("\nwrote ca_shift.json")


if __name__ == "__main__":
    main()

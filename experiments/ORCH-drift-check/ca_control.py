"""ORCH: positive control for the radial CA instrument in ca_radial.py.

ca_radial.py has a NULL (the optical centre, where lateral CA is zero by construction,
and where the measured median change is -0.06% over 180 windows). A null shows the
instrument is quiet. It does NOT show the instrument can respond at all -- a metric
that always returns zero would pass it.

This plants lateral CA of KNOWN magnitude into the OFF arm and asks whether the
statistic moves monotonically with the planted amount. Lateral CA is, to first order,
a per-channel radial SCALE error about the optical centre, so the plant is exactly
that: resample R by (1+s) and B by (1-s) about the centre, leaving G fixed.

Pass condition, registered BEFORE running:
  (a) s = 0 must reproduce the unplanted statistic to within +/-0.02 in correlation
      (this is the plant's own null -- it catches resampling blur masquerading as
      signal, since bilinear interpolation at s=0 is the identity);
  (b) the R/B correlation must become monotonically MORE NEGATIVE as |s| grows;
  (c) the response must be visible at s = 2e-4, which at r = 0.5 is a sub-pixel
      0.42 px shear -- below that the instrument cannot claim to see the real thing.
"""

import os

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

import importlib.util

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("ca_radial", os.path.join(_here, "ca_radial.py"))
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)   # main() is guarded by __name__, so this does not run it

load_tiff_u16 = _m.load_tiff_u16
fringe = _m.fringe
grad_mag = _m.grad_mag

R1 = r"C:\dev\strehl-out\M114-ca-verify\r1"
WIN = 192
RING = 0.50
SHEARS = [0.0, 2e-4, 5e-4, 1e-3, 2e-3]


def plant(img, x0, y0, cx, cy, s):
    """Resample R by (1+s) and B by (1-s) about (cx,cy); G untouched. Bilinear."""
    H, W, _ = img.shape
    yy, xx = np.mgrid[y0:y0 + WIN, x0:x0 + WIN].astype(np.float64)
    out = np.empty((WIN, WIN, 3), np.float32)
    out[..., 1] = img[y0:y0 + WIN, x0:x0 + WIN, 1].astype(np.float32)
    for ch, sc in ((0, 1.0 + s), (2, 1.0 - s)):
        sx = cx + (xx - cx) / sc
        sy = cy + (yy - cy) / sc
        x_i = np.clip(np.floor(sx).astype(np.int64), 0, W - 2)
        y_i = np.clip(np.floor(sy).astype(np.int64), 0, H - 2)
        fx = (sx - x_i).astype(np.float32)
        fy = (sy - y_i).astype(np.float32)
        p = img[..., ch]
        v00 = p[y_i, x_i].astype(np.float32)
        v01 = p[y_i, x_i + 1].astype(np.float32)
        v10 = p[y_i + 1, x_i].astype(np.float32)
        v11 = p[y_i + 1, x_i + 1].astype(np.float32)
        out[..., ch] = ((v00 * (1 - fx) + v01 * fx) * (1 - fy)
                        + (v10 * (1 - fx) + v11 * fx) * fy)
    return out


def main():
    off, W, H = load_tiff_u16(os.path.join(R1, "off.tif"))
    cx, cy = W / 2.0, H / 2.0
    half_diag = float(np.hypot(cx, cy))

    # Reuse the SAME window-selection rule as ca_radial.py, on the OFF arm.
    wins = []
    for k in range(180):
        th = 2.0 * np.pi * k / 180.0
        px = cx + RING * half_diag * np.cos(th)
        py = cy + RING * half_diag * np.sin(th)
        x0 = int(round(px - WIN / 2.0))
        y0 = int(round(py - WIN / 2.0))
        if x0 < 1 or y0 < 1 or x0 + WIN > W - 2 or y0 + WIN > H - 2:
            continue
        g = np.asarray(off[y0:y0 + WIN, x0:x0 + WIN, 1]).astype(np.float32)
        if float(grad_mag(g).mean()) < 60.0:
            continue
        wins.append((x0, y0))
    print("positive control on the r=%.2f ring: %d windows, planted radial shear on R/B"
          % (RING, len(wins)))
    print("(at r=%.2f the shear s displaces a channel by s * %.0f px)\n" % (RING, RING * half_diag))

    base_corr = []
    for (x0, y0) in wins:
        st = fringe(np.asarray(off[y0:y0 + WIN, x0:x0 + WIN, :]))
        if st:
            base_corr.append(st["corr"])
    base = float(np.median(base_corr))
    print("unplanted OFF arm, median R/B correlation = %+.4f  (n=%d)\n" % (base, len(base_corr)))

    print("%-10s %10s %12s %12s %12s" % ("shear s", "px @ r", "med corr", "d vs base", "med amp"))
    results = []
    for s in SHEARS:
        cs, amps = [], []
        for (x0, y0) in wins:
            w = plant(off, x0, y0, cx, cy, s)
            st = fringe(np.clip(w, 0, 65535).astype(np.uint16))
            if st:
                cs.append(st["corr"])
                amps.append(st["amp"])
        mc = float(np.median(cs))
        ma = float(np.median(amps))
        results.append((s, mc, ma))
        print("%-10.1e %10.2f %12.4f %12.4f %12.1f"
              % (s, s * RING * half_diag, mc, mc - base, ma))

    print()
    s0 = results[0]
    ok_a = abs(s0[1] - base) <= 0.02
    print("(a) plant's own null  s=0 reproduces base to %+.4f (bar +/-0.02) : %s"
          % (s0[1] - base, "PASS" if ok_a else "FAIL"))
    corrs = [r[1] for r in results]
    ok_b = all(corrs[i + 1] <= corrs[i] + 1e-9 for i in range(len(corrs) - 1))
    print("(b) monotonically more negative with |s|                        : %s"
          % ("PASS" if ok_b else "FAIL"))
    ok_c = (corrs[1] - base) < -0.01
    print("(c) responds at s=2e-4 (%.2f px), delta %+.4f, bar < -0.01      : %s"
          % (2e-4 * RING * half_diag, corrs[1] - base, "PASS" if ok_c else "FAIL"))
    print()
    if ok_a and ok_b and ok_c:
        print("INSTRUMENT VALIDATED: it is quiet on the null AND responds to a planted")
        print("lateral CA of known size. The radial table in ca_radial.py may be read.")
    else:
        print("INSTRUMENT NOT VALIDATED: do not cite the radial table.")


if __name__ == "__main__":
    main()

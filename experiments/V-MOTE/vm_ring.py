"""V-MOTE P8 -- (a) the mote's centroid on the flats, (b) what the ON arm leaves.

(a) A coordinate is only "correct" relative to the feature's own centroid, so
    the centroid is measured rather than eyeballed: intensity-weighted centre of
    the detrended deficit over the pixels below half the peak depth.
(b) The ON crop shows a faint ring.  Ring amplitude is measured as the radial
    profile of the ON arm's residual about the corrected centre, against the
    OFF arm's, so "essentially gone" is a number and not an impression.
"""
import os, sys
import numpy as np
import tifffile

CACHE = r"C:\dev\strehl-out\V-MOTE\cache"
AB = r"C:\dev\strehl-out\V-MOTE\ab"
QH, QW = 2344, 3520
SITE_Q = (3434, 2305)


def quad_fit_res(f, cx, cy, R, r_in, r_out, h, w):
    y0, y1 = max(0, cy - R), min(h, cy + R + 1)
    x0, x1 = max(0, cx - R), min(w, cx + R + 1)
    sub = f[y0:y1, x0:x1]
    dy = (np.arange(y0, y1) - cy)[:, None] * np.ones((1, x1 - x0))
    dx = np.ones((y1 - y0, 1)) * (np.arange(x0, x1) - cx)[None, :]
    r = np.hypot(dx, dy)
    m = (r >= r_in) & (r <= r_out)
    A = np.stack([np.ones(m.sum()), dx[m], dy[m], dx[m]**2, dx[m]*dy[m], dy[m]**2], 1)
    c, *_ = np.linalg.lstsq(A, sub[m], rcond=None)
    bg = c[0] + c[1]*dx + c[2]*dy + c[3]*dx**2 + c[4]*dx*dy + c[5]*dy**2
    return sub / bg - 1.0, dx, dy, r


def main():
    f = np.load(os.path.join(CACHE, "flat_all.npy")).astype(np.float64)
    cx, cy = SITE_Q
    res, dx, dy, r = quad_fit_res(f, cx, cy, 150, 90, 140, QH, QW)
    peak = res[r <= 20].min()
    m = (res <= 0.5 * peak) & (r <= 45)
    wgt = -(res[m] - 0.5 * peak)
    gx = float((dx[m] * wgt).sum() / wgt.sum())
    gy = float((dy[m] * wgt).sum() / wgt.sum())
    print("== flats: mote 2 centroid ==")
    print("  peak residual %+0.3f%%  half-depth pixels %d" % (100 * peak, int(m.sum())))
    print("  centroid offset from map coord (3434,2305): (%+0.2f, %+0.2f) quads" % (gx, gy))
    print("  centroid            quad (%.1f, %.1f) = photosite (%.0f, %.0f)"
          % (cx + gx, cy + gy, 2 * (cx + gx), 2 * (cy + gy)))
    eq = np.sqrt(m.sum() / np.pi)
    print("  equivalent radius %.1f quads = %.0f photosites (diameter %.0f photosites)"
          % (eq, 2 * eq, 4 * eq))

    print("\n== A/B: what the ON arm leaves at the mote ==")
    off = tifffile.imread(os.path.join(AB, "flower-bud-alone-cpl_OFF.tiff"))[..., 1].astype(np.float64)
    on = tifffile.imread(os.path.join(AB, "flower-bud-alone-cpl_ON.tiff"))[..., 1].astype(np.float64)
    h, w = off.shape
    C = (6878, 4620)
    print("  radial profile about (%d,%d), background = quadratic on 180<=r<=320 px" % C)
    print("     r(px)      OFF%%      ON%%")
    ro, *_ = quad_fit_res(off, C[0], C[1], 320, 180, 320, h, w)
    rn, _, _, rr = quad_fit_res(on, C[0], C[1], 320, 180, 320, h, w)
    for lo in range(0, 120, 10):
        mm = (rr >= lo) & (rr < lo + 10)
        print("     %3d-%3d  %+8.3f  %+8.3f" % (lo, lo + 10, 100 * np.median(ro[mm]), 100 * np.median(rn[mm])))
    mm = rr < 200
    print("  worst 10-px annulus |ON| = %.3f%%; OFF core (r<=16) %+0.3f%% -> ON %+0.3f%%"
          % (max(abs(100 * np.median(rn[(rr >= lo2) & (rr < lo2 + 10)])) for lo2 in range(0, 120, 10)),
             100 * np.median(ro[rr <= 16]), 100 * np.median(rn[rr <= 16])))
    return 0


if __name__ == "__main__":
    sys.exit(main())

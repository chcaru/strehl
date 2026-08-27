"""Grid geometry probe: is the Lightroom export a SIMILARITY transform of
strehl's linear develop of the same RAW, or something worse?

Motivation.  The first probe (5 positions) found the integer shift between the
two developments of frame 32 varying by 26 px in dy across the frame.  If the
only difference between the two files were tone, the shift would be constant.
If the only additional difference were a uniform crop/scale, the shift would be
an AFFINE function of position.  Anything left over after fitting an affine is
a non-linear warp, and the only plausible source of one here is a lens
distortion correction applied by one developer and not the other.

Why it matters.  V-HEADTOHEAD2 concluded the strehl-vs-Zerene fine-scale gap
was a TONE measurement.  If the comparator's inputs were also geometrically
warped relative to a linear develop, then re-developing linearly does not by
itself make the two arms comparable -- it removes one confound and leaves
another.  That has to be known before anyone spends money on a licence to
finish the job.

Method.  Integer cross-correlation (h2.integer_shift, the prior lane's own
registration primitive, chosen there over phase correlation for reasons stated
in its docstring) at a grid of positions.  Gate on correlation peak so that
low-contrast or defocused tiles cannot vote.  Then least-squares fit

    (dy, dx) = A + B . (y, x)

which spans translation, uniform scale, anisotropic scale, rotation and shear,
and report the residual.  A residual at the sub-pixel level means similarity is
enough.  A residual of several px with radial structure means a warp.

FALSIFIER (rule 20): if the residual rms is below ~0.7 px the warp hypothesis
is dead and the geometry story is just "a crop and a scale", which the prior
lane already knew how to handle.
"""
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "V-HEADTOHEAD2"))
import h2  # noqa: E402

LIN = r"C:\dev\strehl-out\V-LINEAR\lintiff"
LRD = r"D:\edited\macro\test2"
T = 384
PEAK_MIN = 0.70          # same spirit as h2h2b.PEAK_MIN = 0.30, stricter here
                         # because these are two developments of ONE exposure:
                         # they share their noise, so a correct match must
                         # correlate far better than two independent stacks do.


def open_luma(path):
    a = tifffile.memmap(path, mode="r")
    return a


def crop(a, y0, x0, t):
    return h2.luma709(np.asarray(a[y0:y0 + t, x0:x0 + t, :3], np.float64))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 32
    lin = open_luma(os.path.join(LIN, f"DSC{n:05d}.tif"))
    lr = open_luma(os.path.join(LRD, f"20260507-DSC{n:05d}.tif"))
    H, W = lr.shape[0], lr.shape[1]
    print(f"frame {n}: LR {W}x{H}  LIN {lin.shape[1]}x{lin.shape[0]}")

    ys = np.linspace(600, H - 600 - T, 5).astype(int)
    xs = np.linspace(600, W - 600 - T, 6).astype(int)
    rows = []
    for y in ys:
        for x in xs:
            ref = crop(lr, y, x, T)
            mov = crop(lin, y + 8, x + 12, T)
            dy, dx, pk = h2.integer_shift(ref, mov, maxshift=28)
            rows.append((y, x, dy, dx, pk))
    r = np.array(rows, float)
    ok = r[:, 4] >= PEAK_MIN
    rail = (np.abs(r[:, 2]) >= 28) | (np.abs(r[:, 3]) >= 28)
    ok &= ~rail
    print(f"tiles {len(r)}, pass peak>={PEAK_MIN}: {ok.sum()}, at search rail: {rail.sum()}")
    if ok.sum() < 8:
        print("too few usable tiles to fit geometry")
        return

    y, x = r[ok, 0], r[ok, 1]
    dy, dx = r[ok, 2], r[ok, 3]
    print(f"\nraw shift range over accepted tiles: "
          f"dy [{dy.min():.0f},{dy.max():.0f}]  dx [{dx.min():.0f},{dx.max():.0f}]")

    # constant-only model (pure translation)
    res_t = np.hypot(dy - dy.mean(), dx - dx.mean())
    # affine model: [1, y, x] -> dy and dx
    M = np.column_stack([np.ones_like(y), y, x])
    cy, *_ = np.linalg.lstsq(M, dy, rcond=None)
    cx, *_ = np.linalg.lstsq(M, dx, rcond=None)
    res_a = np.hypot(dy - M @ cy, dx - M @ cx)

    print(f"\npure translation  : residual rms {np.sqrt((res_t ** 2).mean()):6.2f} px"
          f"   max {res_t.max():5.2f} px")
    print(f"affine (transl+scale+rot+shear): residual rms "
          f"{np.sqrt((res_a ** 2).mean()):6.2f} px   max {res_a.max():5.2f} px")
    print(f"  d(dy)/dy = {cy[1]:+.5f}   d(dy)/dx = {cy[2]:+.5f}")
    print(f"  d(dx)/dy = {cx[1]:+.5f}   d(dx)/dx = {cx[2]:+.5f}")
    print(f"  implied scale LIN/LR: y {1 + cy[1]:.5f}  x {1 + cx[2]:.5f}")

    rms_a = np.sqrt((res_a ** 2).mean())

    # ---- radial model -------------------------------------------------
    # If the residual is a lens distortion correction applied by one developer
    # and not the other, it is radial about the image centre with the standard
    # even-order form  dr = r (k1 r^2 + k2 r^4).  Fit that JOINTLY with the
    # affine, sharing k1/k2 between the two components as the physics requires.
    #
    # THE COMPARISON MUST BE LIKE FOR LIKE.  An earlier version of this block
    # compared a robust (outlier-dropped) affine+radial fit against a
    # non-robust affine fit, and "concluded" a warp from what was actually just
    # the outlier rejection: the fitted k1 was -0.005 px, i.e. nothing.  Both
    # models are therefore fitted on the SAME tile set, and the rejection is
    # decided by the AFFINE model's residual so the radial term cannot be
    # credited with removing tiles it did not earn.
    ccy, ccx = H / 2.0, W / 2.0
    yc, xc = y + T / 2.0 - ccy, x + T / 2.0 - ccx
    rn = np.hypot(ccy, ccx)
    r2 = (yc ** 2 + xc ** 2) / rn ** 2
    n = len(y)
    Z, O = np.zeros(n), np.ones(n)
    Ay = np.column_stack([O, y, x, Z, Z, Z, yc * r2, yc * r2 * r2])
    Ax = np.column_stack([Z, Z, Z, O, y, x, xc * r2, xc * r2 * r2])

    def fit(cols, sel):
        m = int(sel.sum())
        D = np.vstack([Ay[sel][:, cols], Ax[sel][:, cols]])
        bb = np.concatenate([dy[sel], dx[sel]])
        c, *_ = np.linalg.lstsq(D, bb, rcond=None)
        p = D @ c
        rr = np.hypot(dy[sel] - p[:m], dx[sel] - p[m:])
        return c, rr, float(np.sqrt((rr ** 2).mean()))

    AFF = [0, 1, 2, 3, 4, 5]
    RAD = [0, 1, 2, 3, 4, 5, 6, 7]
    allt = np.ones(n, bool)
    _, ra_all, rms_a_all = fit(AFF, allt)
    cr, _, rms_r_all = fit(RAD, allt)
    keep = ra_all <= 2.5 * np.median(ra_all)
    _, _, rms_a_rob = fit(AFF, keep)
    cr2, _, rms_r_rob = fit(RAD, keep)

    print(f"affine + radial (k1,k2)        : residual rms {rms_r_all:6.2f} px")
    print(f"  k1 = {cr[6]:+.4f} px   k2 = {cr[7]:+.4f} px   "
          f"(corner displacement contributed by each term, r=1)")
    print(f"\n  robust set = tiles within 2.5x median AFFINE residual: "
          f"{int(keep.sum())} of {n}")
    print(f"  affine          on robust set : residual rms {rms_a_rob:6.2f} px")
    print(f"  affine + radial on robust set : residual rms {rms_r_rob:6.2f} px")
    print(f"  k1 = {cr2[6]:+.4f} px   k2 = {cr2[7]:+.4f} px")
    print()
    gain = (rms_a_rob - rms_r_rob) / rms_a_rob if rms_a_rob > 0 else 0.0
    if rms_a_rob < 0.7:
        print("VERDICT: a similarity/affine transform accounts for the geometry. "
              "No warp. Handle it the way V-HEADTOHEAD2 handled scale.")
    elif gain > 0.3:
        print(f"VERDICT: NON-LINEAR RADIAL WARP. On the same tiles an affine "
              f"leaves {rms_a_rob:.2f} px rms and adding a two-parameter radial "
              f"term takes it to {rms_r_rob:.2f} px, a {100*gain:.0f}% "
              "reduction. The two developments of the SAME RAW differ by a lens "
              "distortion correction, not only by tone.")
    else:
        print(f"VERDICT: the geometry is affine to within {rms_a_rob:.2f} px rms "
              f"and a radial term buys only {100*gain:.0f}% of that. NO evidence "
              "of a lens-distortion warp between the two developments; the "
              "residual is registration scatter on single frames, not a "
              "systematic geometric difference.")
    print(f"  scale LIN/LR from the affine fit: y {1 + cy[1]:.5f}  x "
          f"{1 + cx[2]:.5f}   (pixel-count ratio {7032/7008:.5f})")

    print(f"\n{'lr_y':>6} {'lr_x':>6} {'dy':>4} {'dx':>4} {'peak':>6} {'res_aff':>8}")
    j = 0
    for i in range(len(r)):
        if not ok[i]:
            print(f"{r[i,0]:6.0f} {r[i,1]:6.0f} {r[i,2]:4.0f} {r[i,3]:4.0f} "
                  f"{r[i,4]:6.3f} {'rejected':>8}")
        else:
            print(f"{r[i,0]:6.0f} {r[i,1]:6.0f} {r[i,2]:4.0f} {r[i,3]:4.0f} "
                  f"{r[i,4]:6.3f} {res_a[j]:8.2f}")
            j += 1


if __name__ == "__main__":
    main()

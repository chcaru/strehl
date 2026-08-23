"""M60 — the defocus side-lobe: a single-depth mechanism that makes veil pixels bimodal.

Found while checking P1's own null. In the D = 0 plant -- ONE depth, no
occlusion of anything by anything at a different distance -- the through-focus
curve of a pixel a few px from a high-contrast edge has THREE local maxima: the
focus spike, and a symmetric pair of side-lobes either side of it.

The mechanism is elementary and does not depend on the compositing model. For a
step edge of height dI blurred by a Gaussian of width sigma, the gradient at a
fixed offset x from the edge is

    |grad I|(x) = dI * G_sigma(x) = dI * exp(-x^2 / 2 sigma^2) / (sigma * sqrt(2 pi))

which is ZERO at sigma = 0, rises to a maximum at sigma = x, and decays after.
With sigma_k = rate * |k - k_focus| that maximum lands at

    |k - k_focus| = x / rate                                        (DERIVED)

i.e. a pair of secondary peaks whose separation from the primary GROWS LINEARLY
with distance from the edge. A genuine second depth puts its peak at a FIXED
frame regardless of distance from the edge. That difference is measurable, and
it is measurable on real data where nothing is planted.

B2 checks the mechanism survives the physically correct single-depth render
(composite first, then blur) -- so it is not an artefact of the layered matte.
B3 checks it against the analytic law.
P2 asks, in a plant with a KNOWN second depth, whether the detector's k2 lands
on the true background peak or on the side-lobe.
"""

import os
import sys
import json
import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402
import importlib
P = importlib.import_module("13-plant")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
FIG = os.path.abspath(os.path.join(HERE, "..", "fig"))
R = 2


def focus(a):
    return uniform_filter(L.sobel_mag(a), 2 * R + 1, mode="reflect")


def b2_single_depth(rate=0.5, n=120, kF=40, H=64, W=192, noise=True, seed=7):
    """ONE depth. Composite first, THEN blur -- the physically correct render."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    edge = int(W * 0.42)
    img0 = np.where(xx < edge, 900.0, 2600.0)
    img0 = img0 + 40.0 * gaussian_filter(rng.normal(0, 1, (H, W)), 1.1)
    F = np.zeros((n, H, W), np.float32)
    for k in range(n):
        s = abs(k - kF) * rate
        a = gaussian_filter(img0, s, mode="nearest") if s > 0 else img0.copy()
        if noise:
            a = a + rng.normal(0, 1, a.shape) * L.sigma_dn(a.astype(np.float32), 100.0)
        F[k] = focus(a.astype(np.float32))
    return F, edge


def peak_offsets(F, edge, kF, offsets):
    """For each offset x into the background, the frame of the local max on k > kF."""
    n, H, W = F.shape
    out = []
    for x in offsets:
        col = F[:, :, edge + x].mean(axis=1)
        right = col[kF + 1:]
        kk = int(np.argmax(right)) + kF + 1
        left = col[:kF]
        kl = int(np.argmax(left))
        out.append((x, kk - kF, kF - kl, float(col[kk]), float(col[kF])))
    return out


if __name__ == "__main__":
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    res = {}

    print("B2  single depth, composite-then-blur (physically correct), rate=0.50")
    F, edge = b2_single_depth(rate=0.5)
    offs = [2, 4, 6, 8, 12, 16, 24, 32]
    rows = peak_offsets(F, edge, 40, offs)
    print("     x(px)  side-lobe offset (frames)   predicted x/rate   lobe/focus height")
    for x, dr, dl, hv, h0 in rows:
        print("     %5d   right %4d  left %4d          %8.1f          %6.2f"
              % (x, dr, dl, x / 0.5, hv / max(h0, 1e-9)))
    res["b2"] = rows

    print("\nB3  the same at rate=0.25 -- the offset must double if the law is sigma=x")
    F2, edge2 = b2_single_depth(rate=0.25)
    rows2 = peak_offsets(F2, edge2, 40, offs)
    for x, dr, dl, hv, h0 in rows2:
        print("     %5d   right %4d  left %4d          %8.1f          %6.2f"
              % (x, dr, dl, x / 0.25, hv / max(h0, 1e-9)))
    res["b3"] = rows2
    a = np.array([r[1] for r in rows], float)
    b = np.array([r[1] for r in rows2], float)
    good = (a > 0) & (b > 0)
    print("     measured ratio of offsets (rate .25 / rate .50) = %.3f   (2.00 if the law holds)"
          % float(np.median(b[good] / a[good])))
    res["b3_ratio"] = float(np.median(b[good] / a[good]))

    print("\nP2  plant WITH a real second depth: does k2 land on the background peak")
    print("    or on the side-lobe?   n=120, kF=40, rate=0.50")
    rng = np.random.default_rng(31337)
    n, kF, W = 120, 40, 192
    ed = int(W * 0.42)
    p2 = []
    for D in (20, 40, 60):
        Fp, Sp, alpha = P.p1_stack(rng, n, kF, kF + D, 0.5)
        z, k1, k2, prom, den = P.run_detector(Fp, Sp)
        for lo, hi in ((1, 8), (8, 16), (16, 24), (24, 40)):
            sl = slice(ed + lo, ed + hi)
            xm = (lo + hi) / 2.0
            kk2 = k2[:, sl].ravel().astype(float)
            near_bg = float(np.mean(np.abs(kk2 - (kF + D)) <= 6))
            near_lobe = float(np.mean(np.abs(np.abs(kk2 - kF) - xm / 0.5) <= 6))
            p2.append(dict(D=D, x=xm, near_bg=near_bg, near_lobe=near_lobe,
                           k2_med=float(np.median(kk2)),
                           k1_med=float(np.median(k1[:, sl])),
                           lobe_pred=kF + xm / 0.5, bg_true=kF + D))
            print("      D=%3d  x~%4.1f px : k2 within 6 frames of the TRUE bg peak "
                  "(k=%3d) %5.1f%% | of the side-lobe (k=%5.1f) %5.1f%%   median k2=%5.1f"
                  % (D, xm, kF + D, 100 * near_bg, kF + xm / 0.5,
                     100 * near_lobe, np.median(kk2)))
    res["p2"] = p2

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for x in (4, 8, 16, 32):
        axes[0].plot(F[:, :, edge + x].mean(axis=1), label="x=%d px" % x)
    axes[0].set_title("B2 single depth, composite-then-blur, rate=0.50\n"
                      "focus response vs frame at fixed offsets into the background")
    axes[0].set_xlabel("frame"); axes[0].legend(fontsize=8)
    xs = np.array([r[0] for r in rows], float)
    axes[1].plot(xs, [r[1] for r in rows], "o-", label="measured, rate=0.50")
    axes[1].plot(xs, xs / 0.5, "k--", label="predicted x/rate, rate=0.50")
    axes[1].plot(xs, [r[1] for r in rows2], "s-", label="measured, rate=0.25")
    axes[1].plot(xs, xs / 0.25, "k:", label="predicted x/rate, rate=0.25")
    axes[1].set_xlabel("distance from the edge (px)")
    axes[1].set_ylabel("side-lobe offset (frames)")
    axes[1].set_title("B3 the single-depth side-lobe law")
    axes[1].legend(fontsize=8)
    plt.tight_layout(); plt.savefig(os.path.join(FIG, "15-sidelobe.png"), dpi=110)

    with open(os.path.join(DATA, "15-sidelobe.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print("\nwrote data/15-sidelobe.json")

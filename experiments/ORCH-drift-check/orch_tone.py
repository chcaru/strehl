"""Is the master actually sRGB-encoded, or linear data wearing an sRGB label?

Section 99 measured masters running 2.5x to 25x brighter than a linear rawpy
decode and concluded only that raw DN is not comparable across the pipeline.
That left the interesting question unasked. A spread of 2.5x at the top and 25x
at the bottom is the SIGNATURE OF A GAMMA CURVE -- sRGB lifts shadows far more
than highlights -- but it is equally the signature of a linear gain plus a black
offset. Those two produce very different pictures:

  correctly encoded   the print looks the way the photographer metered it
  linear, mislabelled  every viewer applies sRGB a second time on top, and the
                       image looks dark, flat and muddy -- which is exactly the
                       word the owner used

The test that separates them does not care about the scale factor at all. Take
matched pixels from the master and from a linear decode of the same scene, and
ask what FUNCTION maps one to the other. A power law fitted in log-log space
returns its exponent:

  exponent ~ 1.0    linear passthrough -> the label is a lie
  exponent ~ 0.45   sRGB / gamma 2.2   -> correctly encoded

This does not need pixel correspondence, which is fortunate because the master
is warped and cropped relative to any single source frame. Quantiles are
alignment-free: the p-th percentile of a scene maps to the p-th percentile of a
monotone tone curve applied to that scene, whatever the geometry did.

That invariance is the whole method, and it has one real hazard: it assumes the
master and the source frame see the SAME SCENE CONTENT. A merge selects sharp
pixels, so its histogram is not identical to any one frame's. The check below
therefore uses many source frames and reports the spread across them, so a
conclusion that rests on one frame's idiosyncratic histogram is visible as
disagreement rather than hidden inside an average.
"""
import os
import sys
import glob

import numpy as np
import tifffile

OUT_ROOT = r"C:\dev\strehl-out"
SRC_ROOT = r"D:\personal\macro"

# Quantiles used for the fit. Avoid the extremes: p<2 is dominated by black
# level and p>98 by clipping, and both bend a power law that is real in between.
QS = np.array([2, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 98], dtype=np.float64)


def luma(rgb):
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1]
            + 0.114 * rgb[..., 2]).astype(np.float64)


def srgb_encode(x):
    """x in [0,1] -> sRGB. The real piecewise curve, not the 1/2.2 shorthand."""
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def fit_exponent(src_q, mst_q):
    """Least-squares exponent of mst = k * src^g, fitted in log-log.

    Returns (g, k, r2). r2 is reported because an exponent from a bad fit is a
    number with no content, and reporting it alone would hide that.
    """
    ok = (src_q > 0) & (mst_q > 0)
    if ok.sum() < 4:
        return None
    ls, lm = np.log(src_q[ok]), np.log(mst_q[ok])
    g, c = np.polyfit(ls, lm, 1)
    pred = g * ls + c
    ss_res = float(np.sum((lm - pred) ** 2))
    ss_tot = float(np.sum((lm - np.mean(lm)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(g), float(np.exp(c)), r2


def main():
    subject = sys.argv[1] if len(sys.argv) > 1 else "tweezers-cpl"
    nsrc = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    import rawpy

    mpath = os.path.join(OUT_ROOT, "SHIP-V2", subject + ".tiff")
    if not os.path.exists(mpath):
        cand = glob.glob(os.path.join(OUT_ROOT, "SHIP-V2", "*" + subject + "*.tiff"))
        if not cand:
            raise SystemExit("no master for %s" % subject)
        mpath = cand[0]
    m = tifffile.imread(mpath)          # tifffile, never PIL
    my = luma(m[..., :3].astype(np.float64))
    mq = np.percentile(my, QS)
    mmax = 65535.0
    print("MASTER  %s" % os.path.basename(mpath))
    print("  shape %r  dtype %s  min %.0f  max %.0f  mean %.0f"
          % (m.shape, m.dtype, my.min(), my.max(), my.mean()))
    print("  quantiles (DN): " + " ".join("%.0f" % v for v in mq))
    print("  as fraction of 65535: " + " ".join("%.4f" % (v / mmax) for v in mq))

    arw = sorted(glob.glob(os.path.join(SRC_ROOT, subject, "*.ARW")))
    if not arw:
        raise SystemExit("no ARW for %s" % subject)
    idx = np.linspace(0, len(arw) - 1, min(nsrc, len(arw))).astype(int)
    # ARM 2. If the master is sRGB-encoded, decoding the SOURCE with the same
    # curve should return exponent ~1.0, while the linear arm returns something
    # else. Running one arm alone cannot distinguish a transfer function from a
    # histogram difference, which is exactly the trap this instrument fell into:
    # it reported 0.90 against a linear source and I read that as "linear".
    srgb_src = "--srgb" in sys.argv
    gam = (2.222, 4.5) if srgb_src else (1, 1)
    print("\nSOURCE  %d of %d frames, rawpy gamma=%r (%s), no_auto_bright"
          % (len(idx), len(arw), gam, "sRGB" if srgb_src else "linear"))

    print("\n%-26s %8s %8s %8s   %s"
          % ("frame", "exponent", "k", "r2", "verdict"))
    gs = []
    for i in idx:
        with rawpy.imread(arw[i]) as r:
            s = r.postprocess(gamma=gam, no_auto_bright=True,
                              use_camera_wb=True, output_bps=16)
        sq = np.percentile(luma(s.astype(np.float64)), QS)
        fit = fit_exponent(sq / mmax, mq / mmax)
        if fit is None:
            print("%-26s  FIT-FAILED" % os.path.basename(arw[i]))
            continue
        g, k, r2 = fit
        if r2 < 0.90:
            v = "POOR FIT - exponent means little"
        elif g > 0.80:
            v = "LINEAR-ISH -> label may be wrong"
        elif g < 0.62:
            v = "TONE CURVE APPLIED"
        else:
            v = "intermediate"
        print("%-26s %8.4f %8.3f %8.4f   %s"
              % (os.path.basename(arw[i]), g, k, r2, v))
        gs.append(g)

    if not gs:
        raise SystemExit("no usable fits")
    gs = np.array(gs)
    print("\nexponent across %d frames: median %.4f  min %.4f  max %.4f  spread %.4f"
          % (len(gs), np.median(gs), gs.min(), gs.max(), np.ptp(gs)))

    print("\nREFERENCE EXPONENTS, computed here rather than quoted:")
    x = np.linspace(0.002, 0.98, 400)
    for name, fn in (("identity (linear)", lambda v: v),
                     ("sRGB", srgb_encode),
                     ("gamma 2.2", lambda v: np.power(v, 1 / 2.2)),
                     ("gamma 1.8", lambda v: np.power(v, 1 / 1.8))):
        xq = np.percentile(x, QS)
        yq = np.percentile(fn(x), QS)
        g, _, r2 = fit_exponent(xq, yq)
        print("  %-20s exponent %.4f  (r2 %.4f)" % (name, g, r2))

    print("\nWHAT THIS CANNOT SEE:")
    print("  - a merge selects sharp pixels, so its histogram is not any one")
    print("    frame's; the spread above is the honest size of that error")
    print("  - a per-channel curve would need three fits, not one on luma")
    print("  - it says nothing about WHICH primaries, only about the transfer")
    print("  - a poor r2 means the mapping is not a power law at all, which is")
    print("    itself informative and is why r2 is printed beside every exponent")


if __name__ == "__main__":
    main()

"""Last candidate for the residual: S2 is a band ratio, so it is scale-sensitive.

Script 09 refuted correlated noise as the driver of the residual (S2 reads
0.9867 for correlated noise against 1.0025 for white -- a 1.6% effect, against a
gap of 0.53 vs the 0.82 blur floor), while confirming the noise really is
correlated (lag-1 -0.456 vs -0.664 for white). So the residual is elsewhere.

The remaining candidate is a property of my own harness, not of the images.
register() in scripts 03/06/08 searches TRANSLATION only. But this project's
whole reason for existing is that focus breathing changes magnification frame to
frame -- the aligner fits a per-frame SIMILARITY, and the brief quotes 232.7 px
of corner-to-corner drift on a deep bracket. So master and source are at
slightly different magnifications, and a translation-only registration cannot
remove that.

S2 is a ratio of a fine band to a coarse band. Rescaling an image moves content
between those bands directly. If a few percent of scale mismatch moves S2 by an
amount comparable to the residual, then the residual is an artefact of my
measurement and NOT a statement about the stacker, and I must not report "the
merge loses detail".

Pure synthetic on real masters: compare a master against a rescaled copy of
ITSELF, where the true sharpness answer is "identical content".
"""
import glob
import os
import sys

import numpy as np
import tifffile

OUT_ROOT, ARM = r"C:\dev\strehl-out", "SHIP-V4"
CROP, PATCH, PATCH_FLOOR = 560, 70, 50.0
IMM = np.array([[1., -2., 1.], [-2., 4., -2.], [1., -2., 1.]])


def luma(rgb):
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]).astype(np.float64)


def fine_abs(y):
    return float(np.mean(np.abs(np.diff(y, axis=1)[:-1, :]) + np.abs(np.diff(y, axis=0)[:, :-1])))


def conv3(a, k):
    o = np.zeros((a.shape[0] - 2, a.shape[1] - 2))
    for i in range(3):
        for j in range(3):
            o += k[i, j] * a[i:i + a.shape[0] - 2, j:j + a.shape[1] - 2]
    return o


def S0(y):
    return fine_abs(y)


def S2(y):
    s = float(np.sqrt(np.pi / 2.0) * np.mean(np.abs(conv3(y, IMM))) / 6.0)
    dx, dy = np.diff(y, axis=1)[:-1, :], np.diff(y, axis=0)[:, :-1]
    f = float(np.mean(dx * dx + dy * dy))
    k = 0.25 * (y[::2, ::2] + y[1::2, ::2] + y[::2, 1::2] + y[1::2, 1::2])
    cx, cy = np.diff(k, axis=1)[:-1, :], np.diff(k, axis=0)[:, :-1]
    c = float(np.mean(cx * cx + cy * cy))
    fs, cs = f - 4.0 * s * s, c - s * s
    return float(np.sqrt(fs / cs)) if fs > 0 and cs > 0 else float("nan")


def rescale(y, f):
    """Bilinear resample about the centre by factor f, same output shape."""
    h, w = y.shape
    yy = (np.arange(h) - h / 2.0) / f + h / 2.0
    xx = (np.arange(w) - w / 2.0) / f + w / 2.0
    yy = np.clip(yy, 0, h - 1.001); xx = np.clip(xx, 0, w - 1.001)
    y0 = yy.astype(int); x0 = xx.astype(int)
    fy = (yy - y0)[:, None]; fx = (xx - x0)[None, :]
    a = y[np.ix_(y0, x0)]; b = y[np.ix_(y0, x0 + 1)]
    c = y[np.ix_(y0 + 1, x0)]; d = y[np.ix_(y0 + 1, x0 + 1)]
    return (a * (1 - fy) * (1 - fx) + b * (1 - fy) * fx
            + c * fy * (1 - fx) + d * fy * fx)


def med_ratio(stat, ref, src):
    n = ref.shape[0] // PATCH
    v = []
    for py in range(n):
        for px in range(n):
            sl = (slice(py * PATCH, (py + 1) * PATCH), slice(px * PATCH, (px + 1) * PATCH))
            if fine_abs(ref[sl]) < PATCH_FLOOR and fine_abs(src[sl]) < PATCH_FLOOR:
                continue
            a, b = stat(ref[sl]), stat(src[sl])
            if np.isfinite(a) and np.isfinite(b) and b > 0:
                v.append(a / b)
    return float(np.median(v)) if v else float("nan")


def main():
    subs = sys.argv[1:] or ["wrapped-text-1", "bee-3-cpl", "coffee-bean", "lavendar-cpl"]
    facs = [1.000, 1.005, 1.01, 1.02, 1.03, 1.05]
    print("SCALE SENSITIVITY. source = master rescaled by f. True answer: same content.")
    print("script07 blur(k=4) floor 0.82..0.88 ; script06 real reading 0.50..0.63\n")
    print("%-22s %8s" % ("subject", "stat") + "".join("%9.3f" % f for f in facs))
    print("-" * (32 + 9 * len(facs)))
    rows0, rows2 = [], []
    for sub in subs:
        cand = glob.glob(os.path.join(OUT_ROOT, "acceptance", ARM, sub + "*.tiff"))
        if not cand:
            continue
        img = luma(tifffile.imread(cand[0])[..., :3].astype(np.float64))
        h, w = img.shape
        big = img[h // 2 - CROP:h // 2 + CROP, w // 2 - CROP:w // 2 + CROP]
        m = big[CROP // 2:CROP // 2 + CROP, CROP // 2:CROP // 2 + CROP]
        v0, v2 = [], []
        for f in facs:
            s = rescale(big, f)[CROP // 2:CROP // 2 + CROP, CROP // 2:CROP // 2 + CROP]
            v0.append(med_ratio(S0, m, s)); v2.append(med_ratio(S2, m, s))
        rows0.append(v0); rows2.append(v2)
        print("%-22s %8s" % (sub[:22], "S0") + "".join("%9.4f" % v for v in v0))
        print("%-22s %8s" % ("", "S2") + "".join("%9.4f" % v for v in v2))
    if rows2:
        print("-" * (32 + 9 * len(facs)))
        print("%-22s %8s" % ("MEDIAN", "S0") + "".join("%9.4f" % v for v in np.median(rows0, 0)))
        print("%-22s %8s" % ("", "S2") + "".join("%9.4f" % v for v in np.median(rows2, 0)))
        m2 = np.median(rows2, 0)
        print("\nS2 at f=1.000 is %.4f (must be 1.0000 by construction)" % m2[0])
        print("S2 at f=1.050 is %.4f -- a 5%% scale error alone moves it %.4f" % (m2[-1], 1.0 - m2[-1]))
        print("residual to explain: 1.000 - 0.53 = 0.47")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

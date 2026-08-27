"""Is the residual a tone-curve mismatch rather than a sharpness difference?

Script 07 established the scale of S2 on real content: a box blur of k=4 applied
to the master only drags the ratio down to 0.8197 (wrapped-text-1), 0.8815
(bee-3-cpl), 0.8639 (coffee-bean), 0.8805 (lavendar-cpl). Script 06 reported
0.588, 0.501, 0.630, 0.502 for those same four subjects against their real
sources. The real readings sit BELOW what a four-pixel box blur of the master
can produce. Whatever separates master from source, it is not in the range of
effects that "one of them is blurrier" spans.

The suspect is the rendering asymmetry script 03 measured. S2 is invariant to
y -> a*y + b by construction, so it already removes the affine part (median
level 1.854x, contrast 2.348x). It is NOT invariant to a change of tone CURVE.
The two arms are:

    master  strehl --srgb --auto-exposure     sRGB curve, exposure fitted
    source  rawpy gamma=(2.222, 4.5)          Rec.709 curve, no_auto_bright

Different curve, different operating point on it. A tone curve redistributes
gradient magnitude across the tonal range non-uniformly, so it changes the
fine/coarse energy balance that S2 reads, and no statistic computed
INDEPENDENTLY on two images can undo it.

The control: histogram-match the source to the master before comparing. That is
a monotone per-image remap, so it cannot reorder or invent spatial structure; it
can only put the two images on a common tonal footing. If the readings move
sharply toward the script-07 blur range, the tone curve was the confound.

CAVEAT, stated before the result: a monotone remap also rescales real local
contrast, and local contrast is partly what sharpness IS. So this arm removes
some genuine signal along with the confound. It bounds the confound; it does not
cleanly partition it. The honest reading of a large move is "most of the gap was
photometric", not "the gap was exactly photometric".
"""
import glob
import os
import sys

import numpy as np
import rawpy
import tifffile

OUT_ROOT, SRC_ROOT, ARM = r"C:\dev\strehl-out", r"D:\personal\macro", "SHIP-V4"
CROP, PATCH, PATCH_FLOOR, SEARCH, CORR_MIN = 560, 70, 50.0, 48, 0.50
SITE_SHARE, SITE_CLIP_MAX = 0.25, 0.05
IMM = np.array([[1., -2., 1.], [-2., 4., -2.], [1., -2., 1.]])

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from importlib import import_module
_m = import_module("06-real") if False else None


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


def hist_match(src, ref):
    """Monotone remap of src so its histogram matches ref's. Structure preserved."""
    sf, rf = src.ravel(), ref.ravel()
    sv, sidx, scnt = np.unique(sf, return_inverse=True, return_counts=True)
    rv, rcnt = np.unique(rf, return_counts=True)
    sq = np.cumsum(scnt).astype(np.float64) / sf.size
    rq = np.cumsum(rcnt).astype(np.float64) / rf.size
    return np.interp(sq, rq, rv)[sidx].reshape(src.shape)


def best_site(my, n=3):
    h, w = my.shape
    best = []
    for y in range(SEARCH, h - CROP - SEARCH, CROP):
        for x in range(SEARCH, w - CROP - SEARCH, CROP):
            best.append((fine_abs(my[y:y + CROP:4, x:x + CROP:4]), y, x))
    best.sort(reverse=True)
    out = []
    for d, y, x in best:
        if all(abs(y - yy) > CROP or abs(x - xx) > CROP for _, yy, xx in out):
            out.append((d, y, x))
        if len(out) >= n:
            break
    return out


def register(ref, mov):
    rf = ref - ref.mean()
    den0 = (rf * rf).sum()
    best, bc = (0, 0), -2.0
    for coarse in (True, False):
        if coarse:
            ys = xs = range(-SEARCH, SEARCH + 1, 4)
        else:
            ys = range(best[0] - 3, best[0] + 4)
            xs = range(best[1] - 3, best[1] + 4)
        for dy in ys:
            for dx in xs:
                if not (-SEARCH <= dy <= SEARCH and -SEARCH <= dx <= SEARCH):
                    continue
                m = mov[SEARCH + dy:SEARCH + dy + CROP, SEARCH + dx:SEARCH + dx + CROP]
                if m.shape != ref.shape:
                    continue
                mm = m - m.mean()
                den = np.sqrt(den0 * (mm * mm).sum())
                c = float((rf * mm).sum() / den) if den > 0 else -2.0
                if c > bc:
                    bc, best = c, (dy, dx)
    return best, bc


def med_ratio(stat, ref, regs):
    n = ref.shape[0] // PATCH
    vals = []
    for py in range(n):
        for px in range(n):
            sl = (slice(py * PATCH, (py + 1) * PATCH), slice(px * PATCH, (px + 1) * PATCH))
            if fine_abs(ref[sl]) < PATCH_FLOOR and max(fine_abs(c[sl]) for c in regs) < PATCH_FLOOR:
                continue
            a = stat(ref[sl])
            bs = [stat(c[sl]) for c in regs]
            bs = [b for b in bs if np.isfinite(b) and b > 0]
            if np.isfinite(a) and bs:
                vals.append(a / max(bs))
    return float(np.median(vals)) if vals else float("nan"), len(vals)


def main():
    subs = sys.argv[1:] or ["wrapped-text-1", "bee-3-cpl", "coffee-bean", "lavendar-cpl"]
    print("TONE-CURVE CONTROL. 'matched' = source histogram-matched to master first.")
    print("script07 blur(k=4) floor for reference: 0.8197 0.8815 0.8639 0.8805\n")
    print("%-22s %8s %8s %8s %8s %6s" % ("subject", "S0 raw", "S0 match", "S2 raw", "S2 match", "n"))
    print("-" * 74)
    rows = []
    for sub in subs:
        cand = glob.glob(os.path.join(OUT_ROOT, "acceptance", ARM, sub + "*.tiff"))
        arw = sorted(glob.glob(os.path.join(SRC_ROOT, sub, "*.ARW")))
        if not cand or not arw:
            print("%-22s (missing)" % sub)
            continue
        my = luma(tifffile.imread(cand[0])[..., :3].astype(np.float64))
        scored = [(fine_abs(my[y:y + CROP, x:x + CROP]), y, x) for _, y, x in best_site(my)]
        top = max(d for d, _, _ in scored)
        sites = [(y, x) for d, y, x in scored if d / top >= SITE_SHARE]
        idx = np.linspace(0, len(arw) - 1, min(8, len(arw))).astype(int)
        srcs = []
        for i in idx:
            with rawpy.imread(arw[i]) as r:
                srcs.append(luma(r.postprocess(gamma=(2.222, 4.5), no_auto_bright=True,
                                               use_camera_wb=True, output_bps=16).astype(np.float64)))
        a0 = a0m = a2 = a2m = None
        acc = {"s0": [], "s0m": [], "s2": [], "s2m": [], "n": 0}
        for (y, x) in sites:
            ref = my[y:y + CROP, x:x + CROP]
            regs = []
            for sy in srcs:
                pad = sy[y - SEARCH:y + CROP + SEARCH, x - SEARCH:x + CROP + SEARCH]
                if pad.shape[0] < CROP + 2 * SEARCH or pad.shape[1] < CROP + 2 * SEARCH:
                    continue
                (dy, dx), c = register(ref, pad)
                if c < CORR_MIN:
                    continue
                regs.append(sy[y + dy:y + dy + CROP, x + dx:x + dx + CROP])
            if not regs:
                continue
            mregs = [hist_match(c, ref) for c in regs]
            v, n = med_ratio(S0, ref, regs); acc["s0"].append(v); acc["n"] += n
            v, _ = med_ratio(S0, ref, mregs); acc["s0m"].append(v)
            v, _ = med_ratio(S2, ref, regs); acc["s2"].append(v)
            v, _ = med_ratio(S2, ref, mregs); acc["s2m"].append(v)
        if not acc["s0"]:
            print("%-22s (no usable site)" % sub)
            continue
        r = (np.median(acc["s0"]), np.median(acc["s0m"]),
             np.median(acc["s2"]), np.median(acc["s2m"]))
        rows.append((sub,) + r)
        print("%-22s %8.3f %8.3f %8.4f %8.4f %6d" % ((sub[:22],) + r + (acc["n"],)))
    if rows:
        a = np.array([r[1:] for r in rows])
        print("\n" + "=" * 74)
        print("median   S0 raw %.3f -> matched %.3f   (x%.2f)"
              % (np.median(a[:, 0]), np.median(a[:, 1]), np.median(a[:, 1] / a[:, 0])))
        print("median   S2 raw %.4f -> matched %.4f   (x%.2f)"
              % (np.median(a[:, 2]), np.median(a[:, 3]), np.median(a[:, 3] / a[:, 2])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

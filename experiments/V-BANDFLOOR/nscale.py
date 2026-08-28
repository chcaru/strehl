r"""N-SCALING INSTRUMENT: does deepening a stack at matched focus range raise
flat-field grain, and does the knob fix it?

PRIMARY AXIS (as directed): flat-field grain ratio deep/shallow, per arm.
Currently reported as x1.1697 by another lane; the criterion is <= 1.0.

WHAT I ADD, AND WHY THE RATIO ALONE IS NOT ENOUGH. The ratio is scale-free: it
divides out any change that affects both N equally. A knob that halved grain at
BOTH N would leave the ratio untouched and score "no improvement", and a knob
that RAISED absolute grain at both N while raising it less at the deep end would
score a "win". What a viewer sees is the absolute grain of the stack they
actually rendered. So this reports BOTH:
  (a) N-SCALING   grain(deep)/grain(shallow) within an arm  -- the directed axis
  (b) ABSOLUTE    grain(B)/grain(A) at each N separately    -- what is delivered
A verdict is only quoted when (a) and (b) are stated together.

GUARD (as directed): the detail column is printed beside every flat column, and
the commissioning includes an arm that applies a GLOBAL BLUR, which must move
the flat column the "good" way AND be caught by the detail column. If that arm
did not trip the detail column the guard would be decorative.

TILE CLASSIFICATION is neutral to BOTH nuisance factors: texture is scored on
the mean of ALL FOUR renders, so neither the arm nor N can move a tile between
classes. Class-swap counts against per-render scoring are printed.

ALL ARITHMETIC IN float64. Noted separately: an f32 participation ratio flushes
squared clamp-floor weights to zero and returns NaN on exactly the most-averaged
coefficients.
"""
import argparse
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bandmetrics as bm                                           # noqa: E402

OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"


def load64(p):
    g, cm, clipf = bm.load(p)
    return np.asarray(g, dtype=np.float64), cm, clipf


def columns(g, y0, x0, ty, tx):
    """Fine-band contrast per tile (dimensionless: band RMS / tile mean)."""
    prof, lvl = bm.band_profile(g, y0, x0, ty, tx)
    return bm.group(prof, lvl, bm.FINE).astype(np.float64)


def classify(gs, y0, x0, ty, tx):
    """Texture class from the mean of ALL renders -- neutral to arm and to N."""
    m = np.mean(gs, axis=0)
    prof, lvl = bm.band_profile(m, y0, x0, ty, tx)
    t = bm.group(prof, lvl, (1,))
    return t, float(np.median(t))


def ratio(a, b, seed=101, nboot=bm.NBOOT):
    """median(b/a) as a MULTIPLIER (not a percent), with a paired bootstrap."""
    r = np.asarray(b, np.float64) / np.maximum(np.asarray(a, np.float64), 1e-12)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(r), size=(nboot, len(r)))
    m = np.median(r[idx], axis=1)
    return (float(np.median(r)), float(np.percentile(m, 2.5)),
            float(np.percentile(m, 97.5)))


def analyse(imgs, clip, tag, quiet=False):
    """imgs: dict with keys (arm, 'deep'|'shallow') -> float64 luminance."""
    keys = sorted(imgs)
    g0 = imgs[keys[0]]
    y0, x0, ty, tx = bm.tile_grid(g0.shape)
    cl = bm.tile_rms(clip.astype(np.float32), ty, tx, y0, x0)
    ok = (cl == 0.0)
    t, thr = classify([imgs[k] for k in keys], y0, x0, ty, tx)
    flat = ok & (t <= thr)
    tex = ok & (t > thr)
    swaps = 0
    for k in keys:
        pr, lv = bm.band_profile(imgs[k], y0, x0, ty, tx)
        tk = bm.group(pr, lv, (1,))
        swaps = max(swaps, int(((tk <= np.median(tk[ok])) != (t <= thr))[ok].sum()))
    col = {k: columns(imgs[k], y0, x0, ty, tx) for k in keys}
    res = {"nflat": int(flat.sum()), "ntex": int(tex.sum()), "swaps": swaps}
    for arm in sorted({k[0] for k in keys}):
        res[("nscale", arm, "flat")] = ratio(col[(arm, "shallow")][flat],
                                             col[(arm, "deep")][flat])
        res[("nscale", arm, "tex")] = ratio(col[(arm, "shallow")][tex],
                                            col[(arm, "deep")][tex])
    for n in ("deep", "shallow"):
        if ("A-unset", n) in col and ("B-coarse8", n) in col:
            res[("arm", n, "flat")] = ratio(col[("A-unset", n)][flat],
                                            col[("B-coarse8", n)][flat])
            res[("arm", n, "tex")] = ratio(col[("A-unset", n)][tex],
                                           col[("B-coarse8", n)][tex])
    if not quiet:
        report(res, tag)
    return res


def fmt(r):
    return "x%.4f [%.4f,%.4f]" % r


def report(res, tag):
    print("  %s   tiles %d flat / %d textured   max class swaps %d"
          % (tag, res["nflat"], res["ntex"], res["swaps"]))
    print("    --- N-SCALING (deep/shallow, matched focus range).  <=1.0000 is the criterion")
    for arm in ("A-unset", "B-coarse8"):
        k = ("nscale", arm, "flat")
        if k in res:
            print("      %-10s FLAT grain %-26s   DETAIL sharp %-26s"
                  % (arm, fmt(res[k]), fmt(res[("nscale", arm, "tex")])))
    print("    --- ABSOLUTE (B/A at fixed N).  <1.0000 = B has less grain / less sharpness")
    for n in ("deep", "shallow"):
        k = ("arm", n, "flat")
        if k in res:
            print("      %-10s FLAT grain %-26s   DETAIL sharp %-26s"
                  % (n, fmt(res[k]), fmt(res[("arm", n, "tex")])))


# ----------------------------------------------------------------- commissioning
def fine_scale(g, frac, mask=None):
    """Scale the FINE bands by `frac`, optionally only where mask is True."""
    lo = bm.smooth(g, bm.RADII[max(bm.FINE) + 1])
    d = g - lo
    if mask is None:
        return lo + frac * d
    w = np.where(mask, frac, 1.0)
    return lo + w * d


def tile_mask(shape, flat_sel, y0, x0, ty, tx):
    m = np.zeros(shape, bool)
    sel = flat_sel.reshape(ty, tx)
    for iy in range(ty):
        for ix in range(tx):
            if sel[iy, ix]:
                m[y0 + iy * bm.TILE:y0 + (iy + 1) * bm.TILE,
                  x0 + ix * bm.TILE:x0 + (ix + 1) * bm.TILE] = True
    return m


def commission(deep_path, shallow_path):
    print("COMMISSIONING the N-scaling instrument on real pixels")
    print("  deep    %s" % deep_path)
    print("  shallow %s" % shallow_path)
    gd, cmd_, cfd = load64(deep_path)
    gs, cms, cfs = load64(shallow_path)
    cm = cmd_ | cms
    print("  clip: deep %.4f%%  shallow %.4f%%" % (100 * cfd, 100 * cfs))
    y0, x0, ty, tx = bm.tile_grid(gd.shape)
    t, thr = classify([gd, gs], y0, x0, ty, tx)
    fmask = tile_mask(gd.shape, (t <= thr).ravel(), y0, x0, ty, tx)

    rng = np.random.default_rng(7)
    lo = bm.smooth(gd, bm.RADII[max(bm.FINE) + 1])
    fine_rms = float(np.sqrt(np.mean((gd - lo) ** 2)))

    def run(name, deep, expect_flat, expect_tex):
        imgs = {("A-unset", "deep"): deep, ("A-unset", "shallow"): gs}
        r = analyse(imgs, cm, name, quiet=True)
        f = r[("nscale", "A-unset", "flat")]
        x = r[("nscale", "A-unset", "tex")]
        okf = ({"up": f[1] > 1.0, "down": f[2] < 1.0,
                "one": abs(f[0] - 1.0) < 1e-9}[expect_flat])
        okx = True if expect_tex is None else (
            {"up": x[1] > 1.0, "down": x[2] < 1.0,
             "one": abs(x[0] - 1.0) < 1e-9}[expect_tex])
        print("  %-46s FLAT %-26s DETAIL %-26s  %s"
              % (name, fmt(f), fmt(x), "PASS" if (okf and okx) else "FAIL"))
        return okf and okx

    rows = []
    rows.append(run("NULL     deep := shallow -> FLAT must be 1.0000",
                    gs.copy(), "one", "one"))
    rows.append(run("DEFECT   +noise in deep (0.5x fine RMS) -> FLAT UP",
                    gd + rng.normal(0, 0.5 * fine_rms, gd.shape), "up", None))
    rows.append(run("DEFECT   +noise in deep (0.2x fine RMS) -> FLAT UP",
                    gd + rng.normal(0, 0.2 * fine_rms, gd.shape), "up", None))
    rows.append(run("IMPROVE  targeted denoise of deep FLAT only -> FLAT DOWN",
                    fine_scale(gd, 0.7, fmask), "down", None))
    rows.append(run("GUARD    GLOBAL blur of deep -> FLAT DOWN and DETAIL must fall",
                    fine_scale(gd, 0.7, None), "down", "down"))
    n = sum(rows)
    print("\n  COMMISSIONED %d/%d arms" % (n, len(rows)))
    if rows[-1]:
        print("  GUARD IS LIVE: a global blur that improves the flat column IS")
        print("  caught by the detail column, so guard 2 can actually fire.")
    return 0 if n == len(rows) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", nargs=2, metavar=("DEEP", "SHALLOW"))
    ap.add_argument("--subject")
    ap.add_argument("--deep", type=int)
    ap.add_argument("--shallow", type=int)
    a = ap.parse_args()
    if a.commission:
        return commission(*a.commission)
    imgs, cm, clips = {}, None, {}
    for arm in ("A-unset", "B-coarse8"):
        for lbl, n in (("deep", a.deep), ("shallow", a.shallow)):
            p = os.path.join(OUT, "%s__N%d__%s.tiff" % (a.subject, n, arm))
            g, c, cf = load64(p)
            imgs[(arm, lbl)] = g
            clips["%s N%d" % (arm, n)] = cf
            cm = c if cm is None else (cm | c)
    print("%s  deep N=%d  shallow N=%d" % (a.subject, a.deep, a.shallow))
    print("  clip: " + "  ".join("%s %.4f%%" % (k, 100 * v) for k, v in clips.items()))
    analyse(imgs, cm, a.subject)
    return 0


if __name__ == "__main__":
    sys.exit(main())

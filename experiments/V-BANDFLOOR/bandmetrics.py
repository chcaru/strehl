r"""V-BANDFLOOR band-resolved A/B instrument.

FOUR COLUMNS, EACH WITH A STATED FOOLING DIRECTION.

  BLOTCH  coarse-band contrast on FLAT tiles.   DOWN = better (less mottle).
  LFC     coarse-band contrast on TEXTURED tiles. DOWN = WORSE (lost modelling).
  SHARP   fine-band contrast on TEXTURED tiles. DOWN = softer.
  GRAIN   fine-band contrast on FLAT tiles.     rule-9 flat control for SHARP.

WHY BLOTCH ALONE IS INADMISSIBLE FOR THIS CHANGE. The treatment under test
averages the coarse pyramid bands harder. Averaging lowers coarse-band variance
EVERYWHERE, including where the coarse variance is real scene modelling. A
statistic that reads "coarse contrast in smooth regions" therefore improves
under indiscriminate coarse dilution, which is not a fix. LFC is the companion
that can convict that: a genuine mottle fix moves BLOTCH much more than LFC; a
dilution moves both by the same fraction. The pair is reported jointly and no
BLOTCH number is quoted without its LFC.

BANDS. Difference of TWICE-APPLIED box means (a 2-fold box is a triangle
kernel; its stopband is far better than a single box, which is what leaked
4.79% into another lane's sharpness column -- SYNTHESIS fact 1806). Radii
double, so band k is roughly the 2^(k+1) .. 2^(k+2) px octave, the same ladder
the merge's own pyramid runs on.

TILE CLASSIFICATION IS ARM-NEUTRAL. Texture is scored on the MEAN of the two
arms, at band 1 (4-8 px), a scale the treatment barely touches. The count of
tiles that would change class if scored on A alone or B alone is reported, so
the neutrality is measured rather than asserted.

CLIP. Every tile containing a pixel at 65535 in any channel or 0 in every
channel is dropped, and the whole-image clip fraction is printed beside every
verdict (SYNTHESIS fact 1817: a saturated region has no structure, so every
structural metric reads clean on a blown master).
"""
import argparse
import json
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

TILE = 256
MARGIN = 0.05
NBANDS = 7
RADII = [1, 2, 4, 8, 16, 32, 64, 128]
FINE = (0, 1)        # ~2-8 px
COARSE = (4, 5)      # ~32-128 px, straddles the convicted 20-60 px plateau
NBOOT = 4000


def lum(a):
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def smooth(a, r):
    if r <= 0:
        return a
    n = 2 * r + 1
    return ndimage.uniform_filter(ndimage.uniform_filter(a, n), n)


def tile_rms(band, ty, tx, y0, x0):
    """RMS of `band` inside each tile, without materialising a copy."""
    sub = band[y0:y0 + ty * TILE, x0:x0 + tx * TILE]
    return np.sqrt((sub * sub).reshape(ty, TILE, tx, TILE).mean(axis=(1, 3)))


def tile_grid(shape):
    h, w = shape
    y0 = int(h * MARGIN) // TILE * TILE + TILE
    x0 = int(w * MARGIN) // TILE * TILE + TILE
    ty = (int(h * (1 - MARGIN)) - y0) // TILE
    tx = (int(w * (1 - MARGIN)) - x0) // TILE
    return y0, x0, ty, tx


def band_profile(g, y0, x0, ty, tx):
    """Per-tile RMS for every band, plus per-tile mean level."""
    prev = smooth(g, RADII[0])
    out = []
    for r in RADII[1:]:
        nxt = smooth(g, r)
        out.append(tile_rms(prev - nxt, ty, tx, y0, x0))
        prev = nxt
    sub = g[y0:y0 + ty * TILE, x0:x0 + tx * TILE]
    lvl = sub.reshape(ty, TILE, tx, TILE).mean(axis=(1, 3))
    return np.stack(out, 0), lvl


def group(prof, lvl, bands):
    """Contrast = band RMS / tile mean level. Dimensionless, so a global linear
    gain difference between arms cancels."""
    e = np.sqrt((prof[list(bands)] ** 2).sum(axis=0))
    return e / np.maximum(lvl, 1e-6)


def boot_med_ratio(a, b, seed=101, nboot=NBOOT):
    """Paired bootstrap over TILES of median(b/a) - 1, in percent.

    Paired because the two arms are the same scene on the same grid at the same
    tile indices; an unpaired interval would be wider than the data warrant and
    would hide a small real move.
    """
    r = b / np.maximum(a, 1e-12)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(r), size=(nboot, len(r)))
    m = np.median(r[idx], axis=1)
    return (100 * (float(np.median(r)) - 1.0),
            100 * (float(np.percentile(m, 2.5)) - 1.0),
            100 * (float(np.percentile(m, 97.5)) - 1.0))


def measure_pair(gA, gB, clipmask, tag="", quiet=False):
    y0, x0, ty, tx = tile_grid(gA.shape)
    cl = tile_rms(clipmask.astype(np.float32), ty, tx, y0, x0)
    ok = (cl == 0.0)
    pA, lA = band_profile(gA, y0, x0, ty, tx)
    pB, lB = band_profile(gB, y0, x0, ty, tx)
    pM, lM = band_profile(0.5 * (gA + gB), y0, x0, ty, tx)

    texM = group(pM, lM, FINE)
    texA = group(pA, lA, FINE)
    texB = group(pB, lB, FINE)
    v = texM[ok]
    lo_c, hi_c = np.percentile(v, [33.333, 66.667])
    flat = ok & (texM <= lo_c)
    tex = ok & (texM >= hi_c)

    # measured arm-neutrality of the classification
    def cls(t):
        vv = t[ok]
        a, b = np.percentile(vv, [33.333, 66.667])
        return (ok & (t <= a)), (ok & (t >= b))
    fA, tA = cls(texA)
    fB, tB = cls(texB)
    swap = int((flat != fA).sum() + (tex != tA).sum() +
               (flat != fB).sum() + (tex != tB).sum())

    res = {"tag": tag, "n_tiles": int(ok.sum()), "n_flat": int(flat.sum()),
           "n_tex": int(tex.sum()), "n_dropped_clip": int((~ok).sum()),
           "class_swaps": swap}
    for name, sel, bands in (("BLOTCH", flat, COARSE), ("LFC", tex, COARSE),
                             ("SHARP", tex, FINE), ("GRAIN", flat, FINE)):
        a = group(pA, lA, bands)[sel]
        b = group(pB, lB, bands)[sel]
        m, lo, hi = boot_med_ratio(a, b)
        res[name] = {"pct": m, "lo": lo, "hi": hi,
                     "A": float(np.median(a)), "B": float(np.median(b))}
    # per-band, textured and flat, so dilution is visible band by band
    res["per_band"] = {}
    for k in range(NBANDS):
        a_f = (pA[k] / np.maximum(lA, 1e-6))[flat]
        b_f = (pB[k] / np.maximum(lB, 1e-6))[flat]
        a_t = (pA[k] / np.maximum(lA, 1e-6))[tex]
        b_t = (pB[k] / np.maximum(lB, 1e-6))[tex]
        res["per_band"][k] = {"flat": boot_med_ratio(a_f, b_f, seed=200 + k),
                              "tex": boot_med_ratio(a_t, b_t, seed=300 + k)}
    if not quiet:
        report(res)
    return res


def report(r):
    print("  %-8s %8s  %-28s %s" % ("column", "B vs A", "95% CI", "direction"))
    meaning = {"BLOTCH": "DOWN = less mottle (GOOD)",
               "LFC": "DOWN = lost modelling (BAD)",
               "SHARP": "DOWN = softer (BAD)",
               "GRAIN": "flat-ROI control for SHARP"}
    for k in ("BLOTCH", "LFC", "SHARP", "GRAIN"):
        v = r[k]
        print("  %-8s %+7.2f%%  [%+7.2f%%, %+7.2f%%]        %s"
              % (k, v["pct"], v["lo"], v["hi"], meaning[k]))
    print("  tiles: %d usable (%d flat / %d textured), %d dropped for clip, "
          "%d class swaps" % (r["n_tiles"], r["n_flat"], r["n_tex"],
                              r["n_dropped_clip"], r["class_swaps"]))


def load(p):
    a = tifffile.imread(p)
    if a.ndim == 2:
        a = np.dstack([a] * 3)
    a = a[:, :, :3]
    cm = (a.max(axis=2) >= 65535) | (a.max(axis=2) <= 0)
    return lum(a), cm, float((a.max(axis=2) >= 65535).mean())


# ---------------------------------------------------------------- commissioning
def band_noise(shape, bands, seed=3):
    """White noise projected onto exactly `bands` of the SAME ladder the
    instrument reads. SYNTHESIS fact 1814: a plant sized in one band's units
    arrives at a tenth of its intended strength in another, so the plant is
    built with the analyser's own filters rather than a hand-picked pair of
    radii."""
    rng = np.random.default_rng(seed)
    n = rng.normal(0.0, 1.0, shape).astype(np.float32)
    acc = np.zeros(shape, np.float32)
    prev = smooth(n, RADII[0])
    for i, r in enumerate(RADII[1:]):
        nxt = smooth(n, r)
        if i in bands:
            acc += prev - nxt
        prev = nxt
    return acc


def plant_mottle(g, q, cm, seed=3):
    """Add mottle whose coarse-band contrast on FLAT tiles is `q` times the
    contrast already there. Sized from the image, not typed."""
    y0, x0, ty, tx = tile_grid(g.shape)
    cl = tile_rms(cm.astype(np.float32), ty, tx, y0, x0)
    pr, lv = band_profile(g, y0, x0, ty, tx)
    t = group(pr, lv, FINE)[cl == 0]
    lo_c = np.percentile(t, 33.333)
    flat = (cl == 0) & (group(pr, lv, FINE) <= lo_c)
    c_flat = float(np.median(group(pr, lv, COARSE)[flat]))
    lvl = float(np.median(lv[flat]))
    n = band_noise(g.shape, COARSE, seed)
    n /= max(float(n.std()), 1e-9)
    amp = q * c_flat * lvl
    print("      [plant sized from the image: flat coarse contrast %.5f, "
          "level %.0f DN -> amplitude %.2f DN rms]" % (c_flat, lvl, amp))
    return (g + amp * n).astype(np.float32)


def attenuate(g, bands, frac):
    """Remove `frac` of the energy in `bands`. frac>0 attenuates, frac<0 boosts."""
    out = g.copy()
    prev = smooth(g, RADII[0])
    for i, r in enumerate(RADII[1:]):
        nxt = smooth(g, r)
        if i in bands:
            out -= frac * (prev - nxt)
        prev = nxt
    return out.astype(np.float32)


def commission(path):
    print("COMMISSIONING on real pixels: %s" % path)
    g, cm, clipf = load(path)
    print("  whole-image clip fraction %.4f%%" % (100 * clipf))
    arms = [
        ("DEFECT   mottle 50% of the flat coarse contrast",
         plant_mottle(g, 0.50, cm), {"BLOTCH": +1}),
        ("DEFECT   mottle 15% of the flat coarse contrast",
         plant_mottle(g, 0.15, cm, seed=9), {"BLOTCH": +1}),
        ("IMPROVE  coarse bands 4-5 cut 50%", attenuate(g, COARSE, 0.5),
         {"BLOTCH": -1, "LFC": -1}),
        ("DEFECT   coarse modelling cut 30%", attenuate(g, COARSE, 0.3),
         {"LFC": -1}),
        ("IMPROVE  coarse modelling boosted 30%", attenuate(g, COARSE, -0.3),
         {"LFC": +1}),
        ("DEFECT   blur sigma 0.8", ndimage.gaussian_filter(g, 0.8),
         {"SHARP": -1}),
        ("IMPROVE  unsharp mask amount 0.5 r=1.5",
         (g + 0.5 * (g - ndimage.gaussian_filter(g, 1.5))).astype(np.float32),
         {"SHARP": +1}),
        ("NULL     identical image", g.copy(), {}),
    ]
    rows = []
    for name, arm, expect in arms:
        r = measure_pair(g, arm, cm, tag=name, quiet=True)
        cols = " ".join("%s %+7.2f%% [%+.2f,%+.2f]"
                        % (k, r[k]["pct"], r[k]["lo"], r[k]["hi"])
                        for k in ("BLOTCH", "LFC", "SHARP", "GRAIN"))
        ok = True
        why = []
        for k, sgn in expect.items():
            v = r[k]
            if sgn > 0 and not (v["pct"] > 0 and v["lo"] > 0):
                ok = False
                why.append("%s did not rise with CI clear of 0" % k)
            if sgn < 0 and not (v["pct"] < 0 and v["hi"] < 0):
                ok = False
                why.append("%s did not fall with CI clear of 0" % k)
        if not expect:  # null arm
            for k in ("BLOTCH", "LFC", "SHARP", "GRAIN"):
                if abs(r[k]["pct"]) > 1e-6:
                    ok = False
                    why.append("%s moved on an identical image" % k)
        rows.append((name, ok, why))
        print("  %-46s %s" % (name.replace("%%", "%"),
                              "PASS" if ok else "FAIL"))
        print("      " + cols)
        for w in why:
            print("      >>> " + w)
    bad = [r for r in rows if not r[1]]
    print("\n  COMMISSIONED %d/%d arms" % (len(rows) - len(bad), len(rows)))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", metavar="TIFF")
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--tag", default="")
    ap.add_argument("--json")
    args = ap.parse_args()
    if args.commission:
        return commission(args.commission)
    gA, cmA, clipA = load(args.a)
    gB, cmB, clipB = load(args.b)
    if gA.shape != gB.shape:
        raise SystemExit("shape mismatch")
    print("%s\n  A clip %.4f%%   B clip %.4f%%" % (args.tag, 100 * clipA, 100 * clipB))
    r = measure_pair(gA, gB, cmA | cmB, tag=args.tag)
    r["clipA"], r["clipB"] = clipA, clipB
    if args.json:
        json.dump(r, open(args.json, "w"), indent=1, default=float)
    return 0


if __name__ == "__main__":
    sys.exit(main())

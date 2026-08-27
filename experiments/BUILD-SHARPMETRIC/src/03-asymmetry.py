"""The rendering asymmetry, measured on real data.

Script 02 proved the ratio is EXACTLY linear in any gain applied to the master:
mean|grad(a*y)| == a*mean|grad(y)|, so x1.20 gain reads 1.2000 and x1.50 reads
1.5000. That is a mathematical identity, not an approximation. It matters here
because the master and the sources in orch_sharp1to1.py are NOT rendered the
same way:

    master   strehl .tiff, rendered --srgb --auto-exposure
    source   rawpy.postprocess(gamma=(2.222, 4.5), no_auto_bright=True, ...)

Two differences, both of which multiply the ratio directly:

  1. EXPOSURE. The master has auto-exposure applied. The source explicitly does
     not (`no_auto_bright=True`). Any brightness difference between the two is
     a gain difference, and by script 02 the ratio is linear in it.
  2. TRANSFER CURVE. sRGB (linear toe, ~2.4 exponent) against Rec.709
     (gamma=2.222, slope 4.5). These are different curves with different local
     slopes, and a tone curve's slope is exactly the factor by which it
     amplifies a small luminance difference -- i.e. a gradient.

This script measures both on real SHIP-V4 masters against their own source
frames, at the same sites the metric uses. It reports the numbers; it does not
correct anything yet.

It measures the confound in the ONLY way that is fair: by comparing the two
renderings of THE SAME PHOTONS at the SAME registered location, and asking how
much of the gradient ratio is explained by level and slope alone.

NOTHING IS CONCLUDED FROM A SINGLE SUBJECT. Every subject with usable sites is
run and the spread is reported, because a rendering asymmetry that is real must
be present in all of them.
"""
import glob
import os
import sys

import numpy as np
import rawpy
import tifffile

OUT_ROOT = r"C:\dev\strehl-out"
SRC_ROOT = r"D:\personal\macro"
ARM = "SHIP-V4"

CROP = 560
PATCH = 70
PATCH_FLOOR = 50.0
SEARCH = 48
CORR_MIN = 0.50
SITE_SHARE = 0.25
SITE_CLIP_MAX = 0.05


def luma(rgb):
    return (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1]
            + 0.114 * rgb[..., 2]).astype(np.float64)


def detail(y):
    f = np.abs(np.diff(y, axis=1)[:-1, :]) + np.abs(np.diff(y, axis=0)[:, :-1])
    k = y[::2, ::2] + y[1::2, ::2] + y[::2, 1::2] + y[1::2, 1::2]
    c = np.abs(np.diff(k, axis=1)[:-1, :]) + np.abs(np.diff(k, axis=0)[:, :-1])
    return float(np.mean(f)), float(np.mean(c) / 4.0)


def best_site(my, n=3):
    h, w = my.shape
    step = CROP
    best = []
    for y in range(SEARCH, h - CROP - SEARCH, step):
        for x in range(SEARCH, w - CROP - SEARCH, step):
            d = detail(my[y:y + CROP:4, x:x + CROP:4])[0]
            best.append((d, y, x))
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
    best, bc = (0, 0), -2.0
    for dy in range(-SEARCH, SEARCH + 1, 4):
        for dx in range(-SEARCH, SEARCH + 1, 4):
            m = mov[SEARCH + dy:SEARCH + dy + CROP, SEARCH + dx:SEARCH + dx + CROP]
            if m.shape != ref.shape:
                continue
            mm = m - m.mean()
            den = np.sqrt((rf * rf).sum() * (mm * mm).sum())
            c = float((rf * mm).sum() / den) if den > 0 else -2.0
            if c > bc:
                bc, best = c, (dy, dx)
    dy0, dx0 = best
    for dy in range(dy0 - 3, dy0 + 4):
        for dx in range(dx0 - 3, dx0 + 4):
            if not (-SEARCH <= dy <= SEARCH and -SEARCH <= dx <= SEARCH):
                continue
            m = mov[SEARCH + dy:SEARCH + dy + CROP, SEARCH + dx:SEARCH + dx + CROP]
            if m.shape != ref.shape:
                continue
            mm = m - m.mean()
            den = np.sqrt((rf * rf).sum() * (mm * mm).sum())
            c = float((rf * mm).sum() / den) if den > 0 else -2.0
            if c > bc:
                bc, best = c, (dy, dx)
    return best, bc


def run_subject(subject, nsrc=8):
    cand = glob.glob(os.path.join(OUT_ROOT, "acceptance", ARM, subject + "*.tiff"))
    if not cand:
        return None
    m = tifffile.imread(cand[0])[..., :3].astype(np.float64)
    my = luma(m)
    sites = best_site(my)
    scored = []
    for _, y, x in sites:
        crop = my[y:y + CROP, x:x + CROP]
        d = detail(crop)[0]
        clipf = float((m[y:y + CROP, x:x + CROP] >= 65000).mean())
        scored.append((d, clipf, y, x))
    top = max(d for d, _, _, _ in scored) if scored else 0.0
    sites = [(y, x) for d, clipf, y, x in scored
             if clipf <= SITE_CLIP_MAX and top and d / top >= SITE_SHARE]
    if not sites:
        return None

    arw = sorted(glob.glob(os.path.join(SRC_ROOT, subject, "*.ARW")))
    if not arw:
        return None
    idx = np.linspace(0, len(arw) - 1, min(nsrc, len(arw))).astype(int)
    srcs = []
    for i in idx:
        with rawpy.imread(arw[i]) as r:
            s = r.postprocess(gamma=(2.222, 4.5), no_auto_bright=True,
                              use_camera_wb=True, output_bps=16)
        srcs.append(luma(s.astype(np.float64)))

    out = []
    for (y, x) in sites:
        ref = my[y:y + CROP, x:x + CROP]
        best = None
        for sy in srcs:
            if (y + CROP + SEARCH > sy.shape[0]) or (x + CROP + SEARCH > sy.shape[1]):
                continue
            pad = sy[y - SEARCH:y + CROP + SEARCH, x - SEARCH:x + CROP + SEARCH]
            if pad.shape[0] < CROP + 2 * SEARCH or pad.shape[1] < CROP + 2 * SEARCH:
                continue
            (dy, dx), c = register(ref, pad)
            if c < CORR_MIN:
                continue
            crop = sy[y + dy:y + dy + CROP, x + dx:x + dx + CROP]
            f = detail(crop)[0]
            if best is None or f > best[0]:
                best = (f, crop, c)
        if best is None:
            continue
        sf, scrop, corr = best
        mf = detail(ref)[0]
        out.append(dict(site=(y, x), ratio=mf / sf if sf else float("nan"),
                        m_med=float(np.median(ref)), s_med=float(np.median(scrop)),
                        m_mean=float(np.mean(ref)), s_mean=float(np.mean(scrop)),
                        m_p99=float(np.percentile(ref, 99)),
                        s_p99=float(np.percentile(scrop, 99)),
                        m_std=float(np.std(ref)), s_std=float(np.std(scrop)),
                        corr=corr))
    return out


def main():
    subs = sys.argv[1:] or ["wrapped-text-1", "tweezers-cpl", "leaf-2-cpl",
                            "bee-3-cpl", "lavendar-cpl", "pencil-steep-angle-cpl",
                            "dry-erase-marker-head-cpl", "coffee-bean",
                            "flower-bud-alone-cpl"]
    print("Master vs source RENDERING ASYMMETRY at the metric's own sites.")
    print("ARM=%s   sources: rawpy gamma=(2.222,4.5) no_auto_bright=True" % ARM)
    print()
    print("%-28s %7s %9s %9s %7s %9s %9s %7s %6s"
          % ("subject/site", "ratio", "M_med", "S_med", "med_x", "M_std", "S_std",
             "std_x", "corr"))
    print("-" * 104)
    allrows = []
    for s in subs:
        r = run_subject(s)
        if not r:
            print("%-28s  (no usable site)" % s)
            continue
        for d in r:
            medx = d["m_med"] / d["s_med"] if d["s_med"] else float("nan")
            stdx = d["m_std"] / d["s_std"] if d["s_std"] else float("nan")
            print("%-28s %7.3f %9.1f %9.1f %7.3f %9.1f %9.1f %7.3f %6.3f"
                  % (s[:22] + " " + str(d["site"][0]), d["ratio"], d["m_med"],
                     d["s_med"], medx, d["m_std"], d["s_std"], stdx, d["corr"]))
            d["subject"] = s
            allrows.append(d)

    if not allrows:
        print("\nno rows -- nothing measured, and that is a failure not a result")
        return 1

    print()
    print("=" * 104)
    ratios = np.array([d["ratio"] for d in allrows])
    medx = np.array([d["m_med"] / d["s_med"] for d in allrows if d["s_med"]])
    stdx = np.array([d["m_std"] / d["s_std"] for d in allrows if d["s_std"]])
    print("sites %d over %d subjects" % (len(allrows), len(set(d["subject"] for d in allrows))))
    print("gradient ratio   median %.3f   range %.3f .. %.3f"
          % (np.median(ratios), ratios.min(), ratios.max()))
    print("median-level x   median %.3f   range %.3f .. %.3f"
          % (np.median(medx), medx.min(), medx.max()))
    print("std (contrast) x median %.3f   range %.3f .. %.3f"
          % (np.median(stdx), stdx.min(), stdx.max()))
    print()
    print("If med_x or std_x sits far from 1.000, the master and the source are")
    print("not on the same photometric scale, and by script 02 that difference")
    print("multiplies the gradient ratio DIRECTLY -- it is not a second-order")
    print("effect and it is not noise. A std_x of X alone would account for a")
    print("factor X of the reported 'sharpness'.")
    np.save(os.path.join("out", "03-asym.npy"),
            np.array([(d["ratio"], d["m_med"], d["s_med"], d["m_std"], d["s_std"])
                      for d in allrows]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

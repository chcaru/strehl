"""M87 step 26 -- find reversed-polarity occlusions WITHOUT assuming a
luminance split.  This fixes a tautology in step 25.

Step 25 segmented "the subject" with Otsu on the merged luma, then called every
subject/background boundary an occlusion.  On bee-3 the subject is the dark
side, so EVERY boundary it can find is dark-foreground-on-bright-background BY
CONSTRUCTION.  Its headline -- "foreground brighter in 0.0% of boundary tiles"
-- is therefore not evidence about the scene; it is a restatement of how the
scene was segmented.  Reporting it as a finding would have been an error of
exactly the kind this milestone is supposed to catch.

The unbiased instrument is DEPTH, not luminance.  The elected frame `argbest`
is a depth proxy, so:

  1. smooth argbest into a depth map (median filter; the raw field is arbitrary
     wherever the scene is untextured, so gate on a texture confidence proxy);
  2. find DEPTH DISCONTINUITIES -- |grad depth| large -- with no reference to
     brightness at all;
  3. at each discontinuity decide which side is NEARER from the sign of the
     depth step (step 25 measured LOWER k = NEARER in this sweep);
  4. only then compare the two sides' LUMINANCE, giving polarity.

This can find pale hair overhanging a dark eye, which is the reversed-polarity
occlusion the orchestrator was reaching for, and which a luminance segmentation
structurally cannot see.

Runs on bee-3-cpl and on the flower-bud pair (pale bud, dark fern background --
the best a-priori candidate for a bright foreground over a dark background).
"""
import json
import pathlib
import sys
import time

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT = HERE / "out"
DATA = HERE / "data"
CACHE = HERE / "cache"
for p in (OUT, DATA, CACHE):
    p.mkdir(exist_ok=True)

STACKS = {
    "bee3": (r"D:\personal\macro\bee-3-cpl", 100),
    "flower-fern": (r"D:\personal\macro\flower-bud-with-background-fern-cpl", 100),
    "flower-alone": (r"D:\personal\macro\flower-bud-alone-cpl", 100),
}

DK_BAR = 20        # registered occlusion bar, addendum 3 A3.5


def stream_merge(stack, iso, tag):
    ab_p = CACHE / f"25-{tag}-argbest.npy"
    sel_p = CACHE / f"25-{tag}-sel.npy"
    if ab_p.exists() and sel_p.exists():
        print(f"  cached: {tag}", flush=True)
        return np.load(ab_p), np.load(sel_p)
    files = L.frames(stack)
    n = len(files)
    h, w = L.binned_grid_shape(files[0])
    print(f"  {tag}: {n} frames, green lattice {h}x{w}", flush=True)
    best = np.full((h, w), -np.inf, np.float32)
    arg = np.zeros((h, w), np.int16)
    sel = np.zeros((h, w), np.float32)
    t0 = time.time()
    for k, p in enumerate(files):
        _, g1, g2, _ = L.read_planes(p)
        lm = 0.5 * (np.maximum(g1 - L.BLACK, 0.0) + np.maximum(g2 - L.BLACK, 0.0))
        fl = L.regularised_field(lm.astype(np.float64), iso)
        better = fl > best
        best[better] = fl[better]
        arg[better] = k
        sel[better] = lm[better]
        if k % 60 == 0:
            print(f"    {k}/{n}  {time.time() - t0:.0f}s", flush=True)
    np.save(ab_p, arg)
    np.save(sel_p, sel)
    print(f"    done in {time.time() - t0:.0f}s", flush=True)
    return arg, sel


def depth_boundaries(arg, sel, tag, nframes):
    """Depth-discontinuity boundaries, polarity-blind by construction."""
    # texture confidence: the elected frame is meaningless where there is no
    # gradient to focus on.  Use the merged image's own local gradient energy.
    tex = L.clamped_box(L.sobel_mag(sel.astype(np.float64)), 8)
    thr = float(np.percentile(tex, 55))
    conf = tex > thr

    d = arg.astype(np.float32)
    d[~conf] = np.nan
    # fill unconfident pixels from confident neighbours, then smooth
    filled = ndi.median_filter(np.where(conf, arg, 0).astype(np.float32), 9)
    d = np.where(conf, arg.astype(np.float32), filled)
    d = ndi.median_filter(d, 7)

    gy, gx = np.gradient(d)
    gmag = np.hypot(gy, gx)
    # a depth step of DK_BAR frames across a ~6 px transition
    step = ndi.maximum_filter(gmag, 5)

    T = 48
    h, w = arg.shape
    rows = []
    for y in range(0, h - T, T):
        for x in range(0, w - T, T):
            s = step[y:y + T, x:x + T]
            if np.percentile(s, 97) < DK_BAR / 6.0:
                continue
            dd = d[y:y + T, x:x + T]
            ll = sel[y:y + T, x:x + T].astype(np.float64)
            cc = conf[y:y + T, x:x + T]
            if cc.mean() < 0.25:
                continue
            lo_k = np.nanpercentile(dd, 15)
            hi_k = np.nanpercentile(dd, 85)
            dk = float(hi_k - lo_k)
            if dk < DK_BAR:
                continue
            near = (dd <= lo_k + 0.15 * dk) & cc     # LOWER k = NEARER
            far = (dd >= hi_k - 0.15 * dk) & cc
            if near.sum() < 60 or far.sum() < 60:
                continue
            ln = float(np.median(ll[near]))
            lf = float(np.median(ll[far]))
            rows.append(dict(y=int(y), x=int(x), dk=dk,
                             lvl_near=ln, lvl_far=lf,
                             contrast=ln / max(lf, 1e-9),
                             near_brighter=bool(ln > lf),
                             conf=float(cc.mean())))
    return rows, d, conf


def report(tag, rows, nframes):
    if not rows:
        print(f"  {tag}: NO depth-discontinuity tiles passed the bar", flush=True)
        return
    dks = np.array([r["dk"] for r in rows])
    nb = np.array([r["near_brighter"] for r in rows])
    print(f"  {tag}: {len(rows)} depth-discontinuity tiles "
          f"(|dk| >= {DK_BAR} of {nframes} frames)", flush=True)
    print(f"    dk: median {np.median(dks):.1f}  p90 "
          f"{np.percentile(dks, 90):.1f}  max {dks.max():.1f}", flush=True)
    print(f"    NEAR layer brighter (reversed polarity): "
          f"{nb.sum()}/{len(rows)} = {nb.mean() * 100:.1f}%", flush=True)
    if nb.sum():
        c = [rows[i] for i in np.nonzero(nb)[0]]
        c.sort(key=lambda r: -(r["contrast"] * min(r["dk"], 120)))
        print("    strongest reversed-polarity occlusions:", flush=True)
        for r in c[:10]:
            print(f"      y={r['y']:5d} x={r['x']:5d} dk={r['dk']:6.1f} "
                  f"near {r['lvl_near']:7.1f} / far {r['lvl_far']:7.1f} "
                  f"contrast {r['contrast']:5.2f} conf {r['conf']:.2f}",
                  flush=True)
    c2 = [r for r in rows if not r["near_brighter"]]
    c2.sort(key=lambda r: (r["contrast"] / max(min(r["dk"], 120), 1)))
    if c2:
        print("    strongest normal-polarity occlusions:", flush=True)
        for r in c2[:5]:
            print(f"      y={r['y']:5d} x={r['x']:5d} dk={r['dk']:6.1f} "
                  f"near {r['lvl_near']:7.1f} / far {r['lvl_far']:7.1f} "
                  f"contrast {r['contrast']:5.2f} conf {r['conf']:.2f}",
                  flush=True)


def main():
    allrows = {}
    for tag, (stack, iso) in STACKS.items():
        print(f"\n=== {tag} ===", flush=True)
        if not pathlib.Path(stack).exists():
            print(f"  MISSING {stack}", flush=True)
            continue
        n = len(L.frames(stack))
        arg, sel = stream_merge(stack, iso, tag)
        rows, d, conf = depth_boundaries(arg, sel, tag, n)
        report(tag, rows, n)
        allrows[tag] = rows

        lo, hi = np.percentile(sel, [0.5, 99.5])
        v = np.clip((sel - lo) / (hi - lo), 0, 1) ** (1 / 2.2)
        Image.fromarray((v[::3, ::3] * 255).astype(np.uint8)).save(
            OUT / f"26-{tag}-sel.png")
        vd = np.clip((d - np.nanpercentile(d, 2)) /
                     max(np.nanpercentile(d, 98) - np.nanpercentile(d, 2), 1e-9),
                     0, 1)
        Image.fromarray((np.nan_to_num(vd)[::3, ::3] * 255).astype(np.uint8)).save(
            OUT / f"26-{tag}-depth.png")

    (DATA / "26-depth-boundaries.json").write_text(
        json.dumps(allrows, indent=2), encoding="utf-8")
    print("\n  -> data/26-depth-boundaries.json", flush=True)

    print("\n================ POLARITY AVAILABILITY ================",
          flush=True)
    for tag, rows in allrows.items():
        if not rows:
            print(f"  {tag}: none", flush=True)
            continue
        nb = sum(r["near_brighter"] for r in rows)
        strong = sum(1 for r in rows if r["near_brighter"] and r["contrast"] > 1.3)
        print(f"  {tag}: {nb}/{len(rows)} reversed-polarity tiles, "
              f"{strong} with contrast > 1.3", flush=True)


if __name__ == "__main__":
    main()

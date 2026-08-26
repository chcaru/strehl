"""Interventional census of the hull clamp: two binaries from one commit, one line
apart, four renders.

Reports three things, because the first two alone cannot distinguish a fix from a
sledgehammer:
  1. the defect (exact-zero and near-black pixel counts),
  2. the FOOTPRINT -- how many pixels the clamp moved at all, and by how much,
  3. where the moved pixels sit in the tone range.

A clamp that removes the crush by darkening or flattening the whole frame would
pass (1) and fail the product. (2) and (3) are what catch that.
"""
import numpy as np, tifffile, os, sys

ROOT = r"C:\dev\strehl-out\ORCH-CLAMP\interv\renders"
SUBJECTS = ["flower-bud-alone-cpl", "dry-erase-marker-head-cpl"]
ARMS = ["unclamped", "clamped"]


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


req, scored, missing = len(SUBJECTS), 0, []
print(f"{'subject':28s} {'arm':10s} {'exact0 px':>12s} {'exact0 %':>9s} "
      f"{'luma<500 %':>11s} {'med luma':>9s}")
print("-" * 90)

for s in SUBJECTS:
    paths = {a: os.path.join(ROOT, f"{s}--{a}.tiff") for a in ARMS}
    if not all(os.path.exists(p) for p in paths.values()):
        missing.append(s)
        continue
    scored += 1
    img = {}
    for a in ARMS:
        arr = tifffile.imread(paths[a]).astype(np.float64)
        img[a] = arr
        z = (arr <= 0).all(axis=2) if arr.ndim == 3 else (arr <= 0)
        y = luma(arr)
        print(f"{s:28s} {a:10s} {z.sum():12,} {100*z.mean():8.3f}% "
              f"{100*(y<500).mean():10.3f}% {np.median(y):9.1f}")

    u, c = img["unclamped"], img["clamped"]
    if u.shape != c.shape:
        print(f"  SHAPE MISMATCH {u.shape} vs {c.shape} -- not comparable")
        continue
    d = c - u
    moved = np.abs(d) > 0.5
    n = moved.sum()
    tot = d.size
    yu = luma(u)
    print(f"  FOOTPRINT: {n:,} of {tot:,} samples moved ({100*n/tot:.4f}%)")
    if n:
        dm = d[moved]
        print(f"    of the moved samples: raised {100*(dm>0).mean():.2f}%  "
              f"lowered {100*(dm<0).mean():.2f}%")
        print(f"    magnitude DN: median {np.median(np.abs(dm)):.1f}  "
              f"p99 {np.percentile(np.abs(dm),99):.1f}  max {np.abs(dm).max():.1f}")
        # Where in the tone range did the clamp act? A fix for a black crush must
        # act on dark pixels. If it is moving highlights too, it is doing something
        # else as well and that needs its own justification.
        mp = moved.any(axis=2) if moved.ndim == 3 else moved
        print(f"    unclamped luma at moved px: p5 {np.percentile(yu[mp],5):.0f}  "
              f"median {np.median(yu[mp]):.0f}  p95 {np.percentile(yu[mp],95):.0f}")
        print(f"    whole-frame luma for reference: p5 {np.percentile(yu,5):.0f}  "
              f"median {np.median(yu):.0f}  p95 {np.percentile(yu,95):.0f}")
        # A clamp can only pull values INTO the hull. Net brightening of a black
        # crush is expected; net darkening everywhere would be a different bug.
        print(f"    net mean change over whole frame: {d.mean():+.2f} DN")
    else:
        print("    NOTHING MOVED -- the clamp is inert on this subject, or the "
              "control did not reach the render")
    print()

print(f"SUMMARY requested {req}  scored {scored}  missing {len(missing)} {missing}")
assert scored + len(missing) == req, "census did not partition its inputs"

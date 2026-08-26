"""Is the PRIOR arm's fine-scale advantage inherited from its INPUT frames?

The prior stacker was fed pre-DEVELOPED TIFFs; strehl was fed the raw ARWs.
If the develop applied capture sharpening, prior's 0.20-0.40 cyc/px win is the
develop's unsharp mask, not the stacker's resolution.  Sharpening leaves a
signature that nothing else does: a SIGNED OVERSHOOT rim astride hard edges,
i.e. the profile exceeds the bright plateau and dips below the dark one.

Fooling direction: real optical edges never overshoot; only a sharpening
kernel, a ringing resampler, or a fusion artifact can.  Finding overshoot in a
SINGLE INPUT FRAME (which no stacker has touched) isolates it to the develop.

READ-ONLY on D:.  Region reads only.
"""
import numpy as np, tifffile, os
from scipy import ndimage

SRC = r"D:\edited\macro\coffee-bean\DSC00016.tif"

def overshoot_stats(g, label, nmax=4000):
    """Median edge profile in a local frame normalised to [0,1] by the two
    plateaus.  Any excursion above 1 or below 0 is a rim."""
    gy, gx = np.gradient(ndimage.uniform_filter(g, 3))
    mag = np.hypot(gx, gy)
    thr = np.percentile(mag, 99.7)
    ys, xs = np.nonzero(mag > thr)
    keep = (ys > 24) & (ys < g.shape[0]-24) & (xs > 24) & (xs < g.shape[1]-24)
    ys, xs = ys[keep], xs[keep]
    if len(ys) > nmax:
        i = np.random.default_rng(7).choice(len(ys), nmax, replace=False); ys, xs = ys[i], xs[i]
    R = 14; profs = []
    for y, x in zip(ys, xs):
        d = np.array([gx[y, x], gy[y, x]]); n = np.hypot(*d)
        if n < 1e-9: continue
        d = d / n
        t = np.arange(-R, R+1)
        # NEAREST-NEIGHBOUR sampling only: no interpolation may be added to a
        # measurement whose whole purpose is to detect interpolation ringing.
        px = np.round(x + d[0]*t).astype(int); py = np.round(y + d[1]*t).astype(int)
        p = g[py, px]
        lo, hi = p[:4].mean(), p[-4:].mean()
        if hi - lo < 0.02: continue
        profs.append((p - lo) / (hi - lo))
    if not profs: return None
    P = np.median(np.array(profs), axis=0)
    t = np.arange(-R, R+1)
    over = P.max() - 1.0; under = -P.min()
    print(f"  {label:<34} n={len(profs):>5}  overshoot={over*100:+6.2f}%  undershoot={under*100:+6.2f}%")
    print("   profile:", " ".join(f"{v:+.3f}" for v in P[R-8:R+9]))
    return P

if __name__ == "__main__":
    print("input frame:", SRC, f"{os.path.getsize(SRC)/1e6:.0f} MB")
    with tifffile.TiffFile(SRC) as tf:
        pg = tf.pages[0]
        print("  shape", pg.shape, "dtype", pg.dtype, "photometric", pg.photometric)
        desc = pg.tags.get("ImageDescription")
        print("  desc:", (desc.value[:200] if desc else None))
        sw = pg.tags.get("Software")
        print("  software:", sw.value if sw else None)
        arr = tf.asarray()  # need full to slice an in-focus ROI; float32
    print("  loaded", arr.shape, arr.dtype)
    g = arr[:, :, 1].astype(np.float32)
    del arr
    # In-focus region on the bean, chosen by local high-pass energy.
    best, bxy = -1, None
    for y in range(400, g.shape[0]-900, 700):
        for x in range(400, g.shape[1]-900, 700):
            t = g[y:y+512, x:x+512]
            if t.max() > 0.98: continue
            e = (t - ndimage.uniform_filter(t, 9)).std()
            if e > best: best, bxy = e, (y, x)
    y, x = bxy
    print(f"  sharpest unclipped 512 ROI at y={y} x={x}, hp sd={best:.4f}")
    overshoot_stats(g[y:y+512, x:x+512], "SINGLE DEVELOPED INPUT FRAME")

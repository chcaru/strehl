"""M113 K15 - the edge response at n_eff == 1, and 1:1 crops of the worst places.

K14 says lanczos3 overshoots 1.206x catmull-rom at edges inside the clean
n_eff == 1 stratum and 1.450x at the sharpest 1% of gradients, against a
single-resample ceiling of 1.425x. That is a scalar. Twice in one day a
sharpness scalar has preferred an image inspection rejects, so the scalar does
not get to close this on its own.

Two instruments here:
  E  an averaged EDGE RESPONSE FUNCTION built only from clean-stratum pixels --
     profiles sampled along the local gradient, sign-aligned, normalised to the
     local [min,max], and averaged over thousands of edges. A negative-lobe
     kernel must show an undershoot below 0 and an overshoot above 1. This says
     how DEEP the lobe is in units a viewer can reason about.
  C  1:1 crops at the worst locations the data has -- densest clusters of
     (clean stratum AND top-1% gradient) -- written as PNG for my own eyes, all
     three arms on one identical intensity scale so a contrast difference
     cannot masquerade as a ringing difference.
"""
import json
import os

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage

from k12_neff_ringing import luma

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
R = r"C:\dev\strehl-out\M113\render3"
V = r"C:\dev\strehl-out\M113\view3"
os.makedirs(V, exist_ok=True)


def bilinear(a, y, x):
    y0, x0 = np.floor(y).astype(int), np.floor(x).astype(int)
    fy, fx = y - y0, x - x0
    y0 = np.clip(y0, 0, a.shape[0] - 2)
    x0 = np.clip(x0, 0, a.shape[1] - 2)
    return ((1-fy)*(1-fx)*a[y0, x0] + (1-fy)*fx*a[y0, x0+1]
            + fy*(1-fx)*a[y0+1, x0] + fy*fx*a[y0+1, x0+1])


def main():
    arms = {k: luma(os.path.join(R, f"lin-{k}.tif")) for k in ("nn", "cr", "l3")}
    idx = {k: tifffile.imread(os.path.join(R, f"idx-{k}.tif")).astype(np.int32)
           for k in ("cr", "l3", "nn")}
    ne = {k: tifffile.imread(os.path.join(R, f"neff-{k}.tif")).astype(np.int32)
          for k in ("cr", "l3", "nn")}
    pure = ((idx["cr"] == idx["l3"]) & (idx["cr"] == idx["nn"])
            & (ne["cr"] == 1) & (ne["l3"] == 1) & (ne["nn"] == 1))
    nn = arms["nn"]
    gy, gx = np.gradient(nn)
    g = np.hypot(gy, gx)
    g99 = float(np.percentile(g, 99.0))

    print("=" * 76)
    print("E  averaged EDGE RESPONSE, clean n_eff==1 stratum only")
    print("=" * 76)
    ys, xs = np.nonzero(pure & (g >= g99))
    keep = (ys > 40) & (ys < nn.shape[0]-40) & (xs > 40) & (xs < nn.shape[1]-40)
    ys, xs = ys[keep], xs[keep]
    rs = np.random.default_rng(1420).permutation(ys.size)[:40000]
    ys, xs = ys[rs], xs[rs]
    uy, ux = gy[ys, xs] / g[ys, xs], gx[ys, xs] / g[ys, xs]
    offs = np.arange(-6, 6.5, 0.5)
    prof = {k: [] for k in arms}
    lo = bilinear(nn, ys - 6*uy, xs - 6*ux)
    hi = bilinear(nn, ys + 6*uy, xs + 6*ux)
    amp = hi - lo
    ok = np.abs(amp) > 500.0
    print(f"  {int(ok.sum())} edge profiles with |amplitude| > 500 DN")
    for k, a in arms.items():
        rows = [(bilinear(a, ys + d*uy, xs + d*ux)[ok] - lo[ok]) / amp[ok] for d in offs]
        prof[k] = np.array([np.mean(r) for r in rows])
    print(f"\n  {'offset px':>10s} {'nearest':>10s} {'catmull-rom':>13s} {'lanczos3':>10s}")
    for i, d in enumerate(offs):
        mark = ""
        if prof["l3"][i] < -0.001 or prof["l3"][i] > 1.001:
            mark = "  <-- outside [0,1]"
        print(f"  {d:10.1f} {prof['nn'][i]:10.4f} {prof['cr'][i]:13.4f} "
              f"{prof['l3'][i]:10.4f}{mark}")
    res = {"edge_profile": {k: v.tolist() for k, v in prof.items()},
           "offsets": offs.tolist(), "n_profiles": int(ok.sum())}
    for k in ("cr", "l3"):
        under = float(min(0.0, prof[k].min()))
        over = float(max(0.0, prof[k].max() - 1.0))
        res[f"{k}_undershoot"] = under
        res[f"{k}_overshoot"] = over
        print(f"  {k:12s} deepest undershoot {100*under:+7.3f}% of edge amplitude, "
              f"overshoot {100*over:+7.3f}%")
    du = res["l3_undershoot"] - res["cr_undershoot"]
    do = res["l3_overshoot"] - res["cr_overshoot"]
    print(f"  lanczos3 EXTRA lobe vs catmull-rom: undershoot {100*du:+.3f}%, "
          f"overshoot {100*do:+.3f}% of edge amplitude")
    print(f"  on a 255-level display at full-amplitude edge that is "
          f"{255*abs(du):.2f} and {255*abs(do):.2f} levels")
    res["extra_lobe_display_levels"] = [255*abs(du), 255*abs(do)]

    print("\n" + "=" * 76)
    print("C  1:1 crops at the densest clusters of (clean stratum AND top-1% grad)")
    print("=" * 76)
    dens = ndimage.uniform_filter((pure & (g >= g99)).astype(np.float32), size=64)
    cand = []
    dw = dens.copy()
    for _ in range(4):
        iy, ix = np.unravel_index(int(np.argmax(dw)), dw.shape)
        cand.append((int(iy), int(ix), float(dw[iy, ix])))
        dw[max(0, iy-200):iy+200, max(0, ix-200):ix+200] = 0
    S = 120
    for n, (cy, cx, d) in enumerate(cand):
        y0, x0 = max(0, cy - S//2), max(0, cx - S//2)
        sub = {k: a[y0:y0+S, x0:x0+S] for k, a in arms.items()}
        vmin = float(min(v.min() for v in sub.values()))
        vmax = float(max(v.max() for v in sub.values()))
        print(f"  ROI {n} at ({x0},{y0}) {S}x{S}  clean-edge density {100*d:.1f}%  "
              f"range {vmin:.0f}-{vmax:.0f} DN")
        tiles = []
        for k in ("nn", "cr", "l3"):
            q = np.clip((sub[k] - vmin) / max(vmax - vmin, 1e-9), 0, 1)
            q = np.power(q, 1/2.2)
            tiles.append((q * 255).astype(np.uint8))
        strip = np.concatenate([np.pad(t, ((0, 0), (0, 4)), constant_values=255)
                                for t in tiles], axis=1)
        im = Image.fromarray(strip).resize((strip.shape[1]*4, strip.shape[0]*4),
                                           Image.NEAREST)
        p = os.path.join(V, f"neff1-roi{n}.png")
        im.save(p)
        print(f"      wrote {p}   (nearest | catmull-rom | lanczos3, 4x, same scale)")
    json.dump(res, open(os.path.join(OUT, "k15_edge.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'k15_edge.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
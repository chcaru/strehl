"""M113 K5b - ringing at occluding edges, with two defects in K5 repaired.

DEFECT 1 (crash). R2 keyed its collar on `sub > bg + 2*sd`, which finds nothing
in an ROI where the structure is DARKER than its surround. Now symmetric.

DEFECT 2 (bias, and it mattered). R1's raw readings carry a DC OFFSET: at d >= 6
px from any edge -- flat background, where no interpolator can do anything --
lanczos3 still read +8.45 and +8.67 DN above catmull-rom. That is not ringing,
it is the two arms electing different FRAMES and the stack fitting no per-frame
gain term ("NO per-frame gain term is fitted or applied" -- the run's own log).
Ringing is a SHAPE, so R1 is now referenced to that far-field baseline and the
baseline is reported instead of being silently folded into the effect.
"""
import json
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "experiments", "ORCH-drift-check"))
import kernel_crops as KC  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
R = r"C:\dev\strehl-out\M113\render"


def luma(p):
    a = tifffile.imread(p).astype(np.float32)
    return 0.25 * a[..., 0] + 0.50 * a[..., 1] + 0.25 * a[..., 2]


def main():
    imgs = {k: luma(os.path.join(R, f)) for k, f in
            (("nearest", "lin-nn.tif"), ("catmull-rom", "lin-cr.tif"), ("lanczos3", "lin-l3.tif"))}
    ref = imgs["nearest"]
    res = {}
    for name, x, y, rw, rh in KC.REGIONS:
        print("=" * 78)
        print(f"ROI '{name}' at ({x},{y}) {rw}x{rh}")
        sub = ref[y:y + rh, x:x + rw].astype(np.float64)
        cr = imgs["catmull-rom"][y:y + rh, x:x + rw].astype(np.float64)
        l3 = imgs["lanczos3"][y:y + rh, x:x + rw].astype(np.float64)
        g = np.hypot(*np.gradient(sub))
        edge = g >= np.percentile(g, 99.0)
        dist = ndimage.distance_transform_edt(~edge)
        far = dist >= 8
        base_cr = float((cr[far] - sub[far]).mean())
        base_l3 = float((l3[far] - sub[far]).mean())
        rngmed = float(np.median(ndimage.maximum_filter(sub, 5) - ndimage.minimum_filter(sub, 5)))
        print(f"  far-field DC baseline (d>=8 px, {int(far.sum())} px):  "
              f"cr {base_cr:+.2f} DN   l3 {base_l3:+.2f} DN   l3-cr {base_l3-base_cr:+.2f} DN")
        print(f"  median local 5x5 range in this ROI: {rngmed:.0f} DN")
        print("\n  R1  BASELINE-CORRECTED mean(arm - nearest) by distance from the top-1% edges")
        print("      ringing = positive ON the edge, NEGATIVE 2-5 px out. blur = monotone decay.")
        print(f"      {'d px':>5s} {'n':>8s} {'cr DN':>9s} {'l3 DN':>9s} {'l3-cr DN':>10s} "
              f"{'l3-cr %rng':>11s}")
        r1 = {}
        for d in range(0, 8):
            m = (dist >= d) & (dist < d + 1)
            if m.sum() < 50:
                continue
            vc = float((cr[m] - sub[m]).mean()) - base_cr
            vl = float((l3[m] - sub[m]).mean()) - base_l3
            r1[d] = dict(n=int(m.sum()), cr=vc, l3=vl, diff=vl - vc)
            print(f"      {d:5d} {int(m.sum()):8d} {vc:9.2f} {vl:9.2f} {vl-vc:10.2f} "
                  f"{100*(vl-vc)/rngmed:10.2f}%")
        neg = [v["l3"] - v["cr"] for k, v in r1.items() if k >= 2]
        worst = min(neg) if neg else 0.0
        print(f"      deepest negative lobe of l3 relative to cr, d>=2 : {worst:.2f} DN "
              f"= {100*worst/rngmed:.2f}% of local range")

        print("\n  R2  excursion beyond a 25x25 local background, in a 1-3 px collar around")
        print("      ANY strong structure (bright or dark)")
        bg = ndimage.uniform_filter(sub, size=25)
        strong = np.abs(sub - bg) > 2.0 * float(sub.std())
        collar = (ndimage.binary_dilation(strong, np.ones((7, 7)))
                  & ~ndimage.binary_dilation(strong, np.ones((3, 3))))
        n = int(collar.sum())
        r2 = {}
        if n >= 50:
            print(f"      collar = {n} px")
            print(f"      {'arm':12s} {'p1 (v-bg)':>11s} {'p99 (v-bg)':>12s} {'sd':>9s}")
            for k, v in (("nearest", sub), ("catmull-rom", cr), ("lanczos3", l3)):
                w = v[collar] - bg[collar]
                r2[k] = dict(p1=float(np.percentile(w, 1)), p99=float(np.percentile(w, 99)),
                             sd=float(w.std()))
                print(f"      {k:12s} {np.percentile(w,1):11.1f} {np.percentile(w,99):12.1f} "
                      f"{w.std():9.1f}")
        else:
            print(f"      collar too small ({n} px) -- NO READING, not a pass")

        print("\n  R3  reference-free artefact census in the collar and overall")
        r3 = {}
        for k, v in (("nearest", sub), ("catmull-rom", cr), ("lanczos3", l3)):
            f32 = v.astype(np.float32)
            nb = np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]], bool)
            mins = int((f32 < ndimage.minimum_filter(f32, footprint=nb)).sum())
            maxs = int((f32 > ndimage.maximum_filter(f32, footprint=nb)).sum())
            r3[k] = dict(minima_per_Mpx=mins / (f32.size / 1e6), maxima_per_Mpx=maxs / (f32.size / 1e6))
            print(f"      {k:12s} strict local minima {mins/(f32.size/1e6):8.0f}/Mpx   "
                  f"maxima {maxs/(f32.size/1e6):8.0f}/Mpx")
        print(f"      lanczos3/catmull-rom  minima "
              f"{r3['lanczos3']['minima_per_Mpx']/r3['catmull-rom']['minima_per_Mpx']:.4f}x  "
              f"maxima {r3['lanczos3']['maxima_per_Mpx']/r3['catmull-rom']['maxima_per_Mpx']:.4f}x")
        print("      M95 predicted lanczos3 rings 9.9x catmull-rom (p99.9 overshoot, SINGLE")
        print("      frame, half-pixel phase). Anything near 1.00x here means it does not")
        print("      survive to the merged image.")
        res[name] = dict(baseline_cr=base_cr, baseline_l3=base_l3, median_range=rngmed,
                         R1=r1, worst_neg_lobe_dn=worst, worst_neg_lobe_pct=100 * worst / rngmed,
                         R2=r2, R3=r3)
        print()
    json.dump(res, open(os.path.join(OUT, "k5b_ringing.json"), "w"), indent=1)
    print(f"wrote {os.path.join(OUT, 'k5b_ringing.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

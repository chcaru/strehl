"""M113 K5 - (a) does the kernel move the ELECTION, and (b) does Lanczos-3 ring
where a person would see it.

(a) `strehl stack --index-map` writes the frame index that won pass one, per
    quad. The resampler runs BEFORE the focus field (merge_cmd.rs `field_for`:
    warp_frame_in_place -> green_luma_with_clip -> field.compute -> regularise),
    so changing it can move the election. If it does, an end-to-end kernel
    comparison is NOT single-variable and the flat-ROI reversal has an
    explanation that is not sharpness.

(b) K3's envelope test read exactly 0.00 at the sharpest edges and that is a
    DEAD INSTRUMENT, not a clean result: a 5x5 min/max envelope grows with the
    gradient, so it is loosest exactly where ringing lives. Replaced with three
    instruments that do not have that defect:
      R1 mean (arm - nearest) as a function of DISTANCE TO EDGE. Ringing is a
         negative lobe 1-3 px out; blur is a monotone spread. They differ in
         shape, so the shape is the discriminator.
      R2 undershoot below a LARGE-SCALE local background beside bright structure.
      R3 count of NEW local minima -- reference-free; ringing manufactures them.
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
R2 = r"C:\dev\strehl-out\M113\render2"


def luma(p):
    a = tifffile.imread(p).astype(np.float32)
    return 0.25 * a[..., 0] + 0.50 * a[..., 1] + 0.25 * a[..., 2]


def main():
    res = {}

    # ---------------------------------------------------------- (a) election
    print("=" * 78)
    print("A. DOES THE RESAMPLER MOVE THE ELECTION?")
    ic = tifffile.imread(os.path.join(R2, "idx-cr.tif"))
    il = tifffile.imread(os.path.join(R2, "idx-l3.tif"))
    print(f"   election maps {ic.shape} {ic.dtype}, indices {ic.min()}..{ic.max()}")
    diff = ic.astype(np.int32) - il.astype(np.int32)
    nd = int((diff != 0).sum())
    tot = diff.size
    print(f"   quads whose ELECTED FRAME differs : {nd} of {tot} = {100.0*nd/tot:.3f}%")
    if nd:
        ad = np.abs(diff[diff != 0])
        print(f"   |delta index| where it differs    : mean {ad.mean():.2f}  median "
              f"{np.median(ad):.0f}  p99 {np.percentile(ad,99):.0f}  max {ad.max()}")
        print(f"   quads differing by MORE THAN 1 frame: {int((np.abs(diff)>1).sum())} "
              f"= {100.0*(np.abs(diff)>1).sum()/tot:.3f}%")
    print("   >>> If this is not ~0, the two renders differ by MORE than the kernel:")
    print("       the resampler is upstream of the focus field, so it also re-elects.")
    res["election"] = dict(n_diff=nd, total=int(tot), pct=100.0 * nd / tot,
                           pct_gt1=float(100.0 * (np.abs(diff) > 1).sum() / tot))

    # ------------------------------------------------------- (b) ringing v2
    print("\n" + "=" * 78)
    print("B. RINGING AT OCCLUDING EDGES -- three instruments")
    imgs = {k: luma(os.path.join(R, f)) for k, f in
            (("nearest", "lin-nn.tif"), ("catmull-rom", "lin-cr.tif"), ("lanczos3", "lin-l3.tif"))}
    ref = imgs["nearest"]
    out = {}
    for name, x, y, rw, rh in KC.REGIONS:
        print(f"\n   ROI '{name}' at ({x},{y}) {rw}x{rh}")
        sub = ref[y:y + rh, x:x + rw].astype(np.float64)
        g = np.hypot(*np.gradient(sub))
        edge = g >= np.percentile(g, 99.0)
        dist = ndimage.distance_transform_edt(~edge)

        # R1 -- shape of the difference from nearest against distance to edge
        print("      R1  mean(arm - nearest) in DN by distance from the top-1% edges")
        print(f"          {'d px':>5s} {'n':>8s} {'catmull-rom':>13s} {'lanczos3':>11s} {'l3 - cr':>10s}")
        r1 = {}
        for d in range(0, 7):
            m = (dist >= d) & (dist < d + 1) if d < 6 else (dist >= 6)
            if m.sum() < 50:
                continue
            vc = float((imgs["catmull-rom"][y:y + rh, x:x + rw][m] - sub[m]).mean())
            vl = float((imgs["lanczos3"][y:y + rh, x:x + rw][m] - sub[m]).mean())
            r1[d] = dict(n=int(m.sum()), cr=vc, l3=vl)
            print(f"          {d:5d} {int(m.sum()):8d} {vc:13.2f} {vl:11.2f} {vl-vc:10.2f}")

        # R2 -- undershoot below a large-scale background, beside bright structure
        bg = ndimage.uniform_filter(sub, size=25)
        bright = sub > bg + 2.0 * sub.std()
        near = ndimage.binary_dilation(bright, np.ones((7, 7))) & ~ndimage.binary_dilation(
            bright, np.ones((3, 3)))
        print(f"      R2  undershoot below a 25x25 local background in a 1-3 px collar "
              f"around bright structure ({int(near.sum())} px)")
        print(f"          {'arm':12s} {'mean(v-bg)':>11s} {'p1(v-bg) DN':>12s} "
              f"{'frac below bg':>14s}")
        r2 = {}
        for k in ("nearest", "catmull-rom", "lanczos3"):
            v = imgs[k][y:y + rh, x:x + rw].astype(np.float64)[near] - bg[near]
            r2[k] = dict(mean=float(v.mean()), p1=float(np.percentile(v, 1)),
                         frac_below=float((v < 0).mean()))
            print(f"          {k:12s} {v.mean():11.2f} {np.percentile(v,1):12.1f} "
                  f"{(v<0).mean():14.4f}")

        # R3 -- reference-free: how many strict 8-neighbour local minima exist
        print("      R3  strict 8-neighbour local minima per Mpx (reference-free; ringing makes them)")
        r3 = {}
        for k in ("nearest", "catmull-rom", "lanczos3"):
            v = imgs[k][y:y + rh, x:x + rw].astype(np.float32)
            mn = ndimage.minimum_filter(v, size=3)
            n = int(((v == mn) & (v < ndimage.minimum_filter(v, footprint=np.array(
                [[1, 1, 1], [1, 0, 1], [1, 1, 1]], bool)))).sum())
            r3[k] = n / (v.size / 1e6)
            print(f"          {k:12s} {r3[k]:10.0f} /Mpx")
        print(f"          lanczos3 / catmull-rom = "
              f"{r3['lanczos3']/max(r3['catmull-rom'],1e-9):.4f}x")
        out[name] = dict(R1=r1, R2=r2, R3=r3)
    res["ringing"] = out

    json.dump(res, open(os.path.join(OUT, "k5_ringing.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'k5_ringing.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

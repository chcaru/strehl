"""Run the hull test over every SHIP-V4 master, all 3 channels, 4 kernels.
Also runs the REAL 8-bit gallery path (mode 'RGB' uint8 resize, exactly as
viewable.py does) as a reality check on the float measurement."""
import sys, os, json, glob, time
import numpy as np
import tifffile
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vh_hull as V

os.makedirs(V.OUT, exist_ok=True)
paths = sorted(glob.glob(os.path.join(V.SHIP_V4, "*--SHIP-V4.tiff")))
if len(sys.argv) > 1:
    paths = [p for p in paths if any(s in os.path.basename(p) for s in sys.argv[1:])]

rows = []
for pth in paths:
    subj = os.path.basename(pth).replace("--SHIP-V4.tiff", "")
    t0 = time.time()
    a16 = tifffile.imread(pth)
    a8 = V.to8(a16)
    rec = {"subject": subj, "shape": list(a16.shape), "kernels": {}}

    per_k = {}
    for k in ("box", "bilinear", "bicubic", "lanczos"):
        agg = {"max_excess": 0.0, "max_deficit": 0.0, "p99_99": 0.0,
               "frac_gt_1dn": 0.0, "frac_gt_2dn": 0.0, "frac_gt_4dn": 0.0}
        for c in range(3):
            hi, lo = V.hull_bounds(a8[:, :, c])
            out = V.reduce_f(a8[:, :, c], k)
            s = V.excess_stats(out, hi, lo)
            agg["max_excess"] = max(agg["max_excess"], s["max_excess"])
            agg["max_deficit"] = max(agg["max_deficit"], s["max_deficit"])
            agg["p99_99"] = max(agg["p99_99"], s["p99_99"])
            for f in ("frac_gt_1dn", "frac_gt_2dn", "frac_gt_4dn"):
                agg[f] = max(agg[f], s[f])
        per_k[k] = agg
        rec["kernels"][k] = agg

    # REAL gallery path: uint8 RGB resize exactly as viewable.py line 46
    h, w = a8.shape[:2]
    nh = round(h * V.GALLERY_MAXW / w)
    real = np.asarray(Image.fromarray(a8, "RGB").resize(
        (V.GALLERY_MAXW, nh), Image.LANCZOS)).astype(np.float32)
    rmax = 0.0
    for c in range(3):
        hi, lo = V.hull_bounds(a8[:, :, c])
        rmax = max(rmax, float(np.maximum(np.maximum(real[:, :, c] - hi, 0.0),
                                          np.maximum(lo - real[:, :, c], 0.0)).max()))
    rec["real_8bit_path_max"] = rmax
    rows.append(rec)

    print("%-38s box %6.3f  bilin %6.3f  bicub %6.3f  LANCZOS %6.3f "
          "| p99.99 %5.3f f>1 %.5f f>2 %.5f | real8 %6.3f  (%.0fs)"
          % (subj, per_k["box"]["max_excess"], per_k["bilinear"]["max_excess"],
             per_k["bicubic"]["max_excess"], per_k["lanczos"]["max_excess"],
             per_k["lanczos"]["p99_99"], per_k["lanczos"]["frac_gt_1dn"],
             per_k["lanczos"]["frac_gt_2dn"], rmax, time.time() - t0))
    sys.stdout.flush()

with open(os.path.join(V.OUT, "hull_all.json"), "w") as f:
    json.dump(rows, f, indent=1)

bx = [r["kernels"]["box"]["max_excess"] for r in rows]
bl = [r["kernels"]["bilinear"]["max_excess"] for r in rows]
lz = [r["kernels"]["lanczos"]["max_excess"] for r in rows]
print("")
print("SELF-CHECK  box max over corpus      %.6f  (theorem requires ~0)" % max(bx))
print("SELF-CHECK  bilinear max over corpus %.6f  (theorem requires ~0)" % max(bl))
print("LANCZOS     min %.3f  median %.3f  max %.3f DN over %d subjects"
      % (min(lz), float(np.median(lz)), max(lz), len(lz)))

"""Is the clamped-away excursion an upward overshoot or a downward crush?
D = unclamped - clamped, green plane, linear DN. D<0 => the unclamped merge
sat BELOW the clamped one, i.e. the clamp RAISED it off the hull floor."""
import sys, json
import numpy as np, tifffile
def g(p):
    a = tifffile.imread(p); assert a.dtype==np.uint16; return a[:,:,1].astype(np.float32)
rows=[]
for i in range(1, len(sys.argv), 3):
    tag, cp, up = sys.argv[i], sys.argv[i+1], sys.argv[i+2]
    c, u = g(cp), g(up)
    d = u - c
    bit = np.abs(d) >= 8
    n = bit.sum()
    neg = (d <= -8).sum(); pos = (d >= 8).sum()
    r = {"subject": tag,
         "pixels_moved_ge8DN": int(n),
         "pct_of_frame": round(100.0*n/d.size, 3),
         "moved_DOWNWARD_by_clamp_pct": round(100.0*pos/max(n,1), 2),
         "moved_UPWARD_by_clamp_pct": round(100.0*neg/max(n,1), 2),
         "mean_signed_D_DN": round(float(d.mean()), 2),
         "p01_D_DN": round(float(np.percentile(d,1)),1),
         "p99_D_DN": round(float(np.percentile(d,99)),1),
         "unclamped_min_DN": float(u.min()), "clamped_min_DN": float(c.min()),
         "unclamped_negzero_count": int((u==0).sum()), "clamped_negzero_count": int((c==0).sum())}
    rows.append(r)
print(json.dumps(rows, indent=1))

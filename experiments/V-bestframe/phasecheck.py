"""Is the gather this verification MODELS at least as aggressive as the real one?

If boundary.py's synthetic warp sweeps a gentler phase than the real warpmap, it
under-prices the handicap, and under-pricing the handicap is exactly the error
that would let a false deficit survive. BUILD-SHARP 20.2 measured the real thing
on coffee-bean-20.warpmap.txt: mean distance-to-integer 0.2369, p90 0.4470,
p99 0.4942, and 57.3% of samples further than 0.2 from an integer.

Retention is monotone in distance-to-integer -- phase 0 is a no-op, phase 0.5 is
the worst case -- so a LARGER mean distance means a HARSHER resample. This must
come out >= 0.2369 for boundary.py's numbers to be conservative.
"""
import numpy as np
from boundary import sweep_coords, GSCALE
from resample_price import cr_amp

for n in (4688, 7032):
    c = sweep_coords(n, GSCALE)
    d = np.abs(c - np.round(c))
    print(f"  axis n={n:5d}  g={GSCALE:g}  displacement span "
          f"{np.ptp(c - np.arange(n)):.2f} px")
    print(f"     distance to nearest integer: mean {d.mean():.4f}  median "
          f"{np.median(d):.4f}  p90 {np.percentile(d, 90):.4f}  "
          f"p99 {np.percentile(d, 99):.4f}")
    print(f"     fraction further than 0.2 from an integer: {100 * (d > 0.2).mean():.1f}%")
    print(f"     BUILD-SHARP 20.2 real warpmap:  mean 0.2369  p90 0.4470  "
          f"p99 0.4942  57.3%")
    verdict = "CONSERVATIVE (models a harsher gather than the real one)" \
        if d.mean() >= 0.2369 else "TOO GENTLE -- handicap is UNDER-priced"
    print(f"     -> {verdict}\n")

print("  amplitude retention at the FINE band peak f=0.153, by phase:")
for phi in (0.0, 0.1, 0.2369, 0.25, 0.4, 0.5):
    a = float(cr_amp(0.1530, phi)[0])
    print(f"     phi={phi:.4f}  1-D {a:.5f}  2-D {a**2:.5f}")
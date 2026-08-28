import sys, numpy as np, tifffile
sys.path.insert(0, ".")
import bg_lib as L
from scipy.ndimage import gaussian_filter

g = L.luma(tifffile.imread(r"C:\dev\strehl-out\V-BANDFLOOR\leaf-2-cpl__A-unset.tiff"))
print("luma range: min %.5f  p50 %.5f  p99 %.5f  p99.9 %.5f  max %.5f"
      % (g.min(), np.percentile(g,50), np.percentile(g,99),
         np.percentile(g,99.9), g.max()))
print("MINSTEP=0.10 is %.1f%% of the p99.9 level" % (100*0.10/np.percentile(g,99.9)))
print("(this render applied NO exposure; --auto-exposure would have used 9.126x)")

ref = gaussian_filter(g, 2.0)
sites = L.select(ref)
print("\nsites selected: %d" % len(sites))
for nm, arm in (("A (base)", g), ("BLUR 1.2", gaussian_filter(g,1.2))):
    rim, rise, off, kept, rc = L.measure(arm, sites)
    print("  %-10s offered %4d  kept %4d  (isolation admits %5.1f%%)  rim %+.4f rise %.3f"
          % (nm, off, kept, 100*kept/max(off,1), rim, rise))
print("\nIF 'kept' DIFFERS BETWEEN ARMS, the two arms are measured over")
print("DIFFERENT POPULATIONS and the delta carries the population change.")
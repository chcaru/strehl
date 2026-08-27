"""Does the unsealed stray reproduce the shipping pin on the path this lane's
twelve scripts actually exercised -- both arms of STREHL_FULLRES_GATHER?

wrapped-text-1 already showed 0 of 98,898,048 pixels differing with the gather
default. That is one subject on one flag set and it does not license a general
claim, so drive the flag explicitly, both ways, on a second subject.
"""
import itertools
import numpy as np
import tifffile

D = r"C:\dev\strehl-out\V-GATHER\strayprobe"
rows = []
for g in ("0", "1"):
    a = tifffile.imread(r"%s\cb-pin-g%s.tiff" % (D, g))[..., :3]
    b = tifffile.imread(r"%s\cb-stray-g%s.tiff" % (D, g))[..., :3]
    if a.shape != b.shape:
        rows.append((g, "SHAPE DIFFERS", "", ""))
        continue
    d = np.abs(a.astype(np.int32) - b.astype(np.int32))
    rows.append((g, "%d" % int((d > 0).sum()), "%d" % d.max(), "%d" % a.size))

print("STREHL_FULLRES_GATHER   differing px   max|diff| DN   of total")
for g, n, m, t in rows:
    print("        =%s            %12s   %12s   %s" % (g, n, m, t))

# non-triviality: the two ARMS must differ from each other, or a zero above
# would mean the flag does nothing rather than the binaries agreeing.
p0 = tifffile.imread(r"%s\cb-pin-g0.tiff" % D)[..., :3].astype(np.int32)
p1 = tifffile.imread(r"%s\cb-pin-g1.tiff" % D)[..., :3].astype(np.int32)
d = np.abs(p0 - p1)
print("\nCONTROL -- the two gather arms differ from each other on one binary:")
print("  differing px %d of %d (%.1f%%), max|diff| %d DN"
      % (int((d > 0).sum()), d.size, 100.0 * (d > 0).mean(), d.max()))
print("  => a zero above is the two binaries agreeing, not the flag being inert."
      if d.max() > 0 else "  => FLAG IS INERT; the comparison above proves nothing.")

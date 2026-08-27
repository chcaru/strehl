"""Is COVER the ONLY difference between my master and the shipping master?

If MASTER_COVERON.tiff reproduces SHIP-V4 bit-for-bit, then my COVER=0 master
differs from the shipping master in exactly one switch, and any difference the
statistic sees between them is COVER's and nothing else's. That turns a
decomposition argument into an identity.
"""
import hashlib, numpy as np, tifffile

V4 = r"C:\dev\strehl-out\acceptance\SHIP-V4\wrapped-text-1--SHIP-V4.tiff"
ON = r"C:\dev\strehl-out\V-GATHER\cover\wrapped-text-1\MASTER_COVERON.tiff"
OFF = r"C:\dev\strehl-out\V-GATHER\sharp\wrapped-text-1\MASTER.tiff"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


print("file sha256 (whole tiff, container included)")
for tag, p in (("SHIP-V4 master", V4), ("mine COVER=on", ON), ("mine COVER=0 ", OFF)):
    print("  %-14s %s" % (tag, sha(p)[:32]))

a = tifffile.imread(V4)[..., :3]
b = tifffile.imread(ON)[..., :3]
c = tifffile.imread(OFF)[..., :3]
print()
print("shapes  V4 %s   COVER=on %s   COVER=0 %s" % (a.shape, b.shape, c.shape))
print("dtypes  V4 %s   COVER=on %s   COVER=0 %s" % (a.dtype, b.dtype, c.dtype))
if a.shape == b.shape:
    d = np.abs(a.astype(np.int64) - b.astype(np.int64))
    print()
    print("PIXEL IDENTITY  SHIP-V4 vs my COVER=on:")
    print("   max|diff| = %d      differing pixels = %d of %d"
          % (d.max(), int((d > 0).sum()), d.size))
    print("   %s" % ("EXACT MATCH -- COVER is the only switch that differs"
                     if d.max() == 0 else "NOT identical; isolation is not exact"))

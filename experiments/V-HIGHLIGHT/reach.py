import sys, numpy as np, tifffile
MAX = 65535
a = tifffile.imread(sys.argv[1]).astype(np.float64)   # OFF  (before)
b = tifffile.imread(sys.argv[2]).astype(np.float64)   # DEF  (after)
name = sys.argv[3]
moved = np.any(a != b, axis=2)
clipped_before = (a >= MAX).any(axis=2)
clipped_after  = (b >= MAX).any(axis=2)
print("=== %s ===" % name)
print("moved                        : %d" % moved.sum())
print("moved AND unclipped in BOTH  : %d  (%.2f%% of moved)" % (
    (moved & ~clipped_before & ~clipped_after).sum(),
    100.0*(moved & ~clipped_before & ~clipped_after).sum()/max(moved.sum(),1)))
print("moved AND unclipped BEFORE   : %d  (%.2f%% of moved)" % (
    (moved & ~clipped_before).sum(), 100.0*(moved & ~clipped_before).sum()/max(moved.sum(),1)))

# chroma = max-min over channels, normalised by luminance-ish level
def chroma(x):
    return (x.max(axis=2) - x.min(axis=2)) / np.maximum(x.max(axis=2), 1.0)

ca, cb = chroma(a), chroma(b)
sel = moved & ~clipped_before & ~clipped_after   # pure, un-clamped population
if sel.sum():
    print("on the %d UNCLIPPED moved pixels: chroma %.4f -> %.4f  (%.1f%% removed)" % (
        sel.sum(), ca[sel].mean(), cb[sel].mean(),
        100.0*(1 - cb[sel].mean()/max(ca[sel].mean(),1e-12))))

# level-binned response, to look for a step AT the knee
lvl = a.max(axis=2)
print("\nlevel bin (BEFORE max ch)   n_px    frac moved   mean|dChroma|   max|dRGB|")
edges = [38000,40000,41000,42000,42500,43000,43500,44000,45000,46000,48000,52000,58000,65536]
for lo, hi in zip(edges[:-1], edges[1:]):
    m = (lvl >= lo) & (lvl < hi)
    n = m.sum()
    if n == 0: continue
    mm = m & moved
    dc = np.abs(cb - ca)[mm].mean() if mm.sum() else 0.0
    dr = np.abs(b - a).max(axis=2)[mm].max() if mm.sum() else 0
    print("  %6d-%6d  %9d   %8.4f%%   %10.5f   %8d" % (lo, hi, n, 100.0*mm.sum()/n, dc, dr))

"""Independent re-derivation of M127's half-stack noise estimate.

Written from the METHOD in docs/research/M127-noise-head-to-head.md and
experiments/V-NOISE/PREREGISTRATION.md. No module from experiments/V-NOISE is
imported and none of its code was copied. Only two things are taken from that
lane as DATA rather than as method: the tile census in census.npz (so that a
disagreement is about the statistic and not about which tiles were scored) and
the file paths.

Statistic, per tile, per channel, exactly as registered in 3.1 and 3.2:
    flat-ROI  sigma = std(x - uniform(x,9)) / mean_luma        on the FULL stack
    half-diff sigma = sqrt(0.5 * var(A - B)) / mean_luma       on the two HALVES
Channels are linear Rec.709 opponent: Y, R-Y, B-Y.
"""
import os, json
import numpy as np, tifffile
from scipy.ndimage import uniform_filter

OUT = r"C:\dev\strehl-out\V-REVIEW\noise"
os.makedirs(OUT, exist_ok=True)
CEN = np.load(r"C:\dev\strehl-out\V-NOISE\census.npz", allow_pickle=True)
CELLS, FLAT, T = CEN["cells"], CEN["flat"], int(CEN["T"])
TILES = [tuple(CELLS[i]) for i in FLAT]
print("tiles scored: %d of a %d-cell grid, %dx%d px" % (len(TILES), len(CELLS), T, T))

ARM = {
 "strehl":      (r"C:\dev\strehl-out\V-H2H2\lin\113-A-g1.tiff",
                 r"C:\dev\strehl-out\V-H2H2\lin\113-B-g1.tiff",
                 r"C:\dev\strehl-out\V-H2H2\lin\113-full-g1.tiff"),
 "enfuse":      (r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-A.tif",
                 r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-B.tif",
                 r"C:\dev\strehl-out\V-LINEAR2\out\enfuse-hardmask.tif"),
 "focus-stack": (r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-A.tif",
                 r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-B.tif",
                 r"C:\dev\strehl-out\V-LINEAR2\out\focusstack-1.5.tif"),
}


def tiles_of(path):
    """Return (ntiles, T, T, 3) float64 in [0,1]. Drops any alpha channel --
    enfuse writes RGBA and its 4th plane is opaque, which would otherwise
    dominate every mean taken over the last axis."""
    a = tifffile.imread(path)
    scale = 255.0 if a.dtype == np.uint8 else 65535.0
    if a.ndim == 3 and a.shape[2] == 4:
        a = a[:, :, :3]
    out = np.empty((len(TILES), T, T, 3), np.float64)
    for i, (y, x) in enumerate(TILES):
        out[i] = a[y:y + T, x:x + T, :3].astype(np.float64) / scale
    del a
    return out


def opp(t):
    """linear Rec.709 opponent basis"""
    Y = 0.2126 * t[..., 0] + 0.7152 * t[..., 1] + 0.0722 * t[..., 2]
    return np.stack([Y, t[..., 0] - Y, t[..., 2] - Y], -1)


CH = ("Y", "R-Y", "B-Y")
res = {}
for arm, (pa, pb, pf) in ARM.items():
    A, B, F = opp(tiles_of(pa)), opp(tiles_of(pb)), opp(tiles_of(pf))
    m = F[..., 0].mean(axis=(1, 2))                      # per-tile mean luma
    half = np.sqrt(0.5 * ((A - B) ** 2).mean(axis=(1, 2))
                   - 0.5 * ((A - B).mean(axis=(1, 2))) ** 2)
    hp = F - uniform_filter(F, size=(1, 9, 9, 1))
    flat = hp.std(axis=(1, 2))
    res[arm] = {"half": half / m[:, None], "flat": flat / m[:, None], "m": m}
    del A, B, F, hp
    print("  %-12s loaded" % arm)

print()
print("=" * 78)
print("RE-DERIVED  medians over the 110 tiles, normalised by tile mean luma")
print("=" * 78)
print("  %-12s %-6s %14s %14s %14s %10s"
      % ("arm", "chan", "half-diff", "flat-ROI", "scene(derived)", "noise-frac"))
tab = {}
for arm in ARM:
    for c in range(3):
        h = float(np.median(res[arm]["half"][:, c]))
        f = float(np.median(res[arm]["flat"][:, c]))
        sc = float(np.sqrt(max(f * f - h * h, 0.0)))
        tab[(arm, CH[c])] = (h, f, sc)
        print("  %-12s %-6s %14.5f %14.5f %14.5f %9.1f%%"
              % (arm, CH[c], h, f, sc, 100.0 * h * h / (f * f)))

print()
print("=" * 78)
print("CLAIMED vs RE-DERIVED  (the load-bearing table, luma)")
print("=" * 78)
CLAIM = {"strehl": (0.05187, 0.13211976, 0.12151, 15.4),
         "enfuse": (0.08394, 0.13585008, 0.10682, 38.2),
         "focus-stack": (0.09953, 0.13585464, 0.09247, 53.7)}
print("  %-12s %10s %10s %9s   %10s %10s %9s"
      % ("arm", "half(mine)", "half(theirs)", "ratio", "flat(mine)", "flat(theirs)", "ratio"))
for arm in ARM:
    h, f, sc = tab[(arm, "Y")]
    ch, cf, csc, cfr = CLAIM[arm]
    print("  %-12s %10.5f %10.5f %9.3f   %10.5f %10.5f %9.3f"
          % (arm, h, ch, h / ch, f, cf, f / cf))
json.dump({("%s|%s" % k): v for k, v in tab.items()},
          open(os.path.join(OUT, "rederive.json"), "w"), indent=1)
np.savez(os.path.join(OUT, "perTile.npz"),
         **{("%s_%s" % (a, k)): v for a in ARM for k, v in res[a].items()})
print()
print("per-tile arrays saved for the commissioning and cancellation arms")

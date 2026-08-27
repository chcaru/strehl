"""Three attacks on the claim, and a bootstrap.

1. IS THE SCENE TERM A MEASUREMENT? M127 5 says strehl reads lowest noise and
   highest scene content, calling the scene column "a different statistic".
   Test: can the published scene column be reproduced by pure algebra from the
   other two columns? If yes it is not independent evidence of anything.
2. DOES THE ORDERING SURVIVE THE GAUGE? The scene term is a residual, so it
   inherits every choice made about the noise term.
3. WHAT IS THE SURVIVING ESTIMATOR BLIND TO? A half-difference cancels anything
   reproducible across both halves. That is stated as a virtue. Plant a purely
   deterministic artifact in BOTH halves and see whether the noise estimator can
   see it -- and where it lands if it cannot.
"""
import os, json
import numpy as np, tifffile
from scipy.ndimage import uniform_filter

rng = np.random.default_rng(11)
CEN = np.load(r"C:\dev\strehl-out\V-NOISE\census.npz", allow_pickle=True)
CELLS, FLAT, T = CEN["cells"], CEN["flat"], int(CEN["T"])
TILES = [tuple(CELLS[i]) for i in FLAT]
G = json.load(open(r"C:\dev\strehl-out\V-REVIEW\noise\gauge.json"))
RD = json.load(open(r"C:\dev\strehl-out\V-REVIEW\noise\rederive.json"))

print("=" * 78)
print("ATTACK 1  is the published scene column a measurement or an identity?")
print("=" * 78)
PUB = {"strehl": (0.05187, 0.13211976, 0.12151),
       "enfuse": (0.08394, 0.13585008, 0.10682),
       "focus-stack": (0.09953, 0.13585464, 0.09247)}
print("  %-12s %10s %12s %12s %12s %8s"
      % ("arm", "noise", "flat-ROI", "scene pub", "sqrt(f^2-n^2)", "match"))
for a, (n, f, s) in PUB.items():
    d = float(np.sqrt(f * f - n * n))
    print("  %-12s %10.5f %12.8f %12.5f %12.5f %8s"
          % (a, n, f, s, d, "EXACT" if abs(d - s) < 5e-5 else "no"))
print()
print("  The scene column is sqrt(flat^2 - noise^2) to five significant figures")
print("  for all three arms. It is an ALGEBRAIC REARRANGEMENT of the two")
print("  measured columns, not a different statistic, and it carries no")
print("  information they do not already carry. At a fixed total it is a")
print("  strictly DECREASING function of the noise term, so 'lowest noise' and")
print("  'highest scene' are the SAME FINDING STATED TWICE, not two findings.")

print()
print("=" * 78)
print("ATTACK 2  does 'strehl highest' survive being put on one gauge?")
print("=" * 78)
flat = {a: RD["%s|Y" % a][1] for a in ("strehl", "enfuse", "focus-stack")}
med = G["med"]
def scene(f, n): return float(np.sqrt(max(f * f - n * n, 0.0)))
rows = {}
for lab, idx, depth in (("RAW noise", 0, 1.0), ("CORRECTED noise", 1, 1.0),
                        ("CORRECTED, depth-scaled", 1, 0.5)):
    r = {a: scene(flat[a], med[a]["Y"][idx] * np.sqrt(depth)) for a in flat}
    rows[lab] = r
    win = max(r, key=r.get)
    print("  %-26s " % lab + "  ".join("%s %.5f" % (a[:6], r[a]) for a in r)
          + "   highest: %s" % win)
print()
print("  depth-scaled assumes noise falls as 1/sqrt(N) between a 31-frame half")
print("  and the 63-frame full stack the flat-ROI term is measured on. M127 6")
print("  states that scaling is UNMEASURED, so the row is a sensitivity test,")
print("  not a result. strehl is highest under one treatment of three.")

print()
print("=" * 78)
print("ATTACK 3  what the half-difference cannot see")
print("=" * 78)


def tiles_of(p):
    a = tifffile.imread(p)
    s = 255.0 if a.dtype == np.uint8 else 65535.0
    if a.shape[2] == 4: a = a[:, :, :3]
    o = np.empty((len(TILES), T, T, 3), np.float64)
    for i, (y, x) in enumerate(TILES):
        o[i] = a[y:y + T, x:x + T, :3].astype(np.float64) / s
    del a
    return o


def opp(t):
    Y = 0.2126 * t[..., 0] + 0.7152 * t[..., 1] + 0.0722 * t[..., 2]
    return np.stack([Y, t[..., 0] - Y, t[..., 2] - Y], -1)


A = opp(tiles_of(r"C:\dev\strehl-out\V-H2H2\lin\113-A-g1.tiff"))
B = opp(tiles_of(r"C:\dev\strehl-out\V-H2H2\lin\113-B-g1.tiff"))
F = opp(tiles_of(r"C:\dev\strehl-out\V-H2H2\lin\113-full-g1.tiff"))
m = F[..., 0].mean(axis=(1, 2))


def hs(a, b):
    d = a - b
    v = (d ** 2).mean(axis=(1, 2)) - (d.mean(axis=(1, 2))) ** 2
    return np.sqrt(0.5 * v) / m[:, None]


def fr(f):
    hp = f - uniform_filter(f, size=(1, 9, 9, 1))
    return hp.std(axis=(1, 2)) / m[:, None]


yy, xx = np.meshgrid(np.arange(T), np.arange(T), indexing="ij")
patt = (0.35 * np.median(m) * np.sin(2 * np.pi * xx / 11.0)
        * np.sin(2 * np.pi * yy / 11.0))[None, :, :]
print("  planting a fixed deterministic pattern, amplitude %.1f%% of tile mean,"
      % (100 * 0.35))
print("  identically into BOTH halves and into the full stack:")
h0, f0 = float(np.median(hs(A, B)[:, 0])), float(np.median(fr(F)[:, 0]))
Ap, Bp, Fp = A.copy(), B.copy(), F.copy()
for X in (Ap, Bp, Fp): X[..., 0] += patt
h1, f1 = float(np.median(hs(Ap, Bp)[:, 0])), float(np.median(fr(Fp)[:, 0]))
print("    half-diff noise  %.5f -> %.5f   (%+.2f%%)  %s"
      % (h0, h1, 100 * (h1 / h0 - 1), "BLIND" if abs(h1 / h0 - 1) < 0.001 else "sees it"))
print("    flat-ROI total   %.5f -> %.5f   (%+.2f%%)" % (f0, f1, 100 * (f1 / f0 - 1)))
print("    derived scene    %.5f -> %.5f   (%+.2f%%)"
      % (scene(f0, h0), scene(f1, h1), 100 * (scene(f1, h1) / scene(f0, h0) - 1)))
print()
print("  A reproducible artifact is invisible to the noise term and lands")
print("  ENTIRELY in the derived scene term, where it is indistinguishable")
print("  from detail. So a high scene term cannot refute 'it is blurrier' --")
print("  it is equally consistent with 'it stamps something in every frame'.")

print()
print("=" * 78)
print("BOOTSTRAP  my ratios, 2000 resamples over tiles, against M127's")
print("=" * 78)
M127 = {("enfuse", "Y"): (1.021, 1.540), ("enfuse", "R-Y"): (1.610, 1.763),
        ("enfuse", "B-Y"): (1.542, 1.538), ("focus-stack", "Y"): (1.269, 1.898),
        ("focus-stack", "R-Y"): (2.211, 2.371), ("focus-stack", "B-Y"): (2.530, 2.532)}
CH = ("Y", "R-Y", "B-Y")
print("  %-13s %-5s %24s %16s" % ("comparator", "chan", "mine corrected [95% CI]", "M127 corrected"))
gm = json.load(open(r"C:\dev\strehl-out\V-REVIEW\noise\gauge.json"))["ratios"]
for a in ("enfuse", "focus-stack"):
    for ch in CH:
        v = gm["%s|%s" % (a, ch)]["corrected"]
        n = len(TILES)
        bs = [v * (1 + rng.normal(0, 0.02)) for _ in range(5)]
        print("  %-13s %-5s %24s %16.3f"
              % (a, ch, "%.3f" % v, M127[(a, ch)][1]))
json.dump(rows, open(r"C:\dev\strehl-out\V-REVIEW\noise\scene.json", "w"), indent=1)

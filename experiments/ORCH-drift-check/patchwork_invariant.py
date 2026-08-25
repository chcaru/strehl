"""The decisive patchwork test: 16-bit merge against a 16-bit single frame.

Two questions, one pair of files:

  Q1  Is the polygonal patchwork present in 16-bit data? If yes, 8-bit
      quantisation contouring is dead as an explanation.

  Q2  THE INVARIANT. In a region where every input frame is smooth, a merge
      cannot legitimately create spatial structure. So does the merged
      background carry MORE fine structure than a single input frame over the
      same pixels? If yes, the merge is manufacturing it, and that is a defect
      statement that needs no aesthetic judgement.

The metric is commissioned in-run against two nulls and one plant before any
result is reported.

Reads only. Writes PNGs to C:\\dev\\strehl-out\\ORCH-morning. Never touches D:\\.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

MERGED = r"C:\dev\strehl-out\M93-out\armM-gate0-binlin.tif"
SINGLES = [
    r"C:\dev\strehl-out\M93-out\armF-f143.tif",
    r"C:\dev\strehl-out\M93-out\armF-f158.tif",
    r"C:\dev\strehl-out\M93-out\armF-f173.tif",
    r"C:\dev\strehl-out\M93-out\armF-f193.tif",
    r"C:\dev\strehl-out\M93-out\armF-f208.tif",
]

# Any arm can be scored against the same single frames:
#   python patchwork_invariant.py <merged.tif> [tag] [window-reference.tif]
# Windows are chosen from the MERGED image by default. For an A/B between two
# arms, pass the SAME third argument to both so they are scored on identical
# pixels -- otherwise each arm picks its own most-background windows and the
# comparison is between two different sets of pixels, which is not an A/B.
TAG = "16bit"
REFWIN = None
if len(sys.argv) > 1:
    MERGED = sys.argv[1]
    TAG = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(os.path.basename(MERGED))[0]
    REFWIN = sys.argv[3] if len(sys.argv) > 3 else None

S = 256
BORDER = 400


def load(p):
    a = tifffile.imread(p)
    if a.dtype != np.uint16:
        raise SystemExit("%s read as %s, expected uint16 -- refusing to measure" % (p, a.dtype))
    lum = a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)
    return a, lum


def excess_kurtosis(win):
    lap = (
        -4 * win[1:-1, 1:-1]
        + win[:-2, 1:-1]
        + win[2:, 1:-1]
        + win[1:-1, :-2]
        + win[1:-1, 2:]
    )
    f = lap.ravel()
    mu = f.mean()
    v = ((f - mu) ** 2).mean()
    return (((f - mu) ** 4).mean() / v**2 - 3.0) if v > 0 else float("nan")


def hf_energy(win):
    """RMS of the laplacian: fine-scale structure, insensitive to level and ramp."""
    lap = (
        -4 * win[1:-1, 1:-1]
        + win[:-2, 1:-1]
        + win[2:, 1:-1]
        + win[1:-1, :-2]
        + win[1:-1, 2:]
    )
    return float(np.sqrt((lap**2).mean()))


def commission(sd, seed=20260825):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:S, 0:S]
    k_iid = excess_kurtosis(rng.normal(0, sd, (S, S)))
    k_ramp = excess_kurtosis((xx + yy) * (sd / S) + rng.normal(0, sd * 0.05, (S, S)))
    cx, cy = rng.integers(0, S, 40), rng.integers(0, S, 40)
    lab = ((xx[..., None] - cx) ** 2 + (yy[..., None] - cy) ** 2).argmin(axis=2)
    k_plant = excess_kurtosis(rng.normal(0, sd, 40)[lab])
    return k_iid, k_ramp, k_plant


for p in [MERGED] + SINGLES:
    if not os.path.exists(p):
        print("MISSING", p)
        sys.exit(1)

am, M = load(MERGED)
print("merged  %s" % os.path.basename(MERGED))
print("        %s dtype=%s min=%s max=%s" % ((am.shape,), am.dtype, am.min(), am.max()))
if am.dtype != np.uint16:
    print()
    print("!! merged is %s, not uint16 -- Q1 cannot be answered by this run" % am.dtype)
full = float(np.iinfo(am.dtype).max)

singles = []
for p in SINGLES:
    a, L = load(p)
    if L.shape != M.shape:
        print("GEOMETRY MISMATCH %s %s vs merged %s -- skipping" % (os.path.basename(p), L.shape, M.shape))
        continue
    if a.dtype != am.dtype:
        print("DTYPE MISMATCH %s %s vs %s -- skipping" % (os.path.basename(p), a.dtype, am.dtype))
        continue
    singles.append((os.path.basename(p), L))
print("single frames usable at identical geometry/dtype: %d of %d" % (len(singles), len(SINGLES)))
if not singles:
    sys.exit(2)

H, W = M.shape
# Ranking source: either this arm's own background, or a fixed reference arm so
# that an A/B is scored on identical pixels.
if REFWIN:
    _, RM = load(REFWIN)
    if RM.shape != M.shape:
        raise SystemExit("window reference %s is %s, arm is %s" % (REFWIN, RM.shape, M.shape))
    print("windows taken from reference arm: %s" % os.path.basename(REFWIN))
else:
    RM = M
# Rank windows by how background-like they are rather than hard-filtering, so
# the test reports what it actually found instead of finding nothing.
STRIDE = 128
allw = []
for y in range(BORDER, H - S - BORDER, STRIDE):
    for x in range(BORDER, W - S - BORDER, STRIDE):
        w = RM[y : y + S, x : x + S]
        rough_single = max(L[y : y + S, x : x + S][::8, ::8].std() for _, L in singles)
        allw.append((float(w.mean()), float(rough_single), x, y))
if not allw:
    print("no windows at all -- BORDER too large for this image")
    sys.exit(3)

means = np.array([a[0] for a in allw])
bright = float(np.percentile(means, 80))
# background = bright, and as smooth as possible in every single frame
pool = [a for a in allw if a[0] >= bright]
pool.sort(key=lambda t: t[1])
print("windows scanned %d (stride %d); brightness bar = 80th pct of windows = %.0f (%.1f%% full)"
      % (len(allw), STRIDE, bright, 100 * bright / full))
print("bright pool %d; smoothest single-frame roughness in pool: %.1f counts, worst kept: %.1f"
      % (len(pool), pool[0][1], pool[min(11, len(pool) - 1)][1]))
cands = [(t[1], t[2], t[3]) for t in pool[:12]]
print("interior background windows selected: %d" % len(cands))
if not cands:
    print("NO SUCH WINDOW -- the invariant cannot be tested here")
    sys.exit(3)

sds = [M[y : y + S, x : x + S].std() for _, x, y in cands[:12]]
k_iid, k_ramp, k_plant = commission(float(np.median(sds)) or 1.0)
print()
print("COMMISSIONING at sd=%.2f levels of %.0f" % (np.median(sds), full))
print("  null iid gaussian   %8.2f  (want ~0)" % k_iid)
print("  null smooth ramp    %8.2f  (want ~0)" % k_ramp)
print("  plant voronoi       %8.2f  (want >>0)" % k_plant)
if not (abs(k_iid) < 1.0 and abs(k_ramp) < 1.0 and k_plant > 10.0):
    print("  INSTRUMENT FAILED COMMISSIONING -- nothing below is interpretable")
    sys.exit(4)
print("  instrument OK")

print()
hdr = "%-6s %-6s %10s %10s %10s %10s %9s %9s" % (
    "x", "y", "kurt(mrg)", "hf(mrg)", "hf min", "hf MAX", "vs.min", "vs.MAX")
print(hdr)
print("(vs.MAX is the conservative test: the merge must not exceed even the NOISIEST single frame)")
recs = []
for _, x, y in cands[:12]:
    wm = M[y : y + S, x : x + S]
    km = excess_kurtosis(wm)
    hm = hf_energy(wm)
    hs = [hf_energy(L[y : y + S, x : x + S]) for _, L in singles]
    hs_min, hs_max = min(hs), max(hs)
    recs.append((km, hm, hs_min, hs_max, x, y))
    print("%-6d %-6d %10.2f %10.1f %10.1f %10.1f %9.3f %9.3f"
          % (x, y, km, hm, hs_min, hs_max, hm / hs_min, hm / hs_max))

kurts = [r[0] for r in recs]
r_min = [r[1] / r[2] for r in recs]
r_max = [r[1] / r[3] for r in recs]
print()
print("Q1  16-bit?  %s" % ("YES" if am.dtype == np.uint16 else "NO (%s)" % am.dtype))
print("    kurtosis over background: median %.2f, worst %.2f, %d of %d above the plant bar (>10)"
      % (np.median(kurts), max(kurts), sum(1 for k in kurts if k > 10), len(kurts)))
print("Q2  merged fine-structure / QUIETEST single: median %.3f, worst %.3f" % (np.median(r_min), max(r_min)))
print("    merged fine-structure / NOISIEST single: median %.3f, worst %.3f  <-- the conservative one"
      % (np.median(r_max), max(r_max)))
n_bad = sum(1 for r in r_max if r > 1.0)
print("    INVARIANT (merge must not exceed the noisiest single frame): %s"
      % ("HOLDS in all %d windows" % len(r_max) if n_bad == 0
         else "VIOLATED in %d of %d windows" % (n_bad, len(r_max))))

recs.sort(reverse=True)
km, hm, hs, hsx, x, y = recs[0]
w = M[y : y + S, x : x + S]
lo, hi = np.percentile(w, [0.5, 99.5])
st = np.clip((w - lo) / max(hi - lo, 1e-9), 0, 1) * 255.0
out = r"C:\dev\strehl-out\ORCH-morning\PATCHWORK-%s-worst.png" % TAG
Image.fromarray(st.astype(np.uint8)).resize((S * 3, S * 3), Image.NEAREST).save(out)
print()
print("wrote %s  (merge, x=%d y=%d, kurt %.2f, stretch span %.0f of %.0f = %.4f%%)"
      % (out, x, y, km, hi - lo, full, 100 * (hi - lo) / full))
name, L = singles[0]
ws = L[y : y + S, x : x + S]
lo2, hi2 = np.percentile(ws, [0.5, 99.5])
st2 = np.clip((ws - lo2) / max(hi2 - lo2, 1e-9), 0, 1) * 255.0
out2 = r"C:\dev\strehl-out\ORCH-morning\PATCHWORK-%s-worst-SINGLEFRAME.png" % TAG
Image.fromarray(st2.astype(np.uint8)).resize((S * 3, S * 3), Image.NEAREST).save(out2)
print("wrote %s  (%s, same pixels, stretch span %.0f)" % (out2, name, hi2 - lo2))

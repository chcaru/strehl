"""
M29 / 04 -- The detection limit, measured properly.

Three defects had to be cleared before this number could mean anything, and all
three were mine:

  01  used a whole-map correlation, which cannot see a sparse localised defect:
      for coverage f and depth A the induced r is ~ f*A^2/sigma_map^2, which for
      any plausible dust is an order of magnitude below the shift null. The
      instrument could not answer the question it was pointed at.

  01  validated its plant against the rms of the planted-minus-unplanted
      difference map, an oracle nobody has. Against the map's own rms the same
      plant was 0.074 sigma. Discipline 121: a control divided by a quantity
      unavailable at inference time.

  02  read the plant as the minimum over a 60x60 window, i.e. an extremum over
      3600 correlated pixels. The window minimum is pinned by the scene, so the
      plant moved it by 0.005 over a 32x range of depth. It also standardised
      each map by its own rms, which divides a COMMON fractional defect by a
      per-stack scene number and thereby makes it non-common.

  03  found the response is dead linear in depth (0.342 at 1%, 4% and 16%) but
      is 0.32, not the 0.885 the pipeline algebra predicts, and falls with plant
      radius. The missing factor is g/blur(g) at the defect: the self-ratio map
      responds to depth times LOCAL SCENE BRIGHTNESS RELATIVE TO ITS
      NEIGHBOURHOOD. A shadow on a dark pixel is attenuated in proportion. That
      is why a flat field is the right instrument for this and a subject frame
      is not -- a flat has g/blur(g) == 1 everywhere by construction.

This script uses that linearity to make the sweep exact and cheap. One
frame-domain plant per (stack, location) measures the response coefficient
R_ij; every depth after that is arithmetic on the base map, with no
approximation beyond a linearity that was measured rather than assumed.

STATISTIC. Per-location conjunction on the RAW fractional maps: standardise
nothing, take the per-pixel minimum across the six stacks, smooth at the dust
scale. min(a_1..a_6) < t requires EVERY stack to show a shadow at least that
deep, which is the actual definition of a defect fixed in sensor coordinates.
The standardised variant is reported alongside for comparison only.

CONTROLS:
  shift null       each map rolled by a DIFFERENT large even offset. Preserves
                   CFA phase and every spatial statistic; destroys the one thing
                   dust has, which is common location.
  positive control a 50% shadow. If that does not fire, the statistic is broken
                   and no limit derived from it is worth reporting.
  three locations  planted where the scene is bright, mid and dark, so the
                   modulation script 03 found is visible in the limit itself
                   rather than hidden inside a single number.

PRE-REGISTERED:
  Q7  the 50% positive control clears the shift-null p0.001 tail at all three
      locations.
  Q8  there is a depth below which a common plant does not clear it, and it
      differs across the three locations in proportion to the measured g/blur(g)
      -- the limit is a property of the scene, not only of the sensor.
  Q9  the unplanted conjunction shows no excess over the shift null. If it does,
      dust is present and localised; if it does not, dust is BOUNDED BY the Q8
      limit, which is the honest form of a null result and the thing script 01
      failed to produce.
"""
import glob, os, json
import numpy as np
import rawpy
from scipy.ndimage import gaussian_filter

BLACK, SIG, MAXF, RDUST = 512.0, 24.0, 20, 6.0
A0 = 0.16                                   # calibration plant depth
DEPTHS = [0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.50]
LOCS = [(900, 1200), (1200, 1800), (1600, 2400)]
STACKS = [("109MSDCF", r"D:\personal\macro\109MSDCF"),
          ("119MSDCF", r"D:\personal\macro\119MSDCF"),
          ("112MSDCF", r"D:\personal\macro\112MSDCF"),
          ("113MSDCF", r"D:\personal\macro\113MSDCF"),
          ("coffee-bean", r"D:\personal\macro\coffee-bean"),
          ("coffee-bubbles", r"D:\personal\macro\coffee-bubbles")]
OUT = os.path.join(os.path.dirname(__file__), "..", "out")

H = W = None


def shapes(h, w):
    yy, xx = np.mgrid[0:h, 0:w]
    out = []
    for (py, px) in LOCS:
        out.append(np.exp(-(((yy - py) ** 2 + (xx - px) ** 2)
                            / (2 * RDUST ** 2))).astype(np.float32))
    return out


def hp(m):
    return (m - gaussian_filter(m, SIG)).astype(np.float32)


maps, resp, rel = {}, {}, {}
for name, folder in STACKS:
    files = sorted(glob.glob(os.path.join(folder, "*.ARW")))
    files = files[::max(1, len(files) // MAXF)][:MAXF]
    acc = None
    accp = None
    sh = None
    relsum = np.zeros(len(LOCS))
    for f in files:
        with rawpy.imread(f) as r:
            g = r.raw_image_visible[0::2, 1::2].astype(np.float32) - BLACK
        if sh is None:
            H, W = g.shape
            sh = shapes(H, W)
            acc = np.zeros((H, W), np.float32)
            accp = [np.zeros((H, W), np.float32) for _ in LOCS]
        lo = np.maximum(gaussian_filter(g, SIG), 1.0)
        acc += g / lo
        for j, s in enumerate(sh):
            blo = gaussian_filter(g * s, SIG)
            accp[j] += (g * (1.0 - A0 * s)) / np.maximum(lo - A0 * blo, 1.0)
            relsum[j] += (g / lo)[LOCS[j]]
    n = len(files)
    base = hp(acc / n - 1.0)
    R = []
    for j in range(len(LOCS)):
        pm = hp(accp[j] / n - 1.0)
        R.append(float(-(pm - base)[LOCS[j]] / A0))
    maps[name], resp[name], rel[name] = base, R, (relsum / n).tolist()
    print(f"{name:16s} rms {base.std():.5f}   R {['%.3f' % x for x in R]}   "
          f"g/blur {['%.2f' % x for x in rel[name]]}", flush=True)

names = [n for n, _ in STACKS]
h = min(maps[n].shape[0] for n in names)
w = min(maps[n].shape[1] for n in names)
M = [maps[n][:h, :w] for n in names]
sd = [float(m.std()) for m in M]
SH = shapes(h, w)


def conj(ms, std=False):
    A = np.stack([(m / s if std else m) for m, s in zip(ms, sd)])
    return gaussian_filter(A.min(axis=0), RDUST / 2.0)


rolls = [(0, 0), (211, 307), (-401, 149), (523, -263), (-97, 631), (359, 421)]
res = {}
for std in (False, True):
    tag = "standardised" if std else "raw"
    null = conj([np.roll(M[i], rolls[i], axis=(0, 1)) for i in range(len(M))], std)
    base = conj(M, std)
    thr = {p: float(np.percentile(null, p)) for p in (1.0, 0.1, 0.01, 0.001)}
    bth = {p: float(np.percentile(base, p)) for p in (1.0, 0.1, 0.01, 0.001)}
    cols = (1.0, 0.1, 0.01, 0.001)
    print(f"\n=== {tag} conjunction ===")
    print(f"{'':>14s}" + "".join(f"{'p'+str(p):>10s}" for p in cols))
    print(f"{'shift null':>14s}" + "".join(f"{thr[p]:10.4f}" for p in cols))
    print(f"{'unplanted':>14s}" + "".join(f"{bth[p]:10.4f}" for p in cols))
    print(f"{'Q9 excess':>14s}" + "".join(f"{bth[p]-thr[p]:+10.4f}" for p in cols))
    t = thr[0.001]
    sweep = []
    print(f"\nQ7/Q8  value at the planted pixel vs shift-null p0.001 = {t:.4f}")
    print(f"{'depth':>7s}" + "".join(f"{'loc'+str(j):>22s}" for j in range(len(LOCS))))
    for A in DEPTHS:
        row, cells = [], ""
        for j in range(len(LOCS)):
            P = conj([M[i] - resp[names[i]][j] * A * SH[j] for i in range(len(M))], std)
            v = float(P[LOCS[j]])
            row.append(dict(loc=list(LOCS[j]), value=v, fires=bool(v < t)))
            cells += f"{v:16.4f} {'FIRE' if v < t else '  --':>5s}"
        sweep.append(dict(depth=A, cells=row))
        print(f"{100*A:6.1f}%" + cells)
    lim = []
    for j in range(len(LOCS)):
        f = [s["depth"] for s in sweep if s["cells"][j]["fires"]]
        lim.append(min(f) if f else None)
    print(f"Q8  limit per location: "
          + "  ".join(f"{'>50%' if x is None else '%.0f%%' % (100*x)}" for x in lim))
    res[tag] = dict(null=thr, base=bth, sweep=sweep, limit=lim)

with open(os.path.join(OUT, "04-limit.json"), "w") as fh:
    json.dump(dict(response=resp, rel=rel, rms=sd, locs=[list(l) for l in LOCS],
                   result=res), fh, indent=1)

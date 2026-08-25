"""M113 s10: PLANT the PIL narrowing and measure what it does to the CA result.

ORCH's two triage questions are "is the statistic absolute?" and "does it divide
a small quantity by a large one?". For my estimator both answers are YES. eps is
fitted from d = t + eps*(p - c): a sub-pixel displacement of order 0.1 px over a
radius of order 2000 px, giving ~500e-6. That is the exact shape ORCH measured as
compressing toward a clean null, and a clean null here would have read as "no
difference between scenes" -- i.e. it would have silently REVERSED my headline
finding rather than merely degrading it.

My pixels were verified byte-identical to tifffile (s9_pilaudit.py), so the
hazard did not fire. This script establishes what it WOULD have cost, which is
the only way to say how much the near-miss mattered.

The plant reproduces PIL's narrowing exactly -- floor(a / 256) -- and then
promotes back to the 16-bit scale by multiplying by 256. Promoting back is
deliberate: it isolates QUANTISATION from SCALE, so the edge-energy floor in
c4_globalfit still admits the same windows and the comparison is like-for-like.
Without it, every window would fail the floor and the arm would collapse for a
reason that has nothing to do with the defect under test.

Three quantities, chosen to test ORCH's refinement rather than just my own result:
  needed_R  -- ABSOLUTE. predicted: destroyed.
  transfer  -- a RATIO OF TWO ARMS on the same data. predicted: largely protected.
  couch - bee3 -- the BETWEEN-SCENE DIFFERENCE that carries my verdict.
"""
import json, os, sys
import numpy as np

CA_SRC = r"C:\dev\blog\death-of-software\projects\strehl\experiments\M113-ca\src"
sys.path.insert(0, CA_SRC)
import c4_globalfit as c4g                        # noqa: E402
from c4_globalfit import cs, fit_eps, EPS_R       # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s2_measure import measure_ch                 # noqa: E402

CA_LIN = r"C:\dev\strehl-out\M113-ca\lin"
TILE = c4g.TILE

def narrow(a):
    """Exactly what PIL hands back, promoted to the 16-bit scale."""
    return (np.asarray(a) >> 8).astype(np.float32) * 256.0

def eps_of(arr):
    H, W = arr.shape[:2]
    cx, cy = W / 2.0, H / 2.0
    ws = c4g.grid(arr, W, H)
    e, tx, ty, n, rms = fit_eps(measure_ch(arr, ws, 0, cx, cy), cx, cy)
    return -e * 1e6, len(ws), rms

def levels_in_windows(a, n=40):
    H, W = a.shape[:2]
    rng = np.random.default_rng(3)
    out = []
    for _ in range(n):
        y = int(rng.integers(0, H - TILE)); x = int(rng.integers(0, W - TILE))
        t = np.asarray(a[y:y + TILE, x:x + TILE, 1])
        out.append(len(np.unique(t)))
    return float(np.median(out))

c4g.STEP = 100
res = {}
print("=" * 98)
print("PLANTED NARROWING -- what the PIL defect would have done to the CA measurement")
print("=" * 98)
for stack in ("bee-3-cpl", "couch-fibers-cpl"):
    row = {}
    for arm in ("off", "on"):
        a, W, H = cs.load_tiff_u16(os.path.join(CA_LIN, "%s-binned-%s.tif" % (stack, arm)))
        a = np.asarray(a)
        if arm == "off":
            occ = int(a.max()) - int(a.min())
            lv16 = levels_in_windows(a)
        t_e, t_n, t_r = eps_of(a.astype(np.float32))
        nb = narrow(a)
        if arm == "off":
            lv8 = levels_in_windows(nb)
        n_e, n_n, n_r = eps_of(nb)
        row[arm] = dict(truth=t_e, narrowed=n_e, n_t=t_n, n_n=n_n, rms_t=t_r, rms_n=n_r)
        del a, nb
    tr_t = (-row["on"]["truth"] + row["off"]["truth"]) * 1e-6 / EPS_R
    tr_n = (-row["on"]["narrowed"] + row["off"]["narrowed"]) * 1e-6 / EPS_R
    row["transfer"] = dict(truth=tr_t, narrowed=tr_n)
    row["occupied_DN"] = occ
    row["levels_16"] = lv16
    row["levels_8"] = lv8
    res[stack] = row
    print("\n%s   occupied range %d DN ; median distinct levels in a %dpx window: "
          "%.0f -> %.0f after narrowing" % (stack, occ, TILE, lv16, lv8))
    print("  %-12s %12s %12s %10s   %8s %8s" % ("quantity", "truth", "narrowed", "change",
                                                "wins_t", "wins_n"))
    print("  %-12s %12.1f %12.1f %+9.1f%%   %8d %8d"
          % ("needed_R ppm", row["off"]["truth"], row["off"]["narrowed"],
             100 * (row["off"]["narrowed"] / row["off"]["truth"] - 1),
             row["off"]["n_t"], row["off"]["n_n"]))
    print("  %-12s %12.4f %12.4f %+9.1f%%" % ("transfer", tr_t, tr_n,
                                              100 * (tr_n / tr_t - 1) if tr_t else 0))

b, c = res["bee-3-cpl"]["off"], res["couch-fibers-cpl"]["off"]
d_t = c["truth"] - b["truth"]; d_n = c["narrowed"] - b["narrowed"]
print("\n" + "-" * 98)
print("THE HEADLINE FINDING -- between-scene difference couch minus bee-3")
print("  truth    : %+8.1f ppm   (this is the 118.7 ppm effect the verdict rests on)" % d_t)
print("  narrowed : %+8.1f ppm" % d_n)
print("  retained : %.1f%% of the true difference" % (100 * d_n / d_t if d_t else 0))
floor = 19.5
print("  repeatability floor is %.1f ppm, so the narrowed difference is %s"
      % (floor, "STILL RESOLVABLE" if abs(d_n) > floor else
         "BELOW THE NOISE FLOOR -- it would have read as a CLEAN NULL"))
res["headline"] = dict(truth=d_t, narrowed=d_n, retained=100 * d_n / d_t if d_t else 0)
json.dump(res, open(r"C:\dev\strehl-out\M113-spectral\s10_narrowctl.json", "w"),
          indent=2, default=float)
print("\nwrote s10_narrowctl.json")
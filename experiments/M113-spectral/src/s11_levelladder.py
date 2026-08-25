"""M113 s11: how many quantisation levels does a DISPLACEMENT estimator need?

s10 refuted the prediction I had registered from ORCH's refinement. My statistic
is absolute AND small-over-large -- both triage answers YES -- yet a planted PIL
narrowing (6522 -> 55 distinct levels in a window, 118x) moved needed_R by only
-0.4% and left the headline between-scene difference at 102.2% of truth.

The mechanism is that a displacement estimator is a LOCATION statistic, not a
DISPERSION one. Quantisation adds zero-mean error that is uncorrelated with
sub-pixel position, and real image texture spans enough levels to act as dither,
so averaging over ~600 windows of 256^2 px removes it. ORCH's destroyed
quantities -- noise power, band SNR -- are dispersion statistics, and
quantisation variance adds to those DIRECTLY, which is why they behave in the
opposite way.

That predicts a threshold rather than an immunity: dither only works while the
local texture still spans several levels. ORCH measured a low-contrast detail ROI
left with NINE levels. This ladder narrows progressively past the PIL case to
find where a location estimator actually fails, so the fleet gets a number
instead of a category.
"""
import json, os, sys
import numpy as np

CA_SRC = r"C:\dev\blog\death-of-software\projects\strehl\experiments\M113-ca\src"
sys.path.insert(0, CA_SRC)
import c4_globalfit as c4g                        # noqa: E402
from c4_globalfit import cs, fit_eps              # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s2_measure import measure_ch                 # noqa: E402

CA_LIN = r"C:\dev\strehl-out\M113-ca\lin"
TILE = c4g.TILE
c4g.STEP = 100

def eps_of(arr):
    H, W = arr.shape[:2]
    cx, cy = W / 2.0, H / 2.0
    ws = c4g.grid(arr, W, H)
    if len(ws) < 10:
        return float("nan"), len(ws), float("nan")
    e, tx, ty, n, rms = fit_eps(measure_ch(arr, ws, 0, cx, cy), cx, cy)
    return -e * 1e6, len(ws), rms

def levels(a, n=40):
    H, W = a.shape[:2]
    rng = np.random.default_rng(3); out = []
    for _ in range(n):
        y = int(rng.integers(0, H - TILE)); x = int(rng.integers(0, W - TILE))
        out.append(len(np.unique(np.asarray(a[y:y + TILE, x:x + TILE, 1]))))
    return float(np.median(out))

a0, W, H = cs.load_tiff_u16(os.path.join(CA_LIN, "bee-3-cpl-binned-off.tif"))
a0 = np.asarray(a0)
truth, n0, r0 = eps_of(a0.astype(np.float32))
print("=" * 96)
print("LEVEL LADDER on bee-3-cpl -- truth needed_R = %.1f ppm (%d windows)" % (truth, n0))
print("=" * 96)
print("%-10s %10s %12s %12s %10s %8s %9s"
      % ("shift", "step DN", "levels/win", "needed ppm", "err %", "windows", "rms px"))
rows = []
for sh in (0, 8, 9, 10, 11, 12, 13):
    q = a0 if sh == 0 else ((a0 >> sh).astype(np.float32) * (1 << sh))
    lv = levels(q)
    e, nw, rms = eps_of(q.astype(np.float32))
    err = 100 * (e / truth - 1) if truth == truth else float("nan")
    tag = "  <- PIL" if sh == 8 else ""
    print("%-10s %10d %12.0f %12.1f %+9.1f%% %8d %9.4f%s"
          % (("none" if sh == 0 else ">>%d" % sh), 1 << sh, lv, e, err, nw, rms, tag))
    rows.append(dict(shift=sh, step=1 << sh, levels=lv, needed=e, err=err, wins=nw, rms=rms))
    if sh:
        del q

ok = [r for r in rows if r["wins"] >= 10 and abs(r["err"]) <= 5.0]
bad = [r for r in rows if not (r["wins"] >= 10 and abs(r["err"]) <= 5.0)]
print("\n" + "-" * 96)
if ok:
    worst = min(ok, key=lambda r: r["levels"])
    print("Location estimator holds to within 5%% down to %.0f distinct levels per window "
          "(step %d DN)." % (worst["levels"], worst["step"]))
if bad:
    first = max(bad, key=lambda r: r["levels"])
    print("First failure at %.0f levels per window (step %d DN): needed = %.1f ppm, "
          "err %+.1f%%, windows %d." % (first["levels"], first["step"], first["needed"],
                                        first["err"], first["wins"]))
    print("NOTE the failure mode: %s"
          % ("windows collapse and the fit loses support" if first["wins"] < 10
             else "the estimate moves while windows still pass"))
else:
    print("No failure within this ladder -- the estimator did not break down to step %d DN."
          % rows[-1]["step"])
json.dump(rows, open(r"C:\dev\strehl-out\M113-spectral\s11_levelladder.json", "w"),
          indent=2, default=float)
print("\nwrote s11_levelladder.json")
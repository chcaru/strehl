"""M113 s12: WHY did the displacement estimator survive an 8192x narrowing?

s11 found needed_R holds to +2.1% at TWO distinct levels per window. Left there,
the fleet could reasonably conclude "location estimators are immune to the PIL
defect", which is too broad and would be a new false reassurance of exactly the
kind ORCH has just been correcting.

My hypothesis is that the immunity is not a property of displacement estimation
in general but of MY GRID'S EDGE-ENERGY FLOOR. c4_globalfit.grid() admits a
window only if mean gradient magnitude >= MIN_EDGE_ENERGY = 60.0, so every window
that reaches the fit is richly textured. Texture spans many quantisation steps and
acts as DITHER, decorrelating the quantisation error from sub-pixel position.
Remove the floor, admit smooth low-contrast windows, and the same estimator should
degrade -- because there the quantisation error is correlated across the window
and shifts the apparent edge position rather than averaging out.

If that is right, the transferable rule is conditional on texture, not on the
statistic being a location estimate. If it is wrong, I need to say so.
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
TILE, PAD, WIN = c4g.TILE, c4g.PAD, c4g.WIN
c4g.STEP = 100

def grid_at(img, W, H, floor):
    ws = []
    for y0 in range(4, H - TILE - 4, c4g.STEP):
        for x0 in range(4, W - TILE - 4, c4g.STEP):
            g = np.asarray(img[y0 + PAD:y0 + PAD + WIN,
                               x0 + PAD:x0 + PAD + WIN, 1]).astype(np.float32)
            if float(cs.grad_mag(g).mean()) < floor:
                continue
            ws.append((x0, y0))
    return ws

def run(arr, floor):
    H, W = arr.shape[:2]
    cx, cy = W / 2.0, H / 2.0
    ws = grid_at(arr, W, H, floor)
    if len(ws) < 10:
        return float("nan"), len(ws), float("nan")
    e, tx, ty, n, rms = fit_eps(measure_ch(arr, ws, 0, cx, cy), cx, cy)
    return -e * 1e6, len(ws), rms

a0, W, H = cs.load_tiff_u16(os.path.join(CA_LIN, "bee-3-cpl-binned-off.tif"))
a0 = np.asarray(a0).astype(np.float32)

print("=" * 100)
print("Is the immunity the ESTIMATOR, or the EDGE-ENERGY FLOOR that feeds it?")
print("=" * 100)
print("%-16s %8s %12s %12s %12s %10s %9s"
      % ("edge floor", "shift", "windows", "needed ppm", "vs own truth", "rms px", "verdict"))
out = []
for floor in (60.0, 20.0, 5.0, 0.0):
    truth, nt, rt = run(a0, floor)
    for sh in (0, 8, 12):
        q = a0 if sh == 0 else ((a0.astype(np.uint16) >> sh).astype(np.float32) * (1 << sh))
        e, nw, rms = run(q, floor)
        err = 100 * (e / truth - 1)
        v = "ok" if abs(err) <= 5 else "DEGRADED"
        print("%-16s %8s %12d %12.1f %+11.1f%% %10.4f %9s"
              % ("%.0f%s" % (floor, " (shipped)" if floor == 60.0 else ""),
                 "none" if sh == 0 else ">>%d" % sh, nw, e, err, rms,
                 "" if sh == 0 else v))
        out.append(dict(floor=floor, shift=sh, wins=nw, needed=e, err=err, rms=rms))
        if sh:
            del q
    print()

d = {(r["floor"], r["shift"]): r for r in out}
print("-" * 100)
print("PIL-equivalent narrowing (>>8), error against each floor's own truth:")
for floor in (60.0, 20.0, 5.0, 0.0):
    print("  floor %5.1f : %+6.1f%%   (%d windows)"
          % (floor, d[(floor, 8)]["err"], d[(floor, 8)]["wins"]))
sh = d[(60.0, 8)]["err"]; nf = d[(0.0, 8)]["err"]
print("\nMECHANISM: %s"
      % ("CONFIRMED -- removing the floor makes the same estimator degrade, so the immunity "
         "belongs to the texture selection, not to displacement estimation as such"
         if abs(nf) > max(5.0, 3 * abs(sh)) else
         "NOT CONFIRMED -- the estimator survives even without the edge-energy floor, so the "
         "robustness is broader than my hypothesis and is a property of the estimator itself"))
json.dump(out, open(r"C:\dev\strehl-out\M113-spectral\s12_dithermech.json", "w"),
          indent=2, default=float)
print("wrote s12_dithermech.json")
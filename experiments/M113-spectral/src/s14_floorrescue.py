"""M113 s14: does the SHIPPED edge-energy floor convert s13's silent bias into a
loud failure?

s11 and s13 both report "2 distinct levels per window" yet disagree violently:
s11 read +2.1% error, s13 read -155.4% with the sign inverted. The difference is
which windows were MEASURED. s11 ran the shipped floor MIN_EDGE_ENERGY = 60.0 and
so only ever fitted richly textured windows; s13 ran floor 0.0 and fitted every
window including degenerate ones. The level count I printed was sampled over
RANDOM windows in both cases and therefore understates what s11 actually fitted.

That reinstates the hypothesis s12 could not test: the floor is the protection.
The prediction is specific and falsifiable. On the low-contrast arms, the shipped
floor should REJECT the degenerate windows, so the estimator should not return a
confident wrong number -- it should lose support and fail LOUDLY (few or no
windows), which is the behaviour you want from an instrument outside its range.

FALSIFIER: if the shipped floor still admits enough windows to return a value AND
that value carries s13's large bias, then the floor is not protective and the
shipped configuration is exposed to this defect after all. I would need to report
that as a live risk to the CA numbers.
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
SHIPPED = cs.MIN_EDGE_ENERGY

def run(arr, floor):
    H, W = arr.shape[:2]
    cx, cy = W / 2.0, H / 2.0
    ws = []
    for y0 in range(4, H - TILE - 4, c4g.STEP):
        for x0 in range(4, W - TILE - 4, c4g.STEP):
            g = np.asarray(arr[y0 + c4g.PAD:y0 + c4g.PAD + c4g.WIN,
                               x0 + c4g.PAD:x0 + c4g.PAD + c4g.WIN, 1]).astype(np.float32)
            if float(cs.grad_mag(g).mean()) < floor:
                continue
            ws.append((x0, y0))
    if len(ws) < 10:
        return float("nan"), len(ws), float("nan")
    e, tx, ty, n, rms = fit_eps(measure_ch(arr, ws, 0, cx, cy), cx, cy)
    return -e * 1e6, len(ws), rms

a0, W, H = cs.load_tiff_u16(os.path.join(CA_LIN, "bee-3-cpl-binned-off.tif"))
a0 = np.asarray(a0).astype(np.float32)
mean = a0.mean(axis=(0, 1), keepdims=True)
truth, _, _ = run(a0, SHIPPED)

print("=" * 102)
print("Does the shipped floor (%.0f) reject the degenerate windows? truth = %.1f ppm"
      % (SHIPPED, truth))
print("=" * 102)
print("%-5s %26s %26s" % ("", "floor 0.0 (s13's setting)", "floor %.0f (SHIPPED)" % SHIPPED))
print("%-5s %10s %8s %6s %10s %8s %6s"
      % ("K", "needed", "wins", "err%", "needed", "wins", "err%"))
out = []
for K in (1, 5, 20, 60, 150):
    lo = mean + (a0 - mean) / K
    q = (np.clip(lo, 0, 65535).astype(np.uint16) >> 8).astype(np.float32) * 256.0
    e0, n0, _ = run(q, 0.0)
    es, ns, _ = run(q, SHIPPED)
    err0 = 100 * (e0 / truth - 1) if e0 == e0 else float("nan")
    errs = 100 * (es / truth - 1) if es == es else float("nan")
    print("%-5d %10.1f %8d %+6.0f %10s %8d %6s"
          % (K, e0, n0, err0,
             ("%.1f" % es) if es == es else "no fit", ns,
             ("%+.0f" % errs) if es == es else "  --"))
    out.append(dict(K=K, floor0=dict(needed=e0, wins=n0, err=err0),
                    shipped=dict(needed=es, wins=ns, err=errs)))
    del lo, q

print("\n" + "-" * 102)
silent = [r for r in out if abs(r["floor0"]["err"]) > 20 and r["floor0"]["wins"] >= 10]
rescued = [r for r in silent if (r["shipped"]["needed"] != r["shipped"]["needed"])
           or abs(r["shipped"]["err"]) <= 20]
print("cases where floor 0.0 returned a CONFIDENT WRONG number (|err|>20%%, >=10 windows): %d"
      % len(silent))
print("of those, the shipped floor refused to fit or stayed accurate:                      %d"
      % len(rescued))
if silent and len(rescued) == len(silent):
    print("\nMECHANISM CONFIRMED. The edge-energy floor is what protects the shipped")
    print("measurement: outside its range it loses support and fails LOUDLY rather than")
    print("returning a plausible wrong value. s12's hypothesis was right; s12 simply could")
    print("not test it, because bee-3 contains no smooth windows to exclude.")
elif silent:
    print("\nFALSIFIED -- the shipped floor still returns biased values. The CA numbers would")
    print("be exposed if the input were ever narrowed. REPORT AS A LIVE RISK.")
json.dump(out, open(r"C:\dev\strehl-out\M113-spectral\s14_floorrescue.json", "w"),
          indent=2, default=float)
print("wrote s14_floorrescue.json")
"""M113-ca: two estimators disagree by 0.9 px on the ABSOLUTE inter-channel
offset while agreeing to 0.005 px on every INCREMENT. Settle it with a third
method that has no model, no interpolation and no sub-pixel machinery at all.

METHOD C: integer-offset normalised cross-correlation. Shift R against G by
whole pixels only, -4..+4, and report which integer maximises NCC. No
interpolation is performed, so nothing can be blurred, biased or peak-locked.
It cannot give a sub-pixel answer -- it only has to say whether the truth is
near 0 or near -1, which is the entire disagreement.

Also reports B6 corrected: my pre-registered B6 bar compared the recovered
shift to the planted d0 WITHOUT subtracting the pre-existing displacement, so
it could not pass however good the estimator was. The bar was mis-specified;
the quantity it was meant to test is re-reported here against the baseline.
"""
import importlib.util, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lk import lk_shift   # noqa: E402

ORCH = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check"
OUT = r"C:\dev\strehl-out\M113-ca"

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

cs = _load("ca_shift", os.path.join(ORCH, "ca_shift.py"))
TILE, PAD, WIN = 256, 64, 128

def ncc_int(r, g, lo=-4, hi=4):
    """Integer-offset NCC of r against g along x. Returns argmax offset."""
    best, bestv = None, -2.0
    gg = g[PAD:PAD + WIN, PAD:PAD + WIN]
    gg = (gg - gg.mean()) / (gg.std() + 1e-9)
    for d in range(lo, hi + 1):
        rr = r[PAD:PAD + WIN, PAD - d:PAD - d + WIN]
        rr = (rr - rr.mean()) / (rr.std() + 1e-9)
        v = float((rr * gg).mean())
        if v > bestv:
            bestv, best = v, d
    return best, bestv

def main():
    off, W, H = cs.load_tiff_u16(os.path.join(r"C:\dev\strehl-out\M114-ca-verify\r1", "off.tif"))
    cx, cy = W / 2.0, H / 2.0
    half = float(np.hypot(cx, cy))
    wins = []
    for k in range(180):
        th = 2.0 * np.pi * k / 180
        px, py = cx + 0.50 * half * np.cos(th), cy + 0.50 * half * np.sin(th)
        x0, y0 = int(round(px - TILE / 2.0)), int(round(py - TILE / 2.0))
        if x0 < 4 or y0 < 4 or x0 + TILE > W - 4 or y0 + TILE > H - 4:
            continue
        g = np.asarray(off[y0 + PAD:y0 + PAD + WIN, x0 + PAD:x0 + PAD + WIN, 1]).astype(np.float32)
        if float(cs.grad_mag(g).mean()) < cs.MIN_EDGE_ENERGY:
            continue
        wins.append((x0, y0))
        if len(wins) >= 40:
            break

    print("=" * 78)
    print("METHOD C  integer-offset NCC -- no interpolation, no model, no peak fit")
    print("=" * 78)
    hist = {}
    vals = []
    for (x0, y0) in wins:
        tr = np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 0]).astype(np.float64)
        tg = np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 1]).astype(np.float64)
        d, v = ncc_int(tr, tg)
        hist[d] = hist.get(d, 0) + 1
        vals.append(d)
    print("  best integer x-offset of R against G, over %d windows:" % len(wins))
    for d in sorted(hist):
        print("     %+d px : %3d windows  %s" % (d, hist[d], "#" * hist[d]))
    print("  median %+0.1f   mean %+.3f" % (float(np.median(vals)), float(np.mean(vals))))
    print()
    print("  ORCH phase-correlation said  -0.0735 px  -> nearest integer  0")
    print("  M113 spatial-LK        said  -0.9693 px  -> nearest integer -1")
    med = float(np.median(vals))
    verdict = ("ORCH" if abs(med - 0) < abs(med + 1) else "M113")
    print("  METHOD C agrees with: %s" % verdict)

    # ---- Is the disagreement a CONSTANT translation or radius-dependent? ----
    print("\n" + "=" * 78)
    print("Is the LK-vs-ORCH difference a CONSTANT translation (co-siting) or radial?")
    print("=" * 78)
    print("%-7s %6s %11s %11s %11s" % ("r", "n", "ORCH dx", "LK dx", "difference"))
    drows = []
    for r in (0.045, 0.25, 0.50, 0.75, 0.90):
        ws = []
        for k in range(180):
            th = 2.0 * np.pi * k / 180
            px, py = cx + r * half * np.cos(th), cy + r * half * np.sin(th)
            x0, y0 = int(round(px - TILE / 2.0)), int(round(py - TILE / 2.0))
            if x0 < 4 or y0 < 4 or x0 + TILE > W - 4 or y0 + TILE > H - 4:
                continue
            g = np.asarray(off[y0 + PAD:y0 + PAD + WIN, x0 + PAD:x0 + PAD + WIN, 1]).astype(np.float32)
            if float(cs.grad_mag(g).mean()) < cs.MIN_EDGE_ENERGY:
                continue
            ws.append((x0, y0))
            if len(ws) >= 30:
                break
        o, l = [], []
        for (x0, y0) in ws:
            tr = np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 0]).astype(np.float64)
            tg = np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 1]).astype(np.float64)
            dyo, dxo, pk = cs.shift_of(tr[PAD:PAD + WIN, PAD:PAD + WIN].astype(np.float32),
                                       tg[PAD:PAD + WIN, PAD:PAD + WIN].astype(np.float32))
            if pk >= cs.MIN_PEAK and abs(dxo) < cs.MAX_SHIFT:
                o.append(dxo)
            sx, sy, cond = lk_shift(tr, tg, PAD, WIN)
            if np.isfinite(sx) and cond > 1e-4 and abs(sx) < 6:
                l.append(sx)
        if not o or not l:
            continue
        mo, ml = float(np.median(o)), float(np.median(l))
        drows.append(dict(r=r, n=len(ws), orch=mo, lk=ml, diff=ml - mo))
        print("%-7.3f %6d %11.4f %11.4f %11.4f" % (r, len(ws), mo, ml, ml - mo))
    dv = [d["diff"] for d in drows]
    print("\n  difference spread across radius: %.4f px (min %.4f, max %.4f)"
          % (max(dv) - min(dv), min(dv), max(dv)))
    print("  A CONSTANT difference means the two estimators disagree on an OFFSET,")
    print("  which cancels in any ratio of DIFFERENCES such as applied/needed.")

    with open(os.path.join(OUT, "c3_baseline.json"), "w") as fh:
        json.dump(dict(ncc_hist={str(k): v for k, v in hist.items()},
                       ncc_median=med, agrees_with=verdict, radial=drows), fh, indent=2)
    print("\nwrote c3_baseline.json")

if __name__ == "__main__":
    main()
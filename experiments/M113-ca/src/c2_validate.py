"""M113-ca B2 + B6 + the direct cross-check on the REAL displacement.

B2: my estimator on the same Fourier plants ORCH's estimator failed.
B6: the control ORCH does NOT have -- a shift that VARIES ACROSS the window,
    which is what a radial SCALE actually produces, with matched resampling on
    both channels so no sharpness difference is introduced.
X : both estimators on the SAME windows with NO plant at all. If ORCH's reads
    half of mine on real data, the x0.50 transfer is not an artefact of my plant.
"""
import importlib.util, json, os, sys
import numpy as np
from scipy.ndimage import map_coordinates

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lk import lk_shift, fshift2, radial_tangential   # noqa: E402

ORCH = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check"
OUT = r"C:\dev\strehl-out\M113-ca"

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

cs = _load("ca_shift", os.path.join(ORCH, "ca_shift.py"))
TILE, PAD, WIN = 256, 64, 128

def pick_windows(off, W, H, cx, cy, half, r, n_want=40, n_ang=180):
    wins = []
    for k in range(n_ang):
        th = 2.0 * np.pi * k / n_ang
        px, py = cx + r * half * np.cos(th), cy + r * half * np.sin(th)
        x0, y0 = int(round(px - TILE / 2.0)), int(round(py - TILE / 2.0))
        if x0 < 4 or y0 < 4 or x0 + TILE > W - 4 or y0 + TILE > H - 4:
            continue
        g = np.asarray(off[y0 + PAD:y0 + PAD + WIN, x0 + PAD:x0 + PAD + WIN, 1]).astype(np.float32)
        if float(cs.grad_mag(g).mean()) < cs.MIN_EDGE_ENERGY:
            continue
        wins.append((x0, y0))
        if len(wins) >= n_want:
            break
    return wins

def main():
    off, W, H = cs.load_tiff_u16(os.path.join(r"C:\dev\strehl-out\M114-ca-verify\r1", "off.tif"))
    cx, cy = W / 2.0, H / 2.0
    half = float(np.hypot(cx, cy))
    wins = pick_windows(off, W, H, cx, cy, half, 0.50)
    print("r=0.50 ring, %d windows, TILE %d, WIN %d\n" % (len(wins), TILE, WIN))

    tiles = []
    for (x0, y0) in wins:
        tiles.append((np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 0]).astype(np.float64),
                      np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 1]).astype(np.float64)))

    # ---------------- B2 ----------------
    print("=" * 78)
    print("B2  my estimator vs Fourier-planted sub-pixel shifts")
    print("=" * 78)
    print("%-9s %11s %11s %10s %6s" % ("planted", "LK recov", "rel", "err", "n"))
    plants = [0.0, 0.05, 0.10, 0.155, 0.25, 0.35, 0.50, 1.0, 2.0,
              -0.05, -0.10, -0.155, -0.25, -0.50, -1.0, -2.0]
    rows, base = [], None
    for d in [0.0] + [p for p in plants if p != 0.0]:
        got = []
        for (tr, tg) in tiles:
            r_t = fshift2(tr, d, 0.0) if d else tr
            dx, dy, cond = lk_shift(r_t, tg, PAD, WIN)
            if np.isfinite(dx) and cond > 1e-4 and abs(dx) < 6:
                got.append(dx)
        med = float(np.median(got)) if got else float("nan")
        if d == 0.0:
            base = med
        rows.append(dict(planted=d, recov=med, rel=med - base, err=med - base - d, n=len(got)))
        print("%-9.3f %11.4f %11.4f %10.4f %6d" % (d, med, med - base, med - base - d, len(got)))
    fine = [r for r in rows if 0 < abs(r["planted"]) <= 0.5]
    x = np.array([r["planted"] for r in fine]); y = np.array([r["rel"] for r in fine])
    slope = float((x * y).sum() / (x * x).sum()); maxres = float(np.abs(y - x).max())
    b2 = (0.95 <= slope <= 1.05) and maxres <= 0.03
    print("\nB2 bar: slope in [0.95,1.05] and max|resid| <= 0.03 px")
    print("   slope %.4f   max|resid| %.4f px   -> %s" % (slope, maxres, "PASS" if b2 else "FAIL"))

    # ---------------- B6 ----------------
    print("\n" + "=" * 78)
    print("B6  a shift that VARIES across the window (what a radial scale really is)")
    print("=" * 78)
    print("A radial magnification eps gives d(x) = eps*(x - x_centre) + eps*r_c.")
    print("Across a 128 px window at eps = -704.5e-6 that is a 0.090 px ramp.")
    print("Both channels are resampled by the SAME order-5 spline at non-integer")
    print("coordinates, so neither is sharper than the other.\n")
    yy, xx = np.mgrid[0:TILE, 0:TILE].astype(np.float64)
    xc = TILE / 2.0
    print("%-8s %-9s %11s %11s %8s" % ("d0", "ramp k", "LK recov", "err", "n"))
    b6rows = []
    for d0, k in ((0.30, 0.0), (0.30, 704.5e-6), (0.30, 4 * 704.5e-6),
                  (-0.30, 704.5e-6), (0.15, 704.5e-6), (0.0, 704.5e-6)):
        got = []
        for (tr, tg) in tiles:
            sR = d0 + k * (xx - xc) + 0.5
            r_t = map_coordinates(tr, [yy, xx - sR], order=5, mode="reflect")
            g_t = map_coordinates(tg, [yy, xx - 0.5], order=5, mode="reflect")
            dx, dy, cond = lk_shift(r_t, g_t, PAD, WIN)
            if np.isfinite(dx) and cond > 1e-4 and abs(dx) < 6:
                got.append(dx)
        med = float(np.median(got)) if got else float("nan")
        b6rows.append(dict(d0=d0, k=k, recov=med, n=len(got)))
        print("%-8.2f %-9.2e %11.4f %11.4f %8d" % (d0, k, med, med - d0, len(got)))
    errs = [abs(r["recov"] - r["d0"]) for r in b6rows if np.isfinite(r["recov"])]
    b6 = max(errs) <= 0.03
    print("\nB6 bar: recovered within 0.03 px of the window-centre value d0")
    print("   max |err| %.4f px -> %s" % (max(errs), "PASS" if b6 else "FAIL"))
    print("   (a ramp 4x the real one moves the answer by %.4f px)"
          % abs(b6rows[2]["recov"] - b6rows[0]["recov"]))

    # ---------------- X ----------------
    print("\n" + "=" * 78)
    print("X   SAME windows, NO plant: ORCH's estimator vs mine on the real data")
    print("=" * 78)
    orch, mine = [], []
    for (tr, tg) in tiles:
        r_w = tr[PAD:PAD + WIN, PAD:PAD + WIN].astype(np.float32)
        g_w = tg[PAD:PAD + WIN, PAD:PAD + WIN].astype(np.float32)
        dyo, dxo, pk = cs.shift_of(r_w, g_w)
        if pk >= cs.MIN_PEAK and abs(dxo) < cs.MAX_SHIFT:
            orch.append(dxo)
        dx, dy, cond = lk_shift(tr, tg, PAD, WIN)
        if np.isfinite(dx) and cond > 1e-4 and abs(dx) < 6:
            mine.append(dx)
    mo, mm = float(np.median(orch)), float(np.median(mine))
    print("  ORCH phase-correlation median dx : %+.4f px  (n=%d)" % (mo, len(orch)))
    print("  M113 spatial-LK      median dx : %+.4f px  (n=%d)" % (mm, len(mine)))
    print("  ratio mine/ORCH                : %.3f" % (mm / mo if mo else float('nan')))
    print("\n  c1 predicted the true value from ORCH's own integer plants: -0.1474 px")
    print("  LK measured it with no plant at all           : %+.4f px" % mm)

    with open(os.path.join(OUT, "c2_validate.json"), "w") as fh:
        json.dump(dict(b2=rows, b2_slope=slope, b2_maxres=maxres, b2_pass=bool(b2),
                       b6=b6rows, b6_pass=bool(b6),
                       x_orch=mo, x_lk=mm, x_ratio=(mm / mo if mo else None)), fh, indent=2)
    print("\nwrote c2_validate.json")

if __name__ == "__main__":
    main()
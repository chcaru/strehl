"""M113-ca B1: does ORCH's estimator work in the regime it was USED in?

ORCH's positive control plants integer pixel rolls (-2,-1,0,+1,+2) and reports
0.045 px accuracy. But every number in facts 1511-1514 is SUB-PIXEL: needed
0.155 px, applied ~0.22 px, residual 0.047 px, floor 0.033-0.051 px.

At an exact integer shift the phase-correlation peak lands ON a grid point, so
the parabolic sub-pixel fit contributes ~nothing. The control therefore never
exercises the only part of the estimator that produces the reported numbers.

This plants BAND-LIMITED sub-pixel shifts by Fourier phase ramp. A Fourier shift
is an exact, unitary, all-pass translation: it does not blur, so it does not
reintroduce the sharpness confound that killed ca_radial.py. ORCH's shift_of is
imported and called UNMODIFIED.
"""
import importlib.util, json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ORCH = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check"
OUT = r"C:\dev\strehl-out\M113-ca"

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

cs = _load("ca_shift", os.path.join(ORCH, "ca_shift.py"))
load_tiff_u16, grad_mag, shift_of, WIN = cs.load_tiff_u16, cs.grad_mag, cs.shift_of, cs.WIN
MIN_PEAK, MAX_SHIFT = cs.MIN_PEAK, cs.MAX_SHIFT

TILE = 256  # Fourier-shift this, crop central WIN, so wraparound never enters.

def fshift_x(t, d):
    """Shift content of t by +d px in x. new[x] = old[x-d]."""
    H, W = t.shape
    k = np.fft.rfftfreq(W)          # cycles per sample
    ph = np.exp(-2j * np.pi * k * d)
    return np.fft.irfft2(np.fft.rfft2(t) * ph[None, :], s=(H, W))

def fshift_sanity():
    """A Fourier shift by an INTEGER must equal np.roll. Guards the sign."""
    rng = np.random.default_rng(0)
    a = rng.normal(size=(64, 64))
    a = a - a.mean()
    for d in (1, 2, -3):
        got = fshift_x(a, d)
        want = np.roll(a, d, axis=1)
        err = float(np.abs(got - want).max())
        print("  fourier-shift vs np.roll, d=%+d : max err %.3e  %s"
              % (d, err, "OK" if err < 1e-9 else "MISMATCH"))
        if err >= 1e-9:
            raise SystemExit("Fourier shift sign/scale is wrong -- refusing to continue")

def main():
    off, W, H = load_tiff_u16(os.path.join(r"C:\dev\strehl-out\M114-ca-verify\r1", "off.tif"))
    cx, cy = W / 2.0, H / 2.0
    half = float(np.hypot(cx, cy))
    print("image %dx%d  half_diag %.1f  WIN %d  MIN_PEAK %.3f" % (W, H, half, WIN, MIN_PEAK))
    print("\nFourier-shift sanity (sign convention):")
    fshift_sanity()

    # Windows on the r=0.50 ring, same selection rule as ORCH (edge energy on OFF green).
    wins = []
    for k in range(180):
        th = 2.0 * np.pi * k / 180
        px, py = cx + 0.50 * half * np.cos(th), cy + 0.50 * half * np.sin(th)
        x0, y0 = int(round(px - TILE / 2.0)), int(round(py - TILE / 2.0))
        if x0 < 4 or y0 < 4 or x0 + TILE > W - 4 or y0 + TILE > H - 4:
            continue
        g = np.asarray(off[y0 + 64:y0 + 64 + WIN, x0 + 64:x0 + 64 + WIN, 1]).astype(np.float32)
        if float(grad_mag(g).mean()) < cs.MIN_EDGE_ENERGY:
            continue
        wins.append((x0, y0))
        if len(wins) >= 40:
            break
    print("\n%d windows on the r=0.50 ring (TILE %d, measured on central %d)"
          % (len(wins), TILE, WIN))

    plants = [0.0, 0.05, 0.10, 0.155, 0.25, 0.35, 0.50, 0.75, 1.0, 1.5, 2.0,
              -0.05, -0.10, -0.155, -0.25, -0.50, -1.0, -2.0]
    rows = []
    print("\n%-10s %12s %12s %10s %6s" % ("planted", "recovered", "delta-from-0", "err", "n"))
    base = None
    for d in [0.0] + [p for p in plants if p != 0.0]:
        got = []
        for (x0, y0) in wins:
            tile_r = np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 0]).astype(np.float64)
            sh = fshift_x(tile_r, d) if d != 0.0 else tile_r
            r_w = sh[64:64 + WIN, 64:64 + WIN].astype(np.float32)
            g_w = np.asarray(off[y0 + 64:y0 + 64 + WIN, x0 + 64:x0 + 64 + WIN, 1]).astype(np.float32)
            dy, dx, pk = shift_of(r_w, g_w)
            if pk < MIN_PEAK or abs(dx) > MAX_SHIFT:
                continue
            got.append(dx)
        med = float(np.median(got)) if got else float("nan")
        if d == 0.0:
            base = med
        rel = med - base
        rows.append(dict(planted=d, recovered=med, relative=rel, err=rel - d, n=len(got)))
        print("%-10.3f %12.4f %12.4f %10.4f %6d" % (d, med, rel, rel - d, len(got)))

    fine = [r for r in rows if abs(r["planted"]) <= 0.5 and r["planted"] != 0.0]
    x = np.array([r["planted"] for r in fine])
    y = np.array([r["relative"] for r in fine])
    slope = float((x * y).sum() / (x * x).sum())
    maxres = float(np.abs(y - x).max())
    coarse = [r for r in rows if abs(r["planted"]) >= 1.0]
    xc = np.array([r["planted"] for r in coarse]); yc = np.array([r["relative"] for r in coarse])
    slope_c = float((xc * yc).sum() / (xc * xc).sum())

    print("\n" + "=" * 74)
    print("B1 PASS BAR (pre-registered): slope in [0.90,1.10] AND max|resid| <= 0.05 px")
    print("  slope over |d| <= 0.5 px  : %.4f" % slope)
    print("  max |residual| there      : %.4f px" % maxres)
    print("  slope over |d| >= 1.0 px  : %.4f   <- the regime ORCH's control tested"
          % slope_c)
    ok = (0.90 <= slope <= 1.10) and maxres <= 0.05
    print("  RESULT: %s" % ("PASS" if ok else "FAIL"))
    print("=" * 74)
    with open(os.path.join(OUT, "c1_subpixel.json"), "w") as fh:
        json.dump(dict(rows=rows, slope_fine=slope, slope_coarse=slope_c,
                       maxres_fine=maxres, passed=bool(ok)), fh, indent=2)
    print("wrote c1_subpixel.json")

if __name__ == "__main__":
    main()
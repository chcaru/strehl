"""M113-ca: re-derive the lateral-CA gain by fitting the PHYSICS, not a ring median.

WHY NOT ORCH's RING MEDIAN. Lateral CA is a radial magnification eps. The
observable is a displacement field

    d(p) = t + eps * (p - c)

with t a constant inter-channel translation. optics.rs already says t is real and
unattributable -- CFA co-siting puts the red site half a quad from the greens,
which is ~1.0 OUTPUT px per axis -- and M107's own fit carries
translation = (0.6294, -0.4240) plane px for exactly this reason.

ORCH's estimator projects d onto the radial direction and takes a median over a
ring. That kills a constant t only if the ring is sampled UNIFORMLY in angle. It
is not: windows are dropped for low edge energy, and at r >= 0.83 much of the
ring falls outside a 3:2 frame, so the survivors cluster near the left and right
edges where cos(theta) is largest and t leaks straight into the radial number.

This fits t and eps JOINTLY over windows spanning the whole frame, so no
constant translation -- physical or instrumental -- can reach eps. eps is also
the quantity the shipped coefficient IS, so it can be compared to eps_r directly.
"""
import importlib.util, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lk import lk_shift, fshift2   # noqa: E402

ORCH = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check"
OUT = r"C:\dev\strehl-out\M113-ca"
R1 = r"C:\dev\strehl-out\M114-ca-verify\r1"
EPS_R = -704.5e-6            # optics.rs A7C2_FE100GM_2XTC_X4CPL

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

cs = _load("ca_shift", os.path.join(ORCH, "ca_shift.py"))
TILE, PAD, WIN, STEP = 256, 64, 128, 200

def grid(img, W, H):
    ws = []
    for y0 in range(4, H - TILE - 4, STEP):
        for x0 in range(4, W - TILE - 4, STEP):
            g = np.asarray(img[y0 + PAD:y0 + PAD + WIN, x0 + PAD:x0 + PAD + WIN, 1]).astype(np.float32)
            if float(cs.grad_mag(g).mean()) < cs.MIN_EDGE_ENERGY:
                continue
            ws.append((x0, y0))
    return ws

def measure(img, ws, which, plant_eps=0.0, cx=0.0, cy=0.0):
    """Displacement of R vs G at each window centre. which in {'lk','orch'}."""
    out = []
    for (x0, y0) in ws:
        wx, wy = x0 + TILE / 2.0, y0 + TILE / 2.0
        tr = np.asarray(img[y0:y0 + TILE, x0:x0 + TILE, 0]).astype(np.float64)
        tg = np.asarray(img[y0:y0 + TILE, x0:x0 + TILE, 1]).astype(np.float64)
        if plant_eps:
            tr = fshift2(tr, plant_eps * (wx - cx), plant_eps * (wy - cy))
        if which == "lk":
            sx, sy, cond = lk_shift(tr, tg, PAD, WIN)
            if not np.isfinite(sx) or cond <= 1e-4 or abs(sx) > 6 or abs(sy) > 6:
                continue
        else:
            dyo, dxo, pk = cs.shift_of(tr[PAD:PAD + WIN, PAD:PAD + WIN].astype(np.float32),
                                       tg[PAD:PAD + WIN, PAD:PAD + WIN].astype(np.float32))
            if pk < cs.MIN_PEAK or abs(dxo) > cs.MAX_SHIFT or abs(dyo) > cs.MAX_SHIFT:
                continue
            sx, sy = dxo, dyo
        out.append((wx, wy, sx, sy))
    return np.array(out) if out else np.zeros((0, 4))

def fit_eps(m, cx, cy, trim=0.2):
    """Robust least squares for d = t + eps*(p - c). Returns (eps, tx, ty, n, rms)."""
    if len(m) < 10:
        return (float("nan"),) * 3 + (0, float("nan"))
    wx, wy, sx, sy = m[:, 0], m[:, 1], m[:, 2], m[:, 3]
    keep = np.ones(len(m), dtype=bool)
    eps = tx = ty = 0.0
    for _ in range(6):
        X = np.zeros((2 * int(keep.sum()), 3))
        Y = np.concatenate([sx[keep], sy[keep]])
        n = int(keep.sum())
        X[:n, 0] = wx[keep] - cx; X[:n, 1] = 1.0
        X[n:, 0] = wy[keep] - cy; X[n:, 2] = 1.0
        coef, *_ = np.linalg.lstsq(X, Y, rcond=None)
        eps, tx, ty = coef
        rx = sx - (tx + eps * (wx - cx)); ry = sy - (ty + eps * (wy - cy))
        res = np.hypot(rx, ry)
        thr = np.quantile(res, 1.0 - trim)
        newkeep = res <= thr
        if newkeep.sum() < 10 or np.array_equal(newkeep, keep):
            keep = newkeep if newkeep.sum() >= 10 else keep
            break
        keep = newkeep
    rx = sx[keep] - (tx + eps * (wx[keep] - cx)); ry = sy[keep] - (ty + eps * (wy[keep] - cy))
    rms = float(np.sqrt((rx ** 2 + ry ** 2).mean()))
    return float(eps), float(tx), float(ty), int(keep.sum()), rms

def main():
    off, W, H = cs.load_tiff_u16(os.path.join(R1, "off.tif"))
    on, _, _ = cs.load_tiff_u16(os.path.join(R1, "on.tif"))
    cx, cy = W / 2.0, H / 2.0
    ws = grid(off, W, H)
    print("grid windows passing ORCH's edge-energy rule: %d  (step %d, TILE %d, WIN %d)"
          % (len(ws), STEP, TILE, WIN))
    print("optics.rs eps_r = %+.6g   (corner displacement %.3f output px)\n"
          % (EPS_R, abs(EPS_R) * float(np.hypot(cx, cy))))

    res = {}
    print("=" * 92)
    print("%-6s %-6s %12s %12s %10s %10s %7s %8s"
          % ("est", "arm", "eps", "eps ppm", "tx px", "ty px", "n", "rms px"))
    print("=" * 92)
    for which in ("lk", "orch"):
        for arm, img in (("off", off), ("on", on)):
            m = measure(img, ws, which, cx=cx, cy=cy)
            eps, tx, ty, n, rms = fit_eps(m, cx, cy)
            res[(which, arm)] = dict(eps=eps, tx=tx, ty=ty, n=n, rms=rms)
            print("%-6s %-6s %12.6g %12.1f %10.4f %10.4f %7d %8.4f"
                  % (which, arm, eps, eps * 1e6, tx, ty, n, rms))

    print("=" * 92)
    print("\nGAIN  (needed = -eps_off ; applied = eps_on - eps_off ; gain = applied/needed)")
    print("%-8s %14s %14s %10s %14s" % ("est", "needed ppm", "applied ppm", "gain", "vs eps_r"))
    out = {}
    for which in ("lk", "orch"):
        eo, en = res[(which, "off")]["eps"], res[(which, "on")]["eps"]
        needed, applied = -eo, en - eo
        gain = applied / needed if needed else float("nan")
        out[which] = dict(eps_off=eo, eps_on=en, needed=needed, applied=applied, gain=gain,
                          applied_over_epsr=applied / (-EPS_R))
        print("%-8s %14.1f %14.1f %10.4f %14.4f"
              % (which, needed * 1e6, applied * 1e6, gain, applied / (-EPS_R)))
    print("\n'vs eps_r' is B8: the correction should APPLY exactly -eps_r = %+.1f ppm."
          % (-EPS_R * 1e6))

    # ---------------- positive control on the global fit ----------------
    print("\n" + "=" * 92)
    print("POSITIVE CONTROL: plant a known radial magnification into red and refit")
    print("=" * 92)
    print("%-10s %14s %14s %12s" % ("planted ppm", "eps_off ppm", "recovered ppm", "err ppm"))
    base = res[("lk", "off")]["eps"]
    ctl = []
    for pe in (500e-6, -500e-6, 1000e-6):
        m = measure(off, ws, "lk", plant_eps=pe, cx=cx, cy=cy)
        eps, tx, ty, n, rms = fit_eps(m, cx, cy)
        ctl.append(dict(planted=pe, recovered=eps, err=(eps - base) - pe))
        print("%-10.1f %14.1f %14.1f %12.2f"
              % (pe * 1e6, base * 1e6, eps * 1e6, ((eps - base) - pe) * 1e6))
    mx = max(abs(c["err"]) for c in ctl)
    print("\nBAR: recovered - baseline must equal planted to within 50 ppm.")
    print("RESULT: max |err| = %.2f ppm -> %s" % (mx * 1e6, "PASS" if mx <= 50e-6 else "FAIL"))

    with open(os.path.join(OUT, "c4_globalfit.json"), "w") as fh:
        json.dump(dict(fits={"%s_%s" % k: v for k, v in res.items()},
                       gain=out, control=ctl, eps_r=EPS_R, n_windows=len(ws)), fh, indent=2)
    print("\nwrote c4_globalfit.json")

if __name__ == "__main__":
    main()
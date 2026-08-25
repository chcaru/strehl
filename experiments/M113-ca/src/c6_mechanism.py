"""M113-ca: why does ORCH's estimator track a PLANTED eps at 91 % yet read only
6 % of the real one? Those two facts are only compatible if the estimator is
locked onto something that MOVES WITH THE PLANT but is NOT the scene displacement.

HYPOTHESIS. Demosaicing reconstructs R and G at the same output sites from the
same neighbourhood, so their high-frequency NOISE is correlated AT ZERO LAG.
Phase correlation whitens (X/|X|), which weights every frequency equally and
therefore maximally amplifies exactly that shared high-frequency noise. The
result is a spurious zero-lag peak that outranks the true displaced peak.

WHY THE CONTROL CANNOT SEE THIS. Planting a shift translates the whole red
channel INCLUDING its noise, so the spurious zero-lag peak translates with it.
An estimator locked on shared noise tracks a plant perfectly while never having
locked onto the scene at all.

TEST. Low-pass both channels before correlating. Blurring suppresses the shared
high-frequency noise and leaves the scene structure. If the lock is on noise,
eps must swing from ~-41 ppm toward the ~-700 ppm the other three cells report.
If the lock is genuine, blurring cannot manufacture a signal that is not there.
"""
import importlib.util, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lk import lk_shift   # noqa: E402
from c4_globalfit import grid, fit_eps, TILE, PAD, WIN, EPS_R   # noqa: E402

ORCH = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check"
OUT = r"C:\dev\strehl-out\M113-ca"
R1 = r"C:\dev\strehl-out\M114-ca-verify\r1"

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
cs = _load("ca_shift", os.path.join(ORCH, "ca_shift.py"))

def blur(t, sigma):
    if sigma <= 0:
        return t
    H, W = t.shape
    ky = np.fft.fftfreq(H)[:, None]; kx = np.fft.rfftfreq(W)[None, :]
    g = np.exp(-2.0 * (np.pi * sigma) ** 2 * (kx ** 2 + ky ** 2))
    return np.fft.irfft2(np.fft.rfft2(t) * g, s=(H, W))

def main():
    off, W, H = cs.load_tiff_u16(os.path.join(R1, "off.tif"))
    cx, cy = W / 2.0, H / 2.0
    half = float(np.hypot(cx, cy))
    ws = grid(off, W, H)

    # ---------- 1. radial profile: where do the two estimators diverge? ----------
    print("=" * 88)
    print("1. MEDIAN RADIAL DISPLACEMENT vs RADIUS -- the field each estimator sees")
    print("=" * 88)
    print("A pure radial magnification eps gives radial displacement eps*R, i.e. a")
    print("STRAIGHT LINE through the origin. eps_r = -704.5 ppm predicts the last column.\n")
    rows = []
    for (x0, y0) in ws:
        wx, wy = x0 + TILE / 2.0, y0 + TILE / 2.0
        tr = np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 0]).astype(np.float64)
        tg = np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 1]).astype(np.float64)
        rx, ry = wx - cx, wy - cy
        rr = float(np.hypot(rx, ry))
        if rr < 1e-6:
            continue
        ux, uy = rx / rr, ry / rr
        dyo, dxo, pk = cs.shift_of(tr[PAD:PAD + WIN, PAD:PAD + WIN].astype(np.float32),
                                   tg[PAD:PAD + WIN, PAD:PAD + WIN].astype(np.float32))
        ao = dxo * ux + dyo * uy if (pk >= cs.MIN_PEAK and abs(dxo) < cs.MAX_SHIFT) else np.nan
        sx, sy, cond = lk_shift(tr, tg, PAD, WIN)
        bo = sx * ux + sy * uy if (np.isfinite(sx) and cond > 1e-4 and abs(sx) < 6) else np.nan
        rows.append((rr / half, ao, bo))
    rows = np.array(rows)
    print("%-10s %7s %14s %14s %14s" % ("r", "n", "ORCH radial", "LK radial", "eps_r says"))
    prof = []
    for lo, hi in ((0.0, 0.15), (0.15, 0.3), (0.3, 0.45), (0.45, 0.6),
                   (0.6, 0.75), (0.75, 0.9), (0.9, 1.05)):
        m = (rows[:, 0] >= lo) & (rows[:, 0] < hi)
        if m.sum() < 5:
            continue
        rmid = float(np.median(rows[m, 0]))
        a = float(np.nanmedian(rows[m, 1])); b = float(np.nanmedian(rows[m, 2]))
        pred = EPS_R * rmid * half
        prof.append(dict(r=rmid, n=int(m.sum()), orch=a, lk=b, pred=pred))
        print("%-10.3f %7d %14.4f %14.4f %14.4f" % (rmid, int(m.sum()), a, b, pred))

    # ---------- 2. the blur test ----------
    print("\n" + "=" * 88)
    print("2. BLUR TEST -- suppress the shared high-frequency noise, re-run ORCH's solver")
    print("=" * 88)
    print("%-10s %14s %12s %10s" % ("sigma px", "ORCH eps ppm", "n", "rms px"))
    blurs = []
    for sigma in (0.0, 0.5, 1.0, 1.5, 2.0, 3.0):
        out = []
        for (x0, y0) in ws:
            wx, wy = x0 + TILE / 2.0, y0 + TILE / 2.0
            tr = np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 0]).astype(np.float64)
            tg = np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 1]).astype(np.float64)
            if sigma:
                tr, tg = blur(tr, sigma), blur(tg, sigma)
            dyo, dxo, pk = cs.shift_of(tr[PAD:PAD + WIN, PAD:PAD + WIN].astype(np.float32),
                                       tg[PAD:PAD + WIN, PAD:PAD + WIN].astype(np.float32))
            if pk < cs.MIN_PEAK or abs(dxo) > cs.MAX_SHIFT or abs(dyo) > cs.MAX_SHIFT:
                continue
            out.append((wx, wy, dxo, dyo))
        m = np.array(out) if out else np.zeros((0, 4))
        eps, tx, ty, n, rms = fit_eps(m, cx, cy)
        blurs.append(dict(sigma=sigma, eps=eps, n=n, rms=rms))
        print("%-10.1f %14.1f %12d %10.4f" % (sigma, eps * 1e6, n, rms))
    print("\nIf blurring MANUFACTURES a large eps that was absent at sigma=0, the")
    print("sigma=0 reading was a lock on shared high-frequency noise, not on the scene.")

    # ---------- 3. look at the pixels ----------
    print("\n" + "=" * 88)
    print("3. DIRECT EDGE PROFILES near the corner -- no registration estimator at all")
    print("=" * 88)
    print("If eps = -704.5 ppm the R and G edges at r ~ 0.9 are ~2.7 output px apart.")
    print("Measured as the centroid of |d/dt| of each channel's mean edge profile,")
    print("projected on the radial direction. A smooth colour cast cannot move this.\n")
    best = None
    for (x0, y0) in ws:
        wx, wy = x0 + TILE / 2.0, y0 + TILE / 2.0
        rr = float(np.hypot(wx - cx, wy - cy)) / half
        if rr < 0.85:
            continue
        g = np.asarray(off[y0 + PAD:y0 + PAD + WIN, x0 + PAD:x0 + PAD + WIN, 1]).astype(np.float64)
        e = float(cs.grad_mag(g.astype(np.float32)).mean())
        if best is None or e > best[0]:
            best = (e, x0, y0, wx, wy, rr)
    _, x0, y0, wx, wy, rr = best
    ux, uy = (wx - cx) / (half * rr), (wy - cy) / (half * rr)
    tr = np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 0]).astype(np.float64)
    tg = np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 1]).astype(np.float64)
    # 1-D profiles along the radial direction through the tile centre, averaged
    # over 41 parallel lines to beat down noise.
    from scipy.ndimage import map_coordinates
    ts = np.arange(-40, 41, 0.25)
    accR, accG = np.zeros_like(ts), np.zeros_like(ts)
    for off_l in range(-20, 21):
        px = TILE / 2.0 + ts * ux - off_l * uy
        py = TILE / 2.0 + ts * uy + off_l * ux
        accR += map_coordinates(tr, [py, px], order=3, mode="reflect")
        accG += map_coordinates(tg, [py, px], order=3, mode="reflect")
    accR /= 41.0; accG /= 41.0
    dR = np.abs(np.gradient(accR)); dG = np.abs(np.gradient(accG))
    cR = float((ts * dR).sum() / dR.sum()); cG = float((ts * dG).sum() / dG.sum())
    print("  window at r = %.3f  (centre %.0f,%.0f)" % (rr, wx, wy))
    print("  radial centroid of |dR/dt| : %+.4f px" % cR)
    print("  radial centroid of |dG/dt| : %+.4f px" % cG)
    print("  R minus G                  : %+.4f px" % (cR - cG))
    print("  eps_r = -704.5 ppm predicts: %+.4f px" % (EPS_R * rr * half))

    with open(os.path.join(OUT, "c6_mechanism.json"), "w") as fh:
        json.dump(dict(profile=prof, blur=blurs,
                       edge=dict(r=rr, cR=cR, cG=cG, diff=cR - cG,
                                 pred=EPS_R * rr * half)), fh, indent=2)
    print("\nwrote c6_mechanism.json")

if __name__ == "__main__":
    main()
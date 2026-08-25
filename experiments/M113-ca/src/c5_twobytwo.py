"""M113-ca: LK on intensity says eps_off = -718.7 ppm. ORCH's phase correlation on
gradient magnitude says -40.8 ppm. A 17.6x disagreement. Two things differ at once:

                      SOLVER: phase correlation   |   SOLVER: spatial LK
   INPUT: grad-mag        ORCH  (-40.8 ppm)       |        cell C
   INPUT: intensity           cell B              |   M113  (-718.7 ppm)

Filling cells B and C says which factor is responsible. That is the whole point:
a difference attributed to the wrong factor leads to the wrong fix.

Cell D adds a fourth input -- HIGH-PASS intensity -- because the leading reason an
intensity-domain LK could be WRONG is that a smoothly varying R/G ratio across the
frame (subject in the centre, background at the edges) projects onto the gradient
columns and masquerades as a radial displacement. High-passing removes exactly
that and leaves real edge misregistration untouched.
"""
import importlib.util, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lk import lk_shift, fshift2   # noqa: E402
from c4_globalfit import grid, fit_eps, TILE, PAD, WIN, EPS_R   # noqa: E402

ORCH = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check"
OUT = r"C:\dev\strehl-out\M113-ca"
R1 = r"C:\dev\strehl-out\M114-ca-verify\r1"

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

cs = _load("ca_shift", os.path.join(ORCH, "ca_shift.py"))

def highpass(t, sigma=6.0):
    """Subtract a Gaussian blur, done in the Fourier domain so it is exact and
    introduces no shift of its own (a symmetric kernel has zero phase)."""
    H, W = t.shape
    ky = np.fft.fftfreq(H)[:, None]; kx = np.fft.rfftfreq(W)[None, :]
    g = np.exp(-2.0 * (np.pi * sigma) ** 2 * (kx ** 2 + ky ** 2))
    F = np.fft.rfft2(t)
    return np.fft.irfft2(F * (1.0 - g), s=(H, W))

def measure_cell(img, ws, cell, cx, cy):
    out = []
    for (x0, y0) in ws:
        wx, wy = x0 + TILE / 2.0, y0 + TILE / 2.0
        tr = np.asarray(img[y0:y0 + TILE, x0:x0 + TILE, 0]).astype(np.float64)
        tg = np.asarray(img[y0:y0 + TILE, x0:x0 + TILE, 1]).astype(np.float64)
        if cell == "A_orch_gradmag_pc":
            a = cs.grad_mag(tr.astype(np.float32))[PAD:PAD + WIN, PAD:PAD + WIN]
            b = cs.grad_mag(tg.astype(np.float32))[PAD:PAD + WIN, PAD:PAD + WIN]
            dyo, dxo, pk = cs.shift_of(tr[PAD:PAD + WIN, PAD:PAD + WIN].astype(np.float32),
                                       tg[PAD:PAD + WIN, PAD:PAD + WIN].astype(np.float32))
            if pk < cs.MIN_PEAK or abs(dxo) > cs.MAX_SHIFT or abs(dyo) > cs.MAX_SHIFT:
                continue
            sx, sy = dxo, dyo
        else:
            if cell == "C_gradmag_lk":
                tr2 = cs.grad_mag(tr.astype(np.float32)).astype(np.float64)
                tg2 = cs.grad_mag(tg.astype(np.float32)).astype(np.float64)
            elif cell == "D_highpass_lk":
                tr2, tg2 = highpass(tr), highpass(tg)
            else:
                tr2, tg2 = tr, tg
            sx, sy, cond = lk_shift(tr2, tg2, PAD, WIN)
            if not np.isfinite(sx) or cond <= 1e-4 or abs(sx) > 6 or abs(sy) > 6:
                continue
        out.append((wx, wy, sx, sy))
    return np.array(out) if out else np.zeros((0, 4))

def main():
    off, W, H = cs.load_tiff_u16(os.path.join(R1, "off.tif"))
    on, _, _ = cs.load_tiff_u16(os.path.join(R1, "on.tif"))
    cx, cy = W / 2.0, H / 2.0
    ws = grid(off, W, H)
    print("windows: %d\n" % len(ws))

    cells = ["A_orch_gradmag_pc", "B_intensity_lk", "C_gradmag_lk", "D_highpass_lk"]
    print("=" * 96)
    print("%-20s %-5s %12s %10s %10s %7s %8s"
          % ("cell", "arm", "eps ppm", "tx px", "ty px", "n", "rms px"))
    print("=" * 96)
    res = {}
    for cell in cells:
        for arm, img in (("off", off), ("on", on)):
            m = measure_cell(img, ws, cell, cx, cy)
            eps, tx, ty, n, rms = fit_eps(m, cx, cy)
            res["%s|%s" % (cell, arm)] = dict(eps=eps, tx=tx, ty=ty, n=n, rms=rms)
            print("%-20s %-5s %12.1f %10.4f %10.4f %7d %8.4f"
                  % (cell, arm, eps * 1e6, tx, ty, n, rms))
        print("-" * 96)

    print("\n%-20s %12s %12s %9s %12s"
          % ("cell", "needed ppm", "applied ppm", "gain", "applied/eps_r"))
    gains = {}
    for cell in cells:
        eo = res["%s|off" % cell]["eps"]; en = res["%s|on" % cell]["eps"]
        needed, applied = -eo, en - eo
        g = applied / needed if needed else float("nan")
        gains[cell] = dict(needed=needed, applied=applied, gain=g,
                           applied_over_epsr=applied / (-EPS_R))
        print("%-20s %12.1f %12.1f %9.4f %12.4f"
              % (cell, needed * 1e6, applied * 1e6, g, applied / (-EPS_R)))

    print("\nshipped eps_r = %+.1f ppm; a faithful correction APPLIES %+.1f ppm"
          % (EPS_R * 1e6, -EPS_R * 1e6))

    # ---- positive control: the SAME plant through every cell ----
    print("\n" + "=" * 96)
    print("CONTROL: plant +500 ppm of radial magnification and re-fit in every cell.")
    print("A cell that cannot see a planted eps cannot see a real one either.")
    print("=" * 96)
    print("%-20s %14s %14s %12s %8s" % ("cell", "baseline ppm", "planted+base", "recovered", "err"))
    ctl = {}
    for cell in cells:
        base = res["%s|off" % cell]["eps"]
        out = []
        for (x0, y0) in ws:
            wx, wy = x0 + TILE / 2.0, y0 + TILE / 2.0
            tr = np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 0]).astype(np.float64)
            tg = np.asarray(off[y0:y0 + TILE, x0:x0 + TILE, 1]).astype(np.float64)
            tr = fshift2(tr, 500e-6 * (wx - cx), 500e-6 * (wy - cy))
            if cell == "A_orch_gradmag_pc":
                dyo, dxo, pk = cs.shift_of(tr[PAD:PAD + WIN, PAD:PAD + WIN].astype(np.float32),
                                           tg[PAD:PAD + WIN, PAD:PAD + WIN].astype(np.float32))
                if pk < cs.MIN_PEAK or abs(dxo) > cs.MAX_SHIFT:
                    continue
                sx, sy = dxo, dyo
            else:
                if cell == "C_gradmag_lk":
                    tr2 = cs.grad_mag(tr.astype(np.float32)).astype(np.float64)
                    tg2 = cs.grad_mag(tg.astype(np.float32)).astype(np.float64)
                elif cell == "D_highpass_lk":
                    tr2, tg2 = highpass(tr), highpass(tg)
                else:
                    tr2, tg2 = tr, tg
                sx, sy, cond = lk_shift(tr2, tg2, PAD, WIN)
                if not np.isfinite(sx) or cond <= 1e-4 or abs(sx) > 6:
                    continue
            out.append((wx, wy, sx, sy))
        m = np.array(out) if out else np.zeros((0, 4))
        eps, tx, ty, n, rms = fit_eps(m, cx, cy)
        err = (eps - base) - 500e-6
        ctl[cell] = dict(base=base, recovered=eps, err=err)
        print("%-20s %14.1f %14.1f %12.1f %8.1f"
              % (cell, base * 1e6, (base + 500e-6) * 1e6, eps * 1e6, err * 1e6))

    with open(os.path.join(OUT, "c5_twobytwo.json"), "w") as fh:
        json.dump(dict(fits=res, gains=gains, control=ctl), fh, indent=2)
    print("\nwrote c5_twobytwo.json")

if __name__ == "__main__":
    main()
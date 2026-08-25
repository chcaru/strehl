"""M113-ca B5/B7: is the SHAPE radial-linear, and is fact 1501's refutation supported?

Fact 1501 said the correction over-extrapolates past its fit support at
r = 0.788. ORCH declared it refuted because one ring at r = 0.83 showed the same
gain as the inside-support rings. That is n = 1 ring, 5.3 % beyond support, on a
contaminated measurement space, with the r = 0.93 ring dropped by a noise gate.

METHOD. Take the global robust fit's constant translation t once, on the whole
frame, then per annulus form the LOCAL scale

    eps(r) = median over windows of  [ (d - t) . rhat ] / |p - c|

so each ring is a direct estimate of the magnification at that radius with the
sensor's constant co-siting translation already removed. A pure radial scale --
which is what the shipped model IS -- predicts a flat eps(r). Curvature means
the shape is wrong, and that is what fact 1501 was about.

Run on the BINNED space (B10: chain transfer 0.94-0.98, the only space with no
cross-channel operator) and on BOTH stacks.

B7 is the innermost ring: eps is multiplied by r there, so a real scale must
produce a vanishing RADIAL DISPLACEMENT at the centre even though eps itself
need not vanish. The null is on the displacement, not on eps.
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c4_globalfit as c4g                                   # noqa: E402
from c4_globalfit import cs, measure, fit_eps, EPS_R          # noqa: E402

LIN = r"C:\dev\strehl-out\M113-ca\lin"
OUT = r"C:\dev\strehl-out\M113-ca"
SUPPORT = 0.788        # optics.rs support_r_max
EDGES = [0.0, 0.15, 0.30, 0.45, 0.60, 0.72, 0.85, 1.00]

def rings(m, cx, cy, tx, ty, half_diag):
    dx = m[:, 2] - tx
    dy = m[:, 3] - ty
    px = m[:, 0] - cx
    py = m[:, 1] - cy
    rad = np.hypot(px, py)
    ok = rad > 1e-6
    rhx, rhy = px / np.where(ok, rad, 1), py / np.where(ok, rad, 1)
    d_r = dx * rhx + dy * rhy
    d_t = -dx * rhy + dy * rhx          # tangential = the estimator's own noise floor
    rn = rad / half_diag
    rows = []
    for lo, hi in zip(EDGES[:-1], EDGES[1:]):
        s = ok & (rn >= lo) & (rn < hi)
        if s.sum() < 6:
            rows.append(dict(lo=lo, hi=hi, n=int(s.sum()), eps=float("nan"),
                             d_r=float("nan"), d_t=float("nan"), rbar=float("nan")))
            continue
        eps = np.median(d_r[s] / rad[s])
        # bootstrap the ring median so "different" can be distinguished from "noisy"
        rng = np.random.default_rng(7)
        idx = np.flatnonzero(s)
        bs = [np.median((d_r[idx[rng.integers(0, len(idx), len(idx))]]
                         / rad[idx[rng.integers(0, len(idx), len(idx))]])) for _ in range(400)]
        rows.append(dict(lo=lo, hi=hi, n=int(s.sum()), eps=float(eps),
                         eps_sd=float(np.std(bs)),
                         d_r=float(np.median(d_r[s])), d_t=float(np.median(np.abs(d_t[s]))),
                         rbar=float(np.median(rn[s]))))
    return rows

def main():
    c4g.STEP = 100
    res = {}
    for name in ("bee-3-cpl", "couch-fibers-cpl"):
        off, W, H = cs.load_tiff_u16(os.path.join(LIN, "%s-binned-off.tif" % name))
        on, _, _ = cs.load_tiff_u16(os.path.join(LIN, "%s-binned-on.tif" % name))
        cx, cy = W / 2.0, H / 2.0
        hd = float(np.hypot(cx, cy))
        ws = c4g.grid(off, W, H)
        cell = {}
        for arm, img in (("off", off), ("on", on)):
            m = measure(img, ws, "lk", cx=cx, cy=cy)
            eps, tx, ty, n, rms = fit_eps(m, cx, cy)
            cell[arm] = dict(rows=rings(m, cx, cy, tx, ty, hd), eps_global=eps, tx=tx, ty=ty)
        res[name] = cell
        print("\n" + "=" * 100)
        print("%s  BINNED  half-diagonal %.1f px   support_r_max = %.3f" % (name, hd, SUPPORT))
        print("=" * 100)
        print("%-13s %5s %7s %12s %9s %12s %11s" %
              ("ring r", "n", "r_bar", "eps_off ppm", "+/- sd", "eps_on ppm", "|d_tan| px"))
        for a, b in zip(cell["off"]["rows"], cell["on"]["rows"]):
            flag = "" if a["hi"] <= SUPPORT else "  << OUTSIDE SUPPORT"
            if a["n"] < 6:
                print("%-13s %5d  (too few windows)" % ("%.2f-%.2f" % (a["lo"], a["hi"]), a["n"])); continue
            print("%-13s %5d %7.3f %12.1f %9.1f %12.1f %11.4f%s"
                  % ("%.2f-%.2f" % (a["lo"], a["hi"]), a["n"], a["rbar"],
                     a["eps"] * 1e6, a["eps_sd"] * 1e6, b["eps"] * 1e6, a["d_t"], flag))
        ins = [r for r in cell["off"]["rows"] if r["n"] >= 6 and r["hi"] <= SUPPORT]
        out = [r for r in cell["off"]["rows"] if r["n"] >= 6 and r["hi"] > SUPPORT]
        if ins and out:
            mi = np.mean([r["eps"] for r in ins]); mo = np.mean([r["eps"] for r in out])
            no = sum(r["n"] for r in out)
            print("-" * 100)
            print("  inside support : mean eps = %+.1f ppm over %d rings, %d windows"
                  % (mi * 1e6, len(ins), sum(r["n"] for r in ins)))
            print("  outside support: mean eps = %+.1f ppm over %d rings, %d windows"
                  % (mo * 1e6, len(out), no))
            print("  ratio outside/inside = %.4f" % (mo / mi))
            cell["inside"] = float(mi); cell["outside"] = float(mo); cell["n_outside"] = int(no)
        r0 = cell["off"]["rows"][0]
        if r0["n"] >= 6:
            print("  B7 centre null : median radial displacement in r<%.2f = %+.4f px "
                  "(tangential noise floor %.4f px)" % (r0["hi"], r0["d_r"], r0["d_t"]))
        del off, on
    with open(os.path.join(OUT, "c10_rings.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print("\nwrote c10_rings.json")

if __name__ == "__main__":
    main()
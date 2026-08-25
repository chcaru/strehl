"""M113-spectral S2: needed_R, needed_B, chain transfer and scene colour per stack.

BLUE IS A FREE NULL CONTROL. optics.rs carries `eps_b: None` and documents that
"the blue gather is unchanged too", so the correction is a red-only operation.
Therefore, by construction:

  * applied_B = eps_B(on) - eps_B(off) must be ZERO. Any non-zero value is a leak
    in my estimator or in the pipeline, not a measurement.
  * the GREEN and BLUE planes of the two arms should be byte-identical.

Both are checked before any between-stack number is believed. This control exists
without my having to build it and I did not notice it until I read optics.rs.

needed_B is also a second, independent optical quantity per stack, and the ratio
needed_B/needed_R is bar S4's discriminator: a magnification or alignment change
multiplies both by the same factor and leaves the ratio fixed, whereas a shift in
effective wavelength moves them independently.
"""
import json, os, sys
import numpy as np

CA_SRC = r"C:\dev\blog\death-of-software\projects\strehl\experiments\M113-ca\src"
sys.path.insert(0, CA_SRC)
import c4_globalfit as c4g                       # noqa: E402
from c4_globalfit import cs, fit_eps, EPS_R      # noqa: E402
from lk import lk_shift                          # noqa: E402

ROOT = r"C:\dev\strehl-out\M113-spectral"
ARMS = os.path.join(ROOT, "arms")
CA_LIN = r"C:\dev\strehl-out\M113-ca\lin"
TILE, PAD, WIN = c4g.TILE, c4g.PAD, c4g.WIN

# reference-frame focus distance, metres, from exiftool FocusDistance2
FOCUS = {"bee-1-cpl": 0.2841, "bee-2-cpl": 0.2917, "bee-3-cpl": 0.2917,
         "couch-fibers-cpl": 0.2841, "lavendar-cpl": 0.2841,
         "dry-erase-marker-head-cpl": 0.2841, "leaf-2-cpl": 0.2771,
         "tweezers-cpl": 0.2738}

def paths(name):
    if name in ("bee-3-cpl", "couch-fibers-cpl"):
        return (os.path.join(CA_LIN, "%s-binned-off.tif" % name),
                os.path.join(CA_LIN, "%s-binned-on.tif" % name))
    return (os.path.join(ARMS, "%s-binned-off.tif" % name),
            os.path.join(ARMS, "%s-binned-on.tif" % name))

def measure_ch(img, ws, ch, cx, cy):
    """Displacement of channel `ch` against green at each window centre."""
    out = []
    for (x0, y0) in ws:
        wx, wy = x0 + TILE / 2.0, y0 + TILE / 2.0
        ta = np.asarray(img[y0:y0 + TILE, x0:x0 + TILE, ch]).astype(np.float64)
        tg = np.asarray(img[y0:y0 + TILE, x0:x0 + TILE, 1]).astype(np.float64)
        sx, sy, cond = lk_shift(ta, tg, PAD, WIN)
        if not np.isfinite(sx) or cond <= 1e-4 or abs(sx) > 6 or abs(sy) > 6:
            continue
        out.append((wx, wy, sx, sy))
    return np.array(out) if out else np.zeros((0, 4))

def main():
    c4g.STEP = 100
    names = [n for n in FOCUS if all(os.path.exists(q) for q in paths(n))]
    names.sort(key=lambda n: FOCUS[n])
    print("stacks with both arms rendered: %d of %d" % (len(names), len(FOCUS)))
    res = {}
    for name in names:
        poff, pon = paths(name)
        off, W, H = cs.load_tiff_u16(poff)
        on, W2, H2 = cs.load_tiff_u16(pon)
        assert (W, H) == (W2, H2)
        cx, cy = W / 2.0, H / 2.0
        ws = c4g.grid(off, W, H)
        cell = {"n_windows": len(ws), "W": W, "H": H, "focus_m": FOCUS[name]}

        # --- null control: green and blue planes must be untouched by a red-only fix
        step = 9
        for ci, cn in ((1, "green"), (2, "blue")):
            a = np.asarray(off[::step, ::step, ci]); b = np.asarray(on[::step, ::step, ci])
            cell["plane_identical_%s" % cn] = bool(np.array_equal(a, b))
        a = np.asarray(off[::step, ::step, 0]); b = np.asarray(on[::step, ::step, 0])
        cell["plane_identical_red"] = bool(np.array_equal(a, b))

        for ch, cn in ((0, "R"), (2, "B")):
            for arm, img in (("off", off), ("on", on)):
                m = measure_ch(img, ws, ch, cx, cy)
                eps, tx, ty, n, rms = fit_eps(m, cx, cy)
                cell["eps_%s_%s" % (cn, arm)] = eps
                cell["n_%s_%s" % (cn, arm)] = n
                cell["rms_%s_%s" % (cn, arm)] = rms
            cell["needed_%s" % cn] = -cell["eps_%s_off" % cn]
            cell["applied_%s" % cn] = cell["eps_%s_on" % cn] - cell["eps_%s_off" % cn]
        cell["transfer"] = cell["applied_R"] / (-EPS_R)
        cell["gain"] = cell["applied_R"] / cell["needed_R"] if cell["needed_R"] else float("nan")
        cell["ratio_BR"] = cell["needed_B"] / cell["needed_R"] if cell["needed_R"] else float("nan")

        sub = np.asarray(off[::17, ::17, :]).astype(np.float64).reshape(-1, 3)
        med = np.median(sub, axis=0)
        cell["med_rgb"] = med.tolist()
        cell["RG"] = float(med[0] / med[1]); cell["BG"] = float(med[2] / med[1])
        res[name] = cell
        print("  %-28s done  needed_R=%.1f  transfer=%.3f" % (name, cell["needed_R"] * 1e6, cell["transfer"]), flush=True)
        del off, on

    print("\n" + "=" * 118)
    print("%-28s %6s %9s %9s %9s %8s %8s %7s %7s" %
          ("stack", "focus", "needed_R", "needed_B", "applied_B", "transfer", "ratioB/R", "R/G", "B/G"))
    print("=" * 118)
    for n in names:
        c = res[n]
        print("%-28s %6.4f %9.1f %9.1f %9.2f %8.4f %8.4f %7.4f %7.4f"
              % (n, c["focus_m"], c["needed_R"] * 1e6, c["needed_B"] * 1e6,
                 c["applied_B"] * 1e6, c["transfer"], c["ratio_BR"], c["RG"], c["BG"]))
    print("=" * 118)

    print("\nNULL CONTROLS (red-only correction => green and blue planes untouched)")
    for n in names:
        c = res[n]
        print("  %-28s green_identical=%-5s blue_identical=%-5s red_identical=%-5s applied_B=%+.2f ppm"
              % (n, c["plane_identical_green"], c["plane_identical_blue"],
                 c["plane_identical_red"], c["applied_B"] * 1e6))

    with open(os.path.join(ROOT, "s2_measure.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print("\nwrote s2_measure.json")

if __name__ == "__main__":
    main()
"""M113-ca B4/B9: the gain on the LINEAR camera-native render, and on a SECOND STACK.

TWO THINGS AT ONCE, because they share a loader.

B9 -- MEASUREMENT SPACE. Every number in facts 1511-1514 was measured on M114's
off.tif/on.tif, which were rendered `--srgb --auto-exposure`. `--srgb` applies
the camera colour matrix, and that matrix is NOT diagonal. Computed from
color.rs's own A7C2_XYZ_TO_CAM (my derivation reproduces the crate's asserted
neutral-response constant 1.0730 to 5e-7):

    R_out = +1.1975*R_cam -0.1250*G_cam -0.0725*B_cam
    G_out = -0.4530*R_cam +2.2300*G_cam -0.7770*B_cam

So output red carries camera green at 10.4 % of its own weight and output green
carries camera red at 20.3 % of its own weight -- both AT ZERO DISPLACEMENT.
The CLI's own --srgb help says "For looking at, NOT for measuring".

This re-measures on the byte-frozen LINEAR camera-native render, where R is R and
G is G, with BOTH estimators. Four cells. If ORCH's estimator recovers the field
on the linear render, its blindness is a property of the measurement space and
not of the estimator; if it stays flat, the estimator is the cause.

B4 -- SECOND STACK. Same four cells on a capture that is not one of the two
M107 fitted the coefficient on.
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from c4_globalfit import cs, grid, measure, fit_eps, EPS_R   # noqa: E402

OUT = r"C:\dev\strehl-out\M113-ca"
LIN = r"C:\dev\strehl-out\M113-ca\lin"
R1 = r"C:\dev\strehl-out\M114-ca-verify\r1"

CASES = [
    ("bee srgb  ", os.path.join(R1, "off.tif"), os.path.join(R1, "on.tif")),
    ("bee linear", os.path.join(LIN, "bee-3-cpl-off.tif"), os.path.join(LIN, "bee-3-cpl-on.tif")),
    ("couch lin ", os.path.join(LIN, "couch-fibers-cpl-off.tif"), os.path.join(LIN, "couch-fibers-cpl-on.tif")),
]

def main():
    res = {}
    for label, poff, pon in CASES:
        if not (os.path.exists(poff) and os.path.exists(pon)):
            print("%-11s SKIP (not rendered): %s" % (label, os.path.basename(poff)))
            continue
        off, W, H = cs.load_tiff_u16(poff)
        on, W2, H2 = cs.load_tiff_u16(pon)
        assert (W, H) == (W2, H2), "arm geometry differs"
        cx, cy = W / 2.0, H / 2.0
        ws = grid(off, W, H)
        print("\n" + "=" * 96)
        print("%s   %dx%d   %d windows pass ORCH's edge-energy rule" % (label, W, H, len(ws)))
        print("=" * 96)
        print("%-6s %-5s %12s %10s %10s %7s %8s" % ("est", "arm", "eps ppm", "tx px", "ty px", "n", "rms px"))
        cell = {}
        for which in ("lk", "orch"):
            for arm, img in (("off", off), ("on", on)):
                m = measure(img, ws, which, cx=cx, cy=cy)
                eps, tx, ty, n, rms = fit_eps(m, cx, cy)
                cell["%s_%s" % (which, arm)] = dict(eps=eps, tx=tx, ty=ty, n=n, rms=rms)
                print("%-6s %-5s %12.1f %10.4f %10.4f %7d %8.4f"
                      % (which, arm, eps * 1e6, tx, ty, n, rms))
        print("-" * 96)
        print("%-6s %13s %13s %9s %11s" % ("est", "needed ppm", "applied ppm", "gain", "appl/eps_r"))
        for which in ("lk", "orch"):
            eo = cell["%s_off" % which]["eps"]; en = cell["%s_on" % which]["eps"]
            needed, applied = -eo, en - eo
            gain = applied / needed if needed else float("nan")
            cell["gain_%s" % which] = gain
            cell["needed_%s" % which] = needed
            cell["applied_%s" % which] = applied
            print("%-6s %13.1f %13.1f %9.4f %11.4f"
                  % (which, needed * 1e6, applied * 1e6, gain, applied / (-EPS_R)))
        res[label.strip()] = cell
        del off, on

    print("\n" + "=" * 96)
    print("SUMMARY -- gain by measurement space and stack (LK = validated instrument)")
    print("=" * 96)
    print("%-12s %12s %12s %12s %12s" % ("case", "gain LK", "gain ORCH", "needed LK", "eps_r ppm"))
    for k, v in res.items():
        print("%-12s %12.4f %12.4f %12.1f %12.1f"
              % (k, v["gain_lk"], v["gain_orch"], v["needed_lk"] * 1e6, -EPS_R * 1e6))
    with open(os.path.join(OUT, "c8_linear.json"), "w") as fh:
        json.dump(res, fh, indent=2)
    print("\nwrote c8_linear.json")

if __name__ == "__main__":
    main()
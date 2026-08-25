"""Does the lateral coefficient drift with focus position within one bracket?

WHY THIS DECIDES THE ARGUMENT. c4 found the apparent per-stack spread in eps_R is
estimator attenuation, not optics, and the physical prior agrees: all six stacks
are the same lens at the same 200 mm with the same 2x teleconverter at focus
distances spanning 0.2707-0.2771 m, and a lens does not change its lateral CA
because you pointed it at a different insect. But there IS one genuine physical
variable left. Each stack is a BRACKET: focus distance sweeps across it, and
lateral CA is a function of focus distance. If eps drifts strongly with frame
index, then no single per-stack coefficient is right either -- the correction
would need to be depth-dependent, which is a different and much larger change
than anything on the table.

So this is not a nice-to-have. It is the test that decides whether "one scalar
per channel" is the right MODEL at all, independent of where the scalar comes
from.

THE MEASUREMENT. c1 already records, for every frame that any tile elected as its
best-focus frame, the fit over just the tiles that elected it. That is a set of
independent per-focus-position estimates of eps, free of charge. Regress eps on
frame index, weighted by tile count.

THE CONFOUND, AND THE CONTROL FOR IT. Tiles do not elect frames at random: near
tiles elect one end of the bracket and far tiles the other, so frame index is
correlated with field radius, and any radial mis-fit would masquerade as focus
dependence. The green null (G1 vs G2) is carried through the identical path and
regressed the same way. G1 and G2 come to focus at the same distance and have no
lateral CA between them, so any slope the null shows on this axis is the
confound's size, and the treatment must be judged against it -- rule 3, raw
statistic beside the excess, in the same table.
"""

import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

PPM = 1e6
MIN_TILES = 15          # a per-frame fit on fewer tiles is not worth regressing


def slope(pf):
    """Weighted least squares of eps (ppm) on frame index, with a t statistic."""
    pf = [r for r in pf if r["n"] >= MIN_TILES]
    if len(pf) < 4:
        return None
    x = np.array([r["frame"] for r in pf], float)
    y = np.array([r["eps"] for r in pf]) * PPM
    w = np.array([r["n"] for r in pf], float)
    W = w / w.sum()
    xm, ym = (W * x).sum(), (W * y).sum()
    sxx = (W * (x - xm) ** 2).sum()
    b = (W * (x - xm) * (y - ym)).sum() / sxx
    a = ym - b * xm
    res = y - (a + b * x)
    dof = len(x) - 2
    s2 = (W * res ** 2).sum() * len(x) / dof
    se = np.sqrt(s2 / (sxx * len(x)))
    return {
        "n_frames": len(x), "span": float(x[-1] - x[0]),
        "eps_mean_ppm": float(ym), "slope_ppm_per_frame": float(b),
        "slope_se": float(se), "t": float(b / se) if se > 0 else float("nan"),
        # The quantity that matters is not the slope but what it integrates to
        # across the bracket actually used.
        "drift_over_bracket_ppm": float(b * (x[-1] - x[0])),
        "spread_pct": float(100 * (y.max() - y.min()) / abs(ym)),
    }


def main():
    out = []
    print("=" * 108)
    print("EPS vs FOCUS POSITION WITHIN A BRACKET")
    print("  drift = slope x bracket span, i.e. how much eps changes from the")
    print("  near end of the stack to the far end, in ppm. The corner")
    print("  displacement that drift is worth is drift x 2112 px.")
    print("=" * 108)
    hdr = (f"{'stack':>18} {'ch':>3} {'nfr':>4} {'span':>5} {'eps mean':>9} "
           f"{'slope':>9} {'t':>7} {'drift':>8} {'px @corner':>11} "
           f"{'spread%':>8}")
    print(hdr)
    for f in sorted(glob.glob(os.path.join(common.OUT, "json",
                                           "c1_lateral_*.json"))):
        st = os.path.basename(f)[len("c1_lateral_"):-len(".json")]
        d = json.load(open(f))
        for ch in ("R", "B", "G2"):
            s = slope(d["per_frame"][ch])
            if s is None:
                continue
            s["stack"], s["ch"] = st, ch
            out.append(s)
            tag = "  <- NULL" if ch == "G2" else ""
            print(f"{st:>18} {ch:>3} {s['n_frames']:4d} {s['span']:5.0f} "
                  f"{s['eps_mean_ppm']:9.1f} {s['slope_ppm_per_frame']:9.4f} "
                  f"{s['t']:7.1f} {s['drift_over_bracket_ppm']:8.1f} "
                  f"{abs(s['drift_over_bracket_ppm'])*1e-6*2112:11.3f} "
                  f"{s['spread_pct']:8.1f}{tag}")
        print()

    print("=" * 108)
    print("SUMMARY: treatment drift vs null drift, in corner plane px")
    print("=" * 108)
    for ch in ("R", "B", "G2"):
        rows = [r for r in out if r["ch"] == ch]
        if not rows:
            continue
        dpx = [abs(r["drift_over_bracket_ppm"]) * 1e-6 * 2112 for r in rows]
        print(f"  {ch:>3}  mean |drift| {np.mean(dpx):.3f} px   "
              f"worst {np.max(dpx):.3f} px   "
              f"mean |slope| t {np.mean([abs(r['t']) for r in rows]):.1f}")
    nul = [abs(r["drift_over_bracket_ppm"]) * 1e-6 * 2112
           for r in out if r["ch"] == "G2"]
    for ch in ("R", "B"):
        rows = [abs(r["drift_over_bracket_ppm"]) * 1e-6 * 2112
                for r in out if r["ch"] == ch]
        print(f"  {ch} drift / null drift = {np.mean(rows)/np.mean(nul):.2f}x")
    print("\n  For scale: the total uncorrected aberration at the corner is")
    print("  1.52 px in red and 0.36 px in blue (c5). A drift small compared")
    print("  with those means one scalar per channel is an adequate model and")
    print("  the correction does not need to be depth-dependent.")

    common.dump("c6_focusdep", out)
    print("\nwrote c6_focusdep.json")


if __name__ == "__main__":
    main()

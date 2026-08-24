"""B3-DOSE -- dose-response of end-to-end residual against a planted log-scale gain.

M97's signtest reports a single residual for a single sidecar. That is one point on
a curve, and a single point cannot tell you whether the instrument is even sensitive
in the regime you care about. M103 measured a 0.0085 disagreement between the
residual predicted from the sidecar's own span arithmetic and the residual signtest
measured, which is ~18 plane px -- the same order as the correction being claimed.
Arguing about that is worthless; sweeping it is decisive.

This sweeps the `gain` hook signtest already exposes (a' = exp(g*ln a), b' = g*b, a
scalar correction applied at the consumption point, never touching the estimator) and
records the measured AS-IS residual at each g. Three things fall out:

  * whether the instrument is monotone and sensitive near residual 1.0 (if it is
    flat there, the 0.1 plane px reading is a floor artefact and must not be quoted);
  * the gain at which each sidecar's residual is actually minimised, which is a
    direct read of how much of the drift that sidecar is missing;
  * a positive control -- g is a known planted multiplier on a real sidecar, so the
    location of the minimum is predictable in advance and can be checked.

Predicted minima (DERIVED, written before the run):
  baseline (span 0.922414, ln -0.080761) minimises at g = 0.154154/0.080761 = 1.909
  M103 fix (span 0.849981, ln -0.162541) minimises at g = 0.154154/0.162541 = 0.948

Everything is reused from signtest itself so this cannot drift from the deciding
instrument. Usage:
    python src/dose.py <sidecar> <out.json> <last> <g0> <g1> ... 
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "M97-warped-merge", "src"))

import signtest as S  # noqa: E402
import residual as RS  # noqa: E402


def main(argv):
    sidecar, out_json, last = argv[1], argv[2], int(argv[3])
    gains = [float(g) for g in argv[4:]]
    if not gains:
        gains = [0.6, 0.8, 0.9, 1.0, 1.1, 1.2, 1.4, 1.7, 1.9, 2.1]

    header, rows0 = S.parse(sidecar)
    plane_w = float(header["plane"].split("x")[0])
    names = sorted(f for f in os.listdir(S.STACK) if f.lower().endswith(".arw"))
    g0 = S.green_plane(os.path.join(S.STACK, names[0]))
    gN = S.green_plane(os.path.join(S.STACK, names[last]))
    scale_px = plane_w / g0.shape[1]
    r_plane = 0.5 * float(np.hypot(3512.0, 2344.0))

    a0r, b0r = rows0[0]
    aNr, bNr = rows0[last]
    print(f"sidecar {os.path.basename(sidecar)}  reference {header['reference']}  "
          f"working {g0.shape[1]}x{g0.shape[0]} ({scale_px:.1f} plane px/px)")
    print(f"|a_0| = {abs(a0r):.6f}  |a_{last}| = {abs(aNr):.6f}  "
          f"ln span = {np.log(abs(aNr) / abs(a0r)):+.6f}")

    # The unaligned truth, measured by the same instrument in the same run so that
    # any bias it carries is present in both numbers being compared. The search is
    # the two-sided one from residual.py: M103 measured that M97's `best_scale`
    # cannot report a residual above 1.0 (its trials call `gather` with a > 1, the
    # branch M97's own round-trip control fails), and a *correctly* solved sidecar
    # lands slightly above 1.0, so a one-sided search would clip precisely the arm
    # under test. Below 1.0 the two agree to 0.1 plane px.
    raw, rawv, rawrail = RS.best_scale_2s(g0, gN)
    print(f"RAW  {raw:.5f}  ncc {rawv:.4f}  railed={rawrail}   "
          f"({abs(raw - 1.0) * r_plane:.1f} plane px of drift)")
    print()
    print(f"{'gain':>6} {'|a_N|':>9} {'residual':>10} {'plane px':>9} "
          f"{'removed':>8} {'ncc':>7} {'railed':>7}")

    out = {"sidecar": sidecar, "raw": raw, "r_plane": r_plane, "points": []}
    drift = abs(raw - 1.0) * r_plane
    for g in gains:
        rows = {k: (np.exp(g * np.log(a)), g * b) for k, (a, b) in rows0.items()}
        a0, b0 = rows[0]
        aN, bN = rows[last]
        w0 = S.gather(g0, a0, b0, scale_px)
        wN = S.gather(gN, aN, bN, scale_px)
        s, v, rail = RS.best_scale_2s(w0, wN)
        px = abs(s - 1.0) * r_plane
        removed = 1.0 - px / drift
        print(f"{g:>6.3f} {abs(aN):>9.6f} {s:>10.5f} {px:>9.1f} "
              f"{removed * 100:>7.1f}% {v:>7.4f} {str(rail):>7}")
        out["points"].append(dict(gain=g, a_last=abs(aN), residual=s,
                                  plane_px=px, removed=removed, ncc=v,
                                  railed=bool(rail)))

    best = min(out["points"], key=lambda p: p["plane_px"])
    out["best"] = best
    print()
    print(f"minimum residual {best['plane_px']:.1f} plane px at gain {best['gain']:.3f} "
          f"({best['removed'] * 100:.1f}% of the drift removed)")
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

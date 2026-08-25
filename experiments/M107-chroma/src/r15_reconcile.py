"""R15 -- reconciling M107's 23% narrowing shift with M113's -0.4%.

ORCH's corrected triage rule says LOCATION statistics are largely immune to
16->8 narrowing, citing M113 at -0.4%/+0.1% under a 118x narrowing. R14
measured M107's transfer check -- built from two location statistics -- moving
0.8338 -> 0.6430, a 23% shift, under a 159x narrowing. Both individual
location estimates moved: off +408.5 -> +320.3 (-21.6%), on -178.9 -> -132.7
(-25.8%). So this is not difference-amplification; the location statistics
themselves moved, which the new rule says should not happen.

One of the two results is being read wrong. Two candidate reconciliations, and
they are ORCH's own, not mine:

  R-A  LEVELS PER WINDOW, NOT PER IMAGE.  ORCH's bound is ~12 distinct levels
       in the window the statistic integrates over, and it warns that the
       file-level and ROI-level counts are the wrong ones.  R14 reported 151
       levels for the WHOLE IMAGE and never counted per window.  If the
       per-window count sits below 12, R14's 23% is exactly ORCH's
       "-43.0% at 4 levels" regime and both results stand.

  R-B  NO SUPPORT FLOOR.  M113 ships MIN_EDGE_ENERGY = 60.0, which ORCH says
       converts silent wrong answers into refusals to fit.  M107's estimator
       (r13_clean_calib.estimate) gates only on std < 1e-6 and den < 1e-3 --
       both effectively zero.  Worse, it normalises each window to unit
       variance, which AMPLIFIES quantisation noise precisely in the
       low-contrast windows M113 excludes.

BARS -- registered before running.

  Y1  Median distinct levels per fitted window, after narrowing, at the
      floor R13 actually used (i.e. none), is BELOW ORCH's bound of 12.
      Falsified if the median is 12 or above -- in which case R-A is dead
      and the 23% is not explained by the level bound.

  Y2  Raising a real support floor collapses the narrowing bias into M113's
      regime: |t8 - t16| / |t16| falls below 5% at some floor that still
      admits at least 100 windows.  Falsified if the bias stays above 15%
      at every such floor, which would mean the support floor does not
      explain the divergence either and I have a genuine contradiction with
      M113 to escalate.

  Y3  CONTROL VALIDITY, per ORCH's saturation warning.  The admitted window
      count must vary by at least 2x across the sweep.  If it does not, the
      sweep excluded nothing, tested nothing, and Y2's verdict -- either way
      -- must be discarded rather than reported.  Y3 is checked FIRST and
      gates Y2.
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r13_clean_calib import CORE, EPS, PAD, R13, STRIDE, SUPPORT_R, WIN  # noqa: E402

QUANTUM = 257.0
FLOORS = [0.0, 15.0, 30.0, 60.0, 120.0, 240.0, 480.0]


def narrow(a):
    return (a.astype(np.float64) / QUANTUM).astype(np.uint8).astype(np.float32) * QUANTUM


def grad_mag(g):
    gy, gx = np.gradient(g)
    return np.hypot(gx, gy)


def estimate_floored(r, g, floor, levels_of=None):
    """r13's estimator plus an M113-style support floor on raw green gradient."""
    h, w = r.shape
    cy, cx = h / 2.0, w / 2.0
    rmax = float(np.hypot(cx, cy))
    num = den_acc = 0.0
    nwin = 0
    levels = []
    for y in range(0, h - WIN, STRIDE):
        for x in range(0, w - WIN, STRIDE):
            wy, wx = y + WIN / 2.0 - cy, x + WIN / 2.0 - cx
            n = np.hypot(wx, wy)
            if n / rmax > SUPPORT_R or n < 1.0:
                continue
            Rw, Gw = r[y:y + WIN, x:x + WIN], g[y:y + WIN, x:x + WIN]
            if Rw.std() < 1e-6 or Gw.std() < 1e-6:
                continue
            Gcore_raw = Gw[PAD:PAD + CORE, PAD:PAD + CORE]
            if float(grad_mag(Gcore_raw).mean()) < floor:
                continue
            nwin += 1
            if levels_of is not None:
                lw = levels_of[y:y + WIN, x:x + WIN][PAD:PAD + CORE, PAD:PAD + CORE]
                levels.append(len(np.unique(lw)))
            Rn = (Rw - Rw.mean()) / Rw.std()
            Gn = (Gw - Gw.mean()) / Gw.std()
            Rc = Rn[PAD:PAD + CORE, PAD:PAD + CORE]
            Gc = Gn[PAD:PAD + CORE, PAD:PAD + CORE]
            gy, gx = np.gradient(Gc)
            ux, uy = wx / n, wy / n
            gu = ux * gx + uy * gy
            d = Rc - Gc
            dd = float((gu * gu).sum())
            if dd < 1e-3:
                continue
            num += (float((gu * d).sum()) / dd) * dd * n
            den_acc += dd * n * n
    rad = num / den_acc if den_acc > 0 else float("nan")
    return rad, nwin, (np.array(levels) if levels else np.array([0]))


def main():
    print("=" * 74)
    print("R15 -- why M107 read 23% where M113 read -0.4%")
    print("=" * 74)

    off = tifffile.imread(os.path.join(R13, "off.tif"))
    on = tifffile.imread(os.path.join(R13, "on.tif"))
    ro16, go16 = off[..., 0].astype(np.float32), off[..., 1].astype(np.float32)
    rn16, gn16 = on[..., 0].astype(np.float32), on[..., 1].astype(np.float32)
    ro8, go8 = narrow(off[..., 0]), narrow(off[..., 1])
    rn8, gn8 = narrow(on[..., 0]), narrow(on[..., 1])

    print("\nY1  LEVELS PER FITTED WINDOW (not per image)")
    _, n0, lv16 = estimate_floored(ro16, go16, 0.0, levels_of=go16)
    _, _, lv8 = estimate_floored(ro8, go8, 0.0, levels_of=go8)
    med8 = float(np.median(lv8))
    print(f"    window {WIN}px, core {CORE}px, {n0} windows at floor 0")
    print(f"    uint16: median {np.median(lv16):7.1f} levels/window  "
          f"p10 {np.percentile(lv16,10):.1f}  p90 {np.percentile(lv16,90):.1f}")
    print(f"    uint8 : median {med8:7.1f} levels/window  "
          f"p10 {np.percentile(lv8,10):.1f}  p90 {np.percentile(lv8,90):.1f}")
    print(f"    (R14 reported 151 levels for the WHOLE IMAGE -- the wrong count)")
    print(f"    ORCH's immunity bound: ~12 levels/window")
    frac_below = float((lv8 < 12).mean())
    y1 = med8 < 12.0
    print(f"    fraction of fitted windows below the bound: {100*frac_below:.1f}%")
    print(f"    Y1 {'HOLDS -- R14 sat inside the failure regime' if y1 else 'FALSIFIED -- level bound does not explain it'}")

    print("\nY3  CONTROL VALIDITY -- window count must vary across the sweep")
    rows = []
    for f in FLOORS:
        t16, n16, _ = estimate_floored(ro16, go16, f)
        u16, _, _ = estimate_floored(rn16, gn16, f)
        t8, n8, lv = estimate_floored(ro8, go8, f, levels_of=go8)
        u8, _, _ = estimate_floored(rn8, gn8, f)
        tr16 = (u16 - t16) / EPS
        tr8 = (u8 - t8) / EPS
        bias = abs(tr8 - tr16) / abs(tr16) if np.isfinite(tr16) and tr16 != 0 else float("nan")
        rows.append((f, n16, float(np.median(lv)), tr16, tr8, bias))
    counts = [r[1] for r in rows]
    varies = max(counts) >= 2 * max(min(counts), 1)
    print(f"    admitted windows across floors: {counts}")
    print(f"    max/min = {max(counts)/max(min(counts),1):.1f}x   "
          f"Y3 {'HOLDS -- the sweep excludes' if varies else 'FALSIFIED -- SATURATED, sweep tested nothing'}")

    print("\nY2  DOES A SUPPORT FLOOR RECOVER M113'S REGIME")
    print(f"    {'floor':>7s} {'n win':>7s} {'lv/win':>7s} {'t16':>8s} {'t8':>8s} {'bias':>8s}")
    for f, n, lv, a, b, bias in rows:
        print(f"    {f:7.0f} {n:7d} {lv:7.1f} {a:8.4f} {b:8.4f} {100*bias:7.1f}%")
    if not varies:
        print("\n    Y2 DISCARDED -- Y3 failed, the control saturated.")
    else:
        ok = [r for r in rows if r[1] >= 100 and r[5] < 0.05]
        y2 = bool(ok)
        print(f"\n    Y2 {'HOLDS' if y2 else 'FALSIFIED'} -- "
              + (f"bias falls to {100*ok[0][5]:.1f}% at floor {ok[0][0]:.0f} "
                 f"on {ok[0][1]} windows" if y2
                 else "no floor with >=100 windows brings bias under 5%"))
        worst = max(r[5] for r in rows if r[1] >= 100)
        if not y2 and worst > 0.15:
            print("    => GENUINE CONTRADICTION WITH M113 -- escalate, do not fold.")
    print("=" * 74)


if __name__ == "__main__":
    main()

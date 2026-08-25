"""V-CA v12 -- verify v11's result before anyone acts on it.

v11 says the family shrinks by half on bee-3-cpl and CHANGES SIGN on
wrapped-text-1 in binned-linear.  Three checks before that is reported:

  1. Is the CA arm live at all in these files?  (M110 cell C: red moves on ~97%,
     green and blue on exactly 0 pixels.)  If red did not move, the file is
     mislabelled and every v11 number is void.
  2. Is the chroma reduction still ZERO AT CENTRE and MONOTONE TO CORNER?  That
     is M110 s14.4's signature of lateral CA specifically, and it is the single
     strongest pro-correction evidence in the corpus.  If it survives in the
     clean space the correction is real even where the aggregate is small.
  3. WHICH fringe is on wrapped-text-1?  A red-only correction fixes red/cyan
     (fact 1537) and cannot fix blue/yellow.  Splitting |R-Y| from |B-Y| says
     whether the sign flip is a failure of the correction or a subject whose
     fringing it was never built to touch.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import tifffile

ROOT = Path(r"C:\dev\strehl-out\M110-sheet")


def load(p):
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p.name}: expected uint16, got {a.dtype}"
    return a


def run(subject):
    o16, n16 = load(ROOT/subject/"lin-default.tif"), load(ROOT/subject/"lin-ca.tif")
    off, on = o16.astype(np.float32), n16.astype(np.float32)
    print(f"\n{'='*76}\n{subject}   {off.shape}\n{'='*76}")

    print("  [1] is the arm live?")
    for ci, nm in ((0, "R"), (1, "G"), (2, "B")):
        d = (n16[..., ci].astype(np.int32) - o16[..., ci].astype(np.int32))
        print(f"      {nm}: {100*float((d != 0).mean()):7.3f}% of px moved   "
              f"max|delta| {int(np.abs(d).max()):6d} DN")

    yo = 0.2126*off[..., 0] + 0.7152*off[..., 1] + 0.0722*off[..., 2]
    yn = 0.2126*on[..., 0] + 0.7152*on[..., 1] + 0.0722*on[..., 2]
    cro, crn = np.abs(off[..., 0]-yo), np.abs(on[..., 0]-yn)
    cbo, cbn = np.abs(off[..., 2]-yo), np.abs(on[..., 2]-yn)

    gy = np.zeros_like(yo); gx = np.zeros_like(yo)
    gy[1:-1, :] = np.abs(yo[2:, :]-yo[:-2, :]); gx[:, 1:-1] = np.abs(yo[:, 2:]-yo[:, :-2])
    g = gy+gx
    edge = g >= float(np.percentile(g[::7, ::7], 98.0))

    h, w, _ = off.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.hypot(xx-(w-1)/2.0, yy-(h-1)/2.0)
    r /= r.max()
    print("  [2] radial profile of the RED-chroma reduction, on edge pixels")
    print(f"      {'r bin':>10}{'n':>10}{'off':>10}{'on':>10}{'change':>10}")
    for lo in np.arange(0.0, 1.0, 0.1):
        m = edge & (r >= lo) & (r < lo+0.1)
        if int(m.sum()) < 3000:
            continue
        a, b = float(cro[m].mean()), float(crn[m].mean())
        print(f"      {lo:.1f}-{lo+0.1:.1f}{int(m.sum()):10d}{a:10.1f}{b:10.1f}{100*(b/a-1):9.2f}%")

    print("  [3] which fringe is on this subject? (edge pixels)")
    print(f"      |R-Y|  {float(cro[edge].mean()):8.1f} -> {float(crn[edge].mean()):8.1f}"
          f"   {100*(float(crn[edge].mean())/float(cro[edge].mean())-1):+7.2f}%")
    print(f"      |B-Y|  {float(cbo[edge].mean()):8.1f} -> {float(cbn[edge].mean()):8.1f}"
          f"   {100*(float(cbn[edge].mean())/float(cbo[edge].mean())-1):+7.2f}%")
    print(f"      ratio |B-Y|/|R-Y| in OFF arm = {float(cbo[edge].mean())/float(cro[edge].mean()):.3f}"
          "   (>1 means blue/yellow dominates, which eps_b=None cannot touch)")


if __name__ == "__main__":
    for s in ("bee-3-cpl", "wrapped-text-1"):
        run(s)

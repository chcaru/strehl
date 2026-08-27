#!/usr/bin/env python3
"""Commission the plant: a dose asserted is not a dose delivered.

Three checks, each of which has to be able to fail:

  1. IDENTITY.  shape=none must round-trip the sidecar to bit-identical
     placements.  If the writer perturbs when asked not to, every later dose is
     the plant plus an unknown constant.
  2. DOSE RECOVERY.  The planted displacement is measured back out through
     wm.corner_err -- an independently written geometry that does not share a
     line of code with the writer -- and must match the request.
  3. SHAPE SEPARATION.  `walk` and `iid` at the SAME absolute envelope must
     differ in LOCAL relative error by a wide margin, because that separation
     is the entire experiment.  If the two shapes are locally similar the
     comparison cannot distinguish accumulation from local error and must not
     be run.
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wm as W  # noqa: E402
from perturb import perturb  # noqa: E402

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else
           r"C:\dev\strehl-out\V-DRIFT\cache\bee-3-cpl-9287871c355f81d7.warpmap.txt")


def abs_err(w1, w2, i):
    """Worst-corner disagreement between two sidecars about frame i's ABSOLUTE
    placement.  Valid here only because the plant is referenced to the same
    frame the solve is, so both files share a reference and absolute
    placements are commensurable."""
    da, db = w1.a[i] - w2.a[i], w1.b[i] - w2.b[i]
    return max(abs(da * c + db) for c in w1.corners())


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="vdrift-plant-"))
    base = W.WarpMap(SRC)
    bad = 0

    # ---- 1. identity -----------------------------------------------------
    p0 = tmp / "none.txt"
    perturb(SRC, p0, "none", 0.0, 1)
    w0 = W.WarpMap(p0)
    worst = max(abs_err(base, w0, i) for i in base.placed())
    ok = worst == 0.0
    bad += not ok
    print(f"[{'PASS' if ok else 'FAIL'}] identity round-trip: worst corner delta "
          f"{worst:.6g} px over {len(base.placed())} frames (want exactly 0)")

    # ---- 2. dose recovery ------------------------------------------------
    for shape in ("iid", "walk"):
        for amp in (0.5, 4.0, 20.0):
            pp = tmp / f"{shape}-{amp}.txt"
            perturb(SRC, pp, shape, amp, 7)
            wp = W.WarpMap(pp)
            got = np.array([abs_err(base, wp, i) for i in base.placed()])
            err = abs(got.max() - amp)
            ok = err < 1e-6
            bad += not ok
            print(f"[{'PASS' if ok else 'FAIL'}] {shape:4s} amp={amp:5.1f}: "
                  f"recovered max {got.max():8.4f} px (delta {err:.2g}), "
                  f"median {np.median(got):7.4f} px")

    # ---- 3. shape separation --------------------------------------------
    AMP = 20.0
    si = perturb(SRC, tmp / "si.txt", "iid", AMP, 7)
    sw = perturb(SRC, tmp / "sw.txt", "walk", AMP, 7)
    print(f"\n  at a matched absolute envelope of {AMP:g} px:")
    print(f"    {'sep':>5} {'walk':>9} {'iid':>9} {'iid/walk':>9}")
    ratios = []
    for sep in (1, 2, 4, 8):
        a, b = sw["local_rel_px"][sep], si["local_rel_px"][sep]
        ratios.append(b / a)
        print(f"    {sep:5d} {a:9.4f} {b:9.4f} {b/a:9.2f}x")
    ok = min(ratios[:2]) > 5.0
    bad += not ok
    print(f"[{'PASS' if ok else 'FAIL'}] shape separation: iid is "
          f"{min(ratios[:2]):.1f}x the local error of walk at sep 1-2 "
          f"(want > 5x, else the arms are not distinguishable)")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'ALL CHECKS PASS' if bad == 0 else f'{bad} CHECK(S) FAILED'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())

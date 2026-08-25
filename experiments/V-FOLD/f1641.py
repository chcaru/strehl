"""V-FOLD: re-derive fact 1641's textured-control numbers on bee-3-cpl.

Reads only. Reuses switch_gate.py's own hf() and pools() so the geometry is
identical to the instrument ORCH used. Prints every textured-pool window's
hf for A0 and the test arm, plus the smooth-pool per-window ratios.
"""
import os, sys
import numpy as np, tifffile
SG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ORCH-drift-check")
sys.path.insert(0, os.path.abspath(SG))
sys.argv = ["switch_gate.py", "ZZZZ"]          # stop the module body from running a real arm
import importlib.util
spec = importlib.util.spec_from_file_location("sg_src", os.path.join(os.path.abspath(SG), "switch_gate.py"))
src = open(spec.origin, encoding="utf-8").read()
body = src.split('print("switch gate:')[0]     # defs only, no __main__ work
ns = {}
exec(compile(body, "switch_gate.py", "exec"), ns)
hf, pools, S = ns["hf"], ns["pools"], ns["S"]
ROOT = r"C:\dev\strehl-out\M116\measure"
def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, (p, a.dtype)
    return a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)
for subj in ["bee-3-cpl", "tweezers-cpl"]:
    for test in ["A1", "A2"]:
        A0 = load(os.path.join(ROOT, "%s__A0.tif" % subj))
        AT = load(os.path.join(ROOT, "%s__%s.tif" % (subj, test)))
        m = 0.5 * (A0 + AT)
        smooth, textured, bar, n = pools(m, A0.shape)
        print("=== %s  A0 vs %s   (bar %.0f, %d windows)" % (subj, test, bar, n))
        print("  TEXTURED pool (switch_gate's control):")
        for x, y in textured:
            h0 = hf(A0[y:y+S, x:x+S]); h1 = hf(AT[y:y+S, x:x+S])
            print("    (%5d,%5d)  hf(A0)=%8.1f  hf(%s)=%8.1f  ratio=%.4f  cut=%.1f%%"
                  % (x, y, h0, test, h1, h1/h0, 100*(1-h1/h0)))
        print("  SMOOTH pool ratios:", ["%.3f" % (hf(AT[y:y+S,x:x+S])/hf(A0[y:y+S,x:x+S])) for x, y in smooth])
        print()

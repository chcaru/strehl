r"""Run ORCH's contrast_ab.py VERBATIM over the band-0 ladder, and report the
clip fraction of every master beside every verdict (fact 1817).

ORCH's criterion: FLAT ratio well below 1.0, EDGE ratio >= 0.98.
Find the knee = largest band-0 scale whose EDGE still clears 0.98.
"""
import os
import subprocess
import sys

import numpy as np
import tifffile

CAB = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check\contrast_ab.py"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\bf112"


def clipfrac(p):
    a = tifffile.imread(p)
    return float((a >= 65535).mean()), float((a <= 0).mean())


pre = sys.argv[1]
rungs = sys.argv[2].split(",")
base = os.path.join(OUT, "%s__A-unset.tiff" % pre)
cb, cd = clipfrac(base)
print("reference %s__A-unset   clip(white) %.4f%%  clip(black) %.4f%%" % (pre, 100 * cb, 100 * cd))
print("%-8s %-8s %-8s %-9s %-9s %-9s %s" % ("rung", "FLAT", "EDGE", "clipW%", "clipB%", "lvl_lift", "ORCH rule"))
for r in rungs:
    p = os.path.join(OUT, "%s__%s.tiff" % (pre, r))
    if not os.path.exists(p):
        print("%-8s MISSING" % r)
        continue
    res = subprocess.run([sys.executable, CAB, base, p], capture_output=True, text=True)
    o = res.stdout + res.stderr
    fl = ed = lift = None
    for ln in o.splitlines():
        if ln.startswith("FLAT"):
            fl = float(ln.split("ratio B/A =")[1].split("|")[0])
            lift = float(ln.split("lift =")[1].split("DN")[0])
        if ln.startswith("EDGE"):
            ed = float(ln.split("ratio B/A =")[1].split("|")[0])
    if fl is None:
        print("%-8s PARSE FAIL: %s" % (r, o[:200]))
        continue
    cw, cbk = clipfrac(p)
    ok = "PASS" if (fl < 1.0 and ed >= 0.98) else ("EDGE FAIL %.4f" % ed if ed < 0.98 else "no FLAT win")
    print("%-8s %-8.4f %-8.4f %-9.4f %-9.4f %-9.1f %s" % (r, fl, ed, 100 * cw, 100 * cbk, lift, ok))

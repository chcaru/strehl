r"""Run ORCH's COMMITTED contrast_ms.py verbatim across the band-0 ladder and
print the full six-band table per rung, plus the three candidate criteria that
ORCH's message and ORCH's committed file disagree about:

  message  : "EDGE ratio at bands 2 and 3 >= 0.98"   (written against commit
             19787752, whose table had FIVE bands and different indices)
  committed: "ACUITY COST band-1 EDGE ratio (want >= 0.98)"

Both are reported so the disagreement is visible per rung rather than argued.
Clip fraction is printed for every master (fact 1817).
"""
import os
import subprocess
import sys

import numpy as np
import tifffile

CMS = r"C:\dev\blog\death-of-software\projects\strehl\experiments\ORCH-drift-check\contrast_ms.py"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\bf112"
if len(sys.argv) > 3:
    OUT = sys.argv[3]

pre = sys.argv[1]
rungs = sys.argv[2].split(",")
base = os.path.join(OUT, "%s__A-unset.tiff" % pre)
print("reference %s__A-unset   clip(white) %.4f%%"
      % (pre, 100 * float((tifffile.imread(base) >= 65535).mean())))

summary = []
for r in rungs:
    p = os.path.join(OUT, "%s__%s.tiff" % (pre, r))
    if not os.path.exists(p):
        print("\n%s MISSING" % r)
        continue
    res = subprocess.run([sys.executable, CMS, base, p], capture_output=True, text=True)
    o = res.stdout + res.stderr
    print("\n===== rung %s   clip(white) %.4f%% ====="
          % (r, 100 * float((tifffile.imread(p) >= 65535).mean())))
    rows = []
    for ln in o.splitlines():
        t = ln.split()
        if len(t) >= 8 and t[0].isdigit():
            print("  " + ln.strip())
            rows.append((int(t[0]), float(t[-4]), float(t[-1])))   # band, FLAT ratio, EDGE ratio
    d = {b: (f, e) for b, f, e in rows}
    summary.append((r, d))

print("\n\n===== LADDER SUMMARY (committed contrast_ms.py band indices) =====")
print("%-6s %-10s %-10s %-10s %-10s %-10s %s" %
      ("rung", "b0 FLAT", "b1 EDGE", "b5 EDGE", "", "", "ORCH final criterion"))
for r, d in summary:
    if 0 not in d:
        continue
    b1e, b2e, b3e, b5e = d[1][1], d[2][1], d[3][1], d[5][1]
    msg = "PASS" if (b2e >= 0.98 and b3e >= 0.98) else "FAIL"
    cmt = "PASS" if b1e >= 0.98 else "FAIL"
    null = "ok" if abs(b5e - 1.0) <= 0.005 else "VOID"
    c1 = "WIN " if d[0][0] < 0.95 else "none"
    c2 = "PASS" if b1e >= 0.98 else "FAIL"
    c3 = "ok  " if abs(b5e - 1.0) <= 0.005 else "VOID"
    allp = "ADMITTED" if (d[0][0] < 0.95 and b1e >= 0.98 and abs(b5e - 1.0) <= 0.005) else "rejected"
    print("%-6s %-10.4f %-10.4f %-10.4f  c1grain:%s  c2acuity:%s  c3null:%s  -> %s"
          % (r, d[0][0], b1e, b5e, c1, c2, c3, allp))




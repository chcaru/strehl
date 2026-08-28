# Why does aura == rim to 0.1 DN on 14 of 26 subjects? Look at the profiles
# instead of reasoning about them. This script prints nothing but measured
# numbers: the band medians, the per-band deficit and surplus, and where each
# maximum lands. If the equality is a real property of the profile shape it
# will be visible here; if it is a coding defect it will also be visible here.
import json
import sys
import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from aura import prominence  # noqa: E402

J = json.loads(open(r"C:\dev\strehl-out\V-SPEED-HALO\aura-faithful.json").read())
rows = J["rows"] if isinstance(J, dict) else J

want = sys.argv[1:] or ["bee-1-cpl", "coffee-bean", "tweezers-cpl", "119MSDCF"]

for r in rows:
    if r["subject"] not in want:
        continue
    v = np.array(r["meds"], float)
    mids = np.array(r["mids"], float)
    dd = prominence(v)
    ss = prominence(-v)
    print("\n=== %s   aura=%.1f rim=%.1f nbands=%d"
          % (r["subject"], r["aura_dn"], r["rim_dn"], len(v)))
    print("  %8s %10s %10s %10s" % ("mid px", "median", "deficit", "surplus"))
    for i in range(len(v)):
        mark = ""
        if np.isfinite(dd[i]) and dd[i] == np.max(dd[np.isfinite(dd)]):
            mark += " <-aura"
        if np.isfinite(ss[i]) and ss[i] == np.max(ss[np.isfinite(ss)]):
            mark += " <-rim"
        print("  %8.1f %10.1f %10s %10s%s"
              % (mids[i], v[i],
                 "%.1f" % dd[i] if np.isfinite(dd[i]) else "-",
                 "%.1f" % ss[i] if np.isfinite(ss[i]) else "-", mark))
    fin = np.isfinite(dd)
    print("  argmax deficit band %d (%.0f px), argmax surplus band %d (%.0f px)"
          % (int(np.argmax(np.where(fin, dd, -np.inf))),
             mids[int(np.argmax(np.where(fin, dd, -np.inf)))],
             int(np.argmax(np.where(fin, ss, -np.inf))),
             mids[int(np.argmax(np.where(fin, ss, -np.inf)))]))
    print("  global min band %d (%.0f px) = %.1f ; global max band %d (%.0f px) = %.1f"
          % (int(np.argmin(v)), mids[int(np.argmin(v))], v.min(),
             int(np.argmax(v)), mids[int(np.argmax(v))], v.max()))

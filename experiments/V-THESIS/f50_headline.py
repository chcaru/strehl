"""The headline in natural units, with NO inversion and NO ladder.

S2_f50 is a half-energy frequency in cyc/px -- it IS "how fine the arm resolves".
The README claims the merge resolves 1.2-1.8x finer detail. That claim, stated
in these units, is f50_merge / f50_argmax = 1.2 to 1.8. This needs no blur
ladder, no Gaussian model and no inversion, so none of the defects in blureq.py
can touch it. Both the raw and the geometry-corrected argmax column are shown;
the geometry correction is BUILD-THESIS's own, and it favours the merge.
"""
import json, pathlib
import numpy as np
d = json.loads(pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\measure-subjects.json").read_text())
print(f"{'subject':<19}{'f50 merge':>10}{'f50 amax':>10}{'raw ratio':>10}"
      f"{'geom ratio':>11}{'README needs':>13}")
print("-" * 73)
raw, geo = [], []
for r in d:
    fm = float(np.median([t["S2_f50_merge"] for t in r["tiles"]]))
    fa = float(np.median([t["S2_f50_argmax"] for t in r["tiles"]]))
    fg = float(np.median([t["S2_f50_argmax_geom"] for t in r["tiles"]]))
    raw.append(fm/fa); geo.append(fm/fg)
    print(f"{r['subject']:<19}{fm:>10.4f}{fa:>10.4f}{fm/fa:>10.3f}{fm/fg:>11.3f}"
          f"{'1.20 - 1.80':>13}")
print("-" * 73)
print(f"raw  merge/argmax f50 ratio: median {np.median(raw):.3f}, "
      f"max {max(raw):.3f} over 6 subjects")
print(f"geom merge/argmax f50 ratio: median {np.median(geo):.3f}, "
      f"max {max(geo):.3f} over 6 subjects")
print()
print("The merge's half-energy frequency never exceeds the selector's by more")
print("than %.1f%% raw / %.1f%% geometry-corrected. The claim needs 20-80%%."
      % ((max(raw)-1)*100, (max(geo)-1)*100))

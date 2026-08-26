"""Reproduce BUILD-THESIS's headline table from their own code and tiles, then
re-run the SAME statistics on the SAME tiles against an EXACT Gaussian ladder.

Column 'BT' is their published number (REPORT.md).
Column 'repro' is their invert() + their stats, re-executed here.
Column 'exact' is their stats inverted against a true Fourier Gaussian instead
of scipy.ndimage.gaussian_filter, which at these sigmas is not a Gaussian.

Nothing under C:\\dev\\strehl-out\\BUILD-THESIS is written.
"""
import json, pathlib, sys
import numpy as np, tifffile

B = pathlib.Path("experiments/BUILD-THESIS").resolve(); sys.path.insert(0, str(B))
V = pathlib.Path("experiments/V-THESIS").resolve(); sys.path.insert(0, str(V))
from stats import STATS                     # noqa: E402  theirs
from blureq import invert, LADDER           # noqa: E402  theirs
from vplant import gauss_exact              # noqa: E402  mine

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")


def invert_exact(t_from, target, fn):
    prev_s, prev_v = 0.0, fn(t_from)
    if target >= prev_v: return 0.0
    for s in LADDER[1:]:
        v = fn(gauss_exact(t_from, s))
        if v <= target:
            w = 0.0 if prev_v == v else (prev_v-target)/(prev_v-v)
            return float(prev_s + w*(s-prev_s))
        prev_s, prev_v = s, v
    return float(LADDER[-1])


BT = {  # from experiments/BUILD-THESIS/REPORT.md, headline table
 "bee-3-cpl":        (-0.45, +0.09, -0.00),
 "bee-1-cpl":        (-0.44, +0.04, +0.47),
 "leaf-2-cpl":       (-0.43, -0.36, +0.38),
 "flowers-cpl":      (+0.49, +0.26, -2.06),
 "tweezers-cpl":     (-0.47, -0.35, +0.40),
 "flat-on-ruler-cpl":(-0.48, -0.44, -0.38),
}
data = json.loads(pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\measure-subjects.json").read_text(encoding="utf8"))
print(f"{'subject':<19}" + "".join(f"{k[:2]+' BT':>9}{k[:2]+' rep':>9}{k[:2]+' exa':>9}" for k in STATS))
for rec in data:
    subj = rec["subject"]
    gm = tifffile.imread(str(R/subj/"merge.tif"))[:,:,1].astype(np.float64)
    ga = tifffile.imread(str(R/subj/"argmax.tif"))[:,:,1].astype(np.float64)
    rep = {k: [] for k in STATS}; exa = {k: [] for k in STATS}
    for t in rec["tiles"]:
        x, y = t["merge_xy"]; ax, ay = t["argmax_xy"]
        Tm, Ta = t["tile_px_merge"], t["tile_px_argmax"]
        tm = gm[y:y+Tm, x:x+Tm]; ta = ga[ay:ay+Ta, ax:ax+Ta]
        for k, fn in STATS.items():
            vm, va = fn(tm), fn(ta)
            if va <= vm:
                rep[k].append(invert(tm, va, fn));       exa[k].append(invert_exact(tm, va, fn))
            else:
                rep[k].append(-invert(ta, vm, fn));      exa[k].append(-invert_exact(ta, vm, fn))
    line = f"{subj:<19}"
    for i, k in enumerate(STATS):
        line += f"{BT[subj][i]:>+9.2f}{np.median(rep[k]):>+9.2f}{np.median(exa[k]):>+9.2f}"
    print(line)

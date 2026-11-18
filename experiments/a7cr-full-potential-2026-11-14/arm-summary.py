"""Summarise tile-signal.py outputs arm by arm, each on its OWN tiles, for arms
whose geometry differs (e.g. --cover crop against scale).

  python -X utf8 arm-summary.py BASE.npz [OTHER.npz ...]

Per file (one arm each): tiles inside the border, above the 15th percentile
of green level, under 1 % clipped, and in the top 30 % of green high-pass
energy among those; summed signal and noise per channel and band. Prints
amplitude ratios to the first file. Tile sets differ between arms of
different geometry, so the ratio carries that sampling difference too.
"""
import sys
import numpy as np

rows = []
for f in sys.argv[1:]:
    z = np.load(f)
    e, m, clip = z['energy'], z['mean_g'], z['clip']
    ok = np.zeros_like(e, bool)
    ok[1:-1, 1:-1] = True
    ok &= (m > np.percentile(m, 15)) & (clip < 0.01)
    ok &= e >= np.percentile(e[ok], 70)
    rows.append((f, ok.sum(), z['sig'][0][ok].sum(0), z['noi'][0][ok].sum(0)))
b = rows[0]
for f, n, s, no in rows:
    hi = np.sqrt(np.clip(s[:, 0], 0, None) / b[2][:, 0])
    lo = np.sqrt(np.clip(s[:, 1], 0, None) / b[2][:, 1])
    nh = np.sqrt(no[:, 0] / b[3][:, 0])
    print(f'{f.split("/")[-1]:28s} tiles {n:4d}  hi R/G/B {hi.round(3)}  lo {lo.round(3)}  noise(hi) {nh.round(3)}  SNR power hi G {s[1, 0] / no[1, 0]:.2f}')

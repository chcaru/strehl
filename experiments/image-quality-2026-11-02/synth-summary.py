"""Summarise synth-stack.py output: candidate / default error-power ratio per cell.

usage: synth-summary.py SYNTH_OUTPUT.txt
Prints, for every (contrast, N, scene), the ratio of the STREHL_PYRAMID_ENSEMBLE=1
arm's error power to the =0 arm's in each band and region class, then the
count of cells where the candidate is worse and the worst ratio.
"""
import re
import sys

cur, rows = None, {}
for line in open(sys.argv[1]):
    m = re.match(r"c=(\S+) scene (\S+) N (\d+)", line)
    if m:
        cur = (m.group(1), int(m.group(3)), m.group(2))
        continue
    m = re.match(r"c=\S+\s+STREHL_PYRAMID_ENSEMBLE=(\d)\s+(.*)", line)
    if m and cur:
        cells = dict(re.findall(r"(\w+ \w+|\w+)=\s*([\d.]+)", ""))
        vals = {}
        for band_part in m.group(2).split("|"):
            band = band_part.split()[0]
            for k, v in re.findall(r"(\w+)=\s*([\d.]+)", band_part):
                vals[f"{band}/{k}"] = float(v)
        rows.setdefault(cur, {})[m.group(1)] = vals
worse, worst = 0, (1.0, None)
total = 0
for key in sorted(rows):
    arms = rows[key]
    if "0" not in arms or "1" not in arms:
        continue
    ratios = {k: arms["1"][k] / arms["0"][k] for k in arms["0"]}
    total += len(ratios)
    bad = {k: r for k, r in ratios.items() if r > 1.0}
    worse += len(bad)
    for k, r in bad.items():
        if r > worst[0]:
            worst = (r, (key, k))
    print(f"c={key[0]:>4} N={key[1]:>3} {key[2]:5s} " +
          " ".join(f"{k}={r:.3f}" for k, r in ratios.items()))
print(f"cells where the gate is worse: {worse} of {total}; worst ratio {worst[0]:.4f} at {worst[1]}")

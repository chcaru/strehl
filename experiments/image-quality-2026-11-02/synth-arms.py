"""Compare every arm of synth-stack.py output against the FIRST arm run.

usage: synth-arms.py SYNTH_OUTPUT.txt
For each arm label (the text before the first band), prints the number of
(scene, band/region) cells where it is worse than the first arm, the worst
ratio and where, and the geometric-mean ratio over all cells.
"""
import math
import re
import sys
from collections import defaultdict

cur = None
data = defaultdict(dict)  # arm -> {(scene, cell): value}
order = []
for line in open(sys.argv[1]):
    m = re.match(r"(?:\S+ )?scene (\S+) N (\d+)", line)
    if m and "fine" not in line:
        tag = re.match(r"(c=\S+ )?", line).group(0)
        cur = f"{tag}{m.group(1)} N{m.group(2)}"
        continue
    if cur is None or "fine " not in line or "oracle" in line or "plain-mean" in line:
        continue
    label = line.split("fine ")[0].strip()
    label = re.sub(r"^c=\S+\s+", "", label)
    if label not in order:
        order.append(label)
    for band_part in ("fine " + line.split("fine ", 1)[1]).split("|"):
        band = band_part.split()[0]
        for k, v in re.findall(r"(\w+)=\s*([\d.]+)", band_part):
            data[label][(cur, f"{band}/{k}")] = float(v)
base = order[0]
print(f"reference arm: {base}")
for arm in order[1:]:
    ratios = {c: data[arm][c] / data[base][c] for c in data[arm] if c in data[base] and data[base][c] > 0}
    worse = {c: r for c, r in ratios.items() if r > 1.0}
    gm = math.exp(sum(math.log(r) for r in ratios.values()) / len(ratios))
    w = max(worse.items(), key=lambda kv: kv[1]) if worse else (None, 1.0)
    print(f"{arm}: worse in {len(worse)}/{len(ratios)} cells, worst {w[1]:.3f} at {w[0]}, geo-mean ratio {gm:.3f}")
    for c, r in sorted(worse.items(), key=lambda kv: -kv[1])[:6]:
        print(f"    {r:.3f} {c}")

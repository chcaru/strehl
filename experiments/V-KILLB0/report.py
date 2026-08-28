"""Render the V-KILLB0 sweep JSONs as tables."""
import glob
import json
import os
import sys

import numpy as np

BINS = ["0.40-0.50", "0.30-0.40", "0.25-0.30", "0.20-0.25",
        "0.17-0.20", "0.10-0.17", "0.05-0.10", "0.02-0.05"]

d = sys.argv[1]
pre = sys.argv[2] if len(sys.argv) > 2 else ""
rows = []
for p in sorted(glob.glob(os.path.join(d, "*.json"))):
    n = os.path.basename(p)[:-5]
    if pre and not n.startswith(pre):
        continue
    if not pre and "-" in n and n.split("-")[0] in ("b0x2", "b0x8", "b0x4x"):
        continue
    rows.append(json.load(open(p)))

print("=" * 128)
print("STRUCTURE-SELECTIVE ACUITY  (per-pixel, selector = 0.05-0.17 cyc/px structure of the DEFAULT arm)")
print("  fine = 0.25-0.50 cyc/px RMS ratio arm/default;  mid = 0.17-0.25 cyc/px ratio")
print("=" * 128)
h = (f"{'subject':<28s} {'medA':>6s} {'clipA%':>7s} {'blkA%':>6s} | "
     f"{'fine@top0.1%':>12s} {'fine@top1%':>11s} {'fine@bot50%':>12s} | "
     f"{'mid@top0.1%':>12s} {'mid@bot50%':>11s} | {'dLevel%':>8s}")
print(h)
print("-" * len(h))
for r in rows:
    s = r["structure"]
    dl = 100.0 * (r["mean_B"] / r["mean_A"] - 1.0)
    print(f"{r['name']:<28s} {r['median_A']:6.0f} {r['clip_A']:7.2f} {r['black_A']:6.2f} | "
          f"{s['top0.1%']['fine_ratio']:12.4f} {s['top1%']['fine_ratio']:11.4f} "
          f"{s['bottom50%']['fine_ratio']:12.4f} | "
          f"{s['top0.1%']['mid_ratio']:12.4f} {s['bottom50%']['mid_ratio']:11.4f} | {dl:+8.3f}")

for site in ("FLAT", "EDGE"):
    print()
    print("=" * 128)
    print(f"BAND AMPLITUDE RATIO rho (arm/default) at {site} tiles -- 12 x 256px tiles, chosen on the default arm")
    print("=" * 128)
    h = f"{'subject':<28s} {'lvl':>6s} {'clip%':>6s} " + " ".join(f"{b:>9s}" for b in BINS)
    print(h)
    print("-" * len(h))
    for r in rows:
        e = r["sites"][site]
        print(f"{r['name']:<28s} {e['level']:6.0f} {e['clip_pct']:6.2f} "
              + " ".join(f"{v:9.4f}" for v in e["rho"]))

print()
print("=" * 128)
print("D = ln(g)/ln(rho)   1 = pure blur, 2 = pure denoise, >2 = denoise with noise left in both arms")
print("  (bins where |rho-1| < 0.003 are inert and D is meaningless there: shown as '.')")
print("=" * 128)
for site in ("FLAT", "EDGE"):
    print(f"-- {site}")
    h = f"{'subject':<28s} " + " ".join(f"{b:>9s}" for b in BINS)
    print(h)
    for r in rows:
        e = r["sites"][site]
        cells = []
        for i in range(len(BINS)):
            if abs(e["rho"][i] - 1.0) < 0.003:
                cells.append(f"{'.':>9s}")
            else:
                cells.append(f"{e['D'][i]:9.3f}")
        print(f"{r['name']:<28s} " + " ".join(cells))

print()
print("EDGE-TILE DILUTION: fraction of a 'high gradient' 256px tile that is actually structure")
for r in rows:
    print(f"   {r['name']:<28s} edge_px_frac = {r['structure']['edge_px_frac']:.4f}")

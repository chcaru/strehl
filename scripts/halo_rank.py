import collections
import csv

rows = list(
    csv.DictReader(
        open(r"C:\dev\strehl-out\baseline-crops\crop-stats-baseline.tsv"), delimiter="\t"
    )
)

by = collections.defaultdict(list)
for r in rows:
    if r["kind"] == "edge" and r.get("edge_overshoot"):
        by[r["subject"]].append(float(r["edge_overshoot"]))

print("Edge overshoot: how far the bright side of an occluding edge rises")
print("above its own 90th-percentile plateau, in LINEAR light, fraction of white.")
print()
print(f"{'subject':40} {'max':>8} {'mean':>8}")
for s, v in sorted(by.items(), key=lambda kv: -max(kv[1])):
    print(f"{s:40} {max(v):>8.4f} {sum(v) / len(v):>8.4f}")

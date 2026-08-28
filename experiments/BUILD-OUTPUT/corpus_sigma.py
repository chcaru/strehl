import re
rows = []
for ln in open(r"D:\strehl-out\BUILD-OUTPUT\scratch\banding_corpus.log", encoding="utf-8", errors="replace"):
    m = re.match(r"^(\S.*?)\s+(shadow|mid|high)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s*$", ln.rstrip())
    if m:
        rows.append((m.group(1).strip(), m.group(2), float(m.group(6)), float(m.group(11)), int(m.group(3))))
print(f"parsed strata: {len(rows)}  (expected 50)")
rows.sort(key=lambda r: r[2])
print("\nlowest sigma (codes) across the WHOLE corpus:")
for r in rows[:6]:
    print(f"  {r[2]:>6.2f}  {r[0]:<34}[{r[1]}]  banded {r[3]:.1f}%  tiles {r[4]}")
print(f"\ncorpus min sigma = {rows[0][2]:.2f}   max = {rows[-1][2]:.2f}")
nz = [r for r in rows if r[3] > 0]
print(f"strata with banded > 0: {len(nz)} -> {[(r[0], r[1], r[3]) for r in nz]}")
tot = sum(r[4] for r in rows)
print(f"total tiles measured across corpus: {tot}")

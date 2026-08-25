import re, json, os, io, sys
root = "."
syn = open(os.path.join(root,"docs/research/SYNTHESIS.md"), encoding="utf-8").read()
lines = syn.split("\n")
rows = {}
pat = re.compile(r"^\|\s*(\d+)\s*\|\s*([A-Z \-]+?)\s*\|\s*([^|]*?)\s*\|\s*(.*)$")
for i,l in enumerate(lines):
    m = pat.match(l)
    if m:
        n = int(m.group(1))
        if n in rows:
            print("DUPLICATE FACT NUMBER", n, "at line", i+1, "prev", rows[n]["line"])
        rows[n] = {"n":n,"line":i+1,"label":m.group(2),"src":m.group(3),"text":m.group(4)}
sel = {n:r for n,r in rows.items() if 1560 <= n <= 1665}
print("total rows parsed:", len(rows), " in range:", len(sel))
missing = [n for n in range(1560,1666) if n not in rows]
print("missing in range:", missing)
json.dump(sel, open("experiments/V-FOLD/facts.json","w",encoding="utf-8"), indent=1)
# label histogram
from collections import Counter
print(Counter(r["label"] for r in sel.values()))
print(Counter(r["src"] for r in sel.values()))

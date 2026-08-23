import io, re, json, os
proj = r"C:\dev\blog\death-of-software\projects\strehl"
src = io.open(os.path.join(proj,"docs","research","SYNTHESIS.md"), encoding="utf-8").read().split("\n")
# section 4 bounds
start = None; end = None
for i,l in enumerate(src):
    if l.startswith("## 4. "): start = i
    if l.startswith("## 5. "): end = i
rows = {}
dups = []
for i in range(start, end):
    l = src[i]
    m = re.match(r"^\|\s*(\d+)\s*\|", l)
    if m:
        n = int(m.group(1))
        if n in rows: dups.append(n)
        rows[n] = {"line": i+1, "text": l}
print("rows parsed:", len(rows), "dups:", dups)
ns = sorted(rows)
print("min", ns[0], "max", ns[-1])
missing = [k for k in range(ns[0], ns[-1]+1) if k not in rows]
print("missing count:", len(missing))
json.dump({str(k):v for k,v in rows.items()}, io.open(os.path.join(proj,"experiments","M56-citations","facts.json"),"w",encoding="utf-8"), indent=1)
cites = json.load(io.open(os.path.join(proj,"experiments","M56-citations","cites.json"),encoding="utf-8"))
cn = sorted(set(c["num"] for c in cites))
unres = [n for n in cn if n not in rows]
print("cited but not a row:", unres)

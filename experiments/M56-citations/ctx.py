import io, json, os, re, sys
proj = r"C:\dev\blog\death-of-software\projects\strehl"
cites = json.load(io.open(os.path.join(proj,"experiments","M56-citations","cites.json"),encoding="utf-8"))
want = sys.argv[1]
files = {}
for c in cites:
    if want not in c["file"]: continue
    files.setdefault(c["file"], []).append(c)
for f, cs in files.items():
    lines = io.open(os.path.join(proj, f.replace("/", os.sep)), encoding="utf-8").read().split("\n")
    print("#"*100); print(f)
    seen = set()
    for c in cs:
        key = c["line"]
        if key in seen: continue
        seen.add(key)
        a = max(0, c["line"]-5); b = min(len(lines), c["line"]+4)
        print("-"*80)
        print(f"[{f}:{c['line']}] cites {sorted(set(x['num'] for x in cs if x['line']==c['line']))}")
        for i in range(a,b):
            mark = ">>" if i+1==c["line"] else "  "
            print(f"{mark}{i+1:5d}| {lines[i]}")

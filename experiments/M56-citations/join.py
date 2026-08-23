import io, json, os, sys
proj = r"C:\dev\blog\death-of-software\projects\strehl"
facts = json.load(io.open(os.path.join(proj,"experiments","M56-citations","facts.json"),encoding="utf-8"))
cites = json.load(io.open(os.path.join(proj,"experiments","M56-citations","cites.json"),encoding="utf-8"))
nums = sorted(set(c["num"] for c in cites))
lo = int(sys.argv[1]); hi = int(sys.argv[2])
for n in nums:
    if not (lo <= n <= hi): continue
    r = facts[str(n)]
    print("="*100)
    print(f"FACT {n}  (SYNTHESIS.md:{r['line']})")
    print(r["text"])
    print("-"*40, "cited at:")
    for c in cites:
        if c["num"]==n:
            print(f"  {c['file']}:{c['line']}  {c['text'][:160]}")

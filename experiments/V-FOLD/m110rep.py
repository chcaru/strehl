import re,sys,io
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
t=open("docs/research/M110-sheet.md",encoding="utf-8").read()
for pat in ["9.73","14.22","61.0","58.7","62.89","62.9","half-max","inert null"]:
    print("#"*80); print("PATTERN:",pat)
    m=re.search(re.escape(pat), t)
    if not m: print("   NOT FOUND"); continue
    s=max(0,m.start()-900); e=min(len(t),m.start()+600)
    print(t[s:e])

import json,re
f = json.load(open("experiments/V-FOLD/facts.json",encoding="utf-8"))
for n in sorted(int(k) for k in f):
    r=f[str(n)]
    t=re.sub(r"\s+"," ",r["text"])
    nnum=len(re.findall(r"\d+\.?\d*\s*%|\d+\.\d{2,}", t))
    print(f'{n} {r["label"][:8]:8s} {r["src"][:9]:9s} num={nnum:3d} {t[:150]}')

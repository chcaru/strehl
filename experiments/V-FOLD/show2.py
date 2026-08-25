import json,re
f=json.load(open("experiments/V-FOLD/facts.json",encoding="utf-8"))
for n in [1567,1568,1569,1570,1571,1572,1573]:
    r=f[str(n)]
    print("="*110); print(n,"|",r["label"],"|",r["src"])
    print(re.sub(r"\s+"," ",r["text"]))

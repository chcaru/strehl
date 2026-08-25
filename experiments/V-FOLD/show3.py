import json,re
f=json.load(open("experiments/V-FOLD/facts.json",encoding="utf-8"))
for n in [1587,1588,1589,1593,1594]:
    r=f[str(n)]
    print("="*110); print(n,"|",r["label"],"|",r["src"])
    print(re.sub(r"\s+"," ",r["text"]))

import json,re,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
f=json.load(open("experiments/V-FOLD/facts.json",encoding="utf-8"))
import sys
for n in sys.argv[1:]:
    r=f[n]
    print("="*110); print(n,"|",r["label"],"|",r["src"])
    print(re.sub(r"\s+"," ",r["text"]))

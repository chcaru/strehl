import json
f = json.load(open("experiments/V-FOLD/facts.json",encoding="utf-8"))
for n in ["1595","1598","1599","1601","1662","1663"]:
    r = f[n]
    print("="*100)
    print(n, "|", r["label"], "|", r["src"], "| line", r["line"])
    print(r["text"])

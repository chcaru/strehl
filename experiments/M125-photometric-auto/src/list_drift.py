import json, sys
d = json.load(open(r"C:\dev\strehl-out\M122\drift-corpus.json"))
print(f"{'stack':<36}{'n':>5}{'sub':>4}{'Dpp':>10}  first..last")
for r in d:
    print(f"{r['stack']:<36}{r['n_used']:>5}{r['sub']:>4}{r['Dpp']:>10.4f}  "
          f"{r['first']}..{r['last']}")

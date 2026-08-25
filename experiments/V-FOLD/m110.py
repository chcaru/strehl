import json
for p in [r"C:\dev\strehl-out\M110-sheet\ca_overshoot_default_vs_ca.json", r"C:\dev\strehl-out\M110-sheet\ca_decile_default_vs_ca.json"]:
    d=json.load(open(p))
    print("="*90); print(p)
    def walk(o, pre="", depth=0):
        if depth>2: 
            print(pre, type(o).__name__, (str(o)[:200])); return
        if isinstance(o,dict):
            for k,v in o.items(): walk(v, pre+"/"+str(k), depth+1)
        elif isinstance(o,list):
            print(pre, f"list[{len(o)}]", str(o[:2])[:300])
        else:
            print(pre, "=", o)
    walk(d)

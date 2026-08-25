import json,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
r=json.load(open(r"C:\dev\strehl-out\M115-deconv-headroom\out\s05_ringing.json",encoding="utf-8"))
print(list(r.keys()))
for stack,v in r["ringing"].items():
    print("###",stack, {k:x for k,x in v.items() if not isinstance(x,(dict,list))})
    for arm,row in v["rows"].items():
        print("   ",arm, {k:(round(x,4) if isinstance(x,float) else x) for k,x in row.items() if not isinstance(x,(list,dict))})

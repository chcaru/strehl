import json,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
d=json.load(open(r"C:\dev\strehl-out\M115-deconv-headroom\out\s07_summary.json",encoding="utf-8"))
print("top:",list(d.keys()))
for arm,v in d["vs_GATE"].items():
    print("vs_GATE",arm, {k:vv for k,vv in v.items() if not isinstance(vv,list)})
b=d["BEST1"]["WIENER"]
for k in ("G_sig","G_noise","R_SNR"):
    o=b[k]
    print("BEST1/WIENER",k, {kk:vv for kk,vv in o.items() if not isinstance(vv,list)})
    print("   f[10]=",o["f"][10]," mean[10]=",o["mean"][10]," se[10]=",o.get("se",[None]*20)[10])
r=json.load(open(r"C:\dev\strehl-out\M115-deconv-headroom\out\s05_ringing.json",encoding="utf-8"))
def walk(o,pre=""):
    if isinstance(o,dict):
        for k,v in o.items(): yield from walk(v,pre+"/"+str(k))
    elif isinstance(o,list):
        yield pre+"[]", o[:6]
    else: yield pre,o
print("=== ringing keys")
for p,v in walk(r):
    if any(s in p.lower() for s in ("hull","out_pct","frac","shell","p999","halo")):
        print("  ",p,"=",str(v)[:160])

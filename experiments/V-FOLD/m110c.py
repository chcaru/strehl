import json
d=json.load(open(r"C:\dev\strehl-out\M110-sheet\ca_decile_default_vs_ca.json"))
print("top keys:", list(d.keys()))
for s,v in d["subjects"].items():
    print("#"*70, s)
    for k,val in v.items():
        if k in ("whole_frame","near_edges"):
            print("--",k, {kk:vv for kk,vv in val.items() if kk!="rows"})
            for r in val["rows"]:
                print("    ", r)
        elif k=="radial":
            for r in val: print("   radial", r)
        elif k=="controls":
            for r in val: print("   ctl", r)
        else:
            print("--",k,"=",str(val)[:600])

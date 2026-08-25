import json,os,sys,re,glob
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
def walk(o, pre=""):
    if isinstance(o,dict):
        for k,v in o.items(): yield from walk(v, pre+"/"+str(k))
    elif isinstance(o,list):
        for i,v in enumerate(o): yield from walk(v, pre+f"[{i}]")
    else:
        yield pre,o
targets=[float(x) for x in sys.argv[2:]]
files = glob.glob(sys.argv[1], recursive=True)
for p in files:
    try: d=json.load(open(p,encoding="utf-8"))
    except Exception as e: continue
    for path,v in walk(d):
        if isinstance(v,(int,float)) and not isinstance(v,bool):
            for t in targets:
                tol = abs(t)*2e-3 + 1e-9
                if abs(v-t)<=tol:
                    print(f"{t:<12} {os.path.basename(p):<28} {path} = {v}")
        elif isinstance(v,str):
            for t in targets:
                s = ("%g"%t)
                if s in v and len(v)<200:
                    print(f"{t:<12} {os.path.basename(p):<28} {path} ~ {v[:150]}")

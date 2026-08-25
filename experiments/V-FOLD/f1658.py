import os,re,json,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
targets=["536.2","118.7","14.9","24.7"]
# 1) whitespace-collapsed scan of every md under docs/
print("=== docs/**/*.md")
for root,dirs,files in os.walk("docs"):
    dirs[:]=[d for d in dirs if d not in (".git","__pycache__")]
    for f in files:
        if not f.endswith(".md"): continue
        p=os.path.join(root,f)
        flat=re.sub(r"\s+"," ",open(p,encoding="utf-8",errors="replace").read())
        for t in targets:
            for m in re.finditer(re.escape(t),flat):
                seg=flat[max(0,m.start()-90):m.start()+90]
                if "ppm" in seg or "CV" in seg or "cpl" in seg or "aperture" in seg.lower():
                    print(f"  [{t}] {p}: ...{seg}...")
print()
print("=== C:/dev/strehl-out/**/*.json  numeric hits (abs tol 0.05 on ppm scale, 0.0005 on fraction)")
def walk(base):
    for root,dirs,files in os.walk(base):
        dirs[:]=[d for d in dirs if d not in (".git","__pycache__")]
        for f in files:
            if f.endswith(".json"): yield os.path.join(root,f)
def rec(o,path,out):
    if isinstance(o,dict):
        for k,v in o.items(): rec(v,path+"/"+str(k),out)
    elif isinstance(o,list):
        for i,v in enumerate(o): rec(v,path+"[%d]"%i,out)
    elif isinstance(o,(int,float)) and not isinstance(o,bool):
        out.append((path,float(o)))
want=[536.2,118.7,14.9,24.7,0.149,0.247,536.2e-6,118.7e-6]
for p in walk(r"C:\dev\strehl-out"):
    try: d=json.load(open(p,encoding="utf-8",errors="replace"))
    except Exception: continue
    out=[]; rec(d,"",out)
    for path,v in out:
        for w in want:
            tol=max(abs(w)*0.0006,1e-9)
            if abs(v-w)<=tol:
                print(f"  {w} ~ {v!r}   {p}  {path}")

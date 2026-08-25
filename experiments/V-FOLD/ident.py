import re,glob,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
pats=["0x010f","0x0110",'"Make"','"Model"',"LensSpec","maker_note","MakerNote","focal","FocalLength","0x829a","exposure_time"]
files=[p for p in glob.glob("crates/**/*.rs",recursive=True)]
prod=[p for p in files if "/tests/" not in p.replace("\\","/")]
print("production .rs files:",len(prod),"of",len(files))
for pat in pats:
    hits=[]
    for p in prod:
        t=open(p,encoding="utf-8",errors="replace").read()
        for i,l in enumerate(t.split("\n")):
            if pat.lower() in l.lower(): hits.append((p,i+1,l.strip()[:110]))
    print(f"-- {pat}: {len(hits)}")
    for h in hits[:4]: print("     ",h[0]+":"+str(h[1]),h[2])

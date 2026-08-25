import re,os,sys,glob
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
pats=["500.8","348.0","30.5%","1.037","1.027","0.851","0.673","0.813"]
roots=["docs","experiments","scripts"]
hits={p:[] for p in pats}
for r in roots:
    for dp,dn,fn in os.walk(r):
        dn[:]=[d for d in dn if d not in (".git","__pycache__","target") and not d.startswith(".cargo")]
        for f in fn:
            if not f.endswith((".md",".py",".txt",".json",".ps1")): continue
            fp=os.path.join(dp,f)
            try: t=open(fp,encoding="utf-8",errors="replace").read()
            except: continue
            c=re.sub(r"\s+"," ",t)
            for p in pats:
                if p in c: hits[p].append(fp)
for p in pats:
    print(p, "->", len(hits[p]), hits[p][:8])

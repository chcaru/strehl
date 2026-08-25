import re,sys,json
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
t=open("docs/research/M113-spectral.md",encoding="utf-8",errors="replace").read()
flat=re.sub(r"\s+"," ",t)
for pat in ["aperture","converter","radial","15 ppm","f/5.6","f/"]:
    idxs=[m.start() for m in re.finditer(re.escape(pat),flat,re.I)]
    print(f"### {pat!r}: {len(idxs)}")
    for i in idxs[:4]:
        print("   ...",flat[max(0,i-300):i+300].replace("|","/"),"...\n")
print("="*100)
d=json.load(open(r"C:\dev\strehl-out\M113-spectral\s3_analyse.json",encoding="utf-8"))
print(json.dumps(d,indent=1)[:3000])

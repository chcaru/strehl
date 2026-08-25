import sys,re
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
t=open("docs/research/M113-ca.md",encoding="utf-8",errors="replace").read()
flat=re.sub(r"\s+"," ",t)
for pat in ["536.2","118.7","14.9","24.7","3.5 ppm","f/5.6","aperture","LensType3","every -cpl","no aperture contrast"]:
    idxs=[m.start() for m in re.finditer(re.escape(pat),flat)]
    print(f"### {pat!r}: {len(idxs)} hits")
    for i in idxs[:3]:
        print("   ...",flat[max(0,i-260):i+260].replace("|","\\|"),"...")
    print()

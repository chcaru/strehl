import re,sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
for f in ["docs/research/M113-spectral.md","docs/research/M113-ca.md"]:
    t=open(f,encoding="utf-8",errors="replace").read()
    flat=re.sub(r"\s+"," ",t)
    print("#"*30,f)
    for pat in [r"radial[^.]{0,400}",r"\+/-\s?15|\u00b115|15 ppm|\+/- 15"]:
        for m in list(re.finditer(pat,flat,re.I))[:6]:
            print("  >>",flat[max(0,m.start()-200):m.start()+400].replace("|","/"))
            print()

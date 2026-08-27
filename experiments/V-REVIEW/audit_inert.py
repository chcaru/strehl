import subprocess, pathlib, numpy as np, tifffile, os
NEW=r"C:\dev\strehl-out\V-REVIEW\target\release\strehl.exe"
OUT=pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\sweep")
def render(sub,tag,extra):
    o=OUT/(tag+".tiff")
    if o.exists(): o.unlink()
    r=subprocess.run([NEW,"stack",sub,"--out",str(o),"--limit","4"]+extra,capture_output=True)
    log=(r.stdout+r.stderr).decode("utf8","replace")
    return (o if (r.returncode==0 and o.exists()) else None), log
def ld(o):
    a=tifffile.imread(str(o)); os.remove(o); return a

print("=== help text for the inert flags ===")
h=subprocess.run([NEW,"stack","--help"],capture_output=True)
ht=(h.stdout+h.stderr).decode("utf8","replace").splitlines()
for want in ["--fix-ca","--demosaic","--target-n-eff","--confidence-tail","--stats-placebo","--flat-roi"]:
    for i,l in enumerate(ht):
        if l.strip().startswith(want):
            print("  "+l.strip()[:110])
            for j in range(1,3):
                if i+j<len(ht) and ht[i+j].strip() and not ht[i+j].strip().startswith("-"):
                    print("      "+ht[i+j].strip()[:106])
            break

SUB=r"D:\personal\macro\109MSDCF"
print("\n=== --confidence-tail: was it silently ACCEPTED on a backend that ignores it? ===")
a,_=render(SUB,"ct_base",["--srgb","--merge","estimator"])
b,_=render(SUB,"ct_test",["--srgb","--merge","estimator","--confidence-tail","0.2"])
if a and b:
    A,B=ld(a),ld(b); n=int(np.count_nonzero(A!=B))
    print("  on ESTIMATOR: %.4f%% samples moved -> %s" % (100.0*n/A.size, "potent" if n else "INERT"))
c,log=render(SUB,"ct_pyr",["--srgb","--merge","pyramid","--confidence-tail","0.2"])
print("  on PYRAMID  : accepted=%s  (a flag the backend cannot use, taken without complaint)" % (c is not None))
if c: os.remove(c)

print("\n=== --target-n-eff on estimator, larger step ===")
d,_=render(SUB,"tn",["--srgb","--merge","estimator","--target-n-eff","1"])
if a is not None and d:
    A2=tifffile.imread(str(OUT/"ct_base.tiff")) if (OUT/"ct_base.tiff").exists() else None
    D=ld(d)
    print("  --target-n-eff 1 vs baseline: %s" % ("cannot compare, baseline consumed" if A2 is None else "%.4f%% moved"%(100.0*np.count_nonzero(D!=A2)/D.size)))

print("\n=== --demosaic: is it simply implied by --srgb? ===")
e,_=render(SUB,"dm1",["--merge","pyramid","--demosaic"])
f,_=render(SUB,"dm2",["--merge","pyramid","--binned"])
if e and f:
    E,F=ld(e),ld(f)
    print("  --demosaic shape %s ; --binned shape %s -> different stages, so --demosaic IS doing something vs --binned" % (E.shape,F.shape))

print("\n=== --stats-placebo: why unrunnable? ===")
g,log=render(SUB,"sp",["--srgb","--merge","estimator","--stats-placebo"])
print("  " + [l for l in log.splitlines() if l.strip()][-2:][0][:150])

print("\n=== --fix-ca: does its profile apply to THIS subject's gear? ===")
for sub in [r"D:\personal\macro\109MSDCF", r"D:\personal\macro\leaf-2-cpl"]:
    if not pathlib.Path(sub).exists(): print("  %s MISSING" % sub); continue
    b1,_=render(sub,"ca0",["--srgb","--merge","pyramid"])
    b2,log=render(sub,"ca1",["--srgb","--merge","pyramid","--fix-ca","a7c2-fe100gm-2xtc-x4cpl"])
    if b1 and b2:
        A,B=ld(b1),ld(b2); n=int(np.count_nonzero(A!=B))
        note=[l.strip() for l in log.splitlines() if "ca" in l.lower() and ("profile" in l.lower() or "lateral" in l.lower())]
        print("  %-34s %.4f%% moved   %s" % (pathlib.Path(sub).name, 100.0*n/A.size, (note[0][:80] if note else "")))

import subprocess, hashlib, pathlib, os, numpy as np, tifffile
EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
DIR = r"D:\personal\macro\coffee-bubbles"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\diff")
ENV = {k:v for k,v in os.environ.items() if not k.startswith("STREHL_")}
def run(tag,args):
    o=OUT/(tag+".tif")
    if o.exists(): o.unlink()
    p=subprocess.run([EXE,"stack",DIR,"--limit","3","--out",str(o)]+args,
                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV)
    return o,p.stdout.decode("utf8","replace")
def stat(o):
    a=tifffile.imread(o).astype(np.float64)
    return hashlib.sha256(o.read_bytes()).hexdigest()[:16].upper(), a.mean(), a.max()

print("="*104)
print("--srgb --binned : does ANY exposure value move a pixel?")
print("="*104)
print("  %-14s %-18s %12s %10s  %s" % ("exposure","hash","mean DN","max DN","verdict"))
o,_=run("bz_base",["--srgb","--binned"]); hb,mb,xb=stat(o)
print("  %-14s %-18s %12.2f %10.0f  baseline" % ("(none)",hb,mb,xb))
for s in ["-3.0","-1.0","0.5","2.0","4.0"]:
    o,log=run("bz_"+s.replace(".","_").replace("-","m"),["--srgb","--binned","--exposure",s])
    h,m,x=stat(o)
    print("  %-14s %-18s %12.2f %10.0f  %s" % (s,h,m,x,"IDENTICAL to baseline" if h==hb else "moves"))
print("\n  what the tool SAYS it did, and which writer ran:")
o,log=run("bz_say",["--srgb","--binned","--exposure","4.0"])
for L in log.split("\n"):
    if L.startswith("exposure") or L.startswith("wrote") or "binned" in L.lower(): print("     "+L.strip()[:150])

print("\n" + "="*104)
print("CONTROL: the same sweep on --srgb WITHOUT --binned (known-working path)")
print("="*104)
o,_=run("dz_base",["--srgb"]); hb2,mb2,_=stat(o)
print("  %-14s %-18s %12.2f  baseline" % ("(none)",hb2,mb2))
for s in ["-3.0","2.0"]:
    o,_=run("dz_"+s.replace(".","_").replace("-","m"),["--srgb","--exposure",s])
    h,m,x=stat(o)
    print("  %-14s %-18s %12.2f  %s" % (s,h,m,"IDENTICAL" if h==hb2 else "moves"))

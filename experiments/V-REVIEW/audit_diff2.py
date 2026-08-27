"""RE-RUN of the flag audit on PIXELS, not file bytes.
The first pass hashed whole files; TIFF metadata rides in that hash, so a flag that
records itself in the header but never touches the image read as 'works'. That
produced a FALSE ACQUITTAL of --exposure. This compares pixel arrays."""
import subprocess, pathlib, os, numpy as np, tifffile, sys
EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
DIR = r"D:\personal\macro\coffee-bubbles"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\diff2"); OUT.mkdir(parents=True, exist_ok=True)
ENV = {k:v for k,v in os.environ.items() if not k.startswith("STREHL_")}
def render(tag,args):
    o=OUT/(tag+".tif")
    if o.exists(): o.unlink()
    p=subprocess.run([EXE,"stack",DIR,"--out",str(o)]+args,
                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV)
    return (o if o.exists() else None), p.returncode, p.stdout.decode("utf8","replace")
L3=["--limit","3"]
def same(a,b):
    if a is None or b is None: return None
    A,B = tifffile.imread(a), tifffile.imread(b)
    if A.shape != B.shape: return False
    return bool(np.array_equal(A,B))

print("="*104); print("COMMISSIONING (on pixels)"); print("="*104)
o1,_,_ = render("base",L3); o2,_,_ = render("base_rerun",L3)
det = same(o1,o2)
o3,rc3,_ = render("lim4",["--limit","4"])
pot = same(o1,o3)
print("  determinism null  same cmd twice        : pixels identical = %s   %s" % (det,"pass" if det else "FAIL"))
print("  potency arm       --limit 3 vs --limit 4: pixels identical = %s   %s" % (pot,"pass" if pot is False else "FAIL"))
if not det or pot is not False: sys.exit("COMMISSIONING FAILED")

CASES = [
 ("--demosaic",         L3+["--demosaic"],                      L3),
 ("--srgb",             L3+["--srgb"],                          L3),
 ("--linear-srgb",      L3+["--linear-srgb"],                   L3),
 ("--resampler",        L3+["--resampler","lanczos3"],          L3),
 ("--pyramid-bands",    L3+["--pyramid-bands","3"],             L3),
 ("--pyramid-gate",     L3+["--pyramid-gate","9.0"],            L3),
 ("--pyramid-exponent", L3+["--pyramid-exponent","4.0"],        L3),
 ("--pyramid-sharpen",  L3+["--pyramid-sharpen","2.0"],         L3),
 ("--pyramid-select",   L3+["--pyramid-select","hard-max"],     L3),
 ("--pyramid-base",     L3+["--pyramid-base","weighted"],       L3),
 ("--fix-ca",           L3+["--fix-ca","a7c2-fe90m28g-2x"],     L3),
 ("--exposure",         L3+["--srgb","--exposure","2.0"],       L3+["--srgb"]),
 ("--auto-exposure",    L3+["--srgb","--auto-exposure"],        L3+["--srgb"]),
 ("--binned",           L3+["--srgb","--binned"],               L3+["--srgb"]),
 ("--gate",             L3+["--merge","estimator","--photometric","off","--gate","8.0"], L3+["--merge","estimator","--photometric","off"]),
 ("--photometric off",  L3+["--merge","estimator","--photometric","off"], L3+["--merge","estimator","--photometric","on"]),
 ("--stats",            L3+["--merge","estimator","--photometric","off","--stats"], L3+["--merge","estimator","--photometric","off"]),
 ("--confidence-tail",  L3+["--merge","estimator","--photometric","off","--confidence-tail","0.5"], L3+["--merge","estimator","--photometric","off"]),
 ("--target-n-eff",     L3+["--merge","estimator","--photometric","off","--target-n-eff","4"], L3+["--merge","estimator","--photometric","off"]),
]
bases={}
print(); print("="*104); print("FLAG -> DOES IT CHANGE A PIXEL?"); print("="*104)
print("  %-20s %-11s %s" % ("flag","pixels","verdict")); print("  "+"-"*98)
for flag,args,basargs in CASES:
    key=tuple(basargs)
    if key not in bases: bases[key]=render("B%d"%(abs(hash(key))%99999),basargs)[0]
    o,rc,log = render(flag.strip("-").replace("-","_").replace(" ","_"),args)
    if o is None:
        err=[x for x in log.strip().split("\n") if x.startswith("Error") or "error:" in x]
        print("  %-20s %-11s REFUSED rc=%d  %s" % (flag,"n/a",rc,(err[-1] if err else "")[:58])); continue
    s = same(bases[key],o)
    print("  %-20s %-11s %s" % (flag,"identical" if s else "differ",
          "*** NO-OP ON PIXELS ***" if s else "changes the image"))

import subprocess, pathlib, os, numpy as np, tifffile, sys
EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
DIR = r"D:\personal\macro\coffee-bubbles"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\denv"); OUT.mkdir(parents=True, exist_ok=True)
BASEENV = {k:v for k,v in os.environ.items() if not k.startswith("STREHL_")}
def render(tag,args,env=None):
    o=OUT/(tag+".tif")
    if o.exists(): o.unlink()
    e=dict(BASEENV); e.update(env or {})
    p=subprocess.run([EXE,"stack",DIR,"--limit","3","--out",str(o)]+args,
                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=e)
    return (o if o.exists() else None), p.returncode, p.stdout.decode("utf8","replace")
def same(a,b):
    if a is None or b is None: return None
    A,B=tifffile.imread(a),tifffile.imread(b)
    return A.shape==B.shape and bool(np.array_equal(A,B))

b,_,blog = render("base",[])
r,_,_    = render("rerun",[])
print("commissioning: determinism = %s" % same(b,r))
p,_,_    = render("pot",["--pyramid-bands","3"])
print("commissioning: potency     = %s (must be False)" % same(b,p))
if not same(b,r) or same(b,p): sys.exit("COMMISSIONING FAILED")

print("\n"+"="*104)
print("ENV VAR -> does it change the shipping `stack` output? (documented ones first)")
print("="*104)
CASES=[("STREHL_ALIGN","0",[],"documented in `stack --help`"),
       ("STREHL_MERGE","estimator",["--photometric","off"],"documented in `stack --help`"),
       ("STREHL_PHOTOMETRIC","off",["--merge","estimator"],"documented in `stack --help`"),
       ("STREHL_SOFT_GATE","1",["--merge","estimator","--photometric","off"],"NOT in --help"),
       ("STREHL_SOFT_GATE","4.0",["--merge","estimator","--photometric","off"],"NOT in --help"),
       ("STREHL_ROBUST_ELECTION","1",["--merge","estimator","--photometric","off"],"NOT in --help"),
       ("STREHL_EDGE_AWARE","0",["--merge","estimator","--photometric","off"],"NOT in --help")]
bases={}
print("  %-24s %-10s %-13s %s" % ("variable","value","pixels","note"))
print("  "+"-"*100)
for var,val,extra,note in CASES:
    key=tuple(extra)
    if key not in bases: bases[key]=render("b%d"%(abs(hash(key))%9999),list(extra))[0]
    o,rc,log = render(("%s_%s"%(var,val)).replace(".","_"),list(extra),{var:val})
    if o is None: print("  %-24s %-10s %-13s REFUSED rc=%d" % (var,val,"n/a",rc)); continue
    s=same(bases[key],o)
    print("  %-24s %-10s %-13s %s%s" % (var,val,"identical" if s else "differ",
          note, "   <== NO EFFECT" if s else ""))
print("\n  does the base run mention alignment at all?")
for L in blog.split("\n"):
    if "align" in L.lower() and len(L.strip())>0: print("    "+L.strip()[:120])

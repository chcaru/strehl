import subprocess, pathlib, os, numpy as np, tifffile
EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
DIR = r"D:\personal\macro\coffee-bubbles"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\denv2"); OUT.mkdir(parents=True, exist_ok=True)
BASEENV={k:v for k,v in os.environ.items() if not k.startswith("STREHL_")}
def render(tag,args,env=None):
    o=OUT/(tag+".tif")
    if o.exists(): o.unlink()
    e=dict(BASEENV); e.update(env or {})
    p=subprocess.run([EXE,"stack",DIR,"--limit","3","--out",str(o)]+args,
                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=e)
    return (o if o.exists() else None),p.returncode,p.stdout.decode("utf8","replace")

print("="*104)
print("RETEST: my earlier baselines used --photometric off, which INFERS the estimator.")
print("        Re-run STREHL_MERGE against a genuine pyramid baseline.")
print("="*104)
b,rcb,logb = render("pyr_base",[])
bk=[L.strip() for L in logb.split("\n") if L.strip().startswith("backend")]
print("  pyramid baseline rc=%d   %s" % (rcb, bk[0] if bk else ""))
o,rc,log = render("env_est",[],{"STREHL_MERGE":"estimator"})
bk2=[L.strip() for L in log.split("\n") if L.strip().startswith("backend")]
print("  STREHL_MERGE=estimator rc=%d   %s" % (rc, bk2[0] if bk2 else ""))
if o is None:
    err=[L for L in log.strip().split("\n") if L.startswith("Error")]
    print("     -> no image written; error: %s" % (err[-1][:110] if err else "?"))
    print("     -> the env var DID switch backend (it reached the estimator's photometric refusal)")
print()
print("  what the log says the backend was, in each case:")
for L in logb.split("\n"):
    if "backend" in L.lower(): print("     base:  "+L.strip()[:110])
for L in log.split("\n"):
    if "backend" in L.lower(): print("     env :  "+L.strip()[:110])

print("\n"+"="*104); print("STREHL_SOFT_GATE -> rc=101 is a Rust PANIC. What does it say?"); print("="*104)
for v in ["1","4.0","on"]:
    o,rc,log = render("sg_"+v.replace(".","_"),["--merge","estimator","--photometric","off"],{"STREHL_SOFT_GATE":v})
    tail=[L for L in log.strip().split("\n") if L.strip()][-2:]
    print("  STREHL_SOFT_GATE=%-5s rc=%-4d %s" % (v,rc," | ".join(t.strip()[:96] for t in tail)))

import subprocess, hashlib, pathlib, os
EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
DIR = r"D:\personal\macro\coffee-bubbles"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\diff")
ENV = {k:v for k,v in os.environ.items() if not k.startswith("STREHL_")}
def run(tag,args):
    o=OUT/(tag+".tif")
    if o.exists(): o.unlink()
    p=subprocess.run([EXE,"stack",DIR,"--limit","3","--out",str(o)]+args,
                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV)
    h=hashlib.sha256(o.read_bytes()).hexdigest()[:16].upper() if o.exists() else "NO-OUTPUT"
    return h,p.returncode,p.stdout.decode("utf8","replace")

print("="*100)
print("IS --exposure A NO-OP ANYWHERE? test every render path that accepts it")
print("="*100)
paths = [("srgb (demosaic branch, the default for --srgb)", ["--srgb"]),
         ("srgb --binned  (binned branch)",                 ["--srgb","--binned"]),
         ("srgb --demosaic (explicit)",                     ["--srgb","--demosaic"])]
for label, base in paths:
    hb,_,_ = run("xb_"+str(abs(hash(label))%9999), base)
    he,rc,log = run("xe_"+str(abs(hash(label))%9999), base+["--exposure","2.0"])
    same = (hb==he)
    print("  %-46s base=%s  +exposure=%s  %s" % (label, hb, he, "*** NO-OP ***" if same else "applies (works)"))
    for L in log.split("\n"):
        if L.startswith("exposure"): print("        log says: " + L.strip())

print("\n" + "="*100)
print("--gate on the estimator, with the photometric blocker removed")
print("="*100)
hb,rcb,_ = run("eg_base",["--merge","estimator","--photometric","off"])
print("  estimator baseline (photometric off)      rc=%d  %s" % (rcb,hb))
for g in ["2.0","8.0","20.0"]:
    h,rc,_ = run("eg_"+g.replace(".","_"),["--merge","estimator","--photometric","off","--gate",g])
    print("  --gate %-5s                              rc=%d  %s  %s" % (g,rc,h,"SAME AS BASELINE" if h==hb else "differs"))

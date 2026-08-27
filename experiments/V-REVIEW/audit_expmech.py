import subprocess, pathlib, os, numpy as np, tifffile
EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
DIR = r"D:\personal\macro\coffee-bubbles"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\diff3"); OUT.mkdir(parents=True, exist_ok=True)
ENV = {k:v for k,v in os.environ.items() if not k.startswith("STREHL_")}
def render(tag,args):
    o=OUT/(tag+".tif")
    if o.exists(): o.unlink()
    p=subprocess.run([EXE,"stack",DIR,"--limit","3","--out",str(o)]+args,
                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV)
    log=p.stdout.decode("utf8","replace")
    line=[L.strip() for L in log.split("\n") if L.startswith("exposure")]
    return (o if o.exists() else None), (line[0] if line else "(no exposure line)")

cases=[("base",["--srgb"]),("m2",["--srgb","--exposure","-2.0"]),
       ("p2",["--srgb","--exposure","2.0"]),("auto",["--srgb","--auto-exposure"])]
imgs={}
print("="*104); print("--srgb : four exposure states, what the tool SAYS and what the PIXELS do"); print("="*104)
for t,a in cases:
    o,line = render(t,a); imgs[t]=o
    print("  %-6s %-28s %s" % (t," ".join(a[1:]) or "(none)", line))
print()
b=tifffile.imread(imgs["base"]).astype(np.float64)
print("  %-8s %14s %14s %14s %10s" % ("case","mean DN","p99 DN","max DN","== base?"))
for t,_ in cases:
    a=tifffile.imread(imgs[t]).astype(np.float64)
    eq=np.array_equal(a,b)
    print("  %-8s %14.4f %14.1f %14.1f %10s" % (t,a.mean(),np.percentile(a,99),a.max(),eq))
print()
for t in ("m2","p2","auto"):
    a=tifffile.imread(imgs[t]).astype(np.int64); d=a-b.astype(np.int64)
    nz=(d!=0)
    print("  %-6s vs base : %d px differ (%.4f%%)  max|delta|=%d  mean delta=%+.4f"
          % (t,nz.sum(),100*nz.mean(),np.abs(d).max(),d.mean()))

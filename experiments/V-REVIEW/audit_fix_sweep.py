import subprocess, pathlib, numpy as np, tifffile, hashlib
NEW = r"C:\dev\strehl-out\V-REVIEW\target\release\strehl.exe"
SUB = r"D:\personal\macro\109MSDCF"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\fix"); OUT.mkdir(parents=True, exist_ok=True)
print("binary:", NEW, "exists:", pathlib.Path(NEW).exists())

def run(tag, extra):
    o=OUT/(tag+".tiff")
    if o.exists(): o.unlink()
    r=subprocess.run([NEW,"stack",SUB,"--out",str(o)]+extra, capture_output=True)
    log=(r.stdout+r.stderr).decode("utf8","replace")
    if r.returncode!=0 or not o.exists():
        return None, log
    return o, log

print("\n=== does the FIXED binary still refuse --exposure on the linear path? ===")
o,log = run("lin", ["--linear-srgb","--exposure=3"])
print("  linear+exposure -> %s" % ("REFUSED: "+[l for l in log.splitlines() if "Error" in l][0][:100] if o is None else "ACCEPTED"))

print("\n=== DETERMINISM ARM (fixed binary) ===")
a,_=run("det1",["--srgb","--exposure=3"]); b,_=run("det2",["--srgb","--exposure=3"])
A=tifffile.imread(str(a)); B=tifffile.imread(str(b))
print("  identical flags twice -> identical pixels: %s" % np.array_equal(A,B))

print("\n=== PIXEL SWEEP on the FIXED binary, --srgb, 109MSDCF 22 frames ===")
vals=["-6","-3","-1","0","1","2","2.60","3","6"]
arr={}
for v in vals:
    o,log=run("f"+v.replace(".","p").replace("-","m"), ["--srgb","--exposure=%s"%v])
    if o is None:
        print("  --exposure=%-5s FAILED" % v); continue
    x=tifffile.imread(str(o)); arr[v]=x
    print("  --exposure=%-5s mean DN %12.4f  max %5d  clipped %.3f%%" % (
        v, x.mean(), int(x.max()), 100.0*np.count_nonzero(x==65535)/x.size))

ks=[v for v in vals if v in arr]
print("\n=== distinct output groups ===")
groups=[]
for v in ks:
    for g in groups:
        if np.array_equal(arr[v],arr[g[0]]): g.append(v); break
    else: groups.append([v])
for n,g in enumerate(groups,1): print("  group %d: %s" % (n,", ".join(g)))
print("  => %d distinct images from %d exposure settings" % (len(groups),len(ks)))

print("\n=== DELIVERED vs COMMANDED (the property the fix claims) ===")
if "0" in arr:
    ref=arr["0"].astype(np.float64)
    m=(ref>0)&(ref<65535)
    print("  %-8s %-12s %-12s %s" % ("stops","commanded","delivered","%samples moved vs 0"))
    for v in ks:
        g=2.0**float(v)
        y=arr[v].astype(np.float64)
        mm=m&(y<65535)
        slope=float((ref[mm]*y[mm]).sum()/max((ref[mm]*ref[mm]).sum(),1e-9))
        moved=100.0*np.count_nonzero(arr[v]!=arr["0"])/ref.size
        print("  %-8s %-12.4f %-12.6f %.3f%%" % (v,g,slope,moved))

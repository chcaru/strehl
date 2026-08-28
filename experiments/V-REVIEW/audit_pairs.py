import subprocess, pathlib, numpy as np, tifffile, os, gc
NEW=r"C:\dev\strehl-out\V-REVIEW\target\release\strehl.exe"
SUB=r"D:\personal\macro\109MSDCF"
OUT=pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\head")
FULL=65535.0
def render(tag,extra):
    o=OUT/(tag+".tiff")
    if o.exists(): o.unlink()
    r=subprocess.run([NEW,"stack",SUB,"--out",str(o),"--limit","4","--srgb","--merge","pyramid"]+extra,capture_output=True)
    return o if (r.returncode==0 and o.exists()) else None
def s_fwd(x,c): return x + (x*x*(3.0-2.0*x) - x)*c
def srgb_dec(e): return np.where(e<=0.040_448_237, e/12.92, ((e+0.055)/1.055)**2.4)
C=0.55
codes=np.arange(65536,dtype=np.float64)/FULL
lo=np.zeros_like(codes); hi=np.ones_like(codes)
for _ in range(60):
    mid=(lo+hi)/2.0; f=s_fwd(mid,C)
    lo=np.where(f<codes,mid,lo); hi=np.where(f<codes,hi,mid)
LUT=srgb_dec(np.clip((lo+hi)/2.0,0,1))
def sl(x,y):
    sxx=float(x@x); return float(x@y)/sxx if sxx>0 else float("nan")

paths={}
for v in ["-2","-1","0","1"]:
    paths[v]=render("r"+v.replace("-","m"),["--exposure",v])
cache={}
def get(v):
    if v not in cache:
        X=tifffile.imread(str(paths[v])); cache[v]=(X.ravel().copy(), LUT[X.astype(np.int64)].ravel()); del X; gc.collect()
    return cache[v]

print("=== ratios BETWEEN exposures. Is `--exposure 0` the odd one out? ===")
print("  %-22s %-12s %-14s %-10s %s" % ("pair","commanded","delivered","%err","n"))
for a,b in [("-2","-1"),("-1","0"),("0","1"),("-1","1"),("-2","1")]:
    Ac,Al=get(a); Bc,Bl=get(b)
    k=(Ac>0)&(Ac<65535)&(Bc>0)&(Bc<65535)
    cmd=2.0**(float(b)-float(a))
    g=sl(Al[k],Bl[k])
    print("  %-22s %-12.6f %-14.7f %+-10.4f %d" % ("%s -> %s"%(a,b),cmd,g,100*(g/cmd-1),int(k.sum())))

print("\n=== same, restricted to samples far from the ceiling (both < 50%) ===")
print("  %-22s %-12s %-14s %-10s %s" % ("pair","commanded","delivered","%err","n"))
for a,b in [("-2","-1"),("-1","0"),("0","1"),("-1","1")]:
    Ac,Al=get(a); Bc,Bl=get(b)
    k=(Ac>0)&(Ac<0.5*65535)&(Bc>0)&(Bc<0.5*65535)
    cmd=2.0**(float(b)-float(a))
    g=sl(Al[k],Bl[k])
    print("  %-22s %-12.6f %-14.7f %+-10.4f %d" % ("%s -> %s"%(a,b),cmd,g,100*(g/cmd-1),int(k.sum())))
for p in paths.values():
    try: os.remove(p)
    except Exception: pass

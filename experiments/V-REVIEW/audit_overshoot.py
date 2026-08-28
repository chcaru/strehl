import subprocess, pathlib, numpy as np, tifffile, os, gc
NEW=r"C:\dev\strehl-out\V-REVIEW\target\release\strehl.exe"
SUB=r"D:\personal\macro\109MSDCF"
OUT=pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\head")
FULL=65535.0
def render(tag,extra):
    o=OUT/(tag+".tiff")
    if o.exists(): o.unlink()
    r=subprocess.run([NEW,"stack",SUB,"--out",str(o),"--limit","4","--srgb","--merge","pyramid"]+extra,capture_output=True)
    return (o if (r.returncode==0 and o.exists()) else None)
def s_fwd(x,c): return x + (x*x*(3.0-2.0*x) - x)*c
def srgb_dec(e): return np.where(e<=0.040_448_237, e/12.92, ((e+0.055)/1.055)**2.4)
C=0.55
codes=np.arange(65536,dtype=np.float64)/FULL
lo=np.zeros_like(codes); hi=np.ones_like(codes)
for _ in range(60):
    mid=(lo+hi)/2.0; f=s_fwd(mid,C)
    lo=np.where(f<codes,mid,lo); hi=np.where(f<codes,hi,mid)
LUT=srgb_dec(np.clip((lo+hi)/2.0,0,1))
def slope(x,y):
    sxx=float(x@x); return float(x@y)/sxx if sxx>0 else float("nan")

b=render("z0",["--exposure","0"]); B=tifffile.imread(str(b)); Bc=B.ravel(); Bl=LUT[B.astype(np.int64)].ravel(); del B; gc.collect()
print("=== IS THE OVERSHOOT CONFINED TO THE HIGHLIGHTS? (knee sits at 0.60 of ceiling) ===")
print("  stratified by BASE code level; a gain error is level-independent, a knee effect is not\n")
for v in ["1","2"]:
    o=render("z"+v,["--exposure",v])
    X=tifffile.imread(str(o)); Xc=X.ravel(); Xl=LUT[X.astype(np.int64)].ravel(); del X; gc.collect()
    cmd=2.0**float(v)
    print("  --exposure %s  (commanded %.4f)" % (v,cmd))
    print("    %-24s %-14s %-12s %s" % ("base band (of ceiling)","delivered","%err","n"))
    for name,loF,hiF in [("0-20%",0.00,0.20),("20-40%",0.20,0.40),("40-60%",0.40,0.60),
                         ("60-80%",0.60,0.80),("80-100%",0.80,1.00),("all unclipped",0.0,1.0)]:
        k=(Bc>loF*65535)&(Bc<=hiF*65535)&(Bc>0)&(Bc<65535)&(Xc>0)&(Xc<65535)
        n=int(k.sum())
        if n<50000: print("    %-24s %-14s %-12s %d" % (name,"-","too few",n)); continue
        g=slope(Bl[k],Xl[k])
        print("    %-24s %-14.7f %+-12.4f %d" % (name,g,100*(g/cmd-1),n))
    del Xc,Xl; gc.collect(); os.remove(o)
os.remove(b)

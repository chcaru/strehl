import subprocess, pathlib, numpy as np, tifffile, os, gc, re
NEW=r"C:\dev\strehl-out\V-REVIEW\target\release\strehl.exe"
SUB=r"D:\personal\macro\109MSDCF"
OUT=pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\head"); OUT.mkdir(parents=True,exist_ok=True)
FULL=65535.0
def render(tag,extra):
    o=OUT/(tag+".tiff")
    if o.exists(): o.unlink()
    r=subprocess.run([NEW,"stack",SUB,"--out",str(o),"--limit","4","--srgb","--merge","pyramid"]+extra,capture_output=True)
    return (o if (r.returncode==0 and o.exists()) else None),(r.stdout+r.stderr).decode("utf8","replace")

# --- the tool's own curve, transcribed from image_out.rs:1035 ---
def s_fwd(x,c): return x + (x*x*(3.0-2.0*x) - x)*c
def srgb_dec(e): return np.where(e<=0.040_448_237, e/12.92, ((e+0.055)/1.055)**2.4)
def srgb_enc(v): return np.where(v<=0.003_130_8, 12.92*v, 1.055*np.power(v,1/2.4)-0.055)

base,log=render("q0",["--exposure","0"])
mc=re.search(r"contrast\s+([0-9.]+)", log) or re.search(r"contrast[^0-9]*([0-9.]+)", log)
CONTRAST=float(mc.group(1)) if mc else 0.55
print("contrast read from the render banner: %s%s" % (CONTRAST, "" if mc else "  (BANNER NOT FOUND - assumed)"))
for l in log.splitlines():
    if "tone" in l.lower() or "contrast" in l.lower(): print("  banner: "+l.strip()[:100])

# --- inverse LUT by bisection on the monotone forward curve ---
codes=np.arange(65536, dtype=np.float64)/FULL
lo=np.zeros_like(codes); hi=np.ones_like(codes)
for _ in range(60):
    mid=(lo+hi)/2.0
    f=s_fwd(mid,CONTRAST)
    lo=np.where(f<codes, mid, lo); hi=np.where(f<codes, hi, mid)
LUT=srgb_dec(np.clip((lo+hi)/2.0,0.0,1.0))
print("LUT built: monotone=%s  range %.3e .. %.6f" % (bool(np.all(np.diff(LUT)>=0)), LUT[1], LUT[-1]))

def slope(x,y):
    sxx=float(x@x); return float(x@y)/sxx if sxx>0 else float("nan")

print("\n=== COMMISSIONING the inversion chain on PLANTED gains (independent of the author) ===")
rng=np.random.default_rng(7)
lin=np.clip(rng.random(400000)**2 * 0.45 + 0.0005, 0, 1)
for planted in (2.0,0.5,1.0,1.3):
    enc_a=np.clip(np.floor(s_fwd(srgb_enc(lin),CONTRAST)*FULL+0.5),0,FULL).astype(np.int64)
    enc_b=np.clip(np.floor(s_fwd(srgb_enc(np.clip(lin*planted,0,1)),CONTRAST)*FULL+0.5),0,FULL).astype(np.int64)
    A=LUT[enc_a]; B=LUT[enc_b]
    k=(enc_a>0)&(enc_a<65535)&(enc_b>0)&(enc_b<65535)
    got=slope(A[k],B[k])
    print("  planted %-5s -> recovered %.7f  (%+.4f%%)  n=%d  %s" % (planted,got,100*(got/planted-1),int(k.sum()),
          "PASS" if abs(got/planted-1)<0.002 else "FAIL"))

BASE=tifffile.imread(str(base)); Bl=LUT[BASE.astype(np.int64)].ravel(); Bc=BASE.ravel()
del BASE; gc.collect()
print("\n=== DELIVERED GAIN IN LINEAR LIGHT, at HEAD ===")
print("  %-8s %-12s %-14s %-10s %s" % ("stops","commanded","delivered","%err","n"))
for v in ["-1","-0.5","-0.25","0.25","0.5","1","2"]:
    o,_=render("q"+v.replace(".","p").replace("-","m"),["--exposure",v])
    if o is None: print("  %-8s FAILED" % v); continue
    X=tifffile.imread(str(o)); Xc=X.ravel(); Xl=LUT[X.astype(np.int64)].ravel()
    del X; gc.collect()
    k=(Bc>0)&(Bc<65535)&(Xc>0)&(Xc<65535)
    got=slope(Bl[k],Xl[k]); c=2.0**float(v)
    print("  %-8s %-12.6f %-14.7f %+-10.4f %d" % (v,c,got,100*(got/c-1),int(k.sum())))
    del Xc,Xl; gc.collect(); os.remove(o)
os.remove(base)

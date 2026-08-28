import subprocess, pathlib, numpy as np, tifffile, os, gc
NEW=r"C:\dev\strehl-out\V-REVIEW\target\release\strehl.exe"
SUB=r"D:\personal\macro\109MSDCF"
OUT=pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\head"); OUT.mkdir(parents=True,exist_ok=True)
def render(tag,extra):
    o=OUT/(tag+".tiff")
    if o.exists(): o.unlink()
    r=subprocess.run([NEW,"stack",SUB,"--out",str(o),"--limit","4","--srgb","--merge","pyramid"]+extra,capture_output=True)
    return (o if (r.returncode==0 and o.exists()) else None),(r.stdout+r.stderr).decode("utf8","replace")

print("=== DETERMINISM ARM at HEAD ===")
a,_=render("d1",["--exposure","1"]); b,_=render("d2",["--exposure","1"])
A=tifffile.imread(str(a)); B=tifffile.imread(str(b))
print("  identical flags twice -> identical pixels: %s" % np.array_equal(A,B))
del A,B; gc.collect(); os.remove(b)

base,_=render("e0",["--exposure","0"])
BASE=tifffile.imread(str(base)).astype(np.float64)
CEIL=65535.0
print("\n=== ADJUDICATING THE FIX: does --exposure move pixels at HEAD? ===")
A1=tifffile.imread(str(a)).astype(np.float64)
moved=int(np.count_nonzero(A1!=BASE))
print("  --exposure 1 vs 0 : %d of %d samples moved (%.4f%%)" % (moved,BASE.size,100.0*moved/BASE.size))
m=(BASE>0)&(BASE<CEIL)&(A1<CEIL)
slope=float((BASE[m]*A1[m]).sum()/(BASE[m]*BASE[m]).sum())
print("  delivered slope   : %.7f  (commanded 2.0)   usable samples %d" % (slope,int(m.sum())))
print("  ORCH claim was    : 2.0132800 slope, 98,821,621 moved")

print("\n=== IS THE OVERSHOOT CLIPPING/ROLL-OFF DRIVEN? exclude highlights progressively ===")
print("  %-22s %-12s %s" % ("exclude BASE above","usable","delivered slope"))
for frac in [1.00,0.95,0.90,0.75,0.50,0.25]:
    mm=(BASE>0)&(BASE<CEIL*frac)&(A1<CEIL*frac)
    if mm.sum()<1000: print("  %-22s %-12d too few" % ("%.0f%% of ceiling"%(100*frac),int(mm.sum()))); continue
    s=float((BASE[mm]*A1[mm]).sum()/(BASE[mm]*BASE[mm]).sum())
    print("  %-22s %-12d %.7f" % ("%.0f%% of ceiling"%(100*frac),int(mm.sum()),s))
del A1; gc.collect(); os.remove(a)

print("\n=== IS THE ERROR CONSTANT, OR PROPORTIONAL TO THE GAIN? ===")
print("  %-10s %-12s %-14s %-12s %s" % ("stops","commanded","delivered","delivered/cmd","%err"))
for v in ["-1","-0.5","-0.25","0.25","0.5","1","2"]:
    o,_=render("s"+v.replace(".","p").replace("-","m"),["--exposure",v])
    if o is None: print("  %-10s FAILED" % v); continue
    X=tifffile.imread(str(o)).astype(np.float64)
    mm=(BASE>0)&(BASE<CEIL)&(X<CEIL)
    s=float((BASE[mm]*X[mm]).sum()/(BASE[mm]*BASE[mm]).sum())
    c=2.0**float(v)
    print("  %-10s %-12.6f %-14.7f %-12.6f %+.4f%%" % (v,c,s,s/c,100.0*(s/c-1.0)))
    del X; gc.collect(); os.remove(o)
os.remove(base)

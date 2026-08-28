import subprocess, pathlib, numpy as np, tifffile, os, gc
NEW=r"C:\dev\strehl-out\V-REVIEW\target\release\strehl.exe"
SUB=r"D:\personal\macro\109MSDCF"
OUT=pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\gaps")
def render(tag,extra):
    o=OUT/(tag+".tiff")
    if o.exists(): o.unlink()
    r=subprocess.run([NEW,"stack",SUB,"--out",str(o),"--limit","4","--srgb","--merge","estimator"]+extra,capture_output=True)
    return (o if (r.returncode==0 and o.exists()) else None),(r.stdout+r.stderr).decode("utf8","replace")
def ld(o):
    a=tifffile.imread(str(o)); os.remove(o); return a

print("=== --stats-placebo as a BARE SWITCH alongside --stats ===")
a,_=render("s0",["--stats"])
b,lg=render("s1",["--stats","--stats-placebo"])
if a and b:
    A,B=ld(a),ld(b); n=int(np.count_nonzero(A!=B))
    pl=[l.strip() for l in lg.splitlines() if "placebo" in l.lower()]
    print("  runs ok. pixels moved: %.4f%% -> %s" % (100.0*n/A.size,"potent" if n else "pixel-INERT"))
    print("  does it change the REPORT it exists to add to?")
    for l in pl[:4]: print("    report: "+l[:100])
    print("  verdict: %s" % ("emits its placebo arm; pixel-inert BY DESIGN" if pl else "NO PLACEBO OUTPUT - inert on its own artefact"))
    del A,B; gc.collect()
else:
    print("  STILL FAILS: "+[l for l in lg.splitlines() if l.strip()][-1][:120])

print("\n=== --focus with a real operator id ===")
c,_=render("f0",[])
if c:
    C0=ld(c)
    for fid in ["brenner-w13","laplacian-w13","ring-1-3-w13"]:
        o,lg=render("f1",["--focus",fid])
        if o is None:
            print("  %-22s UNRUNNABLE: %s" % (fid,[l for l in lg.splitlines() if l.strip()][-1][:70])); continue
        X=ld(o); n=int(np.count_nonzero(X!=C0))
        print("  --focus %-16s %.4f%% moved -> %s" % (fid,100.0*n/C0.size,"potent" if n else "INERT"))
        del X; gc.collect()

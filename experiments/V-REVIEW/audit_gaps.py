import subprocess, pathlib, numpy as np, tifffile, os, gc
NEW=r"C:\dev\strehl-out\V-REVIEW\target\release\strehl.exe"
OUT=pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\gaps"); OUT.mkdir(parents=True,exist_ok=True)
PL=OUT/"placebo"; PL.mkdir(exist_ok=True)
def render(sub,tag,extra,limit="4"):
    o=OUT/(tag+".tiff")
    if o.exists(): o.unlink()
    r=subprocess.run([NEW,"stack",sub,"--out",str(o),"--limit",limit,"--srgb"]+extra,capture_output=True)
    return (o if (r.returncode==0 and o.exists()) else None),(r.stdout+r.stderr).decode("utf8","replace")
def ld(o):
    a=tifffile.imread(str(o)); os.remove(o); return a

S1=r"D:\personal\macro\109MSDCF"; S2=r"D:\personal\macro\coffee-bubbles"
print("=== GAP 1: --stats-placebo WITH its <DIR> ===")
a,_=render(S1,"p0",["--merge","estimator","--stats"])
b,lg=render(S1,"p1",["--merge","estimator","--stats","--stats-placebo",str(PL)])
if a and b:
    A,B=ld(a),ld(b); n=int(np.count_nonzero(A!=B))
    files=list(PL.glob("*"))
    print("  runs ok. pixels moved: %.4f%%  -> %s" % (100.0*n/A.size, "potent" if n else "pixel-INERT"))
    print("  artefacts written to <DIR>: %d  %s" % (len(files), [f.name for f in files][:4]))
    print("  verdict: %s" % ("writes its artefact; pixel-inert BY DESIGN (a diagnostic)" if files else "WRITES NOTHING - inert on its own artefact"))
else:
    print("  FAILED: "+[l for l in lg.splitlines() if l.strip()][-1][:120])

print("\n=== GAP 2: second subject for the INERT rows (coffee-bubbles, 3 frames) ===")
base,_=render(S2,"c0",["--merge","pyramid"],limit="3")
if base is None:
    print("  baseline failed on subject 2")
else:
    B0=ld(base)
    for name,extra in [("--exposure 1",["--exposure","1"]),
                       ("--confidence-tail 0.9",["--confidence-tail","0.9"]),
                       ("--pyramid-exponent 4.0",["--pyramid-exponent","4.0"])]:
        o,lg=render(S2,"c1",["--merge","pyramid"]+extra,limit="3")
        if o is None: print("  %-26s FAILED" % name); continue
        X=ld(o); n=int(np.count_nonzero(X!=B0))
        print("  %-26s %.4f%% moved -> %s" % (name,100.0*n/B0.size,"potent" if n else "INERT on subject 2 too"))
        del X; gc.collect()
    del B0; gc.collect()

print("\n=== GAP 3: --focus / --index-map / --n-eff-map ===")
be,_=render(S1,"e0",["--merge","estimator"])
BE=ld(be) if be else None
for name,extra,art in [("--focus 1",["--focus","1"],None),
                       ("--index-map",["--index-map",str(OUT/"ix.tiff")],OUT/"ix.tiff"),
                       ("--n-eff-map",["--n-eff-map",str(OUT/"ne.tiff")],OUT/"ne.tiff")]:
    if art and art.exists(): art.unlink()
    o,lg=render(S1,"e1",["--merge","estimator"]+extra)
    if o is None:
        print("  %-16s UNRUNNABLE: %s" % (name,[l for l in lg.splitlines() if l.strip()][-1][:80])); continue
    X=ld(o); n=int(np.count_nonzero(X!=BE)) if BE is not None else -1
    msg="%.4f%% moved" % (100.0*n/BE.size) if BE is not None else "no baseline"
    extra_note = (" ; artefact written: %s" % art.exists()) if art else ""
    print("  %-16s %s%s" % (name,msg,extra_note))
    if art and art.exists(): art.unlink()
    del X; gc.collect()

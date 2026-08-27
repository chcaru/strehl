import subprocess, pathlib, numpy as np, tifffile, os, hashlib
NEW=r"C:\dev\strehl-out\V-REVIEW\target\release\strehl.exe"
SUB=r"D:\personal\macro\109MSDCF"
OUT=pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\sweep"); OUT.mkdir(parents=True,exist_ok=True)
COMMON=["--limit","4","--srgb"]

def render(tag, extra):
    o=OUT/(tag+".tiff")
    if o.exists(): o.unlink()
    r=subprocess.run([NEW,"stack",SUB,"--out",str(o)]+COMMON+extra,capture_output=True)
    log=(r.stdout+r.stderr).decode("utf8","replace")
    if r.returncode!=0 or not o.exists(): return None,log
    return o,log

def load_del(o, keep=False):
    a=tifffile.imread(str(o))
    if not keep: os.remove(o)
    return a

print("=== baselines ===")
bp,_=render("base_pyr",["--merge","pyramid"]);  BP=load_del(bp)
be,lg=render("base_est",["--merge","estimator"])
BE=load_del(be) if be else None
print("  pyramid baseline  : shape %s  mean %.4f" % (BP.shape,BP.mean()))
print("  estimator baseline: %s" % ("ok mean %.4f"%BE.mean() if BE is not None else "FAILED - estimator flags will be judged unrunnable"))

print("\n=== DETERMINISM ARM ===")
d,_=render("det",["--merge","pyramid"]); D=load_del(d)
det=np.array_equal(BP,D); print("  identical flags twice -> identical pixels: %s" % det)
assert det, "renderer nondeterministic; every null below unreadable"

TESTS=[
 ("--pyramid-bands 3",        ["--pyramid-bands","3"]),
 ("--pyramid-gate 8.0",       ["--pyramid-gate","8.0"]),
 ("--pyramid-exponent 4.0",   ["--pyramid-exponent","4.0"]),
 ("--pyramid-sharpen 1.0",    ["--pyramid-sharpen","1.0"]),
 ("--pyramid-select hard-max",["--pyramid-select","hard-max"]),
 ("--pyramid-base weighted",  ["--pyramid-base","weighted"]),
 ("--fix-ca a7c2-...x4cpl",   ["--fix-ca","a7c2-fe100gm-2xtc-x4cpl"]),
 ("--exposure 3",             ["--exposure","3"]),
 ("--auto-exposure",          ["--auto-exposure"]),
 ("--resampler lanczos3",     ["--resampler","lanczos3"]),
 ("--resampler nearest",      ["--resampler","nearest"]),
 ("--demosaic",               ["--demosaic"]),
 ("--stats",                  ["--stats"]),
 ("--stats-placebo",          ["--stats-placebo"]),
 ("--gate 8.0",               ["--gate","8.0"]),
 ("--photometric off",        ["--photometric","off"]),
 ("--target-n-eff 2",         ["--target-n-eff","2"]),
 ("--confidence-tail 0.2",    ["--confidence-tail","0.2"]),
 ("--flat-roi 100,100,512,512",  ["--flat-roi","100,100,512,512"]),
 ("--detail-roi 100,100,512,512",["--detail-roi","100,100,512,512"]),
]
print("\n=== POTENCY SWEEP (vs same-backend baseline, decoded pixels) ===")
print("  %-32s %-10s %-10s %s" % ("flag","backend","%moved","verdict"))
rows=[]
for name,extra in TESTS:
    o,log=render("t",["--merge","pyramid"]+extra); backend="pyramid"; ref=BP
    if o is None:
        o,log=render("t",["--merge","estimator"]+extra); backend="estimator"; ref=BE
    if o is None or ref is None:
        last=[l for l in log.splitlines() if l.strip()][-1][:70] if log.strip() else "?"
        print("  %-32s %-10s %-10s %s" % (name,"-","-","UNRUNNABLE: "+last)); rows.append((name,"-","-","unrunnable")); continue
    A=load_del(o)
    if A.shape!=ref.shape:
        print("  %-32s %-10s %-10s %s" % (name,backend,"n/a","DIFFERENT GEOMETRY %s"%(A.shape,))); rows.append((name,backend,"n/a","geometry")); continue
    n=int(np.count_nonzero(A!=ref)); pct=100.0*n/ref.size
    v = "INERT" if n==0 else ("negligible" if pct<0.5 else "potent")
    print("  %-32s %-10s %-10.4f %s" % (name,backend,pct,v))
    rows.append((name,backend,"%.4f"%pct,v))
print("\n=== INERT FLAGS ===")
for r in rows:
    if r[3] in ("INERT","negligible"): print("  %-32s %s (%s%% moved)" % (r[0],r[3],r[2]))

import subprocess, pathlib, numpy as np, tifffile, os
NEW=r"C:\dev\strehl-out\V-REVIEW\target\release\strehl.exe"
SUB=r"D:\personal\macro\109MSDCF"
OUT=pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\sweep")
def render(tag,extra,env=None):
    o=OUT/(tag+".tiff")
    if o.exists(): o.unlink()
    e=dict(os.environ);  e.update(env or {})
    r=subprocess.run([NEW,"stack",SUB,"--out",str(o),"--limit","4","--srgb","--merge","pyramid"]+extra,capture_output=True,env=e)
    log=(r.stdout+r.stderr).decode("utf8","replace")
    return (o if (r.returncode==0 and o.exists()) else None), log
def ld(o):
    a=tifffile.imread(str(o)); os.remove(o); return a

print("=== IS LATERAL CA CORRECTION ON BY DEFAULT? (the alternative explanation) ===")
a,la=render("ca_def",[])
b,lb=render("ca_off",[],env={"STREHL_FIX_CA":"off"})
for tag,l in (("default",la),("STREHL_FIX_CA=off",lb)):
    ln=[x.strip() for x in l.splitlines() if "lateral CA" in x]
    print("  %-18s log: %s" % (tag, ln[0][:96] if ln else "(no lateral CA line)"))
if a and b:
    A,B=ld(a),ld(b); n=int(np.count_nonzero(A!=B))
    print("  default vs CA-off : %.4f%% samples moved -> %s" % (100.0*n/A.size,
          "CA correction IS potent; --fix-ca is redundant, not broken" if n else "CA CORRECTION ITSELF IS INERT"))
else:
    print("  one arm failed")

print("\n=== --confidence-tail judged on the artefact it names (the confidence map) ===")
m1=OUT/"cm1.tiff"; m2=OUT/"cm2.tiff"
for p in (m1,m2):
    if p.exists(): p.unlink()
r1,_=render("cf1",["--confidence-map",str(m1)],env={"STREHL_MERGE":"estimator"})
r2,_=render("cf2",["--confidence-map",str(m2),"--confidence-tail","0.35"],env={"STREHL_MERGE":"estimator"})
print("  confidence map written (default / tail=0.35): %s / %s" % (m1.exists(), m2.exists()))
if m1.exists() and m2.exists():
    M1=tifffile.imread(str(m1)); M2=tifffile.imread(str(m2))
    n=int(np.count_nonzero(M1!=M2))
    print("  map samples moved by --confidence-tail: %.4f%% -> %s" % (100.0*n/M1.size,
          "POTENT on its own artefact" if n else "INERT even on its own artefact"))
for p in (m1,m2,r1,r2):
    try:
        if p and pathlib.Path(p).exists(): os.remove(p)
    except Exception: pass

import subprocess, pathlib, numpy as np, tifffile
BIN = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
SUB = r"D:\personal\macro\109MSDCF"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\exp3")
def run(tag, extra):
    o=OUT/(tag+".tiff")
    if o.exists(): o.unlink()
    r=subprocess.run([BIN,"stack",SUB,"--out",str(o)]+extra, capture_output=True)
    if r.returncode!=0 or not o.exists():
        print("  FAILED %s rc=%d %s" % (tag,r.returncode,(r.stdout+r.stderr).decode('utf8','replace')[-200:])); return None
    return o
print("=== Is the no-op specific to the TONE (--srgb) path? Test the LINEAR path. ===")
for mode,flag in (("linear-srgb","--linear-srgb"),):
    a=run("lin_p3",[flag,"--exposure=3"]); b=run("lin_m3",[flag,"--exposure=-3"])
    if a is None or b is None: continue
    A=tifffile.imread(str(a)); B=tifffile.imread(str(b))
    eq=np.array_equal(A,B); nz=int(np.count_nonzero(A.astype(np.int64)-B.astype(np.int64)))
    print("  %s  +3 vs -3 (64x commanded)" % flag)
    print("    identical pixels : %s" % eq)
    print("    samples differing: %d (%.3f%%)" % (nz,100.0*nz/A.size))
    print("    mean DN +3 / -3  : %.4f / %.4f    ratio %.6f" % (A.mean(),B.mean(),A.mean()/max(B.mean(),1e-9)))

import subprocess, hashlib, pathlib, os, numpy as np, tifffile
EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
DIR = r"D:\personal\macro\coffee-bubbles"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\diff")
ENV = {k:v for k,v in os.environ.items() if not k.startswith("STREHL_")}
def run(tag,args):
    o=OUT/(tag+".tif")
    if o.exists(): o.unlink()
    p=subprocess.run([EXE,"stack",DIR,"--limit","3","--out",str(o)]+args,
                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV)
    return o,p.returncode,p.stdout.decode("utf8","replace")

print("="*104)
print("PIXELS vs METADATA: is the hash difference in the image, or in the file header?")
print("="*104)
for label,args in [("--srgb",["--srgb"]), ("--srgb --binned",["--srgb","--binned"])]:
    ob,rb,_   = run("q_base", args)
    oe,re_,lg = run("q_exp",  args+["--exposure","2.0"])
    print("\n  path: %s" % label)
    print("    rc base=%d  rc exposure=%d" % (rb,re_))
    if rb!=0 or re_!=0:
        print("    NON-ZERO EXIT -- error text:"); print("      "+lg.strip().split("\n")[-1][:160]); continue
    print("    file size  base=%d  exposure=%d" % (ob.stat().st_size, oe.stat().st_size))
    a,b = tifffile.imread(ob), tifffile.imread(oe)
    print("    array shape/dtype  %s %s  |  %s %s" % (a.shape,a.dtype,b.shape,b.dtype))
    eq = np.array_equal(a,b)
    print("    PIXELS identical  : %s" % eq)
    print("    mean base=%.4f  mean exposure=%.4f  ratio=%.4f" % (a.mean(), b.mean(), b.mean()/max(a.mean(),1e-9)))
    if not eq:
        d=(b.astype(np.int64)-a.astype(np.int64))
        print("    pixels differing  : %d of %d (%.3f%%)  max |delta|=%d" % ((d!=0).sum(), d.size, 100*(d!=0).mean(), np.abs(d).max()))
    hb=hashlib.sha256(ob.read_bytes()).hexdigest()[:16].upper()
    he=hashlib.sha256(oe.read_bytes()).hexdigest()[:16].upper()
    print("    file hash  base=%s  exposure=%s  %s" % (hb,he,"SAME" if hb==he else "DIFFER"))
    if eq and hb!=he: print("    >>> PIXELS IDENTICAL BUT FILE DIFFERS -> the difference is METADATA ONLY <<<")

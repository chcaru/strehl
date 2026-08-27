"""Differential flag audit: does each flag CHANGE THE OUTPUT BYTES of the shipping binary?
Commissioned two ways: a determinism null (same cmd twice -> identical) and a potency
arm (--limit 3 vs 4 -> must differ). A flag whose output equals baseline is a NO-OP."""
import subprocess, hashlib, pathlib, os, time, sys
EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
DIR = r"D:\personal\macro\coffee-bubbles"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\diff"); OUT.mkdir(parents=True, exist_ok=True)
ENV = {k:v for k,v in os.environ.items() if not k.startswith("STREHL_")}

def run(tag, args):
    o = OUT/(tag+".tif")
    if o.exists(): o.unlink()
    t=time.time()
    p = subprocess.run([EXE,"stack",DIR,"--limit","3","--out",str(o)]+args,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=ENV)
    log = p.stdout.decode("utf8","replace")
    (OUT/(tag+".log")).write_text(log, encoding="utf8")
    h = hashlib.sha256(o.read_bytes()).hexdigest()[:16].upper() if o.exists() else "NO-OUTPUT"
    return h, p.returncode, time.time()-t, log

print("="*104); print("COMMISSIONING"); print("="*104)
b1,rc1,t1,log1 = run("base", [])
b2,_,_,_       = run("base_rerun", [])
print("  determinism null   base vs base rerun : %s  %s" % (b1, "IDENTICAL (pass)" if b1==b2 else "DIFFER -> harness unusable"))
p4 = subprocess.run([EXE,"stack",DIR,"--limit","4","--out",str(OUT/"lim4.tif")],
                    stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV)
h4 = hashlib.sha256((OUT/"lim4.tif").read_bytes()).hexdigest()[:16].upper()
print("  potency arm        --limit 3 vs 4     : %s  %s" % (h4, "DIFFERS (pass)" if h4!=b1 else "IDENTICAL -> harness blind"))
if b1!=b2 or h4==b1: sys.exit("COMMISSIONING FAILED")
print("  baseline render    rc=%d  %.1fs" % (rc1, t1))

CASES = [
 ("pyramid", "--demosaic",        ["--demosaic"],                     []),
 ("pyramid", "--srgb",            ["--srgb"],                         []),
 ("pyramid", "--linear-srgb",     ["--linear-srgb"],                  []),
 ("pyramid", "--resampler",       ["--resampler","lanczos3"],         []),
 ("pyramid", "--pyramid-bands",   ["--pyramid-bands","3"],            []),
 ("pyramid", "--pyramid-gate",    ["--pyramid-gate","9.0"],           []),
 ("pyramid", "--pyramid-exponent",["--pyramid-exponent","2.0"],       []),
 ("pyramid", "--pyramid-sharpen", ["--pyramid-sharpen","2.0"],        []),
 ("pyramid", "--pyramid-select",  ["--pyramid-select","hard-max"],    []),
 ("pyramid", "--pyramid-base",    ["--pyramid-base","weighted"],      []),
 ("srgb",    "--exposure",        ["--srgb","--exposure","2.0"],      ["--srgb"]),
 ("srgb",    "--auto-exposure",   ["--srgb","--auto-exposure"],       ["--srgb"]),
 ("srgb",    "--binned",          ["--srgb","--binned"],              ["--srgb"]),
 ("est",     "--gate",            ["--merge","estimator","--gate","8.0"], ["--merge","estimator"]),
 ("est",     "--photometric off", ["--merge","estimator","--photometric","off"], ["--merge","estimator"]),
]
bases = {}
print(); print("="*104); print("DIFFERENTIAL: flag vs its own baseline"); print("="*104)
print("  %-20s %-18s %-18s %s" % ("flag","baseline hash","with-flag hash","verdict"))
print("  " + "-"*100)
for group, flag, args, basargs in CASES:
    if group not in bases:
        bases[group] = run("base_"+group, basargs)[0]
    hb = bases[group]
    tag = flag.strip("-").replace(" ","_")
    h, rc, dt, log = run(tag, args)
    if h == "NO-OUTPUT":
        v = "REFUSED rc=%d" % rc
    elif h == hb:
        v = "*** NO-OP: output byte-identical to baseline ***"
    else:
        v = "changes output (works)"
    print("  %-20s %-18s %-18s %s" % (flag, hb, h, v))

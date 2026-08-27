import subprocess, hashlib, pathlib, os
EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
DIR = r"D:\personal\macro\coffee-bubbles"
OUT = pathlib.Path(r"C:\dev\strehl-out\V-REVIEW\diff")
ENV = {k:v for k,v in os.environ.items() if not k.startswith("STREHL_")}
def run(tag,args):
    o=OUT/(tag+".tif")
    if o.exists(): o.unlink()
    p=subprocess.run([EXE,"stack",DIR,"--limit","3","--out",str(o)]+args,
                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV)
    h=hashlib.sha256(o.read_bytes()).hexdigest()[:16].upper() if o.exists() else "NO-OUTPUT"
    return h,p.returncode,p.stdout.decode("utf8","replace")

print("="*100)
print("IS --pyramid-exponent IGNORED, OR DID I PASS ITS DEFAULT? sweep far from any plausible default")
print("="*100)
base,_,_ = run("pe_base",[])
print("  baseline                       %s" % base)
for v in ["0.5","1.0","2.0","4.0","8.0","64.0"]:
    h,rc,log = run("pe_"+v.replace(".","_"),["--pyramid-exponent",v])
    print("  --pyramid-exponent %-6s rc=%d  %s  %s" % (v,rc,h,"SAME AS BASELINE" if h==base else "differs"))
print("\n  control: --pyramid-sharpen (same subsystem, known to work) sweeps")
for v in ["1.0","2.0","4.0"]:
    h,rc,_ = run("ps_"+v.replace(".","_"),["--pyramid-sharpen",v])
    print("  --pyramid-sharpen  %-6s rc=%d  %s  %s" % (v,rc,h,"SAME AS BASELINE" if h==base else "differs"))

print("\n" + "="*100)
print("WHY DID THE ESTIMATOR BASELINE PRODUCE NO OUTPUT?")
print("="*100)
h,rc,log = run("est_base",["--merge","estimator"])
print("  `--merge estimator --limit 3`  rc=%d  hash=%s" % (rc,h))
print("  ---- last 18 lines of its output ----")
for L in log.strip().split("\n")[-18:]: print("    "+L)

"""Reproduce ORCH's bee-1-cpl headline table. N=299, the deepest stack.
Arms: default vs 4,1,1,1,1,1,1. --srgb, no --auto-exposure, per ORCH's recipe.
"""
import hashlib, os, subprocess, time
EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SRC = r"D:\personal\macro\bee-1-cpl"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\bee1"
os.makedirs(OUT, exist_ok=True)
for nm, v in (("A-unset", None), ("F4", "4,1,1,1,1,1,1")):
    dst = os.path.join(OUT, "srgb__%s.tiff" % nm)
    if not os.path.exists(dst):
        env = dict(os.environ); env.pop("STREHL_GATE_FLOOR_SCALE", None)
        if v: env["STREHL_GATE_FLOOR_SCALE"] = v
        t = time.time()
        p = subprocess.run([EXE, "stack", SRC, "-o", dst, "--srgb"],
                           capture_output=True, text=True, env=env)
        open(dst.replace(".tiff", ".log"), "w", encoding="utf-8").write(p.stdout + p.stderr)
        print("  rendered %s in %.1f min rc=%d" % (nm, (time.time()-t)/60, p.returncode), flush=True)
    log = open(dst.replace(".tiff", ".log"), encoding="utf-8").read()
    avg = [l.split(":",1)[1].strip() for l in log.splitlines() if l.strip().startswith("averaged")]
    nf  = [l.strip() for l in log.splitlines() if "averaged over" in l]
    h = hashlib.sha256(open(dst,"rb").read()).hexdigest().upper()
    print("  %-8s %s averaged %s" % (nm, h[:16], avg[0][:44] if avg else "?"), flush=True)
    if nf: print("           %s" % nf[0][:90], flush=True)

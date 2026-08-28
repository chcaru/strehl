"""bee-1-cpl: (a) linear pair to test tone inflation of the headline grain
number, (b) linear split-halves so sigref can say whether the removed
flat-site content is reproducible (real) or not (noise).
"""
import hashlib, os, shutil, subprocess, time
EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SRC = r"D:\personal\macro\bee-1-cpl"
STAGE = r"C:\dev\strehl-out\V-BANDFLOOR\stage"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\bee1"
NS  = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"

def run(indir, dst, val, mode):
    if not os.path.exists(dst):
        env = dict(os.environ); env.pop("STREHL_GATE_FLOOR_SCALE", None)
        if val: env["STREHL_GATE_FLOOR_SCALE"] = val
        t = time.time()
        p = subprocess.run([EXE, "stack", indir, "-o", dst, mode],
                           capture_output=True, text=True, env=env)
        open(dst.replace(".tiff", ".log"), "w", encoding="utf-8").write(p.stdout + p.stderr)
        print("   (%.1f min, rc=%d)" % ((time.time()-t)/60, p.returncode), flush=True)
    log = open(dst.replace(".tiff", ".log"), encoding="utf-8").read()
    avg = [l.split(":",1)[1].strip() for l in log.splitlines() if l.strip().startswith("averaged")]
    h = hashlib.sha256(open(dst,"rb").read()).hexdigest().upper()
    print("  %-34s %s averaged %s" % (os.path.basename(dst), h[:16], avg[0][:30] if avg else "?"), flush=True)

print("=== A: linear pair (tone-stage removed) ===", flush=True)
for nm, v in (("A-unset", None), ("F4", "4,1,1,1,1,1,1")):
    run(SRC, os.path.join(OUT, "lin__%s.tiff" % nm), v, "--linear-srgb")

print("=== B: linear split-halves for sigref ===", flush=True)
fs = sorted(f for f in os.listdir(SRC) if f.upper().endswith(".ARW"))
print("  N=%d" % len(fs), flush=True)
for par, lbl in ((0, "EVEN"), (1, "ODD")):
    d = os.path.join(STAGE, "bee1__%s" % lbl)
    os.makedirs(d, exist_ok=True)
    picked = [f for i, f in enumerate(fs) if i % 2 == par]
    for f in picked:
        if not os.path.exists(os.path.join(d, f)):
            shutil.copy2(os.path.join(SRC, f), os.path.join(d, f))
    print("  staged %s n=%d" % (lbl, len(picked)), flush=True)
    for nm, v in (("A-unset", None), ("F4", "4,1,1,1,1,1,1")):
        run(d, os.path.join(NS, "bee1__%s__%s.tiff" % (lbl, nm)), v, "--linear-srgb")

"""119MSDCF band-0 ladder on split-halves.

119MSDCF is the knob's BEST CASE: its flat-site band-0 signal fraction measures
0.103 (89.7% noise) -- the only genuinely noise-dominated subject in the set.
If raising the band-0 floor is ever the right move, it is right here.
"""
import hashlib, os, subprocess
EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
STAGE = r"C:\dev\strehl-out\V-BANDFLOOR\stage"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"
for lbl in ("EVEN", "ODD"):
    d = os.path.join(STAGE, "119MSDCF__%s" % lbl)
    for nm, v in (("F2", "2,1,1,1,1,1,1"), ("F4", "4,1,1,1,1,1,1"), ("F8", "8,1,1,1,1,1,1")):
        dst = os.path.join(OUT, "119MSDCF__%s__%s.tiff" % (lbl, nm))
        if not os.path.exists(dst):
            env = dict(os.environ); env.pop("STREHL_GATE_FLOOR_SCALE", None)
            env["STREHL_GATE_FLOOR_SCALE"] = v
            p = subprocess.run([EXE, "stack", d, "-o", dst, "--linear-srgb"],
                               capture_output=True, text=True, env=env)
            open(dst.replace(".tiff", ".log"), "w", encoding="utf-8").write(p.stdout + p.stderr)
        log = open(dst.replace(".tiff", ".log"), encoding="utf-8").read()
        avg = [l.split(":", 1)[1].strip() for l in log.splitlines() if l.strip().startswith("averaged")]
        h = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper()
        print("  119MSDCF__%s__%-4s %s averaged %s" % (lbl, nm, h[:16], avg[0][:40] if avg else "?"), flush=True)

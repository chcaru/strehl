"""112MSDCF: ORCH's requested band-0 ladder, plus the renders needed to audit
ORCH's contrast_ab.py conclusions.

Three render sets:
  1. --srgb ladder  : reproduce ORCH's recipe verbatim (their Result 1 and 3)
  2. --linear-srgb  : same arms with NO tone stage, to test whether ORCH's
                      -206.7 DN "flat sites got darker" survives removal of the
                      tone stage, or is an artifact of a one-parameter median
                      rescale applied after a non-linear transfer curve.
  3. --linear-srgb EVEN/ODD split-halves : so sigref.py (commissioned 5/5) can
                      decompose ORCH's flat-site hp_std drop into SIGNAL and
                      NOISE. hp_std alone cannot tell a denoise from a blur.
"""
import hashlib
import os
import shutil
import subprocess

EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SRC = r"D:\personal\macro\112MSDCF"
STAGE = r"C:\dev\strehl-out\V-BANDFLOOR\stage"
OUT = r"C:\dev\strehl-out\V-BANDFLOOR\bf112"
os.makedirs(OUT, exist_ok=True)

LADDER = [("A-unset", None), ("F1", "1,1,1,1,1,1,1"), ("F15", "1.5,1,1,1,1,1,1"),
          ("F2", "2,1,1,1,1,1,1"), ("F3", "3,1,1,1,1,1,1"), ("F4", "4,1,1,1,1,1,1")]


def run(indir, name, val, mode):
    dst = os.path.join(OUT, "%s.tiff" % name)
    if os.path.exists(dst):
        print("  skip %s" % name, flush=True)
        return
    env = dict(os.environ)
    env.pop("STREHL_GATE_FLOOR_SCALE", None)
    if val:
        env["STREHL_GATE_FLOOR_SCALE"] = val
    p = subprocess.run([EXE, "stack", indir, "-o", dst, mode],
                       capture_output=True, text=True, env=env)
    log = p.stdout + p.stderr
    open(dst.replace(".tiff", ".log"), "w", encoding="utf-8").write(log)
    avg = ""
    for line in log.splitlines():
        if line.strip().startswith("averaged"):
            avg = line.split(":", 1)[1].strip()
    h = hashlib.sha256(open(dst, "rb").read()).hexdigest().upper() if p.returncode == 0 else "FAIL"
    print("  %-26s %s  averaged %s" % (name, h[:16], avg), flush=True)


print("=== SET 1: ORCH's --srgb ladder (their recipe verbatim) ===", flush=True)
for nm, v in LADDER:
    run(SRC, "srgb__%s" % nm, v, "--srgb")

print("=== SET 2: --linear-srgb, no tone stage ===", flush=True)
for nm, v in LADDER:
    run(SRC, "lin__%s" % nm, v, "--linear-srgb")

print("=== SET 3: --linear-srgb split-halves for sigref ===", flush=True)
fs = sorted(f for f in os.listdir(SRC) if f.upper().endswith(".ARW"))
for par, lbl in ((0, "EVEN"), (1, "ODD")):
    d = os.path.join(STAGE, "112MSDCF__%s" % lbl)
    os.makedirs(d, exist_ok=True)
    picked = [f for i, f in enumerate(fs) if i % 2 == par]
    for f in picked:
        if not os.path.exists(os.path.join(d, f)):
            shutil.copy2(os.path.join(SRC, f), os.path.join(d, f))
    print("staged %s n=%d first=%s last=%s" % (lbl, len(picked), picked[0], picked[-1]), flush=True)
    for nm, v in (("A-unset", None), ("F2", "2,1,1,1,1,1,1"), ("F4", "4,1,1,1,1,1,1")):
        run(d, "112MSDCF__%s__%s" % (lbl, nm), v, "--linear-srgb")

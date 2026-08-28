"""Symmetric arm: LOWER band 0's floor (0.25,1,1,1,1,1,1).

F4 raised the floor and destroyed split-half covariance -- but that only proves
the coefficients ABOVE the current threshold carry signal. ORCH's question is
about the ones ALREADY BELOW it (54.4% of band 0 on leaf-2-cpl). Lowering the
floor moves those from AVERAGE back into SELECT.

  If reproducible band-0 signal RISES -> the averaged set held recoverable
  signal -> the floor is rejecting something real (population B).
  If it does NOT rise (or only noise rises) -> the capture is empty there and
  the merge was RIGHT to average (population A).

gatefloor.rs:139 requires every entry finite and > 0.0, so 0.25 is accepted.
"""
import os, shutil, subprocess, sys
SRC = r"D:\personal\macro"; OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"
STAGE = r"D:\strehl-out\V-BANDFLOOR\stg"
EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SUBJ, ARM, VAL = sys.argv[1], sys.argv[2], sys.argv[3]
fr = sorted(f for f in os.listdir(os.path.join(SRC, SUBJ)) if f.upper().endswith(".ARW"))
print("%s N=%d arm=%s val=%s" % (SUBJ, len(fr), ARM, VAL), flush=True)
for half, sel in (("EVEN", fr[0::2]), ("ODD", fr[1::2])):
    shutil.rmtree(STAGE, ignore_errors=True); os.makedirs(STAGE)
    for f in sel: shutil.copy2(os.path.join(SRC, SUBJ, f), STAGE)
    o = os.path.join(OUT, "%s__%s__%s.tiff" % (SUBJ, half, ARM))
    env = dict(os.environ); env["STREHL_GATE_FLOOR_SCALE"] = VAL
    r = subprocess.run([EXE, "stack", STAGE, "-o", o, "--linear-srgb"],
                       capture_output=True, env=env)
    err = r.stderr.decode("utf-8", "replace")
    duty = [l for l in err.splitlines() if "%" in l and "averaged" not in l.lower()
            and l.strip().startswith(("level", "band", "  0"))]
    print("  %s rc=%d -> %s" % (half, r.returncode, os.path.basename(o)), flush=True)
    for l in duty[:3]: print("     " + l.strip(), flush=True)
    shutil.rmtree(STAGE, ignore_errors=True)
print("done")

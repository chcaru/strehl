"""Does the coefficient set the band-0 floor moves into AVERAGING carry signal?

Qualifying a band over the whole frame does NOT qualify the subset of
coefficients the gate actually averages -- by construction the gate fires where
NO frame cleared the noise floor, i.e. on the LOWEST-energy coefficients. That
is the same "the subset is not the population" objection I used against ORCH's
flat-site defence, so I must not grant it to myself in reverse.

Direct test: raise ONLY band 0's floor (4,1,1,1,1,1,1). That moves additional
coefficients from SELECT into AVERAGE. Split-half covariance then says whether
what changed was REPRODUCIBLE (signal, present in both disjoint frame halves)
or independent per-half (noise). Split-half covariance cannot contain
independent noise by construction.

Renders --linear-srgb (no tone stage, PLANE grid = the merge's own grid).
Heavy output on D: per the disk directive. Staged ARWs deleted after each pair.
"""
import os, shutil, subprocess, sys
SRC = r"D:\personal\macro"
OUT = r"D:\strehl-out\V-BANDFLOOR\nscale"
STAGE = r"D:\strehl-out\V-BANDFLOOR\stg"
EXE = r"C:\dev\blog\death-of-software\projects\strehl\target-orch\release\strehl.exe"
SUBJ = sys.argv[1]
ARMS = {"A-unset": None, "F4": "4,1,1,1,1,1,1"}
os.makedirs(OUT, exist_ok=True)

fr = sorted(f for f in os.listdir(os.path.join(SRC, SUBJ)) if f.upper().endswith(".ARW"))
print("%s N=%d" % (SUBJ, len(fr)), flush=True)
for half, sel in (("EVEN", fr[0::2]), ("ODD", fr[1::2])):
    shutil.rmtree(STAGE, ignore_errors=True); os.makedirs(STAGE)
    for f in sel: shutil.copy2(os.path.join(SRC, SUBJ, f), STAGE)
    print("  %s staged %d" % (half, len(sel)), flush=True)
    for arm, val in ARMS.items():
        o = os.path.join(OUT, "%s__%s__%s.tiff" % (SUBJ, half, arm))
        env = dict(os.environ)
        env.pop("STREHL_GATE_FLOOR_SCALE", None)
        if val: env["STREHL_GATE_FLOOR_SCALE"] = val
        r = subprocess.run([EXE, "stack", STAGE, "-o", o, "--linear-srgb"],
                           capture_output=True, env=env)
        err = r.stderr.decode("utf-8", "replace")
        avg = [l for l in err.splitlines() if "averaged" in l]
        print("    %-8s rc=%d %s" % (arm, r.returncode, avg[-1].strip() if avg else "NO BANNER"), flush=True)
    shutil.rmtree(STAGE, ignore_errors=True)
print("done")

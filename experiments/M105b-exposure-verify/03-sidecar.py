"""V5c -- does the byte-frozen measurement render depend on MUTABLE STATE that
lives outside the repository?

MECHANISM, read at source (`crates/strehl-cli/src/align_cmd.rs:901-953`):

    `load_or_solve` looks for `<dir>/warpmap.txt`. If it is present, parses,
    matches the stack digest AND has exactly `paths.len()` entries, the merge
    USES it. Otherwise the merge re-solves and then does

        map.save(&side)                       // align_cmd.rs:951

    which WRITES `warpmap.txt` INTO THE CAPTURE DIRECTORY. The comment above it
    reads "Best effort: a read-only capture directory must not fail the merge",
    so the author expected the write to fail on a read-only corpus. It does not
    fail: `D:\personal\macro` is read-only by POLICY, not by permission.

So run N of the same command can consume a file written by run N-1, and the
output of the "byte-frozen" measurement path is a function of what somebody
else ran in that directory earlier.

THE ARMS (all on an ISOLATED COPY of 60 frames under C:\, so that D: is never
written again by this milestone):

    A  cold      no warpmap.txt at all               -> must re-solve
    B  warm      the warpmap.txt arm A just wrote    -> must be ACCEPTED
    C  cold2     warpmap.txt deleted again           -> must re-solve
    D  stale     a warpmap.txt from a DIFFERENT frame count -> must be rejected

PRE-REGISTERED READING (written before the run):

    * A == C is the DETERMINISM control. If the solver is not deterministic
      these arms differ and nothing else in this script means anything. This is
      the placebo: it must show NO effect.
    * A == B is the claim under test. If they differ, the render depends on
      sidecar state and the freeze is not a property of the source tree.
    * D == A is the corroborating arm: a rejected sidecar must land on the same
      answer as no sidecar, because both paths re-solve.

    HAZARD CONFIRMED if A != B while A == C.
    HAZARD REFUTED  if A == B.
    INSTRUMENT BROKEN if A != C, and no other line may then be read.

Read-only on D:. Writes only under C:\dev\strehl-out\M105.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys

EXE = r"C:\dev\strehl-m105-target\release\strehl.exe"
DIR = r"C:\dev\strehl-out\M105\iso60"
OUT = r"C:\dev\strehl-out\M105"
SIDECAR = os.path.join(DIR, "warpmap.txt")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def render(tag, extra=()):
    """One default-path render. No --srgb, no --demosaic: the measurement path."""
    tif = os.path.join(OUT, "v5c-%s.tif" % tag)
    log = os.path.join(OUT, "v5c-%s.log" % tag)
    cmd = [EXE, "stack", DIR, "--out", tif] + list(extra)
    with open(log, "wb") as fh:
        rc = subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT)
    with open(log, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    align = [l.strip() for l in text.splitlines() if l.startswith("alignment")]
    return {
        "arm": tag,
        "exit": rc,
        "sha256": sha256(tif) if os.path.exists(tif) else "NO-FILE",
        "sidecar_existed_before": None,
        "alignment": align[:2],
        "sidecar_after": os.path.exists(SIDECAR),
    }


def drop_sidecar():
    if os.path.exists(SIDECAR):
        os.remove(SIDECAR)


def main():
    rows = []

    drop_sidecar()
    a = render("A-cold")
    a["sidecar_existed_before"] = False
    rows.append(a)

    # Arm B deliberately leaves in place whatever arm A wrote.
    b = render("B-warm")
    b["sidecar_existed_before"] = True
    rows.append(b)

    drop_sidecar()
    c = render("C-cold2")
    c["sidecar_existed_before"] = False
    rows.append(c)

    # Arm D: a sidecar that is real but fitted on a different frame count. The
    # binary must reject it on the length check and re-solve.
    shutil.copyfile(SIDECAR, os.path.join(OUT, "sidecar-60.txt"))
    drop_sidecar()
    d_side = render("D-stale-src", ["--limit", "30"])
    rows.append(d_side)
    d = render("D-stale")
    d["sidecar_existed_before"] = True
    rows.append(d)

    by = {r["arm"]: r["sha256"] for r in rows}
    verdict = {
        "A_cold": by["A-cold"],
        "B_warm": by["B-warm"],
        "C_cold2": by["C-cold2"],
        "D_stale": by["D-stale"],
        "determinism_control_A_eq_C": by["A-cold"] == by["C-cold2"],
        "claim_A_eq_B": by["A-cold"] == by["B-warm"],
        "corroborating_D_eq_A": by["D-stale"] == by["A-cold"],
    }
    if not verdict["determinism_control_A_eq_C"]:
        verdict["VERDICT"] = "INSTRUMENT BROKEN: solver is not deterministic; read nothing else"
    elif not verdict["claim_A_eq_B"]:
        verdict["VERDICT"] = "HAZARD CONFIRMED: the measurement render depends on sidecar state"
    else:
        verdict["VERDICT"] = "HAZARD REFUTED: sidecar state does not move the measurement render"

    res = {"arms": rows, "verdict": verdict}
    print(json.dumps(res, indent=2))
    with open(os.path.join(OUT, "03-sidecar.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)


if __name__ == "__main__":
    sys.exit(main())

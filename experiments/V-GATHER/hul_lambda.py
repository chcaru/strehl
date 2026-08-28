r"""Is PerLevel the wrong mechanism, or merely configured too soft?

`--per-level` at its shipping defaults uses `hull_lambda = 2.0`, and
`pyramid.rs:1013` documents `hull_lambda = 0` as "a hard per-level projection".
So a null reading from `--per-level` alone is ambiguous between:

  (a) bounding the reconstruction per level does not touch manufactured detail
  (b) it would, but a 2x-slack bound is too weak to show it

This fires the hard projection and two intermediate strengths. If the HARD
projection also leaves mid-band contrast unchanged, (b) is excluded and the
level-0 clamp is not the mechanism at any strength this code can express.

`--hull-from 5` is the opposite bracket: it confines the bound to levels coarser
than the scales the gauge can see, and should therefore be nearly inert. It is
the internal negative control on the sweep -- it proves the sweep can produce a
null, so a null from the hard arm is not simply what this script always prints.
"""
import hashlib
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import hul_measure as hm                                           # noqa: E402
from hul_run import PIN, SRC, sha                                  # noqa: E402

ARMS = {
    "pl-lambda0":  ["--per-level", "--hull-lambda", "0"],
    "pl-lambda0p5": ["--per-level", "--hull-lambda", "0.5"],
    "pl-from5":    ["--per-level", "--hull-from", "5"],
}
SUBJECTS = ["foam", "coffee-bubbles"]


def main():
    pin0 = sha(PIN)
    print("pin SHA256 %s" % pin0, flush=True)
    for sub in SUBJECTS:
        print("== %s" % sub, flush=True)
        for arm, flags in ARMS.items():
            dst = hm.arm_path(sub, arm)
            if os.path.exists(dst):
                print("   %-13s exists" % arm, flush=True)
                continue
            t0 = time.time()
            pr = subprocess.run([PIN, os.path.join(SRC, sub), dst, "--camera-linear"] + flags,
                                capture_output=True, text=True, errors="replace")
            log = (pr.stdout or "") + (pr.stderr or "")
            if pr.returncode != 0 or not os.path.exists(dst):
                named = [l for l in log.splitlines()
                         if any(k in l.lower() for k in
                                ("error", "panic", "fail", "unknown", "usage"))]
                raise SystemExit("RENDER FAILED %s/%s rc=%d\n%s"
                                 % (sub, arm, pr.returncode,
                                    "\n".join(named[-12:]) or log[-800:]))
            clamp = [l.strip() for l in log.splitlines() if l.startswith("hull clamp")]
            print("   %-13s %6.1f s   %s" % (arm, time.time() - t0,
                                             clamp[0] if clamp else "-"), flush=True)
    if sha(PIN) != pin0:
        raise SystemExit("PIN CHANGED MID-RUN: the A/B is void")
    print("pin unchanged: %s" % pin0)


if __name__ == "__main__":
    main()

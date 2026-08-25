"""M97e -- the null for the robust pass-one election, and a live reachability probe.

ORCH requires the null before any positive claim: with the feature off the
merged output must hash exactly as it does at HEAD. That is necessary but, on
its own, nearly worthless -- an unreachable feature also passes it, and this
project has now been handed four false zeros from searches that ran nowhere.

So this harness does not merely assert "identical". It measures *whether the
switch is connected at all*, using an arm that cannot be faked:

    TYPO ARM. `arm_from_setting` refuses an unrecognised value with
    `UnknownArm` rather than silently reading it as off. So if a render with
    STREHL_ROBUST_ELECTION=sotf SUCCEEDS, that is positive evidence that
    nothing in the render path ever reads the variable. A held hash on the
    typo arm is a *reachability failure*, not a passing null.

Arms:
    unset       -> HOLD    the shipped default cannot move
    off / 0     -> HOLD    the off spellings are true no-ops
    ungated     -> HOLD    the STRONG null: the whole ring, the whole kernel
                           and the whole election run, and only the weight is
                           withheld. Separates "the gate changed the picture"
                           from "the new plumbing changed the picture".
    soft        -> MOVE once wired; HOLD means unreachable
    sotf (typo) -> REFUSE once wired; HOLD means unreachable

`unset` is repeated N_REPEAT times, because a byte-freeze claimed from a single
run is a claim about one run.

Exit codes come from subprocess.returncode, never from $LASTEXITCODE after a
truncated pipeline.
"""

import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
CARGO = Path.home() / ".cargo" / "bin" / "cargo.exe"
ENV_NAME = "STREHL_ROBUST_ELECTION"
N_REPEAT = 5

HOLDS_RE = re.compile(r"freeze `([^`]+)` HOLDS: ([0-9A-F]{64})")
ACTUAL_RE = re.compile(r"actual\s+sha256\s*:\s*([0-9A-F]{64})")


def run_freeze(value):
    env = dict(os.environ)
    env["PATH"] = str(Path.home() / ".cargo" / "bin") + os.pathsep + env["PATH"]
    env["CARGO_TARGET_DIR"] = r"C:\dev\strehl-target-m97"
    env.pop(ENV_NAME, None)
    if value is not None:
        env[ENV_NAME] = value
    p = subprocess.run(
        [str(CARGO), "test", "--release", "-p", "strehl-cli", "--test", "byte-freeze"],
        cwd=str(REPO), capture_output=True, env=env,
    )
    out = p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")
    # Only hashes the render actually PRODUCED. The failure report prints the
    # expected hash beside the actual one, and counting both was a defect in an
    # earlier version of this harness.
    produced = sorted(set(h for _, h in HOLDS_RE.findall(out)) | set(ACTUAL_RE.findall(out)))
    return p.returncode, out, produced


def main():
    print(f"=== {ENV_NAME} null + reachability ===\n")

    # ---- the null, repeated -------------------------------------------
    seen = []
    for i in range(N_REPEAT):
        code, out, hashes = run_freeze(None)
        ok = code == 0
        seen.append((ok, tuple(hashes)))
        print(f"[unset run {i + 1}/{N_REPEAT}] exit={code} hold={ok} hashes={hashes}")
    stable = len(set(seen)) == 1 and all(ok for ok, _ in seen)
    baseline = seen[0][1]
    print(f"\nnull stable across {N_REPEAT} runs: {stable}")
    if not stable:
        print("THE NULL IS NOT STABLE -- nothing else in this run can be trusted.")
        return 2

    # ---- the off spellings, and the strong null ------------------------
    results = {}
    for label, value in [("off", "off"), ("zero", "0"), ("ungated", "ungated")]:
        code, out, hashes = run_freeze(value)
        held = code == 0 and tuple(hashes) == baseline
        results[label] = (code, tuple(hashes), held)
        print(f"[{label}] exit={code} held={held} hashes={list(hashes)}")

    # ---- reachability: soft must move, a typo must refuse --------------
    reach = {}
    for label, value in [("soft", "soft"), ("typo", "sotf")]:
        code, out, hashes = run_freeze(value)
        moved = code != 0
        named = value in out or "UnknownArm" in out or "STREHL_ROBUST" in out
        reach[label] = (code, tuple(hashes), moved, named)
        print(f"[{label}] exit={code} render_changed_or_refused={moved} "
              f"value_named_in_output={named}")

    print("\n=== VERDICT ===")
    off_ok = all(v[2] for v in results.values())
    print(f"off spellings + ungated all reproduce the baseline hash: {off_ok}")
    for h in baseline:
        print(f"    baseline hash: {h}")

    typo_refused = reach["typo"][2]
    soft_moved = reach["soft"][2]
    if typo_refused:
        print("REACHABLE: a bad value aborted the render, so the switch is read.")
        print(f"    soft arm moved the render: {soft_moved}")
        wired = True
    else:
        print("UNREACHABLE: a deliberately invalid value rendered successfully.")
        print("    `arm_from_setting` refuses an unknown key, so a clean render")
        print("    proves the render path never calls it. The null above is")
        print("    therefore VACUOUS -- it holds because no code changed, not")
        print("    because a live switch was set to off.")
        print("    This is the measurement, not a harness failure.")
        wired = False

    ok = stable and off_ok
    print(f"\nnull: {'HOLDS' if ok else 'BROKEN'}   switch wired into render: {wired}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

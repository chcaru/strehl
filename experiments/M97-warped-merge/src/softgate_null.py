"""M97 -- prove the soft-gate switch is a true no-op when off, and LIVE when on.

A null that reads "identical" is worthless unless the same wiring can be shown
to produce a difference (discipline 598). So this drives the *existing*
byte-freeze corpus suite -- the project's own regression net, which renders a
real 20-frame stack and SHA-256s the output -- once per switch setting:

    unset       -> must HOLD  (the shipped default cannot move)
    "off" / "0" -> must HOLD  (the off spellings are true no-ops)
    "gaussian"  -> must FAIL  (PLANT: proves the switch reaches the render)
    "exponential" -> must FAIL, and with a *different* hash than gaussian
    "nonsense"  -> must FAIL LOUDLY, naming the bad value

Exit codes are read from subprocess.returncode, never from $LASTEXITCODE after
a truncated pipeline (ORCH fact 1490).
"""

import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
CARGO = Path.home() / ".cargo" / "bin" / "cargo.exe"
ENV_NAME = "STREHL_SOFT_GATE"

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
        cwd=str(REPO),
        capture_output=True,
        env=env,
    )
    out = p.stdout.decode("utf-8", "replace") + p.stderr.decode("utf-8", "replace")
    # Only hashes the render actually PRODUCED. The failure report prints the
    # expected hash beside the actual one, and counting both was a defect in
    # the first version of this harness: it reported the gaussian arm as having
    # "reproduced a default hash" when that string was the expectation being
    # quoted back at us.
    produced = sorted(set(h for _, h in HOLDS_RE.findall(out)) | set(ACTUAL_RE.findall(out)))
    return p.returncode, out, produced


def main():
    arms = [
        ("unset", None, "HOLD"),
        ("off", "off", "HOLD"),
        ("zero", "0", "HOLD"),
        ("gaussian", "gaussian", "MOVE"),
        ("exponential", "exponential", "MOVE"),
        ("typo", "gausian", "REFUSE"),
    ]
    results = {}
    failures = []

    for label, value, want in arms:
        code, out, hashes = run_freeze(value)
        held = code == 0
        results[label] = (code, hashes, out)
        print("=" * 74)
        print(f"ARM {label!r}  {ENV_NAME}={value!r}  want={want}")
        print(f"  returncode = {code}   ({'HELD' if held else 'did not hold'})")
        for h in hashes:
            print(f"  hash {h}")

        if want == "HOLD" and not held:
            failures.append(f"{label}: expected the freeze to HOLD, exit {code}")
        if want == "MOVE" and held:
            failures.append(
                f"{label}: the freeze HELD with the kernel on -- the switch is "
                f"NOT reaching the render path (a disconnected probe)"
            )
        if want == "REFUSE":
            if held:
                failures.append(f"{label}: a nonsense value was accepted")
            elif "gausian" not in out:
                failures.append(f"{label}: refused, but did not name the bad value")
            else:
                print("  refused and named the bad value: OK")
        print()

    print("=" * 74)
    print("CROSS-ARM CHECKS")
    print("=" * 74)
    base = results["unset"][1]
    for label in ("off", "zero"):
        if results[label][1] != base:
            failures.append(f"{label}: hashes differ from unset")
        else:
            print(f"  {label:12s} hashes identical to unset  OK")

    g = results["gaussian"][1]
    e = results["exponential"][1]
    if g and set(g) & set(base):
        failures.append("gaussian reproduced a default hash")
    if g and e and set(g) == set(e):
        failures.append("gaussian and exponential produced identical output")
    elif g and e:
        print("  gaussian and exponential differ from each other  OK")

    print()
    print("=" * 74)
    if failures:
        print("FAILURES")
        for f in failures:
            print("  -", f)
        return 1
    print("ALL ARMS AS SPECIFIED")
    print("  the null is byte-identical AND the switch is proved live")
    return 0


if __name__ == "__main__":
    sys.exit(main())

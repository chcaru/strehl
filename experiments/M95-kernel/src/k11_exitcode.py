"""K11 -- can a truncated PowerShell pipeline falsify a command's exit status?

The orchestrator reported that `... | Select-String ... | Select-Object -First N`
makes `$LASTEXITCODE` read **0** after a command whose true exit code is 1, and
warned that this "turns a red control green". That is a claim about every
agent's instruments, including mine, so I reproduced it rather than adopting it.

BARS, REGISTERED BEFORE THE RUN
-------------------------------
The dangerous direction is a FALSE GREEN: a failing command read as success.
The benign direction is a FALSE RED: a succeeding command read as failure, or a
failure read with the wrong nonzero code. A gate written `if ($code -ne 0)
{ throw }` fails closed under a false red and fails OPEN under a false green.

CONFIRM-FALSE-GREEN : some arm reports 0 for a probe whose true code is 1.
                      => the orchestrator is right and my gates need auditing.
NO-FALSE-GREEN      : no arm does. => report that, and say which hazard is real.

Probes are chosen to separate the two candidate triggers:
  * fast  -- exits before the consumer can truncate; the process is already
             reaped when `Select-Object -First N` stops the pipeline.
  * slow  -- streams over ~6 s, so truncation stops it MID-RUN and PowerShell
             terminates it. Wall-clock is recorded as the positive control that
             truncation actually happened: a truncated arm must finish in ~1 s
             against ~6 s, otherwise the arm proves nothing.

Both exit-1 and exit-0 variants of the slow probe are run, because an
instrument that is wrong in only one direction is a different hazard from one
that is wrong in both.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
SRC = ROOT / "experiments" / "M95-kernel" / "src"
OUT = ROOT / "experiments" / "M95-kernel" / "out"

FAST = SRC / "k11_exit_probe.py"
SLOW = SRC / "k11_exit_probe_slow2.py"

PWSH = "pwsh.exe"
PS51 = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"

# (label, probe, true_code, pipeline suffix, expected to truncate)
ARMS = [
    ("fast exit1  no pipeline", FAST, 1, "", False),
    ("fast exit1  | Select-String", FAST, 1, "| Select-String 'Error'", False),
    ("fast exit1  | -First 3 of 10", FAST, 1, "| Select-String 'Error' | Select-Object -First 3", True),
    ("fast exit1  | -First 99", FAST, 1, "| Select-String 'Error' | Select-Object -First 99", False),
    ("fast exit1  | -Last 3", FAST, 1, "| Select-String 'Error' | Select-Object -Last 3", False),
    ("slow exit1  no pipeline", SLOW, 1, "", False),
    ("slow exit1  | -First 3 of 10", SLOW, 1, "| Select-String 'Error' | Select-Object -First 3", True),
    ("slow exit1  | -First 99", SLOW, 1, "| Select-String 'Error' | Select-Object -First 99", False),
    ("slow exit0  no pipeline", SLOW, 0, "", False),
    ("slow exit0  | -First 3 of 10", SLOW, 0, "| Select-String 'Error' | Select-Object -First 3", True),
]


def run_arm(shell, probe, true_code, suffix):
    arg = "" if probe == FAST else f" {true_code}"
    body = (
        "$env:PYTHONIOENCODING='utf-8'; "
        f"$null = python '{probe}'{arg} 2>&1 {suffix}; "
        "Write-Output $LASTEXITCODE"
    )
    t0 = time.time()
    p = subprocess.run(
        [str(shell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", body],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        errors="replace",
        timeout=300,
    )
    dt = time.time() - t0
    txt = (p.stdout or "").strip().splitlines()
    code = None
    for ln in reversed(txt):
        ln = ln.strip()
        if ln.lstrip("-").isdigit():
            code = int(ln)
            break
    return code, dt


R = {"shells": {}}
print("=" * 86)
print("K11  does a truncated pipeline falsify $LASTEXITCODE?")
print("=" * 86)

shells = []
for name, exe in (("pwsh (7.x)", PWSH), ("powershell (5.1)", PS51)):
    try:
        v = subprocess.run(
            [str(exe), "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            capture_output=True, text=True, timeout=90,
        )
        if v.returncode == 0:
            shells.append((name, exe, v.stdout.strip()))
    except Exception as e:  # noqa: BLE001
        print(f"  {name}: unavailable ({e})")

false_green = []
for name, exe, ver in shells:
    print(f"\n--- {name}   version {ver} ---")
    print(f"  {'arm':<34} {'true':>4} {'read':>5} {'secs':>5}  truncated  verdict")
    rows = []
    for label, probe, true_code, suffix, expect_trunc in ARMS:
        code, dt = run_arm(exe, probe, true_code, suffix)
        slow = probe == SLOW
        truncated = slow and dt < 3.5
        if code == true_code:
            verdict = "correct"
        elif code == 0 and true_code != 0:
            verdict = "FALSE GREEN"
            false_green.append((name, label))
        else:
            verdict = f"wrong ({code})"
        # A truncated slow arm must be fast, or truncation did not occur and
        # the arm carries no information.
        ctl = "yes" if truncated else ("no" if slow else "n/a")
        if expect_trunc and slow and not truncated:
            ctl = "NOT-TRUNCATED(!)"
        print(f"  {label:<34} {true_code:>4} {str(code):>5} {dt:>5.1f}  {ctl:<9}  {verdict}")
        rows.append({
            "arm": label, "true_code": true_code, "read_code": code,
            "seconds": round(dt, 2), "truncated": ctl, "verdict": verdict,
        })
    R["shells"][name] = {"version": ver, "rows": rows}

print("\n" + "=" * 86)
if false_green:
    print("VERDICT: CONFIRM-FALSE-GREEN")
    for s, l in false_green:
        print(f"  {s}: {l}")
else:
    print("VERDICT: NO-FALSE-GREEN -- no arm read 0 for a probe whose true code was 1.")
    print("  A failing command was never read as success on either shell tested.")
R["false_green"] = false_green
R["verdict"] = "CONFIRM-FALSE-GREEN" if false_green else "NO-FALSE-GREEN"
print("=" * 86)

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "k11_exitcode.json").write_text(json.dumps(R, indent=2), encoding="utf-8")
print(f"\nwrote {OUT / 'k11_exitcode.json'}")
sys.exit(0)

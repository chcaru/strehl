"""K19b -- was K11's "NO-FALSE-GREEN" verdict a property of the shell, or of my harness?

THE PROBLEM WITH K11, FOUND BY K19
-----------------------------------
K19 established that on pwsh 7.6.5 `-First` does not SET $LASTEXITCODE at all;
it leaves whatever was there (it read the seed 7 back, with the statement having
demonstrably run: DONE=True).

K11 ran every arm in a fresh session, where "whatever was there" is $null. So
K11 could report `None`, but it could NEVER report 0 for a true-1 probe on pwsh
-- not because the shell won't do that, but because K11 never put a 0 anywhere
to be inherited. Its NO-FALSE-GREEN verdict may therefore be a statement about
K11's own design rather than about PowerShell.

That is a power-control failure: an instrument that could not have said
otherwise. This script hands it the disturbance it was blind to.

DESIGN
------
Identical arm, three seeds. The ONLY difference is the exit code of the
command that ran BEFORE the pipeline:

    seed 0  <- simulates the overwhelmingly common real case: the previous
               command succeeded. If pwsh reads 0 here for a true-1 probe,
               that is a FALSE GREEN and the orchestrator's original report
               was right on this shell.
    seed 7  <- K19's discriminator; distinguishes "stale" from "set".
    seed 1  <- the confound the orchestrator warned about: a stale 1 that
               makes a broken arm look correct.

BARS, REGISTERED BEFORE THE RUN
-------------------------------
E0  every seed must take, else the arm is not connected -> hard error.
E1  the no-pipeline control must read 1 under ALL THREE seeds, else the probe
    cannot set a code at all and nothing it says about -First is readable.

FALSE-GREEN-CONFIRMED  the `-First` arm reads 0 under seed 0 for a true-1 probe
                       => K11 section 15.1's verdict is REFUTED and the
                          orchestrator's "reads 0" was right on that shell.
FALSE-GREEN-ABSENT     it does not
                       => K11's verdict stands on its own terms.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
SRC = ROOT / "experiments" / "M95-kernel" / "src"
OUT = ROOT / "experiments" / "M95-kernel" / "out"

FAST = SRC / "k11_exit_probe.py"
SLOW = SRC / "k11_exit_probe_slow2.py"
TRUE_CODE = 1
SEEDS = [0, 7, 1]

PWSH = "pwsh.exe"
PS51 = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"

ARMS = [
    ("no pipeline (control)", FAST, ""),
    ("| -First 3 of 10",      FAST, "| Select-String 'Error' | Select-Object -First 3"),
    ("| -Last 3",             FAST, "| Select-String 'Error' | Select-Object -Last 3"),
    ("SLOW | -First 3 of 10", SLOW, "| Select-String 'Error' | Select-Object -First 3"),
]


def run(shell, probe, suffix, seed):
    arg = "" if probe == FAST else f" {TRUE_CODE}"
    body = "\n".join([
        "$env:PYTHONIOENCODING='utf-8'",
        f"cmd /c exit {seed}",
        f"if ($LASTEXITCODE -ne {seed}) {{ Write-Output 'SEEDFAIL'; exit 9 }}",
        f"$null = python '{probe}'{arg} 2>&1 {suffix}",
        'Write-Output "CODE=$LASTEXITCODE"',
        'Write-Output "DONE"',
    ])
    t0 = time.time()
    p = subprocess.run([str(shell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", body],
                       cwd=str(ROOT), capture_output=True, text=True, errors="replace", timeout=300)
    dt = time.time() - t0
    if "SEEDFAIL" in (p.stdout or ""):
        raise SystemExit(f"E0 FAILED: seed {seed} did not take for {suffix!r}")
    code, done = None, False
    for ln in (p.stdout or "").splitlines():
        s = ln.strip()
        if s.startswith("CODE="):
            code = s[5:].strip()
        elif s == "DONE":
            done = True
    return code, done, dt


print("=" * 96)
print(f"K19b  same arm, three seeds. Probe's TRUE exit code is always {TRUE_CODE}.")
print("      A cell that echoes its seed means -First never set the code.")
print("=" * 96)

shells = []
for name, exe in (("pwsh (7.x)", PWSH), ("powershell (5.1)", PS51)):
    v = subprocess.run([str(exe), "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
                       capture_output=True, text=True, timeout=90)
    if v.returncode == 0:
        shells.append((name, exe, v.stdout.strip()))

R = {"true_code": TRUE_CODE, "seeds": SEEDS, "shells": {}}
false_green = []

for name, exe, ver in shells:
    print(f"\n--- {name}   version {ver} ---")
    print(f"  {'arm':<24} " + "  ".join(f"seed{s}->" for s in SEEDS) + "   reading")
    rows = []
    for label, probe, suffix in ARMS:
        cells, dones = [], []
        for seed in SEEDS:
            c, d, _ = run(exe, probe, suffix, seed)
            cells.append(c)
            dones.append(d)
        echoes_seed = all(c == str(s) for c, s in zip(cells, SEEDS))
        always_true = all(c == str(TRUE_CODE) for c in cells)
        if echoes_seed:
            reading = "NEVER SETS IT (echoes seed)"
        elif always_true:
            reading = "sets it correctly"
        else:
            reading = "mixed/corrupted"
        if cells[0] == "0":
            reading += "  <== FALSE GREEN under seed 0"
            false_green.append((name, label))
        cellstr = "  ".join(f"{str(c):>7}" for c in cells)
        print(f"  {label:<24} {cellstr}   {reading}")
        rows.append({"arm": label, "cells": dict(zip(map(str, SEEDS), cells)),
                     "statements_completed": dones, "reading": reading})

    ctl = [r for r in rows if r["arm"].startswith("no pipeline")][0]
    if not all(v == str(TRUE_CODE) for v in ctl["cells"].values()):
        print("  E1 FAILED: the no-pipeline control did not read the true code under every")
        print(f"             seed ({ctl['cells']}). Nothing this shell says about -First is readable.")
        sys.exit(2)
    print(f"  E1 PASS  no-pipeline control reads {TRUE_CODE} under all three seeds.")
    R["shells"][name] = {"version": ver, "rows": rows}

print("\n" + "=" * 96)
if false_green:
    print("VERDICT: FALSE-GREEN-CONFIRMED")
    for s, l in false_green:
        print(f"  {s}: {l}  read 0 for a probe whose true exit code was {TRUE_CODE}")
    print("\n  => M95-kernel.md section 15.1's 'NO-FALSE-GREEN' verdict is REFUTED.")
    print("     K11 could not produce this because every arm ran in a fresh session,")
    print("     where the inherited value is $null and never 0.")
else:
    print("VERDICT: FALSE-GREEN-ABSENT -- no arm read 0 under a seed of 0.")
R["verdict"] = "FALSE-GREEN-CONFIRMED" if false_green else "FALSE-GREEN-ABSENT"
R["false_green"] = false_green
print("=" * 96)

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "k19b_seeds.json").write_text(json.dumps(R, indent=2), encoding="utf-8")
print(f"\nwrote {OUT / 'k19b_seeds.json'}")

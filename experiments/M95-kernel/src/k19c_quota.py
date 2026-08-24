"""K19c -- is the `-First` quota rule host-independent? Measured on both shells.

WHY THIS EXISTS
---------------
The orchestrator's correction #2 (16:20) states the trap is "deterministic on
QUOTA: -First N loses the exit code whenever N <= the number of objects
produced", with 5/5 reps at the exact boundary (-First 50 LOST, -First 51
preserved) and 5-line output losing at -First 3.

K19b (this milestone, 15:5x) measured, SEEDED, on Windows PowerShell
5.1.26100.9168:

    | -First 3 of 10   seed0 -> 1   seed7 -> 1   seed1 -> 1   sets it correctly

That arm satisfies the quota condition (N=3 <= 10 objects) and PRESERVED the
code under a seed of 0 and a seed of 7. The stale-value confound cannot explain
it: a lost code under seed 0 reads 0, and under seed 7 reads 7. Both read 1.

So either the quota rule is host-dependent, or the difference is the pipeline
SHAPE -- K19b interposed `Select-String` between the native command and
`-First`, and the orchestrator's arms pipe directly. This measures both, at the
boundary, on both hosts.

CONFOUND EXPLICITLY AVOIDED
---------------------------
The orchestrator's own probe/scriptblock_masks_the_trap.ps1 found that routing
the filter through `& $scriptblock` changes the answer. A `switch` or a
parameterised dispatch would reintroduce exactly that. Every pipeline here is
emitted as LITERAL TEXT into the command body, with the seed literal too --
the same design that reproduced the trap in K19/K19b.

BARS, REGISTERED BEFORE THE RUN
-------------------------------
E0  the pre-clear must take on every arm (hard error otherwise).
E1  the no-pipeline control must read the true code under BOTH seeds on BOTH
    hosts, else nothing that host says is readable.
E2  reps within an arm must agree, else the arm is non-deterministic and is
    reported as such rather than summarised.

QUOTA-HOLDS(host)   every N <= objects arm LOSES and every N > objects arm
                    PRESERVES, on that host.
QUOTA-REFUTED(host) some N <= objects arm PRESERVES under both seeds.

PREDICTION, REGISTERED BEFORE RUNNING (from K19b, so it can be scored):
    pwsh 7.6.5  -> QUOTA-HOLDS
    5.1         -> QUOTA-REFUTED at N=3 over 10 lines, direct AND via
                   Select-String, because K19b's 5.1 fast arm preserved.
If 5.1 instead LOSES on the direct shape and PRESERVES only via Select-String,
the variable is pipeline shape rather than host, and I will say so.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
SRC = ROOT / "experiments" / "M95-kernel" / "src"
OUT = ROOT / "experiments" / "M95-kernel" / "out"
PROBE = SRC / "k19c_probe.py"

TRUE_CODE = 1
SEEDS = [0, 7]
REPS = 3

PWSH = "pwsh.exe"
PS51 = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"

# (label, lines, shape, N)  shape: "direct" | "ss" | "last" | "none"
ARMS = [
    ("no pipeline (control)",      50, "none",   0),
    ("50 lines | -First 3",        50, "direct", 3),
    ("50 lines | -First 49",       50, "direct", 49),
    ("50 lines | -First 50 exact", 50, "direct", 50),
    ("50 lines | -First 51",       50, "direct", 51),
    ("50 lines | -First 99",       50, "direct", 99),
    ("50 lines | SS | -First 3",   50, "ss",     3),
    ("50 lines | SS | -First 51",  50, "ss",     51),
    ("10 lines | -First 3",        10, "direct", 3),
    ("10 lines | SS | -First 3",   10, "ss",     3),
    ("50 lines | -Last 3",         50, "last",   3),
]


def body_for(seed, lines, shape, n):
    call = f"python '{PROBE}' {lines} {TRUE_CODE} 2>&1"
    if shape == "direct":
        pipe = f"$null = {call} | Select-Object -First {n}"
    elif shape == "ss":
        pipe = f"$null = {call} | Select-String 'Error' | Select-Object -First {n}"
    elif shape == "last":
        pipe = f"$null = {call} | Select-Object -Last {n}"
    else:
        pipe = f"$null = {call}"
    return "\n".join([
        "$env:PYTHONIOENCODING='utf-8'",
        f"cmd /c exit {seed}",
        f"if ($LASTEXITCODE -ne {seed}) {{ Write-Output 'SEEDFAIL'; exit 9 }}",
        pipe,
        'Write-Output "CODE=$LASTEXITCODE"',
    ])


def invoke(shell, body, mode):
    if mode == "Command":
        args = [str(shell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", body]
        tmp = None
    else:
        tmp = Path(tempfile.gettempdir()) / f"k19c_arm_{os.getpid()}.ps1"
        tmp.write_text(body, encoding="utf-8")
        args = [str(shell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(tmp)]
    try:
        p = subprocess.run(args, cwd=str(ROOT), capture_output=True,
                           text=True, errors="replace", timeout=300)
    finally:
        if tmp and tmp.exists():
            tmp.unlink()
    if "SEEDFAIL" in (p.stdout or ""):
        raise SystemExit("E0 FAILED: pre-clear did not take")
    for ln in (p.stdout or "").splitlines():
        s = ln.strip()
        if s.startswith("CODE="):
            return s[5:].strip()
    return "<absent>"


shells = []
for name, exe in (("pwsh 7.x", PWSH), ("powershell 5.1", PS51)):
    v = subprocess.run([str(exe), "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
                       capture_output=True, text=True, timeout=90)
    if v.returncode == 0:
        shells.append((name, exe, v.stdout.strip()))

print("=" * 100)
print(f"K19c  quota boundary on both hosts, PRE-CLEARED, {REPS} reps, true exit code {TRUE_CODE}")
print("      PREDICTION (registered): pwsh QUOTA-HOLDS; 5.1 QUOTA-REFUTED at N=3 over 10 lines")
print("=" * 100)

R = {"true_code": TRUE_CODE, "seeds": SEEDS, "reps": REPS, "shells": {}}

for name, exe, ver in shells:
    print(f"\n--- {name}   version {ver}   (-Command) ---")
    print(f"  {'arm':<28} {'objs':>5} {'N':>4}  {'seed0':>14} {'seed7':>14}   verdict")
    rows = []
    for label, lines, shape, n in ARMS:
        objs = lines
        cells = {}
        nondet = False
        for seed in SEEDS:
            reps = [invoke(exe, body_for(seed, lines, shape, n), "Command") for _ in range(REPS)]
            if len(set(reps)) != 1:
                nondet = True
            cells[str(seed)] = reps
        s0 = cells["0"]
        s7 = cells["7"]
        preserved = all(c == str(TRUE_CODE) for c in s0 + s7)
        lost = all(c == str(sd) for sd, reps in cells.items() for c in reps)
        if nondet:
            verdict = "NON-DETERMINISTIC"
        elif preserved:
            verdict = "preserved"
        elif lost:
            verdict = "LOST (echoes seed)"
        else:
            verdict = "corrupted"
        quota_pred = "lose" if (shape in ("direct", "ss") and n <= objs) else "keep"
        print(f"  {label:<28} {objs:>5} {n:>4}  {','.join(s0):>14} {','.join(s7):>14}   "
              f"{verdict}   quota says {quota_pred}")
        rows.append({"arm": label, "objects": objs, "N": n, "shape": shape,
                     "seed0": s0, "seed7": s7, "verdict": verdict,
                     "quota_predicts": quota_pred})

    ctl = next(r for r in rows if r["arm"].startswith("no pipeline"))
    if ctl["verdict"] != "preserved":
        print(f"  E1 FAILED on {name}: control did not read {TRUE_CODE} under both seeds "
              f"({ctl['seed0']} / {ctl['seed7']}). Nothing this host says is readable.")
        sys.exit(2)
    print(f"  E1 PASS  control reads {TRUE_CODE} under both seeds.")

    violations = [r for r in rows
                  if r["shape"] in ("direct", "ss")
                  and ((r["quota_predicts"] == "lose" and r["verdict"] == "preserved")
                       or (r["quota_predicts"] == "keep" and r["verdict"] != "preserved"))]
    holds = not violations
    print(f"  => {'QUOTA-HOLDS' if holds else 'QUOTA-REFUTED'} on {name}")
    for v in violations:
        print(f"       violation: {v['arm']}  N={v['N']} <= {v['objects']} objects "
              f"but {v['verdict']}")
    R["shells"][name] = {"version": ver, "rows": rows,
                         "quota": "HOLDS" if holds else "REFUTED",
                         "violations": [v["arm"] for v in violations]}

# -File mode on the single most contested arm
print("\n" + "-" * 100)
print("  -File vs -Command on '50 lines | -First 3' (the arm the orchestrator cites for -1)")
R["file_mode"] = {}
for name, exe, ver in shells:
    got = {}
    for mode in ("Command", "File"):
        got[mode] = {str(s): [invoke(exe, body_for(s, 50, "direct", 3), mode)
                              for _ in range(REPS)] for s in SEEDS}
    print(f"    {name:<16} -Command seed0={','.join(got['Command']['0'])} "
          f"seed7={','.join(got['Command']['7'])}   "
          f"-File seed0={','.join(got['File']['0'])} seed7={','.join(got['File']['7'])}")
    R["file_mode"][name] = got

print("\n" + "=" * 100)
verds = {n: R["shells"][n]["quota"] for n in R["shells"]}
print(f"QUOTA: {verds}")
if len(set(verds.values())) > 1:
    print("=> THE MECHANISM IS HOST-DEPENDENT. The quota rule is not universal.")
else:
    print("=> Same verdict on both hosts.")
print("=" * 100)

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "k19c_quota.json").write_text(json.dumps(R, indent=2), encoding="utf-8")
print(f"\nwrote {OUT / 'k19c_quota.json'}")

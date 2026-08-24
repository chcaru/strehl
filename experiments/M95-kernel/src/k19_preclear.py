"""K19 -- re-audit K11's "safe" arms with a SEEDED $LASTEXITCODE.

WHY THIS EXISTS
---------------
The orchestrator corrected the exit-code trap rule (15:51) and added a confound
K11 did not control for:

  "A naive A/B of this trap gives a FALSE NEGATIVE, because $LASTEXITCODE
   retains the previous command's value... any claim of the form 'X is safe'
   is only as good as its pre-clear."

K11 (experiments/M95-kernel/src/k11_exitcode.py) reported five arms as
"correct" per host. Those are exactly the "X is safe" claims the orchestrator
says are unestablished without a pre-clear, and K11 has no pre-clear line.

K11's DEFENCE, WHICH THIS SCRIPT TESTS RATHER THAN ASSERTS
----------------------------------------------------------
K11 runs every arm in a FRESH `-Command` process, so there is no previous
command to inherit from. If a fresh session starts with $LASTEXITCODE unset,
fresh-session isolation is at least as strong as a pre-clear and K11's safe
claims stand. That is an assumption about the host, so ARM 0 measures it.

WHY A SEED OF 7 RATHER THAN A PRE-CLEAR TO 0
---------------------------------------------
Pre-clearing to 0 discriminates two outcomes: "set" vs "failed to set". Seeding
a distinctive NONZERO discriminates four, which is what is actually needed here:

    CODE=1   -> the arm genuinely set the true code          SAFE, established
    CODE=7   -> stale retention; the arm never set it        SAFE CLAIM VOID
    CODE=0   -> false green, the dangerous direction         TRAP
    CODE=-1  -> corrupted to a wrong nonzero                 TRAP (fails closed)
    <absent> -> the read statement never executed            GATE SKIPPED

A pre-clear to 0 cannot tell CODE=1-genuine from CODE=1-stale, because it never
puts a 1 anywhere to be retained. The seed does.

K11 ALSO COULD NOT DISTINGUISH "PRINTED EMPTY" FROM "NEVER RAN"
----------------------------------------------------------------
K11 emitted a bare `Write-Output $LASTEXITCODE` and parsed the last digit-like
line, so `Write-Output $null` (an empty line) and a statement that never
executed both collapsed to None. This probe prints `CODE=<v>` and then a `DONE`
sentinel, so the two are separable.

BARS, REGISTERED BEFORE THE RUN
-------------------------------
E0  the seed must take on every arm (LASTEXITCODE -eq 7 after `cmd /c exit 7`),
    else that arm is not connected and is aborted rather than reported.
E1  at least one arm must read something other than 1, or this probe has not
    been shown able to detect anything and reports nothing.

VERDICT-STAND    every arm K11 called "correct" reads CODE=1 under the seed
                 => K11's safe claims are established, by isolation not luck.
VERDICT-VOID     any such arm reads CODE=7
                 => it never set the code and K11 reported a stale value.
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
SEED = 7

PWSH = "pwsh.exe"
PS51 = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"

# (label, probe, true_code, pipeline suffix, k11_verdict)
ARMS = [
    ("no pipeline",            FAST, 1, "",                                                  "correct"),
    ("| Select-String",        FAST, 1, "| Select-String 'Error'",                            "correct"),
    ("| -First 3 of 10",       FAST, 1, "| Select-String 'Error' | Select-Object -First 3",   "SPLIT"),
    ("| -First 99",            FAST, 1, "| Select-String 'Error' | Select-Object -First 99",  "correct"),
    ("| -Last 3",              FAST, 1, "| Select-String 'Error' | Select-Object -Last 3",    "correct"),
    ("| Out-String",           FAST, 1, "| Out-String",                                       "untested"),
    ("SLOW | -First 3 of 10",  SLOW, 1, "| Select-String 'Error' | Select-Object -First 3",   "wrong"),
    ("SLOW | -Last 3",         SLOW, 1, "| Select-String 'Error' | Select-Object -Last 3",    "untested"),
]


def ps(shell, body, timeout=300):
    t0 = time.time()
    p = subprocess.run(
        [str(shell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", body],
        cwd=str(ROOT), capture_output=True, text=True, errors="replace", timeout=timeout,
    )
    return p, time.time() - t0


def parse(out):
    """Return (code_str_or_None, statement_completed)."""
    code, done = None, False
    for ln in (out or "").splitlines():
        s = ln.strip()
        if s.startswith("CODE="):
            code = s[5:].strip()
        elif s == "DONE":
            done = True
    return code, done


def run_arm(shell, probe, true_code, suffix):
    arg = "" if probe == FAST else f" {true_code}"
    body = "\n".join([
        "$env:PYTHONIOENCODING='utf-8'",
        f"cmd /c exit {SEED}",
        f"if ($LASTEXITCODE -ne {SEED}) {{ Write-Output 'SEEDFAIL'; exit 9 }}",
        f"$null = python '{probe}'{arg} 2>&1 {suffix}",
        'Write-Output "CODE=$LASTEXITCODE"',
        'Write-Output "DONE"',
    ])
    p, dt = ps(shell, body)
    if "SEEDFAIL" in (p.stdout or ""):
        raise SystemExit(f"E0 FAILED: seed did not take for suffix {suffix!r}")
    code, done = parse(p.stdout)
    return code, done, dt


print("=" * 92)
print("K19  re-audit of K11's 'safe' arms, with $LASTEXITCODE SEEDED to 7 before each arm")
print("=" * 92)

shells = []
for name, exe in (("pwsh (7.x)", PWSH), ("powershell (5.1)", PS51)):
    try:
        v = subprocess.run([str(exe), "-NoProfile", "-Command",
                            "$PSVersionTable.PSVersion.ToString()"],
                           capture_output=True, text=True, timeout=90)
        if v.returncode == 0:
            shells.append((name, exe, v.stdout.strip()))
    except Exception as e:  # noqa: BLE001
        print(f"  {name}: unavailable ({e})")

R = {"seed": SEED, "shells": {}}
void, observed = [], set()

for name, exe, ver in shells:
    print(f"\n--- {name}   version {ver} ---")

    # ARM 0: does a fresh session start with $LASTEXITCODE unset?
    p0, _ = ps(exe, "\n".join([
        'Write-Output "CODE=$LASTEXITCODE"',
        'Write-Output "DONE"',
    ]), timeout=90)
    c0, d0 = parse(p0.stdout)
    unset = (c0 == "") and d0
    print(f"  ARM 0  fresh session, before any native command: CODE={c0!r} DONE={d0}"
          f"   -> {'UNSET (isolation holds)' if unset else 'PRE-SET (isolation BROKEN)'}")

    print(f"\n  {'arm':<22} {'true':>4} {'K11 said':>9} {'CODE':>6} {'ran':>5} {'secs':>5}  verdict")
    rows = []
    for label, probe, true_code, suffix, k11 in ARMS:
        code, done, dt = run_arm(exe, probe, true_code, suffix)
        observed.add(code)
        if code == str(true_code):
            verdict = "set correctly"
        elif code == str(SEED):
            verdict = "STALE - never set"
            if k11 == "correct":
                void.append((name, label))
        elif code == "" and not done:
            verdict = "statement ABORTED"
        elif code == "":
            verdict = "unset (null)"
        elif code == "0":
            verdict = "FALSE GREEN"
        else:
            verdict = f"wrong ({code})"
        print(f"  {label:<22} {true_code:>4} {k11:>9} {str(code):>6} {str(done):>5} {dt:>5.1f}  {verdict}")
        rows.append({"arm": label, "true_code": true_code, "k11_verdict": k11,
                     "code": code, "statement_completed": done,
                     "seconds": round(dt, 2), "verdict": verdict})
    R["shells"][name] = {"version": ver, "arm0_unset": unset, "arm0_code": c0, "rows": rows}

print("\n" + "=" * 92)
if len(observed - {"1"}) == 0:
    print("E1 FAILED: every arm read 1, so this probe has NOT been shown able to")
    print("           report anything else. It carries no information. Reporting nothing.")
    sys.exit(2)
print(f"E1 PASS  arms read more than one distinct value: {sorted(observed, key=str)}")

if void:
    print("\nVERDICT-VOID -- K11 reported a stale value as 'correct' on:")
    for s, l in void:
        print(f"    {s}: {l}")
else:
    print("\nVERDICT-STAND -- every arm K11 called 'correct' genuinely SET the code")
    print("                 under a seed of 7. K11's safe claims are established by")
    print("                 fresh-session isolation, not by inheriting a stale value.")
R["verdict"] = "VOID" if void else "STAND"
R["void_arms"] = void
print("=" * 92)

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "k19_preclear.json").write_text(json.dumps(R, indent=2), encoding="utf-8")
print(f"\nwrote {OUT / 'k19_preclear.json'}")

"""Negative control for verify_s23.py -- a gate that has never failed is not a gate.

Discipline 706: a control that has never been shown to fail is not a control.
Discipline 702: a gate must distinguish TOOL failure from SUBJECT failure in its
exit code, or a green run and a broken run are the same observation. So this
harness plants SUBJECT defects (expect rc=1) and TOOL defects (expect rc=2) and
requires the gate to tell them apart.

TWO RULES THIS HARNESS FOLLOWS, both from measured failures earlier in this
session:

  * Every mutation is anchored on a string asserted to occur EXACTLY ONCE, and
    the harness hard-errors if it does not land. A bare replace(x, y, 1) silently
    mutates the first chance occurrence, which produced a false GREEN on an
    earlier control in this project.
  * The report is restored from a byte copy taken before any mutation and the
    restoration is verified by SHA-256. NEVER `git checkout -- <path>`, which
    reverts to HEAD and has destroyed uncommitted work on this machine.
"""

import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
REPORT = os.path.join(ROOT, "docs", "research", "M95-kernel.md")
OUT = os.path.join(ROOT, "experiments", "M95-resample", "out")
GATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verify_s23.py")

# (label, unique anchor line, replacement, expected rc)
SUBJECT = [
    ("D1 numeric drift in the fitted exponent",
     "    log10(P) = \u22121.1839 + 1.0751 \u00b7 log10(L)",
     "    log10(P) = \u22121.1839 + 1.0752 \u00b7 log10(L)", 1),
    ("D2 sign flip on the overturn threshold",
     "| S_detail reaches 0.50 (becomes \"real signal\") | **\u22120.0250** | **188.1 se** |",
     "| S_detail reaches 0.50 (becomes \"real signal\") | **+0.0250** | **188.1 se** |", 1),
    ("D3 the dark-frame gain quietly improved",
     "| **dark frame, no photograph in it at all** | **+0.1285 dex** |",
     "| **dark frame, no photograph in it at all** | **+0.1385 dex** |", 1),
    ("D4 headline percentage inflated",
     "> the power in the 0.30\u20130.48 cyc/px band is real captured subject detail. 87.2%",
     "> the power in the 0.30\u20130.48 cyc/px band is real captured subject detail. 77.2%", 1),
    ("D5 the section 7 retraction removed",
     "  the owner is complaining about~~ **\u2014 RETRACTED, see \u00a723.** That clause is",
     "  the owner is complaining about. That clause is", 1),
    ("D6 a failed bar silently upgraded",
     "| F1 extrapolation guard | calibration **3208.7\u201314930.9 DN**, detail **2092.9\u201314171.2 DN** | **FAIL \u2014 headline is EXTRAPOLATED at the dim end** |",
     "| F1 extrapolation guard | calibration **3208.7\u201314930.9 DN**, detail **2092.9\u201314171.2 DN** | PASS |", 1),
    ("D7 the orchestrator section deleted",
     "### 23.12 For the orchestrator",
     "### 23.12 Miscellaneous", 1),
]


def sha(path):
    with io.open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run_gate():
    r = subprocess.run([sys.executable, GATE], capture_output=True)
    return r.returncode


def read():
    with io.open(REPORT, "r", encoding="utf-8", newline="") as fh:
        return fh.read()


def write(s):
    with io.open(REPORT, "w", encoding="utf-8", newline="") as fh:
        fh.write(s)


def main():
    backup = os.path.join(tempfile.gettempdir(), "M95-kernel.md.negctl.bak")
    shutil.copy2(REPORT, backup)
    before = sha(REPORT)
    print(f"backup  {backup}")
    print(f"sha256  {before}\n")

    rc = run_gate()
    print(f"baseline gate on the untouched report: rc={rc} "
          f"{'ok' if rc == 0 else 'TOOL PROBLEM -- cannot run controls'}")
    if rc != 0:
        shutil.copy2(backup, REPORT)
        print("restored; aborting")
        sys.exit(2)

    caught, missed = 0, []
    body = read()

    print("\n--- SUBJECT defects, each must produce rc=1 ---")
    for label, anchor, repl, want in SUBJECT:
        n = body.count(anchor)
        if n != 1:
            write(body)
            shutil.copy2(backup, REPORT)
            print(f"  HARNESS FAILURE: anchor for {label!r} occurs {n} times, expected 1")
            print(f"     anchor: {anchor[:90]!r}")
            sys.exit(2)
        write(body.replace(anchor, repl))
        got = run_gate()
        ok = got == want
        print(f"  {'CAUGHT ' if ok else 'MISSED '} {label}: rc={got} (want {want})")
        caught += ok
        if not ok:
            missed.append(label)
        write(body)

    print("\n--- TOOL defects, each must produce rc=2, not rc=1 ---")
    tool = 0
    art = os.path.join(OUT, "x17_close.json")
    hidden = art + ".hidden"
    os.rename(art, hidden)
    got = run_gate()
    ok = got == 2
    print(f"  {'CAUGHT ' if ok else 'MISSED '} T1 artifact missing: rc={got} (want 2)")
    tool += ok
    os.rename(hidden, art)

    write(body.replace("## 23. The scoring band is 87% noise", "## XX. removed", 1))
    got = run_gate()
    ok = got == 2
    print(f"  {'CAUGHT ' if ok else 'MISSED '} T2 section heading gone: rc={got} (want 2)")
    tool += ok
    write(body)

    after = sha(REPORT)
    same = after == before
    print(f"\nrestored byte-exact: {same}")
    if not same:
        shutil.copy2(backup, REPORT)
        print(f"  mismatch -- restored from {backup}; sha now {sha(REPORT)}")
        same = sha(REPORT) == before
        print(f"  byte-exact after backup restore: {same}")

    final = run_gate()
    print(f"gate on the restored report: rc={final}")

    print("\n" + "=" * 70)
    ok_all = (caught == len(SUBJECT) and tool == 2 and same and final == 0)
    print(f"subject defects caught {caught}/{len(SUBJECT)}   "
          f"tool defects distinguished {tool}/2   "
          f"report intact {same}   gate green after restore {final == 0}")
    if missed:
        for m in missed:
            print(f"    MISSED: {m}")
    print("NEGATIVE CONTROL PASS" if ok_all else "NEGATIVE CONTROL FAIL")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()

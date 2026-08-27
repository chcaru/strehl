"""Negative control for the launcher fix in `recert.py`.

The first full run rendered zero masters because `finalpass.ps1` died on
`Get-FileHash: The term ... is not recognized`. The diagnosis was that this
process inherits PowerShell 7's PSModulePath and passes it to Windows
PowerShell 5.1, which cannot load 7's modules.

A diagnosis is a claim and this project does not accept claims. This runs the
SAME launcher twice on ONE subject -- once with the inherited PSModulePath and
once with it dropped -- and requires the first to FAIL and the second to
SUCCEED. If both succeed, the fix is inert and the real cause is still at large;
if both fail, the diagnosis is wrong. Either way the answer is measured.

Run: python control_launcher.py
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recert import FINALPASS, OUT_ROOT, FLAGS, _ps_env, _ps_host  # noqa: E402

SUBJECT = "coffee-bubbles"


def run(arm, host, env):
    cmd = [host, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(FINALPASS),
           "-Exe", str(sys.argv[1]), "-Arm", arm, "-Flags", FLAGS,
           "-OutRoot", str(OUT_ROOT / "control"), "-NoPresent", "-Only", SUBJECT]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    out = r.stdout + r.stderr
    (OUT_ROOT / "logs").mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "logs" / f"control-{arm}.txt").write_text(out, encoding="utf-8")
    tiffs = list((OUT_ROOT / "control" / arm).glob("*.tiff"))
    broke = "is not recognized" in out
    return len(tiffs), broke, out


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: control_launcher.py <strehl.exe>")
    print(f"subject: {SUBJECT}   (one subject is enough: the failure was at startup)\n")

    # `os.environ` is case-insensitive on Windows; `dict(os.environ)` is NOT, and
    # its keys are upper-cased. An earlier version of this control read the plain
    # dict with the mixed-case name, printed `<unset>` for a variable that was
    # plainly set, and refused -- the same defect the fix under test had. Read the
    # case-insensitive mapping.
    psmp = os.environ.get("PSModulePath")
    print(f"PSModulePath inherited by this process:\n  {psmp or '<unset>'}\n")
    if not psmp:
        raise SystemExit("REFUSED: PSModulePath is not set in this process, so the broken arm "
                         "cannot be reproduced and the control would be vacuous.")
    if "powershell\\7" not in psmp.lower():
        raise SystemExit("REFUSED: the inherited PSModulePath does not point at PowerShell 7, "
                         "so arm A would not reproduce the failure this control exists to test.")

    n_bad, broke_bad, _ = run("CTL-INHERITED", "powershell", dict(os.environ))
    print(f"  A  powershell 5.1, PS7 module path inherited : {n_bad} master(s), "
          f"'is not recognized' {'PRESENT' if broke_bad else 'absent'}")

    n_ok, broke_ok, _ = run("CTL-FIXED", _ps_host(), _ps_env())
    print(f"  B  {Path(_ps_host()).stem} + _ps_env()"
          f"{' ' * max(0, 30 - len(Path(_ps_host()).stem))}: {n_ok} master(s), "
          f"'is not recognized' {'PRESENT' if broke_ok else 'absent'}")

    print()
    if broke_bad and n_bad == 0 and not broke_ok and n_ok == 1:
        print("CONTROL PASSED -- the inherited path reproduces the failure and the fix repairs "
              "it.\nThe diagnosis is measured, not assumed, and the fix is potent rather than "
              "merely present.")
        return 0
    if not broke_bad:
        print("CONTROL FAILED -- arm A did NOT reproduce the failure, so arm B's success proves "
              "nothing.\nThe fix is INERT against a cause I have not identified; do not trust it.")
        return 1
    print("CONTROL FAILED -- arm B did not render. The module path is not the whole cause.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

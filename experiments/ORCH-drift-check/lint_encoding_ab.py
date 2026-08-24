"""A/B the corpus_lint reporter fix under the encoding that broke it.

The crash was not visible interactively: Python only falls back to the ANSI
codepage (cp1252 here) when stdout is redirected or piped, which is exactly the
case when an agent captures the output or CI logs it. So the defect hid in the
one mode that matters and looked clean in the one mode a human uses.

Arm A: scripts/corpus_lint.py as committed at HEAD~ (pre-fix).
Arm B: the working-tree version (post-fix).
Both run with PYTHONIOENCODING=cp1252 and stdout captured, which reproduces the
piped case deterministically regardless of console settings.

Registered bars, before running:
  A1  arm A exits non-zero AND prints ZERO violation lines AND prints no
      "FAIL --" summary               -> confirms the defect is real
  A2  arm A's stderr contains UnicodeEncodeError
                                      -> confirms the mechanism is the encoder
  B1  arm B prints all 7 violation lines
  B2  arm B prints the "FAIL --" summary
  B3  arm B exits 1 (the exit-code contract is unchanged)
  B4  arm B's stderr contains no traceback
If A1/A2 fail, the fix is unfalsifiable here and the result must be discarded:
a green B alone proves nothing without a red A.
"""
import os
import re
import subprocess
import sys
import tempfile

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
REL = "scripts/corpus_lint.py"


def head_bytes(rev):
    # Never redirect `git show` through the shell on Windows: `>` re-encodes the
    # stream. Read the blob as bytes.
    p = subprocess.run(["git", "show", f"{rev}:{REL}"], cwd=ROOT,
                       capture_output=True)
    assert p.returncode == 0, p.stderr.decode("utf-8", "replace")
    return p.stdout


def run(script_path):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "cp1252"
    p = subprocess.run([sys.executable, script_path, "--root", ROOT],
                       cwd=ROOT, capture_output=True, env=env)
    return (p.returncode,
            p.stdout.decode("utf-8", "replace"),
            p.stderr.decode("utf-8", "replace"))


VIOL = re.compile(r"^docs/research/.*: \[S\d\] ", re.M)


def main():
    tmp = tempfile.mkdtemp(prefix="lintab-")
    a_path = os.path.join(tmp, "lint_head.py")
    with open(a_path, "wb") as f:
        f.write(head_bytes("HEAD"))

    rc_a, out_a, err_a = run(a_path)
    rc_b, out_b, err_b = run(os.path.join(ROOT, "scripts", "corpus_lint.py"))

    n_a = len(VIOL.findall(out_a))
    n_b = len(VIOL.findall(out_b))

    bars = [
        ("A1 pre-fix hides every violation",
         rc_a != 0 and n_a == 0 and "FAIL —" not in out_a and "FAIL --" not in out_a),
        ("A2 pre-fix mechanism is the encoder", "UnicodeEncodeError" in err_a),
        ("B1 post-fix prints all 7 violations", n_b == 7),
        ("B2 post-fix prints the FAIL summary", "FAIL" in out_b and "violation(s)" in out_b),
        ("B3 post-fix exit code still 1", rc_b == 1),
        ("B4 post-fix stderr has no traceback", "Traceback" not in err_b),
    ]

    print(f"arm A (HEAD)   rc={rc_a} violations_printed={n_a} stderr={len(err_a)}B")
    print(f"arm B (fixed)  rc={rc_b} violations_printed={n_b} stderr={len(err_b)}B")
    print("")
    ok = True
    for name, passed in bars:
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
        ok &= passed
    print("")
    if not bars[0][1] or not bars[1][1]:
        print("DISCARD: arm A did not reproduce the defect, so arm B proves nothing.")
    print("RESULT:", "ALL BARS PASS" if ok else "BARS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

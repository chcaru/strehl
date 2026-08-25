"""Negative control for verify_report.py.

A verifier that has never been shown to fail is not evidence. Plants one wrong
digit on a full-line anchor and requires the verifier to go RED. The anchor is
a complete table row, and the script hard-errors if it does not land -- a
mutation that silently fails to apply produces a green that means nothing.

The report is restored from a copy under $env:TEMP, never with `git checkout`.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPORT = Path(r"C:\dev\blog\death-of-software\projects\strehl\docs\research\M116-promotion.md")
VERIFY = Path(__file__).with_name("verify_report.py")
BACKUP = Path(os.environ["TEMP"]) / "M116-report-negctl.md"

ANCHOR = ("| A2 softgate gaussian | bee-3-cpl | `-0.02044` | `-0.01218` | "
          "`+0.00826` | **FAIL** | **FAIL** | **FAIL** | PASS |")
DEFECT = ANCHOR.replace("`-0.01218`", "`-0.01228`")


def run():
    r = subprocess.run([sys.executable, str(VERIFY)],
                       capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


shutil.copy2(REPORT, BACKUP)
try:
    rc, out = run()
    print(f"[baseline]  rc={rc}  {out.splitlines()[-1]}")
    if rc != 0:
        raise SystemExit("baseline is not green; cannot commission")

    text = REPORT.read_text(encoding="utf-8")
    if text.count(ANCHOR) != 1:
        raise SystemExit(
            f"MUTATION TARGET NOT FOUND: anchor occurs {text.count(ANCHOR)} "
            "times, expected exactly 1")
    REPORT.write_text(text.replace(ANCHOR, DEFECT), encoding="utf-8")

    rc, out = run()
    print(f"[defect]    rc={rc}  {out.splitlines()[-1]}")
    ok = rc != 0
finally:
    shutil.copy2(BACKUP, REPORT)

rc, out = run()
print(f"[restored]  rc={rc}  {out.splitlines()[-1]}")
if rc != 0:
    raise SystemExit("restore failed; report does not verify")

print("COMMISSIONED - the verifier catches a one-digit defect"
      if ok else "USELESS - the verifier passed a planted defect")
sys.exit(0 if ok else 1)

"""Negative control for `verify_report.py`.

Discipline 594: a green verifier is a claim about the world only if it could
have said otherwise, and the claim is only admissible if it is *shown* saying
otherwise. This plants three defects, one in each place a defect could hide,
and requires the verifier to go green -> red -> green on each.

The three defects are chosen to probe different failure modes:

* **D1** -- a number in the report changed. Catches a transcription error.
* **D2** -- a number in the *source JSON* changed, report untouched. Catches a
  verifier that reads the report twice instead of comparing two artefacts.
* **D3** -- a fact label removed. Catches the structural pass being decorative.

Mutations are anchored on unique full-line strings and hard-error if they do
not land. A mutation that silently misses turns this control into a lie: it
would report "the verifier stayed green under a defect" when in truth no defect
was ever planted. Restores are byte-for-byte from an in-memory copy of the
original, and the file's mtime is touched so nothing downstream serves a stale
read.

Exit 0 = the control passed (verifier discriminates). Exit 1 = it did not.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REPORT = ROOT / "docs" / "research" / "M95-kernel.md"
K3 = HERE.parent / "out" / "k3_kernel.json"
VERIFY = HERE / "verify_report.py"


def run_verifier():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run(
        [sys.executable, str(VERIFY)], capture_output=True, text=True, env=env, cwd=str(ROOT)
    )
    return p.returncode


def touch(p):
    os.utime(p, (time.time(), time.time()))


def mutate_text(path, old, new):
    s = path.read_text(encoding="utf-8")
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"MUTATION TARGET NOT FOUND (or ambiguous): {old!r} occurs {n}x in {path.name}")
    path.write_text(s.replace(old, new), encoding="utf-8")
    touch(path)


def main():
    print("negative control for verify_report.py\n")
    rc = run_verifier()
    print(f"  baseline                                       rc={rc}  {'GREEN' if rc == 0 else 'RED'}")
    if rc != 0:
        print("\nBASELINE IS NOT GREEN -- the control cannot run.")
        return 1

    report_orig = REPORT.read_bytes()
    k3_orig = K3.read_bytes()
    results = []

    try:
        # D1 -- a number in the report is wrong.
        mutate_text(
            REPORT,
            "| catmull-rom | 62.5000 DN | **6.2500%** | 2 px |",
            "| catmull-rom | 62.7000 DN | **6.2700%** | 2 px |",
        )
        rc = run_verifier()
        results.append(("D1 report number changed (K22 step)", rc != 0, rc))
        print(f"  D1 report number changed (K22 step)            rc={rc}  {'RED (good)' if rc else 'GREEN (BAD)'}")
        REPORT.write_bytes(report_orig)
        touch(REPORT)

        # D2 -- a number in the source JSON is wrong, report untouched.
        doc = json.loads(K3.read_text(encoding="utf-8"))
        before = doc["b24_election"]["b24_lanczos3"]
        doc["b24_election"]["b24_lanczos3"] = before * 1.5
        K3.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        touch(K3)
        rc = run_verifier()
        results.append(("D2 source JSON changed (B24 flip rate)", rc != 0, rc))
        print(f"  D2 source JSON changed (B24 flip rate)         rc={rc}  {'RED (good)' if rc else 'GREEN (BAD)'}")
        K3.write_bytes(k3_orig)
        touch(K3)

        # D3 -- a fact label is missing.
        mutate_text(REPORT, "**P97.**", "P97 (unlabelled).")
        rc = run_verifier()
        results.append(("D3 fact label stripped (P97)", rc != 0, rc))
        print(f"  D3 fact label stripped (P97)                   rc={rc}  {'RED (good)' if rc else 'GREEN (BAD)'}")
        REPORT.write_bytes(report_orig)
        touch(REPORT)

    finally:
        # Restore unconditionally, even if a mutation raised.
        REPORT.write_bytes(report_orig)
        K3.write_bytes(k3_orig)
        touch(REPORT)
        touch(K3)

    rc = run_verifier()
    print(f"  restored                                       rc={rc}  {'GREEN' if rc == 0 else 'RED'}")
    restored_ok = rc == 0
    assert REPORT.read_bytes() == report_orig, "report not byte-identical after restore"
    assert K3.read_bytes() == k3_orig, "k3_kernel.json not byte-identical after restore"
    print("  byte-identical restore verified for both files")

    ok = restored_ok and all(r[1] for r in results)
    print(f"\n  {sum(1 for r in results if r[1])}/{len(results)} planted defects detected")
    print(f"\n{'CONTROL PASSED -- the verifier discriminates' if ok else 'CONTROL FAILED -- the verifier is decorative'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

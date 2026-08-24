"""Negative control for verify_s22.

A gate that has never been shown to fail is not a gate (discipline 706). This
plants defects one at a time into the live report and requires verify_s22 to
catch each one, then restores the file and proves the restore was byte-exact.

Three kinds of arm:
  DEFECT arms - plant a wrong number or delete a required sentence; the gate
                must exit 1 AND print at least one BAD. Requiring both is what
                separates "found a violation" from "crashed", which post-e3c01aa
                are different observations (discipline 702).
  TOOL arm    - break the verifier itself; it must exit 2, not 0 and not 1.
  POWER arm   - corrupt an artifact the gate hashes off disk, so the on-disk
                hash checks are shown to be live rather than vacuously green.

Anchors are single-line and unique. They are never built from truncated output,
and a miss is a hard error rather than a silent no-op: a plant that does not
land produces a green run that looks exactly like a working gate.

Never uses `git checkout --`. The file is stashed to a byte copy and restored
from that copy.
"""

import hashlib
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
REPORT = REPO / "docs" / "research" / "M95-kernel.md"
VERIFY = HERE / "verify_s22.py"
MONTAGE = pathlib.Path(r"C:\dev\strehl-out\M95-montage\M95-kernel-montage.png")

# (label, exact single-line substring to find, what to replace it with)
DEFECTS = [
    ("mitchell identity dex",
     "| **mitchell** | **-0.200830** | **FAIL, not interpolating** |",
     "| **mitchell** | **-0.200831** | **FAIL, not interpolating** |"),
    ("R4 ratio",
     "| lanczos3 | 37.34 DN | 28.63 DN | **1.30x** | 11 124 | 9 829 407 |",
     "| lanczos3 | 37.34 DN | 28.63 DN | **1.90x** | 11 124 | 9 829 407 |"),
    ("R6 recovered DN",
     "**R6, the power control, passed: 1874.4 DN recovered of 2000 planted, 93.7%.**",
     "**R6, the power control, passed: 1874.9 DN recovered of 2000 planted, 93.7%.**"),
    ("the refusal to call it ringing",
     "measuring, **this is not ringing and I will not call it ringing.**",
     "measuring, **this is clearly ringing and I will call it ringing.**"),
    ("catmull-rom render hash",
     "| catmull-rom | `E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17112` | 330.606 s |",
     "| catmull-rom | `E400A63AA9F6AB1F1957940D7BD9D4965D67E01F6F0E1A0A7ABC30D8E7F17113` | 330.606 s |"),
    ("lanczos2 gain over catmull-rom",
     "| lanczos2 | -0.1963 | **+0.0043** | 2.0 px |",
     "| lanczos2 | -0.1963 | **+0.0143** | 2.0 px |"),
    ("arm 11 pre-registration provenance",
     "B25 to B29 were committed at `42a0c7c`, 15:04:14, before `lanczos2` appeared in",
     "B25 to B29 were committed at `4200000`, 15:04:14, before `lanczos2` appeared in"),
]


def run_verify():
    p = subprocess.run([sys.executable, str(VERIFY)], capture_output=True,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    out = p.stdout.decode("utf-8", "replace")
    return p.returncode, out.count("  BAD  "), out


def main():
    original = REPORT.read_bytes()
    stash = pathlib.Path(tempfile.mkdtemp(prefix="m95negctl_")) / "M95-kernel.md"
    stash.write_bytes(original)
    print(f"stashed {len(original)} bytes to {stash}")
    sha0 = hashlib.sha256(original).hexdigest()

    rc, bad, _ = run_verify()
    print(f"baseline: rc={rc} bad={bad}  {'GREEN' if rc == 0 and bad == 0 else 'NOT GREEN'}")
    if rc != 0 or bad != 0:
        sys.exit("BASELINE IS NOT GREEN; a negative control on a red gate proves nothing")

    caught, total = 0, 0
    text = original.decode("utf-8")
    for label, old, new in DEFECTS:
        total += 1
        n = text.count(old)
        if n != 1:
            REPORT.write_bytes(stash.read_bytes())
            sys.exit(f"ANCHOR FOR {label!r} OCCURS {n} TIMES, EXPECTED 1 -- "
                     f"nothing was planted and this run proves nothing")
        REPORT.write_bytes(text.replace(old, new, 1).encode("utf-8"))
        rc, bad, _ = run_verify()
        hit = (rc == 1 and bad > 0)
        caught += hit
        print(f"  {'CAUGHT ' if hit else 'MISSED '} {label:38s} rc={rc} bad={bad}")
        REPORT.write_bytes(stash.read_bytes())
        if hashlib.sha256(REPORT.read_bytes()).hexdigest() != sha0:
            sys.exit(f"RESTORE AFTER {label!r} WAS NOT BYTE-EXACT")

    print("\n-- TOOL ARM: the verifier must exit 2 when it is the thing that broke --")
    tool = HERE / "_negctl_s22_toolarm.py"
    src = VERIFY.read_text(encoding="utf-8")
    marker = "sys.excepthook = _boom"
    if src.count(marker) != 1:
        sys.exit("TOOL ARM ANCHOR DID NOT LAND")
    tool.write_bytes(src.replace(
        marker, marker + "\n\nraise RuntimeError('planted tool failure')", 1
    ).encode("utf-8"))
    p = subprocess.run([sys.executable, str(tool)], capture_output=True,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    tool_ok = p.returncode == 2
    print(f"  {'PASS' if tool_ok else 'FAIL'}  planted exception -> rc={p.returncode} "
          f"(must be 2, not 0 and not 1)")
    tool.unlink()

    print("\n-- POWER ARM: the on-disk hash checks must not be vacuously green --")
    power_ok = False
    if MONTAGE.exists():
        mstash = stash.parent / "montage.png"
        shutil.copy2(MONTAGE, mstash)
        m0 = hashlib.sha256(MONTAGE.read_bytes()).hexdigest()
        with MONTAGE.open("ab") as f:
            f.write(b"\x00")
        rc, bad, _ = run_verify()
        power_ok = (rc == 1 and bad > 0)
        print(f"  {'PASS' if power_ok else 'FAIL'}  appended one byte to the montage "
              f"-> rc={rc} bad={bad}")
        shutil.copy2(mstash, MONTAGE)
        if hashlib.sha256(MONTAGE.read_bytes()).hexdigest() != m0:
            sys.exit("MONTAGE RESTORE WAS NOT BYTE-EXACT")
        print("  montage restored byte-identical")
    else:
        print("  SKIPPED, montage not on disk")

    rc, bad, _ = run_verify()
    print(f"\nafter restore: rc={rc} bad={bad}  "
          f"{'GREEN' if rc == 0 and bad == 0 else 'NOT GREEN'}")
    print(f"report restored byte-identical: "
          f"{hashlib.sha256(REPORT.read_bytes()).hexdigest() == sha0}")
    print(f"\nnegctl_s22: {caught}/{total} defects caught; "
          f"tool arm {'PASS' if tool_ok else 'FAIL'}; "
          f"power arm {'PASS' if power_ok else 'FAIL'}")
    ok = (caught == total and tool_ok and power_ok and rc == 0 and bad == 0)
    print("negctl_s22: " + ("PASS" if ok else "FAIL"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

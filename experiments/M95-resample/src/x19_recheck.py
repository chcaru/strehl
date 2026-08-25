"""Re-check M95's gates against the two corrections ORCH broadcast at 19:25.

ITEM 1 -- $LASTEXITCODE is not updated after a truncated pipeline, so it
retains the PREVIOUS command's code, and the error runs in both directions.
The instruction is to re-run any pass/fail gate rather than reason about which
direction it would have taken. Every gate is re-run here through
subprocess.run().returncode, which has none of that behaviour, and the LITERAL
code is printed rather than a predicate -- so a reader can see the value, not
my opinion of it.

ITEM 2 -- a backtick in a PowerShell @"..."@ here-string eats itself AND the
following letter, turning `bee-3-cpl` into 0x08 + "ee-3-cpl". corpus_lint's
new S7 check covers this, but a check I did not write is not evidence about my
files until I have looked at my files. This scans them directly for control
bytes and reports the offending letter's context, because the repair is to
restore the eaten letter, never to delete the byte.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
SRC = ROOT / "experiments" / "M95-resample" / "src"

GATES = [
    ("verify_s23", SRC / "verify_s23.py", 0),
    ("negctl_s23", SRC / "negctl_s23.py", 0),
    ("verify_s24", SRC / "verify_s24.py", 0),
    ("negctl_s24", SRC / "negctl_s24.py", 0),
]

print("=" * 66)
print("ITEM 1: gates re-run on subprocess returncode, literal values")
print("=" * 66)
bad_gate = False
for name, path, want in GATES:
    r = subprocess.run(
        [sys.executable, str(path)], capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    tail = [ln for ln in (r.stdout or "").strip().splitlines() if ln.strip()]
    last = tail[-1] if tail else "(no output)"
    ok = r.returncode == want
    bad_gate |= not ok
    print(f"  {name:12s} EXIT={r.returncode}  (want {want})  {'ok' if ok else 'MISMATCH'}")
    print(f"               {last[:88]}")

# corpus_lint reports its verdict on stdout AND in its exit code; print both.
r = subprocess.run(
    [sys.executable, str(ROOT / "scripts" / "corpus_lint.py")],
    capture_output=True, text=True, cwd=str(ROOT), encoding="utf-8", errors="replace",
)
s7 = "S7" in (r.stdout or "")
print(f"  {'corpus_lint':12s} EXIT={r.returncode}  (want 0)  S7 present in checks: {s7}")
for ln in (r.stdout or "").splitlines():
    if "violation" in ln.lower() or "OK" in ln:
        print(f"               {ln.strip()[:88]}")
bad_gate |= r.returncode != 0 or not s7

print()
print("=" * 66)
print("ITEM 2: control-byte scan of every file M95 wrote")
print("=" * 66)

targets: list[Path] = [ROOT / "docs" / "research" / "M95-kernel.md"]
targets += sorted(SRC.glob("*.py"))
targets += sorted((ROOT / "experiments" / "M95-resample" / "out").glob("*.json"))

ALLOWED = {0x09, 0x0A, 0x0D}
findings = 0
for p in targets:
    data = p.read_bytes()
    hits = [(i, b) for i, b in enumerate(data) if b < 0x20 and b not in ALLOWED]
    if hits:
        findings += len(hits)
        print(f"  CONTROL BYTES in {p.relative_to(ROOT)}: {len(hits)}")
        for i, b in hits[:6]:
            ctx = data[max(0, i - 24): i + 24].decode("utf-8", "replace")
            print(f"    offset {i} byte 0x{b:02X} context: {ctx!r}")
print(f"  scanned {len(targets)} files, {findings} control byte(s) found")

# A scan that has only ever said clean is an untested scan. Prove it can fire.
probe = b"the bracket " + bytes([0x08]) + b"ee-3-cpl was measured"
probe_hits = [(i, b) for i, b in enumerate(probe) if b < 0x20 and b not in ALLOWED]
print(f"  positive control (planted 0x08 from a backtick-eaten `bee-3-cpl): "
      f"{len(probe_hits)} hit(s) -- scanner {'FIRES' if probe_hits else 'IS BLIND'}")

ok = (findings == 0) and bool(probe_hits) and not bad_gate
print()
print("VERDICT:", "clean -- nothing reported by M95 is invalidated" if ok else "SOMETHING NEEDS ATTENTION")
sys.exit(0 if ok else 1)

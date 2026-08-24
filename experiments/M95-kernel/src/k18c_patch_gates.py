"""Apply discipline 702's minimum to every gate in this milestone.

k18b_gates.py measured 2 of 10 read-only gates as EXPOSED today. The other
eight are not safe, only lucky: they print report text, and the day a report
gains a minus sign they behave exactly like verify_s16.py and verify_s20.py
did. This inserts the two-line stdout repair into every verify_*.py and
negctl_*.py that lacks it.

It is deliberately the SHALLOW fix. The deep fix -- a distinct exit code for
tool failure -- is applied by hand to verify_s20.py and negctl_s20.py, the pair
behind the live result, because it changes what a caller may conclude and
should not be made by a script.

Each patched file is byte-compiled before the change is kept. Anything that
fails to compile is rolled back from the in-memory original.
"""
import py_compile
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(__file__).resolve().parents[3]
DIRS = [ROOT / "experiments" / "M95-kernel" / "src",
        ROOT / "experiments" / "M95-coverage" / "src"]

PATCH = (
    "\n# Discipline 702: this gate reports through stdout and its exit code is read as\n"
    "# a claim. Python picks the ANSI codepage for piped stdout, which is every agent\n"
    "# tool call and every CI log, and cp1252 cannot encode the minus signs and arrows\n"
    "# this corpus uses. Without this, print() raises mid-run and the process exits 1:\n"
    "# indistinguishable from a real failure. Measured in k18_gate702.py.\n"
    "sys.stdout.reconfigure(encoding=\"utf-8\", errors=\"backslashreplace\")\n"
    "sys.stderr.reconfigure(encoding=\"utf-8\", errors=\"backslashreplace\")\n"
)

targets = sorted(
    p for d in DIRS for pat in ("verify_*.py", "negctl_*.py") for p in d.glob(pat)
)

print(f"{len(targets)} gate(s) found")
patched = skipped = failed = 0
for p in targets:
    src = p.read_text(encoding="utf-8")
    if "reconfigure(" in src:
        print(f"  skip    {p.parents[1].name}/{p.name}  (already repaired)")
        skipped += 1
        continue

    lines = src.splitlines(keepends=True)
    last_import = None
    for i, ln in enumerate(lines[:60]):
        if ln.startswith("import ") or ln.startswith("from "):
            last_import = i
    if last_import is None:
        print(f"  FAIL    {p.parents[1].name}/{p.name}  (no import block found)")
        failed += 1
        continue
    if "import sys" not in src:
        lines.insert(last_import + 1, "import sys\n")
        last_import += 1

    new = "".join(lines[: last_import + 1]) + PATCH + "".join(lines[last_import + 1 :])
    p.write_text(new, encoding="utf-8", newline="")
    try:
        py_compile.compile(str(p), cfile=str(Path(tempfile.gettempdir()) / "chk.pyc"),
                           doraise=True)
    except py_compile.PyCompileError as exc:
        p.write_text(src, encoding="utf-8", newline="")
        print(f"  FAIL    {p.parents[1].name}/{p.name}  rolled back: {exc.msg.strip()[:60]}")
        failed += 1
        continue
    print(f"  patched {p.parents[1].name}/{p.name}")
    patched += 1

print(f"\npatched {patched}, already repaired {skipped}, failed {failed}")
sys.exit(1 if failed else 0)

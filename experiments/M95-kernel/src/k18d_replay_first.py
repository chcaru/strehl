"""Preserve the 5/7 first run of negctl_s21 as an artifact rather than a memory.

Section 21.8 reports that the control caught five of seven on its first run and
that the two misses were real holes. That number was printed by code, but its
capture file was overwritten by the passing run, and a number recalled from my
own earlier output is not a measurement. So it is re-derived here: regress the
two hardening changes, replay the control, restore, and check the restore.

The regressions are anchored on unique full-line strings and this script hard
errors if any anchor fails to land. A silent no-op would produce a 7/7 replay
and a confident, wrong claim that the holes never existed.

The hardened file is copied to TEMP first and restored from that copy, never
from git: reverting a working file to HEAD destroys uncommitted work.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(__file__).resolve().parents[3]
SRC = Path(__file__).resolve().parent
VERIFY = SRC / "verify_s21.py"
NEGCTL = SRC / "negctl_s21.py"
OUT = SRC.parent / "out"

REGRESSIONS = [
    # 1. the ambiguity guard, which is what caught the twin-token hole
    ("""    seen = hay.count(token)
    if seen > 1:
        tool_failure(
            f"AMBIGUOUS TOKEN for {label!r}: {token!r} occurs {seen} times near "
            f"{ctx!r}; mutating one copy would leave the other and read green"
        )
    if seen == 1:""",
     """    seen = hay.count(token)
    if token in hay:"""),
    # 2. the anchor that contained a neighbouring claim's value
    ('num("cp1252 arm ok lines", f"| {c_ok} | none |", "`PYTHONIOENCODING=cp1252` | 1 |")',
     'num("cp1252 arm ok lines", c_ok, "`PYTHONIOENCODING=cp1252` | 1 | 1937 |")'),
    # 3. the token with a twin three lines below the table
    ('num("post-fix fleet", f"**{n_exp_post} of {len(FPOST)} exposed**", "restored 4")',
     'num("post-fix fleet", f"{n_exp_post} of {len(FPOST)} exposed", "restored 4")'),
]

hardened = VERIFY.read_bytes()
stash = Path(tempfile.gettempdir()) / "verify_s21.hardened.py"
stash.write_bytes(hardened)
print(f"hardened copy saved: {stash} ({len(hardened)} bytes)")

text = hardened.decode("utf-8").replace("\r\n", "\n")
for i, (old, new) in enumerate(REGRESSIONS, 1):
    n = text.count(old)
    if n != 1:
        shutil.copyfile(stash, VERIFY)
        sys.exit(f"REGRESSION {i} ANCHOR DID NOT LAND ({n} occurrences); nothing replayed")
    text = text.replace(old, new, 1)
    print(f"  regression {i} applied")

VERIFY.write_text(text, encoding="utf-8", newline="\n")
try:
    r = subprocess.run([sys.executable, str(NEGCTL)], capture_output=True, cwd=str(ROOT))
    log = r.stdout.decode("utf-8", "replace") + r.stderr.decode("utf-8", "replace")
finally:
    shutil.copyfile(stash, VERIFY)

restored = VERIFY.read_bytes() == hardened
print(f"\nverifier restored byte-identical: {restored}")
if not restored:
    sys.exit("RESTORE FAILED")

(OUT / "negctl_s21_FIRST.txt").write_text(log, encoding="utf-8")
print("wrote out/negctl_s21_FIRST.txt\n")
for line in log.splitlines():
    if "CAUGHT" in line or "MISSED" in line or "negative control:" in line:
        print("  " + line.strip())
print(f"\nreplay exit code: {r.returncode}")

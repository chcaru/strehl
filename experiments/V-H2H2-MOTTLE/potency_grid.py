"""V-H2H2: potency control on the escape-check fix.

The audit reports REVERSE_ESCAPE as caught. That is only evidence that the FIX
works if the harness MISSED it beforehand -- otherwise I added a check that
detects nothing new and merely believe I closed a hole. ORCH's lesson: "an inert
plant and a dead instrument give the identical green"; the dual is that a green
fix and an already-covered case give the identical red.

So: take griddiag.py AS COMMITTED AT HEAD (before the return-type check), inject
ONLY the root override so it can be pointed at a scratch tree -- changing no
check whatsoever -- and run the identical REVERSE_ESCAPE mutation through it.

Expected: HEAD = GREEN (misses it), worktree = RED (catches it).
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REAL = Path(r"C:\dev\blog\death-of-software\projects\strehl")
REL_GD = "experiments/V-H2H2-MOTTLE/griddiag.py"
ALIGN = "crates/strehl-cli/src/align_cmd.rs"
SOURCES = [ALIGN, "crates/strehl-cli/src/merge_cmd.rs", "crates/strehl-core/src/pyramid.rs"]

# Read the blob as BYTES via subprocess. Redirecting `git show` through
# PowerShell's `>` re-encodes the stream and silently corrupts the comparison.
# Pinned to the commit that PRECEDES the fix, not to HEAD. When the fix was
# uncommitted, HEAD was the pre-fix version and this control was valid. The
# moment 58e08649 landed, HEAD became the FIXED version and "before" ceased to
# exist -- the control would have compared the fixed script against itself, seen
# RED on both arms, and printed a green that proved nothing. It did not, because
# the injection guard below refused. A control whose reference point moves is a
# control that expires silently; this one now cannot.
PRE_FIX = "a3ae2dd3"
blob = subprocess.run(["git", "show", f"{PRE_FIX}:{REL_GD}"], cwd=REAL,
                      capture_output=True).stdout.decode("utf-8")
if not blob.strip():
    raise SystemExit(f"cannot read {PRE_FIX}:{REL_GD} -- control is void")

OLD_ROOT = 'ROOT = Path(r"C:\\dev\\blog\\death-of-software\\projects\\strehl")'
NEW_ROOT = ('import os as _os\n'
            'ROOT = Path(_os.environ.get("STREHL_GRIDDIAG_ROOT", '
            'r"C:\\dev\\blog\\death-of-software\\projects\\strehl"))')
if blob.count(OLD_ROOT) != 1:
    raise SystemExit(f"cannot inject root override into HEAD copy "
                     f"({blob.count(OLD_ROOT)} matches) -- control is void")
head_gd = blob.replace(OLD_ROOT, NEW_ROOT, 1)

# Confirm the HEAD copy genuinely predates the fix, else the control proves
# nothing about the fix.
if "warp_frame_in_place_fullres signature not found" in head_gd:
    raise SystemExit("HEAD copy already contains the return-type check -- "
                     "there is no 'before' to compare against; control is void")


def mutate_escape(root):
    p = root / ALIGN
    t = p.read_text(encoding="utf-8", errors="replace")
    i = t.find("pub fn warp_frame_in_place_fullres(")
    j = t.find(") -> Result<f64> {", i)
    if i < 0 or j < 0:
        raise SystemExit("MUTATION TARGET NOT FOUND -- control is void")
    p.write_text(t[:j] + ") -> Result<(f64, Vec<f32>)> {"
                 + t[j + len(") -> Result<f64> {"):], encoding="utf-8")


def trial(griddiag_text, mutate):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for rel in SOURCES:
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REAL / rel, dst)
        if mutate:
            mutate(root)
        gd = root / "griddiag.py"
        gd.write_text(griddiag_text, encoding="utf-8")
        env = dict(os.environ, STREHL_GRIDDIAG_ROOT=str(root))
        r = subprocess.run([sys.executable, str(gd)], capture_output=True,
                           text=True, env=env)
        return r.returncode, r.stdout + r.stderr


work_gd = (REAL / REL_GD).read_text(encoding="utf-8")

print("=" * 74)
print("POTENCY CONTROL -- does the return-type check catch anything NEW?")
print("=" * 74)
print(f"{'griddiag version':<22}{'mutation':<18}{'want':<8}{'got':<8}")

trials = [
    ("a3ae2dd3 (pre-fix)", "none",           "GREEN", head_gd, None),
    ("a3ae2dd3 (pre-fix)", "REVERSE_ESCAPE", "GREEN", head_gd, mutate_escape),
    ("worktree (fixed)", "none",         "GREEN", work_gd, None),
    ("worktree (fixed)", "REVERSE_ESCAPE", "RED",  work_gd, mutate_escape),
]
bad = 0
for ver, mut, want, text, fn in trials:
    rc, out = trial(text, fn)
    got = "GREEN" if rc == 0 else "RED"
    ok = got == want
    bad += not ok
    print(f"{ver:<22}{mut:<18}{want:<8}{got:<8}{'ok' if ok else '<<< WRONG'}")
    if not ok:
        print("   " + "\n   ".join(out.strip().splitlines()[-6:]))

print()
if bad:
    sys.exit(f"CONTROL FAILED ({bad} of {len(trials)} arms wrong)")
print("CONTROL PASSED: the mutation is real, HEAD was blind to it, and the")
print("return-type check is what closed the hole. The 6/6 is not self-flattery.")

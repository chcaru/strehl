#!/usr/bin/env python3
"""Commit exactly this lane's change, through a private index, while another
lane holds the shared file staged.

WHY THIS EXISTS, AND WHY THE OBVIOUS METHODS ARE ALL WRONG HERE.
`scripts/check-defaults.py` was handed to this lane exclusively, but by the
time the edit was written BUILD-PLUGIN had a `STREHL_GATE_FLOOR` entry in the
same file AND had run `git add` on it, which swept this lane's four new
entries into THEIR index alongside their own work. That rules out every
ordinary route:

  * `git commit -m ...` (no pathspec) commits their whole staged tree --
    gatefloor.rs, pyramid.rs, byte-freeze.rs -- under this lane's message.
  * `git commit -- scripts/check-defaults.py` takes the WORKTREE content,
    which contains their GATE_FLOOR entry. That entry declares a switch whose
    source file `gatefloor.rs` is not in HEAD, so committing it alone would
    publish a registry that declares a switch the crates do not contain.
  * `git add -p` / `git apply --cached` mutate the shared index they are
    about to commit from, i.e. it races them at the worst possible moment.

THE METHOD: build the intended blob explicitly (HEAD's content plus this
lane's block, nothing else), stage it into a PRIVATE index created from HEAD's
tree via GIT_INDEX_FILE, and commit that tree with commit-tree/update-ref. The
shared index and the working tree are never written. The other lane's `git
commit` afterwards proceeds exactly as it would have.

THE CRLF LESSON THIS SCRIPT ENCODES. The previous cross-lane commit
(439563ff) used `git apply --cached --ignore-whitespace --recount`, which is
the only way that patch would apply -- and it wrote 39 lines with CRLF
terminators into a file that is otherwise pure LF, because `git apply --cached`
writes the index DIRECTLY and bypasses the `core.autocrlf=true` clean filter
that a plain `git add` would have applied. `corpus_lint` caught it as
`[S4] committed with MIXED line endings`, and the defect was this lane's.
So every blob here is normalised to LF and ASSERTED to be LF before staging.
A script that repeats a known defect is worse than no script.

REFUSES rather than guessing: if the extracted block is not found exactly
once, if the reconstruction does not round-trip, or if any blob still holds a
CR, it exits non-zero and stages nothing.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
INDEX = Path(r"C:\dev\strehl-out\BUILD-DEFECT\45-index")

REGISTRY_FILE = "scripts/check-defaults.py"
# The block this lane appended, identified by its first entry. It runs to the
# end of the REGISTRY dict, because the four entries were appended last.
BLOCK_START = '    "STREHL_DEFECT": Declared(\n'
REGISTRY_END = "\n}\n"

EXTRA_FILES = [
    "experiments/BUILD-DEFECT/src/44-default-arms.ps1",
    "experiments/BUILD-DEFECT/out/44-default-arms.log",
    "experiments/BUILD-DEFECT/src/45-isolated-commit.py",
]

MESSAGE = """defect: declare the four STREHL_DEFECT switches, measured

`scripts/check-defaults.py` was RED with four undeclared switches, all of them
this lane's. A switch nobody has declared is a switch nobody has decided the
default for, which is the defect that file exists to catch.

STREHL_DEFECT is declared `verified="measured"` on three arms of one pinned
binary (f30ffdf8, coffee-bean --limit 10, pyramid, identical flags):

    unset  -> E15D9ED90A1C36B4   "defect map      : off (STREHL_DEFECT=off)"
    on     -> 8E4D18ED4A4E9B7F   2/2 sites confirmed, (3434,2305) -14.945%
    bogus  -> exit 1, "is not a setting; it is \\"on\\" or \\"off\\""

Same byte length, different bytes, so the switch moves pixels; the bogus arm
proves the read happens, which is what makes the pair interpretable at all.

All four are `control`, not `quality`, and the notes say out loud why off is
right today: the mote's coordinate is disputed 17x between lanes, and this
lane's own MANUFACTURE arm injects +8.64%..+16.44% at a clean site, so a wrong
coordinate on the default path would stamp a defect into every frame. They are
not labelled `quality` and flipped on to clear the check.

STREHL_DEFECT_ARM and STREHL_DEFECT_HOT_FLOOR are recorded as NOT INDEPENDENT
of the master switch: both are read in defect_arms_from_env, called only at
stack.rs:959, after the early return at :955-957. With STREHL_DEFECT unset
they are never read at all -- the STREHL_SMOOTH_HUBER shape. HOT_FLOOR is
inert twice over, since the default arm `dust` does not select the hot arm.

Checked rather than assumed, per the handover: the byte-freeze corpus CANNOT
reach this code path. Every registry row hardcodes `--merge estimator` in
`argv`, the correction lives in the pyramid loader, and the estimator refuses
a configured map. The hardcoded STREHL_DEFECT=off in `Freeze::env()` spells
out the value those rows already render under; it does not suppress a feature
to hold a hash still. Harness and product agree that unset means off.

Committed through a private index: BUILD-PLUGIN holds this file staged with
its own STREHL_GATE_FLOOR entry, which is excluded here because its source
gatefloor.rs is not in HEAD.
"""


def git(*args, **kw):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, **kw)


def die(msg):
    print(f"REFUSING: {msg}")
    sys.exit(1)


def main():
    head_blob = git("cat-file", "-p", f"HEAD:{REGISTRY_FILE}").stdout
    work = (REPO / REGISTRY_FILE).read_bytes()

    start = BLOCK_START.encode()
    if work.count(start) != 1:
        die(f"block start found {work.count(start)} times, expected exactly 1")
    if head_blob.count(start) != 0:
        die("HEAD already contains the block; nothing to do, or the wrong base")

    i = work.index(start)
    j = work.index(REGISTRY_END.encode(), i)
    block = work[i:j + 1]  # include the trailing newline, not the `}`

    # Reconstruct: HEAD content with the block inserted at HEAD's registry end.
    # Anchored on the LAST entry in HEAD rather than on the first `\n}\n` in
    # the file -- a bare `}` at column 0 closes any dict literal, so an
    # unanchored search would silently splice into the wrong one.
    anchor = b'"STREHL_CONFIDENCE_DEBUG": Declared('
    if head_blob.count(anchor) != 1:
        die(f"anchor entry found {head_blob.count(anchor)} times, expected 1")
    k = head_blob.index(REGISTRY_END.encode(), head_blob.index(anchor))
    rebuilt = head_blob[:k + 1] + block + head_blob[k + 1:]

    # --- refusals -------------------------------------------------------
    if b"STREHL_GATE_FLOOR" in rebuilt:
        die("reconstruction contains BUILD-PLUGIN's STREHL_GATE_FLOOR entry")
    for name in (b'"STREHL_DEFECT"', b'"STREHL_DEFECT_MAP"',
                 b'"STREHL_DEFECT_ARM"', b'"STREHL_DEFECT_HOT_FLOOR"'):
        if rebuilt.count(name + b": Declared(") != 1:
            die(f"{name.decode()} not declared exactly once")
    rebuilt = rebuilt.replace(b"\r\n", b"\n")
    if b"\r" in rebuilt:
        die("a CR survived normalisation in the registry blob")

    print(f"HEAD blob     : {len(head_blob):7d} bytes")
    print(f"block lifted  : {len(block):7d} bytes")
    print(f"reconstruction: {len(rebuilt):7d} bytes, LF only, 4 entries, no GATE_FLOOR")

    # --- private index --------------------------------------------------
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    if INDEX.exists():
        INDEX.unlink()
    env = dict(os.environ, GIT_INDEX_FILE=str(INDEX))

    def pgit(*args, **kw):
        return subprocess.run(["git", *args], cwd=REPO, env=env,
                              capture_output=True, **kw)

    r = pgit("read-tree", "HEAD")
    if r.returncode:
        die(f"read-tree: {r.stderr.decode()}")

    def stage(path, data):
        data = data.replace(b"\r\n", b"\n")
        if b"\r" in data:
            die(f"CR survived in {path}")
        sha = subprocess.run(["git", "hash-object", "-w", "--no-filters", "--stdin"],
                             cwd=REPO, input=data, capture_output=True
                             ).stdout.decode().strip()
        r = pgit("update-index", "--add", "--cacheinfo", f"100644,{sha},{path}")
        if r.returncode:
            die(f"update-index {path}: {r.stderr.decode()}")
        print(f"  staged {path}  {sha[:12]}  {len(data)} bytes")

    stage(REGISTRY_FILE, rebuilt)
    for f in EXTRA_FILES:
        stage(f, (REPO / f).read_bytes())

    tree = pgit("write-tree").stdout.decode().strip()
    head = git("rev-parse", "HEAD").stdout.decode().strip()

    # The tree must differ from HEAD in EXACTLY the files named above.
    changed = git("diff", "--name-only", head, tree).stdout.decode().split()
    expected = sorted([REGISTRY_FILE] + EXTRA_FILES)
    if sorted(changed) != expected:
        die(f"tree touches {changed}, expected {expected}")
    print(f"tree {tree[:12]} touches exactly {len(changed)} intended files")

    commit = subprocess.run(["git", "commit-tree", tree, "-p", head],
                            cwd=REPO, input=MESSAGE.encode(),
                            capture_output=True).stdout.decode().strip()
    r = git("update-ref", "HEAD", commit, head)
    if r.returncode:
        die(f"update-ref: {r.stderr.decode()}")
    print(f"committed {commit[:12]} on top of {head[:12]}")
    INDEX.unlink()


if __name__ == "__main__":
    main()

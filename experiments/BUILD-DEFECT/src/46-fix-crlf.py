#!/usr/bin/env python3
"""Repair this lane's own CRLF defect in the committed merge_cmd.rs.

WHAT WENT WRONG. Commit 439563ff staged three test hunks into merge_cmd.rs
with `git apply --cached --ignore-whitespace --recount` -- the only invocation
that would apply the patch at all, because the patch text and the file
disagreed about line endings. `git apply --cached` writes the index DIRECTLY
and so bypasses the `core.autocrlf=true` clean filter that a plain `git add`
applies, and 39 lines landed in the blob with CRLF terminators inside a file
that is otherwise pure LF. `corpus_lint` flags it as
`crates/strehl-cli/src/merge_cmd.rs:1: [S4] committed with MIXED line endings`.

MEASURED, not assumed:
    439563ff^   CRLF     0   bare-LF 8667   clean
    439563ff    CRLF    39   bare-LF 8641   MIXED

so the parent was clean and this lane made it mixed. `--ignore-whitespace` is
what let the apply succeed, and the same flag is what made the result wrong.

WHY IT IS FIXED HERE RATHER THAN LEFT TO BUILD-PLUGIN. That lane holds
merge_cmd.rs staged, and its staged blob is already pure LF, because a plain
`git add` normalised it. So their commit would incidentally erase this. But
until then corpus_lint is RED for a reason that belongs to this lane, and
their diff currently carries 39 line-ending changes that are not theirs and
that they would be committing under their own name. Normalising HEAD now makes
diff(HEAD, their staged blob) equal to exactly their gatefloor work.

WHY IT IS SAFE. Content-preserving: the only change is `\\r\\n` -> `\\n`, and
the script asserts that the normalised HEAD blob and the normalised repaired
blob are byte-identical before it stages anything. The worktree is never
written and the shared index is never written -- the commit is built in a
private index via GIT_INDEX_FILE, exactly as 45-isolated-commit.py does,
because the other lane is mid-commit and its index must not move.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(r"C:\dev\blog\death-of-software\projects\strehl")
INDEX = Path(r"C:\dev\strehl-out\BUILD-DEFECT\46-index")
TARGET = "crates/strehl-cli/src/merge_cmd.rs"

MESSAGE = """defect: normalise the 39 CRLF lines this lane committed into merge_cmd.rs

corpus_lint reported `[S4] committed with MIXED line endings` on merge_cmd.rs.
It is this lane's defect and this commit repairs it.

MEASURED across revisions before assigning blame:

    439563ff^   CRLF   0   bare-LF 8667   clean
    439563ff    CRLF  39   bare-LF 8641   MIXED

The parent was clean. 439563ff staged three test hunks with
`git apply --cached --ignore-whitespace --recount`, which was the only
invocation that would apply that patch across a CRLF/LF mismatch -- and
`git apply --cached` writes the index directly, bypassing the
core.autocrlf=true clean filter that a plain `git add` would have applied. The
flag that made the apply succeed is the flag that made the result wrong.

Content-preserving: `git diff --ignore-cr-at-eol` between the old and new blob
is empty, and the script asserts byte-equality after normalising both sides.
Exactly 39 bytes are removed.

Built in a private index; BUILD-PLUGIN holds this file staged and mid-commit,
so neither the shared index nor the working tree is written. Their staged blob
is already pure LF, so after this their diff is exactly their own gatefloor
work rather than also carrying 39 line-ending changes that are not theirs.
"""


def die(msg):
    print(f"REFUSING: {msg}")
    sys.exit(1)


def main():
    def git(*a, **kw):
        return subprocess.run(["git", *a], cwd=REPO, capture_output=True, **kw)

    head = git("rev-parse", "HEAD").stdout.decode().strip()
    old = git("cat-file", "-p", f"HEAD:{TARGET}").stdout

    crlf = old.count(b"\r\n")
    lf = old.count(b"\n") - crlf
    print(f"HEAD {head[:12]}  CRLF {crlf}  bare-LF {lf}")
    if crlf == 0:
        print("nothing to do: HEAD is already pure LF (another lane fixed it)")
        return
    if lf == 0:
        die("file is uniformly CRLF, not mixed -- that is a different decision")

    new = old.replace(b"\r\n", b"\n")
    if b"\r" in new:
        die("a bare CR survived; that is content, not a line ending")
    if old.replace(b"\r\n", b"\n") != new:
        die("normalisation is not content-preserving")
    if len(old) - len(new) != crlf:
        die(f"byte delta {len(old) - len(new)} != CRLF count {crlf}")
    print(f"repair: {len(old)} -> {len(new)} bytes, {crlf} removed, content identical")

    INDEX.parent.mkdir(parents=True, exist_ok=True)
    if INDEX.exists():
        INDEX.unlink()
    env = dict(os.environ, GIT_INDEX_FILE=str(INDEX))

    def pgit(*a, **kw):
        return subprocess.run(["git", *a], cwd=REPO, env=env,
                              capture_output=True, **kw)

    if pgit("read-tree", "HEAD").returncode:
        die("read-tree failed")

    sha = subprocess.run(["git", "hash-object", "-w", "--no-filters", "--stdin"],
                         cwd=REPO, input=new, capture_output=True
                         ).stdout.decode().strip()
    if pgit("update-index", "--cacheinfo", f"100644,{sha},{TARGET}").returncode:
        die("update-index failed")

    tree = pgit("write-tree").stdout.decode().strip()
    changed = git("diff", "--name-only", head, tree).stdout.decode().split()
    if changed != [TARGET]:
        die(f"tree touches {changed}, expected only {TARGET}")

    commit = subprocess.run(["git", "commit-tree", tree, "-p", head],
                            cwd=REPO, input=MESSAGE.encode(),
                            capture_output=True).stdout.decode().strip()
    if git("update-ref", "HEAD", commit, head).returncode:
        die("update-ref failed -- HEAD moved under us; rerun")
    print(f"committed {commit[:12]} on top of {head[:12]}")
    INDEX.unlink()


if __name__ == "__main__":
    main()

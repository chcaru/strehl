"""Split my hunks of merge_cmd.rs from BUILD-PLUGIN's.

BUILD-PLUGIN has `merge_cmd.rs` dirty with an uncommitted `gatefloor` module
whose file (`merge_cmd/gatefloor.rs`) is not even tracked yet. Committing the
whole file would (a) commit another lane's work under my message and (b) break
the build for everyone, because `mod gatefloor;` would point at a file that is
not in the repository.

My change is three hunks in `mod tests`, all above line SPLIT of the original.
Theirs are all below it. This prints my hunks only, so they can be staged with
`git apply --cached` and theirs left untouched in the working tree.

It refuses rather than guessing if the split is not clean: if any hunk on
either side of SPLIT mentions `gatefloor`, or if no hunk survives, it exits
non-zero and stages nothing.
"""

import re
import subprocess
import sys

FILE = "crates/strehl-cli/src/merge_cmd.rs"
SPLIT = 8000
MARKER = "gatefloor"

d = subprocess.run(
    ["git", "--no-pager", "diff", "-U3", "--", FILE],
    capture_output=True, text=True, check=True,
).stdout

lines = d.splitlines(keepends=True)
head, hunks, cur = [], [], None
for ln in lines:
    if ln.startswith("@@"):
        if cur is not None:
            hunks.append(cur)
        cur = [ln]
    elif cur is None:
        head.append(ln)
    else:
        cur.append(ln)
if cur is not None:
    hunks.append(cur)

mine, theirs = [], []
for h in hunks:
    old = int(re.match(r"@@ -(\d+)", h[0]).group(1))
    (mine if old >= SPLIT else theirs).append(h)

bad = [h for h in mine if any(MARKER in x for x in h)]
if bad:
    print(f"REFUSING: {len(bad)} hunk(s) above line {SPLIT} mention {MARKER!r}; "
          "the split is not clean", file=sys.stderr)
    sys.exit(2)
if not mine:
    print(f"REFUSING: no hunk above line {SPLIT}; nothing of mine to stage",
          file=sys.stderr)
    sys.exit(2)

print(f"mine: {len(mine)} hunk(s)   theirs: {len(theirs)} hunk(s) "
      f"({sum(1 for h in theirs if any(MARKER in x for x in h))} mention "
      f"{MARKER!r})", file=sys.stderr)
sys.stdout.write("".join(head) + "".join("".join(h) for h in mine))

"""Commit only MY hunks, from a temporary index, leaving the working tree alone.

Five lanes share this working tree and two of my three files carry other
agents' uncommitted work in the SAME file -- BUILD-HALO is live in
`edge_aware_arm()` in merge_cmd.rs, and someone is editing the photometric help
in main.rs. `git commit -- <path>` commits the whole working-tree file, so a
path-scoped commit would sweep their in-flight work into my commit under my
message. That has already happened twice in this repository.

There is no path-scoped way to separate two agents' edits to one file, so this
does it hunk-wise:

  1. read HEAD into a TEMPORARY index (GIT_INDEX_FILE), never the shared one
  2. take the working-tree diff, keep only hunks in my declared line ranges
  3. `git apply --cached` that filtered patch into the temp index only
  4. write-tree / commit-tree / update-ref

The working tree is never written, so the other lanes keep their changes and
`git status` afterwards shows exactly their hunks and nothing of mine.

Every step is checked. A filter that silently selected zero hunks, or a patch
that silently failed to apply, would produce a green run and an empty commit --
which is the failure this project keeps rediscovering, so each is a hard error.

CHANGED 2026-08-26, and the reason matters. Step 2 originally took `git diff`,
which is worktree-vs-INDEX, while step 1 builds the temp index from HEAD. Those
are different bases whenever another lane has something STAGED, and one did: a
staged edit to check-defaults.py at line ~196 that is not in the worktree and
that shortens the file by 4 lines. My hunk therefore appeared at old-side 288
against the index but 292 against HEAD, so the patch would have been applied to
a base it was not computed against and `git apply` would have had to guess.
It now diffs against HEAD explicitly, which is the base the temp index actually
has.

Usage:
    python commit_mine.py <msgfile> <path>:<lo>:<hi> [<path>:<lo>:<hi> ...]

where lo..hi bound the NEW-side start line of the hunks that are mine. Ranges
are given per invocation rather than hard-coded, because a stale range from a
previous commit either fails loudly or, much worse, sweeps a hunk that has since
become somebody else's.
"""
import os
import re
import subprocess
import sys
import tempfile

REPO = r"C:\dev\blog\death-of-software\projects\strehl"

# path -> (min_new_start, max_new_start) of the hunks that are MINE.
# Derived from `git diff -U0` and verified against the other lanes' hunk
# positions: in merge_cmd.rs theirs sit at 133/142 and 1701+, in main.rs at
# 437+. The gaps either side are wide, so -U3 context cannot merge a hunk of
# mine with a hunk of theirs.
# Filled from argv. path -> (min_new_start, max_new_start) of the hunks that
# are MINE. See the usage note in the docstring: these are deliberately NOT
# hard-coded, because a range left over from an earlier commit is a loaded gun.
MINE: dict[str, tuple[int, int]] = {}

# The temp index is built from HEAD, so the patch must be computed against HEAD
# too. See the CHANGED note in the docstring.
DIFF_BASE = "HEAD"

HUNK = re.compile(rb"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def git(*args, **kw):
    r = subprocess.run(["git", "-C", REPO, *args], capture_output=True, **kw)
    if r.returncode != 0:
        sys.exit(f"FAILED: git {' '.join(args)}\n{r.stderr.decode('utf-8', 'replace')}")
    return r.stdout


def filter_patch(path, lo, hi):
    """Return the patch bytes for `path` containing only hunks in [lo, hi]."""
    raw = git("diff", DIFF_BASE, "-U3", "--", path)
    if not raw.strip():
        sys.exit(f"FAILED: no diff at all for {path}")
    lines = raw.split(b"\n")
    header, hunks, cur, kept, dropped = [], [], None, 0, 0
    for ln in lines:
        m = HUNK.match(ln)
        if m:
            if cur is not None:
                hunks.append(cur)
            cur = [int(m.group(1)), [ln]]
        elif cur is not None:
            cur[1].append(ln)
        else:
            header.append(ln)
    if cur is not None:
        hunks.append(cur)

    out = list(header)
    for start, body in hunks:
        if lo <= start <= hi:
            out.extend(body)
            kept += 1
        else:
            dropped += 1
    if kept == 0:
        sys.exit(f"FAILED: filter kept ZERO hunks for {path}. An empty selection "
                 f"would commit nothing and still exit green.")
    print(f"  {path}: kept {kept} hunk(s), left {dropped} for other lanes")
    return b"\n".join(out), kept, dropped


def main():
    msg_path = sys.argv[1]
    specs = sys.argv[2:]
    if not specs:
        sys.exit("no <path>:<lo>:<hi> specs given -- refusing to commit nothing")
    for spec in specs:
        path, lo, hi = spec.rsplit(":", 2)
        MINE[path.replace("\\", "/")] = (int(lo), int(hi))
    head = git("rev-parse", "HEAD").decode().strip()
    print(f"HEAD = {head}")
    print(f"diff base = {DIFF_BASE}")

    tmpdir = tempfile.mkdtemp(prefix="blend-idx-")
    idx = os.path.join(tmpdir, "index")
    env = dict(os.environ, GIT_INDEX_FILE=idx)

    # Build the index from HEAD, NOT from the shared index -- the shared one
    # currently holds staged content belonging to other lanes.
    subprocess.run(["git", "-C", REPO, "read-tree", "HEAD"], env=env, check=True)

    total = 0
    for path, (lo, hi) in MINE.items():
        patch, kept, _ = filter_patch(path, lo, hi)
        pf = os.path.join(tmpdir, os.path.basename(path) + ".patch")
        with open(pf, "wb") as f:
            f.write(patch if patch.endswith(b"\n") else patch + b"\n")
        r = subprocess.run(
            ["git", "-C", REPO, "apply", "--cached", "--whitespace=nowarn", pf],
            env=env, capture_output=True)
        if r.returncode != 0:
            sys.exit(f"FAILED: could not apply my hunks for {path}\n"
                     f"{r.stderr.decode('utf-8', 'replace')}")
        total += kept

    tree = subprocess.run(["git", "-C", REPO, "write-tree"], env=env,
                          capture_output=True, check=True).stdout.decode().strip()
    if tree == git("rev-parse", "HEAD^{tree}").decode().strip():
        sys.exit("FAILED: the resulting tree is identical to HEAD's. Nothing "
                 "would be committed.")

    commit = git("commit-tree", tree, "-p", head, "-F", msg_path).decode().strip()
    git("update-ref", "refs/heads/main", commit, head)
    print(f"committed {commit[:7]} with {total} hunk(s)")

    # The working tree must be untouched: every file I committed should still
    # show as modified, because the OTHER lanes' hunks are still in it.
    print("\nfiles in the commit:")
    print(git("show", "--pretty=format:", "--name-only", commit).decode().strip())


if __name__ == "__main__":
    main()

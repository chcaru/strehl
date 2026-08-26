"""Census every copy of a source file on disk and fingerprint it.

Motivation
----------
ORCH has reported four times that `crates/strehl-cli/src/merge_cmd.rs` contains
no reference to the pyramid backend, and therefore that `strehl stack` still
ships the halo.  Three times the report traced to a stale pinned tree.  Asserting
"89 references at HEAD" a fourth time is not an argument -- it is the same
assertion that already failed to persuade, and it does not explain why a careful
agent reading a real file on disk keeps getting a different answer.

This script answers the useful question instead: *which* file are they reading?
ORCH supplied a fingerprint without meaning to --

    "The four `blend` matches are `support.blend()`, the edge-aware mask"

-- i.e. zero `pyramid`, a handful of `blend`, at least one `support.blend(`.
That is enough to identify a tree by content rather than by argument.

Output is sorted by pyramid count so the wired trees sink to the bottom and the
unwired ones rise to the top.  The live repository is marked.

Usage:  python treecensus.py [root] [filename]
"""

import os
import re
import subprocess
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev"
NAME = sys.argv[2] if len(sys.argv) > 2 else "merge_cmd.rs"
LIVE = os.path.normcase(
    r"C:\dev\blog\death-of-software\projects\strehl\crates\strehl-cli\src\merge_cmd.rs"
)


def head_of(path):
    """Best-effort `git rev-parse --short HEAD` for the tree containing path."""
    d = os.path.dirname(path)
    try:
        out = subprocess.run(
            ["git", "-C", d, "rev-parse", "--short", "HEAD"],
            capture_output=True, timeout=15,
        )
        if out.returncode == 0:
            return out.stdout.decode("utf-8", "replace").strip()
    except Exception:
        pass
    return "-"


def main():
    hits = []
    for dirpath, dirnames, filenames in os.walk(ROOT, onerror=lambda e: None):
        # do not descend into build output; it has no sources worth counting
        dirnames[:] = [d for d in dirnames if d not in (".git", "target", "node_modules")]
        if NAME in filenames:
            hits.append(os.path.join(dirpath, NAME))

    rows = []
    for p in hits:
        try:
            t = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        rows.append({
            "pyr": len(re.findall(r"pyramid", t, re.I)),
            "blend": len(re.findall(r"\bblend", t, re.I)),
            "sup": len(re.findall(r"support\.blend\(", t)),
            "path": p,
            "live": os.path.normcase(p) == LIVE,
        })

    rows.sort(key=lambda r: (r["pyr"], r["path"]))

    print(f"{len(rows)} copies of {NAME} under {ROOT}\n")
    print(f"{'pyramid':>7} {'blend':>6} {'sup':>4}  {'HEAD':<9} path")
    unwired = 0
    for r in rows:
        if r["pyr"] == 0:
            unwired += 1
        mark = "  <== THE LIVE REPOSITORY" if r["live"] else ""
        h = head_of(r["path"]) if (r["live"] or r["pyr"] == 0) else ""
        print(f"{r['pyr']:>7} {r['blend']:>6} {r['sup']:>4}  {h:<9} "
              f"{r['path'].replace(ROOT + os.sep, '')}{mark}")

    print(f"\nunwired copies (pyramid == 0) : {unwired} of {len(rows)}")
    live = [r for r in rows if r["live"]]
    if live:
        print(f"live repository pyramid count : {live[0]['pyr']}")
    else:
        print("live repository               : NOT FOUND under this root")

    # The fingerprint ORCH described, matched by content.
    match = [r for r in rows if r["pyr"] == 0 and r["sup"] >= 1]
    print(f"\ncopies matching ORCH's fingerprint (0 pyramid, has support.blend()): {len(match)}")
    for r in match[:12]:
        print("   ", r["path"].replace(ROOT + os.sep, ""))


if __name__ == "__main__":
    main()

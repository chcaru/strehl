"""Check that every OLD block in M100-exposure.md §4 applies to the repo.

The orchestrator applies §4 by hand. This asserts, mechanically, that each
`OLD:` code fence occurs EXACTLY ONCE in its target file at HEAD, and that the
corresponding `NEW:` block occurs exactly once in the verified tree that was
built and measured. A patch that cannot be located is a patch that will be
mis-applied.

Usage: python patchcheck.py [verified-tree-root]
Writes nothing but stdout.
"""
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", ".."))
TREE = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\strehl-out\M100\vt3"
DOC = os.path.join(REPO, "docs", "research", "M100-exposure.md")

# The §4 sub-sections and the file each one patches.
TARGETS = [
    ("### 4.1", os.path.join("crates", "strehl-cli", "src", "main.rs")),
    ("### 4.2", os.path.join("crates", "strehl-cli", "src", "merge_cmd.rs")),
]


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def main():
    doc = read(DOC)
    body = doc[doc.index("## 4. Verbatim patches"):]
    # Stop before the courtesy patch, which is for a file M100 did not verify.
    body = body[:body.index("### 4.3")]
    ok = fail = 0
    for i, (heading, rel) in enumerate(TARGETS):
        start = body.index(heading)
        end = body.index(TARGETS[i + 1][0]) if i + 1 < len(TARGETS) else len(body)
        section = body[start:end]
        old_src = read(os.path.join(REPO, rel))
        new_src = read(os.path.join(TREE, rel))
        print("=" * 78)
        print("%s  ->  %s" % (heading, rel))
        # Every fenced rust block, tagged by whichever of OLD/NEW appears last
        # before it. The markers are inside bold runs like
        # `**Hunk 1 -- the `Stack` doc comment. OLD:**`, so a plain
        # nearest-token search is more robust than matching the bold run.
        for m in re.finditer(r"```rust\n(.*?)```", section, re.S):
            block = m.group(1)
            before = section[:m.start()]
            io, inew = before.rfind("OLD"), before.rfind("NEW")
            if max(io, inew) < 0:
                continue
            kind = "OLD" if io > inew else "NEW"
            src, label = (old_src, "HEAD") if kind == "OLD" else (new_src,
                                                                 "verified")
            n = src.count(block)
            head = block.strip().splitlines()[0][:56]
            status = "ok" if n == 1 else "*** %d MATCHES ***" % n
            if n == 1:
                ok += 1
            else:
                fail += 1
            print("  %-4s in %-9s %-18s %s" % (kind, label, status, head))
    print()
    print("%d blocks located exactly once, %d not." % (ok, fail))
    raise SystemExit(1 if fail else 0)


if __name__ == "__main__":
    main()

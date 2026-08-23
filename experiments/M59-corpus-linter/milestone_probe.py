"""M59 pass 8: can milestone identity be checked mechanically?

M54 found that `M60` resolves to two unrelated milestones by two different
authors. The orchestrator's honest difficulty is real: a filename alone cannot
tell "one milestone, several parts" (M60, M60b, M60c) from "two milestones, one
number" (M60-robustness... and M60-prior-art...).

This measures whether a machine-visible signature exists anyway, by census:
  - group every docs/research report file by milestone number
  - within a number, separate BARE (`M60-`) from SUFFIXED (`M60b-`) forms
  - the hypothesis under test: a collision shows up as TWO OR MORE BARE files
    sharing a number, because a multi-part milestone uses suffixes for its
    continuations and only ever has one bare part.

If the hypothesis holds corpus-wide with no false positives, the check is cheap
and needs no new convention. If it does not, this prints the counter-examples,
which is the argument for a declared owner instead.

Read-only. Run: python experiments/M59-corpus-linter/milestone_probe.py
"""
import io
import os
import re
import subprocess
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RESEARCH = os.path.join(ROOT, "docs", "research")

# M60-slug.md / M60c-slug.md / m53-slug.md ; also M20-VERIFICATION.md
NAME = re.compile(r"^(?P<pre>[Mm])(?P<num>\d+)(?P<suf>[a-z]*)-(?P<slug>.+)\.md$")


def git(args):
    p = subprocess.run(["git"] + args, cwd=ROOT, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    return p.stdout.decode("utf-8", "replace") if p.returncode == 0 else ""


def main():
    by_num = defaultdict(list)
    unparsed = []
    for name in sorted(os.listdir(RESEARCH)):
        if not name.endswith(".md"):
            continue
        m = NAME.match(name)
        if not m:
            unparsed.append(name)
            continue
        by_num[int(m.group("num"))].append(
            (m.group("suf"), name, m.group("slug")))

    print("report files parsed: %d ; not milestone-shaped: %d %s"
          % (sum(len(v) for v in by_num.values()), len(unparsed),
             unparsed[:6]))
    print("")

    print("A  milestone numbers with more than one file")
    multi = {n: v for n, v in by_num.items() if len(v) > 1}
    print("   %d of %d numbers have several files" % (len(multi), len(by_num)))
    print("")
    print("   %-5s %-6s %s" % ("num", "bare", "files"))
    collisions = []
    for num in sorted(multi):
        parts = multi[num]
        bare = [p for p in parts if p[0] == ""]
        flag = "  <-- TWO BARE" if len(bare) > 1 else ""
        if len(bare) > 1:
            collisions.append((num, parts))
        print("   %-5d %-6d %s%s" % (num, len(bare),
                                     ", ".join(p[1] for p in parts), flag))

    print("")
    print("B  the hypothesis: >1 bare file for a number == a collision")
    print("   numbers flagged: %d" % len(collisions))
    for num, parts in collisions:
        print("   M%d:" % num)
        for suf, name, slug in sorted(parts):
            first = git(["log", "--diff-filter=A", "--format=%h %an %ad",
                         "--date=short", "-1", "--", "docs/research/" + name])
            print("      %-56s %s" % (name, first.strip() or "(uncommitted)"))

    print("")
    print("C  does any single-bare number look like a collision anyway?")
    print("   (a multi-part milestone should share a topic; different topics")
    print("    under one number are the defect, suffix or not)")
    for num in sorted(multi):
        parts = multi[num]
        if len([p for p in parts if p[0] == ""]) > 1:
            continue
        slugs = [p[2] for p in parts]
        heads = set()
        for slug in slugs:
            heads.add(slug.split("-")[0].lower())
        if len(heads) == len(slugs) and len(slugs) > 1:
            print("      M%-4d all slugs start differently: %s"
                  % (num, ", ".join(slugs)))


if __name__ == "__main__":
    main()

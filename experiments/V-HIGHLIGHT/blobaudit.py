"""Apply ORCH's containment test to the ONE dangling blob their census omitted.

Their audit itemised 3 commitmsg + 2 buildlog + 5 substantive = 10, but fsck
reports 11.  d4f2395d56 was never examined.  Their verdict "nobody lost work"
therefore does not cover it.  Test it the way they tested the other five:
count lines present ONLY in the blob.  A magnitude, not a boolean.
"""
import subprocess, sys

def run(args):
    p = subprocess.run(args, capture_output=True, text=True, errors="replace")
    if p.returncode != 0:
        raise SystemExit("git failed: %s\n%s" % (args, p.stderr[:300]))
    return p.stdout.splitlines()

BLOB = "d4f2395d56"
PATH = "experiments/m16-orientation-fpn/data/run-log-c.txt"

blob = run(["git", "cat-file", "-p", BLOB])
head = run(["git", "show", "HEAD:" + PATH])
try:
    work = open(PATH, encoding="utf-8", errors="replace").read().splitlines()
except OSError:
    work = None

def contain(a, b, la, lb):
    sa, sb = set(x.rstrip() for x in a), set(x.rstrip() for x in b)
    only = sorted(sa - sb)
    print("  %-28s blob=%d %s=%d  only-in-blob=%d"
          % (la + " vs " + lb, len(a), lb, len(b), len(only)))
    return only

print("blob %s -> %s" % (BLOB, PATH))
o_head = contain(blob, head, "blob", "HEAD")
if work is not None:
    o_work = contain(blob, work, "blob", "worktree")
print()

if not o_head:
    print("RESULT: only-in-blob = 0 against HEAD.  Every line of this blob still")
    print("exists in the tracked file.  No work is lost here either -- ORCH's")
    print("verdict happens to hold for the blob they did not examine.")
else:
    print("RESULT: %d line(s) exist ONLY in the dangling blob:" % len(o_head))
    for l in o_head[:25]:
        print("   | %s" % l[:110])
    if len(o_head) > 25:
        print("   ... and %d more" % (len(o_head) - 25))
    print()
    print("These are recoverable ONLY while gc.auto=0 holds:")
    print("   git cat-file -p %s > <path>" % BLOB)

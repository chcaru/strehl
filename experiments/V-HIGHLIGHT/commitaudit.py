"""ORCH's census covered dangling BLOBS.  fsck also reports one dangling COMMIT
that is NOT an ancestor of HEAD.  Their "nobody lost work" conclusion never
examined it.  Apply the same containment test, per file, as a magnitude.
"""
import subprocess

C = "6a1cdb6490cfe1c3bf7e29e1fec33d8e3b65e10e"

def run(args, ok_fail=False):
    p = subprocess.run(args, capture_output=True, text=True, errors="replace")
    if p.returncode != 0:
        if ok_fail:
            return None
        raise SystemExit("git failed: %s\n%s" % (args, p.stderr[:300]))
    return p.stdout.splitlines()

files = run(["git", "show", "--name-only", "--format=", C])
files = [f for f in files if f.strip()]
print("dangling commit %s carries %d file(s)\n" % (C[:10], len(files)))

total_lost = 0
for f in files:
    src = run(["git", "show", "%s:%s" % (C, f)])
    head = run(["git", "show", "HEAD:%s" % f], ok_fail=True)
    if head is None:
        print("  %-44s ABSENT FROM HEAD -- all %d lines orphaned" % (f, len(src)))
        total_lost += len(src)
        continue
    only = sorted(set(x.rstrip() for x in src) - set(x.rstrip() for x in head))
    print("  %-44s commit=%-4d HEAD=%-4d only-in-commit=%d"
          % (f, len(src), len(head), len(only)))
    total_lost += len(only)
    for l in only[:8]:
        print("        | %s" % l[:100])

print()
if total_lost == 0:
    print("RESULT: every line of the dangling commit is present in HEAD.")
    print("The work was re-landed by another route; nothing is lost.")
else:
    print("RESULT: %d line(s) exist ONLY in the unreachable commit." % total_lost)
    print("Recoverable while gc.auto=0:  git cherry-pick %s" % C[:10])

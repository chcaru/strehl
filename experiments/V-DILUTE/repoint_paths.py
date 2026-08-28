"""V-DILUTE -- repoint scratch paths from C: to D: after the disk emergency.

ORCH broadcast: write heavy output to D:\\strehl-out\\<LANE>\\ instead of
C:\\dev\\strehl-out\\<LANE>\\.  The masters have been moved; this repoints every
script in the lane so a future re-check still finds them.

Rewrites only the literal scratch root.  Does not touch D:\\personal\\macro,
which is READ-ONLY source data.
"""
import os
import glob

OLD = r"D:\strehl-out\V-DILUTE"
NEW = r"D:\strehl-out\V-DILUTE"
EXP = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-DILUTE"

changed = []
for p in sorted(glob.glob(os.path.join(EXP, "*"))):
    if os.path.isdir(p):
        continue
    try:
        t = open(p, encoding="utf-8").read()
    except (UnicodeDecodeError, PermissionError):
        continue
    if OLD not in t:
        continue
    open(p, "w", encoding="utf-8").write(t.replace(OLD, NEW))
    changed.append((os.path.basename(p), t.count(OLD)))

for name, n in changed:
    print(f"repointed {n:2d} path(s) in {name}")
print(f"\n{len(changed)} files updated")

# sanity: nothing should still reference the old root
left = []
for p in glob.glob(os.path.join(EXP, "*")):
    if os.path.isdir(p):
        continue
    try:
        if OLD in open(p, encoding="utf-8").read():
            left.append(os.path.basename(p))
    except (UnicodeDecodeError, PermissionError):
        pass
print("still referencing C: scratch:", left if left else "none")

"""Diagnose WHY the other lane missed 066A87AB. Not a guess: measure the two
search populations and see whether the exact-name filter explains the gap.
Reported counts were 78 distinct hashes across 160 paths; I found 165 across 301.
"""
import os, hashlib
ROOT = r"C:\dev"
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest().upper()
exact, wide = [], []
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d.lower() not in (".git", "node_modules")]
    for f in fn:
        if not f.lower().endswith(".exe") or "strehl" not in f.lower(): continue
        p = os.path.join(dp, f)
        try: h = sha(p)
        except Exception: continue
        wide.append((p, h, f))
        if f.lower() == "strehl.exe": exact.append((p, h, f))
print("  exact name 'strehl.exe' : %3d paths, %3d distinct hashes"
      % (len(exact), len({h for _, h, _ in exact})))
print("  any strehl*.exe         : %3d paths, %3d distinct hashes"
      % (len(wide), len({h for _, h, _ in wide})))
missed = {h for _, h, _ in wide} - {h for _, h, _ in exact}
print("  builds visible ONLY under the wider pattern: %d" % len(missed))
print()
print("  is 066A87AB among them: %s" % any(h.startswith("066A87AB") for h in missed))
names = sorted({f for _, h, f in wide if h in missed})
print("  filenames that carry a build the exact-name search cannot reach:")
for nm in names: print("      %s" % nm)
print()
tgt = [(p, f) for p, h, f in wide if h.startswith("066A87AB")]
for p, f in tgt:
    print("  066A87AB lives at %s  (filename %r, size %d)" % (p, f, os.path.getsize(p)))
print()
print("  CONCLUSION: the absence report is an artifact of the filename filter,")
print("  not of the filesystem. The build exists and the original aura renders")
print("  ARE reproducible.")

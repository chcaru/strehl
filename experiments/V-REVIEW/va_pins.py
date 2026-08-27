"""Independently re-audit ORCH's three binary claims, and prove every render I
made tonight is sealed to the pin the corpus names.

Claims under test:
  1. 066A87AB...0437B is NOT FOUND anywhere under C:\\dev
  2. C:\\dev\\strehl-out\\PIN-V3\\strehl.exe hashes B50EABC1...7C99 and matches
     no seal in any acceptance corpus, at size 9,568,768
  3. acceptance-pins holds five pins; only two are sealed by any corpus
"""
import os, hashlib, json

ROOT = r"C:\dev"
TARGET = "066A87AB"
PINV3 = r"C:\dev\strehl-out\PIN-V3\strehl.exe"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest().upper()


print("=" * 78)
print("collecting every strehl.exe under C:\\dev")
print("=" * 78)
found = []
for dp, dn, fn in os.walk(ROOT):
    dn[:] = [d for d in dn if d.lower() not in (".git", "node_modules")]
    for f in fn:
        if f.lower().endswith(".exe") and "strehl" in f.lower():
            p = os.path.join(dp, f)
            try:
                found.append((p, sha(p), os.path.getsize(p)))
            except Exception as e:
                print("  unreadable:", p, e)
print("  %d strehl*.exe paths, %d distinct hashes"
      % (len(found), len({h for _, h, _ in found})))

print()
print("=" * 78)
print("CLAIM 1  066A87AB...0437B is NOT FOUND under C:\\dev")
print("=" * 78)
hits = [(p, h, s) for p, h, s in found if h.startswith(TARGET)]
if hits:
    print("  *** REFUTED *** the build IS present, at %d path(s):" % len(hits))
    for p, h, s in hits:
        print("      %s" % p)
        print("      %s  %d bytes" % (h, s))
else:
    print("  CONFIRMED: no strehl*.exe under C:\\dev hashes to %s" % TARGET)
    print("  -> my aura/geom/halo2 renders are not reproducible. The scope")
    print("     caveat is correct and the refusal to backfill their seals was")
    print("     the only thing that kept them from carrying a false provenance.")

print()
print("=" * 78)
print("CLAIM 2  PIN-V3\\strehl.exe is named for a pin it is not")
print("=" * 78)
if os.path.exists(PINV3):
    h = sha(PINV3); s = os.path.getsize(PINV3)
    print("  path   %s" % PINV3)
    print("  sha256 %s" % h)
    print("  size   %d bytes" % s)
    print("  starts B50EABC1: %s" % h.startswith("B50EABC1"))
else:
    print("  NOT PRESENT at that path")
    h = None

print()
print("=" * 78)
print("CLAIM 3  acceptance-pins: how many are sealed by a corpus?")
print("=" * 78)
seals = {}
accroot = r"C:\dev\strehl-out\acceptance"
if os.path.isdir(accroot):
    for corpus in sorted(os.listdir(accroot)):
        d = os.path.join(accroot, corpus)
        if not os.path.isdir(d): continue
        vals = set()
        for f in os.listdir(d):
            if f.endswith(".tiff.ok"):
                vals.add(open(os.path.join(d, f)).read().strip().upper())
        if vals:
            seals[corpus] = vals
            print("  corpus %-12s %d sealed masters, %d distinct seal(s): %s"
                  % (corpus, len([f for f in os.listdir(d) if f.endswith('.tiff.ok')]),
                     len(vals), ", ".join(v[:8] for v in vals)))
allseals = set().union(*seals.values()) if seals else set()

print()
pinroot = r"C:\dev\strehl-out\acceptance-pins"
rows = []
for pin in sorted(os.listdir(pinroot)):
    exe = os.path.join(pinroot, pin, "target", "release", "strehl.exe")
    if not os.path.exists(exe):
        print("  %-12s NO strehl.exe" % pin); continue
    hh = sha(exe)
    named = [c for c, v in seals.items() if hh in v]
    rows.append((pin, hh, os.path.getsize(exe), named))
    print("  %-12s %s  %9d  %s" % (pin, hh[:16], os.path.getsize(exe),
          ("SEALED BY " + ",".join(named)) if named else "*** NOT SEALED BY ANY CORPUS ***"))
sealed = [r for r in rows if r[3]]
print()
print("  partition: %d sealed + %d unsealed = %d pins present"
      % (len(sealed), len(rows) - len(sealed), len(rows)))

print()
print("=" * 78)
print("SIZE COLLISION  how many distinct builds share 9,568,768 bytes?")
print("=" * 78)
bysize = {}
for p, hh, s in found:
    bysize.setdefault(s, set()).add(hh)
n = len(bysize.get(9568768, set()))
print("  distinct hashes at that exact size: %d" % n)
for hh in sorted(bysize.get(9568768, set())):
    who = [c for c, v in seals.items() if hh in v]
    print("    %s  %s" % (hh[:16], ("seals " + ",".join(who)) if who else "unsealed"))

print()
print("=" * 78)
print("MY RENDERS TONIGHT  every artifact must carry a seal naming the pin")
print("=" * 78)
want = sorted(allseals & {v for c, vs in seals.items() if c == "SHIP-V4" for v in vs}) if seals else []
shipv4 = sorted(seals.get("SHIP-V4", set()))
ok = bad = 0
for base in (r"C:\dev\strehl-out\V-REVIEW\aura-ship",):
    for f in sorted(os.listdir(base)):
        if not f.endswith(".tiff"): continue
        p = os.path.join(base, f)
        okf, prv = p + ".ok", p + ".provenance.txt"
        has = os.path.exists(okf) and os.path.exists(prv)
        val = open(okf).read().strip().upper() if os.path.exists(okf) else None
        good = has and shipv4 and val == shipv4[0]
        ok, bad = ok + int(good), bad + int(not good)
        print("  %-46s seal=%s prov=%s matches-SHIP-V4-pin=%s"
              % (f, os.path.exists(okf), os.path.exists(prv),
                 (val == shipv4[0]) if val and shipv4 else False))
print()
print("  partition: %d sealed-and-correct + %d not = %d artifacts" % (ok, bad, ok + bad))
for d in (r"C:\dev\strehl-out\V-REVIEW\geom", r"C:\dev\strehl-out\V-REVIEW\halo2"):
    if os.path.isdir(d):
        t = [f for f in os.listdir(d) if f.endswith(".tiff")]
        k = [f for f in os.listdir(d) if f.endswith(".ok")]
        print("  %-40s %d tiff, %d seals (deliberately NOT backfilled)" % (d, len(t), len(k)))

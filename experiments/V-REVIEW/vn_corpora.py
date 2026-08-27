"""Are the two shipping corpora the same pixels? All 26 subjects."""
import hashlib, os
V3D = r"C:\dev\strehl-out\acceptance\SHIP-V3"
V4D = r"C:\dev\strehl-out\acceptance\SHIP-V4"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""): h.update(b)
    return h.hexdigest().upper()


subs = sorted(n[:-len("--SHIP-V3.tiff")] for n in os.listdir(V3D)
              if n.endswith("--SHIP-V3.tiff"))
same = diff = missing = 0
for s in subs:
    a = os.path.join(V3D, "%s--SHIP-V3.tiff" % s)
    b = os.path.join(V4D, "%s--SHIP-V4.tiff" % s)
    if not os.path.isfile(b):
        print("  %-26s MISSING in V4" % s); missing += 1; continue
    ha, hb = sha(a), sha(b)
    if ha == hb:
        same += 1
    else:
        diff += 1
        print("  %-26s DIFFERS  V3 %s  V4 %s" % (s, ha[:16], hb[:16]))
print()
print("  identical %d   differing %d   missing %d   = %d subjects"
      % (same, diff, missing, same + diff + missing))
print()
sa = sha(os.path.join(V3D, "%s--SHIP-V3.tiff.ok" % subs[0]))
print("  seals: V3 %s" % open(os.path.join(V3D, "%s--SHIP-V3.tiff.ok" % subs[0])).read().strip()[:24])
print("         V4 %s" % open(os.path.join(V4D, "%s--SHIP-V4.tiff.ok" % subs[0])).read().strip()[:24])
print()
print("  If the pixels are identical while the seals name different binaries,")
print("  the two corpora are one set of images rendered by two builds that")
print("  agree on this path -- not two generations of output.")

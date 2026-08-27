r"""Two corpora sealed by two different binaries contain byte-identical images.
There are two explanations and they are not equally benign:

  A. The builds genuinely produce identical output on these subjects, and V4 was
     re-rendered. Then the seals are honest and no lane's numbers are on a
     different gauge.
  B. SHIP-V4 was COPIED from SHIP-V3 and re-sealed. Then the .ok files assert a
     provenance the bytes never had, the seals are the mislabelled-artifact
     failure at corpus scale, and it is far worse than one stray exe.

Discriminate on evidence that a copy cannot fake cheaply: write times, and the
per-file provenance the harness emits alongside each master.
"""
import datetime
import os

V3D = r"C:\dev\strehl-out\acceptance\SHIP-V3"
V4D = r"C:\dev\strehl-out\acceptance\SHIP-V4"


def ts(p):
    return datetime.datetime.fromtimestamp(os.path.getmtime(p))


subs = sorted(f[:-len("--SHIP-V3.tiff")] for f in os.listdir(V3D) if f.endswith(".tiff"))
print("%-28s %-21s %-21s %s" % ("subject", "SHIP-V3 mtime", "SHIP-V4 mtime", "same?"))
print("-" * 82)
same = 0
for s in subs[:6]:
    p3 = os.path.join(V3D, "%s--SHIP-V3.tiff" % s)
    p4 = os.path.join(V4D, "%s--SHIP-V4.tiff" % s)
    if not os.path.exists(p4):
        continue
    eq = abs(os.path.getmtime(p3) - os.path.getmtime(p4)) < 2
    same += eq
    print("%-28s %-21s %-21s %s" % (s, ts(p3).strftime("%Y-%m-%d %H:%M:%S"),
                                    ts(p4).strftime("%Y-%m-%d %H:%M:%S"),
                                    "COPY-LIKE" if eq else "distinct"))

print("\nPROVENANCE DIFF -- first subject, the harness's own record.")
s = subs[0]
for tag, d in (("SHIP-V3", V3D), ("SHIP-V4", V4D)):
    p = os.path.join(d, "%s--%s.tiff.provenance.txt" % (s, tag))
    if not os.path.exists(p):
        print("  %s: no provenance file" % tag)
        continue
    lines = [l.rstrip() for l in open(p, encoding="utf-8", errors="replace")]
    keep = [l for l in lines
            if any(k in l.lower() for k in
                   ("binary", "sha", "commit", "git", "built", "date", "time", "exe"))]
    print("  == %s (%d lines) ==" % (tag, len(lines)))
    for l in keep[:10]:
        print("     %s" % l[:150])

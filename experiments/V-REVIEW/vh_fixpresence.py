import io, sys
P = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-REVIEW\vh_verify.py"
t = io.open(P, encoding="utf-8").read()
old = """for s, n in (("18845", "leaf-2 azimuthal spread"), ("1600 DN", "narrow detection floor"),
             ("1.26x", "best trend separation"), ("3200 DN", "planted rim that read monotone"),
             ("7745", "max-of-noise defect on a clean subject")):
    ck(s in rs, "residual report dropped %s (%s)" % (s, n))
"""
if t.count(old) != 1:
    sys.exit("ANCHOR NOT FOUND (%d) -- refusing to patch" % t.count(old))
new = """# PRESENCE TESTS ARE SATISFIED BY DUPLICATES. Commissioning caught this:
# deleting the 1600 DN floor from the bee-1 row read GREEN because "1600 DN"
# also appears in the bee-2 row and in prose. Each number is now pinned to its
# own canonical site, so a deletion at that site cannot be masked elsewhere.
for anchor, n in (
    ("| **leaf-2-cpl** | **+5721** | **44%** (7/16) | **18845 DN** | walk artifact |",
     "leaf-2 azimuthal spread row"),
    ("| bee-1-cpl | **1600 DN** | 400 DN | 1 of 4 (at 3000 DN) |",
     "bee-1 detection floor row"),
    ("| bee-2-cpl | **1600 DN** | 1600 DN* | 0 of 4 |",
     "bee-2 detection floor row"),
    ("| 4 | 2613 DN | 1323 | 3305 | 0.51x / **1.26x** |",
     "best trend separation row"),
    ("read \\"profile is monotone; no local rim\\"", "the 3200 DN monotone refutation"),
    ("**HALO 7745 DN on known-clean `bee-1-cpl`**", "max-of-noise defect"),
):
    ck(norm(anchor) in rs, "residual report dropped or altered: %s" % n)
"""
io.open(P, "w", newline="\n", encoding="utf-8").write(t.replace(old, new, 1))
print("pinned 6 numeric claims to unique canonical anchors")

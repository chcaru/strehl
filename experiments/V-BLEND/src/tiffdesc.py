import sys, difflib
import tifffile

descs = {}
for p in sys.argv[1:]:
    with tifffile.TiffFile(p) as tf:
        d = {t.name: t.value for t in tf.pages[0].tags.values()}.get("ImageDescription", "")
    descs[p] = d
    print("=" * 70)
    print(p)
    print("=" * 70)
    print(d)
    print()

if len(descs) == 2:
    a, b = list(descs.values())
    print("=" * 70)
    print("DIFF between the two ImageDescriptions")
    print("=" * 70)
    diff = [l for l in difflib.unified_diff(a.splitlines(), b.splitlines(), "before", "after", lineterm="", n=0)]
    print("\n".join(diff) if diff else "IDENTICAL -- byte-for-byte the same description")

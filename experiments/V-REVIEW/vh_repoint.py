"""Repoint my verifier scripts at the banked in-repo inputs.

vh_verify.py, vh_flipcommission.py and vh_union.py all read their inputs from
D:\strehl-out\V-REVIEW\halo, which is scratch. Deleting scratch would leave a
committed verifier that cannot run -- the same failure that made V-RIM's 5-of-14
permanently unreproducible. The inputs are 156 KB of JSON/TXT and are now banked
byte-identical under experiments/V-REVIEW/halo-data/.

Anchored on full unique lines; hard error if any anchor does not land.
"""
import io, os, sys

RESOLVER = (
    'import os as _os\n'
    '_HERE = _os.path.dirname(_os.path.abspath(__file__))\n'
    '_REPO = _os.path.join(_HERE, "halo-data")\n'
    '_SCRATCH = r"D:\\strehl-out\\V-REVIEW\\halo"\n'
    '# prefer the banked in-repo inputs; fall back to scratch if it still exists\n'
    'D = _REPO if _os.path.isdir(_REPO) else _SCRATCH\n'
)

EDITS = [
    ("vh_verify.py", [
        ('D = r"D:\\strehl-out\\V-REVIEW\\halo"', RESOLVER.rstrip("\n")),
    ]),
    ("vh_flipcommission.py", [
        ('BJ = r"D:\\strehl-out\\V-REVIEW\\halo\\blind.json"',
         RESOLVER + 'BJ = _os.path.join(D, "blind.json")'),
        ('TJ = r"D:\\strehl-out\\V-REVIEW\\halo\\trunc2.json"',
         'TJ = _os.path.join(D, "trunc2.json")'),
    ]),
    ("vh_union.py", [
        ('tr = json.load(open(r"D:\\strehl-out\\V-REVIEW\\halo\\trunc2.json"))',
         RESOLVER + 'tr = json.load(open(_os.path.join(D, "trunc2.json")))'),
        ('h3 = json.load(open(r"D:\\strehl-out\\V-REVIEW\\halo\\halo3.json"))',
         'h3 = json.load(open(_os.path.join(D, "halo3.json")))'),
    ]),
]

fail = 0
for fn, subs in EDITS:
    src = io.open(fn, encoding="utf-8").read()
    for old, new in subs:
        n = src.count(old)
        if n != 1:
            print("ANCHOR NOT UNIQUE in %s: %d occurrences of %r" % (fn, n, old[:60]))
            fail += 1
            continue
        src = src.replace(old, new, 1)
    io.open(fn, "w", newline="\n", encoding="utf-8").write(src)
    print("patched %s" % fn)

if fail:
    print("\n*** %d anchors failed -- NOT safe ***" % fail)
    sys.exit(1)
print("\nall anchors landed")

"""Commission the finalpass harness on its own output.

A harness that writes the right filenames is not thereby writing right images.
Three things are checked, and the third is the one that matters:

  1. Every TIFF is uint16 HxWx3 -- accept.py asserts exactly this and a harness
     that emits something else wastes the pass rather than failing it.
  2. Every rendered subject has its `.ok` sentinel, and the sentinel carries the
     binary hash, so a resumed pass can tell "already rendered by THIS binary"
     from "left over from a different one".
  3. THE TWO SUBJECTS DIFFER. Both files came out at exactly 189 MB, which is
     what an uncompressed TIFF of fixed dimensions does -- and it is also what a
     harness that renders the same subject twice does. Identical size is not
     evidence of distinct content, so it is measured instead of assumed.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile

d = Path(sys.argv[1])
tiffs = sorted(d.glob("*--*.tiff"))
assert tiffs, f"no arm TIFFs under {d}"

imgs = {}
for t in tiffs:
    a = tifffile.imread(t)
    assert a.dtype == np.uint16, f"{t.name}: dtype {a.dtype}, accept.py requires uint16"
    assert a.ndim == 3 and a.shape[2] == 3, f"{t.name}: shape {a.shape}, want HxWx3"
    ok = t.with_suffix(t.suffix + ".ok")
    assert ok.exists(), f"{t.name}: no .ok sentinel -- a resumed pass would re-render it"
    imgs[t.name] = a
    print(f"  {t.name:44s} {a.shape} {a.dtype}  ok={ok.read_text().strip()[:16]}")

names = list(imgs)
print()
if len(names) < 2:
    print("only one subject -- discrimination check skipped")
    sys.exit(0)

# The discrimination arm. If this passes trivially the harness is filing one
# render under several names, and every downstream table would be self-comparison.
distinct = 0
for i in range(len(names)):
    for j in range(i + 1, len(names)):
        a, b = imgs[names[i]], imgs[names[j]]
        same = a.shape == b.shape and np.array_equal(a, b)
        print(f"  {names[i]} vs {names[j]}: {'IDENTICAL -- FAIL' if same else 'differ'}")
        assert not same, "two subjects rendered byte-identical images"
        distinct += 1

print(f"\nPASS: {len(names)} subjects, all uint16 HxWx3, {distinct} pair(s) verified distinct")

"""Settle V-M111's claim by execution: does STREHL_FIX_HALO change any number
strehl prints, and does it change the image?

The two questions are separate and the answers are opposite. Run against a stack
deep enough that `|k - k_F| >= delta` is satisfiable -- on a stack no deeper than
`delta` the correction is a guaranteed no-op and the test is degenerate.

Reads the 16-bit TIFF with tifffile. PIL narrows strehl's output to 8 bits
(corpus fact P40) and would report a real change as nearly nothing.
"""

import hashlib
import pathlib
import re
import sys

import numpy as np
import tifffile

O = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\strehl-out\HALOORD")
STEM = sys.argv[2] if len(sys.argv) > 2 else "fb"

# Lines that legitimately differ between any two runs, plus the correction's own
# reporting. Anything left is a STATISTIC, and a statistic moving is the thing
# the claim says cannot happen.
NOISE = re.compile(
    r"wall clock|decode|focus \+ reg|field \+ gate|summed across|ms/frame|s/frame"
    r"|MB/s|MB/worker|throughput|elapsed|wrote |halo fix|pass three|treated|re-elected"
    r"|NOT a fidelity|in-flight|peak, bound"
)


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()[:16]


def stats_only(p: pathlib.Path) -> list[str]:
    return [
        ln.strip()
        for ln in p.read_text(encoding="utf-8", errors="replace").splitlines()
        if ln.strip() and not NOISE.search(ln)
    ]


a_tif, b_tif = O / f"{STEM}A.tif", O / f"{STEM}B.tif"
a_log, b_log = O / f"{STEM}A.log", O / f"{STEM}B.log"

print(f"=== {STEM}: STREHL_FIX_HALO off (A) vs on (B) ===\n")

print(f"A.tif sha {sha(a_tif)}")
print(f"B.tif sha {sha(b_tif)}")
same_bytes = sha(a_tif) == sha(b_tif)
print(f"output identical: {same_bytes}\n")

a = tifffile.imread(a_tif).astype(np.int32)
b = tifffile.imread(b_tif).astype(np.int32)
assert a.shape == b.shape, f"shape mismatch {a.shape} vs {b.shape}"
d = b - a
changed = int(np.count_nonzero(d))
print(f"pixels changed : {changed:,} of {d.size:,} ({100.0 * changed / d.size:.3f}%)")
print(f"max |delta|    : {int(np.abs(d).max()):,} DN of 65535")
print(f"mean |delta|   : {float(np.abs(d).mean()):.2f} DN\n")

sa, sb = stats_only(a_log), stats_only(b_log)
only_a = [x for x in sa if x not in sb]
only_b = [x for x in sb if x not in sa]
print(f"reported statistics differing: {len(only_a) + len(only_b)}")
for ln in (only_a + only_b)[:10]:
    print(f"   {ln[:110]}")

print()
image_moved = changed > 0
stats_moved = bool(only_a or only_b)
if image_moved and not stats_moved:
    print("VERDICT: CONFIRMED. The correction changes the image and moves ZERO")
    print("reported statistics. An A/B on strehl's printed numbers is null by")
    print("construction. Re-read the output TIFF.")
elif not image_moved:
    print("VERDICT: DEGENERATE -- the correction did not change the image, so this")
    print("run cannot speak to the ordering. Use a stack deeper than delta.")
else:
    print("VERDICT: REFUTED -- a reported statistic moved with the correction.")

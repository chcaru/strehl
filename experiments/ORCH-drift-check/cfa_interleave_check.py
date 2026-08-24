"""Does argmax-baseline's new demosaic branch use the same CFA interleave as the merge path?

The branch added for M104c-P6 hard-codes an RGGB layout. If it were transposed
(R and B swapped, or the two greens crossed) the render would still be the right
SIZE -- which is all the P2 check tested -- but the colours would be wrong, and
nothing in the dimension check could see it.

Both TIFFs are the same stack, same --limit, same --srgb. The two subcommands run
DIFFERENT algorithms (argmax selection vs gated estimation), so they must NOT be
byte-identical. But they are looking at the same photons, so their per-channel
means must agree closely. A swapped R/B interleave would show up as the R and B
means trading places -- on a coffee bean, which is strongly red-dominant, that is
a large and unmistakable signal.

Pre-registered, before the run:
  PASS  each channel mean within 10% relative, AND R>G>B ordering preserved in both
  FAIL  R and B means trade rank between the two renders  -> interleave transposed
  FAIL  any channel differs by >10%                       -> interleave suspect
"""

import sys

import numpy as np
import tifffile

BASELINE, MERGE = sys.argv[1], sys.argv[2]

a = tifffile.imread(BASELINE).astype(np.float64)
m = tifffile.imread(MERGE).astype(np.float64)

print(f"argmax-baseline --srgb : {a.shape} {a.dtype}")
print(f"stack --srgb           : {m.shape} {m.dtype}")

if a.shape != m.shape:
    print(f"FAIL -- shapes differ, cannot compare: {a.shape} vs {m.shape}")
    sys.exit(1)

if np.array_equal(a, m):
    print("FAIL -- renders are byte-identical; these are different algorithms,")
    print("        so identity means one of them is not running.")
    sys.exit(1)

names = ["R", "G", "B"]
am = [a[:, :, c].mean() for c in range(3)]
mm = [m[:, :, c].mean() for c in range(3)]

print()
print(f"{'ch':<4}{'baseline':>14}{'merge':>14}{'rel diff':>12}")
worst = 0.0
for c in range(3):
    rel = abs(am[c] - mm[c]) / max(mm[c], 1e-9)
    worst = max(worst, rel)
    print(f"{names[c]:<4}{am[c]:>14.1f}{mm[c]:>14.1f}{rel:>11.2%}")

ra = [names[i] for i in np.argsort(am)[::-1]]
rm = [names[i] for i in np.argsort(mm)[::-1]]
print()
print(f"channel rank, baseline : {' > '.join(ra)}")
print(f"channel rank, merge    : {' > '.join(rm)}")

ok_rank = ra == rm
ok_mag = worst <= 0.10

print()
if ok_rank and ok_mag:
    print(f"PASS -- interleave agrees. worst channel diff {worst:.2%}, rank preserved.")
elif not ok_rank:
    print(f"FAIL -- channel rank differs ({' > '.join(ra)} vs {' > '.join(rm)}).")
    print("        This is the signature of a transposed CFA interleave.")
    sys.exit(1)
else:
    print(f"FAIL -- worst channel diff {worst:.2%} exceeds the 10% bar.")
    sys.exit(1)

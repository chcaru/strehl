"""Which section 6.5 negative-control anchors did section 7 make non-unique?

The checker hard-errors on the FIRST collision, so fixing them one run at a
time costs one full pass each. This reports all of them at once.
"""
import io
import os
import sys

D = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, D)
import vn_negctl65 as N  # noqa: E402

t = io.open(os.path.join(D, "RESULT.md"), encoding="utf-8").read()
bad = 0
for item in list(N.PLANTS) + [N.PLACEBO]:
    label, old = item[0], item[1]
    n = t.count(old)
    if n != 1:
        bad += 1
        print("  %-28s %d occurrences  %r" % (label, n, old))
print("")
print("%d of %d anchors are not unique" % (bad, len(N.PLANTS) + 1))
sys.exit(1 if bad else 0)

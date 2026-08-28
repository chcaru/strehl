"""Confidence-map potency expressed in ORCH's units: % of samples MOVED.

ORCH's commissioning demand is that a known-potent arm be run on the confidence
map AT EACH FRAME COUNT, so that "flat in N" cannot be confused with "not
reading". That is A-KILL-2 in my pre-registration and it was run at every N --
but I reported it as MEANS (409.8 / 463.3 / 811.8), which is not comparable to
ORCH's percent-moved figures (gate 8.0 -> 16.27%, bands 3 -> 9.66%).

This restates the same brackets as fraction of reached samples that differ, so
the instrument's sensitivity at N=299 can be compared against its sensitivity at
N=22 directly, and against V-REVIEW's arms.

65535 marks an unreached pixel and is excluded; comparisons use the intersection
of the two arms' reached masks.
"""
import sys
import numpy as np
import tifffile

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-DILUTE")
import vd_metrics as vd

R = r"C:\dev\strehl-out\V-DILUTE\runs"
UNREACHED = 65535


def load(tag):
    a = tifffile.imread(rf"{R}\{tag}_conf.tif")
    return a, (a != UNREACHED)


def moved(a_tag, b_tag):
    a, ma = load(a_tag)
    b, mb = load(b_tag)
    m = ma & mb
    d = (a[m].astype(np.int32) != b[m].astype(np.int32))
    delta = np.abs(a[m].astype(np.int32) - b[m].astype(np.int32))
    return 100.0 * d.mean(), int(delta.max()), float(delta.mean()), int(m.sum())


print("CONFIDENCE-MAP POTENCY AT EACH FRAME COUNT (ORCH units: % of reached samples moved)")
print("bee-3-cpl, full focus range at every N, pin 9b05d0b7\n")
print(f"{'N':>5}  {'arm pair':<34} {'% moved':>9} {'max |d|':>8} {'mean |d|':>9}")
for n in (22, 63, 299):
    for lbl, other in (("default vs hard-max  (elect floor)", "hardmax"),
                       ("default vs mean-arm  (average ceil)", "meanarm")):
        pct, mx, mn, cnt = moved(f"A_n{n}_default", f"A_n{n}_{other}")
        print(f"{n:>5}  {lbl:<34} {pct:>8.2f}% {mx:>8d} {mn:>9.1f}")
    print()

print("For reference, V-REVIEW's potency arms on the same artefact:")
print("  --pyramid-gate 8.0  -> 16.27% moved")
print("  --pyramid-bands 3   ->  9.66% moved")
print("  --confidence-tail   ->  0.00% moved (inert)")

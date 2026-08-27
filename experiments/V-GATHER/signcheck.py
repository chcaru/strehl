r"""Is window_shift APPLIED in the right direction in certmeasure.py?

est_shift's convention is fixed by its own control at certmeasure.py:246 --
est_shift(a, roll(a, k)) == -k. But a convention is not a usage. certmeasure
consumes it as `yy, xx = y + dy, x + dx` to locate the master's window inside a
source frame, and whether that adds or subtracts the displacement cannot be
settled by reading the sign; it has to be measured against content.

The test plants a known displacement, then asks which of the two candidate
windows actually matches the master's content. Residual is compared, not signs.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import certmeasure as cm                                           # noqa: E402
import sharpaxis as sa                                             # noqa: E402

SUB = "109MSDCF"
W = 512
d = os.path.join(cm.WORK, SUB)
os.makedirs(d, exist_ok=True)
mp = os.path.join(d, "sgn-master.tiff")
got, err, _ = cm.render(SUB, mp)
if not got:
    raise SystemExit("render failed " + err[:200])
mrgb, lat = cm.read_rgb(mp)
ml = sa.lum(mrgb)
del mrgb
os.remove(mp)

K = (23, -17)
synth = np.roll(np.roll(ml, K[0], 0), K[1], 1)   # synth(p) = ml(p - K)
print("planted: source content displaced by %s relative to master" % (K,))
print("%-22s %10s %10s %10s" % ("site", "dy,dx", "resid y+dy", "resid y-dy"))
plus = minus = 0
for (y, x) in sa.pick_sites(ml)[:8]:
    dy, dx, conf = cm.window_shift(ml, synth, (y, x), half=768, win=W)
    ref = ml[y:y + W, x:x + W]

    def resid(a, b):
        ya, xa = a, b
        if ya < 0 or xa < 0 or ya + W > synth.shape[0] or xa + W > synth.shape[1]:
            return float("inf")
        return float(np.abs(synth[ya:ya + W, xa:xa + W] - ref).mean())

    rp, rm = resid(y + dy, x + dx), resid(y - dy, x - dx)
    plus += rp < rm
    minus += rm < rp
    print("(%5d,%5d)  %10s %10.1f %10.1f%s"
          % (y, x, "%+d,%+d" % (dy, dx), rp, rm, "   <-- y-dy wins" if rm < rp else ""))

print("\nsites where y+dy matches content: %d ; where y-dy matches: %d" % (plus, minus))
if minus > plus:
    print("DEFECT: certmeasure.py applies window_shift with the WRONG SIGN; "
          "registration displaces the window AWAY from the matching content.")
elif plus > minus:
    print("CONFIRMED: `yy, xx = y + dy, x + dx` lands on the matching content, "
          "so window_shift's returned sign matches how every call site consumes "
          "it. This is a standing regression control, not an endorsement of any "
          "previously published number: the run preserved as cert-wrongsign.json "
          "was produced BEFORE this negation existed and is retracted.")
else:
    print("INCONCLUSIVE")

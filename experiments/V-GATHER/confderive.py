r"""Derive MIN_CONF instead of typing it.

sharpaxis.py first shipped MIN_CONF = 6.0, a number with no derivation, and it
refused 16 of 16 sites on a subject whose registration was in fact working --
measured shifts of (0,0) and (-1,0) on a 22-frame bracket, which is correct.
A typed threshold that rejects everything looks exactly like a subject with no
usable sites.

The threshold is derived from two measured distributions on the same content:
  RECOVERABLE -- the site against a copy of itself displaced by a known integer
                 shift. The estimator must return that shift. This is the
                 population the axis must ACCEPT.
  UNLOCALISABLE -- the site against independent noise. There is no shift to
                 find. This is the population the axis must REJECT.
MIN_CONF is placed between them, and if they overlap the confidence statistic is
not a usable gate and must be replaced rather than tuned.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import certmeasure as cm                                           # noqa: E402
import sharpaxis as sa                                             # noqa: E402

SUB = sys.argv[1] if len(sys.argv) > 1 else "109MSDCF"
PLANT = (7, -11)

d = os.path.join(cm.WORK, SUB)
os.makedirs(d, exist_ok=True)
mp = os.path.join(d, "conf-master.tiff")
got, err, _ = cm.render(SUB, mp)
if not got:
    raise SystemExit("render failed: " + err[:200])
mrgb, lat = cm.read_rgb(mp)
ml = sa.lum(mrgb)
del mrgb
os.remove(mp)
sites = sa.pick_sites(ml)
rng = np.random.default_rng(5)

rec_conf, rec_ok, null_conf = [], 0, []
for (y, x) in sites:
    cy, cx = y + sa.WIN // 2, x + sa.WIN // 2
    y0, x0, y1, x1 = cy - 768, cx - 768, cy + 768, cx + 768
    # Margin must cover the planted displacement in BOTH directions, or the
    # shifted slice runs off the array and numpy silently returns an empty
    # window rather than raising -- which reaches the FFT as "0 data points".
    my, mx = abs(PLANT[0]), abs(PLANT[1])
    if (y0 - my < 0 or x0 - mx < 0
            or y1 + my > ml.shape[0] or x1 + mx > ml.shape[1]):
        continue
    a = ml[y0:y1, x0:x1]
    b = ml[y0 - PLANT[0]:y1 - PLANT[0], x0 - PLANT[1]:x1 - PLANT[1]]
    dy, dx, conf = cm.est_shift(a, b)
    rec_conf.append(conf)
    ok = (dy, dx) == PLANT
    rec_ok += ok
    n = rng.normal(a.mean(), a.std(), a.shape).astype(np.float32)
    null_conf.append(cm.est_shift(a, n)[2])

rec_conf, null_conf = np.array(rec_conf), np.array(null_conf)
print("sites tested: %d" % len(rec_conf))
print("planted shift %s recovered exactly on %d/%d sites"
      % (PLANT, rec_ok, len(rec_conf)))
if rec_ok != len(rec_conf):
    print("  POSITIVE CONTROL INCOMPLETE -- the estimator does not recover a "
          "known shift on every site; the sign convention or window is wrong")
print("RECOVERABLE  conf: min %.2f  p10 %.2f  median %.2f  max %.2f"
      % (rec_conf.min(), np.percentile(rec_conf, 10), np.median(rec_conf),
         rec_conf.max()))
print("UNLOCALISABLE conf: min %.2f  median %.2f  p90 %.2f  max %.2f"
      % (null_conf.min(), np.median(null_conf), np.percentile(null_conf, 90),
         null_conf.max()))
sep = rec_conf.min() > null_conf.max()
print("\nseparated: %s   (recoverable min %.2f vs unlocalisable max %.2f)"
      % (sep, rec_conf.min(), null_conf.max()))
if sep:
    print("MIN_CONF may be placed at the geometric midpoint: %.2f"
          % float(np.sqrt(rec_conf.min() * null_conf.max())))
else:
    print("OVERLAP -- confidence is not a usable gate on this content")
